pub fn outer() -> u8 {
    fn helper() -> u8 {
        1
    }

    struct Local;

    impl Local {
        fn method(&self) -> u8 {
            2
        }
    }

    helper() + Local.method()
}
