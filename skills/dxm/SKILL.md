---
name: dxm
description: Use when the user types /dxm or /dxm trellis, asks to generate or refresh DXM 大项目开发规范（AI协作） docs such as AGENTS.md or 项目开发规范（AI协作）.md, wants a folder to become a DXM large-project AI collaboration workspace, or asks for the DXM + Trellis / 大开发模式 / project-grill workflow.
---

# DXM Large Project AI Collaboration

## Purpose

DXM turns a project folder into a governed, persisted, and auditable AI collaboration workspace. It separates read-only audit, first-time initialization, normal project work, and template-only scaffolding so that a file write is never mistaken for project readiness or task completion.

## First-principles rule（第一性原理）

Start requirements work from first principles: identify the real user outcome, hard constraints, observable local evidence, and unknown blockers. Challenge hidden assumptions, fake constraints, over-scoped solutions, and implementation bias. Inspect facts that code, docs, config, logs, or runtime can answer instead of asking the user.

## Workflow state machine

Choose exactly one mode and establish a **root/mode/scope lock** before the first write. The lock records the canonical project root, one mode, and the allowed files/runtime surface. Do not silently widen or switch it. If the requested path, current directory, persisted baseline root, or task scope disagrees, stop writes and resolve the mismatch first.

| Mode | Select when | Contract |
| --- | --- | --- |
| `audit` | The user says `只分析`, `先看看`, `暂时不改`, asks for review/investigation, or has not approved a mutation | Read-only: no scaffold, no Trellis task, no runtime mutation, and no file write. Report evidence and the locked scope only. |
| `init` | The canonical root has no complete DXM baseline and the user wants to initialize or continue development | Inspect locally, run the bounded bootstrap below, persist the baseline, scaffold non-destructively, then audit readiness. |
| `task` | Work is inside an existing READY/PARTIAL DXM workspace | Keep the existing baseline; do not rerun initialization. Lock this task's scope, load only relevant docs, and collect acceptance evidence. |
| `scaffold-only` | The user explicitly says `scaffold only`, `只生成模板`, or `先别问` | Create or refresh only requested templates. No interrogation, no baseline/readiness claim, and no Trellis task unless separately requested. |

Analysis-oriented wording selects `audit` unless the user explicitly requests initialization or implementation. A completed scaffold is not proof of `READY`; use the packaged audit result.

When a continue-development request matches both `init` and `task` because the workspace is `PARTIAL`, `task` wins by default: keep the existing baseline artifacts and list the readiness gaps as pending work. Choose `init` on a `PARTIAL` workspace only when the gap is the project baseline itself and the user agrees to establish it.

## Bounded bootstrap contract

This contract applies to default `init` and project-grill routing:

1. **local evidence first**: inspect the locked root's README, manifests, source, config, tests, docs, logs, and safe runtime evidence before asking anything.
2. Ask only **0–3 blocking questions in one batch**. A blocking question is one whose answer changes the next safe action, project boundary, or acceptance contract.
3. For non-blocking choices, state the recommended assumption and proceed. `按推荐走`, `直接做`, or equivalent approval closes all remaining non-blocking clarification.
4. Full/exhaustive, one-question-per-turn `grilling` is **explicit opt-in** only, such as when the user says `grill me`, `完整 grilling`, or asks to walk every branch. It is never the default DXM bootstrap cadence.
5. Do not scaffold before required blocking answers are resolved. If there are no blockers, ask zero questions and proceed with stated assumptions.

Core DXM must remain usable without sibling interview skills. `new-project-grill` and `lightweight-grill` are routing labels, `grill-with-docs` is an optional evidence-grounded router, and `grill-me` is a legacy optional alias.

## Project-grill profiles

| Profile | Use when | Default bounded focus |
| --- | --- | --- |
| `grill-with-docs` | Existing code, docs, README, manifests, scripts, or runtime evidence exist | Inspect first; ask only blockers about goal, current behavior, boundary, risk, acceptance, and non-goals. |
| `new-project-grill` | Empty folder or a new project with no useful docs | Ask only unresolved blockers among user, delivery, core scope, constraints, acceptance, and maintenance. |
| `lightweight-grill` | Scratch, demo, one-off script, or very small utility | Input/output, success criterion, and allowed side effects only when unresolved. |

Use `domain-modeling` only when stable domain terminology, context boundaries, context maps, or ADR decisions actually need to be created or changed. Evidence gathering alone must not create those files.

Redirect instead of initializing when the lock points at a leaf subdirectory, vendor/dependency tree, build output, broad drive/home/system root, or another root than the project baseline. Proceed only when the user confirms that exact directory is the maintained project root.

## `/dxm` execution

After locking `init` or `scaffold-only`, resolve the copied-skill command router (or its underlying scaffold script) relative to this skill directory and pass the locked write mode explicitly:

```text
python "<skill-dir>/scripts/dxm.py" scaffold-only --root "<project-root>"
python "<skill-dir>/scripts/dxm.py" init --root "<project-root>" --baseline "<baseline.json>"
```

