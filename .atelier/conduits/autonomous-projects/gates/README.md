# gates

Recommends the next project for an assistant to work on. Scans a `Projects/` root
(one subdir per project, each with a `project.md` front-matter file and stage
folders `00_backlog/`, `01_to-do/`, `02_in-progress/`, `03_to-review/`) through a
four-stage pipeline -- idle time, front-matter, file counts, selection -- and prints
the single recommended project.

```bash
uv run python main.py /path/to/Projects
```

Selection rules: sort by `priority` ascending, tie-break by `idle_time` descending;
skip projects idle < 15 min, paused (`state: paused`), or with no work left in any bucket.
Prints an empty block if nothing qualifies. Tests: `uv run pytest -q`.
