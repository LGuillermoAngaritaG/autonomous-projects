# autonomous-projects

**Point it at a codebase and walk away. It comes back with ideas — each with a
spec and a plan — plus code reviews. You approve the good ones, and it
implements them, with a second AI checking the work before it reaches you.**

A [flow-atelier](https://github.com/LGuillermoAngaritaG/flow-atelier) package
that turns a folder of projects into a steady stream of small, reviewed
improvements — without handing over the keys. On a schedule (say, every 30
minutes overnight) it studies one project, proposes ideas and code reviews,
drains any raw tasks you dropped in, and waits. You skim the proposals and drag
the good ones into the work queue. Next tick it implements them, a *second* AI
independently checks the work, and the finished change lands awaiting your final
yes.

Why people keep it running:

- **You stay in control.** The bot proposes and implements; *you* decide what's
  worth doing and what's actually done. It never marks its own work complete.
- **Two-agent quality gate.** Every task is built by one agent and verified by
  another before it reaches you — looped until the reviewer signs off.
- **It works while you don't.** Schedule it overnight and wake up to a triaged
  backlog and reviewed diffs instead of a blank page.
- **Just markdown and folders.** Your whole workflow is files you can read,
  edit, and move by hand. No database, no dashboard to learn.
- **Cost-aware.** It watches each AI tool's live 5-hour usage and backs off a
  tool that's near its limit, so a single overnight run won't burn your quota.

```
bot:  00_backlog/  ──▶  02_in-progress/  ──▶  03_to-review/
you:        └────▶ 01_to-do/                        └─▶ 04_done/
you drop raw tasks ▶ 00_tasks/ ──(bot improves)──▶ 00_backlog/
```

## Quickstart

**1. Install flow-atelier and this package.**

```bash
uv tool install flow-atelier
atelier add LGuillermoAngaritaG/autonomous-projects
atelier list conduits        # confirm autonomous-projects appears
```

**2. Create a workspace folder and your first project.**

```bash
cd ~/work
mkdir -p projects/my-api/{00_backlog,00_tasks,00_abandoned,01_to-do,02_in-progress,03_to-review,04_done}
cat > projects/my-api/project.md << 'EOF'
---
location: /abs/path/to/your/codebase
priority: 1
use_git: true
state: working
max_ideas: 10
max_reviews: 5
max_to_do: 5
---
# Goal
What you want done.

# Description
Short context.

# Constraints
Anything the bot must respect.
EOF
```

**3. Run one tick.**

```bash
atelier run autonomous-projects
```

The first tick creates `projects/`, picks your project, tops up the backlog with proposals, and exits. Nothing reaches `04_done/` yet -- that is your move.

**4. See the output and triage.**

Proposals land in `projects/my-api/00_backlog/`. Move the good ones to `projects/my-api/01_to-do/` -- the next tick will implement them.

For front-matter fields, board mechanics, tick internals, and tuning, see the sections below.

---

## Install

**1. Install [flow-atelier](https://github.com/LGuillermoAngaritaG/flow-atelier)** (one time):

```bash
uv tool install flow-atelier
atelier --version
```

**2. Install this package** with `atelier add` (git URL, `owner/repo`, or a
local path):

```bash
atelier add LGuillermoAngaritaG/autonomous-projects
# or from a local checkout:
atelier add ./atelier-examples/autonomous-projects
```

This installs the conduits globally, so you can run them from **any folder**.
Confirm with:

```bash
atelier list conduits        # autonomous-projects should appear
```

**Requirements:** the picker (`gates`) runs under [`uv`](https://docs.astral.sh/uv/),
and the work/review/idea steps drive AI coding harnesses (Claude Code by
default; Codex and OpenCode optionally). Those tools must be installed and
authenticated for the steps that use them.

---

## Run

`cd` into whatever folder you want to hold your projects, then:

```bash
atelier run autonomous-projects
```

The first run creates a `projects/` folder in the current directory and exits
quietly (no projects yet → nothing to do). The folder you run from *is* your
workspace — run from `~/work` and your projects live there; run from elsewhere
and you get a separate set. Add a project, run again.

---

## Scaffold a project

A project is a folder under `projects/<name>/` containing a `project.md` and a
set of numbered stage folders. The folder name is the project's identity — keep
it a plain slug (`my-api`, no spaces or quotes).

```
projects/
  my-api/
    project.md          ← you write this (goal, constraints, limits)
    00_backlog/         ← bot writes idea_*.md / review_*.md / task_*.md proposals
    00_tasks/           ← you drop RAW task files here; the bot turns them into specs
    00_abandoned/       ← you drop rejected proposals here (+ a note saying why)
    01_to-do/           ← you move approved proposals here = the work queue
    02_in-progress/     ← bot moves a task here while working it
    03_to-review/       ← bot moves it here when done; awaiting your review
    04_done/            ← only you move tasks here
```

`project.md` uses YAML front-matter (the template ships at
`references/project_template.md`):

```markdown
---
location: /abs/path/to/the/codebase   # where the bot does the work
priority: 1                            # 1 = highest; ties broken by longest-idle
use_git: true                          # true = commit each task's work; false = just edit
state: working                         # working | paused  (paused = skip this project)
max_ideas: 10                          # cap on idea_*.md in 00_backlog
max_reviews: 5                         # cap on review_*.md in 00_backlog
max_to_do: 5                           # cap on items in 01_to-do
---
# Goal
What you want done.
# Description
Short context.
# Constraints
Anything the bot must respect — these are binding; it won't work around them.
```

The `project.md` file is **yours** — the bot treats it as read-only and never
edits it. To temporarily skip a project, set `state: paused` (no separate folder
needed). Set it back to `working` to resume.

Missing folders or a missing `project.md` are tolerated: absent fields fall back
to safe defaults (`priority: 5`, `state: working`, every cap `0`), which simply
means that bucket generates nothing until you set a cap.

---

## The task board — what to move, and what to expect

The flow is half bot, half you:

- **Bot proposes** → `00_backlog/`. Each tick it can add ideas (`idea_*.md`),
  code reviews (`review_*.md`), and spec'd tasks (`task_*.md`, from your raw
  inbox — see below).
- **You feed raw tasks** → `00_tasks/`. Drop a rough one-line task; the bot runs
  `/spec` + `/plan` on it and writes a polished `task_*.md` into `00_backlog`,
  then deletes the raw file.
- **You triage** `00_backlog/`: move good proposals to `01_to-do/`, bad ones to
  `00_abandoned/`. Leave your reasoning in the abandoned file — it steers future
  proposals away from that kind.
- **Bot executes** `01_to-do/`: moves a task to `02_in-progress/`, does the work
  (commits if `use_git: true`), then a **second agent judges DONE/NOT_DONE** and
  retries up to 10 times until DONE, then moves it to `03_to-review/`.
- **You approve.** Move finished tasks from `03_to-review/` to `04_done/`. **The
  bot never moves anything to `04_done/`** — that judgment is yours.

Nothing happens to a project until you move proposals into `01_to-do/`. The bot
only ever touches `00_backlog/ → 02_in-progress/ → 03_to-review/` (and drains
`00_tasks/`); everything else is your move.

---

## How a tick works — under the hood

Each `atelier run autonomous-projects` is one **tick**. A tick is a small DAG of
tasks (see `.atelier/conduits/autonomous-projects/conduit.yaml`):

```
get_projects_dir ──▶ pick (gates) ──┐
                 └─▶ usage_gate ─────┤
                                     ├─▶ generate_idea     (ideas_left>0      ∧ ideation_ok)
                                     ├─▶ generate_review   (reviews_left>0    ∧ ideation_ok)
                                     ├─▶ improve_task      (to_improve_left>0 ∧ ideation_ok)
                                     └─▶ work_task         (to_do_left>0      ∧ development_ok ∧ review_ok)
```

### 1. `get_projects_dir`
Ensures `projects/` exists in the run directory and emits its absolute path.
Everything downstream is anchored to it.

### 2. `pick` — the project picker (`gates`)
A small Python CLI (`gates/`, run via `uv`) scans every `projects/<name>/`
folder and prints one project plus how much work each bucket has left:

```
project_name: "my-api"
ideas_left: 9
reviews_left: 5
to_do_left: 5
to_improve_left: 0
```

How it decides:

- **Idle gate.** For each project it finds the most-recently-modified file or
  folder across the four stage folders `00_backlog/`, `01_to-do/`,
  `02_in-progress/`, `03_to-review/`, and computes `idle` = minutes since then.
  A project must have been idle for at least the threshold
  (`--min-idle-minutes`, which the conduit sets to `idle_hours × 60`) to be
  eligible. This measures **task-board staleness** — it stops the bot from
  pouncing on a board you're actively triaging. (Note: it does **not** look at
  the codebase at `location`, and it does **not** use git commit time.)
- **Paused / no-work filters.** Projects with `state: paused`, or with all four
  buckets at `0`, are dropped.
- **The four buckets** (each clamped at `≥ 0`):
  - `ideas_left  = max_ideas   − count(00_backlog/idea_*)`
  - `reviews_left = max_reviews − count(00_backlog/review_*)`
  - `to_do_left  = max_to_do   − count(01_to-do/*)`
  - `to_improve_left = count(00_tasks/*)`   ← raw tasks waiting to be spec'd
- **Selection.** Among eligible projects, sort by `priority` ascending
  (1 wins); break ties by `idle` descending (longest-idle first). The top
  project is printed. If none qualify, every count is `0` and the whole tick
  short-circuits.

A tiny `pick_name` step then extracts the bare `my-api` from that block for use
in folder paths.

### 3. `usage_gate` — cost-aware throttle
Reads each AI tool's live **5-hour usage %** (`scripts/usage.mjs`, which reads
each tool's own local data — no network) and compares it to your ceilings,
emitting:

```
ideation_ok: true
development_ok: true
review_ok: true
```

Each role maps to a harness (configurable, see Tuning): `ideation → cc`
(Claude Code), `development → opencode`, `review → codex`. A tool at or over its
`max_usage_*` ceiling closes the roles it powers. Usage that can't be read is
treated as `0%` (**fail-open**), so a broken read never blocks the loop.

### 4. The four work branches
Each branch runs only when **both** its bucket predicate **and** its usage
role(s) pass (conditions are AND-ed). The bucket predicates are regexes over the
picker's output — e.g. `ideas_left: [1-9]` matches any non-zero count:

| Branch | Runs when | Calls | Writes to |
|---|---|---|---|
| `generate_idea`   | `ideas_left > 0` ∧ `ideation_ok` | `generate-idea` conduit | `idea_*.md` → `00_backlog/` |
| `generate_review` | `reviews_left > 0` ∧ `ideation_ok` | `generate-review` conduit | `review_*.md` → `00_backlog/` |
| `improve_task`    | `to_improve_left > 0` ∧ `ideation_ok` | `improve-task` conduit | `task_*.md` → `00_backlog/` (drains `00_tasks/`) |
| `work_task`       | `to_do_left > 0` ∧ `development_ok` ∧ `review_ok` | `work-one-todo` conduit | advances `01_to-do/` → `03_to-review/` |

> **Heads-up on `work_task`:** it's gated on `to_do_left > 0` (free *capacity* in
> the queue, i.e. `01_to-do/` holds fewer than `max_to_do` items). Inside, it
> advances whatever real tasks are in `01_to-do/`, and no-ops cleanly if the
> queue is empty. A practical consequence: if `01_to-do/` is *full*
> (`count == max_to_do`), `to_do_left` is `0` and execution pauses until you
> raise `max_to_do` or items move out — by design, so the queue can't be both
> capped and drained in the same model.

