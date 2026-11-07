# Manual de usuario · LabCount

## 1. Acceso

1. Abra el navegador en `http://127.0.0.1:8000/` (o la URL de despliegue).
2. Si no tiene cuenta, pulse **Registrarse** y complete el formulario.
3. Inicie sesión con su usuario y contraseña.
4. Credenciales demo (si se ejecutó `seed_demo --with-user`):
   **demo / Demo12345!**.

## 2. Panel de monitoreo

1. Seleccione la **fuente de video**:
   - *Cámara web*: indique el número de cámara (0 por defecto).
   - *Archivo de video*: suba un archivo MP4/AVI/MOV/MKV/WEBM (≤ 250 MB).
   - *Demostración*: escena sintética (recomendada para presentaciones).
2. Seleccione el **método de detección**: HOG (personas), Movimiento (MOG2)
   o Híbrido. En modo demo se usa el detector sintético.
3. Configure la **línea de conteo**: orientación (vertical/horizontal) y
   posición (0.1–0.9). La línea divide entradas (lado positivo) de salidas.
4. Pulse **Iniciar monitoreo**. El video anotado aparece en vivo.
5. Observe los KPIs: en laboratorio, entradas, salidas, únicos, pico, FPS.
6. La gráfica de ocupación se actualiza automáticamente.
7. Pulse **Capturar** para guardar un snapshot.
8. Pulse **Finalizar** para cerrar la sesión (se guardan muestras y cruces).

## 3. Historial de sesiones

- Menú **Sesiones**: listado paginado con filtros por estado y búsqueda.
- Pulse una fila para ver el **detalle**: KPIs, gráfica de ocupación, eventos
  de cruce y capturas.
- Exporte una sesión a CSV desde el detalle o todas desde Reportes.

## 4. Reportes

- Menú **Reportes**: resumen agregado (sesiones, entradas, salidas, únicos,
  pico medio).
- Exportar sesiones (CSV, últimos 30 días por defecto).
- Exportar una sesión específica (CSV con muestras y cruces).

## 5. Administración

- `/admin/` (requiere superusuario): gestión de laboratorios, sesiones,
  usuarios, capturas.

## 6. Solución de problemas

| Problema | Acción |
|---|---|
| "No se pudo abrir la fuente" | Verifique la cámara/archivo; use modo Demo. |
| BD no conecta | `docker compose up -d`; revise `.env`. |
| FPS bajo | Reduzca `LABCOUNT_MAX_FRAME_WIDTH` o use detector "motion". |
| Sesión huérfana tras reinicio | Se reconcilia automáticamente al abrir el panel. |
| Error de CSRF | Revise `CSRF_TRUSTED_ORIGINS` y `ALLOWED_HOSTS`. |

## 7. Atajos

- Panel: `/monitoring/`
- Sesiones: `/monitoring/sessions/`
- Reportes: `/reports/`
- Salud: `/health/`
- Admin: `/admin/`