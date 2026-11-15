//! An `async fn` named in a focus is recorded at call tier. LINE probes are
//! not placed inside it: a suspension has no statement boundary to close.
@W
pub async fn spun() {@Y(7)
    let a = 1;
    println!("{a}");
@DE}@U
