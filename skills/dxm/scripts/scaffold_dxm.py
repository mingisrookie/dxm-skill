#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scaffold DXM large-project AI collaboration files into a project root."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import signal
import shutil
import stat
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from dxm_contract import (  # noqa: E402 - keep the packaged sibling import deterministic
    BASELINE_BLOCK_END,
    BASELINE_BLOCK_START,
    BROKEN,
    ContractError,
    EXIT_INVALID,
    EXIT_PARTIAL,
    PARTIAL,
    READY,
    audit_project,
    baseline_markdown,
    load_baseline,
    managed_block_span,
    markdown_noncode_surface,
    validate_managed_markers,
    validate_marker_layout,
)
from dxm_inventory import project_inventory as bounded_project_inventory  # noqa: E402
from dxm_inventory import safe_markdown_label  # noqa: E402
from dxm_git import GitPrivacyError, is_git_worktree, managed_gitignore_content  # noqa: E402
from dxm_io import (  # noqa: E402
    DxmIoError,
    ERROR_WRITE_FAILED,
    ERROR_RECOVERY_REQUIRED,
    ProjectLock,
    ProjectTransaction,
    atomic_replace_text,
    normalize_lf as io_normalize_lf,
    pending_transaction_states,
    recover_transactions,
)
from dxm_policy import LIMITS  # noqa: E402


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


configure_stdio()


FILES = [
    "AGENTS.md",
    "项目开发规范（AI协作）.md",
    "项目完整链路说明.md",
    "项目文件结构说明.md",
    "开发者AI开发与PR提交流程.md",
]

DXM_BLOCK_START = "<!-- DXM-RULES:START -->"
DXM_BLOCK_END = "<!-- DXM-RULES:END -->"
TRELLIS_BLOCK_START = "<!-- DXM-TRELLIS:START -->"
TRELLIS_BLOCK_END = "<!-- DXM-TRELLIS:END -->"
TRELLIS_START_STEP0_START = "<!-- DXM-TRELLIS-START-STEP0:START -->"
TRELLIS_START_STEP0_END = "<!-- DXM-TRELLIS-START-STEP0:END -->"
TRELLIS_WORKFLOW_OVERRIDE_START = "<!-- DXM-TRELLIS-WORKFLOW-OVERRIDE:START -->"
TRELLIS_WORKFLOW_OVERRIDE_END = "<!-- DXM-TRELLIS-WORKFLOW-OVERRIDE:END -->"
DXM_DOC_BLOCK_START = "<!-- DXM-DOC-RULES:START -->"
DXM_DOC_BLOCK_END = "<!-- DXM-DOC-RULES:END -->"

EXIT_TRELLIS_UNAVAILABLE = 3
EXIT_TRELLIS_FAILED = 4

_ACTIVE_TRANSACTION: ProjectTransaction | None = None

SKIP_DIRS = {
    ".git",
    ".idea",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    ".vscode",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "venv",
}
SENSITIVE_NAMES = {
    ".env",
    ".env.local",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "accounts.json",
    "credentials.json",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
    "kubeconfig",
    "service-account.json",
    "tokens",
    "username.json",
}
SENSITIVE_PATTERNS = {
    ".env.*",
    "*.env",
    "*.crt",
    "*.db",
    "*.jks",
    "*.key",
    "*.keystore",
    "*.pem",
    "*.p12",
    "*.pfx",
    "*.secret.*",
    "*.sqlite",
    "credentials*.json",
    "secret*.json",
    "secret*.yaml",
    "secret*.yml",
    "service-account*.json",
    "*service-account*.json",
}
SENSITIVE_TOKEN_RE = re.compile(r"(^|[-_.])(api[-_]?key|credential|credentials|password|secret|token|tokens)([-_.]|$)")
SOURCE_OR_DOC_SUFFIXES = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".h",
    ".hpp",
    ".html",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".kts",
    ".less",
    ".md",
    ".mdx",
    ".mjs",
    ".php",
    ".ps1",
    ".py",
    ".pyw",
    ".rb",
    ".rs",
    ".rst",
    ".sass",
    ".scala",
    ".scss",
    ".sh",
    ".svelte",
    ".swift",
    ".ts",
    ".tsx",
    ".vue",
}
BROAD_ROOT_NAMES = SKIP_DIRS | {"vendor", "vendors", ".venv", "venv", "site-packages"}

TRELLIS_AGENTS_BLOCK = f"""{TRELLIS_BLOCK_START}

## DXM + Trellis 大开发路由

Trellis 是 DXM 下面的中大型任务持久层，不替代本目录长期文档。

- 小修、只读排查、单点 bug、轻量文档调整：默认按 DXM inline **run-only** 处理，创建 `.dxm/runs/<run_id>/run.json`，不强制 Trellis task。
- 新功能、架构变化、跨多文件重构、长周期任务：先用 DXM core 做本地证据优先、单批 0–3 个阻塞问题的有界 project-grill；用户已批准 Trellis 时，再把结论落到 `.trellis/tasks/<task>/prd.md`。
- `grill-with-docs` 可在已安装且任务描述匹配时用于已有代码/文档的有界查证，但仍必须遵守单批 0–3 个阻塞问题；full `grilling` / legacy `grill-me` 只有用户 explicit opt-in 完整/穷举澄清时才调用。它们都不是 Trellis 硬依赖。
- 提问前从第一性原理判断真实目标、硬约束、本地可查事实和仍阻塞的问题，并质疑隐藏假设、过度方案、伪约束和用户给出的实现偏置；本地可查事实不得反问。
- 用户明确说 `scaffold only`、`先别问`、`只分析` 时，不进入 Trellis，不擅自改文件。
- 每次 Trellis 任务完成前必须执行对抗性检查；high-risk 还要不同 Agent 的 canonical `independent-review.md` PASS，并由 receipt 绑定其 `artifact_sha256` 与 reviewer/time/PASS 元数据。它是本地 evidence-consistency/reviewer-separation gate，不是可信身份认证；`high-assurance` 另需独立可信边界的 external provenance。通过后把最终 `check.md` 的文件首个非空行写成顶格独立且全文唯一的 `<!-- DXM-CHECK:PASS -->`，再按 `finish` → `archive <task> --no-commit` → schema_version: 2 completion receipt 收口。
- Trellis 不得自动 stage/commit/push/PR；提交和推送仍需用户明确授权。

{TRELLIS_BLOCK_END}
"""

TRELLIS_DEV_RULES_BLOCK = f"""{TRELLIS_BLOCK_START}

## DXM + Trellis 协作规则

Trellis 只用于中大型开发任务的 PRD、任务状态和检查沉淀。默认路由：

| 场景 | 默认处理 |
| --- | --- |
| 只分析 / 先看看 | 只读，不建 task |
| 小修 / 单点 bug / 单文件文档调整 | DXM inline run-only，建 lightweight run，不建 task |
| 新功能 / 多模块 / 架构 / 跨文件 / 长周期 | DXM core 有界 project-grill；获准后建 Trellis task |
| 需求不清楚但会继续开发 | 先查本地证据并单批问 0–3 个阻塞问题；匹配时可用有界 `grill-with-docs`，full `grilling` 仅 explicit opt-in |
| 用户明确 scaffold only / 先别问 | 只 scaffold，不 grill，不建 task |

启用 Trellis 时必须保持 `session_auto_commit: false`，并遵守本项目 Git/PR 授权规则。
每个可写 task 先建 `.dxm/runs/<run_id>/run.json`；source-only 必须记录 `unverified_boundaries`。运行态声明用带 `observed_at` 的 structured observation；high-risk 要 hash-bound canonical `independent-review.md`，但它只证明本地一致性；`high-assurance` 还要 external provenance。Trellis 最后按 `finish` → `archive <task> --no-commit` → schema_version: 2 归档回执收口。

{TRELLIS_BLOCK_END}
"""

