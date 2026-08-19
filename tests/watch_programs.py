"""The programs `watch`'s tests record, kept apart from the tests.

Same split as `programs.py` and `refocus_programs.py`, for the same reason:
each of these sources exists to produce ONE recorded shape -- an implicit
`del` at the end of an except handler, a LINE event whose only content is an
unbind, interleaved frames -- and the comment explaining that shape belongs
with the source, not in the middle of the test that reads it.
"""

BUFFER = """
def fill(buf, chunk):
    buf.extend(chunk)
    used = len(buf)
    return used

def drain(buf, n):
    del buf[:n]

def main():
    buf = []
    for size, dn in [(40, 0), (30, 10), (25, 20), (34, 30), (0, 69)]:
        fill(buf, [0] * size)
        drain(buf, dn)

if __name__ == "__main__":
    main()
"""

# The `except E as e:` shape, with the one twist that makes the bug visible
# as a WRONG ANSWER rather than as a wrong label: the handler rebinds `e` to
# an int. CPython still emits the implicit `del e` when the handler ends, so
# `e` holds 5 for exactly two recorded sites and is gone at the next three.
# A fold that ignores `unbound` reports three hits instead of one, two of
# them on a name that no longer exists.
HANDLER = """
def stage(n):
    quota = 0
    try:
        raise ValueError("x" * n)
    except ValueError as e:
        e = len(str(e))
        quota = e * 2
    total = quota + n
    return total

def main():
    for n in (1, 5, 2):
        stage(n)

if __name__ == "__main__":
    main()
"""

# `del peak` at the end of each pass. The LINE event that reports it has
# EMPTY deltas and a non-empty `unbound` -- a shape a "skip events with no
# deltas" fold drops on the floor, taking the unbind with it.
LOOPDEL = """
def scan(rows):
    total = 0
    for r in rows:
        peak = r * 3
        total = total + peak
        del peak
    return total

def main():
    scan([1, 2, 3])

if __name__ == "__main__":
    main()
"""

CLIP = """
def note(msg):
    return len(msg)

def main():
    note("x" * 250)
    note("short")

if __name__ == "__main__":
    main()
"""

MIXED = """
def tally(n):
    return n

def main():
    tally(5)
    tally("five")

if __name__ == "__main__":
    main()
"""

# Four sites, every one of which evaluates cleanly. The shape in which a
# name the trace has never heard of produces the STRONGEST verdict this
# command can issue -- so it is the shape the phantom-name warning is tested
# in, not a convenient one where something else was already shouting.
KEEP = """
def keep(n):
    return n

def main():
    for n in (1, 2, 3, 4):
        keep(n)

if __name__ == "__main__":
    main()
"""

# Three activations of one function, nested. Their events INTERLEAVE: the
# innermost frame finishes first, so the frame with the lowest id owns both
# the earliest and the latest site. Anything that walks frames and
# concatenates comes out in the wrong order.
RECURSE = """
def walk(n):
    depth = n
    if n > 0:
        walk(n - 1)
    tail = n + 101
    return tail

def main():
    walk(2)

if __name__ == "__main__":
    main()
"""

# An object and a clipped string sitting beside a plain integer in the same
# frame. `depth > 0 or <name>` short-circuits to a HIT without evaluating the
# second name, which is the only way a site can BE a hit while one of the
# predicate's names has no comparable value -- and therefore the only way to
# see how `watch` renders that name in the state it prints beside the hit.
CARRIER = """
class Box:
    def __init__(self, k):
        self.k = k

def stage(n):
    box = Box(n)
    blob = "x" * 250
    depth = n + 1
    return depth

def main():
    for n in (1, 2):
        stage(n)

if __name__ == "__main__":
    main()
"""
