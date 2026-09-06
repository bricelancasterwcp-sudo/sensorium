"""`exceptions <invocation-id>` answers for a whole cargo invocation (N6).

WHY THE MODE EXISTS
-------------------
`cargo sensorium test --workspace` writes one trace per PROCESS, and the
E6'''' record's adjudicator had to ask the tool 144 separate questions --
then add the answers up by hand -- to learn what became of the workspace's
`Err`s. The question is asked about the invocation, so the tool takes the
invocation's id: the same id `runs` already prints above the group.

WHAT THESE TESTS PIN
--------------------
The header's three counts, the INCOMPLETE members named BEFORE any answer
about chains (an unfinalized process is a gap in the whole, not a zero),
groups merged across processes on the same key with a bracket naming the
spread, the summed tally, the union of the `partial` rows with each row's
process named, the summed panic count, and the four ways this mode refuses:
`--after` (an event id belongs to one process), a member whose recorder
declares no `err_flow` (the whole answer is refused, naming it), an
ambiguous invocation prefix, and a ref that names neither.

The last of them is the rule that keeps the two namespaces apart: a ref
that prefixes a TRACE STEM is a run reference and is never re-read as an
invocation, so adding this mode cannot change the answer to a question that
already had one.

Every builder here fixes its own event ids: the assertions name them
literally, so a builder whose event list moved fails loudly rather than
being re-pasted from a run.
"""
from sensorium import cli
from sensorium.exit import ANSWERED, BAD_CALL, NEGATIVE, UNSETTLED
from tests.helpers import RUST_CAPABILITIES, rust_exc, rust_trace
from tests.rust_traces import (FILE, S1, S2, SITE_FILE, call, err_flow, flow,
                               fn_site, frame, out, ret, swallow_trace)

INV = "20260101-000000-abcdef"
M1 = "20260101-000000-aaa001"
M2 = "20260101-000000-aaa002"
M3 = "20260101-000000-aaa003"
CARGO = ["test", "--workspace"]


def two_sink_trace(tmp_path, monkeypatch, **meta):
    """`load()` calls `read_config()` twice and sinks each `Err` at a
    DIFFERENT `.ok()`: one shape at `load L31` -- the same shape
    `swallow_trace` records -- and one at `load L45`.

    Event ids: e1 CALL load, e2 CALL read_config, e3 RAISE (chain 1's
    origin), e4 RETURN err, e5 HANDLED at L31, e6 CALL read_config, e7 RAISE
    (chain 2's origin), e8 RETURN err, e9 HANDLED at L45, e10 RETURN ok.
    """
    return rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "load", 30], [FILE, "read_config", 12]],
        frames=[frame(1, 1, 10), frame(2, 2, 4, parent=1, depth=1),
                frame(2, 6, 8, parent=1, depth=1)],
        events=[
            call(1000, 1, 30),
            call(2000, 2, 12),
            flow(3000, "RAISE", 2, 2, 14,
                 err_flow("exit", "demo::ConfigError", 'Missing("port")', S1,
                          hop=1, loc=f"{SITE_FILE}:14")),
            ret(4000, 2, 2, "err", 'Err(Missing("port"))'),
            flow(5000, "HANDLED", 1, 1, 31,
                 err_flow("sink_ok", "demo::ConfigError", 'Missing("port")',
                          S1, hop=1, terminal="swallowed_candidate",
                          loc=f"{SITE_FILE}:31")),
            call(6000, 2, 12),
            flow(7000, "RAISE", 3, 2, 14,
                 err_flow("exit", "demo::ConfigError", 'Missing("port")', S2,
                          hop=1, loc=f"{SITE_FILE}:14")),
            ret(8000, 3, 2, "err", 'Err(Missing("port"))'),
            flow(9000, "HANDLED", 1, 1, 45,
                 err_flow("sink_ok", "demo::ConfigError", 'Missing("port")',
                          S2, hop=1, terminal="swallowed_candidate",
                          loc=f"{SITE_FILE}:45")),
            ret(10000, 1, 1, "ok", "None"),
        ],
        sites=[fn_site("load", SITE_FILE, 30),
               fn_site("read_config", SITE_FILE, 12)],
        **meta)


