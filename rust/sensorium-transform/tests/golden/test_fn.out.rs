@Wpub fn under_test() -> u8 {@G(7)
    @R(7)7@E
}

pub mod tests {
    use super::*;

    pub fn setup() -> u8 {@G(8)
        @R(8)under_test()@E
    }

    #[test]
    fn it_works() {@G(9)
        assert_eq!(setup(), 7);
    }
}@U
