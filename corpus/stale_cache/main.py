"""Seeded bug: the memo is keyed on the record's sku, but the price depends
on its tier. Upgrading the tier leaves the key unchanged, so the cache keeps
answering with the pre-upgrade price and the customer is billed the old
amount. Nothing in the output mentions the cache."""

CACHE = {}


def build_key(record):
    return record["sku"]          # BUG: tier is priced but not keyed


def price_of(record):
    key = build_key(record)
    if key in CACHE:
        return CACHE[key]
    price = 10.0 if record["tier"] == "basic" else 25.0
    CACHE[key] = price
    return price


def upgrade(record):
    record["tier"] = "pro"
    return record


def main():
    rec = {"sku": "A1", "tier": "basic"}
    price_of(rec)
    upgrade(rec)
    print("price after upgrade:", price_of(rec))


if __name__ == "__main__":
    main()
