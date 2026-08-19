"""List recorded traces, newest-last."""
from sensorium import paths
from sensorium.store.reader import Trace


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
            flags.append(f"refocus-of:{m['refocus_of']}")
        suffix = f"  [{','.join(flags)}]" if flags else ""
        print(f"{f.stem}  exit:{m.get('exit_status', '?')}  "
              f"events:{sum(t.counts().values())}  "
              f"cmd: {' '.join(m.get('argv', []))}{suffix}")
    return 0
