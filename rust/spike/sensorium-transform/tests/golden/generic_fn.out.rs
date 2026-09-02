use std::fmt::Debug;

fn show<T: Debug>(v: &T) -> String {@G(7)
    format!("{:?}", v)
}

fn where_clause<T>(v: T) -> T
where
    T: Clone,
{@G(8)
    v.clone()
}
