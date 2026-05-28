#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scaffold DXM large-project AI collaboration files into a project root."""

from __future__ import annotations

import argparse
import os
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

SKIP_DIRS = {".git", "node_modules", "dist", "build", "coverage", ".next", "target", "__pycache__"}
SENSITIVE_NAMES = {"config.json", "accounts.json", "username.json", "tokens", ".env", ".env.local"}


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


def write_file(path: Path, content: str, force: bool) -> str:
    if path.exists() and not force:
        return "skipped-existing"
    path.write_text(content, encoding="utf-8")
    return "created" if not path.exists() else "written"


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


def scaffold(root: Path, force: bool) -> list[tuple[str, str]]:
    root.mkdir(parents=True, exist_ok=True)
    results: list[tuple[str, str]] = []
    for filename in FILES:
        target = root / filename
        content = render(read_template(filename), root)
        if filename == "AGENTS.md":
            status = ensure_agents(target, root, force)
        else:
            if target.exists() and not force:
                status = "skipped-existing"
            else:
                target.write_text(content, encoding="utf-8")
                status = "written" if force else "created"
        results.append((filename, status))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold DXM AI collaboration files")
    parser.add_argument("--root", default=os.getcwd(), help="target project root; defaults to current directory")
    parser.add_argument("--force", action="store_true", help="overwrite existing files; use only on explicit user request")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    results = scaffold(root, args.force)

    print(f"DXM scaffold root: {root}")
    for filename, status in results:
        print(f"- {status}: {filename}")
    print("Next: read AGENTS.md, then obey the generated project docs for all future work in this folder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
