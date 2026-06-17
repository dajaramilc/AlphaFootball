"""
Alpha Football v0.4 — Guardado y carga en JSON.

Responsabilidad única: persistir y reconstruir el `EstadoJuego` definido en
`alpha_football.models`. No contiene lógica de juego; solo (de)serialización
resiliente sobre disco.

Garantías de resiliencia:
- Escritura ATÓMICA: se escribe a un archivo temporal y luego se reemplaza, para
  que un corte a mitad de guardado nunca corrompa la partida válida anterior.
- BACKUP automático (`.bak`) del guardado previo antes de sobrescribir.
- Carga TOLERANTE: si el archivo principal está corrupto, se intenta el backup
  antes de fallar. Errores no recuperables (no existe ninguna partida) se propagan.
- Metadata de esquema (`SCHEMA_VERSION`) para futuras migraciones.

Distinguimos errores recuperables (archivo corrupto -> usar backup) de los no
recuperables (no hay ninguna partida que cargar -> propagar al llamador).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from alpha_football.models import SCHEMA_VERSION, EstadoJuego

logger = logging.getLogger(__name__)

# Nombre de archivo de guardado por defecto. La UI puede pasar otra ruta para
# soportar múltiples slots de partida.
RUTA_GUARDADO_DEFECTO = "alpha_football_save.json"

# Clave de metadata dentro del JSON. El estado del juego vive bajo "estado".
_CLAVE_VERSION = "schema_version"
_CLAVE_ESTADO = "estado"


class ErrorGuardado(Exception):
    """Error no recuperable al guardar/cargar la partida (sin fallback posible)."""


def _ruta_temporal(ruta: str) -> str:
    return f"{ruta}.tmp"


def _ruta_backup(ruta: str) -> str:
    return f"{ruta}.bak"


def guardar_partida(estado: EstadoJuego, ruta: str = RUTA_GUARDADO_DEFECTO) -> None:
    """
    Guarda el estado completo en `ruta` de forma atómica y con backup.

    Pasos (cada uno protege contra una forma de corrupción):
      1. Serializar a dict y volcar a JSON en un archivo temporal.
      2. Hacer backup del guardado actual (si existe) antes de tocarlo.
      3. Reemplazar atómicamente el archivo final por el temporal.

    Lanza ErrorGuardado solo ante fallos no recuperables (p.ej. directorio sin
    permisos). Una serialización inválida es un bug de datos: se propaga rápido.
    """
    # La serialización no debe fallar si el contrato se respeta; si falla, es un
    # error no recuperable (datos inconsistentes) y debe propagarse, no silenciarse.
    try:
        contenido = {
            _CLAVE_VERSION: SCHEMA_VERSION,
            _CLAVE_ESTADO: estado.to_dict(),
        }
        texto_json = json.dumps(contenido, ensure_ascii=False, indent=2)
    except (TypeError, ValueError) as error:
        logger.error("No se pudo serializar el estado del juego: %s", error, exc_info=True)
        raise ErrorGuardado(f"Estado no serializable: {error}") from error

    ruta_tmp = _ruta_temporal(ruta)
    try:
        # Paso 1: escribir el temporal completo antes de tocar el archivo bueno.
        with open(ruta_tmp, "w", encoding="utf-8") as archivo:
            archivo.write(texto_json)
            archivo.flush()
            os.fsync(archivo.fileno())  # forzamos a disco para que el reemplazo sea seguro

        # Paso 2: respaldar el guardado anterior (recuperable: si no se puede,
        # seguimos; el reemplazo atómico de abajo es la garantía principal).
        if os.path.exists(ruta):
            try:
                os.replace(ruta, _ruta_backup(ruta))
            except OSError as error:
                logger.warning("No se pudo crear backup de '%s': %s", ruta, error)

        # Paso 3: reemplazo atómico del archivo final.
        os.replace(ruta_tmp, ruta)
        logger.info("Partida guardada en '%s' (esquema v%s)", ruta, SCHEMA_VERSION)

    except OSError as error:
        # Error no recuperable de E/S: limpiamos el temporal y propagamos.
        logger.error("Fallo de E/S al guardar en '%s': %s", ruta, error, exc_info=True)
        _eliminar_silencioso(ruta_tmp)
        raise ErrorGuardado(f"No se pudo guardar en '{ruta}': {error}") from error


def cargar_partida(ruta: str = RUTA_GUARDADO_DEFECTO) -> EstadoJuego:
    """
    Carga el estado desde `ruta`, con fallback al backup `.bak` si el principal
    está corrupto.

    Cascada de fallbacks (solo para corrupción, error recuperable):
      1. Intentar el archivo principal.
      2. Si está corrupto, intentar el backup `.bak`.
    Si no existe ninguna partida (ni principal ni backup), es un error no
    recuperable y se lanza ErrorGuardado para que el llamador inicie partida nueva.
    """
    # Intento 1: archivo principal.
    if os.path.exists(ruta):
        try:
            return _leer_estado(ruta)
        except (OSError, ValueError) as error:
            logger.warning(
                "Guardado principal '%s' ilegible, intentando backup: %s", ruta, error
            )

    # Intento 2: backup.
    ruta_bak = _ruta_backup(ruta)
    if os.path.exists(ruta_bak):
        try:
            estado = _leer_estado(ruta_bak)
            logger.info("Partida recuperada desde backup '%s'", ruta_bak)
            return estado
        except (OSError, ValueError) as error:
            logger.error("Backup '%s' también ilegible: %s", ruta_bak, error)

    # Sin fallback posible: no hay partida válida que cargar.
    raise ErrorGuardado(f"No existe una partida válida en '{ruta}' ni en su backup")


def existe_partida(ruta: str = RUTA_GUARDADO_DEFECTO) -> bool:
    """True si hay un guardado principal o un backup disponible para cargar."""
    return os.path.exists(ruta) or os.path.exists(_ruta_backup(ruta))


def _leer_estado(ruta: str) -> EstadoJuego:
    """
    Lee y reconstruye un EstadoJuego desde un archivo concreto.

    Lanza ValueError si el JSON está corrupto o no respeta el contrato (lo trata
    cargar_partida como recuperable para pasar al siguiente fallback).
    """
    with open(ruta, "r", encoding="utf-8") as archivo:
        contenido: dict[str, Any] = json.load(archivo)

    if not isinstance(contenido, dict) or _CLAVE_ESTADO not in contenido:
        raise ValueError(f"Formato de guardado inválido en '{ruta}'")

    version = contenido.get(_CLAVE_VERSION)
    if version != SCHEMA_VERSION:
        # No bloqueamos por versión distinta: el modelo reconstruye de forma
        # tolerante (campos faltantes -> valores por defecto). Solo avisamos.
        logger.warning(
            "Guardado '%s' tiene esquema v%s; el actual es v%s. Cargando tolerante.",
            ruta, version, SCHEMA_VERSION,
        )

    return EstadoJuego.from_dict(contenido[_CLAVE_ESTADO])


def _eliminar_silencioso(ruta: str) -> None:
    """Borra un archivo si existe, sin romper el flujo si el borrado falla."""
    try:
        if os.path.exists(ruta):
            os.remove(ruta)
    except OSError as error:
        logger.warning("No se pudo eliminar el archivo temporal '%s': %s", ruta, error)
