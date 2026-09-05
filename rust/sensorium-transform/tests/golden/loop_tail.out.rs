//! A `loop` tail is wrapped only when a `break` gives it a value.
@W
pub fn counted() -> u8 {@G(7)
    let mut n = 0u8;
    @R(7)loop {
        n += 1;
        if n == 3 {
            break n;
        }
    }@E
}

pub fn labelled() -> u8 {@G(8)
    let mut n = 0u8;
    @R(8)'outer: loop {
        loop {
            n += 1;
            if n == 3 {
                break 'outer n;
            }
        }
    }@E
}

pub fn inner_break_only() -> u8 {@G(9)
    let mut n = 0u8;
    loop {
        let got = loop {
            n += 1;
            break n;
        };
        if got > 200 {
            std::process::exit(1);
        }
    }
}@U
