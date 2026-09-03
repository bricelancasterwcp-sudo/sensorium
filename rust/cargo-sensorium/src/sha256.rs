//! SHA-256. The tool hash, the mirror's cache key and the manifest's
//! `source_hashes` are all specified as sha256, and this crate's dependency
//! policy has no hash crate in it (the runtime's `src/sha256.rs` is the same
//! algorithm for the same reason, and neither can depend on the other: the
//! runtime is compiled by a bare `rustc` line with no `--extern` at all).
//!
//! Verified against the NIST FIPS 180-2 vectors below. An implementation that
//! is merely self-consistent passes none of them.

/// The 64 round constants: the first 32 bits of the fractional parts of the
/// cube roots of the first 64 primes.
const ROUND_CONSTANTS: [u32; 64] = [
    0x428a_2f98,
    0x7137_4491,
    0xb5c0_fbcf,
    0xe9b5_dba5,
    0x3956_c25b,
    0x59f1_11f1,
    0x923f_82a4,
    0xab1c_5ed5,
    0xd807_aa98,
    0x1283_5b01,
    0x2431_85be,
    0x550c_7dc3,
    0x72be_5d74,
    0x80de_b1fe,
    0x9bdc_06a7,
    0xc19b_f174,
    0xe49b_69c1,
    0xefbe_4786,
    0x0fc1_9dc6,
    0x240c_a1cc,
    0x2de9_2c6f,
    0x4a74_84aa,
    0x5cb0_a9dc,
    0x76f9_88da,
    0x983e_5152,
    0xa831_c66d,
    0xb003_27c8,
    0xbf59_7fc7,
    0xc6e0_0bf3,
    0xd5a7_9147,
    0x06ca_6351,
    0x1429_2967,
    0x27b7_0a85,
    0x2e1b_2138,
    0x4d2c_6dfc,
    0x5338_0d13,
    0x650a_7354,
    0x766a_0abb,
    0x81c2_c92e,
    0x9272_2c85,
    0xa2bf_e8a1,
    0xa81a_664b,
    0xc24b_8b70,
    0xc76c_51a3,
    0xd192_e819,
    0xd699_0624,
    0xf40e_3585,
    0x106a_a070,
    0x19a4_c116,
    0x1e37_6c08,
    0x2748_774c,
    0x34b0_bcb5,
    0x391c_0cb3,
    0x4ed8_aa4a,
    0x5b9c_ca4f,
    0x682e_6ff3,
    0x748f_82ee,
    0x78a5_636f,
    0x84c8_7814,
    0x8cc7_0208,
    0x90be_fffa,
    0xa450_6ceb,
    0xbef9_a3f7,
    0xc671_78f2,
];

/// The initial state: the first 32 bits of the fractional parts of the square
/// roots of the first eight primes.
const INITIAL_STATE: [u32; 8] = [
    0x6a09_e667,
    0xbb67_ae85,
    0x3c6e_f372,
    0xa54f_f53a,
    0x510e_527f,
    0x9b05_688c,
    0x1f83_d9ab,
    0x5be0_cd19,
];

const BLOCK: usize = 64;

