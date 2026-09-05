# Rung-4 Entry — The Grain of `exceptions` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Write the SWALLOWED definition once (HONESTY §11) and cite it everywhere; make `exceptions` on a Rust trace print one block per SHAPE (a `[×N: ids]` bracket on the first chain's block) instead of one per chain; and let `sensorium exceptions <invocation-id>` answer for every process of one `cargo sensorium test` invocation — all measured against the published E6⁗ record as the oracle.

**Architecture:** Python reader side only (`src/sensorium/query/`), plus docs. `Disposition` gains a `site`; a new `exceptions_group.py` folds classified chains into shapes and renders the bracket; a new `exceptions_invocation.py` resolves an invocation id to its member traces and merges their shapes; `exceptions_cmd.run` dispatches to it when the ref is an invocation. The three pins of the old prose sentence and one pin of the old continuation hint are updated by rule before the pre-registration is locked. Crates are untouched (0.3.1); Python goes 0.8.1 → 0.8.2.

**Tech Stack:** Python 3.12+ stdlib only under `src/`; pytest; the synthetic-trace helpers `tests/rust_traces.py` + `tests/helpers.py`; the corpus and vector harnesses; the kept E6⁗ trace stores on `/mnt/extra` and the committed `results.json` as the acceptance oracle.

**Spec:** `docs/superpowers/specs/2026-09-05-sensorium-rung4-entry-grain-design.md` (N1–N8; §2 the definition text; §3 the block shapes; §4 the pre-registration; committed at `db70ef6`, amended `876b5a8`). Parents: rung-3 design R8/R15/R16; borrow-repair design B1/B4/B5. Rigor: `~/.claude/skills/rigorous-experiments/SKILL.md`; notation: `~/.claude/skills/designing-notation-for-llms/SKILL.md`.

## Global Constraints

