# 开发者 AI 开发与 PR 流程

> 项目：`dxm`
> 根目录：`G:\dxm`
> 初始化日期：`2026-07-09`

AI 在本项目里进行开发、整理改动、发起 PR、更新 PR、补充说明或合并时，必须按本文执行，不能跳步、不能猜、不能自创流程。

<!-- DXM-DOC-RULES:START -->

## DXM 文档维护规则

- 本块由 DXM 管理；`--refresh-blocks` 只刷新本块，保留下方项目专属 Git/PR 规则和人工补充。
- GitHub、PR、提交、推送、合并相关结论必须基于真实命令输出和真实 diff。
- 未获用户明确授权时，不得 stage、commit、push、创建 PR、合并 PR、关闭 PR、删分支、强推、创建/推送 tag、创建/编辑 GitHub Release 或修改 Latest。
- PR 文案必须基于真实改动和验证结果，不写机器人腔或空泛结论。

<!-- DXM-DOC-RULES:END -->

## 使用前准备

在让 AI 操作 GitHub 之前，开发者本机必须先安装 GitHub CLI，并完成登录。

最低要求：

```bash
gh --version
gh auth status
git status --short --branch
git remote -v
```

如果 `gh` 不可用、未登录、登录到错误账号、权限不足，AI 必须停止并明确告诉开发者，不准假装已经完成 GitHub 操作。

## 适用场景

本文适用于：

- 发起新的 PR。
- 更新已有 PR。
- 在自己的 PR 下补充说明。
- 在权限允许且用户明确授权时，合并自己的 PR。
- 发布版本、更新 Latest、创建或更新 GitHub Release、补充 release notes。

不适用于：

- 当前目录不是 Git 仓库时强行执行 Git/PR 流程。
- 没有看代码上下文就靠猜测生成 PR 结论。
- 用户没有明确授权时擅自合并、关闭 PR 或删除远端分支。

## 仓库硬性规则

1. 任何结论都不能猜，必须基于真实命令输出、真实 diff、真实代码上下文。
2. 发起 PR 前必须确认目标分支策略；如果项目有 `dev` 分支，默认 PR 指向 `dev`，否则先询问或按项目文档执行。
3. 发起 PR 前必须同步最新远端提交，确认当前分支已经吸收目标基线。
4. 当前工作区有无法确认归属的脏改动时，必须先停下来告诉开发者，不能偷偷带进本次 PR，也不能擅自删除。
5. PR 标题、正文、评论用自然中文直接表达，不写“自动回复”“AI 分析结果如下”这类机器人腔。
6. 没有开发者明确授权时，不得合并 PR、关闭 PR、删除远端分支或强推。

## 标准执行顺序

### 阶段 1：环境确认与仓库现状检查

必须先执行并阅读：

```bash
git status --short --branch
git remote -v
gh auth status
```

确认：当前仓库、当前分支、远端地址、工作区脏改动、GitHub 登录身份。

### 阶段 2：对齐目标基线

新任务应从最新目标基线拉出功能分支。继续已有分支时，必须判断当前分支是否落后于目标基线；可以先继续开发，但发 PR 前必须补齐最新基线。

### 阶段 3：开发与本地整理

AI 开发时必须遵守 `项目开发规范（AI协作）.md`。PR 中只能包含与本次任务相关的改动，不要带入临时调试代码、无关格式化、构建产物、运行态数据或密钥文件。

提交信息必须描述真实功能结果，不写 `update`、`fix`、`AI 修改` 这类空泛信息。

### 阶段 4：发起 PR 前再次同步

准备发起 PR 前，必须再次拉取远端最新提交，并确认当前分支已经吸收目标基线。冲突解决后必须重新检查 diff，不能只删除冲突标记。

### 阶段 5：创建或更新 PR

创建 PR 前先确认目标分支。示例：

```bash
gh pr create --base <target-branch> --head <feature-branch> --title "<PR标题>" --body-file <PR正文文件>
```

