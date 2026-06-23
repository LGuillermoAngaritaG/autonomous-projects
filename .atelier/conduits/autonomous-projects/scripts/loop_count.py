"""Per-tick activity counter: rides {{loop.previous}} to stop a loop at N.

The engine's `repeat:` is a static int and `until:` a regex parsed once, so a
runtime per-tick count can't live on either. Instead each activity loops to a
high literal `repeat:` ceiling and this counter trips the static
`until: output.match(remaining:\\s*0)` once `target` activities have run.

`prior` is the previous iteration's sink output (carried by {{loop.previous}},
empty on iteration 1); `target` is the activity's n_* input.

Phases (always exit 0):
    --phase count    (leading, gates the activity)
        done = made-so-far parsed from prior.
        done >= target -> "made: <done>\\nremaining: 0"  (skip + stop signal)
        else           -> "made: <done>"
    --phase advance  (trailing, after the activity ran)
        "made: <done+1>\\nremaining: <max(target-done-1, 0)>"

The advance task must be the sub-conduit's sink so its `made:` rides forward in
{{loop.previous}}. The count early-skip is a belt-and-suspenders stop if a
round-trip ever drops the counter.
"""

from __future__ import annotations

import argparse
import re
import sys

_MADE_RE = re.compile(r"made:\s*(\d+)")


def parse_made(prior: str) -> int:
    """Last 'made: N' in prior (the carried counter), or 0 if absent."""
    matches = _MADE_RE.findall(prior or "")
    return int(matches[-1]) if matches else 0


def count_phase(prior: str, target: int) -> str:
    """Leading gate output: emit remaining: 0 once the target is reached."""
    done = parse_made(prior)
    if done >= target:
        return f"made: {done}\nremaining: 0"
    return f"made: {done}"


def advance_phase(prior: str, target: int) -> str:
    """Trailing counter output after the activity ran this iteration."""
    done = parse_made(prior)
    return f"made: {done + 1}\nremaining: {max(target - done - 1, 0)}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("count", "advance"), required=True)
    parser.add_argument("--prior", default="")
    parser.add_argument("--target", type=int, required=True)
    args = parser.parse_args()

    if args.phase == "count":
        print(count_phase(args.prior, args.target))
    else:
        print(advance_phase(args.prior, args.target))
    return 0


if __name__ == "__main__":
    sys.exit(main())
