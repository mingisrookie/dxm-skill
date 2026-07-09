---
name: dxm
description: Use when the user types /dxm or /dxm trellis, asks to generate or refresh DXM 大项目开发规范（AI协作） docs such as AGENTS.md or 项目开发规范（AI协作）.md, wants a folder to become a DXM large-project AI collaboration workspace, or asks for the DXM + Trellis / 大开发模式 / project-grill workflow.
---

# DXM Large Project AI Collaboration

## Purpose

DXM turns a project folder into a governed AI collaboration workspace. It creates or refreshes the standard project rule files, then requires future analysis, development, testing, documentation, Git, PR, and handoff work in that folder to follow those local rules. First `/dxm` is a project setup conversation: clarify the project before the docs become the long-term source of truth.

## First-principles rule（第一性原理）

Every requirements question — project-grill, `grilling`, `grill-with-docs`, legacy `grill-me`, `new-project-grill`, `lightweight-grill`, or inline — must start from first principles and adversarial questioning（质疑）, and the frame must be stated before asking the user. First collapse the problem to the real user outcome, irreversible constraints, observable local evidence, and unknown blockers. Then actively challenge hidden assumptions, over-scoped solutions, fake constraints, and user-suggested implementation bias — challenge assumptions instead of merely collecting answers. Finally, ask only the smallest set of questions that changes the next action.

## Trigger contract

### `/dxm`