/// Streaming SHA-256. [`Sha256::update`] may be called any number of times with
/// any split; the digest is the same as one call with the concatenation.
pub struct Sha256 {
    state: [u32; 8],
    block: [u8; BLOCK],
    filled: usize,
    /// Message length in BYTES. The padding writes it in bits.
    len: u64,
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
            state: INITIAL_STATE,
            block: [0u8; BLOCK],
            filled: 0,
            len: 0,
        }
    }

    pub fn update(&mut self, data: &[u8]) {
        self.len = self.len.wrapping_add(data.len() as u64);
        self.absorb(data);
    }

    /// The digest. Consumes the hasher: a finished SHA-256 state has had the
    /// padding folded into it and cannot be extended.
    #[must_use]
    pub fn finish(mut self) -> [u8; 32] {
        let bits = self.len.wrapping_mul(8);
        self.absorb(&[0x80]);
        // Pad with zeroes until exactly the 8-byte length field remains.
        while self.filled != BLOCK - 8 {
            self.absorb(&[0x00]);
        }
        self.absorb(&bits.to_be_bytes());
        let mut out = [0u8; 32];
        for (word, chunk) in self.state.iter().zip(out.chunks_exact_mut(4)) {
            chunk.copy_from_slice(&word.to_be_bytes());
        }
        out
    }

    /// Feed bytes through the block buffer WITHOUT counting them, so the
    /// padding cannot change the length it is about to encode.
    fn absorb(&mut self, mut data: &[u8]) {
        if self.filled > 0 {
            let take = (BLOCK - self.filled).min(data.len());
            self.block[self.filled..self.filled + take].copy_from_slice(&data[..take]);
            self.filled += take;
            data = &data[take..];
            if self.filled == BLOCK {
                let full = self.block;
                self.compress(&full);
                self.filled = 0;
            }
        }
        while data.len() >= BLOCK {
            let (head, tail) = data.split_at(BLOCK);
            let mut full = [0u8; BLOCK];
            full.copy_from_slice(head);
            self.compress(&full);
            data = tail;
        }
        if !data.is_empty() {
            self.block[..data.len()].copy_from_slice(data);
            self.filled = data.len();
        }
    }

    fn compress(&mut self, block: &[u8; BLOCK]) {
        let mut w = [0u32; 64];
        for (word, chunk) in w[..16].iter_mut().zip(block.chunks_exact(4)) {
            *word = u32::from_be_bytes([chunk[0], chunk[1], chunk[2], chunk[3]]);
        }
        for i in 16..64 {
            let s0 = w[i - 15].rotate_right(7) ^ w[i - 15].rotate_right(18) ^ (w[i - 15] >> 3);
            let s1 = w[i - 2].rotate_right(17) ^ w[i - 2].rotate_right(19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16]
                .wrapping_add(s0)
                .wrapping_add(w[i - 7])
                .wrapping_add(s1);
        }
        let [mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut h] = self.state;
        for i in 0..64 {
            let s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let choose = (e & f) ^ ((!e) & g);
            let t1 = h
                .wrapping_add(s1)
                .wrapping_add(choose)
                .wrapping_add(ROUND_CONSTANTS[i])
                .wrapping_add(w[i]);
            let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let majority = (a & b) ^ (a & c) ^ (b & c);
            let t2 = s0.wrapping_add(majority);
            h = g;
            g = f;
            f = e;
            e = d.wrapping_add(t1);
            d = c;
            c = b;
            b = a;
            a = t1.wrapping_add(t2);
        }
        for (slot, value) in self.state.iter_mut().zip([a, b, c, d, e, f, g, h]) {
            *slot = slot.wrapping_add(value);
        }
    }
}

/// Lowercase hex of the digest of `data`.
#[must_use]
pub fn hex(data: &[u8]) -> String {
    let mut h = Sha256::new();
    h.update(data);
    to_hex(&h.finish())
}

/// Lowercase hex of a digest.
#[must_use]
pub fn to_hex(digest: &[u8; 32]) -> String {
    use std::fmt::Write as _;
    let mut s = String::with_capacity(64);
    for byte in digest {
        // `write!` to a String cannot fail; the result is discarded on purpose.
        let _ = write!(s, "{byte:02x}");
    }
    s
}

#[cfg(test)]
mod tests {
    use super::*;

    // NIST FIPS 180-2 appendix B vectors. Change one round constant, one
    // rotate, or one byte of the padding and every one of these fails.
    #[test]
    fn the_empty_message_hashes_to_the_nist_vector() {
        assert_eq!(
            hex(b""),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        );
    }

    #[test]
    fn abc_hashes_to_the_nist_vector() {
        assert_eq!(
            hex(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
    }

    #[test]
    fn the_two_block_message_hashes_to_the_nist_vector() {
        assert_eq!(
            hex(b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"),
            "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"
        );
    }

    #[test]
    fn a_million_letter_a_streamed_in_chunks_hashes_to_the_nist_vector() {
        let mut h = Sha256::new();
        let chunk = vec![b'a'; 1000];
        for _ in 0..1000 {
            h.update(&chunk);
        }
        assert_eq!(
            to_hex(&h.finish()),
            "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0"
        );
    }

    #[test]
    fn a_split_update_agrees_with_one_update_at_every_boundary() {
        // Crosses the 64-byte block boundary four times, so a buffer bug that
        // only shows at a partial block is caught here rather than in the field.
        let data: Vec<u8> = (0u16..300).map(|i| (i % 251) as u8).collect();
        let want = hex(&data);
        for split in 0..=data.len() {
            let mut h = Sha256::new();
            h.update(&data[..split]);
            h.update(&data[split..]);
            assert_eq!(to_hex(&h.finish()), want, "split at {split}");
        }
    }

    #[test]
    fn a_message_that_lands_exactly_on_the_padding_boundary_is_padded_correctly() {
        // 55 bytes is the largest message whose padding still fits in one block
        // and 56 is the smallest that needs a second: `date -u` cannot check
        // this, but `sha256sum` can, and these two are its output.
        assert_eq!(
            hex(&[b'x'; 55]),
            "d5e285683cd4efc02d021a5c62014694958901005d6f71e89e0989fac77e4072"
        );
        assert_eq!(
            hex(&[b'x'; 56]),
            "04c26261370ee7541549d16dee320c723e3fd14671e66a099afe0a377c16888e"
        );
    }
}
