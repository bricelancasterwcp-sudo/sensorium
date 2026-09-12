//! A plain block statement: its completion row names the `let` the block
//! bound and Rust dropped with it (design §5.2). `x` is alive for two rows
//! and the row that says it stopped being alive is the block's own, spliced
//! past its closing brace -- the row the LINE tier did not write before 0.5.0.
@W
pub fn sums() -> i32 {@G(7)@N(8)
    let mut acc = 0;@N(9,acc)
    {
        let x = 2;@N(10,x)
        acc += x;@N(11,acc)
    }@B(12;x)
    @R(7)acc@E
}@U
