"""Catálogo CERRADO de respuestas. El sistema NUNCA genera texto libre.
Textos en swahili: revisar con hablante nativa antes del video."""

REPLIES = {
    "R_CONSENT_ASK":    {"sw": "Tafadhali jibu NDIO kukubali kuhifadhi data yako, au HAPANA kukataa.",
                         "en": "Reply NDIO to consent to storing your data, or HAPANA to decline."},
    "R_CONSENT_OK":     {"sw": "Asante. Ruhusa imehifadhiwa. Tuma BORRAR wakati wowote kufuta data yako.",
                         "en": "Thanks. Consent saved. Send BORRAR any time to delete your data."},
    "R_CONSENT_NO":     {"sw": "Sawa. Hatutahifadhi data yako.",
                         "en": "OK. We will not store your data."},
    "R_RECEIVED":       {"sw": "Ujumbe wako umepokelewa. Mhudumu wa afya ataupitia.",
                         "en": "Message received. A health worker will review it."},
    "R_RECEIVED_URGENT":{"sw": "Ujumbe wako umewekwa kama wa haraka. Mhudumu wa afya ataupitia mara moja.",
                         "en": "Your message was flagged urgent. A health worker will review it right away."},
    "R_NOT_SURE":       {"sw": "Sina uhakika. Mtu atakusaidia.",
                         "en": "I'm not sure. A person will look at this."},
    "R_DELETED":        {"sw": "Data yako imefutwa.",
                         "en": "Your data has been deleted."},
}

INTENTS = {
    "SYMPTOM_REPORT", "APPOINTMENT_REQUEST", "MEDICATION_REFILL",
    "RESULT_QUERY", "CONSENT_YES", "CONSENT_NO", "DELETE_DATA", "UNKNOWN",
}

CONFIDENCE_THRESHOLD = 0.60   # por debajo => R_NOT_SURE + prioridad REVIEW
PRIORITY_ORDER = {"RED": 0, "REVIEW": 1, "YELLOW": 2, "GREEN": 3}
