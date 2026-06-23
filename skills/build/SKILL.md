---
name: build
description: "Implement a single task to completion with a test-driven, independently-verifiable loop — understand the target, write the test first, make it pass, re-run the FULL suite, verify it builds, commit, and hand off concrete evidence. Use whenever you are the builder executing one task that a second agent (or human) will independently re-review and re-test — the build half of a build-then-review loop, advancing a to-do task to DONE, 'implement this task', 'make this change and prove it works'. Built for autonomous runs with no human in the loop: the reviewer who re-runs your tests is your gate, so never claim a green check you didn't earn."
when_to_use: "build this, implement this task, make this change, advance the task to completion, build half of build-and-review, do the work and prove it, make it pass the tests, implement to a DONE verdict, builder step"
metadata:
  version: "1.0.0"
---

# Build: implement one task to completion

You are the **builder** in a build-then-review loop. You implement a single task; then a *second agent independently re-runs the tests* and judges your work DONE or NOT_DONE. It will not take your word — it re-runs everything from scratch.

So the goal is not to *claim* the task is done. It's to leave the codebase in a state that survives an independent re-run by a skeptic. Build for that reviewer. A green checkmark you award yourself is worth nothing here; a passing suite the reviewer reproduces is worth everything.

There is no human in this loop to approve steps or answer mid-build. The reviewer is your gate. That raises the bar on honesty, not lowers it: anything you can't verify, you say so — you don't quietly assume it passed.

## The loop — one task, test-first

Work in small, verifiable slices. For a task with real logic:

1. **Understand the target.** Read the task's description and acceptance criteria, and read the project's `project.md` — its `# Goal` and especially `# Constraints` are *binding*. A change that nails the task but violates a stated constraint is NOT done. If a constraint blocks the obvious step, surface it (see *When you can't finish*); don't work around it.

2. **Load context before writing.** Read the code the task touches and the patterns already in the repo — existing helpers, naming, test style, the `test_command`. Match what's there; the laziest change that fits the codebase is usually the right one. Reusing an existing function beats writing a new one.

3. **Write the test first (RED).** Express the expected behavior as a test and watch it fail for the right reason. A test written after the code tends to assert what the code happens to do, not what the task asked for — writing it first keeps you honest about the target. This is also exactly what the reviewer looks for: a regression test that would actually fail if the behavior broke.

4. **Implement the minimum to pass (GREEN).** Smallest change that makes the test pass. No speculative abstraction, no adjacent "while I'm here" edits — every changed line should trace to the task. Scope creep is what makes a reviewer say NOT_DONE on otherwise-good work.

5. **Run the FULL suite, not just your test.** The reviewer runs the whole suite, so you must too. A change that passes your new test but reddens another is a regression, not a completion. Use the project's `test_command` if the frontmatter sets one; otherwise the repo's conventional suite (`pytest`, `npm test`, `cargo test`, `make test`). **Record the exact pass/fail counts** — they're the evidence the reviewer checks against.

6. **Verify it builds / runs.** Tests passing isn't the same as the thing working. Compile it, run the command, exercise the path the task changed — whatever proves the change is real, not just green.

7. **Commit only if the codebase uses git.** Check with `git rev-parse --is-inside-work-tree`; if it succeeds, commit — staging *only* the files this task touched plus its task-status update, by explicit path. Never `git add -A`, which sweeps in unrelated work (backlog proposals, the human's own edits) and breaks clean rollback. Write a message that says what changed and why. If it isn't a git repo, just leave the edits in place.

8. **Write down what you did and how you verified it** — concretely enough that the reviewer can re-confirm without guessing or re-reading your mind (see *Hand off to the reviewer*).

## Not every task is code

Many tasks here change docs, conduit YAML, templates, or config — there's no unit to RED/GREEN. Don't fake a test loop. Instead, **verify by the means that actually proves the change** and state exactly what you ran:

- A conduit edit → `atelier check <conduit>` (it parses + validates) and `atelier plan <conduit>` for the DAG.
- A doc/template edit → re-read or render the result; grep that the change landed and nothing stale remains.
- A script change → run it on a real input, or add/extend a small `test_*.py` if the logic warrants one (the project's rule: every non-trivial logic change ships a test).

The rule that never bends: **never report a green check you didn't earn.** "No automated test covers this; I verified by running `atelier check` — all 8 conduits OK" is a complete, honest answer. A fabricated or assumed pass is a defect the reviewer will catch and bounce.

## When you can't finish

If a constraint blocks the obvious step, a test won't pass without a decision only a human can make, or the task is genuinely ambiguous — **do not paper over it.** Record the blocker plainly in the work and stop honestly. A task left clearly NOT_DONE *with the reason* is more useful than one falsely claimed DONE: the reviewer, and the human behind the board, need the truth to act. Faking completion just gets caught one step later, after wasting the review.

## Hand off to the reviewer

Your final message *is* the evidence the reviewer judges — and they start from zero context. Make it concrete and skimmable:

- **What changed** — the files and the actual edits, and one line on why that satisfies the task.
- **How you verified** — the exact command and its result. "Ran `uv run pytest`: 40 passed, 0 failed" beats "tests pass." Name the build/run check too if you did one.
- **What you could not verify**, or any constraint you had to work around — stated, not hidden.

## Done when

- The task's acceptance criteria are met and you can point at the evidence for each.
- The full suite is green under a real run — or you've stated plainly that none exists and exactly what you ran instead.
- Every constraint in `project.md` is respected, and no unrelated files got swept in.
- Your write-up would let a skeptical reviewer reproduce the result and reach DONE without having to reconstruct your reasoning.
