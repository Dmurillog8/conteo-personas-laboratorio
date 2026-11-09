# Plan de pruebas — LabCount

Tema: Conteo de personas en el laboratorio. Responsable propuesto de la revisión del equipo: Jorge Alfredo Patiño Suárez (QA). La asignación no significa que haya ejecutado las comprobaciones registradas.

## 1. Objetivo y alcance

Comprobar autenticación, detección, seguimiento, conteo, transmisión y persistencia. Separar pruebas automatizadas, recorrido HTTP de una demo sintética y mediciones con personas reales. Las dos primeras no acreditan precisión en el laboratorio.

## 2. Pruebas automatizadas

Desde la carpeta del proyecto, con PostgreSQL activo:

```bash
python manage.py check
python manage.py test --verbosity 2
```

El primer comando revisa la configuración; el segundo ejecuta los casos y crea/elimina una base temporal. El usuario de PostgreSQL necesita permiso para crearla.

| Área | Archivo | Casos |
|---|---|---:|
| Cuentas | `apps/accounts/tests.py` | 5 |
| Núcleo y salud | `apps/core/tests.py` | 4 |
| Reportes | `apps/reports/tests.py` | 5 |
| Contador | `apps/monitoring/tests/test_counter.py` | 7 |
| Demo y detectores | `apps/monitoring/tests/test_demo_and_detectors.py` | 8 |
| Modelos | `apps/monitoring/tests/test_models.py` | 4 |
| Regresiones de conteo y DNN | `apps/monitoring/tests/test_precision.py` | 12 |
| Seguimiento | `apps/monitoring/tests/test_tracker.py` | 5 |
| Vistas y permisos | `apps/monitoring/tests/test_views.py` | 12 |
| **Total** | | **62** |

Resultado local del 9 de noviembre de 2026: **62 pruebas aprobadas, sin omisiones**, en 19,815 s. Python 3.14.6, Django 5.2.19, OpenCV 4.14.0 y PostgreSQL 16.15. [Salida de ejecución](evidencias/pruebas-automatizadas.txt).

Se incluyen carga e inferencia del modelo ONNX desde una ruta con tildes y rechazo de un archivo corrupto. Si falta el modelo, los casos que lo necesitan pueden omitirse: revisar cada ejecución y no reportar omisiones como aprobaciones.

## 3. Integración realizada

Contra el servidor local se comprobó por HTTP: login, iniciar demo, estadísticas, JPEG y MJPEG, captura, finalizar, historial, detalle y CSV. Se verificaron también los registros en PostgreSQL y el archivo de captura. [Resultados](VALIDACION.md).

Ruth aportó capturas del navegador con portada, panel, cámara real, demo, historial y reportes. Las imágenes mostraban un fallo: el video daba conteos mientras los indicadores laterales permanecían en cero. Se corrigió una excepción de la gráfica y se repitió la demo en el navegador: las tarjetas de ocupación, entradas, salidas y FPS se actualizaron. Queda pendiente documentar una prueba equivalente con cámara real y comparar los conteos manualmente. [demo-sintetica.jpg](evidencias/demo-sintetica.jpg) es un frame del servicio, no una captura de la interfaz ni una escena real.

## 4. Casos manuales pendientes

QA debe registrar fecha, equipo/cámara, configuración, esperado, observado, evidencia y responsable.

| ID | Caso | Resultado esperado | Estado |
|---|---|---|---|
| M01 | Inicio, registro, login y logout | Navegación y mensajes comprensibles; acceso protegido | Pendiente visual |
| M02 | Demo: iniciar, gráfica, capturar, finalizar | Video y métricas visibles; captura e historial accesibles | Indicadores y gráfica verificados en navegador; captura/finalización aprobadas por HTTP |
| M03 | Laboratorio vacío | Conteo estable en cero; registrar falsos positivos | Pendiente cámara |
| M04 | Una persona quieta y caminando | Seguimiento coherente; registrar duplicados o pérdidas | Pendiente cámara |
| M05 | Entrada y salida por línea | Un cruce por paso completo en la dirección correspondiente | Pendiente cámara |
| M06 | Persona detenida junto a la línea | No acumular cruces por pequeñas oscilaciones | Pendiente cámara |
| M07 | Varias personas y oclusiones | Comparar contra conteo manual; registrar cambios de ID | Pendiente cámara |
| M08 | Cambios de luz y distancia | Registrar pérdidas y falsos positivos | Pendiente cámara |
| M09 | Archivo de video real y final del archivo | Procesar, finalizar y guardar datos sin errores | Pendiente archivo real |
| M10 | Historial, filtros, detalle y CSV | Datos coherentes y presentación legible | Pendiente visual; CSV HTTP aprobado |
| M11 | Otra cuenta y staff | Historial según permisos; video activo compartido entre autenticados | Pendiente manual; permisos cubiertos por pruebas |
| M12 | Cámara desconectada u ocupada | Mensaje comprensible y posibilidad de iniciar otra fuente | Pendiente cámara |

En M03–M08 anotar conteo manual y observado, entradas/salidas reales y detectadas, duración, método y condiciones. Calcular errores con esos datos; no inventar porcentajes de precisión. Acordar el umbral aceptable con el docente.

## 5. Aceptación

- Pruebas automatizadas sin fallos; omisiones explícitamente justificadas.
- Configuración, migraciones, PostgreSQL y OpenCV comprobados.
- Recorrido visual y casos reales con evidencia, incluidos fallos y límites.
- Video desde computadora de máximo tres minutos y enlaces accesibles.
- Identificar los datos sintéticos en el informe y exposición.
