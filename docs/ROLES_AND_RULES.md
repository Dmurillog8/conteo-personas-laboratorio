# Roles y reglas de trabajo · LabCount

Proyecto: **Conteo de personas en el laboratorio** (guía G003-S12).

## 1. Roles del equipo

| Rol | Responsabilidades |
|---|---|
| **Product Owner (PO)** | Define alcance, prioriza historias, valida entregables contra la guía. |
| **Scrum Master** | Facilita ceremonias, elimina bloqueos, cuida el tablero Jira. |
| **Tech Lead / Arquitecto** | Decisiones de stack (Django + OpenCV + PostgreSQL), revisión de PR. |
| **Backend Developer** | Modelos, vistas, servicios (detector, tracker, contador, manager). |
| **Frontend Developer** | Plantillas, CSS, JS, gráficas Canvas, UX responsive. |
| **QA / Tester** | Plan de pruebas, ejecución de suite, validación manual end-to-end. |
| **DevOps** | Docker Compose (PostgreSQL), variables de entorno, despliegue. |
| **Documentador** | README, manuales, matriz de riesgos, trazabilidad. |

En un equipo pequeño una persona puede cubrir varios roles; lo importante es
que cada responsabilidad tenga dueño.

## 2. Reglas de trabajo

### 2.1 Código

1. **Rama principal protegida**: `main` solo recibe cambios vía Pull Request.
2. **Convención de commits**: `tipo(alcance): descripción` (ej.
   `feat(monitoring): agregar snapshot`). Tipos: `feat`, `fix`, `docs`,
   `test`, `refactor`, `chore`, `style`.
3. **Sin secretos en el repo**: `.env` está en `.gitignore`; solo se
   versiona `.env.example`.
4. **Sin entorno virtual**: `.venv/` está ignorado; cada desarrollador crea
   el suyo localmente.
5. **Sin archivos generados**: `media/`, `staticfiles/`, logs y `db.sqlite3`
   no se versionan.
6. **Estilo**: PEP 8 para Python; nombres descriptivos en español para
   dominio (laboratorio, sesión, muestra). Inglés solo para identificadores
   técnicos de Django/OpenCV.
7. **Dependencias**: toda nueva dependencia se agrega a `requirements.txt`
   con versión fijada.
8. **Migraciones**: cada cambio de modelo incluye su migración y se revisa
   en el PR.

### 2.2 Calidad

9. **Pruebas obligatorias**: toda funcionalidad nueva incluye pruebas; la
   suite (`python manage.py test`) debe quedar en verde antes de mergear.
10. **`python manage.py check`** debe pasar sin errores.
11. **Cobertura mínima objetivo**: 70 % en servicios de conteo.
12. **Revisión de código**: al menos un aprobador distinto del autor.

### 2.3 Proceso (Scrum)

13. Sprints de 1 semana; daily de 15 min.
14. Definition of Done: código + pruebas + docs + PR aprobado + demo funcional.
15. El tablero Jira es la fuente de verdad del estado (`docs/JIRA_BOARD.md`).

### 2.4 Seguridad

16. Contraseñas validadas por los validadores estándar de Django (mín. 8
    caracteres).
17. Sesiones y CSRF activos; `XFrameOptionsMiddleware` habilitado.
18. En producción: `DEBUG=False`, `SECRET_KEY` seguro, HTTPS y hosts
    configurados.
19. Las sesiones de monitoreo son propiedad de su creador (staff ve todo).

### 2.5 Comunicación

20. Decisiones de arquitectura se documentan en `docs/ARCHITECTURE.md`.
21. Bloqueos se reportan el mismo día en el daily.
22. Los cambios de alcance se acuerdan con el PO y se reflejan en Jira.