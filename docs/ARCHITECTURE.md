# Arquitectura · LabCount

## 1. Visión general

Aplicación web monolítica Django con un hilo de procesamiento de video
(OpenCV) por proceso. PostgreSQL persiste sesiones, muestras, cruces y
capturas. El navegador consume un stream MJPEG y sondea estadísticas por
REST (JSON).

```
┌──────────────┐    HTTP/MJPEG    ┌──────────────────────────┐
│  Navegador   │ ◄──────────────► │  Django (views/urls)     │
│  (HTML/JS/   │                  │  StreamManager (singleton)│
│   Canvas)    │                  │  PeopleCounter (OpenCV)  │
└──────────────┘                  │  PostgreSQL (psycopg)    │
                                  └──────────────────────────┘
```

## 2. Capas

### 2.1 Presentación
- Plantillas Django en `templates/`, CSS/JS propios en `static/`.
- `dashboard.js` sondea `/monitoring/api/stats/` cada 2 s y actualiza KPIs.
- `charts.js` dibuja la gráfica de ocupación en Canvas.
- Video: `<img src="/monitoring/stream/">` (MJPEG).

### 2.2 Control (views)
- `apps/core`, `apps/accounts`, `apps/monitoring`, `apps/reports`.
- Decoradores `login_required`, `require_POST/GET`.
- `reconcile_stale_sessions()` corrige sesiones huérfanas al arrancar.

### 2.3 Servicios de conteo (`apps/monitoring/services/`)
- `detectors.py`: `HOGPersonDetector`, `MotionDetector`, `HybridDetector`,
  `create_detector`. NMS con `cv2.dnn.NMSBoxes`.
- `demo.py`: `DemoScene` (personas animadas) + `DemoPersonDetector`
  (cajas ground-truth).
- `tracker.py`: `CentroidTracker` (asociación greedy por distancia
  euclidiana, confirmación por `min_hits`, tolerancia a desapariciones).
- `counter.py`: `PeopleCounter` (orquesta detector+tracker+cruce de línea+
  anotación+estadísticas).
- `manager.py`: `StreamManager` singleton (hilo daemon, fuente, persistencia).

### 2.4 Persistencia
- Modelos: `Laboratory`, `MonitoringSession`, `OccupancySample`,
  `CrossingEvent`, `Snapshot`.
- Visibilidad por propietario (`visible_to`).

## 3. Flujo de procesamiento de un frame

1. El hilo lee un frame de la fuente (cámara/archivo/demo).
2. `_resize_frame` limita el ancho a `LABCOUNT_MAX_FRAME_WIDTH`.
3. `counter.process(frame)`:
   - Detecta (si toca según `detect_every`).
   - Actualiza el tracker.
   - `_detect_line_crossings`: evalúa cambio de lado respecto a la línea;
     debounce de 1 s por pista; incrementa `entries`/`exits`.
   - Construye `CountingStats`.
   - Anota el frame (línea, cajas, trayectorias, HUD, badge).
4. Se codifica a JPEG y se publica en `StreamManager`.
5. Cada `LABCOUNT_SAMPLE_SECONDS` se persiste una `OccupancySample` y se
   actualiza la sesión.
6. Los cruces se persisten al ocurrir (`CrossingEvent`).

## 4. Concurrencia y ciclo de vida

- Un único hilo daemon por proceso (`StreamManager._run`).
- `threading.RLock` protege el estado compartido.
- Al detener: `stop_event.set()`, join con timeout, finalización de sesión.
- Al arrancar la app: `reconcile_stale_sessions()` marca como error las
  sesiones que quedaron `running` tras un reinicio.

## 5. Decisiones técnicas

- **MJPEG en lugar de WebSockets**: más simple, compatible con `<img>`,
  suficiente para un laboratorio. Polling de stats cada 2 s.
- **Tracker por centroides**: determinista, sin dependencias extra, adecuado
  para pocas personas.
- **Demo sintética**: garantiza una demostración estable sin hardware ni
  modelos pesados.
- **PostgreSQL obligatorio** (guía); SQLite solo para pruebas aisladas.

## 6. Configuración

Parámetros en `config/settings.py` leídos de `.env` (ver README §6). Los
valores por defecto permiten arrancar con `docker compose up -d` +
`migrate` + `runserver`.