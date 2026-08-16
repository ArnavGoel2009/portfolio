from __future__ import annotations
from pathlib import Path
import json, os, subprocess, tempfile
from .worker import WorkerResult

class SubprocessWorker:
    """Execute a configured local CLI without shell interpolation.

    Task input is a temporary JSON file. The child writes JSON to
    JARVIS_RESULT_PATH: {ok, evidence, limitations, error}.
    """
    def __init__(self,name,capabilities,command,timeout=900,allowed_executables=None,cwd=None,env_allowlist=None):
        if not isinstance(command,list) or not command: raise ValueError("command must be a non-empty argv list")
        self.name=name; self.capabilities=list(capabilities); self.command=list(command); self.timeout=timeout
        self.allowed_executables=set(allowed_executables or [Path(command[0]).name])
        self.cwd=str(cwd) if cwd else None; self.env_allowlist=set(env_allowlist or [])
    def _argv(self,task_file):
        exe=Path(self.command[0]).name
        if exe not in self.allowed_executables: raise PermissionError(f"executable not allowed: {exe}")
        return [part.replace("{task_file}",str(task_file)) for part in self.command]
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
            try: data=json.loads(result_file.read_text())
            except Exception as exc:
                return WorkerResult(False,[],["invalid worker result"],f"invalid result JSON: {exc}")
            return WorkerResult(bool(data.get("ok")),list(data.get("evidence") or []),list(data.get("limitations") or []),data.get("error"))
