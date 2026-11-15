"""Per-run recording caps and the store retention policy.

Resolution order, first value wins:

1. A CLI flag (``None`` means the flag was not passed).
2. An environment variable, when it is set and non-empty.
3. A key in ``$SENSORIUM_DIR/config.json`` (or ``~/.sensorium/config.json``
   when ``SENSORIUM_DIR`` is unset).
4. The built-in default.

A value of ``0`` means unlimited for that knob. ``--no-cap`` is unlimited
for every knob the command did not set explicitly.

The config file is a JSON object. Unknown keys are ignored. The keys this
module reads:

- ``max_events``, ``max_bytes``, ``max_calls``: the per-run cap.
- ``store_budget``: optional total size of the trace store, in bytes.
- ``gc_keep``: optional maximum number of traces to retain.
- ``gc_older_than_days``: optional age after which a trace may be removed.

``sensorium gc`` applies whichever of the three retention knobs it was
given. A run applies them automatically only when at least one is set in
the environment or the config file.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MAX_EVENTS = 100_000
DEFAULT_MAX_BYTES = 8 * 1024 * 1024
# Above the largest same-function burst the suite records (300 tasks) and
# far below a hot loop. A lower default would mark those traces truncated.
DEFAULT_MAX_CALLS = 1024

ENV_EVENTS = "SENSORIUM_MAX_EVENTS"
ENV_BYTES = "SENSORIUM_MAX_BYTES"
ENV_CALLS = "SENSORIUM_MAX_CALLS"
ENV_BUDGET = "SENSORIUM_STORE_BUDGET"
ENV_KEEP = "SENSORIUM_GC_KEEP"
ENV_OLDER = "SENSORIUM_GC_OLDER_THAN"

_BYTES = {
    "kib": 1024, "kb": 1024, "k": 1024,
    "mib": 1024 ** 2, "mb": 1024 ** 2, "m": 1024 ** 2,
    "gib": 1024 ** 3, "gb": 1024 ** 3, "g": 1024 ** 3,
}
_DURATION = {"w": 7 * 86400, "d": 86400, "h": 3600, "m": 60, "s": 1}


class LimitsError(ValueError):
    """A cap, a size, or a duration that cannot be read."""


@dataclass(frozen=True)
class Limits:
    """The cap one recording is made under. ``0`` on a field is unlimited."""

    max_events: int
    max_bytes: int
    max_calls: int

    @property
    def engaged(self) -> bool:
        return bool(self.max_events or self.max_bytes or self.max_calls)


@dataclass(frozen=True)
class StorePolicy:
    """What ``gc`` is allowed to delete. ``None`` means that knob is off."""

    max_bytes: int | None = None
    keep: int | None = None
    older_than: float | None = None

    def is_empty(self) -> bool:
        return (self.max_bytes is None and self.keep is None
                and self.older_than is None)


def parse_size(text) -> int:
    """Bytes or a count. ``0`` is unlimited. ``K``/``M``/``G`` are powers of 1024.

    ``KB``/``MB``/``GB`` and ``KiB``/``MiB``/``GiB`` are the same powers.
    A fractional magnitude (``1.5M``) is accepted and truncated toward zero.
    """
    if isinstance(text, bool) or text is None:
        raise LimitsError(f"not a size: {text!r}")
    if isinstance(text, int):
        if text < 0:
            raise LimitsError(f"size must be >= 0 (got {text})")
        return text
    if isinstance(text, float):
        if text < 0:
            raise LimitsError(f"size must be >= 0 (got {text})")
        return int(text)
    raw = str(text).strip().lower().replace("_", "")
    if not raw:
        raise LimitsError("empty size")
    mult = 1
    # Longest suffix first, so "1mb" is mega and not the "m" prefix of it.
    for suffix, factor in sorted(_BYTES.items(), key=lambda kv: len(kv[0]),
                                 reverse=True):
        if raw.endswith(suffix) and raw[:-len(suffix)]:
            mult = factor
            raw = raw[:-len(suffix)].strip()
            break
    try:
        number = float(raw) if "." in raw else int(raw, 10)
    except ValueError as e:
        raise LimitsError(f"not a size: {text!r}") from e
    if number < 0:
        raise LimitsError(f"size must be >= 0 (got {text!r})")
    return int(number * mult)


def parse_duration(text) -> float:
    """Seconds. A bare number is seconds. ``30d``, ``12h``, ``2w``, ``45m``, ``90s``."""
    if isinstance(text, bool) or text is None:
        raise LimitsError(f"not a duration: {text!r}")
    if isinstance(text, (int, float)):
        if text < 0:
            raise LimitsError(f"duration must be >= 0 (got {text})")
        return float(text)
    raw = str(text).strip().lower().replace("_", "")
    if not raw:
        raise LimitsError("empty duration")
    mult = 1.0
    if raw[-1] in _DURATION and not raw[-1].isdigit():
        mult = float(_DURATION[raw[-1]])
        raw = raw[:-1].strip()
        if not raw:
            raise LimitsError(f"not a duration: {text!r}")
    try:
        number = float(raw)
    except ValueError as e:
        raise LimitsError(f"not a duration: {text!r}") from e
    if number < 0:
        raise LimitsError(f"duration must be >= 0 (got {text!r})")
    return number * mult


def config_path(environ: dict | None = None) -> Path:
    env = os.environ if environ is None else environ
    root = env.get("SENSORIUM_DIR")
    base = Path(root) if root else Path.home() / ".sensorium"
    return base / "config.json"


def load_config(environ: dict | None = None) -> dict:
    """The store config object, or ``{}`` when there is no file.

    A file that exists and is not a JSON object is an error: ignoring it
    would apply the defaults and delete, or record, on a policy the user
    thought they had written.
    """
    path = config_path(environ)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise LimitsError(f"cannot read {path}: {e}") from e
    if not isinstance(data, dict):
        raise LimitsError(f"{path} must be a JSON object")
    return data


def _from_env(environ: dict, name: str):
    if name not in environ:
        return None
    text = environ[name]
    if text is None or str(text).strip() == "":
        return None
    return text


def _pick(cli, env_text, config_value, default: int) -> int:
    if cli is not None:
        return parse_size(cli)
    if env_text is not None:
        return parse_size(env_text)
    if config_value is not None:
        return parse_size(config_value)
    return default


def resolve(*, max_events=None, max_bytes=None, max_calls=None,
            no_cap: bool = False, environ: dict | None = None,
            config: dict | None = None) -> Limits:
    """The cap for one recording.

    ``config`` may be passed by a test. Otherwise the store file is read.
    ``no_cap`` fills only the knobs the call did not set.
    """
    env = os.environ if environ is None else environ
    cfg = load_config(env) if config is None else config
    if no_cap:
        if max_events is None:
            max_events = 0
        if max_bytes is None:
            max_bytes = 0
        if max_calls is None:
            max_calls = 0
    return Limits(
        max_events=_pick(max_events, _from_env(env, ENV_EVENTS),
                         cfg.get("max_events"), DEFAULT_MAX_EVENTS),
        max_bytes=_pick(max_bytes, _from_env(env, ENV_BYTES),
                        cfg.get("max_bytes"), DEFAULT_MAX_BYTES),
        max_calls=_pick(max_calls, _from_env(env, ENV_CALLS),
                        cfg.get("max_calls"), DEFAULT_MAX_CALLS),
    )


def _optional_int(cli, env_text, config_value) -> int | None:
    if cli is not None:
        return parse_size(cli)
    if env_text is not None:
        return parse_size(env_text)
    if config_value is not None:
        return parse_size(config_value)
    return None


def store_policy(*, max_bytes=None, keep=None, older_than=None,
                 environ: dict | None = None,
                 config: dict | None = None) -> StorePolicy:
    """Retention for ``gc``. ``older_than`` is seconds when passed as a number."""
    env = os.environ if environ is None else environ
    cfg = load_config(env) if config is None else config
    if older_than is None:
        env_age = _from_env(env, ENV_OLDER)
        if env_age is not None:
            older = parse_duration(env_age)
        elif cfg.get("gc_older_than_days") is not None:
            older = float(parse_size(cfg["gc_older_than_days"])) * 86400
        else:
            older = None
    else:
        older = float(older_than)
    resolved_keep = _optional_int(keep, _from_env(env, ENV_KEEP),
                                  cfg.get("gc_keep"))
    if resolved_keep is not None and resolved_keep < 1:
        raise LimitsError("keep must be >= 1")
    return StorePolicy(
        max_bytes=_optional_int(max_bytes, _from_env(env, ENV_BUDGET),
                                cfg.get("store_budget")),
        keep=resolved_keep,
        older_than=older,
    )
