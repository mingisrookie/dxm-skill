# DXM Skill

> **DXM — Large-project AI collaboration rules for Codex.**<br>
> **DXM —— 面向 Codex 的大项目 AI 协作规范生成与约束 Skill。**

[![Release](https://img.shields.io/github/v/release/mingisrookie/dxm-skill?include_prereleases&label=release)](https://github.com/mingisrookie/dxm-skill/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

DXM is a Codex skill that bootstraps a project-level AI collaboration rule set. When the user runs `/dxm` in a project folder, DXM creates or confirms the standard governance files and instructs future Codex sessions in that folder to follow them.

DXM 是一个 Codex Skill，用于在项目目录中初始化“大项目 AI 协作规范”。当用户在项目中执行 `/dxm` 时，DXM 会生成或确认一组标准治理文件，并让后续 Codex 会话在该目录内默认遵守这些规则。

---

## Table of Contents / 目录

- [Why DXM / 为什么需要 DXM](#why-dxm--为什么需要-dxm)
- [Features / 功能特性](#features--功能特性)
- [Generated Files / 生成文件](#generated-files--生成文件)
- [Installation / 安装](#installation--安装)
- [Quick Start / 快速开始](#quick-start--快速开始)
- [Repository Layout / 仓库结构](#repository-layout--仓库结构)
- [Safety Model / 安全模型](#safety-model--安全模型)
- [Development / 开发与验证](#development--开发与验证)
- [Release / 发布](#release--发布)
- [License / 许可证](#license--许可证)

---

## Why DXM / 为什么需要 DXM

Large projects fail under AI assistance when the agent only edits the immediate file and forgets the surrounding workflow: architecture boundaries, runtime flow, tests, documentation, secrets, branch rules, and final verification.

DXM turns those expectations into project-local documents that Codex can read and follow before working. It is designed for projects where AI must behave like a disciplined maintainer instead of a one-shot code generator.

大项目接入 AI 后，最容易出问题的不是“不会写代码”，而是 AI 只改眼前文件，忘记架构边界、运行链路、测试、文档、敏感数据、分支规则和最终验证。

DXM 将这些要求固化为项目本地文档，让 Codex 在后续工作前可以先读取并遵守。它适合需要 AI 像长期维护者一样工作的项目，而不是只做一次性代码生成。

---

## Features / 功能特性

- **Project-local governance**: Creates an `AGENTS.md` that binds future Codex behavior inside the target folder.
- **Standard long-term documents**: Generates development rules, runtime-flow documentation, file-structure documentation, and PR workflow guidance.
- **Non-destructive by default**: Existing hand-maintained documents are preserved unless overwrite is explicitly requested.
- **Documentation-first maintenance**: Requires docs to stay synchronized with code, runtime flow, and project structure.
- **Verification discipline**: Encourages staged work, targeted checks, final review, and explicit risk reporting.
- **Secret-aware defaults**: Treats runtime files, tokens, passwords, API keys, and account data as non-reportable.
- **Chinese-friendly workflow**: Includes Chinese templates and explicit mojibake/encoding checks for Chinese projects.

---

- **项目级约束**：生成 `AGENTS.md`，让当前目录后续 Codex 行为受本地规则约束。
- **标准长期文档**：生成开发规范、完整链路说明、文件结构说明和 PR 流程说明。
- **默认非破坏性**：已有人工维护文档不会被静默覆盖，除非用户明确要求覆盖。
- **文档同步优先**：要求代码、运行链路、文件结构和长期文档保持一致。
- **验证纪律**：鼓励阶段化开发、定向检查、最终审查和风险显式披露。
- **敏感信息保护**：默认将 token、密码、API Key、账号数据和运行态文件视为不可回显内容。
- **中文项目友好**：内置中文模板，并将中文乱码/编码检查作为完成标准之一。

---

## Generated Files / 生成文件

When executed in a target project root, DXM creates or confirms the following files:

DXM 在目标项目根目录中会创建或确认以下文件：

| File | Purpose |
| --- | --- |
| `AGENTS.md` | Project-level Codex rules and `/dxm` trigger contract. |
| `项目开发规范（AI协作）.md` | AI/developer collaboration rules, architecture boundaries, testing, docs sync, and final reporting requirements. |
| `项目完整链路说明.md` | Runtime flow, configuration chain, modes, outputs, state transitions, and troubleshooting map. |
| `项目文件结构说明.md` | Maintained file/directory ownership and responsibility map. |
| `开发者AI开发与PR提交流程.md` | Git, branch, PR, GitHub CLI, and merge authorization workflow. |

Existing files are skipped by default. This protects carefully maintained project-specific knowledge from being replaced by generic templates.

默认情况下，已存在文件会被跳过。这可以避免用通用模板覆盖项目中已经长期维护过的高价值文档。

---

## Installation / 安装

Install this skill from GitHub using Codex's skill installer:

使用 Codex 的 skill installer 从 GitHub 安装：

```bash
install-skill-from-github.py --repo mingisrookie/dxm-skill --path skills/dxm
```

Alternatively, copy the `skills/dxm` directory into your Codex skills directory and restart Codex.

也可以手动复制 `skills/dxm` 目录到你的 Codex skills 目录，然后重启 Codex。

---

## Quick Start / 快速开始

Open a project folder and ask Codex:

进入一个项目目录后，对 Codex 输入：

```text
/dxm
```

DXM will scaffold the governance files in the current project root. After that, future Codex work in the folder should read and follow `AGENTS.md` plus the generated long-term project documents.

DXM 会在当前项目根目录中生成治理文件。之后，Codex 在该目录中的后续工作应先读取并遵守 `AGENTS.md` 以及生成的长期项目文档。

### Direct script usage / 直接运行脚本

If you need to run the scaffold script directly:

如果需要直接运行脚本：

```bash
python skills/dxm/scripts/scaffold_dxm.py --root /path/to/project
```

Use overwrite only when you explicitly want to replace generated files:

只有在明确希望覆盖已有生成文件时，才使用覆盖模式：

```bash
python skills/dxm/scripts/scaffold_dxm.py --root /path/to/project --force
```

---

## Repository Layout / 仓库结构

```text
skills/dxm/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── assets/
│   └── templates/
│       ├── AGENTS.md.template
│       ├── 项目开发规范（AI协作）.md.template
│       ├── 项目完整链路说明.md.template
│       ├── 项目文件结构说明.md.template
│       └── 开发者AI开发与PR提交流程.md.template
├── references/
│   └── dxm-method.md
└── scripts/
    └── scaffold_dxm.py
```

---

## Safety Model / 安全模型

DXM is intentionally conservative:

DXM 默认采用保守策略：

- It does not overwrite existing project documents unless explicitly forced.
- It treats credentials and runtime state as sensitive.
- It asks Codex to base conclusions on local evidence, command output, tests, logs, diffs, and runtime behavior.
- It requires final replies to disclose what was changed, what was verified, what was skipped, and what risks remain.

---

- 不会静默覆盖已有项目文档，除非明确使用覆盖模式。
- 将凭据和运行态状态视为敏感内容。
- 要求 Codex 基于本地文件、命令输出、测试、日志、diff 和真实运行行为得出结论。
- 要求最终回执说明改动内容、验证内容、跳过项和残余风险。

---

## Development / 开发与验证

Validate the skill metadata:

校验 Skill 元数据：

```bash
python <path-to-skill-creator>/scripts/quick_validate.py skills/dxm
```

Smoke test the scaffold script:

对脚手架做冒烟测试：

```bash
python skills/dxm/scripts/scaffold_dxm.py --root /tmp/dxm-smoke
```

Before publishing, check that the repository does not contain local paths, tokens, API keys, passwords, or project-specific runtime data.

发布前应检查仓库中没有本机路径、token、API Key、密码或项目专属运行态数据。

---

## Release / 发布

Current release:

当前版本：

- [v0.1.0](https://github.com/mingisrookie/dxm-skill/releases/tag/v0.1.0)

Release packages are published on the GitHub Releases page.

发布包在 GitHub Releases 页面提供。

---

## License / 许可证

This project is licensed under the [MIT License](LICENSE).

本项目使用 [MIT License](LICENSE) 许可证。
