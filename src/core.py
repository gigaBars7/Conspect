import shutil
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
import json
import copy


IMG_EXTS = {".jpg", ".jpeg", ".png"}
TARGET_CLASS = 0    # 0 - screen;  1 - whiteboard
TARGET_STRATEGY = 'conf'    # conf или size
WHEN_ERRORS_IN_WHITEBOARD_DELETE_DIR = False
WHEN_ERRORS_IN_CLASSCUTTER_IGNORE_DIR = True
DIR_WITH_IMAGES_FOR_ANALYZE = 'images'
RESULT_SAVE_DIR = ''
MODE = 0    # 0 - tesseract;  1 - easyocr;  2 - tesseract + easyocr
DELETE_CACHE_AFTER_COMPLETION = False


def print_settings(left_part_width=48):
    print('Текущие настройки:')

    print(f'{("1) TARGET_CLASS = " + str(TARGET_CLASS)).ljust(left_part_width)}  '
          f'|  Искать на изображении:')
    print(f'{" " * left_part_width}  |  0 - экран')
    print(f'{"".rjust(left_part_width)}  |  1 - доска')

    print(f'{("2) WHEN_ERRORS_IN_WHITEBOARD_DELETE_DIR = " + str(WHEN_ERRORS_IN_WHITEBOARD_DELETE_DIR)).ljust(left_part_width)}  '
          f'|  При ошибках модели поиска экрана/доски:')
    print(f'{" " * left_part_width}  |  False - как результат взять анализируемое изображение')
    print(f'{" " * left_part_width}  |  True - проигнорировать анализируемое изображение')

    print(f'{("3) WHEN_ERRORS_IN_CLASSCUTTER_IGNORE_DIR = " + str(WHEN_ERRORS_IN_CLASSCUTTER_IGNORE_DIR)).ljust(left_part_width)}  '
          f'|  При ошибках модели классификации:')
    print(f'{" " * left_part_width}  |  False - как результат взять анализируемое изображение')
    print(f'{" " * left_part_width}  |  True - проигнорировать анализируемое изображение')

    dir_with_images = DIR_WITH_IMAGES_FOR_ANALYZE
    if dir_with_images == 'images':
        dir_with_images = 'src/images'
    print(f'{("4) DIR_WITH_IMAGES_FOR_ANALYZE = " + str(dir_with_images)).ljust(left_part_width)}  '
          f'|  Путь директории с изображениями для анализа:')
    print(f'{" " * left_part_width}  |  по умолчанию src/images')

    result_save_dir = RESULT_SAVE_DIR
    if result_save_dir == '':
        result_save_dir = 'src/'
    print(f'{("5) RESULT_SAVE_DIR = " + str(result_save_dir)).ljust(left_part_width)}  '
          f'|  Директория для сохранения текстового файла с результатом:')
    print(f'{" " * left_part_width}  |  по умолчанию src/')

    print(f'{("6) MODE = " + str(MODE)).ljust(left_part_width)}  '
          f'|  Режим работы OCR:')
    print(f'{" " * left_part_width}  |  0 - tesseract')
    print(f'{" " * left_part_width}  |  1 - easyocr')
    print(f'{" " * left_part_width}  |  2 - tesseract + easyocr')

    print()


def agree_with_question(question):
    asn = input(question).strip().lower()
    if asn in ("y", "yes", "1", "true"):
        return True
    else:
        return False


def configure():
    global TARGET_CLASS, WHEN_ERRORS_IN_WHITEBOARD_DELETE_DIR, \
        WHEN_ERRORS_IN_CLASSCUTTER_IGNORE_DIR, DIR_WITH_IMAGES_FOR_ANALYZE, RESULT_SAVE_DIR, MODE

    print_settings()
    use_default = agree_with_question('Использовать настройки по умолчанию (Y, n)? ')
    print()
    if not use_default:
        while True:
            num_prm_to_change = input('Введите номер параметра для изменения: ').strip()
            if num_prm_to_change == '1':
                new_prm = int(input('Введите новое значение (0 или 1): ').strip())
                if new_prm in (0, 1):
                    TARGET_CLASS = new_prm
            elif num_prm_to_change == '2':
                new_prm = input('Введите новое значение (True или False): ').strip().lower()
                if new_prm == 'true':
                    WHEN_ERRORS_IN_WHITEBOARD_DELETE_DIR = True
                elif new_prm == 'false':
                    WHEN_ERRORS_IN_CLASSCUTTER_IGNORE_DIR = False
            elif num_prm_to_change == '3':
                new_prm = input('Введите новое значение (True или False): ').strip().lower()
                if new_prm == 'true':
                    WHEN_ERRORS_IN_CLASSCUTTER_IGNORE_DIR = True
                elif new_prm == 'false':
                    WHEN_ERRORS_IN_CLASSCUTTER_IGNORE_DIR = False
            elif num_prm_to_change == '4':
                new_prm = input('Введите новый путь директории с изображениями для анализа (путь относительно src/ ): ').strip()
                DIR_WITH_IMAGES_FOR_ANALYZE = new_prm
            elif num_prm_to_change == '5':
                new_prm = input('Введите новый путь директории с изображениями для анализа (путь относительно src/ ): ').strip()
                RESULT_SAVE_DIR = new_prm
            elif num_prm_to_change == '6':
                new_prm = int(input('Введите новое значение (0, 1 или 2): ').strip())
                if new_prm in (0, 1, 2):
                    MODE = new_prm

            print()
            print_settings()
            use_current = agree_with_question('Использовать текущие настройки (Y, n)? ')
            print()
            if use_current:
                break


