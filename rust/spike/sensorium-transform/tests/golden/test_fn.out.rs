pub fn under_test() -> u8 {@G(7)
    7
}

#[cfg(test)]
mod tests {
    use super::*;

    fn setup() -> u8 {@G(8)
        under_test()
    }

    #[test]
    fn it_works() {@G(9)
        assert_eq!(setup(), 7);
    }
}
