async fn plain() -> u8 {
    1
}

pub async fn public() -> u8 {
    2
}

struct S;

impl S {
    async fn method(&self) -> u8 {
        3
    }
}

fn sync_fn() -> u8 {@G(7)
    4
}
