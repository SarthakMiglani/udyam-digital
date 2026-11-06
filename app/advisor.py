"""Advisor: a short conversation (6 questions) that turns what the owner says into a structured business profile.

The conversation itself is a scripted state machine in Hindi and English, so it always works and the demo never
depends on a network. An optional hosted LLM (llm.py) can read free text more flexibly, but it only fills the same
profile fields, and everything it returns is validated. It never sets eligibility or price: catalogue.py does.
"""
import re
from . import catalogue as cat, llm

STEPS = ["lang", "business", "size", "location", "internet", "spend", "gst", "needs", "done"]

T = {
    "en": {
        "greet": "Namaste! I am the Accel Business advisor. I will ask a few quick questions, then recommend one bundle with one monthly price. Which language do you prefer?",
        "business": "What kind of business do you run? For example a kirana store, clinic, CA firm, restaurant chain or factory.",
        "size": "How many people work there, and how many locations (shops, branches, plants) do you have? For example: 5 staff, 1 location.",
        "size_retry": "I did not catch the numbers. Please tell me staff and locations, for example: 5 staff, 1 location.",
        "location": "Which city are you in, and what is your pincode? For example: Pune 411001.",
        "location_retry": "Please share your city (and pincode if you have it). We serve tier 1 and tier 2 cities such as Delhi, Pune, Jaipur or Kochi.",
        "internet": "What internet do you use today?",
        "spend": "Roughly how much do you spend in a month on phone and internet in total? A number in rupees is fine.",
        "spend_retry": "A rough number in rupees is enough, for example 1500.",
        "gst": "Is your business GST registered? (I only ask yes or no now. The number comes later, after your consent.)",
        "needs": "Anything specific you want included? Tick what matters, or choose Skip.",
        "thanks": "Thank you. Let me put together your bundle.",
        "unclear": "I could not understand that. A person from our team will call you back shortly so you do not have to repeat yourself.",
        "outside": "We do not have {city} in our tier 1 and 2 coverage list yet. A person from our team will call you back to check what is possible.",
        "skip": "Skip", "done": "Done",
    },
    "hi": {
        "greet": "Namaste! Main Accel Business ka salahkaar hoon. Kuch chhote sawal poochhunga, phir ek bundle aur ek mahine ka ek daam bataunga. Aap kaunsi bhasha chahenge?",
        "business": "Aap kaunsa business chalate hain? Jaise kirana dukaan, clinic, CA firm, restaurant chain ya factory.",
        "size": "Wahan kitne log kaam karte hain aur kitni jagah (dukaan, branch, plant) hain? Jaise: 5 staff, 1 jagah.",
        "size_retry": "Mujhe sankhya samajh nahi aayi. Kripya staff aur jagah batayein, jaise: 5 staff, 1 jagah.",
        "location": "Aap kaunse shehar mein hain aur pincode kya hai? Jaise: Pune 411001.",
        "location_retry": "Kripya shehar ka naam batayein (pincode ho to wo bhi). Hum tier 1 aur tier 2 shehar jaise Delhi, Pune, Jaipur, Kochi mein seva dete hain.",
        "internet": "Abhi aap kaunsa internet use karte hain?",
        "spend": "Phone aur internet par mahine mein lagbhag kitna kharch hota hai? Rupaye mein andaza kaafi hai.",
        "spend_retry": "Rupaye mein andaza kaafi hai, jaise 1500.",
        "gst": "Kya aapka business GST registered hai? (Abhi sirf haan ya na. GST number baad mein, aapki sahmati ke baad.)",
        "needs": "Koi khaas cheez chahiye? Jo zaroori hai chun lein, ya Skip dabayein.",
        "thanks": "Dhanyavaad. Main aapka bundle taiyaar karta hoon.",
        "unclear": "Mujhe samajh nahi aaya. Hamari team ka koi vyakti aapko jaldi call karega, aapko dobara batana nahi padega.",
        "outside": "{city} abhi hamari tier 1 aur 2 suchi mein nahi hai. Hamari team ka koi vyakti call karke dekhega ki kya ho sakta hai.",
        "skip": "Skip", "done": "Ho gaya",
    },
}

