# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Forma de los jugadores (v0.4.26.0)
Cinco niveles (pésima, mala, normal, buena, imparable) que salen de las últimas 5 notas del jugador
(`notas_recientes`) y multiplican su progreso de media y de potencial (desarrollo.py).
- Imparable: 3 notas seguidas >= 7.7. Dura 5 partidos y luego pasa a buena; para activarse otra vez hacen
  falta 3 notas altas nuevas DESPUÉS de terminar la racha.
- Sin UI y sin importar models: los campos (`forma`, `imparable_partidos`, `racha_notas_altas`, `forma_datos`)
  viven en Jugador y aquí solo se leen/escriben con getattr (los saves viejos cargan con los defaults).
Calibración (temporada simulada de 12 clubes, ~4000 notas): nota media 6.25 (σ 1.05); el promedio de las últimas 5
notas tiene mediana 6.2 y σ 0.45. Con los umbrales de abajo: pésima ≈ 5 %, mala ≈ 13 %, normal ≈ 70 %, buena ≈ 12 %.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

NIVELES = ('pesima', 'mala', 'normal', 'buena', 'imparable')
TEXTO = {'pesima': "PÉSIMA", 'mala': "MALA", 'normal': "NORMAL", 'buena': "BUENA", 'imparable': "IMPARABLE"}
# RGB por nivel (la paleta de theme.py no tiene naranja ni gris): rojo, naranja, gris, verde, dorado
COLOR = {'pesima': (255, 68, 68), 'mala': (255, 150, 40), 'normal': (170, 175, 190),
         'buena': (0, 255, 136), 'imparable': (255, 215, 0)}

# promedio de las últimas notas -> nivel (imparable no sale del promedio: lo activa la racha de notas)
UMBRAL_PESIMA = 5.5          # menos que esto: pésima
UMBRAL_MALA = 5.85           # menos que esto: mala
UMBRAL_BUENA = 6.8           # esto o más: buena
MIN_NOTAS = 3                # con menos notas no hay forma: normal

NOTA_IMPARABLE = 7.7         # nota que cuenta para la racha
NOTAS_IMPARABLE = 3          # notas seguidas que la activan
PARTIDOS_IMPARABLE = 5       # partidos que dura (luego pasa a buena)

MULT_PROGRESO = {'pesima': 0.5, 'mala': 0.75, 'normal': 1.0, 'buena': 1.5, 'imparable': 2.0}
MORAL_ALTA = 85              # con esta moral o más, el progreso suma ×1.25
MULT_MORAL_ALTA = 1.25
TOPE_MULT = 3.0              # tope del multiplicador total (forma × moral × canterano)

EDAD_POT_FORMA = 24          # ítem 3: hasta esta edad la buena forma también sube el potencial en la temporada
PROB_POT_FORMA = 0.10        # por partido y × multiplicador (buena ×1.5 = 15 %, imparable ×2 = 20 %)
TOPE_POT_TEMPORADA = 3       # máximo de potencial que se gana así en una temporada


def nivel_por_notas(notas) -> str:
    """Nivel (sin imparable) según el promedio de las últimas 5 notas."""
    try:
        ultimas = [float(n) for n in (notas or [])][-5:]
    except Exception as e:
        logger.error(f"forma: notas inválidas {notas!r}: {e}")
        return 'normal'
    if len(ultimas) < MIN_NOTAS:
        return 'normal'
    promedio = sum(ultimas) / len(ultimas)
    if promedio < UMBRAL_PESIMA:
        return 'pesima'
    if promedio < UMBRAL_MALA:
        return 'mala'
    return 'buena' if promedio >= UMBRAL_BUENA else 'normal'


def en_racha(j) -> bool:
    """¿Está en racha imparable ahora mismo?"""
    try:
        return (getattr(j, 'forma', '') == 'imparable'
                and 0 <= int(getattr(j, 'imparable_partidos', 0) or 0) < PARTIDOS_IMPARABLE)
    except Exception as e:
        logger.error(f"forma: no se pudo leer la racha de {getattr(j, 'apellido', '?')}: {e}")
        return False


