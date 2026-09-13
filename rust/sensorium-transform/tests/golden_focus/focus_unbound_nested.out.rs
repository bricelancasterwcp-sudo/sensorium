//! A nested block-like STATEMENT unbinds its own (design §5.2): the `if`
//! inside this block carries `inner` on its own row, and the block's row
//! carries only `outer`. A rule that recursed into nested blocks would list
//! both names on the outer row and say `inner` died twice.
@W
pub fn nested(flag: bool) -> i32 {@G(7)@N(8,flag)
    let mut acc = 0;@N(9,acc)
    {
        let outer = 1;@N(10,outer)
        if flag {
            let inner = 2;@N(11,inner)
            acc += inner;@N(12,acc)
        }@B(13;inner)
        acc += outer;@N(14,acc)
    }@B(15;outer)
    @R(7)acc@E
}@U