def escaped_trace(tmp_path, monkeypatch, *, fn, line, **meta):
    """A chain of ONE event whose frame returned ok with no sink recorded.

    The verdict for it names no site and quotes no id, and a one-event chain
    prints no `hops:` line -- so the chain's ORIGIN is the only component of
    the key that can tell two of these apart. Two of them at different
    origins are two shapes, in one process or in eleven.
    """
    return rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "run", 3], [FILE, fn, line]],
        frames=[frame(1, 1, 5), frame(2, 2, 4, parent=1, depth=1)],
        events=[
            call(1000, 1, 3),
            call(2000, 2, line),
            flow(3000, "RAISE", 2, 2, line,
                 err_flow("exit", "demo::Boom", "A", S1, hop=1,
                          terminal="ambiguous_escaped")),
            ret(4000, 2, 2, "err", "Err(A)"),
            ret(5000, 1, 1, "ok", "None"),
        ],
        **meta)


def sink31_trace(tmp_path, monkeypatch, *, origin_fn, origin_line, msg,
                 **meta):
    """A chain raised in `origin_fn` and absorbed by the SAME `.ok()` every
    other member's is: `sink_ok` at `load L31`.

    The verdict is therefore word-for-word identical across members once
    ids are masked, and the site it names is the same -- one shape -- while
    the origin, the message and the route differ, which is exactly what the
    key does not look at and the vary lines must report.

    Event ids: e1 CALL load, e2 CALL `origin_fn`, e3 RAISE (the chain's
    origin), e4 RETURN err, e5 HANDLED (the sink), e6 RETURN load ok.
    """
    return rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "load", 30], [FILE, origin_fn, origin_line]],
        frames=[frame(1, 1, 6), frame(2, 2, 4, parent=1, depth=1)],
        events=[
            call(1000, 1, 30),
            call(2000, 2, origin_line),
            flow(3000, "RAISE", 2, 2, origin_line + 2,
                 err_flow("exit", "demo::ConfigError", msg, S1, hop=1)),
            ret(4000, 2, 2, "err", f"Err({msg})"),
            flow(5000, "HANDLED", 1, 1, 31,
                 err_flow("sink_ok", "demo::ConfigError", msg, S1, hop=1,
                          terminal="swallowed_candidate")),
            ret(6000, 1, 1, "ok", "None"),
        ],
        sites=[fn_site("load", SITE_FILE, 30),
               fn_site(origin_fn, SITE_FILE, origin_line)],
        **meta)


def outside_sink31_trace(tmp_path, monkeypatch, **meta):
    """The same `.ok()` at `load L31`, absorbing a chain first seen AT the
    sink: born outside this thread's instrumented frames, so it has a
    detail and -- being one event -- no route at all."""
    return rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "load", 30]],
        frames=[frame(1, 1, 3)],
        events=[
            call(1000, 1, 30),
            flow(2000, "HANDLED", 1, 1, 31,
                 err_flow("sink_ok", "std::io::Error", "Os { code: 2 }", S1,
                          hop=1, origin="outside",
                          terminal="swallowed_candidate")),
            ret(3000, 1, 1, "ok", "None"),
        ],
        sites=[fn_site("load", SITE_FILE, 30)],
        **meta)


def partial_row(qualname, line):
    return {"file": SITE_FILE, "line": line, "qualname": qualname,
            "kind": "try", "reason": "macro-arg"}


def quiet_trace(tmp_path, monkeypatch, **meta):
    """A member that recorded no `Err` chain at all."""
    return rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "run", 3]],
        frames=[frame(1, 1, 2)],
        events=[call(1000, 1, 3), ret(2000, 1, 1, "ok", "()")],
        **meta)


def cut_trace(tmp_path, monkeypatch, **meta):
    """A member whose recording never finalized: one open frame, no close."""
    return rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "run", 3]],
        frames=[frame(1, 1, None, closed_by=None)],
        events=[call(1000, 1, 3)],
        incomplete=True, live_threads=[1], **meta)


