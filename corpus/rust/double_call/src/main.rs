//! Seeded bug: when confirmation fails, `submit` retries the whole payment
//! instead of just the confirmation, so a slow order is charged twice. Both
//! charges succeed, so the program prints one cheerful line and exits 0.

#[derive(Debug, Clone, Copy)]
struct Order {
    amount: f64,
}

#[derive(Debug)]
struct Receipt {
    amount: f64,
}

fn charge(order: Order, ledger: &mut Vec<f64>) -> Receipt {
    ledger.push(order.amount);
    Receipt {
        amount: order.amount,
    }
}

fn confirm(_receipt: &Receipt, slow: bool) -> bool {
    !slow
}

fn submit(order: Order, slow: bool, ledger: &mut Vec<f64>) -> Receipt {
    let receipt = charge(order, ledger);
    if !confirm(&receipt, slow) {
        // BUG: retries the charge, not the confirmation.
        return charge(order, ledger);
    }
    receipt
}

fn main() {
    let mut ledger = Vec::new();
    submit(Order { amount: 40.0 }, true, &mut ledger);
    println!("submitted A-1; ledger total: {}", ledger.iter().sum::<f64>());
}