`--mode init` rejects a missing baseline before any project write; `--mode scaffold-only` rejects `--baseline` and never reports READY. DXM v2 rejects a no-`--mode` write call with `DXM_E_MODE_REQUIRED`; an explicit init exits with the final audit code (`READY=0` / `BROKEN=2` / `PARTIAL=3` / `ABSENT=4`). Use `--output json` whenever an orchestrator must distinguish a completed write operation from readiness. Preserve existing hand-maintained content unless the user explicitly authorizes overwrite.

Ensure the project root contains:

- `AGENTS.md`
- `项目开发规范（AI协作）.md`
- `项目完整链路说明.md`
- `项目文件结构说明.md`
- `开发者AI开发与PR提交流程.md`

After scaffold, run the packaged readiness audit. `ABSENT`, `PARTIAL`, `READY`, and `BROKEN` are distinct states; never turn `PARTIAL` or `BROKEN` into a success-style next step. Write JSON includes `operation`, `readiness`, actual `exit_code`, `issues`, and applicable `error_code` (with `readiness_exit_code` separately); requested JSON also covers argument-boundary failures as `DXM_E_INVALID_ARGUMENTS`. A write is guarded by a project lock, atomic replacement and a transaction journal; audit, doctor, and receipt validation treat active/stale/malformed locks or pending journals as non-ready. If a prior operation is interrupted, run `dxm.py recover --root "<project-root>"` before another write.

If a real Markdown managed marker is orphaned, duplicated, or out of order, stop rather than appending another block; marker examples inside complete fenced/inline code are documentation, not active blocks. Do not overwrite existing project-specific docs unless the user explicitly accepts that loss. Baseline, run, and receipt validation reject high-confidence credential material without echoing its value.

## `/dxm trellis`

Triggers: `/dxm trellis`, `/dxm 大开发`, `/dxm full`, or an explicit request to enable the large-development workflow.

1. Satisfy the selected normal DXM mode and bounded bootstrap first.
2. Run the scaffold with `--trellis --trellis-user "<developer-name>"`; when the name is unavailable, omit `--trellis-user`. The underlying command is `trellis init --codex -u <developer> -y --skip-existing`.
3. An explicit Trellis request succeeds only when Trellis initialization succeeds. Missing CLI, timeout, or non-zero Trellis exit may leave ordinary DXM scaffold files behind, but the combined request remains failed and must not be reported complete.
4. When `.trellis/` exists, require `session_auto_commit: false`, a DXM-aware `trellis-start`, inline routing for small/read-only work, and adversarial check before the `finish` → `archive <task> --no-commit` → archived receipt sequence.
5. Trellis never stages, commits, pushes, creates/merges PRs, tags, or publishes without explicit user authorization.

## Scaffold CLI quick reference

`scaffold_dxm.py` is non-destructive by default: it creates missing files from `assets/templates/`, skips existing files, appends a missing managed block when safe, refuses broad/non-directory roots and unsafe link/non-directory/hardlink ancestors, and reports actual outcomes.

| Flag | Use |
| --- | --- |
| `--root <path>` | Locked target project root; defaults to current directory |
| `--mode init` | Required initialization lock; requires `--baseline`, and exits with final readiness |
| `--mode scaffold-only` | Required template-only writing lock; forbids baseline/readiness claims |
| `--baseline <json-file>` | Validate and persist the `init` project baseline |
| `--dry-run` | Report planned actions without writing files |
| `--refresh-blocks` | Refresh managed blocks while preserving manual content; rehydrate an existing valid baseline block without rewriting its JSON |
| `--inventory-depth N` | Include nested paths in the JSON-safe structure seed (default 1, policy-bounded) |
| `--trellis`, `--trellis-user <name>` | Request Trellis initialization and safety blocks |
| `--trellis-timeout-seconds N` | Maximum wait for `trellis init` (default 120) |
| `--self-test` | Run installed-package smoke checks |
| `--recover`, `--break-stale-lock` | Explicitly recover an interrupted local transaction; stale-lock removal is opt-in |
| `--output text\|json`, `--redact-paths` | Stable automation output, optionally without local root paths |
| `--allow-broad-root` | Use only after explicit confirmation of that broad root |
| `--force` | Overwrite existing DXM target files only after explicit acceptance of manual-content loss |

## Trellis task routing

| Work | Route |
| --- | --- |
| Read-only review, log analysis, explanation | `audit`; no task |
| Small clear bug, one-file fix, light docs | `task` inline **run-only**; create a lightweight run but no Trellis task unless requested |
| New feature, module, architecture change, cross-file refactor | Recommend Trellis once; proceed when the user's request already approves that workflow |
| Multi-stage or cross-session work | Persist a Trellis PRD unless the user opts out |

Trellis PRD belongs in `.trellis/tasks/<task>/prd.md`. Every started Trellis task must progress through create/start/check/finish truthfully; task files alone do not prove completion.

## Lightweight run contract

