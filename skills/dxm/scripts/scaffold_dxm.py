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

EXIT_INVALID = 2
EXIT_TRELLIS_UNAVAILABLE = 3
EXIT_TRELLIS_FAILED = 4

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

- 小修、只读排查、单点 bug、轻量文档调整：默认按 DXM inline 处理，不强制创建 Trellis task。
- 新功能、架构变化、跨多文件重构、长周期任务：先用 DXM core 做本地证据优先、单批 0–3 个阻塞问题的有界 project-grill；用户已批准 Trellis 时，再把结论落到 `.trellis/tasks/<task>/prd.md`。
- `grill-with-docs` 可在已安装且任务描述匹配时用于已有代码/文档的有界查证，但仍必须遵守单批 0–3 个阻塞问题；full `grilling` / legacy `grill-me` 只有用户 explicit opt-in 完整/穷举澄清时才调用。它们都不是 Trellis 硬依赖。
- 提问前从第一性原理判断真实目标、硬约束、本地可查事实和仍阻塞的问题，并质疑隐藏假设、过度方案、伪约束和用户给出的实现偏置；本地可查事实不得反问。
- 用户明确说 `scaffold only`、`先别问`、`只分析` 时，不进入 Trellis，不擅自改文件。
- 每次 Trellis 任务完成前必须执行对抗性检查；发现阻断问题就回到 implement/check。通过后把最终 `check.md` 的文件首个非空行写成顶格独立且全文唯一的 `<!-- DXM-CHECK:PASS -->`，不得存在其他或未闭合 `DXM-CHECK` 片段，再按 `finish` → `archive <task> --no-commit` → 归档目录 completion receipt 校验收口。
- Trellis 不得自动 stage/commit/push/PR；提交和推送仍需用户明确授权。

{TRELLIS_BLOCK_END}
"""

TRELLIS_DEV_RULES_BLOCK = f"""{TRELLIS_BLOCK_START}

## DXM + Trellis 协作规则

Trellis 只用于中大型开发任务的 PRD、任务状态和检查沉淀。默认路由：

| 场景 | 默认处理 |
| --- | --- |
| 只分析 / 先看看 | 只读，不建 task |
| 小修 / 单点 bug / 单文件文档调整 | DXM inline，不建 task |
| 新功能 / 多模块 / 架构 / 跨文件 / 长周期 | DXM core 有界 project-grill；获准后建 Trellis task |
| 需求不清楚但会继续开发 | 先查本地证据并单批问 0–3 个阻塞问题；匹配时可用有界 `grill-with-docs`，full `grilling` 仅 explicit opt-in |
| 用户明确 scaffold only / 先别问 | 只 scaffold，不 grill，不建 task |

启用 Trellis 时必须保持 `session_auto_commit: false`，并遵守本项目 Git/PR 授权规则。
每次需求澄清先从第一性原理出发并质疑隐藏假设，本地证据优先、单批 0–3 个阻塞问题；每次 Trellis 任务完成后先做对抗性检查，最终 `check.md` 的文件首个非空行必须是顶格独立且全文唯一的 `<!-- DXM-CHECK:PASS -->`，不得存在其他或未闭合 `DXM-CHECK` 片段，再按 `finish` → `archive <task> --no-commit` → 归档回执校验收口。

{TRELLIS_BLOCK_END}
"""

TRELLIS_FILE_STRUCTURE_BLOCK = f"""{TRELLIS_BLOCK_START}

## DXM 大开发工作流目录

本项目启用 Trellis/Codex 大开发工作流时，下列目录属于项目级 AI 协作基础设施：

- `.trellis/`：Trellis 项目工作流状态、任务 PRD、spec、workspace journal 和脚本。
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
3. 把结论写入 `.trellis/tasks/<task>/prd.md`，不能只停留在聊天上下文里。
4. 用 `.trellis/scripts/task.py start <task>` 进入 Trellis active task。
5. 按 Trellis 的 implement/check/update-spec 节奏开发、验证、沉淀规范。
6. 任务完成后执行对抗性检查，挑战需求偏差、隐藏假设、负路径、架构边界、测试、文档、敏感信息、乱码和回滚/恢复。
7. 对抗性检查通过后同步 DXM 长期文档；不能只更新 `.trellis/` 内部状态。
8. 先把最终 `check.md` 的文件首个非空行写成顶格独立且全文唯一的 `<!-- DXM-CHECK:PASS -->`，不得存在其他或未闭合 `DXM-CHECK` 片段；再执行 `finish` 和 `archive <task> --no-commit`，在 `.trellis/tasks/archive/<YYYY-MM>/<task>/completion.json` 生成并校验回执；归档前不得预写 `finished: true`。

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
Before asking requirements, reason from first principles（第一性原理）, inspect local evidence first, and ask one batch of 0–3 blocking questions. A matching installed `grill-with-docs` may support the same bounded flow; full `grilling` requires explicit opt-in. After a Trellis task completion, run an adversarial check（对抗性检查）, make exactly one `<!-- DXM-CHECK:PASS -->` fragment the first non-empty, column-zero standalone line in the final `check.md`, reject any other or unclosed `DXM-CHECK` fragment, then `finish`, `archive <task> --no-commit`, and validate the archived completion receipt.

