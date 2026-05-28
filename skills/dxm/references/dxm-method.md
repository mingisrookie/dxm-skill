# DXM Method

DXM is a reusable large-project AI collaboration method distilled from a hand-maintained project rule set.

## What DXM preserves

1. AI development is a controlled workflow, not a one-shot code generation event.
2. Project facts must be discoverable from local files and runtime evidence, not memory.
3. Architecture invariants should be written down so AI does not slowly erode them.
4. Development must be staged: analyze, plan, implement, verify, document, then report.
5. Documentation synchronization is part of completion, not optional cleanup.
6. Encoding quality matters in Chinese projects; mojibake is a blocking defect.
7. Final handoff must reveal verification and remaining risk instead of hiding behind “done”.

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
