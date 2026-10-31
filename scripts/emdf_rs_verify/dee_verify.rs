//! Verify the reverse-engineered DEE emdf_protection against a genuine DEE stream, using this
//! crate's own E-AC-3 framer (`eac3::parse_frames`), EMDF locator (`find_dolby_emdf`) and field
//! walk (`emdf::field_offsets`). Inputs via env: DEE_ORACLE=<dir with out.ec3 and protection/, i.e. sample/>.
use hmac::{Hmac, Mac};
use sha2::Sha256;

const KEY_HEX_CONST: &str = "2c16951c38232060d8975aa6cbdc54813142dc269dcc5d437697206c93871de4";

fn dee_key() -> Vec<u8> {
    (0..32)
        .map(|i| u8::from_str_radix(&KEY_HEX_CONST[2 * i..2 * i + 2], 16).unwrap() ^ 0x7a)
        .collect()
}

fn hmac(key: &[u8], parts: &[&[u8]]) -> [u8; 32] {
    let mut m = <Hmac<Sha256>>::new_from_slice(key).unwrap();
    for p in parts {
        m.update(p);
    }
    m.finalize().into_bytes().into()
}

fn bit(buf: &[u8], p: usize) -> u8 {
    (buf[p >> 3] >> (7 - (p & 7))) & 1
}

fn read(buf: &[u8], p: usize, n: usize) -> u32 {
    (0..n).fold(0, |v, i| (v << 1) | bit(buf, p + i) as u32)
}

/// Copy bits [from, from+n) of `buf` into a fresh MSB-first byte buffer.
fn extract(buf: &[u8], from: usize, n: usize) -> Vec<u8> {
    let mut out = vec![0u8; n.div_ceil(8)];
    for i in 0..n {
        out[i >> 3] |= bit(buf, from + i) << (7 - (i & 7));
    }
    out
}

fn clear(buf: &mut [u8], from: usize, n: usize) {
    for p in from..from + n {
        buf[p >> 3] &= !(1 << (7 - (p & 7)));
    }
}

#[test]
fn dee_protection_matches_emdf_rs_parse() {
    let dir = std::path::PathBuf::from(std::env::var("DEE_ORACLE").expect("set DEE_ORACLE"));
    let data = std::fs::read(dir.join("out.ec3")).unwrap();
    let frames = crate::eac3::parse_frames(&data);
    let key = dee_key();
    println!("key = {}", key.iter().map(|b| format!("{b:02x}")).collect::<String>());
    println!("{} frames parsed by eac3::parse_frames", frames.len());

    let mut ok = 0;
    for (i, f) in frames.iter().take(8).enumerate() {
        let frame = &data[f.offset..f.offset + f.size];
        let (sync, off) = crate::find_dolby_emdf(frame).expect("find_dolby_emdf");
        let a = sync; // all offsets below are frame-relative bits
        let emdf_len = read(frame, a + 16, 16) as usize;
        let body_bits = off.protection_start + (off.prim_bits + off.sec_bits) as usize - 32;
        let key_id = read(frame, a + off.key_id_bit, 3);
        let p = a + off.protection_start;
        let stored_prim = read(frame, p, 32);
        let stored_sec = read(frame, p + 32, 8);

        // DEE's second hash input: the EMDF body (after sync+length) with key_id/prim/sec zeroed.
        let mut body = extract(frame, a + 32, emdf_len * 8);
        clear(&mut body, off.key_id_bit - 32, 3);
        clear(&mut body, off.protection_start - 32, 40);
        let captured_body = std::fs::read(dir.join(format!("protection/upd_{:02}.bin", 3 + 5 * i))).unwrap();
        let body_eq = body == captured_body;

        // DEE's first hash input: the pre-mux frame payload, captured live from DEE.
        let covered = std::fs::read(dir.join(format!("protection/upd_{:02}.bin", 2 + 5 * i))).unwrap();
        let d1 = hmac(&key, &[&covered, &body]);
        let prim = u32::from_be_bytes(d1[..4].try_into().unwrap());
        let sec = hmac(&key, &[&d1])[0] as u32;

        // The crate's current stand-in construction, fed the real key, for contrast.
        let nb = off.protection_start - 32;
        let stand_in = super::dolby_keyed_mac(&key, key_id as u8, &extract(frame, a + 32, nb), nb, 32);

        let pass = body_eq && prim == stored_prim && sec == stored_sec;
        ok += pass as usize;
        println!(
            "frame {i}: emdf@bit {a} len={emdf_len}B body_bits={body_bits} key_id={key_id} \
             prot={}+{} | body==captured:{body_eq} | prim stored={stored_prim:08x} hmac={prim:08x} \
             | sec stored={stored_sec:02x} hmac={sec:02x} | stand-in={stand_in:08x} | {}",
            off.prim_bits,
            off.sec_bits,
            if pass { "MATCH" } else { "FAIL" }
        );
    }
    assert_eq!(ok, 8);
}
