//! A `?` statement inside a focused fn: the `?` keeps its own err wrap, and the
//! statement's LINE goes after the `;` -- so it runs only on the path where the
//! `?` did NOT propagate, which is exactly what design §3.1 promises.

pub fn read_one(s: &str) -> Result<i32, std::num::ParseIntError> {
    let v = s.parse::<i32>()?;
    let w = v + 1;
    Ok(w)
}
