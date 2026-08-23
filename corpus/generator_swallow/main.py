"""Seeded bug: the reading parser turns an unparseable value into a real 0
instead of dropping it, so the mean is dragged down by readings that were
never measurements at all. The output shows a plausible mean over a
plausible count.

The swallow happens inside a GENERATOR, and that is the point of this case.
Until 0.3.0 a generator opened no frame, so the recorder had no `closed_by`
to read and `exceptions` could not say whether the handler stopped the error
or re-raised it; the registered ground truth was the honest under-claim,
`ambiguous`, with the reason stated. Frames made it decidable: the generator
body has a frame now, that frame closed by returning, and the disposition is
`swallowed` on the same evidence any ordinary function's would be.

The under-claim itself is still contract, and still pinned -- by
`suspended_handler`, where the frame never closes and `ambiguous` remains
the only honest verdict. What must never come back HERE is a verdict
withheld from a frame that plainly returned.
"""
READINGS = ["12", "15", "n/a", "18", "--"]


def parse_all(rows):
    for row in rows:
        try:
            yield int(row)
        except ValueError:
            yield 0           # BUG: an unparseable reading becomes a real 0


def main():
    values = list(parse_all(READINGS))
    print(f"mean: {sum(values) / len(values):.1f} over {len(values)} readings")


if __name__ == "__main__":
    main()
