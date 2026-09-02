use std::fmt::Debug;

fn show<T: Debug>(v: &T) -> String {
    format!("{:?}", v)
}

fn where_clause<T>(v: T) -> T
where
    T: Clone,
{
    v.clone()
}
