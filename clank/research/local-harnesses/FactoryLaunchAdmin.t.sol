// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

// The target-launch-forwarder folder holds byte-identical copies of the factory sources plus the router,
// so everything is imported from there to keep one ClankLaunchFactory type.
import {ClankLaunchFactory} from "fwd/ClankLaunchFactory.sol";
import {ClankLaunchAndBuy} from "fwd/ClankLaunchAndBuy.sol";
import {ClankLaunchDeployer} from "fwd/ClankLaunchDeployer.sol";
import {ClankInitializationGuardHook} from
    "fwd/ClankInitializationGuardHook.sol";
import {ClankBondingCurve} from "fwd/ClankBondingCurve.sol";
import {ClankLauncherToken} from "fwd/ClankLauncherToken.sol";
import {ClankCurveMath} from "fwd/libraries/ClankCurveMath.sol";
import {IPoolManager} from "@uniswap/v4-core/src/interfaces/IPoolManager.sol";
import {IHooks} from "@uniswap/v4-core/src/interfaces/IHooks.sol";
import {PoolKey} from "@uniswap/v4-core/src/types/PoolKey.sol";
import {PoolId, PoolIdLibrary} from "@uniswap/v4-core/src/types/PoolId.sol";
import {Currency} from "@uniswap/v4-core/src/types/Currency.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

interface FVm {
    function deal(address, uint256) external;
    function prank(address) external;
    function startPrank(address) external;
    function stopPrank() external;
    function warp(uint256) external;
    function expectRevert(bytes4) external;
    function expectRevert(bytes calldata) external;
    function expectRevert() external;
}

/// Minimal PoolManager stand-in: mirrors V4's beforeInitialize hook dispatch, slot0 storage
/// location (read by StateLibrary.getSlot0 via extsload) and the transient unlock flag.
contract MockPoolManager {
    using PoolIdLibrary for PoolKey;

    mapping(bytes32 => bytes32) public slots;
    bool public unlockedFlag;

    function initialize(PoolKey memory key, uint160 sqrtPriceX96) external returns (int24) {
        bytes32 slot = keccak256(abi.encodePacked(PoolId.unwrap(key.toId()), bytes32(uint256(6))));
        require(slots[slot] == bytes32(0), "PoolAlreadyInitialized");
        if (uint160(address(key.hooks)) & (1 << 13) != 0) {
            IHooks(address(key.hooks)).beforeInitialize(msg.sender, key, sqrtPriceX96);
        }
        slots[slot] = bytes32(uint256(sqrtPriceX96));
        return 0;
    }

    function extsload(bytes32 slot) external view returns (bytes32) {
        return slots[slot];
    }

    function exttload(bytes32) external view returns (bytes32) {
        return unlockedFlag ? bytes32(uint256(1)) : bytes32(0);
    }
}

contract MockPermit2 {
    function approve(address, address, uint160, uint48) external {}
}

/// Minimal PositionManager stand-in. It mints the NFT to the encoded recipient (the locker) and keeps the
/// attached ETH; it does not pull ERC-20s (executor then routes the unused tokens to the locker as dust).
contract MockPositionManager {
    address public poolManager;
    address public permit2;
    uint256 public nextTokenId = 1;
    mapping(uint256 => address) public ownerOf;
    address public locker;
    bool public fail;

    constructor(address pm, address p2) {
        poolManager = pm;
        permit2 = p2;
    }

    function setLocker(address l) external { locker = l; }
    function setFail(bool f) external { fail = f; }
    function msgSender() external pure returns (address) { return address(0); }

    function modifyLiquidities(bytes calldata, uint256) external payable {
        require(!fail, "mint failed");
        ownerOf[nextTokenId++] = locker;
    }
}

