# No option to build the 5.1 core with 90°-phase-shifted surrounds

DEE builds the 5.1 core of a DD+ Atmos stream with its surround channels phase-shifted by 90°. It
signals this as JOC `joc_dmx_config_idx` 3 (`kDmxConfig5XPhaseShift`, ETSI TS 103 420 Table 47)
and as `ph90filt` 1 in the programme information payload. A legacy decoder's Lt/Rt matrix downmix
of that core is then Pro Logic compatible without the decoder applying its own shift.

iclforge builds an unshifted core and signals `joc_dmx_config_idx` 0 (`kDmxConfig5X`). That is
consistent, so this isn't a correctness bug. It is a missing encoder feature.

## Evidence

The same 7.1.4 input was encoded by DEE 5.2.1 and by `forge atmos-cbi`:

| Field | DEE | iclforge |
|---|---|---|
| `joc_dmx_config_idx` | 3 (5.X, 90° phase shift) | 0 (5.X) |
| `ph90filt` (payload 2) | 1 | absent |

## Suggested fix

Add an encoder option, for example `surround-phase=90`, that applies a 90° phase shift to Ls/Rs
(a Hilbert pair) as the core is built. Signal `kDmxConfig5XPhaseShift`, and set `ph90filt` 1 once
payload 2 exists. The decoder needs no change: per `docs/library/decoding.md`, the phase-shift
configurations already reconstruct like their unshifted siblings. DEE turns it on by default.

Low priority: `dmixmod` Lo/Ro, which DEE also prefers, doesn't depend on it.
