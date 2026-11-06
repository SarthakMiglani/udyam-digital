"""Flask app: advisor, quote and checkout, smart KYC, tracker and back office.

Design rule: the browser and the LLM never compute eligibility or price. Every quote is built by catalogue.py.
"""
import os, re, shutil, datetime as dt
from flask import Flask, jsonify, request, send_from_directory
from . import config, store, advisor, catalogue as cat, serviceability as sv, scoring, llm
from .kyc import engine

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
DOC_TYPES = engine.DOCS
KYC_PASS = {"VERIFIED", "LIMITED", "REVIEW"}      # decisions that let the order proceed
CONSENT_PURPOSE = "Verify your business for this order (KYC)"
CONSENT_FIELDS = ["GST certificate", "Udyam certificate", "Signatory ID", "Address proof"]
CONSENT_TEXT = {
    "en": {"title": "Before we read your documents",
           "points": ["Purpose: we use your documents only to verify your business for this order (KYC). Nothing else.",
                      "What we read: GST certificate, Udyam certificate, signatory ID and recent address proof.",
                      "What we keep: the result of the checks and masked ID numbers. The document images are deleted as soon as verification finishes.",
                      "The AI advisor never sees your document images or full ID numbers.",
                      "You can withdraw consent at any time. Processing stops and the data we hold is deleted, unless the law requires us to keep it."],
           "agree": "I agree", "decline": "Not now"},
    "hi": {"title": "Aapke documents padhne se pehle",
           "points": ["Maqsad: hum documents ka upyog sirf is order ke liye aapka business verify karne (KYC) mein karte hain. Aur kisi kaam mein nahi.",
                      "Hum kya padhte hain: GST certificate, Udyam certificate, signatory ID aur taza address proof.",
                      "Hum kya rakhte hain: jaanch ka nateeja aur masked ID number. Verification khatam hote hi document ki tasveerein delete ho jati hain.",
                      "AI advisor aapke document ki tasveerein ya poora ID number kabhi nahi dekhta.",
                      "Aap kabhi bhi sahmati wapas le sakte hain. Processing ruk jati hai aur humare paas jo data hai wo delete ho jata hai, jab tak kanoon rakhne ko na kahe."],
           "agree": "Main sahmat hoon", "decline": "Abhi nahi"},
}
SEG_ROUTE = {"micro": "Channel partner (local language, low cost)", "professional": "Inside sales callback",
             "multisite": "Field force (high-value account)", "manufacturer": "Field force (high-value account)"}


