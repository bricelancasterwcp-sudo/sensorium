@Wmacro_rules! make_fn {
    ($name:ident) => {
        fn $name() -> u8 {
            5
        }
    };
}

make_fn!(generated);

pub fn ordinary() -> u8 {@G(7)
    @R(7)generated()@E
}@U
