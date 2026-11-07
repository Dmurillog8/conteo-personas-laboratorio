# Plan de pruebas · LabCount

## 1. Objetivo

Verificar el cumplimiento funcional y no funcional de la aplicación:
detección/contaje, streaming, persistencia, autenticación y UI.

## 2. Estrategia

- **Pruebas unitarias/integración** con Django Test Framework sobre
  PostgreSQL (BD de test creada/destruida automáticamente).
- **Pruebas manuales** end-to-end con navegador (Chrome/Edge) sobre el
  servidor de desarrollo.
- **Verificación de salud** con `/health/`.

## 3. Suite automatizada

Comando: `python manage.py test`

| Módulo | Archivo | Casos | Qué cubre |
|---|---|---|---|
| Tracker | `apps/monitoring/tests/test_tracker.py` | ~12 | Registro, asociación, confirmación, desaparición, reset, distancia máxima |
| Contador | `apps/monitoring/tests/test_counter.py` | ~8 | Cruce vertical/horizontal, entrada/salida, no doble conteo, ocupación a cero, anotación, clamp de línea |
| Detectores/Demo | `apps/monitoring/tests/test_demo_and_detectors.py` | ~10 | HOG/MOG2/híbrido, NMS, escena demo, detector sintético |
| Modelos | `apps/monitoring/tests/test_models.py` | ~8 | Laboratorio, sesión, muestras, cruces, snapshots, visibilidad |
| Vistas | `apps/monitoring/tests/test_views.py` | ~10 | Dashboard, start/stop, stream, stats, snapshots, sesiones, permisos |

Total actual: **48 pruebas**, todas en verde (~12 s).

## 4. Casos manuales (checklist)

- [ ] Landing carga sin autenticación; redirige al panel si está logueado.
- [ ] Registro e inicio de sesión funcionan; logout redirige a landing.
- [ ] Iniciar monitoreo en modo Demo muestra video anotado en vivo.
- [ ] KPIs se actualizan (ocupación, entradas, salidas, únicos, pico, FPS).
- [ ] Gráfica de ocupación se dibuja y actualiza.
- [ ] Capturar guarda un snapshot visible en el detalle de sesión.
- [ ] Finalizar cierra la sesión y aparece en el historial.
- [ ] Sesiones: filtros por estado y búsqueda; paginación.
- [ ] Detalle de sesión: gráfica, cruces, snapshots.
- [ ] Reportes: resumen agregado; exportación CSV de sesiones y de sesión.
- [ ] `/health/` devuelve `status: ok` con BD y OpenCV.
- [ ] Modo cámara/archivo (si hay hardware/archivo disponible).
- [ ] Permisos: un usuario no ve sesiones de otro (salvo staff).

## 5. Criterios de aceptación

- Suite automatizada en verde.
- `python manage.py check` sin errores.
- Demo end-to-end sin errores en consola ni en logs.
- Todas las rutas principales devuelven 200 para usuario autenticado.

## 6. Entorno de prueba

- Python 3.12, PostgreSQL 16 en Docker (`labcount-postgres`).
- Variables de `.env` con `DB_ENGINE=postgresql`.
- Ejecutar `seed_demo --with-user --with-history` para datos de ejemplo.