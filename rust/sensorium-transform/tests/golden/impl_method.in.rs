pub struct Counter {
    n: u32,
}

impl Counter {
    pub fn new() -> Counter {
        Counter { n: 0 }
    }

    pub fn bump(&mut self) -> u32 {
        self.n += 1;
        self.n
    }
}

pub struct Holder<T> {
    items: Vec<T>,
}

impl<T> Holder<T> {
    pub fn push(&mut self, item: T) {
        self.items.push(item);
    }
}

pub mod deep {
    pub struct Nested;
}

impl self::deep::Nested {
    pub fn pathed(&self) {}
}
