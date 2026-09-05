@Wpub const fn limit() -> usize {
    16
}

pub const fn doubled(n: usize) -> usize {
    n * 2
}

pub fn runtime() -> usize {@G(7)
    @R(7)limit() + doubled(2)@E
}@U
