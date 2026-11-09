# Matriz de riesgos — Conteo de personas en el laboratorio

P e I: 1=bajo, 2=medio, 3=alto. Prioridad=P×I. Responsables de seguimiento según los roles del equipo. Se describen riesgos potenciales, no incidentes ya ocurridos.

| ID | Riesgo | Causa | Impacto en el proyecto | P | I | Prioridad | Acción preventiva | Contingencia | Responsable |
|---|---|---|---|---|---|---|---|---|---|
| R1 | Entrega incompleta | Subestimar pruebas, evidencias y grabación | Pérdida de puntos y atraso | 2 | 3 | 6 | Dividir tareas en Jira, revisar avances y reservar tiempo para validar enlaces | Priorizar requisitos obligatorios y avisar bloqueos | Darlyn Joshua |
| R2 | Error en acceso o interfaz | Validación incompleta o cambios sin revisión | El usuario no puede iniciar el monitoreo | 2 | 2 | 4 | Probar registro/login, campos inválidos y navegación; revisión entre compañeros | Corregir el cambio y repetir el caso fallido | Billy Dilson |
| R3 | Cámara o video no disponible | Cámara ocupada, índice equivocado o códec no compatible | No se puede demostrar captura real | 2 | 3 | 6 | Probar la misma cámara y video antes de grabar; cerrar aplicaciones que la usan | Corregir permisos/índice; usar archivo de respaldo, identificado como grabado | Deyvi Matheus |
| R4 | Base de datos desconectada | Servicio detenido o variables incorrectas | No se guardan sesiones, muestras ni resultados | 2 | 3 | 6 | Verificar PostgreSQL, migraciones y `/health/`; documentar arranque sin publicar secretos | Restablecer servicio/configuración y comprobar persistencia | Ruth Noemi |
| R5 | Conteo incorrecto | Oclusiones, contraluz, movimiento de objetos o pérdida de seguimiento | Resultados distintos del conteo manual | 3 | 3 | 9 | Ensayar escenas reales con conteo manual; ajustar cámara, detector y línea; registrar errores | Documentar limitaciones y repetir pruebas en condiciones controladas | Jorge Alfredo y Deyvi Matheus |
| R6 | Video con retraso | Resolución elevada o CPU insuficiente | Resultados poco fluidos en tiempo real | 2 | 2 | 4 | Medir FPS en el equipo de exposición y ajustar resolución/frecuencia | Reducir carga y repetir la prueba; MOG2 detecta movimiento, no garantiza personas | Deyvi Matheus |
| R7 | Exposición de datos | Publicar `.env`, capturas identificables o enlaces con permisos excesivos | Divulgación de información privada | 2 | 3 | 6 | Revisar archivos antes del push; usar participantes autorizados y permisos de lectura | Retirar la evidencia afectada y cambiar credenciales expuestas | Ruth Noemi y Darlyn Joshua |
| R8 | Falta de evidencia evaluable | Jira solo descrito en Markdown, video sin permisos o PDF sin enlaces | No se puede comprobar la rúbrica | 2 | 3 | 6 | Revisar checklist y abrir enlaces desde una cuenta diferente antes de entregar | Completar tablero, capturas y enlaces funcionales | Darlyn Joshua y Jorge Alfredo |
| R9 | Pérdida de registros | Fallo del equipo o eliminación del directorio de PostgreSQL | Pérdida de sesiones y evidencias | 2 | 2 | 4 | Respaldar base y archivos multimedia antes de cambios de entorno | Restaurar respaldo y repetir validaciones | Darlyn Joshua |

Revisar primero riesgos con prioridad ≥6. La demostración sintética permite verificar el flujo, pero no sustituye la evidencia de detección de personas reales.
