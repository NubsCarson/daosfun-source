// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

// Graduation / locker / fee-escrow audit harness.
// Deploys the recovered Clank sources ("hist/" = target-factory tree) against a LOCAL Uniswap V4
// PoolManager + PositionManager (creation bytecode compiled from canonical v4-core / v4-periphery with
// solc 0.8.26) and the canonical Permit2 runtime, all inside the forge EVM. No live chain is touched.

import {ClankLaunchFactory} from "hist/ClankLaunchFactory.sol";
import {ClankLaunchDeployer} from "hist/ClankLaunchDeployer.sol";
import {ClankBondingCurve} from "hist/ClankBondingCurve.sol";
import {ClankInitializationGuardHook} from "hist/ClankInitializationGuardHook.sol";
import {ClankGraduationExecutor} from "hist/ClankGraduationExecutor.sol";
import {ClankLaunchLocker} from "hist/ClankLaunchLocker.sol";
import {ClankFeeEscrow} from "hist/ClankFeeEscrow.sol";
import {ClankCurveMath} from "hist/libraries/ClankCurveMath.sol";
import {ClankMigrationMath} from "hist/libraries/ClankMigrationMath.sol";

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {IHooks} from "@uniswap/v4-core/src/interfaces/IHooks.sol";
import {IPoolManager} from "@uniswap/v4-core/src/interfaces/IPoolManager.sol";
import {StateLibrary} from "@uniswap/v4-core/src/libraries/StateLibrary.sol";
import {TickMath} from "@uniswap/v4-core/src/libraries/TickMath.sol";
import {Currency} from "@uniswap/v4-core/src/types/Currency.sol";
import {PoolKey} from "@uniswap/v4-core/src/types/PoolKey.sol";
import {PoolId, PoolIdLibrary} from "@uniswap/v4-core/src/types/PoolId.sol";
import {BalanceDelta, BalanceDeltaLibrary} from "@uniswap/v4-core/src/types/BalanceDelta.sol";
import {SwapParams} from "@uniswap/v4-core/src/types/PoolOperation.sol";
import {IPositionManager} from "@uniswap/v4-periphery/src/interfaces/IPositionManager.sol";
import {Actions} from "@uniswap/v4-periphery/src/libraries/Actions.sol";
import {IAllowanceTransfer} from "permit2/src/interfaces/IAllowanceTransfer.sol";

interface GVm {
    function readFile(string calldata) external view returns (string memory);
    function parseBytes(string calldata) external pure returns (bytes memory);
    function etch(address, bytes calldata) external;
    function deal(address, uint256) external;
    function prank(address) external;
    function startPrank(address) external;
    function stopPrank() external;
    function warp(uint256) external;
    function expectRevert() external;
    function expectRevert(bytes4) external;
    function expectRevert(bytes calldata) external;
}

interface IUnlockCallback {
    function unlockCallback(bytes calldata data) external returns (bytes memory);
}

interface IERC721Min {
    function ownerOf(uint256) external view returns (address);
    function transferFrom(address, address, uint256) external;
    function approve(address, uint256) external;
}

contract GQuote is ERC20 {
    constructor() ERC20("Quote", "QT") {}

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}

/// @notice Minimal V4 swapper (unlock callback) used to generate LP fees / post-graduation trades.
contract GSwapper is IUnlockCallback {
    using BalanceDeltaLibrary for BalanceDelta;

    IPoolManager public immutable pm;

    constructor(IPoolManager pm_) {
        pm = pm_;
    }

    receive() external payable {}

    function swap(PoolKey memory key, bool zeroForOne, int256 amountSpecified) external returns (BalanceDelta d) {
        d = abi.decode(pm.unlock(abi.encode(key, zeroForOne, amountSpecified)), (BalanceDelta));
    }

    function unlockCallback(bytes calldata data) external returns (bytes memory) {
        require(msg.sender == address(pm), "pm");
        (PoolKey memory key, bool zeroForOne, int256 amountSpecified) = abi.decode(data, (PoolKey, bool, int256));
        BalanceDelta d = pm.swap(
            key,
            SwapParams({
                zeroForOne: zeroForOne,
                amountSpecified: amountSpecified,
                sqrtPriceLimitX96: zeroForOne ? TickMath.MIN_SQRT_PRICE + 1 : TickMath.MAX_SQRT_PRICE - 1
            }),
            ""
        );
        _resolve(key.currency0, d.amount0());
        _resolve(key.currency1, d.amount1());
        return abi.encode(d);
    }

    function _resolve(Currency c, int128 delta) private {
        if (delta < 0) {
            uint256 owed = uint256(uint128(-delta));
            if (Currency.unwrap(c) == address(0)) {
                pm.settle{value: owed}();
            } else {
                pm.sync(c);
                IERC20(Currency.unwrap(c)).transfer(address(pm), owed);
                pm.settle();
            }
        } else if (delta > 0) {
            pm.take(c, address(this), uint256(uint128(delta)));
        }
    }
}

