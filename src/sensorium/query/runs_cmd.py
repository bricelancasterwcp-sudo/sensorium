"""List recorded traces, newest-last."""
from sensorium import paths
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
    p = sub.add_parser("runs", help="list recorded traces")
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
            f"cmd: {_cmd(m)}{suffix}")


def _header(m: dict) -> str:
    """The cargo command one invocation's traces all came out of.

    Without it a `cargo test` run is 30 unrelated-looking rows with 30
    build-directory paths; with it they are one command's processes, and the
    reader can see at a glance that they belong together. The trace does not
    record cargo's own exit status, so this line does not claim one.
    """
    args = " ".join(m.get("cargo_args") or [])
    return (f"invocation {m['invocation']}: cargo"
            + (f" {args}" if args else ""))


def run(args) -> int:
    files = sorted(paths.traces_dir().glob("*.db"), key=lambda p: p.name)
    if not files:
        print("no traces recorded")
        return 0
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
        print(_header(trace.meta))
        for stem2, t2 in rows:
            if t2.meta.get("invocation") == inv:
                print("  " + _row(stem2, t2))
    return 0
