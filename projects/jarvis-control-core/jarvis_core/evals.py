from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable, Any
import json, time

@dataclass
class EvalCase:
    name: str
    objective: str
    expected: dict

@dataclass
class EvalResult:
    name: str
    passed: bool
    checks: dict[str, bool]
    output: dict
    elapsed_ms: float

class EvalSuite:
    """Deterministic regression harness for JARVIS planners/workers.

    `subject` receives an objective and returns a dict. Expectations are checked
    without asking an LLM to grade itself. Supported checks: required keys,
    exact values, forbidden values, minimum evidence count, and maximum steps.
    """
    def __init__(self, cases: list[EvalCase]):
        self.cases = cases

    @staticmethod
    def _check(output: dict, expected: dict) -> dict[str, bool]:
        checks: dict[str, bool] = {}
        required = expected.get("required_keys", [])
        checks["required_keys"] = all(k in output for k in required)
        for k, v in expected.get("equals", {}).items():
            checks[f"equals:{k}"] = output.get(k) == v
        for k, forbidden in expected.get("forbidden", {}).items():
            checks[f"forbidden:{k}"] = output.get(k) not in forbidden
        if "min_evidence" in expected:
            checks["min_evidence"] = len(output.get("evidence") or []) >= expected["min_evidence"]
        if "max_steps" in expected:
            checks["max_steps"] = len(output.get("steps") or []) <= expected["max_steps"]
        return checks

    def run(self, subject: Callable[[str], dict]) -> list[EvalResult]:
        results = []
        for case in self.cases:
            start = time.perf_counter()
            try:
                output = subject(case.objective)
                if not isinstance(output, dict):
                    output = {"_invalid_output": repr(output)}
                checks = self._check(output, case.expected)
            except Exception as exc:
                output = {"_exception": f"{type(exc).__name__}: {exc}"}
                checks = {"no_exception": False}
            elapsed = (time.perf_counter() - start) * 1000
            results.append(EvalResult(case.name, bool(checks) and all(checks.values()), checks, output, elapsed))
        return results

    @staticmethod
    def summary(results: list[EvalResult]) -> dict[str, Any]:
        passed = sum(r.passed for r in results)
        total = len(results)
        return {"passed": passed, "failed": total-passed, "total": total,
                "pass_rate": passed/total if total else 0.0,
                "failed_cases": [r.name for r in results if not r.passed]}

    @staticmethod
    def save(results: list[EvalResult], path: str | Path) -> None:
        Path(path).write_text(json.dumps([asdict(r) for r in results], indent=2, sort_keys=True))
