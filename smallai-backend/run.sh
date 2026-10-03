#!/usr/bin/env bash
cd "$(dirname "$0")"
source .venv/bin/activate
export API_KEY="${API_KEY:-dev-key}"
export DB_PATH="${DB_PATH:-server.db}"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
