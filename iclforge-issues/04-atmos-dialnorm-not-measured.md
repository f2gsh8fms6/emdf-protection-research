# Atmos encodes default to dialnorm -31 and `atmos-cbi` refuses `dialnorm=auto`

Every Atmos command writes dialnorm 31 unless it is given a number. `atmos-cbi` (like
`atmos-adm`, `atmos-iab` and `atmos-encode` with `src=`/`map=`) refuses `dialnorm=auto`, because
a wide bed "has no single fixed layout to measure loudness against". The result is a stream whose
dialnorm doesn't describe it. A decoder that normalizes to dialnorm then plays it louder than the
same programme encoded by DEE.

## Evidence

For the same 7.1.4 input at 768 kbit/s:

| | DEE 5.2.1 | `forge atmos-cbi` |
|---|---|---|
| dialnorm written | 27 (measured, BS.1770-4 with dialogue intelligence) | 31 (default) |
| `forge loudness <stream>` | -26.92 LKFS, dialnorm 27 | -26.80 LKFS, dialnorm 27 |

iclforge can already measure its own output: `forge loudness` on the iclforge stream gives 27, in
agreement with DEE. The encode just doesn't do this step. With 31, a decoder that normalizes to
-31 applies no attenuation where DEE's stream gets 4 dB, so the iclforge stream plays 4 dB louder.

## Suggested fix

Support `dialnorm=auto` on the Atmos commands, and consider making it the default as DEE does.
Either of these would work:

- Measure the 5.1 bed the encoder builds. `run_atmos_cbi` already meters it with a `LevelMeter`.
  This needs a pre-pass over the input, the way `eac3-encode` reads the whole file when
  `measure_dialnorm` is set.
- Measure the full-layout input with BS.1770-4's channel weights, which cover any layout.

The bed measurement matches what `forge loudness` reports and what DEE wrote here.
