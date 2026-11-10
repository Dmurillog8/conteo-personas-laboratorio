# LabCount Cambios preparados para integrar en GitHub

Fecha de revisión: 9 de noviembre de 2026. Proyecto: Conteo de personas en el laboratorio.

## Estado de publicación

La rama `docs/informe-jira-labcount` reúne todas las correcciones locales descritas aquí y el informe con evidencias Jira. Se creó a partir de `docs/labcount-validacion-entrega`, que ya contenía las correcciones anteriores. `main` conserva la versión original. La publicación de esta rama fue autorizada por Ruth; no se ha solicitado ni realizado su integración en `main`.

## Correcciones del funcionamiento ya incluidas en la rama de revisión

1. **Carga del detector YOLO en Windows.** La lectura del modelo ONNX desde una ruta con tildes podía fallar. `apps/monitoring/services/detectors.py` y `scripts/download_models.py` ahora leen el archivo con Python y entregan sus bytes a OpenCV. Se añadieron casos de prueba para rutas Unicode y archivos corruptos en `apps/monitoring/tests/test_precision.py`.
2. **Indicadores del panel en vivo.** La gráfica ejecutaba una referencia a un método inexistente (`this._draw.bind(this)`), lo que detenía el JavaScript de actualización y dejaba las tarjetas en cero aunque el video mostrara detecciones. Se corrigió `static/js/charts.js` y se actualizó la versión del archivo en `templates/monitoring/dashboard.html` para que el navegador cargue el cambio. La demostración sintética se repitió y las tarjetas mostraron datos variables.
3. **Rótulos que confundían las métricas.** En `apps/monitoring/services/counter.py` y las plantillas se aclaró que se estiman **personas visibles en cámara**, no el total del laboratorio, y que el valor de “únicos” corresponde a identificadores de seguimiento, no a personas distintas. Se ajustó el rótulo de transmisión para que también describa correctamente una fuente sintética. Se retiró de la portada una cifra de precisión sin medición verificable.

## Documentación y evidencia ya incluidas en la rama de revisión

- Se actualizaron `README.md`, manual de uso, arquitectura, integración OpenCV y guía de instalación Windows, incluidos los pasos para PostgreSQL local (`scripts/local_postgres.py`).
- Se incorporaron el informe de la práctica, la lista de entrega docente, la correspondencia con la guía, el plan de pruebas, la validación y el tablero Jira en `docs/`.
- Se documentaron los cinco nombres y roles del equipo para este proyecto, al menos cinco reglas de trabajo, la matriz de riesgos y tres bocetos adaptados a acceso, monitoreo e historial.
- Se guardaron evidencias de la demo sintética, recorrido HTTP y salida de 62 pruebas automatizadas, sin publicar capturas personales de cámara.

## Informe y capturas añadidos a esta rama

- `docs/entrega_local/Informe_LabCount_borrador.docx` y `Informe_LabCount_borrador.pdf`: informe montado sobre la plantilla oficial del docente. Incluye tres capturas Jira en `docs/entrega_local/evidencias_jira/`: tablero, lista de tareas asignadas y resumen. El informe sigue marcado como borrador porque faltan el video de hasta tres minutos con enlace Drive, acceso verificable del docente a Jira y una comparación manual del conteo con personas reales. No debe presentarse como entrega final hasta completar y revisar esos datos.

## Antes de integrar en main

1. Revisar en GitHub la diferencia de la rama `docs/informe-jira-labcount` contra `main` y solicitar la revisión del equipo.
2. Confirmar que el detector funciona en el equipo de exposición y registrar una comparación manual de detecciones y conteos.
3. Confirmar que la documentación corresponde al software y que no hay secretos ni imágenes de personas en los archivos por publicar.
4. Completar las tareas pendientes de Jira, verificar acceso del docente, recortar y compartir el video, y actualizar el PDF final con enlaces accesibles.
5. Solicitar a Ruth autorización antes de integrar esta rama en `main`.
