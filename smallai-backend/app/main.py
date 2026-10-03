import json, os
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, Header, HTTPException
from . import db
from .catalog import REPLIES, CONFIDENCE_THRESHOLD, PRIORITY_ORDER
from .schemas import SmsEnvelope, Ack, SyncRequest, SyncResponse, CaseAction

app = FastAPI(title="Small AI Health Backend")

def auth(x_api_key: str = Header(default="")):
    if x_api_key != os.getenv("API_KEY", "dev-key"):
        raise HTTPException(401, "bad api key")

def now(): return datetime.now(timezone.utc).isoformat()

def ack(m: SmsEnvelope, code: str, priority=None, stored=False, lang_pref="sw") -> Ack:
    return Ack(msg_id=m.msg_id, reply_code=code,
               reply_text=REPLIES[code].get(m.lang, REPLIES[code]["en"]),
               priority=priority, stored=stored)

def process(m: SmsEnvelope) -> Ack:
    """Árbol determinista. Orden importa: borrado > consentimiento > fail-safe > caso."""
    # 1. BORRAR (derecho al borrado). Siempre funciona, con o sin consentimiento.
    if m.intent == "DELETE_DATA" or m.body.strip().upper() == "BORRAR":
        db.run("DELETE FROM cases WHERE patient_ref=?", (m.patient_ref,))
        db.run("DELETE FROM consent WHERE patient_ref=?", (m.patient_ref,))
        return ack(m, "R_DELETED")

    # 2. Consentimiento
    row = db.rows("SELECT status FROM consent WHERE patient_ref=?", (m.patient_ref,))
    status = row[0]["status"] if row else None
    if status != "YES":
        if m.intent == "CONSENT_YES" or m.body.strip().upper() == "NDIO":
            db.run("INSERT OR REPLACE INTO consent VALUES(?,?,?)", (m.patient_ref, "YES", now()))
            return ack(m, "R_CONSENT_OK")
        if m.intent == "CONSENT_NO" or m.body.strip().upper() == "HAPANA":
            db.run("INSERT OR REPLACE INTO consent VALUES(?,?,?)", (m.patient_ref, "NO", now()))
            return ack(m, "R_CONSENT_NO")
        return ack(m, "R_CONSENT_ASK")          # sin consentimiento: NO se guarda el body

    # 3. Fail-safe: baja confianza o intención desconocida => humano, nunca adivinar
    if m.intent == "UNKNOWN" or m.confidence < CONFIDENCE_THRESHOLD:
        priority, code = "REVIEW", "R_NOT_SURE"
    else:
        priority = m.priority
        code = "R_RECEIVED_URGENT" if priority == "RED" else "R_RECEIVED"

    # 4. Guardar caso (idempotente por msg_id: reenvíos del store-and-forward no duplican)
    db.run("""INSERT OR IGNORE INTO cases
      (msg_id,patient_ref,node_id,ts,lang,body,intent,confidence,priority,rule_hits,reply_code)
      VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
      (m.msg_id, m.patient_ref, m.node_id, m.ts, m.lang, m.body, m.intent,
       m.confidence, priority, json.dumps(m.rule_hits), code))
    return ack(m, code, priority=priority, stored=True)

# ---------- Gateway / nodo ----------
@app.post("/sms/inbound", response_model=Ack, dependencies=[Depends(auth)])
def sms_inbound(m: SmsEnvelope):
    """Un SMS en tiempo real (hay cobertura)."""
    return process(m)

@app.post("/sync", response_model=SyncResponse, dependencies=[Depends(auth)])
def sync(req: SyncRequest):
    """Lote del outbox del nodo. El nodo borra de su cola SOLO los msg_id con ack."""
    return SyncResponse(acks=[process(m) for m in req.messages])

# ---------- Panel clínico ----------
@app.get("/cases", dependencies=[Depends(auth)])
def list_cases(status: str = "OPEN"):
    cs = db.rows("SELECT * FROM cases WHERE status=?", (status,))
    for c in cs: c["rule_hits"] = json.loads(c["rule_hits"] or "[]")
    cs.sort(key=lambda c: (PRIORITY_ORDER[c["priority"]], c["ts"]))
    return cs

@app.post("/cases/{msg_id}/action", dependencies=[Depends(auth)])
def case_action(msg_id: str, a: CaseAction):
    """La IA no actúa; una persona cierra el caso."""
    cur = db.run("UPDATE cases SET status=?, reviewer=?, note=? WHERE msg_id=?",
                 ("CLOSED" if a.action == "CLOSED" else a.action, a.reviewer, a.note, msg_id))
    if cur.rowcount == 0: raise HTTPException(404, "case not found")
    return {"ok": True}

@app.get("/health")
def health(): return {"ok": True}
