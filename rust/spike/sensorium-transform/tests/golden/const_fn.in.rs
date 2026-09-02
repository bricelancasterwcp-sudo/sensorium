const fn limit() -> usize {
    16
}

pub const fn doubled(n: usize) -> usize {
    n * 2
}

fn runtime() -> usize {
    limit() + doubled(2)
}
