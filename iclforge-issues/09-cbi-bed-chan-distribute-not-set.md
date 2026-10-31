# `atmos-cbi` leaves `b_bed_chan_distribute` clear

For channel-based immersive input, DEE sets `b_bed_chan_distribute` (ETSI TS 103 420 §5.6.0.8). The
flag lets a renderer spread a bed channel over several speakers when the playback layout is larger
than the bed. `atmos-cbi` always writes 0.

iclforge's own comment on `Program::bed_chan_distribute`
(`libs/objects/include/iclforge/objects/oamd.hpp`) says: "Dolby's own DD+ JOC encoder sets this on
channel-based immersive input." The writer in `libs/objects/src/oamd.cpp` supports the flag, but
the CBI encoder never sets it.

## Evidence

The same 7.1.4 input was encoded by DEE 5.2.1 and by `forge atmos-cbi`:

| Field | DEE | iclforge |
|---|---|---|
| `b_bed_chan_distribute` | 1 | 0 |

What this changes depends on the renderer and the room. With the flag clear, a bed channel stays on
its one speaker in layouts that have more speakers in that zone, for example wides or a
cinema-style surround array. This hasn't been checked on hardware.

## Suggested fix

Set `bed_chan_distribute = true` on the `Program` built by `AtmosEncoder`'s `BedProgram`
constructor, to match DEE. If a reason to turn it off comes up, add an option for that.
