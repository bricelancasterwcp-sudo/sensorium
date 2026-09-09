@Wpub static MAKE: fn() -> u8 = {
    fn helper() -> u8 {@G(7)
        @R(7)1@E
    }
    helper
};

pub const PICK: fn() -> u8 = {
    fn chosen() -> u8 {@G(8)
        @R(8)2@E
    }
    chosen
};

pub trait Named {
    const DEFAULT: fn() -> u8 = {
        fn inner() -> u8 {@G(9)
            @R(9)3@E
        }
        inner
    };
}@U
