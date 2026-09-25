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


def _factor_progreso_edad(edad: int) -> float:
    """
    v2.3.6 (nerf): cuánto del progreso por partido se aprovecha según la edad.
    Los jóvenes crecen, en el pico se sube despacio y a los 31+ subir cuesta muchísimo.
    """
    if edad <= 21:
        return 0.75
    if edad <= 24:
        return 0.55
    if edad <= 27:
        return 0.40
    if edad <= 30:
        return 0.25
    return 0.08


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
    stats_partido: Optional[dict] = None,
) -> list:
    """
    Aplica el desarrollo a los jugadores que disputaron el partido.

    Args:
        equipo: models.Equipo cuya plantilla evoluciona.
        goles_favor / goles_contra: marcador del equipo en ese partido.
        indices_jugaron: índices (en equipo.jugadores) que jugaron; por defecto los 11
                         de la alineación activa o los primeros 11.
        rng: random.Random opcional para reproducibilidad en tests.
        stats_partido: v4.0.0, `partido_ctx.stats_de_equipo(...)`: quiénes jugaron, goles,
                       asistencias y notas REALES del partido (sin él se sortean como antes).

    Returns:
        Lista de dicts con el resumen por jugador (jugador, nota, goles, asistencias, subio_ovr).
    """
    azar = rng or random.Random()
    if equipo is None or not getattr(equipo, "jugadores", None):
        return []
    jugadores = equipo.jugadores

    # Determinar quiénes jugaron
    from alpha_football.partido_ctx import clave
    if stats_partido is not None:   # v4.0.0: los que pisaron la cancha según el partido
        _jug = set(stats_partido.get('jugaron', []))
        indices_jugaron = [i for i, j in enumerate(jugadores) if clave(j) in _jug]
    elif indices_jugaron is None:
        alin = getattr(equipo, "alineacion_activa", None)
        if alin and getattr(alin, "titulares", None):
            indices_jugaron = list(alin.titulares)
        else:
            # v2.3.6: el mismo once que usa el motor para la IA (mejor 4-3-3), no los
            # 11 primeros de la lista (2 porteros y 7 defensas).
            try:
                from alpha_football.engine import _once_titular
                pos = {id(j): i for i, j in enumerate(jugadores)}
                indices_jugaron = [pos[id(j)] for j in _once_titular(equipo) if id(j) in pos]
            except Exception as e_once:
                logger.debug(f"No se pudo calcular el once de {getattr(equipo, 'nombre', '?')}: {e_once}")
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
    if stats_partido is not None:   # v4.0.0: goleadores y asistentes reales (clave = id del objeto)
        for j in participantes:
            goles_por_jug[id(j)] = int(stats_partido.get('goles', {}).get(clave(j), 0))
            asist_por_jug[id(j)] = int(stats_partido.get('asist', {}).get(clave(j), 0))
    for _ in range(max(0, int(goles_favor)) if stats_partido is None else 0):
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
        nota_real = (stats_partido or {}).get('notas', {}).get(clave(j))
        if nota_real is not None:   # v4.0.0: la nota sale de los eventos del partido
            nota = float(nota_real)
        else:
            nota = _nota_partido(j, gano, empato, azar)
            nota = max(4.0, min(10.0, round(nota + gp * 0.6 + ap * 0.3, 1)))
        j.notas_recientes = (list(getattr(j, "notas_recientes", []) or []) + [nota])[-5:]

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
        # v2.3.6: nerf general (los jugadores subían demasiado) + factor por edad.
        inc = 0.0
        if j.posicion in ("POR", "DEF"):
            inc += 0.03  # base plana: cualquier partido suma algo
            if clean_sheet:
                inc += 0.12  # portería a cero
                if j.posicion == "POR":
                    j.porterias_cero += 1   # valla invicta para la tabla de porteros
            if goles_contra <= 1:
                inc += 0.04
            if nota > 7.5:
                inc += 0.08
            if ap > 0:
                inc += 0.10
        else:  # MED, DEL — crecen por goles/asistencias/nota
            inc += gp * 0.15
            inc += ap * 0.08
            if nota > 7.5:
                inc += 0.08
        # Bonus por regularidad: un buen promedio histórico también suma.
        if j.promedio_nota >= 7.0:
            inc += 0.03
        edad_j = int(getattr(j, "edad", 25) or 25)
        # Un veterano (31+) solo progresa con partidos de nota alta.
        if edad_j >= 31 and nota < 7.5:
            inc = 0.0
        # v3.1.0: con buena moral y buena forma progresa un 15% más rápido.
        try:
            from alpha_football.vestuario import forma
            if int(getattr(j, "moral", 70)) >= 75 and forma(j) >= 6.5:
                inc *= 1.15
        except Exception:
            pass
        j.progreso_desarrollo += inc * _factor_progreso_edad(edad_j)

        # Subidas de OVR: cada 1.0 de progreso -> +1 a 3 atributos base al azar.
        # v0.8.x: respetar el techo de potencial. Si el jugador ya está en su techo,
        # el progreso se consume silenciosamente (la "gran temporada" no rompe el límite).
        subio = False
        _pot_actual = _potencial_perezoso(j, azar)
        # v2.3.6: potencial DINÁMICO. Un partido increíble (nota >= 9) de un jugador que
        # ya tocó su techo puede subirle el potencial (poco probable y menos con la edad).
        if nota >= 9.0 and j.overall >= _pot_actual and _pot_actual < 99:
            if azar.random() < (0.30 if edad_j <= 27 else 0.12 if edad_j <= 30 else 0.04):
                _pot_actual += 1
                j.potencial = _pot_actual
        while j.progreso_desarrollo >= 1.0:
            j.progreso_desarrollo = round(j.progreso_desarrollo - 1.0, 4)
            if j.overall < _pot_actual:
                for attr in azar.sample(ATRIBUTOS_BASE, 3):
                    setattr(j, attr, min(99, getattr(j, attr) + 1))
                subio = True
            # si ya está en el techo: se consume el progreso sin subir OVR

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
            # v4.0.0: para la pantalla de calificaciones
            "jugador_id": getattr(j, "id", id(j)),
            "obj": j,
            "amarillas": int((stats_partido or {}).get('amarillas', {}).get(clave(j), 0)),
            "roja": clave(j) in (stats_partido or {}).get('roja', set()),
            "lesion": clave(j) in (stats_partido or {}).get('lesion', set()),
            "minutos": int((stats_partido or {}).get('minutos', {}).get(clave(j), 90)),
        })

    # v0.7: el equipo se "familiariza" con la táctica usada (más si ganó). Vale para el
    # partido en vivo y la simulación instantánea, que pasan ambos por aquí.
    try:
        from alpha_football.engine import actualizar_familiaridad
        actualizar_familiaridad(equipo, gano, empato)
    except Exception as e_fam:
        logger.debug(f"No se pudo actualizar familiaridad táctica: {e_fam}")

    return reporte


