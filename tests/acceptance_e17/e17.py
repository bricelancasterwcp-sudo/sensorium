#!/usr/bin/env python3
"""E17: `sensorium` as an MCP server, measured once.

Launched DETACHED by `e17.sh`, which passes every location in the
environment so that no path on one box is written into a file that travels
with the repository. What this measures is fixed by the record's §1
(`docs/superpowers/acceptance/2026-09-16-sensorium-e17-mcp.md`), which is
byte-locked: seven H rows and a latency reading, each decided by a pure
function in `e17_cells.py` over inputs gathered here and in
`e17_gather.py`.

THE ORDER, AND WHY
------------------
`preflight` and `copy-store` are PRECONDITIONS (`critical=True`): a run
that measured the wrong version, or that had no copy to read, would look
exactly like a run that measured something. Everything after them is a
measurement, and a measurement that fails leaves its cell `dropped` rather
than ending the run with six cells unread. H1 runs first among the
measurements because it is the long one and the part's own cap is 45
minutes PLUS H1's timer; the latency row runs last because it is the only
one nothing gates on.

WHAT IS WRITTEN, AND WHEN
-------------------------
`results-<label>.json` holds every cell, the phases with their seconds, the
versions, the pins and the lens. The `.DONE`/`.FAILED` marker is written
LAST and its content is the part word or the refusal: nothing should be
read out of this directory before that file exists.

Every path in the results file is relative to the work root, and the raw
record's `pins` block is the one place a box path is written down --
`assemble_e17.py` refuses any rendered line that carries `/mnt/` or
`/home/` outside the `E17_DIR=` row.
"""

from __future__ import annotations

import inspect
import json
import os
import re
import secrets
import shutil
import string
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import e17_cells                                                  # noqa: E402
import e17_gather                                                 # noqa: E402
from e17_run import Part, Refused, sha8                           # noqa: E402

#: pytest's own summary LINE -- the whole of it, and the LAST one in the
#: output. The first version of this matched a fragment
#: (`(?:\d+ \w+,?\s*)*\d+ (?:passed|failed|error)`) and read
#: `14 passed, 1 skipped in 0.03s` as `14 passed` alone, so the skip count
#: came back absent and H2's STOP-AS-INSTRUMENT on a skipped conformance
#: run could never fire. The rehearsal did not catch that -- nothing
#: skipped -- and a reading of it did.
SUMMARY = re.compile(r"^.*\b\d+ (?:passed|failed|errors?|skipped)\b.*$",
                     re.M)
COUNT = r"(\d+) {}"

#: H6's minted secret: `sk-e17-` and 33 characters, written to
#: `$E17_DIR/token` at 0600, never printed and never committed. Only its
#: `sha256[:8]` reaches the results file.
TOKEN_PREFIX = "sk-e17-"
TOKEN_BODY = 33
ALPHABET = string.ascii_letters + string.digits

#: The minimum node major the TypeScript recorder needs, and what the
#: preflight reads it out of.
NODE_FLOOR = 24


