# OAMD never carries a `trim_element`

DEE sends a `trim_element` (ETSI TS 103 420 §5.5.12, `oa_element_id_idx` 2) as a second
`oa_element` in every OAMD payload. It tells a renderer how to trim the mix when it folds the
programme down to a smaller speaker layout. iclforge's OAMD has only the `object_element`.
iclforge's parser already reads trim elements (`read_trim_element` in `libs/objects/src/oamd.cpp`),
but nothing writes one.

DEE's template exposes this as `custom_trims` (`surround_trim_5_1`, `height_trim_5_1`, both `auto`
by default), which it writes as `global_trim_mode` 0.

## Evidence

The same 7.1.4 input was encoded by DEE 5.2.1 and by `forge atmos-cbi`:

| Field | DEE | iclforge |
|---|---|---|
| `oa_element_count` | 2 | 1 |
| Elements | `object_element`, `trim_element` | `object_element` |
| `trim_element.warp_mode` | 0 | absent |
| `trim_element.global_trim_mode` | 0 (default trims) | absent |
| `trim_element.b_disable_trim_per_obj` | 0 | absent |

With no trim element, renderers fall back to whatever they do without one. That may or may not
match the "default trims" DEE signals explicitly. This hasn't been checked on hardware.

## Suggested fix

Add a trim element writer next to `build_payload_updates` in `libs/objects/src/oamd.cpp`, and have
`AtmosEncoder` emit one per payload: `warp_mode` 0, `global_trim_mode` 0, no per-object disable.
Optionally expose DEE-style `surround-trim=` and `height-trim=` options that write
`global_trim_mode` 2 (custom) configurations. The parser's six-configuration layout is a good
round-trip check.
