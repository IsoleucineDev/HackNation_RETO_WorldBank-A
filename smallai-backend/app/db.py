import os, sqlite3, threading

_lock = threading.Lock()
_conn = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS consent(
  patient_ref TEXT PRIMARY KEY, status TEXT NOT NULL, ts TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS cases(
  msg_id TEXT PRIMARY KEY, patient_ref TEXT NOT NULL, node_id TEXT, ts TEXT, lang TEXT,
  body TEXT, intent TEXT, confidence REAL, priority TEXT, rule_hits TEXT,
  reply_code TEXT, status TEXT DEFAULT 'OPEN', reviewer TEXT, note TEXT,
  received_at TEXT DEFAULT (datetime('now')));
CREATE INDEX IF NOT EXISTS idx_cases_patient ON cases(patient_ref);
"""

def get():
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(os.getenv("DB_PATH", "server.db"), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.executescript(SCHEMA)
    return _conn

def reset():
    global _conn
    if _conn: _conn.close()
    _conn = None

def run(sql, args=()):
    with _lock:
        cur = get().execute(sql, args); get().commit(); return cur

def rows(sql, args=()):
    with _lock:
        return [dict(r) for r in get().execute(sql, args).fetchall()]
