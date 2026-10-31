# E-AC-3 Atmos commands silently ignore every metadata option except `dialnorm=`

The E-AC-3 Atmos commands (`atmos`, `atmos-path`, `atmos-encode`, `atmos-adm`, `atmos-iab`,
`atmos-cbi`) accept the per-encode metadata options (`drc=`, `heavy`,
`mixmeta`, `dmixmod=`, `cmixlev=`, `surmixlev=`, the Lt/Rt and Lo/Ro mix levels, `bsmod=`,
`copyright`, `origbs=`, `infomdat` and the rest) and their help text lists them. None of them reach
the stream. An Atmos encode therefore can't carry DRC, downmix or informational metadata.

## Evidence

```sh
forge atmos-cbi in.wav plain.ec3 768 7.1.4
forge atmos-cbi in.wav meta.ec3 768 7.1.4 drc=film-light mixmeta dmixmod=loro \
    cmixlev=-3 surmixlev=-3 bsmod=0 copyright origbs=on
cmp plain.ec3 meta.ec3   # identical
```

`forge probe meta.ec3` reports `compr absent`, `dynrng absent`, `dmixmod absent`. The run gives no
warning. Only `atmos-cbi` was run. The other Atmos commands build the same `AtmosConfig`, so the
same applies to them.

## Cause

`AtmosConfig` (`libs/ac3/include/iclforge/ac3/oba/atmos.hpp`) has no metadata fields. Both
`AtmosEncoder::Impl` constructors build the bed substream's `eac3::FrameConfig` from only
`sample_rate`, `bitrate_kbps`, `acmod`, `lfe`, `numblkscod`, `dialnorm`, `fast_mdct` and
`oba_complexity_index`. `FrameConfig` already supports `drc`, `heavy`, `mixing` and the
informational group, and `eac3-encode` fills them from `Options::p`.

## Suggested fix

1. Add the metadata (or a `plan::Metadata`) to `AtmosConfig`, and forward it into
   `.independent` in both `Impl` constructors.
2. Pass `meta.p` through in every Atmos command's `run_atmos_*` function in
   `apps/forge/cli/src/commands/atmos.cpp`.
3. Until that lands, refuse these options on the Atmos commands instead of dropping them.

Patch 01 already signs frames that carry `infomdat` correctly.

## Reference: what DEE writes by default

DEE 5.2.1's `encode_to_atmos_ddp` template writes these defaults:

| Field | DEE | iclforge now |
|---|---|---|
| `dynrng` (line mode) | film light | absent |
| `compr` (RF mode) | film light, every frame | absent (see the RF-mode DRC issue) |
| `mixmdate` | 1 | 0 |
| `dmixmod` | 2 (Lo/Ro) | absent |
| `ltrtcmixlev`, `lorocmixlev`, `ltrtsurmixlev`, `lorosurmixlev` | 4 (-3 dB) each | absent |
| `infomdate` | 1 | 0 |
| `bsmod`, `copyrightb`, `origbs`, `dsurexmod`, `audprodie`, `sourcefscod` | 0, 1, 1, 0, 0, 0 | absent |

After the fix, consider matching these as the Atmos defaults: film light DRC and Lo/Ro at -3 dB.
