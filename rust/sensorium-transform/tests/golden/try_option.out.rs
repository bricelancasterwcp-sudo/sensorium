//! `?` on an `Option`. The wrap is placed all the same -- the transformer
//! cannot see types -- and the runtime ladder's fallback writes nothing for it,
//! which is what design R2 means by "an `Option::None` writes nothing".
@W
fn maybe() -> Option<u8> {@G(7)
    @R(7)Some(1)@E
}

pub fn chained() -> Option<u8> {@G(8)
    let v = @T(9)maybe()@TE?;
    @R(8)Some(v + 1)@E
}@U
