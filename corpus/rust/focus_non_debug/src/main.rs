//! A binding whose type has no `Debug`. The autoref ladder cannot read it,
//! so the delta is `unread` -- the row still says the statement ran and
//! still names `h`, and says out loud that its value was not read.
//!
//! The second half is the honest refusal: `watch` cannot compare a value it
//! does not hold, so `h == 7` is NOTHING WAS CHECKED at that site and exits
//! 3, rather than "not satisfied" -- which would be a claim about a value.

struct Opaque(u8);

fn make() -> u8 {
    let h = Opaque(7);
    h.0
}

fn main() {
    println!("byte: {}", make());
}
