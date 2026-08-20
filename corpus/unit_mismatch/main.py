"""Seeded bug: item_weight returns grams, but shipping_cost expects kilograms,
so shipping is ~1000x too large. Only the final total is printed."""


def shipping_cost(weight_kg):
    return 4.0 + 2.5 * weight_kg


def item_weight(item):
    return item["grams"]          # BUG: grams, not kg


def order_total(items):
    goods = sum(i["price"] for i in items)
    ship = sum(shipping_cost(item_weight(i)) for i in items)
    return round(goods + ship, 2)


def main():
    items = [{"name": "mug", "price": 12.0, "grams": 400},
             {"name": "kettle", "price": 49.0, "grams": 1800}]
    print("total:", order_total(items))


if __name__ == "__main__":
    main()
