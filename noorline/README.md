# NoorLine

Small AI offline-first para atencion primaria rural (voz/SMS). La IA prioriza y pregunta; **una persona decide**.

## Instalar (1 comando)
```bash
./install.sh        # venv + deps + datos + modelo + 34 tests + demo
```
Requiere Python >= 3.10 y acceso a PyPI la primera vez. Despues: `make serve` y abre http://localhost:8000.

## Probar a mano
```bash
make serve          # terminal 1: servidor + panel
make node           # terminal 2: escribe SMS; usa /consent 1 y /sync
```
Prueba: `quiero cita para manana` (bajo), `mi esposa no puede respirar` (alto + alerta local), `hola` (medio, "no estoy seguro: que lo vea una persona").
Seguridad en servidor: `export NOORLINE_API_KEY=algo` antes de `make serve`; panel con `?key=algo`.

## Produccion (Railway + Vercel, planes gratuitos)
![Arquitectura](docs/arquitectura.png)
Guia paso a paso: `docs/DEPLOY.md`.

## Con Claude Code
`cd noorline && claude` -> lee `CLAUDE.md`. Comandos utiles: `/check`, `/add-redflag`.

## Limites honestos
Prototipo de hackathon. Datos de entrenamiento **sinteticos** (144 frases es/en/sw, accuracy en validacion cruzada ~0.7); lista de senales de alerta **ilustrativa, sin validacion clinica**; sin diagnostico; voz real y GSM en roadmap; cifrado de campo (Fernet) sustituye a SQLCipher en la demo.
