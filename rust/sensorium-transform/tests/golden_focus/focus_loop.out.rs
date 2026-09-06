//! A `for` loop: the pattern's binding enters the body once per iteration, the
//! compound assignment writes the name on its left, and the loop is itself a
//! statement whose own LINE carries nothing.
@W
pub fn sum_to_three() -> i32 {@G(7)@N(8)
    let mut total = 0;@N(9,total)
    for i in 0..3 {@N(10,i)
        total += i;@N(11,total)
    }@N(12)
    @R(7)total@E
}@U
