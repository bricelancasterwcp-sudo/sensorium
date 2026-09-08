"""R4: every raw and assembled results file names the schema it was written
under, and a renderer states a re-derivation rather than hiding it.

The debt this closes (design 2026-09-07 §5): an assembled `results.json`
carried no statement of which assembler wrote it, so a record re-derived
under a later schema was indistinguishable from one derived under its own.
The rule is: the RUNNER stamps `schema_version` into the raw record; the
ASSEMBLER copies that token and stamps its own beside it; the RENDERER says
so in §2, and says `re-derived under X from a raw written under Y` when the
two differ.

The two committed records that predate the field are NOT repaired -- the
R-F15/R-G15 precedent is that a derivation is stated, never rewritten -- and
the last test here is the tripwire that keeps them that way.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RUST_TESTS = REPO / "rust" / "tests"
sys.path.insert(0, str(RUST_TESTS))

import acceptance_e4_schema as e4_schema      # noqa: E402
import acceptance_e9_schema as e9_schema      # noqa: E402
import render_acceptance as ra                # noqa: E402
import render_e4                              # noqa: E402
import render_e9                              # noqa: E402


# ------------------------------------------------- the runners stamp the raw

@pytest.mark.parametrize("module, token", [
    ("acceptance_e9", "e9/1"),
    ("acceptance_e4", "e4/1"),
])
def test_the_runner_declares_the_schema_it_writes(module, token):
    """A module constant, so the raw record and the assembler read ONE
    spelling. A runner that stamped a literal into `main` could drift from
    the assembler's copy without a test noticing."""
    mod = __import__(module)
    assert mod.SCHEMA_VERSION == token


@pytest.mark.parametrize("module", ["acceptance_e9", "acceptance_e4"])
def test_the_raw_record_is_stamped_before_anything_can_refuse(module):
    """`schema_version` is set in the FIRST dict literal of `main`, beside
    `started` and `runner` -- not after the byte lock, not after the
    preflight. A run that refuses still writes a raw record, and a raw
    record whose schema is unknown cannot be re-derived later at all."""
    src = (RUST_TESTS / f"{module}.py").read_text()
    head = src[src.index("def main(argv)"):]
    literal = head[head.index("res: dict = {"):head.index("rc = 0")]
    assert '"schema_version": SCHEMA_VERSION' in literal


# ------------------------------------------------ the assembler copies it

@pytest.mark.parametrize("assemble, token", [
    (e9_schema.assemble_e9, "e9/1"),
    (e4_schema.assemble_e4, "e4/1"),
])
def test_the_assembled_record_carries_the_RAWS_token(assemble, token):
    """Copied, never asserted: the assembled record's `schema_version` is
    the schema the MEASUREMENT was written under. Stamping the assembler's
    own token here would make every old raw look freshly derived."""
    out = assemble({"schema_version": token})
    assert out["schema_version"] == token


@pytest.mark.parametrize("assemble, token", [
    (e9_schema.assemble_e9, "e9/1"),
    (e4_schema.assemble_e4, "e4/1"),
])
def test_the_assembler_stamps_its_OWN_token_beside_it(assemble, token):
    """Two fields, never one. `assembled.schema_version` is what this code
    is; `schema_version` is what the raw was. A record with one field could
    not tell a re-derivation from an original derivation."""
    out = assemble({"schema_version": "older/0"})
    assert out["schema_version"] == "older/0"
    assert out["assembled"]["schema_version"] == token


@pytest.mark.parametrize("assemble", [e9_schema.assemble_e9,
                                      e4_schema.assemble_e4])
def test_a_raw_with_no_token_assembles_to_null_and_never_to_the_assemblers(
        assemble):
    """The honest answer for a raw record written before the field existed
    is `null` -- "this raw does not say" -- and NOT the assembler's own
    token, which would claim the measurement was made under a schema that
    did not exist when it ran."""
    out = assemble({})
    assert out["schema_version"] is None
    assert out["assembled"]["schema_version"] is not None


# ------------------------------------------------------ the renderer says so

