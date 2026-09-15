//! Not a seeded bug: this case demonstrates rule v1's NAME rule, not a
//! defect. `token`, `api_key`, `auth_headers` (a field of `Headers`,
//! `authorization`) and `secret` are all names the rule fires on; `handle`
//! fires on nothing itself, and holds no plaintext once redaction runs.
//! `main` never prints the token or the length -- printing either is not
//! the leak this rule guards against, but the sibling Python and
//! TypeScript cases stay silent too, and this one matches them.

#[derive(Debug)]
struct Headers {
    authorization: String,
}

fn secret() -> String {
    std::env::var("SENSORIUM_CORPUS_TOKEN").unwrap_or_default()
}

fn handle(token: String) -> usize {
    let api_key = token.clone();
    let auth_headers = Headers {
        authorization: api_key,
    };
    auth_headers.authorization.len()
}

fn main() {
    handle(secret());
}