如果 PR 已存在：

```bash
gh pr view <PR_NUMBER> --json number,title,baseRefName,headRefName,state,isDraft,url
```

PR 正文建议包含：

```markdown
## 本次改动
-

## 风险与影响
-

## 测试情况
-
```

正文必须基于真实改动和真实验证结果。

### 阶段 6：只有明确授权时才允许合并

如果开发者明确要求 AI 继续合并自己的 PR，必须先确认：

```bash
gh pr view <PR_NUMBER> --json number,title,baseRefName,headRefName,state,isDraft,mergeable,mergeStateStatus,url
```

合并前必须满足：PR 仍 open、不是 draft、目标分支正确、没有未处理冲突、已完成项目要求的验证、开发者明确授权合并。

合并成功后必须验证 PR 状态和本地目标分支是否更新，不能把“同步 PR 分支”和“合并 PR 到目标分支”混为一谈。

## 发布 / Release 工作流

发布工作不是只 push main。用户要求“发布”“更新 latest”“打版本”“发 release”或类似表达时，必须同时核对这些公开表面：

1. 版本文件：`VERSION`、包管理器版本、应用版本或项目真实使用的版本来源。
2. 更新日志：`CHANGELOG.md` 必须新增本次版本条目，说明本次版本的真实变更、修复、验证和已知风险；如本次是规则沉淀或踩坑复盘，再说明来源。
3. Git 状态：提交前确认 `git status --short --branch`，不能带入无关文件、运行态文件或密钥。
4. Tag：获得明确授权后，创建并推送对应版本 tag，例如 `v1.0.0`。
5. GitHub Release：获得明确授权后，创建或更新 `GitHub Release`，并确认它是需要的 `Latest`。
6. 中文更新日志：Release notes 默认使用中文，至少包含“更新日志 / 验证 / 完整更新记录”。
7. 对比链接：Release notes 必须包含上一版本到当前版本的对比链接。
8. 验证证据：Release notes 和最终回执都必须列出实际运行过的测试、自检、版本/tag/latest 核验结果。

授权边界：未获明确授权时，只能准备版本文件、`CHANGELOG.md`、Release notes 草稿和待执行命令清单；只有用户明确要求发布/推送/tag/release 后，才允许执行远端写操作。

发布完成前必须实际检查，且先绑定当前仓库和版本变量：

```bash
$repo = gh repo view --json nameWithOwner --jq .nameWithOwner
$branch = git branch --show-current
$tag = "v$(Get-Content VERSION)"
git rev-parse HEAD
git rev-parse $tag
git ls-remote origin refs/heads/$branch refs/tags/$tag
gh release list -R $repo --limit 5
gh release view $tag -R $repo --json tagName,name,body,url,publishedAt
gh api repos/$repo/releases/latest --jq .tag_name
```

`gh api repos/$repo/releases/latest --jq .tag_name` 必须返回当前 `$tag`，否则不能声称 `Latest` 已更新。本地 HEAD、远端分支和 tag 指向的提交必须一致，不能让 tag 指到旧提交。

如果 `main` 已推送但 `VERSION`、`CHANGELOG.md`、tag、`GitHub Release` 或 `Latest` 没同步，发布不算完成。

## 最终反馈必须说明

1. 当前分支与工作区状态。
2. 改了哪些文件。
3. 是否创建或更新 PR。
4. PR 编号、链接和目标分支。
5. 是否提交、提交号是什么。
6. 是否推送、推送到哪个分支。
7. 运行过哪些测试或检查；如果没跑，要明确说明。
8. 是否已经合并；如果已合并，要说明合并目标、PR 状态和合并提交。
9. 如果本次涉及发布，必须说明 `VERSION`、`CHANGELOG.md`、tag、GitHub Release URL、Latest 校验、中文 Release notes、对比链接和验证证据。
10. 未完成项、阻塞或风险。
