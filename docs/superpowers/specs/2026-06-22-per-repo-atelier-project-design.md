# Per-repo `.atelier/project/` (single-project model)

**Date:** 2026-06-22
**Status:** Approved design, ready for implementation plan

## Problem

Today `autonomous-projects` is a central registry: projects live in
`projects/<name>/` under the run directory, each `project.md` points at a
separate codebase via a `location:` field, and a picker (`gates/main.py`)
chooses the highest-priority idle project each tick.

We want to flip the model. Instead of registering many projects centrally and
picking one, drop a `.atelier/project/` folder **into the target repo itself**.
The conduit advances that one project — the codebase it lives in. No registry,
no picker, one project per repo.

## Scope & constraints

- **Only state ships (for now).** The conduit machinery (conduit YAML, gates,
  scripts, sub-conduits) stays installed centrally. Only `.atelier/project/`
  (project.md + stage folders) lives in the target repo. Making the whole
  machinery self-contained per repo requires changes in atelier core and is
  **deferred** — out of scope here.
- **Targeting via input param.** The central conduit takes a `project_root`
  input naming the repo. Many repos = many schedules, each with its own
  `project_root`. No registry returns.
- **Codebase is implicit.** The codebase a worker edits is the repo holding
  `.atelier/project/` (i.e. `project_root`). The `location:` frontmatter field
  is removed.
- **No idle gating.** Idle-time eligibility is dropped entirely. Pointing the
  conduit at a repo is an explicit decision to run it; there is no
  recently-touched grace period.
- **Gates: full rewrite** (chosen over a surgical refactor): the
  pick-among-many machinery is retired and replaced by a single-project
  evaluator, with its test suite rewritten.

## Folder layout (in each target repo)

```
<repo>/                       # project_root: the codebase workers edit
  .atelier/project/           # the only thing that ships (for now)
    project.md                # frontmatter + Goal/Description/Constraints
    00_abandoned/
    00_backlog/
    00_tasks/
    01_to-do/
    02_in-progress/
    03_to-review/
    04_done/
    05_blocked/
```

No `<name>` nesting level, no central `projects/`. Stage-folder semantics are
unchanged from today.

## Components

### 1. Conduit `autonomous-projects`

- **New required input** `project_root` — absolute path to the target repo.
- **Remove inputs** `idle_hours`.
- **Remove tasks** `get_projects_dir`, `pick`, `pick_name`.
- **Add task** `resolve_project`: verify
  `$project_root/.atelier/project/project.md` exists; if not, emit an all-zeros
  block plus a `reason` and let the tick no-op. Otherwise run the rewritten
  gate and emit `ideas_left / reviews_left / to_do_left / to_improve_left /
  reason`.
- All downstream paths change from
  `{{get_projects_dir.output}}/projects/{{pick_name.output}}/...`
  to `{{inputs.project_root}}/.atelier/project/...`.
- Branch guards (`generate_idea`, `generate_review`, `improve_task`,
  `work_task`) key off `resolve_project.output.match(...)` instead of
  `pick.output.match(...)`; the `pick_name` dependency is removed.
- Pass `project_root` into `work_task` (threaded to `work-one-todo`).
- `usage_gate` reads `--project-md
  {{inputs.project_root}}/.atelier/project/project.md`.
- Update the conduit `description` and any picker-era comments.

### 2. Gates — full rewrite (single-project evaluator)

`main.py <project_dir>` where `project_dir = $project_root/.atelier/project`.
One linear evaluation, no table, no selection, no idle:

1. No `project.md` → all zeros, `reason: no project.md`.
2. Parse frontmatter — keep `state`, `max_ideas`, `max_reviews`,
   `test_command`, `use_git`, `max_usage_*`. **Drop** `location`, `priority`,
   `max_to_do`, `idle_hours`. Keep the malformed-frontmatter warn-and-default
   behavior and the existing field coercions.
