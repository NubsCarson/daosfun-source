// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

import {ClankBondingCurve} from "hist/ClankBondingCurve.sol";
import {ClankFeeEscrow} from "hist/ClankFeeEscrow.sol";
import {ClankGraduationGuard} from "hist/ClankGraduationGuard.sol";
import {ClankCurveMath} from "hist/libraries/ClankCurveMath.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {MockFactory, Quote} from "./CurveAudit.t.sol";

interface Vm2 { function prank(address) external; function startPrank(address) external; function stopPrank() external; }

contract ExtremeParamsTest {
    Vm2 constant vm = Vm2(address(uint160(uint256(keccak256("hevm cheat code")))));
    ClankFeeEscrow escrow = new ClankFeeEscrow();
    ClankGraduationGuard guard = new ClankGraduationGuard();
    event Log(string, uint256);

    function _launch(uint256 phantom, address pair, int24 ts) internal returns (ClankBondingCurve curve, MockFactory f) {
        f = new MockFactory();
        ClankBondingCurve.Config memory c;
        c.factory = address(f); c.feeEscrow = address(escrow); c.protocolFeeRecipient = address(0xFEE);
        c.creator = address(0xC0FFEE); c.pairToken = pair; c.feeBps = 0; c.snipeTaxStartBps = 0; c.snipeTaxSeconds = 60;
        c.phantomQuote = uint128(phantom); c.graduationThreshold = uint128(ClankCurveMath.graduationThreshold(phantom));
        c.graduationGuard = address(guard); c.tickSpacing = ts;
        f.deploy(c, false, address(0xC0FFEE));
        curve = f.curve();
    }

    /// Launch-time validation (as in factory._validateResolvedMigration) at the max phantom; then check whether the
    /// curve can actually be traded and graduated, using an ERC-20 quote with an effectively unlimited balance.
    function testMaxPhantomCurveLifecycle() public {
        uint256 P = ClankCurveMath.MAX_PHANTOM_QUOTE;
        Quote q = new Quote();
        (ClankBondingCurve curve, MockFactory f) = _launch(P, address(q), 1);
        bool quoteFirst = address(q) < f.token();
        emit Log("quoteIsCurrency0", quoteFirst ? 1 : 0);
        q.mint(address(this), type(uint128).max);
        q.approve(address(curve), type(uint256).max);
        uint256 thr = ClankCurveMath.graduationThreshold(P);
        uint256 ok; uint256 fail;
        for (uint256 i = 1; i <= 20; ++i) {
            try curve.buy(thr / 50, 0, address(this)) { ok++; } catch { fail++; }
        }
        emit Log("buys ok", ok); emit Log("buys failed", fail);
        require(ok == 0, "expected every incremental buy to fail at MAX_PHANTOM_QUOTE");
        IERC20 t = IERC20(f.token());
        t.approve(address(curve), type(uint256).max);
        uint256 sOk; uint256 sFail;
        for (uint256 i; i < 20; ++i) {
            try curve.sell(1e24, 0, address(this)) { sOk++; } catch { sFail++; }
        }
        emit Log("sells ok", sOk); emit Log("sells failed", sFail);
        try curve.buy(thr * 3, 0, address(this)) { emit Log("terminal ok", 1); } catch { emit Log("terminal failed", 1); }
        emit Log("state", uint8(curve.state()));
        require(uint8(curve.state()) == 0, "unexpected graduation");
    }
}

contract ExtremeScan {
    ClankFeeEscrow escrow = new ClankFeeEscrow();
    ClankGraduationGuard guard = new ClankGraduationGuard();
    event Log(string, uint256);

    function _launch(uint256 phantom, address pair) internal returns (ClankBondingCurve curve, MockFactory f) {
        f = new MockFactory();
        ClankBondingCurve.Config memory c;
        c.factory = address(f); c.feeEscrow = address(escrow); c.protocolFeeRecipient = address(0xFEE);
        c.creator = address(0xC0FFEE); c.pairToken = pair; c.feeBps = 0; c.snipeTaxStartBps = 0; c.snipeTaxSeconds = 60;
        c.phantomQuote = uint128(phantom); c.graduationThreshold = uint128(ClankCurveMath.graduationThreshold(phantom));
        c.graduationGuard = address(guard); c.tickSpacing = 1;
        f.deploy(c, false, address(0xC0FFEE));
        curve = f.curve();
    }

    function testScanHeadroom() public {
        uint256 M = ClankCurveMath.MAX_PHANTOM_QUOTE;
        for (uint256 e = 4; e <= 40; e += 2) {
            uint256 P = M - M / (10 ** (e / 2)) ;
            Quote q = new Quote();
            (ClankBondingCurve curve,) = _launch(P, address(q));
            q.mint(address(this), type(uint128).max);
            q.approve(address(curve), type(uint256).max);
            uint256 thr = ClankCurveMath.graduationThreshold(P);
            uint256 ok;
            for (uint256 i; i < 5; ++i) { try curve.buy(thr / 50 + i, 0, address(this)) { ok++; } catch {} }
            emit Log("negexp", e / 2);
            emit Log("  buys ok of 5", ok);
            require(ok == 5, "headroom below 1e-2..1e-20 relative still bricks");
        }
    }
}
