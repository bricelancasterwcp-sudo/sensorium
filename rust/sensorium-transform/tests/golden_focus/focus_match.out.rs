//! A `match` whose statement position is the fn's TAIL: no LINE for the match
//! itself, an entry LINE for the arm that binds, and none for the arm that
//! binds nothing (amendment A3).
@W
pub fn classify(o: Option<i32>) {@G(7)@N(8,o)
    match o {
        Some(n) => {@N(9,n)
            let d = n * 2;@N(10,d)
            println!("{d}");@N(11)
        }
        None => {}
    }
}@U