class PartE17(Part):
    """E17's phases, in the order `main` runs them."""

    # -- preconditions -----------------------------------------------------
    def preflight(self) -> dict:
        """P15: the subject is this branch's command, under this branch's
        venv, with the toolchain the corpus needs on the pinned PATH.

        `which -a sensorium` is RECORDED, as §1 says: the environment
        builds a PATH with the venv's `bin` first, so "no `sensorium` ahead
        of it" is true by construction -- and a reading beside the claim is
        what lets a reader check the construction rather than trust it.
        """
        env = self.env()
        self.transcripts.mkdir(parents=True, exist_ok=True)
        if self.store.exists():
            raise Refused(f"{self.rel(self.store)} already exists: E17 is "
                          "measured ONCE, into a fresh copy")
        traces = self.live / "traces"
        if not sorted(traces.glob("*.db")):
            raise Refused(f"the live store under {traces} holds no `*.db`: "
                          "H3 and the latency row have no subject")
        version = self.installed_version()
        if version != e17_cells.EXPECTED_VERSION:
            raise Refused(f"the venv's sensorium reads {version}, not "
                          f"{e17_cells.EXPECTED_VERSION}: this would measure "
                          "another version of the server")
        checks = {"mcp --help": [self.python, "-m", "sensorium", "mcp",
                                 "--help"],
                  "import mcp": [self.python, "-c", "import mcp"],
                  "which sensorium": ["which", "-a", "sensorium"]}
        if not self.dry:
            checks["cargo"] = ["cargo", "--version"]
            checks["node"] = ["node", "--version"]
        read = {}
        for name, argv in checks.items():
            r = self._run(argv, self.work, env, 120)
            self._keep(f"preflight-{name.replace(' ', '-')}", r)
            read[name] = {"rc": r["rc"], "out": r["out"].strip()[:200]}
            if r["rc"] != 0 and name != "which sensorium":
                raise Refused(f"`{' '.join(argv)}` exited {r['rc']}: "
                              f"{r['out'].strip()[:200]}")
        first = read["which sensorium"]["out"].splitlines()
        if first and not first[0].startswith(str(REPO / ".venv")):
            raise Refused(f"`which -a sensorium` finds {first[0]} ahead of "
                          "the venv's: the subject would be another install")
        if not self.dry:
            self._preflight_toolchain(read)
        return {"sensorium": version, "expected": e17_cells.EXPECTED_VERSION,
                "live_db": len(sorted(traces.glob("*.db"))),
                "dry_run": self.dry, "checks": read,
                "timers": dict(self.timers)}

    def _preflight_toolchain(self, read: dict) -> None:
        """The two recorders H1's corpus needs, and the driver Task 10
        built. Skipped under `E17_DRY`, which runs two Python cases."""
        major = re.search(r"v(\d+)", read["node"]["out"])
        if not major or int(major.group(1)) < NODE_FLOOR:
            raise Refused(f"node reads {read['node']['out']}, under the "
                          f"floor of {NODE_FLOOR}: the TypeScript cases "
                          "would skip and H1 would STOP on them")
        driver = os.environ.get("SENSORIUM_CARGO_SENSORIUM")
        if not driver or not os.access(driver, os.X_OK):
            raise Refused("SENSORIUM_CARGO_SENSORIUM is unset or not "
                          "executable: the Rust cases would skip and H1 "
                          "would STOP on them")
        if not (REPO / "corpus" / "typescript" / "node_modules"
                / "vitest").is_dir():
            raise Refused("corpus/typescript/node_modules holds no vitest "
                          "(`npm ci` was not run): the TypeScript cases "
                          "would skip and H1 would STOP on them")

    def copy_store(self) -> dict:
        """`cp -a` of the live store's traces and its key. The subject of
        H3 and of the latency row is a COPY: the live store is read and
        never written, and the server's own `mcp.jsonl` lands beside the
        copy's traces (P9's rule), not beside anybody's."""
        self.store.mkdir(parents=True)
        r = self._run(["cp", "-a", str(self.live / "traces"),
                       str(self.store / "traces")], self.work, self.env(),
                      self.timers["cell"])
        self._keep("copy-store", r)
        if r["rc"] != 0:
            raise Refused(f"`cp -a` of the live traces exited {r['rc']}: "
                          f"{(r['err'] or r['out']).strip()[:200]}")
        key = self.live / "redaction.key"
        if key.is_file():
            shutil.copy2(key, self.store / "redaction.key")
        n_db = len(sorted((self.store / "traces").glob("*.db")))
        if not n_db:
            raise Refused("the copy holds no `*.db`: there is nothing for "
                          "H3 or the latency row to read")
        return {"n_db": n_db, "key": key.is_file(), "seconds": r["seconds"]}

    # -- the measurements --------------------------------------------------
    def h1_corpus(self) -> dict:
        """§9's H1. The rehearsal runs the corpus TWICE on one case each --
        `silent_swallow` for the tool path and `redact_retrofit` for the
        not-a-tool one -- so the `via_cli` branch is exercised before the
        measurement; the cell reads the SECOND, relaxed."""
        base = [self.python, "corpus/run_corpus.py", "--via", "mcp",
                "--compare-cli", "--json"]
        only = (["silent_swallow", "redact_retrofit"] if self.dry
                else [None])
        docs = []
        for case in only:
            argv = base + (["--only", case] if case else ["--require-driver"])
            r = self._run(argv, REPO, self.env(), self.timers["h1"])
            self._keep(f"h1-{case or 'corpus'}",
                       {**r, "out": r["out"][-20000:]})
            docs.append({"case": case, "rc": r["rc"], "killed": r["killed"],
                         "seconds": r["seconds"], "doc": _json(r["out"])})
        return {"runs": docs, "doc": docs[-1]["doc"]}

    def h2_conformance(self) -> dict:
        """§9's H2: the official SDK's ten tests, read off pytest's own
        summary line. `PYTEST_ADDOPTS` is unset by construction -- `env()`
        builds a complete environment and never carries it in."""
        r = self._run([self.python, "-m", "pytest", "-q",
                       "tests/test_mcp_conformance.py", "-rA"], REPO,
                      self.env(), self.timers["cell"])
        self._keep("h2-conformance", {**r, "out": r["out"][-20000:]})
        return {"rc": r["rc"], **pytest_counts(r["out"])}

    def h7_read(self) -> dict | None:
        """§9's H7: the controller runs one Claude Code session by hand and
        leaves `$E17_DIR/h7/h7.json`. Absent is `dropped` with the reason,
        never a zero and never a STOP."""
        path = self.work / "h7" / "h7.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text("utf-8"))

    def mint(self) -> str:
        """H6's token: `sk-e17-` and 33 characters, at 0600, never printed
        and never committed. The results file carries `sha256[:8]`."""
        token = TOKEN_PREFIX + "".join(secrets.choice(ALPHABET)
                                       for _ in range(TOKEN_BODY))
        path = self.work / "token"
        # 0600 at CREATION, and `O_EXCL` so an existing file is never
        # written into: `write_text` then `chmod` leaves the value
        # world-readable-under-the-umask for the width of two syscalls,
        # which is a window a secret does not need to have.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(token + "\n")
        return token

    # -- what the record's §2 pins -----------------------------------------
    def pins(self) -> list[list[str]]:
        """The pin table, as data, and as a LIST: the results file is
        written with `sort_keys=True` so two runs diff cleanly, and a dict
        here would come back alphabetised -- with the work root, which
        DEFINES `$E17_DIR` for every row under it, sorted to the bottom.

        The work root is the ONE place a box path is written down;
        everything under it is `$E17_DIR/…`, and the two toolchain
        directories are spelled with `~` so no other row can carry a
        `/home/` (R16)."""
        home = str(Path.home())
        rows = {"work root": str(self.work),
                "the copy (the subject)": self._pin(self.store) + "/",
                "H4's store": self._pin(self.work / "h4" / "store") + "/",
                "H5's stores": (self._pin(self.work / "h5" / "store") + "/, "
                                + self._pin(self.work / "h5"
                                            / "store-timeout") + "/"),
                "H6's store": self._pin(self.work / "h6" / "store") + "/",
                "transcripts": self._pin(self.transcripts) + "/",
                "instrument output": self._pin(self.out) + "/",
                "copied out of (never written to)":
                    str(self.live).replace(home, "~"),
                "E17_CARGO_BIN": (self.cargo_bin or "(unset)").replace(
                    home, "~"),
                "E17_NODE_BIN": (self.node_bin or "(unset)").replace(
                    home, "~"),
                "H1's cell timer": f"{self.timers['h1']} s",
                "the part's cap": f"{self.timers['part']} s"}
        return [[name, value] for name, value in rows.items()]

    def _pin(self, path: Path) -> str:
        rel = self.rel(path)
        return f"$E17_DIR/{rel}" if not Path(rel).is_absolute() else rel


