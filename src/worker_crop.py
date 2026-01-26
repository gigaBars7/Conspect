import time
import cv2
from worker_base import BaseWorker

class CropWorker(BaseWorker):
    def on_start(self):
        return {"name": "crop-worker", "ready": True}


    def _process_image(self, img):
        h, w = img.shape[:2]
        cw = max(1, w // 2)
        ch = max(1, h // 2)
        x1 = (w - cw) // 2
        y1 = (h - ch) // 2
        x2 = x1 + cw
        y2 = y1 + ch
        crop = img[y1:y2, x1:x2]
        return crop


    def handle(self, op, payload):
        if op != "do":
            raise ValueError(f"unknown op: {op}")

        image_path = payload["image_path"]
        out_path = payload["out_path"]

        img = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if img is None:
            raise FileNotFoundError(f"cannot read image: {image_path}")

        crop = self._process_image(img)

        ok = cv2.imwrite(out_path, crop)
        if not ok:
            raise RuntimeError(f"failed to write image: {out_path}")

        return {"crop_path": out_path}


    def on_shutdown(self):
        return {"bye": True}

if __name__ == "__main__":
    EchoWorker().run()