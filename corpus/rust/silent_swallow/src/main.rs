//! Seeded bug: two of the settings this loader is handed do not parse, and
//! both failures are absorbed on the spot -- one by `.ok()`, one by
//! `let _ =` -- so `load` returns a config built from defaults and the run
//! prints a plausible line. Nothing fails, nothing is logged, and the two
//! settings the operator actually wrote are gone.

#[derive(Debug)]
struct BadSetting(String);

fn parse_port(text: &str) -> Result<u16, BadSetting> {
    text.trim()
        .parse::<u16>()
        .map_err(|_| BadSetting(text.to_string()))
}

fn read_port(text: &str) -> Result<u16, BadSetting> {
    let value = parse_port(text)?;
    Ok(value)
}

#[derive(Debug)]
struct Config {
    port: u16,
    retries: u16,
}

fn load(port_text: &str, retry_text: &str) -> Config {
    // BUG 1: a port that does not parse is turned into None here and then
    // into the default two lines later. The operator's value is discarded
    // without a word.
    let port = read_port(port_text).ok();
    // BUG 2: the retry setting's failure is thrown away outright.
    let _ = read_port(retry_text);
    Config {
        port: port.unwrap_or(8080),
        retries: 3,
    }
}

fn main() {
    let cfg = load("http", "many");
    println!("listening on {} with {} retries", cfg.port, cfg.retries);
}
