# LabCount · Conteo de personas en el laboratorio

Aplicación web para contar y monitorear personas en un laboratorio en tiempo
real. Combina **Django** (backend web), **OpenCV** (captura de video y
detección de personas) y **PostgreSQL** (persistencia). La guía práctica
G003-S12 (Construcción de software) exige estas tres tecnologías y una
interfaz interactiva con video en vivo; este repositorio cumple todos los
requisitos.

> Estado: aplicación funcional, 48 pruebas automatizadas (todas en verde),
> PostgreSQL en contenedor Docker, OpenCV 4.14 integrado como dependencia
> Python (`opencv-python`), sin entorno virtual versionado.

---

## 1. Características

- Tres fuentes de video: cámara web, archivo de video (MP4/AVI/MOV/MKV/WEBM)
  y **demostración sintética** (no requiere cámara ni archivo).
- Tres métodos de detección OpenCV: **HOG** (personas), **MOG2**
  (movimiento) e **Híbrido** (HOG + movimiento). La demostración usa un
  detector sintético con cajas conocidas para garantizar una presentación
  estable.
- Línea virtual de conteo (vertical u horizontal) con dirección de cruce
  (entrada / salida), debounce por pista y seguimiento por centroides.
- Streaming MJPEG en tiempo real con anotaciones (cajas, trayectorias, HUD
  con ocupación, entradas, salidas, únicos, pico, FPS).
- Persistencia de sesiones, muestras de ocupación, eventos de cruce y
  capturas (snapshots) en PostgreSQL.
- Panel de control con gráfica de ocupación (Canvas), historial paginado,
  filtros, exportación CSV y reportes.
- Autenticación (registro/login/logout), control de propiedad de sesiones
  y panel de administración Django.
- Endpoint de salud `/health/` (BD + OpenCV) apto para despliegue.
- Sin dependencias de CDN: CSS y JS propios.

## 2. Stack y versiones

| Componente | Versión |
|---|---|
| Python | 3.12.10 |
| Django | 5.2.19 |
| OpenCV (`opencv-python`) | 4.14.0.94 |
| NumPy | 2.5.4 |
| psycopg (PostgreSQL) | 3.3.8 |
| python-dotenv | 1.2.4 |
| Pillow | 11.3.0 |
| PostgreSQL | 16 (Docker) |

## 3. Estructura del proyecto

```
.
├── apps/
│   ├── core/          # landing, health, modelo Laboratory, context processor
│   ├── accounts/      # registro, login/logout
│   ├── monitoring/    # sesiones, streaming, detector, tracker, contador
│   └── reports/       # reportes y exportación CSV
├── config/            # settings, urls, wsgi, asgi
├── templates/         # plantillas Django
├── static/            # CSS/JS propios + favicon
├── docs/              # documentación del proyecto (roles, wireframes, riesgos, etc.)
├── docker-compose.yml # PostgreSQL 16
├── manage.py
├── requirements.txt
├── .env.example
└── README.md
```

## 4. Requisitos previos

- Python 3.11 o superior.
- Docker Desktop (para PostgreSQL) **o** un servidor PostgreSQL 14+ local.
- Git (opcional, para clonar).
- No se versiona ningún entorno virtual: créelo localmente si lo desea.

## 5. Instalación rápida

```bash
# 1. Clonar / copiar el proyecto
cd "Conteo de personas en el laboratorio"

# 2. (Opcional) entorno virtual local
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

# 3. Dependencias
pip install -r requirements.txt

# 4. Variables de entorno
cp .env.example .env   # Linux/macOS
# Windows (PowerShell): Copy-Item .env.example .env

# 5. Levantar PostgreSQL
docker compose up -d

# 6. Migraciones
python manage.py migrate

# 7. Datos demo (usuario + historial)
python manage.py seed_demo --with-user --with-history

# 8. (Opcional) superusuario para /admin
python manage.py createsuperuser

# 9. Servidor de desarrollo
python manage.py runserver
```

Abra `http://127.0.0.1:8000/`. Credenciales demo: **demo / Demo12345!**.

## 6. Variables de entorno

Ver `.env.example`. Las principales:

| Variable | Descripción | Default |
|---|---|---|
| `DJANGO_SECRET_KEY` | Clave secreta de Django | insegura (solo dev) |
| `DJANGO_DEBUG` | Modo depuración | `True` |
| `DJANGO_ALLOWED_HOSTS` | Hosts permitidos | `127.0.0.1,localhost` |
| `DB_ENGINE` | `postgresql` o `sqlite` (solo pruebas) | `postgresql` |
| `DB_NAME/USER/PASSWORD/HOST/PORT` | Conexión PostgreSQL | `conteo_lab` / `conteo_user` / `conteo_pass` / `127.0.0.1` / `5432` |
| `LABCOUNT_DEFAULT_DETECTOR` | `hybrid`, `hog`, `motion`, `demo` (fuente) | `hybrid` |
| `LABCOUNT_CAMERA_INDEX` | Índice de cámara web | `0` |
| `LABCOUNT_MAX_FRAME_WIDTH` | Ancho máximo de frame | `960` |
| `LABCOUNT_STREAM_FPS` | FPS del stream | `16` |
| `LABCOUNT_DETECT_EVERY` | Detectar cada N frames | `2` |
| `LABCOUNT_SAMPLE_SECONDS` | Persistir muestra cada N segundos | `5` |
| `LABCOUNT_LINE_ORIENTATION` | `vertical` o `horizontal` | `vertical` |
| `LABCOUNT_LINE_POSITION` | Posición relativa de la línea (0.1–0.9) | `0.50` |

