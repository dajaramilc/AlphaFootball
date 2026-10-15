# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Avance por días (v0.4.12.0)
El juego avanza día a día entre tus partidos: un reloj ("hoy") que nunca pasa del día de tu próximo
partido, la energía que se recupera cada día y una agenda con lo que llega en días sueltos.
- Datos: dentro de datos_carrera['calendario'] (el bloque de calendario.asegurar, que se rearma solo
  al cambiar de temporada, liga o club): 'dia' = 'AAAA-MM-DD' y 'agenda' = [{'fecha', 'tipo', 'datos'}].
- Solo el hub (o la pantalla CALENDARIO) crea el reloj: sin reloj todo funciona como antes (activo()).
Sin UI.
"""
from __future__ import annotations

import logging
import random
from contextlib import contextmanager
from datetime import date, timedelta
from typing import Optional

from alpha_football import calendario as CAL

logger = logging.getLogger(__name__)

MAX_DIAS = 400                                               # tope de seguridad de continuar()
PROB_OFERTA_EXTERIOR = 0.25                                   # la de market.crear_oferta_exterior


def _cal(estado: dict) -> dict:
    return CAL.asegurar(estado)


def _a_fecha(txt) -> Optional[date]:
    try:
        return date.fromisoformat(txt) if txt else None
    except Exception:
        return None


def inicio_temporada(estado: dict) -> date:
    from alpha_football import temporada as T      # v0.4.13.0: 1 jul (Europa) / 1 ene (Sudamérica)
    return T.inicio(estado)


def activo(estado: dict) -> bool:
    """¿La partida ya tiene reloj? Lo crea hoy() (el hub, al abrirse)."""
    try:
        return (estado.get('liga') is not None and estado.get('mi_equipo') is not None
                and _a_fecha(_cal(estado).get('dia')) is not None)
    except Exception:
        return False


def hoy(estado: dict) -> date:
    """El día en que estás. Si la partida no tiene reloj lo crea: al inicio de la temporada si no
    has jugado nada; si no, el día de tu próximo partido (save a mitad de temporada)."""
    if estado.get('liga') is None or estado.get('mi_equipo') is None:
        return inicio_temporada(estado)
    cal = _cal(estado)
    d = _a_fecha(cal.get('dia'))
    if d is None:
        evs = CAL.eventos_user(estado)
        prox = next((e for e in evs if not e['jugado']), None)
        if evs and not any(e['jugado'] for e in evs):
            d = min(inicio_temporada(estado), evs[0]['fecha'])
        elif prox is not None:
            d = prox['fecha']
        else:
            d = evs[-1]['fecha'] if evs else inicio_temporada(estado)
        cal['dia'] = d.isoformat()
    return d


def es_dia_de_continuar(estado: dict) -> bool:
    """True si la partida tiene reloj y hoy NO es el día de tu próximo partido: JUGAR pasa a CONTINUAR.
    v0.4.13.0: sin partidos pendientes, los días corren hasta el fin de la temporada."""
    try:
        if not activo(estado):
            return False
        from alpha_football import dia_final as DF
        if DF.activo(estado):
            return False                       # v0.4.14.0: el último día no pasa mientras queden horas
        h = hoy(estado)
        prox = CAL.proximo_evento(estado)
        if prox is not None:
            return h < prox['fecha']
        from alpha_football import temporada as T
        return h < T.fin(estado)
    except Exception as e:
        logger.error(f"dias: no se pudo saber si hoy hay partido: {e}")
        return False


def avanzar_dia(estado: dict) -> dict:
    """Pasa un día: mueve el reloj y recupera la energía del día. Nunca pasa del día de tu próximo
    partido (si hoy hay partido no hace nada). Devuelve {'dias', 'correos', 'ofertas', 'eventos'}."""
    res = {'dias': 0, 'correos': 0, 'ofertas': 0, 'eventos': 0}
    try:
        if not es_dia_de_continuar(estado):
            return res
        asignar_dias(estado)                       # por si quedó algo sin día
        nueva = hoy(estado) + timedelta(days=1)
        _cal(estado)['dia'] = nueva.isoformat()
        res['dias'] = 1
        try:
            from alpha_football.energia import recuperar_todos
            res['correos'] += len(recuperar_todos(estado, 1.0) or [])   # v0.4.19.0: altas médicas = correos
        except Exception as e_en:
            logger.error(f"dias: no se pudo recuperar la energía del día: {e_en}")
        for clave, n in entregar(estado, nueva).items():
            res[clave] += n
        try:
            hito = revisar_dia(estado, nueva)
            if hito:
                res['hito'] = hito
            if hito == 'ultimo':               # v0.4.14.0: llegó el cierre del mercado: empiezan las 20 horas
                from alpha_football import dia_final as DF
                DF.abrir(estado)
        except Exception as e_rev:
            logger.error(f"dias: error revisando el día: {e_rev}", exc_info=True)
        if estado.pop('_parar_avance', None):      # v0.4.14.1: un paso del día pide que CONTINUAR se detenga hoy
            res['parar'] = True
    except Exception as e:
        logger.error(f"dias: error al avanzar un día: {e}", exc_info=True)
    return res


def debe_parar(r: dict) -> bool:
    """v0.4.14.1: ¿lo que pasó ese día detiene a CONTINUAR? Solo una oferta, un evento de vestuario o un paso
    del día que lo pida. La usan continuar() y el avance a la vista del hub."""
    return bool(r.get('ofertas') or r.get('eventos') or r.get('parar'))


def continuar(estado: dict, parar: bool = True) -> dict:
    """Corre los días hasta el día de tu próximo partido; con `parar`, se detiene antes si ese día
    llegó una oferta o un evento de vestuario, o si un paso del día lo pide (estado['_parar_avance']).
    v0.4.14.1: un correo común y la apertura del mercado ya no lo frenan (el último día sí: sus horas no
    dejan pasar el día). Siempre avanza al menos un día si hoy no hay partido."""
    total = {'dias': 0, 'correos': 0, 'ofertas': 0, 'eventos': 0}
    for _ in range(MAX_DIAS):
        if not parar:                          # v0.4.14.0: tests y migraciones: el último día se cierra solo
            from alpha_football import dia_final as DF
            if DF.activo(estado):
                DF.cerrar(estado)
        r = avanzar_dia(estado)
        if r['dias'] == 0:
            break
        for k in ('dias', 'correos', 'ofertas', 'eventos'):
            total[k] += r[k]
        if r.get('hito'):
            total['hito'] = r['hito']
        if parar and debe_parar(r):
            break
    return total


def hasta_el_partido(estado: dict) -> dict:
    """Corre los días sin detenerse hasta el día de tu próximo partido (tests y migraciones)."""
    return continuar(estado, parar=False)


def texto_resumen(r: dict) -> str:
    """'Pasaron 3 días: 1 oferta, 2 correos'."""
    d = int(r.get('dias', 0) or 0)
    if d <= 0:
        return "Hoy es día de partido"
    partes = []
    for clave, uno, varios in (('ofertas', 'oferta', 'ofertas'), ('eventos', 'evento', 'eventos'),
                               ('correos', 'correo', 'correos')):
        n = int(r.get(clave, 0) or 0)
        if n:
            partes.append(f"{n} {uno if n == 1 else varios}")
    if r.get('hito') == 'abre':
        partes.append("abre el mercado")
    elif r.get('hito') == 'cierra':
        partes.append("cierra el mercado")
    elif r.get('hito') == 'ultimo':
        partes.append("último día de fichajes")
    cab = "Pasó 1 día" if d == 1 else f"Pasaron {d} días"
    return f"{cab}: {', '.join(partes)}" if partes else cab


def l2_fecha_fase(estado: dict) -> str:
    """'mié 12 ago 2026 · Mercado abierto · cierra en 19 días': la fecha y la fase, lo principal del hub."""
    from alpha_football import temporada as T
    return f"{CAL.texto_fecha(hoy(estado))} · {T.texto_fase(estado)}"[:56]


def textos_hub(estado: dict) -> Optional[tuple]:
    """(línea 1, línea 2, línea 3) del botón grande del hub cuando hoy no hay partido; None si hay
    partido hoy, es el fin de la temporada o la partida no tiene reloj."""
    from alpha_football import dia_final as DF          # v0.4.14.0: el último día, el panel de las horas
    if DF.activo(estado):
        return DF.textos(estado)
    if not es_dia_de_continuar(estado):
        return None
    from alpha_football import temporada as T
    prox = CAL.proximo_evento(estado)
    h = hoy(estado)
    if prox is None:                                         # v0.4.13.0: los días que faltan para el fin
        n = (T.fin(estado) - h).days
        l3 = f"Fin de temporada: {CAL.texto_fecha(T.fin(estado), False)} (en {n} día{'s' if n != 1 else ''})"
        return "CONTINUAR", l2_fecha_fase(estado), l3[:56]
    n = (prox['fecha'] - h).days
    donde = "vs" if prox['local'] else "en"
    l3 = (f"Próximo: {prox['etiqueta']} {donde} {str(prox['rival'])[:12]} · "
          f"{CAL.texto_fecha(prox['fecha'], False)} (en {n} día{'s' if n != 1 else ''})")
    return "CONTINUAR", l2_fecha_fase(estado), l3[:56]


# --- Agenda ───────────────────────────────────────────────────────────────────

def agenda(estado: dict) -> list:
    """La agenda de la temporada (lista de {'fecha', 'tipo', 'datos'}); una agenda dañada se reinicia."""
    cal = _cal(estado)
    if not isinstance(cal.get('agenda'), list):
        cal['agenda'] = []
    return cal['agenda']


def programar(estado: dict, tipo: str, datos: Optional[dict] = None) -> dict:
    """Agrega algo a la agenda sin día; asignar_dias le pone uno al cerrar el partido."""
    item = {'fecha': None, 'tipo': tipo, 'datos': datos or {}}
    agenda(estado).append(item)
    return item


def dias_libres(estado: dict) -> list:
    """Días entre hoy y tu próxima jornada de liga, sin los días en que juegas (liga o copa)."""
    evs = CAL.eventos_user(estado)
    prox_liga = next((e for e in evs if not e['jugado'] and e['tipo'] == 'liga'), None)
    if prox_liga is None:
        return []
    ocupados = {e['fecha'] for e in evs}
    out, d = [], hoy(estado) + timedelta(days=1)
    while d < prox_liga['fecha']:
        if d not in ocupados:
            out.append(d)
        d += timedelta(days=1)
    return out


def asignar_dias(estado: dict) -> int:
    """Pone día (determinista) a lo que la agenda tiene sin fecha válida. Sin días libres (fin de la
    liga) lo entrega en el acto. Devuelve cuántas entradas asignó."""
    ag = agenda(estado)
    sin = [it for it in ag if isinstance(it, dict) and _a_fecha(it.get('fecha')) is None]
    if not sin:
        return 0
    libres = dias_libres(estado)
    h = hoy(estado)
    club = str(getattr(estado.get('mi_equipo'), 'id', ''))
    jornada = int(getattr(estado.get('liga'), 'jornada_actual', 1) or 1)
    for k, it in enumerate(sin):
        pool = [d for d in libres if d.isoformat() in (it.get('datos') or {}).get('dias', [])] or libres
        if pool:
            azar = random.Random(f"agenda-{CAL.anio(estado)}-{club}-{jornada}-{k}")
            it['fecha'] = azar.choice(pool).isoformat()
        else:
            it['fecha'] = h.isoformat()
    if not libres:
        entregar(estado, h)
    return len(sin)


def _entregar_oferta(estado: dict, exterior: bool) -> int:
    """Crea la oferta de la IA que se sorteó al cerrar el partido (con las mismas funciones de siempre)."""
    from alpha_football import market
    from alpha_football.ui.match_screen import _correo_oferta
    liga, mi = estado.get('liga'), estado.get('mi_equipo')
    if liga is None or mi is None:
        return 0
    if exterior:
        of = market.crear_oferta_exterior(mi, estado, prob=1.0)
    else:
        rivales = [e for e in liga.equipos if e.id != mi.id]
        of = market.crear_oferta_ui(mi, rivales, liga.jornada_actual, liga.num_jornadas, prob=1.0, estado=estado)
    if of and market.traspasado_en_ventana(estado, of.get('jugador')):
        of = None                                # recién llegado: no se lo puede traspasar en esta ventana
    if not of:
        return 0
    estado.setdefault('ofertas_recibidas', []).append(of)
    _correo_oferta(estado, of, "Oferta del exterior por" if exterior else "Oferta por")
    return 1


def _entregar_item(estado: dict, it: dict) -> tuple:
    """Entrega una entrada de la agenda. Devuelve (clave del resumen, cuántos) o ('', 0)."""
    tipo = it.get('tipo')
    if tipo == 'correo':
        msg = it.get('datos') or {}
        if not msg.get('asunto'):
            return '', 0                         # mensaje dañado: se descarta
        from alpha_football import correo as C
        if not C.vigente(estado, msg):           # v0.4.14.1: el jugador se fue antes de que llegara su mensaje
            logger.info(f"dias: se descarta '{msg.get('asunto')}': el jugador ya no está en el club")
            return '', 0
        C.entregar(estado, msg)
        return ('eventos' if msg.get('evento') else 'correos'), 1
    if tipo in ('oferta', 'oferta_ext'):
        return 'ofertas', _entregar_oferta(estado, tipo == 'oferta_ext')
    if tipo == 'garantizadas':
        from alpha_football import salidas
        return 'ofertas', len(salidas.ofertas_garantizadas(estado))
    logger.warning(f"dias: tipo de agenda desconocido '{tipo}': se descarta")
    return '', 0


def entregar(estado: dict, hasta: date) -> dict:
    """Entrega lo que vence hasta `hasta` (incluido). Una entrega que falla se registra y se descarta:
    nunca bloquea el avance del reloj. Devuelve {'correos', 'ofertas', 'eventos'}."""
    res = {'correos': 0, 'ofertas': 0, 'eventos': 0}
    ag = agenda(estado)
    vencen = []
    for it in list(ag):
        if not isinstance(it, dict):
            ag[:] = [x for x in ag if x is not it]       # basura: se descarta
            continue
        f = _a_fecha(it.get('fecha'))
        if f is not None and f <= hasta:
            vencen.append((f, it))
    vencen.sort(key=lambda x: x[0])
    ag[:] = [x for x in ag if all(x is not it for _f, it in vencen)]
    for _f, it in vencen:
        try:
            clave, n = _entregar_item(estado, it)
            if clave:
                res[clave] += n
        except Exception as e:
            logger.error(f"dias: no se pudo entregar '{it.get('tipo')}': {e}", exc_info=True)
    return res


# --- Ofertas de la IA ─────────────────────────────────────────────────────────

def programar_ofertas(estado: dict, rng: Optional[random.Random] = None) -> list:
    """Sorteo de las ofertas de la IA al cerrar el partido, con las probabilidades de siempre: la oferta
    se crea después, el día que asigna asignar_dias. Devuelve las entradas de agenda creadas."""
    from alpha_football import market
    azar = rng or random.Random()
    liga, mi = estado.get('liga'), estado.get('mi_equipo')
    nuevos: list = []
    if liga is None or mi is None:
        return nuevos
    from alpha_football import temporada as T
    libres = dias_libres(estado)
    en_ventana = [d for d in libres if T.ventana_en(estado, d)]       # v0.4.13.0: solo caen días con el mercado abierto
    if en_ventana:
        for _ in range(max(1, len(en_ventana) // 14)):                # huecos largos: una tirada por cada 14 días
            if azar.random() <= market.prob_oferta_ia(mi):
                nuevos.append(programar(estado, 'oferta', {'dias': [d.isoformat() for d in en_ventana]}))
    for _ in range(max(1, len(libres) // 14)):
        if azar.random() <= PROB_OFERTA_EXTERIOR:
            nuevos.append(programar(estado, 'oferta_ext'))
    return nuevos


# --- Lo que ocurre por fecha ──────────────────────────────────────────────────

def revisar_dia(estado: dict, fecha: date) -> Optional[str]:
    """v0.4.13.0: los ritmos de la temporada. Cantera, patrocinios, préstamos y traspasos acordados miran su
    propia clave y son idempotentes: se revisan cada día (al abrir una ventana concretan lo acordado, al
    llegar la mitad renuevan la cantera, etc.). La IA hace su ronda en los días sorteados de la ventana.
    Devuelve 'abre' / 'cierra' si hoy abre el mercado o es el día siguiente a su cierre."""
    from alpha_football import temporada as T
    pasos = (('cantera', 'revisar_jornada'), ('patrocinios', 'revisar_jornada'), ('prestamos', 'revisar_jornada'),
             ('temporadas', 'revisar_jornada'),                  # v0.4.16.0: el otro continente juega y cierra por fecha
             ('intercontinental', 'revisar_jornada'),            # v0.4.26.0: la final de diciembre
             ('premios', 'revisar_jornada'),                     # v0.4.17.0: galas del Balón de Oro y del Sudamericano
             ('finanzas', 'limitar_presupuestos'))               # v0.4.25.0: ningún club pasa de 350 M€
    for modulo, funcion in pasos:
        try:
            mod = __import__(f"alpha_football.{modulo}", fromlist=[funcion])
            getattr(mod, funcion)(estado)
        except Exception as e:
            logger.error(f"dias: no se pudo revisar {modulo}: {e}", exc_info=True)
    try:
        from alpha_football import traspasos_pendientes as TP
        TP.ejecutar(estado)
        TP.limpiar_ofertas(estado)
    except Exception as e:
        logger.error(f"dias: no se pudieron concretar los traspasos acordados: {e}", exc_info=True)
    try:    # v0.4.26.0: las respuestas de "lo analizamos" llegan por días (fecha_resp), no por jornada
        from alpha_football import dia_final as DF
        DF.responder(estado)
    except Exception as e:
        logger.error(f"dias: no se pudieron resolver los análisis del día: {e}", exc_info=True)
    try:    # v0.4.20.0: ningún club de la IA amanece con menos de 16 (llegadas acordadas, vueltas de préstamo...)
        from alpha_football.mercado_ia import asegurar_minimo_ia, resolver_remates
        asegurar_minimo_ia(estado)
        resolver_remates(estado)     # v0.4.21.0: vencido el plazo, los rematados que no fichaste se van
    except Exception as e:
        logger.error(f"dias: no se pudieron completar las plantillas de la IA: {e}", exc_info=True)
    try:
        if T.es_dia_de_ronda(estado, fecha):
            from alpha_football.mercado_ia import ronda_fichajes_ia
            ronda_fichajes_ia(estado, 'ventana')
    except Exception as e:
        logger.error(f"dias: no se pudo hacer la ronda de la IA: {e}", exc_info=True)
    return T.hito_del_dia(estado, fecha)


@contextmanager
def diferir_correos(estado: dict):
    """Mientras dura, correo.enviar guarda el mensaje en la agenda (sin día) en vez de en la bandeja.
    Sin reloj no hace nada: los correos se envían en el acto como siempre."""
    if not activo(estado):
        yield
        return
    previo = estado.get('_diferir_correos')
    estado['_diferir_correos'] = agenda(estado)
    try:
        yield
    finally:
        if previo is None:
            estado.pop('_diferir_correos', None)
        else:
            estado['_diferir_correos'] = previo
