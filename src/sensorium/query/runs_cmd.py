"""List recorded traces, newest-last."""
from sensorium import paths
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


def run(args) -> int:
    files = sorted(paths.traces_dir().glob("*.db"), key=lambda p: p.name)
    if not files:
        print("no traces recorded")
        return 0
    for f in files:
        t = Trace.open(f)
        m = t.meta
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
        print(f"{f.stem}  exit:{m.get('exit_status', '?')}  "
              f"events:{sum(t.counts().values())}  "
              f"cmd: {' '.join(m.get('argv', []))}{suffix}")
    return 0
