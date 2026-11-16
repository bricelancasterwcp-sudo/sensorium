@Wpub async fn plain() -> u8 {@D(7)
    1
@DE}

pub async fn public() -> u8 {@D(8)
    2
@DE}

pub struct S;

impl S {
    pub async fn method(&self) -> u8 {@D(9,self)
        3
    @DE}
}

pub fn sync_fn() -> u8 {@G(10)
    @R(10)4@E
}@U
