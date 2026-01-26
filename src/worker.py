import sys
import json
import time

def send(obj: dict):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()

send({"type": "started", "ok": True})

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue

    try:
        msg = json.loads(line)
    except json.JSONDecodeError:
        send({"type": "result", "id": None, "ok": False, "error": "bad_json"})
        continue

    msg_id = msg.get("id")
    op = msg.get("op")

    if op == "ext":
        send({"type": "result", "id": msg_id, "ok": True, "payload": {"bye": True}})
        raise SystemExit(0)

    # имитация обработки 1 сек
    time.sleep(1)
    send({"type": "result", "id": msg_id, "ok": True, "payload": {"echo": msg.get("payload")}})
