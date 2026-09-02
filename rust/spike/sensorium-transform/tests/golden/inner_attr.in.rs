fn with_inner_attr() {
    #![allow(clippy::let_and_return)]
    let v = 1;
    v
}

fn two_inner_attrs() { #![allow(unused)] #![allow(dead_code)] let _ = 1; }
