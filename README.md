<div align="center">

# DXM 项目协作技能

**把普通项目目录升级成可持续维护、可追踪、可验证的 Codex AI 协作工作区。**

先锁定项目根目录和工作模式，再按需审查、初始化或执行任务；小修走内联处理，中大型任务接入 Trellis。
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

**v1.1.0 - 2026-07-13**

| 更新 | 作用 |
| --- | --- |
| 四模式工作流 | 用 `audit`、`init`、`task`、`scaffold-only` 分离只读审查、首次建档、日常任务和纯模板生成。 |
| 可审计完成门 | 新增项目基线、readiness 四态、证据矩阵、机器可验 check verdict 与 completion receipt validator。 |
| 真实失败语义 | Trellis 缺失、超时、失败或集成不完整不再被误报为成功。 |
| 安全与回归加固 | 补齐 marker、路径链接、凭据、UTF-8、隐私和 core-only 安装回归。 |

---

## 快速使用

### 核心 DXM

使用 Codex 技能安装器从 GitHub 安装核心 DXM：

```bash
install-skill-from-github.py --repo mingisrookie/dxm-skill --path skills/dxm
```

这条命令只安装 `skills/dxm`。核心 DXM 不依赖相邻技能：它能独立锁定 `audit`、`init`、`task`、`scaffold-only` 模式并以内联 0–3 个阻塞问题完成必要澄清。若另行安装了适用的 bounded router，运行时可按全局 skill 路由使用它，但不得改变 0–3 默认节奏；逐题穷举仍只在用户明确要求时启用。

也可以手动复制 `skills/dxm` 目录到你的 Codex skills 目录，然后重启 Codex。手动复制前建议先清理 `__pycache__/` 和 `*.pyc`，或在复制命令里排除它们。

### 可选的相邻技能

仓库同时提供下列可选技能，但安装核心 `skills/dxm` 时不会自动安装，也不影响 DXM 的基本状态机、脚手架和校验能力。安装后，bounded router 可在其描述明确匹配时按全局 skill 路由使用；只有 full/exhaustive grilling 需要用户明确要求，任何自动路由都不得进入逐轮穷举访谈。

| 路径 | 何时额外安装 |
| --- | --- |
| `skills/grilling` | 单独安装后，仅在用户明确要求完整、逐轮方案压力测试时使用。 |
| `skills/grill-with-docs` | 单独安装后，在现有代码/文档澄清任务明确匹配时提供同样的 0–3 有界路由。 |
| `skills/domain-modeling` | 单独安装后，仅在稳定术语、上下文映射或 ADR 确实需要创建/更新时使用。 |
| `skills/grill-me` | 仅为旧提示词和旧文档保留的兼容别名。 |

需要其中某个技能时，使用同一安装命令并把 `--path` 改成表中的对应路径；不需要为了运行 DXM 一次性安装全部相邻技能。

### 初始化项目

进入项目根目录后，对 Codex 输入：

```text
/dxm
```

默认行为不是立刻写文件，而是先锁定项目根目录与模式，再检查本地事实：

| 场景 | 默认处理 |
| --- | --- |
| `只分析` / `先看看` | `audit`：只读，不初始化、不建任务、不改运行态或文件。 |
| 空文件夹 / 新项目 | `init` / `new-project-grill`：先查本地证据，一批最多问 0–3 个真正阻塞的问题，再持久化基线并建档。 |
| 已有代码 / 文档但未建档 | `init`：先读现有材料，再用同一套 0–3 契约澄清；已安装且明确匹配的 bounded router 可以辅助，但不改变节奏。 |
| 已有 DXM 的开发工作 | `task`：复用现有基线，不重复初始化；小脚本 / demo 使用 `lightweight-grill` 的最小问题预算。 |
| `scaffold only` / `先别问` | `scaffold-only`：只生成或补齐模板，不做项目访谈，也不宣称工作区已 READY。 |

`new-project-grill` 和 `lightweight-grill` 只是核心 DXM 的澄清强度标签，不构成硬依赖。可选 skills 只有单独安装后才可能被路由；其中 full `grilling` 必须用户明确点名，bounded `grill-with-docs` 可在描述匹配时辅助，`domain-modeling` 只在稳定域事实确实变化时写入，`grill-me` 只作为旧环境兼容别名。

### 直接运行脚本

