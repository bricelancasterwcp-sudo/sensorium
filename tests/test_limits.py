"""Cap and retention resolution: CLI, then env, then config, then default."""
import json

import pytest

from sensorium.limits import (
    DEFAULT_MAX_BYTES, DEFAULT_MAX_CALLS, DEFAULT_MAX_EVENTS, LimitsError,
    parse_duration, parse_size, resolve, store_policy)


def test_parse_size_suffixes_are_powers_of_1024():
    assert parse_size(0) == 0
    assert parse_size("0") == 0
    assert parse_size("1.5M") == int(1.5 * 1024 ** 2)
    assert parse_size("2KiB") == 2048
    assert parse_size("1KB") == 1024
    assert parse_size("4_096") == 4096
    with pytest.raises(LimitsError):
        parse_size("-1")
    with pytest.raises(LimitsError):
        parse_size("nope")


def test_parse_duration():
    assert parse_duration("30d") == 30 * 86400
    assert parse_duration("12h") == 12 * 3600
    assert parse_duration("2w") == 14 * 86400
    assert parse_duration("45m") == 45 * 60
    assert parse_duration("90s") == 90
    with pytest.raises(LimitsError):
        parse_duration("-5s")


def test_resolve_precedence(tmp_path, monkeypatch):
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path))
    (tmp_path / "config.json").write_text(json.dumps({
        "max_events": 10, "max_bytes": "1K", "max_calls": 4,
    }))
    monkeypatch.setenv("SENSORIUM_MAX_EVENTS", "20")
    monkeypatch.setenv("SENSORIUM_MAX_BYTES", "2K")
    monkeypatch.setenv("SENSORIUM_MAX_CALLS", "8")
    got = resolve(max_events=30, max_bytes="3K", max_calls=9)
    assert (got.max_events, got.max_bytes, got.max_calls) == (30, 3 * 1024, 9)
    env = resolve()
    assert (env.max_events, env.max_bytes, env.max_calls) == (20, 2 * 1024, 8)
    monkeypatch.delenv("SENSORIUM_MAX_EVENTS")
    monkeypatch.delenv("SENSORIUM_MAX_BYTES")
    monkeypatch.delenv("SENSORIUM_MAX_CALLS")
    cfg = resolve()
    assert (cfg.max_events, cfg.max_bytes, cfg.max_calls) == (10, 1024, 4)


def test_no_cap_fills_only_the_unset_knobs(tmp_path, monkeypatch):
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path))
    monkeypatch.setenv("SENSORIUM_MAX_CALLS", "8")
    got = resolve(no_cap=True, max_calls=5)
    assert got.max_calls == 5
    assert got.max_events == 0
    assert got.max_bytes == 0
    assert resolve(no_cap=True).engaged is False


def test_defaults_when_nothing_is_set(tmp_path, monkeypatch):
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path))
    got = resolve()
    assert got.max_events == DEFAULT_MAX_EVENTS
    assert got.max_bytes == DEFAULT_MAX_BYTES
    assert got.max_calls == DEFAULT_MAX_CALLS
    assert got.engaged is True


def test_broken_config_is_an_error(tmp_path, monkeypatch):
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path))
    (tmp_path / "config.json").write_text("[1, 2]")
    with pytest.raises(LimitsError):
        resolve()
    (tmp_path / "config.json").write_text("{")
    with pytest.raises(LimitsError):
        resolve()


def test_store_policy_from_config_and_env(tmp_path, monkeypatch):
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path))
    (tmp_path / "config.json").write_text(json.dumps({
        "store_budget": "1M", "gc_keep": 3, "gc_older_than_days": 2,
    }))
    got = store_policy()
    assert got.max_bytes == 1024 ** 2
    assert got.keep == 3
    assert got.older_than == 2 * 86400
    monkeypatch.setenv("SENSORIUM_STORE_BUDGET", "5K")
    monkeypatch.setenv("SENSORIUM_GC_KEEP", "2")
    monkeypatch.setenv("SENSORIUM_GC_OLDER_THAN", "12h")
    over = store_policy(max_bytes="9K", keep=4, older_than=60)
    assert (over.max_bytes, over.keep, over.older_than) == (9 * 1024, 4, 60.0)
    with pytest.raises(LimitsError):
        store_policy(keep=0)
