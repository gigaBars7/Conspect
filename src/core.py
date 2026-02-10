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


class ResultWriter:
    def __init__(self, result_dir="", filename="result.txt", mode=2):
        self.mode = mode
        self.result_dir = Path(result_dir) if result_dir else Path(".")
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.result_dir / filename
        self.f = None
        self._t_buf = []
        self._e_buf = []

    def open(self):
        self.f = self.path.open("w", encoding="utf-8")
        return self.path

    def close(self):
        if self.f:
            self.f.flush()
            self.f.close()
            self.f = None

    def start_image_block(self, title):
        self._t_buf.clear()
        self._e_buf.clear()

        self.f.write("=" * 100 + "\n")
        self.f.write(str(title) + "\n\n")

    def add(self, t_text=None, e_text=None):
        if t_text:
            self._t_buf.append(t_text)
        if e_text:
            self._e_buf.append(e_text)

    def flush_image_block(self):
        if self.mode == 2:
            self.f.write("{{tesseract}}\n\n")
            self.f.write("\n\n".join(self._t_buf).strip() + "\n\n")

            self.f.write("-" * 100 + "\n\n")

            self.f.write("{{easyocr}}\n\n")
            self.f.write("\n\n".join(self._e_buf).strip() + "\n\n")

        elif self.mode == 0:
            self.f.write("\n\n".join(self._t_buf).strip() + "\n\n")

        elif self.mode == 1:
            self.f.write("\n\n".join(self._e_buf).strip() + "\n\n")

        self.f.flush()

    def end(self):
        self.f.write("=" * 100 + "\n")
        self.f.flush()


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


def handle_error_classcutter(prev_stage_img_path, class_cutter_dir):
    if WHEN_ERRORS_IN_CLASSCUTTER_IGNORE_DIR:
        return
    else:
        dst = class_cutter_dir / f"FAILED_{Path(prev_stage_img_path).name}"
        try:
            shutil.copy2(prev_stage_img_path, dst)
        except Exception as e:
            print(f"[warn] failed to save failed input {prev_stage_img_path} -> {dst}: {e}")


class Stage:
    """
    Шаблон стадии:
      init -> старт воркера -> start_hook()
      iter_one(items):
          - на каждый item создаём директорию в кэше
          - получаем список изображений (hook get_images_list)
          - для каждого изображения собираем payload (hook make_payload)
          - отправляем воркеру, ждём result
          - решаем ok/не ok (hook is_worker_ok)
          - on_success / on_error
      end():
          - save_result() (hook)
          - отправляем ext воркеру и ждём bye
    """

    def __init__(self, name, worker_script, cache):
        self.name = name
        self.worker_script = worker_script
        self.cache = cache

        self.worker = WorkerProcess(worker_script)
        self.req_id = 1  # счётчик сообщений воркеру

    def run(self, items):
        print(f"\n--- STAGE: {self.name} ---")
        self.init()
        self.iter_one(items)
        self.end()
        print(f"--- STAGE DONE: {self.name} ---\n")

    def init(self):
        self.worker.start()
        self.start_hook()

    def iter_one(self, items):
        for item in items:
            item_dir = self.make_item_dir(item)

            images = self.get_images_list(item, item_dir)

            for img_path in images:
                payload = self.make_payload(item, item_dir, img_path)

                evt = self.worker.request(self.req_id, "do", payload)

                self.print_event(evt)

                if evt.get("ok"):
                    self.on_success(item, item_dir, img_path, evt)
                else:
                    self.on_error(item, item_dir, img_path, evt)

                self.req_id += 1

    def end(self):
        self.save_result()

        self.worker.stop(self.req_id)
        self.req_id += 1

    # -------------------------
    # Переопределяются в конкретной стадии
    # -------------------------

    def start_hook(self):
        pass

    def make_item_dir(self, item):
        stem = Path(item).stem
        return self.cache.make_dir(None, stem)

    def get_images_list(self, item, item_dir):
        return self.cache.list_images(item_dir)

    def make_payload(self, item, item_dir, img_path):
        return None

    def on_success(self, item, item_dir, img_path, evt):
        pass

    def on_error(self, item, item_dir, img_path, evt):
        pass

    def save_result(self):
        pass

    def print_event(self, evt):
        print("EVENT:", evt)


