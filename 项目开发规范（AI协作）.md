# 项目开发规范（AI协作）

> 项目：`dxm`
> 根目录：当前仓库根目录（本机规范化路径记录在 `.dxm/project.json`）
> 初始化日期：`2026-07-13`

本文档是面向 AI 与开发者的大项目开发规范。目标是让项目更清晰、更可维护、更可测试，而不是让 AI 只追求“眼前能跑”。

<!-- DXM-DOC-RULES:START -->

<!-- DXM-CONTRACT:1 -->

## DXM 文档维护规则

- 本块由 DXM 管理；`--refresh-blocks` 只刷新本块，保留下方项目专属规范和人工补充。
- 完整流程细则集中维护在本文；`AGENTS.md` 只保留触发约定、红线摘要和本文件指针，避免多处长期事实逐字漂移。
- 修改开发流程、测试要求、架构边界、协作约束后，必须同步更新本文并检查中文乱码。
- 不得把临时方案文件、聊天结论或一次性清单当成长期规范替代品。

<!-- DXM-DOC-RULES:END -->

## 本仓专属覆盖：契约同步与严格必读

本仓维护 DXM 契约本身，因此对通用 selective docs 采用更严格覆盖：任何代码、测试、脚本、配置或文档写入都必须实际阅读 `AGENTS.md`、`项目文件结构说明.md`、`项目完整链路说明.md` 和本文；涉及 Git/PR/version/tag/release/publish 时再读 `开发者AI开发与PR提交流程.md`。

同一份行为契约分布在四层，修改任一层时必须核对其余层：

1. `skills/dxm/SKILL.md` 与 `references/dxm-method.md`：触发、状态机、问题预算和完成门。
2. `skills/dxm/assets/templates/`：生成到用户项目的自包含长期规则。
3. `skills/dxm/scripts/scaffold_dxm.py`、`dxm_contract.py`、`validate_dxm.py`：写入、基线、readiness 和 receipt 的真实行为。
4. `skills/dxm/agents/openai.yaml`、`README.md`、`tests/`：运行时元数据、公开用法和行为级防漂移契约。

至少运行与影响面对应的定向测试；最终收口运行：

```text
python -m unittest discover -s tests -v
python skills/dxm/scripts/scaffold_dxm.py --self-test
python skills/dxm/scripts/validate_dxm.py audit --root . --require-trellis
```

核心包必须在只复制 `skills/dxm`、没有 sibling skills 的隔离目录中仍可执行 self-test 和 validator。Trellis 任务按“对抗检查 → `finish` → `task.py archive <task> --no-commit` → 在归档目录生成/校验 completion receipt → 人类回执”收口；不得在归档前预写 `finished: true`，也不得省略 `--no-commit` 绕过 Git 授权。


## 0. AI 协作执行协议

### 0.1 selective docs（选择性必读）

`AGENTS.md` 是 always 必读入口。不能只凭历史记忆、上次会话摘要或“看起来知道项目”直接执行；再按受影响面读取或重新核对长期文档：

| 受影响面 | 追加必读 |
| --- | --- |
| 任意代码、配置、测试或文档写入 | 当前文件 `项目开发规范（AI协作）.md` |
| 文件新增/删除/重命名、目录职责或模块归属 | `项目文件结构说明.md` |
| 入口、运行态、配置/状态/数据流、service/UI 链路 | `项目完整链路说明.md` |
| Git/PR/合并/version/tag/release/publish | `开发者AI开发与PR提交流程.md` |

如果 `AGENTS.md` 或更窄目录规则声明了更严格的开发前必读集合，遵守更严格规则。selective docs 只减少与当前任务无关的上下文，不得绕过项目约束。

### 0.2 四模式状态机与意图边界

每轮只允许一个模式，并建立 **root/mode/scope lock**。首次写入前锁定规范化项目根目录、模式和允许影响范围；当前路径、`.dxm/project.json` 根目录或任务范围不一致时停止写入，不得静默换根、换模式或扩范围。

