# JOC clip gain makes tvOS play every object 24 dB too quiet

> [!NOTE]
> Fixed by `06-joc-clipgain.patch`. Filed to record the bug and the open decoder question.

`oba::joc::build_payload` (`libs/ac3/src/oba/joc.cpp`) writes `joc_clipgain_x_bits` = 0 and
`joc_clipgain_y_bits` = 0. iclforge's own decoder reads the clip gain as `1 + (y/32) * 2^(x-4)`,
which is unity for any x when y = 0. tvOS instead scales the reconstructed objects by `2^(x-4)`, so
with x = 0 every object plays at exactly 1/16 (-24 dB). The bed is unaffected.

DEE always writes x = 4, y = 0, which is unity under either reading.

## Evidence

- Apple TV 4K (2nd gen), tvOS 27.0. An in-process `ec+3` decode (`AVAudioConverter` to 7.1.4) of
  an iclforge stream with x = 0 put every object exactly 24 dB below iclforge's own decode of the
  same stream. With x = 4, the two decodes matched within 0.2 dB.
- In a blind listen of a 7.1.4 test file, the iclforge encode sounded clearly quieter than DEE's
  encode of the same input.

## Fix

Write x = 4, as DEE does (patch 06).

## Open question

For x other than 4, the decoder's reading disagrees with tvOS. `(1 + y/32) * 2^(x-4)` fits the
tvOS result. The Dolby Reference Player measurements behind the current reading (see
`parse_payload` and `docs/library/decoding.md`) should be rechecked at x other than 4 before the
decoder is changed.
