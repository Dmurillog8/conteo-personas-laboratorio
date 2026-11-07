# Matriz de riesgos · LabCount

Escala: Probabilidad (P) y Impacto (I): 1=bajo, 2=medio, 3=alto.
Prioridad = P × I. Mitigación y plan de contingencia incluidos.

| # | Riesgo | P | I | Prioridad | Mitigación | Contingencia |
|---|---|---|---|---|---|---|
| 1 | PostgreSQL no disponible / conexión fallida | 2 | 3 | 6 | Docker Compose con healthcheck; `.env` documentado; endpoint `/health/` | Usar `DB_ENGINE=sqlite` solo para pruebas locales; restaurar contenedor |
| 2 | Cámara web no accesible o en uso por otra app | 3 | 2 | 6 | Soporte de múltiples backends (DSHOW/MSMF/CAP_ANY); mensajes de error claros | Usar fuente "Demostración" o archivo de video |
| 3 | Video con códec no soportado por OpenCV | 2 | 2 | 4 | Validación de extensión; mensaje de error | Convertir video (ffmpeg) a MP4/H.264 |
| 4 | Falsos positivos/negativos del detector HOG | 3 | 2 | 6 | Modo híbrido (HOG + MOG2); línea de conteo con debounce; demo sintética para presentaciones | Ajustar `LABCOUNT_DETECT_EVERY`, posición de línea, umbral de NMS |
| 5 | Rendimiento insuficiente (FPS bajo) | 2 | 2 | 4 | `LABCOUNT_MAX_FRAME_WIDTH`, detección cada N frames, hilo único | Reducir resolución / FPS; usar detector "motion" |
| 6 | Fuga de memoria / hilo colgado | 2 | 3 | 6 | Hilo daemon; `stop_event`; `close_old_connections()` en persistencia; join con timeout | Reinicio del proceso; reconciliación de sesiones huérfanas al arrancar |
| 7 | Concurrencia en BD desde el hilo de video | 2 | 2 | 4 | `close_old_connections()` antes/después de cada persistencia | Reintentos; revisar pool de conexiones |
| 8 | Exposición de secretos en el repositorio | 1 | 3 | 3 | `.env` en `.gitignore`; `.env.example` sin secretos reales | Rotar `SECRET_KEY` y credenciales de BD |
| 9 | Pérdida de datos por fallo del servidor | 2 | 2 | 4 | Persistencia periódica de muestras y cruces | Exportación CSV; backups de PostgreSQL |
| 10 | Incompatibilidad de versiones de dependencias | 2 | 2 | 4 | `requirements.txt` con versiones fijadas; Python 3.12 probado | Recrear entorno virtual; revisar changelogs |
| 11 | Problemas de permisos/CSRF en producción | 2 | 2 | 4 | `CSRF_TRUSTED_ORIGINS`; documentación de despliegue | Revisar configuración de proxy/hosts |
| 12 | Incumplimiento de la guía (stack/entregables) | 1 | 3 | 3 | Checklist de trazabilidad (`GUIDE_COMPLIANCE.md`); README completo | Ajustar antes de la entrega |
| 13 | Falta de cámara en el aula de presentación | 3 | 2 | 6 | Modo "Demostración" sintética sin hardware | Usar video pregrabado o demo |
| 14 | Tests lentos por BD real | 1 | 1 | 1 | Suite optimizada (~12 s); `SimpleTestCase` donde aplica | Ejecutar subconjuntos con `--pattern` |

Riesgos críticos (prioridad ≥ 6) se revisan en cada sprint.