# --- v0.8.8: desarrollo PASIVO por temporada (envejecimiento + curva de edad) ────────
#
# El desarrollo por partido (arriba) solo toca a los equipos que juegan: el del usuario,
# sus rivales de liga y los de copa. Las OTRAS 4 ligas no se simulan, y NADIE envejecía.
# `progresar_pasivo` cierra eso: aplica una temporada (o varias) de envejecimiento y
# deriva el OVR según la edad. Pura y testeable (acepta rng con semilla).

def _delta_ovr_por_edad(edad: int, rng: random.Random) -> int:
    """Cambio neto de OVR para UNA temporada según la edad (curva de carrera)."""
    # v2.3.6 (nerf): menos subida gratis; a los 31+ tienden a bajar.
    if edad <= 20:
        return rng.choice([0, 1, 1, 2])   # cantera en plena subida
    if edad <= 23:
        return rng.choice([0, 0, 1])      # joven que sigue creciendo
    if edad <= 27:
        return rng.choice([0, 0, 0, 1])   # pico, casi estable
    if edad <= 30:
        return rng.choice([-1, 0, 0])     # leve inicio de declive
    if edad <= 32:
        return rng.choice([-1, -1, -1, 0])  # declive
    return rng.choice([-1, -2, -2])       # veterano en caída


