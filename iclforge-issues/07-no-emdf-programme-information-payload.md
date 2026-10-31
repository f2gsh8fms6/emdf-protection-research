# E-AC-3 encodes carry no EMDF programme information payload (payload ID 2)

DEE puts a programme information payload (ETSI TS 102 366 H.3.2, EMDF payload ID 2) in every frame.
It names the DRC profiles the `dynrng` and `compr` words were computed with, and records the
encoder's surround 90° phase filter, LFE low-pass filter and surround attenuation settings.
iclforge never writes it.

Without it, a decoder or transcoder can't tell which DRC profile a stream uses. It needs the
profile to regenerate DRC, for example when it re-encodes to a different format.

## Evidence

The same 7.1.4 input was encoded at 768 kbit/s by DEE 5.2.1 and by `forge atmos-cbi`:

| Field | DEE | iclforge |
|---|---|---|
| Payload 2 present | every frame, 3 bytes | absent |
| `dynrngprof` | 2 (film light) | absent |
| `comprprof` | 2 (film light) | absent |
| `ph90filt` | 1 | absent |
| `lfefilt` | 1 | absent |
| `suratten` | 0 | absent |
| `lfemonlevcod` | 0 | absent |

## Suggested fix

Write payload 2 whenever DRC or the related filters are in use. Take `dynrngprof` from `drc=`,
`comprprof` from the RF-mode profile (see the RF-mode DRC issue), and the filter flags from what
the encoder actually applied. iclforge's encoder doesn't apply a 90° surround phase filter (see the
JOC downmix issue), so `ph90filt` should be 0 until it does.

Depends on the Atmos metadata plumbing issue for Atmos encodes. The same signing check applies as
for payload 1.