TRELLIS_FILE_STRUCTURE_BLOCK = f"""{TRELLIS_BLOCK_START}

## DXM 大开发工作流目录

本项目启用 Trellis/Codex 大开发工作流时，下列目录属于项目级 AI 协作基础设施：

- `.trellis/`：Trellis 项目工作流状态、任务 PRD、spec、workspace journal 和脚本。
- `.dxm/runs/`：可写任务的 lightweight run、任务 outcome/impact 边界、inline completion receipt 和适用时的 canonical `independent-review.md`；默认由项目忽略，不作为发布产物。
- `.trellis/tasks/`：每个开发任务的 `task.json`、`prd.md`、实现上下文和检查上下文。
- `.trellis/spec/`：可复用项目规范；完成任务后应把稳定经验沉淀回这里。
- `.codex/`：项目级 Codex agents、hooks 和配置。
- `.agents/skills/`：跨 agent 共享的 Trellis skill 入口。

维护要求：修改这些目录的事实结构或工作流含义时，同步更新 `AGENTS.md`、`项目开发规范（AI协作）.md` 和本文档。

{TRELLIS_BLOCK_END}
"""

TRELLIS_CHAIN_BLOCK = f"""{TRELLIS_BLOCK_START}

## DXM 大开发工作流链路

中大型开发、新模块、跨多文件重构、需求不清楚的任务，默认走：

1. 先由 DXM core 做 `project-grill`：有代码/文档时先查证，空项目按 `new-project-grill`，小脚本/demo 按 `lightweight-grill`；核心流程不依赖 sibling skill。
2. 从第一性原理出发、质疑隐藏假设，先从代码和文档自行判断，再单批提出 0–3 个阻塞问题；`grill-with-docs` 可在已安装且任务描述匹配时做同样有界的查证，full `grilling` / legacy `grill-me` 仅在用户 explicit opt-in 深度澄清时作为 optional 增强。
3. 写 `.dxm/runs/<run_id>/run.json` 锁定原始 goal、outcomes、`baseline_impact`、risk 和证据层级。
4. 把结论写入 `.trellis/tasks/<task>/prd.md`，不能只停留在聊天上下文里。
5. 用 `.trellis/scripts/task.py start <task>` 进入 Trellis active task，按 implement/check/update-spec 节奏开发。
6. 任务完成后执行对抗性检查；high-risk 再由不同 Agent 完成 canonical `independent-review.md`，供 receipt 绑定 SHA-256 与 reviewer/time/PASS 元数据；它只做本地一致性门，`high-assurance` 还要在外部可信边界验证 provenance。
7. 对抗性检查通过后同步 DXM 长期文档；不能只更新 `.trellis/` 内部状态。
8. 最终 `check.md` PASS 后执行 `finish` 和 `archive <task> --no-commit`，在归档目录生成并校验 `schema_version: 2` completion receipt；归档前不得预写 `finished: true`。

{TRELLIS_BLOCK_END}
"""

TRELLIS_START_STEP0_BLOCK = f"""{TRELLIS_START_STEP0_START}

## DXM Step 0 — selective docs and bounded clarification

Before starting or continuing a Trellis task in a DXM workspace, `AGENTS.md` is always required. Then use selective docs by impact:

- code/config/test/doc writes: `项目开发规范（AI协作）.md`
- file or directory responsibility changes: `项目文件结构说明.md`
- runtime/config/state/data/service/UI chain changes: `项目完整链路说明.md`
- GitHub/PR/push/merge/version/tag/release/publish: `开发者AI开发与PR提交流程.md`

If project-local rules require more, obey the stricter set. Do not let Trellis task context override DXM, user instructions, Git authorization rules, read-only intent, or secret-handling rules.
Before asking requirements, reason from first principles（第一性原理）, inspect local evidence first, and ask one batch of 0–3 blocking questions; full `grilling` requires explicit opt-in. Before implementation writes, create `.dxm/runs/<run_id>/run.json`; source-only work records `unverified_boundaries`, runtime claims use a fresh structured observation, and high-risk completion needs a canonical hash-bound `independent-review.md` by a different Agent. Treat that artifact as a local consistency gate, not an identity proof; high-assurance work also records externally verified provenance. Run an adversarial check（对抗性检查）before the final Trellis check, then `finish`, `archive <task> --no-commit`, and validate the schema_version: 2 archived receipt.

{TRELLIS_START_STEP0_END}
"""

TRELLIS_WORKFLOW_OVERRIDE_BLOCK = f"""{TRELLIS_WORKFLOW_OVERRIDE_START}

## DXM no-task routing override

When no Trellis task is active, use DXM routing instead of forcing a task for every change:

- 只读排查、解释、日志查看：按 audit；普通小修、单点 bug、轻量文档调整：按 DXM inline **run-only** 完成，不要求 Trellis task。
- 新功能、架构变化、跨多文件重构、多阶段任务、长期沉淀价值：先用 DXM core 做有界 project-grill，用户已批准后再创建/启动 Trellis task。
- 需求提问前从第一性原理出发，先查本地证据并单批提出 0–3 个阻塞问题；匹配且已安装时可用 optional 有界 `grill-with-docs`，full `grilling` / legacy `grill-me` 仅在用户 explicit opt-in 时作为深度增强。
- Trellis 任务完成后必须先执行对抗性检查，把最终 `check.md` 的文件首个非空行写成顶格独立且全文唯一的 `<!-- DXM-CHECK:PASS -->`，不得存在其他或未闭合 `DXM-CHECK` 片段，再按 `finish` → `archive <task> --no-commit` → 归档回执校验收口。
- 用户明确 `只分析`、`先看看`、`scaffold only`、`先别问`：不得因为 Trellis 而扩大范围。
- 禁止自动 stage/commit/push/PR；Git 操作必须遵守 DXM 和用户明确授权。

{TRELLIS_WORKFLOW_OVERRIDE_END}
"""


class ExistingFileEncodingError(Exception):
    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(f"{path} is not valid UTF-8")


class UnsafeProjectRootError(Exception):
    def __init__(self, root: Path) -> None:
        self.root = root
        super().__init__(f"{root} is too broad for DXM scaffold")


class ProjectRootNotDirectoryError(Exception):
    def __init__(self, root: Path, blocker: Path | None = None) -> None:
        self.root = root
        self.blocker = blocker or root
        super().__init__(f"{root} project root must be a directory; blocked by {self.blocker}")


class UnsafeManagedPathError(Exception):
    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"{path} is an unsafe managed path: {reason}")


class BrokenManagedBlockError(Exception):
    def __init__(self, path: Path, start_marker: str, end_marker: str) -> None:
        self.path = path
        self.start_marker = start_marker
        self.end_marker = end_marker
        super().__init__(f"{path} has incomplete managed block {start_marker}")


class InvalidManagedBlockError(Exception):
    def __init__(self, path: Path, start_marker: str, end_marker: str, errors: list[str]) -> None:
        self.path = path
        self.start_marker = start_marker
        self.end_marker = end_marker
        self.errors = tuple(errors)
        super().__init__(f"{path} has invalid managed block {start_marker}: {'; '.join(errors)}")


class TrellisConfigError(Exception):
    """Raised when the limited DXM Trellis config adapter cannot act safely."""


def normalize_lf(content: str) -> str:
    return io_normalize_lf(content)


