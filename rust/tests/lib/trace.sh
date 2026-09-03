# Reading what a recording left behind: the spool (process headers, runner
# records) and the traces (meta, tasks, frames).
#
# Everything here reads through `python3`, including the SQLite reads. The
# `sqlite3` command line is not installed everywhere this has to run, and a
# second, rarely-exercised code path for the same question is a liability, not
# a fallback: `python3` ships `sqlite3` in its standard library, and CI has
# `python3` for the JSON anyway.

# <spool> — the runner's witness, as
# `<records> <bad> <roots without a record> <children carrying one> <detail>`.
#
# The RECORDS are counted first, not the process headers. A test binary that
# runs no instrumented code writes no header at all — the `app-bin` unit test
# has no `#[test]` in it and is exactly that case — so a walk that started from
# the headers would report one fewer test binary than cargo ran, and would call
# the missing one absent rather than silent.
#
# A "root" header is one whose `ppid` is not itself a process in this spool:
# cargo started it, so sensorium's runner did, and it must carry a record. A
# child a test spawned itself is not one, must carry none, and reads
# `unwitnessed` (`rust/HONESTY.md` §5).
runner_report() {
  python3 - "$1" <<'PY'
import glob, json, os, sys
spool = sys.argv[1]
procs = {}
for path in sorted(glob.glob(spool + "/*.proc.json")):
    h = json.load(open(path))
    procs[h["pid"]] = h
records = {}
for path in sorted(glob.glob(spool + "/*.runner.json")):
    r = json.load(open(path))
    records[r["pid"]] = r
bad = ["%d exit=%r signal=%r" % (pid, r.get("exit_status"), r.get("signal"))
       for pid, r in sorted(records.items())
       if r.get("exit_status") != 0 or r.get("signal") is not None]
roots = [pid for pid, h in procs.items() if h["ppid"] not in procs]
children = [pid for pid, h in procs.items() if h["ppid"] in procs]
def name(pid):
    return os.path.basename(procs[pid]["exe"]) if pid in procs else "<recorded nothing>"
unwitnessed_root = ["%d(%s)" % (p, name(p)) for p in sorted(roots) if p not in records]
witnessed_child = ["%d(%s)" % (p, name(p)) for p in sorted(children) if p in records]
detail = "records=%s children=%s" % (
    ",".join("%d:%s" % (p, name(p)) for p in sorted(records)),
    ",".join("%d:%s" % (p, name(p)) for p in sorted(children)) or "-",
)
for label, items in (("BAD", bad), ("ROOT_WITHOUT_A_RECORD", unwitnessed_root),
                     ("RUNNER_RECORD_ON_A_CHILD", witnessed_child)):
    if items:
        detail += " %s=%s" % (label, ",".join(items))
print("%d %d %d %d %s"
      % (len(records), len(bad), len(unwitnessed_root), len(witnessed_child), detail))
PY
}

# <traces dir> <exe basename prefix> — the one trace of that executable.
# Empty output and a non-zero exit when there is not exactly one.
trace_for() {
  python3 - "$1" "$2" <<'PY'
import glob, json, os, sqlite3, sys
traces, prefix = sys.argv[1], sys.argv[2]
hits = []
for db in sorted(glob.glob(os.path.join(traces, "*.db"))):
    c = sqlite3.connect("file:%s?mode=ro" % db, uri=True)
    try:
        row = c.execute("select value from meta where key = 'exe'").fetchone()
    finally:
        c.close()
    if row and os.path.basename(json.loads(row[0])).startswith(prefix):
        hits.append(db)
if len(hits) != 1:
    sys.stderr.write("expected one trace whose exe starts with %r, found %d: %s\n"
                     % (prefix, len(hits), [os.path.basename(h) for h in hits]))
    sys.exit(1)
print(hits[0])
PY
}

# <db> <key> — one meta value, as stored (JSON text).
meta_of() {
  python3 - "$1" "$2" <<'PY'
import sqlite3, sys
c = sqlite3.connect("file:%s?mode=ro" % sys.argv[1], uri=True)
row = c.execute("select value from meta where key = ?", (sys.argv[2],)).fetchone()
c.close()
print(row[0] if row else "")
PY
}

# <db> — the tasks table, one `<thread id>\t<name>` per row.
tasks_of() {
  python3 - "$1" <<'PY'
import sqlite3, sys
c = sqlite3.connect("file:%s?mode=ro" % sys.argv[1], uri=True)
for tid, name in c.execute("select thread_id, name from tasks order by thread_id"):
    print("%s\t%s" % (tid, name if name is not None else "<unnamed>"))
c.close()
PY
}

# <db> <qualname> — `<closed_by> <exc type> <depth> <outcome> <value>` for every
# frame of that function, one per line. The whole panic and return-value story
# in one shape, so a check reads it with `grep` rather than a second query.
frames_of() {
  python3 - "$1" "$2" <<'PY'
import json, sqlite3, sys
c = sqlite3.connect("file:%s?mode=ro" % sys.argv[1], uri=True)
rows = c.execute(
    """select f.id, f.closed_by, f.unwind_exc, f.depth
         from frames f join code_objects co on co.id = f.code_id
        where co.qualname = ? order by f.id""", (sys.argv[2],)).fetchall()
for fid, closed_by, exc, depth in rows:
    kind, msg = "-", "-"
    if exc:
        e = json.loads(exc)
        kind, msg = e.get("type", "-"), e.get("msg", "-")
    outcome, value = "-", "-"
    row = c.execute(
        "select payload from events where frame_id = ? and kind = 'RETURN'", (fid,)).fetchone()
    if row and row[0]:
        p = json.loads(row[0])
        outcome = p.get("outcome", "-")
        v = p.get("value")
        if isinstance(v, dict):
            value = v.get("v", "<%s>" % v.get("k"))
    print("%s %s %s %s %s %s" % (closed_by or "<open>", kind, depth, outcome, value, msg))
c.close()
PY
}

