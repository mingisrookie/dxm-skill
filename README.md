# DXM 项目协作

**需要时增强，不需要时不介入。**

DXM 是一组纯文本技能，帮 AI 补齐三类缺口：项目背景、关键决策、交付证据。规划、调查和实现仍由模型自己完成。

## 当前版本

当前源码版本为 **3.1.0-dev（未发布）**。已发布的最新版本是 v3.0.1，见 [GitHub Release](https://github.com/mingisrookie/dxm-skill/releases/tag/v3.0.1)；其下载包不包含本轮修改，且仍是五个技能的旧结构。

## 安装

1. 下载 Release 中的压缩包并用 `SHA256SUMS` 校验，或直接克隆本仓库。
2. 把需要的技能目录整个复制到宿主的技能目录。常见位置是 Codex 的 `~/.codex/skills/` 和 Claude Code 的 `~/.claude/skills/`（或项目内的 `.claude/skills/`），以宿主当前文档为准。
3. 开启新会话，确认宿主列出的技能描述与 `SKILL.md` 一致。

| 技能 | 作用 | 是否必需 |
| --- | --- | --- |
| `skills/dxm` | 项目背景、关键决策、交付证据与授权边界 | 核心 |
| `skills/grilling` | 逐题压力测试方案，可对照已有代码和文档 | 可选 |
| `skills/domain-modeling` | 业务术语和难以逆转的取舍记录 | 可选 |

技能之间互不依赖，没有运行时脚本，也不需要 Python。从 v3.0.1 升级时，手动移除已并入 `grilling` 的 `grill-me` 和 `grill-with-docs` 安装目录；从 v2 升级见 [迁移说明](docs/migration-v3.md)。

## 怎么使用

用自然语言即可，`/dxm` 用于维护项目协作规则。

“直接修。”目标清楚、证据齐全就直接做，技能不介入。

“继续 Tesla 项目。”按项目身份和本次问题找相关资料，读到足以行动为止；同一客户的多个项目分开处理，读不到资料会如实说明。

“这个方案 grill 我一下。”先查证据，然后一轮一个关键问题，附建议和取舍；喊停就汇总结论，结束访谈本身不构成实施授权。

“为什么又失败了？”下一步选能区分原因的检查。交付时，源码已改、测试通过、运行生效、已推送、已发布分别对应各自的证据。

宿主是否自动选中技能取决于宿主和模型。想让这些行为常驻生效，用 `/dxm` 把 [项目约定示例](skills/dxm/assets/templates/AGENTS.md.template) 并入项目的规则文件。

## 已知局限

技能效果尚未经过真实模型评估，本仓不宣称它更快、更便宜或成功率更高。待执行的对照场景见 [评估场景](docs/evals/scenarios.md)。仓库内的自动测试只验证包结构、引用、编码和发布打包。

## 开发验证

```text
python -B -m unittest discover -s tests -v
git diff --check
```

CI 在 Ubuntu、Windows、macOS 的 Python 3.10、3.12、3.14 上运行整个测试目录。

## 维护者发布

版本号与中文更新日志一致后，推送正式版本标签。CI 先运行九组完整测试，再构建核心包和完整技能包，上传 Release 草稿，重新下载并核对 SHA-256，最后发布并检查 Latest。`tools/package_release.py` 仅用于本仓打包。

## 参考

[Codex 技能加载与调用策略](https://developers.openai.com/codex/skills/)；[Claude Code 技能触发与加载](https://code.claude.com/docs/en/skills)。
