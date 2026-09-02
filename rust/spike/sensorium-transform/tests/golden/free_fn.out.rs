//! A free function at the crate root.

fn add(a: i32, b: i32) -> i32 {@G(7)
    a + b
}

pub fn main_ish() {@G(8)
    let _ = add(1, 2);
}
