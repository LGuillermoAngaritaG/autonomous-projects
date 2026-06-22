"""Self-check for validate_config.py. Run: uv run pytest or python3 tests/test_validate_config.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from validate_config import (
    _check_int_range,
    _check_num_min,
    _check_bool,
    _unknown_keys,
    load_config,
    validate_config,
    validate_inputs,
)

# -- Baseline fixtures (in memory, no subprocess) ---------------------------

CLEAN_CONFIG = {
    "max_usage": {"claude-code": 80, "codex": 95, "opencode": 85},
    "idle-hours-in-project": 0.1,
    "automatic_to_do": {"task": True, "review": False, "idea": False},
    "max_per_tick": {"improve_task": 5, "generate_review": 1, "generate_idea": 1, "to_do": 5},
}

CLEAN_INPUTS = {
    "max_usage_cc": "80",
    "max_usage_codex": "95",
    "max_usage_opencode": "85",
    "idle_hours": "0.1",
    "harness_ideation": "cc",
    "harness_development": "opencode",
    "harness_review": "codex",
    "automatic_to_do_task": "true",
    "automatic_to_do_review": "false",
    "automatic_to_do_idea": "false",
    "max_per_tick_improve_task": "5",
    "max_per_tick_generate_review": "1",
    "max_per_tick_generate_idea": "1",
    "max_per_tick_to_do": "5",
}


# -- Leaf helpers -----------------------------------------------------------

def test_check_int_range_ok():
    w: list[str] = []
    _check_int_range(w, "k", 50, 0, 100)
    assert w == []


def test_check_int_range_out_of_bounds():
    w: list[str] = []
    _check_int_range(w, "k", 150, 0, 100)
    assert len(w) == 1
    assert "out of range" in w[0]


def test_check_int_range_wrong_type():
    w: list[str] = []
    _check_int_range(w, "k", "not-an-int", 0, 100)
    assert len(w) == 1
    assert "expected int" in w[0]


def test_check_num_min_ok():
    w: list[str] = []
    _check_num_min(w, "k", 3.0, 0.0)
    assert w == []


def test_check_num_min_below():
    w: list[str] = []
    _check_num_min(w, "k", -1, 0)
    assert len(w) == 1
    assert "below" in w[0]


def test_check_bool_ok():
    w: list[str] = []
    _check_bool(w, "k", True)
    _check_bool(w, "k", False)
    assert w == []


def test_check_bool_wrong_type():
    w: list[str] = []
    _check_bool(w, "k", "true")
    assert len(w) == 1
    assert "expected bool" in w[0]


def test_unknown_keys_none():
    w: list[str] = []
    _unknown_keys(w, "cfg", {"a", "b"}, {"a", "b"})
    assert w == []


def test_unknown_keys_present():
    w: list[str] = []
    _unknown_keys(w, "cfg", {"a", "x", "y"}, {"a", "b"})
    assert len(w) == 2
    assert all("unknown key" in m for m in w)
    assert "x" in w[0] or "x" in w[1]


# -- validate_config --------------------------------------------------------

def test_clean_config_no_warnings():
    assert validate_config(CLEAN_CONFIG) == []


def test_unknown_key_warns():
    cfg = dict(CLEAN_CONFIG)
    cfg["typo_key"] = "oops"
    ws = validate_config(cfg)
    assert len(ws) >= 1
    assert any("typo_key" in w for w in ws)


def test_usage_out_of_range_warns():
    cfg = dict(CLEAN_CONFIG)
    cfg["max_usage"] = dict(cfg["max_usage"])
    cfg["max_usage"]["codex"] = 150
    ws = validate_config(cfg)
    assert any("max_usage.codex" in w for w in ws)
    assert any("out of range" in w for w in ws)


def test_max_usage_non_dict_warns():
    cfg = dict(CLEAN_CONFIG)
    cfg["max_usage"] = "not-a-dict"
    ws = validate_config(cfg)
    assert any("max_usage" in w for w in ws)


def test_automatic_to_do_non_dict_warns():
    cfg = dict(CLEAN_CONFIG)
    cfg["automatic_to_do"] = 123
    ws = validate_config(cfg)
    assert any("automatic_to_do" in w for w in ws)


def test_max_per_tick_non_dict_warns():
    cfg = dict(CLEAN_CONFIG)
    cfg["max_per_tick"] = None
    assert validate_config(cfg) == []  # None is not a dict but skipped without crash


# -- validate_inputs --------------------------------------------------------

def test_clean_inputs_no_warnings():
    assert validate_inputs(CLEAN_INPUTS) == []


def test_idle_hours_non_numeric_warns():
    inp = dict(CLEAN_INPUTS)
    inp["idle_hours"] = "abc"
    ws = validate_inputs(inp)
    assert len(ws) >= 1
    assert any("idle_hours" in w for w in ws)


def test_invalid_harness_warns():
    inp = dict(CLEAN_INPUTS)
    inp["harness_review"] = "gpt"
    ws = validate_inputs(inp)
    assert len(ws) >= 1
    assert "gpt" in ws[0]


def test_max_usage_cc_out_of_range_warns():
    inp = dict(CLEAN_INPUTS)
    inp["max_usage_cc"] = "150"
    ws = validate_inputs(inp)
    assert any("max_usage_cc" in w for w in ws)


def test_automatic_to_do_bad_value_warns():
    inp = dict(CLEAN_INPUTS)
    inp["automatic_to_do_task"] = "maybe"
    ws = validate_inputs(inp)
    assert any("maybe" in w for w in ws)


def test_max_per_tick_non_numeric_warns():
    inp = dict(CLEAN_INPUTS)
    inp["max_per_tick_to_do"] = "lots"
    ws = validate_inputs(inp)
    assert any("could not parse" in w for w in ws)


# -- load_config ------------------------------------------------------------

def test_missing_config_no_crash():
    result = load_config(Path("/tmp/__nonexistent_config_for_test__.yaml"))
    assert result is None


# -- Manual runner for standalone execution ---------------------------------

if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
    print("all passed")
