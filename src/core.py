import subprocess
import sys
import json
import shutil
from pathlib import Path


IMG_EXTS = {".jpg", ".jpeg", ".png"}
TARGET_CLASS = 0    # 0 - text;  1 - handwritten text
TARGET_STRATEGY = 'conf'    # conf или size
WHEN_ERRORS_IN_WHITEBOARD_DELETE_DIR = False
WHEN_ERRORS_IN_CLASSCUTTER_IGNORE_DIR = True
DIR_WITH_IMAGES_FOR_ANALYZE = 'images'
RESULT_SAVE_DIR = ''
DELETE_CACHE_AFTER_COMPLETION = True


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
    print()


def agree_with_question(question):
    asn = input(question).strip().lower()
    if asn in ("y", "yes", "1", "true"):
        return True
    else:
        return False


def configure():
    global TARGET_CLASS, WHEN_ERRORS_IN_WHITEBOARD_DELETE_DIR, \
        WHEN_ERRORS_IN_CLASSCUTTER_IGNORE_DIR, DIR_WITH_IMAGES_FOR_ANALYZE, RESULT_SAVE_DIR

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

            print()
            print_settings()
            use_current = agree_with_question('Использовать текущие настройки (Y, n)? ')
            print()
            if use_current:
                break


def main():
    dir_with_images = Path(DIR_WITH_IMAGES_FOR_ANALYZE)
    result_save_dir = Path(RESULT_SAVE_DIR)

    id = 1
    proc = init_worker("whiteboard_worker.py")

    cache_root = cache_make_root_dir('cache')

    queue = list_images(dir_with_images)
    for img_path in queue:
        cache_img_dir = cache_make_image_dir(cache_root, img_path.stem)
        out_img = cache_img_dir / f'whiteboard_{img_path.name}'
        payload = {
            "image_path": img_path,
            "out_path": out_img,
            "target_class": TARGET_CLASS,
            "target_strategy": TARGET_STRATEGY
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

            handle_error_whiteboard(img_path, cache_img_dir)
            break

        id += 1

    send(proc, {"id": id, "op": "ext"})
    id += 1
    evt = read_event(proc)
    print("EVENT:", evt)

    rc = proc.wait(timeout=10)
    print(f"worker exit code: {rc}\n")


    # Второй воркер
    proc2 = init_worker("class_cutter_worker.py")

    cache_dirs_queue = list_cache_dirs(cache_root)

    for cache_dir in cache_dirs_queue:
        cache_dir_in_img_dir = cache_make_image_dir(cache_dir, 'class_cutter')
        img_path = list_images(cache_dir)[0]
        payload = {
            "image_path": img_path,
            "out_dir": cache_dir_in_img_dir,
        }
        send(proc2, {"id": id, "op": "do", "payload": payload})

        while True:
            evt = read_event(proc2)
            print("EVENT:", evt)

            if evt.get("type") != "result":
                continue
            if evt.get("id") != id:
                continue

            if evt.get("ok") is True:
                break

            handle_error_classcutter(img_path, cache_dir_in_img_dir)
            break

        id += 1

    send(proc2, {"id": id, "op": "ext"})
    id += 1
    evt = read_event(proc2)
    print("EVENT:", evt)

    rc = proc2.wait(timeout=10)
    print(f"worker exit code: {rc}\n")


    # Третий воркер
    proc3 = init_worker("worker_baseOCR.py")

    result_path = result_save_dir / 'result.txt'
    result_file = result_path.open('w', encoding='utf-8')

    cache_dirs_queue = list_cache_dirs(cache_root)

    for cache_dir in cache_dirs_queue:
        cache_dir_in_img_dir = cache_make_image_dir(cache_dir, 'baseOCR')

        class_cutter_dir = cache_dir / 'class_cutter'
        imgs = sorted(
            list_images(class_cutter_dir),
            key=lambda x: x if 'FAILED' in str(x.stem) else int(str(x.stem).split("_")[0])
        )

        result_file.write('=' * 100 + '\n')
        result_file.write(cache_dir.name + '\n\n')

        for img_path in imgs:
            if str(img_path.stem).split("_")[1] in ('0', '1', 'FAILED'):
                payload = {
                    "image_path": img_path,
                    "out_dir": cache_dir_in_img_dir,
                }
                send(proc3, {"id": id, "op": "do", "payload": payload})

                while True:
                    evt = read_event(proc3)
                    print("EVENT:", evt)

                    if evt.get("type") != "result":
                        continue
                    if evt.get("id") != id:
                        continue

                    if evt.get("ok") is True:
                        txt_path = evt.get("payload").get("txt_path")
                        txt = Path(txt_path).read_text(encoding='utf-8')
                        if txt:
                            result_file.write(txt + '\n\n')
                        break

                    break

                id += 1
    result_file.write('=' * 100 + '\n')
    result_file.flush()
    result_file.close()

    send(proc3, {"id": id, "op": "ext"})
    id += 1
    evt = read_event(proc3)
    print("EVENT:", evt)

    rc = proc3.wait(timeout=10)
    print(f"worker exit code: {rc}\n")


    if DELETE_CACHE_AFTER_COMPLETION:
        shutil.rmtree(cache_root)
        print(f'Deleted cache at: {cache_root}')


if __name__ == "__main__":
    print('\nCONSPECT\n\n')
    configure()
    main()
