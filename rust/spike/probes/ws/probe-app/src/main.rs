//! The probe's own binary. An integration test spawns it through
//! `env!("CARGO_BIN_EXE_app-bin")`, which is the shape of bloomery's
//! subprocess tests.

fn main() {
    println!("app-bin: {}", probe_app::describe());
    println!("app-bin: work(3) = {}", probe_app::work(3));
}