def partidos_restantes(j) -> int:
    """Partidos que le quedan a la racha imparable (0 si no está en racha)."""
    if not en_racha(j):
        return 0
    return max(0, PARTIDOS_IMPARABLE - int(getattr(j, 'imparable_partidos', 0) or 0))


def nivel(j) -> str:
    """Forma actual del jugador. Siempre sale de las notas (saves viejos incluidos), salvo la racha imparable y
    el piso de 'buena' con el que termina la racha (dura hasta su siguiente partido)."""
    try:
        if en_racha(j):
            return 'imparable'
        n = nivel_por_notas(getattr(j, 'notas_recientes', None))
        datos = getattr(j, 'forma_datos', None)
        if isinstance(datos, dict) and datos.get('piso') and NIVELES.index(n) < NIVELES.index('buena'):
            return 'buena'
        return n
    except Exception as e:
        logger.error(f"forma: no se pudo calcular la forma de {getattr(j, 'apellido', '?')}: {e}")
        return 'normal'


def multiplicador_progreso(j, nivel_forma: Optional[str] = None) -> float:
    """Multiplicador del progreso de media y de potencial: forma × (1.25 si moral >= 85), con tope ×3."""
    try:
        m = MULT_PROGRESO.get(nivel_forma or nivel(j), 1.0)
        if int(getattr(j, 'moral', 70) or 0) >= MORAL_ALTA:
            m *= MULT_MORAL_ALTA
        return min(TOPE_MULT, m)
    except Exception as e:
        logger.error(f"forma: no se pudo calcular el multiplicador de {getattr(j, 'apellido', '?')}: {e}")
        return 1.0


def texto_forma(j) -> str:
    """Texto para la ficha: "BUENA", o "IMPARABLE (quedan 3)" con los partidos que le quedan a la racha."""
    n = nivel(j)
    if n == 'imparable':
        q = partidos_restantes(j)
        return f"{TEXTO[n]} (quedan {q})" if q else TEXTO[n]
    return TEXTO[n]


def registrar_nota(j, nota: float) -> Optional[dict]:
    """Actualiza la forma del jugador DESPUÉS de sumar `nota` a notas_recientes (y de aplicar el progreso del
    partido, que usó la forma anterior). Devuelve un evento o None:
      {'tipo': 'entra'}                              — acaba de activarse la racha imparable
      {'tipo': 'sale', 'media': +X, 'potencial': +Y}  — terminó la racha; lo ganado mientras duró."""
    try:
        datos = getattr(j, 'forma_datos', None)
        if not isinstance(datos, dict):
            datos = {}
            j.forma_datos = datos
        nota = float(nota)
        media = int(getattr(j, 'overall', 0) or 0)
        pot = int(getattr(j, 'potencial', 0) or 0)
        if en_racha(j):
            j.imparable_partidos = int(getattr(j, 'imparable_partidos', 0) or 0) + 1
            if j.imparable_partidos < PARTIDOS_IMPARABLE:
                return None
            pot0 = int(datos.get('pot0', 0) or 0)
            evento = {'tipo': 'sale', 'media': max(0, media - int(datos.get('media0', media) or media)),
                      'potencial': max(0, pot - pot0) if pot0 > 0 else 0}
            j.forma, j.imparable_partidos, j.racha_notas_altas = 'buena', 0, 0
            datos.pop('media0', None)
            datos.pop('pot0', None)
            datos['piso'] = True                      # pasa a buena: así sigue hasta su próximo partido
            return evento
        datos.pop('piso', None)
        racha = int(getattr(j, 'racha_notas_altas', 0) or 0)
        racha = racha + 1 if nota >= NOTA_IMPARABLE else 0
        if racha >= NOTAS_IMPARABLE:
            j.forma, j.imparable_partidos, j.racha_notas_altas = 'imparable', 0, 0
            datos['media0'], datos['pot0'] = media, pot
            return {'tipo': 'entra'}
        j.racha_notas_altas = racha
        j.forma = nivel_por_notas(getattr(j, 'notas_recientes', None))
    except Exception as e:
        logger.error(f"forma: no se pudo registrar la nota de {getattr(j, 'apellido', '?')}: {e}")
    return None