/// Stands in for a malicious/compromised trusted forwarder (the owner can rotate it to any address).
contract EvilForwarder {
    function launchAs(
        ClankLaunchFactory f,
        ClankLaunchFactory.TokenParams calldata p,
        uint256 cfg,
        address victim,
        address[] calldata ex
    ) external returns (address, address) {
        return f.launchTokenFor(p, cfg, address(0), victim, ex);
    }
}

contract FactoryLaunchAdminTest {
    FVm constant vm = FVm(address(uint160(uint256(keccak256("hevm cheat code")))));

    MockPoolManager pm;
    MockPermit2 p2;
    MockPositionManager posm;
    ClankInitializationGuardHook hook;
    ClankLaunchFactory factory;
    ClankLaunchDeployer deployer;
    ClankLaunchAndBuy router;

    address constant VICTIM = address(0xC0FFEE);
    address constant ATTACKER = address(0xBAD);
    address constant BUYER = address(0xB0B);
    address constant SINK = address(0x5151);

    uint256 constant PHANTOM = 4_276_000_000_000_000_000; // ~ the live launch record's phantom quote

    receive() external payable {}

    function setUp() public {
        pm = new MockPoolManager();
        p2 = new MockPermit2();
        posm = new MockPositionManager(address(pm), address(p2));
        hook = _deployHook();

        factory = new ClankLaunchFactory(
            ClankLaunchFactory.DeploymentConfig({
                initialOwner: address(this),
                poolManager: address(pm),
                positionManager: address(posm),
                permit2: address(p2),
                initializationHook: address(hook)
            })
        );
        posm.setLocker(address(factory.locker()));
        hook.setFactory(address(factory));
        deployer = new ClankLaunchDeployer(address(factory));
        factory.setLaunchDeployer(deployer);
        factory.addLaunchConfig(
            ClankLaunchFactory.LaunchConfig({
                supply: ClankCurveMath.TOKEN_SUPPLY,
                curveFeeBps: 100,
                phantomQuote: PHANTOM,
                graduationThreshold: ClankCurveMath.graduationThreshold(PHANTOM),
                poolFee: 3000,
                tickSpacing: 200,
                enabled: true
            })
        );
        factory.setSnipeTaxStartBps(5000);
        factory.setLaunchEnabled(true);
        router = new ClankLaunchAndBuy(factory);
        factory.setLaunchForwarder(address(router));
    }

    // ---------------------------------------------------------------- helpers

    function _deployHook() internal returns (ClankInitializationGuardHook h) {
        bytes memory init = abi.encodePacked(
            type(ClankInitializationGuardHook).creationCode, abi.encode(address(pm), address(this))
        );
        bytes32 initHash = keccak256(init);
        uint256 salt;
        for (; salt < 500_000; ++salt) {
            address a = address(
                uint160(uint256(keccak256(abi.encodePacked(bytes1(0xff), address(this), bytes32(salt), initHash))))
            );
            if (uint160(a) & ((1 << 14) - 1) == (1 << 13)) break;
        }
        address deployed;
        assembly {
            deployed := create2(0, add(init, 32), mload(init), salt)
        }
        require(deployed != address(0), "hook deploy");
        h = ClankInitializationGuardHook(deployed);
    }

    function _params(address feeRecipient, bytes32 expected, bytes32 salt)
        internal
        pure
        returns (ClankLaunchFactory.TokenParams memory p)
    {
        p.name = "Victim Token";
        p.symbol = "VIC";
        p.logo = "ipfs://logo";
        p.description = "d";
        p.creatorFeeRecipient = feeRecipient;
        p.expectedEconomics = expected;
        p.salt = salt;
    }

    function _noEx() internal pure returns (address[] memory) {
        return new address[](0);
    }

    // ------------------------------------------------- identity / squatting

    /// A third party replaying a creator's exact parameters gets different addresses (launchId binds msg.sender),
    /// so the victim's predicted addresses cannot be squatted through the public entrypoints.
    function testDirectLaunchCannotSquatAnotherCreator() public {
        ClankLaunchFactory.TokenParams memory p = _params(address(0), factory.previewLaunchEconomics(0), bytes32("s"));
        (address predToken, address predCurve,) = factory.predictLaunch(VICTIM, p, 0, address(0));

        vm.prank(ATTACKER);
        (address t, address c) = factory.launchToken(p, 0, address(0));
        require(t != predToken && c != predCurve, "squatted");

        vm.prank(VICTIM);
        (address vt, address vc) = factory.launchToken(p, 0, address(0));
        require(vt == predToken && vc == predCurve, "victim launch moved");
    }

    /// Router: originalDeployer is always msg.sender; the router cannot be used to launch as someone else.
    function testRouterBindsCreatorToCaller() public {
        ClankLaunchFactory.TokenParams memory p = _params(ATTACKER, factory.previewLaunchEconomics(0), bytes32("s"));
        (address predToken,,) = factory.predictLaunch(VICTIM, p, 0, address(0));
        vm.deal(ATTACKER, 1 ether);
        vm.prank(ATTACKER);
        (address t,,) = router.launchAndBuy{value: 0.01 ether}(p, 0, address(0), 0.01 ether, 0, ATTACKER, _noEx());
        require(t != predToken, "router let attacker launch as victim");
        require(ClankLauncherToken(t).deployer() == ATTACKER, "deployer");
    }

    function testLaunchTokenForRejectsNonForwarder() public {
        ClankLaunchFactory.TokenParams memory p = _params(address(0), factory.previewLaunchEconomics(0), bytes32("s"));
        vm.prank(ATTACKER);
        vm.expectRevert(ClankLaunchFactory.NotLaunchForwarder.selector);
        factory.launchTokenFor(p, 0, address(0), VICTIM, _noEx());
    }

    /// LOW (owner trust): the forwarder is owner-rotatable and fully trusted with creator identity. A compromised
    /// or malicious forwarder can occupy any creator's predicted addresses (creatorFeeRecipient and exemptions are
    /// not part of launchId), make the token report the victim as deployer, give itself tax-free sniping on that
    /// token, and permanently burn the victim's salt.
    function testRotatedForwarderSquatsVictimAddresses() public {
        ClankLaunchFactory.TokenParams memory victimParams =
            _params(address(0), factory.previewLaunchEconomics(0), bytes32("victim-salt"));
        (address predToken, address predCurve,) = factory.predictLaunch(VICTIM, victimParams, 0, address(0));

        EvilForwarder evil = new EvilForwarder();
        factory.setLaunchForwarder(address(evil)); // owner action

        ClankLaunchFactory.TokenParams memory evilParams = victimParams;
        evilParams.creatorFeeRecipient = ATTACKER;
        address[] memory ex = new address[](1);
        ex[0] = SINK;
        (address t, address c) = evil.launchAs(factory, evilParams, 0, VICTIM, ex);

        require(t == predToken && c == predCurve, "not at victim's address");
        require(ClankLauncherToken(t).deployer() == VICTIM, "deployer spoof");
        require(ClankBondingCurve(payable(c)).snipeTaxExempt(ATTACKER), "attacker exempt");
        require(ClankBondingCurve(payable(c)).snipeTaxExempt(SINK), "sink exempt");
        require(factory.getLaunchedToken(t).creatorFeeRecipient == ATTACKER, "fee recipient");

        // The victim's own launch with the same salt is now impossible.
        vm.prank(VICTIM);
        vm.expectRevert();
        factory.launchToken(victimParams, 0, address(0));
    }

    // ------------------------------------------------------ economics pin

    function testEconomicsPinRejectsAdminChangeBetweenQuoteAndLaunch() public {
        bytes32 quoted = factory.previewLaunchEconomics(0);
        factory.setSnipeTaxStartBps(9900); // admin change after the creator quoted
        ClankLaunchFactory.TokenParams memory p = _params(address(0), quoted, bytes32("s"));
        vm.prank(VICTIM);
        vm.expectRevert(
            abi.encodeWithSelector(
                ClankLaunchFactory.LaunchEconomicsMismatch.selector, quoted, factory.previewLaunchEconomics(0)
            )
        );
        factory.launchToken(p, 0, address(0));
    }

    /// INFO: zero expectedEconomics opts out of the pin; the launch silently takes whatever terms apply at
    /// execution time (documented Pons behaviour, but integrators/routers that default to zero lose protection).
    function testZeroEconomicsFollowsAdminChange() public {
        factory.setSnipeTaxStartBps(9900);
        factory.setSnipeTaxSeconds(60);
        ClankLaunchFactory.TokenParams memory p = _params(address(0), bytes32(0), bytes32("s"));
        vm.prank(VICTIM);
        (, address c) = factory.launchToken(p, 0, address(0));
        require(ClankBondingCurve(payable(c)).snipeTaxStartBps() == 9900, "start");
        require(ClankBondingCurve(payable(c)).snipeTaxSeconds() == 60, "secs");
    }

    // ------------------------------------------------------------- router

    /// The router refunds exactly the curve's terminal remainder to the caller, never pre-existing dust.
    function testRouterNativeRefundExactAndDustNotPaidOut() public {
        // Pre-existing dust in the router (sent by someone else).
        vm.deal(address(this), 1 ether);
        (bool ok,) = address(router).call{value: 0.3 ether}("");
        require(ok, "dust");

        ClankLaunchFactory.TokenParams memory p = _params(VICTIM, factory.previewLaunchEconomics(0), bytes32("s"));
        vm.deal(VICTIM, 100 ether);
        vm.prank(VICTIM);
        (address t, address c, uint256 out) =
            router.launchAndBuy{value: 100 ether}(p, 0, address(0), 100 ether, 0, VICTIM, _noEx());

        require(out == ClankCurveMath.SOLD_TOKENS, "not a full fill");
        require(IERC20(t).balanceOf(VICTIM) == out, "tokens");
        require(address(router).balance == 0.3 ether, "router dust changed");
        // Spent = net reserve + 1% fee (recipient exempt from snipe tax).
        ClankLaunchFactory.Launch memory l = factory.getLaunch(t);
        uint256 spent = 100 ether - VICTIM.balance;
        require(spent > l.sweptQuote && spent - l.sweptQuote < l.sweptQuote / 50, "refund accounting");
        require(ClankBondingCurve(payable(c)).state() == ClankBondingCurve.State.Swept, "auto sweep");
    }

    function testRouterRejectsValueMismatch() public {
        ClankLaunchFactory.TokenParams memory p = _params(VICTIM, factory.previewLaunchEconomics(0), bytes32("s"));
        vm.deal(VICTIM, 2 ether);
        vm.prank(VICTIM);
        vm.expectRevert(abi.encodeWithSelector(ClankLaunchAndBuy.NativeValueMismatch.selector, 2 ether, 1 ether));
        router.launchAndBuy{value: 2 ether}(p, 0, address(0), 1 ether, 0, VICTIM, _noEx());
    }

    // ----------------------------------------------------------- snipe tax

    /// Non-exempt recipients pay the decaying tax; it is credited to the factory's escrow balance, not to anyone else.
    function testSnipeTaxChargedToNonExemptAndCreditedToProtocol() public {
        ClankLaunchFactory.TokenParams memory p = _params(address(0), factory.previewLaunchEconomics(0), bytes32("s"));
        vm.prank(VICTIM);
        (, address c) = factory.launchToken(p, 0, address(0));
        ClankBondingCurve curve = ClankBondingCurve(payable(c));
        require(curve.currentSnipeTaxBps(BUYER) == 4900, "tax at t0");
        require(curve.currentSnipeTaxBps(VICTIM) == 0, "creator exempt");

        vm.deal(BUYER, 1 ether);
        vm.prank(BUYER);
        curve.buy{value: 1 ether}(1 ether, 0, BUYER);
        // fee (1%) + tax (49%) = 50% of the gross went to the factory's escrow credit.
        require(factory.feeEscrow().balanceOf(address(factory)) == 0.5 ether, "credit");
    }

    // ------------------------------------------------- swept / rescue lifecycle

    function _launchAndSweep() internal returns (address t, ClankBondingCurve curve) {
        ClankLaunchFactory.TokenParams memory p = _params(address(0), factory.previewLaunchEconomics(0), bytes32("s"));
        vm.prank(VICTIM);
        address c;
        (t, c) = factory.launchToken(p, 0, address(0));
        curve = ClankBondingCurve(payable(c));
        vm.warp(block.timestamp + 61);
        vm.deal(BUYER, 100 ether);
        vm.prank(BUYER);
        curve.buy{value: 100 ether}(100 ether, 0, BUYER);
        require(curve.state() == ClankBondingCurve.State.Swept, "not swept");
    }

    /// Third parties cannot pre-initialize the graduated pool key: the hook only accepts the factory.
    function testThirdPartyCannotPreInitializeGraduationPool() public {
        (address t,) = _launchAndSweep();
        PoolKey memory key = PoolKey({
            currency0: Currency.wrap(address(0)),
            currency1: Currency.wrap(t),
            fee: 3000,
            tickSpacing: 200,
            hooks: IHooks(address(hook))
        });
        vm.prank(ATTACKER);
        vm.expectRevert(ClankInitializationGuardHook.NotFactory.selector);
        pm.initialize(key, 2 ** 96);
    }

    /// Rescue cannot be used to seize reserves when migration works: it migrates instead and pays nobody.
    function testRescueMigratesWhenPossible() public {
        (address t, ClankBondingCurve curve) = _launchAndSweep();
        vm.expectRevert();
        factory.rescueSweptGraduation(t, address(this)); // too early
        vm.warp(block.timestamp + 7 days);
        uint256 before = address(this).balance;
        factory.rescueSweptGraduation{gas: 8_000_000}(t, SINK);
        require(curve.state() == ClankBondingCurve.State.PoolCreated, "should have migrated");
        require(address(this).balance == before && SINK.balance == 0, "paid someone");
    }

    /// INFO/centralization: when migration fails the owner receives all reserves (the recipient argument is ignored).
    function testRescuePaysOwnerIgnoringRecipient() public {
        (address t, ClankBondingCurve curve) = _launchAndSweep();
        ClankLaunchFactory.Launch memory l = factory.getLaunch(t);
        posm.setFail(true);
        vm.warp(block.timestamp + 7 days);
        uint256 before = address(this).balance;
        factory.rescueSweptGraduation{gas: 8_000_000}(t, SINK);
        require(curve.state() == ClankBondingCurve.State.Rescued, "state");
        require(address(this).balance - before == l.sweptQuote, "owner got quote");
        require(IERC20(t).balanceOf(address(this)) == l.sweptTokens, "owner got tokens");
        require(SINK.balance == 0, "recipient ignored");
    }

    /// Unknown tokens / wrong states are rejected on every admin lifecycle entrypoint.
    function testLifecycleGuards() public {
        vm.expectRevert(ClankLaunchFactory.TokenNotFound.selector);
        factory.rescueSweptGraduation(address(0x1234), SINK);
        vm.expectRevert(ClankLaunchFactory.OnlySelf.selector);
        factory.attemptRescueMigration(address(0x1234));
        vm.expectRevert(ClankLaunchFactory.OnlySelf.selector);
        factory.attemptForceGraduation(address(0x1234));
        vm.prank(ATTACKER);
        vm.expectRevert();
        factory.rescueSweptGraduation(address(0x1234), ATTACKER);
    }
}
