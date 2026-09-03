//! The fence: ONE value-carrying arm makes the whole composite ordinary, and it
//! is wrapped. `ret(.., match x { A => panic!(), B => 1 })` is legal and
//! warning-free -- the oracle compiles this file's output to say so.

pub fn one_arm_panics(c: u8) -> u8 {
    match c {
        0 => panic!("zero"),
        _ => 1,
    }
}

pub fn one_branch_exits(c: bool) -> u8 {
    if c {
        std::process::exit(1)
    } else {
        2
    }
}

pub fn an_if_without_else_is_not_the_tail(c: bool) -> u8 {
    if c {
        panic!("then");
    }
    3
}

pub fn a_block_whose_tail_is_a_value() -> u8 {
    {
        let _n = panic_free();
        4
    }
}

fn panic_free() -> u8 {
    5
}

pub fn a_labelled_block_a_break_can_leave_is_wrapped() -> u8 {
    'value: {
        if true {
            break 'value 6;
        }
        panic!("only reached when the break did not fire")
    }
}
