pub unsafe fn raw(p: *const u8) -> u8 {
    *p
}

pub async fn later() -> u8 {
    1
}

pub const unsafe fn frozen() -> u8 {
    2
}
