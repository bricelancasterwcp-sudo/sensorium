"""Seeded bug: the except clause swallows bad rows, so the total is wrong
and nothing in the output says rows were dropped."""
ROWS = ["alice,10", "bob,20", "carol,x7", "dan,5", "erin,??"]


def parse_row(row):
    name, amount = row.split(",")
    return name, int(amount)


def load_all(rows):
    out = []
    for row in rows:
        try:
            out.append(parse_row(row))
        except Exception:
            pass
    return out


def main():
    rows = load_all(ROWS)
    print(f"total: {sum(a for _, a in rows)} from {len(rows)} rows")


if __name__ == "__main__":
    main()
