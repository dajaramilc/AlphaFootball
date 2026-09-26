# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Traspasos acordados con el mercado cerrado
Vender o comprar fuera de la ventana cierra el trato y mueve el dinero en el momento, pero el
jugador se queda en su club hasta que se abre el mercado (jornada n−2). Se guardan en
datos_carrera['traspasos_pendientes'] (sobreviven a guardar/cargar) y se ejecutan al cerrar la
jornada que abre la ventana, antes de que ficha la IA. Correo al acordar y al concretarse. Sin UI.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _dc(estado: dict) -> dict:
    return estado.setdefault('datos_carrera', {})


def _pendientes(estado: dict) -> list:
    return _dc(estado).setdefault('traspasos_pendientes', [])


def _nombre(j) -> str:
    return getattr(j, 'nombre_completo', None) or f"{getattr(j, 'nombre', '')} {getattr(j, 'apellido', '')}".strip()


def mercado_abierto(estado: dict) -> bool:
    liga = estado.get('liga')
    if liga is None:
        return True
    from alpha_football.market import ventana_mercado_abierta
    return ventana_mercado_abierta(int(getattr(liga, 'jornada_actual', 1) or 1),
                                   int(getattr(liga, 'num_jornadas', 22) or 22))


def jornada_apertura(estado: dict) -> int:
    """Jornada en la que vuelve a abrir el mercado (invierno o las 3 últimas de la liga)."""
    from alpha_football.market import proxima_apertura
    liga = estado.get('liga')
    return proxima_apertura(int(getattr(liga, 'jornada_actual', 1) or 1),
                            int(getattr(liga, 'num_jornadas', 22) or 22))


def pendiente_de(estado: dict, jugador) -> Optional[dict]:
    """El traspaso acordado de este jugador (venta o compra), si lo hay."""
    nombre, jid = _nombre(jugador), str(getattr(jugador, 'id', ''))
    return next((p for p in _pendientes(estado)
                 if p.get('jugador') == nombre and str(p.get('jugador_id')) == jid), None)


def diferir_venta(estado: dict, jugador, comprador, monto: int) -> str:
    """Venta cerrada con el mercado cerrado: queda anotada. Devuelve el texto para el correo."""
    j_ap = jornada_apertura(estado)
    mi = estado.get('mi_equipo')
    _pendientes(estado).append({
        'tipo': 'venta', 'jugador': _nombre(jugador), 'jugador_id': getattr(jugador, 'id', None),
        'origen': getattr(mi, 'nombre', ''), 'destino': getattr(comprador, 'nombre', ''),
        'monto': int(monto or 0), 'jornada': j_ap, 'temporada': int(estado.get('temporada', 1) or 1)})
    try:   # ya está vendido: deja de pedir salir (no sigue la escalada con la directiva)
        from alpha_football.salidas import limpiar
        limpiar(jugador)
    except Exception as e:
        logger.error(f"No se pudo limpiar la salida de {_nombre(jugador)}: {e}")
    # el comprador puede ser un club que no está en las ligas vivas (ofertas del exterior)
    estado.setdefault('_compradores_pendientes', {})[_nombre(jugador)] = comprador
    return f"{_nombre(jugador)} se irá a {getattr(comprador, 'nombre', 'su nuevo club')} en la jornada {j_ap}, en cuanto se abra el mercado."


def diferir_compra(estado: dict, jugador, club, monto: int) -> str:
    """Compra cerrada con el mercado cerrado: queda anotada. Devuelve el texto para el correo."""
    j_ap = jornada_apertura(estado)
    mi = estado.get('mi_equipo')
    reg = {'tipo': 'compra', 'jugador': _nombre(jugador), 'jugador_id': getattr(jugador, 'id', None),
           'origen': getattr(club, 'nombre', None), 'destino': getattr(mi, 'nombre', ''),
           'monto': int(monto or 0), 'jornada': j_ap, 'temporada': int(estado.get('temporada', 1) or 1)}
    if club is None:
        # agente libre: no está en ningún club, se guarda entero (la lista de libres no se guarda)
        reg['datos'] = jugador.to_dict()
    _pendientes(estado).append(reg)
    return f"{_nombre(jugador)} llegará en la jornada {j_ap}, en cuanto se abra el mercado."


def actualizar_datos(estado: dict, jugador) -> None:
    """Tras fijar el contrato de un agente libre pendiente, se guarda con su contrato nuevo."""
    p = pendiente_de(estado, jugador)
    if p is not None and 'datos' in p:
        p['datos'] = jugador.to_dict()


