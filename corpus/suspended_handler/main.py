"""The classifier's registered UNDER-CLAIM: a handler whose frame is still
suspended when the recording stops.

`readings` catches the ValueError from an unparseable row and yields a 0 in
its place -- which looks exactly like the swallow in `generator_swallow`,
and in that case the verdict IS `swallowed`, because the generator frame
closed by returning. Here it never closes: the caller pulls one value, parks
the generator in a module-level list and never touches it again, so at the
end of the run the frame is still suspended inside the except block.

Nothing in the trace says what that frame would have done with the
exception, so `exceptions` must answer `ambiguous` and give the reason --
`never closed` -- rather than assume the handler kept it. Reporting
SWALLOWED here would be an over-claim, which is that command's worst
failure mode, and this case exists so such a regression turns something red.

The pins name two `yield` lines, so this file's line layout is part of the
fixture: do not reflow anything above them without re-checking
questions.yaml.
"""
ROWS = ["n/a", "18", "21"]
PENDING = []


def readings(rows):
    for row in rows:
        try:
            yield int(row)
        except ValueError:
            yield 0             # the unparseable reading becomes a real 0


def main():
    stream = readings(ROWS)
    first = next(stream)
    PENDING.append(stream)      # parked here for the rest of the run
    print(f"first: {first}")


if __name__ == "__main__":
    main()
