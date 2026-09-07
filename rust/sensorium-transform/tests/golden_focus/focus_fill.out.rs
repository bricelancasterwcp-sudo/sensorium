//! One focused function: a parameters LINE, then one LINE per statement.
@W
pub fn fill() {@G(7)@N(8)
    let a = 1;@N(9,a)
    let b = a + 1;@N(10,b)
    println!("{b}");@N(11)
}@U
