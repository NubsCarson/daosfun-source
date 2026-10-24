"""Archive the selected token's public dependency graph at the pinned block."""
import concurrent.futures,json,pathlib,subprocess,hashlib
from recover_sources import rpc,BLOCK
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'evidence/contracts'
state=json.loads((OUT/'target-state.json').read_text())
factory=state['factory'];token=state['token'];curve=state['curve']
def query(addr,sig,*args):
    data=subprocess.check_output(['cast','calldata',sig,*args],text=True).strip()
    return rpc('eth_call',[{'to':addr,'data':data},BLOCK])
def address(sig):
    return '0x'+next(r['result'][-40:] for r in state['calls'] if r['address']==factory and r['function']==sig)
locker=address('locker()');positionManager=address('positionManager()')
position=int(query(locker,'lockedPositions(address)',token),16)
context={'chainId':4663,'block':BLOCK,'token':token,'factory':factory,'curve':curve,'locker':locker,'positionManager':positionManager,'positionId':position,'isLocked':int(query(locker,'isLocked(address)',token),16)==1,'positionOwner':'0x'+query(positionManager,'ownerOf(uint256)',str(position))[-40:],'launchRecord':query(factory,'getLaunchedToken(address)',token)}
owner=address('owner()');context['factoryOwnerCode']=rpc('eth_getCode',[owner,BLOCK]);context['factoryOwner']=owner
(OUT/'target-context.json').write_text(json.dumps(context,indent=2)+'\n');print(context,flush=True)
names={'target-fee-escrow':'feeEscrow()','target-locker':'locker()','target-graduation-executor':'graduationExecutor()','target-graduation-guard':'graduationGuard()','target-initialization-hook':'initializationHook()','target-launch-deployer':'launchDeployer()','target-launch-forwarder':'launchForwarder()'}
def fetch(item):
 name,sig=item;addr=address(sig);code=bytes.fromhex(rpc('eth_getCode',[addr,BLOCK])[2:]);(OUT/f'{name}.runtime.bin').write_bytes(code)
 path=OUT/f'{name}-sourcify.json';url=f'https://sourcify.dev/server/v2/contract/4663/{addr}?fields=all'
 if not path.exists():
  r=subprocess.run(['curl','--fail','--silent','--show-error','--max-time','60',url,'-o',str(path)])
  if r.returncode: return {'name':name,'address':addr,'runtimeSha256':hashlib.sha256(code).hexdigest(),'sourceStatus':'not retrieved'}
 d=json.loads(path.read_text())
 for f,v in d['sources'].items():
  rel=pathlib.PurePosixPath(f)
  if rel.is_absolute() or '..' in rel.parts: raise ValueError(f)
  p=ROOT/'verified'/name/'sources'/f;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(v['content'])
 row={'name':name,'address':addr,'runtimeBytes':len(code),'runtimeSha256':hashlib.sha256(code).hexdigest(),'sourceStatus':'retrieved','sourcifyUrl':url,'sourcifyMatchesPinnedCode':d['runtimeBytecode']['onchainBytecode'].lower()=='0x'+code.hex()}
 print(row,flush=True);return row
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool: rows=list(pool.map(fetch,names.items()))
(OUT/'target-dependencies.json').write_text(json.dumps({'block':BLOCK,'contracts':rows},indent=2)+'\n')
