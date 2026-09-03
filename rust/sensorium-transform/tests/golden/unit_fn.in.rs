//! Nothing to return: an entry guard, and no exit wrap anywhere.

pub fn nothing() {
    let _ = 1;
}

pub fn explicit_unit() -> () {
    let _ = 2;
}

pub fn early_return_unit(c: bool) {
    if c {
        return;
    }
    let _ = 3;
}