3. `state != working` → all zeros, `reason: paused` (or `bad state` for an
   unrecognized value).
4. Counts (`.md` only where the worker resumes `.md`):
   - `ideas_left   = max(max_ideas   - count(00_backlog/idea_*),   0)`
   - `reviews_left = max(max_reviews - count(00_backlog/review_*), 0)`
   - `to_improve_left = count(00_tasks/*.md)`
   - `to_do_left = count(01_to-do/*.md) + count(02_in-progress/*.md)`
     (in-progress is counted so a stranded task keeps the project eligible and
     the next tick resumes it).
5. Emit the same output block format as today. `project_name` is set to the
   repo basename for human-readable logs only; nothing downstream parses it.

**Delete:** `select_project.py`'s multi-row pick/sort/sentinel logic; collapse
`idle_time.py`, `count_files.py`, `parse_frontmatter.py` into single-project
helpers (drop the per-project loops and the idle computation). Remove the
`--min-idle-minutes` arg.

**Tests:** rewrite `gates/tests/test_pipeline.py` as single-project cases:
no `project.md`, paused, unrecognized state, malformed frontmatter, each bucket
count (ideas/reviews/to-improve/to-do incl. in-progress), all-zero
nothing-to-do, and a fully eligible project.

### 3. Scaffolder `new_project.py`

`uv run python new_project.py --repo <path>` creates `<repo>/.atelier/project/`
with the stage folders and a `project.md` from the template.

- Drop the `name` slug argument, the `Path.cwd()/projects` root, and
  `--location`.
- Keep the atomic build (temp dir + `os.rename`).
- Refuse if `<repo>/.atelier/project/` already exists, or if `<repo>` is not an
  existing writable directory.

### 4. Template `project_template.md`

Drop `location`, `priority`, `max_to_do`, and the optional `idle_hours`
override. Keep `state`, `use_git`, `test_command`, `max_ideas`, `max_reviews`,
and the optional `max_usage_*` overrides, plus the `# Goal` / `# Description` /
`# Constraints` sections.

### 5. `work-one-todo`

- Add input `project_root` (the codebase), threaded from the top conduit.
- In the `advance` prompt: step 2 drops `location` from the frontmatter parse
  list; step 5 changes "cd into the project's `location` directory from the
  frontmatter" to "cd into `{{inputs.project_root}}`".
- `task-with-review` and `run-*` are unchanged — they only pass the composed
  task text through.

### 6. Config / scripts / README / schedules

- `config.yaml`: remove `idle-hours-in-project`; keep caps/usage knobs; update
  picker-era comments.
- `validate_config.py`: drop the `--idle-hours` argument and its checks.
- Delete the now-unused `idle_minutes.py`.
- README: rewrite around the per-repo model and `new_project.py --repo`;
  remove picker/registry and idle language.
- Schedules: add `inputs.project_root: <repo>` per schedule; remove
  `idle_hours`. One schedule per repo to drive several repos.

## Already in flight

`scripts/project_picker.py` and `scripts/project_state.py` (and their tests)
are already deleted in the working tree, consistent with retiring the picker.

## Out of scope

- Making the conduit machinery self-contained per repo (needs atelier core
  changes).
- Any change to stage-folder semantics, the review loop, or harness wiring
  beyond threading `project_root` and removing `location`/idle.

## Success criteria

- `new_project.py --repo <path>` scaffolds `<path>/.atelier/project/` with all
  stage folders and a `location`/`priority`/`idle`-free `project.md`.
- Running `autonomous-projects` with `project_root=<repo>` advances that repo's
  project: idea/review/improve/work branches fire only when their bucket is
  non-empty and the harness is under its usage ceiling, with no idle gate.
- A missing/paused project makes the tick no-op (all-zero gate block).
- Rewritten gates tests pass; no reference to the picker, `location`,
  `priority`, or idle remains in gates, conduit, template, or config.
