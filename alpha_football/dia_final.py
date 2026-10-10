# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Último día de fichajes (v0.4.14.0)
El 31 de agosto y el 31 de enero el mercado tiene un reloj de 20 horas. Lo que se concreta cuesta horas
(fichajes 3, ventas 2); "lo analizamos" responde a las 3 horas. A las 0 horas, o con CERRAR MERCADO, se
cierra: se retiran las ofertas, caen los análisis pendientes, la IA hace su ronda de cierre y el mercado
queda cerrado el resto del día. Datos: datos_carrera['calendario']['dia_final'] = {'fecha', 'horas', 'cierre'}
(dentro del bloque de C, que se rearma solo al cambiar de temporada, liga o club).
Sin UI.
"""
from __future__ import annotations

import logging
import random
from typing import Optional

from alpha_football import calendario as CAL

logger = logging.getLogger(__name__)

HORAS_DIA = 20
HORAS_FICHAJE = 3            # fichaje inscrito: compra, agente libre o préstamo que llega al user
HORAS_VENTA = 2              # venta o cesión concretada
HORAS_ANALISIS = 3           # "lo analizamos" responde a las 3 horas
PROB_OFERTA_HORA = 0.10
PROB_OFERTA_HORA_TRANSFERIBLES = 0.25


def _hoy_iso(estado: dict) -> str:
    from alpha_football import temporada as T
    return T.fecha(estado).isoformat()


def _bloque(estado: dict) -> Optional[dict]:
    """El estado del último día de HOY (None si hoy no se abrió ninguno)."""
    b = CAL.asegurar(estado).get('dia_final')
    return b if isinstance(b, dict) and b.get('fecha') == _hoy_iso(estado) else None


def horas(estado: dict) -> int:
    b = _bloque(estado)
    return int(b.get('horas', 0) or 0) if b else 0


def activo(estado: dict) -> bool:
    """Hoy es un último día y quedan horas: el reloj de horas corre y el día no pasa."""
    try:
        return horas(estado) > 0
    except Exception:
        return False


_CERRANDO = False            # durante la ronda de cierre de la IA el mercado todavía cuenta como abierto


def cerrado(estado: dict) -> bool:
    """Hoy es un último día cuyo mercado ya se cerró (0 horas o CERRAR MERCADO)."""
    if _CERRANDO:
        return False
    try:
        b = _bloque(estado)
        return b is not None and int(b.get('horas', 0) or 0) <= 0
    except Exception:
        return False


def abrir(estado: dict) -> bool:
    """Empieza el último día (20 horas) si hoy es un cierre de mercado y aún no se abrió. True si lo abrió."""
    try:
        from alpha_football import temporada as T
        if estado.get('liga') is None or not T.ultimo_dia(estado) or _bloque(estado) is not None:
            return False
        CAL.asegurar(estado)['dia_final'] = {'fecha': _hoy_iso(estado), 'horas': HORAS_DIA}
        return True
    except Exception as e:
        logger.error(f"dia_final: no se pudo abrir el último día: {e}", exc_info=True)
        return False


def gastar(estado: dict, h: int) -> bool:
    """Gasta `h` horas del último día. Fuera de él es gratis (True). Con horas insuficientes no gasta (False).
    Tras gastar responde lo que vence y, si quedan 0 horas, cierra el mercado."""
    if not activo(estado):
        return True
    b = _bloque(estado)
    if int(b['horas']) < int(h):
        return False
    antes = int(b['horas'])
    b['horas'] = antes - int(h)
    _anotar_animacion(estado, antes, b['horas'], int(h))
    _tras_pasar_horas(estado)
    return True


MOTIVOS_HORAS = {HORAS_FICHAJE: "Fichaje concretado", HORAS_VENTA: "Venta concretada"}   # v0.4.18.0


def _anotar_animacion(estado: dict, desde: int, hasta: int, h: int) -> None:
    """v0.4.18.0: anota las horas que acaban de correr para que la pantalla las anime (ui/horas_anim.py).
    Si la anterior todavía no se mostró entera y esta sigue donde terminó aquella, la cuenta continúa."""
    previa = estado.get('anim_horas')
    sigue = isinstance(previa, dict) and previa.get('hasta') == desde and 'desde' in previa
    estado['anim_horas'] = {'desde': int(previa['desde']) if sigue else desde, 'hasta': hasta,
                            'motivo': MOTIVOS_HORAS.get(h, f"{h} horas"),
                            'inicio': previa.get('inicio') if sigue else None}


def _tras_pasar_horas(estado: dict, rng: Optional[random.Random] = None) -> None:
    responder(estado, rng)
    if horas(estado) <= 0:
        cerrar(estado, rng)


_RESPONDIENDO = False        # evita la reentrada: una venta aceptada dentro de una respuesta gasta horas


def responder(estado: dict, rng: Optional[random.Random] = None) -> None:
    """Las respuestas de 'lo analizamos' cuya hora llegó (contraofertas y préstamos). Sin reentrada."""
    global _RESPONDIENDO
    if _RESPONDIENDO:
        return
    _RESPONDIENDO = True
    azar = rng or random.Random()
    try:
        from alpha_football import contraofertas, prestamos
        contraofertas.resolver_analisis(estado, azar)
        prestamos.resolver_analisis(estado, azar)
    except Exception as e:
        logger.error(f"dia_final: no se pudieron resolver los análisis: {e}", exc_info=True)
    finally:
        _RESPONDIENDO = False


def prob_oferta_hora(estado: dict) -> float:
    """10% por hora; 25% si tienes transferibles o alguien que pide salir."""
    mi = estado.get('mi_equipo')
    hay = any(getattr(j, 'transferible', False) or getattr(j, 'pide_salir', False)
              for j in getattr(mi, 'jugadores', []) or [])
    return PROB_OFERTA_HORA_TRANSFERIBLES if hay else PROB_OFERTA_HORA


def avanzar_hora(estado: dict, rng: Optional[random.Random] = None) -> dict:
    """Pasa 1 hora (AVANZAR 1 HORA): llegan las respuestas que vencen y puede entrar una oferta por un
    jugador tuyo; a las 0 horas se cierra el mercado. Devuelve {'horas', 'correos', 'ofertas', 'cerro'}."""
    res = {'horas': 0, 'correos': 0, 'ofertas': 0, 'cerro': False}
    if not activo(estado):
        return res
    from alpha_football import correo as C
    azar = rng or random.Random()
    b = _bloque(estado)
    b['horas'] = int(b['horas']) - 1
    res['horas'] = 1
    n0 = len(C.bandeja(estado))
    responder(estado, azar)
    res['correos'] = max(0, len(C.bandeja(estado)) - n0)
    if b['horas'] > 0 and azar.random() < prob_oferta_hora(estado):
        try:
            from alpha_football import dias
            res['ofertas'] = dias._entregar_oferta(estado, False)
        except Exception as e:
            logger.error(f"dia_final: no se pudo crear la oferta de la hora: {e}", exc_info=True)
    if b['horas'] <= 0:
        cerrar(estado, azar)
        res['cerro'] = True
    return res


def _caer_analisis(estado: dict) -> int:
    """Los 'lo analizamos' con hora de respuesta que no llegaron a responder se caen, cada uno con su correo."""
    from alpha_football import correo as C
    dc = estado.setdefault('datos_carrera', {})
    n = 0
    for clave in ('analisis_compras', 'analisis_contratos', 'analisis_prestamos'):
        vivos = []
        for a in dc.get(clave) or []:
            if a.get('hora_resp') is None:
                vivos.append(a)
                continue
            n += 1
            C.enviar(estado, 'club', f"Se cayó el trato por {a.get('jugador', 'el jugador')}",
                     "Se acabó el mercado antes de que respondieran: el trato queda sin efecto.")
        dc[clave] = vivos
    return n


def cerrar(estado: dict, rng: Optional[random.Random] = None) -> dict:
    """Cierra el mercado del último día (0 horas o CERRAR MERCADO). Idempotente: retira las ofertas sin
    responder, cae los análisis pendientes (con correo), la IA hace su ronda de cierre y aparece el cartel
    MERCADO CERRADO. Devuelve {'ofertas', 'analisis', 'ronda'}."""
    res = {'ofertas': 0, 'analisis': 0, 'ronda': False}
    b = _bloque(estado)
    if b is None or b.get('cierre'):
        return res
    b['cierre'] = True                                   # primero la marca: nada se hace dos veces
    azar = rng or random.Random()
    try:
        res['ofertas'] = len(estado.get('ofertas_recibidas') or [])
        estado['ofertas_recibidas'] = []
        res['analisis'] = _caer_analisis(estado)
    except Exception as e:
        logger.error(f"dia_final: no se pudieron limpiar las ofertas y los análisis: {e}", exc_info=True)
    global _CERRANDO
    _CERRANDO = True                                     # tanto con 0 horas como con CERRAR MERCADO la ronda ve el mercado abierto
    try:
        from alpha_football.mercado_ia import ronda_fichajes_ia
        ronda_fichajes_ia(estado, 'ventana', azar)       # con el mercado todavía abierto: ronda de cierre
        res['ronda'] = True
    except Exception as e:
        logger.error(f"dia_final: no se pudo hacer la ronda de cierre: {e}", exc_info=True)
    finally:
        _CERRANDO = False
    b['horas'] = 0
    try:
        from alpha_football.ui import aviso_mercado as AM
        AM._abrir(estado, 'cierra', _hoy_iso(estado))
    except Exception as e:
        logger.error(f"dia_final: no se pudo mostrar el cierre: {e}", exc_info=True)
    return res


def analisis(estado: dict) -> tuple:
    """(ok, hora_resp) de un 'lo analizamos' pedido ahora. Fuera del último día: (True, None), se responde al
    cerrar la jornada siguiente. El último día: con 3 horas o más responde cuando queden `horas - 3`
    (True, h); con menos, (False, None): "no hay tiempo"."""
    if not activo(estado):
        return True, None
    h = horas(estado)
    if h < HORAS_ANALISIS:
        return False, None
    return True, h - HORAS_ANALISIS


def texto_respuesta(hora: Optional[int], uno: bool = False) -> str:
    """'Te responden en 3 horas.' o 'Te responden por correo en la próxima jornada.' ('Te responde…' si `uno`)."""
    quien = "Te responde" if uno else "Te responden"
    return f"{quien} por correo en la próxima jornada." if hora is None else f"{quien} en {HORAS_ANALISIS} horas."


def vencido(estado: dict, item: dict) -> bool:
    """¿Ya toca responder este 'lo analizamos'? Con hora de respuesta (pedido el último día): cuando quedan esas
    horas o menos, o si el último día ya pasó. Sin ella, la regla de siempre: la jornada siguiente."""
    t = int(estado.get('temporada', 1) or 1)
    if int(item.get('temporada', t) or t) != t:
        return True
    hr = item.get('hora_resp')
    if hr is not None:
        return horas(estado) <= int(hr) if _bloque(estado) is not None else True
    return int(getattr(estado.get('liga'), 'jornada_actual', 1) or 1) > int(item.get('jornada', 0) or 0)


def textos(estado: dict) -> tuple:
    """(línea 1, línea 2, línea 3) del botón grande del hub durante el último día."""
    from alpha_football import temporada as T
    return ("ÚLTIMO DÍA", f"{CAL.texto_fecha(T.fecha(estado))} · quedan {horas(estado)} h", "")   # la 3ª línea la ocupan los botones


def texto_hora(r: dict) -> str:
    """'Pasó 1 hora: 1 oferta, 1 correo' / 'Pasó 1 hora: se cerró el mercado'."""
    partes = []
    if int(r.get('ofertas', 0) or 0):
        partes.append(f"{int(r['ofertas'])} oferta{'s' if int(r['ofertas']) != 1 else ''}")
    if int(r.get('correos', 0) or 0):
        partes.append(f"{int(r['correos'])} correo{'s' if int(r['correos']) != 1 else ''}")
    if r.get('cerro'):
        partes.append("se cerró el mercado")
    return "Pasó 1 hora" + (f": {', '.join(partes)}" if partes else "")
