# DXM Method

DXM is a reusable large-project AI collaboration method. Its core is a bounded state machine with persisted project facts, claim-specific evidence, and a validated completion gate.

## State machine

Before mutation, establish a **root/mode/scope lock**: one canonical root, exactly one workflow mode, and an allowed change/runtime surface.

| Mode | Meaning |
| --- | --- |
| `audit` | Read-only investigation; no scaffold, task, runtime mutation, or write. |
| `init` | First project baseline, governed documents, and readiness audit. |
| `task` | Work inside an existing governed workspace without rerunning initialization. |
| `scaffold-only` | Explicit template creation without interrogation or a readiness claim. |

Root or scope disagreement is an integrity problem, not permission to silently follow the current directory. Analysis-oriented language selects `audit` unless the user explicitly approves initialization or implementation.

The write boundary is executable: `init` calls `scaffold_dxm.py --mode init --root <root> --baseline <baseline.json>` and fails before writing when the baseline is absent; explicit template-only work calls `--mode scaffold-only --root <root>` and reports `readiness: NOT_EVALUATED`. A legacy call without `--mode` remains compatible but is not proof of an init gate.

## Bounded clarification

Default DXM `init` starts from first principles: identify the real outcome, hard constraints, local facts, and unknown blockers, then challenge hidden assumptions, fake constraints, over-scoped solutions, and implementation bias. It uses **local evidence first** and asks **0–3 blocking questions in one batch**. A blocking answer must change the next safe action, root/scope boundary, or acceptance contract. Local code, docs, config, logs, tests, and runtime facts are inspected rather than asked back to the user.

Non-blocking choices receive a recommended assumption. `按推荐走`, `直接做`, or equivalent closes those choices and allows work to proceed.

Full/exhaustive, one-question-per-turn `grilling` is **explicit opt-in** only. `new-project-grill` and `lightweight-grill` are bounded DXM labels; `grill-with-docs` is an optional evidence-grounded route; `grill-me` remains a legacy optional alias. Core initialization works with inline clarification when no sibling skill is installed.

`domain-modeling` is used only when stable terms, bounded contexts, context maps, or ADR decisions actually change. Reading evidence does not by itself justify new domain files.

## Persisted truth and readiness

Project facts belong in the baseline and relevant long-term docs, not only in chat. The baseline binds the canonical root, goal/users/deliverables/non-goals, runtime facts, validation commands, assumptions, and acceptance IDs to required evidence kinds.

Scaffold success and project readiness are different claims:

- `ABSENT`: governed documents do not exist;
- `PARTIAL`: documents exist but required baseline/blocks/dependencies are incomplete;
- `READY`: required documents, baseline, markers, and requested workflow integration validate;
- `BROKEN`: encoding, JSON, marker, root, or integrity checks fail.

Only a read-only audit decides readiness. Real Markdown managed markers are valid only as zero pairs or one ordered START/END pair; complete fenced/inline marker examples are ignored, while an unclosed fence cannot hide integrity-significant content.

## Trellis relationship

DXM is the project rule layer; Trellis is the optional medium/large task state layer. Small/read-only work stays inline. Multi-file, architectural, multi-stage, or cross-session work persists a PRD when approved.

Explicit Trellis initialization is truthful: a missing command, timeout, or failed exit may coexist with ordinary DXM files, but cannot be reported as DXM + Trellis success. Every Trellis task tracks create/start/check/finish/archive and runs an adversarial check before `finish` → `archive <task> --no-commit` → archived receipt validation. Trellis never overrides read-only intent, scope lock, secret handling, or explicit Git authorization.

## selective docs loading

`AGENTS.md` is **always** loaded. Additional docs follow the affected surface:

- code/config/test/document writes: `项目开发规范（AI协作）.md`;
- file layout or ownership: `项目文件结构说明.md`;
- entrypoint/runtime/config/state/data/service/UI flow: `项目完整链路说明.md`;
- Git/PR/version/release/publish: `开发者AI开发与PR提交流程.md`.

A project may declare a stricter pre-read set in `AGENTS.md`; that local requirement wins. Selective loading removes unrelated generic context, not project-specific safeguards.

## Evidence matrix

Persisted `acceptance_criteria[].id` and `acceptance_criteria[].evidence_kinds` bind each acceptance claim to required evidence:

- service: listener + health + original-symptom E2E;
- UI: approved reference when applicable + rendered screenshot + navigation/hit-test + regression check;
- online/deployed: real entry-point readback;
- restart durability: restart/recovery verification.

Source inspection or unit tests alone cannot prove a live-surface claim.

## completion receipt

Before claiming `init` or `task` completion, validate a `schema_version: 1` machine-readable completion receipt. It binds `workflow_mode` and canonical `project_root` to `requirements[].id/status/evidence_kinds` and a per-ID/per-kind `evidence` map. It also records `adversarial_check`, `quality_checks.docs/encoding/secrets/rollback`, `trellis.required/task/check_passed/finished`, and `git.commit_performed/commit/push_performed/branch` without performing Git operations. For Trellis, first pass the adversarial check and use exactly one `<!-- DXM-CHECK:PASS -->` fragment as the first non-empty, column-zero standalone line in the final canonical `check.md`; any other or unclosed `DXM-CHECK` fragment fails closed. Then run `finish` and `task.py archive <task> --no-commit`; only after that create and validate `.trellis/tasks/archive/<YYYY-MM>/<task>/completion.json`. Do not predeclare `finished: true`, and never omit `--no-commit` because archive must not bypass Git authorization.

Missing/failed evidence, a missing/malformed/non-passing check verdict, a non-canonical archive month, a trusted-root mismatch, high-confidence credential material in keys or values, or false Trellis state fails receipt validation without echoing sensitive material. File/CLI Trellis validation additionally binds the source path to the archived task's real `completion.json`; mapping inputs validate structure/state only. Scope is separately enforced by the locked task surface, diff review, and adversarial check; detected scope drift also returns work to implement/check. The human handoff summarizes the validated receipt and remaining risk rather than replacing it.

## Evidence priority

When evidence conflicts, prefer:

1. live runtime behavior;
2. captured traffic and command output;
3. actively served/imported assets;
4. current process/config/startup state;
5. persisted project state and maintained docs;
6. generated artifacts, source comments, and old plans.

## Project-specific facts

Keep actual entry points, module boundaries, validation commands, Git policy, runtime-data boundaries, and domain flows in project baseline/docs. Generic method repetition belongs here or in the skill, not copied into every long-term document.

## Release discipline

A release is complete only when the requested code, version metadata, `CHANGELOG.md`, tag, GitHub Release, Latest status, release notes, compare link, and live verification agree. Pushing a branch alone does not prove release completion.
