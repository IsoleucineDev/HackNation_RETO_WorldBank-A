"""REPL de nodo para probar a mano: python -m noorline.cli [--server http://localhost:8000]"""
import argparse, os, tempfile
from .node import Node, http_sender


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default=os.getenv("NOORLINE_SERVER_URL", "http://localhost:8000"))
    ap.add_argument("--db", default=os.path.join(tempfile.gettempdir(), "noorline_node.db"))
    a = ap.parse_args()
    node = Node(a.db, on_alert=lambda ev: print(f"  >>> ALERTA LOCAL: {ev['reason']}"))
    send = http_sender(a.server, os.getenv("NOORLINE_API_KEY"))
    phone = "+000000001"
    print("Comandos: /consent 1|2|9   /sync   /quit   o escribe un SMS.")
    while True:
        try:
            line = input("SMS> ").strip()
        except EOFError:
            break
        if line == "/quit":
            break
        if line.startswith("/consent"):
            print(node.consent(phone, line.split()[-1]))
        elif line == "/sync":
            print(node.sync(send))
        elif line:
            r = node.handle_message(phone, line)
            print(f"  [{r['nivel'].upper()}|{r['reason']}] {r['reply']}")


if __name__ == "__main__":
    main()
