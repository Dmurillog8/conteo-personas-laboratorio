# Tablero Jira · LabCount

Proyecto académico. Convención de claves: `LAB-NN`. Estados:
**Backlog → To Do → In Progress → In Review → Done**.

## 1. Épicas

| Clave | Épica | Descripción |
|---|---|---|
| LAB-E1 | Infraestructura y proyecto base | Django, PostgreSQL, Docker, settings, .env |
| LAB-E2 | Motor de conteo OpenCV | Detector, tracker, contador, línea virtual |
| LAB-E3 | Streaming y panel en tiempo real | MJPEG, API stats, dashboard, JS/Canvas |
| LAB-E4 | Persistencia e historial | Sesiones, muestras, cruces, snapshots |
| LAB-E5 | Reportes y exportación | Resumen, CSV, filtros |
| LAB-E6 | Autenticación y administración | Registro, login, permisos, admin |
| LAB-E7 | Calidad y documentación | Pruebas, README, docs, riesgos |

## 2. Historias de usuario (resumen)

### Épica E1
- **LAB-01** Como desarrollador, quiero un proyecto Django configurado con PostgreSQL para tener la base del sistema. (5 pts) — Done
- **LAB-02** Como desarrollador, quiero Docker Compose con PostgreSQL 16 para levantar la BD fácilmente. (3 pts) — Done
- **LAB-03** Como desarrollador, quiero variables de entorno documentadas (.env.example). (2 pts) — Done

### Épica E2
- **LAB-04** Como sistema, quiero detectar personas con HOG de OpenCV. (5 pts) — Done
- **LAB-05** Como sistema, quiero detectar movimiento con MOG2. (3 pts) — Done
- **LAB-06** Como sistema, quiero un modo híbrido HOG+movimiento. (3 pts) — Done
- **LAB-07** Como sistema, quiero seguir personas por centroides. (5 pts) — Done
- **LAB-08** Como sistema, quiero contar cruces de una línea virtual. (5 pts) — Done
- **LAB-09** Como presentador, quiero un modo demo sintético sin hardware. (5 pts) — Done

### Épica E3
- **LAB-10** Como usuario, quiero ver video en vivo anotado en el navegador. (5 pts) — Done
- **LAB-11** Como usuario, quiero ver KPIs en tiempo real (ocupación, entradas, salidas). (3 pts) — Done
- **LAB-12** Como usuario, quiero una gráfica de ocupación en vivo. (3 pts) — Done
- **LAB-13** Como usuario, quiero iniciar/detener el monitoreo desde el panel. (3 pts) — Done

### Épica E4
- **LAB-14** Como usuario, quiero que las sesiones queden guardadas. (3 pts) — Done
- **LAB-15** Como usuario, quiero consultar el historial de sesiones. (3 pts) — Done
- **LAB-16** Como usuario, quiero ver el detalle de una sesión con gráfica. (3 pts) — Done
- **LAB-17** Como usuario, quiero guardar capturas (snapshots). (2 pts) — Done

### Épica E5
- **LAB-18** Como usuario, quiero exportar sesiones a CSV. (2 pts) — Done
- **LAB-19** Como usuario, quiero exportar el detalle de una sesión a CSV. (2 pts) — Done
- **LAB-20** Como usuario, quiero ver reportes agregados. (3 pts) — Done

### Épica E6
- **LAB-21** Como visitante, quiero registrarme e iniciar sesión. (3 pts) — Done
- **LAB-22** Como sistema, quiero que cada usuario vea solo sus sesiones. (3 pts) — Done
- **LAB-23** Como admin, quiero un panel de administración. (2 pts) — Done

### Épica E7
- **LAB-24** Como QA, quiero pruebas automatizadas del contador y tracker. (5 pts) — Done
- **LAB-25** Como QA, quiero pruebas de vistas y modelos. (3 pts) — Done
- **LAB-26** Como documentador, quiero README y docs completos. (5 pts) — Done
- **LAB-27** Como equipo, quiero matriz de riesgos y bocetos. (3 pts) — Done

## 3. Backlog futuro (no incluido en esta entrega)

- LAB-F1 Detección con modelos DNN (YOLO/MobileNet) para mayor precisión.
- LAB-F2 Alertas por aforo máximo (notificación/email).
- LAB-F3 Multi-cámara simultánea.
- LAB-F4 Despliegue en la nube (Docker + gunicorn + nginx).
- LAB-F5 Dashboard con WebSockets (Channels) en lugar de polling.