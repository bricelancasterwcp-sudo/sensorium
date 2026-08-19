"""Seeded bug: the loyalty spec says a 1000-point order earns the gold
discount, but the boundary test is `points > 1000`, so an order sitting
exactly on the boundary silently takes the silver path. Nothing is printed
about which tier was applied."""


def gold(total):
    return total * 0.80


def silver(total):
    return total * 0.95


def price(points, total):
    if points > 1000:             # BUG: spec says >= 1000
        return gold(total)
    return silver(total)


def main():
    for pts in (500, 1000, 1500):
        price(pts, 100.0)


if __name__ == "__main__":
    main()