| 模式 | 选择条件 | 硬约束 |
| --- | --- | --- |
| `audit` | `先分析`、`只分析`、`暂时不改`、review/排查，或用户尚未授权改变状态 | 严格只读：不 scaffold、不创建 Trellis task、不改变运行态、不写文件。 |
| `init` | 首次建立项目基线与治理文档 | 先查本地证据、做有界澄清、落盘基线、非破坏式 scaffold，再审计 readiness。 |
| `task` | 在已有 READY/PARTIAL DXM 工作区开发或维护 | 沿用基线，不重复初始化；锁定本任务范围并收集验收证据。 |
| `scaffold-only` | 用户明确说 `scaffold only`、`只生成模板`、`先别问` | 只补模板，不访谈、不创建 task、不宣称 READY。 |

分析型措辞默认进入 `audit`；用户要求“开始开发”“按照清单开发”时才进入对应 `init`/`task`。用户说“提交代码”只表示任务目标，Git 操作仍受单独授权规则约束。

### 0.3 首次建档与有界 project-grill

`init` 采用同一套默认契约：

1. 先从**第一性原理**识别真实目标、硬约束、本地事实和未知阻塞，主动**质疑隐藏假设**、伪约束、过度方案和实现偏置；再执行**本地证据优先**，查锁定根目录内的代码、README、manifest、配置、测试、文档、日志和安全运行态，本地可知事实不得反问。
2. 默认只在**单批提出 0–3 个阻塞性问题**。阻塞问题必须会改变下一步安全动作、root/scope 边界或验收契约。
3. 非阻塞选择记录推荐假设后继续；用户说 `按推荐走`、`直接做` 或同义表达时，关闭剩余非阻塞澄清。
4. 完整/穷举、逐题 `grilling` 仅 **explicit opt-in**。只有用户明确说 `grill me`、`完整 grilling` 或要求遍历所有分支时才启用；默认 init 不得使用 exhaustive cadence。
5. 有未解决阻塞项时不得 scaffold；没有阻塞项就问 0 个并继续。

| 场景 | 有界 profile |
| --- | --- |
| 空目录 / 新项目 | `new-project-grill`：只处理用户、交付、核心范围、约束和验收中的阻塞项 |
| 已有代码 / 文档 | `grill-with-docs`：先读证据，再用同一套 0–3 契约澄清 |
| 临时脚本 / demo | `lightweight-grill`：只处理输入输出、成功标准、允许副作用中的阻塞项 |
| 已有完整 DXM | 进入 `task`，除非用户明确要求 re-baseline |

`new-project-grill`、`lightweight-grill` 是标签，`grill-with-docs` 是可选 router，legacy `grill-me` 只是可选别名；核心 DXM 必须能以内联问答完成。`domain-modeling` 只在稳定术语、上下文边界、context map 或 ADR 决策实际新增/变化时写入，普通查证不创建域文档。

写入门必须进入 CLI：`init` 运行 `scaffold_dxm.py --mode init --root <root> --baseline <baseline.json>`；明确模板专用才运行 `--mode scaffold-only --root <root>`。前者缺 baseline 必须零写入失败；后者输出 `readiness: NOT_EVALUATED`，不能冒充 READY。无 `--mode` 调用只保留旧兼容语义。

### 0.4 Trellis 使用边界

Trellis 是中大型任务记忆层，不替代 DXM。

