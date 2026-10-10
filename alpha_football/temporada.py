# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — La temporada por fechas (v0.4.13.0)
Un solo sitio que sabe en qué fase de la temporada estamos, a partir de la FECHA de hoy (el reloj de
dias.py; sin reloj, el día del partido de la jornada actual). El mercado abre y cierra en días del
calendario, no en jornadas; la mitad y el fin de temporada también son fechas.
Sin UI.
"""
from __future__ import annotations

import logging
import random
from datetime import date, timedelta
from typing import Optional

from alpha_football import calendario as CAL

logger = logging.getLogger(__name__)

# (mes, día, años a sumar al año en que empieza la temporada)
CALENDARIO = {
    'europa': {'inicio': (7, 1, 0), 'cierre1': (8, 31, 0), 'mitad': (1, 1, 1), 'cierre2': (1, 31, 1),
               'fin': (6, 30, 1)},
    'sudamerica': {'inicio': (1, 1, 0), 'cierre1': (1, 31, 0), 'mitad': (7, 1, 0), 'cierre2': (8, 31, 0),
                   'fin': (12, 31, 0)},
}
ORDEN = ('inicio', 'invierno')           # orden de apertura dentro de la temporada (en los dos continentes)
RONDAS_IA_POR_VENTANA = 3


def _anio(estado: dict, t: Optional[int] = None) -> int:
    """Año en que empieza la temporada número `t` (por defecto la actual)."""
    base = CAL.anio(estado)
    return base if t is None else base + int(t) - int(estado.get('temporada', 1) or 1)


def hitos(estado: dict, t: Optional[int] = None) -> dict:
    """{'inicio', 'cierre1', 'mitad', 'cierre2', 'fin'} (fechas) de la temporada `t`."""
    plan = CALENDARIO.get(CAL.continente(estado), CALENDARIO['europa'])
    a = _anio(estado, t)
    return {k: date(a + v[2], v[0], v[1]) for k, v in plan.items()}


def ventanas(estado: dict, t: Optional[int] = None) -> dict:
    h = hitos(estado, t)
    return {'inicio': (h['inicio'], h['cierre1']), 'invierno': (h['mitad'], h['cierre2'])}


def inicio(estado: dict) -> date:
    return hitos(estado)['inicio']


def mitad(estado: dict) -> date:
    return hitos(estado)['mitad']


def fin(estado: dict) -> date:
    return hitos(estado)['fin']


def fecha(estado: dict) -> date:
    """Hoy: el reloj (dias.hoy) si la partida lo tiene; si no, el día del partido de la jornada actual."""
    try:
        from alpha_football import dias
        if dias.activo(estado):
            return dias.hoy(estado)
    except Exception as e:
        logger.error(f"temporada: no se pudo leer el reloj: {e}")
    liga = estado.get('liga')
    if liga is None or estado.get('mi_equipo') is None:
        return inicio(estado)
    return CAL.fecha_liga(estado, int(getattr(liga, 'jornada_actual', 1) or 1))


def ventana_actual(estado: dict) -> Optional[str]:
    """'inicio' | 'invierno' si hoy el mercado está abierto; None si no (o si el último día ya se cerró)."""
    h = fecha(estado)
    n = next((n for n, (a, b) in ventanas(estado).items() if a <= h <= b), None)
    if n is not None:
        try:
            from alpha_football import dia_final
            if dia_final.cerrado(estado):
                return None                     # v0.4.14.0: CERRAR MERCADO / 0 horas cierran antes de la medianoche
        except Exception as e:
            logger.error(f"temporada: no se pudo leer el último día: {e}")
    return n


def ventana_abierta(estado: dict) -> bool:
    return ventana_actual(estado) is not None


def ventana_en(estado: dict, d: date) -> bool:
    """¿El día `d` cae dentro de una ventana de mercado de esta temporada?"""
    return any(a <= d <= b for a, b in ventanas(estado).values())


def ultimo_dia(estado: dict) -> bool:
    """¿Hoy es un cierre de mercado (31 de agosto / 31 de enero)?"""
    h = fecha(estado)
    return any(h == b for _a, b in ventanas(estado).values())


def dias_para_cierre(estado: dict) -> Optional[int]:
    n = ventana_actual(estado)
    return None if n is None else (ventanas(estado)[n][1] - fecha(estado)).days


def siguiente_ventana(estado: dict) -> tuple:
    """(temporada, nombre): la ventana abierta hoy o, si el mercado está cerrado, la próxima."""
    t, h = int(estado.get('temporada', 1) or 1), fecha(estado)
    v = ventanas(estado)
    for n in ORDEN:
        if h <= v[n][1]:
            return t, n
    return t + 1, ORDEN[0]


def proxima_apertura(estado: dict) -> date:
    """Primer día de la próxima ventana que todavía no abrió (la de inicio de la temporada siguiente, si no hay más)."""
    t, h = int(estado.get('temporada', 1) or 1), fecha(estado)
    v = ventanas(estado)
    for n in ORDEN:
        if v[n][0] > h:
            return v[n][0]
    return ventanas(estado, t + 1)['inicio'][0]


def hito_del_dia(estado: dict, d: date) -> Optional[str]:
    """'abre' el primer día de una ventana, 'ultimo' el día de su cierre (el último día de fichajes); None el resto."""
    for a, b in ventanas(estado).values():
        if d == a:
            return 'abre'
        if d == b:
            return 'ultimo'
    return None


def segunda_mitad(estado: dict) -> bool:
    return fecha(estado) >= mitad(estado)


def es_fin(estado: dict) -> bool:
    return fecha(estado) >= fin(estado)


def texto_fase(estado: dict) -> str:
    """'Mercado abierto · cierra en 19 días', 'Primera mitad', 'Segunda mitad', 'Temporada terminada · fin 30 jun'."""
    n = ventana_actual(estado)
    if n is not None:
        d = dias_para_cierre(estado)
        return "Mercado abierto · último día" if d == 0 else f"Mercado abierto · cierra en {d} día{'s' if d != 1 else ''}"
    if es_fin(estado):
        return f"Temporada terminada · fin {CAL.texto_fecha(fin(estado), False)}"
    return "Segunda mitad" if segunda_mitad(estado) else "Primera mitad"


def _sabs(estado: dict, t: Optional[int] = None) -> tuple:
    return CAL.sabados(CAL._n(estado), CAL.continente(estado), _anio(estado, t))


def jornada_de(estado: dict, d: date, t: Optional[int] = None) -> int:
    """Primera jornada de la temporada `t` cuyo sábado base cae el día `d` o después (n + 1 si ninguna)."""
    sabs = _sabs(estado, t)
    return next((i + 1 for i, s in enumerate(sabs) if s >= d), len(sabs) + 1)


def ventana_jornadas(estado: dict, nombre: str, t: Optional[int] = None) -> tuple:
    """(primera, última) jornada que cae dentro de la ventana (vacía si última < primera)."""
    a, b = ventanas(estado, t)[nombre]
    return jornada_de(estado, a, t), jornada_de(estado, b + timedelta(days=1), t) - 1


def dias_de_ronda(estado: dict) -> list:
    """Los días (sorteados con semilla, sin el último día) en que la IA hace su ronda de fichajes."""
    out: list = []
    for nombre, (a, b) in ventanas(estado).items():
        dias = [a + timedelta(days=k) for k in range((b - a).days)]
        azar = random.Random(f"rondas-{CAL.anio(estado)}-{nombre}")
        out += sorted(azar.sample(dias, min(RONDAS_IA_POR_VENTANA, len(dias))))
    return sorted(out)


def es_dia_de_ronda(estado: dict, d: date) -> bool:
    return d in dias_de_ronda(estado)