class WhiteboardStage(Stage):
    def __init__(self, cache):
        super().__init__(name="whiteboard", worker_script="whiteboard_worker.py", cache=cache)

    def get_images_list(self, item, item_dir):
        return [Path(item)]

    def make_payload(self, item, item_dir, img_path):
        out_img = item_dir / f"whiteboard_{img_path.name}"
        return {
            "image_path": str(img_path),
            "out_path": str(out_img),
            "target_class": TARGET_CLASS,
            "target_strategy": TARGET_STRATEGY,
        }

    def on_error(self, item, item_dir, img_path, evt):
        handle_error_whiteboard(img_path, item_dir)


class ClassCutterStage(Stage):
    def __init__(self, cache):
        super().__init__(name="class_cutter", worker_script="class_cutter_worker.py", cache=cache)

    def make_item_dir(self, item):
        return Path(item)

    def get_images_list(self, item, item_dir):
        imgs = self.cache.list_images(item_dir)
        if not imgs:
            return []
        return [imgs[0]]

    def make_payload(self, item, item_dir, img_path):
        out_dir = self.cache.make_dir(item_dir, "class_cutter")
        return {
            "image_path": str(img_path),
            "out_dir": str(out_dir),
        }

    def on_error(self, item, item_dir, img_path, evt):
        out_dir = self.cache.make_dir(item_dir, "class_cutter")
        handle_error_classcutter(img_path, out_dir)


class OCRStage(Stage):
    def __init__(self, cache, writer):
        super().__init__(name="ocr", worker_script="baseOCR2_worker.py", cache=cache)
        self.writer = writer

    def start_hook(self):
        p = self.writer.open()
        print(f"[ok] result file: {p}")

    def make_item_dir(self, item):
        return Path(item)

    def get_images_list(self, item, item_dir):
        class_cutter_dir = item_dir / "class_cutter"
        if not class_cutter_dir.is_dir():
            return []

        imgs = self.cache.list_images(class_cutter_dir)

        def _key(p: Path):
            stem = p.stem
            if "FAILED" in stem:
                return (10**9, stem)
            try:
                n = int(stem.split("_")[0])
            except Exception:
                n = 10**9
            return (n, stem)

        imgs = sorted(imgs, key=_key)

        out = []
        for p in imgs:
            parts = p.stem.split("_")
            if len(parts) >= 2 and parts[1] in ("0", "1", "FAILED"):
                out.append(p)
        return out

    def make_payload(self, item, item_dir, img_path):
        return {
            "image_path": str(img_path),
            "mode": MODE,
        }

    def iter_one(self, items):
        for item in items:
            item_dir = self.make_item_dir(item)
            images = self.get_images_list(item, item_dir)

            self.writer.start_image_block(item_dir.name)

            for img_path in images:
                payload = self.make_payload(item, item_dir, img_path)
                evt = self.worker.request(self.req_id, "do", payload)

                self.worker.print_event(
                    evt,
                    truncate_payload_keys=("tesseract_text", "easyocr_text"),
                    max_len=30,
                )

                if evt.get("ok"):
                    self.on_success(item, item_dir, img_path, evt)
                else:
                    self.on_error(item, item_dir, img_path, evt)

                self.req_id += 1

            self.writer.flush_image_block()

        self.writer.end()

    def on_success(self, item, item_dir, img_path, evt):
        payload = evt.get("payload") or {}
        self.writer.add(
            t_text=payload.get("tesseract_text"),
            e_text=payload.get("easyocr_text"),
        )

    def save_result(self):
        self.writer.close()



def main():
    cache = Cache("cache", IMG_EXTS)
    cache.clear_root()

    dir_with_images = Path(DIR_WITH_IMAGES_FOR_ANALYZE)
    items_for_stage1 = cache.list_images(dir_with_images)
    stage1 = WhiteboardStage(cache)
    stage1.run(items_for_stage1)

    items_for_stage2 = cache.list_dirs()
    stage2 = ClassCutterStage(cache)
    stage2.run(items_for_stage2)

    writer = ResultWriter(result_dir=RESULT_SAVE_DIR, filename="result.txt", mode=MODE)
    items_for_stage3 = cache.list_dirs()
    stage3 = OCRStage(cache, writer)
    stage3.run(items_for_stage3)

    if DELETE_CACHE_AFTER_COMPLETION:
        cache.clear_root()
        print(f"Deleted cache at: {cache.root}")



if __name__ == "__main__":
    print('\nCONSPECT\n\n')
    configure()
    main()