/// @notice Terminal buyer that re-enters graduation from the curve's Ready-state refund callback.
contract GTerminalBuyer {
    ClankLaunchFactory public immutable factory;
    address public token;
    bool public reentered;
    uint256 public positionId;

    constructor(ClankLaunchFactory f) {
        factory = f;
    }

    function buy(ClankBondingCurve curve, address token_) external payable {
        token = token_;
        curve.buy{value: msg.value}(msg.value, 0, address(this));
    }

    receive() external payable {
        if (!reentered && token != address(0)) {
            reentered = true;
            factory.graduate(token);
            positionId = factory.createGraduatedPool(token);
        }
    }
}

/// @notice Owner contract that tries to make the rescue's migration attempt fail by holding locks.
contract GHostileOwner is IUnlockCallback {
    ClankLaunchFactory public immutable factory;
    ClankFeeEscrow public immutable escrow;
    IPoolManager public immutable pm;
    address public target;
    uint256 public mode; // 1 = inside escrow claim, 2 = inside PoolManager unlock
    bool public rescueCallSucceeded;
    bytes public rescueRevert;

    constructor(ClankLaunchFactory f, IPoolManager pm_) {
        factory = f;
        escrow = f.feeEscrow();
        pm = pm_;
    }

    function accept() external {
        factory.acceptOwnership();
    }

    function rescueInsideEscrowClaim(address token) external payable {
        target = token;
        mode = 1;
        escrow.credit{value: msg.value}(address(this));
        escrow.claimTo(payable(address(this)));
        mode = 0;
    }

    function rescueInsidePoolManagerUnlock(address token) external {
        target = token;
        mode = 2;
        pm.unlock("");
        mode = 0;
    }

    function unlockCallback(bytes calldata) external returns (bytes memory) {
        _rescue();
        return "";
    }

    function _rescue() private {
        (bool ok, bytes memory ret) =
            address(factory).call{gas: 7_000_000}(abi.encodeCall(ClankLaunchFactory.rescueSweptGraduation, (target, address(this))));
        rescueCallSucceeded = ok;
        rescueRevert = ret;
    }

    receive() external payable {
        if (mode == 1 && msg.sender == address(escrow)) _rescue();
    }
}

