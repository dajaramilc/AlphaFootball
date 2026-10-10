# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Generadores de noticias (v0.4.23.0).

`generar_jornada(estado)` lo llama `noticias.cierre_jornada` una vez por jornada de liga del user (con su partido
ya contado) y publica los hechos de esa jornada; `generar_cierre_temporada(...)` lo llama
`avanzar_nueva_temporada` con los datos del cierre de TU temporada. Las noticias de fichajes, cambios de DT y el
cierre del otro continente las publican sus propios módulos.

Solo se publica lo que de verdad pasó: nunca se inventan resultados. Cada generador corre en su propio `try`
(uno que falla se registra y los demás siguen) y deja su memoria en `datos_carrera['noticias_gen']` (solo
tipos JSON). Los récords viven en `datos_carrera['records']`.
"""
from __future__ import annotations

import logging
import random
from typing import Optional

from alpha_football import noticias as N
from alpha_football.paises import PAISES

logger = logging.getLogger(__name__)

PAIS_POR_LIGA = {p['liga_id']: p['nombre'] for p in PAISES}
DIFERENCIA_GOLEADA = 4          # goles de diferencia para contar como goleada
GAP_SORPRESA = 8                # puntos de nivel (media del mejor XI) que el ganador tiene de menos
MAX_RESULTADOS_TUYOS = 2        # noticias de resultados de tu liga por jornada
LESION_MIN_DIAS = 21
OVR_FIGURA = 80
JORNADAS_ENTRE_LESIONES = 8     # no se repite la lesión de un mismo jugador antes de estas jornadas
CADA_N_JORNADAS_PROMESAS = 6
PROB_POLEMICO = 0.12
RECORDS_BASE = {'goles': 25, 'asistencias': 15}      # récord inicial de una temporada de liga
CERCA_DEL_RECORD = 3
NOMBRE_STAT = {'goles': "goles", 'asistencias': "asistencias"}


# --- lectura del estado (funciones sueltas para poder aislarlas en los tests) -------------------------------

def _nivel(equipo) -> int:
    from alpha_football.market import nivel_club
    return nivel_club(equipo)


def _jornada_user(estado: dict) -> int:
    """Partidos de liga que el user ya jugó esta temporada."""
    from alpha_football.salidas import _clave_jornada
    return int(_clave_jornada(estado)[1])


def _jornada_abs(estado: dict) -> int:
    """Jornada contada desde el inicio de la carrera (para espaciar noticias entre temporadas)."""
    liga = estado.get('liga')
    n = int(getattr(liga, 'num_jornadas', 0) or 0) or 22
    return (int(estado.get('temporada', 1) or 1) - 1) * n + _jornada_user(estado)


def _ligas(estado: dict) -> list:
    """[(liga, es_la_tuya)]: tu liga y las que avanzan de fondo (nunca repite la tuya)."""
    mia = estado.get('liga')
    out = []
    if mia is not None and getattr(mia, 'equipos', None):
        out.append((mia, True))
    vistas = {id(mia)}
    for mapa in (estado.get('primera_division') or {}, estado.get('segunda_division') or {}):
        for liga in mapa.values():
            if liga is not None and id(liga) not in vistas and len(getattr(liga, 'equipos', None) or []) >= 2:
                vistas.add(id(liga))
                out.append((liga, False))
    return out


def _memoria(estado: dict) -> dict:
    dc = estado.setdefault('datos_carrera', {})
    m = dc.setdefault('noticias_gen', {})
    m.setdefault('lesiones', {})          # "<club>:<jugador>" -> jornada absoluta en que se anunció
    m.setdefault('promesas', [])          # "<club>:<jugador>" ya destacados
    m.setdefault('promesa_ultima', -1)
    m.setdefault('avisos', [])            # avisos de récord ya dados
    m.setdefault('balon', [])             # temporadas con candidatos publicados
    records = dc.setdefault('records', {})
    for stat, base in RECORDS_BASE.items():
        records.setdefault(stat, {'valor': base, 'nombre': '', 'temporada': 0})
    return m


def _ya(estado: dict, clave: str) -> bool:
    return any(n.get('clave') == clave for n in N.lista(estado))


def _jugadores(liga):
    for eq in getattr(liga, 'equipos', None) or []:
        for j in getattr(eq, 'jugadores', None) or []:
            yield eq, j


def _clave_j(eq, j) -> str:
    return f"{getattr(eq, 'id', '?')}:{getattr(j, 'id', '?')}"


def _nombre(j) -> str:
    return getattr(j, 'nombre_completo', None) or f"{getattr(j, 'nombre', '')} {getattr(j, 'apellido', '')}".strip()


# --- resultados -----------------------------------------------------------------------------------------------

def _ultima_jugada(liga) -> int:
    js = [p.jornada for p in getattr(liga, 'calendario', None) or [] if p.jugado]
    return max(js) if js else 0


def _posicion(liga, equipo) -> int:
    orden = sorted(liga.equipos, key=lambda e: (e.puntos, e.gf - e.gc, e.gf), reverse=True)
    return next((i + 1 for i, e in enumerate(orden) if e.id == equipo.id), 0)


def _evaluar(liga, p, equipos: dict) -> Optional[dict]:
    """El partido como noticia posible: {'importancia', 'diff', 'tipo', ...} o None si no destaca."""
    from alpha_football.data.clasicos import es_clasico
    loc, vis = equipos.get(p.local_id), equipos.get(p.visitante_id)
    if loc is None or vis is None or p.goles_local is None or p.goles_visitante is None:
        return None
    gl, gv = int(p.goles_local), int(p.goles_visitante)
    diff = abs(gl - gv)
    gana = loc if gl > gv else vis if gv > gl else None
    pierde = vis if gana is loc else loc if gana is vis else None
    gap = (_nivel(pierde) - _nivel(gana)) if gana is not None else 0
    clasico = bool(es_clasico(loc, vis))
    imp, tipo = 0, None
    if clasico:
        imp, tipo = (4 if diff >= 3 else 3), 'clasico'
    if gap >= GAP_SORPRESA:
        imp, tipo = max(imp, 4 if gap >= 12 else 3), tipo or 'sorpresa'
    if diff >= DIFERENCIA_GOLEADA:
        imp, tipo = max(imp, 4 if diff >= 5 else 3), tipo or 'goleada'
    if tipo is None:
        return None
    return {'p': p, 'loc': loc, 'vis': vis, 'gl': gl, 'gv': gv, 'diff': diff, 'gana': gana, 'pierde': pierde,
            'tipo': tipo, 'importancia': imp, 'clasico': clasico}


def _texto_resultado(liga, c: dict) -> tuple:
    """(titular, cuerpo) a partir de datos reales del partido."""
    loc, vis, gl, gv = c['loc'], c['vis'], c['gl'], c['gv']
    g, per = c['gana'], c['pierde']
    marcador = f"{max(gl, gv)}-{min(gl, gv)}"
    if c['tipo'] == 'clasico':
        titular = (f"Clásico para {g.nombre}: {marcador} ante {per.nombre}" if g is not None
                   else f"Clásico igualado: {loc.nombre} {gl}-{gv} {vis.nombre}")
    elif c['tipo'] == 'sorpresa':
        titular = f"Sorpresa: {g.nombre} vence a {per.nombre} ({marcador})"
    else:
        titular = f"{g.nombre} golea {marcador} a {per.nombre}"
    if g is not None:
        cuerpo = (f"{liga.nombre}, jornada {c['p'].jornada}: {g.nombre} (puesto {_posicion(liga, g)}) derrotó a "
                  f"{per.nombre} (puesto {_posicion(liga, per)}) por {marcador}.")
    else:
        cuerpo = f"{liga.nombre}, jornada {c['p'].jornada}: {loc.nombre} y {vis.nombre} empataron {gl}-{gv}."
    return titular, cuerpo


def _publicar_resultado(estado: dict, liga, c: dict, importancia: int) -> int:
    p = c['p']
    clave = (f"res:{estado.get('temporada', 1)}:{liga.tipo}:{getattr(liga, 'division', 1)}:{p.jornada}:"
             f"{p.local_id}-{p.visitante_id}")
    if _ya(estado, clave):
        return 0
    titular, cuerpo = _texto_resultado(liga, c)
    N.publicar(estado, 'resultado', titular, cuerpo, importancia=importancia, equipos=[c['loc'], c['vis']], clave=clave)
    return 1


def _resultados(estado: dict, rng) -> int:
    propios, ajenos = [], []
    for liga, tuya in _ligas(estado):
        j = _ultima_jugada(liga)
        if j <= 0:
            continue
        equipos = {e.id: e for e in liga.equipos}
        for p in liga.calendario:
            if p.jornada != j or not p.jugado:
                continue
            c = _evaluar(liga, p, equipos)
            if c:
                (propios if tuya else ajenos).append((liga, c))
    n = 0
    propios.sort(key=lambda x: (x[1]['importancia'], x[1]['diff']), reverse=True)
    for liga, c in propios[:MAX_RESULTADOS_TUYOS]:
        n += _publicar_resultado(estado, liga, c, c['importancia'])
    # de otras ligas solo lo más destacado (una por jornada): goleadas de 5+ o clásicos con 3+ de diferencia
    destacados = [(l, c) for l, c in ajenos if c['diff'] >= 5 or (c['clasico'] and c['diff'] >= 3)]
    if destacados:
        liga, c = max(destacados, key=lambda x: (x[1]['diff'], x[1]['clasico']))
        n += _publicar_resultado(estado, liga, c, 5 if (c['clasico'] and c['diff'] >= 4) else 4)
    return n


# --- lesiones, promesas, balón de oro, récords, polémico -----------------------------------------------------------

def _lesiones(estado: dict, rng) -> int:
    liga = estado.get('liga')
    m = _memoria(estado)
    ja = _jornada_abs(estado)
    n = 0
    for eq, j in _jugadores(liga):
        if int(getattr(j, 'lesion_dias', 0) or 0) < LESION_MIN_DIAS or j.overall < OVR_FIGURA:
            continue
        k = _clave_j(eq, j)
        if ja - m['lesiones'].get(k, -10_000) < JORNADAS_ENTRE_LESIONES:
            continue
        m['lesiones'][k] = ja
        dias = int(j.lesion_dias)
        fuera = f"unos {dias // 30} meses" if dias >= 60 else f"unos {dias} días"
        N.publicar(estado, 'lesion', f"Lesión grave de {_nombre(j)}",
                   f"{_nombre(j)} ({eq.nombre}, media {j.overall}) estará {fuera} fuera de las canchas.",
                   importancia=4 if (j.overall >= 85 or dias >= 60) else 3, equipos=[eq], jugadores=[j])
        n += 1
    return n


def _promesas(estado: dict, rng) -> int:
    m = _memoria(estado)
    ja = _jornada_abs(estado)
    if ja <= 0 or ja % CADA_N_JORNADAS_PROMESAS != 0 or m['promesa_ultima'] == ja:
        return 0
    elegido = None
    for liga, _tuya in _ligas(estado):
        for eq, j in _jugadores(liga):
            pot = int(getattr(j, 'potencial', 0) or 0)
            if j.edad <= 21 and pot >= 78 and pot - j.overall >= 12 and _clave_j(eq, j) not in m['promesas']:
                if elegido is None or (pot, -j.overall) > (elegido[2], -elegido[1].overall):
                    elegido = (eq, j, pot)
    if elegido is None:
        return 0
    eq, j, pot = elegido
    m['promesa_ultima'] = ja
    m['promesas'].append(_clave_j(eq, j))
    N.publicar(estado, 'promesa', f"{_nombre(j)}, la joven promesa de {eq.nombre}",
               f"A los {j.edad} años ya apunta a una media de {pot}; hoy marca {j.overall}. El mundo del fútbol lo sigue de cerca.",
               importancia=3, equipos=[eq], jugadores=[j])
    return 1


def _candidatos_balon(estado: dict, rng) -> int:
    from alpha_football.premios import PESO_LIGA_1A, puntaje_jugador
    liga = estado.get('liga')
    m = _memoria(estado)
    t = int(estado.get('temporada', 1) or 1)
    if t in m['balon'] or _jornada_user(estado) != int(liga.num_jornadas) // 2:
        return 0
    ranking = []
    for lg, _tuya in _ligas(estado):
        if getattr(lg, 'division', 1) != 1:
            continue
        peso = PESO_LIGA_1A.get(lg.tipo, 0.75)
        for eq, j in _jugadores(lg):
            if int(getattr(j, 'partidos_jugados', 0) or 0) > 0:
                ranking.append((puntaje_jugador(j, peso, False, False), eq, j))
    ranking.sort(key=lambda x: x[0], reverse=True)
    top = ranking[:3]
    if not top:
        return 0
    m['balon'].append(t)
    lineas = [f"{i + 1}. {_nombre(j)} ({eq.nombre}) · {j.goles} goles, {j.asistencias} asistencias, nota {j.promedio_nota:.1f}"
              for i, (_p, eq, j) in enumerate(top)]
    N.publicar(estado, 'premio', f"Balón de Oro: {_nombre(top[0][2])} lidera la carrera",
               "A mitad de temporada los candidatos son:\n" + "\n".join(lineas), importancia=4,
               equipos=[x[1] for x in top], jugadores=[x[2] for x in top])
    return 1


def _records(estado: dict, rng) -> int:
    _memoria(estado)
    records = estado['datos_carrera']['records']
    avisos = estado['datos_carrera']['noticias_gen']['avisos']
    t = int(estado.get('temporada', 1) or 1)
    n = 0
    for stat, atributo in (('goles', 'goles'), ('asistencias', 'asistencias')):
        mejor = None
        for liga, _tuya in _ligas(estado):
            for eq, j in _jugadores(liga):
                v = int(getattr(j, atributo, 0) or 0)
                if mejor is None or v > mejor[0]:
                    mejor = (v, eq, j)
        if mejor is None or mejor[0] <= 0:
            continue
        v, eq, j = mejor
        rec = records[stat]
        clave = f"{t}:{stat}:{_clave_j(eq, j)}"
        if v > rec['valor']:
            records[stat] = {'valor': v, 'nombre': _nombre(j), 'temporada': t}
            N.publicar(estado, 'record', f"{_nombre(j)} bate el récord de {NOMBRE_STAT[stat]}: {v}",
                       f"{_nombre(j)} ({eq.nombre}) llega a {v} {NOMBRE_STAT[stat]} en la temporada y supera la marca anterior ({rec['valor']}).",
                       importancia=4, equipos=[eq], jugadores=[j])
            avisos.append(clave + ":cerca")
            n += 1
        elif rec['valor'] - v <= CERCA_DEL_RECORD and clave + ":cerca" not in avisos:
            avisos.append(clave + ":cerca")
            falta = rec['valor'] - v
            N.publicar(estado, 'record', f"{_nombre(j)} acecha el récord de {NOMBRE_STAT[stat]}",
                       f"{_nombre(j)} ({eq.nombre}) lleva {v} {NOMBRE_STAT[stat]}: " +
                       (f"le faltan {falta} para el récord de {rec['valor']}." if falta else f"iguala el récord de {rec['valor']}."),
                       importancia=4, equipos=[eq], jugadores=[j])
            n += 1
        del avisos[:-200]
    return n


def _polemico(estado: dict, rng) -> int:
    from alpha_football.prensa import mover_moral
    mi = estado.get('mi_equipo')
    if mi is None or rng.random() >= PROB_POLEMICO:
        return 0
    cands = [j for j in getattr(mi, 'jugadores', None) or [] if getattr(j, 'personalidad', '') == 'polemico' and j.moral < 50]
    if not cands:
        return 0
    j = rng.choice(cands)
    mover_moral(mi.jugadores, -1)
    N.publicar(estado, 'vestuario', f"{_nombre(j)} critica al DT en la prensa",
               f"El polémico {_nombre(j)} ({mi.nombre}) filtró su malestar a los medios y el vestuario lo nota: baja la moral del plantel.",
               importancia=3, equipos=[mi], jugadores=[j])
    return 1


def _logros(estado: dict, rng) -> int:
    """Logros que salen de mirar el estado (título de liga, final continental, fichaje de lujo); cada uno publica
    su propia noticia, así que aquí solo se cuenta."""
    from alpha_football import logros as _lg
    return len(_lg.revisar(estado))


def generar_jornada(estado: dict, rng=None) -> int:
    """Publica las noticias de la jornada que se acaba de cerrar. Devuelve cuántas publicó."""
    if not estado.get('liga') or not estado.get('mi_equipo'):
        return 0
    rng = rng or random
    try:
        _memoria(estado)
    except Exception as e:
        logger.error(f"noticias_gen: no se pudo preparar la memoria: {e}", exc_info=True)
        return 0
    total = 0
    for generador in (_resultados, _lesiones, _promesas, _candidatos_balon, _records, _polemico, _logros):
        try:
            total += int(generador(estado, rng) or 0)
        except Exception as e:
            logger.error(f"noticias_gen.{getattr(generador, '__name__', generador)}: {e}", exc_info=True)
    return total


# --- cierre de la temporada del user ------------------------------------------------------------------------------

def _cierre_campeones(estado: dict, liga, campeon_liga, campeones_copas, kw: dict) -> int:
    from alpha_football import competiciones as CP
    n = 0
    if campeon_liga:
        nombre = getattr(campeon_liga, 'nombre', campeon_liga)
        N.publicar(estado, 'campeon', f"{nombre} es campeón de {liga.nombre}",
                   f"{nombre} gana {liga.nombre} y se lleva el título de la temporada {kw['temporada']}.",
                   importancia=5, clave=f"camp:{kw['temporada']}:liga", **kw)
        n += 1
    for tipo, club in (campeones_copas or {}).items():
        if not club:
            continue
        nombre = getattr(club, 'nombre', club)
        copa = CP.NOMBRE_COPA.get(tipo, tipo)
        N.publicar(estado, 'campeon', f"{nombre} gana la {copa}",
                   f"{nombre} conquista la {copa} de la temporada {kw['temporada']}.",
                   importancia=5, clave=f"camp:{kw['temporada']}:{tipo}", **kw)
        n += 1
    return n


def _cierre_movimientos(estado: dict, liga, movimientos, kw: dict) -> int:
    n = 0
    resto = []
    for mov in movimientos or []:
        asc, des = list(mov.get('ascendidos') or []), list(mov.get('descendidos') or [])
        if mov.get('tipo') == liga.tipo:
            if asc:
                N.publicar(estado, 'descenso', f"Ascienden a Primera: {', '.join(asc)}",
                           f"{', '.join(asc)} suben de categoría en {PAIS_POR_LIGA.get(liga.tipo, liga.tipo)}.",
                           importancia=5, categoria='ascenso', **kw)
                n += 1
            if des:
                N.publicar(estado, 'descenso', f"Descienden a Segunda: {', '.join(des)}",
                           f"{', '.join(des)} pierden la categoría en {PAIS_POR_LIGA.get(liga.tipo, liga.tipo)}.",
                           importancia=5, categoria='descenso', **kw)
                n += 1
        elif asc or des:
            resto.append(f"{PAIS_POR_LIGA.get(mov.get('tipo'), mov.get('tipo'))}: suben {', '.join(asc) or '—'}; "
                         f"bajan {', '.join(des) or '—'}.")
    if resto:
        N.publicar(estado, 'descenso', "Ascensos y descensos en el resto de las ligas", "\n".join(resto),
                   importancia=4, categoria='descenso', **kw)
        n += 1
    return n


def _cierre_equipo_del_anio(estado: dict, liga, kw: dict) -> int:
    min_pj = max(3, int(liga.num_jornadas) // 2)
    cupo = {'POR': 1, 'DEF': 4, 'MED': 3, 'DEL': 3}
    por_pos = {pos: [] for pos in cupo}
    for eq, j in _jugadores(liga):
        if int(getattr(j, 'partidos_jugados', 0) or 0) >= min_pj and getattr(j, 'posicion', '') in cupo:
            por_pos[j.posicion].append((float(getattr(j, 'promedio_nota', 0) or 0), int(getattr(j, 'goles', 0) or 0), eq, j))
    if any(len(por_pos[pos]) < n for pos, n in cupo.items()):
        return 0
    once = []
    for pos, n in cupo.items():
        once += [(pos, x) for x in sorted(por_pos[pos], key=lambda x: (x[0], x[1]), reverse=True)[:n]]
    lineas = [f"{pos}  {_nombre(x[3])} ({x[2].nombre}) · nota {x[0]:.1f}" for pos, x in once]
    N.publicar(estado, 'premio', f"Equipo del año de {liga.nombre}", "\n".join(lineas), importancia=4,
               equipos=[x[2] for _p, x in once], jugadores=[x[3] for _p, x in once], **kw)
    return 1


def _pasos_cierre(estado: dict, temporada, pasos) -> int:
    """Corre cada paso del cierre en su propio try, con la temporada que se cierra (no la que ya subió)."""
    liga = estado.get('liga')
    if liga is None:
        return 0
    try:
        _memoria(estado)
    except Exception as e:
        logger.error(f"noticias_gen: no se pudo preparar la memoria del cierre: {e}", exc_info=True)
        return 0
    kw = {'temporada': int(temporada), 'jornada': int(getattr(liga, 'num_jornadas', 0) or 0)}
    total = 0
    for paso, args in pasos:
        try:
            total += int(paso(estado, liga, *args, kw) or 0)
        except Exception as e:
            logger.error(f"noticias_gen.{paso.__name__}: {e}", exc_info=True)
    return total


def generar_cierre_temporada(estado: dict, temporada, campeon_liga, campeones_copas, movimientos=None) -> int:
    """Noticias del cierre de TU temporada: campeones, equipo del año y, si ya se conocen, los ascensos y descensos.
    Se publican con la temporada que se cierra aunque el contador ya haya subido. Hay que llamarla con la tabla
    final todavía intacta (antes de intercambiar los clubes entre divisiones); los ascensos y descensos pueden venir
    después con `generar_cierre_movimientos`. Devuelve cuántas publicó."""
    pasos = [(_cierre_campeones, (campeon_liga, campeones_copas)), (_cierre_equipo_del_anio, ())]
    if movimientos is not None:
        pasos.insert(1, (_cierre_movimientos, (movimientos,)))
    return _pasos_cierre(estado, temporada, pasos)


def generar_cierre_movimientos(estado: dict, temporada, movimientos) -> int:
    """Ascensos y descensos de la temporada que se cierra (`movimientos` = lo que devuelve
    temporadas.ascensos_descensos). Se llama cuando el intercambio de clubes ya se hizo."""
    return _pasos_cierre(estado, temporada, [(_cierre_movimientos, (movimientos,))]) if movimientos else 0
