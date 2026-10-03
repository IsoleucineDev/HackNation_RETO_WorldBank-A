"""Genera docs/arquitectura.svg y docs/arquitectura.png (necesita cairosvg solo para el PNG)."""
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
W, H = 1700, 1180
F = "DejaVu Sans, Arial, sans-serif"
o = []


def t(x, y, s, size=15, w="normal", fill="#10202b", anchor="start"):
    o.append(f'<text x="{x}" y="{y}" font-family="{F}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{escape(s)}</text>')


def lines(x, y, arr, size=14, gap=21, fill="#10202b", w="normal"):
    for i, s in enumerate(arr):
        n = len(s) - len(s.lstrip(" "))
        t(x, y + i * gap, "\u00a0" * n + s.lstrip(" "), size, w, fill)


def box(x, y, w, h, fill, stroke, r=12, sw=2, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')


def arrow(pts, color, label=None, lx=0, ly=0, dash=None, both=False, size=14):
    d = " ".join(("M" if i == 0 else "L") + f"{x},{y}" for i, (x, y) in enumerate(pts))
    da = f' stroke-dasharray="{dash}"' if dash else ""
    ms = f' marker-start="url(#a{color[1:]})"' if both else ""
    o.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="3"{da} marker-end="url(#a{color[1:]})"{ms}/>')


def vtext(x, y, s, size=13, w="bold", fill="#10202b"):
    o.append(f'<text transform="translate({x},{y}) rotate(-90)" font-family="{F}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="middle">{escape(s)}</text>')


def badge(x, y, n, color):
    o.append(f'<circle cx="{x}" cy="{y}" r="15" fill="{color}"/>')
    t(x, y + 5, str(n), 15, "bold", "#fff", "middle")


COL = {"edge": "#2a9d4a", "rail": "#7b3fe4", "vercel": "#10202b", "human": "#d62828", "net": "#0b6fa4"}
o.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
o.append("<defs>" + "".join(f'<marker id="a{c[1:]}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>' for c in COL.values()) + "</defs>")
o.append(f'<rect width="{W}" height="{H}" fill="#f6f7f9"/>')
o.append(f'<rect width="{W}" height="86" fill="#0b3a53"/>')
t(36, 40, "NoorLine · Arquitectura de despliegue", 30, "bold", "#fff")
t(36, 68, "Small AI offline-first para atención primaria · Backend en Railway · Frontend en Vercel · Planes gratuitos", 16, "normal", "#bfe3f5")

# ---------- zona comunidad
box(24, 110, 520, 700, "#eef8f0", COL["edge"], 16, 2, "8 6")
t(44, 140, "COMUNIDAD · sin internet confiable", 17, "bold", COL["edge"])
box(64, 165, 440, 100, "#fff", COL["edge"])
t(84, 195, "Teléfono básico de Noor", 17, "bold")
lines(84, 220, ["Llamada de voz (IVR por teclas) o SMS", "No instala nada: usa el celular que ya tiene"])
box(64, 330, 440, 450, "#fff", COL["edge"], 12, 3)
t(84, 360, "NODO COMUNITARIO (celular reciclado)", 16, "bold", COL["edge"])
lines(84, 392, [
    "• Pasarela SMS / IVR simulado por DTMF",
    "• Consentimiento auditable: 1 acepto · 9 revoca",
    "• Small AI en el borde (< 1 MB):",
    "    reglas de alerta  >  clasificador TF-IDF",
    "• Decide SIN red: Alto / Medio / Bajo",
    "• Respuestas solo de LISTA CERRADA",
    "• SQLite con cifrado de campo (Fernet)",
    "• Cola store-and-forward con event_id",
    "• ALERTA LOCAL al personal si es urgencia",
], 14, 24)
badge(45, 200, 1, COL["net"])
arrow([(284, 265), (284, 330)], COL["net"], both=True)
t(296, 303, "SMS / voz (red GSM)", 13, "normal", COL["net"])

# ---------- Railway
box(590, 110, 500, 700, "#f3edff", COL["rail"], 16, 2)
t(610, 140, "RAILWAY · Backend (Docker + FastAPI)", 17, "bold", COL["rail"])
box(615, 165, 450, 270, "#fff", COL["rail"], 12, 3)
t(635, 195, "API del servidor central", 16, "bold", COL["rail"])
lines(635, 225, [
    "POST /events      recibe y deduplica (idempotente)",
    "GET  /cases       bandeja ordenada: alto > medio > bajo",
    "POST /cases/{id}/action   decide una PERSONA",
    "POST /admin/escalate   medio sin atender → alto",
    "GET  /audit/verify  auditoría con hash encadenado",
    "GET  /health     chequeo de Railway",
], 13, 24)
lines(635, 385, ["Exige X-API-Key · arranca solo si NOORLINE_API_KEY existe", "(NOORLINE_ENV=production)"], 13, 21, COL["rail"])
box(615, 460, 450, 110, "#fff", COL["rail"])
t(635, 490, "Volume de Railway montado en /data", 15, "bold", COL["rail"])
lines(635, 516, ["server.db (SQLite): casos + auditoría", "Sin volume los datos se pierden en cada redeploy"], 13, 21)
box(615, 595, 450, 190, "#fff", COL["rail"])
t(635, 625, "Variables de entorno (panel de Railway)", 15, "bold", COL["rail"])
lines(635, 651, ["NOORLINE_API_KEY=<clave larga y secreta>", "NOORLINE_DB=/data/server.db", "NOORLINE_ENV=production", "PORT  (lo inyecta Railway)", "Dominio público: *.up.railway.app"], 13, 22)

# ---------- Vercel
box(1130, 110, 548, 700, "#eceff3", COL["vercel"], 16, 2)
t(1150, 140, "VERCEL · Frontend estático (Hobby)", 17, "bold")
box(1155, 165, 498, 250, "#fff", COL["vercel"], 12, 3)
t(1175, 195, "Panel clínico (index.html, sin build)", 16, "bold")
lines(1175, 225, [
    "• Login con API key (solo en sessionStorage)",
    "• Bandeja HITL ordenada por riesgo",
    "• Botones: Confirmar urgencia · Bajar a rutina",
    "   · Pedir aclaración · Resolver",
    "• Pide el nombre del humano en cada acción",
    "• Sonido + título parpadeante en Alto",
    "• Polling cada 8 s; pausa si la pestaña está oculta",
], 13, 24)
box(1155, 440, 498, 190, "#fff", COL["vercel"])
t(1175, 470, "vercel.json  ·  rewrite hacia Railway", 15, "bold")
lines(1175, 498, [
    '"source":      "/api/:path*"',
    '"destination": "https://<tu-app>.up.railway.app/:path*"',
    "El navegador solo ve /api/... (mismo origen):",
    "sin CORS y sin exponer la URL de Railway.",
    "python scripts/set_backend_url.py <URL>",
], 13, 22)
box(1155, 655, 498, 130, "#fff", COL["vercel"])
t(1175, 683, "Cabeceras de seguridad", 15, "bold")
lines(1175, 708, ["nosniff · X-Frame-Options DENY", "Referrer-Policy no-referrer · Cache-Control no-store"], 13, 22)

# ---------- personal clinico
box(1230, 840, 350, 80, "#fff", COL["human"], 12, 3)
t(1250, 870, "Personal clínico (navegador)", 16, "bold", COL["human"])
lines(1250, 895, ["Una PERSONA toma la decisión final"], 13)

# ---------- flechas
arrow([(504, 620), (567, 620), (567, 300), (615, 300)], COL["rail"])
vtext(538, 470, "HTTPS POST /events + X-API-Key", 13, "bold", COL["rail"])
badge(567, 650, 2, COL["rail"])
arrow([(1155, 520), (1110, 520), (1110, 330), (1065, 330)], COL["vercel"])
badge(1110, 395, 4, COL["vercel"])
vtext(1102, 470, "proxy /api/*", 12, "bold", COL["vercel"])
arrow([(1580, 880), (1666, 880), (1666, 290), (1653, 290)], COL["human"])
badge(1666, 600, 3, COL["human"])
t(1580, 940, "abre la URL de Vercel e inicia sesión con la API key", 13, "bold", COL["human"], "end")
# alerta local
arrow([(284, 780), (284, 880), (1230, 880)], COL["human"], dash="8 6")
badge(330, 862, 5, COL["human"])
t(352, 867, "Alerta LOCAL (SMS/sirena) al personal de guardia: funciona sin Railway ni Vercel", 13, "bold", COL["human"])

# ---------- notas
y0 = 960
box(24, y0, 520, 190, "#fff", COL["edge"])
t(44, y0 + 30, "Sin red: qué pasa", 16, "bold", COL["edge"])
lines(44, y0 + 56, ["1. El nodo atiende y clasifica localmente.", "2. Urgencia → alerta local inmediata.", "3. Todo se encola con event_id único.", "4. Al volver la red: sync, urgencias primero.", "5. Si se reenvía, el servidor no duplica."], 13, 24)
box(570, y0, 520, 190, "#fff", COL["rail"])
t(590, y0 + 30, "Railway · plan gratuito (verificado oct 2026)", 16, "bold", COL["rail"])
lines(590, y0 + 56, ["• Prueba 30 días con $5 de crédito; luego plan Free", "   con $1/mes, 1 vCPU, 0.5 GB RAM, volume 0.5 GB.", "• Fin de semana de hackathon: alcanza de sobra.", "• Después puede no sostener 24/7: usar sleep o Hobby.", "• Un solo servicio, sin Postgres, para gastar poco."], 13, 24)
box(1116, y0, 562, 190, "#fff", COL["vercel"])
t(1136, y0 + 30, "Vercel Hobby · gratis", 16, "bold")
lines(1136, y0 + 56, ["• 100 GB de transferencia y 1 M de edge requests/mes.", "• Solo uso personal/no comercial (válido para hackathon).", "• Sin sobrecargos: al llegar al tope se pausa.", "• Por eso el polling es de 8 s y se pausa oculto.", "• Los rewrites externos no necesitan funciones."], 13, 24)
t(W / 2, H - 10, "Datos de entrenamiento sintéticos · lista de alertas ilustrativa (sin validación clínica) · la IA no diagnostica ni escribe texto libre al paciente", 12, "normal", "#555", "middle")
o.append("</svg>")

svg = ROOT / "docs" / "arquitectura.svg"
svg.write_text("\n".join(o), encoding="utf-8")
try:
    import cairosvg
    cairosvg.svg2png(url=str(svg), write_to=str(ROOT / "docs" / "arquitectura.png"), scale=1.5)
    print("OK svg + png")
except ImportError:
    print("OK svg (instala cairosvg para el PNG)")
