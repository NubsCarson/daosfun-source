"""Capture public verified sources and deployed code. Read-only JSON-RPC calls."""
import concurrent.futures, hashlib, json, pathlib, subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/contracts'
RPC='https://rpc.mainnet.chain.robinhood.com'
BLOCK='0x5c3696a'
FACTORY='0x798daAa0707C1e538bB5Acf0867Ac0e1A84cccF2'
def rpc(method,params):
    raw=subprocess.check_output(['curl','--fail','--silent','--show-error','--max-time','45',RPC,'-H','content-type: application/json','--data',json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params})])
    d=json.loads(raw)
    if 'error' in d: raise RuntimeError(d['error'])
    return d['result']
def call(addr,sig):
    data=subprocess.check_output(['cast','sig',sig],text=True).strip()
    return rpc('eth_call',[{'to':addr,'data':data},BLOCK])
if __name__=='__main__':
    addresses={'factory':FACTORY,'eth-router':'0xb4a4315abbbf9fcC71a6e48D604310D7A36A6378'}
    getters={'fee-escrow':'feeEscrow()','locker':'locker()','graduation-executor':'graduationExecutor()','graduation-guard':'graduationGuard()','initialization-hook':'initializationHook()','launch-deployer':'launchDeployer()','launch-forwarder':'launchForwarder()'}
    for name,sig in getters.items(): addresses[name]='0x'+call(FACTORY,sig)[-40:]
    block=rpc('eth_getBlockByNumber',[BLOCK,False]); (OUT/'pinned-block.json').write_text(json.dumps(block,indent=2)+'\n')
    def capture(item):
        name,addr=item
        code=bytes.fromhex(rpc('eth_getCode',[addr,BLOCK])[2:]); (OUT/f'{name}.runtime.bin').write_bytes(code)
        url=f'https://sourcify.dev/server/v2/contract/4663/{addr}?fields=all'
        path=OUT/f'{name}-sourcify.json'
        if not path.exists():
            result=subprocess.run(['curl','--fail','--silent','--show-error','--max-time','90',url,'-o',str(path)])
            if result.returncode:
                return {'name':name,'address':addr,'block':BLOCK,'blockHash':block['hash'],'runtimeBytes':len(code),'runtimeSha256':hashlib.sha256(code).hexdigest(),'sourcifyUrl':url,'sourceStatus':'unavailable','curlExit':result.returncode}
        d=json.loads(path.read_text()); recovered=[]
        for f,v in d.get('sources',{}).items():
            rel=pathlib.PurePosixPath(f)
            if rel.is_absolute() or '..' in rel.parts: raise ValueError(f)
            p=ROOT/'verified'/name/'sources'/f; p.parent.mkdir(parents=True,exist_ok=True);p.write_text(v['content']); recovered.append(f)
        if 'stdJsonInput' in d:
            p=ROOT/'verified'/name/'standard-input.json';p.write_text(json.dumps(d['stdJsonInput'],indent=2)+'\n')
        row={'name':name,'address':addr,'block':BLOCK,'blockHash':block['hash'],'runtimeBytes':len(code),'runtimeSha256':hashlib.sha256(code).hexdigest(),'sourcifyUrl':url,'sourcifyRuntimeMatch':d.get('runtimeMatch'),'compiler':d.get('compilation'),'sourceCount':len(recovered),'sourcifyMatchesPinnedCode':d.get('runtimeBytecode',{}).get('onchainBytecode','').lower()=='0x'+code.hex()}
        print(name,addr,len(code),row['sourcifyRuntimeMatch'],len(recovered),flush=True)
        return row
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: rows=list(pool.map(capture,addresses.items()))
    (OUT/'recovered-inventory.json').write_text(json.dumps({'chainId':4663,'rpc':RPC,'block':BLOCK,'blockHash':block['hash'],'contracts':rows},indent=2)+'\n')