- 小修、只读排查、单点 bug、轻量文档调整：默认 DXM inline，不建 Trellis task。
- 新功能、多模块、架构变化、跨文件重构、长周期任务：完成有界 project-grill 后建议一次 Trellis；用户请求已经批准时可创建 task。
- Trellis PRD 必须写入 `.trellis/tasks/<task>/prd.md`；不能只依赖聊天上下文。
- create/start/check/finish 状态必须真实；显式 Trellis 请求遇到 CLI 缺失、超时或失败时，普通 DXM 文件可以已生成，但 DXM + Trellis 整体不得报告成功。
- 每次 Trellis 任务进入 finish/handoff 前必须执行对抗性检查；检查需求偏差、隐藏假设、负路径、架构边界、测试、文档、敏感信息、乱码和回滚/恢复。存在阻断问题时回到 implement/check，不得 finish。
- Trellis 不能自动 stage、commit、push 或创建/合并 PR；Git 操作必须得到用户明确授权。

### 0.5 发布 / Release 完成面

当任务涉及发布、版本、latest、安装包、公开仓库或 release notes 时，必须把发布视为多表面交付：代码提交、版本号、`CHANGELOG.md`、tag、GitHub Release、Latest 状态、中文更新日志、对比链接和验证证据要一起完成。只 push main 不算发布完成。

### 0.6 开发方案与开发清单

用户要求写开发方案时，方案至少包含：

1. 需求理解与真实目标。
2. 现有源码链路分析。
3. 是否符合要求、是否完善、是否完整、是否正确。
4. 是否符合本开发规范、现有架构和命名。
5. 方案自身是否有缺陷、边界遗漏或上下游设计冲突。
6. 与本功能无直接 UI 关系但有逻辑关联的模块检查。
7. 分阶段开发清单。
8. 每个阶段完成后的自检项。
9. 最终全量审查项。

### 0.7 阶段化开发硬要求

进入开发后，必须按开发清单一个阶段一个阶段完成。每完成一个阶段，必须自检：

- 相关代码是否都改到。
- 状态流、日志流、数据流、UI/API 流是否一致。
- 是否有设计缺漏、逻辑缺陷和边界问题。
- 是否引入乱码、错码、异常替换字符。
- 定向测试或必要的静态检查是否通过。

阶段自检未通过时，不能进入下一阶段。最终提交或回执前必须再做一次全局审查。

## 1. 架构原则

### 1.1 真实运行态优先

当源码、文档、注释、旧方案与运行态冲突时，优先级为：

1. 实际运行行为、测试结果、日志和命令输出。
2. 当前入口、配置、启动路径和依赖关系。
3. 根目录长期文档。
4. 历史方案、注释、旧截图和生成物。

如果发现长期文档落后于真实实现，本次任务影响相关事实时必须同步修正文档。

### 1.2 模块边界

- 新功能优先沿现有分层接入，不能把逻辑重新堆回主入口、大文件或无关模块。
- 横切能力（日志、观察、导出、审计、缓存、重试、配置）应放在清晰的公共层或独立模块中，不能借某个业务开关隐式控制。
- 兼容型薄包装允许存在，但必须有明确目的；没有意义的旧分支应在后续重构中清理。
- 不为“看起来整洁”做无关重写、全文件格式化或大范围重命名。

### 1.3 完整链路原则

新增或调整功能时，必须同步检查：

1. 默认值、归一化、保存、恢复、导入导出。
2. UI / CLI / API / 配置入口。
3. 核心执行链路、状态流、日志流、错误传播。
4. 手动操作、自动流程、失败恢复、清理路径。
5. 测试和长期文档。

不能只改一个调用点就声称完成。

## 2. 新增功能接入规范

### 2.1 新增配置项

必须同步检查：默认值、读取、归一化、保存、恢复、导入导出、UI/CLI/API 暴露、文档、测试。

### 2.2 新增流程节点或运行模式

必须先说明它是持久配置、当前轮冻结状态、运行态 UI 模式、单次执行参数，还是能力开关。不能把这些概念混在一起。

### 2.3 新增 provider / 外部集成

优先使用稳定协议接口。只有目标来源没有协议能力、必须依赖页面操作时，才新增浏览器或 UI 自动化分支。新增 provider 必须补齐配置、调度、错误处理、状态落盘、文档和测试。

## 3. 测试规范

### 3.1 原则

