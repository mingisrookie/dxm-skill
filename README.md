<div align="center">

# DXM Skill

**Codex 大项目 AI 协作规范生成、项目澄清与 Trellis 大开发路由 Skill。**

把一个普通项目目录变成可持续维护、可追踪、可验证的 AI 协作工作区：先问清楚，再建档，再按项目规则开发。

[快速使用](#快速使用) · [DXM 工作流](#dxm-工作流) · [Trellis 路由](#dxm--trellis) · [生成文件](#生成文件) · [开发验证](#开发与验证)

[![release](https://img.shields.io/github/v/release/mingisrookie/dxm-skill?include_prereleases&label=release)](https://github.com/mingisrookie/dxm-skill/releases)
[![license](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)
[![skill](https://img.shields.io/badge/Codex%20Skill-dxm-111827)](skills/dxm/SKILL.md)
[![python](https://img.shields.io/badge/Python-3.10%2B-3776AB)](skills/dxm/scripts/scaffold_dxm.py)
[![workflow](https://img.shields.io/badge/workflow-DXM%20%2B%20Trellis-7c3aed)](#dxm--trellis)

[![path](https://img.shields.io/badge/skill%20path-skills%2Fdxm-0f766e)](skills/dxm)
[![docs](https://img.shields.io/badge/docs-Chinese%20project%20governance-d97706)](#生成文件)
[![mode](https://img.shields.io/badge/default-project--grill-blue)](#dxm-工作流)
[![safety](https://img.shields.io/badge/safety-no%20silent%20overwrite-red)](#安全模型)

</div>

## 项目状态

| 项目 | 当前事实 |
| --- | --- |
| 当前发布版 | [`v0.1.0`](https://github.com/mingisrookie/dxm-skill/releases/tag/v0.1.0) |
| 维护仓库 | <https://github.com/mingisrookie/dxm-skill> |
| Skill 路径 | `skills/dxm` |
| 核心脚本 | `skills/dxm/scripts/scaffold_dxm.py` |
| 普通入口 | `/dxm` |
| 大开发入口 | `/dxm trellis` / `/dxm 大开发` |
| 默认原则 | 小修 inline；中大型任务 project-grill 后进入 Trellis |
| 生成方式 | 默认只补缺失文件，不静默覆盖人工维护文档 |

---

## 这是什么

DXM 是一个 Codex Skill，用来把项目目录初始化成“大项目 AI 协作工作区”。它不是只丢几份模板，而是把项目开发前必须弄清楚的事情固化成流程：

1. 先判断目录是不是项目根。
2. 首次 `/dxm` 默认进入 `project-grill`，先问清楚项目目标、边界和验收。
3. 生成或确认 `AGENTS.md` 与四份长期中文项目文档。
4. 后续 Codex 在该目录里工作时，必须先读这些规则，再分析、开发、测试、同步文档和汇报。
5. 如果任务变成中大型开发，再把 PRD 和状态交给 Trellis 持久化。

一句话：**DXM 是项目规则层，grill 是开干前澄清层，Trellis 是中大型任务记忆层。**

---

## 快速使用

### 安装

使用 Codex 的 skill installer 从 GitHub 安装：

```bash
install-skill-from-github.py --repo mingisrookie/dxm-skill --path skills/dxm
```

也可以手动复制 `skills/dxm` 目录到你的 Codex skills 目录，然后重启 Codex。

### 初始化项目

进入项目根目录后，对 Codex 输入：

```text
/dxm
```

默认行为不是立刻开干，而是先判断项目状态：

| 场景 | 默认处理 |
| --- | --- |
| 空文件夹 / 新项目 | `new-project-grill`：问清用户、交付形态、技术栈、范围、验收 |
| 已有代码 / 文档 | `grill-with-docs`：先读现有材料，再拷问需求和边界 |
| 小脚本 / demo | `lightweight-grill`：只问阻塞执行的关键问题 |
| 已有完整 DXM | 不重复 grill，除非要求重梳理 |
| `scaffold only` / `先别问` | 只生成或补齐模板 |
| `只分析` / `先看看` | 只读，不初始化、不改文件 |

其中 `new-project-grill` 和 `lightweight-grill` 是 DXM 模式标签，不要求安装同名 skill；实际提问可由 `grill-me`、`grill-with-docs` 或简短内联问答完成。

### 直接运行脚本

```bash
python skills/dxm/scripts/scaffold_dxm.py --root /path/to/project
```

只有明确需要覆盖已有生成文件时才使用：

```bash
python skills/dxm/scripts/scaffold_dxm.py --root /path/to/project --force
```

---

## DXM 工作流

DXM 解决的是 AI 维护项目时最容易失控的几件事：

- 只改眼前文件，不看完整链路。
- 不知道项目目录里哪些文件负责什么。
- 修改代码后忘记更新长期文档。
- 没跑验证就说“完成”。
- 中文文档、注释或日志出现乱码。
- 把 token、账号、运行态数据写进回复或文档。
- Git / PR / 合并没有明确授权就继续做。

DXM 会把这些约束写进项目根目录，让后续 Codex 会话能重新读取，而不是依赖聊天记忆。

---

## DXM + Trellis

启用大开发模式：

```text
/dxm trellis
```

或直接运行：

```bash
python skills/dxm/scripts/scaffold_dxm.py --root /path/to/project --trellis --trellis-user <developer-name>
```

默认路由：

| 任务类型 | 默认方式 |
| --- | --- |
| 只读分析、日志查看、解释代码 | DXM inline，不建 Trellis task |
| 普通小 bug、单文件小修、轻量文档 | DXM inline，不建 Trellis task |
| 新功能、多模块、架构变化、跨文件重构 | project-grill 后建议或创建 Trellis task |
| 需求不清但会持续开发 | 先 grill，再把 PRD 写进 `.trellis/tasks/<task>/prd.md` |
| 长周期、多阶段、容易断上下文 | 默认 Trellis |

`--trellis` 会做这些安全补充：

- 非交互运行 `trellis init --codex -y --skip-existing`。
- 给 DXM 长期文档追加 Trellis 工作流块。
- 确保 `.trellis/config.yaml` 中 `session_auto_commit: false`。
- 给 `trellis-start` 加 Step 0：先读 `AGENTS.md` 和 DXM 长期文档。
- 给 Trellis workflow 加 DXM no-task override：小修和只读不强制建 task。

---

## 生成文件

DXM 在目标项目根目录创建或确认：

| 文件 | 用途 |
| --- | --- |
| `AGENTS.md` | 项目级 Codex 规则、`/dxm` 触发约定、Trellis 路由规则 |
| `项目开发规范（AI协作）.md` | AI/开发者协作规范、架构边界、测试、文档同步和最终回执要求 |
| `项目完整链路说明.md` | 项目从配置、输入、执行、状态到输出的完整链路 |
| `项目文件结构说明.md` | 根目录、源码目录、脚本、配置、运行态文件的职责边界 |
| `开发者AI开发与PR提交流程.md` | Git、分支、PR、GitHub CLI、合并授权流程 |

默认跳过已有文件，避免覆盖人工长期维护的内容。

---

## 仓库结构

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

## 安全模型

DXM 默认保守：

- 不静默覆盖已有项目文档。
- 不回显真实 token、密码、API Key、账号明细、验证码或密钥内容。
- 只基于文件、命令输出、测试、日志、diff 和真实运行行为下结论。
- 最终回执必须说明改了什么、验证了什么、跳过了什么、还有什么风险。
- Trellis 不得自动 stage、commit、push、PR 或 merge。

---

## 开发与验证

运行单元测试：

```bash
python -m unittest discover -s tests -v
```

手动脚手架冒烟：

```bash
python skills/dxm/scripts/scaffold_dxm.py --root /tmp/dxm-smoke
```

Trellis 冒烟需要本机已安装 `trellis`：

```bash
python skills/dxm/scripts/scaffold_dxm.py --root /tmp/dxm-trellis-smoke --trellis --trellis-user developer
```

发布前检查仓库中没有本机路径、token、API Key、密码、账号数据或运行态文件。

---

## License

MIT，详见 [LICENSE](LICENSE)。
