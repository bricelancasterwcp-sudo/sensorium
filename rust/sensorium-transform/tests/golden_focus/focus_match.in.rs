//! A `match` whose statement position is the fn's TAIL: no LINE for the match
//! itself, an entry LINE for the arm that binds, and none for the arm that
//! binds nothing (amendment A3).

pub fn classify(o: Option<i32>) {
    match o {
        Some(n) => {
            let d = n * 2;
            println!("{d}");
        }
        None => {}
    }
}
