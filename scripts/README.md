# scripts/

Tools for working with real streams, beyond the self-test in
[`../emdf_protection.py`](../emdf_protection.py).

| Path | What it does |
|---|---|
| [`emdf_tool.py`](emdf_tool.py) | **Verify, sign or corrupt** a DD+ Atmos stream, DEE-style, from the bitstream alone |
| [`emdf_rs_verify/`](emdf_rs_verify/) | Checks the findings with the [dolby-atmos-encoder](https://github.com/raress96/dolby-atmos-encoder) crate's own Rust parsers |
| [`iclforge_patches/`](iclforge_patches/) | Patches that make [iclforge](https://github.com/iainchesworthlabs/iclforge)'s signer match DEE and its JOC level match real decoders, plus a trace patch for `emdf_tool.py` |

## emdf_tool.py

```sh
python3 scripts/emdf_tool.py verify  in.ec3            # exit 0 if every frame is valid
python3 scripts/emdf_tool.py sign    in.ec3 out.ec3    # write correct prim + sec tags
python3 scripts/emdf_tool.py corrupt in.ec3 out.ec3    # flip one tag bit per frame, keep CRC valid
```

> [!NOTE]
> Locating each audio block's skip field and the end of the audio data needs a full E-AC-3
> block parser, including coupling. `emdf_tool.py` gets those positions from an instrumented
> iclforge decoder, built with the patches in `iclforge_patches/`. Set `FORGE` to its path (default
> `/tmp/iclforge-build/bin/forge`). Build steps:
> [`docs/reproduce.md`](../docs/reproduce.md#build-the-instrumented-iclforge).

Expected on DEE's stream: `{'valid': 32, 'prim_only': 0, 'invalid': 0, 'no_container': 0}`.

## emdf_rs_verify/

See its [README](emdf_rs_verify/README.md). It needs a Rust toolchain and a checkout of
dolby-atmos-encoder; the README has the full commands.

---

[← Back to the main README](../README.md)
