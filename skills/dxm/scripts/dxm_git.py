#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Git privacy checks for local-only DXM state.

This module intentionally performs only read-only Git queries.  It never
unstages or removes a user's tracked files.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


GITIGNORE_START = "# DXM:START"
GITIGNORE_END = "# DXM:END"
GITIGNORE_BLOCK = f"{GITIGNORE_START}\n.dxm/\n{GITIGNORE_END}\n"


class GitPrivacyError(ValueError):
    """Raised when the managed .gitignore block is unsafe to update."""


@dataclass(frozen=True)
class GitPrivacyResult:
    applicable: bool
    state: str
    issues: tuple[str, ...] = ()


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def is_git_worktree(root: Path) -> bool | None:
    result = _git(root, "rev-parse", "--is-inside-work-tree")
    if result is None:
        return None
    if result.returncode != 0:
        return False
    return result.stdout.strip().lower() == "true"


def managed_gitignore_content(existing: str | None) -> tuple[str, str]:
    """Return canonical content/status while preserving non-managed lines."""

    if existing is None:
        return GITIGNORE_BLOCK, "created"
    marker_lines: list[tuple[str, int, int]] = []
    offset = 0
    for raw_line in existing.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        if GITIGNORE_START in line or GITIGNORE_END in line:
            if line not in {GITIGNORE_START, GITIGNORE_END}:
                raise GitPrivacyError(".gitignore DXM managed markers must occupy complete lines")
            marker_lines.append((line, offset, offset + len(raw_line)))
        offset += len(raw_line)
    starts = [marker for marker in marker_lines if marker[0] == GITIGNORE_START]
    ends = [marker for marker in marker_lines if marker[0] == GITIGNORE_END]
    start_count = len(starts)
    end_count = len(ends)
    if start_count == 0 and end_count == 0:
        return existing.rstrip("\n") + "\n\n" + GITIGNORE_BLOCK, "appended-managed-block"
    if start_count != 1 or end_count != 1:
        raise GitPrivacyError(".gitignore has duplicate or incomplete DXM managed markers")
    start, _start_end = starts[0][1:]
    end, after_end = ends[0][1:]
    if end <= start:
        raise GitPrivacyError(".gitignore has crossed DXM managed markers")
    updated = existing[:start] + GITIGNORE_BLOCK + existing[after_end:]
    return updated, "refreshed-managed-block" if updated != existing else "skipped-existing"


def audit_git_privacy(root: Path) -> GitPrivacyResult:
    """Classify Git privacy without changing repository state."""

    worktree = is_git_worktree(root)
    if worktree is False:
        return GitPrivacyResult(False, "not-git")
    if worktree is None:
        return GitPrivacyResult(True, "unavailable", ("Git privacy audit is unavailable",))

    issues: list[str] = []
    gitignore = root / ".gitignore"
    try:
        existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else None
        _, block_status = managed_gitignore_content(existing)
    except (OSError, UnicodeDecodeError, GitPrivacyError) as exc:
        return GitPrivacyResult(True, "broken", (f".gitignore DXM privacy block is invalid: {type(exc).__name__}",))
    if block_status != "skipped-existing":
        issues.append(".gitignore is missing the portable DXM .dxm/ managed block")

    tracked = _git(root, "ls-files", "--error-unmatch", "--", ".dxm")
    if tracked is None:
        return GitPrivacyResult(True, "unavailable", ("Git tracked-file privacy audit is unavailable",))
    if tracked.returncode == 0:
        return GitPrivacyResult(
            True,
            "tracked",
            tuple(["DXM local state is already tracked by Git; do not auto-remove it", *issues]),
        )

    ignored = _git(root, "check-ignore", "-q", "--", ".dxm/project.json")
    if ignored is None:
        return GitPrivacyResult(True, "unavailable", ("Git ignore privacy audit is unavailable",))
    if ignored.returncode != 0:
        issues.append(".dxm/project.json is not ignored by Git")
    return GitPrivacyResult(True, "ignored" if not issues else "partial", tuple(issues))
