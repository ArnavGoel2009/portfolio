from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib, json, os, re, time
SECRET_PATTERNS=[re.compile(r"sk-[A-Za-z0-9_-]{16,}"),re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*['\"]?([^\s'\"]+)")]
@dataclass
class IngestRecord:
 id:str; source:str; source_ref:str; content_hash:str; ingested_at:float; memory_ids:list[str]
def redact(text):
 out=text
 for p in SECRET_PATTERNS: out=p.sub(lambda m:(m.group(1)+"=[REDACTED]") if m.lastindex and m.lastindex>=2 else "[REDACTED]",out)
 return out
def chunk_text(text,max_chars=1400,overlap=180):
 text=text.strip();chunks=[];start=0
 while text and start<len(text):
  end=min(len(text),start+max_chars)
  if end<len(text):
   cut=max(text.rfind("\n",start,end),text.rfind(". ",start,end))
   if cut>start+max_chars//2:end=cut+1
  chunks.append(text[start:end].strip())
  if end>=len(text):break
  start=max(start+1,end-overlap)
 return [c for c in chunks if c]
class MemoryIngestor:
 def __init__(self,memory_store,state_dir,clock=time.time):
  self.memory=memory_store;self.root=Path(state_dir);self.root.mkdir(parents=True,exist_ok=True);self.path=self.root/"ingest_manifest.json";self.clock=clock
  if not self.path.exists():self.path.write_text("[]")
 def _manifest(self):return json.loads(self.path.read_text())
 def _write(self,rows):
  t=self.path.with_suffix(".tmp");t.write_text(json.dumps(rows,indent=2,sort_keys=True));os.replace(t,self.path)
 def ingest(self,source,source_ref,text,metadata=None):
  clean=redact(text);h=hashlib.sha256(clean.encode()).hexdigest();rows=self._manifest();old=next((r for r in rows if r["source"]==source and r["source_ref"]==source_ref and r["content_hash"]==h),None)
  if old:return IngestRecord(**old)
  mids=[]
  for i,ch in enumerate(chunk_text(clean)):
   mid=hashlib.sha256(f"{source}:{source_ref}:{h}:{i}".encode()).hexdigest()[:24];m=self.memory.remember(ch,source,{**(metadata or {}),"source_ref":source_ref,"content_hash":h,"chunk":i},memory_id=mid);mids.append(m.id)
  rec=IngestRecord(hashlib.sha256(f"{source}:{source_ref}:{h}".encode()).hexdigest()[:24],source,source_ref,h,self.clock(),mids);rows=[r for r in rows if not(r["source"]==source and r["source_ref"]==source_ref)];rows.append(asdict(rec));self._write(rows);return rec
class GitHubAdapter:
 def normalize(self,repo,path,content,ref="main"):return {"source":"github","source_ref":f"{repo}@{ref}:{path}","text":content,"metadata":{"repo":repo,"path":path,"ref":ref}}
class DriveAdapter:
 def normalize(self,file_id,title,content,mime_type=None):return {"source":"drive","source_ref":file_id,"text":content,"metadata":{"title":title,"mime_type":mime_type or "unknown"}}
class TaskOutcomeAdapter:
 def normalize(self,task):
  text=f"Task: {task.get('title','')}\nStatus: {task.get('status','')}\nEvidence: {json.dumps(task.get('evidence') or [],sort_keys=True)}\nLimitations: {json.dumps(task.get('limitations') or [])}"
  return {"source":"task_outcome","source_ref":task["id"],"text":text,"metadata":{"lane":task.get("lane"),"status":task.get("status")}}
