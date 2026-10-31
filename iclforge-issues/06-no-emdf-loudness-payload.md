# E-AC-3 encodes carry no EMDF programme loudness payload (payload ID 1)

DEE puts a `loudness_data` payload (ETSI TS 102 366 H.3.1, EMDF payload ID 1) in every frame of
its DD+ Atmos encodes. It records how the programme was measured and the measured values: relative
gated and speech gated loudness, and true peak. iclforge never writes this payload. Its EMDF
container carries only OAMD (11) and JOC (14).

Loudness-aware playback chains and QC tools read this payload. Without it, `dialnorm` is the only
loudness information in the stream, and an Atmos encode doesn't measure that either (see the
dialnorm issue).

## Evidence

The same 7.1.4 input was encoded at 768 kbit/s by DEE 5.2.1 and by `forge atmos-cbi`:

| | DEE | iclforge |
|---|---|---|
| EMDF payload IDs per frame | 11, 14, 2, 1 | 11, 14 |
| Payload 1 size | 2 or 3 bytes, every frame | absent |
| Payload 1 config | `payload_frame_aligned` 0, duration 1536 | absent |
| Decoded fields | `loudpractyp` 1, `loudcorrdialgat` 0, `loudcorrtyp` 0; in some frames `loudrelgat` 62, `loudspchgat` 63, `truepk` 211 | absent |

## Suggested fix

Write `loudness_data` from the measurement the dialnorm fix needs: BS.1770-4 relative gated,
speech gated and true peak. Append it to the EMDF container after OAMD and JOC.
`libs/objects/src/emdf.cpp` builds the container. The AC-4 encoder's loudness metadata writer
(`libs/ac4/src/encoder/frame/metadata.cpp`) has the same fields.

Check against the signing patches: the protection tag covers the whole container, so new payloads
are signed with no extra work. Verify that tvOS still accepts the seal after the change.
