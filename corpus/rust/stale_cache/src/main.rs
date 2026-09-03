//! Seeded bug: the memo is keyed on the record's sku, but the price depends
//! on its tier. Upgrading the tier leaves the key unchanged, so the cache
//! keeps answering with the pre-upgrade price and the customer is billed
//! the old amount. Nothing in the output mentions the cache.
//!
//! Also a refusal case: the natural question -- "what was `key` at that
//! line?" -- is a per-line question, and this recorder produces no LINE
//! events at all. The pinned truth is that `watch` refuses, and that the
//! same fact is still reachable through the return values it does record.

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