```bash
python skills/dxm/scripts/scaffold_dxm.py --mode scaffold-only --root /path/to/project
```

`init` 的项目事实持久化在 `<project-root>/.dxm/project.json`。该本地 JSON 保留规范化绝对 root；共享 Markdown 只写可移植投影：先对绝对路径 token 做词法规范化并把 root/子路径映射为 `$PROJECT_ROOT`，无法安全归属的剩余绝对路径收敛为 `$ABSOLUTE_PATH`，避免 `..` 或换 clone 路径产生漂移。先准备符合 schema 的 UTF-8 JSON 基线，再让 scaffold 校验、复制并把受管基线块写入链路文档：

```bash
python skills/dxm/scripts/scaffold_dxm.py --mode init --root /path/to/project --baseline <baseline.json>
```

`--baseline` 不会把聊天内容自动猜成项目事实；目标、用户、交付物、非目标、入口、验收 ID、证据类型、验证命令和假设必须由已确认的基线提供。已有人工文档仍按非破坏策略保留。

只查看将要执行的动作、不写文件：

```bash
python skills/dxm/scripts/scaffold_dxm.py --mode scaffold-only --root /path/to/project --dry-run
```

非破坏式刷新 DXM 管理标记块，保留人工维护内容：

```bash
python skills/dxm/scripts/scaffold_dxm.py --mode scaffold-only --root /path/to/project --refresh-blocks
```

生成更深的初始文件结构快照：

```bash
python skills/dxm/scripts/scaffold_dxm.py --mode scaffold-only --root /path/to/project --inventory-depth 2
```

安装后自检：

```bash
python skills/dxm/scripts/scaffold_dxm.py --self-test
```

脚本默认拒绝在盘根、用户根、系统目录、依赖目录或构建产物目录初始化。只有你明确确认目标就是项目根时，才加：

```bash
python skills/dxm/scripts/scaffold_dxm.py --mode scaffold-only --root /path/to/project --allow-broad-root
```

目标 root 已存在时必须是目录。所有受管目标及其已存在祖先必须留在规范化 root 内、是预期的普通目录/文件，且不得通过 symlink、reparse point 或多硬链接文件改写其他位置；任何一项不满足都会在首次写入前以 exit `2` 终止，不留半套文档。

只有明确需要覆盖已有 DXM 目标文件、且接受丢失人工内容风险时才使用：

```bash
python skills/dxm/scripts/scaffold_dxm.py --mode scaffold-only --root /path/to/project --force
```

### Readiness 与完成回执校验

`validate_dxm.py` 是只读校验入口，不会 scaffold、修改运行态或执行 Git 操作：

```bash
python skills/dxm/scripts/validate_dxm.py audit --root /path/to/project --json
python skills/dxm/scripts/validate_dxm.py baseline --file /path/to/baseline.json --json
```

非 Trellis 的 `init` / `task` 可以直接校验锁定根目录内的回执。Trellis 必须先通过对抗检查，并把最终 `check.md` 的文件首个非空行写成顶格独立的 `<!-- DXM-CHECK:PASS -->`；该片段全文只能出现一次，其他、混合或未闭合 `DXM-CHECK` 片段一律失败。随后才可真实 finish 和归档；归档强制 `--no-commit`，避免绕过 Git 授权。归档前不要预写 `finished: true`：

```bash
python .trellis/scripts/task.py finish
python .trellis/scripts/task.py archive <task> --no-commit
# 在归档目录生成 completion.json 后再校验
python skills/dxm/scripts/validate_dxm.py receipt --root /path/to/project --file .trellis/tasks/archive/<YYYY-MM>/<task>/completion.json --json
```

- `audit` 检查五份 DXM 文档、真实 Markdown managed marker、`.dxm/project.json`、根目录一致性及可选 Trellis 完整性；完整 fenced/inline code 中的 marker 示例不算活动块，未闭合 fence 不能掩盖错误。需要 Trellis 时追加 `--require-trellis`。
- `baseline` 只校验项目基线 schema。
- `baseline` / `receipt` 会拒绝 Bearer、private-key header、真实 `sk-...`、`api_key=...` 等高置信凭据；credential-like 字段名会先忽略大小写及空格、点、横线、下划线做规范化，并把检查向 `credentials` / `secrets` / `auth` 等嵌套容器传播。凭据上下文只豁免 `${NAME}`、`env:NAME`、`<env:NAME>` 和明确白名单脱敏占位；错误只报告安全字段路径，不回显 key/value。
- `receipt` 仅接受 `init` / `task`，要求从已锁定 workflow 传入可信 `--root`，再校验 baseline requirement/evidence、对抗检查、质量检查、Trellis 和 Git 事实；Trellis 的 `finished: true` 还必须对应已归档且状态完成的真实 task，其 `check.md` 必须含唯一规范 PASS marker，月份目录必须严格匹配 `YYYY-MM`，CLI/file 输入必须就是该 task 的归档 `completion.json`。validator 不会信任 receipt 内的路径扩读其他目录，也不会代替实际 Git 操作。

