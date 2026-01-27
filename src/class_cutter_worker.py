import cv2
import numpy as np
from pathlib import Path
from ultralytics import YOLO

from worker_base import BaseWorker

class ClassCutterWorker(BaseWorker):
    def __init__(self):
        super().__init__()
        self.model = None


    def on_start(self):
        HERE = Path(__file__).resolve().parent
        weights = HERE.parent / 'weights' / 'class_cutter' / 'best.pt'
        if not weights.exists():
            raise FileNotFoundError(f"Weights not found: {weights}")

        self.model = YOLO(str(weights))
        return {"name": "class_cutter-worker", "ready": True}


    def _process_image(self, img):
        h, w = img.shape[:2]
        cw = max(1, w // 2)
        ch = max(1, h // 2)
        x1 = (w - cw) // 2
        y1 = (h - ch) // 2
        x2 = x1 + cw
        y2 = y1 + ch
        crop = img[y1:y2, x1:x2]
        return [
            {'id': 0, 'cls': 1, 'img': crop},
            {'id': 1, 'cls': 2, 'img': crop},
            {'id': 2, 'cls': 0, 'img': crop}
        ]


    def handle(self, op, payload):
        if op != "do":
            raise ValueError(f"unknown op: {op}")

        image_path = payload["image_path"]
        out_dir = payload["out_dir"]

        src_img = cv2.imread(image_path, cv2.IMREAD_COLOR)
        src_ext = image_path.split(".")[-1]
        if src_img is None:
            raise FileNotFoundError(f"cannot read image: {image_path}")

        img_paths = []
        preds = self._process_image(src_img)
        for pred_img in preds:
            img_id = pred_img["id"]
            img_cls = pred_img["cls"]
            img = pred_img["img"]

            img_name = f'{img_id}_{img_cls}.{src_ext}'
            out_file = f'{out_dir}/{img_name}'
            img_paths.append(out_file)

            ok = cv2.imwrite(out_file, img)

        return {"img_paths": img_paths}


    def on_shutdown(self):
        return {"bye": True}


if __name__ == "__main__":
    ClassCutterWorker().run()