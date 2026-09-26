# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Carrera del DT (v3.2.0)
Contrato del DT (sueldo, años), patrimonio personal (no toca la caja del club),
indemnización al ser despedido y oferta de renovación por correo a mitad de temporada.
Estado en datos_carrera: contrato_dt, patrimonio_dt, renovacion_dt.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

SUELDO_MIN = 100_000
SUELDO_PCT_BALANCE = 0.04
VARIANTES = [(1, 1.25), (2, 1.0), (3, 0.85)]     # (años, multiplicador del sueldo base)
BONO_RENOVACION = 1.10
CALIF_RENOVAR = 60
INDEMNIZACION_FRAC = 0.5


def _dc(estado: dict) -> dict:
    return estado.setdefault('datos_carrera', {})


def _temporada(estado: dict) -> int:
    return int(estado.get('temporada', 1) or 1)


def contrato(estado: dict) -> Optional[dict]:
    c = _dc(estado).get('contrato_dt')
    return c if isinstance(c, dict) else None


def patrimonio(estado: dict) -> int:
    return int(_dc(estado).get('patrimonio_dt', 0) or 0)


def _sumar(estado: dict, monto: int) -> None:
    _dc(estado)['patrimonio_dt'] = patrimonio(estado) + max(0, int(monto))


def ofertas_contrato(estado: dict, equipo, renovacion: bool = False) -> list:
    """3 variantes {'anios', 'sueldo'}: más años = menos sueldo anual."""
    from alpha_football.directiva import calif_dt
    base = max(SUELDO_MIN, int(int(getattr(equipo, 'balance', 0) or 0) * SUELDO_PCT_BALANCE))
    base = base * (0.8 + calif_dt(estado) / 250)
    if renovacion:
        base *= BONO_RENOVACION
    return [{'anios': a, 'sueldo': int(round(base * m, -3))} for a, m in VARIANTES]


def firmar(estado: dict, equipo, oferta: dict, renovacion: bool = False) -> dict:
    """Firma el contrato. En renovación se suma a partir del vencimiento actual."""
    anios = max(1, int(oferta.get('anios', 1)))
    actual = contrato(estado)
    if renovacion and actual:
        desde, hasta = actual['desde'], int(actual['hasta']) + anios
        _dc(estado)['renovacion_dt'] = {'temporada': _temporada(estado), 'estado': 'aceptada'}
    else:
        desde = _temporada(estado)
        hasta = desde + anios - 1
        _dc(estado).pop('renovacion_dt', None)
    c = _dc(estado)['contrato_dt'] = {'club': getattr(equipo, 'nombre', '?'), 'sueldo': int(oferta['sueldo']),
                                      'desde': int(desde), 'hasta': int(hasta)}
    logger.info(f"Contrato DT firmado: {c}")
    return c


def pagar_jornada(estado: dict) -> int:
    """Una jornada de liga del user = sueldo / num_jornadas al patrimonio."""
    c = contrato(estado)
    if not c:
        return 0
    n = max(1, int(getattr(estado.get('liga'), 'num_jornadas', 10) or 10))
    monto = int(c['sueldo']) // n
    _sumar(estado, monto)
    return monto


def indemnizacion(estado: dict, temporada_fin: int) -> int:
    c = contrato(estado)
    if not c:
        return 0
    faltan = max(0, int(c['hasta']) - int(temporada_fin))
    return int(int(c['sueldo']) * faltan * INDEMNIZACION_FRAC)


def cobrar_indemnizacion(estado: dict, temporada_fin: int) -> int:
    monto = indemnizacion(estado, temporada_fin)
    _sumar(estado, monto)
    return monto


