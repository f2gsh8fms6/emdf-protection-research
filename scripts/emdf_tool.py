#!/usr/bin/env python3
"""Verify or (re)sign the EMDF protection of an E-AC-3 JOC (DD+ Atmos) stream, DEE-style.

    emdf_tool.py verify <in.ec3>
    emdf_tool.py sign   <in.ec3> <out.ec3>
    emdf_tool.py corrupt <in.ec3> <out.ec3>        # flip one prim bit per frame, keep CRC valid

Construction (reverse engineered from DEE, see docs/):
    A    = the syncframe with these holes excised, packed MSB-first and rounded to the NEAREST
           16-bit word ((n + 8) // 16 words; zero-padded up, or truncated down):
             [0, 32) syncword..frmsiz | infomdat element (flag + body) | addbsi element
             (addbsie + addbsil + bytes) | skipflde bit | every skip field (skiple, and skipl +
             skipfld when set) | [audio_end, frame_end) aux + crc tail
    B    = EMDF body (after the 16-bit sync and 16-bit length) with prim + sec zeroed
    d1   = HMAC-SHA-256(key, A || B);  prim = d1[:4];  sec = HMAC-SHA-256(key, d1)[:1]

Block-level positions (each block's skip point and the end of the audio data) need a full
E-AC-3 block parser, coupling included. They come from an instrumented iclforge decoder: set
FORGE to its path (see docs/reproduce.md). Everything else is parsed here.
"""
import base64
import hashlib
import hmac
import os
import re
import subprocess
import sys
import tempfile

KEY = bytes(b ^ 0x7A for b in bytes.fromhex(
    "2c16951c38232060d8975aa6cbdc54813142dc269dcc5d437697206c93871de4"))
FORGE = os.environ.get("FORGE", "/tmp/iclforge-build/bin/forge")


class Bits:
    def __init__(self, data: bytes, pos: int = 0):
        self.d, self.pos = data, pos

    def read(self, n: int) -> int:
        v = 0
        for _ in range(n):
            v = (v << 1) | ((self.d[self.pos >> 3] >> (7 - (self.pos & 7))) & 1)
            self.pos += 1
        return v

    def varbits(self, n: int) -> int:  # ETSI TS 102 366 variable_bits(n)
        v = 0
        while True:
            v += self.read(n)
            if not self.read(1):
                return v
            v = (v << n) + (1 << n)


def get_bit(d, p):
    return (d[p >> 3] >> (7 - (p & 7))) & 1


def set_bits(d: bytearray, p: int, val: int, n: int):
    for i in range(n):
        q = p + i
        if (val >> (n - 1 - i)) & 1:
            d[q >> 3] |= 0x80 >> (q & 7)
        else:
            d[q >> 3] &= ~(0x80 >> (q & 7)) & 0xFF


def pack(bitlist):
    out = bytearray((len(bitlist) + 7) // 8)
    for i, b in enumerate(bitlist):
        if b:
            out[i >> 3] |= 0x80 >> (i & 7)
    return bytes(out)


def crc16(data: bytes) -> int:
    crc = 0
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x8005) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def split_frames(data: bytes):
    off, frames = 0, []
    while off + 4 <= len(data) and data[off] == 0x0B and data[off + 1] == 0x77:
        size = ((int.from_bytes(data[off + 2:off + 4], "big") & 0x7FF) + 1) * 2
        frames.append((off, size))
        off += size
    return frames


