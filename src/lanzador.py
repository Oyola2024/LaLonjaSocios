import os
import socket
import sys
import threading
import time
import webbrowser
from getpass import getpass
from pathlib import Path

PUERTO = 8765
URL = f'http://127.0.0.1:{PUERTO}/'


def carpeta_datos():
    base = os.environ.get('LOCALAPPDATA') or str(Path.home() / '.lalonja')
    ruta = Path(base) / 'LaLonja'
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


os.environ.setdefault('LALONJA_DATA_DIR', str(carpeta_datos()))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.settings')

import django  # noqa: E402
django.setup()

from django.conf import settings  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.db import connection  # noqa: E402
from django.db.migrations.executor import MigrationExecutor  # noqa: E402
from waitress import serve  # noqa: E402
from settings.wsgi import application  # noqa: E402
from socios import backups  # noqa: E402


def ya_corriendo():
    with socket.socket() as s:
        return s.connect_ex(('127.0.0.1', PUERTO)) == 0


def backups_periodicos():
    while True:
        try:
            backups.backup_si_corresponde()
        except Exception as e:
            print('No se pudo hacer el backup:', e)
        time.sleep(6 * 3600)


def migraciones_pendientes():
    ejecutor = MigrationExecutor(connection)
    return bool(ejecutor.migration_plan(ejecutor.loader.graph.leaf_nodes()))


def crear_primer_usuario():
    User = get_user_model()
    if User.objects.exists():
        return
    print('\n=== Primera vez: crear el usuario de la secretaría ===')
    usuario = input('Usuario: ').strip()
    clave = getpass('Contraseña: ')
    User.objects.create_superuser(username=usuario, password=clave)
    print('Usuario creado.\n')


def main():
    if ya_corriendo():
        webbrowser.open(URL)
        return

    if Path(settings.DATABASES['default']['NAME']).exists():
        # Si hay cambios de base por aplicar, copia de seguridad antes de migrar
        if migraciones_pendientes():
            backups.hacer_backup()
        else:
            backups.backup_si_corresponde()

    call_command('migrate', interactive=False, verbosity=0)
    crear_primer_usuario()

    threading.Thread(target=backups_periodicos, daemon=True).start()
    threading.Timer(1.5, lambda: webbrowser.open(URL)).start()

    print('=' * 50)
    print(' Club La Lonja - Sistema de socios y cuotas')
    print(f' Abierto en {URL}')
    print(' NO CIERRES ESTA VENTANA mientras uses el sistema.')
    print(' Para salir, cerrala.')
    print('=' * 50)
    serve(application, host='127.0.0.1', port=PUERTO, threads=4)


if __name__ == '__main__':
    main()