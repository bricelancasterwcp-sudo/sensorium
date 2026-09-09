"""A trace in a language this sensorium has no words for is REFUSED, once.

Until S5 `query.vocab.terms()` fell back to the PYTHON column for any
`lang` it did not know. That was defensible only while no trace could
carry an unknown value -- and the moment a third recorder shipped, the
fallback became a machine for producing confident falsehoods: a reader
asking about a COBOL recording would be told about `asyncio tasks`, an
interpreter line reading `python ?`, and threads started "through Python's
own threading/_thread". Those are the rung-1 findings verbatim, one
language further out.

So the refusal lives at ONE choke point, `db.open_trace`, which every
command goes through before it holds a `Trace` at all. This file drives
four commands at one such trace to hold that: not because four commands
are four rules, but because ONE rule reached by four different code paths
is exactly the claim, and a per-renderer check would be four rules that
can drift apart.

The other half is what is NOT refused: a trace with no `lang` key at all
predates the key and is the Python recorder's -- nothing else existed --
and reads exactly as it always has.
"""
import pytest

from sensorium import paths
from sensorium.query.vocab import PYTHON, terms
from sensorium.store.db import TraceFormatError
from sensorium.store.reader import Trace
from sensorium.store.writer import TraceWriter
from tests.helpers import LEGACY_FORMAT, finalize_synthetic, run_cli

RUN = "20260101-000000-abcdef"
RUN2 = "20260101-000001-fedcba"

#: The whole sentence, minus the path and the version -- both of which are
#: the environment's rather than the rule's. `(python, rust, typescript)`
#: is `db.KNOWN_LANGS` spelled out: a reader who meets this line learns
#: which languages an upgrade would have to bring, not merely that theirs
#: is not one of them.
WHO = "was written by cobol-rec 1.0 for lang 'cobol', which this sensorium"
WHAT = ("has no vocabulary for (python, rust, typescript); upgrade "
        "sensorium to read it")


def _cobol(tmp_path, run_id=RUN):
    """A finalized format-4 trace in a language nobody wrote a column for.

    Complete on purpose: every required key is present, so the ONLY thing
    wrong with it is the language. A trace that was also missing meta would
    be refused by the older rule and prove nothing about this one.
    """
    sdir = tmp_path / "sdir"
    path = sdir / "traces" / f"{run_id}.db"
    w = TraceWriter(path, batch=1)
    code = w.intern_code("/w/PAYROLL.CBL", "MAIN-PARA", 1)
    w.add_event(0, 1, "CALL", None, code, 1, {"args": {}})
    finalize_synthetic(w, run_id=run_id, lang="cobol",
                       recorder="cobol-rec 1.0",
                       capabilities={"line": False, "locals": False,
                                     "return_value": False, "tasks": False,
                                     "threads": False, "children": False,
                                     "stdin": False, "output": False,
                                     "object_identity": False,
                                     "refocus": False})
    w.close()
    return sdir, path


def test_the_store_refuses_the_trace_at_open(tmp_path):
    """The rule itself, below every command: `Trace.open` raises, naming
    the recorder, the language, this sensorium and what it does know."""
    _sdir, path = _cobol(tmp_path)
    with pytest.raises(TraceFormatError) as e:
        Trace.open(path)
    message = str(e.value)
    assert str(path) in message, message
    assert WHO in message, message
    assert WHAT in message, message


@pytest.mark.parametrize(
    "command",
    (["info", RUN], ["grep", RUN, ""], ["tree", RUN], ["diff", RUN, RUN2]),
    ids=["info", "grep", "tree", "diff"])
