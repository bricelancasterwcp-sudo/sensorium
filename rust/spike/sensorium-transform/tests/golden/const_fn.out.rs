const fn limit() -> usize {
    16
}

pub const fn doubled(n: usize) -> usize {
    n * 2
}

fn runtime() -> usize {@G(7)
    limit() + doubled(2)
}
