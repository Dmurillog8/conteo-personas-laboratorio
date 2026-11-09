# Instalación y arranque en Windows

## En el equipo de Ruth (configuración preparada)

PostgreSQL 16.15 está instalado en `%LOCALAPPDATA%/LabCount/postgresql16`, fuera de Git. Base `conteo_lab`, servidor `127.0.0.1:5432`. Se conservaron las variables de `.env`. El usuario de la aplicación no es superusuario; tiene CREATEDB para las bases temporales de pruebas. SQL Server Management Studio no administra este servidor; pgAdmin es opcional.

Abrir la carpeta del proyecto en VS Code y usar su terminal:

```powershell
python scripts/local_postgres.py start
python manage.py migrate
python manage.py runserver --noreload
```

- `start`: inicia solo PostgreSQL de LabCount; si está activo, no inicia otro.
- `migrate`: aplica las tablas/migraciones pendientes; puede repetirse.
- `runserver --noreload`: sirve la web para uso local; mantiene un proceso para el motor de video.

Abrir http://127.0.0.1:8000/ y registrarse. Si se habilitó el usuario demo, usar las credenciales de demostración del README. No es una cuenta administradora.

Para cerrar: finalizar el monitoreo en la web, detener Django con Ctrl+C y ejecutar:

```powershell
python scripts/local_postgres.py stop
```

Esto detiene el servidor y conserva los datos. Después de reiniciar Windows, repetir `start`. Consultar estado con `python scripts/local_postgres.py status`. No borrar la carpeta `data`.

## En otro equipo (primera instalación)

1. Instalar Python compatible con `requirements.txt` y Git.
2. Descargar/clonar el proyecto y entrar a su carpeta:

```powershell
git clone https://github.com/Dmurillog8/conteo-personas-laboratorio.git
cd conteo-personas-laboratorio
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`clone` descarga; `cd` entra; `venv` crea un entorno local; `pip install` instala dependencias. El entorno se ignora en Git.

3. Crear `.env` solo si no existe y completar sus variables sin publicar credenciales:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

4. Elegir **una** opción PostgreSQL:
   - Con Docker Desktop instalado y activo: `docker compose up -d db`. Crea/inicia el servicio de `docker-compose.yml`; si el puerto 5432 está ocupado, ajustar `DB_PORT` antes del arranque.
   - Con PostgreSQL instalado: crear una base y un usuario propietario; ajustar `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` y `DB_PORT` en `.env`. Para las pruebas Django el usuario necesita CREATEDB o una base de pruebas preparada por el administrador.

La instalación local de Ruth no se incluye en el repositorio y `local_postgres.py` no la descarga en otros equipos. Obtener PostgreSQL desde https://www.postgresql.org/download/windows/ (instalador o binarios EDB).

5. Aplicar migraciones y verificar:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test --noinput
.\.venv\Scripts\python.exe manage.py runserver --noreload
```

`check` verifica configuración; `test` ejecuta casos en una base temporal separada. No usar SQLite como sustituto de PostgreSQL en la entrega.

6. Registrar una cuenta desde la web. Opcional para práctica local:

```powershell
python manage.py seed_demo --with-user
```

Crea/actualiza `demo / Demo12345!`. `--with-history` añade datos inventados que no deben presentarse como evidencia de conteo real. Usar `createsuperuser` únicamente si se necesita administración.

## Diagnóstico

- `/health/` debe indicar `database: ok` y una versión de OpenCV.
- Si PostgreSQL no conecta, revisar estado y variables; no iniciar Docker en el mismo puerto que el servidor local.
- Si el modelo falta, ejecutar `python scripts/download_models.py` y verificar su carga. Se admite la ruta con tildes.
- Cámara web se refiere a la cámara del equipo que ejecuta Django, no a cualquier navegador remoto.
- El servidor de desarrollo es local. Un despliegue público requiere configuración adicional.