def test_every_command_refuses_it_with_the_same_sentence(command, tmp_path):
    """One rule, four code paths. `cli.main` renders `TraceFormatError` as
    `error: ...` on stderr at exit 2 -- the status for "fix the call",
    which an upgrade is -- and no command reaches a renderer, so no
    Python word is printed about a trace no Python recorded."""
    sdir, path = _cobol(tmp_path)
    # `diff` needs a second side; the same file under a second name is the
    # cheapest one, and it must be refused before the comparison starts.
    path.with_name(f"{RUN2}.db").write_bytes(path.read_bytes())
    r = run_cli(command, cwd=tmp_path, sensorium_dir=sdir)
    text = r.stdout + r.stderr
    assert r.returncode == 2, text
    assert text.startswith("error: "), text
    assert WHO in text and WHAT in text, text
    for word in ("asyncio", "python ?", "MAIN-PARA", "verdict"):
        assert word not in text, (f"{word!r} printed about a COBOL "
                                  f"trace\n{text}")


def test_the_refusal_names_the_recorder_it_cannot_read_or_says_nobody_did(
        tmp_path):
    """A trace whose `recorder` is absent, null or not a string is one case
    to a reader -- nobody said who wrote it -- and the refusal says so
    rather than rendering `None` as a name. Same words the missing-key
    refusal has always used for the same gap."""
    sdir = tmp_path / "sdir"
    path = sdir / "traces" / f"{RUN}.db"
    w = TraceWriter(path, batch=1)
    finalize_synthetic(w, run_id=RUN, lang="cobol", recorder=None)
    w.close()
    with pytest.raises(TraceFormatError) as e:
        Trace.open(path)
    assert ("was written by an unnamed recorder for lang 'cobol'"
            in str(e.value))


def test_a_trace_with_no_lang_key_at_all_still_reads_as_python(tmp_path):
    """The absence is not an unknown value. `lang` became required in
    format 4, so a trace without it is a pre-format-4 trace, and only one
    recorder existed then. It opens, and it gets Python's words -- which is
    what `Trace.lang` has always defaulted to and what this refusal must
    not disturb.
    """
    sdir = tmp_path / "sdir"
    path = sdir / "traces" / f"{RUN}.db"
    w = TraceWriter(path, batch=1)
    code = w.intern_code("/w/prog.py", "main", 1)
    w.add_event(0, 1, "CALL", None, code, 1, {"args": {}})
    w.set_meta("run_id", RUN)
    w.set_meta("argv", ["prog.py"])
    # A legacy trace really is one: format 4 requires `lang` on anything
    # that claims to be finalized, so stamping 4 here would build a shape
    # no recorder produces and be refused by the older rule instead.
    w.set_meta("trace_format", LEGACY_FORMAT)
    w.set_meta("incomplete", False)
    w.close()
    trace = Trace.open(path)
    assert trace.lang == "python"
    assert terms(trace) is PYTHON
    r = run_cli(["info", RUN], cwd=tmp_path, sensorium_dir=sdir)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "python ?" in r.stdout, r.stdout


def test_the_store_directory_layout_this_file_writes_is_the_real_one(
        tmp_path, monkeypatch):
    """A guard on the guard. Every test above writes its trace to
    `<sdir>/traces/<run>.db` by hand; if that stopped being where the CLI
    looks, `run_cli` would find no trace and the refusals above would pass
    on a "no such run" error instead of on the sentence under test."""
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert paths.traces_dir() == tmp_path / "sdir" / "traces"


def test_the_refusal_still_explains_itself_from_an_uninstalled_tree(
        tmp_path, monkeypatch):
    """`db._version` reads this sensorium's installed version to say what
    an upgrade would be an upgrade FROM. A source tree that was never
    installed has no version to read, and a refusal that raised while
    explaining itself would hand the reader a traceback in place of the
    sentence."""
    import importlib.metadata as md
    from sensorium.store import db

    def _no_package(_name):
        raise md.PackageNotFoundError("sensorium")

    monkeypatch.setattr(md, "version", _no_package)
    assert db._version() == "?"
    _sdir, path = _cobol(tmp_path)
    with pytest.raises(TraceFormatError) as e:
        Trace.open(path)
    assert "which this sensorium (?) has no vocabulary for" in str(e.value)