BUSINESS_CHIPS = ["Kirana store", "Salon", "Pharmacy", "Clinic", "CA firm", "Restaurant chain", "Auto-parts unit"]
INTERNET_CHIPS = [("Mobile hotspot", {"en": "Mobile hotspot", "hi": "Mobile hotspot"}),
                  ("Home broadband", {"en": "Home broadband", "hi": "Ghar ka broadband"}),
                  ("Business broadband", {"en": "Business broadband", "hi": "Business broadband"}),
                  ("Leased line", {"en": "Leased line", "hi": "Leased line"}),
                  ("Mixed per site", {"en": "Different at each site", "hi": "Har jagah alag"})]
NEED_CHIPS = [("mobile", "Mobile lines", "Mobile lines"), ("whatsapp", "WhatsApp for customers", "Customers ke liye WhatsApp"),
              ("email", "Business email", "Business email"), ("security", "Security", "Security"),
              ("cctv", "CCTV", "CCTV"), ("pos", "POS / billing", "POS / billing"), ("backup", "Cloud backup", "Cloud backup")]

# keyword -> canonical business type (English, Hinglish and Hindi words)
KEYWORDS = [
    (["kirana", "grocery", "general store", "dukaan", "दुकान", "किराना"], "Kirana store"),
    (["salon", "parlour", "parlor", "beauty"], "Salon"), (["pharmacy", "chemist", "medical store", "dawai"], "Pharmacy"),
    (["bakery"], "Bakery"), (["sweet"], "Sweet shop"), (["boutique", "tailor"], "Boutique"), (["hardware"], "Hardware store"),
    (["stationery"], "Stationery shop"), (["mobile repair", "mobile shop"], "Mobile repair shop"), (["optician", "optical"], "Optician"),
    (["dental"], "Dental clinic"), (["physio"], "Physiotherapy clinic"), (["clinic", "doctor", "hospital"], "Clinic"),
    (["ca firm", "chartered", "accountant", "ca "], "CA firm"), (["law", "lawyer", "advocate"], "Law office"),
    (["coaching", "tuition", "classes"], "Coaching centre"), (["travel"], "Travel agency"), (["diagnostic", "pathology", "lab"], "Diagnostic lab"),
    (["architect"], "Architecture studio"), (["insurance"], "Insurance agency"), (["real estate", "property", "broker"], "Real estate agency"),
    (["restaurant chain", "cafe chain"], "Restaurant chain"), (["pharmacy chain"], "Pharmacy chain"), (["hotel"], "Budget hotel group"),
    (["gym"], "Gym chain"), (["pre-school", "preschool", "play school"], "Pre-school chain"),
    (["retail chain", "showroom", "stores chain", "chain"], "Retail chain"), (["restaurant", "cafe", "dhaba"], "Restaurant"),
    (["auto-parts", "auto parts"], "Auto-parts unit"), (["textile"], "Textile unit"), (["packaging"], "Packaging unit"),
    (["plastic"], "Plastic moulding unit"), (["printing"], "Printing press"), (["furniture"], "Furniture workshop"),
    (["food processing"], "Food processing unit"), (["factory", "manufactur", "unit", "workshop", "plant"], "Manufacturing unit"),
]
CITY_ALIASES = {"bombay": "mumbai", "bangalore": "bengaluru", "madras": "chennai", "calcutta": "kolkata", "vizag": "visakhapatnam",
                "baroda": "vadodara", "mysore": "mysuru", "cochin": "kochi", "new delhi": "delhi"}
WORDNUM = {"ek": 1, "one": 1, "do": 2, "two": 2, "teen": 3, "three": 3, "char": 4, "four": 4, "paanch": 5, "panch": 5, "five": 5,
           "chhe": 6, "che": 6, "six": 6, "saat": 7, "seven": 7, "aath": 8, "eight": 8, "nau": 9, "nine": 9, "das": 10, "ten": 10}
