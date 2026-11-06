"""WhatsApp channel helpers. Shapes follow the Meta WhatsApp Cloud API so the same webhook can be pointed at a real number.

What is real here: parsing inbound webhook payloads, signature verification, and building outbound message objects
(text, reply buttons for up to 3 choices, list messages for up to 10).
What is mocked: nothing is POSTed to Meta. The outbound objects are returned in the HTTP response, and the /whatsapp
page renders them like a phone. Documents are never collected on WhatsApp: KYC happens on the web page, after consent.
"""
import hmac, hashlib, re

RESTART_WORDS = {"restart", "start over", "reset", "new", "dobara", "shuru"}
HUMAN_WORDS = {"human", "agent", "person", "talk to a person", "call me", "insaan", "vyakti"}
MEDIA_NOTE = {
    "en": "Thanks. For your safety please do not send ID or business documents on WhatsApp. You will upload them on a secure page, after you agree to how we use them: {link}",
    "hi": "Dhanyavaad. Suraksha ke liye ID ya business documents WhatsApp par na bhejein. Aap unhein secure page par upload karenge, unke upyog par sahmati dene ke baad: {link}"}
HUMAN_NOTE = {"en": "Done. {route} will call you. They already have what you told me.",
              "hi": "Ho gaya. {route} aapko call karega. Aapne jo bataya wo unke paas pehle se hai."}
AGAIN_NOTE = {"en": "Your bundle is ready. Continue here to verify and order: {link}\nSend RESTART to begin again.",
              "hi": "Aapka bundle taiyaar hai. Verify aur order ke liye yahan aage badhein: {link}\nDobara shuru karne ke liye RESTART bhejein."}


def sid_for(phone):
    return "S-WA" + re.sub(r"\D", "", phone or "")[-10:]


def signature_ok(raw, header, secret):
    """X-Hub-Signature-256: 'sha256=' + HMAC-SHA256(app secret, raw body)."""
    want = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(want, header or "")


def messages_in(payload):
    for e in payload.get("entry", []) or []:
        for c in e.get("changes", []) or []:
            for m in (c.get("value") or {}).get("messages", []) or []:
                yield m


def text_of(m):
    """Text the advisor should see, or None for media."""
    t = m.get("type")
    if t == "text": return (m.get("text") or {}).get("body", "")
    if t == "interactive":
        i = m.get("interactive") or {}
        r = i.get("button_reply") or i.get("list_reply") or {}
        return r.get("id") or r.get("title") or ""
    if t == "button": return (m.get("button") or {}).get("payload") or (m.get("button") or {}).get("text") or ""
    return None


def render(to, msgs):
    """Advisor messages -> Meta-shaped outbound objects."""
    out = []
    for m in msgs:
        base = {"messaging_product": "whatsapp", "to": to}
        chips = m.get("chips") or []
        text = m["text"][:1000]
        if not chips:
            out.append({**base, "type": "text", "text": {"body": text}})
        elif len(chips) <= 3:
            out.append({**base, "type": "interactive", "interactive": {"type": "button", "body": {"text": text},
                        "action": {"buttons": [{"type": "reply", "reply": {"id": c["value"], "title": c["label"][:20]}} for c in chips]}}})
        else:
            rows = chips if len(chips) <= 10 else chips[:9] + [c for c in chips if c["value"] == "__done__"][:1]
            out.append({**base, "type": "interactive", "interactive": {"type": "list", "body": {"text": text},
                        "action": {"button": "Choose", "sections": [{"title": "Options", "rows": [{"id": c["value"], "title": c["label"][:24]} for c in rows]}]}}})
    return out


def summary(rec, lang, link):
    q = rec["tiers"][1]["quote"]; p = q["price"]
    lines = "\n".join(f"• {l['name']}" + (f" x {l['qty']}" if l["qty"] > 1 else "") + f"  ₹{l['monthly']:,}" for l in p["lines"])
    setup = f" + ₹{p['setup']:,} setup" if p["setup"] else ""
    if lang == "hi":
        return f"Aapka bundle ({rec['segment_label']}):\n{lines}\n\nTotal: ₹{p['monthly']:,} har mahine{setup}\n\nBadlav, verify aur order ke liye yahan jaayein: {link}"
    return f"Your bundle ({rec['segment_label']}):\n{lines}\n\nTotal: ₹{p['monthly']:,} a month{setup}\n\nChange it, verify and order here: {link}"
