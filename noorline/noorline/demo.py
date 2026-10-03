"""Demo end-to-end sin red ni hardware: casos A (rutina), B (urgencia), C (duda), D (sin red + store-and-forward)."""
import os, tempfile, warnings
warnings.filterwarnings("ignore")
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from .node import Node
from .server import create_app


def main():
    os.environ.setdefault("NOORLINE_KEY", Fernet.generate_key().decode())
    os.environ.pop("NOORLINE_API_KEY", None)
    tmp = tempfile.mkdtemp(prefix="noorline_")
    client = TestClient(create_app(os.path.join(tmp, "server.db")))
    online = {"v": True}

    def send(payload):
        if not online["v"]:
            raise ConnectionError("sin red")
        client.post("/events", json=payload).raise_for_status()

    node = Node(os.path.join(tmp, "node.db"), on_alert=lambda ev: print("   >>> ALERTA LOCAL (sin red): " + ev["reason"]))
    phone = "+000000001"
    print("== Consentimiento (IVR DTMF, marque 1) ==", node.consent(phone, "1", lang="es"))

    def say(label, text):
        print(f"\n[{label}] Noor: {text!r}")
        r = node.handle_message(phone, text)
        print(f"   nivel={r['nivel'].upper()} razon={r['reason']}\n   -> respuesta (lista cerrada): {r['reply']}")

    say("A rutina", "quiero cita para mi hijo la proxima semana")
    say("B urgencia", "mi esposa no puede respirar bien")
    say("C duda", "me duele y no se que es")
    print("\n== D: SIN RED ==")
    online["v"] = False
    say("D1 rutina sin red", "a que hora abre la clinica")
    say("D2 urgencia sin red", "mi hijo tuvo convulsiones")
    print("   sync intento:", node.sync(send), "(los eventos esperan en el nodo)")
    online["v"] = True
    print("== Vuelve la red ==", node.sync(send))
    print("   reintento (idempotente):", node.sync(send))
    print("\n== Bandeja del servidor (urgencias primero) ==")
    for c in client.get("/cases").json():
        print(f"   {c['level'].upper():5} {c['reason']:28} {(c['text'] or '')[:45]}")
    first = client.get("/cases").json()[0]["event_id"]
    print("\n== Humano confirma la primera urgencia ==", client.post(f"/cases/{first}/action", json={"action": "confirmar_urgencia", "actor": "dra_demo"}).json())
    print("== Escalamiento por timeout (Medio sin atender, +30 min) ==", client.post("/admin/escalate?minutes_ahead=30").json())
    print("== Auditoria (hash encadenado) ==", client.get("/audit/verify").json())


if __name__ == "__main__":
    main()
