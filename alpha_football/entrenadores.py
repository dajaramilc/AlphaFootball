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


def prestigio(dt: Optional[dict]) -> str:
    """v0.4.22.0: etiqueta derivada de la calificación: 'bajo' < 50 · 'medio' 50-69 · 'alto' >= 70."""
    calif = int((dt or {}).get('calif', 0) or 0)
    return 'alto' if calif >= 70 else 'medio' if calif >= 50 else 'bajo'


def _edad_por_nombre(nombre: str) -> int:
    """Edad de un DT del que no se sabe: 38-68, siempre la misma para ese nombre."""
    return random.Random(f"edad-dt-{nombre}").randint(38, 68)


def _nuevo(estado: dict, nombre: str, estilo: str, calif: int, interino: bool = False,
           sueldo_anual: Optional[int] = None, nacionalidad: str = '', edad: Optional[int] = None,
           ex_jugador: bool = False) -> dict:
    d = dts(estado)
    dt = {'id': int(d['sig_id']), 'nombre': nombre, 'estilo': normalizar_estilo(estilo),
          'calif': int(calif), 'interino': bool(interino), 'nacionalidad': str(nacionalidad or ''),
          'sueldo': 0 if interino else int(sueldo_anual if sueldo_anual is not None else sueldo_pedido(calif)),
          'edad': int(edad or 0) or _edad_por_nombre(nombre), 'ex_jugador': bool(ex_jugador)}
    d['sig_id'] = int(d['sig_id']) + 1
    return dt


def _pais_de_club(estado: dict, equipo) -> str:
    """v0.4.10.0: país de la liga donde juega el club ('' si no se encuentra)."""
    from alpha_football.mercado_ia import ligas_de_la_partida
    from alpha_football.retiros import PAIS_POR_LIGA
    for liga, tipo, _div in ligas_de_la_partida(estado):
        if any(eq is equipo for eq in liga.equipos):
            return PAIS_POR_LIGA.get(tipo, '')
    return ''


