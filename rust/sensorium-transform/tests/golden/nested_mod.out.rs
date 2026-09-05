@Wpub mod outer {
    pub fn top() {@G(7)}

    pub mod inner {
        pub fn deep() -> u8 {@G(8)
            @R(8)1@E
        }
    }
}

#[cfg(any())]
mod declared;@U
