"""SQLite order store: sessions, orders, consent records, audit events, simulated notifications, escalated leads.
No document images are ever stored here; only results and masked identifiers."""
import sqlite3, json, datetime as dt, uuid, threading
from . import config

_lock = threading.RLock()
SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, created TEXT, state TEXT);
CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY, session_id TEXT, created TEXT, status TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS consents(id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT, version TEXT, purpose TEXT,
    fields TEXT, lang TEXT, ts TEXT, withdrawn_ts TEXT);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT, ts TEXT, actor TEXT, action TEXT, detail TEXT);
CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT, ts TEXT, channel TEXT, text TEXT);
CREATE TABLE IF NOT EXISTS leads(id TEXT PRIMARY KEY, created TEXT, session_id TEXT, reason TEXT, score REAL, status TEXT, data TEXT);
"""


def conn():
    c = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init():
    with _lock, conn() as c:
        c.executescript(SCHEMA)


def now(): return dt.datetime.now().isoformat(timespec="seconds")
def new_id(prefix): return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


# ---- sessions ----
def save_session(sid, state):
    with _lock, conn() as c:
        c.execute("INSERT INTO sessions(id,created,state) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET state=excluded.state",
                  (sid, now(), json.dumps(state, default=str)))


def load_session(sid):
    with _lock, conn() as c:
        r = c.execute("SELECT state FROM sessions WHERE id=?", (sid,)).fetchone()
    return json.loads(r["state"]) if r else None


# ---- orders ----
def save_order(order):
    with _lock, conn() as c:
        c.execute("INSERT INTO orders(id,session_id,created,status,data) VALUES(?,?,?,?,?) "
                  "ON CONFLICT(id) DO UPDATE SET status=excluded.status, data=excluded.data",
                  (order["id"], order.get("session_id"), order.get("created", now()), order["status"], json.dumps(order, default=str)))


def load_order(oid):
    with _lock, conn() as c:
        r = c.execute("SELECT data FROM orders WHERE id=?", (oid,)).fetchone()
    return json.loads(r["data"]) if r else None


def list_orders():
    with _lock, conn() as c:
        return [json.loads(r["data"]) for r in c.execute("SELECT data FROM orders ORDER BY created DESC")]


# ---- consent, audit, messages ----
def record_consent(order_id, purpose, fields, lang):
    with _lock, conn() as c:
        cur = c.execute("INSERT INTO consents(order_id,version,purpose,fields,lang,ts) VALUES(?,?,?,?,?,?)",
                        (order_id, config.CONSENT_VERSION, purpose, json.dumps(fields), lang, now()))
        return cur.lastrowid


def withdraw_consent(order_id):
    with _lock, conn() as c:
        c.execute("UPDATE consents SET withdrawn_ts=? WHERE order_id=? AND withdrawn_ts IS NULL", (now(), order_id))


def consents(order_id):
    with _lock, conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM consents WHERE order_id=? ORDER BY id", (order_id,))]


def log(order_id, actor, action, detail=""):
    with _lock, conn() as c:
        c.execute("INSERT INTO events(order_id,ts,actor,action,detail) VALUES(?,?,?,?,?)", (order_id, now(), actor, action, detail))


def events(order_id=None, limit=200):
    with _lock, conn() as c:
        q, a = "SELECT * FROM events", ()
        if order_id: q, a = q + " WHERE order_id=?", (order_id,)
        return [dict(r) for r in c.execute(q + " ORDER BY id DESC LIMIT ?", a + (limit,))]


def message(order_id, channel, text):
    with _lock, conn() as c:
        c.execute("INSERT INTO messages(order_id,ts,channel,text) VALUES(?,?,?,?)", (order_id, now(), channel, text))


def messages(order_id):
    with _lock, conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM messages WHERE order_id=? ORDER BY id", (order_id,))]


# ---- escalated leads (back office) ----
def save_lead(lead):
    with _lock, conn() as c:
        c.execute("INSERT INTO leads(id,created,session_id,reason,score,status,data) VALUES(?,?,?,?,?,?,?) "
                  "ON CONFLICT(id) DO UPDATE SET reason=excluded.reason, score=excluded.score, status=excluded.status, data=excluded.data",
                  (lead["id"], lead.get("created", now()), lead.get("session_id"), lead["reason"], lead["score"], lead.get("status", "open"), json.dumps(lead, default=str)))


def list_leads():
    with _lock, conn() as c:
        return [json.loads(r["data"]) for r in c.execute("SELECT data FROM leads ORDER BY score DESC")]
