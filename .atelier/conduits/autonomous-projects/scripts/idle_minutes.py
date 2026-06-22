"""Convert idle_hours -> minutes; bad/blank input -> default with a warning (never raises)."""

import sys

DEFAULT_HOURS = 0.1


def to_minutes(raw: str, default_hours: float = DEFAULT_HOURS) -> float:
    """Parse idle_hours into minutes, falling back to a safe default on bad input.

    :param raw: the raw idle_hours value (may be blank or non-numeric).
    :param default_hours: hours to use when raw can't be parsed.
    :returns: idle minutes; never raises.
    """
    try:
        return float(raw.strip()) * 60.0
    except (ValueError, AttributeError):
        sys.stderr.write(f"warning: bad idle_hours {raw!r}; using {default_hours}h\n")
        return default_hours * 60.0


if __name__ == "__main__":
    print(to_minutes(sys.argv[1] if len(sys.argv) > 1 else ""))