### 5. Per-tick limits (`max_per_tick_*`)
Each branch loops up to a per-tick cap, then stops early when its bucket is
exhausted. The caps live in the conduit as literal `repeat:` values
(idea `1`, review `1`, improve_task `5`, to_do `5`):

- `improve_task` loops `improve-task` until its `task_counter` hits `0` (inbox
  drained), capped at 5.
- `work_task` loops `work-one-todo` until `01_to-do/` is empty, capped at 5 —
  each iteration carries one task all the way to a DONE verdict.
- Ideas/reviews run once (`repeat: 1`). The `generate-idea`/`generate-review`
  conduits already emit a `remaining:` count tail, so raising their cap is a
  two-line edit (set `repeat: N>1` and add
  `until: 'output.match(remaining:\s*0)'`).

> The atelier engine requires `repeat:` to be a **literal integer** — it cannot
> read `{{inputs.max_per_tick_*}}`. So the caps are mirrored as literals on each
> task, with `config.yaml` / the conduit `inputs:` kept as the human-facing
> record. Bumping a cap is a one-number edit in `conduit.yaml`.

### 6. The two-agent execution loop (`work-one-todo`)
For each to-do task, the `work-one-todo` conduit loops the `task-with-review`
conduit (one builder agent + one independent reviewer agent) up to 10 times
`until` the reviewer returns `VERDICT: DONE`. The builder reads the task, cds
into `location`, does the work, runs the project's **full** test suite (must be
green), fills in the task's `# How was done and tested`, and moves it to
`03_to-review/`. If the reviewer says `NOT_DONE`, its reason becomes the next
iteration's priority. Then `work-one-todo` counts the remaining `01_to-do/`
files so the outer per-tick loop knows whether to advance another task.

