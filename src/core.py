import subprocess
import sys
import json
import threading
import time
from pathlib import Path


IMG_EXTS = {".jpg", ".jpeg", ".png"}


def send(proc: subprocess.Popen, obj: dict):
    proc.stdin.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")
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
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    first_line = proc.stdout.readline().strip()
    first_evt = json.loads(first_line)
    print("EVENT:", first_evt)

    if not (first_evt.get("type") == "started" and first_evt.get("ok") is True):
        raise RuntimeError(f"worker didn't start properly: {first_evt}")

    t = threading.Thread(target=reader, args=(proc,), daemon=True)
    t.start()

    return proc, t


def cache_make_root_dir(cache_dir):
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir

def cache_make_image_dir(cache_dir, img_name):
    cache_img_dir = cache_dir / img_name
    cache_img_dir.mkdir(parents=True, exist_ok=True)
    return cache_img_dir


def list_images(input_dir):
    p = Path(input_dir)
    if not p.is_dir():
        raise FileNotFoundError(f"input_dir not found or not a directory: {input_dir}")

    files = [f for f in p.iterdir() if f.is_file() and f.suffix.lower() in IMG_EXTS]
    return files


def main():
    id = 1
    proc, _t = init_worker("worker_crop.py")

    cache_root = cache_make_root_dir('cache')
    input_dir = 'test'

    queue = list_images(input_dir)
    for img_path in queue:
        cache_img_dir = cache_make_image_dir(cache_root, img_path.stem)
        out_img = cache_img_dir / f'crop_{img_path.name}'
        send(proc, {"id": id, "op": "do", "payload": {"image_path": img_path, "out_path": out_img}})
        id += 1

        time.sleep(0.05)

    send(proc, {"id": id, "op": "ext"})
    rc = proc.wait(timeout=5)
    print("worker exit code:", rc)


if __name__ == "__main__":
    main()
