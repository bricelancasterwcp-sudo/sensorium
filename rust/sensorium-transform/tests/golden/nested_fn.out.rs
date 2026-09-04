pub fn outer() -> u8 {@G(7)
    fn helper() -> u8 {@G(8)
        @R(8)1@E
    }

    struct Local;

    impl Local {
        fn method(&self) -> u8 {@G(9)
            @R(9)2@E
        }
    }

    @R(7)helper() + Local.method()@E
}@U
