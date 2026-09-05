"""`exceptions` on a Rust trace prints one block per SHAPE (design N3-N5).

The grain a reader adjudicates at is the SITE, not the chain: the E6''''
record's busiest process printed 54 blocks, 52 of them one sink, and its
adjudicator had to build a per-site table by hand to read them. So two
chains with the same disposition tag, the same site the verdict is about,
and the same verdict text once event and frame ids are masked are ONE
shape, printed once -- the first chain's block, exactly as before, plus a
bracket naming the group.

WHAT THE BRACKET NAMES, AND WHY IT IS THE ORIGIN
-----------------------------------------------
`[x4: e412, e417, ...]` lists each member's ORIGIN event id -- the id the
block's own head line prints, the id `--after` filters on, and the id
`grep`/`tree` take. The first id in the bracket is therefore always the id
on the head line above it, so a reader can tell at a glance which member the
printed sentence is true of. Listing sink ids instead would name events that
appear nowhere else in the block for chains whose origin is not the sink.

Every builder here fixes its own event ids: the assertions below name them
literally, and a builder whose event list moved would fail loudly rather
than be re-pasted from a run.
"""
import shlex

from sensorium import cli
from sensorium.exit import ANSWERED
from sensorium.query.exceptions_group import mask
from tests.programs import LOOP_SAME_MESSAGE, record
from tests.rust_traces import (FILE, S1, SITE_FILE, call, err_flow, flow,
                               fn_site, frame, out, ret, rust_trace,
                               swallow_trace)

#: The RAISE line each origin fn uses, by code index in `escaped_trace`.
ESCAPE_LINES = {2: 18, 3: 40, 4: 70}


def repeat_sink_trace(tmp_path, monkeypatch, *, repeats=2, sink_lines=None,
                      origin_msgs=None):
    """`load()` calls `read_config()` `repeats` times and sinks each `Err`
    with a `.ok()`; `load` then returns ok. Every repeat is a swallowed
    chain absorbed at the SAME site unless `sink_lines` says otherwise.

    Event ids, for `repeats=2`: e1 CALL load; then per repeat i (0-based)
    e(2+4i) CALL read_config, e(3+4i) RAISE (the chain's ORIGIN),
    e(4+4i) RETURN err, e(5+4i) HANDLED (the sink); finally e(2+4*repeats)
    RETURN load ok. So the origins are e3, e7, ... and the sinks e5, e9, ...
    """
    sink_lines = sink_lines or [31] * repeats
    msgs = origin_msgs or ['Missing("port")'] * repeats
    last = 2 + 4 * repeats
    events = [call(1000, 1, 30)]
    frames = [frame(1, 1, last)]
    for i in range(repeats):
        base, ts = 2 + 4 * i, 2000 + 1000 * i
        frames.append(frame(2, base, base + 2, parent=1, depth=1))
        events += [
            call(ts, 2, 12),
            flow(ts + 100, "RAISE", 2 + i, 2, 14,
                 err_flow("exit", "demo::ConfigError", msgs[i], S1 + i,
                          hop=1, loc=f"{SITE_FILE}:14")),
            ret(ts + 200, 2 + i, 2, "err", f"Err({msgs[i]})"),
            flow(ts + 300, "HANDLED", 1, 1, sink_lines[i],
                 err_flow("sink_ok", "demo::ConfigError", msgs[i], S1 + i,
                          hop=1, terminal="swallowed_candidate",
                          loc=f"{SITE_FILE}:{sink_lines[i]}")),
        ]
    events.append(ret(2000 + 1000 * repeats, 1, 1, "ok", "None"))
    return rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "load", 30], [FILE, "read_config", 12]],
        frames=frames, events=events,
        sites=[fn_site("load", SITE_FILE, 30),
               fn_site("read_config", SITE_FILE, 12)])


