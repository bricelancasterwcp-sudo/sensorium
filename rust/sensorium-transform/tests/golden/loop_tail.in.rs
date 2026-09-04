//! A `loop` tail is wrapped only when a `break` gives it a value.

pub fn counted() -> u8 {
    let mut n = 0u8;
    loop {
        n += 1;
        if n == 3 {
            break n;
        }
    }
}

pub fn labelled() -> u8 {
    let mut n = 0u8;
    'outer: loop {
        loop {
            n += 1;
            if n == 3 {
                break 'outer n;
            }
        }
    }
}

pub fn inner_break_only() -> u8 {
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
}
