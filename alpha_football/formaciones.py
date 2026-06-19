# -*- coding: utf-8 -*-
"""
Alpha Football v0.7 — REGISTRO DE FORMACIONES.

Fuente única de verdad para las formaciones jugables. Cada formación define:
  - cuotas: cuántos jugadores por posición (POR/DEF/MED/DEL) deben alinearse.
  - posiciones: 11 coordenadas relativas (x_frac, y_frac) para dibujar el campo
    (mismo convenio que el antiguo POSICIONES_CAMPO_433: y≈0.88 es el arquero,
    y≈0.22 son los delanteros). Ordenadas POR → DEF → MED → DEL.
  - pref: la táctica (estilo_dt) con la que la formación rinde mejor (sinergia).

Lo usan team_screen (selector + campo + validación), engine (sinergia) y
match_screen (menú táctico). Acceso resiliente vía helpers con fallback a 4-3-3.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Cada entrada: {"cuotas": {...}, "posiciones": [(x,y)*11], "pref": estilo_dt}
FORMACIONES: dict[str, dict] = {
    "4-3-3": {
        "cuotas": {"POR": 1, "DEF": 4, "MED": 3, "DEL": 3},
        "pref": "anchelottismo",
        "posiciones": [
            (0.50, 0.88),                                              # POR
            (0.18, 0.68), (0.39, 0.68), (0.61, 0.68), (0.82, 0.68),   # DEF
            (0.25, 0.46), (0.50, 0.46), (0.75, 0.46),                 # MED
            (0.22, 0.24), (0.50, 0.24), (0.78, 0.24),                 # DEL
        ],
    },
    "4-4-2": {
        "cuotas": {"POR": 1, "DEF": 4, "MED": 4, "DEL": 2},
        "pref": "anchelottismo",
        "posiciones": [
            (0.50, 0.88),
            (0.18, 0.68), (0.39, 0.68), (0.61, 0.68), (0.82, 0.68),
            (0.16, 0.46), (0.39, 0.46), (0.61, 0.46), (0.84, 0.46),
            (0.35, 0.24), (0.65, 0.24),
        ],
    },
    "4-3-2-1": {
        "cuotas": {"POR": 1, "DEF": 4, "MED": 5, "DEL": 1},
        "pref": "cruyffismo",
        "posiciones": [
            (0.50, 0.88),
            (0.18, 0.68), (0.39, 0.68), (0.61, 0.68), (0.82, 0.68),
            (0.25, 0.52), (0.50, 0.52), (0.75, 0.52),                 # MED base
            (0.38, 0.34), (0.62, 0.34),                               # MED ofensivos
            (0.50, 0.18),                                             # DEL
        ],
    },
    "5-4-1": {
        "cuotas": {"POR": 1, "DEF": 5, "MED": 4, "DEL": 1},
        "pref": "haramball",
        "posiciones": [
            (0.50, 0.88),
            (0.12, 0.70), (0.31, 0.70), (0.50, 0.70), (0.69, 0.70), (0.88, 0.70),
            (0.16, 0.46), (0.39, 0.46), (0.61, 0.46), (0.84, 0.46),
            (0.50, 0.22),
        ],
    },
    "3-5-2": {
        "cuotas": {"POR": 1, "DEF": 3, "MED": 5, "DEL": 2},
        "pref": "cruyffismo",
        "posiciones": [
            (0.50, 0.88),
            (0.27, 0.70), (0.50, 0.70), (0.73, 0.70),
            (0.12, 0.47), (0.32, 0.47), (0.50, 0.47), (0.68, 0.47), (0.88, 0.47),
            (0.35, 0.24), (0.65, 0.24),
        ],
    },
    "3-4-1-2": {
        "cuotas": {"POR": 1, "DEF": 3, "MED": 5, "DEL": 2},
        "pref": "haramball",
        "posiciones": [
            (0.50, 0.88),
            (0.27, 0.70), (0.50, 0.70), (0.73, 0.70),
            (0.16, 0.50), (0.39, 0.50), (0.61, 0.50), (0.84, 0.50),   # MED base
            (0.50, 0.34),                                             # enganche
            (0.35, 0.20), (0.65, 0.20),
        ],
    },
    "4-2-4": {
        "cuotas": {"POR": 1, "DEF": 4, "MED": 2, "DEL": 4},
        "pref": "flickismo",
        "posiciones": [
            (0.50, 0.88),
            (0.18, 0.68), (0.39, 0.68), (0.61, 0.68), (0.82, 0.68),
            (0.35, 0.47), (0.65, 0.47),
            (0.16, 0.24), (0.39, 0.24), (0.61, 0.24), (0.84, 0.24),
        ],
    },
}

FORMACION_DEFECTO = "4-3-3"


def lista_formaciones() -> list[str]:
    """Devuelve los nombres de formación en orden estable para los selectores."""
    return list(FORMACIONES.keys())


def existe(formacion: str) -> bool:
    return formacion in FORMACIONES


def cuotas(formacion: str) -> dict[str, int]:
    """Cuotas por posición de la formación (fallback a 4-3-3 si no existe)."""
    datos = FORMACIONES.get(formacion) or FORMACIONES[FORMACION_DEFECTO]
    return dict(datos["cuotas"])


def posiciones(formacion: str) -> list[tuple[float, float]]:
    """Coordenadas relativas de los 11 puestos (fallback a 4-3-3)."""
    datos = FORMACIONES.get(formacion) or FORMACIONES[FORMACION_DEFECTO]
    return list(datos["posiciones"])


def pref(formacion: str) -> str:
    """Táctica preferida de la formación (fallback a anchelottismo)."""
    datos = FORMACIONES.get(formacion)
    return datos["pref"] if datos else "anchelottismo"


def mejor_once(jugadores: list, formacion: str) -> list[int]:
    """
    Devuelve los índices del mejor XI (sin lesionados) que respeta las cuotas de la
    formación; rellena a 11 con los mejores restantes si falta cubrir alguna línea.
    Reutilizado por team_screen ("AUTO ONCE") y por el menú táctico en partido.
    """
    cuo = cuotas(formacion)
    por_pos: dict[str, list[tuple[int, int]]] = {"POR": [], "DEF": [], "MED": [], "DEL": []}
    for idx, j in enumerate(jugadores):
        if getattr(j, "lesion_partidos", 0) == 0:
            p = getattr(j, "posicion", "MED")
            if p not in por_pos:
                p = "MED"
            por_pos[p].append((getattr(j, "overall", 60), idx))
    for p in por_pos:
        por_pos[p].sort(reverse=True)

    elegidos: list[int] = []
    for pos, n in cuo.items():
        for _, idx in por_pos[pos][:n]:
            elegidos.append(idx)

    # Rellenar a 11 con los mejores restantes disponibles (si no hay suficientes de una línea).
    # IMPORTANTE: Los porteros (POR) NO se usan de relleno en posiciones de campo;
    # solo se colocan en la posición de POR del esquema táctico.
    sel = set(elegidos)
    necesita_por = len([i for i in elegidos if getattr(jugadores[i], 'posicion', '') == 'POR']) == 0
    restantes = sorted(
        [(getattr(j, "overall", 60), idx) for idx, j in enumerate(jugadores)
         if getattr(j, "lesion_partidos", 0) == 0
         and idx not in sel
         # Excluir porteros del relleno de campo (solo van al slot POR si falta portero)
         and (getattr(j, 'posicion', 'MED') != 'POR' or necesita_por)],
        reverse=True,
    )
    for _, idx in restantes:
        if len(elegidos) >= 11:
            break
        elegidos.append(idx)
    return elegidos[:11]
