# iclforge issues

Draft GitHub issues for [iclforge](https://github.com/iainchesworthlabs/iclforge), one per file.
The first line of each file is the issue title. Issues refer to each other by topic ("see the
dialnorm issue"), so swap in issue numbers once they're filed.

The findings come from 2026-10-11. DEE 5.2.1 (`encode_to_atmos_ddp` template defaults) and
`forge atmos-cbi` encoded the same 42 s 7.1.4 test WAV at 768 kbit/s. The two streams were
compared field by field across all 1320 frames, decoded with iclforge, and played on an Apple TV 4K
(tvOS 27.0). Code references are to iclforge `011506e` with this repository's patches 01 to 05
applied.

| File | Issue | Priority |
|---|---|---|
| [01](01-joc-clipgain-objects-24db-low.md) | JOC clip gain makes tvOS play every object 24 dB too quiet | High, fixed by patch 06 |
| [02](02-cbi-extension-channels-3db-low.md) | `atmos-cbi`: height and back bed channels reconstruct 3 dB low | High |
| [03](03-atmos-ignores-metadata-options.md) | E-AC-3 Atmos commands silently ignore every metadata option except `dialnorm=` | High |
| [04](04-atmos-dialnorm-not-measured.md) | Atmos encodes default to dialnorm -31 and `atmos-cbi` refuses `dialnorm=auto` | High |
| [05](05-no-rf-mode-drc-profiles.md) | No RF-mode DRC: `compr` is never written from a DRC profile | Medium |
| [06](06-no-emdf-loudness-payload.md) | No EMDF programme loudness payload (ID 1) | Medium |
| [07](07-no-emdf-programme-information-payload.md) | No EMDF programme information payload (ID 2) | Low |
| [08](08-oamd-no-trim-element.md) | OAMD never carries a `trim_element` | Low |
| [09](09-cbi-bed-chan-distribute-not-set.md) | `atmos-cbi` leaves `b_bed_chan_distribute` clear | Low |
| [10](10-joc-no-phase-shifted-downmix.md) | No option to build the 5.1 core with 90°-phase-shifted surrounds | Low |
| [11](11-joc-precision-fixed-and-coarse.md) | JOC parameter resolution is fixed and coarser than DEE's | Medium |
| [12](12-levels-loudness-refuse-wide-wav.md) | `forge levels` and `forge loudness` refuse WAVs wider than 5.1 | Low |

## Differences not filed

None of these has any known effect:

- **OAMD payload framing.** iclforge sends OAMD with `payload_frame_aligned` 1, and DEE with 0.
  tvOS accepts both.
- **`object_gain_idx`.** iclforge writes 0 and DEE writes 3. Both mean 0 dB.
- **Encoder tuning.** Dither, delta bit allocation, exponent strategies, `bamode`, `frmfgaincode`
  and `expstre` differ. These are rate-control choices, not missing features.

Both encoders write the same bed (7.1.4), object count (12, with 11 in JOC), `addbsi` Atmos marker,
EMDF version, key ID and protection lengths.
