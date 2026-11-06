# Udyam Digital: a self-serve front door for small-business telecom

Prototype for the Airtel Sync 2026 Digital Track (team Sigmas). It lets a small-business owner go from
"what do I need?" to "my order is placed and I can see where it is" without a sales call, and sends the
owner to a person when the system cannot close the sale.

**All data is synthetic (the case pack). Payments, GSTIN/Udyam registries, serviceability and WhatsApp are mocked.**

## Run it

```bash
sudo apt-get install tesseract-ocr        # KYC reading needs the Tesseract binary
pip install -r requirements.txt
python run.py                             # http://localhost:5000   (customer)   /office   (back office)   /whatsapp   (WhatsApp simulator)
                                          # on macOS port 5000 is taken by AirPlay: PORT=5050 python run.py
python -m pytest -q tests                 # 45 tests, about a minute (the KYC tests run OCR)
pip install playwright && playwright install chromium
python scripts/e2e.py http://localhost:5050   # optional: 53 browser checks over every screen, saves screenshots to ./shots
```

Demo path: pick English or Hindi, answer six short questions, take the Recommended bundle, agree to consent,
choose specimen **K09** (clean) in the KYC step, place the order, then use the demo controls on the tracker.
Try **K01** (cancelled GSTIN: GST-only products are removed), **K06** or **K10** (one wrong character in the
GSTIN: blocked, never auto-corrected), **K04** (blurred: re-upload, or continue on the typed GSTIN),
**K11** (stale address proof), **K07** (legal name differs: manual review).

**WhatsApp channel:** open `/whatsapp`, chat in the phone simulator (reply buttons and list messages, Meta Cloud API payload shape). 
Documents are never collected on WhatsApp: it hands over to the web page with the same answers (`/?s=<session>`). 
The webhook is `/api/whatsapp/webhook`; sending is mocked, and the signature check runs only when `WHATSAPP_APP_SECRET` is set.

**Docs and video:** `docs/EVIDENCE.md` (every number in the deck and how to reproduce it), `docs/architecture.png`, `docs/PRIVACY_NOTE.pdf` (one page). 
`python scripts/make_video.py http://localhost:5050 out/` records the captioned walkthrough (needs Playwright and ffmpeg).

## What it does

| Step | Behaviour |
|---|---|
| Advisor | Scripted English/Hindi flow with tap-to-answer chips, a progress bar and typing indicator; input is locked while a reply is in flight. Two unclear answers in a row, a city outside coverage, or "Talk to a person" hand the owner to the right back-office queue with the answers so far. |
| Quote | Two bundles (Starter, Recommended), one monthly price. Add-ons toggle with live pricing. Items the rules forbid are shown with the reason. A GST-registration route unlocks GST-only products. |
| Consent | Shown before any document is read. Withdrawal stops processing and deletes what is held. |
| KYC | OCR on four documents, mod-36 GSTIN checksum, lookup in the mock registries, cross-checks (name, address age, signatory). Document images are deleted when the check ends. |
| Checkout and tracker | Mock UPI autopay (ID validated), six milestones, simulated WhatsApp messages, slippage notice with a reason. Order link (`/?order=ID`) opens the tracker on any device; the page resumes after a reload. |
| Back office | Leads the advisor could not close, orders needing review, and a propensity-ranked "call first" list. |

## Design rules

1. **A rules engine decides eligibility and price.** City tier, minimum staff, minimum sites, GSTIN required and
   "needs one of" dependencies come from the catalogue. No bundle that breaks a rule can be ordered.
2. **The LLM never decides.** An optional Gemini adapter (`app/llm.py`) can extract business type, size, city and
   spend from free text. Output is validated; if it is off, slow or invalid, the scripted parser takes over.
   It is disabled unless `GEMINI_API_KEY` is set.
3. **KYC decisions have a fixed precedence:** REUPLOAD, then LIMITED, then REVIEW, then VERIFIED.
   An OCR reading is accepted only if the checksum is valid and the number is in the registry; matching is on
   the registration number, never on the name.
4. **Consent first, masked identifiers, delete images after verification.** The AI advisor never sees document images.

## Layout

```
app/catalogue.py     rules engine, bundle builder, pricing
app/advisor.py       bilingual state machine and plain-language explanations
app/kyc/             GSTIN checksum, multi-pass OCR, decision engine
app/scoring.py       propensity model for the back-office list (trained at start-up)
app/serviceability.py  mock pincode check (ends 9: no fibre; 8 or 9: no leased line; 00: survey needed)
app/store.py         SQLite: sessions, orders, consents, events, messages, leads
app/main.py          Flask routes
app/whatsapp.py      WhatsApp webhook payloads and rendering
app/static/          customer page, back office page, WhatsApp simulator
docs/                evidence, architecture diagram, privacy note
tests/               rules, advisor, consent gate, KYC regression, LLM validation and fallback
```

## Honest limitations

- **Registries, payments, serviceability and WhatsApp are mocks.** No real GSTN, Udyam, UPI or Meta calls.
- **The KYC check is not a blind benchmark.** It was tuned against the 12 specimens in the case pack and matches
  all 12 expected outcomes; that is a regression test, not evidence of accuracy on unseen documents.
- **The Gemini adapter has not been run against the live API.** Only validation and fallback are tested, with a stubbed transport.
- **The propensity model is modest:** ROC-AUC 0.71 (5-fold) and 0.72 on a chronological holdout, using fields known at lead creation.
  It prioritises calls; it never rejects a lead.
- **Hindi UI strings are Hinglish written by the team; KYC flag text, product names and WhatsApp updates stay in English.**
- **Mid-flow sessions are not resumed after a reload** (only placed orders are). Going back from consent or KYC to the quote reuses the same draft order.
- **Prices are catalogue midpoints**, not quotes. Hindi strings were written by the team and need a native review.
- **Not certified for anything.** DPDP-style consent and deletion are designed in; no compliance claim is made.
- No authentication on the back-office page; it is a demo.