def _nacionalidad_dt(estado: dict, nombre: str, equipo=None, rng=None) -> str:
    """v0.4.10.0: país real del DT parodiado; si no está, el de la liga del club; si no, uno al azar."""
    from alpha_football.data.nacionalidades import nacionalidad_dt
    from alpha_football.retiros import PAIS_POR_LIGA
    paises = sorted(set(PAIS_POR_LIGA.values()))
    return (nacionalidad_dt(nombre) or (_pais_de_club(estado, equipo) if equipo is not None else '')
            or (rng or random.Random(nombre)).choice(paises))


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
    from alpha_football.data.entrenadores import DT_REALES, DT_LIBRES_REALES
    d = dts(estado)
    rng = random.Random(f"dts-{estado.get('temporada', 1)}-{len(d['por_club'])}")
    for eq, _liga in clubes(estado):
        if _es_mi(estado, eq) or str(eq.id) in d['por_club']:
            continue
        # v0.4.22.0: `dt_sin` = el editor dejó al club sin DT: arranca con uno generado, no con el de la tabla
        real = None if getattr(eq, 'dt_sin', False) else DT_REALES.get(eq.nombre)
        nombre = (getattr(eq, 'dt_nombre', '') or '').strip() or (real[0] if real else nombre_generado(rng))
        # v4.6.0: estilo y calificación puestos en el editor pisan a la tabla y a las estrellas
        estilo = (getattr(eq, 'dt_estilo', '') or (real[1] if real else getattr(eq, 'estilo_dt', 'anchelottismo')))
        calif = int(getattr(eq, 'dt_calif', 0) or 0) or calif_inicial(eq)
        asignar(estado, eq, _nuevo(estado, nombre, estilo, calif, sueldo_anual=sueldo_inicial(eq, calif),
                                   nacionalidad=(str(getattr(eq, 'dt_nacionalidad', '') or '')
                                                 or _nacionalidad_dt(estado, nombre, eq)),
                                   edad=int(getattr(eq, 'dt_edad', 0) or 0)))
    if not d.get('libres_editor_ok'):          # v4.6.0: los DTs libres creados en el editor
        d['libres_editor_ok'] = True
        for x in _dts_libres_editor():
            try:
                d['libres'].append(_nuevo(estado, str(x['nombre']), x.get('estilo', 'anchelottismo'),
                                          max(1, min(99, int(x.get('calif', 50) or 50))),
                                          nacionalidad=(str(x.get('nacionalidad') or '')
                                                        or _nacionalidad_dt(estado, str(x['nombre']))),
                                          edad=int(x.get('edad') or 0)))
            except Exception as e_dl:
                logger.error(f"DT libre del editor inválido {x}: {e_dl}")
    if not d.get('libres_reales_ok'):          # v0.4.22.0: técnicos reales sin club (una vez; también en saves viejos)
        d['libres_reales_ok'] = True
        ocupados = {x.get('nombre') for x in list(d['por_club'].values()) + d['libres']}
        for nombre, estilo, calif, nac, edad in DT_LIBRES_REALES:
            if nombre not in ocupados:
                d['libres'].append(_nuevo(estado, nombre, estilo, calif, nacionalidad=nac, edad=edad))
    while len(d['libres']) < N_LIBRES:
        nom = nombre_generado(rng)
        d['libres'].append(_nuevo(estado, nom, rng.choice(ESTILOS_DT), rng.randint(35, 70),
                                  nacionalidad=_nacionalidad_dt(estado, nom, rng=rng)))
    por_id = {str(eq.id): eq for eq, _liga in clubes(estado)}      # v0.4.10.0: saves sin el campo
    for cid, dt in d['por_club'].items():
        if not dt.get('nacionalidad'):
            dt['nacionalidad'] = _nacionalidad_dt(estado, dt.get('nombre', ''), por_id.get(cid))
    for dt in d['libres']:
        if not dt.get('nacionalidad'):
            dt['nacionalidad'] = _nacionalidad_dt(estado, dt.get('nombre', ''))
    for dt in list(d['por_club'].values()) + d['libres']:           # v0.4.22.0: saves sin edad
        if not dt.get('edad'):
            dt['edad'] = _edad_por_nombre(dt.get('nombre', ''))
        dt.setdefault('ex_jugador', False)


# ── v0.4.22.0: banco de técnicos desempleados ────────────────────────────────

MIN_BANCO = 8                   # con menos libres que esto se rellena hasta N_LIBRES
MAX_BANCO = 40                  # con más, salen los de peor calificación
OVR_RETIRADO_DT = 81            # un retirado de esta media o más puede hacerse entrenador
PROB_RETIRADO_DT = 0.2
ESTILOS_POR_POSICION = {'POR': ("haramball", "choloismo", "anchelottismo"),
                        'DEF': ("choloismo", "haramball", "fullbackismo", "artetismo"),
                        'MED': ("cruyffismo", "dezerbismo", "artetismo", "anchelottismo"),
                        'DEL': ("kloppismo", "flickismo", "cruyffismo", "anchelottismo")}


def mantener_banco(estado: dict, rng: Optional[random.Random] = None) -> None:
    """El banco ni se vacía ni crece sin fin: bajo MIN_BANCO se rellena hasta N_LIBRES con técnicos de nivel
    medio-bajo; sobre MAX_BANCO salen los de peor calificación."""
    d = dts(estado)
    libres = d['libres']
    if len(libres) < MIN_BANCO:
        azar = rng or random.Random(f"banco-{d['sig_id']}")
        while len(libres) < N_LIBRES:
            nom = nombre_generado(azar)
            libres.append(_nuevo(estado, nom, azar.choice(ESTILOS_DT), azar.randint(35, 60),
                                 nacionalidad=_nacionalidad_dt(estado, nom, rng=azar)))
    if len(libres) > MAX_BANCO:
        for dt in sorted(libres, key=lambda x: int(x.get('calif', 0) or 0))[:len(libres) - MAX_BANCO]:
            libres.remove(dt)


