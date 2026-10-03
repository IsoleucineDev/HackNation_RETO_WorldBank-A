"""Servidor central: recibe eventos (idempotente), bandeja HITL, auditoria con hash encadenado, escalamiento por timeout."""
import hashlib, json, os, sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from pathlib import Path
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from .common import ROOT
from .decision import RANK
from .policy import load_policy

ACTIONS = {"confirmar_urgencia": "alto", "bajar_a_rutina": "bajo", "pedir_aclaracion": "medio", "resolver": None}


class Event(BaseModel):
    event_id: str
    patient_id: str
    ts: str
    nivel: str
    intent: str = ""
    conf: float = 0.0
    p_urg: float = 0.0
    flags: list = []
    reason: str = ""
    reply_key: str = ""
    lang: str = "es"
    text: Optional[str] = None
    auto_confirm: bool = False


class Action(BaseModel):
    action: str
    actor: str


def create_app(db_path=None, policy=None):
    policy = policy or load_policy()
    # En produccion (Railway) el contenedor se niega a arrancar sin API key: nunca queda abierto por descuido.
    if os.getenv("NOORLINE_ENV") == "production" and not os.getenv("NOORLINE_API_KEY"):
        raise RuntimeError("NOORLINE_API_KEY es obligatoria cuando NOORLINE_ENV=production")
    # NOORLINE_DB debe apuntar a un Volume de Railway (ej. /data/server.db) para que sobreviva a los redeploys.
    path = str(db_path or os.getenv("NOORLINE_DB") or ROOT / "data" / "server.db")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    app = FastAPI(title="NoorLine server", version="0.1.0")
    origins = [o.strip() for o in os.getenv("NOORLINE_CORS_ORIGINS", "").split(",") if o.strip()]
    if origins:  # solo si el frontend llama directo al backend (con el rewrite de Vercel no hace falta)
        app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"], allow_headers=["X-API-Key", "Content-Type"])
    db = sqlite3.connect(path, check_same_thread=False)
    db.executescript("""
    CREATE TABLE IF NOT EXISTS cases(event_id TEXT PRIMARY KEY, level TEXT, rank INTEGER, status TEXT DEFAULT 'open', received TEXT, updated TEXT, data TEXT);
    CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, actor TEXT, event TEXT, detail TEXT, prev TEXT, hash TEXT);
    """)

    def now():
        return datetime.now(timezone.utc)

    def audit(actor, event, detail):
        prev = (db.execute("SELECT hash FROM audit ORDER BY id DESC LIMIT 1").fetchone() or ["GENESIS"])[0]
        ts = now().isoformat()
        h = hashlib.sha256(f"{prev}|{ts}|{actor}|{event}|{detail}".encode()).hexdigest()
        db.execute("INSERT INTO audit(ts, actor, event, detail, prev, hash) VALUES(?,?,?,?,?,?)", (ts, actor, event, detail, prev, h))

    def auth(x_api_key: Optional[str] = Header(default=None)):
        key = os.getenv("NOORLINE_API_KEY")  # sin clave configurada = modo demo abierto
        if key and x_api_key != key:
            raise HTTPException(401, "API key invalida")

    @app.get("/health")
    def health():
        return {"ok": True, "demo_open": not os.getenv("NOORLINE_API_KEY")}

    @app.post("/events", dependencies=[Depends(auth)])
    def post_event(ev: Event):
        if ev.nivel not in RANK:
            raise HTTPException(422, "nivel invalido")
        if db.execute("SELECT 1 FROM cases WHERE event_id=?", (ev.event_id,)).fetchone():
            return {"status": "duplicate", "event_id": ev.event_id}  # idempotencia
        t = now().isoformat()
        db.execute("INSERT INTO cases(event_id, level, rank, received, updated, data) VALUES(?,?,?,?,?,?)",
                   (ev.event_id, ev.nivel, RANK[ev.nivel], t, t, ev.model_dump_json()))
        audit("node", "evento_recibido", f"{ev.event_id}|{ev.nivel}|{ev.reason}")  # sin texto clinico en el log
        db.commit()
        return {"status": "stored", "event_id": ev.event_id}

    @app.get("/cases", dependencies=[Depends(auth)])
    def cases(status: str = "open"):
        rows = db.execute("SELECT event_id, level, status, received, data FROM cases WHERE status=? ORDER BY rank, received", (status,)).fetchall()
        return [{"event_id": r[0], "level": r[1], "status": r[2], "received": r[3], **json.loads(r[4])} | {"level": r[1]} for r in rows]

    @app.post("/cases/{event_id}/action", dependencies=[Depends(auth)])
    def act(event_id: str, a: Action):
        if a.action not in ACTIONS:
            raise HTTPException(422, f"accion invalida: {list(ACTIONS)}")
        if not a.actor.strip():
            raise HTTPException(422, "actor humano requerido (nunca se baja un caso sin humano)")
        row = db.execute("SELECT level FROM cases WHERE event_id=?", (event_id,)).fetchone()
        if not row:
            raise HTTPException(404, "caso no existe")
        new_level = ACTIONS[a.action] or row[0]
        status = "resuelto" if a.action == "resolver" else "open"
        db.execute("UPDATE cases SET level=?, rank=?, status=?, updated=? WHERE event_id=?",
                   (new_level, RANK[new_level], status, now().isoformat(), event_id))
        audit(a.actor, a.action, f"{event_id}|{row[0]}->{new_level}")
        db.commit()
        return {"event_id": event_id, "level": new_level, "status": status}

    @app.post("/admin/escalate", dependencies=[Depends(auth)])
    def escalate(minutes_ahead: int = 0):
        """Fail-safe: Medio sin atencion humana dentro del timeout sube a Alto."""
        limit = now() + timedelta(minutes=minutes_ahead) - timedelta(minutes=policy["escalation"]["medio_timeout_min"])
        ids = [r[0] for r in db.execute("SELECT event_id FROM cases WHERE status='open' AND level='medio' AND received<=?", (limit.isoformat(),)).fetchall()]
        for i in ids:
            db.execute("UPDATE cases SET level='alto', rank=0, updated=? WHERE event_id=?", (now().isoformat(), i))
            audit("sistema", "auto_escalada_a_alto", i)
        db.commit()
        return {"escalated": ids}

    @app.get("/audit/verify", dependencies=[Depends(auth)])
    def verify():
        prev, n = "GENESIS", 0
        for _id, ts, actor, event, detail, p, h in db.execute("SELECT * FROM audit ORDER BY id").fetchall():
            if p != prev or h != hashlib.sha256(f"{prev}|{ts}|{actor}|{event}|{detail}".encode()).hexdigest():
                return {"valid": False, "broken_at": _id}
            prev, n = h, n + 1
        return {"valid": True, "entries": n}

    @app.get("/", response_class=HTMLResponse)
    def panel():
        return PANEL

    app.state.db = db
    return app


