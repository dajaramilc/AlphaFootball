# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Simulación automática (v0.4.14.1)
La partida avanza sola hasta el día que elijas en CALENDARIO: el segundo entrenador arma el once y tus
partidos se simulan al instante; los días sin partido pasan como con CONTINUAR, pero sin detenerse.
- Las ofertas que llegan quedan en la bandeja y los eventos de vestuario sin responder toman su opción por
  defecto al cierre siguiente (lo de siempre); el último día de fichajes se cierra solo.
- El partido del día elegido NO se juega: llegas a ese día y lo diriges tú.
- Solo la detienen el día elegido, un despido o el fin de la temporada.
Sin UI: la pantalla CALENDARIO llama a paso() una vez por cuadro.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from alpha_football import calendario as CAL

logger = logging.getLogger(__name__)


def puede_simular_hasta(estado: dict, d: date) -> bool:
    """¿Se puede simular hasta ese día? Tiene que ser posterior a hoy y no pasar del fin de la temporada."""
    try:
        from alpha_football import dias, temporada as T
        if estado.get('liga') is None or estado.get('mi_equipo') is None:
            return False
        return dias.hoy(estado) < d <= T.fin(estado)
    except Exception as e:
        logger.error(f"simulacion: no se pudo validar el día {d}: {e}")
        return False


def partidos_hasta(estado: dict, d: date) -> int:
    """Partidos tuyos que dirigiría el segundo entrenador: los pendientes anteriores al día `d`."""
    return sum(1 for ev in CAL.eventos_user(estado) if not ev['jugado'] and ev['fecha'] < d)


def once_del_segundo(estado: dict) -> None:
    """El segundo entrenador arma el once: los mejores disponibles para tu formación (sin lesionados ni
    sancionados, y con los cansados rotando) y un banco nuevo."""
    mi = estado.get('mi_equipo')
    alin = getattr(mi, 'alineacion_activa', None)
    if mi is None or alin is None:
        return                                   # sin alineación guardada el motor ya elige su mejor once
    from alpha_football import formaciones as F
    from alpha_football.energia import puntaje_once
    jugadores = list(mi.jugadores)
    alin.titulares = F.mejor_once(jugadores, alin.formacion, puntaje=puntaje_once)
    alin.convocados = []
    F.normalizar_convocados(alin, jugadores)


def _fin(motivo: str) -> dict:
    return {'tipo': 'fin', 'motivo': motivo}


def _despido_pendiente(estado: dict) -> bool:
    return bool(estado.get('despido_pendiente') or (estado.get('datos_carrera') or {}).get('despido_pendiente'))


def _jugar_hoy(estado: dict) -> Optional[dict]:
    """Simula tu partido de hoy con el once del segundo entrenador: primero la copa si toca, si no la liga.
    Devuelve el partido ya jugado ({'etiqueta', 'rival', 'local', 'gf', 'gc'}) o None si no había."""
    from alpha_football.sanciones import en_competicion
    from alpha_football.ui import league_screen as L, prepartido_screen as PRE
    liga, mi = estado.get('liga'), estado.get('mi_equipo')
    previo = CAL.proximo_evento(estado)
    partido_usuario, esta_finalizada, fase_copa, _rival = L._info_partido(estado, liga, mi)
    if fase_copa:
        from alpha_football.ui.copa_screen import preparar_partido_copa
        if not preparar_partido_copa(estado):
            return None
        local, visitante = estado.get('partido_local_obj'), estado.get('partido_visitante_obj')
    elif esta_finalizada or partido_usuario is None or partido_usuario.jugado:
        return None
    else:
        estado['partido_actual'], estado['match_mode'] = partido_usuario, 'liga'
        local = next((e for e in liga.equipos if e.id == partido_usuario.local_id), None)
        visitante = next((e for e in liga.equipos if e.id == partido_usuario.visitante_id), None)
    if local is None or visitante is None or previo is None:
        return None
    try:
        with en_competicion('copa' if fase_copa else 'liga'):
            once_del_segundo(estado)
            PRE._simular_instantaneo(estado, local, visitante)
    finally:
        PRE._salir_resultado(estado)             # no queda a medias la pantalla del resultado
    hecho = next((ev for ev in CAL.eventos_user(estado) if ev['clave'] == previo['clave']), None)
    if hecho is None or not hecho['jugado']:
        return None                              # no se pudo cerrar: mejor detenerse que girar en falso
    if not fase_copa:
        try:   # lo que el hub hace al cambiar la jornada: copas al día y premios cobrados
            from alpha_football.ui.copa_screen import sincronizar_copa_user
            sincronizar_copa_user(estado)
        except Exception as e:
            logger.error(f"simulacion: no se pudo sincronizar la copa: {e}")
    return {k: hecho[k] for k in ('etiqueta', 'rival', 'local', 'gf', 'gc')}


def paso(estado: dict, hasta: date) -> dict:
    """Un paso de la simulación hacia `hasta`: pasa un día o juega tu partido de hoy.
    Devuelve {'tipo': 'dia', ...lo que llegó} | {'tipo': 'partido', 'partido': {...}} |
    {'tipo': 'fin', 'motivo': 'llego' | 'despido' | 'temporada' | 'bloqueo'}."""
    try:
        from alpha_football import dias, dia_final as DF
        if estado.get('liga') is None or estado.get('mi_equipo') is None:
            return _fin('bloqueo')
        if _despido_pendiente(estado):
            return _fin('despido')
        if dias.hoy(estado) >= hasta:
            return _fin('llego')
        if DF.activo(estado):                    # el último día de fichajes se cierra solo
            DF.cerrar(estado)
            estado['aviso_mercado_activo'] = None            # sin cartel viejo esperando en el hub
        if dias.es_dia_de_continuar(estado):
            r = dias.avanzar_dia(estado)
            return dict(r, tipo='dia') if r.get('dias') else _fin('bloqueo')
        jugado = _jugar_hoy(estado)
        if jugado is not None:
            return {'tipo': 'partido', 'partido': jugado}
        from alpha_football import temporada as T
        return _fin('temporada' if T.es_fin(estado) else 'bloqueo')
    except Exception as e:
        logger.error(f"simulacion: error en un paso: {e}", exc_info=True)
        return _fin('bloqueo')
