# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Sanción de la liga por tope salarial (v0.4.17.0)
Cerrar la temporada con la masa salarial sobre el tope de la directiva trae una sanción de la LIGA al
club: en toda la temporada siguiente no compra, no trae agentes libres ni pide préstamos. Si además
cerró con mala salud financiera, una multa del 40% de su presupuesto base; si el presupuesto nuevo no
alcanza, la liga se lo queda entero y le resta puntos.
- Datos: datos_carrera['sancion_liga'] (una sola; es del club, no del DT).
Sin UI.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

MULTA_PCT_BASE = 0.40
PUNTOS_MULTA = 6


def _dc(estado: dict) -> dict:
    return estado.setdefault('datos_carrera', {})


def registrar(estado: dict, masa: int, tope: int, temporada_fin: int) -> dict:
    """Cierre de la temporada `temporada_fin` con la masa sobre el tope: sanciona la siguiente. La salud
    se mide con el saldo de este momento contra el presupuesto base de la liga que se acaba de jugar."""
    from alpha_football.finanzas import factor_salud, presupuesto_base
    mi, liga = estado.get('mi_equipo'), estado.get('liga')
    base = presupuesto_base(mi, getattr(liga, 'tipo', 'betplay'), getattr(liga, 'division', 1) or 1)
    salud_mala = factor_salud(int(getattr(mi, 'balance', 0) or 0), base) < 1.0
    s = _dc(estado)['sancion_liga'] = {
        'club': getattr(mi, 'nombre', ''), 'temporada': int(temporada_fin) + 1,
        'masa': int(masa), 'tope': int(tope), 'salud_mala': salud_mala,
        'multa': int(base * MULTA_PCT_BASE) if salud_mala else 0, 'multa_estado': None, 'puntos': 0}
    return s


def activa(estado: dict) -> Optional[dict]:
    """La sanción vigente: la del club que diriges hoy y de la temporada en curso."""
    try:
        s, mi = _dc(estado).get('sancion_liga'), estado.get('mi_equipo')
        if not isinstance(s, dict) or mi is None or s.get('club') != mi.nombre:
            return None
        if int(s.get('temporada') or -1) != int(estado.get('temporada', 1) or 1):
            return None
        return s
    except Exception as e:
        logger.error(f"No se pudo leer la sanción de la liga: {e}")
        return None


def motivo_bloqueo(estado: dict, corto: bool = False) -> Optional[str]:
    """Texto para rechazar una compra, un agente libre o un préstamo; None si no hay sanción. Con `corto`,
    una versión de 60 caracteres o menos para el aviso del correo (que recorta a ese ancho)."""
    if activa(estado) is None:
        return None
    if corto:
        return "Sanción de la liga: no puedes fichar esta temporada."
    return "Sanción de la liga: tu club no puede fichar, traer agentes libres ni pedir préstamos esta temporada."


def texto(s: dict) -> str:
    """Frase del correo de evaluación."""
    t = (f"La liga sanciona al club por superar el tope salarial (${int(s.get('masa', 0)) / 1_000_000:.1f}M sobre "
         f"${int(s.get('tope', 0)) / 1_000_000:.1f}M): no podrá fichar, traer agentes libres ni pedir préstamos "
         f"en toda la temporada {s.get('temporada', '?')}.")
    if s.get('salud_mala'):
        t += (f" Por la mala salud financiera del club, además impone una multa de "
              f"${int(s.get('multa', 0)) / 1_000_000:.1f}M: si el presupuesto no alcanza, se lo quedará entero "
              f"y restará {PUNTOS_MULTA} puntos.")
    return t


def texto_corto(s: dict) -> str:
    """Una línea para la pantalla FINANZAS durante la temporada sancionada (con la multa, si ya se cobró)."""
    t = "Sanción de la liga: sin fichajes, libres ni préstamos esta temporada"
    if s.get('multa_estado') == 'pagada':
        t += f" · multa de ${int(s.get('multa', 0) or 0) / 1_000_000:.1f}M pagada"
    elif s.get('multa_estado') == 'impaga':
        t += f" · multa impaga: −{int(s.get('puntos') or PUNTOS_MULTA)} puntos"
    return t


def cobrar_multa(estado: dict) -> Optional[dict]:
    """Cierre financiero, ya con el presupuesto nuevo: cobra una sola vez la multa por mala salud."""
    s, mi = activa(estado), estado.get('mi_equipo')
    if s is None or not s.get('salud_mala') or s.get('multa_estado'):
        return None
    multa, saldo = int(s.get('multa', 0) or 0), int(getattr(mi, 'balance', 0) or 0)
    m = lambda v: f"${v / 1_000_000:.1f}M"
    if saldo >= multa:
        cobrado, s['multa_estado'] = multa, 'pagada'
        mi.balance = saldo - multa
        asunto = "Sanción de la liga: multa pagada"
        cuerpo = (f"La liga cobró la multa de {m(multa)} por cerrar la temporada sobre el tope salarial y con mala "
                  f"salud financiera. Presupuesto disponible: {m(mi.balance)}.")
    else:
        cobrado, s['multa_estado'], s['puntos'] = max(0, saldo), 'impaga', PUNTOS_MULTA
        mi.balance = min(0, saldo)
        mi.puntos = int(getattr(mi, 'puntos', 0) or 0) - PUNTOS_MULTA
        mi.sancion_puntos = int(getattr(mi, 'sancion_puntos', 0) or 0) + PUNTOS_MULTA
        asunto = f"Sanción de la liga: sin presupuesto y −{PUNTOS_MULTA} puntos"
        cuerpo = (f"El presupuesto no alcanzó para la multa de {m(multa)} por cerrar la temporada sobre el tope "
                  f"salarial y con mala salud financiera: la liga se quedó con todo el presupuesto ({m(cobrado)}) "
                  f"y le resta {PUNTOS_MULTA} puntos al club en esta temporada.")
    try:
        from alpha_football.finanzas import registrar as _registrar
        _registrar(estado, 'premios', -cobrado)      # mismo renglón que el premio/multa de la directiva
    except Exception as e:
        logger.error(f"No se pudo registrar la multa de la liga: {e}")
    if not estado.get('despido_pendiente'):          # al despedido ya no le sirve
        try:
            from alpha_football import correo as C
            C.enviar(estado, 'directiva', asunto,
                     cuerpo + " Le recordamos que no podrá fichar, traer agentes libres ni pedir préstamos "
                              "durante toda la temporada.",
                     C.accion('finanzas_screen', "VER FINANZAS"))
        except Exception as e:
            logger.error(f"No se pudo avisar la multa de la liga: {e}")
    return s
