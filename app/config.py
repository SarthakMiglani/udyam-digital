"""Settings. All identifiers and registries in this project are synthetic (case data)."""
import os, datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("UDYAM_DATA_DIR", os.path.join(ROOT, "data"))
DB_PATH = os.environ.get("UDYAM_DB", os.path.join(ROOT, "udyam.db"))
# The case README fixes "today" for date-based checks (address proof <= 90 days old).
TODAY = dt.date.fromisoformat(os.environ.get("UDYAM_TODAY", "2026-07-15"))
CONSENT_VERSION = "v1-2026-11"
UPLOAD_TMP = os.environ.get("UDYAM_TMP", os.path.join(ROOT, ".tmp_uploads"))
# Optional hosted LLM (profile extraction + plain-language explanation only).
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
LLM_TIMEOUT_S = float(os.environ.get("UDYAM_LLM_TIMEOUT", "4"))

WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "udyam-demo")
WHATSAPP_APP_SECRET = os.environ.get("WHATSAPP_APP_SECRET", "")      # when set, webhook calls must carry a valid X-Hub-Signature-256
