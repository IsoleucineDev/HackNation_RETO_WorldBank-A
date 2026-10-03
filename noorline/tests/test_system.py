import json, sqlite3
import pytest
from fastapi.testclient import TestClient
from noorline.node import Node
from noorline.server import create_app


@pytest.fixture
def env(tmp_path):
    client = TestClient(create_app(tmp_path / "s.db"))
    node = Node(tmp_path / "n.db")
    state = {"online": True, "order": []}

    def send(p):
        if not state["online"]:
            raise ConnectionError
        client.post("/events", json=p).raise_for_status()
        state["order"].append(p["nivel"])
    return client, node, send, state, tmp_path


def test_offline_queue_priority_and_idempotent_sync(env):
    client, node, send, state, _ = env
    node.consent("+1", "1")
    state["online"] = False
    node.handle_message("+1", "quiero cita para manana")
    node.handle_message("+1", "mi hijo tuvo convulsiones")
    assert len(node.local_alerts) == 1  # alerta local sin red
    assert node.sync(send)["sent"] == 0 and node.pending() == 2
    state["online"] = True
    assert node.sync(send) == {"sent": 2, "pending": 0}
    assert state["order"] == ["alto", "bajo"]  # urgencias primero
    assert len(client.get("/cases").json()) == 2
    # reenvio manual del mismo evento no duplica
    ev = client.get("/cases").json()[0]
    assert client.post("/events", json=ev | {"nivel": ev["nivel"]}).json()["status"] == "duplicate"


def test_no_consent_stores_no_text(env):
    client, node, send, *_ = env
    node.handle_message("+2", "tengo mucha tos")
    node.sync(send)
    assert client.get("/cases").json()[0]["text"] is None


def test_revoke_scrubs_pending_text(env):
    client, node, send, *_ = env
    node.consent("+3", "1")
    node.handle_message("+3", "quiero cita")
    node.consent("+3", "9")
    node.sync(send)
    assert client.get("/cases").json()[0]["text"] is None


def test_node_db_is_encrypted_at_rest(env):
    _, node, _, _, tmp = env
    node.consent("+4", "1")
    node.handle_message("+4", "texto secreto de prueba")
    raw = sqlite3.connect(tmp / "n.db").execute("SELECT payload FROM outbox").fetchone()[0]
    assert b"texto secreto" not in raw
    assert "+4" not in str(sqlite3.connect(tmp / "n.db").execute("SELECT pid FROM patients").fetchall())


def test_human_required_and_audit_chain(env):
    client, node, send, *_ = env
    node.consent("+5", "1")
    node.handle_message("+5", "me duele y no se que es")
    node.sync(send)
    eid = client.get("/cases").json()[0]["event_id"]
    assert client.post(f"/cases/{eid}/action", json={"action": "bajar_a_rutina", "actor": " "}).status_code == 422
    assert client.post(f"/cases/{eid}/action", json={"action": "bajar_a_rutina", "actor": "dra_x"}).json()["level"] == "bajo"
    assert client.get("/audit/verify").json()["valid"] is True


def test_audit_tamper_detected(env):
    client, node, send, *_ = env
    node.consent("+6", "1")
    node.handle_message("+6", "quiero cita")
    node.sync(send)
    client.app.state.db.execute("UPDATE audit SET detail='manipulado' WHERE id=1")
    assert client.get("/audit/verify").json()["valid"] is False


def test_medio_escalates_to_alto_on_timeout(env):
    client, node, send, *_ = env
    node.consent("+7", "1")
    node.handle_message("+7", "hola")  # baja confianza -> medio
    node.sync(send)
    assert client.post("/admin/escalate").json()["escalated"] == []
    assert len(client.post("/admin/escalate?minutes_ahead=30").json()["escalated"]) == 1
    assert client.get("/cases").json()[0]["level"] == "alto"


def test_api_key_enforced_when_configured(env, monkeypatch):
    client, *_ = env
    monkeypatch.setenv("NOORLINE_API_KEY", "k")
    assert client.get("/cases").status_code == 401
    assert client.get("/cases", headers={"X-API-Key": "k"}).status_code == 200


def test_production_refuses_to_start_without_api_key(tmp_path, monkeypatch):
    monkeypatch.setenv("NOORLINE_ENV", "production")
    monkeypatch.delenv("NOORLINE_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        create_app(tmp_path / "s.db")
    monkeypatch.setenv("NOORLINE_API_KEY", "k")
    assert create_app(tmp_path / "s.db")


def test_db_path_from_env_creates_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("NOORLINE_DB", str(tmp_path / "vol" / "server.db"))
    create_app()
    assert (tmp_path / "vol" / "server.db").exists()


def test_cors_only_when_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("NOORLINE_CORS_ORIGINS", "https://x.vercel.app")
    c = TestClient(create_app(tmp_path / "s.db"))
    r = c.get("/health", headers={"Origin": "https://x.vercel.app"})
    assert r.headers.get("access-control-allow-origin") == "https://x.vercel.app"
    assert c.get("/health", headers={"Origin": "https://evil.com"}).headers.get("access-control-allow-origin") is None
