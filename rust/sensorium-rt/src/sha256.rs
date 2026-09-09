//! SHA-256 -- the repository's only implementation of it.
//!
//! It lives here because the proc header's `env_hash` is specified as one and
//! this crate takes no dependencies (plan decision D1), and because that same
//! constraint makes this crate the only one of the three the other two can
//! both depend on: `sensorium-transform` hashes a focus (`Focus::focus_hash`)
//! and `cargo-sensorium` hashes the tool, the mirror's cache key and each
//! mirrored source. Until 2026-09-08 each of the three carried its own copy,
//! for the reason each copy's header gave: no hash crate is admissible and no
//! two of them could depend on each other. The second half of that was never
//! true of THIS crate -- a leaf with zero dependencies is exactly what the
//! other two can share -- so the two copies are gone and this is what they
//! call. Depending on the runtime crate at BUILD time costs the driver
//! nothing: it already embeds these bytes (`cargo-sensorium/src/rt_src.rs`)
//! and compiles them with its own bare `rustc` line.
//!
//! FIPS 180-4 §6.2. The tests at the bottom are the NIST vectors: an
//! implementation that is merely self-consistent passes none of them.

#[rustfmt::skip]
const K: [u32; 64] = [
    0x428a_2f98, 0x7137_4491, 0xb5c0_fbcf, 0xe9b5_dba5, 0x3956_c25b, 0x59f1_11f1, 0x923f_82a4,
    0xab1c_5ed5, 0xd807_aa98, 0x1283_5b01, 0x2431_85be, 0x550c_7dc3, 0x72be_5d74, 0x80de_b1fe,
    0x9bdc_06a7, 0xc19b_f174, 0xe49b_69c1, 0xefbe_4786, 0x0fc1_9dc6, 0x240c_a1cc, 0x2de9_2c6f,
    0x4a74_84aa, 0x5cb0_a9dc, 0x76f9_88da, 0x983e_5152, 0xa831_c66d, 0xb003_27c8, 0xbf59_7fc7,
    0xc6e0_0bf3, 0xd5a7_9147, 0x06ca_6351, 0x1429_2967, 0x27b7_0a85, 0x2e1b_2138, 0x4d2c_6dfc,
    0x5338_0d13, 0x650a_7354, 0x766a_0abb, 0x81c2_c92e, 0x9272_2c85, 0xa2bf_e8a1, 0xa81a_664b,
    0xc24b_8b70, 0xc76c_51a3, 0xd192_e819, 0xd699_0624, 0xf40e_3585, 0x106a_a070, 0x19a4_c116,
    0x1e37_6c08, 0x2748_774c, 0x34b0_bcb5, 0x391c_0cb3, 0x4ed8_aa4a, 0x5b9c_ca4f, 0x682e_6ff3,
    0x748f_82ee, 0x78a5_636f, 0x84c8_7814, 0x8cc7_0208, 0x90be_fffa, 0xa450_6ceb, 0xbef9_a3f7,
    0xc671_78f2,
];

#[rustfmt::skip]
const H0: [u32; 8] = [
    0x6a09_e667, 0xbb67_ae85, 0x3c6e_f372, 0xa54f_f53a, 0x510e_527f, 0x9b05_688c, 0x1f83_d9ab,
    0x5be0_cd19,
];

/// Streaming SHA-256. `update` may be called any number of times.
pub struct Sha256 {
    state: [u32; 8],
    block: [u8; 64],
    filled: usize,
    total_bytes: u64,
}

impl Default for Sha256 {
    fn default() -> Self {
        Self::new()
    }
}

impl Sha256 {
    #[must_use]
    pub fn new() -> Sha256 {
        Sha256 {
            state: H0,
            block: [0u8; 64],
            filled: 0,
            total_bytes: 0,
        }
    }

