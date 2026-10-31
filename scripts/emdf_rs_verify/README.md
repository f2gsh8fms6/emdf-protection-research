# emdf_rs_verify/

Checks the findings with the Rust parsers of
[dolby-atmos-encoder](https://github.com/raress96/dolby-atmos-encoder) (commit `faf3ef1`), so they
don't rest on the Python implementation alone. Results are in the
[technical report](../../docs/technical-report.md#53-inside-dolby-atmos-encoder).

| File | What it checks |
|---|---|
| `dee_verify.rs` | Parses `sample/out.ec3` with the crate's `parse_frames`, `find_dolby_emdf` and `field_offsets`. Asserts each stored prim/sec equals the HMAC over DEE's captured `covered` plus the body emdf.rs located (protection zeroed), and that this body equals DEE's captured second hash input. Also prints the crate's `dolby_keyed_mac` stand-in with the real key, for contrast. |
| `dee_mux_verify.rs` | Uses the crate's BSI locators to confirm `covered` is the pre-splice core (`infomdate=0`, `addbsie=0`), and that the crate's BSI splice, with DEE's `info_metadata` bits, reproduces the emitted frame up to `audfrm`. |
| `make_premux.py` | Builds `premux.ec3` from the captured `covered` buffers and prints how they align with the emitted frames. |

## Run it

From the repository root, with a Rust toolchain installed:

```sh
git clone https://github.com/raress96/dolby-atmos-encoder
git -C dolby-atmos-encoder checkout faf3ef1

W="$PWD"
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

---

[← Back to scripts](../README.md)