def _equipos(estado: dict) -> list:
    out = []
    try:
        from alpha_football.mercado_ia import ligas_de_la_partida
        out = [eq for liga, _t, _d in ligas_de_la_partida(estado) for eq in liga.equipos]
    except Exception as e:
        logger.error(f"traspasos pendientes: no se pudieron leer las ligas: {e}")
    try:
        from alpha_football.negociacion import clubes_internacionales
        out += [eq for eq, _et in clubes_internacionales(estado)]
    except Exception as e:
        logger.error(f"traspasos pendientes: no se pudieron leer los clubes internacionales: {e}")
    mi = estado.get('mi_equipo')
    if mi is not None and all(eq is not mi for eq in out):
        out.append(mi)
    return out


def _club(estado: dict, nombre: Optional[str]):
    mi = estado.get('mi_equipo')
    if mi is not None and getattr(mi, 'nombre', None) == nombre:
        return mi
    return next((eq for eq in _equipos(estado) if getattr(eq, 'nombre', None) == nombre), None)


def _buscar_jugador(club, p: dict):
    return next((j for j in getattr(club, 'jugadores', []) or []
                 if _nombre(j) == p['jugador'] and str(j.id) == str(p['jugador_id'])), None)


def _ejecutar_venta(estado: dict, p: dict) -> None:
    from alpha_football import correo as C
    origen = _club(estado, p['origen'])
    j = _buscar_jugador(origen, p) if origen is not None else None
    if j is None:
        logger.warning(f"Venta pendiente sin jugador: {p['jugador']} ya no está en {p['origen']}")
        return
    destino = (estado.get('_compradores_pendientes') or {}).pop(p['jugador'], None) or _club(estado, p['destino'])
    from alpha_football.finanzas import quitar_de_plantilla, completar_plantilla
    quitar_de_plantilla(origen, j)
    if destino is not None:
        destino.jugadores.append(j)
        destino.alineacion_activa = None
    try:
        from alpha_football.salidas import limpiar
        limpiar(j)
    except Exception as e:
        logger.error(f"No se pudo limpiar la salida de {p['jugador']}: {e}")
    if origen is estado.get('mi_equipo'):
        completar_plantilla(origen)
    try:
        from alpha_football.negociacion import registrar_pase
        registrar_pase(estado, j, p['origen'], p['destino'], p['monto'], origen is estado.get('mi_equipo'))
    except Exception as e:
        logger.error(f"No se pudo registrar el pase de {p['jugador']}: {e}")
    C.enviar(estado, 'club', f"{p['jugador']} ya se fue",
             f"Se abrió el mercado: {p['jugador']} dejó el club y ya es jugador de {p['destino']}.",
             C.accion('plantilla_screen', "VER PLANTILLA"))


def _ejecutar_compra(estado: dict, p: dict) -> None:
    from alpha_football import correo as C
    destino = _club(estado, p['destino']) or estado.get('mi_equipo')
    if p.get('datos'):
        from alpha_football.models import Jugador
        j = Jugador.from_dict(p['datos'])
    else:
        origen = _club(estado, p['origen'])
        j = _buscar_jugador(origen, p) if origen is not None else None
        if j is None:
            # el jugador desapareció (retiro, base editada...): se devuelve el dinero
            if destino is not None:
                destino.balance = int(getattr(destino, 'balance', 0) or 0) + int(p['monto'])
            C.enviar(estado, 'club', f"Se cayó el fichaje de {p['jugador']}",
                     f"{p['jugador']} ya no está en {p['origen']}. Te devolvieron ${int(p['monto']):,}.")
            return
        origen.jugadores.remove(j)
        origen.alineacion_activa = None
    if destino is None:
        return
    destino.jugadores.append(j)
    try:
        from alpha_football.negociacion import registrar_pase, avisar_llegada
        registrar_pase(estado, j, p['origen'] or 'Libre', p['destino'], p['monto'], True)
        if destino is estado.get('mi_equipo'):
            avisar_llegada(estado, j)
    except Exception as e:
        logger.error(f"No se pudo registrar la llegada de {p['jugador']}: {e}")


def ejecutar(estado: dict) -> int:
    """Con el mercado abierto, concreta los traspasos acordados. Devuelve cuántos se hicieron."""
    pend = _pendientes(estado)
    if not pend or not mercado_abierto(estado):
        return 0
    hechos = 0
    for p in list(pend):
        pend.remove(p)
        try:
            if p.get('tipo') == 'venta':
                _ejecutar_venta(estado, p)
            else:
                _ejecutar_compra(estado, p)
            hechos += 1
        except Exception as e:
            logger.error(f"No se pudo concretar el traspaso de {p.get('jugador')}: {e}", exc_info=True)
    return hechos


def limpiar_ofertas(estado: dict) -> None:
    """Un jugador ya vendido (esperando la ventana) no recibe más ofertas."""
    ventas = {(p['jugador'], str(p['jugador_id'])) for p in _pendientes(estado) if p.get('tipo') == 'venta'}
    if not ventas:
        return
    estado['ofertas_recibidas'] = [
        o for o in estado.get('ofertas_recibidas') or []
        if (_nombre(o.get('jugador')), str(getattr(o.get('jugador'), 'id', ''))) not in ventas]
