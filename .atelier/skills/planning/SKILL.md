---
name: planning
description: "Turns a raw idea plus whatever context you hand over into a great, decision-complete plan and writes it to a document by default. Plans immediately — makes reasonable assumptions, lists open questions inside the plan, no clarifying-question gate. Use whenever the user gives an idea, feature, project, or change and wants it planned out: 'plan this', 'make a plan for X', 'I want to build Y — plan it', 'lay out how we'd do Z'. Use even when the user doesn't say the word 'plan' but hands over an idea and expects a structured path forward. Not for bug fixes (use a debugging skill) or for value judgments about whether to build something at all."
metadata:
  version: "1.0.0"
---

# Planning: Idea In, Great Plan Out

You're handed an idea and some context. Your job is to turn it into a plan good enough that another engineer or agent could execute it without re-deciding the direction — and to write that plan to a document.

The defining behavior of this skill: **plan immediately.** Don't open with a round of clarifying questions. Make the reasonable assumptions a competent engineer would make, write them down explicitly, and surface anything genuinely undecided as an *Open Questions* section inside the plan. The user chose this skill because they want a plan in their hands now, not a conversation. They will redirect you if an assumption is wrong — that's cheaper for them than answering a questionnaire up front.

## Output: a document by default

Write the finished plan to a file. This is the default and you should do it without asking. Pick the path like this:

- If the project has an obvious home for plans (`plans/`, `docs/plans/`, `tasks/`), write there.
- Otherwise write `./<kebab-slug>-plan.md` in the repo root (or cwd if not in a repo).
- Name the file from the idea: "add Stripe billing" → `stripe-billing-plan.md`.

After writing, tell the user the path in one line. Don't paste the whole plan back into the chat on top of writing the file — point them to it and give a 2-3 sentence summary of the shape (phases, biggest risk, any blocking open question).

**Skip the file only if the user says so** — "just tell me", "no doc", "inline", "don't write a file". Then put the plan in the chat instead. When in doubt, write the file.

## Before you plan

Spend a few minutes grounding the plan in reality. A plan built on guesses about the codebase is worse than no plan.

- Confirm where you are: `pwd` / `git rev-parse --show-toplevel`. Don't assume.
- If the idea touches existing code, read the relevant parts. Identify the patterns and conventions already in use so the plan fits the house style instead of fighting it.
- If the plan involves a config value, env var, or default, open the actual config file and lift the live value. Never quote a default from memory.
- If a framework built-in or official pattern already solves this, that's the default recommendation. Search before inventing a custom approach; use Context7 MCP for current library docs when available.

This is read-only. Don't write code, scaffolding, or pseudo-code — the deliverable is the plan.

## What makes the plan great

A great plan is **concrete, ordered, and verifiable.** Work through these:

### 1. State the goal and the assumptions

Open with one paragraph: what we're building and why. Then list the assumptions you're planning under — the decisions you made on the user's behalf. This is what lets you plan immediately without a question gate: every judgment call is visible, so the user can correct any single one without you having to ask about all of them.

### 2. Pick an approach

Recommend one approach with its rationale: what it builds on, the effort, the risk. Mention a single alternative only if the tradeoff is genuinely close (you'd give it better than ~40% odds the user prefers it). Always note the minimal version.

Then stress the recommendation: name its most fragile load-bearing assumption — "this plan assumes X; if X doesn't hold, Y happens." If that assumption is both fragile and load-bearing, reshape the plan to survive its failure. For plans involving external dependencies, high concurrency, or data migration, also check: what happens if a dependency goes down, what breaks first at 10x scale, and how hard is rollback.

### 3. Slice the work vertically

Build one complete path at a time, not horizontal layers. Each slice should deliver working, testable functionality.

**Bad (horizontal):** "Task 1: all the schema. Task 2: all the API. Task 3: all the UI."
**Good (vertical):** "Task 1: user can register (schema + API + UI). Task 2: user can log in (schema + API + UI)."

Order slices bottom-up by dependency — foundations first — and put high-risk work early so it fails fast.

### 4. Write tasks with acceptance criteria

Each task needs enough that someone could pick it up cold:

```markdown
## Task [N]: [Short descriptive title]

**Description:** One paragraph: what this accomplishes.

**Acceptance criteria:**
- [ ] [Specific, testable condition]
- [ ] [Specific, testable condition]

**Verification:**
- [ ] Tests pass: `<command>`
- [ ] Manual check: [what to look at]

**Dependencies:** [Task numbers, or "None"]

**Files likely touched:**
- `src/path/to/file`

**Scope:** [S: 1-2 files | M: 3-5 | L: 5-8 — break L+ down further]
```

A task is too big if it'd take more than one focused session, needs more than 3 acceptance bullets, touches two independent subsystems, or has "and" in its title. Break it down.

### 5. Add checkpoints

After every 2-3 tasks, insert a checkpoint where the system is in a known-good state — tests pass, builds clean, a user-visible flow works end-to-end. Checkpoints are where a human can sanely review progress.

## Plan document template

```markdown
# Plan: [Idea / Feature Name]

## Goal
[One paragraph: what we're building and why.]

## Assumptions
- [Decision made on the user's behalf — correct any that are wrong]
- [...]

## Approach
[Chosen approach + rationale. Alternative only if the tradeoff is close.]
**Fragile assumption:** This plan assumes [X]. If it doesn't hold, [Y].

## Tasks

### Phase 1: Foundation
- [ ] Task 1: ...
- [ ] Task 2: ...
### Checkpoint: Foundation — tests pass, builds clean

### Phase 2: Core
- [ ] Task 3: ...
### Checkpoint: Core — end-to-end flow works

## Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| ... | High/Med/Low | ... |

## Open Questions
- [Genuinely undecided item the user should weigh in on. Each one notes what
  you assumed in the meantime so work isn't blocked waiting for an answer.]
```

Expand or collapse phases to fit the actual work — a small idea might be one phase of three tasks; don't pad it.

## No placeholders

Every step in the plan must be concrete. No "TBD", no "implement later", no "similar to step N", no "details to be determined". A plan full of placeholders is just a promise to plan later. Open Questions are the *one* allowed home for genuine unknowns — and each must say what you assumed so the work proceeds anyway.

## After writing

Point the user to the file and summarize in 2-3 sentences. If they say "implement this" / "go" / "do it", treat that as approval of the written plan — state which plan you're executing, check for obvious repo drift, and proceed. Don't re-litigate the design. If the repo has drifted enough that the plan is unsafe, name the specific drift and stop before editing.
