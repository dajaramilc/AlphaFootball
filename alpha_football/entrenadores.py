# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Entrenadores (v3.4.0)
Cada club de la IA tiene un DT (nombre, estilo, calificación). El estilo del club es el de su
DT. Los clubes que van mal echan a su DT y contratan al mejor libre; si el club entra en tu
banda de nivel, primero te ofrecen el banquillo a ti. Estado en datos_carrera['dts'].
"""
from __future__ import annotations

import logging
import random
from typing import Optional

from alpha_football.estilos import ESTILOS_DT, normalizar_estilo

logger = logging.getLogger(__name__)

N_LIBRES = 20
# v4.6.0: sueldo anual de los DTs de la IA. Un club solo contrata a un DT cuyo sueldo sea a lo
# sumo FRAC_SUELDO_DT de su saldo, y se lo descuenta al contratarlo y en cada temporada
# (mercado_ia.ingresos_fin_temporada): así el Emelec no ficha a Arteta.
SUELDO_DT_MIN = 50_000
FRAC_SUELDO_DT = 0.10
PCT_SUELDO_CLUB = 0.04          # los DTs de arranque cobran ~4% del saldo de su club (como el user)


def dts(estado: dict) -> dict:
    """Estado de los DTs (se crea vacío en saves viejos)."""
    d = estado.setdefault('datos_carrera', {}).setdefault('dts', {})
    for k, v in (('por_club', {}), ('libres', []), ('historial', []), ('despidos_temp', {}),
                 ('ofertas', []), ('sig_id', 1)):
        d.setdefault(k, v)
    return d


def clubes(estado: dict) -> list:
    """(equipo, liga) de las 10 ligas, sin repetir."""
    vistos, out = set(), []
    for clave in ('primera_division', 'segunda_division'):
        for liga in (estado.get(clave) or {}).values():
            for eq in getattr(liga, 'equipos', []) or []:
                if id(eq) not in vistos:
                    vistos.add(id(eq)); out.append((eq, liga))
    return out


def calif_inicial(equipo) -> int:
    """Calif del DT IA = 50 + (estrellas − 3)·10, acotada a 20-90."""
    return max(20, min(90, int(round(50 + (float(getattr(equipo, 'estrellas', 3.0) or 3.0) - 3) * 10))))


def nombre_generado(rng: random.Random) -> str:
    from alpha_football.data.entrenadores import NOMBRES, APELLIDOS
    return f"{rng.choice(NOMBRES)} {rng.choice(APELLIDOS)}"


def sueldo_pedido(calif) -> int:
    """Sueldo anual que pide un DT libre según su calificación (exponencial: los top cuestan)."""
    return max(SUELDO_DT_MIN, int(round(40_000 * 1.08 ** (int(calif) - 20), -3)))


def sueldo_inicial(equipo, calif) -> int:
    """El DT de arranque de un club cobra según el saldo del club (o su pedido, si es mayor)."""
    del_club = int(max(0, int(getattr(equipo, 'balance', 0) or 0)) * PCT_SUELDO_CLUB * (0.8 + int(calif) / 250))
    return max(sueldo_pedido(calif), int(round(del_club, -3)))


def sueldo(dt: Optional[dict]) -> int:
    """Sueldo anual del DT (saves viejos sin 'sueldo': el pedido por su calif; interino: 0)."""
    if not dt or dt.get('interino'):
        return 0
    return int(dt.get('sueldo') or sueldo_pedido(dt.get('calif', 45)))


def puede_pagar(equipo, dt: dict) -> bool:
    return sueldo(dt) <= FRAC_SUELDO_DT * max(0, int(getattr(equipo, 'balance', 0) or 0))


def _nuevo(estado: dict, nombre: str, estilo: str, calif: int, interino: bool = False,
           sueldo_anual: Optional[int] = None) -> dict:
    d = dts(estado)
    dt = {'id': int(d['sig_id']), 'nombre': nombre, 'estilo': normalizar_estilo(estilo),
          'calif': int(calif), 'interino': bool(interino),
          'sueldo': 0 if interino else int(sueldo_anual if sueldo_anual is not None else sueldo_pedido(calif))}
    d['sig_id'] = int(d['sig_id']) + 1
    return dt


def dt_de(estado: dict, equipo) -> Optional[dict]:
    return dts(estado)['por_club'].get(str(getattr(equipo, 'id', '')))


def asignar(estado: dict, equipo, dt: dict) -> None:
    """Pone a `dt` en el banquillo de `equipo` y sincroniza el estilo del club."""
    dts(estado)['por_club'][str(equipo.id)] = dt
    equipo.estilo_dt = dt['estilo']


def _es_mi(estado: dict, equipo) -> bool:
    mi = estado.get('mi_equipo')
    return mi is not None and (equipo is mi or getattr(equipo, 'id', None) == getattr(mi, 'id', -1))


def asegurar_dts(estado: dict) -> None:
    """Idempotente: da DT a todo club IA que no tenga y llena la bolsa de libres."""
    from alpha_football.data.entrenadores import DT_REALES
    d = dts(estado)
    rng = random.Random(f"dts-{estado.get('temporada', 1)}-{len(d['por_club'])}")
    for eq, _liga in clubes(estado):
        if _es_mi(estado, eq) or str(eq.id) in d['por_club']:
            continue
        real = DT_REALES.get(eq.nombre)
        nombre = (getattr(eq, 'dt_nombre', '') or '').strip() or (real[0] if real else nombre_generado(rng))
        # v4.6.0: estilo y calificación puestos en el editor pisan a la tabla y a las estrellas
        estilo = (getattr(eq, 'dt_estilo', '') or (real[1] if real else getattr(eq, 'estilo_dt', 'anchelottismo')))
        calif = int(getattr(eq, 'dt_calif', 0) or 0) or calif_inicial(eq)
        asignar(estado, eq, _nuevo(estado, nombre, estilo, calif, sueldo_anual=sueldo_inicial(eq, calif)))
    if not d.get('libres_editor_ok'):          # v4.6.0: los DTs libres creados en el editor
        d['libres_editor_ok'] = True
        for x in _dts_libres_editor():
            try:
                d['libres'].append(_nuevo(estado, str(x['nombre']), x.get('estilo', 'anchelottismo'),
                                          max(1, min(99, int(x.get('calif', 50) or 50)))))
            except Exception as e_dl:
                logger.error(f"DT libre del editor inválido {x}: {e_dl}")
    while len(d['libres']) < N_LIBRES:
        d['libres'].append(_nuevo(estado, nombre_generado(rng), rng.choice(ESTILOS_DT), rng.randint(35, 70)))


def _dts_libres_editor() -> list:
    """v4.6.0: DTs sin club creados en el editor (clave '_dts_libres' de la base editada)."""
    try:
        import json
        import os
        from alpha_football.paises import RUTA_DB_EDITADA
        if not os.path.exists(RUTA_DB_EDITADA):
            return []
        with open(RUTA_DB_EDITADA, 'r', encoding='utf-8') as f:
            db = json.load(f)
        return [x for x in (db.get('_dts_libres') or []) if isinstance(x, dict) and x.get('nombre')]
    except Exception as e:
        logger.error(f"No se pudieron leer los DTs libres del editor: {e}")
        return []


def mejor_libre(estado: dict, equipo) -> dict:
    """
    Saca de la bolsa al libre con mejor calif que `equipo` puede pagar. Si no le alcanza para
    ninguno, contrata a uno nuevo y barato (el sueldo que el club puede pagar).
    """
    d = dts(estado)
    candidatos = [x for x in d['libres'] if not x.get('interino') and puede_pagar(equipo, x)]
    if not candidatos:
        rng = random.Random(d['sig_id'])
        tope = max(SUELDO_DT_MIN, int(FRAC_SUELDO_DT * max(0, int(getattr(equipo, 'balance', 0) or 0))))
        calif = rng.randint(30, 50)
        return _nuevo(estado, nombre_generado(rng), rng.choice(ESTILOS_DT), calif,
                      sueldo_anual=min(sueldo_pedido(calif), tope))
    mejor = max(candidatos, key=lambda x: x['calif'])
    d['libres'].remove(mejor)
    return mejor


def contratar(estado: dict, equipo) -> dict:
    """El club contrata al mejor DT que puede pagar y le paga la temporada."""
    dt = mejor_libre(estado, equipo)
    equipo.balance = int(getattr(equipo, 'balance', 0) or 0) - sueldo(dt)
    asignar(estado, equipo, dt)
    return dt


def al_cambiar_club(estado: dict, viejo, nuevo) -> None:
    """El user deja `viejo` y toma `nuevo`: el DT de `nuevo` va a libres, `viejo` contrata."""
    d = dts(estado)
    saliente = d['por_club'].pop(str(getattr(nuevo, 'id', '')), None)
    if viejo is not None and viejo is not nuevo:
        contratar(estado, viejo)
    if saliente and not saliente.get('interino'):
        d['libres'].append(saliente)
    d['ofertas'] = [o for o in d['ofertas'] if o.get('club_id') != str(getattr(nuevo, 'id', ''))]


# ── v3.4.0: despidos entre la IA y ofertas de banquillo para el user ─────────

PROB_DESPIDO_JORNADA = 0.08
PROB_DESPIDO_CIERRE = 0.5
PUESTOS_BAJO = 3
PROB_OFERTA_USER = 0.6
JORNADAS_OFERTA = 3


def _clave_liga(liga) -> str:
    return f"{getattr(liga, 'tipo', '?')}-{getattr(liga, 'division', 1)}"


def posicion(liga, equipo) -> int:
    """Puesto actual en la tabla (puntos, diferencia, goles a favor)."""
    tabla = sorted(liga.equipos, key=lambda x: (-x.puntos, -(x.gf - x.gc), -x.gf))
    return next((i + 1 for i, x in enumerate(tabla) if x is equipo), len(tabla))


def esperado(liga, equipo) -> int:
    """Puesto esperado según el ranking de OVR de la liga."""
    ranking = sorted(liga.equipos, key=lambda x: -getattr(x, 'ovr_promedio', 0))
    return next((i + 1 for i, x in enumerate(ranking) if x is equipo), len(ranking))


def _va_mal(liga, equipo) -> bool:
    p = posicion(liga, equipo)
    return p >= esperado(liga, equipo) + PUESTOS_BAJO and p > len(liga.equipos) / 2


def en_banda(estado: dict, equipo) -> bool:
    """¿El club está a tu alcance según tu calificación? (≥70: +10 OVR, ≥55: +5, si no ≤ tuyo)."""
    from alpha_football.directiva import calif_dt
    mi = estado.get('mi_equipo')
    if mi is None:
        return False
    c, ovr, suyo = calif_dt(estado), mi.ovr_promedio, getattr(equipo, 'ovr_promedio', 0)
    tope = ovr + 10 if c >= 70 else ovr + 5 if c >= 55 else ovr
    return suyo <= tope


def despedir(estado: dict, equipo, liga, motivo: str) -> dict:
    """Saca al DT del club (a libres con calif −10) y lo anota. Retorna el DT despedido."""
    d = dts(estado)
    viejo = d['por_club'].pop(str(equipo.id), None) or {}
    if viejo and not viejo.get('interino'):
        # copia: no se muta el dict que el llamador pueda tener (p. ej. dt_de de antes)
        d['libres'].append({**viejo, 'calif': max(0, int(viejo['calif']) - 10)})
    d['historial'].append({'temporada': int(estado.get('temporada', 1) or 1), 'club': equipo.nombre,
                           'dt': viejo.get('nombre', '?'), 'motivo': motivo})
    del d['historial'][:-300]
    if liga is estado.get('liga'):
        from alpha_football import correo as C
        C.enviar(estado, 'club', f"Cambio de DT en {equipo.nombre}",
                 f"Le informamos que {equipo.nombre} ha despedido a {viejo.get('nombre', 'su entrenador')} ({motivo}).")
    return viejo


def _reemplazar(estado: dict, equipo) -> None:
    contratar(estado, equipo)


def _ofrecer_al_user(estado: dict, equipo, liga, motivo: str = "") -> None:
    """El club juega con un interino y te escribe: la oferta dura JORNADAS_OFERTA jornadas."""
    from alpha_football import correo as C
    from alpha_football.directiva import calif_dt
    d = dts(estado)
    rng = random.Random(f"interino-{equipo.id}-{estado.get('temporada', 1)}")
    asignar(estado, equipo, _nuevo(estado, nombre_generado(rng) + " (interino)", 'anchelottismo', 40, interino=True))
    d['ofertas'].append({'club_id': str(equipo.id), 'club': equipo.nombre, 'liga': getattr(liga, 'nombre', ''),
                         'jornadas': JORNADAS_OFERTA, 'temporada': int(estado.get('temporada', 1) or 1),
                         'motivo': motivo})
    # v4.7.0: el correo dice por qué te quieren (despido + tu calificación)
    C.enviar(estado, 'club', f"{equipo.nombre} te quiere como DT",
             f"Tras despedir a nuestro entrenador{f' ({motivo})' if motivo else ''} y en vista de su "
             f"calificación como DT ({calif_dt(estado)}/100), nos complace ofrecerle el banquillo de "
             f"{equipo.nombre} ({getattr(liga, 'nombre', '')}). La oferta tiene una validez de "
             f"{JORNADAS_OFERTA} jornadas; puede responder desde OFERTAS DT.",
             C.accion('ofertas_dt_screen', "VER OFERTA"), firma=f"La Directiva de {equipo.nombre}")


def puede_ofrecer_al_user(estado: dict) -> bool:
    """v4.7.0: no hay otra oferta de club vigente (ofertas_dt)."""
    try:
        from alpha_football.ofertas_dt import oferta_vigente
        return oferta_vigente(estado) is None
    except Exception:
        return True


def ofertas_activas(estado: dict) -> list:
    t = int(estado.get('temporada', 1) or 1)
    return [o for o in dts(estado)['ofertas'] if o.get('temporada') == t and o.get('jornadas', 0) > 0]


def _club_por_id(estado: dict, club_id: str):
    return next(((eq, lg) for eq, lg in clubes(estado) if str(eq.id) == str(club_id)), (None, None))


def revisar_jornada(estado: dict, rng: Optional[random.Random] = None) -> None:
    """Tras cada jornada de liga del user: vencen ofertas y los clubes IA que van mal echan a su DT."""
    azar = rng or random.Random()
    d = dts(estado)
    for o in list(d['ofertas']):                      # 1) las ofertas pendientes pierden una jornada
        o['jornadas'] = int(o.get('jornadas', 0)) - 1
        if o['jornadas'] <= 0:
            d['ofertas'].remove(o)
            eq, _lg = _club_por_id(estado, o['club_id'])
            if eq is not None and (dt_de(estado, eq) or {}).get('interino'):
                _reemplazar(estado, eq)
    for eq, liga in clubes(estado):                    # 2) despidos de la IA
        if _es_mi(estado, eq) or dt_de(estado, eq) is None or dt_de(estado, eq).get('interino'):
            continue
        n = max(1, int(getattr(liga, 'num_jornadas', 10) or 10))
        if int(getattr(liga, 'jornada_actual', 1) or 1) <= n / 3:
            continue
        if d['despidos_temp'].get(_clave_liga(liga), 0) >= 1 or not _va_mal(liga, eq):
            continue
        if azar.random() >= PROB_DESPIDO_JORNADA:
            continue
        motivo = f"iba {posicion(liga, eq)}º y se esperaba {esperado(liga, eq)}º"
        despedir(estado, eq, liga, motivo)
        d['despidos_temp'][_clave_liga(liga)] = d['despidos_temp'].get(_clave_liga(liga), 0) + 1
        if en_banda(estado, eq) and puede_ofrecer_al_user(estado) and azar.random() < PROB_OFERTA_USER:
            _ofrecer_al_user(estado, eq, liga, motivo)
        else:
            _reemplazar(estado, eq)


def cierre_temporada(estado: dict, rng: Optional[random.Random] = None) -> None:
    """Fin de temporada: los que terminaron 3+ puestos bajo lo esperado echan con 50%."""
    azar = rng or random.Random()
    d = dts(estado)
    for eq, liga in clubes(estado):
        if _es_mi(estado, eq) or dt_de(estado, eq) is None:
            continue
        if posicion(liga, eq) >= esperado(liga, eq) + PUESTOS_BAJO and azar.random() < PROB_DESPIDO_CIERRE:
            despedir(estado, eq, liga, "no cumplió en la temporada")
            _reemplazar(estado, eq)
        elif (dt_de(estado, eq) or {}).get('interino'):
            _reemplazar(estado, eq)
    d['despidos_temp'] = {}
    d['ofertas'] = []


def aceptar_oferta(estado: dict, club_id: str):
    """Cambio inmediato de club (sin indemnización: renunciaste)."""
    eq, _lg = _club_por_id(estado, club_id)
    if eq is None or not any(o['club_id'] == str(club_id) for o in ofertas_activas(estado)):
        return None
    from alpha_football.directiva import cambiar_de_club
    cambiar_de_club(estado, eq)                        # llama a al_cambiar_club (quita la oferta)
    dts(estado)['ofertas'] = []
    return eq


def rechazar_oferta(estado: dict, club_id: str) -> None:
    """Rechazas: el club contrata al mejor DT libre."""
    d = dts(estado)
    d['ofertas'] = [o for o in d['ofertas'] if o['club_id'] != str(club_id)]
    eq, _lg = _club_por_id(estado, club_id)
    if eq is not None and (dt_de(estado, eq) or {}).get('interino'):
        _reemplazar(estado, eq)
