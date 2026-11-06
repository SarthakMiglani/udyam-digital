"""GSTIN format, checksum and OCR-tolerant matching."""
import re, itertools
CH = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
def checksum_char(first14):
    tot = 0
    for i, c in enumerate(first14):
        v = CH.index(c) * (1 if i % 2 == 0 else 2)
        tot += v // 36 + v % 36
    return CH[(36 - tot % 36) % 36]
def valid_checksum(g):
    return len(g) == 15 and all(c in CH for c in g) and checksum_char(g[:14]) == g[14]
# position classes: D digit, L letter, A alnum, Z fixed
POS = "DDLLLLLDDDDLAZA"
D2L = {"0": "O", "1": "I", "5": "S", "8": "B", "2": "Z", "6": "G"}
L2D = {v: k for k, v in D2L.items()}
def format_ok(g):
    if len(g) != 15: return False
    for c, p in zip(g, POS):
        if p == "D" and not c.isdigit(): return False
        if p == "L" and not c.isalpha(): return False
        if p == "Z" and c != "Z": return False
        if p == "A" and c not in CH: return False
    return True
def candidates(raw):
    """All readings of an OCR string consistent with the GSTIN layout (O/0, I/1, S/5, B/8, Z/2, G/6 swaps)."""
    s = re.sub(r"[^A-Z0-9]", "", raw.upper())
    if len(s) != 15: return []
    opts = []
    for c, p in zip(s, POS):
        o = {c}
        if p == "D": o = {L2D.get(c, c)} if not c.isdigit() else {c}
        elif p == "L": o = {D2L.get(c, c)} if c.isdigit() else {c}
        elif p == "Z": o = {"Z"}
        else: o = {c, D2L.get(c, c), L2D.get(c, c)}
        opts.append(sorted(o))
    out = ["".join(t) for t in itertools.product(*opts)]
    return [g for g in out if format_ok(g)]
def hamming(a, b): return sum(x != y for x, y in zip(a, b)) if len(a) == len(b) else 99
def mask(g): return g[:2] + "•" * 8 + g[-5:] if g else g
