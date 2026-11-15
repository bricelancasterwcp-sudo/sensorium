@Wpub unsafe fn raw(p: *const u8) -> u8 {@G(7,p)
    @R(7)*p@E
}

pub async fn later() -> u8 {@D(8)
    1
@DE}

pub const unsafe fn frozen() -> u8 {
    2
}@U
