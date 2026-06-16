---
name: review
description: "Conducts a read-only five-axis code review — correctness, readability, architecture, security, performance — on a diff, branch, or PR, with severity-labeled findings and file:line references. Use whenever the user asks to review code, review changes, review a diff or PR, get a second pair of eyes before merge, or sanity-check work another agent or human wrote — even without the word 'review' (e.g. 'is this change safe to merge', 'anything wrong with what I just did', 'look over these commits'). Not for applying fixes, refactoring, running releases (use /check), or root-causing a bug (use /hunt)."
when_to_use: "review, 看看代码, 审一下, 检查代码, 合并前, 能合吗, 有没有问题, 帮我review, 代码评审, review this, review the diff, review my changes, review this PR, look over my code, second pair of eyes, before merge, is this safe to merge, anything wrong with this change, five-axis review, code review"
metadata:
  version: "1.0.0"
---

# Review: Five-Axis Code Review

You are reviewing a change, not rewriting it. Your job is to surface what would otherwise be caught in production — and to say so honestly, with evidence. This skill is read-only: report findings, propose fixes in words, but do not edit code unless the user explicitly asks. If they want fixes applied, that is `/check`.

**The approval standard:** approve a change when it definitely improves code health, even if imperfect. Perfect code does not exist. Do not block a change because it differs from how you would have written it — block it because it is wrong, unsafe, or unmaintainable.

## Scope the Review First

Before reading code, know what you are reviewing and why. Establish two things:

1. **Intent** — what is this change trying to do? Read the PR description, task, or ask in one line if it is unclear. A review without intent can only check syntax.
2. **Diff** — what actually changed? Default to the working diff. Run the appropriate command and read the *whole* diff before commenting:
   - Uncommitted work: `git diff` and `git diff --staged`
   - A branch vs main: `git diff main...HEAD`
   - A GitHub PR: `gh pr view <n>` then `gh pr diff <n>`

If the diff is large (~1000+ lines), say so and suggest splitting rather than skimming. A skimmed review of a huge diff is worse than honest silence — it grants false confidence.

## The Five Axes

Walk every changed file through these. Not every axis fires on every change; note the ones that do.

**1. Correctness** — does it do what it claims?
Edge cases (null, empty, boundary, zero, negative), error paths not just the happy path, off-by-one, race conditions, state left inconsistent on failure. Do the tests actually exercise the new behavior, or just assert it compiles?

**2. Readability** — can the next engineer understand this unaided?
Descriptive names (no bare `data`, `tmp`, `result`), straightforward control flow (no nested ternaries or clever one-liners that need a comment to decode), logical organization. Could it be meaningfully shorter? Is an abstraction earning its complexity, or generalizing before the third use? Flag dead artifacts the change leaves behind: no-op vars, `// removed` comments, backwards-compat shims.

**3. Architecture** — does it fit the system?
Follows existing patterns, or introduces a new one without justification. Duplicates logic that already exists. Dependencies flow the right way (no new cycles). Abstraction level matches its neighbors — not over-engineered, not copy-pasted.

**4. Security** — does it open a hole?
Untrusted input (user, API, file, env) validated at the boundary before use. No secrets in code, logs, or fixtures. Auth/authz checked where it must be. Queries parameterized, output encoded. New dependency: is it maintained, sane in size, license-compatible, vuln-free?

**5. Performance** — does it introduce a bottleneck?
N+1 queries, unbounded loops or fetches, missing pagination on list endpoints, sync work that blocks, large allocations in hot paths, needless re-renders. Quantify when you can: "~50ms per item across the list" beats "might be slow."

## Read the Tests Before the Implementation

Tests reveal what the author thinks the code should do. Read them first: do they exist, do they test behavior rather than implementation detail, do they cover the edge cases from axis 1, would they actually fail if the code regressed? A bug fix without a regression test is incomplete — call it out.

## Label Every Finding by Severity

The author needs to know what blocks merge versus what is taste. Unlabeled feedback gets treated as all-mandatory and wastes their time.

| Label | Meaning |
|-------|---------|
| **Critical** | Blocks merge — security hole, data loss, broken functionality, crash |
| **Important** | Should fix before merge — a real bug, missing error path, or maintainability problem |
| **Nit** | Optional — style, naming, formatting; author may ignore |
| **FYI** | No action — context for later, a heads-up, a question |

Anchor each finding to `file:line` and say *why* it matters and *what* to do. "Validate `user_id` here or this 500s on a missing key" beats "add validation."

## Be Honest

A review that flatters is worse than no review. Sycophancy is the failure mode.

- Do not rubber-stamp. "LGTM" with no evidence of reading helps no one.
- Do not soften a real bug into "a minor concern."
- Say the uncomfortable thing directly, then propose the alternative.
- AI-generated code gets *more* scrutiny, not less — it is confident and plausible exactly when it is wrong.
- If the author has full context and overrides you, defer gracefully. Comment on the code, never the person.

## Dead Code Hygiene

If the change orphans code, list it explicitly and ask before assuming — do not silently delete, and do not silently ignore:

```
Now unused after this change:
- formatLegacyDate() in src/utils/date.ts — replaced by formatDate()
- LEGACY_API_URL in src/config.ts — no remaining references
→ Remove these as part of the change?
```

## Output Format

Lead with the verdict so the reader knows the stakes before the detail.

```
## Review: <change title>

**Verdict:** Approve | Approve with nits | Request changes
**Scope:** <N files, ~M lines — what the change does in one sentence>

### Critical
- `path/to/file.py:42` — <what's wrong, why it blocks, the fix>

### Important
- `path/to/file.py:88` — <the bug or risk, and what to do>

### Nits
- `path/to/file.py:12` — <optional improvement>

### FYI
- <context, question, or heads-up — no action required>
```

If an axis surfaced nothing, omit its findings rather than padding with "no issues found." If the whole change is clean, say so plainly and approve — a short honest approval is a valid review. Don't manufacture findings to look thorough.
