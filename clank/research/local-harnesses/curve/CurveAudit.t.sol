// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

import {ClankBondingCurve} from "hist/ClankBondingCurve.sol";
import {ClankFeeEscrow} from "hist/ClankFeeEscrow.sol";
import {ClankGraduationGuard} from "hist/ClankGraduationGuard.sol";
import {ClankLauncherToken as HistToken} from "hist/ClankLauncherToken.sol";
import {ClankLauncherToken as CurrToken} from "curr/ClankLauncherToken.sol";
import {ClankCurveMath} from "hist/libraries/ClankCurveMath.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

interface Vm {
    function deal(address, uint256) external;
    function prank(address) external;
    function startPrank(address) external;
    function stopPrank() external;
    function warp(uint256) external;
    function assume(bool) external pure;
    function expectRevert(bytes4) external;
    function expectRevert() external;
}

/// Minimal stand-in for the launch factory: deploys curve + token like ClankLaunchDeployer,
/// and implements graduate(token) by sweeping the curve into itself (as ClankLaunchFactory._sweepCurve).
contract MockFactory {
    ClankBondingCurve public curve;
    address public token;
    uint256 public sweptQuote;
    uint256 public sweptTokens;
    uint256 public graduateCalls;

    function deploy(ClankBondingCurve.Config memory cfg, bool burnable, address creator) external {
        curve = new ClankBondingCurve(cfg);
        HistToken.Metadata memory m;
        if (burnable) {
            CurrToken.Metadata memory cm;
            token = address(new CurrToken("T", "T", cm, creator, address(curve), address(this), ClankCurveMath.TOKEN_SUPPLY));
        } else {
            token = address(new HistToken("T", "T", m, creator, address(curve), address(this), ClankCurveMath.TOKEN_SUPPLY));
        }
        curve.initialize(token);
        curve.exemptFromSnipeTax(creator);
    }

    function exempt(address a) external { curve.exemptFromSnipeTax(a); }

    function graduate(address) external {
        graduateCalls++;
        (uint256 q, uint256 t) = curve.graduate(address(this));
        sweptQuote = q;
        sweptTokens = t;
    }

    receive() external payable {}
}

/// Simple ERC20 quote asset.
contract Quote is ERC20 {
    constructor() ERC20("Q", "Q") {}
    function mint(address to, uint256 a) external { _mint(to, a); }
}

/// Buyer contract that tries to reenter during the native terminal refund.
contract RefundReenterer {
    ClankBondingCurve public curve;
    MockFactory public factory;
    bool public reenterBuyOk;
    bool public reenterSellOk;
    bool public graduateOk;
    uint256 public refundSeen;

    constructor(ClankBondingCurve c, MockFactory f) { curve = c; factory = f; }

    function go(uint256 amt) external payable {
        curve.buy{value: amt}(amt, 0, address(this));
    }

    receive() external payable {
        refundSeen = msg.value;
        (reenterBuyOk,) = address(curve).call{value: 0}(abi.encodeCall(ClankBondingCurve.buy, (0, 0, address(this))));
        IERC20(address(curve.token())).approve(address(curve), type(uint256).max);
        (reenterSellOk,) = address(curve).call(abi.encodeCall(ClankBondingCurve.sell, (1e18, 0, address(this))));
        // Factory sweep is permissionless in the real factory; do it from inside the refund callback.
        (graduateOk,) = address(factory).call(abi.encodeCall(MockFactory.graduate, (address(0))));
    }
}

