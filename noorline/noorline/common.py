import hashlib, os, re, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def norm(text: str) -> str:
    """Minusculas, sin acentos, espacios normalizados (para reglas y modelo)."""
    t = unicodedata.normalize("NFKD", text.lower().replace("\u2019", "'"))
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip()


def pseudo_id(phone: str) -> str:
    """Identificador pseudonimo: nunca se guarda el numero en claro."""
    salt = os.getenv("NOORLINE_SALT", "demo-salt-change-me")
    return hashlib.sha256((salt + phone).encode()).hexdigest()[:16]
