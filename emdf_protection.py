#!/usr/bin/env python3
"""
EMDF keyed authentication: the Dolby Encoding Engine's construction, reimplemented.

Reverse engineered from the Dolby Encoding Engine (DEE,
dee_audio_filter_ddp_atmos.so) and validated byte-exactly against 8 frames of
DEE's own DD+ JOC output. Full write-up: docs/technical-report.md.

Algorithm
---------
The 32-bit primary ("prim") and 8-bit secondary ("sec") emdf_protection fields
are NOT a CRC and NOT a plain checksum. They are two truncated HMAC-SHA-256
tags with a 32-byte key embedded in the encoder binary:

    key32 = unhex("2c16951c38232060d8975aa6cbdc54813142dc269dcc5d437697206c93871de4")
            with every byte XORed with 0x7a
          = 566cef6642595a1aa2ed20dcb1a62efb
            4b38a65ce7b627390ced5a16e9fd679e

    prim(32 bits) = HMAC-SHA-256(key32, covered || container)[0:4]
    sec (8 bits)  = HMAC-SHA-256(key32, prim_digest_32_bytes)[0:1]
    key_id(3 bits)= 0 in every DEE frame (hashed as-is; zeroing it would be a no-op)

where

  covered   = DEE's pre-mux core frame from bit 32 (fscod) on, before the Atmos
              muxer edits it: infomdate=0, addbsie=0, no skip-field syntax, no
              per-block skiple, no EMDF; ends at the end of the audio data
              (16-bit word aligned), with no padding/aux/CRC2. Relative to the
              emitted frame its audfrm is 3 bits shorter (see docs/technical-report.md).
  container = the EMDF body after the 16-bit sync and 16-bit length (emdf_version
              .. end of protection_bits_secondary, byte-padded; = `body` in
              dolby-atmos-encoder's emdf.rs) with the 40 protection bits (prim 32b +
              sec 8b) written as ZEROS.

DEE context layout (FUN_00386200 = init, FUN_003b5460 = update,
FUN_00386d00 = finalize) is bog-standard HMAC-SHA-256: ipad block at ctx+0x80,
opad block at ctx+0xc0, SHA-256 state stored as little-endian words. The hash
itself is stock SHA-256 (standard IV and K constants).

Verification (sample/, protection/)
-----------------------------------
For frames 0..7 of DEE's own encode of a 1-second 5.1 test signal:
    prim == HMAC(key, upd_{2+5i} || upd_{3+5i})[:4]        8/8 MATCH
    sec  == HMAC(key, that digest)[0]                      8/8 MATCH
(upd_NN.bin are the literal bytes DEE fed into its hash contexts, captured
live via gdb breakpoints on FUN_003b5460.)

Key derivation (FUN_00386ee0 @ .so file offset 0x286ee0)
--------------------------------------------------------
The function builds the 64-char ASCII hex string
"2c16951c38232060d8975aa6cbdc54813142dc269dcc5d437697206c93871de4"
on the stack byte-by-byte, then decodes it two chars at a time applying
`b = (hi_digit*16 + lo_digit) ^ 0x7a`. If a config-table entry supplies a key
(FUN_00386200 branch, plVar9[1] != NULL) that key is used instead; with no
license/config key the embedded default above is what ships.
"""

import hashlib
import hmac

# 32-byte HMAC key embedded in DEE (hex string constant XOR 0x7a).
EMDF_HEX_CONST = "2c16951c38232060d8975aa6cbdc54813142dc269dcc5d437697206c93871de4"
EMDF_KEY = bytes(b ^ 0x7A for b in bytes.fromhex(EMDF_HEX_CONST))

PROTECTION_BITS = 32 + 8  # prim + sec, zero while hashing


def compute_protection(covered: bytes, container: bytes) -> tuple[bytes, int]:
    """Compute the EMDF protection fields exactly as DEE does.

    covered    the pre-mux core frame from bit 32 on (see module docstring), as one
               byte string, MSB-first bit packing (the natural bit-writer output).
    container  the EMDF body (emdf_version .. protection_bits_secondary, byte-padded)
               with the 40 protection bits zeroed.

    Returns (prim, sec):
      prim  4 bytes (32-bit primary protection, big-endian bit order)
      sec   1 byte  (8-bit secondary protection)
    """
    digest1 = hmac.new(EMDF_KEY, covered + container, hashlib.sha256).digest()
    prim = digest1[:4]
    sec = hmac.new(EMDF_KEY, digest1, hashlib.sha256).digest()[:1]
    return prim, sec


def zero_protection(container: bytes, protection_bit_offset: int) -> bytes:
    """Zero prim + sec in an EMDF body copy.

    protection_bit_offset = start of protection_bits_primary within the body
    (emdf.rs `field_offsets().protection_start - 32`).
    """
    out = bytearray(container)
    for i in range(protection_bit_offset, protection_bit_offset + PROTECTION_BITS):
        out[i >> 3] &= ~(0x80 >> (i & 7))
    return bytes(out)


def _self_test() -> None:
    """Recompute frames 0..7 from DEE's live-captured hash inputs and compare
    against the prim/sec DEE stored in its emitted stream (sample/bodies.json)."""
    import json
    import os

    sample = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample")
    here = os.path.join(sample, "protection")
    if not os.path.isdir(here):
        print("self-test: no captured sample data found, skipping")
        return
    stored = json.load(open(os.path.join(sample, "bodies.json")))

    # Frame i: covered = upd_{2+5i}, body = upd_{3+5i}
    ok = 0
    for i in range(8):
        a = open(os.path.join(here, "upd_%02d.bin" % (2 + 5 * i)), "rb").read()
        c = open(os.path.join(here, "upd_%02d.bin" % (3 + 5 * i)), "rb").read()
        prim, sec = compute_protection(a, c)
        want = stored[i]
        match = int.from_bytes(prim, "big") == want["prim"] and sec[0] == want["sec"]
        ok += match
        print("frame %d: prim=%s sec=0x%02x stored=%08x/0x%02x %s"
              % (i, prim.hex(), sec[0], want["prim"], want["sec"], "MATCH" if match else "FAIL"))
    print("self-test: %d/8 frames match DEE's emitted protection" % ok)
    assert ok == 8


if __name__ == "__main__":
    _self_test()
