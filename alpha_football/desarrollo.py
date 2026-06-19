# -*- coding: utf-8 -*-
"""
Alpha Football v0.5 — DESARROLLO DINÁMICO DE JUGADORES (Fase 3).

Al terminar cada partido, los jugadores con minutos evolucionan:
nota del partido (4.0–10.0), promedio histórico, progreso oculto de desarrollo y,
al acumular 1.0 de progreso, +1 de OVR (sumando +1 a 3 atributos base al azar).
Recalcula el valor de mercado con la fórmula de market.calcular_valor.

Mecánica PURA y testeable: opera sobre models.Equipo/Jugador (los persistidos),
para que el crecimiento se guarde entre partidos. La UI (match/career) solo la invoca.
"""
from __future__ import annotations

import logging
import random
from typing import Any, Optional

logger = logging.getLogger(__name__)

ATRIBUTOS_BASE = ("ataque", "defensa", "fisico", "tecnica", "mental")


def _nota_partido(jugador: Any, gano: bool, empato: bool, rng: random.Random) -> float:
    """Nota base del partido en [4.0, 10.0], según resultado, nivel del jugador y azar."""
    base = 6.0
    if gano:
        base += 0.8
    elif empato:
        base += 0.2
    else:
        base -= 0.4
    # Los mejores jugadores rinden un poco mejor en promedio
    base += (jugador.overall - 65) * 0.03
    base += rng.uniform(-1.0, 1.2)
    return max(4.0, min(10.0, round(base, 1)))


