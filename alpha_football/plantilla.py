# -*- coding: utf-8 -*-
"""
Alpha Football — Expansión de plantillas.

Agrega suplentes generados a cada equipo para que las plantillas tengan más fondo
(5 jugadores extra por club: un arquero de respaldo y relevos en cada línea).
Resiliente: si algo falla, devuelve el equipo intacto sin romper la carga del juego.
"""

from __future__ import annotations

import random
import logging

logger = logging.getLogger(__name__)

# Nombres de parodia para los suplentes generados (banca / cantera).
_NOMBRES_SUPLENTES = [
    ("Juan", "Bancalarga"), ("Pedro", "Calienta-banca"), ("Luis", "Suplencio"),
    ("Carlos", "Reservez"), ("Diego", "Promesa-Jr"), ("Andrés", "Canterano"),
    ("Mateo", "Polivalente"), ("Brian", "Pierna-fría"), ("Kevin", "Minutos-basura"),
    ("Santi", "Matamonos"), ("Felipe", "Multiusos"), ("Nico", "Rota-equipo"),
    ("Cristian", "De-la-casa"), ("Yeison", "Garra-extra"), ("Faber", "Comodín"),
]

# Posiciones de los 5 suplentes: un arquero de respaldo y fondo en cada línea.
_POSICIONES_SUPLENTES = ["POR", "DEF", "MED", "DEL", "MED"]


def _atributos_por_posicion(posicion: str, ovr: int):
    """Reparte los 5 atributos según la posición (misma fórmula que los agentes libres)."""
    if posicion == "POR":
        return 15, ovr + 5, ovr, ovr - 10, ovr + 5
    if posicion == "DEF":
        return ovr - 20, ovr + 10, ovr + 5, ovr - 10, ovr + 5
    if posicion == "MED":
        return ovr - 5, ovr - 5, ovr, ovr + 5, ovr
    return ovr + 10, ovr - 20, ovr, ovr + 5, ovr  # DEL


def expandir_plantilla(equipo, objetivo: int = 20, tope: int = 32):
    """
    Asegura que el equipo tenga al menos `objetivo` jugadores (rellenando con suplentes
    generados), SIN pasar de `tope`. Idempotente por longitud: si ya tiene `objetivo` o más,
    no agrega nada. Resiliente: ante error, deja el equipo intacto.
    """
    # Importación perezosa: si models falla, no podemos crear jugadores -> equipo intacto.
    try:
        from alpha_football.models import Jugador
    except Exception as error_import:
        logger.error(f"No se pudo importar Jugador para expandir plantilla: {error_import}")
        return equipo

    try:
        jugadores = getattr(equipo, "jugadores", None)
        if jugadores is None:
            return equipo

        objetivo = min(objetivo, tope)
        faltan = objetivo - len(jugadores)
        if faltan <= 0:
            return equipo  # ya tiene suficientes (idempotente por longitud)

        # Nivel base: promedio del once existente (o 60 si el equipo viniera vacío).
        if jugadores:
            base_ovr = sum(j.overall for j in jugadores) // len(jugadores)
        else:
            base_ovr = 60

        # ID base por encima de los existentes para no chocar con el mercado/guardado.
        id_base = max([getattr(j, "id", 0) for j in jugadores], default=8000) + 100

        for idx in range(faltan):
            posicion = _POSICIONES_SUPLENTES[idx % len(_POSICIONES_SUPLENTES)]
            # Suplentes algo por debajo del once base para que los titulares sigan siendo titulares.
            ovr = max(40, base_ovr - random.randint(3, 9))
            atk, dfs, fis, tec, men = _atributos_por_posicion(posicion, ovr)
            if idx < len(_NOMBRES_SUPLENTES):
                nombre, apellido = _NOMBRES_SUPLENTES[idx]
            else:
                nombre, apellido = (f"Sub{idx + 1}", "Banca")

            jugadores.append(Jugador(
                nombre=nombre,
                apellido=apellido,
                posicion=posicion,
                ataque=max(10, min(99, atk)),
                defensa=max(10, min(99, dfs)),
                fisico=max(10, min(99, fis)),
                tecnica=max(10, min(99, tec)),
                mental=max(10, min(99, men)),
                moral=70,
                id=id_base + idx,
                edad=random.randint(18, 24),
            ))

        return equipo

    except Exception as error_expansion:
        logger.error(f"Error al expandir la plantilla de un equipo: {error_expansion}")
        return equipo


def expandir_liga(liga, objetivo: int = 20, tope: int = 32):
    """Asegura `objetivo` jugadores (cap `tope`) en todos los equipos de una liga (fail-soft)."""
    try:
        for equipo in getattr(liga, "equipos", []) or []:
            expandir_plantilla(equipo, objetivo, tope)
    except Exception as error_liga:
        logger.error(f"Error al expandir las plantillas de la liga: {error_liga}")
    return liga