def test_the_schema_sentence_states_a_re_derivation_when_they_differ():
    sentence = ra.schema_sentence({"schema_version": "e4/1",
                                   "assembled": {"schema_version": "e4/2"}})
    assert "re-derived under `e4/2` from a raw written under `e4/1`" in sentence


def test_the_schema_sentence_states_the_ONE_version_when_they_agree():
    sentence = ra.schema_sentence({"schema_version": "e4/1",
                                   "assembled": {"schema_version": "e4/1"}})
    assert "`e4/1`" in sentence
    assert "re-derived" not in sentence


def test_a_raw_that_names_no_schema_is_SAID_to_name_none():
    """Never rendered as though the assembler's token were the raw's: the
    gap is the fact, and a dash or a silently repeated token would hide a
    record whose provenance is genuinely unknown."""
    sentence = ra.schema_sentence({"schema_version": None,
                                   "assembled": {"schema_version": "e4/1"}})
    assert "none recorded" in sentence
    assert "re-derived under `e4/1`" in sentence


@pytest.mark.parametrize("renderer, token", [(render_e9, "e9/1"),
                                             (render_e4, "e4/1")])
def test_the_renderers_section_2_PRINTS_the_field(renderer, token):
    """H5's second reading of the E4′ record: on a dry assemble the E9 and
    E4 renderers print their own `schema_version` fields."""
    record = json.loads(json.dumps(_minimal_record(renderer)))
    record["schema_version"] = token
    record["assembled"] = {"schema_version": token}
    text = "\n".join(renderer.environment(record))
    assert "**Schema.**" in text
    assert f"`{token}`" in text


def _minimal_record(renderer) -> dict:
    """The smallest record `environment` can render: every key it reads,
    empty. Built here rather than loaded from the committed file, because
    the committed files are exactly the ones this slice must NOT touch."""
    return {
        "acceptance": f"docs/superpowers/acceptance/{renderer.__name__}.md",
        "started": None, "finished": None, "runner": None,
        "byte_lock": {}, "environment": {},
    }


# ---------------------------------------- the two committed records PREDATE

@pytest.mark.parametrize("name", [
    "2026-09-06-sensorium-rung4-e9.results.json",
    "2026-09-07-sensorium-rung4-e4.results.json",
])
def test_the_committed_results_predate_the_field_and_are_NOT_repaired(name):
    """A TRIPWIRE, not a wish. Both records were assembled before
    `schema_version` existed, and re-deriving them now would rewrite a
    measured record to look like one made under a schema that postdates it
    -- the R-F15/R-G15 precedent forbids exactly that. The fact is carried
    in CARRIED-DEBT and stated in the E4′ record's H5; if this test ever
    goes red, someone re-derived a closed record.
    """
    path = REPO / "docs" / "superpowers" / "acceptance" / name
    record = json.loads(path.read_text())
    assert "schema_version" not in record, (
        f"{name} was re-derived; a closed record's derivation is STATED, "
        "never rewritten")


# ------------------------------- every renderer is reachable from `--doc`

def test_every_renderer_with_a_document_ENTRY_is_reachable_from_doc():
    """A1's review minors: `render_e6q.py` was written with the same
    `document(argv)` entry point as its siblings and never added to
    `render_acceptance`'s chain, so the only way to render the E6⁗ document
    was to run its module directly. `render_grain` had acquired the same
    hole. The dispatch is a table now, and this is the check that a renderer
    added beside them joins it."""
    import importlib
    entries = sorted(p.stem for p in RUST_TESTS.glob("render_*.py")
                     if "def document(argv)" in p.read_text())
    # every module that HAS the entry point is routed to by some `--doc`
    assert set(entries) - set(ra.DOCS.values()) == set(), entries
    # ...and every name in the table resolves to a module that has one
    for doc, module in ra.DOCS.items():
        assert importlib.import_module(module).document, doc


def test_an_unknown_doc_names_every_document_this_renderer_can_render(
        capsys):
    """The refusal message was a hand-typed list of four and named neither
    `e6q` nor `grain`. Derived from the table, so it cannot go stale."""
    assert ra.main(["--doc", "nope"]) == 2
    err = capsys.readouterr().err
    for name in ["rung2", "e5prime", *ra.DOCS]:
        assert f"`{name}`" in err, name
