"""E11's JSON, for whichever half `e11.sh` just ran.

(a) reads the `tree` and `info` the shell captured: the frame must be
    reported as suspended at the end of the recording, and the trace must
    NOT carry the INCOMPLETE banner. Both are read out of the text the
    reader printed, because what the reader SAYS is the endpoint -- a
    meta key read straight from sqlite would pass a gate about the reader
    without the reader ever having been asked.

(b) finds the killed container's trace in the store, asks `info` about it,
    and `diff`s it against a complete trace of the same file. `diff` must
    REFUSE at exit 3. The complete counterpart is any trace of the same
    file from a DIFFERENT invocation that is not itself incomplete.

`value` is the number of the half's claims that held, out of its own total.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

from lens import cell, emit, sensorium_bin
from sensorium.store.reader import Trace

#: `tree_cmd` prints `  ~ suspended<where> at end of recording`.
SUSPENDED = ("~ suspended", "at end of recording")
#: THE INCOMPLETE BANNER, AND WHY THIS IS A PATTERN AND NOT A STRING.
#: Four commands print an incomplete banner and they print four different
#: sentences -- `info_cmd` says "recording ended without a finalize pass",
#: `caps` and `exceptions_cmd` say "this recording never finalized",
#: `exceptions_invocation` names the run. What every one of them shares, and
#: what "the INCOMPLETE banner" means, is a line that STARTS with the word.
#: This instrument first held one of the four sentences as a literal and so
#: read `info`'s banner as absent when it was plainly there -- the defect is
#: recorded in the acceptance record's §5, because it was found after E11(b)
#: had already printed a number.
BANNER = re.compile(r"^INCOMPLETE:", re.MULTILINE)
#: `diff`'s "cannot settle it" status.
UNSETTLED = 3


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")


def half_a() -> dict:
    env = os.environ
    tree = read(env["E11A_TREE"])
    info = read(env["E11A_INFO"])
    suspended = all(needle in tree for needle in SUSPENDED)
    complete = BANNER.search(info) is None
    claims = {"tree_says_suspended": suspended, "info_has_no_incomplete_banner": complete}
    return cell(sum(1 for v in claims.values() if v), len(claims),
                half="a: a promise that never settles",
                run=env["E11_RUN"], claims=claims,
                tree_exit=int(env["E11A_TREE_STATUS"]),
                info_exit=int(env["E11A_INFO_STATUS"]),
                banner_lines=[ln.strip() for ln in info.splitlines()
                              if ln.startswith("INCOMPLETE:")],
                suspended_lines=[ln.strip() for ln in tree.splitlines()
                                 if SUSPENDED[0] in ln])


def sensorium(store: str, *args) -> tuple[int, str]:
    proc = subprocess.run([sensorium_bin(), *args], capture_output=True, text=True,
                          env={**os.environ, "SENSORIUM_DIR": store})
    return proc.returncode, proc.stdout + proc.stderr


def half_b() -> dict:
    env = os.environ
    store, inv, want = env["E11_STORE"], env["E11B_INV"], env["E11B_FILE"]
    killed = complete = None
    for db in sorted((Path(store) / "traces").glob("*.db")):
        meta = Trace.open(db).meta
        if meta.get("test_file") != want:
            continue
        if meta.get("invocation") == inv and meta.get("incomplete"):
            killed = (db.stem, meta)
        elif meta.get("invocation") != inv and not meta.get("incomplete"):
            complete = complete or (db.stem, meta)
    dropped = []
    if killed is None:
        dropped.append(f"invocation {inv} left no incomplete trace of {want} "
                       "-- the kill did not land on that container")
    if complete is None:
        dropped.append(f"the store holds no complete trace of {want} from "
                       "another invocation to compare against")
    if killed is None or complete is None:
        return cell(None, 3, dropped, half="b: a container SIGKILLed mid-file",
                    invocation=inv, file=want,
                    kill_log=read(env["E11B_KILLED"]).splitlines(),
                    driver_exit=int(env["E11B_DRIVER_STATUS"]))

    info_code, info_text = sensorium(store, "info", killed[0])
    diff_code, diff_text = sensorium(store, "diff", killed[0], complete[0])
    Path(env["E11B_OUT"], "logs", "e11b-info.txt").write_text(info_text, encoding="utf-8")
    Path(env["E11B_OUT"], "logs", "e11b-diff.txt").write_text(diff_text, encoding="utf-8")
    claims = {
        "trace_incomplete_true": bool(killed[1].get("incomplete")),
        "info_prints_incomplete_banner": BANNER.search(info_text) is not None,
        "diff_refuses_at_exit_3": diff_code == UNSETTLED,
    }
    return cell(sum(1 for v in claims.values() if v), len(claims),
                half="b: a container SIGKILLed mid-file",
                invocation=inv, file=want, killed_run=killed[0],
                complete_run=complete[0], claims=claims,
                diff_exit=diff_code, info_exit=info_code,
                banner_lines=[ln.strip() for ln in info_text.splitlines()
                              if ln.startswith("INCOMPLETE:")],
                diff_verdict=next((ln.strip() for ln in diff_text.splitlines()
                                   if ln.startswith("verdict:")
                                   or "REFUSED" in ln), None),
                kill_log=read(env["E11B_KILLED"]).splitlines(),
                driver_exit=int(env["E11B_DRIVER_STATUS"]))


def main() -> int:
    emit(half_a() if os.environ["E11_MODE"] == "a" else half_b())
    return 0


if __name__ == "__main__":
    sys.exit(main())
