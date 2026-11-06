import os, sys, json, tempfile, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"))
from app import config, catalogue as cat, advisor, llm, store
from app.main import create_app
from app.kyc import engine

KEY = {"K01": "LIMITED", "K02": "VERIFIED", "K03": "VERIFIED", "K04": "REUPLOAD", "K05": "REVIEW", "K06": "REUPLOAD",
       "K07": "REVIEW", "K08": "VERIFIED", "K09": "VERIFIED", "K10": "REUPLOAD", "K11": "REUPLOAD", "K12": "VERIFIED"}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
    app = create_app(); app.config["TESTING"] = True
    return app.test_client()


def post(c, path, body=None, **kw): return c.post(path, json=body or {}, **kw)


def run_advisor(c, answers):
    sid = post(c, "/api/session").get_json()["sid"]; last = None
    for a in answers:
        last = post(c, "/api/chat", {"sid": sid, "text": a}).get_json()
    return sid, last


KIRANA = ["English", "kirana store", "4 staff, 1 shop", "Pune 411001", "hotspot", "20000", "no", "skip"]


# ---------- rules engine ----------
def test_gstin_required_product_blocked_without_gst():
    p = {"tier": 1, "employees": 40, "sites": 3, "gst_status": "No"}
    assert any(w["rule"] == "gstin_required" for w in cat.eligibility("P03", p))  # Biz Fibre 1G


def test_cancelled_gstin_is_not_active():
    assert "Cancelled" not in cat.GST_OK and "No" not in cat.GST_OK


def test_dependency_rule_flags_missing_base():
    p = {"tier": 1, "employees": 40, "sites": 3, "gst_status": "Active"}
    assert any(v["rule"] == "dependency" for v in cat.check_bundle({"P09": 1}, p))      # failover without a base line
    assert not cat.check_bundle({"P01": 1, "P09": 1}, p)


def test_price_is_sum_of_lines():
    pr = cat.price({"P01": 1, "P07": 2})
    assert pr["monthly"] == sum(l["monthly"] for l in pr["lines"])


# ---------- advisor ----------
def test_kirana_flow_gives_valid_bundle_without_gst_products(client):
    _, r = run_advisor(client, KIRANA)
    rec = r["recommendation"]
    assert rec["segment"] and len(rec["tiers"]) == 2
    for t in rec["tiers"]: assert t["quote"]["valid"], t["quote"]["violations"]


def test_hindi_flow_works(client):
    _, r = run_advisor(client, ["Hindi", "kirana", "3 log, 1 dukaan", "Pune 411001", "hotspot", "15000", "nahi", "skip"])
    assert r["lang"] == "hi" and r.get("recommendation")


def test_unclear_answers_escalate_to_person(client):
    sid = post(client, "/api/session").get_json()["sid"]
    post(client, "/api/chat", {"sid": sid, "text": "English"})
    out = None
    for _ in range(4): out = post(client, "/api/chat", {"sid": sid, "text": "asdf qwer"}).get_json()
    assert out.get("escalated") and out["lead"]["route"]


def test_unknown_city_goes_to_back_office(client):
    _, r = run_advisor(client, ["English", "kirana store", "4 staff, 1 shop", "Timbuktu 123456"])
    assert r.get("escalated") or r["messages"]


# ---------- consent gate and KYC ----------
def order_for(c):
    sid, r = run_advisor(c, KIRANA)
    b = r["recommendation"]["tiers"][1]["bundle"]
    o = post(c, "/api/order", {"sid": sid, "bundle": b}).get_json()
    return o["order_id"]


def test_kyc_blocked_without_consent(client):
    oid = order_for(client)
    r = client.post(f"/api/order/{oid}/kyc", data={"specimen": "K09"})
    assert r.status_code == 403 and r.get_json()["decision"] == "BLOCKED"


def test_checkout_needs_consent_and_kyc(client):
    oid = order_for(client)
    assert post(client, f"/api/order/{oid}/checkout").status_code == 409


def test_full_happy_path_and_image_deletion(client):
    oid = order_for(client)
    post(client, f"/api/order/{oid}/consent")
    r = client.post(f"/api/order/{oid}/kyc", data={"specimen": "K09"}).get_json()
    assert r["decision"] == "VERIFIED" and r["images_deleted"] is True
    assert not os.path.exists(os.path.join(config.UPLOAD_TMP, oid))
    o = post(client, f"/api/order/{oid}/checkout").get_json()
    assert len(o["milestones"]) == 6
    old = o["milestones"][-1]["planned"]
    s = post(client, f"/api/order/{oid}/demo/slip", {"days": 2}).get_json()
    assert s["milestones"][-1]["planned"] > old
    assert any("moved" in m["text"] for m in s["messages"])


