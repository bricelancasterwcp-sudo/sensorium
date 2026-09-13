//! A nested block-like STATEMENT unbinds its own (design §5.2): the `if`
//! inside this block carries `inner` on its own row, and the block's row
//! carries only `outer`. A rule that recursed into nested blocks would list
//! both names on the outer row and say `inner` died twice.

pub fn nested(flag: bool) -> i32 {
    let mut acc = 0;
    {
        let outer = 1;
        if flag {
            let inner = 2;
            acc += inner;
        }
        acc += outer;
    }
    acc
}
