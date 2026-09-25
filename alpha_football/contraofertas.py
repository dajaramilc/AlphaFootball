# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Contraofertas y "lo analizamos" (v3.5.0)
Ventas: cada oferta recibida tiene un tope oculto; contraofertar dentro del tope cierra la venta, hasta
+30% del tope queda "en análisis" (respuesta por correo en la jornada siguiente, 50/50) y más arriba
se retira. Compras: las ofertas del user entre el 85% y el 100% del mínimo del club se analizan igual
(negociacion.evaluar_compra) y se resuelven aquí.
"""
from __future__ import annotations

import logging
import random
from typing import Optional

logger = logging.getLogger(__name__)

TOPE_RANGO = (1.10, 1.35)
MARGEN_ANALISIS = 1.30
PROB_ACEPTA_ANALISIS = 0.5
RETENCION_CLUB = 0.25        # v4.4.0: de cada venta el club se queda el 25%; el resto va al presupuesto


def acreditar_venta(estado: dict, jugador, comprador, monto: int, asunto: Optional[str] = None) -> int:
    """v4.4.0: cobra una venta del user (75% al presupuesto) y avisa por correo. Retorna lo acreditado."""
    monto = int(monto or 0)
    neto = monto - int(monto * RETENCION_CLUB)
    mi = estado.get('mi_equipo')
    if mi is not None:
        mi.balance += neto
    try:
        from alpha_football.finanzas import registrar
        registrar(estado, 'ventas', neto)
    except Exception as e:
        logger.error(f"acreditar_venta: no se pudo registrar el ingreso: {e}")
    try:
        from alpha_football import correo as C
        from alpha_football.negociacion import dinero_exacto
        nombre = getattr(jugador, 'nombre_completo', None) or f"{jugador.nombre} {jugador.apellido}"
        C.enviar(estado, 'directiva', asunto or f"Venta cerrada: {nombre}",
                 f"Se vendió a {nombre} a {getattr(comprador, 'nombre', 'otro club')} por {dinero_exacto(monto)}. "
                 f"El club retiene el {int(RETENCION_CLUB * 100)}%: designamos {dinero_exacto(neto)} a presupuesto.",
                 C.accion('historial_pases_screen', "VER HISTORIAL"))
    except Exception as e:
        logger.error(f"acreditar_venta: no se pudo enviar el correo: {e}")
    return neto


def _jornada(estado: dict) -> int:
    return int(getattr(estado.get('liga'), 'jornada_actual', 1) or 1)


def asignar_tope(of: dict, rng: Optional[random.Random] = None) -> int:
    """v3.5.0: tope oculto del comprador (se fija una sola vez por oferta)."""
    if 'tope' not in of:
        azar = rng or random.Random()
        monto = int(of.get('monto', 0) or 0)
        tope = int(monto * azar.uniform(*TOPE_RANGO))
        if not of.get('exterior'):
            tope = min(tope, max(monto, int(getattr(of.get('comprador'), 'balance', 0) or 0)))
        of['tope'] = tope
    return int(of['tope'])


def retirar(estado: dict, of: dict) -> None:
    estado['ofertas_recibidas'] = [o for o in (estado.get('ofertas_recibidas') or []) if o is not of]


def vender(estado: dict, of: dict) -> bool:
    """Cierra la venta de `of` (lógica que antes vivía en ofertas_screen._aceptar). True si vendió."""
    mi_equipo = estado.get('mi_equipo')
    jug = of.get('jugador'); comp = of.get('comprador'); monto = of.get('monto', 0)
    if not mi_equipo or not jug or not comp:
        return False
    if jug not in mi_equipo.jugadores:
        # v2.9.1: oferta vieja (ya vendido, venta forzada o se fue libre): no cobrar ni duplicar.
        logger.warning(f"Oferta descartada: {getattr(jug, 'nombre_completo', '?')} ya no está en tu plantilla.")
        return False
    estado['ofertas_recibidas'] = [o for o in (estado.get('ofertas_recibidas') or [])
                                   if o.get('jugador') is not jug]
    try:
        from alpha_football.finanzas import quitar_de_plantilla
        quitar_de_plantilla(mi_equipo, jug)     # v2.9.0: reindexa la alineación
        acreditar_venta(estado, jug, comp, monto)     # v4.4.0: 25% para el club + correo
        comp.jugadores.append(jug)
        jug.transferible = jug.pide_salir = False     # v3.1.0
        try:  # v4.4.0: se borra la escalada de salida
            from alpha_football.salidas import limpiar as _limpiar_salida
            _limpiar_salida(jug)
        except Exception as e_lim:
            logger.error(f"No se pudo limpiar la salida: {e_lim}")
        try:
            comp.balance = max(0, comp.balance - monto)
        except Exception:
            pass
        try:  # v2.7.0: historial propio de pases
            from alpha_football.negociacion import registrar_pase
            registrar_pase(estado, jug, mi_equipo.nombre, comp.nombre, monto, True)
        except Exception as e_hist:
            logger.error(f"No se pudo registrar la venta: {e_hist}")
        # v0.8.2: solo generar suplente si la plantilla cae por debajo de 15.
        try:
            from alpha_football.finanzas import completar_plantilla
            completar_plantilla(mi_equipo)          # v2.9.1: con portero y contrato
            estado.setdefault('transfer_log', []).append(
                f"Venta: {jug.nombre_completo} -> {comp.nombre} por ${monto:,}")
        except Exception as e_rep:
            logger.error(f"No se pudo generar reemplazo: {e_rep}")
        return True
    except Exception as e:
        logger.error(f"Error al aceptar oferta: {e}")
        return False


def contraofertar(estado: dict, of: dict, pedido: int, rng: Optional[random.Random] = None) -> tuple:
    """v3.5.0: ('aceptada'|'analizando'|'rechazada'|'invalida', mensaje)."""
    from alpha_football.negociacion import dinero_exacto
    pedido = int(pedido or 0)
    comp = getattr(of.get('comprador'), 'nombre', 'El club')
    if of.get('contra'):
        return 'invalida', "Ya contraofertaste por esta oferta."
    if pedido <= int(of.get('monto', 0) or 0):
        return 'invalida', "La contraoferta tiene que superar la oferta."
    tope = asignar_tope(of, rng)
    if pedido <= tope:
        of['monto'] = pedido
        vender(estado, of)
        return 'aceptada', f"{comp} acepta {dinero_exacto(pedido)}."
    if pedido <= int(tope * MARGEN_ANALISIS):
        of['contra'] = {'pedido': pedido, 'estado': 'analizando', 'jornada': _jornada(estado)}
        return 'analizando', f"{comp}: \"Lo analizamos\". Te responden por correo en la próxima jornada."
    retirar(estado, of)
    return 'rechazada', f"{comp} considera excesivo {dinero_exacto(pedido)} y retira la oferta."


def _resolver_ventas(estado: dict, azar: random.Random) -> None:
    from alpha_football import correo as C
    from alpha_football.negociacion import dinero_exacto
    mi = estado.get('mi_equipo')
    for of in list(estado.get('ofertas_recibidas') or []):
        c = of.get('contra') or {}
        if c.get('estado') != 'analizando' or _jornada(estado) <= int(c.get('jornada', 0)):
            continue
        jug, comp = of.get('jugador'), of.get('comprador')
        if mi is None or jug not in mi.jugadores:
            retirar(estado, of)          # v3.5.0: ya no está → se descarta en silencio
            continue
        nombre = getattr(jug, 'nombre_completo', '?')
        if azar.random() < PROB_ACEPTA_ANALISIS:
            of['monto'] = int(c['pedido'])
            vender(estado, of)
            C.enviar(estado, 'club', f"{comp.nombre} acepta tu contraoferta",
                     f"{nombre} se va a {comp.nombre} por {dinero_exacto(c['pedido'])}.")
        else:
            retirar(estado, of)
            C.enviar(estado, 'club', f"{comp.nombre} se retira",
                     f"No pagará {dinero_exacto(c['pedido'])} por {nombre}. La oferta quedó sin efecto.")


def _resolver_compras(estado: dict, azar: random.Random) -> None:
    from alpha_football import correo as C
    from alpha_football.negociacion import dinero_exacto, minimo_club, buscar_en_club
    dc = estado.setdefault('datos_carrera', {})
    pend = dc.setdefault('analisis_compras', [])
    for a in list(pend):
        if _jornada(estado) <= int(a.get('jornada', 0)):
            continue
        pend.remove(a)
        club, j = buscar_en_club(estado, a['club_id'], a['jugador_id'])
        if club is None or j is None:
            continue
        if azar.random() < PROB_ACEPTA_ANALISIS:
            compra = {k: a[k] for k in ('jugador_id', 'club_id', 'monto', 'temporada')}
            C.enviar(estado, 'club', f"{club.nombre} acepta tu oferta",
                     f"Aceptan {dinero_exacto(a['monto'])} por {j.nombre_completo}. "
                     "Negocia el contrato con el jugador mientras la ventana siga abierta.",
                     {'pantalla': 'negociacion_screen', 'texto': "NEGOCIAR CONTRATO", 'compra': compra})
        else:
            C.enviar(estado, 'club', f"{club.nombre} rechaza tu oferta",
                     f"No vende a {j.nombre_completo} por {dinero_exacto(a['monto'])}. "
                     f"Pide {dinero_exacto(minimo_club(j, club))}.")


def _ubicar_contrato(estado: dict, a: dict) -> tuple:
    """(jugador, club, motivo_si_no_se_puede) de un contrato en análisis."""
    from alpha_football.negociacion import buscar_en_club
    mi = estado.get('mi_equipo')
    if a['modo'] == 'renovar':
        j = next((x for x in getattr(mi, 'jugadores', []) or [] if str(x.id) == str(a['jugador_id'])), None)
        return j, None, None if j is not None else "Ya no está en tu plantilla."
    if int(a.get('temporada', -1)) != int(estado.get('temporada', 1) or 1):
        return None, None, "El acuerdo era de otra temporada."
    from alpha_football.market import ventana_mercado_abierta
    liga = estado.get('liga')
    if liga is None or not ventana_mercado_abierta(liga.jornada_actual, liga.num_jornadas):
        return None, None, "La ventana de fichajes se cerró."
    if a.get('club_id') is None:
        j = next((x for x in estado.get('free_agents_list') or []
                  if str(x.id) == str(a['jugador_id']) and x.nombre_completo == a['jugador']), None)
        return j, None, None if j is not None else "Firmó con otro club."
    club, j = buscar_en_club(estado, a['club_id'], a['jugador_id'])
    return j, club, None if j is not None else "Ya no está en ese club."


def _resolver_contratos(estado: dict, azar: random.Random) -> None:
    """v4.4.0: respuesta del jugador a un contrato "en análisis" (fichaje o renovación)."""
    from alpha_football import correo as C
    from alpha_football import negociacion as N
    dc = estado.setdefault('datos_carrera', {})
    pend = dc.setdefault('analisis_contratos', [])
    temporada = int(estado.get('temporada', 1) or 1)
    for a in list(pend):
        if int(a.get('temporada', temporada)) == temporada and _jornada(estado) <= int(a.get('jornada', 0)):
            continue
        pend.remove(a)
        nombre, renueva = a.get('jugador', '?'), a['modo'] == 'renovar'
        j, club, motivo = _ubicar_contrato(estado, a)
        if j is None:
            C.enviar(estado, 'jugador', f"{nombre}: contrato sin efecto", motivo or "No se pudo cerrar el contrato.")
            continue
        if azar.random() >= PROB_ACEPTA_ANALISIS:
            pedido = N.salario_pedido(j, a['modo'], a['clausula_mult'])
            C.enviar(estado, 'jugador', f"{nombre} no acepta tu propuesta",
                     f"No firma por {N.dinero_exacto(a['salario'])} al año. Pide {N.dinero_exacto(pedido)}.",
                     C.accion('plantilla_screen', "VER PLANTILLA") if renueva else None)
            continue
        if renueva:
            N.renovar(estado, j, a['salario'], a['anios'], a['clausula_mult'])
            C.enviar(estado, 'jugador', f"{nombre} acepta renovar",
                     f"Firma hasta {a['anios']} años por {N.dinero_exacto(a['salario'])} al año.",
                     C.accion('plantilla_screen', "VER PLANTILLA"))
            continue
        ok, msg = N.completar_fichaje(estado, j, club, a['monto'], a['salario'], a['anios'], a['clausula_mult'])
        if not ok:   # si ficha, fichar() ya manda el correo de llegada
            C.enviar(estado, 'jugador', f"{nombre} aceptó, pero no se pudo cerrar", msg)


def resolver_analisis(estado: dict, rng: Optional[random.Random] = None) -> None:
    """Hook de cada jornada de liga del user."""
    azar = rng or random.Random()
    for paso in (_resolver_ventas, _resolver_compras, _resolver_contratos):
        try:
            paso(estado, azar)
        except Exception as e:
            logger.error(f"resolver_analisis ({paso.__name__}): {e}", exc_info=True)
