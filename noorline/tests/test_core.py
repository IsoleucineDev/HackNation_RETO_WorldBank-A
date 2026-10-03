import pytest
from noorline import redflags
from noorline.decision import decidir
from noorline.intent import IntentClassifier, cross_val
from noorline.policy import load_policy, validate

POL = load_policy()
CLF = IntentClassifier.load()

# Lista ILUSTRATIVA (no validada clinicamente). Meta del hackathon: recall 100% en este set.
ALERT_SET = ["mi esposa no puede respirar bien", "no puedo respirar", "tiene falta de aire", "he can't breathe", "she cannot breathe",
             "siwezi kupumua", "mtoto hawezi kupumua", "mucha sangre", "heavy bleeding", "damu nyingi", "se desmayo", "he is unconscious",
             "amezimia", "tuvo convulsiones", "kifafa", "my son had a seizure", "NO PUEDO RESPIRAR!!", "Cant   breathe"]


def test_redflag_recall_is_100pct():
    missed = [t for t in ALERT_SET if not redflags.match(t, POL["red_flags"])]
    assert not missed, missed


@pytest.mark.parametrize("t", ALERT_SET)
def test_redflag_always_alto_and_fixed_reply(t):
    d = decidir(t, POL, CLF)
    assert d.nivel == "alto" and d.reply_key == "mensaje_urgencia_fijo"


def test_no_consent_no_automation():
    d = decidir("quiero cita", POL, CLF, consent=False)
    assert d.nivel == "medio" and d.reason == "sin_consentimiento" and d.reply_key == "derivar_persona"


def test_routine_is_bajo_and_ambiguous_is_not():
    assert decidir("quiero cita para manana", POL, CLF).nivel == "bajo"
    assert decidir("nataka miadi kesho", POL, CLF).nivel == "bajo"
    assert decidir("hola", POL, CLF).nivel == "medio"  # baja confianza -> humano


def test_malestar_never_automated():
    assert decidir("me duele mucho la cabeza y tengo fiebre", POL, CLF).nivel in ("medio", "alto")


def test_a0_only_routes():
    p = dict(POL, autonomy_level="A0")
    assert decidir("quiero cita para manana", p, CLF).reply_key == "acuse"


def test_reply_outside_allowed_list_is_blocked():
    p = dict(POL, allowed_patient_replies=["derivar_persona"])
    assert decidir("quiero cita para manana", p, CLF).reply_key == "derivar_persona"


def test_intent_cv_accuracy_honest_floor():
    assert cross_val() >= 0.65  # set sintetico pequeno; ver docs/DATA_CARD.md


def test_policy_validation():
    with pytest.raises(ValueError):
        validate(dict(POL, autonomy_level="A9"))
    with pytest.raises(ValueError):
        validate(dict(POL, thresholds=dict(POL["thresholds"], medio_urgencia=0.9)))