任何结构性改动都必须伴随测试迁移或新增。优先测试：模块是否接入、核心纯函数是否仍可验证、回退/停止/异常传播是否仍正确。

### 3.2 最低要求

- 改 JavaScript / TypeScript：至少运行该项目真实可用的语法、类型或测试入口；只有纯 JS 文件且无项目命令时，才退回 `node --check <file>`。
- 改 Python：至少对修改过的 Python 文件运行 `python -m py_compile <file>`，若项目有 `pytest`、`unittest`、`ruff`、`mypy` 或 CI 入口，以项目真实命令为准。
- 改 Go / Rust / Java / 其他语言：运行该语言和本项目真实使用的最小语法、类型、测试或构建检查，例如 `go test ./...`、`cargo test`、`mvn test`；不可硬套 Node/JS 规则。
- 改核心逻辑：运行项目当前真实回归命令；如果清单、README、长期文档、CI 配置和实际可运行命令冲突，以当前实际可运行命令为准，并说明证据。
- 改文档-only：至少做文档内容、链接和乱码检查。
- 测试失败时不得提交；除非用户明确要求保留失败状态用于排查，否则必须先修复。

### 3.3 evidence matrix（声明与证据矩阵）

基线中的每条验收标准必须使用稳定的 `acceptance_criteria[].id`，并通过 `acceptance_criteria[].evidence_kinds` 声明所需证据；PRD 采用同一组 ID。最低证据按声明类型确定：

| 声明 | 必须提供的证据 |
| --- | --- |
| `service` 可用/故障已修复 | `listener` + `health` + `original-symptom E2E` |
| `UI` 正确/可用 | 适用时的 `approved reference` + `rendered screenshot` + `navigation/hit-test` + `regression` |
| `online/deployed` | 真实入口的 `entry-point readback` |
| `restart durability` | 实际 `restart/recovery` 验证 |

单元测试、源码阅读或配置检查只能作为辅助证据，不能单独证明运行态、UI、上线或重启持久性声明。验收项没有所需证据时保持未完成。

## 4. 文档更新规范

必须更新长期文档的场景：

- 文件新增、删除、重命名或职责变化：更新 `项目文件结构说明.md`。
- 功能链路、运行模式、状态流、输出文件、故障归因变化：更新 `项目完整链路说明.md`。
- 开发流程、架构边界、测试要求、协作约束变化：更新当前文件。

不能只改代码不改文档；不能让链路文档落后于真实实现；不能让临时方案文件替代根目录长期文档。

## 5. 乱码要求

所有中文文档、中文注释、中文日志、UI 文案、错误提示文案都必须避免乱码。修改任何包含中文的文件时，必须把乱码检查视为与功能正确同级的必做项。

## 6. AI 自检清单

每次修改后至少自问：

1. 我是否 always 读取了 `AGENTS.md`，并按 selective docs 表核对了本任务相关长期文档及更严格的本地必读要求？
2. 我这次新增逻辑是不是应该下沉到模块？
3. 我有没有漏掉配置、状态、日志、错误处理、测试或文档中的一环？
4. 我有没有补或迁移测试？
5. 我有没有更新对应长期文档？
6. 我修改的中文内容是否无可见乱码？
7. 我有没有新增不必要的兼容分支、兜底分支或旧逻辑？
8. 如果本次涉及发布，我是否同步了版本号、`CHANGELOG.md`、tag、GitHub Release、Latest、中文更新日志、对比链接和验证证据？
9. 我有没有保护敏感文件，不回显真实 token、密码、API Key 或账号明细？
10. 如果本次是 Trellis 任务，我是否核对了 create/start/check/finish 真实状态，并在 finish 前执行对抗性检查、处理阻断发现？

## 7. 完成标准

满足以下条件时，才可以视为一次合格开发完成：

