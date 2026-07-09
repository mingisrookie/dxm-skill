# 更新日志

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