DEVA = str.maketrans("०१२३४५६७८९", "0123456789")
YES = ["yes", "y", "haan", "han", "ha", "haa", "hai", "ji", "registered", "हाँ", "हां"]
NO = ["no", "n", "nahi", "nahin", "na", "nope", "not", "नहीं", "नही"]


def _nums(text):
    t = text.translate(DEVA).lower().replace(",", "")
    out = []
    for m in re.finditer(r"\d+(?:\.\d+)?\s*(?:k|hazaar|hazar|thousand)?|[a-z]+", t):
        tok = m.group(0).strip()
        mm = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(k|hazaar|hazar|thousand)?", tok)
        if mm:
            v = float(mm.group(1)) * (1000 if mm.group(2) else 1); out.append(int(v) if v == int(v) else v)
        elif tok in WORDNUM: out.append(WORDNUM[tok])
    return out


def parse_business(text):
    t = " " + text.lower() + " "
    for words, canon in KEYWORDS:
        if any(w in t for w in words): return canon
    return None


def parse_size(text):
    t = text.translate(DEVA).lower()
    nums = [n for n in _nums(t) if 0 < n < 5000]
    if not nums: return None
    emp, sites = int(nums[0]), 1
    if len(nums) > 1: sites = int(nums[1])
    else:
        m = re.search(r"(\d+)\s*(?:locations?|branch(?:es)?|shops?|outlets?|stores?|sites?|jagah)", t)
        if m and re.search(r"(?:staff|people|employees?|log|workers?)", t): sites = int(m.group(1))
    return {"employees": max(1, emp), "sites": max(1, sites)}


def parse_location(text):
    t = text.lower()
    for a, c in CITY_ALIASES.items(): t = t.replace(a, c)
    city = next((c for c in cat.CITY_TIER if c in t), None)
    pin = re.search(r"\b(\d{6})\b", text.translate(DEVA))
    return {"city": cat.CITY_NAME[city] if city else None, "pincode": pin.group(1) if pin else None,
            "raw": re.sub(r"\d{6}", "", text).strip(" ,")}


def parse_internet(text):
    t = text.lower()
    for key, labels in INTERNET_CHIPS:
        if any(l.lower() in t for l in labels.values()) or key.lower() in t: return key
    if "hotspot" in t or "mobile" in t or "data" in t: return "Mobile hotspot"
    if "lease" in t: return "Leased line"
    if "business" in t: return "Business broadband"
    if "home" in t or "ghar" in t or "wifi" in t or "broadband" in t: return "Home broadband"
    return None


def parse_spend(text):
    n = [x for x in _nums(text) if x >= 50]
    return int(n[0]) if n else None


def parse_yesno(text):
    w = re.findall(r"[a-zऀ-ॿ]+", text.lower())
    if any(x in NO for x in w): return False
    if any(x in YES for x in w): return True
    return None


def new_session(sid):
    return {"sid": sid, "lang": "en", "step": "lang", "profile": {}, "needs": [], "tries": {}, "done": False, "escalate": None}


def _bot(text, chips=None, multi=False, input_type="text"):
    return {"role": "bot", "text": text, "chips": chips or [], "multi": multi, "input": input_type}


def first_message():
    return [_bot(T["en"]["greet"] + "\n\n" + T["hi"]["greet"], [{"label": "English", "value": "English"}, {"label": "हिन्दी / Hindi", "value": "Hindi"}], input_type="none")]


