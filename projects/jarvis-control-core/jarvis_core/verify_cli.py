from __future__ import annotations
import argparse, json
from dataclasses import asdict
from .audit_verify import verify_state


def main(argv=None):
    parser=argparse.ArgumentParser(description='Verify JARVIS task state and audit invariants')
    parser.add_argument('state_dir',help='Directory containing tasks.json and audit.jsonl')
    parser.add_argument('--pretty',action='store_true',help='Pretty-print JSON output')
    args=parser.parse_args(argv)
    report=verify_state(args.state_dir)
    print(json.dumps(asdict(report),indent=2 if args.pretty else None,sort_keys=True))
    return 0 if report.ok else 2


if __name__=='__main__':
    raise SystemExit(main())
