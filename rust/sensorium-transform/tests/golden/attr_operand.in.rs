//! An outer attribute on the tail expression belongs to the STATEMENT, not to
//! the call argument -- `f(#[allow(..)] e)` is not Rust -- so the wrap opens
//! after the attributes and they keep the statement they were written on.

pub fn one_attribute() -> u8 {
    #[allow(unused_variables)]
    1
}

pub fn two_attributes() -> u8 {
    #[allow(unused_variables)]
    #[allow(unused_mut)]
    2
}
