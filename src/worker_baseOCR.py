import cv2
import pytesseract
from pathlib import Path
from worker_base import BaseWorker

class BaceOCRWorker(BaseWorker):
    def on_start(self):
        return {"name": "baseOCR-worker", "ready": True}

    def preprocess_text(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        gray = cv2.bilateralFilter(gray, d=7, sigmaColor=40, sigmaSpace=40)
        bg = cv2.medianBlur(gray, 31)
        norm = cv2.divide(gray, bg, scale=255)
        otsu = cv2.threshold(norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        return otsu

    def preprocess_handwritten(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        return otsu


    def _process_image(self, img, img_path, lang="rus+eng"):
        stem = Path(img_path).stem
        parts =stem.split("_")
        if len(parts) < 2:
            raise ValueError(f"bad filename format (expected [img_id]_[cls_id])")

        self.img_id = parts[0]
        self.cls_id = parts[1]

        if (self.img_id or self.cls_id) == 'FAILED':
            self.img_id = '0'
            self.cls_id = '0'

        if self.cls_id == "0":
            bin_img = self.preprocess_text(img)
            psm = 6
        elif self.cls_id == "1":
            bin_img = self.preprocess_handwritten(img)
            psm = 3

        cfg = f'--oem 3 --psm {psm} -c preserve_interword_spaces=1'
        text = pytesseract.image_to_string(bin_img, lang=lang, config=cfg)

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