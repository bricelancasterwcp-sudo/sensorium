pub static MAKE: fn() -> u8 = {
    fn helper() -> u8 {
        1
    }
    helper
};

pub const PICK: fn() -> u8 = {
    fn chosen() -> u8 {
        2
    }
    chosen
};

pub trait Named {
    const DEFAULT: fn() -> u8 = {
        fn inner() -> u8 {
            3
        }
        inner
    };
}
