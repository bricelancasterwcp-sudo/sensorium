pub fn with_inner_attr() -> u8 {
    #![allow(clippy::let_and_return)]@G(7)
    let v = 1;
    @R(7)v@E
}

pub fn two_inner_attrs() { #![allow(unused)] #![allow(dead_code)]@G(8) let _ = 1; }@U