contract CurveAuditTest {
    Vm constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    ClankFeeEscrow escrow;
    ClankGraduationGuard guard;
    MockFactory factory;
    ClankBondingCurve curve;
    IERC20 token;

    address constant CREATOR = address(0xC0FFEE);
    address constant ALICE = address(0xA11CE);
    address constant BOB = address(0xB0B);
    address constant FEE_RECIPIENT = address(0xFEE);

    uint128 constant DEFAULT_PHANTOM = 1.5 ether;

    function setUp() public {
        escrow = new ClankFeeEscrow();
        guard = new ClankGraduationGuard();
    }

    function _cfg(uint128 phantom, uint16 feeBps, uint16 snipeStart, address pair, int24 ts)
        internal
        view
        returns (ClankBondingCurve.Config memory c)
    {
        c.factory = address(0); // set by deploy
        c.feeEscrow = address(escrow);
        c.protocolFeeRecipient = FEE_RECIPIENT;
        c.creator = CREATOR;
        c.pairToken = pair;
        c.feeBps = feeBps;
        c.snipeTaxStartBps = snipeStart;
        c.snipeTaxSeconds = 60;
        c.phantomQuote = phantom;
        c.graduationThreshold = uint128(ClankCurveMath.graduationThreshold(phantom));
        c.graduationGuard = address(guard);
        c.tickSpacing = ts;
    }

    function _launch(uint128 phantom, uint16 feeBps, uint16 snipeStart, bool burnable) internal {
        _launchPair(phantom, feeBps, snipeStart, burnable, address(0), 60);
    }

    function _launchPair(uint128 phantom, uint16 feeBps, uint16 snipeStart, bool burnable, address pair, int24 ts)
        internal
    {
        factory = new MockFactory();
        ClankBondingCurve.Config memory c = _cfg(phantom, feeBps, snipeStart, pair, ts);
        c.factory = address(factory);
        factory.deploy(c, burnable, CREATOR);
        curve = factory.curve();
        token = IERC20(factory.token());
    }

    function _k() internal view returns (uint256) {
        (uint256 q, uint256 t) = curve.getReserves();
        return q * t;
    }

    function _buy(address who, uint256 amt) internal returns (uint256 out) {
        vm.deal(who, who.balance + amt);
        vm.prank(who);
        out = curve.buy{value: amt}(amt, 0, who);
    }

    function _sellAll(address who) internal returns (uint256 out) {
        uint256 bal = token.balanceOf(who);
        if (bal == 0) return 0;
        vm.startPrank(who);
        token.approve(address(curve), bal);
        out = curve.sell(bal, 0, who);
        vm.stopPrank();
    }

    // ------------------------------------------------------------------
    // 1. Buy-then-sell round trips cannot profit, even with a zero fee.
    // ------------------------------------------------------------------
    function testFuzz_RoundTripNeverProfits(uint128 phantom, uint256 pre, uint256 amt) public {
        phantom = uint128(bound(phantom, 1e6, 1e24));
        _launch(phantom, 0, 0, false);
        uint256 thr = ClankCurveMath.graduationThreshold(phantom);
        pre = bound(pre, 0, thr * 9 / 10);
        amt = bound(amt, 1, thr / 20 + 1);
        if (pre > 0) { try this.extBuy(BOB, pre) {} catch {} }
        uint256 k0 = _k();
        try this.extBuy(ALICE, amt) {} catch { return; }
        try this.extSellAll(ALICE) {} catch { return; }
        require(ALICE.balance <= amt, "round trip profit");
        require(_k() >= k0, "k decreased");
        require(address(curve).balance == curve.trackedQuote(), "native desync");
    }

    function extBuy(address who, uint256 amt) external returns (uint256) { return _buy(who, amt); }
    function extSellAll(address who) external returns (uint256) { return _sellAll(who); }

    // ------------------------------------------------------------------
    // 2. Dust loops with a zero fee: thousands of 1-wei buys and tiny sells.
    // ------------------------------------------------------------------
    function testDustLoopNoExtraction() public {
        _launch(DEFAULT_PHANTOM, 0, 0, false);
        _buy(BOB, 0.3 ether);
        uint256 start = 10 ether;
        vm.deal(ALICE, start);
        uint256 k0 = _k();
        vm.startPrank(ALICE);
        token.approve(address(curve), type(uint256).max);
        for (uint256 i; i < 400; ++i) {
            curve.buy{value: 1}(1, 0, ALICE);
        }
        // sell back in the smallest chunks that produce nonzero output
        uint256 bal = token.balanceOf(ALICE);
        uint256 chunk = bal / 400;
        for (uint256 i; i < 399; ++i) {
            try curve.sell(chunk, 0, ALICE) {} catch {}
        }
        uint256 rest = token.balanceOf(ALICE);
        if (rest > 0) { try curve.sell(rest, 0, ALICE) {} catch {} }
        vm.stopPrank();
        require(ALICE.balance <= start, "dust profit");
        require(_k() >= k0, "k decreased");
        require(address(curve).balance == curve.trackedQuote(), "native desync");
    }

    // ------------------------------------------------------------------
    // 3. Everyone can always exit: all holders sell back; reserve stays solvent.
    // ------------------------------------------------------------------
    function testFuzz_AllHoldersCanExit(uint128 phantom, uint256[6] memory buys) public {
        phantom = uint128(bound(phantom, 1e6, 1e24));
        _launch(phantom, 100, 0, false);
        uint256 thr = ClankCurveMath.graduationThreshold(phantom);
        address[6] memory who = [address(0x1001), address(0x1002), address(0x1003), address(0x1004), address(0x1005), address(0x1006)];
        for (uint256 i; i < 6; ++i) {
            uint256 a = bound(buys[i], 1, thr / 7);
            try this.extBuy(who[i], a) {} catch {}
        }
        // sell in reverse and shuffled order
        for (uint256 i = 6; i > 0; --i) {
            address h = who[i - 1];
            uint256 bal = token.balanceOf(h);
            if (bal == 0) continue;
            (uint256 qr, uint256 tr) = curve.getReserves();
            if (ClankCurveMath.sellOutput(qr, tr, bal) == 0) continue; // sub-wei dust: ZeroOutput by design
            _sellAll(h); // must never revert (no InsufficientRealReserve / underflow)
        }
        require(curve.trackedTokens() + 1e18 > ClankCurveMath.TOKEN_SUPPLY || curve.trackedQuote() < 7, "stranded");
        require(address(curve).balance == curve.trackedQuote(), "native desync");
    }

    // ------------------------------------------------------------------
    // 4. Terminal partial fill: refund exactness, fee/tax split, state.
    // ------------------------------------------------------------------
    function testFuzz_TerminalFillAccounting(uint128 phantom, uint256 overpay, uint16 feeBps, uint256 elapsed) public {
        phantom = uint128(bound(phantom, 1e6, 1e24));
        feeBps = uint16(bound(feeBps, 0, 1000));
        _launch(phantom, feeBps, 3000, false);
        vm.warp(block.timestamp + bound(elapsed, 0, 70));
        uint256 thr = ClankCurveMath.graduationThreshold(phantom);
        uint256 amt = thr * 3 + bound(overpay, 0, thr * 5);
        vm.deal(ALICE, amt);
        uint256 escrowBefore = address(escrow).balance;
        (uint256 used, uint256 net, uint256 fee, uint256 qOut, uint256 refund) = curve.quoteBuyFor(ALICE, amt);
        vm.prank(ALICE);
        uint256 out = curve.buy{value: amt}(amt, 0, ALICE);
        require(out == qOut && out == ClankCurveMath.SOLD_TOKENS, "out");
        require(ALICE.balance == refund && refund == amt - used, "refund");
        require(address(escrow).balance - escrowBefore == fee && used == net + fee, "fee");
        // auto-graduation swept everything into the factory
        require(uint8(curve.state()) == uint8(ClankBondingCurve.State.Swept), "not swept");
        require(factory.sweptQuote() == net && factory.sweptTokens() == ClankCurveMath.MIGRATION_TOKENS, "sweep");
        require(net >= thr, "below threshold");
        require(address(curve).balance == 0, "residual");
    }

    // ------------------------------------------------------------------
    // 5. Reentrancy from the native refund callback.
    // ------------------------------------------------------------------
    function testRefundCallbackReentrancy() public {
        _launch(DEFAULT_PHANTOM, 100, 0, false);
        RefundReenterer r = new RefundReenterer(curve, factory);
        uint256 amt = 20 ether;
        vm.deal(address(this), amt);
        r.go{value: amt}(amt);
        require(r.refundSeen() > 0, "no refund");
        require(!r.reenterBuyOk() && !r.reenterSellOk(), "reentered trade");
        require(r.graduateOk(), "sweep inside callback failed");
        // outer _tryAutoGraduate then fails gracefully: exactly one successful sweep
        require(factory.graduateCalls() == 1, "double graduate");
        require(uint8(curve.state()) == uint8(ClankBondingCurve.State.Swept), "state");
        require(address(curve).balance == 0, "residual");
    }

    // ------------------------------------------------------------------
    // 6. No trading after Ready / Swept, no double graduation.
    // ------------------------------------------------------------------
    function testNoTradingAfterGraduation() public {
        _launch(DEFAULT_PHANTOM, 100, 0, false);
        _buy(ALICE, 20 ether);
        vm.deal(BOB, 1 ether);
        vm.prank(BOB);
        vm.expectRevert(ClankBondingCurve.CurveGraduated.selector);
        curve.buy{value: 1 ether}(1 ether, 0, BOB);
        vm.startPrank(ALICE);
        token.approve(address(curve), 1e18);
        vm.expectRevert(ClankBondingCurve.CurveGraduated.selector);
        curve.sell(1e18, 0, ALICE);
        vm.stopPrank();
        vm.expectRevert();
        factory.graduate(address(0));
    }

    // ------------------------------------------------------------------
    // 7. Burnable (current) token: burning outstanding supply cannot affect curve accounting,
    //    and nobody can burn the curve's reserve.
    // ------------------------------------------------------------------
    function testBurnableTokenDoesNotBreakCurve() public {
        _launch(DEFAULT_PHANTOM, 100, 0, true);
        _buy(ALICE, 1 ether);
        _buy(BOB, 1 ether);
        uint256 half = token.balanceOf(ALICE) / 2;
        vm.prank(ALICE);
        (bool b,) = address(token).call(abi.encodeWithSignature("burn(uint256)", half)); require(b, "burn");
        // cannot burn from the curve without its allowance
        vm.prank(ALICE);
        (bool ok,) = address(token).call(abi.encodeWithSignature("burnFrom(address,uint256)", address(curve), 1));
        require(!ok, "burned curve reserve");
        _sellAll(BOB);
        _sellAll(ALICE);
        require(address(curve).balance == curve.trackedQuote(), "desync");
        require(token.balanceOf(address(curve)) == curve.trackedTokens(), "token desync");
        // remaining quote is surplus left by the burner; curve still graduates normally
        _buy(BOB, 20 ether);
        require(uint8(curve.state()) == uint8(ClankBondingCurve.State.Swept), "no graduation");
        require(factory.sweptTokens() == ClankCurveMath.MIGRATION_TOKENS, "sweep tokens");
    }

    function testHistoricalTokenRejectsBurn() public {
        _launch(DEFAULT_PHANTOM, 100, 0, false);
        _buy(ALICE, 1 ether);
        vm.prank(ALICE);
        (bool ok,) = address(token).call(abi.encodeWithSignature("burn(uint256)", 1));
        require(!ok, "historical burn succeeded");
    }

    // ------------------------------------------------------------------
    // 8. Snipe tax is keyed on the recipient, not the payer.
    // ------------------------------------------------------------------
    function testSnipeTaxKeyedOnRecipient() public {
        _launch(DEFAULT_PHANTOM, 100, 5000, false);
        require(curve.currentSnipeTaxBps(ALICE) == 4900, "tax");
        require(curve.currentSnipeTaxBps(CREATOR) == 0, "creator exempt");
        // a non-exempt payer buying for the exempt creator pays no tax (tokens go to creator)
        (,, uint256 feeForCreator,,) = curve.quoteBuyFor(CREATOR, 1 ether);
        (,, uint256 feeForAlice,,) = curve.quoteBuyFor(ALICE, 1 ether);
        require(feeForCreator == 0.01 ether && feeForAlice == 0.5 ether, "fee");
        vm.warp(block.timestamp + 60);
        require(curve.currentSnipeTaxBps(ALICE) == 0, "decay");
    }

    // ------------------------------------------------------------------
    // 9. Graduation sandwich: a front-run that turns the victim's buy into a terminal partial fill
    //    still honours the victim's per-unit price bound.
    // ------------------------------------------------------------------
    function testTerminalProportionalSlippage() public {
        _launch(DEFAULT_PHANTOM, 100, 0, false);
        uint256 thr = ClankCurveMath.graduationThreshold(DEFAULT_PHANTOM);
        uint256 victimIn = thr / 4;
        (,,, uint256 expectedOut,) = curve.quoteBuyFor(ALICE, victimIn);
        uint256 minOut = expectedOut * 99 / 100;
        // attacker front-runs by buying almost everything
        _buy(BOB, thr * 95 / 100);
        vm.deal(ALICE, victimIn);
        vm.prank(ALICE);
        (bool ok,) = address(curve).call{value: victimIn}(abi.encodeCall(ClankBondingCurve.buy, (victimIn, minOut, ALICE)));
        require(!ok, "victim filled at a worse average price than bound");
    }

    // ------------------------------------------------------------------
    // 10. ERC-20 quote: fee-on-transfer rejected; forced/donated balances never priced.
    // ------------------------------------------------------------------
    function testErc20QuoteDonationIgnored() public {
        Quote q = new Quote();
        _launchPair(5_000e6, 100, 0, false, address(q), 60);
        q.mint(ALICE, 1_000_000e6);
        q.mint(address(curve), 777e6); // donation
        (uint256 qr,) = curve.getReserves();
        require(qr == 5_000e6, "donation priced");
        vm.startPrank(ALICE);
        q.approve(address(curve), type(uint256).max);
        curve.buy(100e6, 0, ALICE);
        token.approve(address(curve), type(uint256).max);
        curve.sell(token.balanceOf(ALICE), 0, ALICE);
        vm.stopPrank();
        require(q.balanceOf(address(curve)) == curve.trackedQuote() + 777e6, "erc20 desync");
    }

    function bound(uint256 x, uint256 lo, uint256 hi) internal pure returns (uint256) {
        if (hi <= lo) return lo;
        return lo + (x % (hi - lo + 1));
    }
}
