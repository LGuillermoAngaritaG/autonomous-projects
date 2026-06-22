"""Check that conduit.yaml repeat: and config.yaml max_per_tick: agree. Run: python3 tests/test_cap_sync.py"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONDUIT_DIR = HERE.parent.parent  # .atelier/conduits/autonomous-projects

CONDUIT = CONDUIT_DIR / "conduit.yaml"
CONFIG = CONDUIT_DIR / "config.yaml"

# Map conduit task name to config.yaml key.
KEY_MAP = {"work_task": "to_do"}
TASKS = ("generate_idea", "generate_review", "improve_task", "work_task")


def parse_repeats(path: Path):
    text = path.read_text()
    out = {}
    for t in TASKS:
        idx = text.index(f"  - {t}:")
        after = text[idx:]
        m = re.search(r"repeat:\s+(\d+)", after)
        assert m, f"repeat: not found after task {t} in {path.name}"
        out[t] = int(m.group(1))
    return out


def parse_config_caps(path: Path):
    text = path.read_text()
    out = {}
    block = re.search(r"max_per_tick:\s*\n((?:\s+\w+:\s+\d+\n?)+)", text)
    assert block, "max_per_tick: block not found"
    for line in block.group(1).splitlines():
        k, v = line.split(":")
        out[k.strip()] = int(v.strip())
    return out


def test_caps_agree():
    repeats = parse_repeats(CONDUIT)
    caps = parse_config_caps(CONFIG)
    for task, repeat_val in repeats.items():
        key = KEY_MAP.get(task, task)
        cfg_val = caps[key]
        assert repeat_val == cfg_val, (
            f"MISMATCH: conduit.yaml {task}.repeat ({repeat_val}) != "
            f"config.yaml max_per_tick.{key} ({cfg_val}). "
            "Edit the task's repeat: in conduit.yaml, then update both mirrors."
        )
    print("ok — all per-tick caps agree across conduit.yaml and config.yaml")


if __name__ == "__main__":
    test_caps_agree()
    print("all passed")
