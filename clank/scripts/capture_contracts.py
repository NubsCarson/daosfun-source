"""Inspect the initial discovery capture without overwriting pinned runtime evidence."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'evidence/contracts'
rows=json.loads((out/'initial-rpc.json').read_text())
ALPHABET='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
def b58(data):
 n=int.from_bytes(data,'big');s=''
 while n:n,r=divmod(n,58);s=ALPHABET[r]+s
 return ALPHABET[0]*(len(data)-len(data.lstrip(b'\0')))+s
records=[]
for row,name,address in zip(rows[2:],['factory','eth-router'],['0x798daAa0707C1e538bB5Acf0867Ac0e1A84cccF2','0xb4a4315abbbf9fcC71a6e48D604310D7A36A6378']):
 data=bytes.fromhex(row['result'][2:])
 suffix=data[-int.from_bytes(data[-2:],'big')-2:-2]
 ipfs=suffix.find(b'dipfsX\x22');solc=suffix.find(b'dsolcC')
 if ipfs < 0 or solc < 0: raise ValueError('Unsupported CBOR metadata layout')
 cid=b58(suffix[ipfs+7:ipfs+41]);version='.'.join(str(x) for x in suffix[solc+6:solc+9])
 records.append(dict(name=name,address=address,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),solc_version=version,metadata_cid=cid))
(out/'inventory.json').write_text(json.dumps(records,indent=2)+'\n');print(json.dumps(records,indent=2))