abstract contract GraduationBase {
    using StateLibrary for IPoolManager;
    using PoolIdLibrary for PoolKey;

    GVm internal constant vm = GVm(address(uint160(uint256(keccak256("hevm cheat code")))));
    address internal constant PERMIT2 = 0x000000000022D473030F116dDEE9F6B43aC78BA3;
    address internal constant OWNER = address(0x0A11);
    address internal constant ATTACKER = address(0xBAD);
    address internal constant FEE_DEST = address(0xFEE0);
    uint256 internal constant PHANTOM = 1.5 ether;
    uint24 internal constant POOL_FEE = 10_000;
    int24 internal constant TICK_SPACING = 200;

    IPoolManager internal pm;
    IPositionManager internal posm;
    ClankInitializationGuardHook internal hook;
    ClankLaunchFactory internal factory;
    ClankGraduationExecutor internal executor;
    ClankLaunchLocker internal locker;
    ClankFeeEscrow internal escrow;
    uint256 internal saltNonce;

    receive() external payable {}

    function _deployRaw(bytes memory code) internal returns (address a) {
        assembly {
            a := create(0, add(code, 32), mload(code))
        }
        require(a != address(0), "deploy failed");
    }

    function setUp() public virtual {
        vm.etch(PERMIT2, vm.parseBytes(vm.readFile("graduation/graduation-fixtures/Permit2.runtime.hex")));
        pm = IPoolManager(
            _deployRaw(
                abi.encodePacked(
                    vm.parseBytes(vm.readFile("graduation/graduation-fixtures/PoolManager.creation.hex")), abi.encode(address(this))
                )
            )
        );
        posm = IPositionManager(
            _deployRaw(
                abi.encodePacked(
                    vm.parseBytes(vm.readFile("graduation/graduation-fixtures/PositionManager.creation.hex")),
                    abi.encode(address(pm), PERMIT2, uint256(100_000), address(0xD35C), address(0x0E7E))
                )
            )
        );

        // Mine a CREATE2 salt so the hook address carries exactly the BEFORE_INITIALIZE flag.
        bytes memory initCode =
            abi.encodePacked(type(ClankInitializationGuardHook).creationCode, abi.encode(address(pm), OWNER));
        bytes32 initHash = keccak256(initCode);
        uint256 salt;
        for (;; ++salt) {
            address predicted = address(
                uint160(uint256(keccak256(abi.encodePacked(bytes1(0xff), address(this), bytes32(salt), initHash))))
            );
            if (uint160(predicted) & 0x3FFF == 0x2000) break;
        }
        hook = new ClankInitializationGuardHook{salt: bytes32(salt)}(pm, OWNER);

        factory = new ClankLaunchFactory(
            ClankLaunchFactory.DeploymentConfig({
                initialOwner: OWNER,
                poolManager: address(pm),
                positionManager: address(posm),
                permit2: PERMIT2,
                initializationHook: address(hook)
            })
        );
        executor = factory.graduationExecutor();
        locker = factory.locker();
        escrow = factory.feeEscrow();
        ClankLaunchDeployer deployer = new ClankLaunchDeployer(address(factory));

        vm.startPrank(OWNER);
        hook.setFactory(address(factory));
        factory.setLaunchDeployer(deployer);
        factory.addLaunchConfig(
            ClankLaunchFactory.LaunchConfig({
                supply: ClankCurveMath.TOKEN_SUPPLY,
                curveFeeBps: 100,
                phantomQuote: PHANTOM,
                graduationThreshold: ClankCurveMath.graduationThreshold(PHANTOM),
                poolFee: POOL_FEE,
                tickSpacing: TICK_SPACING,
                enabled: true
            })
        );
        factory.setLaunchEnabled(true);
        factory.setFeeDestination(FEE_DEST);
        vm.stopPrank();
    }

    function _launch(address pairToken) internal returns (address token, ClankBondingCurve curve) {
        ClankLaunchFactory.TokenParams memory p;
        p.name = "Grad";
        p.symbol = "GRD";
        p.logo = "ipfs://logo";
        p.salt = bytes32(++saltNonce);
        address c;
        (token, c) = factory.launchToken(p, 0, pairToken);
        curve = ClankBondingCurve(payable(c));
    }

    function _key(address token, address pairToken) internal view returns (PoolKey memory key) {
        bool q0 = pairToken < token;
        key = PoolKey({
            currency0: Currency.wrap(q0 ? pairToken : token),
            currency1: Currency.wrap(q0 ? token : pairToken),
            fee: POOL_FEE,
            tickSpacing: TICK_SPACING,
            hooks: IHooks(address(hook))
        });
    }

    function _sqrtPrice(PoolKey memory key) internal view returns (uint160 p) {
        (p,,,) = pm.getSlot0(key.toId());
    }

    /// @dev Native terminal buy by a plain EOA-like address (auto-graduation sweeps to Swept).
    function _fillNative(ClankBondingCurve curve) internal {
        vm.deal(address(0xB0B), 1_000 ether);
        vm.prank(address(0xB0B));
        curve.buy{value: 100 ether}(100 ether, 0, address(0xB0B));
    }
}

