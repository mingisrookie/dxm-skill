# Changelog

## v1.0.1 - 2026-06-29

### Changed

- DXM requirements clarification now explicitly starts from first principles（第一性原理）before asking the user.
- Calls to `grilling`, `grill-with-docs`, and legacy `grill-me` now require adversarial questioning（质疑）of hidden assumptions, fake constraints, over-scoped solutions, and user-suggested implementation bias.
- Trellis task completion now requires an adversarial check（对抗性检查）before finish or handoff; blocking findings return the task to implement/check.
- Synced the installed skill guidance, generated project templates, Trellis managed blocks, and packaged self-test assertions.

### Verified

- `python -m unittest discover -s tests -v`
- `python skills/dxm/scripts/scaffold_dxm.py --self-test`
- `git diff --check`

## v1.0.0 - 2026-06-28

### Changed

- 基于最近真实开发和发布踩坑蒸馏 DXM 规则：发布工作不再只看代码是否推到 `main`，必须同步版本号、`CHANGELOG.md`、tag、GitHub Release、Latest 状态、中文更新日志、对比链接和验证证据。
- 生成的 `开发者AI开发与PR提交流程.md` 增加发布 / Release 工作流，明确 GitHub Release notes 默认使用中文。
- 生成的 `项目开发规范（AI协作）.md` 增加发布完成面自检，避免遗漏公开发布表面。

### Verified

- `python -m unittest discover -s tests -v`
- `python skills/dxm/scripts/scaffold_dxm.py --self-test`
- `git diff --check`

## v0.3.2 - 2026-06-28

### Added

- Bundled current grill-related skills under `skills/`: `grilling`, `grill-with-docs`, `domain-modeling`, and the legacy `grill-me` alias.

### Changed

- Synced DXM project-grill routing with the current `grilling`, `grill-with-docs`, and `domain-modeling` skill split while preserving `grill-me` as a legacy alias.

## v0.3.1 - 2026-06-22

### Added

- Added explicit incomplete-marker validation for DXM and Trellis managed blocks; a `START` marker without the matching `END` marker now fails loudly instead of returning success.
- Added Trellis managed-block refresh support for `DXM-TRELLIS`, `DXM-TRELLIS-START-STEP0`, and `DXM-TRELLIS-WORKFLOW-OVERRIDE` when `--refresh-blocks` is used.
- Added `--inventory-depth N` to include nested project paths in the generated file inventory.
- Added `--self-test` so an installed skill can run packaged smoke checks without the repository test suite.

### Changed

- Sensitive-file inventory now avoids token/secret/password/credential keyword false positives for common source and documentation files such as `token_utils.py`, `password-reset.tsx`, and `secret-management.md`, while preserving explicit secret-file matches.

## v0.3.0 - 2026-06-22

### Added

- Added `--dry-run` to report scaffold actions without creating or modifying files.
- Added `--refresh-blocks` to refresh DXM-managed marker blocks while preserving manual content outside those blocks.
- Added a CLI broad-root guard for drive roots, home roots, system directories, vendor/dependency folders, and build output folders; pass `--allow-broad-root` only when that broad path is intentionally the project root.
- Added `DXM-DOC-RULES` managed blocks to long-term document templates so generated guidance can evolve non-destructively.
- Added tests for LF-only output, non-UTF-8 protection, marker idempotency, Trellis safety overrides, dry-run behavior, sensitive-file inventory, broad-root detection, and Trellis preflight failures.

### Changed

- Scaffold output is now normalized to UTF-8 with LF line endings on every platform.
- Existing files are read as strict UTF-8 before any DXM-managed update; invalid encodings fail early instead of being silently rewritten or mixed.
- Trellis mode now preflights existing DXM/Trellis target files before appending marker blocks, reducing partial-write failure risk.
- Test guidance in `项目开发规范（AI协作）.md.template` is now language-neutral instead of assuming Node/JavaScript.
- `AGENTS.md.template` now points to `项目开发规范（AI协作）.md` for full process details and keeps only trigger rules plus red-line summaries.
- Sensitive-file inventory matching now covers more common secret files while avoiding keyword false positives such as `tokenizer.py`, `passwordless.md`, and `secretary-notes.md`.

### Fixed

- Fixed Windows CRLF generation and mixed CRLF/LF output when Trellis blocks were appended after scaffold creation.
- Fixed non-UTF-8 `AGENTS.md` handling that could previously create mixed-encoding files.
- Fixed duplicate DXM/Trellis marker insertion when only a start marker existed.
- Fixed Trellis documentation wording that implied existing hand-maintained docs were skipped rather than preserved with managed marker appends.

## v0.2.0 - 2026-06-21

- Added DXM + Trellis routing support, safety overrides, and scaffold tests.
- Added standard DXM templates for `AGENTS.md`, project development rules, full-chain docs, file-structure docs, and AI/PR workflow docs.
