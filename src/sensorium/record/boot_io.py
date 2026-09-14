"""Stream interception: what the recorder puts in front of `sys.stdout`,
`sys.stderr` and `sys.stdin` while the target runs.

Split out of `boot.py` at that file's 800-line ceiling, along the seam the
material has. These two proxies are the only part of the recorder the TARGET
touches directly -- by writing to a stream, or by reading one -- and they
know nothing about resolving a target, installing monitoring, the audit hook
or the writer's lifecycle, which is the rest of `boot`. Both are re-exported
there, so a caller (or a test) that reaches for `boot._Tee` still finds it,
and finds the same class object.

Both are delegating proxies rather than stream subclasses, and both
normalise through `capture.plain_str` before they test or store anything.
The reason is stated at each and is one reason: a `str` subclass with live
dunders would otherwise run the program's own code from inside the
instrument, at the program's own line.
"""
from sensorium.record import capture


# -- stream interception ---------------------------------------------------
class _Tee:
    """Pass writes through to the real stream and into the trace.

    A delegating proxy rather than a TextIOBase subclass: programs reach for
    `sys.stdout.buffer`, `.fileno()`, `.encoding` and `.isatty()`, and a
    subclass would answer those for itself instead of for the stream the
    program actually has. Output written straight to the file descriptor
    (`os.write(1, ...)`, a child process) bypasses this and is not captured;
    the trace holds what went through the Python stream object.
    """

    def __init__(self, orig, name, writer) -> None:
        self._orig = orig
        self._name = name
        self._writer = writer

    def write(self, s):
        n = self._orig.write(s)
        # Normalise BEFORE testing or storing. `s` is whatever the program
        # passed to `print`, which may be a `str` subclass with live dunders:
        # `if s:` ran its `__bool__`/`__len__` from inside the program's own
        # call, the instance was then held in the writer's buffer until the
        # next flush, and bound into sqlite from there. An exception out of
        # any of that is the recorder killing the program it observes, at the
        # program's own line. Found by the sweep for item 7, not reported.
        text = capture.plain_str(s)
        if text:
            self._writer.add_output(self._writer.last_event_id, self._name,
                                    text)
        return n

    def writelines(self, lines) -> None:
        for line in lines:
            self.write(line)

    def flush(self) -> None:
        self._orig.flush()

    def __getattr__(self, name):
        return getattr(self._orig, name)


_MARK_ON_CALL = ("read", "readline", "readlines", "readinto", "read1")
_MARK_ON_ACCESS = ("buffer", "detach")


class _StdinProxy:
    """Mark the run as having consumed stdin, so replay knows it is not pure.

    Only reads that go through the Python object are seen. An interactive
    `input()` on a real tty is served by the readline fast path against fd 0
    and does not touch this proxy; piped and redirected stdin, which is what
    a recorded run almost always has, does.

    Everything else about the stream must behave exactly as it would without
    the recorder -- an instrument that changes the program it observes is
    worse than no instrument.
    """

    def __init__(self, orig) -> None:
        self._orig = orig
        self.consumed = False

    def _marking(self, fn):
        def inner(*a, **k):
            self.consumed = True
            return fn(*a, **k)
        return inner

    def __getattr__(self, name):
        attr = getattr(self._orig, name)     # raises first: absent is not use
        # `name` is whatever the program passed to `getattr`, and CPython
        # hands a `str` SUBCLASS straight through -- so the two membership
        # tests below would run its `__eq__` and `__hash__`, from inside the
        # program's own `getattr(sys.stdin, ...)` call, where without the
        # recorder no comparison happens at all. Measured; found by the
        # general-case audit for item 7.
        name = capture.plain_str(name)
        if name in _MARK_ON_CALL:
            return self._marking(attr)
        if name in _MARK_ON_ACCESS:
            # Handing out the binary layer forfeits the ability to see the
            # read, so the access itself counts. Over-marking is the safe
            # direction: it costs a refused refocus, where a missed mark
            # costs a MATCH verdict on a run that was never repeatable.
            self.consumed = True
        return attr

    # Implicit special-method lookup goes to the type, not to __getattr__, so
    # every dunder a program might use on a stream is spelled out here. A
    # missing one is not a missed mark -- it is a TypeError in a program that
    # ran fine without the recorder.
    def __iter__(self):
        self.consumed = True
        return self               # a file is its own iterator; so is this

    def __next__(self):
        self.consumed = True
        return next(self._orig)

    def __enter__(self):
        self._orig.__enter__()
        return self               # never the raw stream: reads must stay seen

    def __exit__(self, *exc_info):
        return self._orig.__exit__(*exc_info)

    def __repr__(self) -> str:
        return repr(self._orig)   # the instrument does not announce itself