def panic_only_trace(tmp_path, monkeypatch, **meta):
    """A member that panicked and recorded no `Err` chain: the panic is a
    frame's unwind, not a chain, and is COUNTED rather than dropped."""
    unwind = {"kind": "panic", "type": "panic", "msg": "boom", "serial": 1}
    return rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "crash", 40]],
        frames=[frame(1, 1, None, closed_by=None, unwind_exc=unwind)],
        events=[
            call(1000, 1, 40),
            {"ts": 2000, "thread": 1, "kind": "RAISE", "frame": 1, "code": 1,
             "line": 41,
             "payload": {"exc": rust_exc("panic", "boom", 1, kind="panic")},
             "task": None},
        ],
        **meta)


def three_members(tmp_path, monkeypatch):
    """One invocation: a swallow at sink A, the same shape plus a swallow at
    sink B, and a process that never finalized and recorded no chain."""
    swallow_trace(tmp_path, monkeypatch, run_id=M1, invocation=INV,
                  cargo_args=CARGO)
    two_sink_trace(tmp_path, monkeypatch, run_id=M2, invocation=INV,
                   cargo_args=CARGO)
    cut_trace(tmp_path, monkeypatch, run_id=M3, invocation=INV,
              cargo_args=CARGO)
    return INV


# -- the answer -------------------------------------------------------------
def test_an_invocation_id_answers_for_every_member(
        tmp_path, monkeypatch, capsys):
    """One question, three processes: the header counts them, the two
    members that sank an `Err` at `load L31` are ONE group, and the tally is
    the sum over every member's chains."""
    inv = three_members(tmp_path, monkeypatch)
    assert cli.main(["exceptions", inv]) == ANSWERED
    o = out(capsys)
    assert (f"invocation {INV}: cargo test --workspace -- 3 processes, "
            "2 with Err chains, 1 with none") in o, o
    assert "raised (3 chains over 2 processes, 2 swallowing sites):" in o, o
    # sink A: one block, named for the FIRST member, counting both
    assert o.count("(load L31)") == 1, o
    assert f"  [×2 over 2 processes: first e3 in {M1}, +1]" in o, o
    # sink B: one process, and the block still says which one
    assert o.count("(load L45)") == 1, o
    assert f"  [in {M2}]" in o, o
    assert "dispositions: swallowed 3" in o, o
    # the merged members agree in everything the key does not look at, so
    # the block flags nothing: a vary line means something because it is
    # not printed here.
    assert "origins:" not in o and "messages:" not in o, o
    assert "details vary" not in o and "routes:" not in o, o


def one_process_two_chains_trace(tmp_path, monkeypatch, **meta):
    """`load()` sinks TWO `Err`s at the SAME `.ok()` (L31), so one process
    carries a shape of two chains.

    Event ids: e1 CALL load, e2 CALL read_config, e3 RAISE (chain 1's
    origin), e4 RETURN err, e5 HANDLED at L31, e6 CALL read_config, e7 RAISE
    (chain 2's origin), e8 RETURN err, e9 HANDLED at L31, e10 RETURN ok.
    """
    return rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "load", 30], [FILE, "read_config", 12]],
        frames=[frame(1, 1, 10), frame(2, 2, 4, parent=1, depth=1),
                frame(2, 6, 8, parent=1, depth=1)],
        events=[
            call(1000, 1, 30),
            call(2000, 2, 12),
            flow(3000, "RAISE", 2, 2, 14,
                 err_flow("exit", "demo::ConfigError", 'Missing("port")', S1,
                          hop=1, loc=f"{SITE_FILE}:14")),
            ret(4000, 2, 2, "err", 'Err(Missing("port"))'),
            flow(5000, "HANDLED", 1, 1, 31,
                 err_flow("sink_ok", "demo::ConfigError", 'Missing("port")',
                          S1, hop=1, terminal="swallowed_candidate",
                          loc=f"{SITE_FILE}:31")),
            call(6000, 2, 12),
            flow(7000, "RAISE", 3, 2, 14,
                 err_flow("exit", "demo::ConfigError", 'Missing("port")', S2,
                          hop=1, loc=f"{SITE_FILE}:14")),
            ret(8000, 3, 2, "err", 'Err(Missing("port"))'),
            flow(9000, "HANDLED", 1, 1, 31,
                 err_flow("sink_ok", "demo::ConfigError", 'Missing("port")',
                          S2, hop=1, terminal="swallowed_candidate",
                          loc=f"{SITE_FILE}:31")),
            ret(10000, 1, 1, "ok", "None"),
        ],
        sites=[fn_site("load", SITE_FILE, 30),
               fn_site("read_config", SITE_FILE, 12)],
        **meta)


