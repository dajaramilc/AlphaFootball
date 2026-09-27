# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Ofertas de otros clubes para que los dirijas (v4.6.0)
Al cerrar cada jornada de liga (menos las 3 últimas) puede llegar una oferta de un club de las
ligas vivas según tu calificación de DT: alta = clubes mejores, media = parecidos, baja = rara vez
y peores. Máximo 2 por temporada, una vigente a la vez, con 2 jornadas para responder.
Aceptar = directiva.cambiar_de_club a mitad de temporada. Sin UI (v4.7.0: ofertas_dt_screen la muestra).
"""
from __future__ import annotations

import logging
import random
from typing import Optional

logger = logging.getLogger(__name__)

MAX_POR_TEMPORADA = 2
PLAZO = 2                       # jornadas para responder
# (calif mínima, probabilidad por jornada, banda de media relativa a la tuya)
NIVELES = [(70, 0.10, (0.0, 8.0)), (40, 0.07, (-4.0, 4.0)), (0, 0.02, (-12.0, -2.0))]


def _dc(estado: dict) -> dict:
    return estado.setdefault('datos_carrera', {})


def oferta_vigente(estado: dict) -> Optional[dict]:
    of = _dc(estado).get('oferta_dt')
    return of if isinstance(of, dict) else None


def _contador(estado: dict) -> list:
    temporada = int(estado.get('temporada', 1) or 1)
    c = _dc(estado).get('ofertas_dt_temporada')
    if not isinstance(c, list) or len(c) != 2 or int(c[0]) != temporada:
        c = _dc(estado)['ofertas_dt_temporada'] = [temporada, 0]
    return c


def _nivel(calif: int) -> tuple:
    return next((p, banda) for minimo, p, banda in NIVELES if calif >= minimo)


def _candidatos(estado: dict, banda: tuple) -> list:
    mi = estado.get('mi_equipo')
    ovr = float(getattr(mi, 'ovr_promedio', 70) or 70)
    out = []
    for clave in ('primera_division', 'segunda_division'):
        for liga in (estado.get(clave) or {}).values():
            for eq in getattr(liga, 'equipos', []) or []:
                if eq is mi or getattr(eq, 'id', None) == getattr(mi, 'id', None):
                    continue
                if ovr + banda[0] <= float(getattr(eq, 'ovr_promedio', 0) or 0) <= ovr + banda[1]:
                    out.append((eq, liga))
    return out


def _objetivo_de(club, liga) -> str:
    """Texto del objetivo que la directiva del club ofertante te pondría (mismo criterio que el tuyo)."""
    try:
        from alpha_football import directiva as D
        ranking = sorted(liga.equipos, key=lambda e: -getattr(e, 'ovr_promedio', 0))
        r = next((i + 1 for i, e in enumerate(ranking) if e is club), len(ranking))
        ventaja = (ranking[0].ovr_promedio - ranking[1].ovr_promedio) if len(ranking) > 1 else 0
        try:
            from alpha_football.ui.copa_screen import cupos_copa
            cupo = cupos_copa(getattr(liga, 'tipo', ''))
        except Exception:
            cupo = 3
        return D.objetivo_por_ranking(r, len(ranking), getattr(liga, 'division', 1) or 1, cupo, ventaja)[2]
    except Exception as e:
        logger.error(f"No se pudo calcular el objetivo de la oferta: {e}")
        return "—"


def revisar_jornada(estado: dict, rng: Optional[random.Random] = None) -> None:
    """Cierre de jornada de liga: vence la oferta vieja y, con suerte, llega una nueva."""
    try:
        from alpha_football import directiva as D, correo as C
        liga, mi = estado.get('liga'), estado.get('mi_equipo')
        if liga is None or mi is None or estado.get('despido_pendiente'):
            return
        jugadas = D._jugadas(liga, mi)
        of = oferta_vigente(estado)
        if of is not None:
            if jugadas >= int(of.get('vence', 0)):
                _dc(estado).pop('oferta_dt', None)
                C.enviar(estado, 'club', f"Venció la oferta de {of['club']}",
                         "Al no recibir respuesta en el plazo previsto, hemos optado por otro entrenador.",
                         firma=f"La Directiva de {of['club']}")
            return
        try:   # v4.7.0: una sola oferta de club a la vez (tampoco con una de banquillo vigente)
            from alpha_football.entrenadores import ofertas_activas
            if ofertas_activas(estado):
                return
        except Exception as e_en:
            logger.error(f"No se pudieron revisar las ofertas de banquillo: {e_en}")
        cont = _contador(estado)
        n = int(getattr(liga, 'num_jornadas', 22) or 22)
        if cont[1] >= MAX_POR_TEMPORADA or jugadas < 1 or jugadas > n - 3:
            return
        azar = rng or random.Random()
        prob, banda = _nivel(D.calif_dt(estado))
        if azar.random() >= prob:
            return
        cands = _candidatos(estado, banda)
        if not cands:
            return
        club, liga_c = azar.choice(cands)
        cont[1] += 1
        _dc(estado)['oferta_dt'] = {'club_id': club.id, 'club': club.nombre, 'liga': liga_c.nombre,
                                    'media': round(float(club.ovr_promedio), 1),
                                    'objetivo': _objetivo_de(club, liga_c),
                                    'presupuesto': int(getattr(club, 'balance', 0) or 0),
                                    'temporada': int(estado.get('temporada', 1) or 1), 'vence': jugadas + PLAZO}
        mi_nombre = getattr(estado.get('mi_equipo'), 'nombre', 'su club')
        # v4.7.0: el correo dice por qué te quieren y se responde desde OFERTAS DT
        C.enviar(estado, 'club', f"{club.nombre} quiere que lo dirijas",
                 f"Su calificación como DT ({D.calif_dt(estado)}/100) y su trabajo en {mi_nombre} no han pasado "
                 f"desapercibidos. Nos complace ofrecerle la dirección técnica de {club.nombre} ({liga_c.nombre}, "
                 f"media {club.ovr_promedio:.1f}) desde este mismo momento. Dispone de {PLAZO} jornadas para "
                 "responder desde OFERTAS DT.",
                 C.accion('ofertas_dt_screen', "VER OFERTA"), firma=f"La Directiva de {club.nombre}")
    except Exception as e:
        logger.error(f"Error al revisar las ofertas de clubes: {e}")


def desde_llegada(estado: dict, eq, temporada: Optional[int] = None) -> dict:
    """v4.7.0: puntos y goles del club desde que llegaste (si llegaste a mitad de esa temporada)."""
    ll = _dc(estado).get('llegada_club') or {}
    t = int(temporada if temporada is not None else estado.get('temporada', 1) or 1)
    base = {'pts': int(getattr(eq, 'puntos', 0) or 0), 'gf': int(getattr(eq, 'gf', 0) or 0),
            'gc': int(getattr(eq, 'gc', 0) or 0)}
    if ll.get('club') == getattr(eq, 'nombre', None) and int(ll.get('temporada', -1)) == t:
        return {k: base[k] - int(ll.get(k, 0) or 0) for k in base}
    return base


def rechazar(estado: dict) -> None:
    _dc(estado).pop('oferta_dt', None)


def aceptar(estado: dict) -> str:
    """Cambia de club a mitad de temporada. La temporada en el club viejo queda como 'se fue'."""
    from alpha_football import directiva as D
    from alpha_football.negociacion import buscar_en_club
    of = oferta_vigente(estado)
    if of is None:
        return "No hay oferta vigente."
    nuevo, _j = buscar_en_club(estado, of['club_id'], None)
    _dc(estado).pop('oferta_dt', None)
    if nuevo is None:
        return f"{of['club']} ya no está disponible."
    mi, liga = estado.get('mi_equipo'), estado.get('liga')
    obj = _dc(estado).get('objetivo') or {}
    orden = sorted(liga.equipos, key=lambda e: (e.puntos, e.gf - e.gc, e.gf), reverse=True)
    pos = next((i + 1 for i, e in enumerate(orden) if e is mi), len(orden))
    estado.setdefault('historial', []).append({
        'temporada': int(estado.get('temporada', 1) or 1), 'equipo': mi.nombre, 'pos': pos, 'posicion': pos,
        'pts': mi.puntos, 'puntos': mi.puntos, 'gf': mi.gf, 'gc': mi.gc, 'campeon_liga': '—',
        'libertadores': '—', 'bono_liga': 0, 'bono_copa': 0, 'bono_total': 0,
        'objetivo': obj.get('texto', ''), 'objetivo_resultado': 'se fue', 'directiva_monto': 0,
        'despedido': False, 'se_fue': True})
    D.cambiar_de_club(estado, nuevo)
    _dc(estado)['llegada_club'] = {'club': nuevo.nombre, 'temporada': int(estado.get('temporada', 1) or 1),
                                   'pts': int(nuevo.puntos), 'gf': int(nuevo.gf), 'gc': int(nuevo.gc)}
    from alpha_football import correo as C
    C.enviar(estado, 'directiva', f"Bienvenido a {nuevo.nombre}",
             f"Le damos la bienvenida a {nuevo.nombre}. En breve le comunicaremos los objetivos de la temporada.",
             C.accion('objetivos_screen', "VER OBJETIVOS"))
    return f"Ahora diriges a {nuevo.nombre}."