def read_existing_text(path: Path) -> str:
    try:
        return normalize_lf(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise ExistingFileEncodingError(path) from exc


def write_text_lf(path: Path, content: str) -> None:
    if _ACTIVE_TRANSACTION is not None:
        _ACTIVE_TRANSACTION.write_text(path, content)
        return
    atomic_replace_text(path, content)


def is_reparse_or_symlink(path: Path) -> bool:
    try:
        info = os.lstat(path)
    except OSError:
        return False
    attributes = getattr(info, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(info.st_mode) or bool(attributes & reparse_flag)


def validate_managed_path(root: Path, path: Path) -> None:
    """Reject managed writes that could escape the locked canonical root."""

    canonical_root = root.resolve(strict=False)
    lexical_path = path.absolute()
    try:
        lexical_path.relative_to(canonical_root)
    except ValueError as exc:
        raise UnsafeManagedPathError(path, "path is outside the locked project root") from exc

    try:
        resolved_parent = path.parent.resolve(strict=False)
        resolved_parent.relative_to(canonical_root)
    except (OSError, ValueError) as exc:
        raise UnsafeManagedPathError(path, "parent resolves outside the locked project root") from exc

    current = path if path.exists() or path.is_symlink() else path.parent
    while True:
        if current.exists() or current.is_symlink():
            if current != canonical_root and is_reparse_or_symlink(current):
                raise UnsafeManagedPathError(path, f"link or reparse component: {current.name}")
            try:
                info = os.lstat(current)
            except OSError as exc:
                raise UnsafeManagedPathError(path, f"cannot inspect path component: {current.name}") from exc
            if current == path:
                if not stat.S_ISREG(info.st_mode):
                    raise UnsafeManagedPathError(path, "existing target is not a regular file")
                if info.st_nlink > 1:
                    raise UnsafeManagedPathError(path, "existing target has multiple hard links")
            elif not stat.S_ISDIR(info.st_mode):
                raise UnsafeManagedPathError(path, f"ancestor is not a directory: {current.name}")
        if current == canonical_root:
            break
        if current.parent == current:
            raise UnsafeManagedPathError(path, "path ancestry does not reach the locked project root")
        current = current.parent


def extract_block(content: str, start_marker: str, end_marker: str) -> str | None:
    span = managed_block_span(content, start_marker, end_marker)
    if span is None:
        return None
    return content[slice(*span)]


def replace_block(existing: str, block: str, start_marker: str, end_marker: str) -> str | None:
    span = managed_block_span(existing, start_marker, end_marker)
    if span is None:
        return None
    start, end = span
    return existing[:start] + block + existing[end:]


def managed_block_state(content: str, start_marker: str, end_marker: str) -> str:
    errors = validate_marker_layout(content, start_marker, end_marker)
    if errors:
        return "broken"
    if managed_block_span(content, start_marker, end_marker) is None:
        return "missing"
    return "complete"


def require_complete_managed_block(path: Path, content: str, start_marker: str, end_marker: str) -> None:
    errors = validate_marker_layout(content, start_marker, end_marker)
    if not errors:
        return
    # Preserve the long-standing actionable wording for the common truncated
    # START case while reporting all other corrupt layouts as invalid.
    marker_surface = markdown_noncode_surface(content)
    if marker_surface.count(start_marker) == 1 and marker_surface.count(end_marker) == 0:
        raise BrokenManagedBlockError(path, start_marker, end_marker)
    raise InvalidManagedBlockError(path, start_marker, end_marker, errors)


def check_managed_blocks(path: Path, content: str, marker_pairs: list[tuple[str, str]]) -> None:
    # Keep the specific truncated-block diagnostic before the global marker
    # grammar check. Crossed/nested/malformed layouts still fail below.
    for start_marker, end_marker in marker_pairs:
        require_complete_managed_block(path, content, start_marker, end_marker)
    layout_errors = validate_managed_markers(content)
    if layout_errors:
        start_marker, end_marker = marker_pairs[0] if marker_pairs else ("<!-- DXM-*:START -->", "<!-- DXM-*:END -->")
        raise InvalidManagedBlockError(path, start_marker, end_marker, layout_errors)


def scaffold_marker_pairs(filename: str) -> list[tuple[str, str]]:
    pairs = [(TRELLIS_BLOCK_START, TRELLIS_BLOCK_END)]
    if filename == "AGENTS.md":
        return [(DXM_BLOCK_START, DXM_BLOCK_END), *pairs]
    if filename == "项目完整链路说明.md":
        return [
            (DXM_DOC_BLOCK_START, DXM_DOC_BLOCK_END),
            (BASELINE_BLOCK_START, BASELINE_BLOCK_END),
            *pairs,
        ]
    return [(DXM_DOC_BLOCK_START, DXM_DOC_BLOCK_END), *pairs]


def is_sensitive_name(name: str, *, is_file: bool = True) -> bool:
    lowered = name.lower()
    if lowered in SENSITIVE_NAMES:
        return True
    if any(fnmatch.fnmatch(lowered, pattern) for pattern in SENSITIVE_PATTERNS):
        return True
    if is_file and Path(lowered).suffix in SOURCE_OR_DOC_SUFFIXES:
        return False
    if not is_file:
        return False
    return SENSITIVE_TOKEN_RE.search(lowered) is not None


def is_broad_root(root: Path) -> bool:
    resolved = root.resolve()
    if resolved == resolved.parent:
        return True
    try:
        if resolved == Path.home().resolve():
            return True
    except RuntimeError:
        pass

    for env_name in ["SystemRoot", "WINDIR", "ProgramFiles", "ProgramFiles(x86)", "ProgramData", "APPDATA", "LOCALAPPDATA"]:
        value = os.environ.get(env_name)
        if not value:
            continue
        try:
            if resolved == Path(value).resolve():
                return True
        except RuntimeError:
            continue

    return resolved.name.lower() in BROAD_ROOT_NAMES


def validate_project_root(root: Path, allow_broad_root: bool) -> None:
    existing = root
    while not os.path.lexists(existing) and existing != existing.parent:
        existing = existing.parent
    if os.path.lexists(existing) and not existing.is_dir():
        raise ProjectRootNotDirectoryError(root, existing)
    if not allow_broad_root and is_broad_root(root):
        raise UnsafeProjectRootError(root)


def read_template(name: str) -> str:
    template_dir = Path(__file__).resolve().parents[1] / "assets" / "templates"
    return normalize_lf((template_dir / f"{name}.template").read_text(encoding="utf-8"))


def project_inventory(
    root: Path,
    depth: int = 1,
    *,
    max_entries: int = LIMITS["inventory_max_entries"],
    max_bytes: int = LIMITS["inventory_max_bytes"],
    timeout_seconds: int = LIMITS["inventory_timeout_seconds"],
) -> str:
    return bounded_project_inventory(
        root,
        depth=depth,
        max_entries=max_entries,
        max_bytes=max_bytes,
        timeout_seconds=timeout_seconds,
        skip_dirs=SKIP_DIRS,
        is_sensitive_name=lambda name, is_file: is_sensitive_name(name, is_file=is_file),
    )


def render(
    content: str,
    root: Path,
    inventory_depth: int = 1,
    *,
    inventory_max_entries: int = LIMITS["inventory_max_entries"],
    inventory_max_bytes: int = LIMITS["inventory_max_bytes"],
    inventory_timeout_seconds: int = LIMITS["inventory_timeout_seconds"],
) -> str:
    return (
        content.replace("{{project_name}}", safe_markdown_label(root.name))
        .replace("{{generated_date}}", datetime.now().strftime("%Y-%m-%d"))
        .replace(
            "{{file_inventory}}",
            project_inventory(
                root,
                inventory_depth,
                max_entries=inventory_max_entries,
                max_bytes=inventory_max_bytes,
                timeout_seconds=inventory_timeout_seconds,
            ),
        )
    )


def dxm_block(
    root: Path,
    inventory_depth: int = 1,
    *,
    inventory_max_entries: int = LIMITS["inventory_max_entries"],
    inventory_max_bytes: int = LIMITS["inventory_max_bytes"],
    inventory_timeout_seconds: int = LIMITS["inventory_timeout_seconds"],
) -> str:
    return render(
        read_template("AGENTS.md"),
        root,
        inventory_depth,
        inventory_max_entries=inventory_max_entries,
        inventory_max_bytes=inventory_max_bytes,
        inventory_timeout_seconds=inventory_timeout_seconds,
    )


def refresh_managed_block(path: Path, content: str, start_marker: str, end_marker: str, dry_run: bool = False) -> str:
    existing = read_existing_text(path)
    state = managed_block_state(existing, start_marker, end_marker)
    if state == "missing":
        return "would-skip-no-managed-block" if dry_run else "skipped-no-managed-block"
    if state == "broken":
        raise BrokenManagedBlockError(path, start_marker, end_marker)

    block = extract_block(content, start_marker, end_marker)
    updated = replace_block(existing, block or content, start_marker, end_marker)
    if updated is None or updated == existing:
        return "would-skip-existing" if dry_run else "skipped-existing"
    if dry_run:
        return "would-refresh-managed-block"
    write_text_lf(path, updated)
    return "refreshed-managed-block"


def ensure_agents(
    path: Path,
    root: Path,
    force: bool,
    dry_run: bool = False,
    refresh_blocks: bool = False,
    inventory_depth: int = 1,
    *,
    inventory_max_entries: int = LIMITS["inventory_max_entries"],
    inventory_max_bytes: int = LIMITS["inventory_max_bytes"],
    inventory_timeout_seconds: int = LIMITS["inventory_timeout_seconds"],
) -> str:
    content = dxm_block(
        root,
        inventory_depth,
        inventory_max_entries=inventory_max_entries,
        inventory_max_bytes=inventory_max_bytes,
        inventory_timeout_seconds=inventory_timeout_seconds,
    )
    if dry_run:
        if force or not path.exists():
            return "would-create" if not force else "would-write"
        existing = read_existing_text(path)
        state = managed_block_state(existing, DXM_BLOCK_START, DXM_BLOCK_END)
        if state == "broken":
            raise BrokenManagedBlockError(path, DXM_BLOCK_START, DXM_BLOCK_END)
        if state == "complete":
            if refresh_blocks:
                return "would-refresh-managed-block"
            return "would-skip-existing"
        return "would-append-dxm-block"

    if force or not path.exists():
        write_text_lf(path, content)
        return "created" if not force else "written"

    existing = read_existing_text(path)
    state = managed_block_state(existing, DXM_BLOCK_START, DXM_BLOCK_END)
    if state == "broken":
        raise BrokenManagedBlockError(path, DXM_BLOCK_START, DXM_BLOCK_END)
    if state == "complete":
        if refresh_blocks:
            return refresh_managed_block(path, content, DXM_BLOCK_START, DXM_BLOCK_END)
        return "skipped-existing"

    updated = existing.rstrip("\n") + "\n\n" + content.rstrip("\n") + "\n"
    write_text_lf(path, updated)
    return "appended-dxm-block"


def append_block_once(
    path: Path,
    block: str,
    start_marker: str = TRELLIS_BLOCK_START,
    end_marker: str = TRELLIS_BLOCK_END,
    dry_run: bool = False,
    refresh_blocks: bool = False,
) -> str:
    if not path.exists():
        if dry_run:
            return "would-create"
        path.parent.mkdir(parents=True, exist_ok=True)
        write_text_lf(path, block)
        return "created"

    existing = read_existing_text(path)
    state = managed_block_state(existing, start_marker, end_marker)
    if state == "broken":
        raise BrokenManagedBlockError(path, start_marker, end_marker)
    if state == "complete":
        if refresh_blocks:
            updated = replace_block(existing, block, start_marker, end_marker)
            if updated is None or updated == existing:
                return "would-skip-existing" if dry_run else "skipped-existing"
            if dry_run:
                return "would-refresh-managed-block"
            write_text_lf(path, updated)
            return "refreshed-managed-block"
        return "skipped-existing"

    if dry_run:
        return "would-append-trellis-block"
    updated = existing.rstrip("\n") + "\n\n" + block.rstrip("\n") + "\n"
    write_text_lf(path, updated)
    return "appended-trellis-block"


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return parsed


def bounded_positive_int(maximum: int):
    def parse(value: str) -> int:
        parsed = positive_int(value)
        if parsed > maximum:
            raise argparse.ArgumentTypeError(f"must be <= {maximum}")
        return parsed

    return parse


def valid_trellis_user(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise argparse.ArgumentTypeError("must not be empty")
    if len(candidate) > LIMITS["trellis_user_max_length"]:
        raise argparse.ArgumentTypeError(
            f"must be <= {LIMITS['trellis_user_max_length']} characters"
        )
    if any(ord(character) < 32 or ord(character) == 127 for character in candidate):
        raise argparse.ArgumentTypeError("must not contain control characters")
    return candidate


def run_self_test() -> None:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="dxm-self-test-") as tmp:
        root = Path(tmp) / "project"
        results = scaffold(root, force=False, dry_run=False, refresh_blocks=False, trellis=False, inventory_depth=2)
        statuses = dict(results)
        for filename in FILES:
            path = root / filename
            if not path.exists():
                raise AssertionError(f"{filename} was not created")
            data = path.read_bytes()
            if b"\r\n" in data or b"\r" in data:
                raise AssertionError(f"{filename} does not use LF-only line endings")
            if statuses.get(filename) not in {"created", "appended-dxm-block"}:
                raise AssertionError(f"{filename} unexpected status: {statuses.get(filename)}")

        for filename in FILES:
            path = root / filename
            check_managed_blocks(path, path.read_text(encoding="utf-8"), scaffold_marker_pairs(filename))

        dry_root = Path(tmp) / "dry-run-project"
        dry_results = scaffold(dry_root, force=False, dry_run=True, refresh_blocks=False, trellis=False, inventory_depth=1)
        if dry_root.exists():
            raise AssertionError("--dry-run created the target root")
        if not all(status == "would-create" for _, status in dry_results):
            raise AssertionError("--dry-run did not report would-create for a new project")


def kill_process_tree(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return

    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            return
        except OSError:
            process.kill()
            return

    try:
        os.killpg(process.pid, signal.SIGKILL)
    except OSError:
        process.kill()


def run_trellis_init(root: Path, developer: str, timeout_seconds: int) -> tuple[str, str]:
    trellis_cmd = shutil.which("trellis")
    if not trellis_cmd:
        return ("missing-command", "trellis command not found on PATH")

    cmd = [trellis_cmd, "init", "--codex", "-u", developer, "-y", "--skip-existing"]
    popen_kwargs: dict[str, object] = {}
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    try:
        process = subprocess.Popen(
            cmd,
            cwd=root,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **popen_kwargs,
        )
    except OSError as exc:
        error_type = type(exc).__name__
        return (f"failed-launch-{error_type}", f"trellis init launch failed: {error_type}")
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        kill_process_tree(process)
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
        output = "\n".join(
            part
            for part in [
                (stdout or "").strip(),
                (stderr or "").strip(),
                f"trellis init timed out after {timeout_seconds}s",
            ]
            if part
        )
        return ("timeout", output)

    output = "\n".join(part for part in [(stdout or "").strip(), (stderr or "").strip()] if part)
    if process.returncode == 0:
        return ("initialized" if (root / ".trellis").is_dir() else "incomplete-no-trellis-dir", output)
    return (f"failed-exit-{process.returncode}", output)


_TRELLIS_ACTIVE_SCALAR_RE = re.compile(
    r"^session_auto_commit[ \t]*:[ \t]*(?P<value>[^#\r\n]*?)(?:[ \t]+#.*)?$"
)
_TRELLIS_COMMENTED_SCALAR_RE = re.compile(
    r"^#[ \t]*session_auto_commit[ \t]*:[ \t]*(?P<value>[^#\r\n]*?)(?:[ \t]+#.*)?$"
)
_TRELLIS_QUOTED_KEY_RE = re.compile(r"^[\"']session_auto_commit[\"'][ \t]*:")


def _trellis_boolean_scalar(value: str) -> bool:
    normalized = value.strip().casefold()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise TrellisConfigError(
        "Trellis config has a non-boolean top-level session_auto_commit value; use Trellis' official config command"
    )


def _normalize_trellis_session_auto_commit(existing: str) -> str:
    """Safely update only an unquoted top-level Boolean YAML scalar.

    DXM does not attempt to parse arbitrary YAML.  The adapter rejects quoted
    keys, aliases, block scalars, or any other unsupported shape instead of
    applying a broad regular-expression substitution.
    """

    lines = normalize_lf(existing).splitlines(keepends=True)
    active_indexes: list[int] = []
    commented_indexes: list[int] = []
    for index, line in enumerate(lines):
        raw = line.rstrip("\n")
        if raw.startswith((" ", "\t")):
            continue
        if _TRELLIS_QUOTED_KEY_RE.match(raw):
            raise TrellisConfigError(
                "Trellis config uses a quoted session_auto_commit key; use Trellis' official config command"
            )
        active = _TRELLIS_ACTIVE_SCALAR_RE.fullmatch(raw)
        if active is not None:
            _trellis_boolean_scalar(active.group("value"))
            active_indexes.append(index)
            continue
        commented = _TRELLIS_COMMENTED_SCALAR_RE.fullmatch(raw)
        if commented is not None:
            _trellis_boolean_scalar(commented.group("value"))
            commented_indexes.append(index)

    desired = "session_auto_commit: false\n"
    if active_indexes:
        first = active_indexes[0]
        lines[first] = desired
        for index in reversed(active_indexes[1:]):
            del lines[index]
        return "".join(lines)
    if commented_indexes:
        first = commented_indexes[0]
        lines[first] = desired
        for index in reversed(commented_indexes[1:]):
            del lines[index]
        return "".join(lines)
    return "".join(lines).rstrip("\n") + "\n\n" + desired


def _trellis_session_auto_commit_is_disabled(content: str) -> bool:
    active_values: list[bool] = []
    for line in normalize_lf(content).splitlines():
        if line.startswith((" ", "\t")):
            continue
        active = _TRELLIS_ACTIVE_SCALAR_RE.fullmatch(line)
        if active is not None:
            active_values.append(_trellis_boolean_scalar(active.group("value")))
    return active_values == [False]


def ensure_session_auto_commit_disabled(root: Path, dry_run: bool = False) -> str:
    config = root / ".trellis" / "config.yaml"
    if not config.exists():
        return "missing-config"

    existing = read_existing_text(config)
    updated = _normalize_trellis_session_auto_commit(existing)
    if not _trellis_session_auto_commit_is_disabled(updated):
        raise TrellisConfigError("Trellis config adapter could not verify session_auto_commit: false")
    if updated != existing:
        if dry_run:
            return "would-update"
        write_text_lf(config, updated)
        return "updated"
    return "skipped-existing"


def ensure_trellis_start_step0(root: Path, dry_run: bool = False, refresh_blocks: bool = False) -> str:
    path = root / ".agents" / "skills" / "trellis-start" / "SKILL.md"
    if not path.exists():
        return "missing-trellis-start-skill"
    return append_block_once(
        path,
        TRELLIS_START_STEP0_BLOCK,
        TRELLIS_START_STEP0_START,
        TRELLIS_START_STEP0_END,
        dry_run,
        refresh_blocks,
    )


def ensure_trellis_workflow_override(root: Path, dry_run: bool = False, refresh_blocks: bool = False) -> str:
    path = root / ".trellis" / "workflow.md"
    return append_block_once(
        path,
        TRELLIS_WORKFLOW_OVERRIDE_BLOCK,
        TRELLIS_WORKFLOW_OVERRIDE_START,
        TRELLIS_WORKFLOW_OVERRIDE_END,
        dry_run,
        refresh_blocks,
    )


def ensure_trellis_docs(root: Path, dry_run: bool = False, refresh_blocks: bool = False) -> list[tuple[str, str]]:
    return [
        ("AGENTS.md", append_block_once(root / "AGENTS.md", TRELLIS_AGENTS_BLOCK, dry_run=dry_run, refresh_blocks=refresh_blocks)),
        (
            "项目开发规范（AI协作）.md",
            append_block_once(root / "项目开发规范（AI协作）.md", TRELLIS_DEV_RULES_BLOCK, dry_run=dry_run, refresh_blocks=refresh_blocks),
        ),
        (
            "项目文件结构说明.md",
            append_block_once(root / "项目文件结构说明.md", TRELLIS_FILE_STRUCTURE_BLOCK, dry_run=dry_run, refresh_blocks=refresh_blocks),
        ),
        (
            "项目完整链路说明.md",
            append_block_once(root / "项目完整链路说明.md", TRELLIS_CHAIN_BLOCK, dry_run=dry_run, refresh_blocks=refresh_blocks),
        ),
    ]


def ensure_trellis_safety_overrides(root: Path, dry_run: bool = False, refresh_blocks: bool = False) -> list[tuple[str, str]]:
    return [
        (".trellis/config.yaml session_auto_commit", ensure_session_auto_commit_disabled(root, dry_run)),
        (".agents/skills/trellis-start/SKILL.md DXM Step 0", ensure_trellis_start_step0(root, dry_run, refresh_blocks)),
        (".trellis/workflow.md DXM no-task routing", ensure_trellis_workflow_override(root, dry_run, refresh_blocks)),
    ]


def planned_trellis_post_init_actions() -> list[tuple[str, str]]:
    return [
        ("AGENTS.md", "would-apply-after-trellis-init"),
        ("项目开发规范（AI协作）.md", "would-apply-after-trellis-init"),
        ("项目文件结构说明.md", "would-apply-after-trellis-init"),
        ("项目完整链路说明.md", "would-apply-after-trellis-init"),
        (".trellis/config.yaml session_auto_commit", "would-apply-after-trellis-init"),
        (".agents/skills/trellis-start/SKILL.md DXM Step 0", "would-apply-after-trellis-init"),
        (".trellis/workflow.md DXM no-task routing", "would-apply-after-trellis-init"),
    ]


def validate_trellis_update_inputs(root: Path) -> None:
    if not root.exists():
        return
    paths: list[tuple[Path, list[tuple[str, str]]]] = [
        (root / "AGENTS.md", scaffold_marker_pairs("AGENTS.md")),
        (root / "项目开发规范（AI协作）.md", scaffold_marker_pairs("项目开发规范（AI协作）.md")),
        (root / "项目文件结构说明.md", scaffold_marker_pairs("项目文件结构说明.md")),
        (root / "项目完整链路说明.md", scaffold_marker_pairs("项目完整链路说明.md")),
        (root / ".trellis" / "config.yaml", []),
        (root / ".agents" / "skills" / "trellis-start" / "SKILL.md", [(TRELLIS_START_STEP0_START, TRELLIS_START_STEP0_END)]),
        (root / ".trellis" / "workflow.md", [(TRELLIS_WORKFLOW_OVERRIDE_START, TRELLIS_WORKFLOW_OVERRIDE_END)]),
    ]
    for path, marker_pairs in paths:
        validate_managed_path(root, path)
        if path.exists():
            content = read_existing_text(path)
            check_managed_blocks(path, content, marker_pairs)


def validate_update_inputs(
    root: Path,
    force: bool,
    refresh_blocks: bool,
    trellis: bool = False,
    baseline: bool = False,
) -> None:
    if not root.exists():
        return
    for filename in FILES:
        path = root / filename
        validate_managed_path(root, path)
        if not path.exists():
            continue
        baseline_target = baseline and filename == "项目完整链路说明.md"
        if not force and (filename == "AGENTS.md" or refresh_blocks or trellis or baseline_target):
            content = read_existing_text(path)
            check_managed_blocks(path, content, scaffold_marker_pairs(filename))


def ensure_dxm_gitignore(root: Path, *, dry_run: bool = False) -> tuple[str, str] | None:
    """Guarantee a portable local-state ignore rule when the target is Git-backed.

    This never calls ``git rm --cached``: pre-existing tracked DXM state is a
    human ownership decision and is surfaced by the post-write audit instead.
    """

    if not root.exists():
        return None
    worktree = is_git_worktree(root)
    if worktree is False:
        return None
    if worktree is None:
        return (".gitignore DXM privacy", "git-privacy-unavailable")
    path = root / ".gitignore"
    validate_managed_path(root, path)
    existing = read_existing_text(path) if path.exists() else None
    desired, status = managed_gitignore_content(existing)
    if dry_run:
        if existing is None:
            status = "would-create"
        elif desired != existing:
            status = "would-append-managed-block" if "# DXM:START" not in existing else "would-refresh-managed-block"
        else:
            status = "would-skip-existing"
    elif desired != existing:
        write_text_lf(path, desired)
    return (".gitignore DXM privacy", status)


def scaffold(
    root: Path,
    force: bool,
    dry_run: bool = False,
    refresh_blocks: bool = False,
    trellis: bool = False,
    inventory_depth: int = 1,
    baseline: bool = False,
    *,
    inventory_max_entries: int = LIMITS["inventory_max_entries"],
    inventory_max_bytes: int = LIMITS["inventory_max_bytes"],
    inventory_timeout_seconds: int = LIMITS["inventory_timeout_seconds"],
) -> list[tuple[str, str]]:
    validate_update_inputs(root, force, refresh_blocks, trellis, baseline)
    if not dry_run:
        root.mkdir(parents=True, exist_ok=True)
    results: list[tuple[str, str]] = []
    for filename in FILES:
        target = root / filename
        content = render(
            read_template(filename),
            root,
            inventory_depth,
            inventory_max_entries=inventory_max_entries,
            inventory_max_bytes=inventory_max_bytes,
            inventory_timeout_seconds=inventory_timeout_seconds,
        )
        if filename == "AGENTS.md":
            status = ensure_agents(
                target,
                root,
                force,
                dry_run,
                refresh_blocks,
                inventory_depth,
                inventory_max_entries=inventory_max_entries,
                inventory_max_bytes=inventory_max_bytes,
                inventory_timeout_seconds=inventory_timeout_seconds,
            )
        elif dry_run:
            if force or not target.exists():
                status = "would-write" if force else "would-create"
            elif refresh_blocks:
                status = refresh_managed_block(target, content, DXM_DOC_BLOCK_START, DXM_DOC_BLOCK_END, dry_run=True)
            else:
                status = "would-skip-existing"
        elif target.exists() and not force:
            if refresh_blocks:
                status = refresh_managed_block(target, content, DXM_DOC_BLOCK_START, DXM_DOC_BLOCK_END)
            else:
                status = "skipped-existing"
        else:
            write_text_lf(target, content)
            status = "written" if force else "created"
        results.append((filename, status))
    gitignore_result = ensure_dxm_gitignore(root, dry_run=dry_run)
    if gitignore_result is not None:
        results.append(gitignore_result)
    return results


def canonical_json(data: dict[str, object]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def persist_project_baseline(
    root: Path,
    data: dict[str, object],
    *,
    dry_run: bool = False,
) -> list[tuple[str, str]]:
    """Persist the validated baseline and hydrate its dedicated chain-doc block."""

    baseline_path = root / ".dxm" / "project.json"
    validate_managed_path(root, baseline_path)
    validate_managed_path(root, root / "项目完整链路说明.md")
    desired_json = canonical_json(data)
    if baseline_path.exists():
        existing_json = read_existing_text(baseline_path)
        baseline_status = "would-skip-existing" if dry_run else "skipped-existing"
        if existing_json != desired_json:
            baseline_status = "would-update" if dry_run else "updated"
    else:
        baseline_status = "would-create" if dry_run else "created"

    if not dry_run and baseline_status != "skipped-existing":
        write_text_lf(baseline_path, desired_json)

    chain_path = root / "项目完整链路说明.md"
    block_status = append_block_once(
        chain_path,
        baseline_markdown(data),
        BASELINE_BLOCK_START,
        BASELINE_BLOCK_END,
        dry_run=dry_run,
        refresh_blocks=True,
    )
    status_aliases = {
        "would-append-trellis-block": "would-append-baseline-block",
        "appended-trellis-block": "appended-baseline-block",
    }
    return [
        (".dxm/project.json", baseline_status),
        ("项目完整链路说明.md project baseline", status_aliases.get(block_status, block_status)),
    ]


def refresh_project_baseline_block(
    root: Path,
    data: dict[str, object],
    *,
    dry_run: bool = False,
) -> list[tuple[str, str]]:
    """Refresh only the rendered baseline block from an existing local baseline."""

    chain_path = root / "项目完整链路说明.md"
    validate_managed_path(root, chain_path)
    block_status = append_block_once(
        chain_path,
        baseline_markdown(data),
        BASELINE_BLOCK_START,
        BASELINE_BLOCK_END,
        dry_run=dry_run,
        refresh_blocks=True,
    )
    status_aliases = {
        "would-append-trellis-block": "would-append-baseline-block",
        "appended-trellis-block": "appended-baseline-block",
    }
    return [("项目完整链路说明.md project baseline", status_aliases.get(block_status, block_status))]


def print_trellis_notes(trellis_output: str) -> None:
    if not trellis_output:
        return
    notable = [
        line
        for line in trellis_output.splitlines()
        if line.strip()
        and (
            "Mode:" in line
            or "Developer:" in line
            or "Configuring" in line
            or "Codex hooks" in line
            or "Created" in line
            or "Tracking" in line
            or "Error:" in line
            or "timed out" in line
            or "timeout" in line
            or "command not found" in line
        )
    ]
    if notable:
        print("Trellis notes:")
        for line in notable:
            print(f"  {line}")


def print_safe_update_error(
    exc: ExistingFileEncodingError | BrokenManagedBlockError | InvalidManagedBlockError | UnsafeManagedPathError,
) -> None:
    if isinstance(exc, UnsafeManagedPathError):
        print(f"Error: {exc.path} is an unsafe managed path: {exc.reason}.", file=sys.stderr)
        return
    if isinstance(exc, ExistingFileEncodingError):
        print(f"Error: {exc.path} is not valid UTF-8; convert it to UTF-8 before DXM can safely update it.", file=sys.stderr)
        return
    if isinstance(exc, BrokenManagedBlockError):
        print(
            f"Error: {exc.path} has incomplete managed block {exc.start_marker}; "
            f"restore the matching {exc.end_marker} before DXM can safely update it.",
            file=sys.stderr,
        )
        return
    print(
        f"Error: {exc.path} has invalid managed block {exc.start_marker}: "
        f"{'; '.join(exc.errors)}. Repair the marker layout before DXM can safely update it.",
        file=sys.stderr,
    )


def _result_counts(results: list[tuple[str, str]]) -> tuple[int, int]:
    written_statuses = {
        "created",
        "written",
        "updated",
        "refreshed-managed-block",
        "appended-managed-block",
        "appended-trellis-block",
        "appended-baseline-block",
    }
    written = sum(1 for _, status in results if status in written_statuses)
    skipped = sum(1 for _, status in results if "skip" in status)
    return written, skipped


def _visible_root(root: Path, redact_paths: bool) -> str:
    return "$PROJECT_ROOT" if redact_paths else str(root)


def _emit_payload(args: argparse.Namespace, payload: dict[str, object], *, stderr: bool = False) -> None:
    if args.output == "json":
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    elif stderr:
        print(f"Error: {payload['summary']}", file=sys.stderr)


def _emit_failure(
    args: argparse.Namespace,
    *,
    code: str,
    summary: str,
    exit_code: int = EXIT_INVALID,
    root: Path | None = None,
) -> int:
    payload: dict[str, object] = {
        "operation": "recover" if args.recover else (args.mode or "unknown"),
        "operation_status": "failed",
        "readiness": "NOT_EVALUATED",
        "readiness_exit_code": None,
        "exit_code": exit_code,
        "issues": [summary],
        "error_code": code,
        "summary": summary,
    }
    if root is not None:
        payload["root"] = _visible_root(root, args.redact_paths)
    _emit_payload(args, payload, stderr=True)
    return exit_code


def _emit_scaffold_result(
    args: argparse.Namespace,
    root: Path,
    results: list[tuple[str, str]],
    audit: object | None,
    trellis_exit: int,
    trellis_output: str,
) -> int:
    readiness = "NOT_EVALUATED"
    readiness_exit_code: int | None = None
    issues: list[str] = []
    if audit is not None and args.mode != "scaffold-only":
        readiness = PARTIAL if trellis_exit and audit.state == READY else audit.state
        readiness_exit_code = audit.exit_code if readiness == audit.state else EXIT_PARTIAL
        issues = list(audit.issues)
        if trellis_exit and readiness == PARTIAL and not issues:
            issues.append("explicit Trellis initialization did not complete successfully")
    if trellis_exit in {EXIT_TRELLIS_UNAVAILABLE, EXIT_TRELLIS_FAILED}:
        exit_code = trellis_exit
    elif args.dry_run or args.mode == "scaffold-only":
        exit_code = 0
    else:
        assert readiness_exit_code is not None
        exit_code = readiness_exit_code
    files_written, files_skipped = _result_counts(results)
    payload: dict[str, object] = {
        "operation": args.mode,
        "operation_status": "completed",
        "root": _visible_root(root, args.redact_paths),
        "readiness": readiness,
        "readiness_exit_code": readiness_exit_code,
        "exit_code": exit_code,
        "files_written": files_written,
        "files_skipped": files_skipped,
        "results": [{"target": target, "status": status} for target, status in results],
        "issues": issues,
        "error_code": None,
    }
    if args.output == "json":
        _emit_payload(args, payload)
    else:
        print(f"DXM scaffold root: {_visible_root(root, args.redact_paths)}")
        print(f"DXM workflow mode: {args.mode}")
        for filename, status in results:
            print(f"- {status}: {filename}")
        print_trellis_notes(trellis_output)
        if args.dry_run:
            print("DXM scaffold result: DRY_RUN")
            print("DXM readiness: NOT_EVALUATED")
        elif args.mode == "scaffold-only":
            print("DXM scaffold result: SCAFFOLD_ONLY")
            print("DXM readiness: NOT_EVALUATED")
            print("Scaffold-only completed; no project readiness claim was made.")
        else:
            print(f"DXM scaffold status: {readiness}")
            for issue in issues:
                print(f"  - {issue}")
            if readiness == READY:
                print("Next: read AGENTS.md, then obey the generated project docs for all future work in this folder.")
            else:
                print("Next action: resolve the listed readiness gaps; DXM has not claimed READY.")

    if trellis_exit == EXIT_TRELLIS_UNAVAILABLE:
        if args.output != "json":
            print("DXM_SCAFFOLDED_TRELLIS_UNAVAILABLE")
        return exit_code
    if trellis_exit == EXIT_TRELLIS_FAILED:
        if args.output != "json":
            print("DXM_SCAFFOLDED_TRELLIS_FAILED")
        return exit_code
    return exit_code


def _run_recovery(args: argparse.Namespace, root: Path) -> int:
    if not root.is_dir():
        return _emit_failure(
            args,
            code=ERROR_RECOVERY_REQUIRED,
            summary="recovery requires an existing project directory",
            root=root,
        )
    try:
        recovered = recover_transactions(root, break_stale_lock=args.break_stale_lock)
    except DxmIoError as exc:
        if args.debug and exc.cause is not None:
            traceback.print_exception(exc.cause, file=sys.stderr)
        return _emit_failure(args, code=exc.code, summary=exc.summary, root=root)
    audit = audit_project(root, require_trellis=False)
    payload = {
        "operation": "recover",
        "operation_status": "completed",
        "root": _visible_root(root, args.redact_paths),
        "recovered_transactions": recovered,
        "readiness": audit.state,
        "readiness_exit_code": audit.exit_code,
        "exit_code": audit.exit_code,
        "issues": list(audit.issues),
        "error_code": None,
    }
    if args.output == "json":
        _emit_payload(args, payload)
    else:
        print(f"DXM recovery root: {_visible_root(root, args.redact_paths)}")
        print(f"DXM recovery transactions: {recovered}")
        print(f"DXM readiness: {audit.state}")
        for issue in audit.issues:
            print(f"  - {issue}")
    return audit.exit_code


def _json_requested(arguments: list[str]) -> bool:
    for index, argument in enumerate(arguments):
        if argument == "--json" or argument == "--output=json":
            return True
        if argument == "--output" and index + 1 < len(arguments) and arguments[index + 1] == "json":
            return True
    return False


def _argument_error_operation(arguments: list[str]) -> str:
    if "--recover" in arguments:
        return "recover"
    for index, argument in enumerate(arguments):
        value: str | None = None
        if argument == "--mode" and index + 1 < len(arguments):
            value = arguments[index + 1]
        elif argument.startswith("--mode="):
            value = argument.partition("=")[2]
        if value in {"init", "scaffold-only"}:
            return value
    return "unknown"


class DxmArgumentParser(argparse.ArgumentParser):
    """Keep requested JSON output machine-readable even for parse failures."""

    def __init__(self, *args: object, json_requested: bool = False, **kwargs: object) -> None:
        self._json_requested = json_requested
        super().__init__(*args, **kwargs)

    def error(self, _message: str) -> None:
        if self._json_requested:
            payload = {
                "operation": _argument_error_operation(sys.argv[1:]),
                "operation_status": "failed",
                "readiness": "NOT_EVALUATED",
                "readiness_exit_code": None,
                "exit_code": EXIT_INVALID,
                "issues": ["invalid DXM CLI arguments"],
                "error_code": "DXM_E_INVALID_ARGUMENTS",
                "summary": "invalid DXM CLI arguments",
            }
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            raise SystemExit(EXIT_INVALID)
        super().error(_message)


def main() -> int:
    parser = DxmArgumentParser(
        description="DXM v2 scaffold and recovery CLI",
        json_requested=_json_requested(sys.argv[1:]),
    )
    parser.add_argument("--root", default=os.getcwd(), help="target project root; defaults to current directory")
    parser.add_argument(
        "--mode",
        choices=("init", "scaffold-only"),
        help="required DXM v2 write mode; init requires --baseline and scaffold-only forbids it",
    )
    parser.add_argument("--force", action="store_true", help="overwrite existing files; use only on explicit user request")
    parser.add_argument("--dry-run", action="store_true", help="report planned scaffold actions without writing files")
    parser.add_argument("--refresh-blocks", action="store_true", help="refresh DXM/Trellis-managed marker blocks while preserving manual content")
    parser.add_argument(
        "--baseline",
        type=Path,
        help="validated project baseline JSON to persist as .dxm/project.json and hydrate into the chain document",
    )
    parser.add_argument(
        "--inventory-depth",
        type=bounded_positive_int(LIMITS["inventory_max_depth"]),
        default=1,
        help=f"maximum directory depth for the safe inventory (1-{LIMITS['inventory_max_depth']})",
    )
    parser.add_argument("--self-test", action="store_true", help="run packaged DXM scaffold smoke checks and exit")
    parser.add_argument("--recover", action="store_true", help="recover interrupted local DXM transactions; does not scaffold")
    parser.add_argument("--break-stale-lock", action="store_true", help="allow --recover to clear a verified stale project lock")
    parser.add_argument("--allow-broad-root", action="store_true", help="allow scaffolding in a drive, home, system, vendor, or build root")
    parser.add_argument("--trellis", action="store_true", help="also initialize Trellis/Codex big-development workflow")
    parser.add_argument(
        "--trellis-user",
        type=valid_trellis_user,
        default=os.environ.get("USERNAME") or os.environ.get("USER") or "developer",
        help="bounded developer name passed to trellis init when --trellis is used",
    )
    parser.add_argument(
        "--trellis-timeout-seconds",
        type=bounded_positive_int(LIMITS["trellis_timeout_max_seconds"]),
        default=120,
        help=f"maximum seconds to wait for Trellis init (1-{LIMITS['trellis_timeout_max_seconds']})",
    )
    parser.add_argument("--output", choices=("text", "json"), default="text", help="result format")
    parser.add_argument("--json", dest="output", action="store_const", const="json", help="alias for --output json")
    parser.add_argument("--redact-paths", action="store_true", help="replace root paths in result output with $PROJECT_ROOT")
    parser.add_argument("--debug", action="store_true", help="print a chained traceback for unexpected local failures")
    args = parser.parse_args()

    if args.self_test:
        if args.mode is not None or args.recover:
            return _emit_failure(args, code="DXM_E_INVALID_ARGUMENTS", summary="--self-test cannot be combined with write or recovery modes")
        try:
            run_self_test()
        except AssertionError as exc:
            return _emit_failure(args, code="DXM_E_SELF_TEST_FAILED", summary=str(exc))
        if args.output == "json":
            _emit_payload(args, {"operation": "self-test", "operation_status": "completed", "error_code": None})
        else:
            print("DXM self-test OK")
        return 0

    root = Path(args.root).resolve()
    if args.recover:
        if args.mode is not None or args.baseline is not None or args.dry_run or args.trellis:
            return _emit_failure(args, code="DXM_E_INVALID_ARGUMENTS", summary="--recover cannot be combined with scaffold options", root=root)
        return _run_recovery(args, root)
    if args.mode is None:
        return _emit_failure(args, code="DXM_E_MODE_REQUIRED", summary="DXM v2 requires an explicit --mode", root=root)
    if args.mode == "init" and args.baseline is None:
        return _emit_failure(args, code="DXM_E_BASELINE_REQUIRED", summary="--mode init requires --baseline before any project write", root=root)
    if args.mode == "scaffold-only" and args.baseline is not None:
        return _emit_failure(args, code="DXM_E_INVALID_ARGUMENTS", summary="--mode scaffold-only cannot accept --baseline or establish readiness", root=root)

    baseline_data: dict[str, object] | None = None
    refresh_existing_baseline = False
    results: list[tuple[str, str]] = []
    trellis_output = ""
    trellis_exit = 0
    try:
        validate_project_root(root, args.allow_broad_root)
        if args.baseline is not None:
            baseline_data = load_baseline(args.baseline, expected_root=root)
            existing_baseline = root / ".dxm" / "project.json"
            if root.exists():
                validate_managed_path(root, existing_baseline)
            if existing_baseline.exists():
                read_existing_text(existing_baseline)
        elif args.refresh_blocks:
            existing_baseline = root / ".dxm" / "project.json"
            if existing_baseline.exists():
                baseline_data = load_baseline(
                    existing_baseline,
                    expected_root=root,
                    require_trusted_path=True,
                )
                refresh_existing_baseline = True
        if args.trellis:
            validate_trellis_update_inputs(root)
        if root.exists():
            validate_managed_path(root, root / ".dxm" / "locks" / "project.lock")
            validate_managed_path(root, root / ".dxm" / "transactions" / "preflight.json")
        if pending_transaction_states(root):
            raise DxmIoError(ERROR_RECOVERY_REQUIRED, "an interrupted DXM transaction requires --recover before a new write")

        if args.dry_run:
            results = scaffold(
                root,
                args.force,
                True,
                args.refresh_blocks,
                args.trellis,
                args.inventory_depth,
                baseline=baseline_data is not None,
            )
            if baseline_data is not None:
                if refresh_existing_baseline:
                    results.extend(refresh_project_baseline_block(root, baseline_data, dry_run=True))
                else:
                    results.extend(persist_project_baseline(root, baseline_data, dry_run=True))
        else:
            global _ACTIVE_TRANSACTION
            with ProjectLock(root, args.mode):
                if pending_transaction_states(root):
                    raise DxmIoError(ERROR_RECOVERY_REQUIRED, "an interrupted DXM transaction requires --recover before a new write")
                transaction = ProjectTransaction(root, args.mode)
                _ACTIVE_TRANSACTION = transaction
                try:
                    results = scaffold(
                        root,
                        args.force,
                        False,
                        args.refresh_blocks,
                        args.trellis,
                        args.inventory_depth,
                        baseline=baseline_data is not None,
                    )
                    if baseline_data is not None:
                        if refresh_existing_baseline:
                            results.extend(refresh_project_baseline_block(root, baseline_data, dry_run=False))
                        else:
                            results.extend(persist_project_baseline(root, baseline_data, dry_run=False))

                    if args.trellis:
                        if (root / ".trellis").is_dir():
                            status, trellis_output = ("already-present", "")
                        else:
                            status, trellis_output = run_trellis_init(root, args.trellis_user, args.trellis_timeout_seconds)
                        if status == "missing-command":
                            trellis_exit = EXIT_TRELLIS_UNAVAILABLE
                        elif status in {"timeout", "incomplete-no-trellis-dir"} or status.startswith(("failed-exit-", "failed-launch-")):
                            trellis_exit = EXIT_TRELLIS_FAILED
                        results.append(("trellis init --codex", status))
                        if (root / ".trellis").exists():
                            validate_trellis_update_inputs(root)
                            results.extend(ensure_trellis_docs(root, refresh_blocks=args.refresh_blocks))
                            results.extend(ensure_trellis_safety_overrides(root, refresh_blocks=args.refresh_blocks))
                    transaction.commit()
                except BaseException:
                    try:
                        transaction.rollback()
                    finally:
                        _ACTIVE_TRANSACTION = None
                    raise
                _ACTIVE_TRANSACTION = None

        if args.dry_run and args.trellis:
            status, trellis_output = ("would-run", "")
            results.append(("trellis init --codex", status))
            if (root / ".trellis").exists():
                results.extend(ensure_trellis_docs(root, dry_run=True, refresh_blocks=args.refresh_blocks))
                results.extend(ensure_trellis_safety_overrides(root, dry_run=True, refresh_blocks=args.refresh_blocks))
            else:
                results.extend(planned_trellis_post_init_actions())
    except (
        ExistingFileEncodingError,
        BrokenManagedBlockError,
        InvalidManagedBlockError,
        UnsafeManagedPathError,
        TrellisConfigError,
    ) as exc:
        return _emit_failure(args, code="DXM_E_UNSAFE_UPDATE", summary=str(exc), root=root)
    except GitPrivacyError as exc:
        return _emit_failure(args, code="DXM_E_GITIGNORE_INVALID", summary=str(exc), root=root)
    except ContractError as exc:
        return _emit_failure(args, code="DXM_E_INVALID_BASELINE", summary="invalid DXM baseline: " + "; ".join(exc.errors), root=root)
    except UnsafeProjectRootError as exc:
        return _emit_failure(args, code="DXM_E_UNSAFE_ROOT", summary=f"{exc.root} is too broad for DXM scaffold; choose a project root or pass --allow-broad-root explicitly", root=root)
    except ProjectRootNotDirectoryError as exc:
        detail = "" if exc.blocker == exc.root else f" Existing ancestor {exc.blocker} is not a directory."
        return _emit_failure(args, code="DXM_E_ROOT_NOT_DIRECTORY", summary=f"{exc.root} project root must be a directory.{detail}", root=root)
    except DxmIoError as exc:
        if args.debug and exc.cause is not None:
            traceback.print_exception(exc.cause, file=sys.stderr)
        return _emit_failure(args, code=exc.code, summary=exc.summary, root=root)
    except OSError as exc:
        if args.debug:
            traceback.print_exception(exc, file=sys.stderr)
        return _emit_failure(args, code=ERROR_WRITE_FAILED, summary="an unexpected local filesystem operation failed", root=root)

    audit = None
    if not args.dry_run and (args.mode == "init" or args.trellis):
        base_audit = audit_project(root, require_trellis=False)
        audit = audit_project(root, require_trellis=args.trellis)
        if args.trellis and trellis_exit == 0:
            base_issues = set(base_audit.issues)
            trellis_only_issues = [issue for issue in audit.issues if issue not in base_issues]
            if trellis_only_issues:
                trellis_exit = EXIT_TRELLIS_FAILED
                results.append(("trellis integration audit", "incomplete"))
    return _emit_scaffold_result(args, root, results, audit, trellis_exit, trellis_output)


if __name__ == "__main__":
    raise SystemExit(main())
