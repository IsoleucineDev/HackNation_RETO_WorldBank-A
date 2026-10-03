# Backend + Gateway (Ileana)

## Correr
    python3 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    uvicorn app.main:app --port 8000          # servidor
    python -m pytest -q                        # tests (6)
    python gateway_sim.py send "NDIO" CONSENT_YES 0.99 GREEN
    python gateway_sim.py flush

## Endpoints (header X-API-Key)
| Método | Ruta | Quién | Qué hace |
|---|---|---|---|
| POST | /sms/inbound | nodo | 1 SMS en vivo |
| POST | /sync | nodo | lote del outbox; borra de cola solo lo con ack |
| GET | /cases?status=OPEN | panel (Diana) | casos ordenados RED > REVIEW > YELLOW > GREEN |
| POST | /cases/{msg_id}/action | panel | CALLED / REFERRED / CLOSED (decide una persona) |
| GET | /health | todos | ping |

## Contrato
Ver app/schemas.py (SmsEnvelope, Ack). El servidor NO clasifica: recibe intent + confidence + priority del nodo (Kiara).
Fail-safe: intent UNKNOWN o confidence < 0.60 => prioridad REVIEW + R_NOT_SURE.
Respuestas: solo claves de app/catalog.py (catálogo cerrado). Textos en swahili: validar con hablante nativa.