def _json(text: str) -> dict | None:
    """The JSON object a `--json` run printed, or `None`. Read from the
    first `{`: a recorder that printed to stdout would otherwise turn a
    complete report into an unparseable one."""
    at = text.find("{")
    if at < 0:
        return None
    try:
        return json.loads(text[at:])
    except ValueError:
        return None


def _count(text: str, word: str) -> int | None:
    found = re.search(COUNT.format(word), text)
    return int(found.group(1)) if found else None


def pytest_counts(out: str) -> dict:
    """`{passed, skipped}` off pytest's last summary line.

    No summary line at all is `None` for both -- pytest did not report, so
    nothing was counted. A summary line with no `skipped` in it IS a zero:
    pytest omits a category that is empty, and that omission is a count it
    took. The two are different facts and H2 reads them differently.
    """
    lines = SUMMARY.findall(out)
    if not lines:
        return {"passed": None, "skipped": None}
    last = lines[-1]
    return {"passed": _count(last, "passed") or 0,
            "skipped": _count(last, "skipped") or 0}


def _cell(fn, gathered, **extra) -> dict:
    """One cell, over what its phase gathered -- or over `None`s when the
    phase did not run. The parameter names are the contract between a
    gather and its cell, and a gather that left a key out leaves a `None`,
    which is a `dropped` and never a pass."""
    names = [n for n in inspect.signature(fn).parameters if n not in extra]
    got = gathered or {}
    return fn(**{name: got.get(name) for name in names}, **extra)


