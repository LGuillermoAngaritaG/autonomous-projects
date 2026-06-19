"""Count unprocessed .md tasks left in the inbox; print 'task_counter: N'.

Emitted by improve-task's count_remaining task so the parent improve-all-tasks
loop can break when the inbox drains (until: output.match(task_counter:\\s*0)).
"""
import os
import sys


def main() -> None:
    inbox = sys.argv[1] if len(sys.argv) > 1 else ""
    if not inbox or not os.path.isdir(inbox):
        print("task_counter: 0")
        return
    remaining = sum(
        1
        for name in os.listdir(inbox)
        if name.lower().endswith(".md") and os.path.isfile(os.path.join(inbox, name))
    )
    print(f"task_counter: {remaining}")


if __name__ == "__main__":
    main()