def retirados_a_banco(estado: dict, retiros: list, rng: Optional[random.Random] = None) -> list:
    """Cada retirado de OVR_RETIRADO_DT o más tiene PROB_RETIRADO_DT de hacerse entrenador: entra al banco con
    su nombre, nacionalidad y edad, calificación de novato (45-65 según su media) y un estilo de su posición.
    Devuelve los DTs creados."""
    azar = rng or random.Random()
    d = dts(estado)
    creados = []
    for r in retiros or []:
        ovr = int(r.get('ovr', 0) or 0)
        if ovr < OVR_RETIRADO_DT or azar.random() >= PROB_RETIRADO_DT:
            continue
        nombre = str(r.get('nombre', '') or '').strip()
        if not nombre:
            continue
        dt = _nuevo(estado, nombre, azar.choice(ESTILOS_POR_POSICION.get(r.get('posicion'), tuple(ESTILOS_DT))),
                    min(65, 45 + (ovr - OVR_RETIRADO_DT) * 2),
                    nacionalidad=str(r.get('nacionalidad') or '') or _nacionalidad_dt(estado, nombre, rng=azar),
                    edad=int(r.get('edad', 0) or 0), ex_jugador=True)
        d['libres'].append(dt)
        creados.append(dt)
        try:
            from alpha_football import noticias
            noticias.publicar(estado, 'dt_cambio', f"{nombre} se convierte en entrenador",
                              f"{nombre} colgó los botines a los {dt['edad']} años en {r.get('equipo', 'su club')} y no "
                              "piensa alejarse de las canchas: ya tiene su licencia de entrenador y espera la llamada "
                              "de su primer banquillo.", importancia=4, dts=[dt])
        except Exception as e_not:
            logger.error(f"No se pudo publicar la noticia del retirado {nombre}: {e_not}")
    return creados


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


def _cadena(estado: dict) -> dict:
    """v0.4.22.0: movimientos de DT de esta jornada (contador común a todas las ligas). `mov` cuenta los
    robos entre clubes; `movidos`, los ids de los DTs que hoy ya cambiaron de sitio (robados, contratados
    del banco o despedidos): ninguno se mueve dos veces. Se reinicia al cambiar (temporada, jornada)."""
    from alpha_football.salidas import _clave_jornada
    d = dts(estado)
    clave = list(_clave_jornada(estado))
    cad = d.get('cadena')
    if not isinstance(cad, dict) or cad.get('clave') != clave:
        cad = d['cadena'] = {'clave': clave, 'mov': 0, 'movidos': []}
    return cad


def _libres_pagables(estado: dict, equipo) -> list:
    """Libres que `equipo` puede contratar hoy: los que puede pagar, sin el que acaban de despedir."""
    movidos = set(_cadena(estado)['movidos'])
    return [x for x in dts(estado)['libres']
            if not x.get('interino') and x.get('id') not in movidos and puede_pagar(equipo, x)]


def mejor_libre(estado: dict, equipo) -> dict:
    """
    Saca de la bolsa al libre con mejor calif que `equipo` puede pagar. Si no le alcanza para
    ninguno, contrata a uno nuevo y barato (el sueldo que el club puede pagar).
    """
    d = dts(estado)
    candidatos = _libres_pagables(estado, equipo)
    if not candidatos:
        rng = random.Random(d['sig_id'])
        tope = max(SUELDO_DT_MIN, int(FRAC_SUELDO_DT * max(0, int(getattr(equipo, 'balance', 0) or 0))))
        calif = rng.randint(30, 50)
        nom = nombre_generado(rng)
        return _nuevo(estado, nom, rng.choice(ESTILOS_DT), calif,
                      sueldo_anual=min(sueldo_pedido(calif), tope),
                      nacionalidad=_nacionalidad_dt(estado, nom, equipo, rng))
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
    """El user deja `viejo` y toma `nuevo`: el DT de `nuevo` va a libres y `viejo` cubre su vacante como
    cualquier club de la IA (v0.4.22.0: entra en la cadena y sale en Noticias; a ti no te lo vuelve a ofrecer)."""
    d = dts(estado)
    saliente = d['por_club'].pop(str(getattr(nuevo, 'id', '')), None)
    if viejo is not None and viejo is not nuevo:
        _eq, liga = _club_por_id(estado, getattr(viejo, 'id', ''))
        if cubrir_vacante(estado, viejo, liga, ofrecer=False) is None:
            contratar(estado, viejo)             # `mi_equipo` aún era el viejo: no entra en la cadena, pero no queda sin DT
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


