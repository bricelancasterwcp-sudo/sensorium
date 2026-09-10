"""The spool reader's own surface: what it yields, and what it refuses.

`sensorium.ts.spool.read` streams (A3). BOOT is read eagerly from line 1 --
a spool that does not say what wrote it is refused before a single record
is walked -- and every later record is yielded as the file is read, so
`exit` and `torn_tail` are facts only once the walk is done. The refusals
that used to come out of `read()` now come out of the WALK, and the tests
below hold each of them at the point it surfaces.

These five tests lived in `tests/test_ts_ingest_meta.py` until A3; they are
here because that module reached the 800-line ceiling, and because "what
the reader refuses" and "what a converted trace carries" are two subjects.
What a refusal does to an INGEST -- the line printed, the trace not left
behind -- stays there, with the command it is about.
"""
import pytest

from tests.ts_spools import FIXTURES


def test_a_spool_with_no_boot_names_the_file():
    from sensorium.ts import spool
    with pytest.raises(spool.SpoolError) as e:
        list(spool.read(FIXTURES / "no-boot" / "7101-0.jsonl").records)
    assert "7101-0.jsonl" in str(e.value)


def test_a_boot_that_is_not_line_one_is_refused_naming_the_line(tmp_path):
    """BOOT is the header, not a record that may turn up anywhere.

    The reader takes it from line 1 and nowhere else: a spool whose first
    line is something else cannot be dated or placed until the whole file
    has been walked, and a reader that streams has already handed records
    to its caller by then. Refused where it is met, naming the line.
    """
    from sensorium.ts import spool as spool_mod
    bad = tmp_path / "9-0.jsonl"
    bad.write_text('{"e":"SEEN","name":"x","ts":1}\n'
                   '{"e":"BOOT","wire":1,"pid":9,"ts":2}\n')
    with pytest.raises(spool_mod.SpoolError) as e:
        spool_mod.read(bad)
    assert "line 1" in str(e.value)
    assert "9-0.jsonl" in str(e.value)


def test_a_torn_final_line_is_dropped_and_not_refused():
    """A container killed mid-`appendFileSync` leaves half a line. That is
    the tail this recorder declares unknowable, not a corrupt file: the line
    is dropped, the trace says `incomplete`, and nothing counts the loss."""
    from sensorium.ts import spool as spool_mod
    sp = spool_mod.read(FIXTURES / "killed-mid-file" / "439886-0.jsonl")
    records = list(sp.records)      # the walk is what finds the torn tail
    assert len(records) == 119      # 120 whole lines, one of them BOOT
    assert sp.torn_tail is True
    assert sp.exit is None


def test_a_malformed_line_anywhere_else_is_a_refusal(tmp_path):
    """...and only the LAST line gets that benefit. A broken line in the
    middle is a corrupt file, and reading past it would silently drop a
    record the container did finish writing."""
    from sensorium.ts import spool as spool_mod
    good = (FIXTURES / "each-names" / "439934-0.jsonl").read_text().splitlines()
    bad = tmp_path / "9-0.jsonl"
    bad.write_text("\n".join(good[:5] + ["{not json"] + good[5:]) + "\n")
    with pytest.raises(spool_mod.SpoolError) as e:
        list(spool_mod.read(bad).records)
    assert "line 6" in str(e.value)
    assert "9-0.jsonl" in str(e.value)


def test_a_line_that_is_not_a_record_is_refused(tmp_path):
    """Every line carries an `e` naming its kind, and it is a string. A
    line that carries something else is not a record this converter can
    dispatch on."""
    from sensorium.ts import spool as spool_mod
    bad = tmp_path / "9-0.jsonl"
    bad.write_text('{"e": 7}\n')
    with pytest.raises(spool_mod.SpoolError) as e:
        list(spool_mod.read(bad).records)
    assert "line 1 is not a record" in str(e.value)


def test_a_line_that_is_not_utf8_is_refused_naming_the_line(tmp_path):
    """The one refusal whose text AND surfacing point both moved (A3).

    A spool used to be decoded whole, so a bad byte anywhere was "cannot be
    read as a spool" with no line in it. The walk decodes a line at a time
    and names the line it could not read. What must never happen is the
    other repair -- `errors="replace"` -- which would turn a corrupt byte
    into a U+FFFD inside a record and convert it as though it were the text
    the container wrote.
    """
    from sensorium.ts import spool as spool_mod
    bad = tmp_path / "9-0.jsonl"
    bad.write_bytes(b'{"e":"BOOT","wire":1,"pid":9,"startTs":1}\n'
                    b'{"e":"SEEN","name":"\xff"}\n')
    with pytest.raises(spool_mod.SpoolError) as e:
        list(spool_mod.read(bad).records)
    assert "line 2" in str(e.value)
    assert "not UTF-8" in str(e.value)
    assert "9-0.jsonl" in str(e.value)
