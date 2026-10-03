#!/usr/bin/env bash
# Instalacion de un comando: crea venv, instala deps, genera datos sinteticos, entrena el modelo,
# corre los tests y la demo. Si algo falla, se detiene con un mensaje claro.
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' || { echo "ERROR: se requiere Python >= 3.10"; exit 1; }
echo "==> [1/5] Entorno virtual"; [ -d .venv ] || "$PY" -m venv .venv
. .venv/bin/activate
echo "==> [2/5] Dependencias"; pip install -q --upgrade pip && pip install -q -r requirements.txt
echo "==> [3/5] Datos sinteticos + modelo de intencion"; python scripts/make_data.py && python -c "from noorline.intent import IntentClassifier as C; C.train(); print('modelo entrenado')"
echo "==> [4/5] Tests"; python -m pytest -q
echo "==> [5/5] Demo end-to-end"; python -W ignore -m noorline.demo
cat <<'MSG'

LISTO. Siguientes pasos:
  make serve      # servidor + panel en http://localhost:8000
  make node       # nodo interactivo (otra terminal): escribe SMS de prueba
  make demo       # demo sin red ni hardware
  make test       # tests
Para Claude Code: abre esta carpeta y ejecuta `claude`; lee CLAUDE.md automaticamente.
MSG
