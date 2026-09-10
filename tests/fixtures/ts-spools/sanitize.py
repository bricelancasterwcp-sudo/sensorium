#!/usr/bin/env python3
"""Turn a spool recorded on somebody's box into a fixture this repository
can commit.

A spool is a faithful record of the machine it was recorded on: the whole
environment, the absolute path of every source file, the node binary, the
working directory. None of that belongs in a test fixture -- it would pin
the fixture to one box, and it would publish an environment. This script is
the ONE transformation applied to a recorded spool, so a reviewer reading
`tests/fixtures/ts-spools/<case>/` can see exactly what was done to it and
re-derive the file from the probe project (`typescript/probes/README.md`)
by running this again.

    python sanitize.py <recorded-root> <src> <dst>

`<src>` is a `.jsonl` spool or a `.json` manifest/tally; `<dst>` is where
the sanitized copy goes. Three rewrites, in this order:

1. Every string, anywhere in any record, that contains `<recorded-root>`
   has it replaced by `/w/probes`. That covers BOOT's `cwd` and `argv`,
   FILE's `abs`, FILE_START's `path` and a manifest's `file` without this
   script having to know which keys those are -- a wire that grows a key
   holding a path is covered the day it grows it.
2. BOOT's `env` becomes `{"PATH": "/usr/bin"}`. The environment is not
   rewritten, it is REPLACED: an allowlist would leak the next variable
   somebody adds. `envHash` is deliberately NOT recomputed -- it is the
   digest of the environment that was actually recorded, and a digest of
   the fixture's fake environment would be a fact about nothing.
3. The directory the node binary was run from -- `dirname(argv[0])` of the
   BOOT record -- becomes `/usr/bin`. It is the one absolute path a spool
   carries that is not under the recorded root.

Then the result is CHECKED: a sanitized file still containing `/home/` or
`/mnt/` is a failure, not a warning, and nothing is written. That check is
the point of the script; the rewrites are how it is usually satisfied.
"""
import json
import posixpath
import sys

FAKE_ROOT = "/w/probes"
FAKE_BIN = "/usr/bin"
FAKE_ENV = {"PATH": "/usr/bin"}
#: Path prefixes that must not survive into a committed fixture. Checked
#: against the finished text, so a path reached by a key this script does
#: not know about still fails the run.
FORBIDDEN = ("/home/", "/mnt/")


def rewrite(value, subs: list[tuple[str, str]]):
    """`value` with every substitution applied to every string inside it."""
    if isinstance(value, str):
        for old, new in subs:
            value = value.replace(old, new)
        return value
    if isinstance(value, list):
        return [rewrite(v, subs) for v in value]
    if isinstance(value, dict):
        return {k: rewrite(v, subs) for k, v in value.items()}
    return value


def node_bin_dir(records: list) -> str | None:
    """The directory the recorded interpreter was run from, or None."""
    for rec in records:
        if isinstance(rec, dict) and rec.get("e") == "BOOT":
            argv = rec.get("argv") or []
            if argv:
                return posixpath.dirname(argv[0])
    return None


def sanitize(records: list, root: str) -> list:
    subs = [(root.rstrip("/"), FAKE_ROOT)]
    bin_dir = node_bin_dir(records)
    if bin_dir:
        subs.append((bin_dir, FAKE_BIN))
    out = []
    for rec in records:
        rec = rewrite(rec, subs)
        if isinstance(rec, dict) and rec.get("e") == "BOOT":
            rec["env"] = dict(FAKE_ENV)
        out.append(rec)
    return out


def render(records: list, lines: bool) -> str:
    if lines:
        return "".join(json.dumps(r, separators=(",", ":")) + "\n"
                       for r in records)
    return json.dumps(records[0], separators=(",", ":")) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: sanitize.py <recorded-root> <src> <dst>",
              file=sys.stderr)
        return 2
    root, src, dst = argv
    lines = src.endswith(".jsonl")
    with open(src, encoding="utf-8") as fh:
        text = fh.read()
    records = ([json.loads(ln) for ln in text.splitlines() if ln.strip()]
               if lines else [json.loads(text)])
    text = render(sanitize(records, root), lines)
    for needle in FORBIDDEN:
        if needle in text:
            where = text.index(needle)
            print(f"error: {needle!r} survives sanitizing at offset {where}: "
                  f"...{text[max(0, where - 40):where + 60]}...",
                  file=sys.stderr)
            return 1
    with open(dst, "w", encoding="utf-8") as fh:
        fh.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
