---
name: spec
description: Write a short spec document before coding — objective, success criteria, boundaries, open questions. Use whenever the user is starting a feature, project, or non-trivial change and there's no written spec yet, OR when a request is vague enough that "done" isn't yet defined. Trigger even if the user doesn't say the word "spec" — phrases like "let's build X", "I want to add Y", "help me plan out Z", or any ask where requirements are fuzzy all qualify. Not for single-line fixes, typos, or changes where the requirement is already unambiguous.
---

# Simple Spec

## What this does

Produce one spec file before writing code. Not a planning pipeline, not a task tracker — a single short document that makes the goal and the boundaries explicit so the work has a target to hit.

The spec's whole value is surfacing misunderstandings *before* code exists, when they're free to fix. That means the most important move is naming your assumptions out loud, not filling in a perfect template.

## Workflow

1. **State your assumptions first.** Before writing anything, list what you're assuming and let the user correct you. This is the part that actually prevents wasted work.

   ```
   ASSUMPTIONS:
   1. This runs as a CLI, not a web service
   2. Input is a single JSON file, not a stream
   3. Python 3.11+, since that's what the repo uses
   → Correct me now or I proceed with these.
   ```

2. **Write the spec to a file.** Default to `spec.md` in the repo root (or alongside the feature). Keep it short — a spec that takes 15 minutes to read won't get read.

3. **Flag open questions instead of guessing.** Anything you couldn't resolve goes in Open Questions, not into a silent assumption.

## Spec template

Keep every section to a few lines. If a section has nothing real to say, cut it rather than padding it.

```markdown
# Spec: [Name]

## Objective
What we're building and why. Who uses it. One paragraph.

## Success Criteria
Specific, testable conditions for "done". Not "make it fast" but
"responds in <200ms for a 1000-row input". If you can't test it, sharpen it.

## Boundaries
- Always: [things to always do — e.g. validate inputs, run tests before commit]
- Ask first: [things needing approval — e.g. new dependencies, schema changes]
- Never: [hard limits — e.g. commit secrets, touch the vendor dir]

## Open Questions
Anything unresolved that needs a human answer before or during the build.
```

## Turning vague asks into success criteria

When a request is fuzzy, the spec's job is to translate it into something you can check. Show the translation so the user can correct the target:

```
REQUEST: "make the import faster"

SUCCESS CRITERIA:
- A 50MB CSV imports in <10s (currently ~40s)
- Memory stays under 500MB during import
→ Right targets?
```

A clear target lets you loop toward "done" on your own instead of guessing what the user meant.

## When you're done

The spec is good enough when:
- Someone else could read it and know what success looks like
- Every fuzzy word ("fast", "robust", "clean") has been replaced with something testable
- The unknowns are listed as Open Questions, not buried as assumptions
- It's saved to a file in the repo

Then build. Update the spec if a decision changes mid-flight — an outdated spec is worse than a short one.