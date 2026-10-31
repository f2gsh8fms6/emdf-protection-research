# sample/

A short stream signed by DEE, for checking the key and the construction against real output.

| File | What it is |
|---|---|
| `out.ec3` | **DEE's output:** 32 DD+ JOC (Atmos) frames with valid seals, from a 1-second 5.1 test signal |
| `bodies.json` | Per-frame EMDF fields parsed from `out.ec3`: bit position, `key_id`, stored `prim`/`sec`, raw body hex |
| `protection/upd_NN.bin` | The exact bytes DEE passed to its HMAC, captured live with gdb, for frames 0 to 7 |

## Reading `protection/`

For frame *i* (0 to 7):

* `upd_{2+5i}.bin` is `covered`, the pre-mux core frame
* `upd_{3+5i}.bin` is `container`, the EMDF body with the seal bits zeroed

So frame 0 is `upd_02` + `upd_03`, frame 1 is `upd_07` + `upd_08`, and so on.

## What uses these files

| Tool | Needs |
|---|---|
| [`../emdf_protection.py`](../emdf_protection.py) self-test, and the hand demo in the [main README](../README.md#try-it-in-one-minute) | `bodies.json` + `protection/` |
| [`../scripts/emdf_tool.py`](../scripts/emdf_tool.py) `verify` | `out.ec3` |
| [`../scripts/emdf_rs_verify/`](../scripts/emdf_rs_verify/) | `out.ec3` + `protection/` |

---

[← Back to the main README](../README.md)
