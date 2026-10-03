"""Reglas de decision. Principios: (1) ante la duda subir de nivel, (2) nunca bajar un caso sin humano,
(3) nunca texto libre al paciente (lista cerrada), (4) toda decision lleva su razon."""
from dataclasses import dataclass, field, asdict
from enum import Enum
from . import redflags

ROUTINE = {"agendar_cita", "recordatorio", "seguimiento", "faq_horarios"}
RANK = {"alto": 0, "medio": 1, "bajo": 2}


class Nivel(str, Enum):
    ALTO = "alto"
    MEDIO = "medio"
    BAJO = "bajo"


# Lista cerrada de respuestas al paciente. Editable solo por la clinica.
REPLIES = {
    "mensaje_urgencia_fijo": {
        "es": "Hemos avisado a una persona. Si es grave, vaya ya a la clinica o llame a emergencias.",
        "en": "We have alerted a person. If it is serious, go to the clinic now or call emergency services.",
        "sw": "Tumemjulisha mtu. Ikiwa ni hatari, nenda kliniki sasa au piga simu ya dharura."},
    "cita_propuesta": {
        "es": "Le proponemos cita el martes 10:00. La clinica la confirmara. Responda 1 si le sirve, 2 para otra hora.",
        "en": "We suggest Tuesday 10:00. The clinic will confirm. Reply 1 if it works, 2 for another time.",
        "sw": "Tunapendekeza Jumanne saa 4 asubuhi. Kliniki itathibitisha. Jibu 1 ikikufaa, 2 kwa muda mwingine."},
    "recordatorio": {
        "es": "Le enviaremos un recordatorio por SMS antes de su cita.",
        "en": "We will send you an SMS reminder before your appointment.",
        "sw": "Tutakutumia ukumbusho kwa SMS kabla ya miadi yako."},
    "faq_horarios": {
        "es": "Horario de la clinica: {horario}.",
        "en": "Clinic hours: {horario}.",
        "sw": "Saa za kliniki: {horario}."},
    "pregunta_aclaracion": {
        "es": "Una persona revisara su mensaje. Es un dolor o malestar muy fuerte? Responda 1 = si, 2 = no.",
        "en": "A person will review your message. Is it very severe? Reply 1 = yes, 2 = no.",
        "sw": "Mtu atakagua ujumbe wako. Ni maumivu makali sana? Jibu 1 = ndiyo, 2 = hapana."},
    "derivar_persona": {
        "es": "Una persona de la clinica le contactara pronto.",
        "en": "A person from the clinic will contact you soon.",
        "sw": "Mtu kutoka kliniki atawasiliana nawe hivi karibuni."},
    "acuse": {
        "es": "Recibimos su mensaje.", "en": "We received your message.", "sw": "Tumepokea ujumbe wako."},
}


@dataclass
class Decision:
    nivel: str
    intent: str
    conf: float
    p_urg: float
    flags: list = field(default_factory=list)
    reason: str = ""
    reply_key: str = "derivar_persona"
    auto_confirm: bool = False

    def dict(self):
        return asdict(self)


def reply_text(key: str, lang: str, policy: dict) -> str:
    tpl = REPLIES.get(key, REPLIES["derivar_persona"]).get(lang) or REPLIES[key]["es"]
    return tpl.format(horario=policy.get("faq", {}).get("horario", "-"))


def decidir(text: str, policy: dict, classifier, consent: bool = True) -> Decision:
    th = policy["thresholds"]
    if not consent:
        d = Decision("medio", "desconocido", 0.0, 0.0, [], "sin_consentimiento", "derivar_persona")
    else:
        flags = redflags.match(text, policy["red_flags"])
        intent, conf, p = classifier.predict(text)
        if flags:
            d = Decision("alto", intent, conf, p, flags, "red_flag:" + ",".join(flags), "mensaje_urgencia_fijo")
        elif conf < th["confianza_minima"]:
            d = Decision("medio", intent, conf, p, [], "baja_confianza", "pregunta_aclaracion")
        elif p >= th["alto_urgencia"]:
            d = Decision("alto", intent, conf, p, [], "urgencia_modelo", "mensaje_urgencia_fijo")
        elif p >= th["medio_urgencia"] or intent == "malestar":
            d = Decision("medio", intent, conf, p, [], "posible_malestar", "pregunta_aclaracion")
        elif intent == "hablar_persona":
            d = Decision("medio", intent, conf, p, [], "pidio_persona", "derivar_persona")
        elif intent in ROUTINE:
            key = {"agendar_cita": "cita_propuesta", "recordatorio": "recordatorio",
                   "seguimiento": "recordatorio", "faq_horarios": "faq_horarios"}[intent]
            if policy["autonomy_level"] == "A0":
                key = "acuse"  # A0: solo enrutar
            d = Decision("bajo", intent, conf, p, [], "rutina", key,
                         auto_confirm=policy["autonomy_level"] == "A2")
        else:
            d = Decision("medio", intent, conf, p, [], "no_clasificado", "derivar_persona")
    # Cualquier respuesta fuera de la lista permitida por la clinica -> derivar a persona.
    if d.reply_key not in policy["allowed_patient_replies"]:
        d.reply_key = "derivar_persona"
    return d