def test_a_group_confined_to_one_member_says_process_in_the_singular(
        tmp_path, monkeypatch, capsys):
    """A count that reads `1 processes` is the tell that a number was
    printed by a template rather than said by anyone, and in this mode the
    singular is the COMMON case: most shapes of a 144-process sweep live in
    one member. Two processes, a shape of two chains that both came from the
    first, and the header's own `over N processes` counting the members that
    had a chain -- both singular here, and neither is the member count."""
    one_process_two_chains_trace(tmp_path, monkeypatch, run_id=M1,
                                 invocation=INV, cargo_args=CARGO)
    quiet_trace(tmp_path, monkeypatch, run_id=M2, invocation=INV,
                cargo_args=CARGO)
    assert cli.main(["exceptions", INV]) == ANSWERED
    o = out(capsys)
    assert (f"invocation {INV}: cargo test --workspace -- 2 processes, "
            "1 with Err chains, 1 with none") in o, o
    assert "raised (2 chains over 1 process, 1 swallowing sites):" in o, o
    assert f"  [×2 over 1 process: first e3 in {M1}, +1]" in o, o
    assert "1 processes" not in o, o
    assert "dispositions: swallowed 2" in o, o


def test_the_after_refusal_counts_a_lone_member_in_the_singular(
        tmp_path, monkeypatch, capsys):
    """The refusal's other use of the same speller. An invocation of one
    process still refuses `--after` -- the id is minted per process and the
    mode is the invocation's -- and the sentence that says why must not read
    `spans 1 processes`."""
    swallow_trace(tmp_path, monkeypatch, run_id=M1, invocation=INV,
                  cargo_args=CARGO)
    assert cli.main(["exceptions", INV, "--after", "e1"]) == BAD_CALL
    o = out(capsys)
    assert ("--after names an event of one process; this answer spans "
            "1 process -- page with --limit") in o, o


def test_incomplete_members_are_named_before_the_answer(
        tmp_path, monkeypatch, capsys):
    """A process that stopped mid-flight is a gap in the whole answer, so it
    is named ABOVE the chains rather than left to be inferred from a count
    that does not add up."""
    inv = three_members(tmp_path, monkeypatch)
    assert cli.main(["exceptions", inv]) == ANSWERED
    o = out(capsys)
    line = (f"INCOMPLETE: {M3} never finalized -- its Err chains after the "
            "cut are not below")
    assert line in o, o
    assert o.index(line) < o.index("raised ("), o
    # the members that DID finalize are not accused of stopping early
    assert M1 not in o.split("raised (")[0].replace(line, ""), o


def test_the_exit_status_follows_the_rule(tmp_path, monkeypatch, capsys):
    """0 if any chain; else 3 if any member never finalized (silence there
    reports where the RECORDING ended); else 1."""
    a = tmp_path / "a"
    assert cli.main(["exceptions", three_members(a, monkeypatch)]) == ANSWERED
    capsys.readouterr()

    b = tmp_path / "b"
    quiet_trace(b, monkeypatch, run_id=M1, invocation=INV, cargo_args=CARGO)
    cut_trace(b, monkeypatch, run_id=M2, invocation=INV, cargo_args=CARGO)
    assert cli.main(["exceptions", INV]) == UNSETTLED
    o = out(capsys)
    assert "no exceptions recorded across 2 processes" in o, o
    assert f"INCOMPLETE: {M2} never finalized" in o, o

    c = tmp_path / "c"
    quiet_trace(c, monkeypatch, run_id=M1, invocation=INV, cargo_args=CARGO)
    quiet_trace(c, monkeypatch, run_id=M2, invocation=INV, cargo_args=CARGO)
    assert cli.main(["exceptions", INV]) == NEGATIVE
    o = out(capsys)
    assert "no exceptions recorded across 2 processes" in o, o
    assert "INCOMPLETE" not in o, o


