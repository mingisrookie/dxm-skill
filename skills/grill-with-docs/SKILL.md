---
name: grill-with-docs
description: Use when requirements or a plan must be clarified against existing code, docs, runtime evidence, domain terminology, glossary entries, ADRs, or documented decisions.
---

# Grill With Docs

Ground clarification in the locked project scope. Start from first principles: identify the real outcome, hard constraints, local facts, and unknown blockers, then challenge hidden assumptions, fake constraints, over-scoped solutions, and implementation bias. Use **local evidence first**: inspect the relevant code, docs, config, tests, logs, and safe runtime state before asking the user.

## Default bounded route

For DXM bootstrap or normal clarification, ask **0–3 blocking questions in one batch**. State recommended assumptions for non-blocking choices and proceed when the user says `按推荐走`, `直接做`, or equivalent. Do not invoke the one-question-per-turn `grilling` cadence by default.

## Full route

Full/exhaustive `grilling` is **explicit opt-in** only. Use it only when the user asks for `grill me`, `完整 grilling`, every decision branch, or an equivalent exhaustive stress-test.

## Domain facts

Use `domain-modeling` only when stable terminology, bounded contexts, context maps, or an ADR decision actually needs to be created or changed. Evidence review and ordinary clarification do not write `CONTEXT.md`, `CONTEXT-MAP.md`, or ADR files.

Return resolved blockers, recommended assumptions, and any necessary domain-document changes to the calling workflow. Do not scaffold or widen its root/mode/scope lock.
