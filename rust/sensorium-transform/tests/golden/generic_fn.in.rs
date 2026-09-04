use std::fmt::Debug;

pub fn show<T: Debug>(v: &T) -> String {
    format!("{:?}", v)
}

pub fn where_clause<T>(v: T) -> T
where
    T: Clone,
{
    v.clone()
}
