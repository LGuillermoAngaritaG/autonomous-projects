# autonomous-projects — how to use

A flow-atelier conduit that advances ONE project living in a target repo's
`.atelier/project/` folder. You point it at a repo and say how much to do this
"tick"; it studies the project, proposes ideas + code reviews, specs raw tasks,
and advances approved work — with a second agent re-running the tests before
anything reaches the human. Full detail: repo `README.md`.

## The one mental model

- **The bot proposes and implements. The human decides what's worth doing and
  what's actually done.** Proposals land in `00_backlog/`; the human drags good
  ones into `01_to-do/`; the bot works those. **Nothing ever auto-promotes to
  `04_done/` — that's the human's move.** Don't do it for them unasked.

## Run a tick

```bash
atelier run autonomous-projects --input project_root=/abs/path/to/repo \
  --input n_ideas=2 --input n_reviews=1 --input n_improve=0 --input n_todo=3
```

- `project_root` (required): absolute path to the repo that holds
  `.atelier/project/` — the codebase the bot edits.
- `n_ideas` / `n_reviews` / `n_improve` / `n_todo`: how many of each activity
  this tick. **All default `0`, so a bare run does nothing.** Name only what you
  want. `n_improve` drains raw tasks from `00_tasks/`; `n_todo` advances approved
  tasks from `01_to-do/`. Both stop early if their queue empties.
- `max_usage` (default `80`): skip an activity if the harness's live 5h usage is
  at/over this %.

## First time on a repo

1. Need `uv`, the `claude` CLI, and `python3` on PATH (the tick's `dep_guard`
   checks this and fails fast if missing).
2. If the repo has no `.atelier/project/`, scaffold it:
   ```bash
   atelier run scaffold-project --input project_root=/abs/path/to/repo
   ```
3. Open `<repo>/.atelier/project/project.md` and fill in `# Goal` /
   `# Constraints` (optionally a `test_command:`). This file is the human's —
   read it, never overwrite it.

## The board (what moves where)

```
bot:  00_backlog/  ──▶  02_in-progress/  ──▶  03_to-review/
you:        └────▶ 01_to-do/                        └─▶ 04_done/
you drop raw tasks ▶ 00_tasks/ ──(bot improves)──▶ 00_backlog/
stalled task ▶ 05_blocked/ (bot parks what it couldn't finish, with a note)
```

- Bot writes `idea_*.md` / `review_*.md` / `task_*.md` → `00_backlog/`.
- Human triages: good → `01_to-do/`, bad → `00_abandoned/` (leave a why-note;
  it steers future proposals away).
- Bot picks the highest-priority `01_to-do/` task, builds it, a second agent
  re-runs the tests and judges DONE/NOT_DONE (up to 10 retries), then moves it
  to `03_to-review/` — or `05_blocked/` if it gave up.
- Human approves: `03_to-review/` → `04_done/`.

## Feeding tasks

Two ways to get the bot to *do* work (vs. propose it):

1. **Drop a raw task** into `00_tasks/` — a `.md` file with whatever you want
   done, even one rough line of plain text (no frontmatter needed). Run a tick
   with `--input n_improve=N`: the bot runs `/spec` + `/plan` on it, writes a
   polished `task_*.md` into `00_backlog/` (your wording is carried verbatim into
   `# Description`), and deletes the raw file. Then triage it like any proposal:
   move to `01_to-do/` and advance with `n_todo`.
2. **Write a ready task** straight into `01_to-do/` and advance it with
   `--input n_todo=N` — skips the spec/plan step. Use the `references/task_template.md`
   shape; you only need to fill `# Description` (and set `priority`). The bot
   fills `# Spec` / `# Plan` / `# What was done` / `# How was done and tested`.

**Priority steers order.** The bot picks the `01_to-do/` task with the lowest
`priority:` number first (ties broken by filename); blank/missing sorts last.
Generated proposals get defaults — tasks `1`, reviews `2`, ideas `3` — so set
`priority` to override what runs first.

Don't pre-fill `# Spec`/`# Plan`/`# What was done`/`# How was done and tested` —
those are the bot's to write. `project.md` and the task `# Description` are yours.

## Schedule it (optional)

Run on a timer — one schedule file per repo, with the per-tick counts you want:

```yaml
conduit_name: autonomous-projects
inputs: {project_root: /abs/path/to/repo, n_ideas: "2", n_reviews: "1", n_todo: "5"}
schedule: {mode: interval, name: autonomous-projects-30min, every_minutes: 30, timezone: America/Bogota}
```

```bash
atelier schedule add path/to/schedule.yaml
atelier scheduler start
```

Wrap the run in `scripts/tick_lock.py` if ticks can overlap (a tick may run up
to 2h) so a slow tick doesn't race the next.
