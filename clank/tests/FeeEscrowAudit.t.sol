// SPDX-License-Identifier: MIT
pragma solidity >=0.8.26 <0.9.0;
interface AuditVm {
    function readFileBinary(string calldata) external view returns(bytes memory);
    function deal(address,uint256) external;
    function prank(address) external;
}
interface Escrow {
    function credit(address) external payable;
    function claimTo(address payable) external returns(uint256);
    function balanceOf(address) external view returns(uint256);
    function totalCredits() external view returns(uint256);
}
contract RejectPayment { receive() external payable { revert("reject"); } }
contract NestedClaim {
    Escrow public escrow;
    bool public nestedSucceeded;
    constructor(Escrow e){escrow=e;}
    function collect() external {escrow.claimTo(payable(address(this)));}
    receive() external payable {
        (nestedSucceeded,)=address(escrow).call(abi.encodeCall(Escrow.claimTo,(payable(address(this)))));
    }
}
contract FeeEscrowAuditTest {
    AuditVm constant vm=AuditVm(address(uint160(uint256(keccak256("hevm cheat code")))));
    Escrow escrow;
    address constant ALICE=address(0xA11CE);
    address constant BOB=address(0xB0B);
    function setUp() public {
        bytes memory code=vm.readFileBinary("../evidence/contracts/target-fee-escrow.creation.bin");
        address deployed;assembly {deployed:=create(0,add(code,32),mload(code))}
        require(deployed!=address(0),"deployment failed");escrow=Escrow(deployed);
        require(keccak256(deployed.code)==keccak256(vm.readFileBinary("../evidence/contracts/target-fee-escrow.runtime.bin")),"not captured runtime");
        vm.deal(address(this),10 ether);
    }
    function testCallerCannotWithdrawAnotherBeneficiaryCredit() public {
        escrow.credit{value:2 ether}(ALICE);
        vm.prank(BOB);(bool ok,)=address(escrow).call(abi.encodeCall(Escrow.claimTo,(payable(BOB))));
        require(!ok && escrow.balanceOf(ALICE)==2 ether && escrow.totalCredits()==2 ether,"cross beneficiary claim");
    }
    function testRejectingRecipientRestoresCredit() public {
        escrow.credit{value:2 ether}(ALICE);RejectPayment recipient=new RejectPayment();
        vm.prank(ALICE);(bool ok,)=address(escrow).call(abi.encodeCall(Escrow.claimTo,(payable(address(recipient)))));
        require(!ok && escrow.balanceOf(ALICE)==2 ether && escrow.totalCredits()==2 ether,"failed transfer lost credit");
        vm.prank(ALICE);escrow.claimTo(payable(BOB));
        require(BOB.balance==2 ether && escrow.totalCredits()==0,"retry failed");
    }
    function testReentryCannotClaimTwice() public {
        NestedClaim recipient=new NestedClaim(escrow);escrow.credit{value:2 ether}(address(recipient));
        recipient.collect();
        require(!recipient.nestedSucceeded() && address(recipient).balance==2 ether,"double claim");
        require(escrow.totalCredits()==0 && address(escrow).balance==0,"accounting");
    }
    function testForcedSurplusDoesNotBecomeCredit() public {
        escrow.credit{value:2 ether}(ALICE);vm.deal(address(escrow),5 ether);
        vm.prank(ALICE);escrow.claimTo(payable(ALICE));
        require(ALICE.balance==2 ether && address(escrow).balance==3 ether && escrow.totalCredits()==0,"surplus claim");
    }
}