def escaped_trace(tmp_path, monkeypatch, *, origins):
    """`hold()` calls one fn per entry of `origins` (a code index: 2 =
    `first`, 3 = `second`, 4 = `third`), each of which returns an `Err`
    nothing absorbs, and closes ok. Every chain reads *ambiguous -- the
    frame holding it returned ok with no sink recorded* -- a verdict that
    names NO site, so these chains group by their ORIGIN site and by
    nothing else.

    Event ids: e1 CALL hold; then per Err i (0-based) e(2+3i) CALL,
    e(3+3i) RAISE (the origin), e(4+3i) RETURN err; finally the RETURN of
    `hold`. So the origins are e3, e6, e9, ...
    """
    n = len(origins)
    events = [call(1000, 1, 5)]
    frames = [frame(1, 1, 2 + 3 * n)]
    for i, c in enumerate(origins):
        base, ts, line = 2 + 3 * i, 2000 + 1000 * i, ESCAPE_LINES[c]
        frames.append(frame(c, base, base + 2, parent=1, depth=1))
        events += [
            call(ts, c, line),
            flow(ts + 100, "RAISE", 2 + i, c, line,
                 err_flow("exit", "demo::Boom", "A", S1 + i, hop=1,
                          terminal="ambiguous_escaped")),
            ret(ts + 200, 2 + i, c, "err", "Err(A)"),
        ]
    events.append(ret(2000 + 1000 * n, 1, 1, "ok", "()"))
    return rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "hold", 5], [FILE, "first", 18], [FILE, "second", 40],
               [FILE, "third", 70]],
        frames=frames, events=events)


NO_SINK = ("ambiguous -- the frame holding it returned ok with no sink "
           "recorded")


# -- N3/N4: one block per shape, the bracket naming the members ------------
def test_two_chains_at_one_sink_print_once_with_a_bracket_and_the_tally_counts_two(
        tmp_path, monkeypatch, capsys):
    """Two `Err`s from two calls of `read_config`, both sunk by the same
    `.ok()` at L31: one block, the first chain's sentence, a bracket naming
    both origins -- and a tally that still counts CHAINS."""
    run_id = repeat_sink_trace(tmp_path, monkeypatch, repeats=2)
    assert cli.main(["exceptions", run_id]) == ANSWERED
    text = out(capsys)
    assert text.count("SWALLOWED --") == 1, text
    assert "raised (2):" in text, text
    # the FIRST chain's block, unchanged, with the bracket appended
    assert ("    SWALLOWED -- absorbed by sink_ok at e5 (load L31) in f1, "
            "which returned ok  [×2: e3, e7]") in text, text
    # the head above it names the first member, and the bracket opens with it
    head = ("  e3 RAISE   read_config raise "
            "demo::ConfigError('Missing(\"port\")') L14")
    assert head in text, text
    assert text.index(head) < text.index("×2"), text
    # the second chain's own sentence is NOT printed
    assert "at e9 (load L31)" not in text, text
    assert "dispositions: swallowed 2" in text, text
    # nothing varies: one origin site, one message, one detail, one route
    assert "origins:" not in text and "messages:" not in text, text
    assert "details vary" not in text and "routes:" not in text, text


def test_a_group_of_one_is_byte_identical_to_the_ungrouped_block(
        tmp_path, monkeypatch, capsys):
    """The corpus and the vectors pin single-chain blocks. A group of one
    prints no bracket, no vary line, and not a word of new punctuation."""
    run_id = swallow_trace(tmp_path, monkeypatch)
    assert cli.main(["exceptions", run_id]) == ANSWERED
    text = out(capsys)
    assert "[×" not in text, text
    assert "\n".join([
        "raised (1):",
        "  e3 RAISE   read_config raise "
        "demo::ConfigError('Missing(\"port\")') L14",
        "    SWALLOWED -- absorbed by sink_ok at e5 (load L31) in f1, "
        "which returned ok",
        "      hops: e3 read_config L14 exit -> e5 load L31 sink_ok",
        "dispositions: swallowed 1",
    ]) + "\n" == text, text


