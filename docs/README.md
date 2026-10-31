# Primer: the EMDF protection field

[← Main README](../README.md) · [Technical report](technical-report.md) · [Reproduce the results](reproduce.md)

Everything you need to understand the field, in about five minutes. For binary addresses and
the full proof, see the [technical report](technical-report.md).

## The short version

DD+ Atmos frames (E-AC-3 with Joint Object Coding) carry a small container of Atmos metadata
called **EMDF**, defined in ETSI TS 102 366 Annex H. Inside it is the 40-bit `emdf_protection`
field: a 32-bit **primary** tag and an 8-bit **secondary** tag. The specification defines the
field's layout and then declines to say what goes in it:

> the calculation is "implementation dependent and is not defined in the present document"

**What goes in it:** two truncated **HMAC-SHA-256** tags, keyed with a 32-byte key that the Dolby
Encoding Engine (DEE) embeds in its binary. The key is stored as a hex string with every byte
XORed with `0x7a`, which keeps it out of plain `strings` output.

## The construction

DEE hashes two messages per frame, with the same key:

| Tag | Message | Truncation |
|---|---|---|
| `prim` (32 bits) | `covered ‖ container` | first 4 bytes of digest 1 |
| `sec` (8 bits) | the **full 32-byte digest 1** | first byte of digest 2 |

```text
prim = HMAC-SHA-256(key, covered || container)[0:4]
sec  = HMAC-SHA-256(key, digest1)[0:1]
key  = 566cef6642595a1aa2ed20dcb1a62efb4b38a65ce7b627390ced5a16e9fd679e
```

* **`container`** is the EMDF body (everything after the 16-bit `0x5838` sync and 16-bit length)
  with the 40 protection bits set to zero.
* **`covered`** is the core audio frame as it was **before** the Atmos metadata was spliced in.
* **`key_id`** is a 3-bit key selector. It is 0 in every DEE frame.

### What `covered` is, exactly

This is the subtle part. `covered` is **not** a prefix of the frame you receive. DEE's muxer
splices `infomdat`, `addbsi` and the skip fields into the *middle* of the frame after the core is
encoded, so a verifier has to undo that splice by cutting these holes out of the emitted frame:

| Hole | Extent |
|---|---|
| Header | bits 0–31: syncword through `frmsiz` |
| `infomdat` element | flag **and** body |
| `addbsi` element | `addbsie`, `addbsil` and the bytes |
| `skipflde` | one flag bit |
| Every block's skip field | `skiple`, plus `skipl` and `skipfld` when set |
| Tail | end of the audio data to end of frame: aux data and CRC2 |

What remains is packed MSB-first and rounded to the **nearest** 16-bit word.

Finding those boundaries means walking the E-AC-3 bitstream field by field, through the BSI and
every audio block, including channel coupling. Every verifier, signer and integration depends on
getting this walk right.

## Five key results

1. **It is a MAC, not a checksum.** Every CRC-8 polynomial and the standard CRC-32 space, swept
   over 7 candidate regions, found no match that held across frames. That null result pointed to
   a secret key long before the algorithm was known.
2. **The algorithm is stock HMAC-SHA-256.** Textbook ipad/opad blocks were observed live in DEE's
   hash contexts, with the standard SHA-256 IV and round constants. Nothing exotic.
3. **The key ships inside the encoder.** A function builds the hex string on the stack and
   XOR-decodes it. A config table can override the key per payload id, but with none configured
   DEE signs with the embedded default.
4. **It is proven byte-exactly, several ways.** 32/32 DEE frames and 125/125 frames of an iclforge
   stream verify from the emitted bits alone, under an independent Python implementation. The
   Python signer and the patched iclforge signer produce byte-identical streams.
5. **The secondary tag matters.** It is a second HMAC over the *untruncated* primary digest. A
   verifier that ignores it accepts tampered frames, and a signer that leaves it zero produces
   tags that fail a complete verifier.

## What's still open

* **Other hardware.** tvOS 27.0 on an Apple TV checks the tag and accepts this construction: a
  signed iclforge stream decodes its objects, and one wrong tag bit mutes it
  ([technical report](technical-report.md#54-on-hardware-apple-tv)). AVRs and TVs that decode DD+
  themselves are untested.
* **Other keys.** Streams from other encoders or DEE configurations may use a different key.
  A commercial DD+ Atmos sample would settle it.
* **iclforge's own verifier** still declines coupled frames, so it reports genuine DEE streams as
  unsigned. That is a limit of its frame walker, not of the construction.

The technical report lists [every open question](technical-report.md#6-open-questions).

### For dolby-atmos-encoder

The [dolby-atmos-encoder](https://github.com/raress96/dolby-atmos-encoder) crate's
`dolby_keyed_mac` stand-in does not match DEE, even with the real key: it hashes
`key_id ‖ body[..]`, not `covered ‖ container`. Its `EmdfProtector` seam never sees the core
frame it would need, so wiring in DEE's construction means changing that seam's signature. The
crate already holds the right `covered` buffer: the core frame it passes to
`inject_frame_skipfield`. Details in the [technical report](technical-report.md#53-inside-dolby-atmos-encoder).

## Glossary

| Term | Meaning |
|---|---|
| **DD+ / E-AC-3** | Dolby Digital Plus, the codec streaming services use |
| **JOC** | Joint Object Coding: the object data that makes DD+ into "DD+ with Dolby Atmos" |
| **EMDF** | Extensible Metadata Delivery Format container (Annex H). It carries OAMD (payload 11) and JOC (payload 14) inside the frame's skip field |
| **OAMD** | Object Audio Metadata: where each Atmos object is and how it moves |
| **DEE** | Dolby Encoding Engine, Dolby's licensed reference encoder |
| **`covered`** | The signed part of the frame: the pre-mux core frame from bit 32, holes cut out, rounded to the nearest 16-bit word |
| **container / body** | The EMDF body after sync `0x5838` and length, with the protection bits zeroed for hashing |
| **prim / sec** | The 32-bit primary and 8-bit secondary protection tags |
| **`key_id`** | 3-bit key selector; 0 means DEE's embedded default key |
| **hole** | A bit range cut out of the emitted frame to rebuild `covered` |
| **coregraft** | dolby-atmos-encoder's diagnostic mode: a real Dolby core with replacement metadata |

## FAQ

<details>
<summary><b>Does the spec hide this?</b></summary>

No. The spec defines the fields and leaves the calculation to the implementation. Everything here
describes DEE's implementation, established by examining its behaviour and binary, not from any
published document.
</details>

<details>
<summary><b>Why is <code>covered</code>'s <code>audfrm</code> 3 bits shorter than the emitted frame's?</b></summary>

The emitted frame sets `skipflde=1` and has 2 extra zero flags. Which 2 flags they are is
unresolved: every candidate encodes to identical bytes for these streams, so it cannot be
observed here.
</details>

<details>
<summary><b>What does verifying an unsigned stream report?</b></summary>

`emdf_tool.py verify` reports each frame as `valid`, `prim_only` (secondary tag wrong) or
`invalid`. Unsigned frames come back `invalid`, and single-bit edits are caught even when the frame
CRC is re-stamped to match.
</details>

## Provenance

The authenticated-region choice and the secondary-tag derivation are **not in any public
document**. They were established by examining a licensed reference encoder (DEE, including its
binary) and validated bit-exactly against signed streams it emitted. The key lives only in this
repository's research files; it is not part of any library, test suite or shipped code.
Interoperability research use only.
