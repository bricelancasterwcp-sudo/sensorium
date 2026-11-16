"""A tiny checkout. examples/test_shipping.py fails on the total.

item_weight returns grams. shipping_cost treats that number as kilograms,
so a 1.8 kg kettle is billed as 1800 kg.
"""


def shipping_cost(weight_kg):
    return 4.0 + 2.5 * weight_kg


def item_weight(item):
    return item["grams"]


def order_total(items):
    goods = sum(i["price"] for i in items)
    ship = sum(shipping_cost(item_weight(i)) for i in items)
    return round(goods + ship, 2)
