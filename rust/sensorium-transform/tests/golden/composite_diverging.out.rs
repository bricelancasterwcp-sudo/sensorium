//! Composites every arm of which diverges. Wrapping one makes the `ret` call
//! itself unreachable, which rustc reports as `unreachable_code`.
@W
extern "C" {
    fn abs(v: i32) -> i32;
}

pub fn both_branches_diverge(c: bool) -> u8 {@G(7)
    if c {
        panic!("then")
    } else {
        unreachable!("else")
    }
}

pub fn every_arm_diverges(c: u8) -> u8 {@G(8)
    match c {
        0 => panic!("zero"),
        1 => todo!(),
        _ => std::process::exit(1),
    }
}

pub fn a_block_whose_tail_diverges() -> u8 {@G(9)
    {
        let _n = 1;
        unimplemented!()
    }
}

pub fn an_unsafe_block_whose_tail_diverges() -> u8 {@G(10)
    unsafe {
        let _ = @L(11)abs(-1)@LE;
        panic!("after the unsafe call")
    }
}

pub fn nested_composites_diverge(c: bool, d: u8) -> u8 {@G(12)
    if c {
        match d {
            0 => panic!("zero"),
            _ => std::process::abort(),
        }
    } else {
        loop {
            std::hint::spin_loop();
        }
    }
}@U
