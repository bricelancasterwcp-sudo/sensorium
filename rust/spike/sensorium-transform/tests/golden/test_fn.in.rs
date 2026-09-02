pub fn under_test() -> u8 {
    7
}

#[cfg(test)]
mod tests {
    use super::*;

    fn setup() -> u8 {
        under_test()
    }

    #[test]
    fn it_works() {
        assert_eq!(setup(), 7);
    }
}
