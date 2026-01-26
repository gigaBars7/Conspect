import subprocess
import sys
import json
import threading
import time
from pathlib import Path


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


def init_worker(worker_script):
    proc = subprocess.Popen(
        [sys.executable, worker_script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    t = threading.Thread(target=reader, args=(proc,), daemon=True)
    t.start()

    time.sleep(0.2)

    return proc, t


def main():
    proc, _t = init_worker("worker_crop.py")

    in_img = r"test/photo_2025-10-27_12-58-17.jpg"
    out_dir = Path("test/crop")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_img = str(out_dir / "crop.jpg")

    send(proc, {"id": "1", "op": "do", "payload": {"image_path": in_img, "out_path": out_img}})

    time.sleep(5.0)

    send(proc, {"id": "3", "op": "ext"})
    rc = proc.wait(timeout=5)
    print("worker exit code:", rc)


if __name__ == "__main__":
    main()