PANEL = """<!doctype html><html lang=es><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>NoorLine - Bandeja clinica</title><style>
body{font-family:system-ui;margin:0;background:#f6f7f9}header{background:#0b3a53;color:#fff;padding:12px 16px}
.c{margin:10px;padding:10px 14px;border-radius:8px;background:#fff;border-left:8px solid #999}
.alto{border-color:#d62828}.medio{border-color:#f4a100}.bajo{border-color:#2a9d4a}
button{margin:4px 4px 0 0;padding:6px 10px;border:0;border-radius:6px;background:#0b3a53;color:#fff;cursor:pointer}
small{color:#555}</style><header><b>NoorLine</b> - bandeja de casos (la IA prioriza; una persona decide)</header><div id=l></div>
<script>
const key=new URLSearchParams(location.search).get('key'),H=key?{'X-API-Key':key}:{};let last=0;
function beep(){try{const a=new AudioContext(),o=a.createOscillator();o.connect(a.destination);o.start();setTimeout(()=>o.stop(),300)}catch(e){}}
async function act(id,action){const actor=prompt('Su nombre (obligatorio):');if(!actor)return;
await fetch('/cases/'+id+'/action',{method:'POST',headers:{...H,'Content-Type':'application/json'},body:JSON.stringify({action,actor})});load()}
async function load(){const r=await fetch('/cases',{headers:H});if(!r.ok){l.textContent='Error '+r.status;return}
const cs=await r.json(),n=cs.filter(c=>c.level=='alto').length;if(n>last)beep();last=n;document.title=(n?'('+n+') ':'')+'NoorLine';
l.innerHTML=cs.map(c=>`<div class="c ${c.level}"><b>${c.level.toUpperCase()}</b> - ${c.reason} <small>conf ${c.conf.toFixed(2)} | ${c.intent} | ${c.received}</small>
<div>${c.text?c.text.replace(/</g,'&lt;'):'<i>(sin contenido: sin consentimiento)</i>'}</div>
<button onclick="act('${c.event_id}','confirmar_urgencia')">Confirmar urgencia</button><button onclick="act('${c.event_id}','bajar_a_rutina')">Bajar a rutina</button>
<button onclick="act('${c.event_id}','pedir_aclaracion')">Pedir aclaracion</button><button onclick="act('${c.event_id}','resolver')">Resolver</button></div>`).join('')||'<p style="margin:16px">Sin casos abiertos.</p>'}
load();setInterval(load,3000)
</script></html>"""
