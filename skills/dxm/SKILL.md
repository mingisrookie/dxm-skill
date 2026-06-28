---
name: dxm
description: Use when the user types "/dxm", asks to generate or refresh 大项目开发规范（AI协作） files, wants a folder to become a DXM large-project AI collaboration workspace, or asks for DXM + Trellis / 大开发模式 / project-grill workflow.
---

# DXM Large Project AI Collaboration

## Purpose

DXM turns a project folder into a governed AI collaboration workspace. It creates or refreshes the standard project rule files, then requires future analysis, development, testing, documentation, Git, PR, and handoff work in that folder to follow those local rules.

DXM is also the entry point for project clarification: first `/dxm` should normally ask enough questions to make the project understandable before the docs become the long-term source of truth.

## Trigger contract

### `/dxm`

When the user says `/dxm`:

1. Treat the current working directory as the target project root unless the user gives another path. Do not run this in a broad drive root like `G:\` unless the user explicitly says that is the project root.
2. If the user says `只分析`, `先看看`, or equivalent read-only language, do not scaffold or edit files. Inspect only and report what DXM would do.
3. If the user says `scaffold only`, `只生成模板`, or `先别问`, run the scaffold directly and do not grill.
4. Otherwise classify the target before scaffolding. `new-project-grill` and `lightweight-grill` are DXM mode labels, not required standalone skill names; execute them with the current grill skills (`grilling`, `grill-with-docs`, `domain-modeling`), the legacy `grill-me` alias, or concise inline questions as appropriate:
   - Empty folder / new project: use `new-project-grill` via `grilling` or the legacy `grill-me` alias.
   - Existing code or docs: run `grill-with-docs`, which routes the interview through `grilling` plus `domain-modeling`.
   - Temporary script / demo: run `lightweight-grill` with only blocking questions, using inline questions or `grilling` when useful.
   - Existing complete DXM docs: do not repeat grill unless the user asks to re-baseline.
   - Subdirectory misfire: tell the user to move to the project root; do not initialize the leaf folder.
   - vendor / dependency / build output: only initialize if the user says this is the thing they maintain or study.
5. Run the bundled scaffold script after the project intent is clear. Resolve `scripts/scaffold_dxm.py` relative to this skill directory. In a standard Codex install this is usually `%USERPROFILE%\.codex\skills\dxm\scripts\scaffold_dxm.py`; in a repo checkout use `skills/dxm/scripts/scaffold_dxm.py` relative to the checkout root.

```powershell
$skill = Join-Path $env:USERPROFILE ".codex\skills\dxm"
python "$skill\scripts\scaffold_dxm.py" --root "<project-root>"
```

Cross-platform checkout form:

```bash
python skills/dxm/scripts/scaffold_dxm.py --root "<project-root>"
```

6. Ensure these files exist in the project root:
   - `AGENTS.md`
   - `项目开发规范（AI协作）.md`
   - `项目完整链路说明.md`
   - `项目文件结构说明.md`
   - `开发者AI开发与PR提交流程.md`
7. Do not overwrite existing project-specific docs unless the user explicitly asks for overwrite. Existing docs are likely hand-curated and higher value than templates.
8. After scaffolding, read `AGENTS.md` and follow it for the rest of the session.
9. For read-only planning evidence, use `--dry-run` instead of guessing what scaffold would do. For non-destructive generated-block upgrades, use `--refresh-blocks`; it refreshes DXM and Trellis marker blocks while preserving manual content outside those blocks. Use `--inventory-depth N` only when the initial file-structure seed should include nested paths. Use `--self-test` to verify an installed skill package. The CLI also has a broad-root guard; use `--allow-broad-root` only when the user explicitly confirms the target really is a drive, home, system, vendor, or build root.
10. If the scaffold reports an incomplete managed block, do not ignore it or claim success. Restore the missing end marker or ask whether to overwrite the affected generated file.

### `/dxm trellis`

When the user says `/dxm trellis`, `/dxm 大开发`, `/dxm full`, or otherwise asks to enable DXM for large development workflow:

1. First satisfy normal `/dxm` behavior and project-grill expectations.
2. Run the bundled scaffold script with Trellis enabled:

```powershell
$skill = Join-Path $env:USERPROFILE ".codex\skills\dxm"
python "$skill\scripts\scaffold_dxm.py" --root "<project-root>" --trellis --trellis-user "<developer-name>"
```

3. This must remain non-destructive: DXM docs are created when missing, existing hand-maintained docs are preserved, DXM/Trellis marker blocks are appended once or refreshed only inside managed markers, incomplete marker pairs fail loudly, and Trellis is initialized non-interactively with `trellis init --codex -y --skip-existing`.
4. If `trellis` is not on PATH, finish the normal DXM scaffold and report that Trellis initialization was skipped because the CLI is missing.
5. When `.trellis/` exists, ensure the DXM safety overrides are present:
   - `session_auto_commit: false` in `.trellis/config.yaml`.
   - `trellis-start` Step 0 reads `AGENTS.md` and the DXM long-term docs first.
   - Trellis no-task workflow allows DXM inline work for small fixes and read-only analysis.
   - Trellis must not stage, commit, push, create PRs, or merge without explicit user authorization.
6. After scaffolding, read `AGENTS.md`; if `.trellis/` exists, also treat Trellis task files as part of the project workflow.

## Project-grill modes

Use these labels consistently so future sessions route the same way:

| Mode | Use when | Ask for |
| --- | --- | --- |
| `grill-with-docs` | Existing code, docs, README, manifests, scripts, or runtime evidence exist | Goal, current behavior, architecture boundary, domain terms/ADRs, risk, validation, non-goals |
| `new-project-grill` | Empty folder or a new project with no useful docs | User, delivery shape, stack preference, core scope, non-goals, data/API/security, acceptance criteria, maintenance horizon |
| `lightweight-grill` | Scratch, demo, one-off script, or very small utility | Only blockers: input/output, success criterion, allowed side effects |

`new-project-grill` and `lightweight-grill` are routing labels. If no same-name skill exists, use `grilling` or direct inline questions; `grill-me` remains only a legacy alias. If existing docs/code are available, prefer `grill-with-docs`; when domain terms or ADRs change, also use `domain-modeling`.

Default principle: first `/dxm` is a project setup conversation. Skip grill only for explicit scaffold-only/read-only intent, existing complete DXM, or wrong target directory.

## Trellis routing policy

DXM is the global project rule layer. Grill is the clarification step. Trellis is the durable task layer for medium/large work.

Do not require the user to remember `/dxm trellis`. The agent must proactively classify task scale:

| Task | Default |
| --- | --- |
| Read-only analysis, log review, explanation | DXM inline; no Trellis task |
| Small bug, one-file fix, light docs | DXM inline; no Trellis task unless requested |
| New feature, new module, architecture change, cross-file refactor | Recommend or default to Trellis |
| Requirements unclear and work will continue | project-grill first; Trellis if PRD/check memory matters |
| Multi-stage or likely to span sessions | Trellis task required unless user opts out |

Suggested wording for medium/large tasks:

> 我判断这是中大型/长期任务，建议走 Trellis：先 project-grill 问清楚，再写入 task PRD 后执行。可以吗？

Suggested wording for small tasks:

> 我按小修 inline 处理，不建 Trellis task。

## Standard behavior inside a DXM workspace

Before any non-trivial code, test, script, config, documentation, Git, PR, or release work:

1. Read `AGENTS.md`.
2. Read or re-check the three project maintenance docs:
   - `项目文件结构说明.md`
   - `项目完整链路说明.md`
   - `项目开发规范（AI协作）.md`
3. If Git/PR/release/version/latest work is requested, also read `开发者AI开发与PR提交流程.md`.
4. Resolve conflicts by observed runtime and current files first, then docs. If docs are stale and the task changes facts, update the docs before reporting completion.

## DXM operating rules

- Separate user intent: `只分析/先看看` means read-only; `开始开发/直接改/提交` means execute to verified completion.
- Use evidence, not memory: inspect files, configs, commands, diffs, tests, listeners, logs, and runtime output.
- Phase work: plan the affected chain, change one stage at a time, verify each stage, then run a final global review.
- Preserve architecture boundaries: do not pile new logic into a main file when an existing module, provider, service, route, manager, or helper layer owns it.
- Keep code and docs synchronized: file-structure changes update `项目文件结构说明.md`; runtime-flow changes update `项目完整链路说明.md`; process/boundary changes update `项目开发规范（AI协作）.md`.
- Treat Chinese encoding as a completion blocker. Check modified Chinese docs, logs, comments, and UI strings for visible mojibake or replacement characters.
- Protect secrets and runtime data. Never paste real tokens, passwords, API keys, account lists, or credential-bearing state into reports.
- Final replies must say what changed, what was verified, which docs were synchronized, and what risks or skipped checks remain. For release work, also report `VERSION`, `CHANGELOG.md`, tag, GitHub Release, Latest status, Chinese release notes, and compare link evidence.

## Scaffold script notes

`scaffold_dxm.py` is non-destructive by default:

- creates missing files from `assets/templates/`;
- skips existing files;
- appends a DXM block to an existing `AGENTS.md` only if the block is absent;
- with `--trellis`, initializes Trellis if available and appends DXM/Trellis blocks once;
- refuses broad roots unless `--allow-broad-root` is explicitly passed;
- prints a concise created/skipped summary.

Use `--force` only when the user explicitly wants to replace generated files.

## References

Read `references/dxm-method.md` when you need the distilled method behind the generated files or when adapting the templates for another large project.
