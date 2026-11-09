# Trazabilidad de la guía y rúbrica — LabCount

Guía G003-S12 y capturas de evaluación proporcionadas por el equipo. Tema: **Conteo de personas en el laboratorio**. Revisión local: 9 de noviembre de 2026.

Implementado significa que existe código; validado significa que se obtuvo evidencia de ejecución. Un documento de planificación no sustituye un tablero real ni una grabación.

## Requisitos técnicos y sesiones

| Requisito | Evidencia | Estado / límite |
|---|---|---|
| Python y Django | `config/`, `apps/`, `requirements.txt`; `manage.py check` | Validado localmente |
| OpenCV obligatorio | Detectores, contador, gestor de video; módulo `cv2` | Carga del modelo y pruebas aprobadas |
| PostgreSQL | Configuración, migraciones y servidor local 16.15 | Creado y probado; datos fuera del repositorio |
| Sesión 1: proyecto y captura/transmisión en tiempo real | Django, `cv2.VideoCapture`, MJPEG | Demo HTTP y apertura de cámara real visibles en capturas de Ruth; falta evaluación sistemática |
| Sesión 2: procesamiento, detección y resultados sobre video | YOLO/OpenCV DNN, HOG, MOG2, híbrido; cajas, línea y métricas | Código y pruebas presentes; precisión real pendiente. MOG2 detecta movimiento |
| Sesión 3: interfaz y pruebas | Panel, historial, reportes; 62 pruebas aprobadas sin omisiones | HTTP validado; demo en navegador actualiza las tarjetas tras corrección; faltan casos reales |
| Conteo de personas | Detecciones, seguimiento, cruces | Personas visibles estimadas; no acredita ocupación de toda la sala |
| GitHub | [Rama publicada `docs/labcount-validacion-entrega`](https://github.com/Dmurillog8/conteo-personas-laboratorio/tree/docs/labcount-validacion-entrega) | Pendiente de revisión e integración en `main` |
| README, requirements y exclusión de entorno virtual | Archivos presentes y `.gitignore` | Revisar archivos incluidos antes de publicar |

## Rúbrica suministrada (10 puntos)

| Criterio | Máximo | Material preparado | Pendiente |
|---|---:|---|---|
| Roles y al menos cinco reglas | 2 | [Cinco integrantes y ocho reglas](ROLES_AND_RULES.md) | Revisión y participación efectiva del equipo |
| Tres bocetos completos | 2 | [Acceso, panel e historial](WIREFRAMES.md), PNG/SVG | Incorporar al PDF; confirmar adaptación al tema |
| Al menos tres riesgos con causa, impacto y prevención | 3 | [Nueve riesgos](RISK_MATRIX.md) | Revisar e incorporar al PDF |
| Jira con columnas, asignaciones, capturas y enlace | 3 | [Tablero LAB con 12 tareas](JIRA_BOARD.md) | Añadir capturas y verificar acceso del docente |

La rúbrica menciona pantallas de biblioteca; la guía permite conteo de personas. Se proponen acceso, monitoreo e historial como adaptación. Confirmar con el docente; no se declara esa equivalencia aprobada ni se garantiza calificación.

## Entregables y condiciones

| Requisito | Estado |
|---|---|
| Aplicativo funcional con detección en tiempo real | Ejecución local, cámara real visible en capturas y demo con tarjetas actualizadas; precisión real pendiente |
| PDF usando plantilla del aula | Contenido en `docs/`; ensamblado final y evidencias pendientes |
| Enlace GitHub dentro del PDF | Rama publicada; actualizar el enlace al resultado final tras la integración |
| Video desde computadora, máximo tres minutos, funciones implementadas | Grabación aportada de ~3 min 34 s; recortar o repetir a ≤3 min |
| Video en Drive y permisos correctos | Pendiente; no se proporcionó enlace |
| Participación de todos y plazo | Acreditar participación y consultar plazo en plataforma |
| Trabajo original y fuentes | Reconocer repositorio base y explicar aportes propios |

Los videos de rostros, objetos y manos son recursos de apoyo, no funciones obligatorias del tema elegido.

Consultar [validación](VALIDACION.md), [pruebas](TEST_PLAN.md) y [pasos de entrega](ENTREGA_DOCENTE.md).
