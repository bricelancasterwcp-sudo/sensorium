mod outer {
    pub fn top() {}

    pub mod inner {
        pub fn deep() -> u8 {
            1
        }
    }
}

mod declared;
