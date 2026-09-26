# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Sanciones por competición y acumulación de amarillas
- Liga y copa llevan sanciones separadas: `partidos_sancion` (liga) y `sancion_copa` (copa). Una
  roja se cumple en la competición donde se vio.
- Acumulación: 5 amarillas en liga = 1 fecha; 3 en copa = 1 partido (el contador vuelve a 0).
  La doble amarilla de un partido es roja: esas dos no cuentan para la acumulación.
- La competición que se está jugando se fija con `en_competicion('copa')` alrededor de los
  partidos de copa (motor de copas, partido en vivo y pre-partido); por defecto es la liga.
Sin UI.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger(__name__)

LIMITE_AMARILLAS = {'liga': 5, 'copa': 3}
_ACTUAL = ['liga']


def _norm(competicion: Optional[str]) -> str:
    c = competicion or _ACTUAL[0]
    return 'copa' if c == 'copa' else 'liga'


def competicion_actual() -> str:
    return _ACTUAL[0]


@contextmanager
def en_competicion(competicion: Optional[str]):
    """Mientras dura el bloque, las sanciones que se consultan/aplican son las de esa competición."""
    previa = _ACTUAL[0]
    _ACTUAL[0] = _norm(competicion)
    try:
        yield
    finally:
        _ACTUAL[0] = previa


def _attr_sancion(competicion: Optional[str]) -> str:
    return 'sancion_copa' if _norm(competicion) == 'copa' else 'partidos_sancion'


def _attr_amarillas(competicion: Optional[str]) -> str:
    return 'amarillas_copa' if _norm(competicion) == 'copa' else 'amarillas_liga'


def partidos_sancion(j, competicion: Optional[str] = None) -> int:
    return int(getattr(j, _attr_sancion(competicion), 0) or 0)


def sancionado(j, competicion: Optional[str] = None) -> bool:
    return partidos_sancion(j, competicion) > 0


def sancionado_en_algo(j) -> bool:
    return sancionado(j, 'liga') or sancionado(j, 'copa')


def sumar_sancion(j, partidos: int, competicion: Optional[str] = None) -> None:
    """Roja: la sanción de esa competición pasa a ser al menos `partidos`."""
    attr = _attr_sancion(competicion)
    setattr(j, attr, max(int(getattr(j, attr, 0) or 0), int(partidos)))


def descontar(j, competicion: Optional[str] = None) -> None:
    """El equipo jugó un partido de esa competición y el sancionado no jugó: cumple una fecha."""
    attr = _attr_sancion(competicion)
    if int(getattr(j, attr, 0) or 0) > 0:
        setattr(j, attr, int(getattr(j, attr)) - 1)


def amarillas(j, competicion: Optional[str] = None) -> int:
    return int(getattr(j, _attr_amarillas(competicion), 0) or 0)


def limite(competicion: Optional[str] = None) -> int:
    return LIMITE_AMARILLAS[_norm(competicion)]


def sumar_amarilla(j, competicion: Optional[str] = None) -> Optional[str]:
    """Suma una amarilla. 'sancion' si llegó al límite (queda sancionado 1 partido y el contador
    vuelve a 0), 'aviso' si queda a una del límite, None en otro caso."""
    c = _norm(competicion)
    attr = _attr_amarillas(c)
    n = int(getattr(j, attr, 0) or 0) + 1
    if n >= LIMITE_AMARILLAS[c]:
        setattr(j, attr, 0)
        s = _attr_sancion(c)
        setattr(j, s, int(getattr(j, s, 0) or 0) + 1)
        return 'sancion'
    setattr(j, attr, n)
    return 'aviso' if n == LIMITE_AMARILLAS[c] - 1 else None


def texto_amarillas(j) -> str:
    """"Liga 3/5 · Copa 1/3" para las fichas."""
    return f"Liga {amarillas(j, 'liga')}/{limite('liga')} · Copa {amarillas(j, 'copa')}/{limite('copa')}"


def nueva_temporada(j) -> None:
    """Al empezar la temporada se limpian contadores y sanciones de ambas competiciones."""
    j.partidos_sancion = 0
    j.sancion_copa = 0
    j.amarillas_liga = 0
    j.amarillas_copa = 0
