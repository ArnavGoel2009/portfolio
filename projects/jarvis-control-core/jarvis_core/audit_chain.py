from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib, hmac, json, os, time

GENESIS="0"*64

def canonical(obj:dict)->bytes:
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

def event_hash(prev_hash:str,payload:dict)->str:
    return hashlib.sha256(prev_hash.encode()+b"\n"+canonical(payload)).hexdigest()

@dataclass(frozen=True)
class ChainReport:
    ok:bool
    errors:list[str]
    event_count:int
    head:str

class AuditChain:
    """Append-only hash-chained audit log with optional HMAC checkpoints.

    Each row commits to the previous row's hash and the current canonical
    payload. Mutation, deletion-from-middle, insertion, or reordering breaks
    verification. HMAC checkpoints let an external trusted process anchor the
    current head so tail truncation is detectable too.
    """
    def __init__(self,state_dir,clock=time.time):
        self.root=Path(state_dir);self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"audit_chain.jsonl";self.clock=clock
    def _rows(self):
        if not self.path.exists():return []
        return [json.loads(x) for x in self.path.read_text().splitlines() if x.strip()]
    def head(self):
        rows=self._rows();return rows[-1]["hash"] if rows else GENESIS
    def append(self,event:str,actor:str,data:dict|None=None):
        prev=self.head()
        payload={"ts":self.clock(),"event":event,"actor":actor,"data":data or {}}
        digest=event_hash(prev,payload)
        row={"prev_hash":prev,"hash":digest,**payload}
        with self.path.open("a",encoding="utf-8") as f:
            f.write(json.dumps(row,sort_keys=True,separators=(",",":"))+"\n")
            f.flush();os.fsync(f.fileno())
        return row
    def checkpoint(self,key:bytes):
        head=self.head()
        return {"head":head,"mac":hmac.new(key,head.encode(),hashlib.sha256).hexdigest()}
    @staticmethod
    def verify_checkpoint(checkpoint:dict,key:bytes)->bool:
        expected=hmac.new(key,checkpoint["head"].encode(),hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected,checkpoint.get("mac",""))
    def verify(self,expected_checkpoint:dict|None=None,key:bytes|None=None)->ChainReport:
        errors=[];prev=GENESIS;rows=[]
        if self.path.exists():
            for n,line in enumerate(self.path.read_text().splitlines(),1):
                if not line.strip():continue
                try:r=json.loads(line)
                except Exception:
                    errors.append(f"INVALID_JSON:{n}");continue
                rows.append(r)
                if r.get("prev_hash")!=prev:
                    errors.append(f"PREV_HASH_MISMATCH:{n}")
                payload={k:r.get(k) for k in ("ts","event","actor","data")}
                want=event_hash(prev,payload)
                if r.get("hash")!=want:
                    errors.append(f"HASH_MISMATCH:{n}")
                prev=r.get("hash") or prev
        head=prev
        if expected_checkpoint is not None:
            if key is None:
                errors.append("CHECKPOINT_KEY_REQUIRED")
            elif not self.verify_checkpoint(expected_checkpoint,key):
                errors.append("CHECKPOINT_MAC_INVALID")
            elif expected_checkpoint.get("head")!=head:
                errors.append("CHECKPOINT_HEAD_MISMATCH")
        return ChainReport(not errors,errors,len(rows),head)
