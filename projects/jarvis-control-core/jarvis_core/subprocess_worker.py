from __future__ import annotations
from pathlib import Path
import json, os, subprocess, tempfile
from .worker import WorkerResult

class SubprocessWorker:
    """Execute a configured local CLI without shell interpolation.

    Task input is a temporary JSON file. The child writes JSON to
    JARVIS_RESULT_PATH: {ok, evidence, limitations, error}.
    """
    def __init__(self,name,capabilities,command,timeout=900,allowed_executables=None,cwd=None,env_allowlist=None,max_result_bytes=1_000_000):
        if not isinstance(command,list) or not command: raise ValueError("command must be a non-empty argv list")
        if timeout <= 0: raise ValueError("timeout must be positive")
        if max_result_bytes <= 0: raise ValueError("max_result_bytes must be positive")
        self.name=name; self.capabilities=list(capabilities); self.command=list(command); self.timeout=timeout
        self.allowed_executables=set(allowed_executables or [Path(command[0]).name])
        self.cwd=str(cwd) if cwd else None; self.env_allowlist=set(env_allowlist or [])
        self.max_result_bytes=max_result_bytes
    def _argv(self,task_file):
        exe=Path(self.command[0]).name
        if exe not in self.allowed_executables: raise PermissionError(f"executable not allowed: {exe}")
        return [part.replace("{task_file}",str(task_file)) for part in self.command]
    def _invalid(self,message):
        return WorkerResult(False,[],["invalid worker result"],message)
    def _validate_result(self,data):
        if not isinstance(data,dict): return self._invalid("result root must be an object")
        if not isinstance(data.get("ok"),bool): return self._invalid("ok must be boolean")
        evidence=data.get("evidence") or []
        limitations=data.get("limitations") or []
        error=data.get("error")
        if not isinstance(evidence,list): return self._invalid("evidence must be a list")
        if not isinstance(limitations,list) or any(not isinstance(x,str) for x in limitations):
            return self._invalid("limitations must be a list of strings")
        if error is not None and not isinstance(error,str): return self._invalid("error must be string or null")
        for i,item in enumerate(evidence):
            if not isinstance(item,dict): return self._invalid(f"evidence[{i}] must be an object")
            if not isinstance(item.get("type"),str) or not item.get("type"):
                return self._invalid(f"evidence[{i}].type must be a non-empty string")
            if not isinstance(item.get("ref"),str) or not item.get("ref"):
                return self._invalid(f"evidence[{i}].ref must be a non-empty string")
        return WorkerResult(data["ok"],evidence,limitations,error)
    def execute(self,task):
        with tempfile.TemporaryDirectory(prefix="jarvis-worker-") as td:
            td=Path(td); task_file=td/"task.json"; result_file=td/"result.json"
            task_file.write_text(json.dumps(task.__dict__,sort_keys=True))
            env={"PATH":os.environ.get("PATH",""),"JARVIS_TASK_PATH":str(task_file),"JARVIS_RESULT_PATH":str(result_file)}
            for key in self.env_allowlist:
                if key in os.environ: env[key]=os.environ[key]
            try:
                cp=subprocess.run(self._argv(task_file),cwd=self.cwd,env=env,capture_output=True,text=True,timeout=self.timeout,shell=False)
            except subprocess.TimeoutExpired:
                return WorkerResult(False,[],["worker timed out"],f"timeout after {self.timeout}s")
            if cp.returncode!=0:
                err=(cp.stderr or cp.stdout or f"exit {cp.returncode}")[-2000:]
                return WorkerResult(False,[],["subprocess exited non-zero"],err)
            if not result_file.exists():
                return WorkerResult(False,[],["worker produced no result contract"],"missing JARVIS_RESULT_PATH output")
            try:
                if result_file.stat().st_size > self.max_result_bytes:
                    return self._invalid(f"result exceeds {self.max_result_bytes} bytes")
                data=json.loads(result_file.read_text())
            except Exception as exc:
                return self._invalid(f"invalid result JSON: {exc}")
            return self._validate_result(data)