def revisar_renovacion(estado: dict) -> None:
    """A mitad de temporada, si el contrato vence esta temporada: oferta (calif ≥ 60) o negativa."""
    from alpha_football import correo as C
    from alpha_football.directiva import calif_dt
    liga, c, t = estado.get('liga'), contrato(estado), _temporada(estado)
    if liga is None or not c or int(c['hasta']) != t:
        return
    if int(getattr(liga, 'jornada_actual', 1) or 1) <= int(getattr(liga, 'num_jornadas', 10) or 10) // 2:
        return
    r = _dc(estado).get('renovacion_dt') or {}
    if r.get('temporada') == t:
        return
    if calif_dt(estado) >= CALIF_RENOVAR or hito_temporada(estado):   # con un título asegurado no se niega
        _dc(estado)['renovacion_dt'] = {'temporada': t, 'estado': 'ofrecida'}
        C.enviar(estado, 'directiva', "Oferta de renovación de contrato",
                 "Estamos contentos con tu trabajo y queremos que sigas. Mira nuestra propuesta.",
                 C.accion('contrato_dt_screen', "VER OFERTA"))
    else:
        _dc(estado)['renovacion_dt'] = {'temporada': t, 'estado': 'negada'}
        C.enviar(estado, 'directiva', "No renovaremos tu contrato",
                 "Tu contrato vence al final de la temporada y la directiva no lo renovará.")


CUPOS_ASCENSO = 2      # los 2 primeros de 2ª suben (resumen_temporada_screen)


def hito_temporada(estado: dict) -> Optional[str]:
    """Texto del gran logro de la temporada si ya está asegurado: campeón de liga, ascenso o
    campeón de la copa internacional. None si todavía no hay ninguno."""
    try:
        if estado.get('copa_mejor_fase_temp') == 'Campeón':
            from alpha_football import competiciones as CP
            t = CP.tipo_copa_user(estado)
            return f"campeón de la {CP.NOMBRE_COPA.get(t, 'copa')}" if t else "campeón de la copa"
        liga, mi = estado.get('liga'), estado.get('mi_equipo')
        if liga is None or mi is None:
            return None
        partidos = list(getattr(liga, 'calendario', []) or [])
        if not any(p.jugado for p in partidos):
            return None                                       # temporada sin empezar: no hay tabla
        quedan = any(not p.jugado for p in partidos)
        if quedan:
            from alpha_football.directiva import peor_posicion_posible
            puesto = peor_posicion_posible(liga, mi)          # lo peor que te puede pasar
        else:
            from alpha_football.ui.postpartido import posicion_liga
            puesto = posicion_liga(liga, mi.id)               # tabla final (desempata por goles)
        if puesto == 1:
            return "campeón de liga" if getattr(liga, 'division', 1) != 2 else "campeón de 2ª y ascenso"
        if getattr(liga, 'division', 1) == 2 and 1 <= puesto <= CUPOS_ASCENSO:
            return "ascenso a 1ª división"
    except Exception as e:
        logger.error(f"No se pudo revisar el hito de la temporada: {e}")
    return None


def revisar_renovacion_por_hito(estado: dict) -> bool:
    """Si la directiva te negó la renovación esta temporada pero lograste un hito (título, ascenso,
    copa), se disculpa y te ofrece renovar. Una sola vez. True si ofreció."""
    from alpha_football import correo as C
    t, c = _temporada(estado), contrato(estado)
    r = _dc(estado).get('renovacion_dt') or {}
    if not c or int(c['hasta']) != t or r.get('temporada') != t or r.get('estado') != 'negada':
        return False
    hito = hito_temporada(estado)
    if not hito:
        return False
    _dc(estado)['renovacion_dt'] = {'temporada': t, 'estado': 'ofrecida', 'disculpa': hito}
    C.enviar(estado, 'directiva', "Te pedimos disculpas: queremos renovarte",
             f"Nos equivocamos al no renovarte. Con el {hito} demostraste que eres el indicado. "
             "Te ofrecemos un contrato nuevo: míralo en MI CONTRATO antes de que termine la temporada.",
             C.accion('contrato_dt_screen', "VER OFERTA"))
    return True


def rechazar_renovacion(estado: dict) -> None:
    _dc(estado)['renovacion_dt'] = {'temporada': _temporada(estado), 'estado': 'rechazada'}


def contrato_vencido(estado: dict, temporada_fin: int) -> bool:
    c = contrato(estado)
    return bool(c) and int(c['hasta']) <= int(temporada_fin)


def asegurar_contrato(estado: dict) -> None:
    """Saves viejos o club cambiado sin firmar: contrato de 2 años con la variante media."""
    mi = estado.get('mi_equipo')
    c = contrato(estado)
    if mi is None or (c and c.get('club') == getattr(mi, 'nombre', None)):
        return
    firmar(estado, mi, ofertas_contrato(estado, mi)[1])
