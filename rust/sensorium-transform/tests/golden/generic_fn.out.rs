use std::fmt::Debug;

pub fn show<T: Debug>(v: &T) -> String {@G(7)
    @R(7)format!("{:?}", v)@E
}

pub fn where_clause<T>(v: T) -> T
where
    T: Clone,
{@G(8)
    @R(8)v.clone()@E
}@U
