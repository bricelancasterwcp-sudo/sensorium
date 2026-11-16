from examples.shipping import order_total


def test_order_total_for_a_mug_and_kettle():
    items = [
        {"name": "mug", "price": 12.0, "grams": 400},
        {"name": "kettle", "price": 49.0, "grams": 1800},
    ]
    # 0.4 kg mug ships at 5.00, 1.8 kg kettle at 8.50; goods 61.00.
    assert order_total(items) == 74.5
