# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Nombres únicos de jugadores (v4.4.0)
Registro de los nombres completos en uso para que los jugadores generados (suplentes de
relleno, reemplazos, agentes libres, regens) no repitan nombre. `desduplicar(estado)` corre
al crear o cargar una carrera: arma el registro y renombra los repetidos (se queda el primero).
"""
from __future__ import annotations

import logging
import random
from typing import Optional

logger = logging.getLogger(__name__)

_USADOS: set = set()


def _clave(nombre: str, apellido: str) -> str:
    return f"{nombre} {apellido}".strip().lower()


def _pools(pais: str, rng) -> tuple:
    """(nombres, apellidos) del país; sin país conocido, los de un país al azar (no mezcla)."""
    from alpha_football.retiros import NOMBRES_POR_PAIS
    return NOMBRES_POR_PAIS.get(pais) or NOMBRES_POR_PAIS[rng.choice(sorted(NOMBRES_POR_PAIS))]


def en_uso(nombre: str, apellido: str) -> bool:
    return _clave(nombre, apellido) in _USADOS


def reservar(nombre: str, apellido: str) -> None:
    _USADOS.add(_clave(nombre, apellido))


def registrar(jugador) -> None:
    reservar(getattr(jugador, 'nombre', ''), getattr(jugador, 'apellido', ''))


def nombre_unico(pais: str = '', azar: Optional[random.Random] = None, reservar: bool = True) -> tuple:
    """
    (nombre, apellido) que nadie usa. Con país conocido siempre sale de ese país (si se agotan
    las combinaciones simples, apellido compuesto); sin país, de un país al azar.
    """
    rng = azar or random
    try:
        from alpha_football.retiros import NOMBRES_POR_PAIS
        conocido = pais in NOMBRES_POR_PAIS
        for compuesto, intentos in ((False, 40), (conocido, 400)):
            for _ in range(intentos):
                nombres, apellidos = _pools(pais, rng)
                n, a = rng.choice(nombres), rng.choice(apellidos)
                if compuesto:
                    a = f"{a}-{rng.choice([x for x in apellidos if x != a])}"
                if not en_uso(n, a):
                    if reservar:
                        _USADOS.add(_clave(n, a))
                    return n, a
        # Casi imposible (miles de combinaciones libres): apellido compuesto.
        n, a = rng.choice(nombres), f"{rng.choice(apellidos)}-{rng.choice(apellidos)}"
    except Exception as e:
        logger.error(f"nombre_unico: {e}")
        n, a = "Juan", f"Pérez-{rng.randint(100, 999)}"
    if reservar:
        _USADOS.add(_clave(n, a))
    return n, a


def _todos_los_jugadores(estado: dict) -> list:
    equipos = []
    for clave in ('primera_division', 'segunda_division'):
        for liga in (estado.get(clave) or {}).values():
            equipos += list(getattr(liga, 'equipos', []) or [])
    for cache in (estado.get('_copas_pool') or {}).values():
        equipos += list((cache or {}).get('equipos', {}).values())
    equipos += list((estado.get('_copas_generados') or {}).values())
    mi = estado.get('mi_equipo')
    if mi is not None:
        equipos.append(mi)
    jugadores, vistos_eq, vistos_j = [], set(), set()
    for eq in equipos:
        if id(eq) in vistos_eq:
            continue
        vistos_eq.add(id(eq))
        for j in getattr(eq, 'jugadores', []) or []:
            if id(j) not in vistos_j:
                vistos_j.add(id(j))
                jugadores.append(j)
    for j in estado.get('free_agents_list') or []:
        if id(j) not in vistos_j:
            vistos_j.add(id(j))
            jugadores.append(j)
    return jugadores


def desduplicar(estado: dict) -> int:
    """Rehace el registro con todos los jugadores de la carrera y renombra los repetidos."""
    _USADOS.clear()
    repetidos = []
    try:
        for j in _todos_los_jugadores(estado):
            k = _clave(getattr(j, 'nombre', ''), getattr(j, 'apellido', ''))
            if k in _USADOS:
                repetidos.append(j)
            else:
                _USADOS.add(k)
        for j in repetidos:
            j.nombre, j.apellido = nombre_unico(getattr(j, 'nacionalidad', '') or '')
        if repetidos:
            logger.info(f"desduplicar: {len(repetidos)} jugadores renombrados")
    except Exception as e:
        logger.error(f"desduplicar: {e}", exc_info=True)
    return len(repetidos)
