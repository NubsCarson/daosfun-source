// SPDX-License-Identifier: MIT
pragma solidity >=0.8.26 <0.9.0;
interface SnapshotVm {
function etch(address,bytes calldata) external; function store(address,bytes32,bytes32) external;
function deal(address,uint256) external; function chainId(uint256) external; function roll(uint256) external; function warp(uint256) external;
function readFileBinary(string calldata) external view returns(bytes memory);
function record() external; function accesses(address) external returns(bytes32[] memory,bytes32[] memory);
}
abstract contract CriticalSnapshot {
SnapshotVm constant snapshotVm=SnapshotVm(address(uint160(uint256(keccak256("hevm cheat code")))));
function _loadSnapshot() internal {
snapshotVm.chainId(4663); snapshotVm.roll(96709714); snapshotVm.warp(1792839173);
snapshotVm.etch(address(bytes20(hex"58daec3116aae6d93017baaea7749052e8a04fa7")),snapshotVm.readFileBinary("../evidence/critical-snapshot/0x58daec3116aae6d93017baaea7749052e8a04fa7.bin"));
snapshotVm.deal(address(bytes20(hex"58daec3116aae6d93017baaea7749052e8a04fa7")),0);
snapshotVm.store(address(bytes20(hex"58daec3116aae6d93017baaea7749052e8a04fa7")),bytes32(uint256(79757581023863940445078001373723520495415049657540508656498995735891356587262)),bytes32(uint256(1300848334149424734853861127132037285308154932967)));
snapshotVm.store(address(bytes20(hex"58daec3116aae6d93017baaea7749052e8a04fa7")),bytes32(uint256(90861521877193764911514498395109893171726248987901813085171292846227009626566)),bytes32(uint256(0)));
snapshotVm.store(address(bytes20(hex"58daec3116aae6d93017baaea7749052e8a04fa7")),bytes32(uint256(105633823371605622855985012529308896326573136514007345698682702234875466001713)),bytes32(uint256(0)));
snapshotVm.etch(address(bytes20(hex"77cb92c232137739452446c5712fb0055a344c3d")),snapshotVm.readFileBinary("../evidence/critical-snapshot/0x77cb92c232137739452446c5712fb0055a344c3d.bin"));
snapshotVm.deal(address(bytes20(hex"77cb92c232137739452446c5712fb0055a344c3d")),754208697317774441);
snapshotVm.etch(address(bytes20(hex"8366a39cc670b4001a1121b8f6a443a643e40951")),snapshotVm.readFileBinary("../evidence/critical-snapshot/0x8366a39cc670b4001a1121b8f6a443a643e40951.bin"));
snapshotVm.deal(address(bytes20(hex"8366a39cc670b4001a1121b8f6a443a643e40951")),23877759698163765253414);
snapshotVm.etch(address(bytes20(hex"a042794f670cfe57209438cbe63dbdf4424b6dff")),snapshotVm.readFileBinary("../evidence/critical-snapshot/0xa042794f670cfe57209438cbe63dbdf4424b6dff.bin"));
snapshotVm.deal(address(bytes20(hex"a042794f670cfe57209438cbe63dbdf4424b6dff")),0);
snapshotVm.store(address(bytes20(hex"a042794f670cfe57209438cbe63dbdf4424b6dff")),bytes32(uint256(0)),bytes32(uint256(669711064822384598169668981098294221571059961142443791943404)));
snapshotVm.etch(address(bytes20(hex"b45beb38f21be1d29e6b9c6e9dc4222d1c12f1f1")),snapshotVm.readFileBinary("../evidence/critical-snapshot/0xb45beb38f21be1d29e6b9c6e9dc4222d1c12f1f1.bin"));
snapshotVm.deal(address(bytes20(hex"b45beb38f21be1d29e6b9c6e9dc4222d1c12f1f1")),0);
snapshotVm.store(address(bytes20(hex"b45beb38f21be1d29e6b9c6e9dc4222d1c12f1f1")),bytes32(uint256(105944447373304919922975499485986128487416177601674000887014320976943128906276)),bytes32(uint256(914920940120800024511748161607413739550440910335)));
snapshotVm.store(address(bytes20(hex"b45beb38f21be1d29e6b9c6e9dc4222d1c12f1f1")),bytes32(uint256(105944447373304919922975499485986128487416177601674000887014320976943128906275)),bytes32(uint256(1428358571846231451785425977991918772900691248876)));
snapshotVm.store(address(bytes20(hex"b45beb38f21be1d29e6b9c6e9dc4222d1c12f1f1")),bytes32(uint256(0)),bytes32(uint256(683909737478426311113252565698285889610258336829)));
snapshotVm.store(address(bytes20(hex"b45beb38f21be1d29e6b9c6e9dc4222d1c12f1f1")),bytes32(uint256(70319816728846589445362000750570655803700195216363692647688146666176345628416)),bytes32(uint256(1)));
snapshotVm.etch(address(bytes20(hex"bab7dbd758c8de7a28e315d3a88d68bb671acd3f")),snapshotVm.readFileBinary("../evidence/critical-snapshot/0xbab7dbd758c8de7a28e315d3a88d68bb671acd3f.bin"));
snapshotVm.deal(address(bytes20(hex"bab7dbd758c8de7a28e315d3a88d68bb671acd3f")),0);
snapshotVm.store(address(bytes20(hex"bab7dbd758c8de7a28e315d3a88d68bb671acd3f")),bytes32(uint256(70319816728846589445362000750570655803700195216363692647688146666176345628416)),bytes32(uint256(1)));
snapshotVm.etch(address(bytes20(hex"d405e0dff2d0cc7eaa48b3aec2e3f2456c072000")),snapshotVm.readFileBinary("../evidence/critical-snapshot/0xd405e0dff2d0cc7eaa48b3aec2e3f2456c072000.bin"));
snapshotVm.deal(address(bytes20(hex"d405e0dff2d0cc7eaa48b3aec2e3f2456c072000")),0);
snapshotVm.store(address(bytes20(hex"d405e0dff2d0cc7eaa48b3aec2e3f2456c072000")),bytes32(uint256(2)),bytes32(uint256(1029668197326181859522595315486009236101186908657)));
snapshotVm.etch(address(bytes20(hex"e3dc0e862c4eff876a1c40b10205844111da6ee7")),snapshotVm.readFileBinary("../evidence/critical-snapshot/0xe3dc0e862c4eff876a1c40b10205844111da6ee7.bin"));
snapshotVm.deal(address(bytes20(hex"e3dc0e862c4eff876a1c40b10205844111da6ee7")),0);
snapshotVm.etch(address(bytes20(hex"fa31d04462746aaa24bc7e5626403e09e4b106ec")),snapshotVm.readFileBinary("../evidence/critical-snapshot/0xfa31d04462746aaa24bc7e5626403e09e4b106ec.bin"));
snapshotVm.deal(address(bytes20(hex"fa31d04462746aaa24bc7e5626403e09e4b106ec")),0);
}
function _assertRecordedReads() internal {
bytes32[] memory slots;
(slots,)=snapshotVm.accesses(address(bytes20(hex"58daec3116aae6d93017baaea7749052e8a04fa7")));
for(uint256 i=0;i<slots.length;++i){
require(slots[i]==bytes32(uint256(79757581023863940445078001373723520495415049657540508656498995735891356587262)) || slots[i]==bytes32(uint256(90861521877193764911514498395109893171726248987901813085171292846227009626566)) || slots[i]==bytes32(uint256(105633823371605622855985012529308896326573136514007345698682702234875466001713)),"read of uncaptured storage");
}
(slots,)=snapshotVm.accesses(address(bytes20(hex"77cb92c232137739452446c5712fb0055a344c3d")));
for(uint256 i=0;i<slots.length;++i){
require(false,"read of uncaptured storage");
}
(slots,)=snapshotVm.accesses(address(bytes20(hex"8366a39cc670b4001a1121b8f6a443a643e40951")));
for(uint256 i=0;i<slots.length;++i){
require(false,"read of uncaptured storage");
}
(slots,)=snapshotVm.accesses(address(bytes20(hex"a042794f670cfe57209438cbe63dbdf4424b6dff")));
for(uint256 i=0;i<slots.length;++i){
require(slots[i]==bytes32(uint256(0)),"read of uncaptured storage");
}
(slots,)=snapshotVm.accesses(address(bytes20(hex"b45beb38f21be1d29e6b9c6e9dc4222d1c12f1f1")));
for(uint256 i=0;i<slots.length;++i){
require(slots[i]==bytes32(uint256(105944447373304919922975499485986128487416177601674000887014320976943128906276)) || slots[i]==bytes32(uint256(105944447373304919922975499485986128487416177601674000887014320976943128906275)) || slots[i]==bytes32(uint256(0)) || slots[i]==bytes32(uint256(70319816728846589445362000750570655803700195216363692647688146666176345628416)),"read of uncaptured storage");
}
(slots,)=snapshotVm.accesses(address(bytes20(hex"bab7dbd758c8de7a28e315d3a88d68bb671acd3f")));
for(uint256 i=0;i<slots.length;++i){
require(slots[i]==bytes32(uint256(70319816728846589445362000750570655803700195216363692647688146666176345628416)),"read of uncaptured storage");
}
(slots,)=snapshotVm.accesses(address(bytes20(hex"d405e0dff2d0cc7eaa48b3aec2e3f2456c072000")));
for(uint256 i=0;i<slots.length;++i){
require(slots[i]==bytes32(uint256(2)),"read of uncaptured storage");
}
(slots,)=snapshotVm.accesses(address(bytes20(hex"e3dc0e862c4eff876a1c40b10205844111da6ee7")));
for(uint256 i=0;i<slots.length;++i){
require(false,"read of uncaptured storage");
}
(slots,)=snapshotVm.accesses(address(bytes20(hex"fa31d04462746aaa24bc7e5626403e09e4b106ec")));
for(uint256 i=0;i<slots.length;++i){
require(false,"read of uncaptured storage");
}
}
}
