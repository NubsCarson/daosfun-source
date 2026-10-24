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
    function testCapturedCreate2AddressMatchesOriginalPayload() public view {
        bytes memory original = vm.readFileBinary("../evidence/contracts/target-token.user-creation.bin");
        bytes32 launchId = 0x5389eef4763e7643fbd938f7cb06fb367b302522a45a231811a35086ec98491a;
        address launchDeployer = address(bytes20(hex"5748de42dd639919550523d7ffd52589f02727bf"));
        bytes32 salt = keccak256(abi.encodePacked(launchId, "CLANK_TOKEN"));
        address predicted = address(uint160(uint256(keccak256(abi.encodePacked(bytes1(0xff), launchDeployer, salt, keccak256(original))))));
        require(predicted == address(bytes20(hex"fa31d04462746aaa24bc7e5626403e09e4b106ec")), "CREATE2 address differs");
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
    function testFuzzDelegatedSpendCannotExceedAllowance(uint96 rawAllowance, uint96 rawSpend) public {
        uint256 allowed=uint256(rawAllowance)%SUPPLY;
        uint256 spent=uint256(rawSpend)%SUPPLY;
        vm.prank(curve);token.approve(ALICE,allowed);
        vm.prank(ALICE);(bool ok,)=address(token).call(abi.encodeCall(Token.transferFrom,(curve,BOB,spent)));
        require(ok==(spent<=allowed),"allowance boundary");
        require(token.allowance(curve,ALICE)==(ok?allowed-spent:allowed),"allowance rollback");
        require(token.balanceOf(BOB)==(ok?spent:0),"recipient accounting");
        require(token.totalSupply()==SUPPLY,"supply changed");
    }
    function testFuzzSelfTransferPreservesBalance(uint96 rawAmount) public {
        uint256 amount=uint256(rawAmount)%SUPPLY;
        vm.prank(curve);token.transfer(curve,amount);
        require(token.balanceOf(curve)==SUPPLY && token.totalSupply()==SUPPLY,"self transfer changes supply");
    }
    function testMaxAllowanceStillRequiresBalance() public {
        vm.prank(curve);token.approve(ALICE,type(uint256).max);
        vm.prank(ALICE);(bool ok,)=address(token).call(abi.encodeCall(Token.transferFrom,(curve,BOB,SUPPLY+1)));
        require(!ok,"overspend accepted");
        require(token.allowance(curve,ALICE)==type(uint256).max,"failed spend changed allowance");
        vm.prank(ALICE);token.transferFrom(curve,BOB,1 ether);
        require(token.allowance(curve,ALICE)==type(uint256).max,"infinite allowance decremented");
    }
    function testZeroReceiverRestoresAllowance() public {
        vm.prank(curve);token.approve(ALICE,1 ether);
        vm.prank(ALICE);(bool ok,)=address(token).call(abi.encodeCall(Token.transferFrom,(curve,address(0),1 ether)));
        require(!ok && token.allowance(curve,ALICE)==1 ether,"invalid receiver rollback");
        require(token.balanceOf(curve)==SUPPLY && token.totalSupply()==SUPPLY,"invalid receiver accounting");
    }
    function testFuzzTransferSequenceConservesModel(uint256 seed) public {
        address[3] memory actors=[curve,ALICE,BOB];
        uint256[3] memory balances=[SUPPLY,uint256(0),uint256(0)];
        for(uint256 i=0;i<32;++i){
            seed=uint256(keccak256(abi.encode(seed,i)));
            uint256 from=seed%3; uint256 to=(seed>>8)%3;
            uint256 amount=(seed>>16)%(balances[from]+1);
            vm.prank(actors[from]);token.transfer(actors[to],amount);
            balances[from]-=amount;balances[to]+=amount;
            for(uint256 j=0;j<3;++j)require(token.balanceOf(actors[j])==balances[j],"model mismatch");
            require(token.totalSupply()==SUPPLY,"sequence changed supply");
        }
    }
}