{TRELLIS_START_STEP0_END}
"""

TRELLIS_WORKFLOW_OVERRIDE_BLOCK = f"""{TRELLIS_WORKFLOW_OVERRIDE_START}

## DXM no-task routing override

When no Trellis task is active, use DXM routing instead of forcing a task for every change:

- 只读排查、解释、日志查看、普通小修、单点 bug、轻量文档调整：可以按 DXM inline 完成，不要求创建 Trellis task。
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


def normalize_lf(content: str) -> str:
    return content.replace("\r\n", "\n").replace("\r", "\n")


def read_existing_text(path: Path) -> str:
    try:
        return normalize_lf(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise ExistingFileEncodingError(path) from exc


def write_text_lf(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(normalize_lf(content))


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


def project_inventory(root: Path, depth: int = 1) -> str:
    if not root.exists():
        return "- 当前目录尚不存在；实际 scaffold 会先创建项目根目录。"

    lines: list[str] = []

    def visit(directory: Path, current_depth: int, prefix: str = "") -> None:
        for child in sorted(directory.iterdir(), key=lambda p: p.name.lower()):
            name = child.name
            display = f"{prefix}{name}"
            if is_reparse_or_symlink(child):
                lines.append(f"- `{display}`：链接或重解析点；为保持 root/scope lock，不展开。")
                continue
            if name in SKIP_DIRS:
                lines.append(f"- `{display}/`：依赖、构建或工具目录；通常不展开维护。")
                continue
            if is_sensitive_name(name, is_file=child.is_file()):
                suffix = "/" if child.is_dir() else ""
                lines.append(f"- `{display}{suffix}`：运行态或敏感数据；只说明用途，不回显真实内容。")
                continue
            suffix = "/" if child.is_dir() else ""
            if child.is_dir():
                lines.append(f"- `{display}/`：项目目录；首次 /dxm 生成后需要补充职责说明。")
                if current_depth < depth:
                    visit(child, current_depth + 1, f"{display}/")
            else:
                lines.append(f"- `{display}`：项目文件；首次 /dxm 生成后需要补充职责说明。")

    visit(root, 1)
    return "\n".join(lines) if lines else "- 当前目录为空；开始开发前补充文件结构。"


def render(content: str, root: Path, inventory_depth: int = 1) -> str:
    return (
        content.replace("{{project_name}}", root.name)
        .replace("{{generated_date}}", datetime.now().strftime("%Y-%m-%d"))
        .replace("{{file_inventory}}", project_inventory(root, inventory_depth))
    )


def dxm_block(root: Path, inventory_depth: int = 1) -> str:
    return render(read_template("AGENTS.md"), root, inventory_depth)


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
) -> str:
    content = dxm_block(root, inventory_depth)
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


def ensure_session_auto_commit_disabled(root: Path, dry_run: bool = False) -> str:
    config = root / ".trellis" / "config.yaml"
    if not config.exists():
        return "missing-config"

    existing = read_existing_text(config)
    desired = "session_auto_commit: false"
    # Horizontal-whitespace-only anchors: \s would match newlines in (?m) mode and
    # swallow a preceding blank line, breaking idempotency on repeated runs.
    active_re = re.compile(r"(?m)^session_auto_commit[^\S\n]*:[^\S\n]*.*$")
    commented_re = re.compile(r"(?m)^#[^\S\n]*session_auto_commit[^\S\n]*:.*$")
    if active_re.search(existing):
        seen_active = False

        def collapse_active(_match: re.Match[str]) -> str:
            nonlocal seen_active
            if seen_active:
                return ""
            seen_active = True
            return desired

        updated = active_re.sub(collapse_active, existing)
    elif commented_re.search(existing):
        # Trellis ships the key commented out (`# session_auto_commit: true`);
        # uncomment in place instead of appending a contradictory duplicate.
        updated = commented_re.sub(desired, existing, count=1)
    else:
        updated = existing.rstrip("\n") + "\n\n" + desired + "\n"
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


def scaffold(
    root: Path,
    force: bool,
    dry_run: bool = False,
    refresh_blocks: bool = False,
    trellis: bool = False,
    inventory_depth: int = 1,
    baseline: bool = False,
) -> list[tuple[str, str]]:
    validate_update_inputs(root, force, refresh_blocks, trellis, baseline)
    if not dry_run:
        root.mkdir(parents=True, exist_ok=True)
    results: list[tuple[str, str]] = []
    for filename in FILES:
        target = root / filename
        content = render(read_template(filename), root, inventory_depth)
        if filename == "AGENTS.md":
            status = ensure_agents(target, root, force, dry_run, refresh_blocks, inventory_depth)
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold DXM AI collaboration files")
    parser.add_argument("--root", default=os.getcwd(), help="target project root; defaults to current directory")
    parser.add_argument(
        "--mode",
        choices=("init", "scaffold-only"),
        help="lock the scaffold write mode; init requires --baseline, scaffold-only forbids it",
    )
    parser.add_argument("--force", action="store_true", help="overwrite existing files; use only on explicit user request")
    parser.add_argument("--dry-run", action="store_true", help="report planned scaffold actions without writing files")
    parser.add_argument("--refresh-blocks", action="store_true", help="refresh DXM/Trellis-managed marker blocks while preserving manual content")
    parser.add_argument(
        "--baseline",
        type=Path,
        help="validated project baseline JSON to persist as .dxm/project.json and hydrate into the chain document",
    )
    parser.add_argument("--inventory-depth", type=positive_int, default=1, help="maximum directory depth to include in the generated file inventory")
    parser.add_argument("--self-test", action="store_true", help="run packaged DXM scaffold smoke checks and exit")
    parser.add_argument("--allow-broad-root", action="store_true", help="allow scaffolding in a drive, home, system, vendor, or build root")
    parser.add_argument("--trellis", action="store_true", help="also initialize Trellis/Codex big-development workflow")
    parser.add_argument(
        "--trellis-user",
        default=os.environ.get("USERNAME") or os.environ.get("USER") or "developer",
        help="developer name passed to trellis init when --trellis is used",
    )
    parser.add_argument(
        "--trellis-timeout-seconds",
        type=int,
        default=120,
        help="maximum seconds to wait for trellis init when --trellis is used",
    )
    args = parser.parse_args()

    if args.self_test:
        try:
            run_self_test()
        except AssertionError as exc:
            print(f"DXM self-test FAILED: {exc}", file=sys.stderr)
            return 2
        print("DXM self-test OK")
        return 0

    if args.mode == "init" and args.baseline is None:
        print("Error: --mode init requires --baseline before any project write.", file=sys.stderr)
        return EXIT_INVALID
    if args.mode == "scaffold-only" and args.baseline is not None:
        print("Error: --mode scaffold-only cannot accept --baseline or establish readiness.", file=sys.stderr)
        return EXIT_INVALID

    root = Path(args.root).resolve()
    baseline_data: dict[str, object] | None = None
    try:
        validate_project_root(root, args.allow_broad_root)
        if args.baseline is not None:
            baseline_data = load_baseline(args.baseline, expected_root=root)
            existing_baseline = root / ".dxm" / "project.json"
            if root.exists():
                validate_managed_path(root, existing_baseline)
            if existing_baseline.exists():
                # Validate readability before scaffold creates or refreshes any
                # project documents, preserving the preflight transaction boundary.
                read_existing_text(existing_baseline)
        if args.trellis:
            validate_trellis_update_inputs(root)
        results = scaffold(
            root,
            args.force,
            args.dry_run,
            args.refresh_blocks,
            args.trellis,
            args.inventory_depth,
            baseline=baseline_data is not None,
        )
        if baseline_data is not None:
            results.extend(persist_project_baseline(root, baseline_data, dry_run=args.dry_run))
    except (ExistingFileEncodingError, BrokenManagedBlockError, InvalidManagedBlockError, UnsafeManagedPathError) as exc:
        print_safe_update_error(exc)
        return EXIT_INVALID
    except ContractError as exc:
        print(f"Error: invalid DXM baseline: {'; '.join(exc.errors)}", file=sys.stderr)
        return EXIT_INVALID
    except UnsafeProjectRootError as exc:
        print(f"Error: {exc.root} is too broad for DXM scaffold; choose a project root or pass --allow-broad-root explicitly.", file=sys.stderr)
        return EXIT_INVALID
    except ProjectRootNotDirectoryError as exc:
        detail = "" if exc.blocker == exc.root else f" Existing ancestor {exc.blocker} is not a directory."
        print(f"Error: {exc.root} project root must be a directory.{detail}", file=sys.stderr)
        return EXIT_INVALID

    trellis_output = ""
    trellis_exit = 0
    if args.trellis:
        if args.dry_run:
            status, trellis_output = ("would-run", "")
        elif (root / ".trellis").is_dir():
            status, trellis_output = ("already-present", "")
        else:
            status, trellis_output = run_trellis_init(root, args.trellis_user, args.trellis_timeout_seconds)
        if status == "missing-command":
            trellis_exit = EXIT_TRELLIS_UNAVAILABLE
        elif status in {"timeout", "incomplete-no-trellis-dir"} or status.startswith(("failed-exit-", "failed-launch-")):
            trellis_exit = EXIT_TRELLIS_FAILED
        results.append(("trellis init --codex", status))
        if args.dry_run and (root / ".trellis").exists():
            try:
                results.extend(ensure_trellis_docs(root, dry_run=True, refresh_blocks=args.refresh_blocks))
                results.extend(ensure_trellis_safety_overrides(root, dry_run=True, refresh_blocks=args.refresh_blocks))
            except (ExistingFileEncodingError, BrokenManagedBlockError, InvalidManagedBlockError, UnsafeManagedPathError) as exc:
                print_safe_update_error(exc)
                return EXIT_INVALID
        elif args.dry_run:
            results.extend(planned_trellis_post_init_actions())
        if not args.dry_run and (root / ".trellis").exists():
            try:
                validate_trellis_update_inputs(root)
                results.extend(ensure_trellis_docs(root, refresh_blocks=args.refresh_blocks))
                results.extend(ensure_trellis_safety_overrides(root, refresh_blocks=args.refresh_blocks))
            except (ExistingFileEncodingError, BrokenManagedBlockError, InvalidManagedBlockError, UnsafeManagedPathError) as exc:
                print_safe_update_error(exc)
                return EXIT_INVALID

    audit = None
    if not args.dry_run:
        base_audit = audit_project(root, require_trellis=False)
        audit = audit_project(root, require_trellis=args.trellis)
        if args.trellis and trellis_exit == 0:
            base_issues = set(base_audit.issues)
            trellis_only_issues = [issue for issue in audit.issues if issue not in base_issues]
            if trellis_only_issues:
                trellis_exit = EXIT_TRELLIS_FAILED
                results.append(("trellis integration audit", "incomplete"))

    print(f"DXM scaffold root: {root}")
    print(f"DXM workflow mode: {args.mode or 'legacy-compatible'}")
    for filename, status in results:
        print(f"- {status}: {filename}")
    print_trellis_notes(trellis_output)
    if args.dry_run:
        print("DXM scaffold result: DRY_RUN")
        print("DXM readiness: NOT_EVALUATED")
    elif args.mode == "scaffold-only":
        print("DXM scaffold result: SCAFFOLD_ONLY")
        print("DXM readiness: NOT_EVALUATED")
    else:
        assert audit is not None
        display_state = PARTIAL if trellis_exit and audit.state == READY else audit.state
        print(f"DXM scaffold status: {display_state}")
        for issue in audit.issues:
            print(f"  - {issue}")
        if trellis_exit and display_state == PARTIAL and not audit.issues:
            print("  - explicit Trellis initialization did not complete successfully")

    if trellis_exit == EXIT_TRELLIS_UNAVAILABLE:
        print("DXM_SCAFFOLDED_TRELLIS_UNAVAILABLE")
        return trellis_exit
    if trellis_exit == EXIT_TRELLIS_FAILED:
        print("DXM_SCAFFOLDED_TRELLIS_FAILED")
        return trellis_exit

    if not args.dry_run and args.mode != "scaffold-only" and audit.state == READY:
        print("Next: read AGENTS.md, then obey the generated project docs for all future work in this folder.")
    elif not args.dry_run and args.mode != "scaffold-only" and audit.state in {PARTIAL, BROKEN}:
        print("Next action: resolve the listed readiness gaps; DXM has not claimed READY.")
    elif not args.dry_run and args.mode == "scaffold-only":
        print("Scaffold-only completed; no project readiness claim was made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
