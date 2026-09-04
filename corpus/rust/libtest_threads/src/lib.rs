//! Rust-only case: four tests doing instrumented work, run once with
//! `--test-threads=1` and once with `--test-threads=4`.
//!
//! Nothing here is buggy. The planted truth is about the INSTRUMENT: libtest
//! gives every test its own OS thread, so the wall-clock order of events
//! changes with the thread count while each test's own causal stream does
//! not. A reader that compared the two runs as flat event streams would
//! report a divergence that is not one; a reader that compares them as
//! tasks reports MATCH and says that the tasks carried the verdict.

pub fn normalise(raw: &str) -> String {
    raw.trim().to_lowercase()
}

pub fn tally(items: &[u32]) -> u32 {
    items.iter().copied().sum()
}

pub fn widest(items: &[&str]) -> usize {
    items.iter().map(|s| normalise(s).len()).max().unwrap_or(0)
}

pub fn label(n: u32) -> String {
    format!("row-{}", tally(&[n, 1]))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalises_whitespace() {
        assert_eq!(normalise("  Alice "), "alice");
    }

    #[test]
    fn tallies_a_row() {
        assert_eq!(tally(&[1, 2, 3]), 6);
    }

    #[test]
    fn measures_the_widest() {
        assert_eq!(widest(&["ab", "abcd"]), 4);
    }

    #[test]
    fn labels_a_row() {
        assert_eq!(label(4), "row-5");
    }
}
