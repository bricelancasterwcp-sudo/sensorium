pub fn with_inner_attr() -> u8 {
    #![allow(clippy::let_and_return)]
    let v = 1;
    v
}

pub fn two_inner_attrs() { #![allow(unused)] #![allow(dead_code)] let _ = 1; }
