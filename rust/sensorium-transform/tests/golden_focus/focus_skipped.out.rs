//! An `async fn` named in the focus is SKIPPED with the reason it already had:
//! the focus is read after `classify`, so a kind the transformer does not
//! instrument can never be focused (design §2.2).
@W
pub async fn spun() {
    let a = 1;
    println!("{a}");
}@U