- 代码职责边界清晰。
- 新旧功能链路完整。
- 开发清单各阶段已逐项完成并自检。
- 每个 acceptance ID 都有 evidence matrix 要求的证据，关键路径及原始症状已验证。
- 根目录长期文档已同步。
- 没有可见乱码。
- Trellis 任务的对抗性检查已完成，且没有未处理阻断问题。
- 工作区范围已确认，没有误提交草稿、密钥、运行态数据或无关文件。
- 机器可读 completion receipt 已通过 validator；未通过时不得声称完成。

## 8. completion receipt 与最终回执

`init` 或 `task` 声称完成前必须生成 `schema_version: 1` 的机器可读 completion receipt，并使用 DXM validator 校验。Trellis 任务必须先通过对抗检查，把最终 `check.md` 的文件首个非空行写成顶格独立的 `<!-- DXM-CHECK:PASS -->`，确保该片段全文只出现一次且不存在其他或未闭合 `DXM-CHECK` 片段；执行 `finish`，再执行 `task.py archive <task> --no-commit`。只有归档完成后，才在 `.trellis/tasks/archive/<YYYY-MM>/<task>/completion.json` 生成回执并执行：

```text
python "<skill-dir>/scripts/validate_dxm.py" receipt --root "<project-root>" --file .trellis/tasks/archive/<YYYY-MM>/<task>/completion.json
```

普通 `finish` 不等于可审计的完成事实；归档前不得预写 `finished: true`。归档必须携带 `--no-commit`，避免 Trellis 默认行为绕过用户的 Git 授权边界。CLI/file 校验必须确认输入就是归档 task 的真实 `completion.json`，且归档月份目录严格匹配 `YYYY-MM`；baseline/receipt 会规范化 credential-like key 并向嵌套容器传播检查，凭据上下文只允许显式 env 引用或白名单脱敏占位，错误只报安全字段路径且不得回显凭据。

schema 必须与 validator 一致：

- `workflow_mode` 与 `project_root`，后者必须是 root/mode/scope lock 的规范化根目录；
- `requirements[]` 中每项的 `id`、`status`（完成时为 `passed`）和 `evidence_kinds`；
- `evidence` 按 requirement ID、kind 映射到安全证据引用列表；
- `adversarial_check.passed` 与摘要；
- `quality_checks` 下的 `docs`、`encoding`、`secrets`、`rollback` 布尔结果；
- `trellis.required`，以及适用时的 `task`、`check_passed`、`finished` 真实状态；
- `git.commit_performed` / `commit` 和 `push_performed` / `branch` 真实状态；只记录事实，不得自动执行 Git 操作。

缺需求、缺证据、对抗检查失败、`check.md` 缺失/非 PASS/格式不合法、非规范月份目录、可信 root 不一致、高置信凭据或虚假 Trellis 完成状态时，validator 必须拒绝。scope 由任务锁、diff 审查和对抗检查单独执行；发现扩范围同样回到 implement/check，但不得伪称为 receipt schema 字段。

最终人类回执只能忠实摘要已验证的 completion receipt，并简明说明：

1. 改了什么。
2. 是否遵守本规范，尤其是架构边界、文档同步、测试和乱码检查。
3. 跑了哪些测试、evidence matrix 验收或检查；如是 Trellis 任务，还要说明对抗性检查和 finish 状态。
4. 是否提交、提交号是什么。
5. 是否推送、推送到哪个分支。
6. 如涉及发布，必须说明 `VERSION`、`CHANGELOG.md`、tag、GitHub Release URL、Latest 校验、中文 Release notes、对比链接和验证证据。
7. 如果有未完成项、未运行测试、缺失证据或残余风险，必须明确说出。

<!-- DXM-TRELLIS:START -->

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
每次需求澄清先从第一性原理出发并质疑隐藏假设，本地证据优先、单批 0–3 个阻塞问题；每次 Trellis 任务完成后先做对抗性检查，再按 `finish` → `archive <task> --no-commit` → 归档回执校验收口。

<!-- DXM-TRELLIS:END -->