# v0.4.11.0: (calificación mínima, piso, techo) de media respecto de la tuya. Antes solo había
# techo y cualquier club más flojo podía ofrecerte el banquillo.
BANDAS_OFERTA = ((70, -2, 10), (55, -4, 5), (0, -6, 0))


def en_banda(estado: dict, equipo) -> bool:
    """¿El club está a tu alcance según tu calificación? (≥70: −2 a +10 · ≥55: −4 a +5 · resto: −6 a 0)."""
    from alpha_football.directiva import calif_dt
    mi = estado.get('mi_equipo')
    if mi is None:
        return False
    c, ovr, suyo = calif_dt(estado), mi.ovr_promedio, getattr(equipo, 'ovr_promedio', 0)
    piso, techo = next((p, t) for minimo, p, t in BANDAS_OFERTA if c >= minimo)
    return ovr + piso <= suyo <= ovr + techo


def despedir(estado: dict, equipo, liga, motivo: str) -> dict:
    """Saca al DT del club (a libres con calif −10) y lo anota. Retorna el DT despedido.
    v0.4.22.0: ya no envía el correo "Cambio de DT"; la noticia la publica cubrir_vacante (`saliente=`)."""
    d = dts(estado)
    viejo = d['por_club'].pop(str(equipo.id), None) or {}
    if viejo and not viejo.get('interino'):
        # copia: no se muta el dict que el llamador pueda tener (p. ej. dt_de de antes)
        d['libres'].append({**viejo, 'calif': max(0, int(viejo['calif']) - 10)})
        _cadena(estado)['movidos'].append(viejo['id'])       # hoy no lo contrata nadie (tampoco el club que lo echó)
    d['historial'].append({'temporada': int(estado.get('temporada', 1) or 1), 'club': equipo.nombre,
                           'dt': viejo.get('nombre', '?'), 'motivo': motivo})
    del d['historial'][:-300]
    return viejo


def _reemplazar(estado: dict, equipo) -> None:
    contratar(estado, equipo)


# ── v0.4.22.0: cadena de contrataciones ──────────────────────────────────────

MAX_CADENA = 4                  # robos de DT entre clubes por jornada (todas las ligas juntas)
INTENTOS_ROBO = 3               # candidatos a los que el club llama antes de ir al banco
PROB_ACEPTA_ROBO = 0.6
SUBE_SUELDO_ROBO = 1.2          # el DT que cambia de club renegocia al alza
MARGEN_ROBO = 0.5               # el club de origen debe tener al menos esta media de menos


def _importancia(estado: dict, liga) -> int:
    """4 en 1ª división o en tu país; 2 en la 2ª de otros países (se ve en Noticias, no entra al feed)."""
    if int(getattr(liga, 'division', 1) or 1) <= 1 or getattr(liga, 'tipo', None) == getattr(estado.get('liga'), 'tipo', ''):
        return 4
    return 2


def _noticia(estado: dict, liga, titulares: tuple, cuerpo: str, equipos: list, tecnicos: list) -> None:
    try:
        from alpha_football import noticias
        noticias.publicar(estado, 'dt_cambio', noticias.titular(*titulares), cuerpo,
                          importancia=_importancia(estado, liga), equipos=equipos, dts=tecnicos)
    except Exception as e:
        logger.error(f"No se pudo publicar la noticia de DT: {e}")


