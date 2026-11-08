# Integración de OpenCV · LabCount

## 1. Decisión

La guía exige OpenCV. En lugar de clonar/vendorizar el repositorio
`opencv/opencv` (código C++ que no aporta a una app Django y complicaría
el build y el despliegue), se integra la rueda oficial `opencv-python`,
que expone exactamente el módulo `cv2` utilizado en todo el proyecto.

Motivos:
- Portabilidad: `pip install -r requirements.txt` basta en Windows/Linux/macOS.
- Reproducibilidad: versión fijada (4.14.0.94).
- Sin toolchain C++ ni compilación.
- El mismo API `cv2` que la guía y los ejemplos esperan.

## 2. Uso de `cv2` en el proyecto

| Archivo | Funciones OpenCV usadas |
|---|---|
| `services/detectors.py` | `cv2.dnn.readNetFromONNX` + `cv2.dnn.blobFromImage` (YOLO), `cv2.HOGDescriptor`, `cv2.createBackgroundSubtractorMOG2`, `cv2.dnn.NMSBoxes`, `cv2.cvtColor`, `cv2.RETR_EXTERNAL`, `cv2.findContours` |
| `services/tracker.py` | `numpy` (asociación euclidiana) |
| `services/counter.py` | `cv2.rectangle`, `cv2.putText`, `cv2.circle`, `cv2.line`, `cv2.addWeighted`, `cv2.getTextSize`, `cv2.FONT_HERSHEY_SIMPLEX` |
| `services/manager.py` | `cv2.VideoCapture`, `cv2.imencode`, `cv2.resize`, `cv2.INTER_AREA/LINEAR` |
| `services/demo.py` | `cv2` para dibujar la escena sintética |
| `views.py` | `cv2.imencode` (preview/snapshot) |
| `core/views.py` | `import cv2` en `/health/` para reportar versión |

## 3. Verificación

```bash
python -c "import cv2; print(cv2.__version__)"   # 4.14.0
curl http://127.0.0.1:8000/health/                # opencv: 4.14.0
```

## 4. Notas de rendimiento

- Los frames se redimensionan a `LABCOUNT_MAX_FRAME_WIDTH` (960 px).
- La detección se ejecuta cada `LABCOUNT_DETECT_EVERY` frames (2 por
  defecto) para mantener FPS.
- El stream se codifica a JPEG calidad 82 y se sirve a 25 FPS máx.

## 5. Alternativas consideradas

- Vendorizar `opencv/opencv`: descartado (build complejo, no aporta).
- `opencv-contrib-python`: no necesario (no se usan módulos contrib).
- Modelos DNN (YOLO): **implementado** como detector `dnn` (ver sección 6).

## 6. Detector por red neuronal (recomendado)

- Modelo: YOLOv5n exportado a ONNX (~4 MB, clase COCO `person`), en
  `models/yolov5n.onnx`. Si falta: `python scripts/download_models.py`.
- Se ejecuta con `cv2.dnn` (CPU), sin PyTorch ni GPU. ~40-80 ms por frame.
- Entrada con *letterbox* 640×640 para no deformar a las personas.
- Variables: `LABCOUNT_DNN_MODEL`, `LABCOUNT_DNN_CONFIDENCE` (0.45).
- Si el modelo no existe, el sistema usa el detector híbrido automáticamente.

### Mejoras de precisión del conteo

- **Cajas contenidas**: se descartan cajas (cabeza, piernas) que quedan
  dentro de la caja de una persona; antes una persona se contaba como 2-3.
- **Fragmentos de movimiento (MOG2)**: se unen cabeza/torso/piernas en una
  sola silueta.
- **Seguimiento**: asociación por IoU + distancia proporcional al tamaño
  de la persona; fusión de pistas duplicadas; las pistas no confirmadas se
  descartan rápido y no suman visitantes únicos.
- **Línea de conteo con histéresis**: zona muerta de ±3 % alrededor de la
  línea; un cruce solo se cuenta al pasar de un lado firme al otro.
- **Ocupación estable**: mediana de los últimos 5 ciclos de detección.
- Solo se dibujan personas confirmadas (lo que se ve es lo que se cuenta).