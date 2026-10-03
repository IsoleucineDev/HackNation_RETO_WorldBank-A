#!/usr/bin/env bash
set -euo pipefail

echo ">> Buscando server.py..."
SERVER=""
for p in noorline/server.py noorline/serve.py server.py app.py; do
  [[ -f "$p" ]] && SERVER="$p" && break
done
if [[ -z "$SERVER" ]]; then
  echo "ERROR: no encontré server.py. Ajusta la ruta en el script."
  exit 1
fi
echo "   encontrado: $SERVER"

cp "$SERVER" "$SERVER.bak"

echo ">> Mostrando líneas 40-60 (contexto del bug):"
sed -n '40,60p' "$SERVER"
echo "----------------------------------------"

echo ">> Parcheando para crear el directorio de la DB automáticamente..."
python3 - "$SERVER" <<'PYEOF'
import sys, re
p = sys.argv[1]
src = open(p).read()

# Inserta mkdir del directorio padre justo antes de la línea sqlite3.connect(path, ...)
pattern = re.compile(
    r'^(\s*)(db\s*=\s*sqlite3\.connect\(\s*path\b[^\n]*\n)',
    re.MULTILINE,
)

def repl(m):
    indent, line = m.group(1), m.group(2)
    return (
        f'{indent}from pathlib import Path as _Path\n'
        f'{indent}if isinstance(path, str) and path not in (":memory:", ""):\n'
        f'{indent}    _Path(path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)\n'
        f'{indent}{line}'
    )

new, n = pattern.subn(repl, src, count=1)
if n == 0:
    print("   !! No encontré 'db = sqlite3.connect(path, ...)'. Edítalo a mano.")
    print("   Asegúrate de que la línea 50 tenga algo como:")
    print("      Path(path).parent.mkdir(parents=True, exist_ok=True)")
    print("   antes de sqlite3.connect(path, ...)")
else:
    open(p, "w").write(new)
    print(f"   parcheado: {p} ({n} reemplazo)")
PYEOF

echo ""
echo ">> Diff de $SERVER:"
diff -u "$SERVER.bak" "$SERVER" || true

echo ""
echo ">> Verificando Dockerfile..."
if grep -qE '^USER\s+app' Dockerfile 2>/dev/null; then
  echo "   ADVERTENCIA: tu Dockerfile todavía tiene 'USER app'."
  echo "   Cámbialo a root para que el mkdir funcione sobre el volumen."
fi
if ! grep -qE 'mkdir -p /data' Dockerfile 2>/dev/null; then
  echo "   ADVERTENCIA: no hay 'RUN mkdir -p /data' en el Dockerfile."
fi

echo ""
echo "Siguiente paso (manual):"
echo "  git add $SERVER Dockerfile"
echo "  git commit -m 'fix(railway): crear directorio de DB antes de connect'"
echo "  git push"
