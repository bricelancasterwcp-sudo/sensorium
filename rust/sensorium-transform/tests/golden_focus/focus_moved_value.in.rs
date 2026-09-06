//! Borrow safety by construction (design §3.2): the capture is a shared borrow
//! taken immediately after the write and released at the probe's own `;`, so a
//! value a LATER statement moves is still captured, and moving it is still
//! legal. `Vec::new()` is here because its element type is not known until a
//! later statement -- the autoref ladder must not need it to be.

pub fn move_it() -> usize {
    let v = vec![1, 2];
    let w = v;
    let mut later = Vec::new();
    later.push(w.len());
    let n = later[0];
    n
}
