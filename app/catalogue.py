"""Catalogue rules engine. This module, not the LLM, decides what may be sold and at what price.

Eligibility comes from product_catalogue.csv: city tier, minimum employees, minimum sites,
GSTIN needed, and "needs one of" dependencies. Prices are catalogue midpoints.
"""
import math
import pandas as pd
from . import config

CAT = pd.read_csv(f"{config.DATA_DIR}/product_catalogue.csv").set_index("product_id")
_CITY = pd.read_csv(f"{config.DATA_DIR}/smb_leads.csv", usecols=["city", "city_tier", "state"]).drop_duplicates("city")
CITY_TIER = {r.city.lower(): int(r.city_tier) for r in _CITY.itertuples()}
CITY_NAME = {r.city.lower(): r.city for r in _CITY.itertuples()}

# GSTIN states that allow GST-only products. "Declared" = owner says yes, not yet checked at KYC.
GST_OK = {"Active", "Declared"}


def name(pid): return CAT.loc[pid, "product_name"]
def unit_price(pid): return round((CAT.loc[pid, "price_min_inr_per_month"] + CAT.loc[pid, "price_max_inr_per_month"]) / 2)
def tiers(pid): return [int(t) for t in str(CAT.loc[pid, "available_city_tiers"]).split(";")]
def needs_one_of(pid):
    v = CAT.loc[pid, "requires_one_of"]
    return v.split("|") if isinstance(v, str) and v else []


def eligibility(pid, profile):
    """Hard reasons this product cannot be sold to this business as it stands. Empty list = eligible.
    Dependencies are checked at bundle level, because a quote can add the base product."""
    p, why = CAT.loc[pid], []
    if int(profile["tier"]) not in tiers(pid):
        why.append({"rule": "city_tier", "detail": f"sold in tier {'/'.join(map(str, tiers(pid)))} cities only"})
    if profile["employees"] < p.min_employees:
        why.append({"rule": "min_employees", "detail": f"needs {p.min_employees}+ employees"})
    if profile["sites"] < p.min_sites:
        why.append({"rule": "min_sites", "detail": f"needs {p.min_sites}+ sites"})
    if p.requires_gstin == "Y" and profile.get("gst_status") not in GST_OK:
        why.append({"rule": "gstin_required", "detail": "needs an active GSTIN"})
    return why


def check_bundle(bundle, profile):
    """Every rule violation in a bundle {pid: qty}. Used for quotes, add-ons and the audit of past sales."""
    v = []
    for pid, q in bundle.items():
        for w in eligibility(pid, profile):
            v.append({"product": pid, **w})
        deps = needs_one_of(pid)
        if deps and not any(d in bundle for d in deps):
            v.append({"product": pid, "rule": "dependency", "detail": "needs one of " + ", ".join(name(d) for d in deps)})
        if CAT.loc[pid, "unit"] == "per site" and q > profile["sites"]:
            v.append({"product": pid, "rule": "quantity", "detail": f"per-site product, only {profile['sites']} site(s)"})
        if q < 1:
            v.append({"product": pid, "rule": "quantity", "detail": "quantity must be at least 1"})
    return v


def price(bundle):
    """Monthly recurring, one-time setup, contract length and typical install days for a bundle."""
    lines, monthly, setup = [], 0, 0
    for pid, q in bundle.items():
        u, s = unit_price(pid), int(CAT.loc[pid, "one_time_setup_inr"])
        lines.append({"pid": pid, "name": name(pid), "unit": CAT.loc[pid, "unit"], "qty": q,
                      "unit_price": u, "monthly": u * q, "setup": s * q})
        monthly += u * q; setup += s * q
    contract = max([int(CAT.loc[p, "min_contract_months"]) for p in bundle] or [1])
    install = max([int(CAT.loc[p, "typical_install_days"]) for p in bundle] or [0])
    return {"lines": lines, "monthly": monthly, "setup": setup, "contract_months": contract, "install_days": install}


