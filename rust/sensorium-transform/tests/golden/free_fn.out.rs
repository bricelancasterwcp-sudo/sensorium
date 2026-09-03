//! A free function at the crate root.

pub fn add(a: i32, b: i32) -> i32 {@G(7)
    @R(7)a + b@E
}

pub fn main_ish() {@G(8)
    let _ = add(1, 2);
}@U
