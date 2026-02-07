import cv2
import numpy as np
from pathlib import Path
from ultralytics import YOLO

from worker_base import BaseWorker

class WhiteboadWorker(BaseWorker):
    def __init__(self):
        super().__init__()
        self.model = None


    def on_start(self):
        HERE = Path(__file__).resolve().parent
        weights = HERE.parent / 'weights' / 'whiteboard' / 'best.pt'
        if not weights.exists():
            raise FileNotFoundError(f"Weights not found: {weights}")

        self.model = YOLO(str(weights))
        return {"name": "whiteboard-worker", "ready": True}


    def _predict(self, img):
        pred = self.model.predict(
            source=img,
            conf=0.25,
            iou=0.5,
            device="cuda",
            save=False,
            verbose=False
        )[0]
        return pred


    def _select_detection_index(self, pred, target_class=None, target_strategy="conf"):
        boxes = pred.boxes
        boxes_count = int(boxes.cls.shape[0])
        if boxes_count == 0:
            raise RuntimeError("no detections")
        idxs = np.arange(boxes_count, dtype=int)

        if target_class is not None:
            classes = boxes.cls.cpu().numpy()
            idxs = (classes == target_class).nonzero()[0]

        if len(idxs) == 0:
            raise RuntimeError("no detections for target_class")

        if len(idxs) == 1:
            return int(idxs[0])

        if target_strategy == "conf":
            return int(idxs[boxes.conf[idxs].argmax()])
        elif target_strategy == "size":
            xywh = boxes.xywh.cpu().numpy()
            sizes = xywh[:, 2] * xywh[:, 3]
            return int(idxs[np.argmax(sizes[idxs])])


    def _mask_for_index(self, pred, idx, W, H):
        mask = pred.masks.data[idx].detach().cpu().numpy()
        if mask.ndim == 3:
            mask = mask[0]
        mask = cv2.resize(mask, (W, H), cv2.INTER_NEAREST)
        mask = (mask > 0.5).astype(np.uint8) * 255
        return mask


    def _largest_contour(self, mask):
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return max(cnts, key=cv2.contourArea)


    def _quad_from_contour(self, cnt):
        peri = cv2.arcLength(cnt, True)
        quad = cv2.approxPolyDP(cnt, 0.02 * peri, True)

        if len(quad) == 4:
            box = quad.reshape(4, 2)
        else:
            rect = cv2.minAreaRect(cnt)
            box = cv2.boxPoints(rect)
        return box


    def _order_points_tl_tr_br_bl(self, pts):
        pts = pts.astype(np.float32)
        s = pts.sum(axis=1)
        d = np.diff(pts, axis=1).ravel()

        tl = pts[np.argmin(s)]
        br = pts[np.argmax(s)]
        tr = pts[np.argmin(d)]
        bl = pts[np.argmax(d)]

        return np.array([tl, tr, br, bl], dtype=np.float32)


    def _compute_warp_size(self, src):
        tl, tr, br, bl = src
        w = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
        h = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
        w = max(1, w)
        h = max(1, h)
        return w, h


    def _warp_perspective_rgb(self, img_rgb, src):
        w, h = self._compute_warp_size(src)
        dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)
        M = cv2.getPerspectiveTransform(src, dst)
        return cv2.warpPerspective(img_rgb, M, (w, h))


    def _process_image(self, img, target_class=None, target_strategy='conf'):
        pred = self._predict(img)
        H, W = img.shape[:2]
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        idx = self._select_detection_index(
            pred, target_class=target_class, target_strategy=target_strategy
        )
        mask = self._mask_for_index(pred, idx=idx, W=W, H=H)
        cnt = self._largest_contour(mask)
        box = self._quad_from_contour(cnt)
        src = self._order_points_tl_tr_br_bl(box)
        warp = self._warp_perspective_rgb(img_rgb, src)

        return warp


    def handle(self, op, payload):
        if op != "do":
            raise ValueError(f"unknown op: {op}")

        image_path = str(payload["image_path"])
        out_path = str(payload["out_path"])
        target_class = payload["target_class"]

        img = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if img is None:
            raise FileNotFoundError(f"cannot read image: {image_path}")

        if "target_strategy" in payload:
            warp_rgb = self._process_image(img, target_class=target_class, target_strategy=payload["target_strategy"])
        else:
            warp_rgb = self._process_image(img, target_class=target_class)

        warp_bgr = cv2.cvtColor(warp_rgb, cv2.COLOR_RGB2BGR)
        ok = cv2.imwrite(out_path, warp_bgr)
        if not ok:
            raise RuntimeError(f"failed to write image: {out_path}")

        return {"warp_path": out_path}


    def on_shutdown(self):
        return {"bye": True}

if __name__ == "__main__":
    WhiteboadWorker().run()