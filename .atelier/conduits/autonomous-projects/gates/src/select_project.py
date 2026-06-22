"""Module 4: derive, filter, sort the table and emit the recommended project."""

MIN_IDLE_MINUTES = 15

_EMPTY = {
    "project_name": "",
    "ideas_left": 0,
    "reviews_left": 0,
    "to_do_left": 0,
    "to_improve_left": 0,
}


def select_project(table: list[dict], min_idle: float = MIN_IDLE_MINUTES) -> dict:
    """Pick the recommended project after deriving columns and filtering.

    :param table: fully-populated rows (idle, front-matter, counts).
    :param min_idle: minimum idle minutes a project must have to qualify.
    :returns: chosen row with *_left columns, or a zeroed sentinel if none qualify.
    """
    for row in table:
        row["ideas_left"] = max(row["max_ideas"] - row["count_00_ideas"], 0)
        # to_do_left = tasks actually waiting in 01_to-do (the human approved them),
        # NOT free capacity. work_task must run only when real tasks are queued;
        # gating on capacity made it fire over an empty queue. max_to_do no longer
        # gates anything (the bot never fills 01_to-do — the human does).
        row["to_do_left"] = row["count_01_to_do"]
        row["reviews_left"] = max(row["max_reviews"] - row["count_00_reviews"], 0)
        row["to_improve_left"] = row["count_00_tasks"]

    def _row_min_idle(row: dict) -> float:
        per_project = row.get("idle_hours")
        return per_project * 60 if per_project is not None else min_idle

    survivors = [
        row
        for row in table
        if row["idle_time"] >= _row_min_idle(row)
        and row["state"] == "working"
        and not (
            row["ideas_left"] == 0
            and row["to_do_left"] == 0
            and row["reviews_left"] == 0
            and row["to_improve_left"] == 0
        )
    ]
    if not survivors:
        return dict(_EMPTY)

    survivors.sort(key=lambda r: (r["priority"], -r["idle_time"]))
    return survivors[0]


def format_selection(row: dict) -> str:
    """Render the exact output block for a selected (or empty) row.

    :param row: result of select_project.
    :returns: the formatted multi-line string.
    """
    return (
        f'project_name: "{row["project_name"]}"\n'
        f"ideas_left: {row['ideas_left']}\n"
        f"reviews_left: {row['reviews_left']}\n"
        f"to_do_left: {row['to_do_left']}\n"
        f"to_improve_left: {row['to_improve_left']}"
    )
