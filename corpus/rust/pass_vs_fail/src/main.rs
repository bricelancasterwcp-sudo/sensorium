//! Seeded bug: the same boundary error as `wrong_branch`, but reached from
//! the command line, so the passing input and the failing input are two
//! separate runs of one program. 1001 points behaves; 1000 points, which
//! the spec says must earn gold, silently takes silver.

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
    let points: u32 = std::env::args()
        .nth(1)
        .expect("points")
        .parse()
        .expect("points must be a number");
    println!("billed: {}", price(points, 100.0));
}