def create_app():
    app = Flask(__name__, static_folder=STATIC, static_url_path="/static")
    os.makedirs(config.UPLOAD_TMP, exist_ok=True)
    store.init()
    scoring.load()

    def err(msg, code=400): return jsonify({"error": msg}), code

    def get_session(sid):
        s = store.load_session(sid)
        return s

    # ---------------- pages ----------------
    @app.get("/")
    def index(): return send_from_directory(STATIC, "index.html")

    @app.get("/office")
    def office_page(): return send_from_directory(STATIC, "office.html")

    @app.get("/api/health")
    def health():
        return jsonify({"ok": True, "llm": "on (optional, validated)" if llm.enabled() else "off (scripted flow)",
                        "today": config.TODAY.isoformat(), "data": "synthetic case data"})

    # ---------------- advisor ----------------
    @app.post("/api/session")
    def new_session():
        sid = store.new_id("S"); st = advisor.new_session(sid); store.save_session(sid, st)
        return jsonify({"sid": sid, "messages": advisor.first_message()})

    def full_profile(st):
        p = dict(st["profile"])
        p.setdefault("employees", 1); p.setdefault("sites", 1); p.setdefault("tier", 2)
        p["segment"] = cat.infer_segment(p.get("business_type"), p["employees"], p["sites"])
        return p

    def make_lead(st, reason, profile=None):
        p = profile or full_profile(st)
        try: sc = scoring.score_profile(p, st.get("needs"))
        except Exception: sc = 0.0
        lid = "LD-" + st["sid"][2:]
        lead = {"id": lid, "session_id": st["sid"], "created": store.now(), "reason": reason, "score": round(sc, 3), "status": "open",
                "route": SEG_ROUTE.get(p.get("segment"), "Inside sales callback"),
                "captured": {k: p.get(k) for k in ("business_type", "employees", "sites", "city", "pincode", "monthly_spend", "gst_registered", "lang")},
                "segment": cat.SEGMENT_LABEL.get(p.get("segment"), "Unknown")}
        store.save_lead(lead); return lead

    def run_chat(st, text):
        """One advisor turn. Shared by the web chat and the WhatsApp webhook so both channels behave identically."""
        if st["done"] and not st["escalate"]: return {"messages": [], "done": True, "lang": st["lang"]}
        msgs = advisor.handle(st, text)
        out = {"messages": msgs, "done": st["done"], "lang": st["lang"],
               "progress": [min(advisor.STEPS.index(st["step"]), 8), 8]}
        if st["done"]:
            if st["escalate"]:
                out["lead"] = make_lead(st, st["escalate"]); out["escalated"] = True
            else:
                out["recommendation"] = compose(st)
                if out["recommendation"].get("needs_survey"):
                    out["lead"] = make_lead(st, "Site needs a survey: no fibre or AirFiber confirmed at the pincode")
        store.save_session(st["sid"], st)
        return out

    @app.post("/api/chat")
    def chat():
        d = request.get_json(force=True); st = get_session(d.get("sid"))
        if not st: return err("unknown session", 404)
        return jsonify(run_chat(st, d.get("text", "")))

    @app.get("/api/session/<sid>/recommendation")
    def resume_recommendation(sid):
        """Lets a customer continue on the web from a WhatsApp link, with the answers already given."""
        st = get_session(sid)
        if not st: return err("unknown session", 404)
        if not st["done"] or st["escalate"]: return err("this conversation has no bundle yet", 409)
        return jsonify({"recommendation": compose(st), "lang": st["lang"], "sid": sid})

    @app.post("/api/escalate")
    def escalate():
        d = request.get_json(force=True); st = get_session(d.get("sid"))
        if not st: return err("unknown session", 404)
        lead = make_lead(st, d.get("reason") or "Owner asked to talk to a person")
        return jsonify({"lead": lead})

    def quote_for(profile, bundle):
        viol = cat.check_bundle(bundle, profile)
        pr = cat.price(bundle)
        sp = profile.get("monthly_spend") or 0
        return {"price": pr, "first_bill": pr["monthly"] + pr.get("setup", 0), "violations": [{**v, "name": cat.name(v["product"])} for v in viol], "valid": not viol,
                "vs_spend": round(pr["monthly"] / sp, 1) if sp else None,
                "expected_install_date": (config.TODAY + dt.timedelta(days=pr["install_days"] + 1)).isoformat()}

    def compose(st):
        p = full_profile(st); serv = sv.check(p.get("pincode"))
        rec = cat.recommend(p, serv, st.get("needs"))
        tiers = []
        for key, label in (("starter", "Starter"), ("recommended", "Recommended")):
            b = rec[key]; tiers.append({"key": key, "label": label, "bundle": b, "quote": quote_for(p, b)})
        expl = advisor.explain(p, rec, tiers[1]["quote"]["price"]["monthly"], st["lang"])
        out = {"profile": p, "segment": rec["segment"], "segment_label": rec["segment_label"], "serviceability": serv,
               "tiers": tiers, "explanation": expl, "notes": rec["notes"], "removed": rec["removed"],
               "needs_survey": not serv["fibre"] and not serv["airfiber"],
               "gst_unlock": cat.blocked_by_gst(p, serv) if p.get("gst_status") not in cat.GST_OK else [],
               "addons": cat.addon_options(p, tiers[1]["bundle"])}
        st["profile"] = {k: v for k, v in p.items()}
        return out

    @app.post("/api/quote")
    def quote():
        d = request.get_json(force=True); st = get_session(d.get("sid"))
        if not st: return err("unknown session", 404)
        p = full_profile(st)
        order = store.load_order(d["order_id"]) if d.get("order_id") else None
        if order: p["gst_status"] = order.get("gst_status", p.get("gst_status"))
        bundle = {k: int(v) for k, v in (d.get("bundle") or {}).items() if k in cat.CAT.index and int(v) > 0}
        if not bundle: return err("empty bundle")
        q = quote_for(p, bundle)
        q["addons"] = cat.addon_options(p, bundle)
        return jsonify(q)

    # ---------------- order, consent, KYC ----------------
    @app.post("/api/order")
    def create_order():
        d = request.get_json(force=True); st = get_session(d.get("sid"))
        if not st: return err("unknown session", 404)
        p = full_profile(st)
        bundle = {k: int(v) for k, v in (d.get("bundle") or {}).items() if k in cat.CAT.index and int(v) > 0}
        q = quote_for(p, bundle)
        if not q["valid"]: return jsonify({"error": "bundle breaks catalogue rules", "violations": q["violations"]}), 422
        existing = store.load_order(st.get("order_id")) if st.get("order_id") else None
        if existing and not existing.get("milestones"):        # still a draft: update it instead of creating another
            existing.update({"bundle": bundle, "bundle_original": dict(bundle), "quote": q, "profile": p})
            if existing["status"].startswith("Paused"): existing["status"] = "Draft"
            store.save_order(existing); store.log(existing["id"], "customer", "order_updated", f"bundle {sorted(bundle)}; monthly {q['price']['monthly']}")
            return jsonify({"order_id": existing["id"], "quote": q, "consent": bool((existing.get("consent") or {}).get("id") and not existing["consent"].get("withdrawn"))})
        oid = store.new_id("ORD")
        order = {"id": oid, "session_id": st["sid"], "created": store.now(), "status": "Draft", "profile": p, "needs": st.get("needs", []),
                 "bundle": bundle, "bundle_original": dict(bundle), "quote": q, "serviceability": sv.check(p.get("pincode")), "gst_status": p.get("gst_status", "No"),
                 "kyc": None, "consent": None, "milestones": [], "sim_now": config.TODAY.isoformat()}
        store.save_order(order); store.log(oid, "customer", "order_created", f"bundle {sorted(bundle)}; monthly {q['price']['monthly']}")
        st["order_id"] = oid; store.save_session(st["sid"], st)
        return jsonify({"order_id": oid, "quote": q, "consent": False})

    @app.get("/api/consent")
    def consent_text(): return jsonify({**CONSENT_TEXT.get(request.args.get("lang", "en"), CONSENT_TEXT["en"]), "version": config.CONSENT_VERSION})

    @app.post("/api/order/<oid>/consent")
    def give_consent(oid):
        o = store.load_order(oid)
        if not o: return err("unknown order", 404)
        lang = (request.get_json(silent=True) or {}).get("lang", "en")
        cid = store.record_consent(oid, CONSENT_PURPOSE, CONSENT_FIELDS, lang)
        o["consent"] = {"id": cid, "version": config.CONSENT_VERSION, "ts": store.now(), "withdrawn": False}
        if o["status"].startswith("Paused"): o["status"] = "Draft"
        store.save_order(o); store.log(oid, "customer", "consent_given", f"{config.CONSENT_VERSION}, purpose: {CONSENT_PURPOSE}")
        return jsonify({"ok": True, "consent": o["consent"]})

    @app.post("/api/order/<oid>/consent/withdraw")
    def withdraw(oid):
        o = store.load_order(oid)
        if not o: return err("unknown order", 404)
        store.withdraw_consent(oid)
        o["consent"] = {**(o.get("consent") or {}), "withdrawn": True}; o["kyc"] = None; o["status"] = "Paused: consent withdrawn"
        store.save_order(o)
        store.log(oid, "customer", "consent_withdrawn", "processing stopped; held KYC results deleted; order paused")
        store.log(oid, "system", "data_deleted", "KYC result and masked identifiers removed from the order")
        return jsonify({"ok": True, "status": o["status"]})

    def reprice_for_gst(o):
        """After KYC says the GSTIN is not usable, strip products that need one and say what was removed."""
        p = {**o["profile"], "gst_status": o["gst_status"]}
        bundle, removed = dict(o["bundle"]), []
        for pid in list(bundle):
            if cat.eligibility(pid, p): removed.append(cat.name(pid)); bundle.pop(pid)
        for pid in list(bundle):
            deps = cat.needs_one_of(pid)
            if deps and not any(x in bundle for x in deps): removed.append(cat.name(pid)); bundle.pop(pid)
        o["bundle"], o["quote"] = bundle, quote_for(p, bundle)
        return removed

    @app.post("/api/order/<oid>/kyc")
    def run_kyc(oid):
        o = store.load_order(oid)
        if not o: return err("unknown order", 404)
        c = o.get("consent")
        if not c or c.get("withdrawn"):
            store.log(oid, "system", "kyc_blocked", "no consent on record; documents not read")
            return jsonify({"decision": "BLOCKED", "reason": "No consent recorded. Documents are not read until you agree."}), 403
        tmp = os.path.join(config.UPLOAD_TMP, oid); shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
        paths = {}
        try:
            specimen = request.form.get("specimen")
            if specimen:  # demo shortcut: use one of the 12 specimen applicants from the case data
                for t in DOC_TYPES:
                    src = os.path.join(config.DATA_DIR, "kyc_documents", f"{specimen}_{t}.png")
                    if os.path.exists(src): shutil.copy(src, os.path.join(tmp, t + ".png")); paths[t] = os.path.join(tmp, t + ".png")
            for t in DOC_TYPES:
                f = request.files.get(t)
                if f and f.filename:
                    ext = os.path.splitext(f.filename)[1].lower()
                    if ext not in (".png", ".jpg", ".jpeg"): return err("only png or jpg images")
                    dst = os.path.join(tmp, t + ext); f.save(dst); paths[t] = dst
            if not paths: return err("no documents provided")
            typed = (request.form.get("typed_gstin") or "").strip().upper() or None
            store.log(oid, "system", "kyc_started", f"{len(paths)} document(s) received")
            res = engine.check_documents(paths, consent=True, typed_gstin=typed, label=oid)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)  # delete images as soon as verification finishes
        gone = not os.path.exists(tmp)
        store.log(oid, "system", "images_deleted", f"document images removed from disk: {'yes' if gone else 'no'}")
        result = {"decision": res["decision"], "facts": res["facts"], "flags": [{"level": a, "text": b} for a, b in res["flags"]],
                  "images_deleted": gone}
        gs = res["facts"].get("gstin_status")
        if gs: o["gst_status"] = gs
        if o.get("bundle_original"):                      # a re-check starts again from what the owner chose
            o["bundle"] = dict(o["bundle_original"]); o["quote"] = quote_for({**o["profile"], "gst_status": o["gst_status"]}, o["bundle"])
        removed = []
        if res["decision"] == "LIMITED": removed = reprice_for_gst(o)
        o["kyc"] = result
        o["status"] = {"VERIFIED": "KYC verified", "REVIEW": "KYC under manual review", "LIMITED": "KYC verified for non-GST products",
                       "REUPLOAD": "Action needed: fix documents"}.get(res["decision"], "KYC")
        store.save_order(o)
        store.log(oid, "system", "kyc_result", f"{res['decision']}" + ((": " + " | ".join(b for a, b in res["flags"] if a != "INFO")) if any(a != "INFO" for a, b in res["flags"]) else ": all checks passed"))
        out = {**result, "order_status": o["status"], "removed_products": removed, "quote": o["quote"], "gst_status": o["gst_status"]}
        return jsonify(out)

    # ---------------- checkout and tracker ----------------
    LABELS = {"placed": "Order placed", "kyc": "KYC complete", "feasibility": "Site feasibility confirmed",
              "visit": "Engineer visit", "installed": "Installed", "active": "Activated"}

    def build_milestones(o):
        d0 = config.TODAY; inst = o["quote"]["price"]["install_days"]
        review = o["kyc"] and o["kyc"]["decision"] == "REVIEW"
        plan = [("placed", 0), ("kyc", 2 if review else 0), ("feasibility", max(1, min(2, inst - 1))), ("visit", max(2, inst - 1)),
                ("installed", max(2, inst)), ("active", max(3, inst + 1))]
        last, out = 0, []
        for k, off in plan:
            off = max(off, last); last = off
            out.append({"key": k, "label": LABELS[k] + (" (manual review)" if k == "kyc" and review else ""),
                        "planned": (d0 + dt.timedelta(days=off)).isoformat(), "actual": None})
        out[0]["actual"] = out[0]["planned"]
        return out

    @app.post("/api/order/<oid>/checkout")
    def checkout(oid):
        o = store.load_order(oid)
        if not o: return err("unknown order", 404)
        if not o.get("consent") or o["consent"].get("withdrawn"): return err("consent is needed before checkout", 409)
        k = o.get("kyc")
        if not k or k["decision"] not in KYC_PASS: return err("KYC must pass before checkout (fix the documents first)", 409)
        if not o["quote"]["valid"] or not o["bundle"]: return err("bundle is not valid", 409)
        upi = ((request.get_json(silent=True) or {}).get("upi") or "demo@upi").strip()
        if not re.fullmatch(r"[\w.\-]{2,}@[A-Za-z]{2,}", upi): return err("Enter a UPI ID like name@bank", 422)
        o["upi_masked"] = upi[0] + "•••" + upi[upi.index("@"):]
        o["milestones"] = build_milestones(o); o["status"] = "Order placed"; o["payment"] = "UPI autopay mandate (mock, no money moved)"
        o["sim_now"] = config.TODAY.isoformat()
        store.save_order(o); store.log(oid, "customer", "checkout", f"UPI autopay mandate created (mock) for {o['upi_masked']}")
        store.message(oid, "WhatsApp", f"Your order {oid} is placed. Expected activation {o['milestones'][-1]['planned']}. Track it here, no need to call.")
        if k["decision"] == "REVIEW":
            st = store.load_session(o["session_id"]) or {"sid": o["session_id"], "profile": o["profile"], "needs": o.get("needs", [])}
            lead = make_lead(st, "KYC needs manual review: " + "; ".join(f["text"] for f in k["flags"] if f["level"] == "REVIEW")[:200], o["profile"])
            store.log(oid, "system", "sent_to_back_office", lead["id"])
        return jsonify(order_view(o))

    def current_status(o):
        done = [m for m in o["milestones"] if m["actual"]]
        return done[-1]["label"] if done else o["status"]

    def order_view(o):
        o = dict(o)
        if o.get("milestones"):
            o["status"] = current_status(o)
            o["expected_activation"] = o["milestones"][-1]["planned"]
        o["messages"] = store.messages(o["id"]); o["events"] = store.events(o["id"], 40)
        return o

    @app.get("/api/order/<oid>")
    def get_order(oid):
        o = store.load_order(oid)
        return jsonify(order_view(o)) if o else err("unknown order", 404)

    @app.post("/api/order/<oid>/demo/advance")
    def advance(oid):
        o = store.load_order(oid)
        if not o or not o.get("milestones"): return err("order not placed", 404)
        days = int((request.get_json(silent=True) or {}).get("days", 1))
        now = dt.date.fromisoformat(o["sim_now"]) + dt.timedelta(days=days); o["sim_now"] = now.isoformat()
        for m in o["milestones"]:
            if m["actual"]: continue
            if dt.date.fromisoformat(m["planned"]) <= now:
                m["actual"] = m["planned"]
                store.message(oid, "WhatsApp", f"Update: {m['label']} ({m['planned']}).")
                store.log(oid, "system", "milestone", m["label"])
            else: break
        o["status"] = current_status(o); store.save_order(o)
        return jsonify(order_view(o))

    @app.post("/api/order/<oid>/demo/slip")
    def slip(oid):
        o = store.load_order(oid)
        if not o or not o.get("milestones"): return err("order not placed", 404)
        d = request.get_json(silent=True) or {}
        days, reason = int(d.get("days", 2)), d.get("reason") or "engineer availability"
        old = o["milestones"][-1]["planned"]
        for m in o["milestones"]:
            if not m["actual"]: m["planned"] = (dt.date.fromisoformat(m["planned"]) + dt.timedelta(days=days)).isoformat(); m["slipped"] = True
        new = o["milestones"][-1]["planned"]
        store.message(oid, "WhatsApp", f"Heads up: your activation moved from {old} to {new} ({reason}). We are sorry. Nothing for you to do, we will keep this page updated.")
        store.log(oid, "system", "date_slipped", f"{old} -> {new}: {reason}"); store.save_order(o)
        return jsonify(order_view(o))

    # ---------------- back office ----------------
    @app.get("/api/office")
    def office():
        orders = store.list_orders()
        rows = []
        for o in orders:
            if o["status"] == "Draft": continue
            v = order_view(o)
            rows.append({"id": o["id"], "status": v["status"], "business": o["profile"].get("business_type"), "city": o["profile"].get("city"),
                         "monthly": o["quote"]["price"]["monthly"], "kyc": (o.get("kyc") or {}).get("decision"),
                         "flags": [f["text"] for f in (o.get("kyc") or {}).get("flags", []) if f["level"] != "INFO"],
                         "expected": v.get("expected_activation"), "slipped": any(m.get("slipped") for m in o.get("milestones", []))})
        return jsonify({"leads": store.list_leads(), "orders": rows, "stalled": scoring.rank_stalled(25),
                        "model": {"auc_5fold": 0.71, "auc_chronological_holdout": 0.72, "top_decile_conv": 0.18, "overall_conv": 0.074,
                                  "note": "Logistic regression on fields known at lead creation. Prioritises, never rejects."}})

    @app.post("/api/office/lead/<lid>/assign")
    def assign(lid):
        leads = {l["id"]: l for l in store.list_leads()}
        if lid not in leads: return err("unknown lead", 404)
        l = leads[lid]; l["status"] = "assigned: " + (request.get_json(silent=True) or {}).get("to", l.get("route", "sales"))
        store.save_lead(l); return jsonify(l)

    @app.get("/api/audit")
    def audit(): return jsonify({"events": store.events(request.args.get("order"), 300), "consents": store.consents(request.args["order"]) if request.args.get("order") else []})

    @app.get("/api/specimens")
    def specimens(): return jsonify({"ids": [f"K{i:02d}" for i in range(1, 13)]})

    # ---------------- WhatsApp channel (Meta Cloud API webhook shape; sending is mocked) ----------------
    from . import whatsapp as wa

    @app.get("/whatsapp")
    def whatsapp_page(): return send_from_directory(STATIC, "whatsapp.html")

    @app.get("/api/whatsapp/webhook")
    def wa_verify():
        if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == config.WHATSAPP_VERIFY_TOKEN:
            return request.args.get("hub.challenge", ""), 200
        return err("verification failed", 403)

    @app.post("/api/whatsapp/webhook")
    def wa_webhook():
        raw = request.get_data()
        if config.WHATSAPP_APP_SECRET and not wa.signature_ok(raw, request.headers.get("X-Hub-Signature-256", ""), config.WHATSAPP_APP_SECRET):
            return err("bad signature", 403)
        payload = request.get_json(silent=True) or {}
        outbound, inbound = [], []
        for m in wa.messages_in(payload):
            phone = m.get("from", "")
            sid = wa.sid_for(phone); inbound.append({"from": phone, "type": m.get("type")})
            text = wa.text_of(m); lower = (text or "").strip().lower()
            st = get_session(sid)
            base = request.host_url.rstrip("/")
            if lower in wa.RESTART_WORDS or not st:
                st = advisor.new_session(sid); store.save_session(sid, st)
                outbound += wa.render(phone, advisor.first_message()); continue
            if text is None:                       # image, document, voice note, location...
                outbound += wa.render(phone, [{"text": wa.MEDIA_NOTE[st["lang"]].format(link=f"{base}/?s={sid}"), "chips": []}]); continue
            if lower in wa.HUMAN_WORDS:
                lead = make_lead(st, "Owner asked for a person on WhatsApp")
                outbound += wa.render(phone, [{"text": wa.HUMAN_NOTE[st["lang"]].format(route=lead["route"]), "chips": []}]); continue
            if st["done"] and not st["escalate"]:
                outbound += wa.render(phone, [{"text": wa.AGAIN_NOTE[st["lang"]].format(link=f"{base}/?s={sid}"), "chips": []}]); continue
            out = run_chat(st, text)
            outbound += wa.render(phone, out["messages"])
            if out.get("escalated"):
                outbound += wa.render(phone, [{"text": wa.HUMAN_NOTE[st["lang"]].format(route=out["lead"]["route"]), "chips": []}])
            elif out.get("recommendation"):
                outbound += wa.render(phone, [{"text": wa.summary(out["recommendation"], st["lang"], f"{base}/?s={sid}"), "chips": []}])
        return jsonify({"status": "ok", "inbound": inbound, "outbound": outbound})

    return app
