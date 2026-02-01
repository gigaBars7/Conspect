import cv2
import pytesseract
import easyocr
from pathlib import Path
from worker_base import BaseWorker

class BaceOCRWorker(BaseWorker):
    def on_start(self):
        self.easyocr_reader = easyocr.Reader(['ru', 'en'], gpu=True)
        return {"name": "baseOCR-worker", "ready": True}


    def ocr_easyocr(self, img):
        result = self.easyocr_reader.readtext(img, detail=0, paragraph=True)
        text = "\n".join(result)
        return text


    def prep_tesseract_printed(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        gray = cv2.bilateralFilter(gray, d=7, sigmaColor=40, sigmaSpace=40)
        bg = cv2.medianBlur(gray, 31)
        norm = cv2.divide(gray, bg, scale=255)
        otsu = cv2.threshold(norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        return otsu


    def prep_tesseract_handwritten(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        return otsu


    def ocr_tesseract(self, img, cls_id, lang="rus+eng"):
        if cls_id == "0":
            bin_img = self.prep_tesseract_printed(img)
            psm = 6
        elif cls_id == "1":
            bin_img = self.prep_tesseract_handwritten(img)
            psm = 3

        cfg = f'--oem 3 --psm {psm} -c preserve_interword_spaces=1'
        text = pytesseract.image_to_string(bin_img, lang=lang, config=cfg)
        return text


    def _parse_ids(self, img_path):
        stem = Path(img_path).stem
        parts =stem.split("_")
        if len(parts) < 2:
            raise ValueError(f"bad filename format (expected [img_id]_[cls_id])")

        img_id = parts[0]
        cls_id = parts[1]

        if (img_id or cls_id) == 'FAILED':
            img_id = '0'
            cls_id = '0'

        return img_id, cls_id


    def _process_image(self, img, img_path, mode):
        img_id, cls_id = self._parse_ids(img_path)
        if mode not in (0, 1, 2):
            raise ValueError("mode must be 0 (tesseract), 1 (easyocr), or 2 (both)")

        t_text = ""
        e_text = ""

        if mode in (0, 2):
            t_text = self.ocr_tesseract(img, cls_id=cls_id, lang='rus+eng')
        if mode in (1, 2):
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            e_text = self.ocr_easyocr(img_rgb)

        return {
            "img_id": img_id,
            "cls_id": cls_id,
            "tesseract_text": t_text.strip(),
            "easyocr_text": e_text.strip(),
        }


    def handle(self, op, payload):
        if op != "do":
            raise ValueError(f"unknown op: {op}")

        image_path = payload["image_path"]
        mode = payload["mode"]

        img = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if img is None:
            raise FileNotFoundError(f"cannot read image: {image_path}")

        res = self._process_image(img, image_path, mode)

        return {
            "tesseract_text": res["tesseract_text"],
            "easyocr_text": res["easyocr_text"],
        }


    def on_shutdown(self):
        return {"bye": True}

if __name__ == "__main__":
    BaceOCRWorker().run()