def test_two_origin_sites_stay_two_shapes_across_processes(
        tmp_path, monkeypatch, capsys):
    """The merge key is the WHOLE key, the origin fallback included. These
    two chains earn the same tag and word-for-word the same verdict -- which
    names no site -- and neither prints a route, so a merge that looked at
    anything less than the site would report two places as one."""
    escaped_trace(tmp_path, monkeypatch, fn="alpha", line=18, run_id=M1,
                  invocation=INV, cargo_args=CARGO)
    escaped_trace(tmp_path, monkeypatch, fn="beta", line=28, run_id=M2,
                  invocation=INV, cargo_args=CARGO)
    assert cli.main(["exceptions", INV]) == ANSWERED
    o = out(capsys)
    assert "raised (2 chains over 2 processes, 0 swallowing sites):" in o, o
    assert o.count("ambiguous -- the frame holding it returned ok") == 2, o
    assert f"  [in {M1}]" in o and f"  [in {M2}]" in o, o
    assert "alpha raise" in o and "beta raise" in o, o
    assert "dispositions: ambiguous 2" in o, o


def test_the_vary_sets_are_unioned_across_the_members(
        tmp_path, monkeypatch, capsys):
    """One sink, three processes, and everything the key does not look at
    differing: the flags count across the INVOCATION.

    Without the union each set would hold only the printed member's own
    values, and a block absorbing errors from three origins in three
    processes would report no variation at all -- the one reading a reader
    cannot get back by asking again.
    """
    sink31_trace(tmp_path, monkeypatch, origin_fn="read_config",
                 origin_line=12, msg='Missing("port")', run_id=M1,
                 invocation=INV, cargo_args=CARGO)
    sink31_trace(tmp_path, monkeypatch, origin_fn="fetch", origin_line=60,
                 msg='Missing("host")', run_id=M2, invocation=INV,
                 cargo_args=CARGO)
    outside_sink31_trace(tmp_path, monkeypatch, run_id=M3, invocation=INV,
                         cargo_args=CARGO)
    assert cli.main(["exceptions", INV]) == ANSWERED
    o = out(capsys)
    assert o.count("SWALLOWED --") == 1, o
    assert f"  [×3 over 3 processes: first e3 in {M1}, +2]" in o, o
    assert "      origins: 3 distinct (first shown)" in o, o
    assert "      messages: 3 distinct (first shown)" in o, o
    # the printed member has no detail and does have a route, and each
    # parenthetical says so (R-G5)
    assert "      details vary (2 distinct; this one has none)" in o, o
    assert "      routes: 3 distinct (first shown)" in o, o
    assert "dispositions: swallowed 3" in o, o


def test_the_partial_rows_are_a_union_and_not_a_concatenation(
        tmp_path, monkeypatch, capsys):
    """`meta.partial` lists the sites of every unit a process LINKED, so a
    site in a shared crate is repeated in every member that links it
    (ruling R-G10). The block counts PLACES, names the process for a site
    only one member carries, and says how many carry the rest."""
    shared = partial_row("shared", 21)
    swallow_trace(tmp_path, monkeypatch, run_id=M1, invocation=INV,
                  cargo_args=CARGO,
                  partial=[shared, partial_row("u1", 22),
                           partial_row("u2", 23)])
    swallow_trace(tmp_path, monkeypatch, run_id=M2, invocation=INV,
                  cargo_args=CARGO,
                  partial=[shared, partial_row("u3", 24)])
    assert cli.main(["exceptions", INV]) == ANSWERED
    o = out(capsys)
    # four places, not the five rows the two members hold between them
    assert "partial: 4 ?-sites the transformer could not reach" in o, o
    assert f"  shared {SITE_FILE}:21 (macro-arg) in 2 processes" in o, o
    assert f"  u1 {SITE_FILE}:22 (macro-arg) in {M1}" in o, o
    assert f"  u2 {SITE_FILE}:23 (macro-arg) in {M1}" in o, o
    # the cap hides the fourth place, and its continuation names the
    # process that carries it
    assert "u3" not in o, o
    assert f"  ... 1 more (sensorium info {M2})" in o, o


