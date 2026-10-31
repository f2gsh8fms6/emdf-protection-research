# keys/

| File | What it is |
|---|---|
| `dee_emdf.key.b64` | The 32-byte HMAC key from DEE, base64-encoded |

The format is iclforge's signing key file. To read it in Python:

```python
import base64
key = base64.b64decode(open("keys/dee_emdf.key.b64").read())   # 32 bytes
```

The same key in hex: `566cef6642595a1aa2ed20dcb1a62efb4b38a65ce7b627390ced5a16e9fd679e`.

In the binary (`dee_audio_filter_ddp_atmos.so`) it is stored as a hex-string constant with every
byte XORed with `0x7a`. The [technical report](../docs/technical-report.md#3-where-it-lives-in-the-binary) explains where
it was found and how the extraction was confirmed.

> [!IMPORTANT]
> This key was extracted from a licensed binary and is published for interoperability research.
> See the provenance notice in the [main README](../README.md).

---

[← Back to the main README](../README.md)
