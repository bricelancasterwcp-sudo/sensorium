//! A `for` loop: the pattern's binding enters the body once per iteration, the
//! compound assignment writes the name on its left, and the loop is itself a
//! statement whose own LINE has no delta and unbinds what its pattern bound.

pub fn sum_to_three() -> i32 {
    let mut total = 0;
    for i in 0..3 {
        total += i;
    }
    total
}
