# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Nivel al cierre de temporada (v4.4.0)
Ascenso (+3..+6, techo 83), descenso (−2..−5) y temporada sin objetivos (0..−2) según el
rendimiento de cada jugador relativo a su plantel, corregido por puesto (nota − media de su
puesto en su liga). Tope con la curva por edad. Sin UI.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

TRAMOS = {'descenso': (-2, -3, -4, -5), 'ascenso': (6, 5, 4, 3), 'objetivos': (0, -1, -2)}
NO_ELEGIBLE = {'descenso': -3, 'ascenso': 4, 'objetivos': -1}
TOPE = {'descenso': -6, 'objetivos': -3}
TECHO_ASCENSO = 83
FRACCION_ELEGIBLE = 3          # elegible = jugó al menos 1/3 de las jornadas de liga
PUESTOS = ('POR', 'DEF', 'MED', 'DEL')


def _num_jornadas(liga) -> int:
    n = int(getattr(liga, 'num_jornadas', 0) or 0)
    return n or 2 * max(1, len(getattr(liga, 'equipos', []) or []) - 1)


def _elegible(j, num_jornadas: int) -> bool:
    return int(getattr(j, 'partidos_jugados', 0) or 0) * FRACCION_ELEGIBLE >= max(1, int(num_jornadas or 1))


def medias_por_puesto(liga) -> dict:
    """{puesto: media de promedio_nota de los elegibles de la liga}; '*' = media de todos."""
    nj = _num_jornadas(liga)
    por_puesto, todas = {}, []
    for eq in getattr(liga, 'equipos', []) or []:
        for j in getattr(eq, 'jugadores', []) or []:
            if _elegible(j, nj):
                n = float(getattr(j, 'promedio_nota', 0) or 0)
                por_puesto.setdefault(getattr(j, 'posicion', 'MED'), []).append(n)
                todas.append(n)
    general = sum(todas) / len(todas) if todas else 6.0
    medias = {'*': general}
    for p in PUESTOS:
        vals = por_puesto.get(p)
        medias[p] = sum(vals) / len(vals) if vals else general
    return medias


