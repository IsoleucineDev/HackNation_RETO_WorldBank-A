from .common import norm


def match(text: str, flags: list) -> list:
    """Reglas deterministas: devuelve ids de senales de alerta. Ganan siempre al modelo."""
    t = norm(text)
    return [f["id"] for f in flags if any(norm(str(k)) in t for k in f["keywords"])]