def test_the_partial_rows_and_panics_are_the_union_and_the_sum(
        tmp_path, monkeypatch, capsys):
    """What the recording was not watching qualifies the WHOLE answer, so
    every member's unreachable `?` sites are listed -- each naming its own
    process, because that is where a reader would go to see it -- and the
    panics are summed rather than reported once."""
    swallow_trace(tmp_path, monkeypatch, run_id=M1, invocation=INV,
                  cargo_args=CARGO,
                  partial=[{"file": SITE_FILE, "line": 21,
                            "qualname": "load", "kind": "try",
                            "reason": "macro-arg"}])
    panic_only_trace(tmp_path, monkeypatch, run_id=M2, invocation=INV,
                     cargo_args=CARGO,
                     partial=[{"file": SITE_FILE, "line": 44,
                               "qualname": "save", "kind": "try",
                               "reason": "macro-arg"}])
    assert cli.main(["exceptions", INV]) == ANSWERED
    o = out(capsys)
    assert "partial: 2 ?-sites the transformer could not reach" in o, o
    assert f"  load {SITE_FILE}:21 (macro-arg) in {M1}" in o, o
    assert f"  save {SITE_FILE}:44 (macro-arg) in {M2}" in o, o
    assert "panics: 1 recorded -- this command judges Err flow" in o, o


# -- what this mode refuses -------------------------------------------------
def test_after_is_refused_in_invocation_mode(tmp_path, monkeypatch, capsys):
    """`--after e12` names an event of ONE process, and the ids of 3
    processes are not one sequence. Paging here is `--limit`."""
    inv = three_members(tmp_path, monkeypatch)
    assert cli.main(["exceptions", inv, "--after", "e3"]) == BAD_CALL
    o = out(capsys)
    assert ("--after names an event of one process; this answer spans 3 "
            "processes -- page with --limit") in o, o
    assert "raised (" not in o and "dispositions:" not in o, o


def test_a_member_without_err_flow_refuses_the_whole(
        tmp_path, monkeypatch, capsys):
    """A merged count over a member whose recorder wrote no err-flow record
    would be a number missing an unknown amount of the program. The whole
    answer is refused, naming the member the reader must re-record."""
    caps = {**RUST_CAPABILITIES, "err_flow": False}
    swallow_trace(tmp_path, monkeypatch, run_id=M1, invocation=INV,
                  cargo_args=CARGO)
    quiet_trace(tmp_path, monkeypatch, run_id=M2, invocation=INV,
                cargo_args=CARGO, capabilities=caps,
                recorder="sensorium-rt 0.2.0")
    assert cli.main(["exceptions", INV]) == UNSETTLED
    o = out(capsys)
    assert ("REFUSED: exceptions needs err_flow, which recorder "
            "sensorium-rt 0.2.0 declares it does not produce "
            "(capabilities.err_flow: false); nothing was checked "
            f"(member {M2})") in o, o
    assert "SWALLOWED" not in o and "raised (" not in o, o


def test_a_member_that_is_not_a_rust_trace_refuses_the_whole(
        tmp_path, monkeypatch, capsys):
    """Only the Rust driver writes `meta.invocation`, so this member cannot
    exist -- and what it would be missing is a RULE, not a record, so the
    refusal names the language rather than a capability. The fixture is
    deliberately incoherent (a trace declaring `lang: python` that carries
    an invocation id): the refusal must fire before anything reads it."""
    swallow_trace(tmp_path, monkeypatch, run_id=M1, invocation=INV,
                  cargo_args=CARGO)
    quiet_trace(tmp_path, monkeypatch, run_id=M2, invocation=INV,
                cargo_args=CARGO, lang="python")
    assert cli.main(["exceptions", INV]) == UNSETTLED
    o = out(capsys)
    assert ("REFUSED: exceptions across an invocation is defined for Rust "
            f"traces; member {M2} is python") in o, o
    assert "SWALLOWED" not in o and "raised (" not in o, o


def test_an_ambiguous_prefix_is_refused(tmp_path, monkeypatch, capsys):
    """Two invocations under one prefix: answering for either would be a
    guess about which question was asked."""
    a, b = "20260101-000000-aaaaaa", "20260101-000000-aaaaab"
    swallow_trace(tmp_path, monkeypatch, run_id="20260101-000000-r00001",
                  invocation=a, cargo_args=CARGO)
    swallow_trace(tmp_path, monkeypatch, run_id="20260101-000000-r00002",
                  invocation=b, cargo_args=CARGO)
    assert cli.main(["exceptions", "20260101-000000-aaaaa"]) == BAD_CALL
    err = capsys.readouterr().err
    assert f"is ambiguous: {a}, {b}" in err, err