def desarrollar_plantilla_post_partido(
    equipo: Any,
    goles_favor: int,
    goles_contra: int,
    indices_jugaron: Optional[list] = None,
    rng: Optional[random.Random] = None,
) -> list:
    """
    Aplica el desarrollo a los jugadores que disputaron el partido.

    Args:
        equipo: models.Equipo cuya plantilla evoluciona.
        goles_favor / goles_contra: marcador del equipo en ese partido.
        indices_jugaron: índices (en equipo.jugadores) que jugaron; por defecto los 11
                         de la alineación activa o los primeros 11.
        rng: random.Random opcional para reproducibilidad en tests.

    Returns:
        Lista de dicts con el resumen por jugador (jugador, nota, goles, asistencias, subio_ovr).
    """
    azar = rng or random.Random()
    if equipo is None or not getattr(equipo, "jugadores", None):
        return []
    jugadores = equipo.jugadores

    # Determinar quiénes jugaron
    if indices_jugaron is None:
        alin = getattr(equipo, "alineacion_activa", None)
        if alin and getattr(alin, "titulares", None):
            indices_jugaron = list(alin.titulares)
        else:
            indices_jugaron = list(range(min(11, len(jugadores))))
    participantes = [jugadores[i] for i in indices_jugaron if 0 <= i < len(jugadores)]
    if not participantes:
        return []

    gano = goles_favor > goles_contra
    empato = goles_favor == goles_contra
    clean_sheet = goles_contra == 0

    # Repartir los goles del equipo entre MED/DEL (ponderado por ataque) y asignar asistencias.
    atacantes = [j for j in participantes if j.posicion in ("MED", "DEL")] or participantes
    goles_por_jug: dict[int, int] = {id(j): 0 for j in participantes}
    asist_por_jug: dict[int, int] = {id(j): 0 for j in participantes}
    for _ in range(max(0, int(goles_favor))):
        pesos = [max(1, j.ataque) for j in atacantes]
        anotador = azar.choices(atacantes, weights=pesos, k=1)[0]
        goles_por_jug[id(anotador)] += 1
        posibles = [j for j in atacantes if j is not anotador]
        if posibles and azar.random() < 0.7:  # 70% de los goles llevan asistencia
            asist = azar.choice(posibles)
            asist_por_jug[id(asist)] += 1

    # Importación perezosa para evitar ciclos (market importa models, no desarrollo).
    try:
        from alpha_football.market import calcular_valor
    except Exception:
        calcular_valor = None  # type: ignore

    reporte = []
    for j in participantes:
        gp = goles_por_jug[id(j)]
        ap = asist_por_jug[id(j)]

        # Nota del partido (con bonus por contribución), acotada a [4.0, 10.0]
        nota = _nota_partido(j, gano, empato, azar)
        nota = max(4.0, min(10.0, round(nota + gp * 0.6 + ap * 0.3, 1)))

        # Estadísticas acumuladas
        j.partidos_jugados += 1
        j.goles += gp
        j.asistencias += ap
        pj = max(1, j.partidos_jugados)
        j.promedio_nota = round(((j.promedio_nota * (pj - 1)) + nota) / pj, 2)

        # Progreso oculto de desarrollo según posición (v0.7: más peso a MED/DEL y a la nota)
        # v0.8.3 (F3): los defensas y porteros progresan más fácil para que no se
        # queden estancados toda la temporada. Se les da:
        #   - base plana por partido (+0.04)
        #   - portería a cero reforzada (+0.20 vs +0.10 anterior)
        #   - bonus por encajar ≤1 gol (+0.08)
        #   - nota >7.5 reforzado (+0.10 vs +0.06)
        #   - bonus por asistencia (+0.20)
        # MED/DEL mantienen su progresión rápida (goles/asistencias).
        inc = 0.0
        if j.posicion in ("POR", "DEF"):
            inc += 0.04  # base plana: cualquier partido suma algo
            if clean_sheet:
                inc += 0.20  # portería a cero: recompensa fuerte
                if j.posicion == "POR":
                    j.porterias_cero += 1   # valla invicta para la tabla de porteros
            if goles_contra <= 1:
                inc += 0.08  # casi perfecto también suma
            if nota > 7.5:
                inc += 0.10
            if ap > 0:
                inc += 0.20  # asistencia (rara en defensas/porteros pero gratificante)
        else:  # MED, DEL — crecen más rápido por goles/asistencias/nota
            inc += gp * 0.26
            inc += ap * 0.14
            if nota > 7.5:
                inc += 0.14
        # Bonus por regularidad: un buen promedio histórico también hace subir el valor/OVR.
        if j.promedio_nota >= 7.0:
            inc += 0.04
        j.progreso_desarrollo += inc

        # Subidas de OVR: cada 1.0 de progreso -> +1 a 3 atributos base al azar
        subio = False
        while j.progreso_desarrollo >= 1.0:
            j.progreso_desarrollo = round(j.progreso_desarrollo - 1.0, 4)
            for attr in azar.sample(ATRIBUTOS_BASE, 3):
                setattr(j, attr, min(99, getattr(j, attr) + 1))
            subio = True

        # Recalcular valor de mercado (OVR^2 * 1000 * factor_edad)
        if calcular_valor is not None:
            try:
                j.valor = calcular_valor(j)
            except Exception as e_val:
                logger.debug(f"No se pudo recalcular valor de {j.nombre_completo}: {e_val}")

        reporte.append({
            "jugador": getattr(j, "nombre_completo", j.nombre),
            "nota": nota,
            "goles": gp,
            "asistencias": ap,
            "subio_ovr": subio,
            # v0.8.6: posicion + id para acumular estadísticas de copa por jugador
            # (goleadores, asistentes, porterías a cero, rendimiento) sin colisiones de nombre.
            "posicion": getattr(j, "posicion", ""),
            "id": getattr(j, "id", id(j)),
        })

    # v0.7: el equipo se "familiariza" con la táctica usada (más si ganó). Vale para el
    # partido en vivo y la simulación instantánea, que pasan ambos por aquí.
    try:
        from alpha_football.engine import actualizar_familiaridad
        actualizar_familiaridad(equipo, gano, empato)
    except Exception as e_fam:
        logger.debug(f"No se pudo actualizar familiaridad táctica: {e_fam}")

    return reporte
