"""What the converter puts in a trace, through the real driver.

Holds the off-by-one in `c/sample/stats.c` (`sum_range` returns 12, not
20), the `char *` `"brice"` as a `str` value, the NULL deref as a
`SIGSEGV` with frames closed by unwind, a waited exit signal 11, a
`struct point` argument that still has `x` and `y`, a double return, a
two-int struct return, and `API_KEY` stored as the redacted marker.

Skipped by name when gcc or pyelftools is missing. A missing driver is a
failure, not a skip.
"""
import json
import shutil

import pytest

pytest.importorskip("elftools", reason="pyelftools is not installed")

if shutil.which("gcc") is None:
    pytest.skip("gcc is not on PATH", allow_module_level=True)

from sensorium.redact import REDACTED
from tests.c_helpers import SAMPLES, build_and_run, calls, returns, run_c


def _num(value):
    if isinstance(value, dict) and value.get("k") == "num":
        return value.get("v")
    return None


@pytest.fixture(scope="module")
def stats_good(tmp_path_factory):
    root = tmp_path_factory.mktemp("stats")
    return build_and_run(root / "good", SAMPLES / "stats.c", root / "sdir",
                          binary="stats")


@pytest.fixture(scope="module")
def stats_crash(tmp_path_factory):
    root = tmp_path_factory.mktemp("stats-crash")
    return build_and_run(root / "bad", SAMPLES / "stats.c", root / "sdir",
                          argv=("bob",), binary="stats")


@pytest.fixture(scope="module")
def types_run(tmp_path_factory):
    root = tmp_path_factory.mktemp("types")
    return build_and_run(root / "work", SAMPLES / "types.c", root / "sdir",
                          binary="types")


def test_sum_range_returns_the_off_by_one(stats_good):
    """`{2, 4, 6, 8}` skipping the last element is 12. A correct sum is 20."""
    assert stats_good.proc.returncode == 0, stats_good.proc.stderr
    vals = [_num((e.payload or {}).get("value")) for e in returns(stats_good.trace, "sum_range")]
    assert 12 in vals, vals
    assert 20 not in vals, vals


def test_name_len_records_brice_as_a_str(stats_good):
    found = []
    for event in calls(stats_good.trace, "name_len"):
        args = (event.payload or {}).get("args") or {}
        found.append(args)
        for value in args.values():
            if (isinstance(value, dict) and value.get("k") == "str"
                    and value.get("v") == "brice"):
                return
    pytest.fail(f"no str argument 'brice' on name_len: {found}")


def test_null_deref_is_a_waited_sigsegv(stats_crash):
    trace = stats_crash.trace
    raises = trace.events("RAISE")
    blob = json.dumps([e.payload for e in raises])
    assert raises, "no RAISE on the NULL deref"
    assert "SIGSEGV" in blob, blob
    unwound = [f for f in trace.frames() if f.closed_by == "unwind"]
    assert unwound, [(f.closed_by, trace.code(f.code_id).qualname) for f in trace.frames()]
    name_len = [f for f in unwound if trace.code(f.code_id).qualname.endswith("name_len")]
    assert name_len, [(trace.code(f.code_id).qualname, f.closed_by) for f in trace.frames()]
    assert trace.meta.get("exit_signal") == 11, trace.meta.get("exit_signal")
    assert trace.meta.get("exit_status_basis") == "waited", trace.meta.get("exit_status_basis")


def test_struct_point_argument_renders_with_x_and_y(stats_good):
    """`manhattan` takes two `struct point`s. The rendered call names x and y."""
    found = calls(stats_good.trace, "manhattan")
    assert found, "no call of manhattan"
    blob = json.dumps(found[0].payload)
    assert "x" in blob and "y" in blob, blob
    assert "1" in blob and "2" in blob and "4" in blob and "6" in blob, blob
    text = run_c(["tree", stats_good.trace.path.stem], stats_good.work,
                 stats_good.sdir).stdout
    assert "manhattan" in text, text
    assert "x" in text and "y" in text, text


def test_double_return_decodes(types_run):
    """`ret_double(1.25)` is 2.5, as a numeric value, not an unread slot."""
    assert types_run.proc.returncode == 0, types_run.proc.stderr
    vals = [(e.payload or {}).get("value") for e in returns(types_run.trace, "ret_double")]
    assert vals, "no return from ret_double"
    nums = [_num(v) for v in vals]
    assert any(n is not None and abs(float(n) - 2.5) < 1e-9 for n in nums), vals


def test_struct_of_two_ints_decodes(types_run):
    """`ret_point(3, 4)` comes back with both fields. A correct sum of the
    two ints is 7; the trace has to show the fields, not only the sum."""
    vals = [(e.payload or {}).get("value") for e in returns(types_run.trace, "ret_point")]
    assert vals, "no return from ret_point"
    blob = json.dumps(vals)
    assert "unread" not in blob, blob
    assert "x" in blob and "y" in blob, blob
    assert "3" in blob and "4" in blob, blob


def test_api_key_is_redacted(tmp_path):
    secret = "c-recorder-secret-value"
    src = tmp_path / "hello.c"
    src.write_text('#include <stdio.h>\nint main(void){printf("hi\\n");return 0;}\n')
    rec = build_and_run(
        tmp_path / "work", src, tmp_path / "sdir", binary="hello",
        run_env={"API_KEY": secret}, env_drop=("SENSORIUM_NO_REDACT",))
    env = rec.trace.meta.get("env") or {}
    assert env.get("API_KEY") == REDACTED, env.get("API_KEY")
    redaction = rec.trace.meta.get("redaction") or {}
    assert redaction.get("mode") == "on", redaction
    blob = rec.trace.path.read_bytes()
    assert secret.encode() not in blob, "the secret was stored in the trace file"