def _prompt(state, key):
    L = state["lang"]
    if key == "business": return _bot(T[L]["business"], [{"label": c, "value": c} for c in BUSINESS_CHIPS])
    if key == "internet": return _bot(T[L]["internet"], [{"label": lab[L], "value": k} for k, lab in INTERNET_CHIPS], input_type="none")
    if key == "gst":
        yes, no = ("Yes", "No") if L == "en" else ("Haan", "Nahi")
        return _bot(T[L]["gst"], [{"label": yes, "value": "yes"}, {"label": no, "value": "no"}], input_type="none")
    if key == "needs":
        chips = [{"label": n[1] if L == "en" else n[2], "value": n[0]} for n in NEED_CHIPS]
        chips.append({"label": T[L]["done"], "value": "__done__"})
        return _bot(T[L]["needs"], chips, multi=True, input_type="none")
    return _bot(T[L][key])


def _retry(state, key, retry_key=None):
    n = state["tries"].get(key, 0) + 1; state["tries"][key] = n
    if n >= 2:  # do not trap the owner in a loop: hand over to a person with what we already know
        state["escalate"] = f"Advisor could not understand the answer to '{key}' twice"
        state["done"] = True; state["step"] = "done"
        return [_bot(T[state["lang"]]["unclear"], input_type="none")]
    return [_bot(T[state["lang"]][retry_key or key + "_retry"] if (retry_key or key + "_retry") in T[state["lang"]] else T[state["lang"]][key])]


def handle(state, text):
    """Advance the conversation by one user message. Returns the bot's reply messages. Mutates state."""
    text = (text or "").strip()
    step, L, p = state["step"], state["lang"], state["profile"]
    llm_fields = llm.extract(step, text, L) if step in ("business", "size", "location", "spend") else None
    if step == "lang":
        state["lang"] = "hi" if re.search(r"hindi|हिन्दी|hi\b|हिंदी", text.lower()) else "en"
        state["step"] = "business"; p["lang"] = state["lang"]
        return [_prompt(state, "business")]
    if step == "business":
        b = (llm_fields or {}).get("business_type") or parse_business(text) or (text[:40] if text else None)
        if not b: return _retry(state, "business", "business")
        p["business_type"] = b; state["step"] = "size"; return [_prompt(state, "size")]
    if step == "size":
        s = (llm_fields or {}).get("size") or parse_size(text)
        if not s: return _retry(state, "size")
        p.update(s); state["step"] = "location"; return [_prompt(state, "location")]
    if step == "location":
        loc = parse_location(text)
        if not loc["city"]:
            if loc["raw"] and state["tries"].get("location", 0) >= 1:  # named a place we do not cover
                state["escalate"] = f"Location outside tier 1-2 coverage list: {loc['raw'][:40]}"
                state["done"] = True; state["step"] = "done"
                return [_bot(T[L]["outside"].format(city=loc["raw"][:30]), input_type="none")]
            return _retry(state, "location")
        p.update({"city": loc["city"], "pincode": loc["pincode"], "tier": cat.CITY_TIER[loc["city"].lower()]})
        state["step"] = "internet"; return [_prompt(state, "internet")]
    if step == "internet":
        i = parse_internet(text) or "Mobile hotspot"
        p["current_internet"] = i; state["step"] = "spend"; return [_prompt(state, "spend")]
    if step == "spend":
        sp = (llm_fields or {}).get("spend") or parse_spend(text)
        if sp is None: return _retry(state, "spend")
        p["monthly_spend"] = int(sp); state["step"] = "gst"; return [_prompt(state, "gst")]
    if step == "gst":
        yn = parse_yesno(text)
        if yn is None: return [_prompt(state, "gst")]
        p["gst_registered"] = yn; p["gst_status"] = "Declared" if yn else "No"
        state["step"] = "needs"; return [_prompt(state, "needs")]
    if step == "needs":
        v = text.strip().lower()
        if v in ("__done__", "skip", "done", ""):
            state["done"] = True; state["step"] = "done"; return [_bot(T[L]["thanks"], input_type="none")]
        valid = {n[0] for n in NEED_CHIPS}
        if v in valid and v not in state["needs"]: state["needs"].append(v)
        return [_bot(("Added. Anything else? Choose Done when finished." if L == "en" else "Joda gaya. Aur kuch? Ho jaye to Done dabayein."),
                     [{"label": (n[1] if L == "en" else n[2]), "value": n[0]} for n in NEED_CHIPS if n[0] not in state["needs"]]
                     + [{"label": T[L]["done"], "value": "__done__"}], multi=True, input_type="none")]
    return []


