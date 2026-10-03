"""Simulador de nodo/gateway SMS con cola store-and-forward.
Uso:
  python gateway_sim.py send "NDIO" CONSENT_YES 0.99 GREEN     # encola un SMS
  python gateway_sim.py send "nina homa kali" SYMPTOM_REPORT 0.9 RED
  python gateway_sim.py status                                  # ver cola
  python gateway_sim.py flush                                   # intenta sincronizar (simula 'volvió la señal')
Variables: SERVER=http://127.0.0.1:8000  API_KEY=dev-key  PHONE=+255700000000
"""
import hashlib, json, os, sqlite3, sys, urllib.request, uuid
from datetime import datetime, timezone

SERVER = os.getenv("SERVER", "http://127.0.0.1:8000")
KEY = os.getenv("API_KEY", "dev-key")
SALT = os.getenv("PHONE_SALT", "cambia-esta-sal")
NODE = os.getenv("NODE_ID", "node-01")
BATCH = 20

db = sqlite3.connect(os.getenv("OUTBOX_DB", "outbox.db"))
db.execute("CREATE TABLE IF NOT EXISTS outbox(msg_id TEXT PRIMARY KEY, payload TEXT, tries INT DEFAULT 0)")

def patient_ref(phone): return hashlib.sha256((SALT + phone).encode()).hexdigest()[:32]

def enqueue(body, intent="UNKNOWN", conf=0.0, prio="GREEN", rules=()):
    m = {"msg_id": str(uuid.uuid4()), "node_id": NODE,
         "patient_ref": patient_ref(os.getenv("PHONE", "+255700000000")),
         "ts": datetime.now(timezone.utc).isoformat(), "lang": "sw", "body": body,
         "intent": intent, "confidence": float(conf), "priority": prio, "rule_hits": list(rules)}
    db.execute("INSERT INTO outbox(msg_id,payload) VALUES(?,?)", (m["msg_id"], json.dumps(m)))
    db.commit(); return m["msg_id"]

def flush():
    rows = db.execute("SELECT msg_id,payload FROM outbox ORDER BY rowid LIMIT ?", (BATCH,)).fetchall()
    if not rows: print("cola vacía"); return
    req = urllib.request.Request(SERVER + "/sync",
        data=json.dumps({"messages": [json.loads(p) for _, p in rows]}).encode(),
        headers={"Content-Type": "application/json", "X-API-Key": KEY})
    try:
        acks = json.load(urllib.request.urlopen(req, timeout=10))["acks"]
    except Exception as e:                       # sin señal: NO se borra nada, se reintenta luego
        db.execute("UPDATE outbox SET tries=tries+1"); db.commit()
        print(f"sin conexión ({e}); {len(rows)} mensajes siguen en cola"); return
    for a in acks:                               # borrar SOLO lo confirmado por el servidor
        db.execute("DELETE FROM outbox WHERE msg_id=?", (a["msg_id"],))
        print(f"ack {a['msg_id'][:8]} -> {a['reply_code']} | SMS de vuelta: {a['reply_text']}")
    db.commit()

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "send": print("encolado", enqueue(*sys.argv[2:6]))
    elif cmd == "flush": flush()
    else: print("en cola:", db.execute("SELECT COUNT(*) FROM outbox").fetchone()[0])
