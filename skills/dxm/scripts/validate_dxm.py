#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only CLI for DXM baseline, run, readiness, and completion validation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from dxm_contract import (
    EXIT_INVALID,
    EXIT_OK,
    ContractError,
    audit_project,
    load_baseline,
    validate_receipt,
    validate_run,
    version_text,
)


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _print_validation(label: str, path: Path, errors: list[str], as_json: bool) -> None:
    payload = {
        "kind": label,
        "file": str(path.resolve(strict=False)),
        "valid": not errors,
        "errors": errors,
    }
    if as_json:
        _print_json(payload)
        return
    print(f"{label}: {'valid' if not errors else 'invalid'}")
    print(f"file: {payload['file']}")
    if errors:
        print("errors:")
        for error in errors:
            print(f"  - {error}")


def _audit(args: argparse.Namespace) -> int:
    result = audit_project(Path(args.root), require_trellis=args.require_trellis)
    if args.json:
        _print_json(result.to_dict())
    else:
        print(f"state: {result.state}")
        print(f"root: {result.root}")
        if result.issues:
            print("issues:")
            for issue in result.issues:
                print(f"  - {issue}")
    return result.exit_code


def _baseline(args: argparse.Namespace) -> int:
    path = Path(args.file)
    errors: list[str] = []
    try:
        load_baseline(path)
    except ContractError as exc:
        errors.extend(exc.errors)
    _print_validation("baseline", path, errors, args.json)
    return EXIT_INVALID if errors else EXIT_OK


def _receipt(args: argparse.Namespace) -> int:
    path = Path(args.file)
    errors = validate_receipt(
        path,
        expected_root=Path(args.root),
        allow_legacy=args.legacy_v1,
    )
    _print_validation("legacy-receipt" if args.legacy_v1 else "receipt", path, errors, args.json)
    return EXIT_INVALID if errors else EXIT_OK


def _run(args: argparse.Namespace) -> int:
    path = Path(args.file)
    errors = validate_run(path, expected_root=Path(args.root))
    _print_validation("run", path, errors, args.json)
    return EXIT_INVALID if errors else EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only DXM contract validator")
    parser.add_argument("--version", action="version", version=version_text())
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="audit a DXM project root")
    audit.add_argument("--root", required=True, help="project root to audit")
    audit.add_argument("--require-trellis", action="store_true", help="require a complete Trellis integration")
    audit.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    audit.set_defaults(handler=_audit)

    baseline = subparsers.add_parser("baseline", help="validate a project baseline JSON file")
    baseline.add_argument("--file", required=True, help="baseline JSON file")
    baseline.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    baseline.set_defaults(handler=_baseline)

    run = subparsers.add_parser("run", help="validate a lightweight task run JSON file")
    run.add_argument("--root", required=True, help="trusted project root used to verify run scope")
    run.add_argument("--file", required=True, help="canonical .dxm/runs/<run_id>/run.json file")
    run.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    run.set_defaults(handler=_run)

    receipt = subparsers.add_parser("receipt", help="validate a completion receipt JSON file")
    receipt.add_argument("--root", required=True, help="trusted project root used to verify receipt claims")
    receipt.add_argument("--file", required=True, help="completion receipt JSON file")
    receipt.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    receipt.add_argument(
        "--legacy-v1",
        action="store_true",
        help="audit a historical schema v1 receipt; never treats it as a current v2 completion",
    )
    receipt.set_defaults(handler=_receipt)
    return parser


def main() -> int:
    configure_stdio()
    args = build_parser().parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
