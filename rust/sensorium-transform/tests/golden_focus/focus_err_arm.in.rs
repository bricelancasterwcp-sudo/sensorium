//! A focused fn whose arms an `Err(..) =>` probe also lands in. Two wraps meet
//! on the same bytes of a bare-expression arm body -- the LINE arm-entry wrap
//! (amendment A1) and the err-flow arm probe's -- and the `Kind`/`seq` order
//! has to nest them, not interleave them. `oracle.rs` compiles the result.

pub fn handled(r: Result<i32, String>) -> i32 {
    match r {
        Ok(v) => v,
        Err(e) => {
            eprintln!("{e}");
            0
        }
    }
}

pub fn bare(r: Result<i32, String>) -> i32 {
    match r {
        Ok(v) => v,
        Err(e) => e.len() as i32,
    }
}