def _versions(part: PartE17) -> dict:
    """What the four versions §1 pins read on the day."""
    out = {"sensorium": part.installed_version(),
           "expected": e17_cells.EXPECTED_VERSION, "mcp": None,
           "claude": None, "python": sys.version.split()[0]}
    sdk = part._run([part.python, "-c", "import importlib.metadata as m; "
                     "print(m.version('mcp'))"], REPO, part.env(), 60)
    out["mcp"] = sdk["out"].strip() if sdk["rc"] == 0 else None
    # `claude` is not on the pinned PATH -- it is the DEPLOY TARGET, not a
    # subject -- so it is found on the launcher's PATH and then run by its
    # absolute path under the pinned environment, which is how its version
    # gets recorded without the pin being widened for it.
    claude = shutil.which("claude")
    if claude:
        r = part._run([claude, "--version"], part.work, part.env(), 60)
        out["claude"] = r["out"].strip()[:120] if r["rc"] == 0 else None
    return out


def main() -> int:
    work = Path(os.environ["E17_WORK"]).resolve()
    out = Path(os.environ["E17_OUT"]).resolve()
    label = os.environ.get("E17_LABEL", "e17")
    dry = os.environ.get("E17_DRY", "0") not in ("", "0")
    live = Path(os.environ.get("E17_LIVE") or (Path.home() / ".sensorium"))
    part = PartE17(work, out, label, dry, live)
    result: dict = {"started": time.time(), "dry_run": dry, "label": label}
    cells: dict = {}
    result["cells"] = cells
    try:
        result["preflight"] = part.phase("preflight", part.preflight,
                                         critical=True)
        copied = part.phase("copy-store", part.copy_store, critical=True)
        result["n_db"] = (copied or {}).get("n_db")
        h1 = part.phase("h1-corpus", part.h1_corpus)
        result["h1"] = {"runs": [{k: v for k, v in run.items() if k != "doc"}
                                 for run in (h1 or {}).get("runs", [])]}
        cells["H1"] = _cell(e17_cells.h1, {"doc": (h1 or {}).get("doc")},
                            dry=dry)
        cells["H2"] = _cell(e17_cells.h2,
                            part.phase("h2-conformance", part.h2_conformance))
        gathered = part.phase("h3-cap", lambda: e17_gather.h3(part))
        result["h3"] = {"run": (gathered or {}).get("_run"),
                        "events": (gathered or {}).get("_events")}
        cells["H3"] = _cell(e17_cells.h3, gathered)
        cells["H4"] = _cell(e17_cells.h4,
                            part.phase("h4-gate",
                                       lambda: e17_gather.h4(part)))
        cells["H5"] = _cell(e17_cells.h5,
                            part.phase("h5-liveness",
                                       lambda: e17_gather.h5(part)))
        token = part.phase("mint", part.mint, critical=True)
        result["token_sha8"] = sha8(token) if token else None
        cells["H6"] = _cell(e17_cells.h6,
                            part.phase("h6-secrecy",
                                       lambda: e17_gather.h6(part, token)))
        cells["H7"] = e17_cells.h7(part.phase("h7-read", part.h7_read))
        cells["latency"] = _cell(
            e17_cells.latency,
            part.phase("latency", lambda: e17_gather.latency(part)))
        result["versions"] = part.phase("versions",
                                        lambda: _versions(part)) or {}
        result["dropped"] = [{"cell": name, "word": "dropped",
                              "reason": cell["read"]}
                             for name, cell in cells.items()
                             if cell["word"] == "dropped"]
        result["part"] = e17_cells.part_word(cells)
        result["status"] = "complete"
    except Refused as exc:
        result["status"], result["refusal"] = "refused", str(exc)
    result["phases"] = part.phases
    result["finished"] = time.time()
    result["seconds"] = round(result["finished"] - result["started"], 1)
    result.setdefault("dropped", [])
    # The tail is guarded too: a marker that is never written leaves the
    # operator polling a directory forever, which is the one outcome worse
    # than a refusal.
    try:
        result["pins"] = part.pins()
        result["lens"] = {"work_root": str(work), "store": str(part.store),
                          "transcripts": str(part.transcripts),
                          "repo": str(REPO), "out": str(out),
                          "live": str(live)}
    except Exception as exc:                            # noqa: BLE001
        result["status"] = "refused"
        result["refusal"] = f"the pin table could not be written: {exc}"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"results-{label}.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str) + "\n")
    ok = result["status"] == "complete"
    # The marker's content is the PART WORD on a completed run and the
    # REFUSAL on any other: a run refused in the tail may already carry a
    # part word, and writing that word into `.FAILED` would name a verdict
    # for a run that did not publish one.
    (out / ("e17.DONE" if ok else "e17.FAILED")).write_text(
        ((result["part"] if ok else result.get("refusal")) or "?") + "\n")
    print(("done: " + result["part"]) if ok
          else ("FAILED: " + result["refusal"]), flush=True)
    for name, cell in cells.items():
        print(f"{name}: {cell['word']} -- {cell['read'][:200]}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
