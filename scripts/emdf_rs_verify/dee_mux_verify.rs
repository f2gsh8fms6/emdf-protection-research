//! Is DEE's hashed `covered` buffer the pre-splice core that this crate's `inject_frame_skipfield`
//! expects? Uses the crate's own BSI locators on premux.ec3 (= emitted 32-bit header + captured
//! covered, built by make_premux.py). Inputs via env: DEE_ORACLE, DEE_PREMUX.
use super::*;

#[test]
fn dee_premux_is_pre_splice_core() {
    let premux = std::fs::read(std::env::var("DEE_PREMUX").expect("set DEE_PREMUX")).unwrap();
    let dir = std::path::PathBuf::from(std::env::var("DEE_ORACLE").expect("set DEE_ORACLE"));
    let emitted = std::fs::read(dir.join("out.ec3")).unwrap();
    let (pf, ef) = (parse_frames(&premux), parse_frames(&emitted));
    for i in 0..8 {
        let (pi, ei) = (&pf[i], &ef[i]);
        let core = &premux[pi.offset..pi.offset + pi.size];
        let out = &emitted[ei.offset..ei.offset + ei.size];
        let (p, addbsie) = bsi_addbsie_pos(core, pi).unwrap();
        let (ip, iv) = bsi_infomdate_pos(core, pi).unwrap();
        assert_eq!((iv, addbsie), (0, 0), "pre-splice core has no infomdat/addbsi");

        // Replay inject_frame_skipfield's BSI splice, but with DEE's emitted info_metadata body
        // (bsmod3 copyrightb1 origbs1 dsurexmod2 audprodie1 sourcefscod1) instead of 9 zeros.
        let cb = |q: usize| (core[q >> 3] >> (7 - (q & 7))) & 1;
        let ob = |q: usize| (out[q >> 3] >> (7 - (q & 7))) & 1;
        let info: Vec<u8> = (ip + 1..ip + 10).map(ob).collect();
        let mut v: Vec<u8> = (0..ip).map(cb).collect();
        v.push(1);
        v.extend(&info);
        v.extend((ip + 1..p).map(cb));
        v.push(1);
        v.extend([0, 0, 0, 0, 0, 1]); // addbsil = 1 → 2 bytes
        v.extend((0..16).map(|k| (0x0110u16 >> (15 - k)) as u8 & 1));
        let audfrm = v.len();
        v.extend((p + 1..core.len() * 8).map(cb));
        let first = (32..v.len().min(out.len() * 8)).find(|&q| v[q] != ob(q)).unwrap();
        assert!(first >= audfrm, "BSI splice must reproduce emitted bits 32..audfrm");
        println!(
            "frame {i}: core infomdate@{ip}=0 addbsie@{p}=0; DEE info_metadata={info:?}; \
             spliced == emitted for bits 32..{first} (audfrm starts at {audfrm})"
        );
    }
}
