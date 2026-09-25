# -*- coding: utf-8 -*-
"""
v3.7.0: registro central de países y ligas (8 países × 1ª/2ª = 16 ligas).

Reemplaza las listas fijas de ligas que estaban repartidas por el código (menu, market,
plantilla, copa, premios, negociación...). Todo lo que necesite "qué ligas hay", "de qué
región es" o "cómo se llama" lee de acá.
"""
from __future__ import annotations

import importlib
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# v3.7.0: orden de la grilla del alta. Los nombres de las ligas que ya existían se conservan.
PAISES = [
    {'codigo': 'inglaterra', 'nombre': 'Inglaterra', 'liga_id': 'premier', 'emoji': 'EN', 'region': 'europa',
     'liga': 'Premier League Parodia', 'liga_2a': 'Premier League Parodia - Championship', 'corto': 'ING'},
    {'codigo': 'espana', 'nombre': 'España', 'liga_id': 'laliga', 'emoji': 'ES', 'region': 'europa',
     'liga': 'LaLiga EA Sports Parodia', 'liga_2a': 'LaLiga EA Sports Parodia - Segunda División', 'corto': 'ESP'},
    {'codigo': 'italia', 'nombre': 'Italia', 'liga_id': 'seriea', 'emoji': 'IT', 'region': 'europa',
     'liga': 'Serie A Parodia', 'liga_2a': 'Serie B Parodia', 'corto': 'ITA'},
    {'codigo': 'brasil', 'nombre': 'Brasil', 'liga_id': 'brasil', 'emoji': 'BR', 'region': 'sudamerica',
     'liga': 'Brasileirao Parodia', 'liga_2a': 'Brasileirao Parodia - Série B', 'corto': 'BRA'},
    {'codigo': 'argentina', 'nombre': 'Argentina', 'liga_id': 'argentina', 'emoji': 'AR', 'region': 'sudamerica',
     'liga': 'Liga Profesional Argentina Parodia',
     'liga_2a': 'Liga Profesional Argentina Parodia - Primera Nacional', 'corto': 'ARG'},
    {'codigo': 'colombia', 'nombre': 'Colombia', 'liga_id': 'betplay', 'emoji': 'CO', 'region': 'sudamerica',
     'liga': 'Liga BetPlay Dimayor Parodia', 'liga_2a': 'Liga BetPlay Dimayor Parodia - Segunda División',
     'corto': 'COL'},
    {'codigo': 'uruguay', 'nombre': 'Uruguay', 'liga_id': 'uruguay', 'emoji': 'UY', 'region': 'sudamerica',
     'liga': 'Liga AUF Uruguaya Parodia', 'liga_2a': 'Segunda AUF Parodia', 'corto': 'URU'},
    {'codigo': 'ecuador', 'nombre': 'Ecuador', 'liga_id': 'ecuador', 'emoji': 'EC', 'region': 'sudamerica',
     'liga': 'LigaPro Ecuador Parodia', 'liga_2a': 'LigaPro Serie B Parodia', 'corto': 'ECU'},
]
TIPOS_LIGA = tuple(p['liga_id'] for p in PAISES)
EUROPA = tuple(p['liga_id'] for p in PAISES if p['region'] == 'europa')
SUDAMERICA = tuple(p['liga_id'] for p in PAISES if p['region'] == 'sudamerica')
EQUIPOS_POR_LIGA = 12

_POR_TIPO = {p['liga_id']: p for p in PAISES}
_POR_CODIGO = {p['codigo']: p for p in PAISES}


def num_jornadas(n_equipos: int) -> int:
    """Ida y vuelta: 2·(n−1) jornadas (12 equipos → 22)."""
    try:
        return max(2, 2 * (int(n_equipos) - 1))
    except Exception:
        return 2


def pais_de(tipo: str) -> Optional[dict]:
    """País por liga_id ('seriea') o por código ('italia'); None si no existe."""
    return _POR_TIPO.get(str(tipo or '')) or _POR_CODIGO.get(str(tipo or ''))


def es_europa(tipo: str) -> bool:
    return tipo in EUROPA or tipo == 'champions'


def es_sudamerica(tipo: str) -> bool:
    return tipo in SUDAMERICA or tipo == 'libertadores'


RUTA_DB_EDITADA = "alpha_football_edited_db.json"
MAX_NOMBRE_LIGA = 40
_cache_overrides: dict = {'mtime': None, 'ligas': {}}


