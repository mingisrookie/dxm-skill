#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Small stable DXM command router for copied-skill installations.

The router intentionally keeps each command in its existing dedicated module
so the audit path remains read-only and scaffold/recovery keep their explicit
write boundary.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


def _delegate(script: str, arguments: list[str]) -> int:
    result = subprocess.run([sys.executable, str(SCRIPT_DIR / script), *arguments], check=False)
    return result.returncode


def _doctor(root: Path, as_json: bool) -> int:
    from dxm_contract import EXIT_PARTIAL, audit_project
    from dxm_git import audit_git_privacy
    from dxm_io import inspect_recovery_state

    canonical = root.resolve(strict=False)
    audit = audit_project(canonical)
    privacy = audit_git_privacy(canonical)
    recovery = inspect_recovery_state(canonical)
    payload = {
        "command": "doctor",
        "root": str(canonical),
        "readiness": audit.state,
        "readiness_exit_code": audit.exit_code,
        "issues": list(audit.issues),
        "git_privacy": {"applicable": privacy.applicable, "state": privacy.state, "issues": list(privacy.issues)},
        "pending_transactions": list(recovery.pending_transactions),
        "recovery": {
            "lock_state": recovery.lock_state,
            "committed_transactions": recovery.committed_transactions,
            "issues": list(recovery.issues),
        },
        "recovery_required": recovery.recovery_required,
        "write_blocked": recovery.write_blocked,
    }
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(f"DXM doctor root: {canonical}")
        print(f"readiness: {audit.state}")
        print(f"git_privacy: {privacy.state}")
        print(f"pending_transactions: {len(recovery.pending_transactions)}")
        print(f"lock_state: {recovery.lock_state}")
        for issue in dict.fromkeys([*audit.issues, *privacy.issues, *recovery.issues]):
            print(f"  - {issue}")
    if audit.exit_code != 0:
        return audit.exit_code
    return EXIT_PARTIAL if recovery.write_blocked else 0


def main() -> int:
    raw_arguments = sys.argv[1:]
    if raw_arguments and raw_arguments[0] in {"init", "scaffold-only", "recover", "audit", "status"}:
        command, forwarded_arguments = raw_arguments[0], raw_arguments[1:]
        if command in {"init", "scaffold-only"}:
            return _delegate("scaffold_dxm.py", ["--mode", command, *forwarded_arguments])
        if command == "recover":
            return _delegate("scaffold_dxm.py", ["--recover", *forwarded_arguments])
        forwarded = ["audit", *forwarded_arguments]
        if command == "status" and "--json" not in forwarded:
            forwarded.append("--json")
        return _delegate("validate_dxm.py", forwarded)

    parser = argparse.ArgumentParser(description="DXM v2 command router")
    parser.add_argument("--version", action="store_true", help="show the packaged validator version")
    subparsers = parser.add_subparsers(dest="command")
    for command in ("init", "scaffold-only", "recover"):
        child = subparsers.add_parser(command)
        child.add_argument("arguments", nargs=argparse.REMAINDER)
    for command in ("audit", "status"):
        child = subparsers.add_parser(command)
        child.add_argument("arguments", nargs=argparse.REMAINDER)
    doctor = subparsers.add_parser("doctor")
    doctor.add_argument("--root", default=".")
    doctor.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.version:
        return _delegate("validate_dxm.py", ["--version"])
    if args.command is None:
        parser.print_help()
        return 2
    if args.command == "doctor":
        return _doctor(Path(args.root), args.json)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