def _potencial_perezoso(jugador: Any, _azar: random.Random) -> int:
    """
    Devuelve el potencial del jugador; si todavía no estaba calculado (`potencial == 0`),
    lo calcula y lo guarda. Usa un RNG propio sembrado con el id del jugador para que
    el resultado sea estable entre llamadas y entre módulos.
    Fallback permisivo: si algo falla, devuelve 99 (no acotar el crecimiento).
    """
    try:
        pot = int(getattr(jugador, "potencial", 0) or 0)
        if pot > 0:
            return pot
        ovr = int(getattr(jugador, "overall", 50))
        edad = int(getattr(jugador, "edad", 25))
        # RNG sembrado con el id del jugador (no consume el azar principal)
        rng_id = random.Random(int(getattr(jugador, "id", 0)) or 0)
        pot = calcular_potencial(ovr, edad, rng_id)
        setattr(jugador, "potencial", pot)
        return pot
    except Exception:
        return 99


def calcular_potencial(overall: int, edad: int, rng: random.Random) -> int:
    """
    Potencial final (techo de OVR) generoso: el bono sobre el OVR actual depende de la
    edad (jóvenes tienen techo MUY arriba; veteranos casi igual a su OVR actual).
    El resultado se acota a [overall+1, 99] para que SIEMPRE sea mayor que el OVR de
    partida y nunca supere el techo absoluto del motor. Determinista si se pasa un rng
    con semilla fija.
    Ejemplos pedidos por Diego:
      20/80  → 90-92
      24/85  → 89-91
      27/80  → 83-85
    """
    # v2.3.8: los jóvenes tienen bastante más techo (antes 14/11/8/5).
    if edad <= 18:
        bono = 20
    elif edad <= 20:
        bono = 16
    elif edad <= 22:
        bono = 12
    elif edad <= 24:
        bono = 7
    elif edad <= 26:
        bono = 4
    elif edad <= 28:
        bono = 4
    elif edad <= 30:
        bono = 3
    elif edad <= 32:
        bono = 2
    else:
        bono = 1     # 33 o más
    jitter = rng.randint(-1, 1)
    return max(overall + 1, min(99, overall + bono + jitter))