## 7. Uso

1. Inicie sesión (o regístrese).
2. En el panel, elija **Fuente de video**:
   - *Cámara web*: índice de cámara.
   - *Archivo de video*: suba un video.
   - *Demostración*: escena sintética con personas animadas (recomendado
     para presentaciones sin hardware).
3. Elija **Método de detección** (HOG / movimiento / híbrido). En demo se
   usa el detector sintético independientemente.
4. Configure la **línea de conteo** (orientación y posición).
5. Pulse **Iniciar monitoreo**. El video anotado aparece en vivo.
6. Use **Capturar** para guardar un snapshot y **Finalizar** para cerrar la
   sesión (se persisten muestras y cruces).
7. Consulte **Sesiones** (historial, detalle con gráfica) y **Reportes**
   (exportación CSV).

## 8. Pruebas

```bash
python manage.py test
```

Suite actual: **48 pruebas** (tracker, contador, detectores/demo, modelos,
vistas). Todas en verde. La base de pruebas usa PostgreSQL (crea/destruye
la BD de test automáticamente).

## 9. Arquitectura (resumen)

- `PeopleCounter` (`apps/monitoring/services/counter.py`) procesa cada frame:
  detector → tracker → cruce de línea → anotación → estadísticas.
- `CentroidTracker` (`tracker.py`) asocia detecciones por distancia
  euclidiana, confirma tras `min_hits` y tolera desapariciones.
- `StreamManager` (`manager.py`) es un singleton con un hilo daemon que
  mantiene la fuente abierta y publica el último JPEG; el endpoint MJPEG
  (`/monitoring/stream/`) y la API (`/monitoring/api/stats/`) consumen ese
  estado. Persiste muestras cada `LABCOUNT_SAMPLE_SECONDS` y cruces al
  ocurrir.
- Modelos: `Laboratory`, `MonitoringSession`, `OccupancySample`,
  `CrossingEvent`, `Snapshot`. Visibilidad por propietario (staff ve todo).

Más detalle en `docs/ARCHITECTURE.md`.

## 10. OpenCV: integración y justificación

La guía exige OpenCV. En lugar de vendorizar el código fuente C++ del
repositorio `opencv/opencv` (lo cual no aporta a una app Django y
complicaría el build), se integra `opencv-python` como dependencia, que
expone el mismo módulo `cv2` usado en todo el proyecto:

- Captura: `cv2.VideoCapture` (cámara/archivo).
- Detección: `cv2.HOGDescriptor`, `cv2.createBackgroundSubtractorMOG2`,
  NMS por `cv2.dnn.NMSBoxes`.
- Anotación: `cv2.rectangle`, `cv2.putText`, `cv2.circle`, `cv2.line`,
  `cv2.addWeighted`.
- Codificación: `cv2.imencode(".jpg", ...)` para MJPEG y snapshots.

Esto mantiene el proyecto portable (pip install) y reproducible, y permite
ejecutar `import cv2` en cualquier entorno con la rueda instalada.

## 11. Documentación adicional

En `docs/`:

- `ROLES_AND_RULES.md` — roles del equipo y reglas de trabajo.
- `WIREFRAMES.md` — 3 bocetos de interfaz (landing, panel, historial).
- `RISK_MATRIX.md` — matriz de riesgos.
- `JIRA_BOARD.md` — tablero Jira (épicas/historias).
- `ARCHITECTURE.md` — arquitectura detallada.
- `TEST_PLAN.md` — plan de pruebas.
- `USER_MANUAL.md` — manual de usuario.
- `GUIDE_COMPLIANCE.md` — trazabilidad contra la guía.
- `OPENCV_INTEGRATION.md` — detalle de integración OpenCV.

## 12. Despliegue / notas

- En producción: `DEBUG=False`, `DJANGO_SECRET_KEY` seguro,
  `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` configurados, servir estáticos
  con `collectstatic` detrás de un reverse proxy, y ejecutar con gunicorn/uwsgi.
- La base de datos debe ser PostgreSQL (requisito de la guía); `DB_ENGINE=sqlite`
  solo se admite para pruebas aisladas.
- No se versionan `.env`, `.venv`, `media/`, `staticfiles/`, logs.

## 13. Licencia

Proyecto académico para la guía G003-S12. Uso educativo.