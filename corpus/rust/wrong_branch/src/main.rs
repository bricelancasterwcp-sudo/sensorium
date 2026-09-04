//! Seeded bug: the loyalty spec says a 1000-point order earns the gold
//! discount, but the boundary test is `points > 1000`, so an order sitting
//! exactly on the boundary silently takes the silver path. Nothing is
//! printed about which tier was applied.

fn gold(total: f64) -> f64 {
    total * 0.80
}

fn silver(total: f64) -> f64 {
    total * 0.95
}

fn price(points: u32, total: f64) -> f64 {
    if points > 1000 {
        // BUG: the spec says `>= 1000`.
        return gold(total);
    }
    silver(total)
}

fn main() {
    let mut billed = 0.0;
    for points in [500u32, 1000, 1500] {
        billed += price(points, 100.0);
    }
    println!("billed: {billed}");
}
