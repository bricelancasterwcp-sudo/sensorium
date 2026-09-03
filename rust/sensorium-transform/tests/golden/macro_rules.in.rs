macro_rules! make_fn {
    ($name:ident) => {
        fn $name() -> u8 {
            5
        }
    };
}

make_fn!(generated);

pub fn ordinary() -> u8 {
    generated()
}