def _noticia_llegada(estado: dict, equipo, liga, dt: dict, origen=None, saliente: Optional[dict] = None,
                     motivo: str = '', se_fue_a: str = '') -> None:
    """Una sola noticia por vacante cubierta: quién llega (de otro club o del banco), a quién reemplaza y
    por qué quedó libre el banquillo (lo despidieron o se fue a `se_fue_a`). Sin `saliente` conocido (venció tu
    oferta, dejaste tú el club), solo la llegada."""
    nom, club = dt['nombre'], equipo.nombre
    llega = f"que deja el banquillo de {origen.nombre}" if origen is not None else "que estaba sin club"
    equipos = [equipo] + ([origen] if origen is not None else [])
    if not saliente or saliente.get('interino'):
        _noticia(estado, liga, (f"{nom} firma por el {club}", f"{club} ficha a {nom}", f"{club} ya tiene nuevo técnico"),
                 f"{club} presentó como su nuevo entrenador a {nom}, {llega}.", equipos, [dt])
        return
    viejo = saliente.get('nombre', 'su entrenador')
    causa = (f"{viejo} dejó {club} para dirigir a {se_fue_a}." if se_fue_a
             else f"{club} despidió a {viejo}{f' ({motivo})' if motivo else ''}.")
    _noticia(estado, liga, (f"{nom} reemplaza a {viejo} en el {club}", f"{club}: {nom} por {viejo}",
                            f"{club} cambia de técnico"),
             f"{causa} Su reemplazo es {nom}, {llega}.", equipos, [dt, saliente])


def _sueldo_robo(dt: dict) -> int:
    return max(int(sueldo(dt) * SUBE_SUELDO_ROBO), sueldo_pedido(dt.get('calif', 45)))


def _candidatos_robo(estado: dict, equipo, liga) -> list:
    """[(dt, club de origen, su liga)] que `equipo` puede intentar llevarse, en orden de preferencia: DTs de
    clubes de la IA de menor nivel (media inferior, o la división de abajo de su país), mejores que el mejor
    libre que puede pagar, que no se hayan movido hoy y cuyo sueldo nuevo le alcance. Misma liga → mismo
    país → mismo continente; a igualdad, el del estilo del DT que se fue y luego la mejor calificación."""
    from alpha_football.temporadas import continente_de
    movidos = set(_cadena(estado)['movidos'])
    tipo, div = getattr(liga, 'tipo', ''), int(getattr(liga, 'division', 1) or 1)
    ovr = float(getattr(equipo, 'ovr_promedio', 0) or 0)
    piso = max((int(x.get('calif', 0) or 0) for x in _libres_pagables(estado, equipo)), default=-1)
    tope = FRAC_SUELDO_DT * max(0, int(getattr(equipo, 'balance', 0) or 0))
    estilo = getattr(equipo, 'estilo_dt', '')
    out = []
    for origen, liga_o in clubes(estado):
        dt = dt_de(estado, origen)
        if origen is equipo or _es_mi(estado, origen) or not dt or dt.get('interino') or dt.get('id') in movidos:
            continue
        tipo_o, div_o = getattr(liga_o, 'tipo', ''), int(getattr(liga_o, 'division', 1) or 1)
        if continente_de(tipo_o) != continente_de(tipo):
            continue
        menor = float(getattr(origen, 'ovr_promedio', 0) or 0) <= ovr - MARGEN_ROBO or (tipo_o == tipo and div_o > div)
        if not menor or int(dt.get('calif', 0) or 0) <= piso or _sueldo_robo(dt) > tope:
            continue
        cerca = 0 if liga_o is liga else 1 if tipo_o == tipo else 2
        out.append(((cerca, dt.get('estilo') != estilo, -int(dt['calif'])), dt, origen, liga_o))
    out.sort(key=lambda x: x[0])
    return [(dt, origen, liga_o) for _orden, dt, origen, liga_o in out]