def _overrides() -> dict:
    """
    v3.7.0: nombres de liga puestos en el editor ("_ligas" de la base editada). Se cachea por
    mtime del archivo: las pantallas lo consultan en cada frame y la base pesa varios MB.
    """
    import json
    import os
    try:
        if not os.path.exists(RUTA_DB_EDITADA):
            _cache_overrides.update(mtime=None, ligas={})
            return {}
        mtime = os.path.getmtime(RUTA_DB_EDITADA)
        if _cache_overrides['mtime'] != mtime:
            with open(RUTA_DB_EDITADA, 'r', encoding='utf-8') as f:
                db = json.load(f)
            ligas = db.get('_ligas') if isinstance(db, dict) else None
            _cache_overrides.update(mtime=mtime, ligas=ligas if isinstance(ligas, dict) else {})
        return _cache_overrides['ligas']
    except Exception as e_ov:
        logger.error(f"No se pudieron leer los nombres de liga editados: {e_ov}")
        return {}


def nombre_liga_defecto(tipo: str, division: int = 1) -> str:
    p = pais_de(tipo)
    if not p:
        return f"Liga {str(tipo).upper()} Parodia"
    return p['liga_2a'] if int(division or 1) == 2 else p['liga']


def nombre_liga(tipo: str, division: int = 1) -> str:
    """Nombre de la liga: el del editor (v3.7.0) si existe, si no el del registro."""
    p = pais_de(tipo)
    if p:
        campo = 'nombre_2a' if int(division or 1) == 2 else 'nombre'
        propio = str((_overrides().get(p['liga_id']) or {}).get(campo) or '').strip()
        if propio:
            return propio[:MAX_NOMBRE_LIGA]
    return nombre_liga_defecto(tipo, division)


def fijar_nombre_en_db(db: dict, tipo: str, division: int, nombre: str) -> None:
    """v3.7.0: escribe (o borra, si queda vacío) el nombre de liga en un dict de base editada."""
    p = pais_de(tipo)
    if not p or not isinstance(db, dict):
        return
    campo = 'nombre_2a' if int(division or 1) == 2 else 'nombre'
    nombre = str(nombre or '')[:MAX_NOMBRE_LIGA]
    ligas = db.setdefault('_ligas', {})
    entrada = ligas.setdefault(p['liga_id'], {})
    if nombre.strip():
        entrada[campo] = nombre
    else:
        entrada.pop(campo, None)
        if not entrada:
            ligas.pop(p['liga_id'], None)


