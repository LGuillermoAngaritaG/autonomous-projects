"""Emit per-role usage-throttle flags for the current tick.

Stdout contract (always exit 0):
    ideation_ok: true|false
    development_ok: true|false
    review_ok: true|false

Each role's live 5h usage (usage.mjs) is compared against the harness ceiling
that does its work:
    ideation_ok     -> harness_ideation       (gates generate_idea + generate_review)
    development_ok  -> harness_development     (gates work_on_to_do, with review_ok)
    review_ok       -> harness_review          (gates work_on_to_do, with development_ok)
A tool at or over its max_usage_* ceiling closes its role. Usage that can't be
read is treated as 0% (fail open), so a broken read never blocks the loop.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Maps a harness short name (the conduit's harness_* inputs) to the usage.mjs
# label and the conduit's matching max_usage_* ceiling.
HARNESS_TOOL = {"cc": "claudecode", "codex": "codex", "opencode": "opencode"}


def read_usage() -> dict[str, int]:
    """Live 5h usage % per usage.mjs label. Fail open: empty on any error."""
    script = Path(__file__).resolve().parent / "usage.mjs"
    usage: dict[str, int] = {}
    try:
        out = subprocess.run(
            ["node", str(script)],
            capture_output=True, text=True, timeout=120,
        ).stdout
    except Exception:
        return usage
    for line in out.splitlines():
        label, _, val = line.partition(":")
        try:
            usage[label.strip()] = int(val.strip().rstrip("%"))
        except ValueError:
            pass  # "n/a" or junk -> leave unset (treated as 0%)
    return usage


def role_ok(role_harness: str, usage: dict[str, int], max_usage: dict[str, int]) -> bool:
    """True unless the harness running this role is at/over its ceiling.

    :param role_harness: harness short name for the role (cc/codex/opencode).
    :param usage: live usage % keyed by usage.mjs label.
    :param max_usage: ceiling % keyed by usage.mjs label.
    :returns: False only when a known harness is at/over its ceiling.
    """
    tool = HARNESS_TOOL.get(role_harness)
    if tool is None:
        return True  # unknown harness -> don't throttle on it
    return usage.get(tool, 0) < max_usage.get(tool, 100)


CEILING_KEYS = ("max_usage_cc", "max_usage_codex", "max_usage_opencode")
_HARNESS_CEILING = {"cc": "max_usage_cc", "codex": "max_usage_codex", "opencode": "max_usage_opencode"}


def read_project_ceilings(path: str) -> dict[str, int]:
    if not path:
        return {}
    md = Path(path)
    if not md.is_file():
        return {}
    try:
        text = md.read_text(encoding="utf-8")
    except OSError:
        return {}
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    result: dict[str, int] = {}
    for line in m.group(1).splitlines():
        for key in CEILING_KEYS:
            prefix = key + ":"
            if line.strip().startswith(prefix):
                val = line.strip()[len(prefix):].strip()
                try:
                    result[key] = int(val)
                except ValueError:
                    pass
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-usage-cc", type=int, default=100)
    parser.add_argument("--max-usage-codex", type=int, default=100)
    parser.add_argument("--max-usage-opencode", type=int, default=100)
    parser.add_argument("--harness-ideation", default="cc")
    parser.add_argument("--harness-development", default="opencode")
    parser.add_argument("--harness-review", default="codex")
    parser.add_argument("--project-md", default="")
    args = parser.parse_args()

    usage = read_usage()
    max_usage = {
        "claudecode": args.max_usage_cc,
        "codex": args.max_usage_codex,
        "opencode": args.max_usage_opencode,
    }
    ceilings = read_project_ceilings(args.project_md)
    for harness_key, usage_key in _HARNESS_CEILING.items():
        if usage_key in ceilings:
            max_usage[HARNESS_TOOL[harness_key]] = ceilings[usage_key]
    flags = {
        "ideation_ok": role_ok(args.harness_ideation, usage, max_usage),
        "development_ok": role_ok(args.harness_development, usage, max_usage),
        "review_ok": role_ok(args.harness_review, usage, max_usage),
    }
    for key, val in flags.items():
        print(f"{key}: {str(val).lower()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
