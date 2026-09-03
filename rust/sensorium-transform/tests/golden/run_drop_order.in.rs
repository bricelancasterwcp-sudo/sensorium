//! Run probe: `Drop` order across a wrapped tail and a wrapped `return`.
//! The transformed and the untransformed build must print the same lines.

use std::cell::RefCell;

thread_local! {
    static LOG: RefCell<Vec<String>> = const { RefCell::new(Vec::new()) };
}

fn note(what: &str) {
    LOG.with(|log| log.borrow_mut().push(what.to_owned()));
}

struct Noisy(&'static str);

impl Drop for Noisy {
    fn drop(&mut self) {
        note(self.0);
    }
}

fn through_tail() -> usize {
    let _first = Noisy("drop first-declared");
    let _second = Noisy("drop second-declared");
    note("tail evaluated");
    Noisy("tail temporary").0.len()
}

fn through_return(c: bool) -> usize {
    let _held = Noisy("drop held");
    if c {
        note("return evaluated");
        return Noisy("return temporary").0.len();
    }
    0
}

fn main() {
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
}
