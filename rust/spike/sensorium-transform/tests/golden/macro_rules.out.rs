macro_rules! make_fn {
    ($name:ident) => {
        fn $name() -> u8 {
            5
        }
    };
}

make_fn!(generated);

fn ordinary() -> u8 {@G(7)
    generated()
}
