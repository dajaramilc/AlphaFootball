# -*- coding: utf-8 -*-
"""
Alpha Football v2.3.6 — BALÓN DE ORO.

Al cerrar la temporada se elige al mejor jugador de TODAS las ligas (1ª y 2ª de los
5 países) según su rendimiento de la temporada: nota media, goles, asistencias,
vallas invictas, títulos (liga y copa) y el peso de la liga donde jugó.
Mecánica pura y testeable: recibe las ligas y devuelve un dict serializable.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# v3.8.0: peso de cada liga de 1ª desde el registro de países (Europa 1.0; Brasil y Argentina 0.85;
# el resto 0.75) y de cualquier 2ª (0.6).
def _pesos_1a() -> dict:
    try:
        from alpha_football.paises import PAISES
        return {p['liga_id']: 1.0 if p['region'] == 'europa' else 0.85 if p['liga_id'] in ('brasil', 'argentina')
                else 0.75 for p in PAISES}
    except Exception as e_p:
        logger.error(f"Balón de Oro: no se pudo leer paises: {e_p}")
        return {'premier': 1.0, 'laliga': 1.0, 'seriea': 1.0, 'brasil': 0.85, 'argentina': 0.85}


PESO_LIGA_1A = _pesos_1a()
PESO_LIGA_2A = 0.6
BONO_CAMPEON_LIGA = 15.0          # v3.8.0: liga de 1ª ganada
BONO_CAMPEON_COPA = 20.0          # v3.8.0: Champions o Libertadores ganada
MIN_PARTIDOS_PCT = 0.5   # hay que haber jugado al menos la mitad de la liga


def _clave_tabla(e: Any) -> tuple:
    return (getattr(e, 'puntos', 0), getattr(e, 'gf', 0) - getattr(e, 'gc', 0), getattr(e, 'gf', 0))


def puntaje_jugador(j: Any, peso_liga: float, campeon_liga: bool, campeon_copa: bool,
                    goles_copa: int = 0, asist_copa: int = 0, vallas_copa: int = 0) -> float:
    """
    v3.8.0: goles×4 + asistencias×2 + max(0, nota−6)×10 + liga 15 + copa 20 + (POR) vallas×1.5,
    todo × peso de la liga. Los goles/asistencias/vallas de copa se suman a los de liga.
    """
    nota = float(getattr(j, 'promedio_nota', 0) or 0)
    goles = int(getattr(j, 'goles', 0) or 0) + int(goles_copa or 0)
    asist = int(getattr(j, 'asistencias', 0) or 0) + int(asist_copa or 0)
    base = goles * 4.0 + asist * 2.0 + max(0.0, nota - 6.0) * 10.0
    if getattr(j, 'posicion', '') == 'POR':
        base += (int(getattr(j, 'porterias_cero', 0) or 0) + int(vallas_copa or 0)) * 1.5
    if campeon_liga:
        base += BONO_CAMPEON_LIGA
    if campeon_copa:
        base += BONO_CAMPEON_COPA
    return round(base * peso_liga, 2)


def _stats_copa_por_jugador(datos_copas: Optional[dict]) -> dict:
    """{(club, nombre): {'goles','asist','vallas'}} sumando las dos copas de la temporada."""
    res: dict = {}
    for c in (datos_copas or {}).values():
        for s in ((c or {}).get('stats') or {}).values():
            try:
                k = (s.get('club', ''), s.get('nombre', ''))
                d = res.setdefault(k, {'goles': 0, 'asist': 0, 'vallas': 0, 'pj': 0})
                d['pj'] += int(s.get('pj', 0) or 0)            # v4.3.0: partidos de copa
                d['goles'] += int(s.get('goles', 0) or 0)
                d['asist'] += int(s.get('asist', 0) or 0)
                d['vallas'] += int(s.get('vallas', 0) or 0)
            except Exception as e_s:
                logger.debug(f"Balón de Oro: fila de copa inválida {s}: {e_s}")
    return res


def calcular_balon_de_oro(primeras: dict, segundas: dict, temporada: int,
                          campeon_copa=None, n_podio: int = 3,
                          datos_copas: Optional[dict] = None) -> Optional[dict]:
    """
    Recorre las 10 ligas y devuelve {'temporada', 'ganador', 'podio'} (cada jugador como
    dict con nombre, equipo, liga, posición, OVR, goles, asistencias, nota, PJ y puntaje),
    o None si nadie jugó lo suficiente.
    """
    # v3.8.0: campeon_copa puede ser un nombre o una colección (campeones de las dos copas);
    # datos_copas = datos_carrera['copas'] (goles/asistencias/vallas de copa por jugador).
    if isinstance(campeon_copa, str) or campeon_copa is None:
        campeones_copa = {campeon_copa} if campeon_copa else set()
    else:
        campeones_copa = {x for x in campeon_copa if x}
    stats_copa = _stats_copa_por_jugador(datos_copas)
    candidatos = []
    for division, mapa in ((1, primeras or {}), (2, segundas or {})):
        for tipo, liga in mapa.items():
            if liga is None or not getattr(liga, 'equipos', None):
                continue
            try:
                peso = PESO_LIGA_1A.get(tipo, 0.75) if division == 1 else PESO_LIGA_2A
                jornadas = int(getattr(liga, 'num_jornadas', 10) or 10)
                campeon = max(liga.equipos, key=_clave_tabla)
                for eq in liga.equipos:
                    # v4.3.0: el mínimo es el % sobre liga + copa; los partidos de copa del club se
                    # toman del jugador que más jugó en ella
                    pj_copa_eq = max((stats_copa.get((eq.nombre, getattr(x, 'nombre_completo', '')), {}).get('pj', 0)
                                      for x in eq.jugadores), default=0)
                    min_pj = max(3, int((jornadas + pj_copa_eq) * MIN_PARTIDOS_PCT))
                    for j in eq.jugadores:
                        sc = stats_copa.get((eq.nombre, getattr(j, 'nombre_completo', '')), {})
                        if int(getattr(j, 'partidos_jugados', 0) or 0) + int(sc.get('pj', 0) or 0) < min_pj:
                            continue
                        pts = puntaje_jugador(j, peso, eq is campeon, eq.nombre in campeones_copa,
                                              sc.get('goles', 0), sc.get('asist', 0), sc.get('vallas', 0))
                        candidatos.append((pts, j, eq, liga, sc))
            except Exception as e_liga:
                logger.error(f"Balón de Oro: error revisando la liga '{tipo}': {e_liga}")
    if not candidatos:
        return None
    candidatos.sort(key=lambda c: c[0], reverse=True)

    def _ficha(pts, j, eq, liga, sc) -> dict:
        return {
            'nombre': getattr(j, 'nombre_completo', f"{j.nombre} {j.apellido}"),
            'equipo': eq.nombre,
            'liga': getattr(liga, 'nombre', getattr(liga, 'tipo', '?')),
            'posicion': getattr(j, 'posicion', '?'),
            'ovr': int(getattr(j, 'overall', 0) or 0),
            'goles': int(getattr(j, 'goles', 0) or 0),
            'asistencias': int(getattr(j, 'asistencias', 0) or 0),
            'nota': round(float(getattr(j, 'promedio_nota', 0) or 0), 2),
            'pj': int(getattr(j, 'partidos_jugados', 0) or 0) + int(sc.get('pj', 0) or 0),   # v4.3.0: liga + copa
            'goles_copa': int(sc.get('goles', 0) or 0),        # v3.8.0
            'asistencias_copa': int(sc.get('asist', 0) or 0),
            'puntaje': pts,
        }

    podio = [_ficha(*c) for c in candidatos[:n_podio]]
    return {'temporada': int(temporada), 'ganador': podio[0], 'podio': podio}
