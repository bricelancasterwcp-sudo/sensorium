"""Seeded bug: `lookup` reports a miss by returning None, `display_name`
hands that None straight back without noticing, and the program only dies
two frames later when `.title()` is called on it. The traceback names the
line that crashed, which is not the line that was wrong."""
NAMES = {1: "alice"}


def lookup(uid):
    return NAMES.get(uid)         # BUG: a miss is indistinguishable from a hit


def display_name(uid):
    return lookup(uid)


def main():
    print(display_name(1).title())
    print(display_name(7).title())


if __name__ == "__main__":
    main()