def bsi_holes(f: bytes):
    """Walk an independent E-AC-3 bsi (Table E1.2). Returns the infomdat and addbsi ranges
    [start, end) and the skipflde bit."""
    r = Bits(f, 16)
    strmtyp = r.read(2); r.read(3); r.read(11)
    fscod = r.read(2)
    numblkscod = 3 if fscod == 3 else r.read(2)
    if fscod == 3:
        r.read(2)
    acmod = r.read(3); lfeon = r.read(1); r.read(5)  # bsid
    for _ in range(2 if acmod == 0 else 1):
        r.read(5)
        if r.read(1):
            r.read(8)
    if strmtyp == 1 and r.read(1):
        r.read(16)
    nblks = 6 if numblkscod == 3 else numblkscod + 1
    if r.read(1):  # mixmdate
        if acmod > 2: r.read(2)
        if (acmod & 1) and acmod > 2: r.read(6)
        if acmod & 4: r.read(6)
        if lfeon and r.read(1): r.read(5)
        if strmtyp == 0:
            if r.read(1): r.read(6)
            if acmod == 0 and r.read(1): r.read(6)
            if r.read(1): r.read(6)
            mixdef = r.read(2)
            if mixdef == 1: r.read(5)
            elif mixdef == 2: r.read(12)
            elif mixdef == 3:
                mixdeflen = r.read(5)   # NB: read first, then advance -- "r.pos += (r.read(5)+2)*8"
                r.pos += (mixdeflen + 2) * 8  # would use the stale pre-read pos (augmented assign)
            if acmod < 2:
                if r.read(1): r.read(14)
                if acmod == 0 and r.read(1): r.read(14)
            if r.read(1):  # frmmixcfginfoe
                if numblkscod == 0: r.read(5)
                else:
                    for _ in range(nblks):
                        if r.read(1): r.read(5)
    info_start = r.pos
    if r.read(1):  # infomdate
        r.read(5)
        if acmod == 2: r.read(4)
        if acmod >= 6: r.read(2)
        if r.read(1): r.read(8)
        if acmod == 0 and r.read(1): r.read(8)
        if fscod < 3: r.read(1)
    info = (info_start, r.pos)
    if strmtyp == 0 and numblkscod != 3: r.read(1)  # convsync
    if strmtyp == 2 and (numblkscod == 3 or r.read(1)): r.read(6)
    addbsi_start = r.pos
    if r.read(1):
        addbsil = r.read(6)     # read first, then advance (see mixdef note above)
        r.pos += (addbsil + 1) * 8
    addbsi = (addbsi_start, r.pos)
    # audfrm up to skipflde
    if numblkscod == 3: r.read(2)  # expstre, ahte
    r.read(2 + 1 + 1 + 1 + 1 + 1 + 1)  # snroffststr transproce blkswe dithflage bamode frmfgaincode dbaflde
    return info, addbsi, r.pos


def block_positions(path: str):
    """Per frame: [(skip point, skipl or None)], audio_end - from the instrumented decoder."""
    with tempfile.TemporaryDirectory() as td:
        p = subprocess.run([FORGE, "decode", path, os.path.join(td, "x.wav")],
                           env={**os.environ, "ICLF_BITPOS": "1"}, capture_output=True, text=True)
    frames, skips, big = [], [], {}
    for line in p.stderr.splitlines():
        if m := re.search(r"skippt blk=\d+ pos=(\d+)", line):
            skips.append(int(m[1]))
        elif m := re.search(r"skip blk=\d+ pos=(\d+) skipl=(\d+)", line):
            big[int(m[1])] = int(m[2])   # keyed by BIT POSITION, matching the skippt entries
        elif m := re.search(r"audio_end pos=(\d+)", line):
            frames.append(([(s, big.get(s)) for s in skips], int(m[1])))
            skips, big = [], {}
    if not frames:
        sys.exit(f"no BITPOS output from {FORGE}: is it the instrumented build?")
    return frames


def emdf_fields(f: bytes, start: int):
    """Walk an EMDF container at bit `start` (0x5838). Returns (body_start, body_bits, prim_pos,
    prim_bits, sec_bits)."""
    r = Bits(f, start)
    assert r.read(16) == 0x5838
    length = r.read(16)
    body = r.pos
    if r.read(2) == 3: r.varbits(2)
    if r.read(3) == 7: r.varbits(3)
    end_bit = len(f) * 8
    while True:
        if r.pos + 5 > end_bit:   # bounds guard, as in emdf.rs field_offsets
            return None
        pid = r.read(5)
        if pid == 0:
            break
        if pid == 0x1F: r.varbits(5)
        smploffste = r.read(1)
        if smploffste: r.read(12)
        if r.read(1): r.varbits(11)
        if r.read(1): r.varbits(2)
        if r.read(1): r.read(8)
        if not r.read(1):
            aligned = 0
            if not smploffste:
                aligned = r.read(1)
                if aligned: r.read(2)
            if smploffste or aligned: r.read(7)
        sz = r.varbits(8)   # read first, then advance (augmented assign would use the stale pos)
        r.pos += sz * 8
    lens = [0, 8, 32, 128]
    pb, sb = lens[r.read(2)], lens[r.read(2)]
    return body, length * 8, r.pos, pb, sb