def test_two_sinks_are_two_shapes(tmp_path, monkeypatch, capsys):
    """Same fn, same disposition, two `.ok()` calls on different lines:
    two sites, so two blocks, each printed exactly as it is today."""
    run_id = repeat_sink_trace(tmp_path, monkeypatch, repeats=2,
                               sink_lines=[31, 33])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    text = out(capsys)
    assert text.count("SWALLOWED --") == 2, text
    assert "[×" not in text, text
    assert ("SWALLOWED -- absorbed by sink_ok at e5 (load L31) in f1, "
            "which returned ok") in text, text
    assert ("SWALLOWED -- absorbed by sink_ok at e9 (load L33) in f1, "
            "which returned ok") in text, text
    assert "dispositions: swallowed 2" in text, text


def test_a_sink_shape_whose_messages_differ_says_so_and_not_origins(
        tmp_path, monkeypatch, capsys):
    """One sink, two `Err`s raised at ONE site that are not the same
    error. The group is real (same tag, same site, same masked verdict) and
    the block says the members' ERRORS are not all one thing -- `messages:`
    (ruling R-G6). The old single `heads` set called this "2 distinct
    origins", which was a false statement about where they came from."""
    run_id = repeat_sink_trace(
        tmp_path, monkeypatch, repeats=2,
        origin_msgs=['Missing("port")', 'Missing("host")'])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    text = out(capsys)
    assert text.count("SWALLOWED --") == 1, text
    assert "[×2: e3, e7]" in text, text
    assert "      messages: 2 distinct (first shown)" in text, text
    # one site, so nothing to say about origins; and the two routes differ
    # only by ids, which the mask explains
    assert "origins:" not in text, text
    assert "routes:" not in text, text
    assert "details vary" not in text, text
    assert "dispositions: swallowed 2" in text, text


def test_ambiguous_no_sink_chains_group_by_origin_site(
        tmp_path, monkeypatch, capsys):
    """A verdict that names no site is keyed on the chain's ORIGIN site:
    two `Err`s born in `first` are one shape, and the one born in `second`
    is another -- though all three print the same sentence."""
    run_id = escaped_trace(tmp_path, monkeypatch, origins=[2, 2, 3])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    text = out(capsys)
    assert text.count(NO_SINK) == 2, text
    assert "[×2: e3, e6]" in text, text
    assert "  e3 RAISE   first raise demo::Boom('A') L18" in text, text
    assert "  e9 RAISE   second raise demo::Boom('A') L40" in text, text
    assert "  e6 RAISE" not in text, text
    assert "dispositions: ambiguous 3" in text, text


# -- N5: --limit counts shapes, --after still scopes chains ----------------
def test_limit_counts_shapes_and_the_note_raises_the_limit(
        tmp_path, monkeypatch, capsys):
    """Four chains, three shapes. `--limit 1` clips SHAPES, the tally
    still counts CHAINS, and the continuation raises the limit -- an event
    cursor over grouped output would re-show a partial group."""
    run_id = escaped_trace(tmp_path, monkeypatch, origins=[2, 2, 3, 4])
    assert cli.main(["exceptions", run_id, "--limit", "1"]) == ANSWERED
    text = out(capsys)
    assert text.count(NO_SINK) == 1, text
    assert "[×2: e3, e6]" in text, text
    assert "e9 RAISE" not in text and "e12 RAISE" not in text, text
    assert "dispositions: ambiguous 4" in text, text
    assert (f"... 2 more; continue with: sensorium exceptions {run_id} "
            "--limit 3") in text, text
    assert "--after" not in text, text
    # and the continuation is runnable, showing every shape
    hint = text.strip().splitlines()[-1].split("continue with: ", 1)[1]
    assert cli.main(shlex.split(hint)[1:]) == ANSWERED
    rest = out(capsys)
    assert rest.count(NO_SINK) == 3, rest
    assert "... " not in rest, rest


