"""Smart KYC: consent gate -> OCR -> extract -> registry lookup -> cross-checks -> decision."""
import re, glob, os, datetime as dt, difflib
import cv2, numpy as np, pandas as pd, pytesseract
from .ocrlib import load, deskew, sharpen, ocr, text_mask
from . import gstin as G
from .. import config

D = config.DATA_DIR + "/"
TODAY = config.TODAY
GST = pd.read_csv(D + "mock_gstin_registry.csv").set_index("gstin")
UDY = pd.read_csv(D + "mock_udyam_registry.csv").set_index("udyam_number")
DOCS = ["gst_certificate", "udyam_certificate", "signatory_id", "address_proof"]
BOILER = ("Specimen", "Format for", "Fictional", "Accel YTL", "SYNTHETIC")

def mask_udyam(u): return u[:9] + "•••" + u[-4:] if u else u
def mask_id(s): return "•" * (len(s) - 3) + s[-3:] if s else s

# ---------- OCR with quality gate ----------
def passes(img):
    """Four renderings of the same page; letters like I/T/O/0 are read differently in each."""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY); m = 255 - text_mask(img)
    f = lambda a: cv2.resize(a, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    return [g, f(g), m, f(m)]

def read_doc(path, doc_type=None):
    img = load(path)
    img, angle = deskew(img)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.Laplacian(gray, cv2.CV_64F).var()
    txt = ocr(gray, 6)
    lines = [l.strip() for l in txt.splitlines() if l.strip() and not l.strip().startswith(BOILER)]
    reads = []
    if doc_type == "gst_certificate":
        for v in passes(img):
            m = re.search(r"GSTIN\s*([A-Z0-9 ]{14,17})", ocr(v, 6))
            if m and len(m.group(1).replace(" ", "")) == 15: reads.append(m.group(1).replace(" ", ""))
    return {"lines": lines, "angle": round(float(angle), 1), "sharpness": round(float(blur), 1), "gstin_reads": reads}

def readable(doc_type, lines):
    t = " ".join(lines)
    key = {"gst_certificate": r"GSTIN\s*[A-Z0-9]{10}", "udyam_certificate": r"Enterprise name\s+\S+",
           "signatory_id": r"Name\s+\S+|^Name$", "address_proof": r"Bill date\s*\d{4}-\d\d-\d\d"}[doc_type]
    return bool(re.search(key, t, re.M)) and len(lines) >= 5

# ---------- field extraction ----------
def val(lines, label, stop=None):
    t = "\n".join(lines)
    m = re.search(label + r"[ \t]*(.*)", t)
    return m.group(1).strip() if m else ""

def join_wrapped(parts):
    out = ""
    for p in parts:
        p = p.strip()
        if not out: out = p; continue
        if p and p[0].islower(): out += p                       # word split mid-way ("An" + "dhra")
        elif out[-1].isdigit() and p[:1].isdigit(): out += p    # pincode split mid-number
        else: out += " " + p
    return out

def split_pincode(addr):
    m = re.search(r"-+\s*(\d{6})\s*$", addr)
    return (addr[:m.start()].strip(" ,-"), m.group(1)) if m else (addr.strip(), "")

def parse_gst(lines):
    t = "\n".join(lines)
    d = {"gstin_raw": re.sub(r"\s", "", val(lines, r"GSTIN")),
         "legal_name": val(lines, r"Legal name"), "trade_name": val(lines, r"Trade name"),
         "constitution": val(lines, r"Constitution")}
    m = re.search(r"Address of principal\s*(.*?)\n\s*place of business\s*(.*?)\n\s*Date of liability", t, re.S)
    if m:
        d["address"], d["pincode"] = split_pincode(join_wrapped([m.group(1), m.group(2)]))
    d["liability_date"] = val(lines, r"Date of liability")
    return d

def parse_udyam(lines):
    t = "\n".join(lines)
    m = re.search(r"(UDYAM\s*-\s*[A-Z]{2}\s*-\s*[0O]{2}\s*-\s*[0-9OIS]{7})", t)
    num = re.sub(r"\s", "", m.group(1)) if m else ""
    if num:
        p = num.split("-"); p[2] = "00"; p[3] = p[3].replace("O", "0").replace("I", "1").replace("S", "5"); num = "-".join(p)
    return {"udyam": num if re.fullmatch(r"UDYAM-[A-Z]{2}-00-\d{7}", num) else "",
            "name": val(lines, r"Enterprise name"), "activity": val(lines, r"Major activity"),
            "city": val(lines, r"City"), "state": val(lines, r"State"), "date": val(lines, r"Date of registration")}

def parse_id(lines):
    L = lines
    def after(label):
        for i, l in enumerate(L):
            if l == label and i + 1 < len(L): return L[i + 1]
            if l.startswith(label + " "): return l[len(label):].strip()
        return ""
    return {"name": after("Name"), "designation": after("Designation"), "business": after("For business"),
            "id_no": after("ID no."), "valid_till": after("Valid till")}

def parse_bill(lines):
    t = "\n".join(lines)
    m = re.search(r"Supply address\s*(.*?)\n\s*Bill date", t, re.S)
    addr, pin = split_pincode(join_wrapped(m.group(1).split("\n"))) if m else ("", "")
    return {"billed_to": val(lines, r"Billed to"), "address": addr, "pincode": pin, "bill_date": val(lines, r"Bill date")}

PARSERS = {"gst_certificate": parse_gst, "udyam_certificate": parse_udyam, "signatory_id": parse_id, "address_proof": parse_bill}

# ---------- helpers ----------
def norm(s): return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()
def sim(a, b): return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()
def date(s):
    try: return dt.date.fromisoformat(s)
    except Exception: return None
def proprietor(legal):
    m = re.match(r"(.*?)\s*\(Prop\.\s*(.*)\)", legal)
    return (m.group(1).strip(), m.group(2).strip()) if m else (None, legal)

def resolve_gstin(reads):
    """Several OCR readings -> (status, gstin, note). Accept a reading only if it is a registry entry with a valid checksum."""
    reads = [reads] if isinstance(reads, str) else list(reads)
    votes = {}
    for r in reads:
        for c in G.candidates(r): votes[c] = votes.get(c, 0) + 1
    hits = [c for c in votes if c in GST.index and G.valid_checksum(c)]
    if hits:
        hit = max(hits, key=lambda c: votes[c])
        plain = [re.sub(r"[^A-Z0-9]", "", r.upper()) for r in reads]
        return "found", hit, ("" if hit in plain[:1] else "OCR reading was ambiguous (O/0, I/T style); resolved by checksum and registry")
    # no reading matches: report the most common reading and its nearest registry entry
    cands = [c for r in reads for c in G.candidates(r)] or [re.sub(r"[^A-Z0-9]", "", (reads[0] if reads else "").upper())]
    base = max(set(cands), key=cands.count)
    best = min(GST.index, key=lambda g: min([G.hamming(base, g)] + [G.hamming(c, g) for c in cands]))
    d = min([G.hamming(base, best)] + [G.hamming(c, best) for c in cands])
    chk = any(G.valid_checksum(c) for c in cands)
    pos = [i + 1 for i, (x, y) in enumerate(zip(base, best)) if x != y]
    return ("near_miss" if d <= 2 else "not_found"), (best if d <= 2 else ""), f"checksum {'ok' if chk else 'FAILS'}; closest registry entry differs at character position {', '.join(map(str, pos))}"

# ---------- main ----------
def check_applicant(kid, consent=False, typed_gstin=None, folder=D + "kyc_documents/"):
    """Run the checker on one of the 12 specimen applicants shipped with the case data."""
    paths = {t: f"{folder}{kid}_{t}.png" for t in DOCS if os.path.exists(f"{folder}{kid}_{t}.png")}
    return check_documents(paths, consent=consent, typed_gstin=typed_gstin, label=kid)


def check_documents(paths, consent=False, typed_gstin=None, label="applicant"):
    """paths: {doc_type: image path}. Consent gate first; nothing is read without it."""
    kid = label
    out = {"id": kid, "flags": [], "facts": {}}
    if not consent:
        out.update(decision="BLOCKED", reason="No consent recorded. Documents are not read until the applicant agrees."); return out
    docs, raw = {}, {}
    for dtype in DOCS:
        p = paths.get(dtype)
        if not p or not os.path.exists(p):
            if dtype != "udyam_certificate": out["flags"].append(("REUPLOAD", f"{dtype.replace('_', ' ')} not provided"))
            continue
        r = read_doc(p, dtype); raw[dtype] = r
        if not readable(dtype, r["lines"]):
            out["flags"].append(("REUPLOAD", f"{dtype.replace('_', ' ')} is unreadable (sharpness {r['sharpness']}); ask for a clearer photo")); continue
        if r["angle"] and abs(r["angle"]) >= 3: out["facts"][dtype + "_deskewed"] = f"{r['angle']}°"
        docs[dtype] = PARSERS[dtype](r["lines"])
    gst, udy, sig, bill = (docs.get(k) for k in DOCS)
    reg = None
    # --- GSTIN ---
    raw_g = (raw.get("gst_certificate", {}).get("gstin_reads") or [(gst or {}).get("gstin_raw")] if gst else None) or ([typed_gstin] if typed_gstin else None)
    raw_g = [x for x in (raw_g or []) if x] or None
    if gst is None and typed_gstin: out["facts"]["gstin_source"] = "typed by applicant (certificate unreadable)"
    if raw_g:
        st, g, note = resolve_gstin(raw_g)
        if st == "found":
            reg = GST.loc[g]; out["facts"]["gstin"] = G.mask(g); out["facts"]["gstin_status"] = reg.status
            if note: out["flags"].append(("INFO", note))
            if reg.status != "Active": out["flags"].append(("LIMIT", f"GSTIN is {reg.status}. GST-only products cannot be sold; offer the non-GST bundle or ask for a fresh registration"))
        elif st == "near_miss":
            out["flags"].append(("REUPLOAD", f"GSTIN on the certificate is not in the registry ({note}). Likely a typo or an altered document; ask the applicant to confirm the number")); out["facts"]["gstin"] = "not verified"
        else:
            out["flags"].append(("REUPLOAD", f"GSTIN not found in the registry ({note})"))
    # --- GST certificate vs registry ---
    if gst and reg is not None:
        if sim(gst["legal_name"], reg.legal_name) < 0.97:
            out["flags"].append(("REVIEW", f"Legal name on certificate ('{gst['legal_name']}') differs from the registry ('{reg.legal_name}')"))
        if gst["trade_name"] and sim(gst["trade_name"], reg.trade_name) < 0.97:
            out["flags"].append(("REVIEW", f"Trade name on certificate ('{gst['trade_name']}') differs from the registry ('{reg.trade_name}')"))
    # --- Udyam ---
    if udy is None and "udyam_certificate" in raw: pass
    if udy is not None:
        if not udy["udyam"]:
            out["flags"].append(("REVIEW", "Udyam certificate has no readable registration number; ask for the 19-character number"))
        elif udy["udyam"] not in UDY.index:
            out["flags"].append(("REUPLOAD", "Udyam number is not in the registry"))
        else:
            u = UDY.loc[udy["udyam"]]; out["facts"]["udyam"] = mask_udyam(udy["udyam"])
            if sim(udy["name"], u.enterprise_name) < 0.9: out["flags"].append(("REVIEW", f"Udyam enterprise name differs from the registry ('{u.enterprise_name}')"))
            if udy["activity"] and udy["activity"] != u.major_activity:
                out["flags"].append(("INFO", f"Udyam certificate says '{udy['activity']}', registry says '{u.major_activity}' (soft flag)"))
    elif "udyam_certificate" not in raw:
        out["flags"].append(("REVIEW", "No Udyam certificate. Ask for it, or record that the business is not Udyam-registered"))
    # --- name consistency across documents ---
    if gst and reg is not None:
        names = {"Udyam": (udy or {}).get("name"), "signatory ID": (sig or {}).get("business"), "address proof": (bill or {}).get("billed_to")}
        for k, v in names.items():
            if v and sim(v, reg.trade_name) < 0.9: out["flags"].append(("REVIEW", f"{k} names '{v}', registry trade name is '{reg.trade_name}'"))
    # --- signatory ---
    if sig:
        vt = date(sig["valid_till"])
        if vt and vt < TODAY: out["flags"].append(("REUPLOAD", f"Signatory ID expired on {vt}"))
        if gst and reg is not None and reg.constitution == "Proprietorship":
            owner, _ = proprietor(reg.legal_name)
            if owner and sim(sig["name"], owner) < 0.9:
                out["flags"].append(("REVIEW", f"Signatory '{sig['name']}' is not the proprietor ('{owner}'); needs an authorisation letter"))
        out["facts"]["signatory_id"] = mask_id(sig["id_no"])
    # --- address proof ---
    if bill:
        bd = date(bill["bill_date"])
        if bd is None: out["flags"].append(("REUPLOAD", "Bill date unreadable"))
        else:
            age = (TODAY - bd).days; out["facts"]["bill_age_days"] = age
            if age > 90: out["flags"].append(("REUPLOAD", f"Address proof is {age} days old (limit 90 days); ask for a recent bill"))
        if reg is not None:
            ra, rp = split_pincode(reg.principal_place_of_business)
            if bill["pincode"] != rp or sim(bill["address"], ra) < 0.85:
                out["flags"].append(("REVIEW", f"Address on the bill does not match the registered address ('{bill['address']} {bill['pincode']}' vs '{ra} {rp}')"))
    if gst is None and typed_gstin and reg is not None:
        out["flags"] = [(("REVIEW", "GST certificate image unreadable; verified against the GSTIN the applicant typed. Ask for a clearer copy before activation") if f[1].startswith("gst certificate is unreadable") else f) for f in out["flags"]]
    sev = [f[0] for f in out["flags"]]
    out["decision"] = ("REUPLOAD" if "REUPLOAD" in sev else "LIMITED" if "LIMIT" in sev else "REVIEW" if "REVIEW" in sev else "VERIFIED")
    out["parsed"] = docs
    return out
