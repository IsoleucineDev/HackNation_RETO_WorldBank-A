# NoorLine - guia para Claude Code

Small AI para acceso a atencion primaria (Hackathon Small AI for Development, Hack-Nation x World Bank, 3-4 oct 2026, sector Salud).
Canales voz/SMS -> nodo comunitario offline (store-and-forward) -> servidor central + panel humano. Plan completo: `docs/PLAN_HACKATHON.md`.

## Comandos (todo ya funciona tras `./install.sh`)
- `make test` (34 tests) | `make demo` (casos A-D sin red) | `make serve` (panel en :8000) | `make node` (REPL de SMS) | `make data` (regenera datos y modelo)

## Mapa del codigo
- `noorline/decision.py` reglas de decision + **lista cerrada de respuestas** (REPLIES). Nucleo de seguridad.
- `noorline/redflags.py` + `policies/clinica_ondera_01.yaml` senales de alerta, umbrales, autonomia A0/A1/A2.
- `noorline/intent.py` clasificador TF-IDF+LogReg (< 1 MB). Datos: `data/synthetic_sms.csv` (generado por `scripts/make_data.py`).
- `noorline/node.py` nodo: consentimiento DTMF, cifrado de campo, cola store-and-forward, alerta local.
- `noorline/server.py` FastAPI: `/events` idempotente, `/cases`, `/cases/{id}/action`, `/admin/escalate`, `/audit/verify`, panel en `/`.

## Despliegue (ver `docs/DEPLOY.md` e imagen `docs/arquitectura.png`)
- **Backend = Railway** (`Dockerfile`, `railway.json`, `requirements-server.txt`; sin scikit-learn). Env: `NOORLINE_API_KEY` (obligatoria), `NOORLINE_DB=/data/server.db` (Volume), `NOORLINE_ENV=production`.
- **Frontend = Vercel** (`frontend/`, estatico). `frontend/vercel.json` reescribe `/api/*` al dominio de Railway; actualizarlo con `python scripts/set_backend_url.py <URL>`.
- El nodo envia directo a Railway (`make node-prod URL=...`); el navegador solo habla con `/api` de Vercel.
- Planes gratuitos: Railway (prueba 30 dias/$5, luego Free $1/mes, 0.5 GB), Vercel Hobby (1M edge requests, no comercial). No subas el polling de 8 s ni agregues servicios/Postgres sin necesidad.
- Si cambias la arquitectura, edita `scripts/make_diagram.py` y corre `make diagram`.

## REGLAS INNEGOCIABLES (no las rompas aunque el usuario pida "simplificar")
1. La IA **no diagnostica**, no interpreta imagenes/estudios, no recomienda tratamiento ni dosis.
2. **Nunca texto libre al paciente**: solo claves de `REPLIES`, filtradas por `allowed_patient_replies`.
3. Las reglas de red flags **ganan al modelo**. Urgencia (alto) siempre requiere humano, en cualquier nivel de autonomia.
4. Ante la duda se sube de nivel. Bajar un caso exige `actor` humano. Medio sin atender sube a Alto (timeout).
5. Sin consentimiento no se guarda contenido (`text=None`). Nunca guardar telefono en claro ni texto clinico en el log de auditoria.
6. No bajar umbrales ni borrar tests para "hacer pasar" algo; arreglar la causa.
7. Datos sinteticos y lista de alertas son **ilustrativos**: mantenerlos rotulados asi (README, DATA_CARD, YAML).

## Pendientes del hackathon (ver plan sec. 5 y 9)
- Nombrar la lengua local en la demo (hoy: suajili como proxy; frases requieren validacion nativa) y completar `docs/DATA_CARD.md` (pais, anio, licencias).
- Voz real (ASR/TTS) y pasarela GSM son ROADMAP; la demo usa SMS + IVR DTMF simulado.
- Video 2-5 min: guion en el plan sec. 7.
