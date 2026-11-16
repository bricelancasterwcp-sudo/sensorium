# Shipping example

A pytest that fails because `item_weight` returns grams and `shipping_cost`
reads that number as kilograms.

    sensorium run -- pytest examples/test_shipping.py -q
    sensorium exceptions last
    sensorium flow last --value 1800
    sensorium refocus last --focus examples.shipping:shipping_cost --compact