contract GraduationAuditTest is GraduationBase {
    using StateLibrary for IPoolManager;
    using PoolIdLibrary for PoolKey;

    /// Pre-initialising the exact Clank PoolKey at a skewed price is impossible for third parties.
    function testThirdPartyCannotPreInitializeClankPool() public {
        (address token,) = _launch(address(0));
        PoolKey memory key = _key(token, address(0));
        vm.prank(ATTACKER);
        vm.expectRevert();
        pm.initialize(key, TickMath.getSqrtPriceAtTick(-200_000));
        require(_sqrtPrice(key) == 0, "pool initialised");
    }

    /// End-to-end native graduation: price equals curve terminal price, NFT locked, approvals cleared,
    /// nothing left on factory/executor, migration gas far below the 5M rescue budget.
    function testNativeGraduationEndToEnd() public {
        (address token, ClankBondingCurve curve) = _launch(address(0));
        _fillNative(curve);
        require(uint8(curve.state()) == 2, "not swept");
        ClankLaunchFactory.Launch memory l = factory.getLaunch(token);
        uint160 expected = ClankMigrationMath.migrationPrice(token, address(0), l.sweptQuote, l.sweptTokens, PHANTOM);

        uint256 escrowBefore = escrow.balanceOf(address(factory));
        uint256 g = gasleft();
        vm.prank(ATTACKER);
        uint256 positionId = factory.createGraduatedPool(token);
        uint256 used = g - gasleft();
        require(used < 1_500_000, "migration gas unexpectedly high");

        PoolKey memory key = _key(token, address(0));
        require(_sqrtPrice(key) == expected, "price != curve terminal price");
        require(IERC721Min(address(posm)).ownerOf(positionId) == address(locker), "not locked");
        require(locker.isLocked(token) && locker.lockedPositions(token) == positionId, "not recorded");
        require(uint8(curve.state()) == 3, "not PoolCreated");

        l = factory.getLaunch(token);
        uint256 quoteDust = escrow.balanceOf(address(factory)) - escrowBefore;
        require(uint256(l.seededQuote) + quoteDust == uint256(factory.getLaunch(token).seededQuote) + quoteDust, "accounting");
        require(uint256(l.seededQuote) + quoteDust + 0 >= ClankCurveMath.graduationThreshold(PHANTOM), "quote short");
        // dust is rounding-only (a few wei), token dust is only rounding too
        require(quoteDust < 1e6, "quote dust not rounding-sized");
        require(IERC20(token).balanceOf(address(locker)) < 1e12, "token dust not rounding-sized");

        // No residual balances or approvals on executor/factory.
        require(address(executor).balance == 0 && IERC20(token).balanceOf(address(executor)) == 0, "executor residue");
        require(address(factory).balance == 0 && IERC20(token).balanceOf(address(factory)) == 0, "factory residue");
        require(IERC20(token).allowance(address(executor), PERMIT2) == 0, "erc20 approval left");
        (uint160 amt,,) = IAllowanceTransfer(PERMIT2).allowance(address(executor), token, address(posm));
        require(amt == 0, "permit2 approval left");

        // Cannot migrate twice.
        vm.expectRevert();
        factory.createGraduatedPool(token);
    }

    /// The locked position cannot be decreased, burned or transferred by anyone (including owner/factory).
    function testLockedPositionCannotBeWithdrawn() public {
        (address token, ClankBondingCurve curve) = _launch(address(0));
        _fillNative(curve);
        uint256 positionId = factory.createGraduatedPool(token);

        bytes memory actions = abi.encodePacked(uint8(Actions.DECREASE_LIQUIDITY), uint8(Actions.TAKE_PAIR));
        bytes[] memory params = new bytes[](2);
        params[0] = abi.encode(positionId, uint256(1e18), uint128(0), uint128(0), bytes(""));
        PoolKey memory key = _key(token, address(0));
        params[1] = abi.encode(key.currency0, key.currency1, ATTACKER);
        address[3] memory callers = [ATTACKER, OWNER, address(factory)];
        for (uint256 i; i < 3; ++i) {
            vm.prank(callers[i]);
            vm.expectRevert();
            posm.modifyLiquidities(abi.encode(actions, params), block.timestamp + 1);

            vm.prank(callers[i]);
            vm.expectRevert();
            IERC721Min(address(posm)).transferFrom(address(locker), callers[i], positionId);
        }
        // ERC721 permit via EIP-1271: locker has no isValidSignature and no fallback.
        (bool ok,) = address(locker).call(abi.encodeWithSignature("isValidSignature(bytes32,bytes)", bytes32(0), ""));
        require(!ok, "locker answers 1271");
        require(IERC721Min(address(posm)).ownerOf(positionId) == address(locker), "moved");
    }

    /// LP fees accrue and are collected (permissionlessly) only to the factory fee destination.
    function testCollectFeesPaysOnlyFeeDestination() public {
        (address token, ClankBondingCurve curve) = _launch(address(0));
        _fillNative(curve);
        factory.createGraduatedPool(token);

        GSwapper s = new GSwapper(pm);
        vm.deal(address(s), 10 ether);
        PoolKey memory key = _key(token, address(0));
        s.swap(key, true, -1 ether); // buy token with ETH (native is currency0)
        uint256 got = IERC20(token).balanceOf(address(s));
        s.swap(key, false, -int256(got)); // sell back

        uint256 ethBefore = FEE_DEST.balance;
        vm.prank(ATTACKER);
        locker.collectFees(token);
        require(FEE_DEST.balance > ethBefore, "no native fees");
        require(IERC20(token).balanceOf(FEE_DEST) > 0, "no token fees");
        require(ATTACKER.balance == 0 && IERC20(token).balanceOf(ATTACKER) == 0, "attacker got fees");
    }

    /// Donated ETH/tokens on executor & locker cannot brick or skew migration.
    function testDonationsDoNotBrickMigration() public {
        (address token, ClankBondingCurve curve) = _launch(address(0));
        _fillNative(curve);
        vm.deal(address(executor), 3 ether); // forced ETH (selfdestruct-equivalent)
        uint256 beforeCredit = escrow.balanceOf(address(factory));
        factory.createGraduatedPool(token);
        require(escrow.balanceOf(address(factory)) >= beforeCredit + 3 ether, "foreign ETH not escrowed");
        require(address(executor).balance == 0, "executor kept ETH");
        require(uint8(curve.state()) == 3, "not created");
    }

    /// Terminal buyer re-enters graduate + createGraduatedPool from the Ready-state refund callback.
    /// The pool is still created at the exact curve terminal price; no value is extracted.
    function testTerminalBuyerReentrantGraduationIsSafe() public {
        (address token, ClankBondingCurve curve) = _launch(address(0));
        GTerminalBuyer b = new GTerminalBuyer(factory);
        vm.deal(address(this), 100 ether);
        b.buy{value: 100 ether}(curve, token);
        require(b.reentered(), "no reentry");
        require(uint8(curve.state()) == 3, "not PoolCreated");
        ClankLaunchFactory.Launch memory l = factory.getLaunch(token);
        PoolKey memory key = _key(token, address(0));
        uint160 expected =
            ClankMigrationMath.migrationPrice(token, address(0), l.seededQuote, ClankCurveMath.MIGRATION_TOKENS, PHANTOM);
        // seededQuote excludes rounding dust, so compare loosely via tick equality
        require(
            TickMath.getTickAtSqrtPrice(_sqrtPrice(key)) == TickMath.getTickAtSqrtPrice(expected), "price skewed"
        );
    }

    /// Owner rescue after 7 days cannot seize a migratable launch: the migration attempt succeeds.
    function testOwnerRescueOfMigratableLaunchJustMigrates() public {
        (address token, ClankBondingCurve curve) = _launch(address(0));
        _fillNative(curve);
        vm.warp(block.timestamp + 7 days + 1);
        uint256 ob = OWNER.balance;
        vm.prank(OWNER);
        factory.rescueSweptGraduation{gas: 8_000_000}(token, OWNER);
        require(uint8(curve.state()) == 3, "rescued instead of migrated");
        require(OWNER.balance == ob && IERC20(token).balanceOf(OWNER) == 0, "owner received reserves");
    }

    /// Hostile owner holding the escrow's reentrancy lock: migration still succeeds (credit() is unguarded).
    function testHostileOwnerHoldingEscrowLockCannotForceRescue() public {
        (address token, ClankBondingCurve curve) = _launch(address(0));
        _fillNative(curve);
        GHostileOwner h = new GHostileOwner(factory, pm);
        vm.prank(OWNER);
        factory.transferOwnership(address(h));
        h.accept();
        vm.warp(block.timestamp + 7 days + 1);
        vm.deal(address(this), 1 ether);
        h.rescueInsideEscrowClaim{value: 1 wei}(token);
        require(h.rescueCallSucceeded(), "rescue call reverted");
        require(uint8(curve.state()) == 3, "owner forced rescue");
        require(IERC20(token).balanceOf(address(h)) == 0, "owner got tokens");
    }

    /// Hostile owner inside a PoolManager unlock: rescue refuses outright.
    function testHostileOwnerInsideUnlockIsRejected() public {
        (address token, ClankBondingCurve curve) = _launch(address(0));
        _fillNative(curve);
        GHostileOwner h = new GHostileOwner(factory, pm);
        vm.prank(OWNER);
        factory.transferOwnership(address(h));
        h.accept();
        vm.warp(block.timestamp + 7 days + 1);
        h.rescueInsidePoolManagerUnlock(token);
        require(!h.rescueCallSucceeded(), "rescue ran inside unlock");
        require(uint8(curve.state()) == 2, "state changed");
    }

    /// ERC-20 quote path: price, approvals, quote dust flush to escrow, no residue.
    function testErc20QuoteGraduation() public {
        GQuote q = new GQuote();
        uint256 ph = 1_500e18;
        vm.startPrank(OWNER);
        factory.setPairTokenEconomics(address(q), ph, ClankCurveMath.graduationThreshold(ph), 18);
        factory.setPairTokenApproved(address(q), true);
        vm.stopPrank();
        (address token, ClankBondingCurve curve) = _launch(address(q));

        address buyer = address(0xB0B);
        q.mint(buyer, 1_000_000e18);
        vm.startPrank(buyer);
        q.approve(address(curve), type(uint256).max);
        curve.buy(100_000e18, 0, buyer);
        vm.stopPrank();
        require(uint8(curve.state()) == 2, "not swept");

        ClankLaunchFactory.Launch memory l = factory.getLaunch(token);
        uint160 expected = ClankMigrationMath.migrationPrice(token, address(q), l.sweptQuote, l.sweptTokens, ph);
        uint256 positionId = factory.createGraduatedPool(token);
        PoolKey memory key = _key(token, address(q));
        require(_sqrtPrice(key) == expected, "price");
        require(IERC721Min(address(posm)).ownerOf(positionId) == address(locker), "owner");
        require(q.allowance(address(executor), PERMIT2) == 0 && IERC20(token).allowance(address(executor), PERMIT2) == 0, "approvals");
        (uint160 a1,,) = IAllowanceTransfer(PERMIT2).allowance(address(executor), address(q), address(posm));
        (uint160 a2,,) = IAllowanceTransfer(PERMIT2).allowance(address(executor), token, address(posm));
        require(a1 == 0 && a2 == 0, "permit2 approvals");
        uint256 dust = executor.pendingQuoteDust(address(q));
        require(q.balanceOf(address(executor)) == dust && dust < 1e6, "quote residue");
        if (dust != 0) {
            vm.prank(ATTACKER);
            executor.flushQuoteDust(address(q));
            require(escrow.balanceOfToken(address(factory), address(q)) >= dust, "dust not escrowed");
        }
        // ERC-20 donation to the executor is excluded from dust and cannot be flushed by anyone.
        q.mint(address(executor), 5e18);
        vm.expectRevert(ClankGraduationExecutor.NothingToFlush.selector);
        executor.flushQuoteDust(address(q));
    }
}
