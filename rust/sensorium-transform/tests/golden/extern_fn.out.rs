#[no_mangle]
pub extern "C" fn callback(v: i32) -> i32 {
    v + 1
}

extern "C" {
    fn abs(v: i32) -> i32;
}

pub fn ordinary() -> i32 {@G(7)
    @R(7)unsafe { abs(-1) }@E
}@U
