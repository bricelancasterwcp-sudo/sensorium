"""Source of tests/fixtures/format2_gen.db, recorded by sensorium 0.2.0
(main @ d59cafc, trace_format 2) with NO focus. Do not edit: the .db is what
0.2.0 wrote for exactly this program, and the tests pin how a format-3
reader describes a format-2 trace (arc-1 wording).

Shape it holds -- the one `format2_async.db` does not isolate: a plain sync
framed function calling a GENERATOR, with the generator's body calling a
helper of its own. In 0.2.0 that produced two distinct old-trace shapes at
once: the generator's own CALL recorded unframed under its caller's frame,
and each helper frame left parentless and tagged with the caller it could
not be hung under.
"""


def clean(s):
    return int(s.strip())


def rows():
    for raw in [" 10", "20 ", " 30 "]:
        yield clean(raw)


def parse(stream):
    return [v for v in stream]


def main():
    values = parse(rows())
    return sum(values)


if __name__ == "__main__":
    print(main())
