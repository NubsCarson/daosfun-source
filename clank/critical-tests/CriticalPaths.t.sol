// SPDX-License-Identifier: MIT
pragma solidity >=0.8.26 <0.9.0;
import {CriticalSnapshot} from "./CriticalSnapshot.sol";
interface CriticalVm {
    function prank(address) external;
    function warp(uint256) external;
    function readFileBinary(string calldata) external view returns(bytes memory);
}
interface StateViews {
    function state() external view returns(uint8);
    function owner() external view returns(address);
    function ownerOf(uint256) external view returns(address);
}
/// @notice All calls and impersonation execute only in the local captured-state replay. No broadcast.
contract CriticalPathsTest is CriticalSnapshot {
    CriticalVm constant vm=CriticalVm(address(uint160(uint256(keccak256("hevm cheat code")))));
    address constant TOKEN=address(bytes20(hex"fa31d04462746aaa24bc7e5626403e09e4b106ec"));
    address constant FACTORY=address(bytes20(hex"b45beb38f21be1d29e6b9c6e9dc4222d1c12f1f1"));
    address constant CURVE=address(bytes20(hex"a042794f670cfe57209438cbe63dbdf4424b6dff"));
    address constant LOCKER=address(bytes20(hex"e3dc0e862c4eff876a1c40b10205844111da6ee7"));
    address constant EXECUTOR=address(bytes20(hex"bab7dbd758c8de7a28e315d3a88d68bb671acd3f"));
    address constant HOOK=address(bytes20(hex"d405e0dff2d0cc7eaa48b3aec2e3f2456c072000"));
    address constant POOL_MANAGER=address(bytes20(hex"8366a39cc670b4001a1121b8f6a443a643e40951"));
    address constant POSITION_MANAGER=address(bytes20(hex"58daec3116aae6d93017baaea7749052e8a04fa7"));
    address constant OUTSIDER=address(0xBADC0DE);
    function setUp() public {
        _loadSnapshot();
        require(block.chainid==4663 && block.number==96709714,"wrong snapshot");
        require(keccak256(TOKEN.code)==keccak256(vm.readFileBinary("../evidence/contracts/target-token.runtime.bin")),"token code differs");
        require(keccak256(FACTORY.code)==keccak256(vm.readFileBinary("../evidence/contracts/target-factory.runtime.bin")),"factory code differs");
        require(keccak256(CURVE.code)==keccak256(vm.readFileBinary("../evidence/contracts/target-curve.runtime.bin")),"curve code differs");
        require(keccak256(LOCKER.code)==keccak256(vm.readFileBinary("../evidence/contracts/target-locker.runtime.bin")),"locker code differs");
        require(keccak256(EXECUTOR.code)==keccak256(vm.readFileBinary("../evidence/contracts/target-graduation-executor.runtime.bin")),"executor code differs");
        require(keccak256(HOOK.code)==keccak256(vm.readFileBinary("../evidence/contracts/target-initialization-hook.runtime.bin")),"hook code differs");
        require(StateViews(CURVE).state()==3,"not PoolCreated");
        _positionStillLocked();
    }
    function _positionStillLocked() private view {
        require(StateViews(POSITION_MANAGER).ownerOf(3034864)==LOCKER,"position ownership changed");
    }
    function _reject(address caller,address target,bytes memory data,bytes memory expected) private {
        snapshotVm.record();
        vm.prank(caller);(bool ok,bytes memory reason)=target.call(data);
        require(!ok && keccak256(reason)==keccak256(expected),"expected exact rejection");
        _positionStillLocked();
        _assertRecordedReads();
    }
    function testOutsiderCannotRescueOrRedirectFees() public {
        bytes memory err=abi.encodeWithSignature("OwnableUnauthorizedAccount(address)",OUTSIDER);
        _reject(OUTSIDER,FACTORY,abi.encodeWithSignature("rescueSweptGraduation(address,address)",TOKEN,OUTSIDER),err);
        _reject(OUTSIDER,FACTORY,abi.encodeWithSignature("setFeeDestination(address)",OUTSIDER),err);
    }
    function testOwnerCannotRescueGraduatedAGIEvenAfterDelay() public {
        address owner=StateViews(FACTORY).owner();vm.warp(block.timestamp+365 days);
        _reject(owner,FACTORY,abi.encodeWithSignature("rescueSweptGraduation(address,address)",TOKEN,owner),abi.encodeWithSignature("InvalidState(uint8,uint8)",uint8(2),uint8(3)));
        _reject(owner,FACTORY,abi.encodeWithSignature("forceSweptGraduation(address)",TOKEN),abi.encodeWithSignature("InvalidState(uint8,uint8)",uint8(1),uint8(3)));
    }
    function testSelfCallHelpersCannotBypassAccessControl() public {
        _reject(OUTSIDER,FACTORY,abi.encodeWithSignature("attemptRescueMigration(address)",TOKEN),abi.encodeWithSignature("OnlySelf()"));
        _reject(OUTSIDER,FACTORY,abi.encodeWithSignature("attemptForceGraduation(address)",TOKEN),abi.encodeWithSignature("OnlySelf()"));
    }
    function testCurveCannotBeDrainedOrReinitializedByOutsider() public {
        _reject(OUTSIDER,CURVE,abi.encodeWithSignature("graduate(address)",OUTSIDER),abi.encodeWithSignature("NotFactory()"));
        _reject(OUTSIDER,CURVE,abi.encodeWithSignature("initialize(address)",OUTSIDER),abi.encodeWithSignature("NotFactory()"));
        _reject(OUTSIDER,CURVE,abi.encodeWithSignature("markRescued()"),abi.encodeWithSignature("NotFactory()"));
    }
    function testGraduatedCurveCannotReopenEvenFromFactory() public {
        _reject(FACTORY,CURVE,abi.encodeWithSignature("initialize(address)",TOKEN),abi.encodeWithSignature("AlreadyInitialized()"));
        _reject(FACTORY,CURVE,abi.encodeWithSignature("graduate(address)",OUTSIDER),abi.encodeWithSignature("InvalidState(uint8,uint8)",uint8(1),uint8(3)));
    }
    function testExecutorRejectsOutsiderBeforeMovingReserves() public {
        _reject(OUTSIDER,EXECUTOR,abi.encodeWithSignature("mintFullRangePosition(address,address,uint24,int24,uint128,uint128)",TOKEN,address(0),uint24(3000),int24(200),uint128(1),uint128(1)),abi.encodeWithSignature("NotFactory()"));
    }
    function testLockerCannotBeReassignedOrApproveWithdrawal() public {
        _reject(OUTSIDER,LOCKER,abi.encodeWithSignature("lockPosition(address,uint256,address)",TOKEN,uint256(3034864),address(0)),abi.encodeWithSignature("NotFactory()"));
        _reject(OUTSIDER,LOCKER,abi.encodeWithSignature("approve(address,uint256)",OUTSIDER,uint256(3034864)),bytes(""));
        _reject(OUTSIDER,POSITION_MANAGER,abi.encodeWithSignature("transferFrom(address,address,uint256)",LOCKER,OUTSIDER,uint256(3034864)),abi.encodeWithSignature("Error(string)","NOT_AUTHORIZED"));
    }
    function testRepeatGraduationCannotCreateSecondClaimOnReserves() public {
        _reject(OUTSIDER,FACTORY,abi.encodeWithSignature("graduate(address)",TOKEN),abi.encodeWithSignature("InvalidState(uint8,uint8)",uint8(1),uint8(3)));
        _reject(OUTSIDER,FACTORY,abi.encodeWithSignature("createGraduatedPool(address)",TOKEN),abi.encodeWithSignature("InvalidState(uint8,uint8)",uint8(2),uint8(3)));
    }
    struct PoolKey {address currency0;address currency1;uint24 fee;int24 tickSpacing;address hooks;}
    function testPoolInitializationCannotSpoofFactory() public {
        PoolKey memory key=PoolKey(address(0),TOKEN,3000,200,HOOK);
        bytes memory data=abi.encodeWithSignature("beforeInitialize(address,(address,address,uint24,int24,address),uint160)",OUTSIDER,key,uint160(1<<96));
        _reject(OUTSIDER,HOOK,data,abi.encodeWithSignature("NotPoolManager()"));
        _reject(POOL_MANAGER,HOOK,data,abi.encodeWithSignature("NotFactory()"));
    }
    function testProtocolRolesCannotUseOwnerRescue() public {
        address[8] memory callers=[address(0),OUTSIDER,TOKEN,CURVE,LOCKER,EXECUTOR,HOOK,FACTORY];
        for(uint256 i=0;i<callers.length;++i){
            address caller=callers[i];
            require(caller!=StateViews(FACTORY).owner(),"fixture unexpectedly owner");
            _reject(caller,FACTORY,abi.encodeWithSignature("rescueSweptGraduation(address,address)",TOKEN,OUTSIDER),abi.encodeWithSignature("OwnableUnauthorizedAccount(address)",caller));
        }
    }
    function testProtocolRolesCannotSweepCurve() public {
        address[7] memory callers=[address(0),OUTSIDER,TOKEN,CURVE,LOCKER,EXECUTOR,HOOK];
        for(uint256 i=0;i<callers.length;++i){
            _reject(callers[i],CURVE,abi.encodeWithSignature("graduate(address)",OUTSIDER),abi.encodeWithSignature("NotFactory()"));
        }
    }
}
