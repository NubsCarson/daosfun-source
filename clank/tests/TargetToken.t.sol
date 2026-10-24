// SPDX-License-Identifier: MIT
pragma solidity >=0.8.26 <0.9.0;

interface Vm {
    function readFileBinary(string calldata path) external view returns (bytes memory);
    function prank(address sender) external;
}
interface Token {
    function name() external view returns (string memory);
    function symbol() external view returns (string memory);
    function decimals() external view returns (uint8);
    function totalSupply() external view returns (uint256);
    function balanceOf(address) external view returns (uint256);
    function allowance(address,address) external view returns (uint256);
    function transfer(address,uint256) external returns (bool);
    function approve(address,uint256) external returns (bool);
    function transferFrom(address,address,uint256) external returns (bool);
    function burn(uint256) external;
    function burnFrom(address,uint256) external;
    function launchFactory() external view returns (address);
    function curve() external view returns (address);
    function deployer() external view returns (address);
}
/// @notice Executes the user's original initcode and runtime entirely in a local EVM.
contract TargetTokenTest {
    Vm constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));
    Token token;
    address curve;
    address constant ALICE = address(0xA11CE);
    address constant BOB = address(0xB0B);
    uint256 constant SUPPLY = 1_000_000_000 ether;
    function setUp() public {
        bytes memory code = vm.readFileBinary("../evidence/contracts/target-token.user-creation.bin");
        address deployed;
        assembly { deployed := create(0, add(code, 32), mload(code)) }
        require(deployed != address(0), "original initcode deployment failed");
        token = Token(deployed);
        curve = token.curve();
    }
    function testOriginalInitcodeProducesExactPastedRuntime() public view {
        bytes memory expected = vm.readFileBinary("../evidence/contracts/target-token.user-runtime.bin");
        require(keccak256(address(token).code) == keccak256(expected), "runtime differs");
    }
    function testInitialSupplyAndMetadata() public view {
        require(token.totalSupply() == SUPPLY && token.balanceOf(curve) == SUPPLY, "initial supply");
        require(token.decimals() == 18, "decimals");
        require(keccak256(bytes(token.name())) == keccak256("Artificial Girlfriend Intelligence"), "name");
        require(keccak256(bytes(token.symbol())) == keccak256("AGI"), "symbol");
        require(token.launchFactory() == address(bytes20(hex"b45beb38f21be1d29e6b9c6e9dc4222d1c12f1f1")), "factory");
    }
    function testTransferHasNoTokenLevelTax() public {
        vm.prank(curve);require(token.transfer(ALICE, 100 ether), "transfer");
        vm.prank(ALICE);require(token.transfer(BOB, 30 ether), "transfer");
        require(token.balanceOf(ALICE)==70 ether && token.balanceOf(BOB)==30 ether, "tax or restriction");
        require(token.totalSupply()==SUPPLY, "supply changed");
    }
    function testUnauthorizedTransferAndBurnFail() public {
        vm.prank(ALICE);(bool moved,) = address(token).call(abi.encodeCall(Token.transferFrom,(curve,ALICE,1 ether)));
        require(!moved,"unapproved transfer");
        vm.prank(ALICE);(bool burned,) = address(token).call(abi.encodeCall(Token.burnFrom,(curve,1 ether)));
        require(!burned,"unapproved burn");
        require(token.totalSupply()==SUPPLY && token.balanceOf(curve)==SUPPLY,"failed call changed accounting");
    }
    function testFixedSupplyRejectsEvenAuthorizedBurn() public {
        vm.prank(curve);require(token.approve(ALICE, 50 ether), "approval");
        vm.prank(ALICE);require(token.transferFrom(curve,BOB,20 ether), "transferFrom");
        require(token.allowance(curve,ALICE)==30 ether,"transfer allowance");
        vm.prank(ALICE);(bool ok,bytes memory reason)=address(token).call(abi.encodeCall(Token.burnFrom,(curve,30 ether)));
        require(!ok && keccak256(reason)==keccak256(abi.encodeWithSignature("FixedSupply()")),"authorized burn must fail");
        require(token.allowance(curve,ALICE)==30 ether,"failed burn consumed allowance");
        vm.prank(BOB);(ok,reason)=address(token).call(abi.encodeCall(Token.burn,(1 ether)));
        require(!ok && keccak256(reason)==keccak256(abi.encodeWithSignature("FixedSupply()")),"self burn must fail");
        require(token.totalSupply()==SUPPLY && token.balanceOf(BOB)==20 ether,"fixed supply");
    }
    function testNoMintOrUpgradeSelectorAvailableToDeployer() public {
        vm.prank(token.deployer());(bool minted,) = address(token).call(abi.encodeWithSignature("mint(address,uint256)",ALICE,1 ether));
        require(!minted,"mint surface");
        vm.prank(token.deployer());(bool upgraded,) = address(token).call(abi.encodeWithSignature("upgradeTo(address)",ALICE));
        require(!upgraded,"upgrade surface");
        require(token.totalSupply()==SUPPLY,"supply changed");
    }
    function testFuzzTransferConservesSupply(uint96 amount) public {
        uint256 value=uint256(amount)%SUPPLY;
        vm.prank(curve);require(token.transfer(ALICE,value),"transfer");
        require(token.balanceOf(curve)+token.balanceOf(ALICE)==SUPPLY,"conservation");
        require(token.totalSupply()==SUPPLY,"supply");
    }
}