def test_after_still_scopes_by_origin_id(tmp_path, monkeypatch, capsys):
    """`--after` filters CHAINS by origin id, before any group forms: drop
    the first member of a two-chain shape and what is left is a group of
    one, printed with its own sentence and no bracket."""
    run_id = repeat_sink_trace(tmp_path, monkeypatch, repeats=2)
    assert cli.main(["exceptions", run_id, "--after", "e3"]) == ANSWERED
    text = out(capsys)
    assert ("raised (1 of 2; 1 earlier chain(s) skipped by --after e3):"
            in text), text
    assert "[×" not in text, text
    assert ("SWALLOWED -- absorbed by sink_ok at e9 (load L31) in f1, "
            "which returned ok") in text, text
    assert "e3 RAISE" not in text, text
    assert "dispositions: swallowed 1" in text, text


def test_nine_ids_print_eight_and_a_plus_one(tmp_path, monkeypatch, capsys):
    """The bracket is a name for the group, not a dump of it: eight ids,
    then how many more there are."""
    run_id = escaped_trace(tmp_path, monkeypatch, origins=[2] * 9)
    assert cli.main(["exceptions", run_id]) == ANSWERED
    text = out(capsys)
    assert text.count(NO_SINK) == 1, text
    assert ("[×9: e3, e6, e9, e12, e15, e18, e21, e24, … +1]"
            in text), text
    assert "e27" not in text, text
    assert "dispositions: ambiguous 9" in text, text


# -- N7: the Python rules and their output are untouched -------------------
def test_the_python_path_is_untouched(tmp_path, monkeypatch, capsys):
    """`LOOP_SAME_MESSAGE` swallows the same ValueError at the same line
    three times -- one shape by the Rust key, and still three blocks here.
    Python grouping is a rung-4 item; until its "site the verdict is about"
    is defined, this path prints one block per RAISE and pages by event."""
    run_id = record(tmp_path, monkeypatch, LOOP_SAME_MESSAGE)
    assert cli.main(["exceptions", run_id]) == ANSWERED
    text = out(capsys)
    assert text.count("SWALLOWED") == 3, text
    assert "[×" not in text, text
    assert "swallowed 3" in text, text
    assert cli.main(["exceptions", run_id, "--limit", "1"]) == ANSWERED
    clipped = out(capsys)
    assert clipped.count("SWALLOWED") == 1, clipped
    assert "2 more; continue with:" in clipped, clipped
    assert "--after e" in clipped, clipped


# -- R-G2: for an origin-keyed verdict, the ROUTE joins the key ------------
def two_routes_trace(tmp_path, monkeypatch):
    """Two `Err`s born at ONE origin site (`first L18`), one of which
    crossed a frame on its way out and one of which did not -- the shape
    `corpus/rust/outcome_generic` and `macro_arg_partial` are built on.

    Event ids: e1 CALL hold, e2 CALL relay, e3 CALL first, e4 RAISE (the
    first chain's ORIGIN), e5 RETURN first err, e6 RAISE relay (its hop,
    and its terminal), e7 RETURN relay err, e8 CALL first, e9 RAISE (the
    second chain, born and ended in one event), e10 RETURN first err,
    e11 RETURN hold ok.
    """
    return rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "hold", 5], [FILE, "first", 18], [FILE, "relay", 30]],
        frames=[frame(1, 1, 11),
                frame(3, 2, 7, parent=1, depth=1),
                frame(2, 3, 5, parent=2, depth=2),
                frame(2, 8, 10, parent=1, depth=1)],
        events=[
            call(1000, 1, 5),
            call(1100, 3, 30),
            call(1200, 2, 18),
            flow(1300, "RAISE", 3, 2, 18,
                 err_flow("exit", "demo::Boom", "A", S1, hop=1)),
            ret(1400, 3, 2, "err", "Err(A)"),
            flow(1500, "RAISE", 2, 3, 32,
                 err_flow("try", "demo::Boom", "A", S1, hop=2,
                          terminal="ambiguous_escaped")),
            ret(1600, 2, 3, "err", "Err(A)"),
            call(1700, 2, 18),
            flow(1800, "RAISE", 4, 2, 18,
                 err_flow("exit", "demo::Boom", "A", S1 + 1, hop=1,
                          terminal="ambiguous_escaped")),
            ret(1900, 4, 2, "err", "Err(A)"),
            ret(2000, 1, 1, "ok", "()"),
        ])