@dataclass
class Cache:
    root: Path
    img_exts: set

    def __init__(self, root="cache", img_exts=None):
        self.root = Path(root)
        self.img_exts = img_exts


    def ensure_root(self):
        self.root.mkdir(parents=True, exist_ok=True)
        return self.root

    def clear_root(self):
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True, exist_ok=True)
        return self.root

    def make_dir(self, parent, name):
        base = self.root if parent is None else Path(parent)
        d = base / name
        d.mkdir(parents=True, exist_ok=True)
        return d

    def list_dirs(self, dir_path=None):
        p = self.root if dir_path is None else Path(dir_path)
        if not p.is_dir():
            raise FileNotFoundError(f"directory not found: {p}")
        return sorted([x for x in p.iterdir() if x.is_dir()])

    def list_images(self, dir_path):
        p = Path(dir_path)
        if not p.is_dir():
            raise FileNotFoundError(f"directory not found: {p}")
        files = [x for x in p.iterdir() if x.is_file() and x.suffix.lower() in self.img_exts]
        return sorted(files)


class WorkerProcess:
    def __init__(self, worker_script):
        self.worker_script = worker_script
        self.proc = None

    def start(self):
        self.proc = subprocess.Popen(
            [sys.executable, self.worker_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        evt = self.read_event()
        print("EVENT:", evt)
        if not (evt.get("type") == "started" and evt.get("ok") is True):
            raise RuntimeError(f"worker didn't start properly: {evt}")
        return evt

    def stop(self, req_id):
        self.send({"id": req_id, "op": "ext"})
        evt = self.read_event()
        print("EVENT:", evt)
        rc = self.proc.wait(timeout=10)
        print(f"worker exit code: {rc}\n")
        self.proc = None
        return evt, rc

    def send(self, obj):
        self.proc.stdin.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")
        self.proc.stdin.flush()

    def read_event(self):
        while True:
            line = self.proc.stdout.readline()
            if line == "":
                raise RuntimeError("worker stdout closed")
            line = line.strip()
            if not line:
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                print("[bad json]", line)

    def wait_result(self, req_id):
        while True:
            evt = self.read_event()
            print("EVENT:", evt)

            if evt.get("type") != "result":
                continue
            if evt.get("id") != req_id:
                continue
            return evt

    def request(self, req_id, op, payload):
        self.send({"id": req_id, "op": op, "payload": payload})
        return self.wait_result(req_id)

    def print_event(self, evt, truncate_payload_keys=None, max_len=30):
        e = copy.deepcopy(evt)
        if truncate_payload_keys and isinstance(e.get("payload"), dict):
            for k in truncate_payload_keys:
                v = e["payload"].get(k)
                if isinstance(v, str) and len(v) > max_len:
                    e["payload"][k] = v.replace("\n", " ")[:max_len] + "…"
        print("EVENT:", e)


def handle_error_whiteboard(img_path, img_cache_dir):
    if WHEN_ERRORS_IN_WHITEBOARD_DELETE_DIR:
        try:
            shutil.rmtree(img_cache_dir)
        except Exception as e:
            print(f"[warn] failed to delete cache dir {img_cache_dir}: {e}")
    else:
        dst = img_cache_dir / f"FAILED_{Path(img_path).name}"
        try:
            shutil.copy2(img_path, dst)
        except Exception as e:
            print(f"[warn] failed to save failed input {img_path} -> {dst}: {e}")




def main():
    cache = Cache("cache", IMG_EXTS)
    cache.clear_root()

    dir_with_images = Path(DIR_WITH_IMAGES_FOR_ANALYZE)

    queue = cache.list_images(dir_with_images)

    worker1 = WorkerProcess('whiteboard_worker.py')
    worker1.start()

    req_id = 1
    for img_path in queue:
        img_dir = cache.make_dir(None, img_path.stem)

        out_img_name = img_dir / f'whiteboard_{img_path.name}'
        payload = {
            'image_path': str(img_path),
            'out_path': str(out_img_name),
            'target_class': TARGET_CLASS,
            'target_strategy': TARGET_STRATEGY,
        }
        evt = worker1.request(req_id, 'do', payload)

        if evt.get("ok"):
            pass
        else:
            handle_error_whiteboard(img_path, img_dir)

        req_id += 1

    worker1.stop(req_id)




if __name__ == "__main__":
    print('\nCONSPECT\n\n')
    configure()
    main()
