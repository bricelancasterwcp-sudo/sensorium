"""Seeded bug: when confirmation fails, `submit` retries the whole payment
instead of just the confirmation, so a slow order is charged twice. Both
charges succeed, so the program prints one cheerful line and exits 0."""

LEDGER = []


def charge(order):
    LEDGER.append(order["amount"])
    return {"ok": True, "amount": order["amount"]}


def confirm(receipt, slow):
    return not slow


def submit(order, slow):
    receipt = charge(order)
    if not confirm(receipt, slow):
        receipt = charge(order)   # BUG: retries the charge, not the confirm
    return receipt


def main():
    submit({"id": "A-1", "amount": 40.0}, True)
    print("submitted A-1; ledger total:", sum(LEDGER))


if __name__ == "__main__":
    main()
