"""CONTRATO DE API: Nodo local <-> Servidor <-> Panel clínico."""
from typing import Literal, Optional
from pydantic import BaseModel, Field

Intent = Literal["SYMPTOM_REPORT", "APPOINTMENT_REQUEST", "MEDICATION_REFILL",
                 "RESULT_QUERY", "CONSENT_YES", "CONSENT_NO", "DELETE_DATA", "UNKNOWN"]
EdgePriority = Literal["GREEN", "YELLOW", "RED"]          # lo asigna el motor de reglas (Kiara)
Priority = Literal["GREEN", "YELLOW", "RED", "REVIEW"]    # REVIEW lo fuerza el servidor (fail-safe)


class SmsEnvelope(BaseModel):
    """Un SMS ya procesado por el nodo edge. El servidor NO clasifica."""
    msg_id: str = Field(min_length=8, max_length=64)       # UUID; idempotencia
    node_id: str = Field(max_length=32)
    patient_ref: str = Field(min_length=8, max_length=64)  # hash(teléfono+salt); nunca el número
    ts: str                                                # ISO-8601 UTC, hora del nodo
    lang: str = "sw"
    body: str = Field(max_length=480)                      # texto crudo del SMS
    intent: Intent = "UNKNOWN"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    priority: EdgePriority = "GREEN"                       # de reglas, no de IA libre
    rule_hits: list[str] = []                              # ids de reglas que dispararon (auditable)


class Ack(BaseModel):
    msg_id: str
    reply_code: str                                        # clave del catálogo cerrado
    reply_text: str
    priority: Optional[Priority] = None
    stored: bool                                           # False => nada guardado (sin consentimiento)


class SyncRequest(BaseModel):
    messages: list[SmsEnvelope] = Field(max_length=200)


class SyncResponse(BaseModel):
    acks: list[Ack]


class CaseAction(BaseModel):
    action: Literal["CALLED", "REFERRED", "CLOSED"]        # decide una persona
    note: str = Field(default="", max_length=500)
    reviewer: str = Field(max_length=64)
