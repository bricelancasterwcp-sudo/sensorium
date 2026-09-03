//! Nothing to return: an entry guard, and no exit wrap anywhere.

pub fn nothing() {@G(7)
    let _ = 1;
}

pub fn explicit_unit() -> () {@G(8)
    let _ = 2;
}

pub fn early_return_unit(c: bool) {@G(9)
    if c {
        return;
    }
    let _ = 3;
}@U
