import os, uuid, pytest
os.environ["DB_PATH"] = ":memory:"
from fastapi.testclient import TestClient
from app import db
from app.main import app

H = {"X-API-Key": "dev-key"}
P = "hash_patient_0001"

@pytest.fixture(autouse=True)
def fresh():
    db.reset(); yield

def msg(body, intent="UNKNOWN", conf=0.0, prio="GREEN", p=P):
    return {"msg_id": str(uuid.uuid4()), "node_id": "node-01", "patient_ref": p,
            "ts": "2026-10-03T10:00:00Z", "lang": "sw", "body": body,
            "intent": intent, "confidence": conf, "priority": prio, "rule_hits": []}

c = TestClient(app)
def post(m): return c.post("/sms/inbound", json=m, headers=H).json()

def test_no_consent_stores_nothing():
    r = post(msg("nina homa", "SYMPTOM_REPORT", 0.9))
    assert r["reply_code"] == "R_CONSENT_ASK" and not r["stored"]
    assert c.get("/cases", headers=H).json() == []

def test_consent_then_case_and_priority_order():
    post(msg("NDIO", "CONSENT_YES", 0.99))
    post(msg("miadi", "APPOINTMENT_REQUEST", 0.9, "GREEN"))
    post(msg("dharura", "SYMPTOM_REPORT", 0.9, "RED"))
    cases = c.get("/cases", headers=H).json()
    assert [x["priority"] for x in cases] == ["RED", "GREEN"]

def test_failsafe_low_confidence():
    post(msg("NDIO", "CONSENT_YES", 0.99))
    r = post(msg("???", "SYMPTOM_REPORT", 0.30, "RED"))
    assert r["reply_code"] == "R_NOT_SURE" and r["priority"] == "REVIEW"

def test_idempotent_sync():
    post(msg("NDIO", "CONSENT_YES", 0.99))
    m = msg("miadi", "APPOINTMENT_REQUEST", 0.9)
    for _ in range(2):
        r = c.post("/sync", json={"messages": [m]}, headers=H).json()
        assert r["acks"][0]["stored"]
    assert len(c.get("/cases", headers=H).json()) == 1

def test_borrar_deletes_everything():
    post(msg("NDIO", "CONSENT_YES", 0.99))
    post(msg("miadi", "APPOINTMENT_REQUEST", 0.9))
    r = post(msg("BORRAR", "DELETE_DATA", 0.99))
    assert r["reply_code"] == "R_DELETED"
    assert c.get("/cases", headers=H).json() == []
    assert post(msg("hola"))["reply_code"] == "R_CONSENT_ASK"   # consentimiento también borrado

def test_auth_and_human_action():
    assert c.get("/cases").status_code == 401
    post(msg("NDIO", "CONSENT_YES", 0.99))
    m = msg("miadi", "APPOINTMENT_REQUEST", 0.9); post(m)
    r = c.post(f"/cases/{m['msg_id']}/action", headers=H,
               json={"action": "CLOSED", "reviewer": "nurse1", "note": "ok"})
    assert r.status_code == 200 and c.get("/cases", headers=H).json() == []