---

## Tuning — parameters you control

### Per project (front-matter in `project.md`)

| Field              | What it controls |
|--------------------|------------------|
| `priority`         | 1–5; lower wins when several projects are eligible in a tick. Ties broken by longest-idle. |
| `use_git`          | `true` = commit each task's work; `false` = just edit files. (Does **not** affect the idle calculation.) |
| `state`            | `working` runs; `paused` skips the project entirely. |
| `max_ideas`        | Stop generating ideas once `00_backlog/idea_*.md` reaches this. |
| `max_reviews`      | Stop generating reviews once `00_backlog/review_*.md` reaches this. |
| `max_to_do`        | Free-capacity cap on `01_to-do/`. Drives `to_do_left`; see the work_task heads-up above. |
| `idle_hours`       | *(optional)* Override the run-level `idle_hours` for this project. Falls back to the run-level input when absent. |
| `max_usage_cc`     | *(optional)* Override the run-level `max_usage_cc` ceiling for this project. Falls back to the run-level input when absent. |
| `max_usage_codex`  | *(optional)* Same for Codex. |
| `max_usage_opencode` | *(optional)* Same for OpenCode. |

### Per run (`--input`)

| Input | Default | What it controls |
|-------|---------|------------------|
| `idle_hours` | `0.1` | Minimum task-board idle before a project is eligible, in hours (× 60 → minutes for `gates`). `0.1` ≈ 6 minutes. Raise it to leave more settling time after you triage. |
| `max_usage_cc` | `80` | Claude Code 5h-usage ceiling (%). At/over → its roles close. |
| `max_usage_codex` | `95` | Codex 5h-usage ceiling (%). |
| `max_usage_opencode` | `85` | OpenCode 5h-usage ceiling (%). |
| `harness_ideation` | `cc` | Harness for ideas + reviews + task improvement. |
| `harness_development` | `opencode` | Harness that does the build half of `work_task`. |
| `harness_review` | `codex` | Harness that does the review half of `work_task`. |
| `max_per_tick_generate_idea` | `1` | Documented per-tick cap (mirror in the task's `repeat:`). |
| `max_per_tick_generate_review` | `1` | "" |
| `max_per_tick_improve_task` | `5` | "" |
| `max_per_tick_to_do` | `5` | "" |
| `automatic_to_do_task` / `_review` / `_idea` | `true` / `false` / `false` | Declared for parity with `config.yaml`; not yet wired to any branch. |

```bash
atelier run autonomous-projects --input idle_hours=2 --input max_usage_cc=60
```

---

## Architecture / files

Everything lives under `.atelier/conduits/`:

```
autonomous-projects/
  conduit.yaml          the tick DAG (pick → usage_gate → 4 branches)
  config.yaml           human-facing record of the default knobs
  gates/                the project-picker CLI (uv project)
    main.py             CLI: <projects-root> [--min-idle-minutes N]
    src/idle_time.py        board-staleness idle per project
    src/parse_frontmatter.py  reads project.md front-matter (PyYAML)
    src/count_files.py      counts files per stage folder
    src/select_project.py   derives *_left, filters, sorts, prints the block
    tests/                  6 unit tests (uv run pytest)
  scripts/
    usage_gate.py        live-usage throttle → ideation/development/review _ok
    usage.mjs            reads each tool's local 5h-usage data
    tests/test_usage_gate.py
  references/
    project_template.md  the project.md starter
    task_template.md     the task_*.md starter
generate-idea/           sub-conduit: /idea → /plan → store idea_*.md (+ count tail)
generate-review/         sub-conduit: review → /plan → store review_*.md (+ count tail)
improve-task/            sub-conduit: /spec + /plan a raw task → task_*.md, emits task_counter
improve-all-tasks/       loops improve-task until the inbox drains
work-one-todo/           advances ONE to-do task to DONE, emits task_counter
task-with-review/        one builder agent + one reviewer agent, returns a VERDICT
```

The picker and usage shim are pure and unit-tested; the generation/execution
steps drive the AI harnesses. Sub-conduits receive their folder paths from the
parent, so the numbered-folder layout is defined in one place (`conduit.yaml`).

---

## Schedule it

Run on a timer with a schedule file (point `run_path` at your workspace folder):

```yaml
conduit_name: autonomous-projects
inputs:
  idle_hours: '0.1'
run_path: /abs/path/to/your/workspace
schedule:
  mode: interval
  name: autonomous-projects-30min
  every_minutes: 30
  timezone: America/Bogota
```

```bash
atelier schedule add path/to/schedule.yaml
atelier scheduler start      # foreground daemon; Ctrl+C to stop
```

Overnight, each tick picks the most-deserving idle project, tops up its backlog
with ideas and reviews, improves any raw tasks you dropped, and advances up to
five approved to-do tasks through the two-agent DONE loop — backing off any AI
tool that's near its usage ceiling. You wake up to a triaged backlog and
reviewed diffs waiting for your yes.