def test_an_ambiguous_TRACE_prefix_keeps_its_own_answer(
        tmp_path, monkeypatch, capsys):
    """The guard on the fall-through, which nothing else exercises.

    `exceptions_cmd.run` opens the invocation namespace on ONE lookup
    failure -- "this ref names no trace". Every other `TraceLookupError` is
    an answered question and is re-raised: a run prefix that matches two
    trace stems is ambiguous, and re-reading it as an invocation id would
    answer `no trace or invocation matches` to a ref that matches two
    traces, sending the reader to look for a recording rather than to type
    a longer prefix.
    """
    swallow_trace(tmp_path, monkeypatch, run_id=M1)
    swallow_trace(tmp_path, monkeypatch, run_id=M2)
    assert cli.main(["exceptions", "20260101-000000-aaa00"]) == BAD_CALL
    err = capsys.readouterr().err
    assert (f"error: '20260101-000000-aaa00' is ambiguous: {M1}, {M2}"
            in err), err
    assert "no trace or invocation matches" not in err, err


def test_a_ref_that_is_neither_keeps_the_old_error(
        tmp_path, monkeypatch, capsys):
    """A ref naming neither namespace fails the way a bad run ref always
    has -- one line on stderr, exit 2 -- and says both were looked in."""
    swallow_trace(tmp_path, monkeypatch, run_id=M1, invocation=INV,
                  cargo_args=CARGO)
    assert cli.main(["exceptions", "nope"]) == BAD_CALL
    err = capsys.readouterr().err
    assert "error: no trace or invocation matches 'nope'" in err, err


def test_a_run_id_still_wins_over_an_invocation_prefix(
        tmp_path, monkeypatch, capsys):
    """The two namespaces overlap in shape, so the rule is order: a ref that
    resolves to a TRACE is that trace's, and adding this mode cannot change
    an answer a run reference already had."""
    inv = "20260101-000000-aaa0cd"
    swallow_trace(tmp_path, monkeypatch, run_id=M1, invocation=inv,
                  cargo_args=CARGO)
    swallow_trace(tmp_path, monkeypatch, run_id="20260101-000000-bbb002",
                  invocation=inv, cargo_args=CARGO)
    # "20260101-000000-aaa0" prefixes BOTH the invocation id and exactly one
    # trace stem; the trace wins.
    assert cli.main(["exceptions", "20260101-000000-aaa0"]) == ANSWERED
    o = out(capsys)
    assert "raised (1):" in o, o
    assert "invocation " not in o and "processes" not in o, o


# -- R-G12: two files, one site text, one answer ---------------------------
#: The E6⁗ workspace's own collision, and the reason the first measurement's
#: H4 was a STOP: `sandbox` sits at L42 in both of these `bloomery-daemon`
#: test files, and the file-less key merged their chains ACROSS processes --
#: 18 of them booked under `task_exec_read_find_test.rs` while
#: `task_exec_run_test.rs` vanished from the table entirely
#: (`docs/superpowers/acceptance/2026-09-05-sensorium-rung4-entry-grain.md`
#: §4.3/§5.1). The names are the record's, so the pin below is that shape.
READ_FIND = "/w/bloomery-daemon/tests/task_exec_read_find_test.rs"
RUN_TEST = "/w/bloomery-daemon/tests/task_exec_run_test.rs"
M4 = "20260101-000000-aaa004"


