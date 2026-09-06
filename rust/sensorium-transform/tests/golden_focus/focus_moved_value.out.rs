//! Borrow safety by construction (design §3.2): the capture is a shared borrow
//! taken immediately after the write and released at the probe's own `;`, so a
//! value a LATER statement moves is still captured, and moving it is still
//! legal. `Vec::new()` is here because its element type is not known until a
//! later statement -- the autoref ladder must not need it to be.
@W
pub fn move_it() -> usize {@G(7)@N(8)
    let v = vec![1, 2];@N(9,v)
    let w = v;@N(10,w)
    let mut later = Vec::new();@N(11,later)
    later.push(w.len());@N(12)
    let n = later[0];@N(13,n)
    @R(7)n@E
}@U
