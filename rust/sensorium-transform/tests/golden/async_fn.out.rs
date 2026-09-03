pub async fn plain() -> u8 {
    1
}

pub async fn public() -> u8 {
    2
}

pub struct S;

impl S {
    pub async fn method(&self) -> u8 {
        3
    }
}

pub fn sync_fn() -> u8 {@G(7)
    @R(7)4@E
}@U
