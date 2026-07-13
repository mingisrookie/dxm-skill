---
name: grilling
description: Use when the user explicitly asks for an exhaustive plan or design interview, says grill me, requests full grilling, or asks to stress-test every decision branch before building.
---

# Grilling

This is the full/exhaustive interview cadence and is **explicit opt-in** only. A default DXM `init`, `project-grill`, `new-project-grill`, or `lightweight-grill` uses the bounded 0–3-question contract instead of this skill.

## Cadence

1. Start from first principles and challenge hidden assumptions, fake constraints, over-scoped solutions, and implementation bias. Then use **local evidence first**: inspect code, docs, config, logs, tests, and safe runtime facts that can answer a question.
2. Identify unresolved decisions and their dependencies. Do not ask the user for locally discoverable facts.
3. Ask one decision question at a time, wait for the answer, and include a recommended answer with its trade-off.
4. Walk only branches that can change scope, architecture, safety, acceptance, or maintenance. Stop when those decisions have a shared answer.
5. If the user says `按推荐走`, `直接做`, or asks to stop interviewing, accept the stated recommendations and hand control back to the calling workflow.

Do not scaffold, edit project files, or widen the caller's root/mode/scope lock merely because this interview is active.
