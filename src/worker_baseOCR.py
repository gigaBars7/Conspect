import cv2
from pathlib import Path
from worker_base import BaseWorker

class BaceOCRWorker(BaseWorker):
    def on_start(self):
        return {"name": "baseOCR-worker", "ready": True}


    def _process_image(self, img, img_path):
        stem = Path(img_path).stem
        parts =stem.split("_")
        if len(parts) < 2:
            raise ValueError(f"bad filename format (expected [img_id]_[cls_id])")

        self.img_id = parts[0]
        self.cls_id = parts[1]

        if (self.img_id or self.cls_id) == 'FAILED':
            self.img_id = '0'
            self.cls_id = '0'

        text = f"Текст из изображения: {self.img_id} Класс: {self.cls_id}"
        return {"img_id": self.img_id, "cls_id": self.cls_id, "text": text}


    def handle(self, op, payload):
        if op != "do":
            raise ValueError(f"unknown op: {op}")

        image_path = payload["image_path"]
        out_dir = Path(payload["out_dir"])

        img = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if img is None:
            raise FileNotFoundError(f"cannot read image: {image_path}")

        res = self._process_image(img, image_path)

        out_path = out_dir / f"{res['img_id']}_{res['cls_id']}.txt"
        out_txt = out_path.write_text(res['text'], encoding='utf-8')

        return {"txt_path": str(out_path)}


    def on_shutdown(self):
        return {"bye": True}

if __name__ == "__main__":
    BaceOCRWorker().run()