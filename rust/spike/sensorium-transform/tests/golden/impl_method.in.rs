struct Counter {
    n: u32,
}

impl Counter {
    fn new() -> Self {
        Counter { n: 0 }
    }

    fn bump(&mut self) -> u32 {
        self.n += 1;
        self.n
    }
}

struct Holder<T> {
    items: Vec<T>,
}

impl<T> Holder<T> {
    fn push(&mut self, item: T) {
        self.items.push(item);
    }
}

mod deep {
    pub struct Nested;
}

impl self::deep::Nested {
    fn pathed(&self) {}
}