def cubrir_vacante(estado: dict, equipo, liga, rng: Optional[random.Random] = None, motivo: str = '',
                   ofrecer: bool = True, se_fue_a: str = '', saliente: Optional[dict] = None) -> Optional[dict]:
    """Un club de la IA sin DT (o con interino) busca técnico. Devuelve el DT que llega (None si se queda con
    un interino a la espera de tu respuesta).
    1) Si entra en tu banda puede ofrecerte el banquillo, como en los despidos de siempre. Con `ofrecer=False`
       no se te ofrece ni esta vacante ni las que deje la cadena (cierre de temporada, o acabas de cambiar de club).
    2) Si no, intenta robárselo a un club menor: hasta INTENTOS_ROBO candidatos, cada uno acepta con
       PROB_ACEPTA_ROBO; el club de origen queda vacante y repite el proceso (`se_fue_a` = adónde se fue su DT).
    3) Sin robo, o agotados los MAX_CADENA movimientos de la jornada, contrata del banco.
    `saliente` (el DT que dejó la vacante, despedido con `motivo` o marchado a `se_fue_a`) va a la noticia: una
    sola por vacante, "{nuevo} reemplaza a {viejo} en el {club}"."""
    if _es_mi(estado, equipo):
        return None
    azar = rng or random.Random()
    if ofrecer and en_banda(estado, equipo) and puede_ofrecer_al_user(estado) and azar.random() < PROB_OFERTA_USER:
        if saliente and not saliente.get('interino') and not se_fue_a:     # el reemplazo tardará: el despido ya es noticia
            nom = saliente.get('nombre', 'su entrenador')
            _noticia(estado, liga, (f"El {equipo.nombre} despide a {nom}", f"{equipo.nombre} despide a {nom}",
                                    f"{equipo.nombre} despide a su técnico"),
                     f"{equipo.nombre} anunció la salida de {nom}{f' ({motivo})' if motivo else ''}. Un interino "
                     "dirige al equipo mientras la directiva busca a su reemplazo.", [equipo], [saliente])
        _ofrecer_al_user(estado, equipo, liga, motivo, se_fue_a)
        return None
    cad = _cadena(estado)
    if cad['mov'] < MAX_CADENA:
        for dt, origen, liga_o in _candidatos_robo(estado, equipo, liga)[:INTENTOS_ROBO]:
            if azar.random() >= PROB_ACEPTA_ROBO:
                continue
            dts(estado)['por_club'].pop(str(origen.id), None)
            dt['sueldo'] = _sueldo_robo(dt)
            equipo.balance = int(getattr(equipo, 'balance', 0) or 0) - sueldo(dt)
            asignar(estado, equipo, dt)
            cad['mov'] += 1
            cad['movidos'].append(dt['id'])
            _noticia_llegada(estado, equipo, liga, dt, origen, saliente, motivo, se_fue_a)
            cubrir_vacante(estado, origen, liga_o, azar, ofrecer=ofrecer, se_fue_a=equipo.nombre, saliente=dt)
            return dt
    dt = contratar(estado, equipo)
    cad['movidos'].append(dt['id'])
    _noticia_llegada(estado, equipo, liga, dt, None, saliente, motivo, se_fue_a)
    return dt


