"""Optional hosted LLM, used only to read free-text answers into the same profile fields the scripted flow fills.

It never sees document images or full ID numbers, never chooses products, and never sets eligibility or price.
Everything it returns is validated; on any error, timeout or odd output the scripted parser is used instead.
Enabled only when GEMINI_API_KEY is set (Google AI Studio free tier). Not exercised in this repo's automated
tests against the live API: tests stub the transport and check validation and fallback.
"""
import json, urllib.request
from . import config

MODEL = "gemini-2.0-flash"
URL = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={k}"


def enabled(): return bool(config.GEMINI_API_KEY)


def _post(url, payload, timeout):  # transport; replaced in tests
    req = urllib.request.Request(url, json.dumps(payload).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read())


PROMPTS = {
    "business": 'Return JSON {"business_type": string} naming the kind of small business in this message (a few words, English).',
    "size": 'Return JSON {"employees": integer, "sites": integer} for staff count and number of locations in this message. Use 1 site if not stated.',
    "location": 'Return JSON {"city": string} for the Indian city in this message.',
    "spend": 'Return JSON {"spend": integer} for the monthly telecom spend in rupees in this message.',
}


def extract(step, text, lang):
    """-> dict in the shape advisor.handle expects, or None (use the scripted parser)."""
    if not enabled() or step not in PROMPTS or not text: return None
    try:
        out = _post(URL.format(m=MODEL, k=config.GEMINI_API_KEY),
                    {"contents": [{"parts": [{"text": PROMPTS[step] + "\nMessage: " + text[:300]}]}],
                     "generationConfig": {"responseMimeType": "application/json", "temperature": 0}}, config.LLM_TIMEOUT_S)
        data = json.loads(out["candidates"][0]["content"]["parts"][0]["text"])
        return validate(step, data)
    except Exception:
        return None


def validate(step, d):
    if not isinstance(d, dict): return None
    if step == "business":
        b = d.get("business_type")
        return {"business_type": b.strip()[:40]} if isinstance(b, str) and b.strip() else None
    if step == "size":
        e, s = d.get("employees"), d.get("sites", 1)
        if isinstance(e, int) and isinstance(s, int) and 1 <= e <= 5000 and 1 <= s <= 500:
            return {"size": {"employees": e, "sites": s}}
        return None
    if step == "spend":
        v = d.get("spend")
        return {"spend": v} if isinstance(v, int) and 0 < v < 100_000_000 else None
    return None