def progresar_pasivo(equipo: Any, anios: int = 1, rng: Optional[random.Random] = None) -> None:
    """
    Aplica `anios` temporadas de envejecimiento + drift de OVR a toda la plantilla.

    Para cada jugador y por cada año: `edad += 1` y se mueve el OVR según la curva
    (sumando/restando el delta a los 5 atributos base, acotados a [10, 99], de modo
    que el promedio cambie ese delta). Recalcula el valor de mercado al final.

    v0.8.x: integra la regla de veterano + temporada destacada.
      - Si el jugador rindió muy bien esta temporada (`promedio_nota >= 7.3`),
        un jugador de hasta 33 años puede SUBIR +1 (acotado por su potencial) y
        se le sube el techo `potencial` en 1-2 puntos.
        Un veterano de 34+ con gran temporada NO BAJA esa temporada.
      - Si rindió sólido (`promedio_nota >= 6.8`) y tiene ≤33, se mantiene.
      - Resto: curva por edad normal, también acotada por el techo.
    Sin `promedio_nota` (ligas/pools de fondo) se aplica la curva por edad tal cual,
    sin invocar la regla destacada.

    Determinista si se pasa un `rng` con semilla fija (se usa así para envejecer las
    otras ligas y los pools internacionales de forma reproducible según la temporada).
    """
    azar = rng or random.Random()
    if equipo is None or not getattr(equipo, "jugadores", None):
        return
    try:
        from alpha_football.market import calcular_valor
    except Exception:
        calcular_valor = None  # type: ignore

    pasos = max(0, int(anios))
    for j in equipo.jugadores:
        for _ in range(pasos):
            edad = int(getattr(j, "edad", 25))
            # Resolver techo (perezozo: si potencial==0 lo calcula y guarda)
            _pot_actual = _potencial_perezoso(j, azar)

            # Delta por la curva base de carrera
            delta = _delta_ovr_por_edad(edad, azar)

            # Regla de veterano + temporada destacada. Solo aplica cuando el jugador
            # realmente rindió esta temporada (promedio_nota > 0). Las ligas/pools de
            # fondo (sin promedio_nota) siguen su curva normal.
            _nota = float(getattr(j, "promedio_nota", 0) or 0)
            # v2.3.6: a los 31+ subir es muy difícil; solo una temporada EXCELENTE frena
            # la caída (y rara vez suma +1). Los jóvenes/pico con gran temporada suben.
            if edad >= 31:
                if _nota >= 7.8:
                    delta = 1 if azar.random() < 0.25 else max(delta, 0)
                elif _nota >= 7.4:
                    delta = max(delta, 0)
                elif _nota >= 7.0:
                    delta = max(delta, -1)
            elif _nota >= 7.3:
                # Gran temporada + edad de crecimiento: puede subir +1 (nunca baja)
                delta = max(delta, 1)
                # Potencial dinámico: la irrupción sube el techo (más cuanto más joven)
                try:
                    _pot_actual = min(
                        99,
                        int(getattr(j, "potencial", 0) or 0) + (azar.choice([1, 2]) if edad <= 26 else 1)
                    )
                    setattr(j, "potencial", _pot_actual)
                except Exception as e_pot:
                    logger.debug(f"No se pudo subir el potencial de {getattr(j, 'nombre', '?')}: {e_pot}")
            elif _nota >= 6.8:
                # Temporada sólida: no cae, pero tampoco crece por encima de la curva
                delta = max(delta, 0)

            # v0.8.x: nunca crecer por encima del potencial. Si delta cruza el techo,
            # recortar. Si igual no entra, queda en 0.
            if delta > 0 and j.overall + delta > _pot_actual:
                delta = max(0, _pot_actual - j.overall)

            if delta != 0:
                for attr in ATRIBUTOS_BASE:
                    setattr(j, attr, max(10, min(99, getattr(j, attr) + delta)))
            j.edad = edad + 1
        if calcular_valor is not None:
            try:
                j.valor = calcular_valor(j)
            except Exception as e_val:
                logger.debug(f"No se pudo recalcular valor pasivo de {getattr(j, 'nombre', '?')}: {e_val}")


def progresar_liga_pasivo(liga: Any, anios: int = 1, rng: Optional[random.Random] = None) -> None:
    """Envejece de una pasada todos los equipos de una liga (fail-soft)."""
    try:
        for equipo in getattr(liga, "equipos", []) or []:
            progresar_pasivo(equipo, anios, rng)
    except Exception as e_liga:
        logger.error(f"Error al progresar pasivamente la liga: {e_liga}")


# --- v2.3.8: más techo para los jóvenes en partidas ya empezadas ─────────────────
_BONO_POTENCIAL_VIEJO = ((18, 14), (20, 11), (22, 8), (24, 5))
_BONO_POTENCIAL_NUEVO = ((18, 20), (20, 16), (22, 12), (24, 7))


def _bono_por_edad(tabla, edad: int) -> int:
    for tope, bono in tabla:
        if edad <= tope:
            return bono
    return 0


def migrar_potencial_jovenes(equipos) -> int:
    """Suma a los ≤24 años la diferencia entre el bono de potencial nuevo y el viejo
    (una sola vez por partida). Retorna cuántos jugadores se ajustaron."""
    ajustados = 0
    for eq in equipos:
        for j in getattr(eq, 'jugadores', []) or []:
            edad = int(getattr(j, 'edad', 30) or 30)
            pot = int(getattr(j, 'potencial', 0) or 0)
            extra = _bono_por_edad(_BONO_POTENCIAL_NUEVO, edad) - _bono_por_edad(_BONO_POTENCIAL_VIEJO, edad)
            if pot and extra > 0:
                j.potencial = min(99, pot + extra)
                ajustados += 1
    return ajustados
