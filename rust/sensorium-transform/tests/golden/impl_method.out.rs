pub struct Counter {
    n: u32,
}

impl Counter {
    pub fn new() -> Counter {@G(7)
        @R(7)Counter { n: 0 }@E
    }

    pub fn bump(&mut self) -> u32 {@G(8)
        self.n += 1;
        @R(8)self.n@E
    }
}

pub struct Holder<T> {
    items: Vec<T>,
}

impl<T> Holder<T> {
    pub fn push(&mut self, item: T) {@G(9)
        self.items.push(item);
    }
}

pub mod deep {
    pub struct Nested;
}

impl self::deep::Nested {
    pub fn pathed(&self) {@G(10)}
}@U
