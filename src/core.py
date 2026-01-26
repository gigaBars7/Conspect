import subprocess
import sys
import json
import threading
import time

def send(proc: subprocess.Popen, obj: dict):
    proc.stdin.write(json.dumps(obj, ensure_ascii=False) + "\n")
    proc.stdin.flush()

def reader(proc: subprocess.Popen):
    for line in iter(proc.stdout.readline, ""):
        line = line.strip()
        if not line:
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            print("[bad json]", line)
            continue
        print("EVENT:", evt)

def main():
    proc = subprocess.Popen(
        [sys.executable, "worker_echo.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    t = threading.Thread(target=reader, args=(proc,), daemon=True)
    t.start()

    time.sleep(0.2)  # дать воркеру успеть написать started

    send(proc, {"id": "1", "op": "do", "payload": {"x": 1}})
    time.sleep(0.5)
    send(proc, {"id": "2", "op": "do", "payload": {"x": 2}})
    time.sleep(5.0)

    send(proc, {"id": "3", "op": "ext"})
    rc = proc.wait(timeout=5)
    print("worker exit code:", rc)

if __name__ == "__main__":
    main()
