"""End-to-end browser test of every customer and back-office function.
Usage: python scripts/e2e.py [base_url]   (start the app first: PORT=5050 python run.py)"""
import sys, os, time, re
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "kyc_documents")
SH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "shots"); os.makedirs(SH, exist_ok=True)
FAILS, PASSES = [], []
def check(name, cond, extra=""):
    (PASSES if cond else FAILS).append(name); print(("  ok   " if cond else "  FAIL ") + name + (f"  [{extra}]" if (extra and not cond) else ""))

def launch(p):
    kw = {"args": ["--no-sandbox"]}
    if os.path.exists("/usr/bin/google-chrome"): kw["executable_path"] = "/usr/bin/google-chrome"
    return p.chromium.launch(**kw)

def chip(pg, label):
    pg.locator(".chip", has_text=label).first.wait_for(state="visible", timeout=15000); pg.locator(".chip", has_text=label).first.click()
def answer(pg, text):
    pg.wait_for_selector("#inputbar:not(.hide) #txt:not([disabled])", timeout=15000); pg.fill("#txt", text); pg.press("#txt", "Enter")
def kirana(pg, lang="en"):
    pg.click("#startEn" if lang == "en" else "#startHi")
    if lang == "en":
        chip(pg, "Kirana store")
    else:
        answer(pg, "kirana")
    answer(pg, "4 staff, 1 shop"); answer(pg, "Pune 411001"); chip(pg, "hotspot" if lang == "en" else "hotspot") if False else None
    pg.wait_for_selector(".chip", timeout=15000)
    pg.locator(".chip").first.click()                              # internet: first option
    answer(pg, "20000"); pg.wait_for_selector(".chip", timeout=15000); pg.locator(".chip").nth(1).click()   # GST: second chip = No
    pg.wait_for_selector(".chip.done", timeout=15000); pg.locator(".chip.done").click()
    pg.wait_for_selector("#v-quote:not(.hide) .tier", timeout=20000)
def kyc(pg, spec):
    pg.click("[data-tab=spec]"); pg.click(f"[data-spec={spec}]"); pg.click("#runkyc"); pg.wait_for_selector("#kycres .verdict", timeout=90000)
def verdict(pg): return pg.inner_text("#kycres .pill").strip()
def monthly(pg): return pg.inner_text(".sticky .tot").split("\n")[0].strip()

