"""Seeded bug: the same boundary error as `wrong_branch`, but reached from
the command line so the passing input and the failing input are two separate
runs of one program. 1001 points behaves; 1000 points, which the spec says
must earn gold, silently takes silver."""
import sys


def gold(total):
    return total * 0.80


def silver(total):
    return total * 0.95


def price(points, total):
    if points > 1000:             # BUG: spec says >= 1000
        return gold(total)
    return silver(total)


def main():
    price(int(sys.argv[1]), 100.0)


if __name__ == "__main__":
    main()