1. Treat the current working directory as the target project root unless the user gives another path. Do not run this in a broad drive root like `G:\` unless the user explicitly says that is the project root.
2. If the user says `只分析`, `先看看`, or equivalent read-only language: inspect only and report what DXM would do. Do not scaffold or edit files, and stop here — none of the later items apply.
3. If the user says `scaffold only`, `只生成模板`, or `先别问`: skip the grill routing in item 4 and continue from item 5.
4. Otherwise classify the target before scaffolding and route it through the Project-grill modes table below, applying the first-principles rule before any question.
5. Run the bundled scaffold script after the project intent is clear. Resolve `scripts/scaffold_dxm.py` relative to this skill's own directory (the skill loader reports the base path; typical installs are `%USERPROFILE%\.codex\skills\dxm` for Codex and `%USERPROFILE%\.claude\skills\dxm` for Claude Code; in a repo checkout use `skills/dxm/scripts/scaffold_dxm.py`):

```text
python "<skill-dir>/scripts/scaffold_dxm.py" --root "<project-root>"
```

6. Ensure these files exist in the project root:
   - `AGENTS.md`
   - `项目开发规范（AI协作）.md`
   - `项目完整链路说明.md`
   - `项目文件结构说明.md`
   - `开发者AI开发与PR提交流程.md`
7. Do not overwrite existing project-specific docs unless the user explicitly asks for overwrite. Existing docs are likely hand-curated and higher value than templates.
8. After scaffolding, read `AGENTS.md` and follow it for the rest of the session.
9. If the scaffold reports an incomplete managed block, do not ignore it or claim success. Restore the missing end marker or ask whether to overwrite the affected generated file.

### `/dxm trellis`

Triggers: `/dxm trellis`, `/dxm 大开发`, `/dxm full`, or any request to enable DXM for large development workflow.

1. First satisfy normal `/dxm` behavior and project-grill expectations, then run the same scaffold command with `--trellis --trellis-user "<developer-name>"` added; omit `--trellis-user` when the developer name is unknown — it defaults to the OS user name.
2. This must remain non-destructive: DXM docs are created when missing, existing hand-maintained docs are preserved, DXM/Trellis marker blocks are appended once or refreshed only inside managed markers, and incomplete marker pairs fail loudly. Trellis is initialized non-interactively as `trellis init --codex -u <developer> -y --skip-existing`.
3. If `trellis` is not on PATH, finish the normal DXM scaffold and report that Trellis initialization was skipped because the CLI is missing.
4. When `.trellis/` exists, ensure the DXM safety overrides are present:
   - `session_auto_commit: false` in `.trellis/config.yaml`;
   - `trellis-start` Step 0 reads `AGENTS.md` and the DXM long-term docs first;
   - the Trellis no-task workflow allows DXM inline work for small fixes and read-only analysis;
   - every Trellis task completion runs the adversarial completion check (below) before finish/handoff;
   - Trellis must not stage, commit, push, create PRs, or merge without explicit user authorization.
5. Treat Trellis task files under `.trellis/` as part of the project workflow for the rest of the session.

## Scaffold CLI quick reference

`scaffold_dxm.py` is non-destructive by default: it creates missing files from `assets/templates/`, skips existing files, appends the DXM block to an existing `AGENTS.md` only when the block is absent, refuses broad roots, and prints a concise created/skipped summary.

| Flag | Use |
| --- | --- |
| `--root <path>` | Target project root; defaults to the current directory |
| `--dry-run` | Report planned actions without writing files; use this for read-only planning evidence instead of guessing what scaffold would do |
| `--refresh-blocks` | Non-destructive upgrade: refresh DXM/Trellis marker blocks while preserving manual content outside those blocks |
| `--inventory-depth N` | Only when the initial file-structure seed should include nested paths (default 1) |
| `--trellis`, `--trellis-user <name>` | Also initialize Trellis and append the Trellis safety blocks; `--trellis-user` defaults to the OS user name |
| `--trellis-timeout-seconds N` | Max wait for `trellis init` (default 120) |
| `--self-test` | Verify an installed skill package with packaged smoke checks |
| `--allow-broad-root` | Only when the user explicitly confirms the target really is a drive, home, system, vendor, or build root |
| `--force` | Overwrite existing DXM target files; only when the user explicitly asks to replace them and accepts loss of manual content |

## Project-grill modes

Use these labels consistently so future sessions route the same way:

| Mode | Use when | Ask for |
| --- | --- | --- |
| `grill-with-docs` | Existing code, docs, README, manifests, scripts, or runtime evidence exist | Goal, current behavior, architecture boundary, domain terms/ADRs, risk, validation, non-goals |
| `new-project-grill` | Empty folder or a new project with no useful docs | User, delivery shape, stack preference, core scope, non-goals, data/API/security, acceptance criteria, maintenance horizon |
| `lightweight-grill` | Scratch, demo, one-off script, or very small utility | Only blockers: input/output, success criterion, allowed side effects |

`new-project-grill` and `lightweight-grill` are DXM routing labels, not required standalone skills: execute them with `grilling`, the legacy `grill-me` alias, or concise inline questions. `grill-with-docs` routes the interview through `grilling` plus `domain-modeling`; when domain terms or ADRs change, also use `domain-modeling`.

Skip or redirect the grill only in these cases:

- Explicit scaffold-only or read-only intent (trigger contract items 2–3).
- Existing complete DXM docs: do not repeat the grill unless the user asks to re-baseline.
- Subdirectory misfire: tell the user to move to the project root; do not initialize the leaf folder.
- vendor / dependency / build output: only initialize if the user says this is the thing they maintain or study.

## Trellis routing policy

DXM is the global project rule layer. Grill is the clarification step. Trellis is the durable task layer for medium/large work. Do not require the user to remember `/dxm trellis`: the agent must proactively classify task scale.

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

### Adversarial completion check（对抗性检查）

After every Trellis task reaches check/finish, or whenever the agent believes the Trellis work is done, run an adversarial check before marking it complete: challenge the result against requirements, hidden assumptions, negative paths, architecture boundaries, tests, docs, secrets, encoding, rollback/recovery, and user intent. Any blocking finding sends the task back into implement/check; do not finish on an unchecked result.

## Standard behavior inside a DXM workspace

Before any non-trivial code, test, script, config, documentation, Git, PR, or release work:

1. Read `AGENTS.md`.
2. Read or re-check the three project maintenance docs: `项目文件结构说明.md`, `项目完整链路说明.md`, `项目开发规范（AI协作）.md`.
3. If Git/PR/release/version/latest work is requested, also read `开发者AI开发与PR提交流程.md`.
4. Resolve conflicts by observed runtime and current files first, then docs. If docs are stale and the task changes facts, update the docs before reporting completion.

## DXM operating rules

- Separate user intent: `只分析/先看看` means read-only; `开始开发/直接改/提交` means execute to verified completion.
- Apply the first-principles rule above to every requirements inquiry or grill call.
- Use evidence, not memory: inspect files, configs, commands, diffs, tests, listeners, logs, and runtime output.
- Phase work: plan the affected chain, change one stage at a time, verify each stage, then run a final global review and, for Trellis work, the adversarial completion check.
- Preserve architecture boundaries: do not pile new logic into a main file when an existing module, provider, service, route, manager, or helper layer owns it.
- Keep code and docs synchronized: file-structure changes update `项目文件结构说明.md`; runtime-flow changes update `项目完整链路说明.md`; process/boundary changes update `项目开发规范（AI协作）.md`.
- Treat Chinese encoding as a completion blocker. Check modified Chinese docs, logs, comments, and UI strings for visible mojibake or replacement characters.
- Protect secrets and runtime data. Never paste real tokens, passwords, API keys, account lists, or credential-bearing state into reports.
- Final replies must say what changed, what was verified, which docs were synchronized, whether the Trellis adversarial check passed when applicable, and what risks or skipped checks remain. For release work, also report `VERSION`, `CHANGELOG.md`, tag, GitHub Release, Latest status, Chinese release notes, and compare link evidence.

## References

Read `references/dxm-method.md` when you need the distilled method behind the generated files or when adapting the templates for another large project.
