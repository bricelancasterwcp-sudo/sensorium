pub fn outer() -> u8 {@G(7)
    fn helper() -> u8 {@G(8)
        1
    }

    struct Local;

    impl Local {
        fn method(&self) -> u8 {@G(9)
            2
        }
    }

    helper() + Local.method()
}
