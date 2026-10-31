#!/usr/bin/env python3
"""Build premux.ec3 (emitted 32-bit header + DEE's captured `covered`, frmsiz patched) and map
`covered` onto the emitted frame. Usage: make_premux.py <sample-dir> <premux.ec3 out>"""
import sys

oracle, dest = sys.argv[1], sys.argv[2]
out = open(f"{oracle}/out.ec3", "rb").read()


def bits(b):
    return "".join(f"{x:08b}" for x in b)


premux, off = "", 0
for i in range(8):
    fs = (int.from_bytes(out[off + 2 : off + 4], "big") & 0x7FF) + 1
    F = bits(out[off : off + fs * 2])
    off += fs * 2
    A = bits(open(f"{oracle}/protection/upd_{2 + 5 * i:02d}.bin", "rb").read())

    s = F[:32] + A
    s += "0" * (-len(s) % 16)
    s = s[:21] + format(len(s) // 16 - 1, "011b") + s[32:]
    premux += s

    # Anchor-and-extend alignment: (covered bit, emitted bit, run length). Gaps between runs are
    # the bits the Atmos muxer inserted (BSI splice, per-block skiple, EMDF skip field).
    segs, a = [], 0
    while a + 32 <= len(A):
        p = F.find(A[a : a + 32])
        if p >= 0 and F.find(A[a : a + 32], p + 1) < 0:
            n = 0
            while a + n < len(A) and p + n < len(F) and A[a + n] == F[p + n]:
                n += 1
            segs.append((a, p, n))
            a += n
        else:
            a += 1
    covered_end = segs[-1][0] + segs[-1][2]
    print(f"frame {i}: covered={len(A)}b ends at emitted bit {segs[-1][1] + segs[-1][2]}/{len(F)} "
          f"(fully aligned: {covered_end == len(A)}) runs={segs}")

open(dest, "wb").write(int(premux, 2).to_bytes(len(premux) // 8, "big"))
