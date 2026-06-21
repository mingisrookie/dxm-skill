#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scaffold DXM large-project AI collaboration files into a project root."""

from __future__ import annotations

import argparse
import os
import re
import signal
import shutil
import subprocess
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

SKIP_DIRS = {".git", "node_modules", "dist", "build", "coverage", ".next", "target", "__pycache__"}
SENSITIVE_NAMES = {"config.json", "accounts.json", "username.json", "tokens", ".env", ".env.local"}

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


def read_template(name: str) -> str:
    template_dir = Path(__file__).resolve().parents[1] / "assets" / "templates"
    return (template_dir / f"{name}.template").read_text(encoding="utf-8")


def project_inventory(root: Path) -> str:
    lines: list[str] = []
    for child in sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        name = child.name
        if name in SKIP_DIRS:
            lines.append(f"- `{name}/`：依赖、构建或工具目录；通常不展开维护。")
            continue
        if name in SENSITIVE_NAMES:
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


def ensure_agents(path: Path, root: Path, force: bool) -> str:
    content = dxm_block(root)
    if force or not path.exists():
        path.write_text(content, encoding="utf-8")
        return "created" if not force else "written"

    existing = path.read_text(encoding="utf-8", errors="replace")
    if DXM_BLOCK_START in existing and DXM_BLOCK_END in existing:
        return "skipped-existing"
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        if not existing.endswith("\n"):
            fh.write("\n")
        fh.write("\n")
        fh.write(content)
        if not content.endswith("\n"):
            fh.write("\n")
    return "appended-dxm-block"


def append_block_once(path: Path, block: str, start_marker: str = TRELLIS_BLOCK_START, end_marker: str = TRELLIS_BLOCK_END) -> str:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(block, encoding="utf-8")
        return "created"

    existing = path.read_text(encoding="utf-8", errors="replace")
    if start_marker in existing and end_marker in existing:
        return "skipped-existing"

    with path.open("a", encoding="utf-8", newline="\n") as fh:
        if not existing.endswith("\n"):
            fh.write("\n")
        fh.write("\n")
        fh.write(block)
        if not block.endswith("\n"):
            fh.write("\n")
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


def ensure_session_auto_commit_disabled(root: Path) -> str:
    config = root / ".trellis" / "config.yaml"
    if not config.exists():
        return "missing-config"

    existing = config.read_text(encoding="utf-8", errors="replace")
    updated, count = re.subn(r"(?m)^\s*session_auto_commit\s*:\s*.*$", "session_auto_commit: false", existing)
    if count == 0:
        updated = existing.rstrip() + "\n\nsession_auto_commit: false\n"
    if updated != existing:
        config.write_text(updated, encoding="utf-8")
        return "updated"
    return "skipped-existing"


def ensure_trellis_start_step0(root: Path) -> str:
    path = root / ".agents" / "skills" / "trellis-start" / "SKILL.md"
    if not path.exists():
        return "missing-trellis-start-skill"
    return append_block_once(path, TRELLIS_START_STEP0_BLOCK, TRELLIS_START_STEP0_START, TRELLIS_START_STEP0_END)


def ensure_trellis_workflow_override(root: Path) -> str:
    path = root / ".trellis" / "workflow.md"
    return append_block_once(path, TRELLIS_WORKFLOW_OVERRIDE_BLOCK, TRELLIS_WORKFLOW_OVERRIDE_START, TRELLIS_WORKFLOW_OVERRIDE_END)


def ensure_trellis_docs(root: Path) -> list[tuple[str, str]]:
    return [
        ("AGENTS.md", append_block_once(root / "AGENTS.md", TRELLIS_AGENTS_BLOCK)),
        ("项目开发规范（AI协作）.md", append_block_once(root / "项目开发规范（AI协作）.md", TRELLIS_DEV_RULES_BLOCK)),
        ("项目文件结构说明.md", append_block_once(root / "项目文件结构说明.md", TRELLIS_FILE_STRUCTURE_BLOCK)),
        ("项目完整链路说明.md", append_block_once(root / "项目完整链路说明.md", TRELLIS_CHAIN_BLOCK)),
    ]


def ensure_trellis_safety_overrides(root: Path) -> list[tuple[str, str]]:
    return [
        (".trellis/config.yaml session_auto_commit", ensure_session_auto_commit_disabled(root)),
        (".agents/skills/trellis-start/SKILL.md DXM Step 0", ensure_trellis_start_step0(root)),
        (".trellis/workflow.md DXM no-task routing", ensure_trellis_workflow_override(root)),
    ]


def scaffold(root: Path, force: bool) -> list[tuple[str, str]]:
    root.mkdir(parents=True, exist_ok=True)
    results: list[tuple[str, str]] = []
    for filename in FILES:
        target = root / filename
        content = render(read_template(filename), root)
        if filename == "AGENTS.md":
            status = ensure_agents(target, root, force)
        elif target.exists() and not force:
            status = "skipped-existing"
        else:
            target.write_text(content, encoding="utf-8")
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
    results = scaffold(root, args.force)
    trellis_output = ""
    if args.trellis:
        status, trellis_output = run_trellis_init(root, args.trellis_user, args.trellis_timeout_seconds)
        results.append(("trellis init --codex", status))
        if (root / ".trellis").exists():
            results.extend(ensure_trellis_docs(root))
            results.extend(ensure_trellis_safety_overrides(root))

    print(f"DXM scaffold root: {root}")
    for filename, status in results:
        print(f"- {status}: {filename}")
    print_trellis_notes(trellis_output)
    print("Next: read AGENTS.md, then obey the generated project docs for all future work in this folder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