def test_one_origin_two_routes_are_two_shapes(tmp_path, monkeypatch, capsys):
    """A verdict that names no site is keyed on the route as well (ruling
    R-G2): where the sentence says nothing about a place, the journey is
    the answer, and a chain with NO recorded hop is not the same shape as
    one that crossed a frame -- the missing hop is the finding."""
    run_id = two_routes_trace(tmp_path, monkeypatch)
    assert cli.main(["exceptions", run_id]) == ANSWERED
    text = out(capsys)
    assert text.count(NO_SINK) == 2, text
    assert "[×" not in text, text
    assert "routes:" not in text, text
    assert "  e4 RAISE   first raise demo::Boom('A') L18" in text, text
    assert "  e9 RAISE   first raise demo::Boom('A') L18" in text, text
    assert ("      hops: e4 first L18 exit -> e6 relay L32 try"
            in text), text
    assert "dispositions: ambiguous 2" in text, text


# -- R-G3: the route's vary line does not answer to `hops:` ----------------
def mixed_sink_trace(tmp_path, monkeypatch, *, outside_first=False):
    """One `.ok()` at `load L31` absorbing two chains that reached it
    differently: one raised in `read_config` and hopped out, one first seen
    at the sink itself (born outside, so it has a detail and no route).
    Same tag, same SINK site, same masked verdict -- one shape, whose
    members differ in every set the key does not look at.

    `outside_first` puts the born-outside chain FIRST, which is what makes
    the two parentheticals of ruling R-G5 observable: the printed member
    then has a detail and no route, and with the default it has a route and
    no detail.

    Event ids, default order: e1 CALL load, e2 CALL read_config, e3 RAISE
    (chain 1's origin), e4 RETURN err, e5 HANDLED (the sink, ending chain
    1), e6 HANDLED (the whole of chain 2), e7 RETURN load ok. With
    `outside_first`: e1 CALL load, e2 HANDLED (the whole of the outside
    chain), e3 CALL read_config, e4 RAISE, e5 RETURN err, e6 HANDLED,
    e7 RETURN load ok.
    """
    outside = err_flow("sink_ok", "std::io::Error", 'Os { code: 2 }',
                       S1 + 1, hop=1, origin="outside",
                       terminal="swallowed_candidate")
    raised = err_flow("exit", "demo::ConfigError", 'Missing("port")', S1,
                      hop=1)
    sunk = err_flow("sink_ok", "demo::ConfigError", 'Missing("port")', S1,
                    hop=1, terminal="swallowed_candidate")
    if outside_first:
        events = [call(1000, 1, 30),
                  flow(1050, "HANDLED", 1, 1, 31, outside),
                  call(1100, 2, 12),
                  flow(1200, "RAISE", 2, 2, 14, raised),
                  ret(1300, 2, 2, "err", 'Err(Missing("port"))'),
                  flow(1400, "HANDLED", 1, 1, 31, sunk)]
        frames = [frame(1, 1, 7), frame(2, 3, 5, parent=1, depth=1)]
    else:
        events = [call(1000, 1, 30),
                  call(1100, 2, 12),
                  flow(1200, "RAISE", 2, 2, 14, raised),
                  ret(1300, 2, 2, "err", 'Err(Missing("port"))'),
                  flow(1400, "HANDLED", 1, 1, 31, sunk),
                  flow(1500, "HANDLED", 1, 1, 31, outside)]
        frames = [frame(1, 1, 7), frame(2, 2, 4, parent=1, depth=1)]
    return rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "load", 30], [FILE, "read_config", 12]],
        frames=frames,
        events=events + [ret(1600, 1, 1, "ok", "None")])


