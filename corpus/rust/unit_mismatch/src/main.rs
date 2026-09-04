//! Seeded bug: item_weight returns grams, but shipping_cost expects
//! kilograms, so shipping is ~1000x too large. Only the final total is
//! printed, and it is merely large, not obviously wrong.

struct Item {
    price: f64,
    grams: f64,
}

fn shipping_cost(weight_kg: f64) -> f64 {
    4.0 + 2.5 * weight_kg
}

fn item_weight(item: &Item) -> f64 {
    // BUG: grams, where every caller means kilograms.
    item.grams
}

fn order_total(items: &[Item]) -> f64 {
    let mut total = 0.0;
    for item in items {
        total += item.price;
        total += shipping_cost(item_weight(item));
    }
    (total * 100.0).round() / 100.0
}

fn main() {
    let items = [
        Item {
            price: 12.0,
            grams: 400.0,
        },
        Item {
            price: 49.0,
            grams: 1800.0,
        },
    ];
    println!("total: {}", order_total(&items));
}
