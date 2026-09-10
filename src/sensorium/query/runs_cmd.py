"""List recorded traces, newest-last."""
from sensorium import paths
from sensorium.exit import ANSWERED, NEGATIVE
from sensorium.query.vocab import exit_brief
from sensorium.store.reader import Trace


def _licence_flag(m: dict) -> str:
    """`(granted)` is not what was granted.

    A bare "granted" here reads as unbounded, which is the same failure this
    listing already refuses for a bare "refocus-of" and a bare "MATCH", one
    step further along: what `refocus` actually grants is a licence over a
    counted, itemised set of points, and `sensorium info` prints them. Say
    how many, and where to read them. A withheld licence keeps its own count
    for the same reason.
    """
    licence = m.get("refocus_licence")
    if not licence:
        return ""
    key = ("refocus_licence_verified" if licence == "granted"
           else "refocus_licence_reasons")
    n = len(m.get(key) or [])
    if not n:
        return f"({licence},points-not-recorded)"
    return f"({licence}:{n},see-info)"


def add_parser(sub) -> None:
    p = sub.add_parser(
        "runs", help="list recorded traces",
        epilog="exit: 0 yes, 1 no, 2 fix the call, 3 change the recording")
    p.set_defaults(func=run)


def _cmd(m: dict) -> str:
    """What was run, as short as it can be said without losing it.

    A Rust trace's `argv[0]` is the absolute path of a test binary under
    `target/`, which is 90 characters of build directory and one useful
    word. The basename of `exe` is that word; `info` prints the full path,
    so nothing is lost -- it moves to the view that has room for it. A trace
    with no `exe` (every Python one) is unchanged: its whole argv.
    """
    argv = m.get("argv") or []
    exe = m.get("exe")
    if not exe:
        return " ".join(argv)
    return " ".join([str(exe).rsplit("/", 1)[-1], *argv[1:]])


def _row(stem: str, trace: Trace) -> str:
    m = trace.meta
    flags = []
    if m.get("incomplete"):
        flags.append("INCOMPLETE")
    if m.get("refocus_of"):
        # The verdict rides with the label, and the licence rides with
        # the verdict. A bare "refocus-of" reads as a pedigree; a bare
        # "verdict:MATCH" reads as a clean bill of health for a rerun
        # whose licence was withheld on every count. Same failure, one
        # level down.
        flags.append(f"refocus-of:{m['refocus_of']}")
        flags.append(f"verdict:{m.get('refocus_verdict', 'UNVERIFIED')}"
                     + _licence_flag(m))
    suffix = f"  [{','.join(flags)}]" if flags else ""
    return (f"{stem}  exit:{exit_brief(m)}  "
            f"events:{sum(trace.counts().values())}  "
            f"{_what(m, trace.lang)}{suffix}")


def _what(m: dict, lang: str) -> str:
    """Which process this row is, in the fewest words that still tell it
    apart from the others in its invocation.

    A Rust invocation's members are distinct BINARIES, so the command is
    what tells them apart. A vitest invocation's members are workers of one
    harness: every one of them has the same
    `node .../vitest/dist/workers/forks.js` command line, and a listing of
    them by argv is a column of identical strings. What differs is the test
    FILE the container ran, which the converter records as `test_file`
    (`typescript/HONESTY.md` section 6) -- so that is what the row shows,
    and `info` keeps the whole command line.

    A reused worker ran several files and carries `test_files`: the count,
    not the list, because a row is one line. A container that ran none -- a
    `globalSetup` in the main process, any `node --test` process -- carries
    neither key and keeps its argv, and that ABSENCE is the recorder's
    statement rather than a gap.

    GATED ON `lang`, NOT ON THE KEY BEING THERE (R27a). `info` has always
    decided its language-specific blocks by `trace.lang` and never by
    sniffing a key, for the reason `vocab` exists: a key name is not a
    recorder's signature, and one recorder reading another's key off a
    trace is the same class of error as reading another's WORD off it. Two
    commands over one trace must not disagree about which recorder wrote
    it, so `runs` reads the language the same way.
    """
    if lang != "typescript":
        return f"cmd: {_cmd(m)}"
    one = m.get("test_file")
    if one:
        return f"file: {one}"
    several = m.get("test_files")
    if several:
        return f"files: {len(several)}"
    return f"cmd: {_cmd(m)}"