def frame_tag(f: bytes, skips, audio_end):
    info, addbsi, skipflde = bsi_holes(f)
    holes = [(0, 32), info, addbsi, (skipflde, skipflde + 1)]
    container = None
    for pos, skipl in skips:
        if skipl is None:
            holes.append((pos, pos + 1))
        else:
            holes.append((pos, pos + 10 + 8 * skipl))
            if container is None and int.from_bytes(f, "big") >> (len(f) * 8 - pos - 26) & 0xFFFF == 0x5838:
                container = pos + 10
    holes.append((audio_end, len(f) * 8))
    if container is None:
        return None
    kept, cur = [], 0
    for a, b in sorted(holes):
        kept.extend(get_bit(f, q) for q in range(cur, a))
        cur = max(cur, b)
    target = ((len(kept) + 8) // 16) * 16
    kept = (kept + [0] * 16)[:target]
    body, nbits, prim_pos, pb, sb = emdf_fields(f, container)
    b = [get_bit(f, body + k) for k in range(nbits)]
    for k in range(prim_pos - body, prim_pos - body + pb + sb):
        b[k] = 0
    d1 = hmac.new(KEY, pack(kept) + pack(b), hashlib.sha256).digest()
    prim = int.from_bytes(d1[:4], "big") >> (32 - pb) if pb <= 32 else int.from_bytes(d1[:pb // 8], "big")
    sec = hmac.new(KEY, d1, hashlib.sha256).digest()[0] >> (8 - sb) if sb else 0
    return prim_pos, pb, sb, prim, sec


def main():
    cmd, src = sys.argv[1], sys.argv[2]
    data = bytearray(open(src, "rb").read())
    frames = split_frames(data)
    pos = block_positions(src)
    assert len(pos) == len(frames), (len(pos), len(frames))
    stats = {"valid": 0, "prim_only": 0, "invalid": 0, "no_container": 0}
    for idx, ((off, size), (skips, end)) in enumerate(zip(frames, pos)):
        f = bytes(data[off:off + size])
        t = frame_tag(f, skips, end)
        if t is None:
            stats["no_container"] += 1
            continue
        prim_pos, pb, sb, prim, sec = t
        r = Bits(f, prim_pos)
        have_p, have_s = r.read(pb), r.read(sb)
        if cmd == "verify":
            if have_p == prim and have_s == sec: stats["valid"] += 1
            elif have_p == prim: stats["prim_only"] += 1
            else: stats["invalid"] += 1
            if idx < 3 or have_p != prim:
                print(f"frame {idx}: prim {have_p:08x} want {prim:08x}  sec {have_s:02x} want {sec:02x}")
            continue
        fb = bytearray(f)
        if cmd == "sign":
            set_bits(fb, prim_pos, prim, pb)
            set_bits(fb, prim_pos + pb, sec, sb)
        elif cmd == "corrupt":
            set_bits(fb, prim_pos, have_p ^ 1, pb)
        c = crc16(bytes(fb[2:-2]))
        fb[-2:] = c.to_bytes(2, "big")
        data[off:off + size] = fb
    if cmd == "verify":
        print(f"{src}: {stats}")
        sys.exit(0 if stats["invalid"] == stats["prim_only"] == 0 else 1)
    open(sys.argv[3], "wb").write(data)
    print(f"{cmd}: wrote {sys.argv[3]} ({len(frames) - stats['no_container']} frames)")


if __name__ == "__main__":
    main()
