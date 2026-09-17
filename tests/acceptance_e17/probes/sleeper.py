#!/usr/bin/env python3
"""H5's subject: a program that is still running when the cancel lands.

Thirty seconds, and ONE child of its own (`sleep 30`), because §9's H5 is a
claim about a process GROUP and not about a process: the server spawns its
child with `start_new_session=True` and kills by `killpg`, so a probe with
no children could not tell a group kill from a leader kill. The child is
`sleep`, not another Python: it inherits the group, it costs nothing, and
it outlives its parent by design if the group is not swept.

Both pids are written down beside this script's own working directory --
`sleeper.pid` and `sleeper-child.pid` -- so a rehearsal that leaves
anything behind can be found by reading two files rather than by grepping
the box's process table. They are evidence for the operator; the cell reads
the pgid off the server's own `sensorium mcp: child <pid> pgid <pgid> tool
record` stderr line, which is the thing H5 says it reads.

Never imported: E17 copies this file next to its `h5` store and records the
copy, so the recording's cwd and this file's are the same directory and
nothing is written into the worktree.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

#: §9's "sleeps 30 s". Long enough that the cancel at t=5 s and the
#: `--run-timeout 3` arm both land while the child is genuinely alive.
SECONDS = 30

HERE = Path.cwd()


def handle() -> int:
    """The one frame worth recording: spawn, note both pids, wait."""
    child = subprocess.Popen(["sleep", str(SECONDS)])
    (HERE / "sleeper.pid").write_text(f"{os.getpid()}\n")
    (HERE / "sleeper-child.pid").write_text(f"{child.pid}\n")
    print(f"sleeper: pid {os.getpid()} child {child.pid}", flush=True)
    time.sleep(SECONDS)
    child.wait()
    return 0


if __name__ == "__main__":
    sys.exit(handle())
