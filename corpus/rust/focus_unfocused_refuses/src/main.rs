//! The `stale_cache` program, recorded WITHOUT a `--focus`, so that the
//! unfocused reading has a case whose name says what it is for.
//!
//! Seeded bug: the memo is keyed on the record's sku, but the price depends
//! on its tier. Upgrading the tier leaves the key unchanged, so the cache
//! keeps answering with the pre-upgrade price.
//!
//! The point pinned here is not the bug. It is that a driver which CAN
//! produce LINE events still declares `line: false` for a run that asked
//! for none, and that `watch` refuses on that declaration instead of
//! answering from an empty record.

use std::collections::HashMap;

#[derive(Debug, Clone)]
struct Record {
    sku: String,
    tier: String,
}

fn build_key(record: &Record) -> String {
    // BUG: the tier is priced but not keyed.
    record.sku.clone()
}

fn price_of(record: &Record, cache: &mut HashMap<String, f64>) -> f64 {
    let key = build_key(record);
    if let Some(hit) = cache.get(&key) {
        return *hit;
    }
    let price = if record.tier == "basic" { 10.0 } else { 25.0 };
    cache.insert(key, price);
    price
}

fn upgrade(record: &mut Record) -> String {
    record.tier = "pro".to_string();
    record.tier.clone()
}

fn main() {
    let mut cache = HashMap::new();
    let mut rec = Record {
        sku: "A1".to_string(),
        tier: "basic".to_string(),
    };
    price_of(&rec, &mut cache);
    upgrade(&mut rec);
    println!("price after upgrade: {}", price_of(&rec, &mut cache));
}
