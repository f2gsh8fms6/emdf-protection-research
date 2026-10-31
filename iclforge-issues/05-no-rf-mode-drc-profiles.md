# No RF-mode DRC: `compr` is never written from a DRC profile

iclforge's E-AC-3 encoder can write line-mode DRC (`dynrng`, per block) from a profile with
`drc=<profile>`. It has no way to write RF-mode DRC (`compr`, per syncframe) from a profile. The
only source of `compr` is `heavy`, which is §7.7.2's peak ceiling in the mono downmix, not a
compression profile. DEE writes both, and its defaults use film light for each.

Decoders in RF mode, and those whose "night mode" or dynamic-range setting picks the RF words, get
no profile-based compression from an iclforge stream.

## Evidence

Plain E-AC-3, 5.1 input:

| Command | `dynrng` | `compr` |
|---|---|---|
| `forge eac3-encode in.wav out.ec3 640 drc=film-light` | 1 .. 255 | absent |
| `forge eac3-encode in.wav out.ec3 640 drc=film-light heavy` | 1 .. 255 | 0 |

DEE 5.2.1's Atmos encode of a 7.1.4 test file (`rf_mode_drc_profile` film_light) wrote `compr` in
every frame, with values spread across codes 255, 1, 2, 4 and others. Its EMDF programme
information payload names the profile (`comprprof` 2, film light).

## Suggested fix

Add an RF-mode profile option, for example `rf-drc=<profile>`, that computes `compr` per syncframe
from the same `meta::Profile` curves with RF-mode's +11 dB boost and its overload protection.
Write it as the AC-3/E-AC-3 `compr` word, and keep `heavy` as the explicit peak-ceiling mode.
A sensible default is the same profile as `drc=`. DEE's template sets both to film light.

Depends on the Atmos metadata plumbing issue for Atmos encodes.
