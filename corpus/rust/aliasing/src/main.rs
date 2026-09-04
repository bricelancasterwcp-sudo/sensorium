//! Seeded bug: derive_sandbox does not copy the config it was handed, it
//! clones the Arc, so the sandbox and production share one Config behind
//! one Mutex and `timeout = 1` writes through to production.
//!
//! Refusal case. The question this bug raises is an IDENTITY question --
//! same object or a copy? -- and this recorder declares it captures no
//! object identity. The pinned truth is that the tool REFUSES rather than
//! answering it from the values it does happen to have.

use std::sync::{Arc, Mutex};

#[derive(Debug, Clone)]
struct Config {
    retries: u32,
    timeout: u32,
}

fn make_default() -> Arc<Mutex<Config>> {
    Arc::new(Mutex::new(Config {
        retries: 3,
        timeout: 30,
    }))
}

fn derive_sandbox(cfg: &Arc<Mutex<Config>>) -> Arc<Mutex<Config>> {
    // BUG: an Arc clone is an alias, not a copy of the config.
    let sandbox = Arc::clone(cfg);
    sandbox.lock().expect("config poisoned").timeout = 1;
    sandbox
}

fn read_timeout(cfg: &Arc<Mutex<Config>>) -> u32 {
    cfg.lock().expect("config poisoned").timeout
}

fn main() {
    let prod = make_default();
    let sand = derive_sandbox(&prod);
    println!(
        "prod timeout: {} sandbox timeout: {}",
        read_timeout(&prod),
        read_timeout(&sand)
    );
}