# ---------- plain-language explanation (template based; the LLM may reword, rules still decide) ----------
WHY = {
    "P01": ("A reliable fibre line for your billing, UPI and calls.", "Billing, UPI aur calls ke liye bharosemand fibre."),
    "P02": ("Faster fibre so your team and cloud tools do not slow down.", "Tez fibre, taaki aapki team aur cloud tools dheere na hon."),
    "P04": ("5G AirFiber works where fibre is not available.", "Jahan fibre nahi hai wahan 5G AirFiber kaam karta hai."),
    "P05": ("A dedicated line for steady speed for your plant or office.", "Aapke plant ya office ke liye alag dedicated line."),
    "P07": ("Business mobile lines for you and your team, on one bill.", "Aapke aur team ke liye business mobile lines, ek hi bill mein."),
    "P08": ("Postpaid lines with more data for staff who work on the road.", "Zyada data wali postpaid lines, bahar kaam karne wale staff ke liye."),
    "P09": ("Backup 4G/5G so every site stays online if the main line drops.", "Mukhya line band ho to bhi har jagah online rahe."),
    "P15": ("WhatsApp Business so customers can reach you. Needs an active GSTIN.", "Customers aap tak WhatsApp se pahunch sakein. Active GSTIN zaroori."),
    "P16": ("Business email and storage for your team, no personal Gmail.", "Team ke liye business email aur storage, personal Gmail nahi."),
    "P17": ("Cloud backup so your records survive a lost laptop or phone.", "Laptop ya phone kho jaye to bhi records surakshit."),
    "P19": ("Cloud POS and billing, with your internet already sorted.", "Cloud POS aur billing, internet ke saath."),
    "P20": ("Endpoint security on your office computers.", "Office computers ke liye security."),
    "P21": ("A managed firewall for your plant network. Needs an active GSTIN.", "Plant network ke liye managed firewall. Active GSTIN zaroori."),
    "P23": ("Cloud CCTV you can watch from your phone.", "Apne phone se dekhne wala cloud CCTV."),
    "P10": ("SD-WAN ties your sites into one managed network.", "SD-WAN aapki sabhi jagahon ko ek network mein jodta hai."),
}


def explain(profile, rec, quote_monthly, lang="en"):
    i = 0 if lang == "en" else 1
    seg = rec["segment_label"]
    sp = profile.get("monthly_spend") or 0
    head = (f"For a {profile.get('business_type', 'business')} with {profile['employees']} staff at {profile['sites']} location(s) in "
            f"{profile.get('city', 'your city')}, I matched you with the {seg.lower()} bundle."
            if lang == "en" else
            f"{profile.get('city', 'aapke shehar')} mein {profile['employees']} staff aur {profile['sites']} jagah wale "
            f"{profile.get('business_type', 'business')} ke liye maine {seg.lower()} bundle chuna.")
    lines = [WHY[p][i] for p in rec["recommended"] if p in WHY]
    if sp:
        r = quote_monthly / sp
        if r < 0.8:
            lines.append(f"This is about ₹{quote_monthly:,} a month, less than the ₹{sp:,} you spend today." if lang == "en" else
                         f"Ye lagbhag ₹{quote_monthly:,} har mahine hai, aapke abhi ke ₹{sp:,} kharch se kam.")
        else:
            lines.append((f"This is about {r:.1f}x what you spend today (₹{sp:,}). If that feels high, start with the Starter and add more later."
                          if lang == "en" else
                          f"Ye aapke abhi ke kharch (₹{sp:,}) ka lagbhag {r:.1f} guna hai. Zyada lage to Starter se shuru karein, baad mein badhayein."))
    return {"headline": head, "lines": lines}
