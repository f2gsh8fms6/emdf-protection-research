# iclforge_patches/

Patches for [iclforge](https://github.com/iainchesworthlabs/iclforge) that make its signer produce
DEE-identical tags, fill in the DEE key automatically, fix its JOC level on real decoders, and add
the bit-position tracing `emdf_tool.py` needs.

| File | What it does |
|---|---|
| `01-infomdat-hole.patch` | Leaves the **whole** `infomdat` element out of the signed message, not just its flag bit, and signs frames that carry it |
| `02-secondary-tag.patch` | Writes and verifies the 8-bit **secondary** tag, which was previously left zero. Apply after 01 |
| `03-bitpos-trace.patch` | Debug only: with `ICLF_BITPOS` set, the decoder prints the block bit positions `emdf_tool.py` reads |
| `04-default-signing.patch` | Ships the DEE key (`dee_default_signing_key()`) and signs every E-AC-3 Atmos encode with it by default. Apply after 02 |
| `05-signing-docs.patch` | Updates iclforge's docs for 04: signs by default, the key is built in, and this part is not clean-room. Records the Apple TV hardware result. Apply after 04 |
| `06-joc-clipgain.patch` | Writes the JOC clip gain as DEE does (`joc_clipgain_x_bits` 4). With the 0 iclforge wrote, tvOS plays the objects 24 dB too quiet. Apply after 05 |

01, 02, 04 and 06 include tests, and every patch but 03 updates the docs. Apply all six, in
order, to a fresh checkout:

```sh
git clone --depth 1 https://github.com/iainchesworthlabs/iclforge
cd iclforge
for p in 01-infomdat-hole 02-secondary-tag 03-bitpos-trace 04-default-signing 05-signing-docs \
         06-joc-clipgain; do
  git apply /path/to/scripts/iclforge_patches/$p.patch
done
```

After 04, `forge atmos out.ec3 4` (and the other E-AC-3 Atmos commands) produces a signed stream
with no key argument, byte-identical to what this repository's `emdf_tool.py sign` writes. Build
steps: [`docs/reproduce.md`](../../docs/reproduce.md#build-the-instrumented-iclforge).

> [!WARNING]
> After 02, streams signed by the unpatched signer **fail** verification on their secondary tag,
> because valid tags must carry both halves. Re-sign them.

> [!IMPORTANT]
> The key, the authenticated region, and the secondary-tag derivation come from examining DEE, not
> from a public document. Patch 05 states this in iclforge's own docs. See the provenance notice in
> the [main README](../../README.md) before proposing these changes upstream.

---

[← Back to the main README](../../README.md)
