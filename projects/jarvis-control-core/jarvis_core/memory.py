from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import Counter
import hashlib, json, math, os, re, time

TOKEN_RE=re.compile(r"[a-zA-Z0-9_]{2,}")
def tokens(text:str)->list[str]: return TOKEN_RE.findall(text.lower())

@dataclass
class Memory:
    id:str; text:str; source:str; created_at:float; metadata:dict

class LocalMemoryStore:
    """Local-first persistent memory with deterministic BM25 retrieval and provenance."""
    def __init__(self,state_dir,clock=time.time):
        self.root=Path(state_dir); self.root.mkdir(parents=True,exist_ok=True); self.path=self.root/"memories.json"; self.clock=clock
        if not self.path.exists(): self._write([])
    def _read(self): return json.loads(self.path.read_text())
    def _write(self,rows):
        tmp=self.path.with_suffix(".tmp"); tmp.write_text(json.dumps(rows,indent=2,sort_keys=True)); os.replace(tmp,self.path)
    def remember(self,text,source,metadata=None,memory_id=None):
        if not text.strip(): raise ValueError("memory text cannot be empty")
        mid=memory_id or hashlib.sha256((source+"\n"+text).encode()).hexdigest()[:24]; rows=self._read()
        existing=next((r for r in rows if r["id"]==mid),None)
        if existing:return Memory(**existing)
        m=Memory(mid,text,source,self.clock(),metadata or {}); rows.append(asdict(m)); self._write(rows); return m
    def forget(self,memory_id):
        rows=self._read(); new=[r for r in rows if r["id"]!=memory_id]
        if len(new)==len(rows):return False
        self._write(new);return True
    def retrieve(self,query,k=5,filters=None):
        rows=self._read()
        if filters: rows=[r for r in rows if all(r.get("metadata",{}).get(a)==b for a,b in filters.items())]
        if not rows:return []
        docs=[tokens(r["text"]) for r in rows]; q=tokens(query)
        if not q:return []
        N=len(docs); avgdl=sum(map(len,docs))/max(N,1); df=Counter()
        for d in docs:
            for t in set(d):df[t]+=1
        scored=[]; k1=1.5; b=.75
        for r,d in zip(rows,docs):
            tf=Counter(d);score=0.0
            for t in q:
                if t not in tf:continue
                idf=math.log(1+(N-df[t]+.5)/(df[t]+.5)); score+=idf*(tf[t]*(k1+1))/(tf[t]+k1*(1-b+b*len(d)/max(avgdl,1)))
            if score>0:scored.append((score,r))
        scored.sort(key=lambda x:(x[0],x[1]["created_at"]),reverse=True)
        return [{"score":round(s,6),**r} for s,r in scored[:k]]
    def context(self,query,k=5,filters=None,max_chars=4000):
        hits=self.retrieve(query,k,filters);out=[];used=0
        for h in hits:
            line=f"[memory:{h['id']} source={h['source']}] {h['text']}"
            if used+len(line)>max_chars:break
            out.append(line);used+=len(line)+1
        return "\n".join(out)
