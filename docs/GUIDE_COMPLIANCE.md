# Trazabilidad contra la guía · LabCount

Guía: G003-S12-SOFTWARE2019-PRESENCIAL-CONSTRU2026115102458 (Construcción
de software). Requisitos identificados y cómo se cumplen.

| # | Requisito de la guía | Cumplimiento en el proyecto |
|---|---|---|
| 1 | Backend en Python con framework Django | Django 5.2 (`config/`, apps) |
| 2 | Uso obligatorio de OpenCV | `opencv-python` 4.14; `cv2` en detectores, tracker, contador, manager, vistas |
| 3 | Base de datos PostgreSQL | `django.db.backends.postgresql`; Docker Compose PostgreSQL 16; `.env` |
| 4 | Captura de video en tiempo real (cámara/archivo) | `cv2.VideoCapture`; `StreamManager._open_source` |
| 5 | Detección de personas | HOG (`HOGDescriptor`), MOG2, híbrido; NMS |
| 6 | Conteo y resultados sobre el video | Línea virtual, cajas, trayectorias, HUD con métricas |
| 7 | Interfaz web interactiva | Dashboard, formularios, gráfica Canvas, polling REST |
| 8 | Repositorio GitHub con README y requirements | `README.md`, `requirements.txt`, estructura lista para `git init`/push |
| 9 | Sin entorno virtual versionado | `.gitignore` excluye `.venv/` |
| 10 | Tema elegido: "Conteo de personas en el laboratorio" | Título, modelos, UI y docs usan el tema |
| 11 | Roles y reglas de trabajo | `docs/ROLES_AND_RULES.md` |
| 12 | 3 bocetos de interfaz (sketches) | `docs/WIREFRAMES.md` |
| 13 | Matriz de riesgos | `docs/RISK_MATRIX.md` |
| 14 | Tablero Jira | `docs/JIRA_BOARD.md` |
| 15 | Pruebas | `docs/TEST_PLAN.md` + 48 pruebas automatizadas |

## Verificación rápida

```bash
python manage.py check          # sin errores
python manage.py test           # 48 OK
curl http://127.0.0.1:8000/health/   # status ok, opencv 4.14.0, database ok
```

## Notas

- OpenCV se integra como dependencia (`opencv-python`) en lugar de
  vendorizar el repositorio C++: más portable y reproducible, y expone el
  mismo módulo `cv2` exigido por la guía (ver `OPENCV_INTEGRATION.md`).
- PostgreSQL es obligatorio; SQLite solo se admite para pruebas aisladas
  (`DB_ENGINE=sqlite`).