def _ofrecer_al_user(estado: dict, equipo, liga, motivo: str = "", se_fue_a: str = "") -> None:
    """El club juega con un interino y te escribe: la oferta dura JORNADAS_OFERTA jornadas.
    `se_fue_a` (v0.4.22.0): la vacante no viene de un despido, su DT se marchó a ese club."""
    from alpha_football import correo as C
    from alpha_football.directiva import calif_dt
    d = dts(estado)
    rng = random.Random(f"interino-{equipo.id}-{estado.get('temporada', 1)}")
    nom = nombre_generado(rng)
    asignar(estado, equipo, _nuevo(estado, nom + " (interino)", 'anchelottismo', 40, interino=True,
                                   nacionalidad=_nacionalidad_dt(estado, nom, equipo, rng)))
    d['ofertas'].append({'club_id': str(equipo.id), 'club': equipo.nombre, 'liga': getattr(liga, 'nombre', ''),
                         'jornadas': JORNADAS_OFERTA, 'temporada': int(estado.get('temporada', 1) or 1),
                         'motivo': motivo})
    if se_fue_a:
        d['ofertas'][-1]['causa'] = f"Su DT se marchó a {se_fue_a}"
    causa = (f"Tras la marcha de nuestro entrenador a {se_fue_a}" if se_fue_a
             else f"Tras despedir a nuestro entrenador{f' ({motivo})' if motivo else ''}")
    # v4.7.0: el correo dice por qué te quieren (despido + tu calificación)
    C.enviar(estado, 'club', f"{equipo.nombre} te quiere como DT",
             f"{causa} y en vista de su "
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
            eq, lg = _club_por_id(estado, o['club_id'])
            if eq is not None and (dt_de(estado, eq) or {}).get('interino'):
                cubrir_vacante(estado, eq, lg, azar, ofrecer=False)
    for eq, liga in clubes(estado):                    # 2) despidos de la IA
        if _es_mi(estado, eq) or dt_de(estado, eq) is None or dt_de(estado, eq).get('interino'):
            continue
        if dt_de(estado, eq).get('id') in _cadena(estado)['movidos']:
            continue                                   # v0.4.22.0: llegó en esta misma jornada
        n = max(1, int(getattr(liga, 'num_jornadas', 10) or 10))
        if int(getattr(liga, 'jornada_actual', 1) or 1) <= n / 3:
            continue
        if d['despidos_temp'].get(_clave_liga(liga), 0) >= 1 or not _va_mal(liga, eq):
            continue
        if azar.random() >= PROB_DESPIDO_JORNADA:
            continue
        motivo = f"iba {posicion(liga, eq)}º y se esperaba {esperado(liga, eq)}º"
        viejo = despedir(estado, eq, liga, motivo)
        d['despidos_temp'][_clave_liga(liga)] = d['despidos_temp'].get(_clave_liga(liga), 0) + 1
        cubrir_vacante(estado, eq, liga, azar, motivo, saliente=viejo)   # v0.4.22.0: oferta al user, robo a otro club o banco
    mantener_banco(estado, azar)


def cierre_temporada(estado: dict, rng: Optional[random.Random] = None, paises=None) -> None:
    """Fin de temporada: los que terminaron 3+ puestos bajo lo esperado echan con 50%.
    v0.4.16.0: con `paises`, solo los clubes de esos países (el cierre de un continente); las ofertas de
    banquillo y los despidos de la temporada solo se reinician si el cierre incluye a tu país."""
    azar = rng or random.Random()
    d = dts(estado)
    filtro = set(paises) if paises is not None else None
    for eq, liga in clubes(estado):
        if filtro is not None and getattr(liga, 'tipo', None) not in filtro:
            continue
        if _es_mi(estado, eq):
            continue
        dt = dt_de(estado, eq)
        # v0.4.22.0: las vacantes del cierre no se te ofrecen (las ofertas se borran al terminar la temporada)
        if dt is None or dt.get('interino'):
            cubrir_vacante(estado, eq, liga, azar, ofrecer=False)
        elif dt.get('id') in _cadena(estado)['movidos']:
            continue                                 # llegó en este mismo cierre
        elif posicion(liga, eq) >= esperado(liga, eq) + PUESTOS_BAJO and azar.random() < PROB_DESPIDO_CIERRE:
            viejo = despedir(estado, eq, liga, "no cumplió en la temporada")
            cubrir_vacante(estado, eq, liga, azar, "no cumplió en la temporada", ofrecer=False, saliente=viejo)
    mantener_banco(estado, azar)
    if filtro is not None and getattr(estado.get('liga'), 'tipo', None) not in filtro:
        return                                   # no es tu cierre: tu temporada sigue
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
    """Rechazas: el club busca otro DT (se lo roba a un club menor o contrata al mejor libre)."""
    d = dts(estado)
    d['ofertas'] = [o for o in d['ofertas'] if o['club_id'] != str(club_id)]
    eq, lg = _club_por_id(estado, club_id)
    if eq is not None and (dt_de(estado, eq) or {}).get('interino'):
        cubrir_vacante(estado, eq, lg, ofrecer=False)
