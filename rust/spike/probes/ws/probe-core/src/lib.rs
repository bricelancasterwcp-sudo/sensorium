//! The probe workspace's leaf library. Exercises the module-tree shapes the
//! wrapper has to walk: a sibling file module, a directory module with its own
//! child, and a `#[path]` module whose file name does not match the mod name.

pub mod sub;

mod helper;

#[path = "renamed_source.rs"]
pub mod renamed;

/// A free fn: the plainest instrumentation site there is.
pub fn add(a: u32, b: u32) -> u32 {
    a + b
}

/// A `const fn`: the transformer must skip it and say so.
pub const fn always_seven() -> u32 {
    7
}

pub struct Counter {
    value: u32,
}

impl Counter {
    pub fn new() -> Counter {
        Counter { value: 0 }
    }

    pub fn bump(&mut self) -> u32 {
        self.value = helper::increment(self.value);
        self.value
    }
}

impl Default for Counter {
    fn default() -> Counter {
        Counter::new()
    }
}

/// An inline module: walked in place, never resolved to a file.
pub mod inline {
    pub fn shout(s: &str) -> String {
        s.to_uppercase()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn add_adds() {
        assert_eq!(add(2, 3), 5);
    }

    #[test]
    fn counter_counts() {
        let mut c = Counter::new();
        c.bump();
        assert_eq!(c.bump(), 2);
    }

    #[test]
    fn modules_resolve() {
        assert_eq!(sub::deep_value(), 42);
        assert_eq!(renamed::renamed_marker(), "renamed");
        assert_eq!(inline::shout("hi"), "HI");
    }
}
