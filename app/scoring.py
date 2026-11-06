"""Propensity score: which leads are most likely to convert, so human time goes where it pays.

Logistic regression on fields known when the lead is created (no stage, drop reason or dates, to avoid leakage).
On the case data: ROC-AUC about 0.71 (5-fold) and 0.72 on a chronological holdout; top-decile leads convert at about 18%
against 7.4% overall. Modest: use it to prioritise, never to reject a lead.
"""
import pandas as pd, numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from . import config

CAT = ["lead_source", "segment", "city_tier", "preferred_language", "annual_turnover_band", "has_gstin", "has_udyam",
       "current_internet", "current_provider"]
NUM = ["employee_count", "num_sites", "monthly_telecom_spend_inr", "n_int"]
_model, _df = None, None


def _features(df):
    X = df[CAT + NUM].copy(); X["city_tier"] = X["city_tier"].astype(str); return X


def load():
    global _model, _df
    if _model is not None: return _model, _df
    df = pd.read_csv(f"{config.DATA_DIR}/smb_leads.csv")
    df["n_int"] = df.products_of_interest.fillna("").str.count(";") + 1
    df["y"] = (df.outcome == "Activated").astype(int)
    ct = ColumnTransformer([("c", OneHotEncoder(handle_unknown="ignore"), CAT), ("n", StandardScaler(), NUM)])
    _model = make_pipeline(ct, LogisticRegression(max_iter=2000, C=0.5)).fit(_features(df), df.y)
    df["score"] = _model.predict_proba(_features(df))[:, 1]
    _df = df
    return _model, _df


SEG_LABEL = {"micro": "Micro retail & services", "professional": "Professional offices",
             "multisite": "Small multi-site businesses", "manufacturer": "Small manufacturers"}


def score_profile(profile, needs=None):
    """Score a live advisor session. Source is set to 'Website form', the closest digital channel in the history."""
    m, _ = load()
    row = pd.DataFrame([{
        "lead_source": "Website form", "segment": SEG_LABEL.get(profile.get("segment"), "Micro retail & services"),
        "city_tier": str(profile.get("tier", 2)), "preferred_language": "Hindi" if profile.get("lang") == "hi" else "English",
        "annual_turnover_band": "40 lakh - 1.5 cr", "has_gstin": "Y" if profile.get("gst_registered") else "N", "has_udyam": "N",
        "current_internet": profile.get("current_internet") or "Mobile hotspot", "current_provider": "Other",
        "employee_count": profile.get("employees", 1), "num_sites": profile.get("sites", 1),
        "monthly_telecom_spend_inr": profile.get("monthly_spend", 0), "n_int": len(needs or []) + 1}])
    return float(m.predict_proba(row)[:, 1][0])


def rank_stalled(n=25):
    """The historical leads that stalled after contact, ranked by score: the 'who should sales call first' list."""
    _, df = load()
    d = df[(df.outcome == "Dropped") & (df.stage_reached.isin(["Needs assessed", "Quote accepted", "KYC complete"]))]
    d = d.sort_values("score", ascending=False).head(n)
    return [{"lead_id": r.lead_id, "business_type": r.business_type, "segment": r.segment, "city": r.city,
             "source": r.lead_source, "stage": r.stage_reached, "reason": r.drop_reason, "score": round(float(r.score), 3)}
            for r in d.itertuples()]


def decile_lift():
    _, df = load()
    k = len(df) // 10; top = df.sort_values("score", ascending=False).head(k)
    return {"top_decile_conv": round(float(top.y.mean()), 3), "overall": round(float(df.y.mean()), 3)}
