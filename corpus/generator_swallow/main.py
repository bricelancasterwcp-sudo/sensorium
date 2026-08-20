"""Seeded bug: the reading parser turns an unparseable value into a real 0
instead of dropping it, so the mean is dragged down by readings that were
never measurements at all. The output shows a plausible mean over a
plausible count.

The swallow happens inside a GENERATOR, and that is the point of this case.
Generators and coroutines open no frame, so the recorder has no `closed_by`
to read and `exceptions` cannot say whether the handler stopped the error or
re-raised it. The registered ground truth is therefore the honest
under-claim -- `ambiguous`, with the reason stated -- and NOT a disposition.
An `exceptions` that ever reported SWALLOWED here would be over-claiming,
which is that command's worst failure mode; this case exists so that such a
regression turns something red.
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
