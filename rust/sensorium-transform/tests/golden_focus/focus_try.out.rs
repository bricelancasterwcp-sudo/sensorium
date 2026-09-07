//! A `?` statement inside a focused fn: the `?` keeps its own err wrap, and the
//! statement's LINE goes after the `;` -- so it runs only on the path where the
//! `?` did NOT propagate, which is exactly what design §3.1 promises.
@W
pub fn read_one(s: &str) -> Result<i32, std::num::ParseIntError> {@G(7)@N(8,s)
    let v = @T(11)s.parse::<i32>()@TE?;@N(9,v)
    let w = v + 1;@N(10,w)
    @R(7)Ok(w)@E
}@U