def sandbox42_trace(tmp_path, monkeypatch, *, file, **meta):
    """One `Err` absorbed by a `let _ =` at `sandbox L42` in `file`.

    Two members built from two different files print the same site text and
    the same masked verdict: the code object's FILE is the only component of
    the key that tells them apart.

    Event ids: e1 CALL sandbox, e2 CALL read_config, e3 RAISE (the chain's
    origin), e4 RETURN err, e5 HANDLED (the sink at L42), e6 RETURN ok.
    """
    return rust_trace(
        tmp_path, monkeypatch,
        codes=[[file, "sandbox", 40], [FILE, "read_config", 12]],
        frames=[frame(1, 1, 6), frame(2, 2, 4, parent=1, depth=1)],
        events=[
            call(1000, 1, 40),
            call(2000, 2, 12),
            flow(3000, "RAISE", 2, 2, 14,
                 err_flow("exit", "demo::ConfigError", 'Missing("port")', S1,
                          hop=1)),
            ret(4000, 2, 2, "err", 'Err(Missing("port"))'),
            flow(5000, "HANDLED", 1, 1, 42,
                 err_flow("sink_let_underscore", "demo::ConfigError",
                          'Missing("port")', S1, hop=1,
                          terminal="swallowed_candidate")),
            ret(6000, 1, 1, "ok", "None"),
        ],
        sites=[fn_site("sandbox", file, 40),
               fn_site("read_config", SITE_FILE, 12)],
        **meta)


def test_two_members_whose_site_texts_collide_are_two_shapes_naming_their_files(
        tmp_path, monkeypatch, capsys):
    """The record's own miss, made small (ruling R-G12). Two processes sink
    an `Err` at a `sandbox L42` that is not the same place: two shapes, each
    verdict naming its file, and two swallowing sites in the header. Under
    the key the first measurement shipped this printed ONE block of two
    chains, and the second file appeared nowhere in the answer."""
    sandbox42_trace(tmp_path, monkeypatch, file=READ_FIND, run_id=M1,
                    invocation=INV, cargo_args=CARGO)
    sandbox42_trace(tmp_path, monkeypatch, file=RUN_TEST, run_id=M2,
                    invocation=INV, cargo_args=CARGO)
    assert cli.main(["exceptions", INV]) == ANSWERED
    o = out(capsys)
    assert "raised (2 chains over 2 processes, 2 swallowing sites):" in o, o
    assert ("    SWALLOWED -- absorbed by sink_let_underscore at e5 "
            "(sandbox L42 in task_exec_read_find_test.rs) in f1, which "
            f"returned ok  [in {M1}]") in o, o
    assert ("    SWALLOWED -- absorbed by sink_let_underscore at e5 "
            "(sandbox L42 in task_exec_run_test.rs) in f1, which "
            f"returned ok  [in {M2}]") in o, o
    assert "dispositions: swallowed 2" in o, o


def test_the_collision_is_a_property_of_the_answer_not_of_a_member(
        tmp_path, monkeypatch, capsys):
    """No member of this invocation collides with itself: three processes
    sink at a `sandbox L42` -- two of them in the SAME file, one in another
    -- and a fourth sinks somewhere else entirely. The two `sandbox` shapes
    still name their files, because the answer is where they are read
    together; and the shape nothing collides with is printed exactly as it
    is today, with no file in it."""
    sandbox42_trace(tmp_path, monkeypatch, file=READ_FIND, run_id=M1,
                    invocation=INV, cargo_args=CARGO)
    sandbox42_trace(tmp_path, monkeypatch, file=READ_FIND, run_id=M2,
                    invocation=INV, cargo_args=CARGO)
    sandbox42_trace(tmp_path, monkeypatch, file=RUN_TEST, run_id=M3,
                    invocation=INV, cargo_args=CARGO)
    swallow_trace(tmp_path, monkeypatch, run_id=M4, invocation=INV,
                  cargo_args=CARGO)
    assert cli.main(["exceptions", INV]) == ANSWERED
    o = out(capsys)
    assert "raised (4 chains over 4 processes, 3 swallowing sites):" in o, o
    assert ("    SWALLOWED -- absorbed by sink_let_underscore at e5 "
            "(sandbox L42 in task_exec_read_find_test.rs) in f1, which "
            f"returned ok  [×2 over 2 processes: first e3 in {M1}, +1]"
            ) in o, o
    assert ("    SWALLOWED -- absorbed by sink_let_underscore at e5 "
            "(sandbox L42 in task_exec_run_test.rs) in f1, which "
            f"returned ok  [in {M3}]") in o, o
    # the shape with nothing to be told apart from: today's sentence exactly
    assert ("    SWALLOWED -- absorbed by sink_ok at e5 (load L31) in f1, "
            f"which returned ok  [in {M4}]") in o, o
    assert "(load L31 in " not in o, o
    assert "dispositions: swallowed 4" in o, o
