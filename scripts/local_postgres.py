"""Controla la instalación local de PostgreSQL preparada para LabCount en Windows."""
from pathlib import Path
import argparse
import os
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "status", "stop"])
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("Este auxiliar es para Windows; use su servicio PostgreSQL o Docker.")
    root = Path(os.environ["LOCALAPPDATA"]) / "LabCount" / "postgresql16"
    pg_ctl = root / "pgsql" / "bin" / "pg_ctl.exe"
    data = root / "data"
    if not pg_ctl.is_file() or not (data / "PG_VERSION").is_file():
        print("Instalación local no encontrada. Consulte docs/INSTALACION_WINDOWS.md.")
        return 1
    flags = subprocess.CREATE_NO_WINDOW
    status = subprocess.run([str(pg_ctl), "-D", str(data), "status"],
                            capture_output=True, creationflags=flags)
    if args.action == "status":
        print("PostgreSQL de LabCount está activo." if status.returncode == 0 else "PostgreSQL de LabCount está detenido.")
        return status.returncode
    if args.action == "start" and status.returncode == 0:
        print("PostgreSQL de LabCount ya está activo.")
        return 0
    if args.action == "stop" and status.returncode == 3:
        print("PostgreSQL de LabCount ya está detenido.")
        return 0
    command = [str(pg_ctl), "-D", str(data), "-w"]
    if args.action == "start":
        command += ["-l", str(root / "server.log"), "start"]
    else:
        command += ["-m", "fast", "stop"]
    # Evita que el servidor en segundo plano mantenga abiertas las tuberías del padre.
    result = subprocess.run(command, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, creationflags=flags)
    if result.returncode:
        print(f"No se completó la operación. Consulte {root / 'server.log'}.")
    else:
        print("PostgreSQL de LabCount iniciado." if args.action == "start" else "PostgreSQL de LabCount detenido.")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