`audit` 的 readiness 与退出码固定如下；`baseline` / `receipt` 合法时返回 `0`，输入或契约非法时返回 `2`：

| Readiness | 退出码 | 含义 |
| --- | --- | --- |
| `READY` | `0` | 必需文档、marker 和基线完整，且请求的可选集成有效。 |
| `BROKEN` | `2` | JSON/UTF-8/marker/root 等完整性错误。 |
| `PARTIAL` | `3` | 文档可读，但基线、managed block、必需文件或可选集成尚不完整。 |
| `ABSENT` | `4` | 尚无 DXM 文档集。 |

`PARTIAL` / `BROKEN` 不能输出成功式下一步，也不能被当成 `READY`。

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
python skills/dxm/scripts/scaffold_dxm.py --mode init --root /path/to/project --baseline <baseline.json> --trellis --trellis-user <developer-name>
```

默认路由：

| 任务类型 | 默认方式 |
| --- | --- |
| 只读分析、日志查看、解释代码 | DXM 内联处理，不建 Trellis 任务 |
| 普通小 bug、单文件小修、轻量文档 | DXM 内联处理，不建 Trellis 任务 |
| 新功能、多模块、架构变化、跨文件重构 | project-grill 后建议或创建 Trellis 任务 |
| 需求不清但会持续开发 | 核心 DXM 先用内联 0–3 契约澄清；进入 Trellis 后把 PRD 写进 `.trellis/tasks/<task>/prd.md` |
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
| `.dxm/project.json` | 仅在提供有效 `--baseline` 时持久化的本地规范化项目基线；共享链路文档使用 `$PROJECT_ROOT` / `$ABSOLUTE_PATH` 可移植投影，不保留本机绝对路径 |

默认只创建缺失文件，避免覆盖人工长期维护的内容。需要升级 DXM 或 Trellis 管理块时，使用 `--refresh-blocks`，脚本只会刷新标记块内的生成内容。

生成文件统一写入 UTF-8 + LF。若已有待更新文件不是合法 UTF-8，脚本会停止并提示先转换编码，避免静默制造乱码或混合编码。

---

## 仓库结构

```text
skills/dxm/
├── SKILL.md
├── VERSION
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
    ├── scaffold_dxm.py
    ├── dxm_contract.py
    └── validate_dxm.py
```

---

## 安全模型

DXM 默认保守：

- 不静默覆盖已有项目文档。
- 写前拒绝非目录 root、非目录祖先、symlink/reparse target 和多硬链接受管文件。
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

模拟用户只安装 `skills/dxm` 的临时副本，并分别验证 scaffold 与只读 validator；该冒烟不复制任何相邻技能：

```powershell
$temp = Join-Path ([IO.Path]::GetTempPath()) ("dxm-core-smoke-" + [guid]::NewGuid())
$core = Join-Path $temp "dxm"
New-Item -ItemType Directory -Path $temp | Out-Null
Copy-Item -Recurse -LiteralPath "skills/dxm" -Destination $core
python "$core/scripts/scaffold_dxm.py" --self-test
python "$core/scripts/validate_dxm.py" --version
Remove-Item -Recurse -Force -LiteralPath $temp
```

手动脚手架冒烟：

```bash
python skills/dxm/scripts/scaffold_dxm.py --mode scaffold-only --root /tmp/dxm-smoke
```

Trellis 冒烟需要本机已安装 `trellis`：

```bash
python skills/dxm/scripts/scaffold_dxm.py --mode scaffold-only --root /tmp/dxm-trellis-smoke --trellis --trellis-user developer
```

发布前检查仓库中没有本机路径、token、API Key、密码、账号数据或运行态文件。

---

## 许可证

MIT，详见 [LICENSE](LICENSE)。
