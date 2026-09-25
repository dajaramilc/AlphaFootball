# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Energía, resistencia, lesiones y sanciones (v3.1.0)
Sin UI y sin importar models (models importa de aquí los factores de rendimiento).
La energía (0-100) baja minuto a minuto según la resistencia y se recupera al cerrar cada
jornada de liga. Por debajo de 60 se lesiona más; el rendimiento baja desde 70 (barra amarilla)
y el doble de rápido desde 55 (barra roja).
"""
from __future__ import annotations

import logging
import random
from typing import Optional

logger = logging.getLogger(__name__)

GASTO_BASE = 0.40
UMBRAL = 60                 # lesiones
UMBRAL_AMARILLO = 70        # v4.4.0: desde aquí rinde menos (barra amarilla)
UMBRAL_ROJO = 55            # v4.4.0: desde aquí cae el doble de rápido (barra roja)
BONUS_RASGO_RES = {'pulmon_de_hierro': 15, 'rustico': 8, 'regateador': -5}
PROB_LESION_90 = 0.012
PROB_ROJA_90 = 0.004
DURACION_LESION = (1, 2, 3, 4)
PESOS_LESION = (50, 25, 15, 10)


def _edad(j) -> int:
    return int(getattr(j, 'edad', 25) or 25)


def _res(j) -> int:
    return int(getattr(j, 'resistencia', 50) or 50)


def resistencia_inicial(fisico: int, edad: int, rasgo: Optional[str], semilla: str) -> int:
    azar = random.Random(f"res|{semilla}")
    r = int(fisico) + azar.randint(-8, 8)
    if int(edad) > 30:
        r -= 2 * (int(edad) - 30)
    r += BONUS_RASGO_RES.get(rasgo or '', 0)
    return max(1, min(99, r))


def gasto_por_minuto(j) -> float:
    g = GASTO_BASE * (1.5 - _res(j) / 100)
    return g * 1.10 if _edad(j) > 30 else g


def energia_en_minuto(j, minutos: int, mult: float = 1.0) -> float:
    # v3.3.0: `mult` = multiplicador del gasto por estilo (Kloppismo ×1.3).
    return max(0.0, float(getattr(j, 'energia', 100.0)) - gasto_por_minuto(j) * mult * max(0, int(minutos)))


def energia_actual(j) -> float:
    vivo = getattr(j, 'energia_vivo', None)
    return float(getattr(j, 'energia', 100.0)) if vivo is None else float(vivo)


def factor_energia(e: float) -> float:
    e = float(e)
    return 1.0 - max(0.0, UMBRAL_AMARILLO - e) / 600.0 - max(0.0, UMBRAL_ROJO - e) / 600.0


def factor_lesion(e: float) -> float:
    return 1.0 + max(0.0, UMBRAL - float(e)) / 30.0


def factor_moral(m: float) -> float:
    return 1.0 + (float(m) - 70.0) * 0.004


def puntaje_once(j) -> float:
    """Media ajustada por cansancio para que la IA rote (−0.3 por punto de energía bajo 70)."""
    return float(getattr(j, 'overall', 60)) - max(0.0, 70.0 - float(getattr(j, 'energia', 100.0))) * 0.3


def recuperacion(j) -> float:
    r = 15 + 0.15 * _res(j)
    return r - 3 if _edad(j) > 30 else r


def recuperar(j) -> None:
    j.energia = min(100.0, float(getattr(j, 'energia', 100.0)) + recuperacion(j))


def recuperar_todos(estado: dict) -> None:
    """Cierre de jornada de liga: recuperan todos los clubes de las 10 ligas y los de la copa."""
    equipos = []
    for clave in ('primera_division', 'segunda_division'):
        for liga in (estado.get(clave) or {}).values():
            equipos += list(getattr(liga, 'equipos', []) or [])
    # v3.8.0: clubes del banco internacional que juegan las copas (cache del motor)
    for cache in (estado.get('_copas_pool') or {}).values():
        equipos += list((cache or {}).get('equipos', {}).values())
    equipos += list((estado.get('_copas_generados') or {}).values())
    vistos = set()
    for eq in equipos:
        if id(eq) in vistos:
            continue
        vistos.add(id(eq))
        for j in getattr(eq, 'jugadores', []) or []:
            recuperar(j)


def cerrar_partido(equipo, minutos: dict, rng: Optional[random.Random] = None,
                   incidencias: Optional[list] = None) -> list:
    """
    Cierre físico de un partido de `equipo`. `minutos` = {jugador.id: minutos jugados}.
    Gasta energía de los que jugaron, descuenta 1 a lesionados/sancionados que no jugaron
    y sortea lesiones y rojas. Retorna las incidencias nuevas.
    v4.0.0: con `incidencias` (las del partido: {'tipo','jugador','partidos'}) NO se sortea:
    se aplican esas (lesión → lesion_partidos, sanción → partidos_sancion).
    """
    propios = {id(j) for j in getattr(equipo, 'jugadores', []) or []}
    azar = rng or random.Random()
    lista = []
    # v3.3.0: Kloppismo gasta más energía.
    from alpha_football.estilos import factor_gasto_estilo
    mult = factor_gasto_estilo(getattr(equipo, 'estilo_dt', ''))
    for j in list(getattr(equipo, 'jugadores', []) or []):
        try:
            j.energia_vivo = None
            m = int(minutos.get(getattr(j, 'id', None), 0) or 0)
            if m <= 0:
                if j.lesion_partidos > 0:
                    j.lesion_partidos -= 1
                if j.partidos_sancion > 0:
                    j.partidos_sancion -= 1
                continue
            antes = float(getattr(j, 'energia', 100.0))
            j.energia = energia_en_minuto(j, m, mult)
            media = (antes + j.energia) / 2
            if incidencias is not None:
                continue
            if azar.random() < PROB_LESION_90 * m / 90 * factor_lesion(media):
                j.lesion_partidos = azar.choices(DURACION_LESION, weights=PESOS_LESION)[0]
                lista.append({'tipo': 'lesion', 'jugador': j, 'partidos': j.lesion_partidos})
            elif azar.random() < PROB_ROJA_90 * m / 90:
                j.partidos_sancion = 2 if azar.random() < 0.2 else 1
                lista.append({'tipo': 'sancion', 'jugador': j, 'partidos': j.partidos_sancion})
        except Exception as e:
            logger.error(f"cerrar_partido: error con {getattr(j, 'apellido', '?')}: {e}")
    if incidencias is not None:
        return aplicar_incidencias([i for i in incidencias if id(i.get('jugador')) in propios])
    return lista


def aplicar_incidencias(incidencias: list) -> list:
    """v4.0.0: escribe en los jugadores las lesiones/sanciones del partido; devuelve
    [{'tipo', 'jugador', 'partidos'}] (el formato que usa el vestuario para el correo)."""
    out = []
    for inc in incidencias or []:
        try:
            j = inc.get('jugador')
            if j is None:
                continue
            n = int(inc.get('partidos', 1) or 1)
            if inc.get('tipo') == 'lesion':
                j.lesion_partidos = max(int(getattr(j, 'lesion_partidos', 0) or 0), n)
            else:
                j.partidos_sancion = max(int(getattr(j, 'partidos_sancion', 0) or 0), n)
            out.append({'tipo': inc.get('tipo'), 'jugador': j, 'partidos': n})
        except Exception as e:
            logger.error(f"aplicar_incidencias: incidencia inválida {inc}: {e}")
    return out
