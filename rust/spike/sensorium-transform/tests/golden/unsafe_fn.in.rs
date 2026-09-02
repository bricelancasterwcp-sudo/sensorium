unsafe fn raw(p: *const u8) -> u8 {
    *p
}

async fn later() -> u8 {
    1
}

const unsafe fn frozen() -> u8 {
    2
}
