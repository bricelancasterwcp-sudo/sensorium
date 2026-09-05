//! Nothing to return: an entry guard, and no exit wrap anywhere.
@W
pub fn nothing() {@G(7)
    let _ = @L(8)1@LE;
}

pub fn explicit_unit() -> () {@G(9)
    let _ = @L(10)2@LE;
}

pub fn early_return_unit(c: bool) {@G(11)
    if c {
        return;
    }
    let _ = @L(12)3@LE;
}@U
