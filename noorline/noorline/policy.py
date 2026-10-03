import os
from pathlib import Path
import yaml
from .common import ROOT

LEVELS_AUTONOMY = {"A0", "A1", "A2"}


def validate(pol: dict) -> dict:
    if pol.get("autonomy_level") not in LEVELS_AUTONOMY:
        raise ValueError("autonomy_level debe ser A0, A1 o A2")
    th = pol.get("thresholds", {})
    for k in ("alto_urgencia", "medio_urgencia", "confianza_minima"):
        if not 0 <= float(th.get(k, -1)) <= 1:
            raise ValueError(f"threshold {k} debe estar en [0,1]")
    if th["medio_urgencia"] >= th["alto_urgencia"]:
        raise ValueError("medio_urgencia debe ser < alto_urgencia")
    if not pol.get("red_flags"):
        raise ValueError("red_flags no puede estar vacio (lista validada por personal clinico)")
    return pol


def load_policy(path=None) -> dict:
    p = Path(path or os.getenv("NOORLINE_POLICY") or ROOT / "policies" / "clinica_ondera_01.yaml")
    return validate(yaml.safe_load(p.read_text(encoding="utf-8")))
