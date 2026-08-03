#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Versioned machine-readable DXM policy shared by core CLIs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class PolicyError(ValueError):
    """Raised when the packaged DXM policy cannot be trusted."""


POLICY_PATH = Path(__file__).resolve().parents[1] / "contract" / "policy.json"


def load_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PolicyError("DXM policy is unreadable") from exc
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise PolicyError("DXM policy has an unsupported schema")
    profiles = data.get("profiles")
    limits = data.get("limits")
    if not isinstance(profiles, dict) or not isinstance(limits, dict):
        raise PolicyError("DXM policy is incomplete")
    if set(profiles) != {"lite", "standard", "high-assurance"}:
        raise PolicyError("DXM policy has invalid profiles")
    required_limits = {
        "inventory_max_depth",
        "inventory_max_entries",
        "inventory_max_bytes",
        "inventory_timeout_seconds",
        "trellis_timeout_max_seconds",
        "trellis_user_max_length",
        "lock_stale_seconds",
    }
    if set(limits) != required_limits or any(type(limits[key]) is not int or limits[key] < 1 for key in required_limits):
        raise PolicyError("DXM policy has invalid limits")
    return data


POLICY = load_policy()
PROFILES = frozenset(POLICY["profiles"])
LIMITS: dict[str, int] = POLICY["limits"]