def test_the_route_vary_line_is_spelled_routes_not_hops(
        tmp_path, monkeypatch, capsys):
    """A sink group whose members took different routes is FLAGGED, and
    the flag is spelled `routes:` (ruling R-G3): the first spelling shared
    its prefix with the real `hops:` line, so every counter over the output
    -- the corpus's own `expect_count` among them -- counted a flag as a
    journey."""
    run_id = mixed_sink_trace(tmp_path, monkeypatch)
    assert cli.main(["exceptions", run_id]) == ANSWERED
    text = out(capsys)
    assert text.count("SWALLOWED --") == 1, text
    assert "[×2: e3, e6]" in text, text
    # one real hops line in the output, and a `hops:` count that says one
    assert text.count("hops:") == 1, text
    assert len([ln for ln in text.splitlines()
                if ln.strip().startswith("hops:")]) == 1, text
    assert "      routes: 2 distinct (first shown)" in text, text
    assert "distinct paths" not in text, text
    # every set differs, and they are named in the pinned order
    body = [ln.strip() for ln in text.splitlines()]
    labels = [ln.split(":")[0] if ":" in ln.split(" (")[0] else "details"
              for ln in body
              if ln.startswith(("origins:", "messages:", "details vary",
                                "routes:"))]
    assert labels == ["origins", "messages", "details", "routes"], text
    assert "      origins: 2 distinct (first shown)" in text, text
    assert "      messages: 2 distinct (first shown)" in text, text
    # the printed member HAS a route and HAS no detail, and each
    # parenthetical says which (ruling R-G5)
    assert "      details vary (2 distinct; this one has none)" in text, text
    assert "dispositions: swallowed 2" in text, text


def test_a_flag_says_so_when_the_printed_block_has_none_of_what_it_counts(
        tmp_path, monkeypatch, capsys):
    """The same sink, with the born-outside chain printed FIRST: that
    member has a detail and no hops line, so `routes:` must not claim the
    first is shown (ruling R-G5) while `details vary` may."""
    run_id = mixed_sink_trace(tmp_path, monkeypatch, outside_first=True)
    assert cli.main(["exceptions", run_id]) == ANSWERED
    text = out(capsys)
    assert text.count("SWALLOWED --") == 1, text
    assert "[×2: e2, e4]" in text, text
    # the printed member is the born-outside one: a detail, and no route
    assert ("      born outside this thread's instrumented frames; "
            "absorbed at sink_ok") in text, text
    assert "hops:" not in text, text
    assert "      routes: 2 distinct (this one has none)" in text, text
    assert "      details vary (2 distinct; first shown)" in text, text
    assert "dispositions: swallowed 2" in text, text


# -- R-G7: the continuation carries the reader's own --after ---------------
def test_the_note_keeps_the_after_the_reader_gave(
        tmp_path, monkeypatch, capsys):
    """`--after e3 --limit 1` over four chains in three shapes: the
    continuation must answer the SAME question, so it carries the
    `--after`. Without it the next page reports four chains where the
    reader asked about three."""
    run_id = escaped_trace(tmp_path, monkeypatch, origins=[2, 2, 3, 4])
    assert cli.main(["exceptions", run_id, "--after", "e3",
                     "--limit", "1"]) == ANSWERED
    text = out(capsys)
    assert "raised (3 of 4; 1 earlier chain(s) skipped by --after e3):" in text
    assert (f"... 2 more; continue with: sensorium exceptions {run_id} "
            "--after e3 --limit 3") in text, text
    # and the continuation is runnable and answers the same three chains
    hint = text.strip().splitlines()[-1].split("continue with: ", 1)[1]
    assert cli.main(shlex.split(hint)[1:]) == ANSWERED
    rest = out(capsys)
    assert "raised (3 of 4; 1 earlier chain(s) skipped by --after e3):" in rest
    assert "dispositions: ambiguous 3" in rest, rest
    assert "... " not in rest, rest


# -- R-G8: the mask leaves Rust's float type names alone -------------------
def test_the_mask_does_not_eat_rust_float_type_names():
    """`f64` in a panic message is a TYPE, not a frame. Masking it merged
    two verdicts that name different types -- and `f3` is still a frame."""
    assert mask("expected f64, found f32 at e12 in f3") == (
        "expected f64, found f32 at e# in f#")
    assert mask("f16 f128 f1 f4 f321 e0") == "f16 f128 f# f# f# e#"
    assert mask("kind: NotFound, code: 2") == "kind: NotFound, code: 2"
