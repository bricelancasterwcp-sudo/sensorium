//! `?` on an `Option`. The wrap is placed all the same -- the transformer
//! cannot see types -- and the runtime ladder's fallback writes nothing for it,
//! which is what design R2 means by "an `Option::None` writes nothing".

fn maybe() -> Option<u8> {
    Some(1)
}

pub fn chained() -> Option<u8> {
    let v = maybe()?;
    Some(v + 1)
}
