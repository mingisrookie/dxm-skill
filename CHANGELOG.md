# Changelog

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
