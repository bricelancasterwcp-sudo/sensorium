//! THROWAWAY SPIKE CODE. Stamps the caller's own optimisation level into the
//! binary, so the lens it prints is what cargo actually compiled rather than
//! what someone assumed.
fn main() {
    println!("cargo::rerun-if-changed=build.rs");
    let profile = std::env::var("PROFILE").unwrap_or_else(|_| "unknown".into());
    // Cargo's historical name for the dev profile's directory is "debug".
    let profile = if profile == "debug" { "dev" } else { &profile };
    println!("cargo::rustc-env=SENSORIUM_CALLER_PROFILE={profile}");
    println!(
        "cargo::rustc-env=SENSORIUM_CALLER_OPT_LEVEL={}",
        std::env::var("OPT_LEVEL").unwrap_or_else(|_| "unknown".into())
    );
}
