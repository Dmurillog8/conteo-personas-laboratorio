"""Descarga el modelo YOLO usado por el detector "dnn".

Uso (desde la carpeta del proyecto):

    python scripts/download_models.py

El modelo YOLOv5n en formato ONNX (~4 MB) se guarda en ``models/`` y se
ejecuta con ``cv2.dnn`` de OpenCV; no requiere PyTorch ni GPU.
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

MODELS = {
    "yolov5n.onnx": "https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5n.onnx",
}

BASE_DIR = Path(__file__).resolve().parent.parent
TARGET = BASE_DIR / "models"


def main() -> int:
    TARGET.mkdir(exist_ok=True)
    for name, url in MODELS.items():
        destination = TARGET / name
        if destination.exists() and destination.stat().st_size > 1_000_000:
            print(f"[ok] {name} ya existe")
            continue
        print(f"Descargando {name} ...")
        urllib.request.urlretrieve(url, destination)
        print(f"[ok] {destination} ({destination.stat().st_size / 1e6:.1f} MB)")

    import cv2

    net = cv2.dnn.readNetFromONNX(str(TARGET / "yolov5n.onnx"))
    print(f"[ok] OpenCV {cv2.__version__} cargó el modelo correctamente: {net is not None}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
