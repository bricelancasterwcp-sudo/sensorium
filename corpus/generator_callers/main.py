"""Two parentage shapes that have nothing to do with asyncio.

A generator body calling a helper: v1 parented the helper to the CONSUMER's
frame (the last one opened on the thread), which is not who called it. The
generator has a frame of its own now, so the helper is simply its child --
the same relationship an ordinary call would have -- and the fix is visible
as structure rather than as a tag naming a caller with no frame. And a key
function called back from C-level sorted(): its real caller is the frame
that called sorted, which v1 also said -- by the accident of stack
discipline holding for C callbacks. Both are pinned so the fix is seen to be
about the caller frame, not about coroutines.

Seeded bug: the key function ranks by the wrong field, so the longest name
sorts first instead of the highest score.
"""


def parse(s):
    return int(s)


def rows(items):
    for it in items:
        yield parse(it)


def rank(rec):
    return len(rec[0])          # BUG: should be rec[1]


def main():
    total = sum(rows(["10", "20", "30"]))
    best = sorted([("al", 9), ("bea", 3)], key=rank, reverse=True)[0]
    print(f"total: {total}  best: {best[0]}")


if __name__ == "__main__":
    main()
