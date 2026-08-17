from __future__ import annotations
from dataclasses import dataclass
import json, shutil, subprocess
from .worker import WorkerResult

@dataclass(frozen=True)
class CLIProfile:
    name: str
    executable: str
    capabilities: tuple[str, ...]
    args: tuple[str, ...]
    timeout: int = 1200

PROFILES = {
    "codex": CLIProfile("codex", "codex", ("python", "git", "coding"), ("exec", "--json", "-")),
    "claude": CLIProfile("claude", "claude", ("python", "git", "coding", "research"), ("-p", "--output-format", "json")),
    "gemini": CLIProfile("gemini", "gemini", ("coding", "research"), ("-p",)),
}

def probe_cli(profile: CLIProfile):
    path = shutil.which(profile.executable)
    if not path:
        return {"name": profile.name, "available": False, "path": None}
    cp = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=10, shell=False)
    return {"name": profile.name, "available": cp.returncode == 0, "path": path, "version": (cp.stdout or cp.stderr).strip()[:200]}

class NativeCLIWorker:
    """Native Codex/Claude/Gemini CLI boundary. Uses supported local CLI auth; no web-session bypass."""
    def __init__(self, profile: CLIProfile, cwd=None, timeout=None):
        self.profile = profile
        self.name = profile.name
        self.capabilities = list(profile.capabilities)
        self.cwd = str(cwd) if cwd else None
        self.timeout = timeout or profile.timeout

    def execute(self, task):
        path = shutil.which(self.profile.executable)
        if not path:
            return WorkerResult(False, [], ["CLI not installed"], f"{self.profile.executable} not found")
        prompt = (
            "You are a JARVIS worker. Execute the task below in the current workspace. "
            "Do not claim success without inspectable evidence. Return ONLY JSON with keys "
            "ok:boolean, evidence:[{type,ref}], limitations:[string], error:string|null.\nTASK:\n"
            + json.dumps(task.__dict__, sort_keys=True)
        )
        try:
            cp = subprocess.run([path, *self.profile.args], input=prompt, cwd=self.cwd, capture_output=True, text=True, timeout=self.timeout, shell=False)
        except subprocess.TimeoutExpired:
            return WorkerResult(False, [], ["native CLI timeout"], f"timeout after {self.timeout}s")
        if cp.returncode != 0:
            return WorkerResult(False, [], ["native CLI non-zero exit"], (cp.stderr or cp.stdout)[-2000:])
        raw = cp.stdout.strip()
        candidates = []
        try:
            candidates = [json.loads(raw)]
        except Exception:
            for line in raw.splitlines():
                try: candidates.append(json.loads(line))
                except Exception: pass
        for data in reversed(candidates):
            if isinstance(data, dict) and isinstance(data.get("ok"), bool):
                evidence = data.get("evidence") or []
                limitations = data.get("limitations") or []
                if all(isinstance(x, dict) and x.get("type") and x.get("ref") for x in evidence):
                    return WorkerResult(data["ok"], evidence, limitations, data.get("error"))
        return WorkerResult(False, [], ["CLI output did not contain JARVIS envelope"], "unparseable result contract")
