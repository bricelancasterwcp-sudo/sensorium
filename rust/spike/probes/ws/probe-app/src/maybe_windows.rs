//! Never compiled on this box. It exists so the `cfg_attr` above is not a lie.

pub fn maybe_marker() -> &'static str {
    "maybe"
}
