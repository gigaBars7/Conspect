import sys
import json

class BaseWorker:
    """Каркас JSONL-воркера."""

    def send(self, obj: dict) -> None:
        print(json.dumps(obj, ensure_ascii=False), flush=True)

    def on_start(self):
        return {}

    def handle(self, op, payload):
        return {"echo": payload}

    def on_shutdown(self):
        return {}

    def run(self) -> None:
        self.send({"type": "started", "ok": True, "payload": self.on_start()})

        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                self.send({"type": "result", "id": None, "ok": False, "error": "bad_json"})
                continue

            msg_id = msg.get("id")
            op = msg.get("op")
            payload = msg.get("payload")

            if op == "ext":
                self.send({"type": "result", "id": msg_id, "ok": True, "payload": self.on_shutdown()})
                return

            try:
                out = self.handle(op, payload)
                self.send({"type": "result", "id": msg_id, "ok": True, "payload": out})
            except Exception as e:
                self.send({"type": "result", "id": msg_id, "ok": False, "error": str(e)})