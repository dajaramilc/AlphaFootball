# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Calendario real (v0.4.11.0)
Fecha real de cada partido del user. La temporada va de agosto a mayo en Europa y de enero a
diciembre en Sudamérica, y se arma A PARTIR de las ventanas de mercado (market.ventanas_mercado):
las jornadas de cada ventana quedan antes del 31 de agosto / 31 de enero, que son los cierres.
- Liga: sábado, domingo o lunes. Copa: martes, miércoles o jueves entre dos jornadas.
- Las fechas base salen de una semilla (no cambian al guardar y cargar). Solo se guarda lo
  reprogramado: datos_carrera['calendario'] = {'clave': [...], 'mov': {clave del partido: 'AAAA-MM-DD'}}.
- Dos partidos tuyos necesitan MIN_DIAS entre sí: revisar_choques mueve uno y avisa por correo.
- El descanso (energía) es proporcional a los días entre partidos: descanso_tras_liga.
Sin UI.
"""
from __future__ import annotations

import logging
import random
from datetime import date, timedelta
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

ANIO_BASE = {'europa': 2026, 'sudamerica': 2027}       # año en que empieza la temporada 1
# (mes, día, años a sumar al de inicio): cierre de la ventana de inicio, último sábado posible del
# tramo 2, primer día del tramo 3, cierre de la ventana de invierno y último sábado posible del tramo 4
PLAN = {
    'europa': {'cierre1': (8, 31, 0), 'fin2': (12, 21, 0), 'ini3': (1, 2, 1), 'cierre2': (1, 31, 1),
               'fin4': (5, 31, 1)},
    'sudamerica': {'cierre1': (1, 31, 0), 'fin2': (7, 20, 0), 'ini3': (8, 1, 0), 'cierre2': (8, 31, 0),
                   'fin4': (12, 13, 0)},
}
DIAS_LIGA = ((0, 55), (1, 40), (2, 5))       # días desde el sábado (sáb, dom, lun) y su peso
DIAS_COPA = ((3, 40), (4, 45), (5, 15))      # días desde el sábado anterior (mar, mié, jue) y su peso
MIN_DIAS = 3                                 # días mínimos entre dos partidos tuyos
DIAS_SEM = ('lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom')
MESES = ('ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic')
ETIQUETA_COPA = {'champions': 'UCL', 'libertadores': 'LIB'}


def texto_fecha(d: date, con_anio: bool = True) -> str:
    """'sáb 15 ago 2026' (o sin el año)."""
    t = f"{DIAS_SEM[d.weekday()]} {d.day} {MESES[d.month - 1]}"
    return f"{t} {d.year}" if con_anio else t


def _f(anio_inicio: int, t: tuple) -> date:
    return date(anio_inicio + t[2], t[0], t[1])


def _sabado_desde(d: date) -> date:
    """Primer sábado igual o posterior a d."""
    return d + timedelta(days=(5 - d.weekday()) % 7)


def _sabado_hasta(d: date) -> date:
    """Último sábado igual o anterior a d."""
    return d - timedelta(days=(d.weekday() - 5) % 7)


def _repartir(m: int, primero: date, ultimo: date) -> list:
    """m sábados repartidos parejo entre `primero` y `ultimo`; si no caben, el tramo se alarga."""
    if m <= 0:
        return []
    if m == 1:
        return [primero]
    huecos = max(m - 1, (ultimo - primero).days // 7)
    return [primero + timedelta(days=7 * int(i * huecos / (m - 1) + 0.5)) for i in range(m)]


def cierres(cont: str, anio_inicio: int) -> tuple:
    """(cierre de la ventana de inicio, cierre de la ventana de invierno)."""
    p = PLAN.get(cont, PLAN['europa'])
    return _f(anio_inicio, p['cierre1']), _f(anio_inicio, p['cierre2'])


@lru_cache(maxsize=64)
def sabados(n: int, cont: str, anio_inicio: int) -> tuple:
    """Sábado base de cada jornada (índice 0 = J1), anclado a los cierres de mercado."""
    from alpha_football.market import ventanas_mercado
    n = max(1, int(n))
    p = PLAN.get(cont, PLAN['europa'])
    vs = {v[2]: v for v in ventanas_mercado(n)}
    k1 = min(n, vs['inicio'][1])                              # última jornada de la ventana de inicio
    c1, c2 = cierres(cont, anio_inicio)
    m1 = max(0, k1 - 1)                                       # jornadas antes del primer cierre
    ult1 = _sabado_hasta(c1 - timedelta(days=3))              # su lunes también cae antes del cierre
    out = [ult1 - timedelta(days=7 * (m1 - 1 - i)) for i in range(m1)]
    tras1 = _sabado_desde(c1 + timedelta(days=1))
    if 'invierno' in vs:
        a, k2 = vs['invierno'][0], vs['invierno'][1]
        out += _repartir(a - k1, tras1, _sabado_hasta(_f(anio_inicio, p['fin2'])))
        out += _repartir(k2 - a, _sabado_desde(_f(anio_inicio, p['ini3'])), _sabado_hasta(c2 - timedelta(days=3)))
        out += _repartir(n - k2 + 1, _sabado_desde(c2 + timedelta(days=1)), _sabado_hasta(_f(anio_inicio, p['fin4'])))
    else:
        out += _repartir(n - m1, tras1, _sabado_hasta(_f(anio_inicio, p['fin4'])))
    for i in range(1, len(out)):                              # nunca dos jornadas el mismo fin de semana
        if out[i] <= out[i - 1]:
            out[i] = out[i - 1] + timedelta(days=7)
    return tuple(out[:n])


@lru_cache(maxsize=4096)
def _dia(semilla: str, pesos: tuple) -> int:
    """Día sorteado con esa semilla: siempre el mismo para el mismo partido."""
    return random.Random(semilla).choices([d for d, _w in pesos], weights=[w for _d, w in pesos])[0]


# --- Estado ───────────────────────────────────────────────────────────────────

def continente(estado: dict) -> str:
    try:
        from alpha_football.paises import es_sudamerica
        return 'sudamerica' if es_sudamerica(getattr(estado.get('liga'), 'tipo', '') or '') else 'europa'
    except Exception:
        return 'europa'


def anio(estado: dict) -> int:
    """Año en que empieza la temporada del user (temporada 1: 2026/27 en Europa, 2027 en Sudamérica)."""
    cont = continente(estado)
    mundo = ((estado.get('datos_carrera') or {}).get('mundo') or {}).get('anio') or {}
    if mundo.get(cont):
        return int(mundo[cont])
    return ANIO_BASE[cont] + int(estado.get('temporada', 1) or 1) - 1


def _n(estado: dict) -> int:
    return max(1, int(getattr(estado.get('liga'), 'num_jornadas', 22) or 22))


def _sabs(estado: dict) -> tuple:
    return sabados(_n(estado), continente(estado), anio(estado))


def asegurar(estado: dict) -> dict:
    """El calendario guardado de esta temporada; al cambiar de temporada, liga o club se rearma."""
    dc = estado.setdefault('datos_carrera', {})
    clave = [anio(estado), continente(estado), _n(estado), str(getattr(estado.get('mi_equipo'), 'id', ''))]
    cal = dc.get('calendario')
    if not isinstance(cal, dict) or cal.get('clave') != clave:
        cal = dc['calendario'] = {'clave': clave, 'mov': {}}
        dc.pop('descanso_pendiente', None)
    if not isinstance(cal.get('mov'), dict):
        cal['mov'] = {}
    return cal


def _movido(estado: dict, clave: str) -> Optional[date]:
    txt = asegurar(estado)['mov'].get(clave)
    try:
        return date.fromisoformat(txt) if txt else None
    except Exception:
        return None


def fecha_liga(estado: dict, jornada: int) -> date:
    """Día en que el user juega esa jornada de liga."""
    j = max(1, min(_n(estado), int(jornada or 1)))
    movido = _movido(estado, f"liga:{j}")
    if movido:
        return movido
    a = anio(estado)
    club = str(getattr(estado.get('mi_equipo'), 'id', ''))
    return _sabs(estado)[j - 1] + timedelta(days=_dia(f"liga-{a}-{club}-{j}", DIAS_LIGA))


# --- Copa ─────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1024)
def _copa_base(n: int, cont: str, anio_inicio: int, tipo: str, i: int, fj: tuple) -> date:
    """Día base de la fecha i de una copa: entre la jornada fj[i] y la siguiente."""
    sabs = sabados(n, cont, anio_inicio)
    j = max(1, min(n, fj[i]))
    if j >= n:                                        # la final: el sábado siguiente a la última jornada
        return sabs[-1] + timedelta(days=7)
    s1, s2 = sabs[j - 1], sabs[j]
    semanas = list(range(max(1, (s2 - s1).days // 7)))        # semana w: su martes es s1 + 3 + 7w
    for c in cierres(cont, anio_inicio):
        if s1 < c < s2:                               # hueco de un cierre de mercado: la copa va después
            semanas = [w for w in semanas if s1 + timedelta(days=3 + 7 * w) > c] or semanas[-1:]
    orden = sum(1 for x in fj[:i] if x == fj[i])      # otra fecha en el mismo hueco: una semana después
    w = semanas[min(len(semanas) - 1, (len(semanas) - 1) // 2 + orden)]
    return s1 + timedelta(days=7 * w + _dia(f"copa-{anio_inicio}-{tipo}-{i}", DIAS_COPA))


def fecha_copa(estado: dict, tipo: str, i: int) -> Optional[date]:
    """Día de la fecha `i` de esa copa (None si la copa o la fecha no existen)."""
    try:
        from alpha_football import competiciones as CP
        c = CP.copa(estado, tipo)
        fj = tuple(int(x) for x in ((c or {}).get('fechas_jornada') or ()))
        i = int(i)
        if not c or not 0 <= i < len(fj):
            return None
        return (_movido(estado, f"copa:{tipo}:{i}")
                or _copa_base(_n(estado), continente(estado), anio(estado), tipo, i, fj))
    except Exception as e:
        logger.error(f"No se pudo calcular la fecha {i} de la copa {tipo}: {e}")
        return None


# --- Partidos del user ────────────────────────────────────────────────────────

def eventos_user(estado: dict) -> list:
    """Tus partidos de liga y de copa ordenados por fecha."""
    out: list = []
    liga, mi = estado.get('liga'), estado.get('mi_equipo')
    if liga is None or mi is None:
        return out
    try:
        nombres = {e.id: e.nombre for e in liga.equipos}
        for p in getattr(liga, 'calendario', None) or []:
            if mi.id not in (p.local_id, p.visitante_id):
                continue
            loc = p.local_id == mi.id
            gf, gc = (p.goles_local, p.goles_visitante) if loc else (p.goles_visitante, p.goles_local)
            out.append({'clave': f"liga:{int(p.jornada)}", 'tipo': 'liga', 'num': int(p.jornada),
                        'fecha': fecha_liga(estado, p.jornada), 'jugado': bool(p.jugado), 'local': loc,
                        'rival': nombres.get(p.visitante_id if loc else p.local_id, '?'),
                        'gf': gf if p.jugado else None, 'gc': gc if p.jugado else None,
                        'etiqueta': f"J{int(p.jornada)}"})
    except Exception as e:
        logger.error(f"calendario: no se pudieron leer los partidos de liga: {e}")
    try:
        from alpha_football import competiciones as CP
        t = CP.tipo_copa_user(estado)
        c = CP.copa(estado, t) if t else None
        for p in (c or {}).get('partidos') or []:
            if mi.nombre not in (p.get('local'), p.get('visitante')):
                continue
            num = int(p.get('fecha', 0) or 0)
            f = fecha_copa(estado, t, num)
            if f is None:
                continue
            loc, jugado = p.get('local') == mi.nombre, bool(p.get('jugado'))
            gf, gc = (p.get('gl'), p.get('gv')) if loc else (p.get('gv'), p.get('gl'))
            out.append({'clave': f"copa:{t}:{num}", 'tipo': 'copa', 'num': num, 'fecha': f, 'jugado': jugado,
                        'local': loc, 'rival': p.get('visitante') if loc else p.get('local'),
                        'gf': gf if jugado else None, 'gc': gc if jugado else None,
                        'etiqueta': ETIQUETA_COPA.get(t, 'COPA')})
    except Exception as e:
        logger.error(f"calendario: no se pudieron leer los partidos de copa: {e}")
    out.sort(key=lambda x: (x['fecha'], x['tipo'] != 'liga'))
    return out


def proximo_evento(estado: dict) -> Optional[dict]:
    return next((e for e in eventos_user(estado) if not e['jugado']), None)


def hoy(estado: dict) -> date:
    """El día en que estás parado: el de tu próximo partido (o el del último si ya no quedan)."""
    evs = eventos_user(estado)
    prox = next((e for e in evs if not e['jugado']), None)
    if prox is not None:
        return prox['fecha']
    return evs[-1]['fecha'] if evs else _sabs(estado)[0]


def texto_proximo(estado: dict) -> str:
    """Fecha de tu próximo partido ('' si no hay)."""
    try:
        ev = proximo_evento(estado)
        return texto_fecha(ev['fecha']) if ev else ''
    except Exception as e:
        logger.error(f"calendario: no se pudo leer el próximo partido: {e}")
        return ''


# --- Reprogramación ───────────────────────────────────────────────────────────

def _opciones(ev: dict) -> list:
    """Otros días posibles para ese partido (liga: su fin de semana; copa: martes a jueves de su
    semana), del más cercano al más lejano."""
    f = ev['fecha']
    if ev['tipo'] == 'liga':
        base = f - timedelta(days=(f.weekday() - 5) % 7)          # su sábado
    else:
        base = f - timedelta(days=(f.weekday() - 1) % 7)          # su martes
    dias = [base + timedelta(days=k) for k in (0, 1, 2)]
    return sorted((d for d in dias if d != f), key=lambda d: abs((d - f).days))


def _cabe(evs: list, k: int, nueva: date) -> bool:
    """¿El partido k puede pasar a `nueva` sin quedar a menos de MIN_DIAS de sus vecinos?"""
    antes = evs[k - 1]['fecha'] if k > 0 else None
    despues = evs[k + 1]['fecha'] if k + 1 < len(evs) else None
    return ((antes is None or (nueva - antes).days >= MIN_DIAS)
            and (despues is None or (despues - nueva).days >= MIN_DIAS))


def _avisar_cambio(estado: dict, ev: dict, nueva: date, otro: dict) -> None:
    try:
        from alpha_football import correo as C
        que = f"la jornada {ev['num']} de liga" if ev['tipo'] == 'liga' else "el partido de copa"
        C.enviar(estado, 'club', f"Partido reprogramado: {ev['etiqueta']} contra {ev['rival']}",
                 f"{que[0].upper()}{que[1:]} contra {ev['rival']} "              # v0.4.18.0: sin la frase de los días de descanso
                 f"pasa del {texto_fecha(ev['fecha'], False)} al {texto_fecha(nueva, False)}. Quedaba demasiado "
                 f"cerca de {otro['etiqueta']} contra {otro['rival']} ({texto_fecha(otro['fecha'], False)}).",
                 C.accion('calendario_screen', "VER CALENDARIO"))
    except Exception as e:
        logger.error(f"No se pudo avisar el partido reprogramado: {e}")


def revisar_choques(estado: dict, max_eventos: int = 3) -> list:
    """Mira tus próximos partidos: si dos quedan a menos de MIN_DIAS, mueve uno y avisa por correo.
    Orden: el de liga dentro de su fin de semana, el de copa entre martes y jueves, el de liga al
    fin de semana siguiente. Devuelve los cambios hechos ([{'clave', 'de', 'a'}])."""
    cambios: list = []
    try:
        if estado.get('liga') is None or estado.get('mi_equipo') is None:
            return cambios
        cal = asegurar(estado)
        for _vuelta in range(6):                                  # cada vuelta arregla un choque
            evs = eventos_user(estado)
            pend = [k for k, e in enumerate(evs) if not e['jugado']][:max_eventos]
            a = next((k for k in pend[:-1] if (evs[k + 1]['fecha'] - evs[k]['fecha']).days < MIN_DIAS), None)
            if a is None:
                break
            b = a + 1
            intentos = [(k, d) for k in (a, b) if evs[k]['tipo'] == 'liga' for d in _opciones(evs[k])]
            intentos += [(k, d) for k in (a, b) if evs[k]['tipo'] == 'copa' for d in _opciones(evs[k])]
            intentos += [(k, evs[k]['fecha'] + timedelta(days=7)) for k in (b, a) if evs[k]['tipo'] == 'liga']
            hecho = next(((k, d) for k, d in intentos if _cabe(evs, k, d)), None)
            if hecho is None:
                logger.info(f"calendario: choque sin solución entre {evs[a]['clave']} y {evs[b]['clave']}")
                break
            k, nueva = hecho
            cal['mov'][evs[k]['clave']] = nueva.isoformat()
            cambios.append({'clave': evs[k]['clave'], 'de': evs[k]['fecha'], 'a': nueva})
            _avisar_cambio(estado, evs[k], nueva, evs[b] if k == a else evs[a])
    except Exception as e:
        logger.error(f"calendario: error revisando los choques: {e}", exc_info=True)
    return cambios


# --- Descanso ─────────────────────────────────────────────────────────────────

def dias_por_jornada(estado: dict) -> float:
    """Días que hay en promedio entre dos jornadas: con esos días se recupera lo de una jornada."""
    s = _sabs(estado)
    return max(1.0, (s[-1] - s[0]).days / max(1, len(s) - 1))


def descanso_tras_liga(estado: dict, jornada: int) -> tuple:
    """(días hasta el próximo partido de cualquier competición, días que quedan después hasta la
    jornada siguiente). Sin copa en ese hueco: (todos los días, 0)."""
    jornada = int(jornada)
    if jornada >= _n(estado):
        return 7.0, 0.0
    f0 = fecha_liga(estado, jornada)
    total = max(1, (fecha_liga(estado, jornada + 1) - f0).days)
    antes = None
    try:
        from alpha_football import competiciones as CP
        for t in ('champions', 'libertadores'):
            c = CP.copa(estado, t)
            if not c or c.get('campeon'):
                continue
            for i, x in enumerate(c.get('fechas_jornada') or []):
                if int(x) != jornada:
                    continue
                f = fecha_copa(estado, t, i)
                d = (f - f0).days if f else 0
                if 0 < d < total:
                    antes = d if antes is None else min(antes, d)
    except Exception as e:
        logger.error(f"calendario: no se pudo leer la copa para el descanso: {e}")
    if antes is None:
        return float(total), 0.0
    return float(antes), float(total - antes)


def aplicar_descanso_pendiente(estado: dict) -> float:
    """Aplica (una sola vez) el descanso que quedó esperando a tu partido de copa. Devuelve los días."""
    dias = float((estado.get('datos_carrera') or {}).pop('descanso_pendiente', 0) or 0)
    if dias > 0:
        from alpha_football.energia import recuperar_todos
        recuperar_todos(estado, dias)
    return dias


def tras_partido_copa_user(estado: dict) -> None:
    """Al cerrar tu partido de copa: el resto del descanso hasta la jornada siguiente y los choques."""
    try:
        aplicar_descanso_pendiente(estado)
        revisar_choques(estado)
    except Exception as e:
        logger.error(f"calendario: error tras el partido de copa: {e}")
