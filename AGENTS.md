# AGENTS.md — DXM 大项目 AI 协作规则

<!-- DXM-RULES:START -->

<!-- DXM-CONTRACT:1 -->

本目录已启用 DXM。`AGENTS.md` 是 always 必读入口；详细开发、验收、文档同步和完成门集中在 `项目开发规范（AI协作）.md`。

## 四模式状态机

每次工作只选择一个模式，并建立 **root/mode/scope lock**。首次写入前必须锁定规范化项目根目录、当前模式和允许影响范围；路径、`.dxm/project.json` 根目录或任务范围不一致时先停止写入并解决冲突，不得静默换根或扩范围。

| 模式 | 选择条件 | 硬约束 |
| --- | --- | --- |
| `audit` | `只分析`、`先看看`、`暂时不改`、review/排查，或用户尚未授权改变状态 | 严格只读：不 scaffold、不创建 Trellis task、不改变运行态、不写文件。 |
| `init` | 首次建立项目基线和治理文档 | 先查证、做有界澄清、落盘基线、非破坏式 scaffold，再审计 readiness。 |
| `task` | 在已有 READY/PARTIAL DXM 工作区执行任务 | 沿用基线，不重复初始化；锁定本任务范围并收集验收证据。 |
| `scaffold-only` | 用户明确说 `scaffold only`、`只生成模板`、`先别问` | 只生成/刷新模板；不访谈、不创建 task、不宣称 READY。 |

分析型措辞默认进入 `audit`；除非用户明确要求初始化或开发。scaffold 成功不等于项目 READY。

## `/dxm` 有界建档

`init` 默认执行以下唯一 project-grill 契约：

1. 先从**第一性原理**识别真实目标、硬约束、本地事实和未知阻塞，主动**质疑隐藏假设**、伪约束、过度方案和实现偏置；再执行**本地证据优先**，查锁定根目录内的代码、README、manifest、配置、测试、文档、日志和安全运行态，本地能查清的事实不得反问。
2. 只把会改变下一步安全动作、范围或验收契约的问题视为阻塞问题；默认 **单批提出 0–3 个阻塞性问题**。
3. 非阻塞选择给出推荐假设后继续。用户说 `按推荐走`、`直接做` 或同义表达时，立即关闭剩余非阻塞澄清。
4. 完整/穷举、逐题 `grilling` 仅 **explicit opt-in**；只有用户明确说 `grill me`、`完整 grilling`、遍历所有分支时才启用，默认 init 不得使用 exhaustive cadence。
5. 阻塞答案未解决前不得 scaffold；没有阻塞问题时问 0 个，记录假设后继续。

澄清 profile：

- `grill-with-docs`：已有代码/文档时先查证，再做同一套 0–3 有界澄清。
- `new-project-grill`：空项目，仅问用户、交付、核心范围、约束和验收中的未决阻塞项。
- `lightweight-grill`：脚本/demo，仅问输入输出、成功标准和允许副作用中的阻塞项。
- `grill-me`：legacy 可选别名；不是 DXM 硬依赖。
- `domain-modeling`：仅当稳定术语、上下文边界、context map 或 ADR 决策确实新增/变化时写入；普通查证不创建这些文件。

核心 DXM 在没有上述 sibling skill 时也必须能以内联有界问答完成建档。

确保根目录存在：

- `AGENTS.md`
- `项目开发规范（AI协作）.md`
- `项目完整链路说明.md`
- `项目文件结构说明.md`
- `开发者AI开发与PR提交流程.md`

已有人工内容不得静默覆盖。真实 Markdown marker 孤立、重复、交叉、乱序、非规范或未闭合时停止，不得继续追加；完整 fenced/inline code 中的 marker 示例不算活动块，未闭合 fence 不能隐藏错误。baseline/receipt 会规范化 credential-like 字段名并向嵌套容器传播检查；除显式环境变量引用或白名单脱敏占位外，凭据上下文中的 literal 必须拒绝，错误不得回显 key/value。建档后用只读 audit 区分 `ABSENT` / `PARTIAL` / `READY` / `BROKEN`；`PARTIAL`、`BROKEN` 不得输出成功式下一步。

脚本写入必须显式携带模式锁：`init` 使用 `--mode init --baseline <baseline.json>`，缺 baseline 时必须在任何写入前失败；模板专用使用 `--mode scaffold-only`，不得携带 baseline，输出 `readiness: NOT_EVALUATED`。不带 `--mode` 的旧 CLI 只用于兼容，不能证明完成了 init gate。

## Trellis 路由

- 小修、只读、单点 bug、轻量文档：DXM inline，不建 task。
- 新功能、多模块、架构变化、跨文件重构、长周期：建议一次 Trellis；用户请求已明确批准时可进入。
- Trellis PRD 写入 `.trellis/tasks/<task>/prd.md`，create/start/check/finish 状态必须真实。
- 显式 Trellis 请求遇到 CLI 缺失、超时或失败时，普通 DXM 文件可以已生成，但 DXM + Trellis 整体不得报告成功。
- finish/handoff 前执行对抗性检查；阻断发现回到 implement/check。
- 不得自动 stage/commit/push/PR/tag/release；Git 操作仍需用户明确授权。

## selective docs（选择性必读）

