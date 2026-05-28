---
name: dxm
description: Use when the user types "/dxm", asks to generate or refresh 大项目开发规范（AI协作） files, or wants a folder to become a DXM large-project AI collaboration workspace. Scaffolds and enforces project-level AGENTS.md plus the four standard Chinese maintenance documents for AI-assisted development, architecture boundaries, full runtime flow, file structure, and PR workflow.
---

# DXM Large Project AI Collaboration

## Purpose

Use this skill to turn the current folder into a DXM-governed large-project workspace. DXM means: generate the standard project rule files, then obey them for all future analysis, development, testing, documentation, Git, PR, and handoff work in that folder.

## Trigger contract

When the user says `/dxm`:

1. Treat the current working directory as the target project root unless the user gives another path.
2. Run the bundled scaffold script. Resolve `scripts/scaffold_dxm.py` relative to this skill directory:

```powershell
python "<path-to-installed-dxm-skill>\scripts\scaffold_dxm.py" --root "<project-root>"
```

3. Ensure these files exist in the project root:
   - `AGENTS.md`
   - `项目开发规范（AI协作）.md`
   - `项目完整链路说明.md`
   - `项目文件结构说明.md`
   - `开发者AI开发与PR提交流程.md`
4. Do not overwrite existing project-specific docs unless the user explicitly asks for overwrite. Existing docs are likely hand-curated and higher value than templates.
5. After scaffolding, read `AGENTS.md` and follow it for the rest of the session.

## Standard behavior inside a DXM workspace

Before any non-trivial code, test, script, config, documentation, Git, PR, or release work:

1. Read `AGENTS.md`.
2. Read or re-check the three project maintenance docs:
   - `项目文件结构说明.md`
   - `项目完整链路说明.md`
   - `项目开发规范（AI协作）.md`
3. If Git/PR work is requested, also read `开发者AI开发与PR提交流程.md`.
4. Resolve conflicts by observed runtime and current files first, then docs. If docs are stale and the task changes facts, update the docs before reporting completion.

## DXM operating rules

- Separate user intent: `只分析/先看看` means read-only; `开始开发/直接改/提交` means execute to verified completion.
- Use evidence, not memory: inspect files, configs, commands, diffs, tests, listeners, logs, and runtime output.
- Phase work: plan the affected chain, change one stage at a time, verify each stage, then run a final global review.
- Preserve architecture boundaries: do not pile new logic into a main file when an existing module, provider, service, route, manager, or helper layer owns it.
- Keep code and docs synchronized: file-structure changes update `项目文件结构说明.md`; runtime-flow changes update `项目完整链路说明.md`; process/boundary changes update `项目开发规范（AI协作）.md`.
- Treat Chinese encoding as a completion blocker. Check modified Chinese docs, logs, comments, and UI strings for visible mojibake or replacement characters.
- Protect secrets and runtime data. Never paste real tokens, passwords, API keys, account lists, or credential-bearing state into reports.
- Final replies must say what changed, what was verified, which docs were synchronized, and what risks or skipped checks remain.

## Scaffold script notes

`scaffold_dxm.py` is non-destructive by default:

- creates missing files from `assets/templates/`;
- skips existing files;
- appends a DXM block to an existing `AGENTS.md` only if the block is absent;
- prints a concise created/skipped summary.

Use `--force` only when the user explicitly wants to replace generated files.

## References

Read `references/dxm-method.md` when you need the distilled method behind the generated files or when adapting the templates for another large project.
