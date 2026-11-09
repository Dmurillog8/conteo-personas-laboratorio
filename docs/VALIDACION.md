# Registro de validación local — LabCount

**Fecha: 9 de noviembre de 2026.** Tema: Conteo de personas en el laboratorio. Base revisada: commit `985cb474caa87a436715bd773a4fc4030055073b`. Los cambios se publicaron en la rama [`docs/labcount-validacion-entrega`](https://github.com/Dmurillog8/conteo-personas-laboratorio/tree/docs/labcount-validacion-entrega); la integración en `main` requiere revisión.

## Entorno y base de datos

| Componente | Versión / configuración comprobada |
|---|---|
| Sistema | Windows |
| Python | 3.14.6 |
| Django | 5.2.19 |
| OpenCV | 4.14.0 (`opencv-python` 4.14.0.94) |
| PostgreSQL | 16.15, local en `127.0.0.1:5432` |
| Base / usuario | `conteo_lab` / `conteo_user` |
| Instalación | `%LOCALAPPDATA%/LabCount/postgresql16`, fuera del repositorio |

Se conservaron las variables locales existentes. No se incluyen contraseñas aquí. SQL Server Management Studio no reemplaza PostgreSQL, exigido por la guía. Docker es una alternativa de instalación, no un requisito adicional para este equipo.

## Comprobaciones

| Comprobación | Resultado |
|---|---|
| `python manage.py migrate` | Migraciones aplicadas |
| `python manage.py check` | Sin problemas identificados |
| `python manage.py makemigrations --check --dry-run` | Sin cambios de modelos pendientes |
| `python -m pip check` | Sin dependencias incompatibles detectadas |
| `python scripts/download_models.py` | Modelo existente y carga OpenCV correcta |
| `python manage.py test --verbosity 2` | **62 pruebas, 19,815 s, OK; ninguna omitida** |
| `/health/` | HTTP 200; status y database OK; OpenCV 4.14.0 |
| Auxiliar PostgreSQL | Detener, iniciar y consultar estado funcionaron |

[Salida de pruebas](evidencias/pruebas-automatizadas.txt). Se utilizó una base temporal PostgreSQL eliminada al finalizar. El tiempo corresponde a esta ejecución.

## Corrección del detector

Se reprodujo un fallo al cargar el modelo ONNX desde una ruta Windows con tildes. El archivo existía, pero OpenCV no podía abrirlo por nombre. Ahora Python lee sus bytes y OpenCV recibe el contenido. El script de comprobación utiliza el mismo mecanismo.

Se añadieron regresiones para carga/inferencia desde ruta Unicode y error ante un modelo corrupto. Un archivo presente pero ilegible ya no queda oculto como prueba omitida.

## Recorrido por HTTP

Se probó el servidor local con la cuenta de demostración y escena sintética, sin acceder a la cámara:

1. Inicio de sesión y panel.
2. Inicio de demo; estadísticas con `running=True`.
3. Recepción de JPEG válido y encabezado/frame MJPEG.
4. Captura y finalización con `running=False`.
5. Historial, detalle y reportes con HTTP 200.
6. Dos exportaciones CSV con cabeceras y filas.
7. Consulta PostgreSQL: sesión 1 en estado `stopped`, **3 muestras, 2 cruces y 1 captura**, con archivo existente.

[Registro HTTP](evidencias/flujo-http.txt). [Frame de demo](evidencias/demo-sintetica.jpg): imagen generada por el servicio y revisada visualmente, no fotografía del laboratorio ni captura del navegador. La sesión figura como «Escena de demostración (sintética)» en el historial.

## Límites y pendientes

- Ruth aportó capturas del navegador del 9 de noviembre: portada, configuración, cámara web con persona y anotaciones, demostración sintética, historial y reportes. Eso acredita una **revisión visual parcial** y apertura de cámara real en su equipo. La captura no mide precisión ni verifica todos los casos del [plan manual](TEST_PLAN.md).
- En las capturas iniciales el video mostraba cifras distintas de cero mientras las tarjetas laterales seguían en cero. Se identificó una excepción al construir la gráfica (`this._draw.bind(...)`, método inexistente) y se corrigió en `static/js/charts.js`. Tras reiniciar el servidor y actualizar el navegador, se inició una nueva demo sintética: las tarjetas pasaron de cero a seis personas visibles, pico siete, una entrada, una salida y 15,9 FPS; el gráfico volvió a estar presente. Esta comprobación visual confirma la actualización de indicadores en la demo, pero no mide precisión con cámara real.
- El reinicio del servidor durante la comprobación interrumpió una sesión sintética de prueba, que quedó marcada «Con error» en el historial. No representa un fallo de detección. La siguiente sesión de prueba se inició correctamente.
- No se midió precisión ni se compararon sistemáticamente los cruces con un conteo manual. La demo usa detecciones sintéticas conocidas.
- El conteo representa personas visibles estimadas. Los identificadores de seguimiento no equivalen a identidades únicas.
- Una sesión de captura por proceso. Video/estadísticas activos se comparten entre autenticados; historial y controles tienen permisos de propietario/staff. No hay aislamiento completo entre laboratorios.
- Uso local del servidor de desarrollo; despliegue requiere configuración adicional.
- Se creó el [tablero Jira LAB](JIRA_BOARD.md) con 12 tareas asignadas. Faltan capturas del tablero y comprobar acceso del docente.
- El video aportado, grabado desde computadora, dura aproximadamente 3 min 34 s: debe ajustarse a **máximo 3 min** y compartirse mediante Drive. Participación del equipo y PDF final siguen pendientes: ver [entrega](ENTREGA_DOCENTE.md).