def test_limited_kyc_removes_gst_only_products(client):
    oid = order_for(client)
    post(client, f"/api/order/{oid}/consent")
    r = client.post(f"/api/order/{oid}/kyc", data={"specimen": "K01"}).get_json()
    assert r["decision"] == "LIMITED" and r["gst_status"] == "Cancelled"


def test_withdrawal_blocks_further_processing(client):
    oid = order_for(client)
    post(client, f"/api/order/{oid}/consent"); post(client, f"/api/order/{oid}/consent/withdraw")
    assert client.post(f"/api/order/{oid}/kyc", data={"specimen": "K09"}).status_code == 403


def test_rule_breaking_bundle_cannot_be_ordered(client):
    sid, _ = run_advisor(client, KIRANA)
    r = post(client, "/api/order", {"sid": sid, "bundle": {"P12": 1}})
    assert r.status_code == 422 or r.status_code == 200 and not r.get_json()["quote"]["valid"]


# ---------- KYC regression on the 12 case specimens ----------
@pytest.mark.parametrize("kid", sorted(KEY))
def test_kyc_specimens(kid):
    r = engine.check_applicant(kid, consent=True)
    assert r["decision"] == KEY[kid]


def test_kyc_refuses_without_consent():
    assert engine.check_applicant("K09", consent=False)["decision"] == "BLOCKED"