- **Branch** `feat/rung4-entry-grain` from `main` @ `e307d90` (exists; design at `db70ef6` + `876b5a8`). PR against `main`; merge is Brice's. Never push `main`.
- **Stdlib only** under `src/sensorium/`; Python 3.12/3.13/3.14 (the CI matrix). **No Rust source, runtime, transformer or converter change**; crates stay 0.3.1. Any cargo command (T5's corpus run only) uses `CARGO_TARGET_DIR` under `/mnt/extra/sensorium-rung2/`, one at a time.
- **Python `exceptions` output on a PYTHON trace is byte-identical to 0.8.1** (N7): no Python expectation in the suite, the vectors v01–v15 or the Python corpus changes. A group of ONE on a Rust trace is byte-identical to 0.8.1 (N4).
- **The `dispositions:` tally counts chains** (N5) — never groups. `--limit` counts groups; `--after` keeps its scope meaning in single-run mode and is refused (exit 2) in invocation mode.
- **Pins updated BY RULE only, all named in §1 before the lock**: `corpus/rust/err_stored/questions.yaml`, `corpus/rust/err_rendered_into_value/questions.yaml`, `docs/trace-format/vectors/v18-exceptions-rust-ambiguous-merge.json` (the sentence, N2); `docs/trace-format/vectors/v17-exceptions-rust-swallowed.json` (the continuation hint, N5). Any other expectation change is a finding, not a fix.
- **Pre-registration byte-locked before any oracle number is read** (T4's last commits: §1 committed ALONE, then the runner's `BYTE_LOCK` set); the runner refuses on a byte difference; a completed measurement is never re-rolled; a miss is a STOP with its number. **No `src/` change after the lock.**
- **No box-local path in any committed file** except the acceptance record's lens rows and this plan. The kept stores: `/mnt/extra/sensorium-rung2/sensorium-dir/e6q/{a,ws,ws0}` (READ-ONLY for this slice — nothing records into them; nothing deletes them). Corpus target for T5: `/mnt/extra/sensorium-rung2/corpus-target-grain` (fresh). Driver: `/mnt/extra/sensorium-rung2/rust-target/debug/cargo-sensorium` (0.3.1, already built).
- **No file over 800 lines** (`src/sensorium/query/exceptions_rust.py` is 597; the new modules keep it there; `tests/test_acceptance_e6q.py` is at 800 and is not touched).
- **Every new or changed test is mutation-tested** (mutant → failing test → restored, in the report; Python mutants purge `__pycache__` with `PYTHONDONTWRITEBYTECODE=1`).
- **Commits by explicit path** (never `git add -A`; never stage anything under `.superpowers/`); `git show --stat HEAD` read after every commit; messages end with the two trailer lines
  `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01D5ALVP7MSxhfTzxp4TFDPn`
- Every shell command starts `cd /home/brice/workspace/sensorium &&`; pytest is `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest`; the full suite with the driver is `SENSORIUM_CARGO_SENSORIUM=/mnt/extra/sensorium-rung2/rust-target/debug/cargo-sensorium CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/corpus-target PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q` (≈1201 passed / 1 skipped at the base).
- Ledger: `.superpowers/sdd/2026-09-05-sensorium-rung4-entry-grain/progress.md` (gitignored) — rulings, oracle numbers, lock sha, commit shas.

---

## Decisions carried from the design

N1 definition → T1; N2 the tool's sentence + pins + prose test → T1; N3/N4 grouping key and block → T2; N5 tally/limit/after → T2; N6 invocation mode → T3; N7 Python untouched → every task's tests; N8 deferred items → T6's CARRIED-DEBT/inbox lines. Controller rulings in the ledger: R-G0 (key excludes hops/details/head — flagged as "vary" lines), R-G1 (paging by `--limit`; `--after` refused in invocation mode).

## Pre-registration — §1 of `docs/superpowers/acceptance/2026-09-05-sensorium-rung4-entry-grain.md`

Design §4's table H1–H6 verbatim, plus the lens paragraph and the reported-without-a-gate list. The oracle numbers it quotes are already in the ledger (from the published record): A = 5 sites {`memory.rs:156` 3, `task/exec.rs:606` 4, `memory/store.rs:96` 2, `task/registry.rs:1084` 4, `task/registry.rs:379` 1}, tally `swallowed 14, ambiguous 8`; WS = 144 processes / 114 with chains / 30 with none / 91 sites / 782 swallows, summed tally `swallowed 782, ambiguous 330, panicked 2`; WS0 = 144 / 114 / 30 / 98 sites / 812, `swallowed 812, ambiguous 300, panicked 2`. T4 writes §1 with these numbers and commits it ALONE; T5 refuses to run if §1 differs.

## File Structure

- Modify `src/sensorium/query/exceptions_cmd.py` — `Disposition.site` (defaulted field); `run()` dispatches an invocation ref (after `find_trace` fails with "no trace matches") to `exceptions_invocation.run`; the Python path unchanged.
- Modify `src/sensorium/query/exceptions_rust.py` — `_swallowed`/`_escaped`/`_handled_then_failed` set `site`; the tool's sentence (N2); `run()` delegates printing to the group renderer.
- Create `src/sensorium/query/exceptions_group.py` — `Shape`, `group_chains(trace, chains, idx)`, `render_groups(...)`, the masking, the bracket, the vary lines, the limit/note.
- Create `src/sensorium/query/exceptions_invocation.py` — `resolve_invocation(ref) -> (invocation_id, [Path])`, `run(args, invocation_id, paths)`.
- Modify `rust/HONESTY.md` §11 (the SWALLOWED bullet = design §2), `docs/superpowers/specs/2026-09-04-sensorium-rung3-err-flow-design.md` (one dated line in R15).
- Modify the four pins (Global Constraints). Create `tests/test_exceptions_rust_grouping.py`, `tests/test_exceptions_invocation.py`, `tests/test_honesty_prose.py`, `tests/test_acceptance_grain.py`; create `rust/tests/acceptance_grain.py`, `rust/tests/acceptance_grain_schema.py`.
- Create `docs/superpowers/acceptance/2026-09-05-sensorium-rung4-entry-grain.md` (+ `.results.json` at T5).
- T6: `README.md` (`exceptions` section), `rust/README.md` if it shows `exceptions` output, `CHANGELOG.md` 0.8.2, `docs/CARRIED-DEBT.md`, `docs/superpowers/specs/2026-09-02-sensorium-rung3-inbox.md` §2a, `pyproject.toml` 0.8.2.

---

### Task 0: Baseline, oracle extraction, store check

**Files:** ledger only (no committed change).

- [ ] **Step 1: Tree, baseline suite**

Run: `cd /home/brice/workspace/sensorium && git status --porcelain && git log --oneline -3 && SENSORIUM_CARGO_SENSORIUM=/mnt/extra/sensorium-rung2/rust-target/debug/cargo-sensorium CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/corpus-target PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q 2>&1 | tail -1`
Expected: clean; HEAD `876b5a8`; `1201 passed, 1 skipped` (±0; anything red is a finding — stop). Record the line.

- [ ] **Step 2: The kept stores are present and read-only for us**

Run: `for a in a ws ws0; do echo "$a $(ls /mnt/extra/sensorium-rung2/sensorium-dir/e6q/$a/traces/*.db | wc -l)"; done; SENSORIUM_DIR=/mnt/extra/sensorium-rung2/sensorium-dir/e6q/ws PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m sensorium runs | head -2; SENSORIUM_DIR=/mnt/extra/sensorium-rung2/sensorium-dir/e6q/ws0 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m sensorium runs | head -1`
Expected: `a 1`, `ws 144`, `ws0 144`; the ws header `invocation 20260905-091115-9e8e5a: cargo test --workspace`; record ws0's invocation id in the ledger (T4 needs it for §1).

- [ ] **Step 3: Extract the oracle from the published record into the ledger** — one script, output pasted into the ledger's "Oracle numbers" section:

```bash
cd /home/brice/workspace/sensorium && .venv/bin/python - <<'EOF'
import json, collections
d = json.load(open("docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6q.results.json"))
for arm in ("E6qA", "E6qWS", "E6qWS0"):
    x = d["endpoints"][arm]
    lines = [dict(p, run=p.get("run", x["run"])) for p in (x.get("swallowed") or [])] \
          + [dict(p) for p in (x.get("swallowed_sweep") or [])]
    sites = collections.Counter(f'{p["sink"]["file"]}:{p["sink"]["line"]}' for p in lines)
    tallies = [x.get("tally_line")] + [s.get("tally_line") for s in (x.get("sweep_processes") or [])]
    tot = collections.Counter()
    for t in tallies:
        if t:
            for part in t[len("dispositions: "):].split(", "):
                k, v = part.rsplit(" ", 1); tot[k] += int(v)
    print(arm, "lines", len(lines), "sites", len(sites), "tally-lines", sum(1 for t in tallies if t),
          "summed", dict(tot))
    if arm == "E6qA":
        print(" per-site", dict(sites))
EOF
```
Expected: A `lines 14 sites 5`, WS `lines 782 sites 91 tally-lines 114 summed {swallowed 782, ambiguous 330, panicked 2}`, WS0 `lines 812 sites 98 tally-lines 114 summed {swallowed 812, ambiguous 300, panicked 2}`. If any differs from the ledger's block, STOP and report (the ledger was derived the same way; a difference means a mis-transcription).

- [ ] **Step 4: Report** (no commit).

---

### Task 1: The definition (N1/N2)

**Files:**
- Modify: `rust/HONESTY.md` (§11's SWALLOWED bullet), `docs/superpowers/specs/2026-09-04-sensorium-rung3-err-flow-design.md` (R15 row: one dated sentence appended), `src/sensorium/query/exceptions_rust.py:409-414` (`_escaped`'s detail sentence), `corpus/rust/err_stored/questions.yaml`, `corpus/rust/err_rendered_into_value/questions.yaml`, `docs/trace-format/vectors/v18-exceptions-rust-ambiguous-merge.json`
- Test: `tests/test_honesty_prose.py` (new)

**Interfaces:**
- Produces: the sentence constant `ESCAPED_DETAIL` in `exceptions_rust.py` (module-level, used by `_escaped`) so the test imports it rather than re-typing it; HONESTY §11's bullet text (design §2, verbatim).

- [ ] **Step 1: Write the failing tests** — `tests/test_honesty_prose.py`:

```python
"""The tool's own words about SWALLOWED are the ledger's words (design N1/N2).

`rust/HONESTY.md` §11 is the one home of the definition; the sentence the
tool prints under an escaped arm, and the four load-bearing phrases of the
definition, must be found there verbatim -- so the promise a reader meets
in the output cannot drift from the promise the ledger makes."""
from pathlib import Path

from sensorium.query import exceptions_rust

REPO = Path(__file__).resolve().parents[1]


def _section_11() -> str:
    text = (REPO / "rust" / "HONESTY.md").read_text()
    start = text.index("\n## 11. Err flow")
    end = text.find("\n## ", start + 1)
    return text[start:end if end != -1 else None]


def test_the_tools_escaped_sentence_is_in_honesty_section_11():
    assert exceptions_rust.ESCAPED_DETAIL in _section_11()


def test_the_tools_escaped_sentence_names_reading_as_not_leaving():
    assert "only reads it (a guard, a predicate), formats or logs it" in exceptions_rust.ESCAPED_DETAIL


def test_the_definition_carries_its_four_load_bearing_phrases():
    s = _section_11()
    for phrase in ("no value derived from the `Err` left the arm",
                   "Reading the error does not carry it out",
                   "a guarded arm's disposition is its body's",
                   "0 of them"):
        assert phrase in s, phrase
```

Run: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_honesty_prose.py -q` → Expected: FAIL (`ESCAPED_DETAIL` does not exist).

- [ ] **Step 2: The sentence** — in `exceptions_rust.py`, above `_escaped`:

```python
#: The one sentence the tool prints under an escaped arm. It is a QUOTATION
#: of `rust/HONESTY.md` §11's SWALLOWED definition (design N2, 2026-09-05):
#: reading the error -- a guard, a predicate -- does not carry it out of the
#: arm; only a value derived from it leaving the arm does.
ESCAPED_DETAIL = ("a bound error that is stored, returned or moved out of the arm "
                  "is not a swallow; an arm that only reads it (a guard, a "
                  "predicate), formats or logs it and continues is one")
```
and `_escaped` uses `ESCAPED_DETAIL` where it built the old sentence.

- [ ] **Step 3: HONESTY §11** — replace the `- **SWALLOWED** — …` bullet (currently `rust/HONESTY.md` ~line 576–583) with design §2's text verbatim (it is a blockquote in the design; in HONESTY it is the bullet's body — keep the `- **SWALLOWED** —` lead). Add, at the end of the bullet, the sentence: *"The tool's own words under an escaped arm are a quotation of this bullet: `a bound error that is stored, returned or moved out of the arm is not a swallow; an arm that only reads it (a guard, a predicate), formats or logs it and continues is one` (`tests/test_honesty_prose.py` pins it)."* Check `wc -l rust/HONESTY.md` ≤ 800.

- [ ] **Step 4: R15 pointer** — append to the R15 row of the rung-3 design (inside the cell, at its end): *" **Definition moved 2026-09-05 to `rust/HONESTY.md` §11 (rung-4 entry, design N1); this row's guard ruling is its source and is restated nowhere else.**"* Nothing else in that file changes (`git diff --word-diff` must show insertion only).

- [ ] **Step 5: The three pins, by rule** — in `corpus/rust/err_stored/questions.yaml` (lines 11 and 34–35), `corpus/rust/err_rendered_into_value/questions.yaml` (39–40) and the vector `v18` (its `expect_contains` sentence): the old sentence → the new one, split across the two needles at the same place it was split (`"… is not a swallow; an arm that only reads it (a guard, a predicate), formats or logs it and continues is one"`). `err_stored`'s `truth` prose (line 11) is updated the same way.

- [ ] **Step 6: Green, then the covering suites**

Run: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_honesty_prose.py tests/test_exceptions_rust.py tests/test_exceptions_rust_ambiguous.py tests/test_vectors.py -q` → green; then the two corpus cases with the driver: `SENSORIUM_CARGO_SENSORIUM=/mnt/extra/sensorium-rung2/rust-target/debug/cargo-sensorium CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/corpus-target PYTHONDONTWRITEBYTECODE=1 .venv/bin/python corpus/run_corpus.py --only rust/err_stored --only rust/err_rendered_into_value` (check `run_corpus.py --help` for repeated `--only`; else run twice) → both pass.

- [ ] **Step 7: Mutations** — (1) change one word in `ESCAPED_DETAIL` → `test_the_tools_escaped_sentence_is_in_honesty_section_11` red; (2) delete "a guarded arm's disposition is its body's" from HONESTY → the phrases test red; restore both.

- [ ] **Step 8: Commit**

```bash
git add rust/HONESTY.md docs/superpowers/specs/2026-09-04-sensorium-rung3-err-flow-design.md src/sensorium/query/exceptions_rust.py corpus/rust/err_stored/questions.yaml corpus/rust/err_rendered_into_value/questions.yaml docs/trace-format/vectors/v18-exceptions-rust-ambiguous-merge.json tests/test_honesty_prose.py
git commit -m "docs+feat(exceptions): one SWALLOWED definition in HONESTY §11; the tool's sentence quotes it and names reading as not leaving (design N1/N2)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01D5ALVP7MSxhfTzxp4TFDPn"
```

---

### Task 2: Grouping by shape (N3–N5)

**Files:**
- Modify: `src/sensorium/query/exceptions_cmd.py:176-181` (`Disposition` gains `site: str | None = None`), `src/sensorium/query/exceptions_rust.py` (`_swallowed`, `_escaped`, `_handled_then_failed` set `site`; `run()` calls the group renderer), `docs/trace-format/vectors/v17-exceptions-rust-swallowed.json` (the `--limit 1` continuation hint pin)
- Create: `src/sensorium/query/exceptions_group.py`
- Test: `tests/test_exceptions_rust_grouping.py` (new)

**Interfaces:**
- Consumes: `exceptions_rust.Index`, `classify(trace, chain, idx) -> Disposition`, `_hops_line(trace, chain)`, `_at(trace, e)`, `fmt.fmt_event`, `fmt.more_note`, `Chain.origin`/`.events`.
- Produces:

```python
# exceptions_group.py
@dataclass
class Shape:
    key: tuple            # (tag, site, masked_verdict)
    tag: str
    first: object         # the first Chain of the shape (origin order)
    disposition: object   # its Disposition
    chains: list          # every Chain in the shape, origin order
    heads: set            # masked head lines seen
    details: set          # detail strings seen (None allowed)
    hops: set             # hops lines seen (None allowed)

MASK = re.compile(r"\b([ef])\d+\b")
def mask(text: str) -> str: ...            # "e412" -> "e#", "f204" -> "f#"
def site_of(trace, chain, d) -> str: ...   # d.site or _at(trace, chain.origin)
def group_chains(trace, chains, idx, classify) -> tuple[list[Shape], dict]:
    """Shapes in order of first appearance; the tally dict counts CHAINS."""
def bracket(shape, max_ids=8) -> str: ...  # "  [×4: e412, e417, e420, e443]" / "… +K"; "" when len == 1
def vary_lines(shape) -> list[str]: ...    # ["origins: 5 distinct (first shown)", ...] only where a set has > 1 member
def print_shapes(trace, shapes, limit) -> int:
    """Prints up to `limit` shapes (first chain's block + bracket + vary lines); returns how many were printed."""
```
- `exceptions_rust.run` becomes: header → scope → `shapes, tally = group_chains(...)` → `shown = print_shapes(trace, shapes, args.limit)` → tally line → `more_note(len(shapes), shown, f"sensorium exceptions {shlex.quote(args.run)} --limit {shown + (len(shapes) - shown)}")` — the hint raises the limit (N5). `--after` still filters `scope` before grouping.

- [ ] **Step 1: Failing tests** — `tests/test_exceptions_rust_grouping.py`, built on `tests/rust_traces.py`'s vocabulary (read `swallow_trace` and write a sibling `two_sinks_trace`/`repeat_sink_trace` builder IN THIS TEST FILE or in `rust_traces.py` if it fits under 800 lines):

```python
def test_two_chains_at_one_sink_print_once_with_a_bracket_and_the_tally_counts_two(tmp_path, monkeypatch, capsys):
    # `load` sinks two Errs from two calls of read_config with the same .ok() at L31
    run_id = repeat_sink_trace(tmp_path, monkeypatch, repeats=2)
    assert cli.main(["exceptions", run_id]) == ANSWERED
    text = out(capsys)
    assert text.count("SWALLOWED --") == 1
    assert "[×2: e5, e11]" in text          # the two HANDLED event ids, in order
    assert "dispositions: swallowed 2" in text

def test_a_group_of_one_is_byte_identical_to_the_ungrouped_block(tmp_path, monkeypatch, capsys):
    run_id = swallow_trace(tmp_path, monkeypatch)
    cli.main(["exceptions", run_id]); text = out(capsys)
    assert "[×" not in text
    assert "SWALLOWED -- absorbed by sink_ok at e5 (load L31) in f1, which returned ok" in text

def test_two_sinks_are_two_shapes(...)        # two distinct sink lines -> two blocks, no bracket
def test_a_sink_shape_whose_origins_differ_says_so(...)   # same sink, two origin sites -> "origins: 2 distinct (first shown)"
def test_ambiguous_no_sink_chains_group_by_origin_site(...)  # two origins -> two shapes; same origin twice -> one with [×2]
def test_limit_counts_shapes_and_the_note_raises_the_limit(...)  # 3 shapes, --limit 1 -> one block, "... 2 more; continue with: sensorium exceptions <run> --limit 3"
def test_after_still_scopes_by_origin_id(...)   # --after e<first origin> drops the first shape's first chain; tally shrinks accordingly
def test_nine_ids_print_eight_and_a_plus_one(...)  # "[×9: e…, …, … +1]"
def test_the_python_path_is_untouched(...)      # a Python trace from tests/programs.py: output identical to a snapshot taken before this task (compute by calling the Python classifier directly, or pin one known Python case's exact lines)
```
Make each builder deterministic so the asserted event ids are exact. Run → all FAIL (no `exceptions_group`, no bracket).

- [ ] **Step 2: Implement** `exceptions_group.py` per the interface; `Disposition.site`; the three `site=` assignments (`_swallowed`: `site=_at(trace, h)`; `_escaped`: the arm event's `_at`; `_handled_then_failed`: the sink's `_at`); `run()` rewired. The masked-verdict key uses `mask(d.verdict)`; `heads` collect `mask(fmt_event(trace, chain.origin))`; `details` collect `d.detail`; `hops` collect `mask(_hops_line(trace, chain))`. The bracket goes on the verdict line separated by two spaces. Vary lines are printed after the detail/hops lines, indented like the detail (6 spaces), in the order origins / details / hops, each only when its set has more than one member.

- [ ] **Step 3: Green; the whole exceptions family; the pin** — run the new file + `tests/test_exceptions*.py` + `tests/test_vectors.py`. v17's `--limit 1` question pins `["... 1 more; continue with: sensorium exceptions", "--after e4 --limit 1"]` → by N5 it becomes `["... 1 more; continue with: sensorium exceptions", "--limit 2"]`; update the vector and say so in the commit message. Then the Rust corpus: `… corpus/run_corpus.py` for all `rust/*` cases → 0 failures (no corpus case has a repeated site: all blocks are groups of one — if any case FAILS, that is a finding: STOP and report the diff rather than editing the case).

- [ ] **Step 4: Mutations** — (1) key ignores `site` → the two-sinks test red; (2) tally counts shapes → the `swallowed 2` assertion red; (3) bracket cap 8 → 9 → the `+1` test red; (4) `--after` filter removed → the after test red; (5) note hint uses `--after` → the limit test red. Restore each.

- [ ] **Step 5: Sizes + commit** — `wc -l src/sensorium/query/exceptions_rust.py src/sensorium/query/exceptions_group.py tests/test_exceptions_rust_grouping.py` (≤ 800 each).

```bash
git add src/sensorium/query/exceptions_cmd.py src/sensorium/query/exceptions_rust.py src/sensorium/query/exceptions_group.py tests/test_exceptions_rust_grouping.py docs/trace-format/vectors/v17-exceptions-rust-swallowed.json
git commit -m "feat(exceptions): one block per shape on a Rust trace — a [×N: ids] bracket on the first chain's block; the tally still counts chains; --limit counts shapes (design N3–N5)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01D5ALVP7MSxhfTzxp4TFDPn"
```

---

### Task 3: Invocation mode (N6)

**Files:**
- Create: `src/sensorium/query/exceptions_invocation.py`
- Modify: `src/sensorium/query/exceptions_cmd.py::run` (dispatch), `src/sensorium/paths.py` (nothing — resolution lives in the new module because it needs `Trace.open`)
- Test: `tests/test_exceptions_invocation.py` (new)

**Interfaces:**

```python
# exceptions_invocation.py
class InvocationLookupError(Exception): ...
def resolve_invocation(ref: str) -> tuple[str, list[Path]]:
    """Every trace whose meta.invocation == ref, or whose invocation uniquely
    starts with ref. Raises InvocationLookupError("no trace or invocation matches
    {ref!r}") when none, and ("{ref!r} is ambiguous: <ids>") when the prefix
    names more than one invocation. Opens every trace in the store once."""
def run(args, invocation_id: str, members: list[Path]) -> int:
    """Header, INCOMPLETE members, partial union, panics sum, merged shapes,
    summed tally, note, exit status per N6."""
```
- `exceptions_cmd.run`: wrap `paths.find_trace(args.run)` — on `TraceLookupError` whose message starts `no trace matches`, call `resolve_invocation(args.run)`; on success dispatch `exceptions_invocation.run(args, inv, members)`; if it raises `InvocationLookupError`, print its message and return `BAD_CALL` (2) — the same status a bad run ref gets today (check how `cli.main` renders `TraceLookupError` and match it). `--after` with an invocation → print `--after names an event of one process; this answer spans N processes -- page with --limit` and return `BAD_CALL`.
- Merge rule: a shape's key is the same `(tag, site, masked_verdict)`; the merged shape keeps the FIRST member's first chain as `first` (member order = trace file name order, the order `runs` prints), counts `n = Σ chains`, `processes = {run ids}`; the bracket in this mode reads `[×303 over 11 processes: first e1204 in 20260905-091125-fc7302, +302]` (no id list — ids are per process).
- Header lines (in this order): `invocation <id>: cargo <args> -- <N> processes, <k> with Err chains, <N-k> with none`; for each INCOMPLETE member: `INCOMPLETE: <run-id> never finalized -- its Err chains after the cut are not below`; `partial:` union with the member named per row (`<qualname> <file>:<line> (<reason>) in <run-id>`), capped like the single-run block; `panics: <sum> recorded -- …` when > 0; then `raised (<chains> chains over <k> processes, <S> swallowing sites):` where S = shapes with tag swallowed.
- A member whose recorder declares `err_flow: false`: print `REFUSED: <the caps.require sentence> (member <run-id>)` and return `UNSETTLED` before any classification.
- Exit: `ANSWERED` if any chain; else `UNSETTLED` if any member INCOMPLETE, else `NEGATIVE` — printing `no exceptions recorded across <N> processes` for the empty case.

- [ ] **Step 1: Failing tests** — build three synthetic Rust traces sharing `meta.invocation = "20260101-000000-abcdef"` (pass `invocation=…` through `swallow_trace(**meta)`; check `tests/helpers.rust_trace` accepts extra meta keys — read it; extend the helper if it does not): one with a swallow at sink A, one with the same sink A shape plus a swallow at sink B, one with no chains and `incomplete=True`. Tests:

```python
def test_an_invocation_id_answers_for_every_member(...):      # header "3 processes, 2 with Err chains, 1 with none"; "[×2 over 2 processes:" for sink A; sink B once; "dispositions: swallowed 3"
def test_incomplete_members_are_named_before_the_answer(...):  # the INCOMPLETE line names the third run id, printed before "raised ("
def test_the_exit_status_follows_the_rule(...):                # any chain -> 0; none + incomplete -> 3; none + all whole -> 1 (three stores)
def test_after_is_refused_in_invocation_mode(...):             # exit 2 and the sentence
def test_a_member_without_err_flow_refuses_the_whole(...):     # a member with capabilities err_flow False -> REFUSED naming it, exit 3
def test_an_ambiguous_prefix_is_refused(...):                  # two invocations "2026…-aaaaaa"/"2026…-aaaaab", ref "2026…-aaaaa" -> exit 2 "is ambiguous"
def test_a_ref_that_is_neither_keeps_the_old_error(...):       # "nope" -> the existing no-trace message and status
def test_a_run_id_still_wins_over_an_invocation_prefix(...):   # a ref that prefixes a trace stem is resolved as that trace, never as an invocation
```

- [ ] **Step 2: Implement**, green, then `tests/test_exceptions*.py` + `tests/test_runs*.py` (if any) + `tests/test_cli*.py` green.

- [ ] **Step 3: Mutations** — (1) merge key ignores site → the sink-B test red; (2) INCOMPLETE members not printed → red; (3) exit rule returns 0 on empty → red; (4) `--after` accepted → red; (5) ambiguity check removed → red. Restore.

- [ ] **Step 4: Commit** (explicit paths: the two `src` files, the test file).

---

### Task 4: Acceptance tooling, box-free tests, §1 locked ALONE

**Files:**
- Create: `rust/tests/acceptance_grain.py`, `rust/tests/acceptance_grain_schema.py`, `tests/test_acceptance_grain.py`
- Create: `docs/superpowers/acceptance/2026-09-05-sensorium-rung4-entry-grain.md` (header + §1, ALONE)

**Interfaces:**
- Reuse: `acceptance_rung3.{byte_lock_check, byte_lock_facts}` (they take a `doc` and `commit`), `acceptance_lib.{run, step, sha256_file, Refused}`, `acceptance_phases_rung3._sink_files`-style sqlite lookups (copy the two-line query, cite it), `acceptance_phases_rung3.phase_e6` for H1 (needs `paths` with `sensorium_driver`, `sensorium_dir`; `cfg["corpus_target"]`, `cfg["e6_workdir"]`).
- Env: `SENSORIUM_E6Q_STORES=/mnt/extra/sensorium-rung2/sensorium-dir/e6q` (the parent of `a`, `ws`, `ws0`), `SENSORIUM_DRIVER`, `SENSORIUM_CORPUS_TARGET`, `SENSORIUM_DIR` (a fresh store for H1's corpus recordings only).
- Runner functions (box-free-testable): `oracle(results_json) -> {"a": {(file,line): n}, "ws": {...}, "ws0": {...}, "tallies": {...}, "per_process": {arm: {run: tally_line|None}}}`; `parse_shapes(stdout) -> list[{tag, first_event, n, processes}]` (reads the bracket: `[×N: e…]` or `[×N over M processes: first e… in <run>, +K]`; a block without a bracket is n=1); `parse_tally(stdout) -> str|None`; `site_of_event(db_path, event_id) -> (file, line)` (the sqlite join); `compare_sites(measured: Counter, expected: Counter) -> {"equal": bool, "missing": [...], "extra": [...], "count_diffs": [...]}`.
- Main order: byte-lock → env → oracle from the committed `results.json` → H2 (A run) → H3 (every ws + ws0 trace: run `exceptions <run> --limit 100000`, compare tally line + Σ swallow group counts) → H4 (both invocations, wall-timed, 60 s kill = H5) → H1 (`phase_e6` on the corpus, fresh target) → H6 (`pytest -q` whole suite + `cargo test --workspace`? NO cargo: crates unchanged; run the Python suite only and record) → raw json → `--assemble` → markers `grain.DONE`/`.FAILED`. Every cell `{value, n, lens, dropped}`; nothing invented.

- [ ] **Step 1: Failing box-free tests** (`tests/test_acceptance_grain.py`): `parse_shapes` on a hand-written stdout (three blocks: one bare, one `[×4: e1, e2, e3, e4]`, one `[×9 over 3 processes: first e7 in r1, +8]`) → `[1, 4, 9]` with tags and processes; `oracle` on a tiny fake results json → the per-site counters and the summed tally; `compare_sites` reports missing/extra/count diffs and never says equal when a count differs; `site_of_event` on a tmp sqlite with `events`/`code_objects` rows; the lock tests (skip by name until `BYTE_LOCK` is set); the schema's none-vs-zero (a phase that did not run is `None` with a reason); the renderer prints `not measured (…)`.

- [ ] **Step 2: Implement runner + schema; green; mutations** — (1) `compare_sites` ignores count diffs → red; (2) `parse_shapes` treats a missing bracket as 0 → red; (3) the schema fills H4's headline from the oracle instead of the measurement → red (a test that feeds an oracle and no measurement must get `None`). Commit the tooling with `BYTE_LOCK = None`.

- [ ] **Step 3: §1 ALONE** — the acceptance document: header (what it measures; the oracle is the PUBLISHED record; the kept stores are the inputs; "§1 is byte-locked", the `awk` range), `## 1. Pre-registration` = design §4's table verbatim with the ledger's oracle numbers, the lens paragraph (stores' paths; the ws0 invocation id from T0; the driver 0.3.1 sha; Python version; the record's commit), "Reported without a gate", the four by-rule pin updates named (N2's three, N5's one), then `## 2. Environment` / `(written by Task 5)`. Commit ALONE: `docs(rung4): pre-register H1–H6 for the grain slice`; record the sha as LOCK.

- [ ] **Step 4: `BYTE_LOCK = "<sha>"`**, `-k lock` passes, commit the one line.

---

### Task 5: Measure once; §2–§5

- [ ] **Step 1: Preflight** — tree clean at the lock+1 commit; the stores present; `SENSORIUM_DIR` for H1 fresh (`/mnt/extra/sensorium-rung2/sensorium-dir/grain`, must not exist); `corpus-target-grain` absent; the driver sha recorded; load < 4.
- [ ] **Step 2: Launch detached** (`setsid nohup <launch.sh> &`, pid file, read nothing before `grain.DONE`/`.FAILED`). A `.FAILED` before any oracle comparison was printed is infrastructure: fix the runner plumbing (commit it, saying so) and relaunch; after a number is read: STOP and report.
- [ ] **Step 3: §2 lens, §3 rendered, §4 verdicts** (one row per H, the rule verbatim, the number, PASS/STOP; for H4 the missing/extra/count-diff lists if any), **§5 gaps** (what was not measured; any shape group whose vary lines fired, counted; the record's grain vs the tool's where they differ and why).
- [ ] **Step 4: `--assemble`, commit the record + results json**: `docs(rung4): grain slice measured — H1 … H6 <verdicts>`; `pytest tests/test_acceptance_grain.py -q` green (lock included).

---

### Task 6: Docs, version 0.8.2, close-out

- [ ] `README.md` `exceptions` section: a paragraph on the grouped block (`[×N: ids]`), the vary lines, `--limit` counting shapes, and the invocation form (`sensorium exceptions <invocation-id>` with the `runs` header id) — with the measured numbers from the record (54 blocks → 3 shapes; 144 calls → 1); note N7 (Python traces print per raise). `rust/README.md` if it shows `exceptions` output.
- [ ] `CHANGELOG.md` `## 0.8.2 — <date>`: the definition, the grouping, the invocation answer, the four by-rule pin updates, H1–H6 in the record's words. `pyproject.toml` → 0.8.2 (grep first: `0\.8\.1`/`0\.8\.2` hits accounted for; crates untouched).
- [ ] `docs/CARRIED-DEBT.md`: new `## 2026-09-05 — rung-4 entry, the grain of exceptions (Python 0.8.2)` section (Settled: the wording debt; Deferred: the acknowledgment marker N8 with its decided notation; Python grouping N7; whatever §5 found; Process lessons); in the borrow-repair section strike the wording-debt item (`~~…~~ — resolved: HONESTY §11 …`) and annotate the "three contestable classes" item (grouping makes the classes visible as shapes; the marker remains the settlement). `docs/superpowers/specs/2026-09-02-sensorium-rung3-inbox.md` §2a: the marker and Python grouping added as rung-4 items.
- [ ] Full gate: whole Python suite with the driver; `git status` clean; `wc -l` of every touched file ≤ 800. Commit(s) by explicit path. PR body draft in the ledger.

### After Task 6 — final review, fix wave, PR

Whole-branch review (fable) on `e307d90..HEAD` with the design, the record and the ledger's deferred lines; ONE fix wave (doc/test only after the lock); scoped re-review; push; PR; CI green; merge is Brice's.

## Self-review

- Spec coverage: N1/N2 → T1; N3/N4/N5 → T2; N6 → T3; N7 → T2/T3 tests + T6 README; N8 → T6; design §4 H1–H6 → T4/T5; §5's test list → T1/T2/T3/T4; §6 order kept.
- Placeholders: `<sha>`, `<date>`, `<verdicts>` are values the ledger supplies at the named step; the T2/T3 test lists name behaviours with exact expected strings where the string is fixed by the design (the bracket, the note, the header).
- Type consistency: `Disposition.site` (T2) is what `site_of` reads; `Shape` fields named identically in T2 and T4's parser expectations; `resolve_invocation`/`InvocationLookupError`/`run(args, invocation_id, members)` named identically in T3's interface and `exceptions_cmd.run`'s dispatch; `parse_shapes`/`oracle`/`compare_sites`/`site_of_event` named identically in T4's interface and tests.

---

## Addendum 2026-09-05 — repair slice after H4's STOP (ruling R-G12)

The first measurement (`docs/superpowers/acceptance/2026-09-05-sensorium-rung4-entry-grain.md`, commit `5841e3f`) read H4 **STOP**: the shape key's site was `qualname L<line>` with no file, and two test files sharing a `sandbox L42` (and two sharing a `fresh_dir L64`) merged across processes — 21 chains booked under a sibling file, every count conserved. That record stands as written. The repair is a NEW pre-registration measured once, on this branch, before T6.

### Task 7: The site key gains the file; collision disambiguation; the repair pre-registration locked ALONE

**Files:**
- Modify: `src/sensorium/query/exceptions_cmd.py` (`Disposition.site` becomes the SITE EVENT's identity the key needs — a `(file, line, qualname)` triple — or a small `Site` dataclass; the Python path never sets it), `src/sensorium/query/exceptions_rust.py` (`_swallowed`/`_escaped`/`_handled_then_failed` build it from the event's code object: `trace.code(e.code_id).file`, `e.line`, `qualname`; `_at` unchanged for PRINTING), `src/sensorium/query/exceptions_group.py` (`site_of` returns the triple for the key — origin fallback likewise; `print_shape` gains a `disambiguate: bool` so a colliding block prints `(<qualname> L<line> in <file basename>)` in its verdict parenthetical; `print_shapes` computes the collision set = shapes whose printed site text `qualname L<line>` occurs in more than one shape of THIS answer), `src/sensorium/query/exceptions_invocation.py` (merge on the same key; the collision set computed over the merged shapes; the `[in <run>]`/`[×N over …]` brackets unchanged).
- Create: `rust/tests/acceptance_grain_repair.py` (a sibling of `acceptance_grain.py`: imports its `main`/phases and overrides `DOC = …-grain-repair.md`, `BYTE_LOCK`, the ledger subdirectory `acceptance-grain-repair/` and the marker names; nothing else), `tests/test_acceptance_grain_repair.py` (the lock tests + "the sibling differs from the original only in DOC/BYTE_LOCK/paths"), `docs/superpowers/acceptance/2026-09-05-sensorium-rung4-entry-grain-repair.md` (header + §1 ALONE).
- Test: `tests/test_exceptions_rust_grouping.py` (+2: a single trace whose two code objects share `qualname`+`line` in two files → two shapes, both verdict lines carrying `in <basename>`; the no-collision case byte-identical), `tests/test_exceptions_invocation.py` (+1: two members, same `qualname L<line>` in different files → two merged shapes with the basenames; the positive control from the record: the same `sandbox L42` shape).

**Interfaces:**
- Consumes: T2's `Shape`/`group_chains`/`print_shape(s)`; T3's `_merge`/`bracket`; `Trace.code(code_id).file`.
- Produces: `Disposition.site: tuple[str, int, str] | None` (`(file, line, qualname)`); `exceptions_group.site_text(site) -> str` (`qualname L<line>`), `site_file(site) -> str` (basename); `collisions(shapes) -> set[key]`; `print_shape(trace, shape, bracket_text=…, disambiguate=False)`.

- [ ] **Step 1: failing tests** (the three above, exact strings: `(sandbox L42 in task_exec_run_test.rs)`; the byte-identity pins of T2 must still pass unchanged).
- [ ] **Step 2: implement**; corpus `51/108/0` (no case collides — if one does, STOP and report); the whole exceptions family + vectors green; mutants: (1) key drops the file → the two-files test red; (2) disambiguation off → the basename assertion red; (3) collision set computed per member instead of per answer in invocation mode → red.
- [ ] **Step 3: commit** the `src/` + test files by explicit path (`fix(exceptions): the shape key carries the file; colliding site texts print their file (R-G12)`).
- [ ] **Step 4: the sibling runner + its tests** (`BYTE_LOCK = None`), commit.
- [ ] **Step 5: §1′ ALONE** — `…-grain-repair.md`: header (this is the repair of the 2026-09-05 record's H4 STOP; that record stands; the oracle and the stores are the same), `## 1. Pre-registration` = the first document's §1 rows H1–H6 VERBATIM except: H4′'s endpoint reads "**ws: exactly 91 SWALLOWED shapes, one per (file, line) site, whose multiset equals the record's 91-row table (782 chains); ws0: 98 shapes / 812; summed tally, in the tool's `TAG_ORDER`, `swallowed 782, panicked 2, ambiguous 330` / `swallowed 812, panicked 2, ambiguous 300`; header 144/114/30; INCOMPLETE 0; collisions disambiguated: every shape whose site text collides carries its file basename (count reported)**"; H2′/H3′ state the tally lines as the tool prints them; H1′ names the by-rule pins (unchanged set); the lens names the first record and its lock. Commit ALONE; record the sha; set `BYTE_LOCK` in the sibling; `-k lock` passes.

### Task 8: Measure the repair once; §2–§5 of the repair record

Exactly Task 5's discipline (build the debug driver first; launch the SIBLING runner detached under `acceptance-grain-repair/`; read nothing before its marker; `.FAILED` before numbers = infrastructure, after = STOP). §2–§5 in the repair document; §4's verdicts table; §5 names what the repair changed against the first record (89/96 sites → 91/98; the disambiguated shapes counted). Commit the record + its `.results.json`. If H4′ is still a STOP, it is recorded with its number and the slice ships with two STOP records and no third measurement — the ruling is Brice's.

Task 6 then documents BOTH records (CHANGELOG 0.8.2: "measured twice; the first read STOP on the key's file; the second …").
