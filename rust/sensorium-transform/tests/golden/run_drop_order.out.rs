//! Run probe: `Drop` order across a wrapped tail and a wrapped `return`.
//! The transformed and the untransformed build must print the same lines.
@W
use std::cell::RefCell;

thread_local! {
    static LOG: RefCell<Vec<String>> = const { RefCell::new(Vec::new()) };
}

fn note(what: &str) {@G(7)
    LOG.with(|log| log.borrow_mut().push(what.to_owned()));
}

struct Noisy(&'static str);

impl Drop for Noisy {
    fn drop(&mut self) {@G(8)
        note(self.0);
    }
}

fn through_tail() -> usize {@G(9)
    let _first = Noisy("drop first-declared");
    let _second = Noisy("drop second-declared");
    note("tail evaluated");
    @R(9)Noisy("tail temporary").0.len()@E
}

fn through_return(c: bool) -> usize {@G(10)
    let _held = Noisy("drop held");
    if c {
        note("return evaluated");
        return @R(10)Noisy("return temporary").0.len()@E;
    }
    @R(10)0@E
}

fn main() {@G(11)
    let a = through_tail();
    note("after through_tail");
    let b = through_return(true);
    note("after through_return");
    LOG.with(|log| {
        for line in log.borrow().iter() {
            println!("{line}");
        }
    });
    println!("values {a} {b}");
}@U
