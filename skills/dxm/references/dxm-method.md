# DXM Method

DXM is a reusable large-project AI collaboration method distilled from a hand-maintained project rule set.

## What DXM preserves

1. AI development is a controlled workflow, not a one-shot code generation event.
2. First `/dxm` is a project setup conversation: clarify the project before turning templates into long-term truth.
3. Requirements questions start from first principles（第一性原理）: real outcome, hard constraints, local evidence, and remaining blockers come before asking the user.
4. Project facts must be discoverable from local files and runtime evidence, not memory.
5. Architecture invariants should be written down so AI does not slowly erode them.
6. Development must be staged: analyze, plan, implement, verify, document, then report.
7. Trellis task completion includes an adversarial check（对抗性检查）before finish or handoff.
8. Documentation synchronization is part of completion, not optional cleanup.
9. Encoding quality matters in Chinese projects; mojibake is a blocking defect.
10. Final handoff must reveal verification and remaining risk instead of hiding behind “done”.

## Project-grill routing

Use the lightest clarification mode that still makes the future project understandable:

- `grill-with-docs`: existing code or docs exist; questions must be grounded in those files and use `domain-modeling` when terminology or ADRs change.
- `new-project-grill`: empty or brand-new project; ask about user, delivery shape, stack, scope, non-goals, dependencies, acceptance, and maintenance horizon.
- `lightweight-grill`: scratch/demo/small script; only ask blocking questions.

`new-project-grill` and `lightweight-grill` are DXM mode labels, not mandatory standalone skills. Implement them with `grilling`, `grill-with-docs`, the legacy `grill-me` alias, or concise inline questions depending on available context.

Skip grill only when the user explicitly asks for scaffold-only/read-only behavior, the folder already has complete DXM docs, or the current directory is not the project root.

Before any requirements question, prompt the agent to reason from first principles: collapse the problem to the real outcome, hard constraints, local evidence, and unknown blockers, then ask only questions that change the next action.

## Trellis relationship

DXM is the project rule layer. Grill is the clarification layer. Trellis is the medium/large task memory layer.

Default routing:

- small read-only or one-file work: DXM inline;
- unclear, multi-file, architectural, multi-stage, or long-lived work: project-grill, then Trellis task PRD;
- after every Trellis task completion: adversarial check, then finish/handoff only if no blocking finding remains;
- Trellis never overrides DXM Git authorization, read-only intent, or secret-handling rules.

## What stays project-specific

Keep these in the generated project docs, not in this global skill:

- actual entrypoints and module boundaries;
- real test/build/run commands;
- Git branch and PR policy;
- sensitive runtime files;
- domain-specific providers, states, modes, and flows;
- old or transitional architecture that only applies to one repository.

## Evidence priority

When rules conflict, prefer:

1. live runtime behavior;
2. command output, logs, tests, and diffs;
3. currently served or imported assets;
4. current config and startup path;
5. maintained root docs;
6. old plans, comments, and generated artifacts.

## Release discipline

Real DXM use showed that pushing `main` is not enough for release work. A release is complete only when version metadata, `CHANGELOG.md`, tag, GitHub Release, Latest status, Chinese release notes, compare link, and verification evidence are all synchronized and checked on the live GitHub surface.
