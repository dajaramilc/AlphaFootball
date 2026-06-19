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

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from alpha_football.models import SCHEMA_VERSION, EstadoJuego

logger = logging.getLogger(__name__)

# Nombre de archivo de guardado por defecto. La UI puede pasar otra ruta para
# soportar múltiples slots de partida.
RUTA_GUARDADO_DEFECTO = "alpha_football_save.json"

# Carpeta y cantidad de slots de la persistencia multislot (Fase 2).
CARPETA_SLOTS = "saves"
TOTAL_SLOTS = 5

# Clave de metadata dentro del JSON. El estado del juego vive bajo "estado".
_CLAVE_VERSION = "schema_version"
_CLAVE_ESTADO = "estado"
# Integridad del guardado (Fase 2): firma y checksum para detectar corrupción/manipulación.
_MAGIC = "ALPHAFB"
_CLAVE_MAGIC = "magic"
_CLAVE_CHECKSUM = "checksum"
_CLAVE_META = "meta"  # cabecera de visualización del slot (no entra en el checksum)


def _checksum(estado_dict: dict) -> str:
    """SHA-256 del bloque de estado (orden estable) para validar integridad."""
    serial = json.dumps(estado_dict, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(serial.encode("utf-8")).hexdigest()


class ErrorGuardado(Exception):
    """Error no recuperable al guardar/cargar la partida (sin fallback posible)."""


def _ruta_temporal(ruta: str) -> str:
    return f"{ruta}.tmp"


def _ruta_backup(ruta: str) -> str:
    return f"{ruta}.bak"


def guardar_partida(estado: EstadoJuego, ruta: str = RUTA_GUARDADO_DEFECTO,
                    meta: Optional[dict] = None) -> None:
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
        estado_dict = estado.to_dict()
        contenido = {
            _CLAVE_MAGIC: _MAGIC,
            _CLAVE_VERSION: SCHEMA_VERSION,
            _CLAVE_CHECKSUM: _checksum(estado_dict),
            _CLAVE_ESTADO: estado_dict,
        }
        if meta:
            contenido[_CLAVE_META] = meta
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

    # Integridad (Fase 2): si el guardado trae firma/checksum, validarlos. Si no los
    # trae (saves viejos), se carga tolerante. Un fallo aquí es ValueError -> recuperable
    # (cargar_partida intenta el .bak).
    magic = contenido.get(_CLAVE_MAGIC)
    if magic is not None and magic != _MAGIC:
        raise ValueError(f"Firma inválida en '{ruta}' (esperado '{_MAGIC}', vino '{magic}')")

    estado_dict = contenido[_CLAVE_ESTADO]
    checksum_guardado = contenido.get(_CLAVE_CHECKSUM)
    if checksum_guardado is not None and _checksum(estado_dict) != checksum_guardado:
        raise ValueError(f"Checksum no coincide en '{ruta}': el guardado pudo corromperse o alterarse")

    version = contenido.get(_CLAVE_VERSION)
    if version != SCHEMA_VERSION:
        # No bloqueamos por versión distinta: el modelo reconstruye de forma
        # tolerante (campos faltantes -> valores por defecto). Solo avisamos.
        logger.warning(
            "Guardado '%s' tiene esquema v%s; el actual es v%s. Cargando tolerante.",
            ruta, version, SCHEMA_VERSION,
        )

    return EstadoJuego.from_dict(estado_dict)


def _eliminar_silencioso(ruta: str) -> None:
    """Borra un archivo si existe, sin romper el flujo si el borrado falla."""
    try:
        if os.path.exists(ruta):
            os.remove(ruta)
    except OSError as error:
        logger.warning("No se pudo eliminar el archivo temporal '%s': %s", ruta, error)


# --- Persistencia multislot (Fase 2) ------------------------------------------
# La UI elige el slot (1..TOTAL_SLOTS); aquí solo se gestiona el almacenamiento.

def ruta_slot(n: int, carpeta: str = CARPETA_SLOTS) -> str:
    """Ruta del archivo de un slot: <carpeta>/slot_<n>.json."""
    return os.path.join(carpeta, f"slot_{int(n)}.json")


def _construir_meta(estado: EstadoJuego, nombre_partida: str) -> dict:
    """Cabecera de visualización del slot (no entra en el checksum del estado)."""
    equipo = estado.equipo_usuario()
    liga = estado.liga_por_id(estado.liga_usuario_id) if estado.liga_usuario_id else None
    return {
        "nombre_partida": str(nombre_partida or "Partida sin nombre"),
        "fecha_guardado": datetime.now(timezone.utc).isoformat(),
        "equipo_nombre": getattr(equipo, "nombre", "—") if equipo else "—",
        "temporada": int(getattr(estado, "temporada", 1)),
        "jornada": int(getattr(liga, "jornada_actual", 1)) if liga else 1,
        "presupuesto": int(getattr(equipo, "balance", 0)) if equipo else 0,
    }


def guardar_en_slot(estado: EstadoJuego, n: int, nombre_partida: str,
                    carpeta: str = CARPETA_SLOTS) -> None:
    """Guarda el estado en el slot n con su cabecera de visualización (atómico + checksum)."""
    os.makedirs(carpeta, exist_ok=True)
    meta = _construir_meta(estado, nombre_partida)
    guardar_partida(estado, ruta_slot(n, carpeta), meta=meta)


def cargar_slot(n: int, carpeta: str = CARPETA_SLOTS) -> EstadoJuego:
    """Carga el estado de un slot (con la misma cascada de fallback al .bak)."""
    return cargar_partida(ruta_slot(n, carpeta))


def leer_cabecera_slot(n: int, carpeta: str = CARPETA_SLOTS) -> Optional[dict]:
    """
    Lee SOLO la cabecera (meta) de un slot para listarlo en la UI sin reconstruir todo
    el estado. Devuelve None si el slot está libre o ilegible.
    """
    ruta = ruta_slot(n, carpeta)
    if not os.path.exists(ruta):
        return None
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            contenido = json.load(archivo)
        if not isinstance(contenido, dict):
            return None
        meta = contenido.get(_CLAVE_META) or {}
        meta.setdefault("nombre_partida", "Partida")
        return meta
    except (OSError, ValueError) as error:
        logger.warning("No se pudo leer la cabecera del slot %s: %s", n, error)
        return None


def listar_slots(carpeta: str = CARPETA_SLOTS, total: int = TOTAL_SLOTS) -> list:
    """
    Devuelve una lista de longitud `total`; cada elemento es la cabecera del slot
    (dict) o None si está libre. Pensado para pintar el menú Cargar/Guardar.
    """
    return [leer_cabecera_slot(n, carpeta) for n in range(1, total + 1)]


def eliminar_slot(n: int, carpeta: str = CARPETA_SLOTS) -> None:
    """
    Elimina físicamente los archivos correspondientes al slot n y su backup (.bak).
    Funciona de forma resiliente y fail-soft.
    """
    try:
        ruta = ruta_slot(n, carpeta)
        ruta_bak = _ruta_backup(ruta)
        
        # Eliminar de forma segura
        _eliminar_silencioso(ruta)
        _eliminar_silencioso(ruta_bak)
        logger.info(f"Slot de guardado {n} y su backup eliminados de forma física.")
    except Exception as e:
        logger.error(f"Error al eliminar slot {n} de la carpeta {carpeta}: {e}")