# ---------- segment inference (from the case data: segment is driven by type of business and size) ----------
MULTI_TYPES = ["chain", "hotel group"]
MANUF_TYPES = ["unit", "workshop", "press"]
PROF_TYPES = ["architecture", "ca firm", "coaching", "clinic", "lab", "insurance", "law", "agency", "studio"]
MICRO_TYPES = ["shop", "store", "kirana", "salon", "bakery", "boutique", "pharmacy", "optician"]


def infer_segment(business_type, employees, sites):
    t = (business_type or "").lower()
    if sites >= 3 or any(k in t for k in MULTI_TYPES): return "multisite"
    if any(k in t for k in MANUF_TYPES) or (employees >= 12 and any(k in t for k in ["factory", "manufactur"])): return "manufacturer"
    if any(k in t for k in PROF_TYPES): return "professional"
    if any(k in t for k in MICRO_TYPES) or employees <= 6: return "micro"
    return "professional" if employees >= 7 else "micro"


SEGMENT_LABEL = {"micro": "Micro retail & services", "professional": "Professional offices",
                 "multisite": "Small multi-site business", "manufacturer": "Small manufacturer"}


# ---------- bundle building ----------
def _conn(profile, serv, per_site=False, big=False):
    """Pick the connectivity product for each site. Fibre first; 5G AirFiber when fibre is not feasible at the pincode."""
    sites = profile["sites"] if per_site else 1
    if serv.get("fibre"):
        pid = "P02" if big else "P01"
        return pid, sites, None
    if serv.get("airfiber") and "P04" in CAT.index:
        return "P04", sites, "Fibre is not feasible at this pincode, so we switched to 5G AirFiber instead of losing the order."
    return None, 0, "Neither fibre nor 5G AirFiber is confirmed at this pincode: a surveyor will confirm before any price is final."


NEED_PRODUCTS = {  # what the owner can tick in the advisor -> products added to the recommended bundle
    "internet": [], "mobile": ["P07"], "whatsapp": ["P15"], "sms": ["P14"], "email": ["P16"],
    "security": ["P20"], "cctv": ["P23"], "pos": ["P19"], "backup": ["P17"], "website": ["P18"], "tollfree": ["P13"],
    "wifi": ["P22"], "failover": ["P09"], "static_ip": ["P11"], "firewall": ["P21"],
}


def _qty(pid, profile, seg):
    """Quantities follow the pattern in what real customers bought (activated bundles in smb_leads.csv)."""
    e, s = profile["employees"], profile["sites"]
    per_site = CAT.loc[pid, "unit"] == "per site"
    if pid in ("P07",): return min(max(1, math.ceil(e / 2)), 3) if seg == "micro" else min(max(2, math.ceil(e / 6)), 5)
    if pid == "P08": return 4 if seg == "multisite" else 5 if seg == "manufacturer" else min(max(2, math.ceil(e / 6)), 4)
    if pid == "P16": return {"professional": min(max(3, round(e * 0.6)), 25), "manufacturer": 10, "multisite": 10}.get(seg, min(e, 5))
    if pid == "P20": return min(max(3, round(e * 0.4)), 25) if seg == "professional" else 10
    if pid == "P23": return 2 * s if seg == "multisite" else 2 if seg == "micro" else 4
    if pid == "P19": return s if seg == "multisite" else 1
    if pid == "P24": return 10
    if pid in ("P12",): return 3
    return s if per_site else 1


