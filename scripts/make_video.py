"""Record a captioned walkthrough of the prototype (silent, captions on screen). Output: demo.webm in the given folder.
Usage: python scripts/make_video.py http://localhost:5050 /tmp/video"""
import sys, os, time, random
from playwright.sync_api import sync_playwright
BASE = sys.argv[1]; OUT = sys.argv[2]; os.makedirs(OUT, exist_ok=True)
INIT = """
(()=>{
 const mk=()=>{ if(document.getElementById('__cap')) return;
  const c=document.createElement('div'); c.id='__cap';
  c.style.cssText='position:fixed;left:50%;bottom:26px;transform:translateX(-50%);max-width:880px;z-index:99999;background:rgba(20,23,31,.93);color:#fff;font:600 21px/1.35 -apple-system,Segoe UI,Arial,sans-serif;padding:13px 22px;border-radius:14px;text-align:center;box-shadow:0 8px 30px rgba(0,0,0,.4);opacity:0;transition:opacity .25s;pointer-events:none';
  document.documentElement.appendChild(c);
  const d=document.createElement('div'); d.id='__dot';
  d.style.cssText='position:fixed;width:22px;height:22px;border-radius:50%;background:rgba(228,0,0,.55);border:2px solid #fff;z-index:100000;pointer-events:none;left:-40px;top:-40px;transform:translate(-50%,-50%);box-shadow:0 0 0 3px rgba(228,0,0,.25)';
  document.documentElement.appendChild(d);
  addEventListener('mousemove',e=>{d.style.left=e.clientX+'px';d.style.top=e.clientY+'px'},true);
  window.__cap=t=>{c.textContent=t;c.style.opacity=t?1:0};
 };
 if(document.readyState==='loading') addEventListener('DOMContentLoaded',mk); else mk();
})();
"""
t0 = time.time()
def cap(pg, text, secs=2.5):
    pg.evaluate("t=>window.__cap&&window.__cap(t)", text); pg.wait_for_timeout(int(secs * 1000))
def uncap(pg): pg.evaluate("window.__cap&&window.__cap('')")
def type_(pg, sel, text): pg.click(sel); pg.type(sel, text, delay=45); pg.wait_for_timeout(250); pg.press(sel, "Enter")
def chip(pg, label): pg.locator(".chip", has_text=label).first.wait_for(state="visible", timeout=15000); pg.wait_for_timeout(500); pg.locator(".chip", has_text=label).first.click()

