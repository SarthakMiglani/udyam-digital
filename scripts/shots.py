"""Drive the full customer flow in a headless browser and save screenshots to ./shots."""
import sys, time
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(BASE); pg.wait_for_selector(".chip")
    def chip(label): pg.click(f".chip:has-text('{label}')"); time.sleep(0.4)
    def say(txt): pg.fill("#txt", txt); pg.click("#send"); time.sleep(0.5)
    chip("English"); chip("Kirana store"); say("4 staff, 1 shop"); say("Pune 411001")
    chip("Mobile hotspot"); say("20000"); chip("No")
    pg.screenshot(path="shots/1_chat.png"); chip("Done")
    pg.wait_for_selector("#go", timeout=8000); time.sleep(0.5); pg.screenshot(path="shots/2_quote.png", full_page=True)
    pg.click("#go"); pg.wait_for_selector("#agree"); pg.screenshot(path="shots/3_consent.png")
    pg.click("#agree"); pg.wait_for_selector("#spec"); pg.select_option("#spec", "K09"); pg.click("#runkyc")
    pg.wait_for_selector("#tocheckout", timeout=60000); pg.screenshot(path="shots/4_kyc_verified.png", full_page=True)
    pg.select_option("#spec", "K01"); pg.click("#runkyc"); time.sleep(8); pg.screenshot(path="shots/4b_kyc_K01.png", full_page=True)
    pg.click("#tocheckout"); pg.wait_for_selector("#place"); pg.click("#place"); pg.wait_for_selector(".timeline")
    pg.click("[data-adv='3']"); time.sleep(0.8); pg.click("#slip"); time.sleep(0.8)
    pg.screenshot(path="shots/5_tracker.png", full_page=True)
    o = b.new_page(viewport={"width": 1280, "height": 900}); o.goto(BASE + "/office"); time.sleep(1); o.screenshot(path="shots/6_office.png", full_page=True)
    print("JS errors:", errs or "none"); b.close()