    pub fn update(&mut self, mut data: &[u8]) {
        self.total_bytes = self.total_bytes.wrapping_add(data.len() as u64);
        if self.filled > 0 {
            let room = 64 - self.filled;
            let take = room.min(data.len());
            self.block[self.filled..self.filled + take].copy_from_slice(&data[..take]);
            self.filled += take;
            data = &data[take..];
            if self.filled < 64 {
                return;
            }
            let block = self.block;
            compress(&mut self.state, &block);
            self.filled = 0;
        }
        while data.len() >= 64 {
            let mut block = [0u8; 64];
            block.copy_from_slice(&data[..64]);
            compress(&mut self.state, &block);
            data = &data[64..];
        }
        self.block[..data.len()].copy_from_slice(data);
        self.filled = data.len();
    }

    #[must_use]
    pub fn finish(mut self) -> [u8; 32] {
        let bits = self.total_bytes.wrapping_mul(8);
        self.update_raw(&[0x80]);
        while self.filled != 56 {
            self.update_raw(&[0x00]);
        }
        self.update_raw(&bits.to_be_bytes());
        debug_assert_eq!(self.filled, 0);
        let mut out = [0u8; 32];
        for (i, word) in self.state.iter().enumerate() {
            out[i * 4..i * 4 + 4].copy_from_slice(&word.to_be_bytes());
        }
        out
    }

    /// `update` without counting the bytes: padding is not message length.
    fn update_raw(&mut self, data: &[u8]) {
        let before = self.total_bytes;
        self.update(data);
        self.total_bytes = before;
    }
}

fn compress(state: &mut [u32; 8], block: &[u8; 64]) {
    let mut w = [0u32; 64];
    for i in 0..16 {
        w[i] = u32::from_be_bytes([
            block[i * 4],
            block[i * 4 + 1],
            block[i * 4 + 2],
            block[i * 4 + 3],
        ]);
    }
    for i in 16..64 {
        let s0 = w[i - 15].rotate_right(7) ^ w[i - 15].rotate_right(18) ^ (w[i - 15] >> 3);
        let s1 = w[i - 2].rotate_right(17) ^ w[i - 2].rotate_right(19) ^ (w[i - 2] >> 10);
        w[i] = w[i - 16]
            .wrapping_add(s0)
            .wrapping_add(w[i - 7])
            .wrapping_add(s1);
    }
    let [mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut h] = *state;
    for i in 0..64 {
        let big_s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
        let ch = (e & f) ^ ((!e) & g);
        let t1 = h
            .wrapping_add(big_s1)
            .wrapping_add(ch)
            .wrapping_add(K[i])
            .wrapping_add(w[i]);
        let big_s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
        let maj = (a & b) ^ (a & c) ^ (b & c);
        let t2 = big_s0.wrapping_add(maj);
        h = g;
        g = f;
        f = e;
        e = d.wrapping_add(t1);
        d = c;
        c = b;
        b = a;
        a = t1.wrapping_add(t2);
    }
    for (s, v) in state.iter_mut().zip([a, b, c, d, e, f, g, h]) {
        *s = s.wrapping_add(v);
    }
}

/// Lowercase hex of the digest of `data`. The one-call form.
#[must_use]
pub fn hex(data: &[u8]) -> String {
    let mut h = Sha256::new();
    h.update(data);
    to_hex(&h.finish())
}

/// Lowercase hex of a whole digest: all 64 characters.
#[must_use]
pub fn to_hex(digest: &[u8; 32]) -> String {
    hex_prefix(digest, 64)
}

