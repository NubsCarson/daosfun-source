"""Read-only EVM contract topology at a pinned block. Never signs or sends transactions."""
from pathlib import Path
import json,subprocess
ROOT=Path(__file__).resolve().parents[1]
RPC='https://rpc.mainnet.chain.robinhood.com';factory='0x798daAa0707C1e538bB5Acf0867Ac0e1A84cccF2'
block='0x5c3696a'
functions=['owner()','tokenImplementation()','curveImplementation()','locker()','memeHook()','launchForwarder()','initializationHook()','poolManager()','positionManager()','feeDestination()','protocolFeeRecipient()']
queries=[]
for i,f in enumerate(functions):
 sig=subprocess.check_output(['cast','sig',f],text=True).strip()
 queries.append({'jsonrpc':'2.0','id':i,'method':'eth_call','params':[{'to':factory,'data':sig},block]})
body=json.dumps(queries)
raw=subprocess.check_output(['curl','--fail','--silent','--show-error',RPC,'-H','content-type: application/json','--data',body],text=True)
rows=json.loads(raw);out=[]
for x in rows:
 item={'function':functions[x['id']],**x};value=x.get('result','')
 if len(value)==66:item['address']='0x'+value[-40:]
 out.append(item)
p=ROOT/'evidence/contracts/topology.json';p.write_text(json.dumps({'factory':factory,'block':block,'calls':out},indent=2)+'\n')
print(p.read_text())
