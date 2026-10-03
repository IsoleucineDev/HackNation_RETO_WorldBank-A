"""Apunta el rewrite de Vercel al dominio publico de Railway.
Uso: python scripts/set_backend_url.py https://tu-servicio.up.railway.app"""
import json, re, sys
from pathlib import Path

if len(sys.argv) != 2 or not re.fullmatch(r"https://[\w.-]+(:\d+)?", sys.argv[1].rstrip("/")):
    sys.exit("Uso: python scripts/set_backend_url.py https://tu-servicio.up.railway.app")
url = sys.argv[1].rstrip("/")
p = Path(__file__).resolve().parent.parent / "frontend" / "vercel.json"
cfg = json.loads(p.read_text())
cfg["rewrites"][0]["destination"] = f"{url}/:path*"
p.write_text(json.dumps(cfg, indent=2) + "\n")
print(f"OK: /api/* -> {url}/*  ({p})")