def _header(m: dict, lang: str) -> str:
    """The command one invocation's traces all came out of, in the words of
    whatever ran it.

    Without it a `cargo test` run is 30 unrelated-looking rows with 30
    build-directory paths, and a `vitest run` is a dozen rows of the same
    worker script; with it they are one command's processes, and the reader
    can see at a glance that they belong together.

    THE EXIT STATUS IS THE DIFFERENCE BETWEEN THE TWO HEADERS, and it is a
    difference in what was RECORDED, not in taste. The cargo runner shim
    waits for each test binary and nothing waits for cargo, so a Rust
    invocation has no status to print and this line does not claim one. The
    TypeScript driver spawns the harness and waits for the harness, so
    `harness_exit` is a status somebody really did observe -- carried with
    its own basis, and printed with it (`(waited)`), because that is the
    whole of what makes it different from the `unwitnessed` on every member
    row below it.

    Which of the two is decided by `lang` and never by the presence of a
    `harness` key, for the reason `_what` gives at length (R27a).
    """
    if lang == "typescript":
        return (f"invocation {m['invocation']}: {_harness_cmd(m)}"
                + _harness_exit(m))
    args = " ".join(m.get("cargo_args") or [])
    return (f"invocation {m['invocation']}: cargo"
            + (f" {args}" if args else ""))


def _harness_cmd(m: dict) -> str:
    """The command the user typed, verbatim (R26).

    `harness_command` is those tokens before the driver consumed or
    re-issued anything, and it is the only list here that is a command.
    The fallback is for a trace whose converter predates the key, and it
    is what this line printed before: `harness` + `harness_args`, which
    reconstructs a plausible-looking command rather than the real one --
    `node-test --test test/` names no program, and a `--root` the user
    passed is missing from it. Kept because the alternative for such a
    trace is printing nothing at all; corrected by re-recording.
    """
    typed = m.get("harness_command")
    if typed:
        return " ".join(typed)
    return " ".join([m["harness"], *(m.get("harness_args") or [])]).rstrip()


def _harness_exit(m: dict) -> str:
    """How the harness ended, when somebody waited for it -- and nothing at
    all when the record is absent, which is a driver killed before the
    harness returned rather than a harness that ended at 0.

    `status` and `signal` are exclusive: a process killed by a signal chose
    no status, and printing `exit:None` for one is the failure the whole
    exit rule exists to stop (TRACE-FORMAT section 4).
    """
    ending = m.get("harness_exit")
    if not ending:
        return ""
    basis = ending.get("basis", "waited")
    if ending.get("status") is not None:
        return f"  exit:{ending['status']} ({basis})"
    if ending.get("signal") is not None:
        return f"  exit:signal {ending['signal']} ({basis})"
    return ""


def run(args) -> int:
    files = sorted(paths.traces_dir().glob("*.db"), key=lambda p: p.name)
    if not files:
        print("no traces recorded")
        return NEGATIVE
    # Opened in name order, exactly as before, and rendered in one pass
    # afterwards: a group's members are its whole invocation, which can be
    # anywhere in the listing, so the rows have to exist before the first
    # header can be printed.
    rows = [(f.stem, Trace.open(f)) for f in files]
    seen: set = set()
    for stem, trace in rows:
        inv = trace.meta.get("invocation")
        if inv is None:
            print(_row(stem, trace))
            continue
        if inv in seen:
            continue                      # printed under its own header
        seen.add(inv)
        print(_header(trace.meta, trace.lang))
        for stem2, t2 in rows:
            if t2.meta.get("invocation") == inv:
                print("  " + _row(stem2, t2))
    return ANSWERED
