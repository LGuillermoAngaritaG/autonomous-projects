# autonomous-projects

**Point it at a codebase and walk away. It comes back with ideas with a spec and plan ready, then when you accept them, it can implement them.**

A [flow-atelier](https://github.com/LGuillermoAngaritaG/flow-atelier) package
that turns a folder of projects into a steady stream of small, reviewed
improvements — without handing the keys over. On a schedule (say, every 30
minutes overnight) it studies one project, proposes an idea and a code review,
and waits. You skim the proposals and drag the good ones into `to-do/`. Next
tick it implements them, a *second* AI independently checks the work, and the
finished change lands in `in-review/` for your final yes.

Why people keep it running:

- **You stay in control.** The bot proposes and implements; *you* decide what's
  worth doing and what's actually done. It never merges its own homework.
- **Two-agent quality gate.** Every task is built by one agent and verified by
  another before it reaches you — looped until the reviewer signs off.
- **It works while you don't.** Schedule it overnight and wake up to a triaged
  backlog and reviewed diffs instead of a blank page.
- **Just markdown and folders.** Your whole workflow is files you can read,
  edit, and move by hand. No database, no dashboard to learn.

```
bot:  backlog/  ──▶  in-progress/  ──▶  in-review/
you:        └─▶ to-do/                        └─▶ done/
```

## Install

**1. Install [flow-atelier](https://github.com/LGuillermoAngaritaG/flow-atelier)** (one time, if you don't have it):

```bash
uv tool install flow-atelier
atelier --version
```

**2. Install this package** with `atelier add` (git URL, `owner/repo`, or a
local path):

```bash
atelier add LGuillermoAngaritaG/autonomous-projects    # from the repo
# or from a local checkout:
atelier add ./atelier-examples/autonomous-projects
```

This installs the conduits globally, so you can run them from **any folder**.
Confirm with:

```bash
atelier list conduits        # autonomous-projects should appear
```

## Run

`cd` into whatever folder you want to hold your projects, then:

```bash
atelier run autonomous-projects
```

The first run scaffolds `projects/working/`, `projects/paused/`, and `tasks/`
in the current folder, then exits with `SKIP` (no projects yet). The folder you
run from *is* your workspace — run from `~/work` and your projects live there;
run from somewhere else and you get a separate set. Add a project, run again.

## Scaffold a project

A project is one markdown file in `projects/working/`. The filename stem is the
project's identity — keep it a plain slug (`my-api.md`, no spaces or quotes).
Create the file with this shape (the same template ships at
`references/project_template.md` in the package):

```markdown
---
location: /abs/path/to/the/codebase   # where the bot does the work
priority: 1                            # 1 = highest; ties broken by oldest file
use_git: true                          # true = commit changes; false = just edit
max_ideas: 10
max_reviews: 5
max_to_review: 5
---
# Goal
What you want done.
# Description
Short context.
# Constraints
Anything the bot must respect — these are binding; it won't work around them.
```

The project file is **yours** — the bot treats it as read-only and never edits
it. 

To temporarily skip a project, drop a file with the **same name** in
`projects/paused/`.

## The task board — what to move, and what to expect

Each project gets a kanban folder tree under `tasks/<name>/`, created
automatically:

```
backlog/       bot writes idea_*.md and review_*.md proposals here
abandoned/     you drop rejected proposals here (+ a note saying why)
to-do/         you move approved proposals here = the work queue
in-progress/   bot moves a task here while working it
in-review/     bot moves it here when done; awaiting your review
done/          only you move tasks here
```

The flow is half bot, half you:

- **Bot proposes.** Each tick it adds at most one idea and one review to
  `backlog/`.
- **You triage** `backlog/`: move good proposals to `to-do/`, bad ones to
  `abandoned/`. Leave your reasoning in the abandoned file — it steers future
  proposals away from that kind.
- **Bot executes** `to-do/`: moves a task to `in-progress/`, does the work
  (commits if `use_git: true`), then a second agent judges DONE/NOT_DONE and
  re-tries up to 10 times until DONE, then moves it to `in-review/`.
- **You approve.** Move finished tasks from `in-review/` to `done/`. **The bot
  never moves anything to `done/`** — that judgment is yours.

What to expect: nothing happens to a project until you move proposals into
`to-do/`. The bot only ever touches `backlog/ → in-progress/ → in-review/`;
everything else is your move.

## Tuning — parameters you control

**Per project** (frontmatter in the project file):

| Field           | What it controls |
|-----------------|------------------|
| `priority`      | 1–5; lower wins when several projects are eligible in a tick. |
| `use_git`       | `true` = commit each task's work; `false` = just edit files. |
| `max_ideas`     | Stop generating ideas once `backlog/idea_*.md` reaches this. |
| `max_reviews`   | Stop generating reviews once `backlog/review_*.md` reaches this. |
| `max_to_review` | Pause *executing* `to-do/` once `in-review/` reaches this — so finished work doesn't pile up unreviewed. Generation keeps going. |

Raise `max_ideas`/`max_reviews` to let the backlog grow faster; lower them to
keep the bot quiet until you've triaged. Lower `max_to_review` to force
yourself to review before more work lands.

**Per run** (`--input`):

| Input        | Default | What it controls |
|--------------|---------|------------------|
| `idle_hours` | `0.1`   | A project is skipped if its `location` was edited (or committed, when `use_git`) more recently than this. Prevents the bot from stepping on code you're actively touching. |

```bash
atelier run autonomous-projects --input idle_hours=2
```

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
