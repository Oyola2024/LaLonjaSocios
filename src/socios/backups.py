import shutil
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings


def _carpeta():
    carpeta = Path(settings.BACKUP_DIR)
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


def listar():
    return sorted(_carpeta().glob('lalonja-*.sqlite3'))


def hacer_backup():
    origen = Path(settings.DATABASES['default']['NAME'])
    destino = _carpeta() / f"lalonja-{datetime.now():%Y-%m-%d_%H%M%S}.sqlite3"
    with closing(sqlite3.connect(origen)) as src, closing(sqlite3.connect(destino)) as dst:
        src.backup(dst)

    # Segunda copia fuera de la PC (pendrive o carpeta sincronizada con Drive)
    extra = getattr(settings, 'BACKUP_EXTRA_DIR', None)
    if extra and Path(extra).is_dir():
        shutil.copy2(destino, Path(extra) / destino.name)

    # Conservar solo los últimos N
    for viejo in listar()[:-settings.BACKUP_CONSERVAR]:
        viejo.unlink(missing_ok=True)
    return destino


def backup_si_corresponde(horas=24):
    copias = listar()
    if copias:
        ultima = datetime.fromtimestamp(copias[-1].stat().st_mtime)
        if datetime.now() - ultima < timedelta(hours=horas):
            return None
    return hacer_backup()