def deltas_equipo(equipo, medias: dict, num_jornadas: int, caso: str) -> dict:
    """{id(jugador): delta} por tramos (cuartos/tercios) del puntaje nota − media del puesto."""
    tramos = TRAMOS[caso]
    k = len(tramos)
    js = list(getattr(equipo, 'jugadores', []) or [])
    out = {id(j): NO_ELEGIBLE[caso] for j in js}

    def _puntaje(j):
        return float(getattr(j, 'promedio_nota', 0) or 0) - float(
            medias.get(getattr(j, 'posicion', 'MED'), medias.get('*', 6.0)))
    orden = sorted((j for j in js if _elegible(j, num_jornadas)), key=_puntaje, reverse=True)
    n = len(orden)
    for i, j in enumerate(orden):
        out[id(j)] = tramos[min(k - 1, i * k // n)]
    return out


def aplicar(equipo, caso: str, estado: Optional[dict] = None) -> list:
    """Mueve la media de toda la plantilla según `caso`. Devuelve [(jugador, delta aplicado)]."""
    from alpha_football.mercado_ia import _mover_media, _recalcular_valores
    estado = estado if isinstance(estado, dict) else {}
    plan = (estado.get('_nivel_plan') or {}).get(id(equipo))
    if caso == 'descenso' and plan and plan.get('grande'):
        try:  # v4.4.0: los 3 mejores del grande que desciende piden salir (antes del bajón)
            from alpha_football.salidas import marcar_salida_forzada
            marcar_salida_forzada(estado, equipo)
        except Exception as e_sf:
            logger.error(f"No se pudo marcar la salida forzada de {getattr(equipo, 'nombre', '?')}: {e_sf}")
    js = list(getattr(equipo, 'jugadores', []) or [])
    if caso == 'ascenso':
        # los que pedían salir por el descenso vuelven a estar en 1ª: ya no tienen motivo para irse
        from alpha_football.salidas import limpiar
        for j in js:
            if getattr(j, 'salida_forzada', False):
                limpiar(j)
    if plan:
        deltas = deltas_equipo(equipo, plan['medias'], plan['num_jornadas'], caso)
    else:
        deltas = {id(j): NO_ELEGIBLE[caso] for j in js}
    tmp = estado.setdefault('_nivel_tmp', {})
    base = {id(j): j.overall for j in js}     # media antes del bajón/salto (el correo muestra el total)
    cambios = []
    for j in js:
        d = int(deltas.get(id(j), NO_ELEGIBLE[caso]))
        if caso == 'ascenso':
            d = 0 if j.overall >= TECHO_ASCENSO else min(d, TECHO_ASCENSO - j.overall)
        if d:
            antes = j.overall
            _mover_media(j, d)
            d = j.overall - antes                       # lo realmente aplicado (atributos topeados)
            pot = int(getattr(j, 'potencial', 0) or 0)
            if caso == 'ascenso' and d > 0 and pot:
                j.potencial = min(99, max(pot + d, j.overall + 1))
        if caso in TOPE:
            tmp[id(j)] = (d, j.overall, TOPE[caso])
        cambios.append((j, d))
    _recalcular_valores(equipo)
    estado.setdefault('_nivel_movidos', set()).add(id(equipo))
    mi = estado.get('mi_equipo')
    if mi is not None and equipo is mi:
        estado['_nivel_user'] = {'caso': caso, 'cambios': cambios, 'base': base}
    return cambios


def _clave_tabla(e):
    return (getattr(e, 'puntos', 0), getattr(e, 'gf', 0) - getattr(e, 'gc', 0), getattr(e, 'gf', 0))


def _ligas(estado: dict) -> list:
    from alpha_football.mercado_ia import ligas_de_la_partida
    return ligas_de_la_partida(estado)


def objetivo_fallado_user(estado: dict) -> bool:
    """Liga fallada, copa fallada (o sin copa) y ningún pedido cumplido en la temporada que cierra."""
    dc = estado.get('datos_carrera') or {}
    info = dc.get('directiva_ultimo') or {}
    temporada_fin = int(estado.get('temporada', 2) or 2) - 1
    if info.get('temporada') != temporada_fin or info.get('resultado') != 'fallado':
        return False
    copa = info.get('copa')
    if isinstance(copa, dict) and copa.get('resultado') != 'fallado':
        return False
    return not any(p.get('cumplido') and int(p.get('temporada', 0) or 0) == temporada_fin
                   for p in dc.get('pedidos_temporada') or [])


def pos_max_ia(liga, tipo: str, division: int, eq, ranking: Optional[list] = None) -> int:
    """El 'objetivo' de un club de la IA: el mismo cálculo que la directiva usa con el user."""
    from alpha_football.directiva import objetivo_por_ranking
    rk = ranking or sorted(liga.equipos, key=lambda e: -float(getattr(e, 'ovr_promedio', 0) or 0))
    n = len(rk)
    r = next((i + 1 for i, e in enumerate(rk) if e is eq), n)
    ventaja = (rk[0].ovr_promedio - rk[1].ovr_promedio) if n > 1 else 0
    try:
        from alpha_football.ui.copa_screen import cupos_copa
        cupo = cupos_copa(tipo)
    except Exception:
        cupo = 3
    return int(objetivo_por_ranking(r, n, int(division or 1), cupo, ventaja)[1])


def preparar(estado: dict) -> None:
    """Antes del swap (tablas finales, stats aún sin resetear): plan por club."""
    dc = estado.setdefault('datos_carrera', {})
    mi = estado.get('mi_equipo')
    temporada_fin = int(estado.get('temporada', 2) or 2) - 1
    foto = dc.get('objetivos_ia') or {}
    foto_pm = (foto.get('pos_max') or {}) if foto.get('temporada') == temporada_fin else {}
    fallo_user = objetivo_fallado_user(estado)
    plan = {}
    for liga, tipo, division in _ligas(estado):
        medias = medias_por_puesto(liga)
        nj = _num_jornadas(liga)
        rk = sorted(liga.equipos, key=lambda e: -float(getattr(e, 'ovr_promedio', 0) or 0))
        tabla = sorted(liga.equipos, key=_clave_tabla, reverse=True)
        for eq in liga.equipos:
            try:
                if mi is not None and eq is mi:
                    fallo = fallo_user
                else:
                    pm = foto_pm.get(eq.nombre) or pos_max_ia(liga, tipo, division, eq, rk)
                    fallo = tabla.index(eq) + 1 > int(pm)
                plan[id(eq)] = {'medias': medias, 'num_jornadas': nj, 'objetivo_fallado': bool(fallo),
                                'grande': int(division or 1) == 1 and rk.index(eq) < len(rk) // 2}
            except Exception as e_eq:
                logger.error(f"No se pudo preparar el nivel de {getattr(eq, 'nombre', '?')}: {e_eq}")
    estado['_nivel_plan'] = plan
    estado['_nivel_tmp'] = {}
    estado['_nivel_movidos'] = set()
    estado.pop('_nivel_user', None)


def aplicar_objetivos(estado: dict) -> None:
    """Bajón 0..−2 a los clubes que no cumplieron ningún objetivo y no subieron ni bajaron."""
    plan = estado.get('_nivel_plan') or {}
    movidos = set(estado.get('_nivel_movidos') or set())
    for liga, _tipo, _div in _ligas(estado):
        for eq in list(liga.equipos):
            p = plan.get(id(eq))
            if p and p.get('objetivo_fallado') and id(eq) not in movidos:
                try:
                    aplicar(eq, 'objetivos', estado)
                except Exception as e_obj:
                    logger.error(f"No se pudo aplicar el bajón por objetivos a {eq.nombre}: {e_obj}")


ASUNTOS = {'descenso': "Descenso: los jugadores están en mala forma y perdieron nivel",
           'objetivos': "Temporada sin objetivos: los jugadores están en mala forma y perdieron nivel",
           'ascenso': "Ascenso: el plantel da un salto de nivel"}


def _correo_user(estado: dict, user: dict, devueltos: dict) -> None:
    from alpha_football import correo as C
    base = user.get('base') or {}
    # delta real que se ve en la plantilla: bajón/salto + curva por edad + devolución por el tope
    cambios = [(j, int(j.overall) - int(base[id(j)]) if id(j) in base else int(d) + int(devueltos.get(id(j), 0)))
               for j, d in user.get('cambios') or []]
    if not cambios:
        return
    prom = sum(d for _j, d in cambios) / len(cambios)
    orden = sorted(cambios, key=lambda x: x[1], reverse=user.get('caso') == 'ascenso')
    lista = "; ".join(f"{j.nombre} {j.apellido} {d:+d}" for j, d in orden)
    C.enviar(estado, 'club', ASUNTOS.get(user.get('caso'), "Cambios de nivel en el plantel"),
             f"Cambio promedio: {prom:+.1f} de media. {lista}.", C.accion('plantilla_screen', "VER PLANTILLA"))


def aplicar_topes(estado: dict) -> dict:
    """Tras la curva por edad: la pérdida (bajón + curva) no pasa del tope; correo al user."""
    from alpha_football.mercado_ia import _mover_media
    tmp = estado.pop('_nivel_tmp', None) or {}
    devueltos = {}
    for liga, _tipo, _div in _ligas(estado):
        for eq in liga.equipos:
            for j in eq.jugadores:
                t = tmp.get(id(j))
                if not t:
                    continue
                bajon, ovr_tras, tope = t
                perdida = int(bajon) + min(0, j.overall - int(ovr_tras))
                if perdida < tope:
                    antes = j.overall
                    _mover_media(j, tope - perdida)
                    devueltos[id(j)] = j.overall - antes
                    try:
                        from alpha_football.market import calcular_valor
                        j.valor = calcular_valor(j)
                    except Exception as e_val:
                        logger.debug(f"No se pudo recalcular el valor de {j.nombre}: {e_val}")
    user = estado.pop('_nivel_user', None)
    if user:
        try:
            _correo_user(estado, user, devueltos)
        except Exception as e_c:
            logger.error(f"No se pudo avisar el cambio de nivel: {e_c}")
    estado.pop('_nivel_plan', None)
    estado.pop('_nivel_movidos', None)
    return devueltos


def foto_objetivos_ia(estado: dict) -> None:
    """Al empezar la temporada (tras el mercado de pretemporada): pos_max de cada club."""
    t = int(estado.get('temporada', 1) or 1)
    pm = {}
    for liga, tipo, division in _ligas(estado):
        rk = sorted(liga.equipos, key=lambda e: -float(getattr(e, 'ovr_promedio', 0) or 0))
        for eq in liga.equipos:
            try:
                pm[eq.nombre] = pos_max_ia(liga, tipo, division, eq, rk)
            except Exception as e_pm:
                logger.error(f"No se pudo fijar el objetivo de {getattr(eq, 'nombre', '?')}: {e_pm}")
    estado.setdefault('datos_carrera', {})['objetivos_ia'] = {'temporada': t, 'pos_max': pm}
