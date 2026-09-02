fn with_inner_attr() {
    #![allow(clippy::let_and_return)]@G(7)
    let v = 1;
    v
}

fn two_inner_attrs() { #![allow(unused)] #![allow(dead_code)]@G(8) let _ = 1; }