# <db> <thread id> — how many events that thread recorded.
events_on_thread() {
  python3 - "$1" "$2" <<'PY'
import sqlite3, sys
c = sqlite3.connect("file:%s?mode=ro" % sys.argv[1], uri=True)
print(c.execute("select count(*) from events where thread_id = ?", (int(sys.argv[2]),)).fetchone()[0])
c.close()
PY
}

# <manifests dir> — the crate names that were handed to the wrapper.
wrapped_crates() {
  python3 - "$1" <<'PY'
import glob, json, sys
names = sorted({json.load(open(f))["crate_name"] for f in glob.glob(sys.argv[1] + "/*.json")})
print(" ".join(names))
PY
}

# <manifests dir> <mirror dir> — `<bad> <checked> <detail>`.
#
# The invariant behind unit identity (`rust/HONESTY.md` §7): the crate root in
# each unit's mirror must name THAT unit. One shared mirror cannot hold two
# units of the same crate root, and the loser reads as a healthy build — which
# is how rung 1 met this (findings §5.22). `checked` is asserted greater than
# zero because a walk that examined nothing reports no bad units either
# (findings §5.29).
unit_identity() {
  python3 - "$1" "$2" <<'PY'
import glob, json, os, sys
mdir, mirror = sys.argv[1], sys.argv[2]
bad, checked = [], 0
for f in sorted(glob.glob(mdir + "/*.json")):
    m = json.load(open(f))
    for rel in sorted(m["files"]):
        path = os.path.join(mirror, m["unit"], rel)
        if not os.path.exists(path):
            bad.append("%s %s: no mirror file" % (m["crate_name"], rel))
            continue
        text = open(path).read()
        if 'Unit::new("' in text:
            checked += 1
            if 'Unit::new("%s")' % m["unit"] not in text:
                got = text.split('Unit::new("')[1].split('"')[0]
                bad.append("%s/%s %s carries %s" % (m["crate_name"], m["crate_type"], rel, got))
print("%d %d %s" % (len(bad), checked, "; ".join(bad[:3]) or "-"))
PY
}

# <spool> <manifests dir> — CALLs into a probe_core lib site from a process
# whose executable rustdoc has already deleted: `<calls> <detail>`.
doctest_calls() {
  python3 - "$1" "$2" <<'PY'
import glob, json, os, struct, sys
spool, mdir = sys.argv[1], sys.argv[2]
want = set()
for f in glob.glob(mdir + "/*.json"):
    m = json.load(open(f))
    if m["crate_name"] == "probe_core" and m["crate_type"] == "lib":
        want.add(m["unit"])
total, who = 0, []
for ph in sorted(glob.glob(spool + "/*.proc.json")):
    h = json.load(open(ph))
    ids = {int(k) for k, v in h.get("units", {}).items() if v in want}
    if not ids:
        continue
    calls = 0
    for sp in glob.glob("%s/%s.*.spool" % (spool, h["pid"])):
        b = open(sp, "rb").read()
        if b[:4] != b"SNSR":
            continue
        off = 11 + struct.unpack_from("<H", b, 9)[0]
        while off + 24 <= len(b):
            _seq, _ts, site, kind, _o, _r = struct.unpack_from("<QQIBBH", b, off)
            off += 24
            if kind == 1 and (site >> 24) in ids:
                calls += 1
    if calls:
        who.append("%s(%d calls, exe=%s)" % (h["pid"], calls, h["exe"]))
        total += calls
if total == 0:
    seen = []
    for ph in sorted(glob.glob(spool + "/*.proc.json")):
        h = json.load(open(ph))
        seen.append("%s:%s:units=%s:spools=%d" % (
            h["pid"], os.path.basename(h["exe"]), h.get("units"),
            len(glob.glob("%s/%s.*.spool" % (spool, h["pid"])))))
    allm = sorted((json.load(open(f))["crate_name"], json.load(open(f))["crate_type"],
                   json.load(open(f))["unit"]) for f in glob.glob(mdir + "/*.json"))
    who.append("want=%s seen=[%s] manifests=%s" % (sorted(want), "; ".join(seen) or "nothing", allm))
print("%d %s" % (total, " ".join(who)))
PY
}

# <spool> — the process whose executable rustdoc deleted, and whether it was
# runner-waited: `<n dead-exe processes> <n of those with a runner record> <detail>`.
doctest_processes() {
  python3 - "$1" <<'PY'
import glob, json, os, sys
spool = sys.argv[1]
dead, waited, detail = 0, 0, []
for ph in sorted(glob.glob(spool + "/*.proc.json")):
    h = json.load(open(ph))
    exe = h["exe"]
    if "/rustdoctest" not in exe:
        continue
    dead += 1
    has_runner = os.path.exists(os.path.join(spool, "%d.runner.json" % h["pid"]))
    status = None
    if has_runner:
        waited += 1
        status = json.load(open(os.path.join(spool, "%d.runner.json" % h["pid"])))["exit_status"]
    detail.append("%d exe=%s exists=%s runner=%s exit=%r"
                  % (h["pid"], exe, os.path.exists(exe), has_runner, status))
print("%d %d %s" % (dead, waited, "; ".join(detail) or "-"))
PY
}
