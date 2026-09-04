//! Seeded bug: `lookup` reports a miss by returning None, `display_name`
//! hands that None straight back without noticing, and the program only
//! dies two frames later when `title` unwraps it. The panic names the
//! frame that unwrapped, which is not the frame that was wrong.

static NAMES: [(u32, &str); 1] = [(1, "alice")];

fn lookup(uid: u32) -> Option<&'static str> {
    // BUG: a miss is reported as None, indistinguishable from a hit that
    // legitimately has no name, and nobody downstream checks.
    NAMES.iter().find(|(id, _)| *id == uid).map(|(_, name)| *name)
}

fn display_name(uid: u32) -> Option<&'static str> {
    lookup(uid)
}

fn title(name: Option<&str>) -> String {
    name.expect("display name missing").to_uppercase()
}

fn main() {
    println!("{}", title(display_name(1)));
    println!("{}", title(display_name(7)));
}
