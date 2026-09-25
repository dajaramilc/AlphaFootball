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


def expandir_plantilla(equipo, objetivo: int = 25, tope: int = 40):
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
            # v4.4.0: nombre único (antes los 15 de _NOMBRES_SUPLENTES se repetían en cada club)
            from alpha_football.nombres import nombre_unico
            nombre, apellido = nombre_unico(getattr(jugadores[0], 'nacionalidad', '') if jugadores else '')

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


def expandir_liga(liga, objetivo: int = 25, tope: int = 40):
    """Asegura `objetivo` jugadores (cap `tope`) en todos los equipos de una liga (fail-soft)."""
    try:
        for equipo in getattr(liga, "equipos", []) or []:
            expandir_plantilla(equipo, objetivo, tope)
    except Exception as error_liga:
        logger.error(f"Error al expandir las plantillas de la liga: {error_liga}")
    return liga


# --- v2.3.6: techo de media por región al CREAR las ligas ────────────────────────
# Sudamérica arranca con media máxima 81; después cada jugador puede crecer hasta su
# potencial (o más, si su potencial dinámico sube por rendimiento).
TECHO_SUDAMERICA = 81
from alpha_football.paises import SUDAMERICA as _SUDAMERICA  # noqa: E402
TIPOS_SUDAMERICA = _SUDAMERICA + ('libertadores',)   # v3.7.0: incluye uruguay y ecuador
_ATRIBUTOS = ("ataque", "defensa", "fisico", "tecnica", "mental")


def aplicar_techo_ovr(equipos, techo: int) -> int:
    """
    Baja a `techo` la media de los jugadores que lo superan (restando el exceso a sus
    5 atributos, así conserva su perfil). Retorna cuántos jugadores se ajustaron.
    """
    ajustados = 0
    for equipo in equipos or []:
        for j in getattr(equipo, "jugadores", []) or []:
            try:
                exceso = int(j.overall) - techo
                if exceso <= 0:
                    continue
                for attr in _ATRIBUTOS:
                    setattr(j, attr, max(10, getattr(j, attr) - exceso))
                # Si algún atributo topó en 10, el redondeo puede dejarlo arriba: afinar.
                for _ in range(20):
                    if j.overall <= techo:
                        break
                    mayor = max(_ATRIBUTOS, key=lambda a: getattr(j, a))
                    setattr(j, mayor, getattr(j, mayor) - 1)
                ajustados += 1
            except Exception as e_techo:
                logger.warning(f"No se pudo aplicar el techo a {getattr(j, 'nombre', '?')}: {e_techo}")
    return ajustados


BRECHA_DIVISIONES = 12   # v3.0.0: media de la 1ª - media de la 2ª (Diego: 10-14, no 20)


def acercar_segunda(equipos_2a, equipos_1a, brecha: int = BRECHA_DIVISIONES) -> int:
    """
    Sube (o baja) los 5 atributos y el potencial de todos los jugadores de la 2ª para que
    la media de sus clubes quede `brecha` puntos por debajo de la de la 1ª del país.
    Retorna el desplazamiento aplicado.
    """
    try:
        m1 = sum(e.ovr_promedio for e in equipos_1a) / len(equipos_1a)
        m2 = sum(e.ovr_promedio for e in equipos_2a) / len(equipos_2a)
        delta = round(m1 - brecha - m2)
        if not delta:
            return 0
        for equipo in equipos_2a:
            for j in getattr(equipo, "jugadores", []) or []:
                for attr in _ATRIBUTOS:
                    setattr(j, attr, max(10, min(99, getattr(j, attr) + delta)))
                if getattr(j, "potencial", 0):
                    j.potencial = max(j.overall, min(99, j.potencial + delta))
        return delta
    except Exception as e_br:
        logger.warning(f"No se pudo acercar la 2ª a la 1ª: {e_br}")
        return 0


def aplicar_techo_region(tipo: str, equipos) -> None:
    """Aplica el techo de Sudamérica si `tipo` es una liga/copa sudamericana."""
    if tipo in TIPOS_SUDAMERICA:
        n = aplicar_techo_ovr(equipos, TECHO_SUDAMERICA)
        if n:
            logger.info(f"Techo {TECHO_SUDAMERICA} aplicado a {n} jugadores de '{tipo}'.")
