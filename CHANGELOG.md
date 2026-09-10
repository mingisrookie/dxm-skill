# 更新日志

## v3.0.1 - 2026-09-10

- 包含下方 v3.0.0 的全部重构：完全移除 Trellis，保留 Grill、领域知识、真实验证和授权边界。
- 修复 Windows 默认编码下读取中文 CI 配置的问题；测试和打包工具显式使用 UTF-8，新增防止依赖默认编码的回归检查。
- v3.0.0 的 Windows CI 未通过，因此未创建公开 Release；保留其候选标签，不改写已推送历史。
- 提供核心包、包含 Grill 的完整技能包和 SHA256SUMS；仅在完整跨平台测试与下载回验通过后发布。

**完整更新记录：** [v2.0.0...v3.0.1](https://github.com/mingisrookie/dxm-skill/compare/v2.0.0...v3.0.1)

## v3.0.0 - 2026-09-10（候选，未发布）

### 变更

- 删除 Trellis 集成、旧工作流 CLI/内部模块、任务契约和固定文档生成模板，不保留兼容层。
- 保留并改进深入 Grill、证据型澄清、领域术语、重要决策、真实验证和授权边界。
- 不再强制状态文件、固定文档数量、机器回执或额外流程审批；按风险使用参考资料、验证和交接记录。
- 统一访谈停止规则，修复领域建模在只读讨论中可能自动写入的规则缺口。
- 提供带原许可证的独立核心包和完整技能包，增加避免覆盖安装残留旧模块的迁移说明。
- CI 运行完整当前测试目录；标签发布增加版本绑定、精确包内容校验、可重现打包和 SHA-256 下载回验。

### 验证与边界

- 本地完整测试与 `git diff --check`；五个技能分别进行可移植性检查。
- CI 配置覆盖 Ubuntu / Windows / macOS 的 Python 3.10、3.12、3.14；全部通过后才允许发布。
- 发布任务从 GitHub 重新下载资产，与 SHA256SUMS 比对，再核验标签、主分支、Release 和 Latest。
- 尚未执行真实模型 A/B 评估。发布不会自动更新用户级安装或已打开的会话。

**完整更新记录：** [v2.0.0...v3.0.0](https://github.com/mingisrookie/dxm-skill/compare/v2.0.0...v3.0.0)

## v2.0.0 - 2026-08-03

### 新增

- 新增 `dxm.py` 产品命令面：`init`、`scaffold-only`、`audit` / `status`、`doctor` 与显式 `recover` 共用核心实现，并提供稳定 JSON 输出。
- 新增 `contract/policy.json` 和标准库 policy loader，集中限定 inventory、Trellis 输入、lock 与 profile 的边界；baseline 支持 `lite`、`standard`（默认）和 `high-assurance`。
- 新增项目锁、同目录原子替换、transaction journal/backup 与恢复链路；中断写入或 stale lock 不再允许下一次 scaffold 直接叠加。
- 新增 Git worktree 本地状态保护：维护可移植 `.gitignore` 托管块、审计 `.dxm/` 忽略/跟踪状态、绝不自动执行 `git rm --cached`。
- 新增安全 inventory renderer：文件名只作为 JSON 数据输出，不读取文件内容，默认跳过工具状态目录并受深度、条目、字节与超时上限约束。

### 变更

- **P0 修复：** 显式 `--mode init` 的退出码现在严格等于 post-write readiness：`READY=0`、`BROKEN=2`、`PARTIAL=3`、`ABSENT=4`；`--output json` 分离 `operation_status`、`readiness`、实际 `exit_code`、`readiness_exit_code` 与 `issues`，并在参数边界错误时也返回稳定的 `DXM_E_INVALID_ARGUMENTS` JSON。
- v2 写入命令必须明确 `--mode init` 或 `--mode scaffold-only`；旧式省略 mode 调用返回 `DXM_E_MODE_REQUIRED`，`scaffold-only` 仅报告 `NOT_EVALUATED`。
- baseline/run/receipt 收紧未知字段、扩展命名空间、项目相对路径和 Windows 可移植性校验；receipt 的顶层、requirements、检查对象和 structured observation 只允许已声明字段，普通输入错误使用稳定错误码，默认不泄露 traceback。
- `.gitignore` 仅刷新完整、单独成行且顺序正确的 DXM marker；含尾随规则、嵌入 marker 或逆序 marker 一律拒绝，避免吞掉人工 ignore 规则。
- inventory 改为流式早停，并按最终 JSON（含截断元数据）计算 byte cap；宽目录、慢枚举和极小边界不再先无界排序或超过声明上限。
- journal recovery 绑定安全 operation ID、journal filename、entry schema 和 backup layout；恢复、audit、doctor 与 receipt 共同 fail closed 处理 pending/malformed transaction、unsafe state topology 和 stale lock。
- Trellis `session_auto_commit` 更新改为受限的顶层 Boolean adapter；无法安全理解的 YAML 形态会拒绝而不是用正则猜测改写。
- bounded grill、DXM 模板和 Trellis 注入统一为“本地证据优先、单批 0–3 阻塞问题、full grilling 必须显式 opt-in”；本地 independent review 明确仅是证据一致性/reviewer 字段分离门。
- CI 改为最小权限、完整 SHA pin，并覆盖 Ubuntu / Windows / macOS 的 Python 3.10、3.12、3.14、self-test 与 core entry-point smoke。

### 修复

- 修复 `init` 写入后审计为 `PARTIAL` / `BROKEN` 仍返回 0 的 P0 假成功。
- 修复目标 Git 仓中 `.dxm/` 可意外进入跟踪、inventory 文件名可破坏 Markdown、写入过程中断无恢复路径、普通本地 I/O 缺少统一错误契约等问题。
- 修复 profile/provenance 语义过度承诺：`high-assurance` 只要求记录外部可信边界验证过的 provenance 形状，本地 validator 不声称认证远端身份。

### 验证

- `python -B -m unittest discover -s tests -q`：231 项通过，2 项因当前 Windows 账号缺少目录 symlink 权限跳过；另执行 `scaffold_dxm.py --self-test`、core-only copy smoke、`dxm.py --version`、`validate_dxm.py audit --root . --require-trellis --json` 与 `git diff --check`。
- v2 回归覆盖 P0 退出码/JSON、Git privacy、lock/recovery crash window、安全 inventory、schema/path/profile、Trellis 配置 adapter 与 core package smoke。
- 发布时额外验证独立 reviewer PASS、归档 receipt、tag、GitHub Release/Latest 和 release asset 的干净再下载 SHA-256 manifest。

### 已知限制与迁移

- v2 不接受没有 `--mode` 的写入调用；调用方必须改为 `--mode init` 或 `--mode scaffold-only`。`init` 的 PARTIAL/BROKEN 非零退出应由自动化正确处理。
- DXM 可安全检查并恢复自己管理的文件事务；外部 `trellis init`、Git index 和远程 Release 都是显式边界，不会被本地 rollback 伪装为已恢复。
- local review/hash 不能证明可信身份；高保障项目仍需要在独立 CI/OIDC 或等效边界完成实际 provenance 验证。

**完整更新记录：** [v1.2.0...v2.0.0](https://github.com/mingisrookie/dxm-skill/compare/v1.2.0...v2.0.0)

## v1.2.0 - 2026-08-01

### 新增

- 所有可写 `init` / `task` 在实现前建立 lightweight `run.json`，锁定原始目标、范围、任务 outcomes、交付声明、证据类型、baseline impact、风险与 Trellis 路由；小而明确的修改保持 run-only，不再被迫创建 Trellis task。
- completion receipt 独立升级到 schema v2，用 `run_id` 与 `run_sha256` 精确绑定本次任务，而不是把项目 baseline 的全部验收项填成本次通过。
- 运行态声明使用带时间、主体、方法、结果和摘要的 structured observation；项目内 artifact 可用 path + SHA-256 绑定，isolated 证据必须证明最终产物和真实决定性分支。
- high-risk 发布、部署、live-data 和多模块架构任务要求不同 Agent 的独立复核；回执会绑定 canonical `independent-review.md` 的身份、时间、PASS verdict 和 SHA-256。

### 变更

- 交付层级改为从用户当时的任务目标推导：源码、配置或单测不能单独证明真实运行态；拿不到所需证据时必须报告 partial/blocked，不能静默缩小目标。
- 明确 source-only 可以完成源码交付，但必须记录 `unverified_boundaries`，且不得宣称已经生效、部署或在线修复。
- `baseline_impact` 现在要求每个 baseline ID 精确标记为 `affected` 或 `not_affected`；未触及项不得伪装成本次 freshly passed。
- DXM managed contract 升级到 v2；baseline 与 run 继续使用 schema v1，completion receipt 使用 schema v2，历史 receipt v1 仅能通过显式 `--legacy-v1` 做审计。
- 当前 installed DXM core 与源码发布面分开核验，版本、manifest、自测与 validator 行为必须从安装路径实际读回。

### 修复

- 阻止 completion receipt 通过自定义 requirements、旧 baseline 证据或无关 review 文件缩小原始任务后自证完成。
- 拒绝 `not_affected` 项携带 outcome/pass-padding 字段，并校验 run、receipt、canonical directory leaf 与大小写完全一致。
- 拒绝尾随点和 Windows 设备名等会折叠到同一路径的 run ID，关闭大小写与路径别名绕过。
- evidence 错误使用稳定索引，不再把不可信 requirement ID 或 evidence kind 原文回显到错误信息。
- `--legacy-v1` 严格限制为 schema v1 历史审计，不能接受或冒充当前 v2 completion。

### 验证

- `python -B -m unittest discover -s tests -v`：共 197 项，196 项通过，1 项因当前 Windows 账号缺少目录 symlink 权限跳过。
- source 与 installed `scaffold_dxm.py --self-test`。
- source 与 installed `validate_dxm.py --version`、`audit --require-trellis`、canonical run/receipt 校验。
- core-only 12 文件 source/installed SHA-256 manifest 一致性。
- 独立第二 Agent 对抗审查、`git diff --check`、strict UTF-8/乱码和 credential-shaped literal 检查。

### 已知限制与迁移

- 已打开的 Codex 会话可能缓存旧 skill；文件安装态更新后，新任务或重启才能可靠加载新规则。
- 仍使用 contract marker 1 的既有项目会被新版 audit 判为 `PARTIAL`，需用非破坏式 managed-block refresh 升级；baseline 数据本身无需升版。
- 按明确非目标，本地完成门不提供签名服务、强制命令包装器或 append-only ledger；拥有整个工作区写权限的操作者仍能伪造全部本地状态。

**完整更新记录：** [v1.1.0...v1.2.0](https://github.com/mingisrookie/dxm-skill/compare/v1.1.0...v1.2.0)

## v1.1.0 - 2026-07-13

### 新增

- 新增 `audit`、`init`、`task`、`scaffold-only` 四模式工作流，写入前锁定规范化项目根目录、工作模式和允许影响范围。
- 新增 `.dxm/project.json` 项目基线，以及 `ABSENT`、`PARTIAL`、`READY`、`BROKEN` 四态只读审计。
- 新增 `dxm_contract.py` 和 `validate_dxm.py`，统一 baseline、managed marker、readiness 与 completion receipt 契约。
- 新增机器可读 completion receipt，按验收 ID 和证据类型校验完成声明、对抗检查、质量门及 Trellis 归档事实。
- 新增策略契约、工作流案例、路径安全、隐私、readiness 和 receipt 回归测试。

### 变更

- `/dxm` 初始化改为本地证据优先，默认只单批询问 0–3 个真正阻塞的问题；完整逐轮 `grilling` 仅在用户明确要求时启用。
- 核心 DXM 不再依赖相邻访谈技能；`grill-with-docs` 保持有界可选路由，`grill-me` 仅作为旧环境兼容别名。
- 文档加载改为 `AGENTS.md` 始终必读，其余长期文档按受影响面选择性加载。
- Trellis 完成链路收紧为“对抗检查 → finish → `archive --no-commit` → 归档回执校验”。
- `agents/openai.yaml` 更新为当前 `interface` metadata 结构，并为 core-only 安装提供独立版本信息。

### 修复

- Trellis 命令缺失、超时、启动失败、非零退出或未产出完整集成时不再返回假成功。
- `scaffold-only` 明确输出 `NOT_EVALUATED`，不再把模板写入成功误报为项目 `READY`。
- 加固孤立、重复、交叉、乱序、非规范或未闭合 marker，以及未闭合 Markdown fence 的识别，避免在损坏文档上继续追加。
- 加固受管文件及祖先路径检查，拒绝越出 root、symlink、reparse point、多硬链接和非普通文件。
- 修复 Windows runner 中 trusted root 与 receipt 词法路径因临时目录或父级别名不同而误判越界；校验现先沿词法 root 检查内部链接节点，再确认解析后的目标仍在规范 root 内。
- Trellis 完成门只接受规范 `YYYY-MM` 归档目录，以及作为 `check.md` 文件首个非空、顶格独立行且全文唯一的 `<!-- DXM-CHECK:PASS -->`；其他或未闭合 marker-like 片段一律拒绝。
- baseline 与 receipt 会规范化 credential-like 字段名并向嵌套容器传播检查；除显式环境变量引用和白名单脱敏占位外，凭据 literal 按安全字段路径拒绝且不回显敏感值。
- 本地 `.dxm/project.json` 保留规范化绝对根目录；共享 Markdown 会先词法折叠 `.` / `..`，再使用 `$PROJECT_ROOT` / `$ABSOLUTE_PATH` 可移植投影，避免不同 clone 路径产生长期文档漂移。
- `scaffold-only` 的目标路径存在文件型祖先时，真实执行和 `--dry-run` 都返回结构化 exit 2，不再抛出 traceback。
- 修正 CI 文档与实际 workflow 不一致的描述，并将 `.codex/`、`.dxm/`、`.trellis/` 本地自用状态排除在发行产物之外。

### 验证

- `python -m unittest discover -s tests -v`：共 173 项，172 项通过，1 项因当前 Windows 账号缺少目录 symlink 权限跳过。
- `python skills/dxm/scripts/scaffold_dxm.py --self-test`
- `python skills/dxm/scripts/validate_dxm.py audit --root . --require-trellis --json`
- `python -m py_compile` 覆盖本轮 Python 文件。
- `git diff --check`
- UTF-8、LF、BOM、中文乱码和敏感信息检查。
- core-only 临时安装及本地 installed skill SHA-256 manifest 一致性检查。

### 已知限制

- 当前 Windows 账号无法执行目录 symlink 创建测试；hardlink、reparse/junction 和其他路径逃逸分支已有可执行覆盖。
- completion receipt 校验器核验回执与证据结构，不会重跑证据命令或独立查询 Git 远端。
- 已打开的 Codex 会话可能缓存旧 skill metadata，更新本地技能后需要重启 Codex。

## v1.0.4 - 2026-07-09

### 修复

- 将 `CHANGELOG.md` 全文统一为中文标题、中文小节和中文条目，保留必要的命令、路径、版本号和产品名。
- 复查 README 最新更新摘要与使用说明，去掉 `inline`、`task`、`marker` 等不必要英文散落表达。
- 更新 GitHub Release 说明为中文表述，并用 v1.0.4 作为包含文档修正的最新归档版本。

### 验证

- `python -m unittest discover -s tests -v`
- `python skills/dxm/scripts/scaffold_dxm.py --self-test`
- `git diff --check`
- UTF-8 / LF / 中文乱码检查

## v1.0.3 - 2026-07-09

### 新增

- 本仓启用 DXM 自用规则：根目录新增 `AGENTS.md` 和四份长期项目文档，后续维护也按 DXM 规则执行。
- 新增 `tests/test_doc_sync.py`，作为 `skills/dxm/SKILL.md`、生成模板和 `scaffold_dxm.py` 三处契约防漂移测试。
- 新增回归检查，确保 `--force` 风险说明与真实覆盖范围一致，并要求本仓链路文档描述真实 DXM 流程。

### 变更

- 重整 `skills/dxm/SKILL.md`，让 `/dxm` 的只读分支和只补模板分支更明确。
- 文档写明真实 Trellis 初始化命令 `trellis init --codex -u <developer> -y --skip-existing`，并说明 `--trellis-user` 的默认来源。
- 明确 `--force` 会覆盖已有 DXM 目标文件，只能在用户接受人工内容可能丢失时使用。
- 用本仓真实流程替换占位式链路说明，覆盖技能触发、脚手架 CLI、模板、Trellis 模式、测试和 CI。
- README 增加 v1.0.3 最新更新摘要，并同步 Trellis 命令表述。

### 验证

- `python -m unittest discover -s tests -v`
- `python skills/dxm/scripts/scaffold_dxm.py --self-test`
- `git diff --check`

## v1.0.2 - 2026-07-02

### 新增

- 新增 GitHub Actions CI，在 Ubuntu 和 Windows 上运行单元测试与打包后的 `--self-test`。
- 新增 Trellis 后置安全动作的试运行报告，方便在新项目上预览将要追加的 DXM 安全块。

### 变更

- 将 `--self-test` 收敛为安装与冒烟检查，内容断言统一放在 `tests/` 下维护。
- 扩展文件结构快照的跳过目录，覆盖常见虚拟环境、IDE、pytest、tox、mypy 和 ruff 目录。
- 不再仅凭 `config.json` 文件名把它判定为敏感文件；仍保留明确的凭据、密钥和服务账号匹配规则。
- 减少 README 中的版本重复，并说明手动复制技能前如何清理 `__pycache__/`。

## v1.0.1 - 2026-06-29

### 变更

- DXM 需求澄清现在明确要求先从第一性原理出发，再向用户提问。
- 调用 `grilling`、`grill-with-docs` 和旧版 `grill-me` 时，必须先质疑隐藏假设、伪约束、过度方案和用户给出的实现偏置。
- Trellis 任务在完成或交接前必须执行对抗性检查；发现阻断问题时回到实现/检查阶段。
- 同步已安装技能说明、生成模板、Trellis 管理块和打包自测断言。

### 验证

- `python -m unittest discover -s tests -v`
- `python skills/dxm/scripts/scaffold_dxm.py --self-test`
- `git diff --check`

## v1.0.0 - 2026-06-28

### 变更

- 基于真实开发和发布踩坑沉淀 DXM 规则：发布工作不再只看代码是否推到 `main`，必须同步版本号、`CHANGELOG.md`、tag、GitHub Release、Latest 状态、中文更新日志、对比链接和验证证据。
- 生成的 `开发者AI开发与PR提交流程.md` 增加发布 / Release 工作流，明确 GitHub 发布说明默认使用中文。
- 生成的 `项目开发规范（AI协作）.md` 增加发布完成面自检，避免遗漏公开发布表面。

### 验证

- `python -m unittest discover -s tests -v`
- `python skills/dxm/scripts/scaffold_dxm.py --self-test`
- `git diff --check`

## v0.3.2 - 2026-06-28

### 新增

- 在 `skills/` 下打包当前 grill 相关技能：`grilling`、`grill-with-docs`、`domain-modeling`，以及旧版 `grill-me` 别名。

### 变更

- 将 DXM 项目澄清路由同步到当前 `grilling`、`grill-with-docs` 和 `domain-modeling` 技能拆分，同时保留 `grill-me` 旧版别名。

## v0.3.1 - 2026-06-22

### 新增

- 新增 DXM 和 Trellis 管理块的不完整标记校验；出现只有 `START`、没有匹配 `END` 的标记时会明确失败，不再误报成功。
- `--refresh-blocks` 现在支持刷新 `DXM-TRELLIS`、`DXM-TRELLIS-START-STEP0` 和 `DXM-TRELLIS-WORKFLOW-OVERRIDE` 管理块。
- 新增 `--inventory-depth N`，用于把更深层级的项目路径纳入生成的文件结构快照。
- 新增 `--self-test`，让已安装技能无需完整仓库测试套件也能运行打包冒烟检查。

### 变更

- 敏感文件快照规则减少对普通源码和文档的误判，例如 `token_utils.py`、`password-reset.tsx`、`secret-management.md`；明确密钥文件仍会被保护。

## v0.3.0 - 2026-06-22

### 新增

- 新增 `--dry-run`，只报告脚手架动作，不创建或修改文件。
- 新增 `--refresh-blocks`，只刷新 DXM 管理标记块，保留块外人工内容。
- 新增 CLI 宽泛根目录保护，拒绝盘根、用户根、系统目录、依赖目录和构建产物目录；只有该宽泛路径确实是项目根时才传 `--allow-broad-root`。
- 长期文档模板新增 `DXM-DOC-RULES` 管理块，让生成后的规则可以非破坏式演进。
- 新增测试覆盖 LF 行尾、非 UTF-8 保护、标记幂等、Trellis 安全覆盖、试运行行为、敏感文件快照、宽泛根目录识别和 Trellis 预检失败。

### 变更

- 脚手架输出在所有平台统一为 UTF-8 与 LF 行尾。
- 更新任何 DXM 管理块前，先按严格 UTF-8 读取已有文件；遇到非法编码会提前失败，避免静默改写或混合编码。
- Trellis 模式在追加标记块前预检现有 DXM/Trellis 目标文件，降低部分写入失败风险。
- `项目开发规范（AI协作）.md.template` 的测试说明改为语言中立，不再默认假设 Node/JavaScript 项目。
- `AGENTS.md.template` 改为指向 `项目开发规范（AI协作）.md` 获取完整流程，只保留触发规则和红线摘要。
- 敏感文件快照匹配覆盖更多常见密钥文件，同时避免误判 `tokenizer.py`、`passwordless.md`、`secretary-notes.md` 这类普通文件。

### 修复

- 修复 Windows 下生成 CRLF，以及脚手架创建后追加 Trellis 块导致 CRLF/LF 混用的问题。
- 修复非 UTF-8 `AGENTS.md` 可能被写成混合编码文件的问题。
- 修复只有开始标记时可能重复插入 DXM/Trellis 标记的问题。
- 修复 Trellis 文档表述容易让人误解为跳过已有人工文档，而不是保留人工内容并追加管理块的问题。

## v0.2.0 - 2026-06-21

- 新增 DXM + Trellis 路由支持、安全覆盖和脚手架测试。
- 新增标准 DXM 模板，覆盖 `AGENTS.md`、项目开发规范、完整链路说明、文件结构说明和 AI/PR 流程文档。
