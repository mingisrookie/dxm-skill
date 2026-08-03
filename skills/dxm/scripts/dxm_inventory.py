#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bounded, data-only DXM project inventory rendering."""

from __future__ import annotations

import json
import os
import stat
import time
from pathlib import Path
from typing import Callable


TOOL_STATE_DIRS = frozenset({".agents", ".codex", ".dxm", ".trellis"})


def _is_reparse_or_symlink(path: Path) -> bool:
    try:
        info = os.lstat(path)
    except OSError:
        return False
    attributes = getattr(info, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(info.st_mode) or bool(attributes & reparse_flag)


def _json_for_markdown(value: object) -> str:
    """Serialize untrusted text without allowing a Markdown fence/comment escape."""

    encoded = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return (
        encoded.replace("`", "\\u0060")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def safe_markdown_label(value: str) -> str:
    """Return a one-line display label that cannot create Markdown structure."""

    encoded = _json_for_markdown(value)
    return encoded[1:-1] if encoded.startswith('"') and encoded.endswith('"') else encoded


def _inventory_payload(
    entries: list[dict[str, str]],
    *,
    truncated_reason: str | None = None,
    note: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "format": "dxm-inventory-v2",
        "entries": entries,
        "truncated": truncated_reason is not None,
    }
    if truncated_reason is not None:
        payload["truncated_reason"] = truncated_reason
    if note is not None:
        payload["note"] = note
    return payload


def _render_payload(payload: dict[str, object], max_bytes: int) -> str:
    """Render a JSON payload within the declared byte cap.

    A truncation reason adds metadata after the last candidate was considered,
    so the final serialized form—not a smaller preview—owns the limit.
    """

    encoded = _json_for_markdown(payload)
    if len(encoded.encode("utf-8")) <= max_bytes:
        return encoded
    for fallback in (
        {"format": "dxm-inventory-v2", "entries": [], "truncated": True},
        {"format": "dxm-inventory-v2", "truncated": True},
        {"truncated": True},
        {},
    ):
        encoded = _json_for_markdown(fallback)
        if len(encoded.encode("utf-8")) <= max_bytes:
            return encoded
    return ""


def project_inventory(
    root: Path,
    *,
    depth: int,
    max_entries: int,
    max_bytes: int,
    timeout_seconds: int,
    skip_dirs: set[str] | frozenset[str],
    is_sensitive_name: Callable[[str, bool], bool],
) -> str:
    """Return a safely fenced, bounded JSON inventory without reading file contents."""

    if max_bytes < 2:
        raise ValueError("max_bytes must allow a JSON payload")

    def render(payload: dict[str, object]) -> str:
        return "#### 文件结构快照（安全编码）\n\n````json\n" + _render_payload(payload, max_bytes) + "\n````"

    if not root.exists():
        return render(_inventory_payload([], note="project-root-does-not-exist"))

    started = time.monotonic()
    entries: list[dict[str, str]] = []
    truncated_reason: str | None = None
    all_skip_dirs = set(skip_dirs) | set(TOOL_STATE_DIRS)

    def timed_out() -> bool:
        return time.monotonic() - started >= timeout_seconds

    def fits_final_truncation(candidate: dict[str, str]) -> bool:
        # Reserve the longest fixed reason so a later max-entry or max-byte
        # cut cannot make the serialized payload exceed its declared limit.
        preview = _inventory_payload([*entries, candidate], truncated_reason="max-entries")
        return len(_json_for_markdown(preview).encode("utf-8")) <= max_bytes

    def add(path: str, kind: str, note: str) -> bool:
        nonlocal truncated_reason
        candidate = {"path": path, "kind": kind, "note": note}
        if len(entries) >= max_entries:
            truncated_reason = "max-entries"
            return False
        if not fits_final_truncation(candidate):
            truncated_reason = "max-bytes"
            return False
        entries.append(candidate)
        return True

    def visit(directory: Path, current_depth: int, prefix: str = "") -> None:
        nonlocal truncated_reason
        if truncated_reason is not None:
            return
        if timed_out():
            truncated_reason = "timeout"
            return
        try:
            children = directory.iterdir()
        except PermissionError:
            add(prefix.rstrip("/") or ".", "directory", "permission-denied")
            return
        except OSError:
            add(prefix.rstrip("/") or ".", "directory", "unreadable")
            return

        while True:
            if truncated_reason is not None:
                return
            if timed_out():
                truncated_reason = "timeout"
                return
            try:
                child = next(children)
            except StopIteration:
                return
            except PermissionError:
                add(prefix.rstrip("/") or ".", "directory", "permission-denied")
                return
            except OSError:
                add(prefix.rstrip("/") or ".", "directory", "unreadable")
                return
            if timed_out():
                truncated_reason = "timeout"
                return
            name = child.name
            relative = f"{prefix}{name}"
            if _is_reparse_or_symlink(child):
                add(relative, "link", "not-expanded")
                continue
            try:
                child_is_dir = child.is_dir()
                child_is_file = child.is_file()
            except OSError:
                add(relative, "unknown", "unreadable")
                continue
            if child_is_dir and name in all_skip_dirs:
                add(relative, "directory", "tool-or-build-state-not-expanded")
                continue
            if is_sensitive_name(name, child_is_file):
                add(relative, "directory" if child_is_dir else "file", "sensitive-name-not-expanded")
                continue
            if child_is_dir:
                if not add(relative, "directory", "project-directory"):
                    return
                if current_depth < depth:
                    visit(child, current_depth + 1, f"{relative}/")
            else:
                add(relative, "file", "project-file")

    visit(root, 1)
    return render(_inventory_payload(entries, truncated_reason=truncated_reason))