with sync_playwright() as p:
    kw = {"args": ["--no-sandbox"]}
    if os.path.exists("/usr/bin/google-chrome"): kw["executable_path"] = "/usr/bin/google-chrome"
    b = p.chromium.launch(**kw)
    ctx = b.new_context(viewport={"width": 1280, "height": 720}, record_video_dir=OUT, record_video_size={"width": 1280, "height": 720})
    ctx.add_init_script(INIT); pg = ctx.new_page(); pg.goto(BASE); pg.wait_for_selector("#startEn"); pg.wait_for_timeout(600)

    cap(pg, "Udyam Digital: a small-business owner goes from 'what do I need?' to a placed order, with no sales call.", 4.5)
    cap(pg, "Rules decide eligibility and price. The AI only talks. Everything shown is synthetic data.", 3.5)
    pg.click("#startEn"); cap(pg, "1. Advisor: six short questions, tap or type. Hindi is one tap away.", 2.5)
    chip(pg, "Kirana store"); pg.wait_for_selector("#inputbar:not(.hide) #txt:not([disabled])", timeout=15000); pg.wait_for_timeout(800)
    type_(pg, "#txt", "4 staff, 1 shop"); pg.wait_for_selector("#txt:not([disabled])", timeout=15000); pg.wait_for_timeout(500)
    type_(pg, "#txt", "Pune 411001"); chip(pg, "Mobile hotspot"); pg.wait_for_selector("#txt:not([disabled])", timeout=15000); pg.wait_for_timeout(500)
    type_(pg, "#txt", "20000"); pg.wait_for_selector(".chip", timeout=15000); pg.wait_for_timeout(600); pg.locator(".chip").nth(1).click()
    pg.wait_for_selector(".chip.done", timeout=15000); pg.wait_for_timeout(600); pg.locator(".chip.done").click()
    pg.wait_for_selector("#v-quote:not(.hide) .tier", timeout=20000); pg.wait_for_timeout(700)

    cap(pg, "2. One bundle, one monthly price. Two tiers; the rules engine built both.", 3.5)
    pg.locator(".tier").first.click(); pg.wait_for_timeout(1200); pg.locator(".tier").nth(1).click(); pg.wait_for_timeout(800)
    cap(pg, "Change anything and the price updates live. Rules are re-checked on every change.", 2.5)
    pg.locator("[data-d='1']").first.click(); pg.wait_for_timeout(1500); pg.locator("[data-d='-1']").first.click(); pg.wait_for_timeout(900)
    pg.locator("details.grp summary", has_text="Not available").scroll_into_view_if_needed(); pg.locator("details.grp summary", has_text="Not available").click(); pg.wait_for_timeout(500)
    cap(pg, "Products this business cannot buy are shown with the reason, not silently hidden.", 4)
    pg.locator("details.grp summary", has_text="Not available").click()
    pg.evaluate("window.scrollTo({top:0,behavior:'smooth'})"); pg.wait_for_timeout(700)
    pg.click("#go"); pg.wait_for_selector("#agree"); cap(pg, "3. Consent first. No consent, no document is ever read. Withdrawal is one click.", 4); pg.click("#agree")
    pg.wait_for_selector("#runkyc")

    cap(pg, "4. Smart KYC. Case-pack specimens: a GSTIN with one wrong character.", 2.5)
    pg.click("[data-spec=K06]"); pg.click("#runkyc"); pg.wait_for_selector("#kycres .verdict", timeout=90000)
    cap(pg, "Checksum and registry both fail, so it is blocked, never auto-corrected. The owner is told what to fix.", 4.5)
    pg.click("[data-spec=K01]"); pg.click("#runkyc"); pg.wait_for_selector("#kycres .verdict", timeout=90000)
    cap(pg, "A cancelled GSTIN: GST-only products are removed and the rest can go ahead.", 4)
    pg.click("[data-spec=K09]"); pg.click("#runkyc"); pg.wait_for_selector("#kycres .verdict", timeout=90000)
    cap(pg, "Clean documents: verified in seconds. IDs masked, images deleted.", 4)
    pg.click("#tocheckout"); pg.wait_for_selector("#place"); cap(pg, "5. Checkout with a mock UPI autopay mandate. No money moves.", 3)
    pg.click("#place"); pg.wait_for_selector(".timeline", timeout=15000)
    cap(pg, "6. Tracker: every step to activation, so the owner never has to chase.", 3.5)
    pg.click("summary:has-text('Demo controls')"); pg.click("[data-adv='3']"); pg.wait_for_timeout(1200)
    cap(pg, "Time moves on and milestones complete.", 2.5)
    pg.click("summary:has-text('Demo controls')"); pg.click("#slip"); pg.wait_for_timeout(900); pg.locator(".wa").last.scroll_into_view_if_needed()
    cap(pg, "If a date slips, the owner is told first, with the reason.", 4)

    pg.goto(BASE + "/whatsapp"); pg.wait_for_selector(".wm", timeout=15000); pg.wait_for_timeout(1500)
    pg.fill("#wa-num", "9198" + str(random.randint(10000000, 99999999))); pg.click("#wa-reset"); pg.wait_for_selector(".wbtn:not([disabled])", timeout=15000)
    cap(pg, "7. WhatsApp: the same advisor behind a Cloud API webhook. Taps, lists, no app to install.", 4)
    pg.locator(".wbtn", has_text="Hindi").click(); pg.wait_for_timeout(2500)
    cap(pg, "Hindi from the first message. Documents are never taken on WhatsApp; KYC moves to the secure page.", 4.5)
    pg.goto(BASE + "/office"); pg.wait_for_selector(".kpi"); pg.wait_for_timeout(600)
    cap(pg, "8. Back office: leads the advisor could not close arrive with their answers, and orders in review.", 4.5)
    pg.click("[data-t=stalled]"); pg.wait_for_timeout(600)
    cap(pg, "A 'call first' list ranked by a propensity model. It prioritises people and never rejects a lead.", 4.5)
    cap(pg, "Rules decide. AI talks. People stay in the loop. Thank you.", 4)
    uncap(pg); pg.wait_for_timeout(500)
    path = pg.video.path(); ctx.close(); b.close()
    os.replace(path, os.path.join(OUT, "demo.webm")); print("recorded", round(time.time() - t0), "s")