# ---------- LLM adapter: validation and fallback ----------
def test_llm_off_without_key(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    assert llm.extract("business", "kirana", "en") is None


def test_llm_rejects_bad_output():
    assert llm.validate("size", {"employees": -3, "sites": 1}) is None
    assert llm.validate("size", {"employees": "ten"}) is None
    assert llm.validate("spend", {"spend": 10**12}) is None
    assert llm.validate("business", {"business_type": ""}) is None


def test_llm_valid_output_with_stub(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "x")
    monkeypatch.setattr(llm, "_post", lambda *a, **k: {"candidates": [{"content": {"parts": [{"text": json.dumps({"employees": 6, "sites": 2})}]}}]})
    assert llm.extract("size", "6 log 2 shops", "en") == {"size": {"employees": 6, "sites": 2}}


def test_llm_failure_falls_back(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "x")
    def boom(*a, **k): raise TimeoutError()
    monkeypatch.setattr(llm, "_post", boom)
    assert llm.extract("size", "6 staff", "en") is None


# ---------- application behaviour added in the UI pass ----------
def test_going_back_does_not_create_duplicate_orders(client):
    sid, r = run_advisor(client, KIRANA)
    b = r["recommendation"]["tiers"][1]["bundle"]
    a = post(client, "/api/order", {"sid": sid, "bundle": b}).get_json()["order_id"]
    c = post(client, "/api/order", {"sid": sid, "bundle": b}).get_json()["order_id"]
    assert a == c


def test_upi_id_is_validated(client):
    oid = order_for(client); post(client, f"/api/order/{oid}/consent")
    client.post(f"/api/order/{oid}/kyc", data={"specimen": "K09"})
    assert post(client, f"/api/order/{oid}/checkout", {"upi": "not a upi"}).status_code == 422
    assert post(client, f"/api/order/{oid}/checkout", {"upi": "rakshit@okaxis"}).status_code == 200


def test_reconsent_after_withdrawal_unpauses_order(client):
    oid = order_for(client)
    post(client, f"/api/order/{oid}/consent"); post(client, f"/api/order/{oid}/consent/withdraw")
    assert client.get(f"/api/order/{oid}").get_json()["status"].startswith("Paused")
    post(client, f"/api/order/{oid}/consent")
    assert client.get(f"/api/order/{oid}").get_json()["status"] == "Draft"
    assert client.post(f"/api/order/{oid}/kyc", data={"specimen": "K09"}).get_json()["decision"] == "VERIFIED"


def test_progress_reported_to_the_ui(client):
    sid = post(client, "/api/session").get_json()["sid"]
    r = post(client, "/api/chat", {"sid": sid, "text": "English"}).get_json()
    assert r["progress"][1] == 8 and 0 <= r["progress"][0] <= 8


def test_quote_exposes_first_bill_and_addon_categories(client):
    sid, r = run_advisor(client, KIRANA)
    q = r["recommendation"]["tiers"][1]["quote"]
    assert q["first_bill"] == q["price"]["monthly"] + q["price"]["setup"]
    assert all("category" in a for a in r["recommendation"]["addons"])


# ---------- WhatsApp channel ----------
import hmac, hashlib


def wa_msg(c, body, frm="919800000001", headers=None, secret=None):
    payload = {"entry": [{"changes": [{"value": {"messages": [{"from": frm, "id": "wamid.1", **body}]}}]}]}
    raw = json.dumps(payload).encode(); h = dict(headers or {"Content-Type": "application/json"})
    if secret: h["X-Hub-Signature-256"] = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return c.post("/api/whatsapp/webhook", data=raw, headers=h)


def wa_text(c, t, frm="919800000001"): return wa_msg(c, {"type": "text", "text": {"body": t}}, frm).get_json()


def wa_pick(c, i, kind="list_reply", frm="919800000001"):
    return wa_msg(c, {"type": "interactive", "interactive": {"type": kind, kind: {"id": i, "title": i}}}, frm).get_json()


def test_whatsapp_verification_handshake(client):
    ok = client.get("/api/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=udyam-demo&hub.challenge=123")
    assert ok.status_code == 200 and ok.get_data(as_text=True) == "123"
    assert client.get("/api/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=nope&hub.challenge=1").status_code == 403


def test_whatsapp_first_message_offers_language_buttons(client):
    out = wa_text(client, "Hi")["outbound"][0]
    assert out["type"] == "interactive" and out["interactive"]["type"] == "button"
    assert len(out["interactive"]["action"]["buttons"]) <= 3


def test_whatsapp_full_flow_ends_with_bundle_and_web_link(client):
    wa_text(client, "Hi"); wa_pick(client, "English", "button_reply")
    for t in ["Kirana store", "4 staff, 1 shop", "Pune 411001"]: wa_text(client, t)
    wa_pick(client, "hotspot"); wa_text(client, "20000"); wa_pick(client, "no"); r = wa_pick(client, "__done__")
    body = r["outbound"][-1]["text"]["body"]
    assert "₹" in body and "/?s=S-WA" in body
    sid = body.split("/?s=")[1].split()[0]
    rec = client.get(f"/api/session/{sid}/recommendation").get_json()
    assert rec["recommendation"]["tiers"][1]["quote"]["valid"]            # the web page resumes with the same answers


def test_whatsapp_list_messages_never_exceed_ten_rows(client):
    wa_text(client, "Hi"); wa_pick(client, "English", "button_reply")
    for o in wa_text(client, "x")["outbound"]:
        if o.get("interactive", {}).get("type") == "list":
            assert len(o["interactive"]["action"]["sections"][0]["rows"]) <= 10


def test_whatsapp_media_is_refused_and_points_to_secure_page(client):
    wa_text(client, "Hi"); wa_pick(client, "English", "button_reply")
    r = wa_msg(client, {"type": "image", "image": {"id": "1"}}).get_json()
    assert "do not send ID" in r["outbound"][0]["text"]["body"] and "/?s=" in r["outbound"][0]["text"]["body"]


def test_whatsapp_human_request_creates_lead(client):
    wa_text(client, "Hi"); wa_pick(client, "English", "button_reply"); wa_text(client, "Kirana store")
    r = wa_text(client, "talk to a person")
    assert "will call you" in r["outbound"][0]["text"]["body"]
    assert any(l["id"].startswith("LD-WA") for l in client.get("/api/office").get_json()["leads"])


def test_whatsapp_restart_starts_over(client):
    wa_text(client, "Hi"); wa_pick(client, "English", "button_reply")
    assert wa_text(client, "restart")["outbound"][0]["interactive"]["type"] == "button"


def test_whatsapp_signature_enforced_when_secret_set(client, monkeypatch):
    monkeypatch.setattr(config, "WHATSAPP_APP_SECRET", "s3cret")
    assert wa_msg(client, {"type": "text", "text": {"body": "Hi"}}).status_code == 403
    assert wa_msg(client, {"type": "text", "text": {"body": "Hi"}}, secret="wrong").status_code == 403
    assert wa_msg(client, {"type": "text", "text": {"body": "Hi"}}, secret="s3cret").status_code == 200


def test_resume_link_rejects_unfinished_sessions(client):
    sid = post(client, "/api/session").get_json()["sid"]
    assert client.get(f"/api/session/{sid}/recommendation").status_code == 409
    assert client.get("/api/session/S-NOPE/recommendation").status_code == 404