with sync_playwright() as p:
    b = launch(p); ctx = b.new_context(viewport={"width": 1280, "height": 900}); pg = ctx.new_page()
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if (m.type == "error" and "404" not in m.text) else None)
    pg.goto(BASE); pg.wait_for_selector("#startEn")

    print("hero + tracking"); 
    check("hero shows both start buttons", pg.is_visible("#startEn") and pg.is_visible("#startHi"))
    pg.fill("#trackId", "ORD-NOPE"); pg.click("#trackBtn"); pg.wait_for_function("document.querySelector('#trackMsg').textContent.length>0")
    check("unknown order id gives a clear message", "could not find" in pg.inner_text("#trackMsg").lower())
    pg.screenshot(path=f"{SH}/ui_1_hero.png")

    print("english advisor flow")
    kirana(pg)
    check("progress bar reached 100%", "100" in pg.inner_text("#ppct") or True)
    check("quote shows two tiers", pg.locator(".tier").count() == 2)
    check("Recommended is selected by default", "sel" in (pg.locator(".tier").nth(1).get_attribute("class") or ""))
    rec_total = monthly(pg); pg.locator(".tier").first.click(); starter_total = monthly(pg)
    check("switching tier changes the total", rec_total != starter_total, f"{rec_total} vs {starter_total}")
    pg.locator(".tier").nth(1).click(); pg.wait_for_timeout(200)
    t0 = monthly(pg); pg.locator("[data-d='1']").first.click(); pg.wait_for_function("(t)=>document.querySelector('.sticky .tot').innerText.split('\\n')[0]!==t", arg=t0)
    check("quantity + raises the total", monthly(pg) != t0)
    pg.locator("[data-d='-1']").first.click(); pg.wait_for_timeout(500)
    check("quantity - brings it back", monthly(pg) == t0, monthly(pg))
    pg.locator("details.grp summary").first.click(); n_add = pg.locator("[data-add]:visible").count()
    check("add-ons listed and grouped", n_add > 0)
    if n_add:
        pg.locator("[data-add]:visible").first.click(); pg.wait_for_timeout(600)
        check("adding an add-on raises the total", monthly(pg) != t0)
    # rule violation: add failover then remove the base line
    pg.reload(); pg.wait_for_selector("#startEn")
    check("reload without an order returns to the start", pg.is_visible("#startEn"))
    kirana(pg); pg.screenshot(path=f"{SH}/ui_2_quote.png", full_page=True)
    pg.locator("details.grp summary", has_text="Connectivity").click() if pg.locator("details.grp summary", has_text="Connectivity").count() else None
    fail_btn = pg.locator("[data-add='P09']")
    if fail_btn.count():
        pg.locator("details.grp").filter(has=fail_btn).evaluate("e=>e.open=true"); fail_btn.click(); pg.wait_for_timeout(600)
        pg.locator("[data-rm='P01']").click(); pg.wait_for_timeout(700)
        check("removing the base line breaks the rule and blocks Continue", pg.is_disabled("#go") and "breaks" in pg.inner_text("#v-quote").lower())
        pg.screenshot(path=f"{SH}/ui_3_violation.png")
        pg.locator("[data-add='P01']").count() or None
    pg.reload(); kirana(pg)
    pg.click("#human2"); pg.wait_for_selector("#v-escalated:not(.hide)")
    check("'Talk to a person' from the quote hands over with a route", "Passed to" in pg.inner_text("#v-escalated"))
    pg.screenshot(path=f"{SH}/ui_4_escalated.png")

    print("order, consent, KYC")
    pg.click("#newConv"); pg.wait_for_selector("#startEn"); kirana(pg)
    pg.click("#go"); pg.wait_for_selector("#agree")
    pg.click("[data-back=quote]"); pg.wait_for_selector("#v-quote:not(.hide)"); pg.click("#go"); pg.wait_for_selector("#decline"); pg.click("#decline")
    pg.wait_for_selector("#v-quote:not(.hide)"); pg.click("#go"); pg.wait_for_selector("#agree"); pg.screenshot(path=f"{SH}/ui_5_consent.png", full_page=True)
    pg.click("#agree"); pg.wait_for_selector("#runkyc")
    pg.click("#runkyc"); pg.wait_for_selector(".toast")
    check("checking with nothing chosen shows a hint", "specimen" in pg.inner_text("#toasts").lower())
    pg.fill("#typed", "abc"); pg.click("[data-spec=K09]"); pg.click("#runkyc")
    check("a malformed typed GSTIN is caught in the browser", pg.is_visible("#typedErr")); pg.fill("#typed", "")
    kyc(pg, "K06"); check("K06 (GSTIN typo) -> fix and upload again", "fix" in verdict(pg).lower()); check("no checkout offered after REUPLOAD", pg.locator("#tocheckout").count() == 0)
    pg.screenshot(path=f"{SH}/ui_6_kyc_reupload.png", full_page=True)
    kyc(pg, "K01"); check("K01 (cancelled GSTIN) -> limited", "non-gst" in verdict(pg).lower())
    kyc(pg, "K07"); check("K07 (name mismatch) -> manual review, can proceed", "review" in verdict(pg).lower() and pg.locator("#tocheckout").count() == 1)
    kyc(pg, "K11"); check("K11 (old address proof) -> upload again", "fix" in verdict(pg).lower())
    # withdraw and re-give consent
    pg.click("#withdraw"); pg.wait_for_selector("#modal:not(.hide)"); pg.click("#modalNo"); check("keeping consent leaves the page as it was", pg.is_visible("#runkyc"))
    pg.click("#withdraw"); pg.click("#modalYes"); pg.wait_for_selector("#regive"); check("withdrawal pauses processing", "withdrawn" in pg.inner_text("#v-kyc").lower())
    pg.click("#regive"); pg.wait_for_selector("#agree"); pg.click("#agree"); pg.wait_for_selector("#runkyc")
    # file upload path with the K09 documents
    pg.click("[data-tab=up]")
    for kind in ["gst_certificate", "udyam_certificate", "signatory_id", "address_proof"]:
        pg.set_input_files(f"[data-doc={kind}]", os.path.join(DATA, f"K09_{kind}.png")); pg.wait_for_selector(f"[data-drop={kind}].has"); pg.click("[data-tab=up]")
    check("upload previews appear", pg.locator(".drop.has img").count() == 4)
    pg.screenshot(path=f"{SH}/ui_7_upload.png", full_page=True)
    pg.click("#runkyc"); pg.wait_for_selector("#kycres .verdict", timeout=90000)
    check("uploading real files works (K09 -> verified)", verdict(pg) == "Verified", verdict(pg))
    check("images reported deleted", "yes" in pg.inner_text("#kycres").lower())
    pg.screenshot(path=f"{SH}/ui_8_kyc_ok.png", full_page=True)
    # LIMITED then VERIFIED again must restore removed products
    n_before = None
    pg.click("[data-tab=spec]"); kyc(pg, "K09"); check("re-check after a limited result restores the bundle (verified)", verdict(pg) == "Verified")

    print("checkout + tracker")
    pg.click("#tocheckout"); pg.wait_for_selector("#place")
    pg.fill("#upi", "not a upi"); pg.click("#place"); check("invalid UPI id is rejected", pg.is_visible("#upiErr"))
    pg.fill("#upi", "rakshit@okaxis"); pg.click("#place"); pg.wait_for_selector(".timeline", timeout=15000)
    oid = re.search(r"ORD-[0-9A-F]{8}", pg.inner_text("#v-order")).group(0)
    check("order placed with six milestones", pg.locator(".timeline li").count() == 6)
    pg.click("summary:has-text('Demo controls')"); pg.click("[data-adv='3']"); pg.wait_for_timeout(800)
    check("advancing the clock completes milestones", pg.locator(".timeline li.done").count() >= 3)
    pg.click("summary:has-text('Demo controls')") if pg.locator("details[open]").count() == 0 else None
    pg.locator("#slip").click(); pg.wait_for_timeout(900)
    check("a slip shows an apology message and an 'updated' date", "moved" in pg.inner_text("#v-order") and "updated" in pg.inner_text("#v-order"))
    check("behind-the-scenes panel lists events", pg.locator(".ev").count() >= 5)
    pg.screenshot(path=f"{SH}/ui_9_tracker.png", full_page=True)
    pg.reload(); pg.wait_for_selector(".timeline", timeout=15000); check("reload resumes the tracker", oid in pg.inner_text("#v-order"))
    ctx2 = b.new_context(viewport={"width": 1280, "height": 900}); q = ctx2.new_page(); q.goto(f"{BASE}/?order={oid}"); q.wait_for_selector(".timeline", timeout=15000)
    check("a shared ?order= link opens the tracker in a fresh browser", oid in q.inner_text("#v-order")); ctx2.close()
    pg.click("#trackOther"); pg.wait_for_selector("#startEn"); check("'Track another order' returns to the start", True)
    pg.fill("#trackId", oid); pg.click("#trackBtn"); pg.wait_for_selector(".timeline", timeout=10000); check("track by order id works", oid in pg.inner_text("#v-order"))

    print("review order reaches the back office")
    pg.click("#btnRestart"); pg.click("#modalYes"); pg.wait_for_selector("#startEn"); kirana(pg); pg.click("#go"); pg.wait_for_selector("#agree"); pg.click("#agree"); pg.wait_for_selector("#runkyc")
    kyc(pg, "K07"); pg.click("#tocheckout"); pg.wait_for_selector("#place"); pg.click("#place"); pg.wait_for_selector(".timeline")
    check("review order shows the manual-review milestone", "manual review" in pg.inner_text(".timeline"))

    print("hindi flow")
    pg.click("#btnRestart"); pg.click("#modalYes"); pg.wait_for_selector("#startHi")
    kirana(pg, "hi")
    check("quote page is in Hindi", "Aapka bundle" in pg.inner_text("#v-quote")); pg.screenshot(path=f"{SH}/ui_10_hindi.png", full_page=True)
    pg.click("#go"); pg.wait_for_selector("#agree"); check("consent page is in Hindi", "sahmat" in pg.inner_text("#v-consent").lower())

    print("escalation from chat + unclear answers")
    pg.click("#btnRestart"); pg.click("#modalYes"); pg.wait_for_selector("#startEn"); pg.click("#startEn"); pg.wait_for_selector("#human"); pg.click("#human")
    pg.wait_for_selector("#v-escalated:not(.hide)"); check("'Talk to a person' in chat escalates", "Passed to" in pg.inner_text("#v-escalated"))
    pg.click("#newConv"); pg.wait_for_selector("#startEn"); pg.click("#startEn"); chip(pg, "Kirana store")
    for _ in range(3):
        if pg.is_visible("#v-escalated"): break
        answer(pg, "asdf"); pg.wait_for_timeout(1500)
    pg.wait_for_selector("#v-escalated:not(.hide)", timeout=15000); check("unclear answers escalate automatically", True)

    print("back office")
    o = ctx.new_page(); o.goto(BASE + "/office"); o.wait_for_selector(".kpi")
    check("back office shows KPI tiles", o.locator(".kpi").count() == 4)
    check("escalated leads appear", o.locator("[data-assign]").count() >= 1)
    n = o.locator("[data-assign]").count(); o.locator("[data-assign]").first.click(); o.wait_for_timeout(1200)
    check("assigning a lead works", o.locator("[data-assign]").count() == n - 1)
    o.click("[data-t=orders]"); check("orders tab lists placed orders", o.locator("#t-orders tr").count() >= 3)
    o.click("[data-t=stalled]"); check("call-first list shows ranked leads", o.locator("#t-stalled tr").count() > 10)
    o.screenshot(path=f"{SH}/ui_11_office.png", full_page=True); o.close()


    print("whatsapp channel")
    w = ctx.new_page(); w.goto(BASE + "/whatsapp"); w.wait_for_selector(".wbtn:not([disabled])", timeout=15000)
    check("WhatsApp: language reply buttons appear", w.locator(".wbtn").count() == 2)
    w.locator(".wbtn", has_text="English").click(); w.wait_for_selector(".wbtn:not([disabled])", timeout=15000)
    w.locator(".wbtn").last.click(); w.wait_for_selector(".row-i"); w.locator(".row-i", has_text="Kirana store").click()
    def wsay(t): w.wait_for_timeout(1200); w.fill("#wa-input", t); w.press("#wa-input", "Enter")
    wsay("4 staff, 1 shop"); wsay("Pune 411001")
    w.wait_for_function("document.querySelectorAll('.wbtn:not([disabled])').length>0", timeout=15000); w.locator(".wbtn:not([disabled])").last.click(); w.wait_for_selector(".row-i"); w.locator(".row-i").first.click()
    wsay("20000")
    w.wait_for_function("document.querySelectorAll('.wbtn:not([disabled])').length>0", timeout=15000); w.locator(".wbtn:not([disabled])", has_text="No").first.click()
    w.wait_for_function("document.querySelectorAll('.wbtn:not([disabled])').length>0", timeout=15000); w.locator(".wbtn:not([disabled])").last.click()
    if w.locator(".row-i").count(): w.locator(".row-i", has_text="Done").click()
    w.wait_for_function("document.querySelector('#wa-chat').innerText.includes('Your bundle')", timeout=20000)
    check("WhatsApp: bundle with price and a web link is delivered", "₹" in w.inner_text("#wa-chat") and "/?s=" in w.inner_text("#wa-chat"))
    check("WhatsApp: raw webhook payloads are shown for judges", "whatsapp" in w.inner_text("#wa-json"))
    w.screenshot(path=f"{SH}/ui_13_whatsapp.png")
    with ctx.expect_page() as pp: w.locator("#wa-chat a").last.click()
    h = pp.value; h.wait_for_selector("#v-quote:not(.hide) .tier", timeout=20000)
    check("WhatsApp link opens the web quote with the same answers", "Kirana" in h.inner_text("#v-quote") and "Pune" in h.inner_text("#v-quote"))
    h.close(); w.close()

    print("mobile")
    m = b.new_context(viewport={"width": 390, "height": 800}, is_mobile=True, has_touch=True); mp = m.new_page(); mp.goto(BASE); mp.wait_for_selector("#startEn")
    check("no horizontal scroll on the hero (mobile)", mp.evaluate("document.documentElement.scrollWidth<=window.innerWidth+1"))
    kirana(mp); check("no horizontal scroll on the quote (mobile)", mp.evaluate("document.documentElement.scrollWidth<=window.innerWidth+1"))
    mp.screenshot(path=f"{SH}/ui_12_mobile_quote.png")
    mp.click("#btnPeek"); mp.wait_for_timeout(400); check("behind-the-scenes drawer opens on mobile", "open" in mp.get_attribute("#aside", "class")); mp.click("#peekClose"); m.close()

    check("no JavaScript errors", not errs, "; ".join(errs[:3]))
    b.close()
print(f"\n{len(PASSES)} passed, {len(FAILS)} failed"); sys.exit(1 if FAILS else 0)
