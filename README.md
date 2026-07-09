<div align="center">

# DXM 项目协作技能

**把普通项目目录升级成可持续维护、可追踪、可验证的 Codex AI 协作工作区。**

先问清楚需求，再生成长期规则；小修走内联处理，中大型任务接入 Trellis。
脚手架默认 UTF-8 + LF，只补缺失内容，不静默覆盖人工文档。

[快速使用](#快速使用) · [最新更新](#最新更新摘要) · [DXM 工作流](#dxm-工作流) · [Trellis 路由](#dxm--trellis) · [生成文件](#生成文件)

[![release](https://img.shields.io/github/v/release/mingisrookie/dxm-skill?include_prereleases&label=release)](https://github.com/mingisrookie/dxm-skill/releases)
[![license](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)
[![skill](https://img.shields.io/badge/Codex%20Skill-dxm-111827)](skills/dxm/SKILL.md)
[![python](https://img.shields.io/badge/Python-3.10%2B-3776AB)](skills/dxm/scripts/scaffold_dxm.py)

</div>

## 这是什么

DXM 不是一次性模板生成器。它把“项目规则、开工前澄清、中大型任务状态”固化到项目根目录，让后续 Codex 会话有可重新读取、可验证的本地事实。

### 默认怎么处理

| 你关心的事 | DXM 的默认答案 |
| --- | --- |
| 项目还没有 AI 协作规则 | 输入 `/dxm`，生成或确认 `AGENTS.md` 和四份长期中文项目文档。 |
| 需求或边界还不清楚 | 首次 `/dxm` 默认先 `project-grill`，问清目标、范围、风险和验收。 |
| 只是小修或只读排查 | 走 DXM 内联处理，不强制创建 Trellis 任务。 |
| 是多模块、中大型、长期任务 | 用 `/dxm trellis` / `/dxm 大开发`，把 PRD、状态和执行入口交给 Trellis。 |
| 担心脚手架误写 | 先 `--dry-run` 看计划；默认拒绝盘根、用户根、系统目录、依赖目录和构建产物目录。 |
| 担心覆盖人工文档 | 默认只创建缺失文件；`--refresh-blocks` 只更新 DXM 管理块，保留人工内容。 |

发布信息以仓库 [`VERSION`](VERSION)、Git 标签和 [GitHub Releases](https://github.com/mingisrookie/dxm-skill/releases) 为准。技能路径：`skills/dxm` · 核心脚本：`skills/dxm/scripts/scaffold_dxm.py`

### 三层模型

| 层 | 负责什么 | 默认触发 |
| --- | --- | --- |
| DXM | 项目规则、长期文档、验证和交付红线 | `/dxm` |
| project-grill | 开发前澄清目标、边界、验收和风险 | 首次初始化或需求不清 |
| Trellis | 中大型任务的 PRD、状态、阶段和跨会话记忆 | `/dxm trellis` / `/dxm 大开发` |

一句话：**DXM 是项目规则层，grill 是开干前澄清层，Trellis 是中大型任务记忆层。**

### 最新更新摘要

完整历史见 [`CHANGELOG.md`](CHANGELOG.md)。README 只保留最近一版重点，避免发布时双份维护。

**v1.0.4 - 2026-07-09**

| 更新 | 作用 |
| --- | --- |
| 更新日志中文化 | `CHANGELOG.md` 全文改为中文标题、中文小节和中文条目，只保留必要命令、路径、版本号和产品名。 |
| README 文案复查 | 去掉 `inline`、`task`、`marker` 等不必要英文散落表达，保留技术命令和目录名。 |
| 发布说明修正 | GitHub Release 说明改为中文表述，v1.0.4 作为包含文档修正的最新归档版本。 |
| v1.0.3 变更保留 | DXM 自用规则、三处契约防漂移、Trellis 命令和 `--force` 风险说明见 [`CHANGELOG.md`](CHANGELOG.md)。 |

---

## 快速使用

### 安装

使用 Codex 技能安装器从 GitHub 安装：

```bash
install-skill-from-github.py --repo mingisrookie/dxm-skill --path skills/dxm
```

也可以手动复制 `skills/dxm` 目录到你的 Codex skills 目录，然后重启 Codex。手动复制前建议先清理 `__pycache__/` 和 `*.pyc`，或在复制命令里排除它们。

### 初始化项目

进入项目根目录后，对 Codex 输入：

```text
/dxm
```

默认行为不是立刻开干，而是先判断项目状态：

| 场景 | 默认处理 |
| --- | --- |
| 空文件夹 / 新项目 | `new-project-grill`：用 `grilling` 问清用户、交付形态、技术栈、范围、验收 |
| 已有代码 / 文档 | `grill-with-docs`：先读现有材料，再用 `grilling` + `domain-modeling` 拷问需求、边界、术语和 ADR |
| 小脚本 / demo | `lightweight-grill`：只问阻塞执行的关键问题 |
| 已有完整 DXM | 不重复 grill，除非要求重梳理 |
| `scaffold only` / `先别问` | 只生成或补齐模板 |
| `只分析` / `先看看` | 只读，不初始化、不改文件 |

其中 `new-project-grill` 和 `lightweight-grill` 是 DXM 模式标签，不要求安装同名技能；实际提问优先由 `grilling`、`grill-with-docs` 和 `domain-modeling` 完成，旧环境可回退到旧版 `grill-me` 或简短内联问答。

### 直接运行脚本

```bash
python skills/dxm/scripts/scaffold_dxm.py --root /path/to/project
```

只查看将要执行的动作、不写文件：

```bash
python skills/dxm/scripts/scaffold_dxm.py --root /path/to/project --dry-run
```

非破坏式刷新 DXM 管理标记块，保留人工维护内容：

```bash
python skills/dxm/scripts/scaffold_dxm.py --root /path/to/project --refresh-blocks
```

生成更深的初始文件结构快照：

```bash
python skills/dxm/scripts/scaffold_dxm.py --root /path/to/project --inventory-depth 2
```

安装后自检：

```bash
python skills/dxm/scripts/scaffold_dxm.py --self-test
```

脚本默认拒绝在盘根、用户根、系统目录、依赖目录或构建产物目录初始化。只有你明确确认目标就是项目根时，才加：

```bash
python skills/dxm/scripts/scaffold_dxm.py --root /path/to/project --allow-broad-root
```

只有明确需要覆盖已有 DXM 目标文件、且接受丢失人工内容风险时才使用：

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
| 只读分析、日志查看、解释代码 | DXM 内联处理，不建 Trellis 任务 |
| 普通小 bug、单文件小修、轻量文档 | DXM 内联处理，不建 Trellis 任务 |
| 新功能、多模块、架构变化、跨文件重构 | project-grill 后建议或创建 Trellis 任务 |
| 需求不清但会持续开发 | 先 `grilling` / `grill-with-docs`，再把 PRD 写进 `.trellis/tasks/<task>/prd.md` |
| 长周期、多阶段、容易断上下文 | 默认 Trellis |

`--trellis` 会做这些安全补充：

- 非交互运行 `trellis init --codex -u <developer> -y --skip-existing`。
- 给 DXM 长期文档追加或刷新 Trellis 工作流块。
- 确保 `.trellis/config.yaml` 中 `session_auto_commit: false`。
- 给 `trellis-start` 加第 0 步：先读 `AGENTS.md` 和 DXM 长期文档。
- 给 Trellis 工作流加 DXM 免建任务覆盖规则：小修和只读不强制建任务。
- 在任何 DXM/Trellis 标记写入前预检已有目标文件必须是 UTF-8，且标记必须成对，避免失败后留下半写入或坏块静默成功。

---

## 生成文件

DXM 在目标项目根目录创建或确认：

| 文件 | 用途 |
| --- | --- |
| `AGENTS.md` | 项目级 Codex 规则、`/dxm` 触发约定、Trellis 路由规则 |
| `项目开发规范（AI协作）.md` | AI/开发者协作规范、架构边界、测试、文档同步和最终回执要求 |
| `项目完整链路说明.md` | 项目从配置、输入、执行、状态到输出的完整链路 |
| `项目文件结构说明.md` | 根目录、源码目录、脚本、配置、运行态文件的职责边界 |
| `开发者AI开发与PR提交流程.md` | Git、分支、PR、GitHub CLI、合并授权、发布、发布说明与 Latest 核验流程 |

默认只创建缺失文件，避免覆盖人工长期维护的内容。需要升级 DXM 或 Trellis 管理块时，使用 `--refresh-blocks`，脚本只会刷新标记块内的生成内容。

生成文件统一写入 UTF-8 + LF。若已有待更新文件不是合法 UTF-8，脚本会停止并提示先转换编码，避免静默制造乱码或混合编码。

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

## 许可证

MIT，详见 [LICENSE](LICENSE)。
