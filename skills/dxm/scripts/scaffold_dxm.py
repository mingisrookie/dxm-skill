#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scaffold DXM large-project AI collaboration files into a project root."""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import signal
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

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

SKIP_DIRS = {".git", "node_modules", "dist", "build", "coverage", ".next", "target", "__pycache__"}
SENSITIVE_NAMES = {
    ".env",
    ".env.local",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "accounts.json",
    "config.json",
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
BROAD_ROOT_NAMES = SKIP_DIRS | {"vendor", "vendors", ".venv", "venv", "site-packages"}

TRELLIS_AGENTS_BLOCK = f"""{TRELLIS_BLOCK_START}

## DXM + Trellis 大开发路由

Trellis 是 DXM 下面的中大型任务持久层，不替代本目录长期文档。

- 小修、只读排查、单点 bug、轻量文档调整：默认按 DXM inline 处理，不强制创建 Trellis task。
- 新功能、架构变化、跨多文件重构、长周期任务、需求不清楚：先 project-grill，再把结论落到 `.trellis/tasks/<task>/prd.md`。
- 用户明确说 `scaffold only`、`先别问`、`只分析` 时，不进入 Trellis，不擅自改文件。
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
| 新功能 / 多模块 / 架构 / 跨文件 / 长周期 | project-grill 后建 Trellis task |
| 需求不清楚但会继续开发 | 先 grill-with-docs，再决定是否建 task |
| 用户明确 scaffold only / 先别问 | 只 scaffold，不 grill，不建 task |

启用 Trellis 时必须保持 `session_auto_commit: false`，并遵守本项目 Git/PR 授权规则。

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

1. 先用 `project-grill` 问清楚；有代码/文档时用 `grill-with-docs`，空项目用 `new-project-grill`，小脚本/demo 用 `lightweight-grill`。
2. 提问前先从代码和文档自行判断，能确定的是否题、偏好题、低风险取舍题作为推荐假设推进。
3. 把结论写入 `.trellis/tasks/<task>/prd.md`，不能只停留在聊天上下文里。
4. 用 `.trellis/scripts/task.py start <task>` 进入 Trellis active task。
5. 按 Trellis 的 implement/check/update-spec/finish 节奏开发、验证、沉淀规范。
6. 任务完成后同步 DXM 长期文档；不能只更新 `.trellis/` 内部状态。

{TRELLIS_BLOCK_END}
"""

TRELLIS_START_STEP0_BLOCK = f"""{TRELLIS_START_STEP0_START}

## DXM Step 0 — read project rules first

Before starting or continuing a Trellis task in a DXM workspace, read and obey:

1. `AGENTS.md`
2. `项目文件结构说明.md`
3. `项目完整链路说明.md`
4. `项目开发规范（AI协作）.md`
5. `开发者AI开发与PR提交流程.md` when GitHub, PR, push, merge, or release work is involved

Do not let Trellis task context override DXM, user instructions, Git authorization rules, read-only intent, or secret-handling rules.

{TRELLIS_START_STEP0_END}
"""

TRELLIS_WORKFLOW_OVERRIDE_BLOCK = f"""{TRELLIS_WORKFLOW_OVERRIDE_START}

## DXM no-task routing override

When no Trellis task is active, use DXM routing instead of forcing a task for every change:

- 只读排查、解释、日志查看、普通小修、单点 bug、轻量文档调整：可以按 DXM inline 完成，不要求创建 Trellis task。
- 新功能、架构变化、跨多文件重构、多阶段任务、长期沉淀价值、需求不清楚：先 project-grill，再创建/启动 Trellis task。
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


def extract_block(content: str, start_marker: str, end_marker: str) -> str | None:
    start = content.find(start_marker)
    if start == -1:
        return None
    end = content.find(end_marker, start)
    if end == -1:
        return None
    return content[start : end + len(end_marker)]


def replace_block(existing: str, block: str, start_marker: str, end_marker: str) -> str | None:
    start = existing.find(start_marker)
    if start == -1:
        return None
    end = existing.find(end_marker, start)
    if end == -1:
        return None
    end += len(end_marker)
    return existing[:start] + block + existing[end:]


def is_sensitive_name(name: str) -> bool:
    lowered = name.lower()
    if lowered in SENSITIVE_NAMES:
        return True
    if any(fnmatch.fnmatch(lowered, pattern) for pattern in SENSITIVE_PATTERNS):
        return True
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
    if not allow_broad_root and is_broad_root(root):
        raise UnsafeProjectRootError(root)


def read_template(name: str) -> str:
    template_dir = Path(__file__).resolve().parents[1] / "assets" / "templates"
    return normalize_lf((template_dir / f"{name}.template").read_text(encoding="utf-8"))


def project_inventory(root: Path) -> str:
    if not root.exists():
        return "- 当前目录尚不存在；实际 scaffold 会先创建项目根目录。"

    lines: list[str] = []
    for child in sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        name = child.name
        if name in SKIP_DIRS:
            lines.append(f"- `{name}/`：依赖、构建或工具目录；通常不展开维护。")
            continue
        if is_sensitive_name(name):
            suffix = "/" if child.is_dir() else ""
            lines.append(f"- `{name}{suffix}`：运行态或敏感数据；只说明用途，不回显真实内容。")
            continue
        suffix = "/" if child.is_dir() else ""
        if child.is_dir():
            lines.append(f"- `{name}/`：项目目录；首次 /dxm 生成后需要补充职责说明。")
        else:
            lines.append(f"- `{name}`：项目文件；首次 /dxm 生成后需要补充职责说明。")
    return "\n".join(lines) if lines else "- 当前目录为空；开始开发前补充文件结构。"


def render(content: str, root: Path) -> str:
    return (
        content.replace("{{project_name}}", root.name)
        .replace("{{project_root}}", str(root))
        .replace("{{generated_date}}", datetime.now().strftime("%Y-%m-%d"))
        .replace("{{file_inventory}}", project_inventory(root))
    )


def dxm_block(root: Path) -> str:
    return render(read_template("AGENTS.md"), root)


def refresh_managed_block(path: Path, content: str, start_marker: str, end_marker: str, dry_run: bool = False) -> str:
    existing = read_existing_text(path)
    if start_marker not in existing:
        return "would-skip-no-managed-block" if dry_run else "skipped-no-managed-block"
    if end_marker not in existing:
        return "would-skip-existing-marker-start" if dry_run else "skipped-existing-marker-start"

    block = extract_block(content, start_marker, end_marker)
    updated = replace_block(existing, block or content, start_marker, end_marker)
    if updated is None or updated == existing:
        return "would-skip-existing" if dry_run else "skipped-existing"
    if dry_run:
        return "would-refresh-managed-block"
    write_text_lf(path, updated)
    return "refreshed-managed-block"


def ensure_agents(path: Path, root: Path, force: bool, dry_run: bool = False, refresh_blocks: bool = False) -> str:
    content = dxm_block(root)
    if dry_run:
        if force or not path.exists():
            return "would-create" if not force else "would-write"
        existing = read_existing_text(path)
        if DXM_BLOCK_START in existing:
            if refresh_blocks and DXM_BLOCK_END in existing:
                return "would-refresh-managed-block"
            return "would-skip-existing" if DXM_BLOCK_END in existing else "would-skip-existing-marker-start"
        return "would-append-dxm-block"

    if force or not path.exists():
        write_text_lf(path, content)
        return "created" if not force else "written"

    existing = read_existing_text(path)
    if DXM_BLOCK_START in existing:
        if refresh_blocks:
            return refresh_managed_block(path, content, DXM_BLOCK_START, DXM_BLOCK_END)
        return "skipped-existing" if DXM_BLOCK_END in existing else "skipped-existing-marker-start"

    updated = existing.rstrip("\n") + "\n\n" + content.rstrip("\n") + "\n"
    write_text_lf(path, updated)
    return "appended-dxm-block"


def append_block_once(
    path: Path,
    block: str,
    start_marker: str = TRELLIS_BLOCK_START,
    end_marker: str = TRELLIS_BLOCK_END,
    dry_run: bool = False,
) -> str:
    if not path.exists():
        if dry_run:
            return "would-create"
        path.parent.mkdir(parents=True, exist_ok=True)
        write_text_lf(path, block)
        return "created"

    existing = read_existing_text(path)
    if start_marker in existing:
        return "skipped-existing" if end_marker in existing else "skipped-existing-marker-start"

    if dry_run:
        return "would-append-trellis-block"
    updated = existing.rstrip("\n") + "\n\n" + block.rstrip("\n") + "\n"
    write_text_lf(path, updated)
    return "appended-trellis-block"


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
        return ("initialized" if (root / ".trellis").exists() else "completed", output)
    return (f"failed-exit-{process.returncode}", output)


def ensure_session_auto_commit_disabled(root: Path, dry_run: bool = False) -> str:
    config = root / ".trellis" / "config.yaml"
    if not config.exists():
        return "missing-config"

    existing = read_existing_text(config)
    updated, count = re.subn(r"(?m)^\s*session_auto_commit\s*:\s*.*$", "session_auto_commit: false", existing)
    if count == 0:
        updated = existing.rstrip() + "\n\nsession_auto_commit: false\n"
    if updated != existing:
        if dry_run:
            return "would-update"
        write_text_lf(config, updated)
        return "updated"
    return "skipped-existing"


def ensure_trellis_start_step0(root: Path, dry_run: bool = False) -> str:
    path = root / ".agents" / "skills" / "trellis-start" / "SKILL.md"
    if not path.exists():
        return "missing-trellis-start-skill"
    return append_block_once(path, TRELLIS_START_STEP0_BLOCK, TRELLIS_START_STEP0_START, TRELLIS_START_STEP0_END, dry_run)


def ensure_trellis_workflow_override(root: Path, dry_run: bool = False) -> str:
    path = root / ".trellis" / "workflow.md"
    return append_block_once(path, TRELLIS_WORKFLOW_OVERRIDE_BLOCK, TRELLIS_WORKFLOW_OVERRIDE_START, TRELLIS_WORKFLOW_OVERRIDE_END, dry_run)


def ensure_trellis_docs(root: Path, dry_run: bool = False) -> list[tuple[str, str]]:
    return [
        ("AGENTS.md", append_block_once(root / "AGENTS.md", TRELLIS_AGENTS_BLOCK, dry_run=dry_run)),
        ("项目开发规范（AI协作）.md", append_block_once(root / "项目开发规范（AI协作）.md", TRELLIS_DEV_RULES_BLOCK, dry_run=dry_run)),
        ("项目文件结构说明.md", append_block_once(root / "项目文件结构说明.md", TRELLIS_FILE_STRUCTURE_BLOCK, dry_run=dry_run)),
        ("项目完整链路说明.md", append_block_once(root / "项目完整链路说明.md", TRELLIS_CHAIN_BLOCK, dry_run=dry_run)),
    ]


def ensure_trellis_safety_overrides(root: Path, dry_run: bool = False) -> list[tuple[str, str]]:
    return [
        (".trellis/config.yaml session_auto_commit", ensure_session_auto_commit_disabled(root, dry_run)),
        (".agents/skills/trellis-start/SKILL.md DXM Step 0", ensure_trellis_start_step0(root, dry_run)),
        (".trellis/workflow.md DXM no-task routing", ensure_trellis_workflow_override(root, dry_run)),
    ]


def validate_trellis_update_inputs(root: Path) -> None:
    if not root.exists():
        return
    paths = [
        root / "AGENTS.md",
        root / "项目开发规范（AI协作）.md",
        root / "项目文件结构说明.md",
        root / "项目完整链路说明.md",
        root / ".trellis" / "config.yaml",
        root / ".agents" / "skills" / "trellis-start" / "SKILL.md",
        root / ".trellis" / "workflow.md",
    ]
    for path in paths:
        if path.exists():
            read_existing_text(path)


def validate_update_inputs(root: Path, force: bool, refresh_blocks: bool, trellis: bool = False) -> None:
    if not root.exists():
        return
    for filename in FILES:
        path = root / filename
        if not path.exists():
            continue
        if not force and (filename == "AGENTS.md" or refresh_blocks or trellis):
            read_existing_text(path)


def scaffold(root: Path, force: bool, dry_run: bool = False, refresh_blocks: bool = False, trellis: bool = False) -> list[tuple[str, str]]:
    validate_update_inputs(root, force, refresh_blocks, trellis)
    if not dry_run:
        root.mkdir(parents=True, exist_ok=True)
    results: list[tuple[str, str]] = []
    for filename in FILES:
        target = root / filename
        content = render(read_template(filename), root)
        if filename == "AGENTS.md":
            status = ensure_agents(target, root, force, dry_run, refresh_blocks)
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold DXM AI collaboration files")
    parser.add_argument("--root", default=os.getcwd(), help="target project root; defaults to current directory")
    parser.add_argument("--force", action="store_true", help="overwrite existing files; use only on explicit user request")
    parser.add_argument("--dry-run", action="store_true", help="report planned scaffold actions without writing files")
    parser.add_argument("--refresh-blocks", action="store_true", help="refresh DXM-managed marker blocks while preserving manual content")
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

    root = Path(args.root).resolve()
    try:
        validate_project_root(root, args.allow_broad_root)
        if args.trellis and not args.dry_run:
            validate_trellis_update_inputs(root)
        results = scaffold(root, args.force, args.dry_run, args.refresh_blocks, args.trellis)
    except ExistingFileEncodingError as exc:
        print(f"Error: {exc.path} is not valid UTF-8; convert it to UTF-8 before DXM can safely update it.", file=sys.stderr)
        return 2
    except UnsafeProjectRootError as exc:
        print(f"Error: {exc.root} is too broad for DXM scaffold; choose a project root or pass --allow-broad-root explicitly.", file=sys.stderr)
        return 2

    trellis_output = ""
    if args.trellis:
        if args.dry_run:
            status, trellis_output = ("would-run", "")
        else:
            status, trellis_output = run_trellis_init(root, args.trellis_user, args.trellis_timeout_seconds)
        results.append(("trellis init --codex", status))
        if args.dry_run and (root / ".trellis").exists():
            try:
                results.extend(ensure_trellis_docs(root, dry_run=True))
                results.extend(ensure_trellis_safety_overrides(root, dry_run=True))
            except ExistingFileEncodingError as exc:
                print(f"Error: {exc.path} is not valid UTF-8; convert it to UTF-8 before DXM can safely update it.", file=sys.stderr)
                return 2
        if not args.dry_run and (root / ".trellis").exists():
            try:
                validate_trellis_update_inputs(root)
                results.extend(ensure_trellis_docs(root))
                results.extend(ensure_trellis_safety_overrides(root))
            except ExistingFileEncodingError as exc:
                print(f"Error: {exc.path} is not valid UTF-8; convert it to UTF-8 before DXM can safely update it.", file=sys.stderr)
                return 2

    print(f"DXM scaffold root: {root}")
    for filename, status in results:
        print(f"- {status}: {filename}")
    print_trellis_notes(trellis_output)
    print("Next: read AGENTS.md, then obey the generated project docs for all future work in this folder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