`AGENTS.md` always 必读，再按受影响面加载：

| 受影响面 | 追加必读 |
| --- | --- |
| 任意代码、配置、测试或文档写入 | `项目开发规范（AI协作）.md` |
| 文件新增/删除/重命名、目录职责 | `项目文件结构说明.md` |
| 入口、运行态、配置/状态/数据流、service/UI 链路 | `项目完整链路说明.md` |
| Git/PR/合并/version/tag/release/publish | `开发者AI开发与PR提交流程.md` |

如果当前项目规则声明了更严格的开发前必读集合，遵守更严格规则；selective docs 只减少无关上下文，不削弱项目约束。

## evidence matrix 与完成门

基线/PRD 用稳定 `acceptance_criteria[].id` 和 `acceptance_criteria[].evidence_kinds` 绑定验收与证据。service 要 listener + health + original-symptom E2E；UI 要适用时的 approved reference + rendered screenshot + navigation/hit-test + regression；online/deployed 要 real entry-point readback；restart durability 要 restart/recovery。单测或配置/源码检查不能单独证明这些运行态声明。

`init` 或 `task` 报告完成前，必须生成并通过 `schema_version: 1` 的机器可读 **completion receipt** 校验。回执用 `workflow_mode`、规范化 `project_root`、`requirements[].id/status/evidence_kinds` 和按 ID/kind 组织的 `evidence` 绑定声明与证据；同时记录 `adversarial_check`、`quality_checks.docs/encoding/secrets/rollback`、`trellis.required/task/check_passed/finished` 和 `git.commit_performed/commit/push_performed/branch`。Trellis 必须先在无阻断项的最终 `check.md` 中把 `<!-- DXM-CHECK:PASS -->` 写成文件首个非空、顶格独立的行，且全文只出现一次、不得存在其他或未闭合 `DXM-CHECK` 片段；再按“`finish` → `task.py archive <task> --no-commit` → 在 `.trellis/tasks/archive/<YYYY-MM>/<task>/completion.json` 生成并校验回执”收口。CLI/file 校验还必须把输入路径绑定到该真实归档文件，归档前不得预写 `finished: true`，`--no-commit` 不得省略。缺失或非 PASS verdict、非规范月份目录、凭据 key/value 或其他校验失败均不得声称完成。

## 红线与文档同步

- 先用真实文件、命令输出、日志、测试、diff 和运行态证据建立结论。
- 新功能沿现有分层接入，不能把逻辑堆回主入口或无关模块。
- 文件职责变化更新 `项目文件结构说明.md`；运行/状态链变化更新 `项目完整链路说明.md`；流程/架构/测试规则变化更新 `项目开发规范（AI协作）.md`。
- 发布工作不是只 push main；涉及发布 / release / version / latest / tag 时读取 `开发者AI开发与PR提交流程.md`，核对完整发布面和真实入口证据。
- 中文文档、注释、日志、UI 文案和错误提示出现乱码视为未完成。
- 不回显 token、密码、API Key、账号、验证码、会话或密钥内容。
- 最终人类回执必须忠实摘要已验证的 completion receipt、未运行检查和残余风险，不能只说“已完成”。

<!-- DXM-RULES:END -->

## 本仓更严格的开发前必读

本仓维护的是 DXM 契约本身。任何涉及代码、测试、脚本、配置或文档写入的任务，除 always 阅读本文件外，开始前必须实际阅读或重新核对：

1. `项目文件结构说明.md`
2. `项目完整链路说明.md`
3. `项目开发规范（AI协作）.md`
4. 涉及 Git/PR/version/tag/release/publish 时再读 `开发者AI开发与PR提交流程.md`

这是本项目对通用 selective docs 的更严格覆盖，不能因模板默认规则而省略。

<!-- DXM-TRELLIS:START -->

## DXM + Trellis 大开发路由

Trellis 是 DXM 下面的中大型任务持久层，不替代本目录长期文档。

- 小修、只读排查、单点 bug、轻量文档调整：默认按 DXM inline 处理，不强制创建 Trellis task。
- 新功能、架构变化、跨多文件重构、长周期任务：先用 DXM core 做本地证据优先、单批 0–3 个阻塞问题的有界 project-grill；用户已批准 Trellis 时，再把结论落到 `.trellis/tasks/<task>/prd.md`。
- `grill-with-docs` 可在已安装且任务描述匹配时用于已有代码/文档的有界查证，但仍必须遵守单批 0–3 个阻塞问题；full `grilling` / legacy `grill-me` 只有用户 explicit opt-in 完整/穷举澄清时才调用。它们都不是 Trellis 硬依赖。
- 提问前从第一性原理判断真实目标、硬约束、本地可查事实和仍阻塞的问题，并质疑隐藏假设、过度方案、伪约束和用户给出的实现偏置；本地可查事实不得反问。
- 用户明确说 `scaffold only`、`先别问`、`只分析` 时，不进入 Trellis，不擅自改文件。
- 每次 Trellis 任务完成前必须执行对抗性检查；发现阻断问题就回到 implement/check。通过后按 `finish` → `archive <task> --no-commit` → 归档目录 completion receipt 校验收口。
- Trellis 不得自动 stage/commit/push/PR；提交和推送仍需用户明确授权。

<!-- DXM-TRELLIS:END -->
