# JOC parameter resolution is fixed and coarser than DEE's

Every E-AC-3 Atmos command builds `AtmosConfig` with `num_bands_idx` 4 (9 bands) and leaves
`fine_quant` false (the 96-step coarse quantizer). The JOC writer also always uses a smooth slope
with one data point. None of these can be changed from the CLI. For the same input, DEE uses 12
bands and the fine quantizer, and uses a steep slope in some frames.

Coarser matrices reconstruct objects less accurately, especially when objects share bed channels,
and the smooth-only ramp smears abrupt changes across a frame. Neither has been measured against
DEE yet.

## Evidence

The same 7.1.4 input was encoded at 768 kbit/s by DEE 5.2.1 and by `forge atmos-cbi`. The values
are the same for every one of the 11 JOC objects:

| Field | DEE | iclforge |
|---|---|---|
| `joc_num_bands_idx` | 5 (12 bands) | 4 (9 bands) |
| `joc_num_quant_idx` | 1 (fine, 192 steps) | 0 (coarse, 96 steps) |
| `joc_slope_idx` | 1 (steep, with `joc_offset_ts`) in 24 of 1320 frames, else 0 | always 0 |
| JOC payload size | mostly 99 to 102 bytes | 77 to 79 bytes |

## Suggested fix

1. Expose `joc-bands=<idx>` and `joc-quant=fine|coarse` on the Atmos commands. Today each
   `run_atmos_*` passes `.num_bands_idx = 4` and never sets `fine_quant`.
2. Measure per-object reconstruction SNR at DEE's settings (12 bands, fine) against the current
   ones at a typical bit rate, and change the defaults if it wins. The extra 20-odd bytes come out
   of the mantissas.
3. Separately, find out when DEE picks a steep slope with `joc_offset_ts`, and consider doing the
   same (`build_payload` in `libs/ac3/src/oba/joc.cpp`). The comment there argues against steep
   slopes for moving objects.
