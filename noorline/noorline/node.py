"""Nodo comunitario: recibe SMS/IVR, decide localmente (offline), alerta localmente y encola (store-and-forward)."""
import json, os, sqlite3, uuid
from datetime import datetime, timezone
from cryptography.fernet import Fernet
from .common import ROOT, pseudo_id
from .decision import RANK, decidir, reply_text
from .intent import IntentClassifier
from .policy import load_policy

CONSENT_VERSION = "v1-2026-10"


def _fernet() -> Fernet:
    """Cifrado de campo en reposo (sustituto de SQLCipher para la demo). Clave: env NOORLINE_KEY o archivo local 0600."""
    key = os.getenv("NOORLINE_KEY")
    if key:
        return Fernet(key.encode())
    kp = ROOT / ".noorline_key"
    if not kp.exists():
        kp.write_bytes(Fernet.generate_key())
        kp.chmod(0o600)
    return Fernet(kp.read_bytes())


def now_iso():
    return datetime.now(timezone.utc).isoformat()


class Node:
    def __init__(self, db_path, policy=None, classifier=None, on_alert=None):
        self.policy = policy or load_policy()
        self.clf = classifier or IntentClassifier.load()
        self.on_alert = on_alert or (lambda ev: None)
        self.local_alerts = []
        self.f = _fernet()
        self.db = sqlite3.connect(str(db_path), check_same_thread=False)
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS patients(pid TEXT PRIMARY KEY, lang TEXT, consent INTEGER DEFAULT 0, consent_ts TEXT, consent_version TEXT);
        CREATE TABLE IF NOT EXISTS consent_log(id INTEGER PRIMARY KEY AUTOINCREMENT, pid TEXT, ts TEXT, action TEXT, version TEXT, channel TEXT);
        CREATE TABLE IF NOT EXISTS outbox(event_id TEXT PRIMARY KEY, pid TEXT, rank INTEGER, state TEXT DEFAULT 'pendiente', attempts INTEGER DEFAULT 0, created TEXT, payload BLOB);
        """)

    # --- consentimiento (DTMF auditable): 1 = acepto, 2 = no acepto, 9 = revocar
    def consent(self, phone, digit, lang="es", channel="ivr_dtmf"):
        pid = pseudo_id(phone)
        action = {"1": "otorgado", "2": "rechazado", "9": "revocado"}.get(str(digit))
        if not action:
            return "tecla_invalida"
        self.db.execute("INSERT OR IGNORE INTO patients(pid, lang) VALUES(?,?)", (pid, lang))
        ok = 1 if action == "otorgado" else 0
        self.db.execute("UPDATE patients SET lang=?, consent=?, consent_ts=?, consent_version=? WHERE pid=?",
                        (lang, ok, now_iso(), CONSENT_VERSION, pid))
        self.db.execute("INSERT INTO consent_log(pid, ts, action, version, channel) VALUES(?,?,?,?,?)",
                        (pid, now_iso(), action, CONSENT_VERSION, channel))
        if action == "revocado":  # minimizacion: borrar texto de eventos aun no enviados
            for eid, blob in self.db.execute("SELECT event_id, payload FROM outbox WHERE pid=? AND state='pendiente'", (pid,)).fetchall():
                ev = json.loads(self.f.decrypt(blob))
                ev["text"] = None
                self.db.execute("UPDATE outbox SET payload=? WHERE event_id=?", (self.f.encrypt(json.dumps(ev).encode()), eid))
        self.db.commit()
        return action

    def _patient(self, phone):
        pid = pseudo_id(phone)
        self.db.execute("INSERT OR IGNORE INTO patients(pid, lang) VALUES(?,?)", (pid, self.policy.get("language_default", "es")))
        row = self.db.execute("SELECT lang, consent FROM patients WHERE pid=?", (pid,)).fetchone()
        return pid, row[0], bool(row[1])

    def handle_message(self, phone, text):
        pid, lang, consent = self._patient(phone)
        d = decidir(text, self.policy, self.clf, consent=consent)
        ev = {"event_id": str(uuid.uuid4()), "patient_id": pid, "ts": now_iso(), "lang": lang,
              "text": text if consent else None,  # sin consentimiento NO se guarda contenido
              **d.dict()}
        self.db.execute("INSERT INTO outbox(event_id, pid, rank, created, payload) VALUES(?,?,?,?,?)",
                        (ev["event_id"], pid, RANK[d.nivel], ev["ts"], self.f.encrypt(json.dumps(ev).encode())))
        self.db.commit()
        if d.nivel == "alto":  # alerta LOCAL: funciona sin red
            self.local_alerts.append(ev)
            self.on_alert(ev)
        return {"event_id": ev["event_id"], "nivel": d.nivel, "reason": d.reason,
                "reply_key": d.reply_key, "reply": reply_text(d.reply_key, lang, self.policy)}

    def pending(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM outbox WHERE state='pendiente'").fetchone()[0]

    def sync(self, send, batch=50):
        """Store-and-forward: urgencias primero; se detiene al primer fallo de red. send(payload) lanza excepcion si falla."""
        sent = 0
        rows = self.db.execute("SELECT event_id, payload FROM outbox WHERE state='pendiente' ORDER BY rank, created LIMIT ?", (batch,)).fetchall()
        for eid, blob in rows:
            try:
                send(json.loads(self.f.decrypt(blob)))
            except Exception:
                self.db.execute("UPDATE outbox SET attempts=attempts+1 WHERE event_id=?", (eid,))
                self.db.commit()
                break
            self.db.execute("UPDATE outbox SET state='confirmado' WHERE event_id=?", (eid,))
            sent += 1
        self.db.commit()
        return {"sent": sent, "pending": self.pending()}


def http_sender(url, api_key=None):
    """Sender real por HTTP (stdlib, sin dependencias) para correr nodo y servidor en procesos separados."""
    import urllib.request

    def send(payload):
        req = urllib.request.Request(url.rstrip("/") + "/events", data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json", **({"X-API-Key": api_key} if api_key else {})})
        urllib.request.urlopen(req, timeout=5).read()
    return send