def recommend(profile, serv, needs=None):
    """Build a starter and a recommended bundle for this business, then let the rules strip what is not allowed.

    Returns dict(starter, recommended, notes, removed). Defaults come from what activated customers in each
    segment actually bought (attach rate >= ~40%); other products are optional add-ons the owner can toggle.
    """
    needs = needs or []
    seg = profile.get("segment") or infer_segment(profile.get("business_type"), profile["employees"], profile["sites"])
    profile = {**profile, "segment": seg}
    notes, removed = [], []
    big = seg in ("professional", "multisite") and profile["employees"] >= 5
    conn, cq, cnote = _conn(profile, serv, per_site=seg == "multisite", big=big)
    if cnote: notes.append(cnote)
    core, extras = {}, {}
    if conn: core[conn] = cq
    if seg == "micro":
        core["P07"] = _qty("P07", profile, seg); extras = {"P19": 1}
    elif seg == "professional":
        core["P16"] = _qty("P16", profile, seg); core["P08"] = _qty("P08", profile, seg)
        extras = {"P20": _qty("P20", profile, seg), "P17": 1}
    elif seg == "multisite":
        core["P08"] = _qty("P08", profile, seg)
        extras = {"P09": profile["sites"], "P19": profile["sites"], "P23": _qty("P23", profile, seg)}
    else:  # manufacturer
        core["P08"] = _qty("P08", profile, seg); core["P16"] = _qty("P16", profile, seg)
        if profile.get("gst_status") in GST_OK and serv.get("leased", True): core["P05"] = 1  # dedicated line only with GSTIN
        extras = {"P20": 10, "P21": 1}
        if "P05" in core and conn: core.pop(conn, None)  # leased line replaces shared fibre as the main link
    # Starter = the smallest bundle the business can run on: entry fibre (or AirFiber), no premium links.
    small = {"P02": "P01"}.get(conn, conn)
    starter = {k: v for k, v in core.items() if k not in ("P05", "P02")}
    if small: starter[small] = cq
    if seg == "professional": starter.pop("P08", None)   # office staff start without mobile lines
    rec = {**core, **extras}
    for n in needs:
        for pid in NEED_PRODUCTS.get(n, []):
            rec.setdefault(pid, _qty(pid, profile, seg))
    # ---- the rules decide: strip anything not allowed, with the reason ----
    def clean(b, label):
        b = dict(b)
        for pid in list(b):
            why = eligibility(pid, profile)
            if why:
                removed.append({"product": pid, "name": name(pid), "tier": label, "reasons": why}); b.pop(pid)
        for pid in list(b):  # dependency: add the base product if the bundle has none, else drop
            deps = needs_one_of(pid)
            if deps and not any(d in b for d in deps):
                base = conn if conn and conn in deps else None
                if base: b[base] = max(b.get(base, 0), 1)
                else:
                    removed.append({"product": pid, "name": name(pid), "tier": label,
                                    "reasons": [{"rule": "dependency", "detail": "needs one of " + ", ".join(name(d) for d in deps)}]}); b.pop(pid)
        return b
    starter, rec = clean(starter, "starter"), clean(rec, "recommended")
    seen, uniq = set(), []
    for r in removed:
        k = (r["product"], tuple(w["rule"] for w in r["reasons"]))
        if k not in seen: seen.add(k); uniq.append(r)
    return {"segment": seg, "segment_label": SEGMENT_LABEL[seg], "starter": starter, "recommended": rec,
            "notes": notes, "removed": uniq}


def addon_options(profile, bundle):
    """Every other product, with whether it can be added to this bundle and why not."""
    out = []
    for pid in CAT.index:
        if pid in bundle: continue
        why = eligibility(pid, profile)
        deps = needs_one_of(pid)
        if not why and deps and not any(d in bundle for d in deps):
            why = [{"rule": "dependency", "detail": "needs one of " + ", ".join(name(d) for d in deps) + " in the bundle"}]
        out.append({"pid": pid, "name": name(pid), "category": CAT.loc[pid, "category"], "unit": CAT.loc[pid, "unit"], "unit_price": unit_price(pid),
                    "setup": int(CAT.loc[pid, "one_time_setup_inr"]), "default_qty": _qty(pid, profile, profile.get("segment", "micro")),
                    "allowed": not why, "why_not": why})
    return out


def blocked_by_gst(profile, serv, needs=None):
    """Products an owner without an active GSTIN cannot buy yet, to show what a GST registration would unlock."""
    p2 = {**profile, "gst_status": "Active"}
    return [name(pid) for pid in CAT.index if CAT.loc[pid, "requires_gstin"] == "Y" and not eligibility(pid, p2)]