def renombrar_liga(tipo: str, division: int, nombre: str) -> None:
    """
    v3.7.0: renombra la liga (1ª o 2ª) y lo persiste en "_ligas" de la base editada
    (se trunca a 40 caracteres; vacío = vuelve al nombre por defecto).
    """
    import json
    import os
    try:
        db = {}
        if os.path.exists(RUTA_DB_EDITADA):
            with open(RUTA_DB_EDITADA, 'r', encoding='utf-8') as f:
                db = json.load(f)
            if not isinstance(db, dict):
                db = {}
        fijar_nombre_en_db(db, tipo, division, nombre)
        with open(RUTA_DB_EDITADA, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        _cache_overrides['mtime'] = None
    except Exception as e_ren:
        logger.error(f"No se pudo renombrar la liga {tipo} ({division}ª): {e_ren}")


def clave_db(tipo: str, division: int = 1) -> str:
    """v3.7.0: clave de la liga en alpha_football_edited_db.json ('premier' / 'segunda_premier')."""
    return f"segunda_{tipo}" if int(division or 1) == 2 else str(tipo)


def cargar_datos_liga(tipo: str, division: int = 1) -> Optional[Any]:
    """
    Liga cruda desde data/<tipo>.py o data/segunda_<tipo>.py (sin post-procesos).
    None si el país todavía no tiene datos (módulo inexistente) o la liga viene vacía.
    """
    if tipo not in TIPOS_LIGA:
        return None
    modulo = f"alpha_football.data.{'segunda_' if int(division or 1) == 2 else ''}{tipo}"
    try:
        mod = importlib.import_module(modulo)
    except ModuleNotFoundError as e_mod:
        if getattr(e_mod, 'name', '') == modulo:
            return None   # v3.7.0: país sin datos todavía → sin liga (no un mock)
        raise
    liga = mod.get_liga()
    if liga is None or not getattr(liga, 'equipos', None):
        return None
    liga.num_jornadas = num_jornadas(len(liga.equipos))
    liga.nombre = nombre_liga(tipo, division)   # v3.7.0: nombre del registro (o el del editor)
    return liga


def completar_ligas(estado: dict) -> None:
    """
    v3.7.0: migración de partidas (se llama al empezar cada temporada; idempotente).
    - Carga los países/divisiones que falten (saves de 5 países → 8).
    - Completa cada liga hasta 12 con clubes de los datos que no estén en NINGUNA liga
      (primero de su división, después de la otra del país).
    - Fija num_jornadas = 2·(n−1); a las ligas cambiadas les vacía el calendario (se regenera).
    - Clásicos, DTs de la IA, contratos (los valores ya vienen de la carga).
    """
    try:
        from alpha_football.ui import menu as _menu
    except Exception as e_imp:
        logger.error(f"completar_ligas: no se pudo importar el menú: {e_imp}")
        return
    primeras = estado.setdefault('primera_division', {})
    segunda = estado.setdefault('segunda_division', {})
    mapas = {1: primeras, 2: segunda}
    cache: dict = {}

    def _cargada(tipo, div):
        if (tipo, div) not in cache:
            try:
                cache[(tipo, div)] = (_menu.load_league_teams(tipo) if div == 1
                                      else _menu.load_division_teams(tipo, 2))
            except Exception as e_load:
                logger.error(f"completar_ligas: no se pudo cargar {tipo} ({div}ª): {e_load}")
                cache[(tipo, div)] = None
        return cache[(tipo, div)]

    def _usados() -> set:
        return {eq.nombre for m in mapas.values() for l in m.values() if l is not None
                for eq in getattr(l, 'equipos', []) or []}

    cambiadas = []
    try:
        # 1. Países / divisiones que faltan en la partida.
        for tipo in TIPOS_LIGA:
            for div, mapa in mapas.items():
                if mapa.get(tipo) is not None:
                    continue
                liga = _cargada(tipo, div)
                if liga is None:
                    continue
                cache.pop((tipo, div), None)   # el objeto pasa a ser la liga viva, no una fuente
                usados = _usados()
                liga.equipos = [eq for eq in liga.equipos if eq.nombre not in usados]
                liga.division = div
                mapa[tipo] = liga
                cambiadas.append(liga)
                logger.info(f"completar_ligas: se agregó {tipo} ({div}ª) con {len(liga.equipos)} clubes")
        # 2. Completar hasta 12 y fijar las jornadas.
        for tipo in TIPOS_LIGA:
            for div, mapa in mapas.items():
                liga = mapa.get(tipo)
                if liga is None:
                    continue
                if len(liga.equipos) < EQUIPOS_POR_LIGA:
                    usados = _usados()
                    for fuente_div in (div, 3 - div):
                        fuente = _cargada(tipo, fuente_div)
                        for eq in (getattr(fuente, 'equipos', None) or []):
                            if len(liga.equipos) >= EQUIPOS_POR_LIGA:
                                break
                            if eq.nombre not in usados:
                                usados.add(eq.nombre)
                                liga.equipos.append(eq)   # en el sitio: estado['equipos'] sigue apuntando
                    if liga not in cambiadas:
                        cambiadas.append(liga)
                for eq in liga.equipos:
                    eq.division = div
                n_j = num_jornadas(len(liga.equipos))
                if getattr(liga, 'num_jornadas', None) != n_j:
                    liga.num_jornadas = n_j
                    if liga not in cambiadas:
                        cambiadas.append(liga)
        for liga in cambiadas:
            liga.calendario = []
            liga.jornada_actual = 1
    except Exception as e_comp:
        logger.error(f"completar_ligas: error completando ligas: {e_comp}")
    try:
        _menu.sincronizar_nombres_ligas(primeras, segunda)
    except Exception as e_nom:
        logger.error(f"completar_ligas: no se pudieron sincronizar los nombres: {e_nom}")
    if not cambiadas:
        return
    try:
        from alpha_football.data.clasicos import asignar_rivales
        asignar_rivales([eq for m in mapas.values() for l in m.values() if l is not None for eq in l.equipos])
    except Exception as e_cl:
        logger.error(f"completar_ligas: no se pudieron asignar los clásicos: {e_cl}")
    try:
        from alpha_football.entrenadores import asegurar_dts
        asegurar_dts(estado)
    except Exception as e_dt:
        logger.error(f"completar_ligas: no se pudieron asignar los DTs: {e_dt}")
    try:
        from alpha_football.finanzas import asegurar_contratos
        asegurar_contratos(estado)
    except Exception as e_ct:
        logger.error(f"completar_ligas: no se pudieron asegurar los contratos: {e_ct}")
    estado.pop('_pool_internacional', None)
    logger.info(f"completar_ligas: {len(cambiadas)} ligas migradas a {EQUIPOS_POR_LIGA} equipos")
