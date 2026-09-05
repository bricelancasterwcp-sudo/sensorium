//! Run probe: `Drop` order and temporary lifetimes across an err wrap. The
//! transformed and the untransformed build must print the same lines.
//!
//! The risk this exists to falsify is specific to the `match` the wrap is made
//! of: a `match` extends the temporaries of its SCRUTINEE to the end of the
//! match, and the wrap puts the operand there. If that ended a temporary's life
//! earlier than the enclosing statement would have, a `Drop` would move -- and
//! `rust/HONESTY.md` §9 promises it does not.

struct Noisy(&'static str);

impl Drop for Noisy {
    fn drop(&mut self) {
        println!("drop {}", self.0);
    }
}

impl Noisy {
    fn value(&self) -> Result<u8, String> {
        println!("value {}", self.0);
        Ok(1)
    }
}

fn side(x: u8) -> u8 {
    println!("side {x}");
    x
}

fn through_try() -> Result<u8, String> {
    let v = Noisy("try").value()?;
    println!("after ?");
    Ok(v)
}

fn through_sink() -> u8 {
    let v = Noisy("sink").value().unwrap_or(side(9));
    println!("after sink");
    v
}

fn through_let() {
    let _ = Noisy("let").value();
    println!("after let _");
}

fn main() {
    println!("{:?}", through_try());
    println!("{}", through_sink());
    through_let();
}
