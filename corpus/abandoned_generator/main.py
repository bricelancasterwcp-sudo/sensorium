"""A paged reader the consumer stops pulling from -- and never finishes.

No planted bug: the fact under test is a SHAPE, not a wrong number. `main`
breaks out of the loop as soon as it has enough rows, so the generator is
dropped while parked at its `yield`. CPython throws GeneratorExit in at that
suspension point, the frame unwinds, and the last page is never produced.

Nothing on stdout distinguishes that from a reader that ran out of pages:
either way the loop ends and the count is printed. `tree` says which it was
and where the generator was standing -- `~ abandoned (dropped while
suspended at L<n>)` -- and claims no return value for a frame that never
returned one.

The pins name the `yield` line, so this file's line layout is part of the
fixture: do not reflow anything above it without re-checking questions.yaml.
"""
ROWS = ["ab", "cd", "ef", "gh", "ij", "kl"]


def pages(rows, size):
    for i in range(0, len(rows), size):
        yield rows[i:i + size]


def main():
    seen = []
    for page in pages(ROWS, 2):
        seen.extend(page)
        if len(seen) >= 3:
            break               # the reader is dropped here, still parked
    print(f"seen: {len(seen)} of {len(ROWS)}")


if __name__ == "__main__":
    main()
