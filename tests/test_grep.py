"""`grep`: search events by name or captured-value content."""
import shlex

from sensorium.exit import NEGATIVE
from sensorium import cli
from tests.programs import CLEAN, CRASH, SWALLOW, record, synthetic


# -- grep ------------------------------------------------------------------
def test_grep_by_value_content(tmp_path, monkeypatch, capsys):
    run_id = record(tmp_path, monkeypatch, SWALLOW)
    assert cli.main(["grep", run_id, "carol"]) == 0
    out = capsys.readouterr().out
    assert "parse_row" in out and "matches:" in out


def test_grep_kind_and_fn_filters(tmp_path, monkeypatch, capsys):
    run_id = record(tmp_path, monkeypatch, CRASH)
    assert cli.main(["grep", run_id, "get", "--kind", "RETURN",
                     "--fn", "get"]) == 0
    out = capsys.readouterr().out
    assert "get -> None" in out and "get -> 'Alice'" in out
    assert "CALL" not in out                      # --kind actually filtered


def test_grep_limit_offers_continuation(tmp_path, monkeypatch, capsys):
    run_id = record(tmp_path, monkeypatch, SWALLOW)
    cli.main(["grep", run_id, "parse_row", "--limit", "1"])
    out = capsys.readouterr().out
    assert "more; continue with:" in out and "--after e" in out


def test_grep_continuation_is_runnable_and_reveals_the_rest(
        tmp_path, monkeypatch, capsys):
    """The hint must be a command, not a template, and paging through it must
    reproduce the unclipped result exactly -- no gap, no repeat. Task 10 was
    sent back for emitting a `--root fN` template instead of a command."""
    run_id = record(tmp_path, monkeypatch, SWALLOW)
    assert cli.main(["grep", run_id, "parse_row"]) == 0
    full = [ln for ln in capsys.readouterr().out.splitlines()
            if ln.startswith("e")]
    assert len(full) > 3

    pages: list[str] = []
    argv = ["grep", run_id, "parse_row", "--limit", "3"]
    for _ in range(10):                      # guard: never loop forever
        assert cli.main(argv) == 0
        out = capsys.readouterr().out
        pages += [ln for ln in out.splitlines() if ln.startswith("e")]
        tail = out.strip().splitlines()[-1]
        if "continue with: " not in tail:
            break
        hint = tail.split("continue with: ", 1)[1]
        assert "eN" not in hint and "fN" not in hint and "..." not in hint
        argv = shlex.split(hint)
        assert argv[0] == "sensorium"
        argv = argv[1:]
    assert pages == full


def test_grep_continuation_carries_every_filter(tmp_path, monkeypatch, capsys):
    """A hint that drops --kind/--fn resumes a *different* search and
    silently shows rows the first page had filtered out."""
    run_id = record(tmp_path, monkeypatch, SWALLOW)
    assert cli.main(["grep", run_id, "parse_row", "--kind", "CALL",
                     "--fn", "parse_row", "--limit", "1"]) == 0
    out = capsys.readouterr().out
    hint = out.strip().splitlines()[-1].split("continue with: ", 1)[1]
    assert "--kind CALL" in hint and "--fn parse_row" in hint

    assert cli.main(shlex.split(hint)[1:]) == 0
    rest = capsys.readouterr().out
    rows = [ln for ln in rest.splitlines() if ln.startswith("e")]
    assert len(rows) == 1 and rows[0].split()[1] == "CALL"  # --limit carried
    assert "matches: 4" in rest                   # 5 calls, 1 already shown


def test_grep_reports_the_true_total_not_just_what_it_printed(
        tmp_path, monkeypatch, capsys):
    run_id = record(tmp_path, monkeypatch, SWALLOW)
    cli.main(["grep", run_id, "parse_row"])
    total = int(next(ln for ln in capsys.readouterr().out.splitlines()
                     if ln.startswith("matches:")).split()[1])
    assert total > 1
    cli.main(["grep", run_id, "parse_row", "--limit", "1"])
    out = capsys.readouterr().out
    assert f"matches: {total}" in out
    assert "showing 1" in out


def test_grep_no_match_says_what_it_looked_at(tmp_path, monkeypatch, capsys):
    run_id = record(tmp_path, monkeypatch, CLEAN)
    assert cli.main(["grep", run_id, "nonexistent-token"]) == NEGATIVE
    out = capsys.readouterr().out
    assert "matches: 0" in out
    assert "scanned" in out and "event" in out


def test_grep_zero_match_note_owns_up_to_the_fn_filter(
        tmp_path, monkeypatch, capsys):
    """"none contained 'alice'" is a false statement about a trace in which
    three events do contain it and were removed by --fn. Every active filter
    has to appear in the line that explains the empty result."""
    run_id = record(tmp_path, monkeypatch, SWALLOW)
    assert cli.main(["grep", run_id, "alice"]) == 0
    hits = int(next(ln for ln in capsys.readouterr().out.splitlines()
                    if ln.startswith("matches:")).split()[1])
    assert hits > 0                              # 'alice' really is in there

    assert cli.main(["grep", run_id, "alice", "--fn", "nosuchfn"]) == NEGATIVE
    out = capsys.readouterr().out
    assert "matches: 0" in out
    assert "excluded by --fn 'nosuchfn'" in out
    assert "none of the remaining" in out
    assert "none contained" not in out           # the false fact


def test_grep_line_kind_with_no_line_capture_says_why(
        tmp_path, monkeypatch, capsys):
    run_id = record(tmp_path, monkeypatch, CLEAN)      # recorded without --focus
    assert cli.main(["grep", run_id, "a", "--kind", "LINE"]) == NEGATIVE
    out = capsys.readouterr().out
    assert "matches: 0" in out
    assert "--focus" in out


def test_grep_rejects_a_nonpositive_limit(tmp_path, monkeypatch, capsys):
    run_id = record(tmp_path, monkeypatch, CLEAN)
    assert cli.main(["grep", run_id, "add", "--limit", "0"]) == 2
    assert "--limit" in capsys.readouterr().out


def test_grep_skips_events_with_no_code_object(tmp_path, monkeypatch, capsys):
    w = synthetic(tmp_path, monkeypatch)
    c = w.intern_code("/tmp/prog.py", "add", 1)
    w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    w.add_event(0, 1, "CALL", None, None, 1, {"args": {}})   # no code object
    w.close()

    assert cli.main(["grep", "20260101-000000-abcdef", "CALL"]) == 0
    out = capsys.readouterr().out
    assert "matches: 1" in out
    assert "scanned" not in out
