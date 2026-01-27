import subprocess
import sys
import json
import shutil
from pathlib import Path


IMG_EXTS = {".jpg", ".jpeg", ".png"}

IGNORE_ERRORS_DELETE_DIR = False


def send(proc: subprocess.Popen, obj: dict):
    proc.stdin.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")
    proc.stdin.flush()


def read_event(proc: subprocess.Popen):
    while True:
        line = proc.stdout.readline()
        if line == "":
            raise RuntimeError("worker stdout closed")
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            print("[bad json]", line)


def init_worker(worker_script):
    proc = subprocess.Popen(
        [sys.executable, worker_script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    evt = read_event(proc)
    print("EVENT:", evt)
    if not (evt.get("type") == "started" and evt.get("ok") is True):
        raise RuntimeError(f"worker didn't start properly: {evt}")

    return proc


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


def list_cache_dirs(cache_root):
    dirs = [p for p in cache_root.iterdir() if p.is_dir()]
    return dirs


def handle_error_for_image(img_path, img_cache_dir):
    if IGNORE_ERRORS_DELETE_DIR:
        try:
            shutil.rmtree(img_cache_dir)
        except Exception as e:
            print(f"[warn] failed to delete cache dir {img_cache_dir}: {e}")
    else:
        dst = img_cache_dir / f"FAILED_{img_path.name}"
        try:
            shutil.copy2(img_path, dst)
        except Exception as e:
            print(f"[warn] failed to save failed input {img_path} -> {dst}: {e}")



def main():
    id = 1
    proc = init_worker("whiteboard_worker.py")

    cache_root = cache_make_root_dir('cache')
    input_dir = 'test'

    queue = list_images(input_dir)
    for img_path in queue:
        cache_img_dir = cache_make_image_dir(cache_root, img_path.stem)
        out_img = cache_img_dir / f'whiteboard_{img_path.name}'
        payload = {
            "image_path": img_path,
            "out_path": out_img,
            "target_class": 0,
        }
        send(proc, {"id": id, "op": "do", "payload": payload})

        while True:
            evt = read_event(proc)
            print("EVENT:", evt)

            if evt.get("type") != "result":
                continue
            if evt.get("id") != id:
                continue

            if evt.get("ok") is True:
                break

            handle_error_for_image(img_path, cache_img_dir)
            break

        id += 1

    send(proc, {"id": id, "op": "ext"})
    evt = read_event(proc)
    print("EVENT:", evt)

    rc = proc.wait(timeout=10)
    print("worker exit code:", rc)


    # Второй воркер
    cache_dirs_queue = list_cache_dirs(cache_root)

    print("\nCACHE DIRS QUEUE:")
    for cache_dir in cache_dirs_queue:
        img_path = list_images(cache_dir)[0]
        print(" -", img_path)


if __name__ == "__main__":
    main()