/// Lowercase hex of the digest's first `n` bytes' worth of characters.
#[must_use]
pub fn hex_prefix(digest: &[u8; 32], chars: usize) -> String {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut out = String::with_capacity(chars);
    for byte in digest.iter().take(chars.div_ceil(2)) {
        out.push(HEX[(byte >> 4) as usize] as char);
        out.push(HEX[(byte & 0xf) as usize] as char);
    }
    out.truncate(chars);
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn nist_vector_empty() {
        assert_eq!(
            hex(b""),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        );
    }

    #[test]
    fn nist_vector_abc() {
        assert_eq!(
            hex(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
    }

    #[test]
    fn nist_vector_two_block() {
        assert_eq!(
            hex(b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"),
            "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"
        );
    }

    #[test]
    fn nist_vector_million_a() {
        let mut h = Sha256::new();
        for _ in 0..1000 {
            h.update(&[b'a'; 1000]);
        }
        assert_eq!(
            hex_prefix(&h.finish(), 64),
            "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0"
        );
    }

    #[test]
    fn streaming_in_odd_pieces_matches_one_shot() {
        let msg: Vec<u8> = (0u8..=255).cycle().take(1000).collect();
        let mut h = Sha256::new();
        for chunk in msg.chunks(7) {
            h.update(chunk);
        }
        assert_eq!(hex_prefix(&h.finish(), 64), hex(&msg));
    }

    /// The two padding boundaries, which no NIST vector above lands on.
    ///
    /// 55 bytes is the largest message whose padding still fits in one block
    /// and 56 is the smallest that needs a second. `nist_vector_two_block`
    /// is 56 bytes and so drives `finish`'s `while self.filled != 56` loop
    /// through a full second block; NOTHING here drove it through ZERO
    /// iterations until this test, which is what a 55-byte message does. Kept
    /// from `cargo-sensorium/src/sha256.rs`, deleted when this module became
    /// the repository's only sha256 (2026-09-08); the two digests are
    /// `sha256sum`'s, re-checked against Python's `hashlib` before re-pinning.
    #[test]
    fn a_message_that_lands_exactly_on_the_padding_boundary_is_padded_correctly() {
        assert_eq!(
            hex(&[b'x'; 55]),
            "d5e285683cd4efc02d021a5c62014694958901005d6f71e89e0989fac77e4072"
        );
        assert_eq!(
            hex(&[b'x'; 56]),
            "04c26261370ee7541549d16dee320c723e3fd14671e66a099afe0a377c16888e"
        );
    }

    /// EVERY split point of one message, not one chunking of it.
    ///
    /// `streaming_in_odd_pieces_matches_one_shot` above splits 1000 bytes into
    /// 7-byte pieces -- one arrangement. This crosses the 64-byte block
    /// boundary four times and tries all 301 places the caller could have cut
    /// it, so a buffer bug that only shows at one particular partial block is
    /// caught here rather than in the field. Kept from
    /// `cargo-sensorium/src/sha256.rs`, deleted when this module became the
    /// repository's only sha256 (2026-09-08).
    #[test]
    fn a_split_update_agrees_with_one_update_at_every_boundary() {
        let data: Vec<u8> = (0u16..300).map(|i| (i % 251) as u8).collect();
        let want = hex(&data);
        for split in 0..=data.len() {
            let mut h = Sha256::new();
            h.update(&data[..split]);
            h.update(&data[split..]);
            assert_eq!(to_hex(&h.finish()), want, "split at {split}");
        }
    }

    /// `to_hex` is `hex_prefix(.., 64)`, and `hex` is `to_hex` of a one-shot
    /// digest. A reader of `cargo-sensorium`'s `tool_hash` -- which streams,
    /// then calls `to_hex` -- and of `sensorium-transform`'s `focus_hash` --
    /// which calls `hex` -- has to be able to assume the two agree.
    #[test]
    fn hex_and_to_hex_and_hex_prefix_are_one_rendering() {
        let mut h = Sha256::new();
        h.update(b"abc");
        let digest = h.finish();
        assert_eq!(
            to_hex(&digest),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
        assert_eq!(hex(b"abc"), to_hex(&digest));
        assert_eq!(hex_prefix(&digest, 64), to_hex(&digest));
        assert_eq!(&hex(b"abc")[..16], &hex_prefix(&digest, 16));
    }

    #[test]
    fn hex_prefix_truncates_to_an_odd_length() {
        let digest = [0xabu8; 32];
        assert_eq!(hex_prefix(&digest, 1), "a");
        assert_eq!(hex_prefix(&digest, 5), "ababa");
        assert_eq!(hex_prefix(&digest, 16), "abababababababab");
    }
}
