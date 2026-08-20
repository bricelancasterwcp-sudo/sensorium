"""Seeded bug: the buffer is meant to alert before it can overrun, but the
alert fires at `used > 100` while the buffer's real high-water mark is 99.
The alert never fires, the program exits 0, and the run looks perfectly
healthy from the outside."""


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