Every writable `task` creates a `schema_version: 1` run at `.dxm/runs/<run_id>/run.json` before the first source/config/test/doc change. `init` creates it immediately after the validated baseline is persisted and before implementation work. The run locks canonical root, start time, original goal, scope, author, stable outcomes, `claim_type`, `evidence_kinds`, `baseline_impact`, risk, Trellis routing, and `unverified_boundaries`. Validate it with `validate_dxm.py run --root "<project-root>" --file .dxm/runs/<run_id>/run.json`.

Small clear work stays **run-only**. If intent is ambiguous and the answer changes safety, scope, or acceptance, inspect locally and ask one batch of 0–3 blocking questions; do not force a full interview. Infer delivery from the user's task, not from what is easiest to prove:

- behavior words such as fix/enable/take effect/work normally require runtime-appropriate evidence;
- explicit **source-only** work may finish as source delivery only, must list `unverified_boundaries`, and must not claim runtime effect, deployment, or online recovery;
- if required runtime evidence cannot be obtained, report partial/blocked instead of silently shrinking the original goal.

## selective docs loading

`AGENTS.md` is **always** loaded. Then load only the long-term docs relevant to the affected surface:

| Affected surface | Additional required doc |
| --- | --- |
| Any code, config, test, or documentation write | `项目开发规范（AI协作）.md` |
| File layout, ownership, add/delete/rename | `项目文件结构说明.md` |
| Entry point, runtime, config/state/data flow, service or UI behavior | `项目完整链路说明.md` |
| Git, PR, merge, version, tag, release, publish | `开发者AI开发与PR提交流程.md` |

Project `AGENTS.md` may require a stricter pre-read set; obey that stricter local contract. Selective docs loading reduces unrelated context but never bypasses an explicit project rule.

## Evidence matrix and completion gate

Persisted baseline/PRD criteria define durable invariants, while the run outcomes define this task's claims and evidence. `baseline_impact` must cover every baseline ID exactly once as `affected` (with outcome IDs) or `not_affected` (with a rationale); untouched invariants are not re-labelled as freshly passed.

- service claims require listener + health + original-symptom E2E;
- UI claims require an approved reference when applicable + rendered screenshot + navigation/hit-test + regression check;
- online/deployed claims require real entry-point readback;
- restart-durability claims require restart/recovery verification.

Unit tests or config/source inspection alone cannot prove those claims.

Runtime-sensitive evidence uses a **structured observation** with `observed_at`, `subject`, `method`, `result`, and `summary`. When a project-local artifact `path` is supplied, include its `sha256`; the validator checks boundary, existence, and hash. An isolated proof additionally sets `isolated: true`, `final_artifact: true`, and a non-empty `decisive_branch`; merely launching a window is not an E2E. High-risk release/deploy/live-data/multi-module architecture work sets `independent_review_required: true` and needs a fresh `independent_review` PASS from an Agent different from the run author. The receipt uses `artifact_sha256` to bind canonical `independent-review.md` (`.trellis/tasks/.../<task>/` for Trellis, `.dxm/runs/<run_id>/` for run-only), whose top-level `reviewer_id`, timezone-aware `reviewed_at`, and `verdict: PASS` must match the review metadata. This is a local evidence-consistency/reviewer-separation gate, not trusted identity proof. baseline `profile` supports `lite`, `standard` (default), and `high-assurance`; the latter also requires external provenance validated at an independent trusted boundary. Normal small fixes do not.

Before reporting `init` or `task` complete, create a `schema_version: 2` machine-readable **completion receipt** and validate it. It binds `run_id` + `run_sha256`, task-specific `requirements[].id/status/evidence_kinds`, per-ID/per-kind `evidence`, `baseline_impact`, and `unverified_boundaries`; it also records `independent_review` when required, `adversarial_check`, `quality_checks` (`docs`, `encoding`, `secrets`, `rollback`), `trellis.required/task/check_passed/finished`, and `git.commit_performed/commit/push_performed/branch`. Default validation rejects legacy v1; `--legacy-v1` is historical audit-only and never proves current completion.

For Trellis work, the final canonical `check.md` must use exactly one `<!-- DXM-CHECK:PASS -->` fragment as its first non-empty, column-zero standalone line, written only after no blocker remains. Then run `finish`, `task.py archive <task> --no-commit`, create `.trellis/tasks/archive/<YYYY-MM>/<task>/completion.json`, and validate it. A run-only task writes `.dxm/runs/<run_id>/completion.json`. Missing/failing/stale evidence, run/outcome/impact drift, an invalid check verdict or path, missing independent review, trusted-root mismatch, credentials, or false Trellis state fails closed. Git fields report truth and never authorize operations.

## Operating rules

- Prefer live runtime, captured traffic, served assets, process config, persisted state, then source/docs.
- Change one stage at a time and verify the original symptom plus relevant negative paths.
- Preserve existing architecture boundaries and manual documentation.
- Synchronize changed project facts into the relevant long-term docs.
- Treat visible Chinese mojibake or replacement characters as a completion blocker.
- Protect tokens, passwords, API keys, sessions, private runtime data, and sensitive filenames.
- Final human output summarizes the validated completion receipt, any skipped checks, and residual risk; it never substitutes for the machine-readable gate.

## References

Read `references/dxm-method.md` when adapting or explaining this state machine and its evidence/completion model.
