# Reproduce the results

[← Main README](../README.md) · [Primer](README.md) · [Technical report](technical-report.md)

Every result in the [technical report](technical-report.md) can be re-run from this repository.
The experiments go from "no build at all" to "full toolchain".

| # | Experiment | Needs | Expected |
|---|---|---|---|
| 1 | [Self-test](#1-self-test) | Python 3 | 8/8 frames match |
| 2 | [Verify DEE's stream](#2-verify-dees-stream) | + iclforge build | 32/32 valid |
| 3 | [Detect tampering](#3-detect-tampering) | + iclforge build | 32/32 invalid |
| 4 | [Sign a stream](#4-sign-a-stream) | + iclforge build | 125/125 valid, byte-identical to iclforge's own signing |
| 5 | [Rust cross-check](#5-rust-cross-check) | + Rust toolchain | 2 tests pass |
| 6 | [Capture DEE's hash inputs](#6-capture-dees-hash-inputs-yourself) | DEE + gdb | optional |

Run everything from the repository root:

```sh
W="$PWD"
```

## 1. Self-test

No build, about a second. Recomputes frames 0–7 of DEE's stream from the hash inputs captured in
`sample/protection/`, and compares them with the tags DEE wrote (`sample/bodies.json`):

```sh
python3 emdf_protection.py
```

```text
frame 0: prim=afac597c sec=0x2a stored=afac597c/0x2a MATCH
...
self-test: 8/8 frames match DEE's emitted protection
```

**What it proves:** given the same two messages, the key and the HMAC construction reproduce
DEE's tags exactly.

## Build the instrumented iclforge

Experiments 2–4 recompute tags from the raw stream with
[`scripts/emdf_tool.py`](../scripts/emdf_tool.py). It parses everything itself except each audio
block's skip point and the end of the audio data, which need a full E-AC-3 block walker with
channel coupling. It gets those positions from an iclforge decoder built with the patches in
[`scripts/iclforge_patches/`](../scripts/iclforge_patches/):

```sh
git clone --depth 1 https://github.com/iainchesworthlabs/iclforge /tmp/iclforge-src
cd /tmp/iclforge-src
for p in 01-infomdat-hole 02-secondary-tag 03-bitpos-trace 04-default-signing 05-signing-docs \
         06-joc-clipgain; do
  git apply "$W/scripts/iclforge_patches/$p.patch"
done
cmake -S . -B /tmp/iclforge-build -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DICLFORGE_SENDSPIN_CORE_ONLY=ON -DICLFORGE_BUILD_GUI=OFF -DICLFORGE_BUILD_EXAMPLES=OFF
ninja -C /tmp/iclforge-build forge
cd "$W"
```

| Patch | Purpose |
|---|---|
| `01-infomdat-hole` | iclforge's signer cuts out the whole `infomdat` element, as DEE does |
| `02-secondary-tag` | iclforge's signer writes and verifies the secondary tag |
| `03-bitpos-trace` | Prints the block bit positions `emdf_tool.py` reads (with `ICLF_BITPOS` set) |
| `04-default-signing` | Ships the DEE key and signs every E-AC-3 Atmos encode with it by default |
| `05-signing-docs` | Docs-only: updates iclforge's signing docs for 04 and records the Apple TV result |
| `06-joc-clipgain` | Writes the JOC clip gain as DEE does, so real decoders play the objects at full level |

Only 03 is needed for `emdf_tool.py`; 01, 02, 04 and 05 are the signer improvements, 06 is for
playback on real hardware, and step 4 below exercises 04.

The extra CMake options skip modules that need unrelated packages (MbedTLS, Qt). `emdf_tool.py`
looks for `/tmp/iclforge-build/bin/forge` by default. If you built elsewhere, point `FORGE` at it:

```sh
export FORGE=/path/to/bin/forge
```

## 2. Verify DEE's stream

```sh
python3 scripts/emdf_tool.py verify sample/out.ec3
```

```text
frame 0: prim afac597c want afac597c  sec 2a want 2a
...
sample/out.ec3: {'valid': 32, 'prim_only': 0, 'invalid': 0, 'no_container': 0}
```

Exit code 0. The first frames printed match the captured table in the technical report.

**What it proves:** the construction, including how `covered` is rebuilt from the emitted frame,
reproduces all 32 of DEE's tags from the bitstream alone.

## 3. Detect tampering

Flip one primary-tag bit in every frame, re-stamp each frame's CRC so only the EMDF tag can catch
the change, then verify:

```sh
python3 scripts/emdf_tool.py corrupt sample/out.ec3 /tmp/corrupt.ec3
python3 scripts/emdf_tool.py verify /tmp/corrupt.ec3
```

Expected: `{'valid': 0, 'prim_only': 0, 'invalid': 32, 'no_container': 0}` and exit code 1.

**What it proves:** the verifier genuinely recomputes the tag. CRC-clean edits are caught by the
40 protection bits alone.

## 4. Sign a stream

With patch 04, `forge atmos` signs by default. Generate a 4-second (125-frame) stream and verify
it with no key argument anywhere:

```sh
/tmp/iclforge-build/bin/forge atmos /tmp/forge-signed.ec3 4          # signed with the built-in DEE key
python3 scripts/emdf_tool.py verify /tmp/forge-signed.ec3           # 125 valid, exit 0
/tmp/iclforge-build/bin/forge decode /tmp/forge-signed.ec3 /tmp/out.wav \
  verify-objects                                                   # 125 valid, 0 mismatched
```

Now make an unsigned stream, sign it with the Python tool, and show the two signings agree byte
for byte:

```sh
/tmp/iclforge-build/bin/forge atmos /tmp/unsigned.ec3 4 sign-objects=off
python3 scripts/emdf_tool.py verify /tmp/unsigned.ec3              # 0 valid, 125 invalid
python3 scripts/emdf_tool.py sign /tmp/unsigned.ec3 /tmp/signed.ec3
cmp /tmp/signed.ec3 /tmp/forge-signed.ec3 && echo "byte-identical"
```

**What it proves:** iclforge signs E-AC-3 Atmos automatically with the built-in key, and that
output is bit-for-bit what the independent Python signer produces.

> [!NOTE]
> A stream signed by iclforge *without* `02-secondary-tag.patch` has its secondary tag left at
> zero, so it fails verification on that field (124/125 frames). Valid tags need both halves.

## 5. Rust cross-check

Checks the findings with the Rust parsers of
[dolby-atmos-encoder](https://github.com/raress96/dolby-atmos-encoder) instead of the Python ones.
The harness copies the crate to a temporary directory and drops two test modules into it:

```sh
git clone https://github.com/raress96/dolby-atmos-encoder
git -C dolby-atmos-encoder checkout faf3ef1

T=/tmp/dae-verify; rm -rf "$T"; mkdir -p "$T"
git -C dolby-atmos-encoder ls-files | tar -C dolby-atmos-encoder -cf - -T - | tar -C "$T" -xf -
cp scripts/emdf_rs_verify/dee_verify.rs scripts/emdf_rs_verify/dee_mux_verify.rs "$T/src/"
printf '\n#[cfg(test)]\n#[path = "dee_verify.rs"]\nmod dee_verify;\n' >> "$T/src/emdf.rs"
printf '\n#[cfg(test)]\n#[path = "dee_mux_verify.rs"]\nmod dee_mux_verify;\n' >> "$T/src/eac3.rs"
python3 scripts/emdf_rs_verify/make_premux.py "$W/sample" "$T/premux.ec3"
(cd "$T" && DEE_ORACLE="$W/sample" DEE_PREMUX="$T/premux.ec3" \
  cargo test --release dee_ -- --nocapture --test-threads=1)
```

Expected: `test result: ok. 2 passed`.

**What it proves:** stored tags equal `HMAC(key, covered ‖ body)` when computed with the crate's
own parsers, and `covered` is the pre-splice core frame. See the
[harness README](../scripts/emdf_rs_verify/README.md) for what each test asserts.

## 6. Capture DEE's hash inputs yourself

Optional, and only for re-deriving the findings from scratch: `sample/protection/` already holds
the captured inputs. You need the DEE binary and gdb.

1. Break on the SHA-256 update routine in `dee_audio_filter_ddp_atmos.so`: `FUN_003b5460`
   (objdump) or `FUN_004b5460` (Ghidra, base `+0x100000`). Subtract the load base.
2. On each call, dump the buffer and length while DEE encodes a 5.1 WAV to DD+ JOC.
3. For frame *i*, `upd_{2+5i}` is `covered` and `upd_{3+5i}` is the zeroed container.
   `upd_00` and `upd_01` are the ipad blocks (key ⊕ `0x36`), a handy check on the key.

Function addresses for the build examined are in the technical report's
[binary map](technical-report.md#3-where-it-lives-in-the-binary). Other builds will differ.

## Troubleshooting

<details>
<summary><code>no BITPOS output from .../forge: is it the instrumented build?</code></summary>

`03-bitpos-trace.patch` is missing from the build, or `FORGE` points at a different binary.
Rebuild as above, or set `FORGE` explicitly.
</details>

<details>
<summary>Frame counts disagree (<code>assert len(pos) == len(frames)</code>)</summary>

The forge binary used is not the instrumented build. Set `FORGE` to the binary you built.
</details>

<details>
<summary><code>IndexError</code> in <code>Bits.read</code> on a new stream</summary>

Usually a frame whose EMDF container sits past the last parsed position. Check that the stream is
a complete DD+ JOC stream and that `FORGE` is the instrumented build.
</details>

<details>
<summary><code>sec</code> mismatches on a freshly signed stream</summary>

It was signed without `02-secondary-tag.patch`, which leaves the secondary tag at zero. Re-sign
with a patched iclforge or with `emdf_tool.py sign`.
</details>

<details>
<summary>iclforge's <code>verify-objects</code> reports DEE's stream as unsigned</summary>

Expected. iclforge's frame walker declines coupled frames, and DEE codes every block with coupling.
That is a limit of iclforge, not of the construction; `emdf_tool.py` handles these frames.
</details>
