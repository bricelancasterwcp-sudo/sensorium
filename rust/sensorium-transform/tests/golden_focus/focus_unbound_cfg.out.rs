//! A `cfg`'d `let` is neither a delta nor an unbind -- the symmetric rule
//! (design §5.2). `#[cfg(any())]` takes the statement out of the build, the
//! probe after it is declined for that reason
//! (`is_conditionally_compiled`, fix round 1's I2), and no row may claim the
//! name it would have bound. `b`, one line down, is unbound normally, so the
//! case says the filter is narrow rather than that the block went silent.
@W
pub fn conditional() -> i32 {@G(7)@N(8)
    let mut acc = 0;@N(9,acc)
    {
        #[cfg(any())]
        let a = 1;
        let b = 2;@N(10,b)
        acc += b;@N(11,acc)
    }@B(12;b)
    @R(7)acc@E
}@U
