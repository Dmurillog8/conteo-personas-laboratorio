# Entrega al docente — pasos y pendientes

**Tema elegido: Conteo de personas en el laboratorio.** Guía G003-S12 y capturas de la rúbrica proporcionadas por el equipo. Este proyecto es independiente de HemoVision.

## 1. Preparar el proyecto (sesión 1 de la guía)

- Revisar el proyecto Django y su configuración.
- Configurar PostgreSQL y aplicar migraciones siguiendo [instalación](INSTALACION_WINDOWS.md).
- Verificar captura y transmisión de video en tiempo real desde cámara conectada al equipo que ejecuta Django.

## 2. Procesar y contar (sesión 2)

- Usar OpenCV (`cv2`) para leer imágenes/video, detectar personas y mostrar resultados sobre el video.
- Probar detector YOLO, seguimiento y cruces de línea; distinguir detección real de demo sintética.
- Explicar qué se mide: personas visibles, entradas/salidas por línea, identificadores de seguimiento y pico observado.

## 3. Interfaz y pruebas (sesión 3)

- Comprobar inicio de sesión, panel, captura, finalización, historial y reportes.
- Completar los casos de [pruebas manuales](TEST_PLAN.md) con resultado, evidencia y responsable.
- Verificar repositorio con README y requirements; excluir `.env` y entorno virtual.

## 4. Documentar según la rúbrica (10 puntos)

| Criterio | Máximo | Material preparado | Evidencia que debe entregar el equipo |
|---|---:|---|---|
| Roles y reglas | 2 | [Cinco roles y ocho reglas](ROLES_AND_RULES.md) | Incorporar al informe; comprobar responsabilidades con cada integrante |
| Tres bocetos | 2 | [Login, panel, historial](WIREFRAMES.md) | Tres imágenes legibles y sus descripciones |
| Matriz de riesgos | 3 | [Nueve riesgos](RISK_MATRIX.md) | Riesgo, causa, impacto y acción preventiva; incluir matriz en PDF |
| Jira | 3 | [Tablero LAB](JIRA_BOARD.md) con tres columnas y 12 tareas asignadas | Capturas y comprobación de acceso del docente |

La rúbrica menciona login, préstamo y listado de libros, mientras la guía admite este tema. Se adaptaron las tres pantallas a login, conteo e historial. Confirmar esta equivalencia con el docente; no se añadieron funciones de biblioteca. Los videos de rostros/manos/objetos son recursos de apoyo, no funciones obligatorias del tema elegido.

## 5. Grabar el video (máximo 3 minutos)

Grabar desde **computadora**, no desde teléfono. Mostrar las funciones implementadas; ensayar para no exceder 180 segundos. Guion sugerido:

| Tiempo | Contenido |
|---|---|
| 0:00–0:15 | Tema, propósito y equipo |
| 0:15–0:35 | Registro/acceso y panel |
| 0:35–1:35 | Cámara real, detector, línea, entrada/salida, conteo y gráfica; breve muestra de las otras fuentes |
| 1:35–2:05 | Captura, finalizar, historial y detalle |
| 2:05–2:30 | Reportes, filtros y CSV; administración si forma parte de la demostración |
| 2:30–2:50 | PostgreSQL, pruebas, limitaciones del conteo y repositorio |
| 2:50–3:00 | Cierre y participación del equipo |

Subir a Google Drive con permiso de visualización para el docente y probar el enlace. La demo sintética debe identificarse como simulación; no acredita precisión con personas reales.

## 6. Preparar el PDF final

Usar la plantilla de entrega del aula virtual. Completar portada (asignatura, práctica, tema, integrantes, docente, fecha), objetivo, desarrollo, roles/reglas, tres bocetos, matriz de riesgos, tablero Jira, pruebas/resultados, conclusiones, fuentes y enlaces. Los apartados propuestos organizan la evidencia; conservar cualquier sección obligatoria de la plantilla.

| Enlace/evidencia | Estado |
|---|---|
| GitHub | https://github.com/Dmurillog8/conteo-personas-laboratorio — subir y revisar los cambios locales antes de entregar |
| Tablero Jira real | https://proyecto-practico-experimentental.atlassian.net/jira/software/projects/LAB/boards/34?filter=&groupBy=none |
| Capturas del tablero | PENDIENTES |
| Video Google Drive ≤3 minutos | Grabación local de ~3 min 34 s: ajustar duración y subir a Drive |
| Evidencia con personas reales | Capturas de cámara web aportadas; falta comparación manual del conteo |
| PDF en plantilla y revisión de permisos | PENDIENTE |

No sustituir pendientes por enlaces inventados. Todos los integrantes deben participar y estar presentes según la guía. Verificar el plazo en la plataforma; las fechas del documento no acreditan la fecha límite. Reconocer el repositorio base y explicar el aporte del equipo.

## 7. Revisión antes de entregar

- [ ] Docente confirma adaptación de bocetos al tema.
- [ ] Roles y reglas revisados por el equipo.
- [ ] Bocetos y matriz incluidos y legibles.
- [ ] Guardar capturas de Jira y verificar acceso del docente (tablero y asignaciones ya creados).
- [ ] Pruebas manuales reales completadas; resultados sin afirmaciones no comprobadas.
- [ ] Video grabado desde computadora, ≤3 min, Drive accesible.
- [ ] Cambios revisados y publicados en GitHub; README y requirements presentes.
- [ ] PDF final en plantilla con enlaces funcionando.
- [ ] Participación de todos y entrega dentro del plazo.
