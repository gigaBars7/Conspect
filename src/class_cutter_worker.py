import cv2
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
        pred = self.model.predict(
            source=img,
            conf=0.3,
            iou=0.5,
            device="cuda",
            save=False,
            verbose=False
        )[0]

        if len(pred.boxes) == 0:
            raise RuntimeError("no detections")

        xyxy = pred.boxes.xyxy.detach().cpu().numpy()
        cls = pred.boxes.cls.detach().cpu().numpy().astype(int)

        # 0: 'text', 1: 'handwritten text', 2: 'formula', 3: 'scheme',
        # 4: 'image', 5: 'graph', 6: 'table', 7: 'interface'
        target_cls = (0, 1, 2, 3, 4, 5, 6)

        h, w = img.shape[:2]
        line_tol = max(12, int(0.02 * h))

        items = []
        for b, c in zip(xyxy, cls):
            if c not in target_cls:
                continue
            x1, y1, x2, y2 = b.tolist()
            x1i = max(0, min(w - 1, int(round(x1))))
            y1i = max(0, min(h - 1, int(round(y1))))
            x2i = max(0, min(w, int(round(x2))))
            y2i = max(0, min(h, int(round(y2))))
            if x2i <= x1i or y2i <= y1i:
                continue
            yc = 0.5 * (y1i + y2i)
            row = int(round(yc / line_tol))
            items.append((row, x1i, y1i, x2i, y2i, c))

        if not items:
            raise RuntimeError("no detections for target_classes")

        items.sort(key=lambda t: (t[0], t[1]))

        preds = []
        for idx, (row, x1i, y1i, x2i, y2i, c) in enumerate(items, start=1):
            crop = img[y1i:y2i, x1i:x2i]
            preds.append({
                "id": idx,
                "cls": int(c),
                "img": crop
            })

        return preds


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