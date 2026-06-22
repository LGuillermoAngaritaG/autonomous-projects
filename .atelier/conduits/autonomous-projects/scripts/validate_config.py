"""Pre-flight config validation for autonomous-projects tick.

Stdout contract (always exit 0):
    config_ok: true
    -- or one or more --
    warning: <message>
    note: <message>   (informational, e.g. missing optional config.yaml)

Warn-only: never blocks a tick, never exits non-zero.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


# -- Known schemas -----------------------------------------------------------

_CONFIG_KNOWN_TOP = {"max_usage", "idle-hours-in-project", "automatic_to_do", "max_per_tick"}
_CONFIG_MAX_USAGE_KEYS = {"claude-code", "codex", "opencode"}
_CONFIG_AUTO_TODO_KEYS = {"task", "review", "idea"}
_CONFIG_MAX_PER_TICK_KEYS = {"improve_task", "generate_review", "generate_idea", "to_do"}

_INPUT_INT_RANGE = {
    "max_usage_cc": (0, 100),
    "max_usage_codex": (0, 100),
    "max_usage_opencode": (0, 100),
}
_INPUT_INT_MIN = {
    "max_per_tick_improve_task": 0,
    "max_per_tick_generate_review": 0,
    "max_per_tick_generate_idea": 0,
    "max_per_tick_to_do": 0,
}
_INPUT_HARNESS_KEYS = {"harness_ideation", "harness_development", "harness_review"}
_VALID_HARNESSES = {"cc", "codex", "opencode"}
_INPUT_BOOL_KEYS = {"automatic_to_do_task", "automatic_to_do_review", "automatic_to_do_idea"}


# -- Leaf helpers ------------------------------------------------------------

def _check_int_range(warnings: list[str], key: str, value: object, lo: int, hi: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        warnings.append(f"{key}: expected int in [{lo}, {hi}], got {type(value).__name__} ({value!r})")
    elif value < lo or value > hi:
        warnings.append(f"{key}: value {value} out of range [{lo}, {hi}]")


def _check_num_min(warnings: list[str], key: str, value: object, lo: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        warnings.append(f"{key}: expected number >= {lo}, got {type(value).__name__} ({value!r})")
    elif value < lo:
        warnings.append(f"{key}: value {value} below minimum {lo}")


def _check_bool(warnings: list[str], key: str, value: object) -> None:
    if not isinstance(value, bool):
        warnings.append(f"{key}: expected bool, got {type(value).__name__} ({value!r})")


def _unknown_keys(warnings: list[str], label: str, actual_keys: set[str], known_keys: set[str]) -> None:
    for key in sorted(actual_keys - known_keys):
        warnings.append(f"{label}.{key}: unknown key (likely a typy)")


# -- Config validation -------------------------------------------------------

def load_config(path: Path) -> dict | None:
    """Return parsed dict, or None if file missing / unreadable (fail open)."""
    try:
        import yaml  # noqa: PLC0415 — system-level dep, may not be in uv venv
    except ImportError:
        return None
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return None
    except Exception:
        return None  # fail open


def validate_config(cfg: dict) -> list[str]:
    """Validate parsed config.yaml dict against known schema. Returns warnings list (empty = ok)."""
    warnings: list[str] = []
    if not isinstance(cfg, dict):
        warnings.append(f"config: expected a dict, got {type(cfg).__name__}")
        return warnings

    _unknown_keys(warnings, "config", set(cfg.keys()), _CONFIG_KNOWN_TOP)

    # max_usage.{claude-code,codex,opencode}
    mu = cfg.get("max_usage")
    if mu is not None:
        if isinstance(mu, dict):
            _unknown_keys(warnings, "config.max_usage", set(mu.keys()), _CONFIG_MAX_USAGE_KEYS)
            for tool in ("claude-code", "codex", "opencode"):
                if tool in mu:
                    _check_int_range(warnings, f"config.max_usage.{tool}", mu[tool], 0, 100)
        else:
            warnings.append("config.max_usage: expected a dict")

    # idle-hours-in-project
    ih = cfg.get("idle-hours-in-project")
    if ih is not None:
        _check_num_min(warnings, "config.idle-hours-in-project", ih, 0.0)

    # automatic_to_do.{task,review,idea}
    at = cfg.get("automatic_to_do")
    if at is not None:
        if isinstance(at, dict):
            _unknown_keys(warnings, "config.automatic_to_do", set(at.keys()), _CONFIG_AUTO_TODO_KEYS)
            for key in ("task", "review", "idea"):
                if key in at:
                    _check_bool(warnings, f"config.automatic_to_do.{key}", at[key])
        else:
            warnings.append("config.automatic_to_do: expected a dict")

    # max_per_tick.{improve_task,generate_review,generate_idea,to_do}
    mpt = cfg.get("max_per_tick")
    if mpt is not None:
        if isinstance(mpt, dict):
            _unknown_keys(warnings, "config.max_per_tick", set(mpt.keys()), _CONFIG_MAX_PER_TICK_KEYS)
            for key in ("improve_task", "generate_review", "generate_idea", "to_do"):
                if key in mpt:
                    _check_num_min(warnings, f"config.max_per_tick.{key}", mpt[key], 0)
        else:
            warnings.append("config.max_per_tick: expected a dict")

    return warnings


# -- Inputs validation -------------------------------------------------------

def validate_inputs(values: dict[str, str]) -> list[str]:
    """Validate tick run inputs (strings). Returns warnings list (empty = ok)."""
    warnings: list[str] = []

    for key, (lo, hi) in _INPUT_INT_RANGE.items():
        raw = values.get(key)
        if raw is not None:
            try:
                val = int(raw)
                _check_int_range(warnings, key, val, lo, hi)
            except (ValueError, TypeError):
                warnings.append(f"{key}: could not parse {raw!r} as int")

    for key, lo in _INPUT_INT_MIN.items():
        raw = values.get(key)
        if raw is not None:
            try:
                val = int(raw)
                _check_num_min(warnings, key, val, lo)
            except (ValueError, TypeError):
                warnings.append(f"{key}: could not parse {raw!r} as int")

    for key in _INPUT_HARNESS_KEYS:
        raw = values.get(key)
        if raw is not None and raw not in _VALID_HARNESSES:
            warnings.append(f"{key}: {raw!r} is not a valid harness (expected cc, codex, or opencode)")

    for key in _INPUT_BOOL_KEYS:
        raw = values.get(key)
        if raw is not None and raw not in ("true", "false"):
            warnings.append(f"{key}: {raw!r} is not valid (expected true or false)")

    ih_raw = values.get("idle_hours")
    if ih_raw is not None:
        try:
            val = float(ih_raw)
            _check_num_min(warnings, "idle_hours", val, 0.0)
        except (ValueError, TypeError):
            warnings.append(f"idle_hours: could not parse {ih_raw!r} as number")

    return warnings


# -- CLI ---------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-path", default=None)
    parser.add_argument("--max-usage-cc", default="80")
    parser.add_argument("--max-usage-codex", default="95")
    parser.add_argument("--max-usage-opencode", default="85")
    parser.add_argument("--idle-hours", default="0.1")
    parser.add_argument("--harness-ideation", default="cc")
    parser.add_argument("--harness-development", default="opencode")
    parser.add_argument("--harness-review", default="codex")
    parser.add_argument("--automatic-to-do-task", default="true")
    parser.add_argument("--automatic-to-do-review", default="false")
    parser.add_argument("--automatic-to-do-idea", default="false")
    parser.add_argument("--max-per-tick-improve-task", default="5")
    parser.add_argument("--max-per-tick-generate-review", default="1")
    parser.add_argument("--max-per-tick-generate-idea", default="1")
    parser.add_argument("--max-per-tick-to-do", default="5")
    args = parser.parse_args()

    warnings: list[str] = []

    config_path = Path(args.config_path) if args.config_path else None
    if config_path is not None:
        if config_path.exists():
            cfg = load_config(config_path)
            if cfg is not None:
                warnings.extend(validate_config(cfg))
        else:
            warnings.append(f"note: config.yaml not found at {config_path} (optional mirror, skipping)")

    inputs = {
        "max_usage_cc": args.max_usage_cc,
        "max_usage_codex": args.max_usage_codex,
        "max_usage_opencode": args.max_usage_opencode,
        "idle_hours": args.idle_hours,
        "harness_ideation": args.harness_ideation,
        "harness_development": args.harness_development,
        "harness_review": args.harness_review,
        "automatic_to_do_task": args.automatic_to_do_task,
        "automatic_to_do_review": args.automatic_to_do_review,
        "automatic_to_do_idea": args.automatic_to_do_idea,
        "max_per_tick_improve_task": args.max_per_tick_improve_task,
        "max_per_tick_generate_review": args.max_per_tick_generate_review,
        "max_per_tick_generate_idea": args.max_per_tick_generate_idea,
        "max_per_tick_to_do": args.max_per_tick_to_do,
    }
    warnings.extend(validate_inputs(inputs))

    if not warnings:
        print("config_ok: true")
    else:
        for w in warnings:
            print(w)

    return 0


if __name__ == "__main__":
    sys.exit(main())
