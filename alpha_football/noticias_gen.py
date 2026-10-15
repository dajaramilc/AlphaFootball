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
VENTANA_CARRERA = 3             # v0.4.26.0: jornadas desde el aviso en que la carrera de un premio aún se publica
OVR_IMPORTANTE = 76             # v0.4.26.0: "importante de su club": de sus 3 mejores y con esta media o más
PROB_TRANSFERIBLE = 0.25        # por jornada, con el enfriamiento cumplido
JORNADAS_ENTRE_TRANSFERIBLES = 4
JORNADAS_TRANSFERIBLE = 6       # cuánto dura la marca de transferible que pone esta noticia
JORNADAS_RECORDAR_TRANSFERIBLE = 24    # y cuánto se recuerda para no repetir al mismo jugador
OVR_NO_VEN = 78                 # v0.4.26.0: "bueno" para "No ven a X en el equipo"
PARTIDOS_SIN_JUGAR = 4          # partidos seguidos de su club sin que el bueno y sano juegue
MAX_NO_VEN_POR_JORNADA = 1


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
    m.setdefault('sudamericano', [])      # v0.4.26.0: ídem para la carrera al Jugador Sudamericano del Año
    m.setdefault('transferibles', {})     # v0.4.26.0: "<jugador>" -> [jornada absoluta, 1 si la marca la puso la noticia]
    m.setdefault('transferible_ultima', -10_000)
    m.setdefault('sin_jugar', {})         # v0.4.26.0: "<club>:<jugador>" -> [PJ del club, PJ del jugador, racha, avisado]
    m.setdefault('titulos', [])           # v0.4.25.0: títulos ya anunciados ("camp:<temporada>:<liga>:<división>"...)
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


def _ranking_carrera(estado: dict, solo_sudamerica: bool, media_min: float) -> list:
    """[(puntaje, club, jugador)] de la carrera de un premio, de mayor a menor puntaje y con los que llegan a la
    media mínima primero. Mismo pool y misma fórmula que premios.calcular_balon_de_oro / calcular_sudamericano."""
    from alpha_football import premios as PR
    from alpha_football.paises import SUDAMERICA
    ranking = []
    for lg, _tuya in _ligas(estado):
        if solo_sudamerica and getattr(lg, 'tipo', '') not in SUDAMERICA:
            continue
        primera = int(getattr(lg, 'division', 1) or 1) == 1
        peso = PR.PESO_LIGA_1A.get(getattr(lg, 'tipo', ''), 0.75) if primera else PR.PESO_LIGA_2A
        for eq, j in _jugadores(lg):
            if int(getattr(j, 'partidos_jugados', 0) or 0) > 0:
                ranking.append((PR.puntaje_jugador(j, peso, False, False), eq, j))
    ranking.sort(key=lambda x: x[0], reverse=True)
    return PR.priorizar_por_media(ranking, lambda x: float(getattr(x[2], 'overall', 0) or 0), media_min)


def _carrera(estado: dict, memoria: str, solo_sudamerica: bool, num: int, den: int) -> int:
    """v0.4.26.0: la noticia de la carrera de un premio cuando se juegan `num`/`den` de la temporada: los tres
    candidatos con su media, goles y nota. Una vez por temporada. El Balón de Oro y el Sudamericano van en
    noticias separadas y en fechas distintas."""
    from alpha_football import premios as PR
    liga = estado.get('liga')
    m = _memoria(estado)
    t = int(estado.get('temporada', 1) or 1)
    aviso = int(liga.num_jornadas) * num // den
    if t in m[memoria] or not aviso <= _jornada_user(estado) < aviso + VENTANA_CARRERA:
        return 0
    top = _ranking_carrera(estado, solo_sudamerica, 0 if solo_sudamerica else PR.MEDIA_MIN_BALON)[:3]
    if not top:
        return 0
    m[memoria].append(t)
    lineas = [f"{i + 1}. {_nombre(j)} ({eq.nombre}) · media {j.overall}, {j.goles} goles, {j.asistencias} asistencias, "
              f"nota {j.promedio_nota:.1f}" for i, (_p, eq, j) in enumerate(top)]
    lider = _nombre(top[0][2])
    if solo_sudamerica:
        titular = N.titular(f"Carrera al Sudamericano del Año: {lider} lidera",
                            f"Sudamericano del Año: {lider} lidera la carrera", f"Sudamericano del Año: lidera {lider}")
        intro = "Con la temporada en su tramo final, los candidatos a Jugador Sudamericano del Año son:\n"
    else:
        titular = N.titular(f"Carrera al Balón de Oro: {lider} lidera",
                            f"Balón de Oro: {lider} lidera la carrera", f"Balón de Oro: lidera {lider}")
        intro = "A mitad de temporada los candidatos al Balón de Oro son:\n"
    N.publicar(estado, 'premio', titular, intro + "\n".join(lineas), importancia=4,
               equipos=[x[1] for x in top], jugadores=[x[2] for x in top])
    return 1


def _candidatos_balon(estado: dict, rng) -> int:
    """La carrera al Balón de Oro (a mitad de temporada): hace falta media >= premios.MEDIA_MIN_BALON para ganarlo."""
    return _carrera(estado, 'balon', False, 1, 2)


def _candidatos_sudamericano(estado: dict, rng) -> int:
    """La carrera al Jugador Sudamericano del Año (a tres cuartos de temporada): solo las ligas sudamericanas."""
    return _carrera(estado, 'sudamericano', True, 3, 4)


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


def _importantes_ia(estado: dict):
    """v0.4.26.0: (club, jugador) de los 3 mejores de cada club de la IA (sin cedidos) que valen OVR_IMPORTANTE o más."""
    mi = estado.get('mi_equipo')
    for liga, _tuya in _ligas(estado):
        for eq in liga.equipos:
            if eq is mi or getattr(eq, 'nombre', None) == getattr(mi, 'nombre', None):
                continue
            for j in sorted(getattr(eq, 'jugadores', None) or [], key=lambda x: -x.overall)[:3]:
                if j.overall >= OVR_IMPORTANTE and not getattr(j, 'prestamo', None):
                    yield eq, j


def _transferibles(estado: dict, rng) -> int:
    """v0.4.26.0: "Sorpresa: ponen a X en transferibles". Cuenta lo que ya está marcado en un club de la IA (salida
    forzada tras un descenso) y, de vez en cuando, un club que pone en la lista a una de sus figuras: queda con
    `transferible` unas jornadas (un hecho del estado, no solo un titular). Un jugador no se repite hasta pasadas
    JORNADAS_RECORDAR_TRANSFERIBLE jornadas."""
    m = _memoria(estado)
    ja = _jornada_abs(estado)
    mem = m['transferibles']
    mi = estado.get('mi_equipo')
    soltar = {k for k, v in mem.items() if v[1] and ja - v[0] >= JORNADAS_TRANSFERIBLE}
    if soltar:                                          # vence la marca que puso esta noticia
        for liga, _tuya in _ligas(estado):
            for eq, j in _jugadores(liga):
                if str(getattr(j, 'id', '')) in soltar and eq is not mi:
                    j.transferible = False
        for k in soltar:
            mem[k][1] = 0
    for k in [k for k, v in mem.items() if ja - v[0] >= JORNADAS_RECORDAR_TRANSFERIBLE]:
        del mem[k]
    if ja - m['transferible_ultima'] < JORNADAS_ENTRE_TRANSFERIBLES:
        return 0
    cands = [(eq, j) for eq, j in _importantes_ia(estado) if str(j.id) not in mem]
    marcados = [c for c in cands if getattr(c[1], 'transferible', False) or getattr(c[1], 'salida_forzada', False)]
    if marcados:
        eq, j = max(marcados, key=lambda c: c[1].overall)
        puso = 0
    elif cands and rng.random() < PROB_TRANSFERIBLE:
        eq, j = rng.choice(cands)
        j.transferible = True
        puso = 1
    else:
        return 0
    mem[str(j.id)] = [ja, puso]
    m['transferible_ultima'] = ja
    from alpha_football import correo as C
    nombre = _nombre(j)
    quien = f"{nombre} ({j.posicion}, media {j.overall}, {j.edad} años)"
    cuerpo = (f"Tras el descenso, {eq.nombre} deja en la lista de transferibles a {quien}. El club escuchará ofertas."
              if getattr(j, 'salida_forzada', False) else
              f"{eq.nombre} sorprende al poner en la lista de transferibles a {quien}, uno de sus pilares. "
              "El club está dispuesto a escuchar ofertas.")
    N.publicar(estado, 'otro',
               N.titular(f"Sorpresa: ponen a {nombre} en transferibles", f"Sorpresa: {nombre}, en transferibles",
                         f"{nombre}, en la lista de transferibles"),
               cuerpo, importancia=4 if j.overall >= 85 else 3, categoria='fichaje', equipos=[eq], jugadores=[j],
               accion=C.accion('buscador_screen', "VER BUSCADOR"))
    return 1


def _no_ven(estado: dict, rng) -> int:
    """v0.4.26.0: "No ven a X en el equipo": un jugador bueno y sano de un club de la IA lleva PARTIDOS_SIN_JUGAR
    partidos de su club sin sumar minutos. Se rastrea comparando los PJ del club con los del jugador entre una
    jornada y la siguiente (solo de los buenos); el que se lesiona o es sancionado vuelve a empezar de cero, porque
    entonces no es una decisión del técnico. Un aviso por racha."""
    m = _memoria(estado)
    previo = m['sin_jugar']
    nuevo, elegibles = {}, []
    mi = estado.get('mi_equipo')
    for liga, _tuya in _ligas(estado):
        for eq in liga.equipos:
            if eq is mi or getattr(eq, 'nombre', None) == getattr(mi, 'nombre', None):
                continue
            pj_club = int(getattr(eq, 'pj', 0) or 0)
            for j in getattr(eq, 'jugadores', None) or []:
                if j.overall < OVR_NO_VEN or getattr(j, 'prestamo', None) or not j.disponible:
                    continue
                k = _clave_j(eq, j)
                pj_j = int(getattr(j, 'partidos_jugados', 0) or 0)
                antes = previo.get(k)
                if antes is None or pj_club < antes[0] or pj_j != antes[1]:
                    racha, avisado = 0, 0                    # empieza, jugó (o cambió la temporada): de cero
                else:
                    racha, avisado = int(antes[2]) + (pj_club - int(antes[0])), int(antes[3])
                nuevo[k] = [pj_club, pj_j, racha, avisado]
                if racha >= PARTIDOS_SIN_JUGAR and not avisado:
                    elegibles.append((racha, j.overall, k, eq, j))
    previo.clear()
    previo.update(nuevo)
    elegibles.sort(key=lambda x: (x[0], x[1]), reverse=True)
    n = 0
    for racha, _ovr, k, eq, j in elegibles[:MAX_NO_VEN_POR_JORNADA]:
        previo[k][3] = 1
        nombre = _nombre(j)
        N.publicar(estado, 'vestuario',
                   N.titular(f"No ven a {nombre} en el equipo de {eq.nombre}", f"No ven a {nombre} en {eq.nombre}",
                             f"No ven a {nombre} en el equipo"),
                   f"{nombre} ({j.posicion}, media {j.overall}) lleva {racha} partidos sin sumar minutos con "
                   f"{eq.nombre} pese a estar sano. En su entorno ya se pregunta si el técnico cuenta con él.",
                   importancia=4 if j.overall >= 85 else 3, equipos=[eq], jugadores=[j])
        n += 1
    return n


def _logros(estado: dict, rng) -> int:
    """Logros que salen de mirar el estado (título de liga, final continental, fichaje de lujo); cada uno publica
    su propia noticia, así que aquí solo se cuenta."""
    from alpha_football import logros as _lg
    return len(_lg.revisar(estado))


# --- títulos: en cuanto un equipo gana o asegura uno ----------------------------------------------------------

MAX_TITULOS_RECORDADOS = 200
COPAS_CONTINENTE = {'champions': 'europa', 'libertadores': 'sudamerica'}


def _anunciado(estado: dict, clave: str) -> bool:
    return clave in _memoria(estado)['titulos']


def _anotar(estado: dict, clave: str) -> None:
    vistos = _memoria(estado)['titulos']
    if clave not in vistos:
        vistos.append(clave)
        del vistos[:-MAX_TITULOS_RECORDADOS]


def _continente_de(liga) -> str:
    from alpha_football.paises import es_sudamerica
    return 'sudamerica' if es_sudamerica(getattr(liga, 'tipo', '') or '') else 'europa'


def _anio_continente(estado: dict, cont: str) -> int:
    """El año en que empezó la temporada en curso de ese continente, leído sin crear nada (ni el reloj ni el
    calendario): el que guarda el mundo desfasado o, si no hay desfase, el de tu temporada de carrera."""
    try:
        guardado = (((estado.get('datos_carrera') or {}).get('mundo') or {}).get('anio') or {}).get(cont)
        if guardado:
            return int(guardado)
    except (TypeError, ValueError):
        pass
    from alpha_football import calendario as CAL
    return CAL.ANIO_BASE[cont] + int(estado.get('temporada', 1) or 1) - 1


def _clave_liga(estado: dict, liga, tuya: bool, temporada=None) -> str:
    """Identidad de un título de liga: tu liga cuenta por tu temporada de carrera; las demás, por el año de su
    continente (la temporada de Sudamérica no coincide con la tuya)."""
    division = getattr(liga, 'division', 1)
    if tuya:
        t = temporada if temporada is not None else int(estado.get('temporada', 1) or 1)
        return f"camp:{t}:{getattr(liga, 'tipo', '?')}:{division}"
    return f"camp:a{_anio_continente(estado, _continente_de(liga))}:{getattr(liga, 'tipo', '?')}:{division}"


def _pendientes_por_equipo(liga) -> dict:
    """Partidos que le faltan por jugar a cada club de la liga (por id)."""
    faltan = {e.id: 0 for e in liga.equipos}
    for p in getattr(liga, 'calendario', None) or []:
        if getattr(p, 'jugado', False):
            continue
        for eid in (p.local_id, p.visitante_id):
            if eid in faltan:
                faltan[eid] += 1
    return faltan


def estado_del_titulo(liga) -> Optional[dict]:
    """El título de liga mirado con la tabla de hoy: None si todavía se puede perder, o
    {'lider', 'puntos', 'segundo', 'techo', 'faltan', 'terminado'} si el líder ya no puede ser alcanzado
    (`techo` = los puntos máximos del segundo; `faltan` = lo que le queda por jugar al líder; `terminado` = la
    liga acabó)."""
    equipos = list(getattr(liga, 'equipos', None) or [])
    if len(equipos) < 2 or not any(getattr(p, 'jugado', False) for p in getattr(liga, 'calendario', None) or []):
        return None
    faltan = _pendientes_por_equipo(liga)
    orden = sorted(equipos, key=lambda e: (e.puntos, e.gf - e.gc, e.gf), reverse=True)
    lider = orden[0]
    techos = [(e.puntos + 3 * faltan.get(e.id, 0), e) for e in orden[1:]]
    techo, segundo = max(techos, key=lambda x: x[0])
    terminado = all(v == 0 for v in faltan.values())
    if not terminado and lider.puntos <= techo:
        return None
    return {'lider': lider, 'puntos': int(lider.puntos), 'segundo': segundo, 'techo': int(techo),
            'faltan': int(faltan.get(lider.id, 0)), 'terminado': terminado}


def _titulo_liga(estado: dict, liga, tuya: bool) -> int:
    est = estado_del_titulo(liga)
    if est is None:
        return 0
    base = _clave_liga(estado, liga, tuya)
    ganado = base + ":final"
    if _anunciado(estado, ganado) or (not est['terminado'] and _anunciado(estado, base + ":asegurado")):
        return 0
    lider = est['lider']
    pais = PAIS_POR_LIGA.get(getattr(liga, 'tipo', ''), getattr(liga, 'tipo', ''))
    if tuya:
        nombre_t = N.nombre_temporada(estado, estado.get('temporada', 1))
    else:
        cont = _continente_de(liga)
        nombre_t = N.nombre_anio(cont, _anio_continente(estado, cont))
    if est['terminado']:
        titular = N.titular(f"{lider.nombre} se proclama campeón de {liga.nombre}",
                            f"{lider.nombre}, campeón de {liga.nombre}", f"{lider.nombre} es campeón")
        cuerpo = (f"{lider.nombre} termina primero en {liga.nombre} ({pais}) con {est['puntos']} puntos y se lleva el "
                  f"título de la temporada {nombre_t}.")
        clave = ganado
    else:
        titular = N.titular(f"{lider.nombre} asegura el título de {liga.nombre}", f"{lider.nombre} asegura el título",
                            f"{lider.nombre}, campeón matemático")
        falta = est['faltan']
        cuerpo = (f"Con {est['puntos']} puntos y {falta} partido{'s' if falta != 1 else ''} por jugar, {lider.nombre} ya no "
                  f"puede ser alcanzado en {liga.nombre} ({pais}): {est['segundo'].nombre} solo llegaría a {est['techo']} "
                  f"puntos.")
        clave = base + ":asegurado"
    N.publicar(estado, 'campeon', titular, cuerpo, importancia=5 if tuya else 4, equipos=[lider], clave=clave)
    _anotar(estado, clave)
    return 1


def anunciar_copa(estado: dict, c: Optional[dict]) -> int:
    """La noticia del campeón de una copa en cuanto se juega su final (no al cerrar la temporada). Una sola vez por
    copa y año. `c` es el dict de competiciones.copa; sin campeón no hace nada."""
    if not isinstance(c, dict) or not c.get('campeon'):
        return 0
    tipo = c.get('tipo')
    from alpha_football import competiciones as CP
    cont = COPAS_CONTINENTE.get(tipo, 'europa')
    anio = c.get('anio')
    clave = f"copa:{anio if anio is not None else c.get('temporada', '?')}:{tipo}"
    if _anunciado(estado, clave):
        return 0
    _anotar(estado, clave)
    copa = CP.NOMBRE_COPA.get(tipo, tipo)
    nombre_t = N.nombre_anio(cont, anio) if anio is not None else N.nombre_temporada(estado, c.get('temporada', 1), cont)
    campeon = c['campeon']
    N.publicar(estado, 'campeon',
               N.titular(f"{campeon} es el campeón de la {copa}", f"{campeon} gana la {copa}", f"La {copa} ya tiene campeón"),
               f"{campeon} conquista la {copa} de la temporada {nombre_t}.", importancia=5, clave=clave)
    return 1


def _titulos(estado: dict, rng) -> int:
    """Títulos de liga ganados o asegurados en cualquier liga de primera (y la tuya, sea cual sea) y copas con
    campeón: se anuncian en esta jornada, no al cerrar la temporada."""
    from alpha_football import competiciones as CP
    n = 0
    for liga, tuya in _ligas(estado):
        if not tuya and int(getattr(liga, 'division', 1) or 1) != 1:
            continue
        try:
            n += _titulo_liga(estado, liga, tuya)
        except Exception as e:
            logger.error(f"noticias_gen._titulos: {getattr(liga, 'nombre', '?')}: {e}", exc_info=True)
    for tipo in COPAS_CONTINENTE:
        try:
            n += anunciar_copa(estado, CP.copa(estado, tipo))
        except Exception as e:
            logger.error(f"noticias_gen._titulos: copa {tipo}: {e}", exc_info=True)
    return n


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
    for generador in (_titulos, _resultados, _lesiones, _promesas, _candidatos_balon, _candidatos_sudamericano,
                      _records, _polemico, _transferibles, _no_ven, _logros):
        try:
            total += int(generador(estado, rng) or 0)
        except Exception as e:
            logger.error(f"noticias_gen.{getattr(generador, '__name__', generador)}: {e}", exc_info=True)
    return total


# --- cierre de la temporada del user ------------------------------------------------------------------------------

def _cierre_campeones(estado: dict, liga, campeon_liga, campeones_copas, kw: dict) -> int:
    """Campeones de tu temporada. Lo que ya se anunció en su momento (título asegurado, final de copa) no se repite."""
    from alpha_football import competiciones as CP
    n = 0
    nombre_t = N.nombre_temporada(estado, kw['temporada'])
    if campeon_liga:
        nombre = getattr(campeon_liga, 'nombre', campeon_liga)
        ganado = _clave_liga(estado, liga, True, kw['temporada']) + ":final"
        if not _anunciado(estado, ganado):
            N.publicar(estado, 'campeon', f"{nombre} es campeón de {liga.nombre}",
                       f"{nombre} gana {liga.nombre} y se lleva el título de la temporada {nombre_t}.",
                       importancia=5, clave=f"camp:{kw['temporada']}:liga", **kw)
            _anotar(estado, ganado)
            n += 1
    for tipo, club in (campeones_copas or {}).items():
        if not club:
            continue
        nombre = getattr(club, 'nombre', club)
        copa = CP.NOMBRE_COPA.get(tipo, tipo)
        c = CP.copa(estado, tipo) or {}
        anio = c.get('anio')
        ya = f"copa:{anio if anio is not None else c.get('temporada', '?')}:{tipo}"
        if _anunciado(estado, ya):
            continue                               # se anunció en cuanto se jugó la final
        _anotar(estado, ya)
        N.publicar(estado, 'campeon', f"{nombre} gana la {copa}",
                   f"{nombre} conquista la {copa} de la temporada {nombre_t}.",
                   importancia=5, clave=f"camp:{kw['temporada']}:{tipo}", **kw)
        n += 1
    return n


MAX_DESCENSOS_DESTACADOS = 4


def _clubes_por_nombre(estado: dict) -> dict:
    from alpha_football.mercado_ia import ligas_de_la_partida
    return {eq.nombre: eq for liga, _t, _d in ligas_de_la_partida(estado) for eq in liga.equipos}


def descensos_destacados(estado: dict, movimientos, excluir_tipo: Optional[str] = None) -> list:
    """[(club, país)] de los clubes que pierden la categoría (ligas distintas de `excluir_tipo`), los de más peso
    primero: estrellas del club y, a igualdad, su nivel. Solo los MAX_DESCENSOS_DESTACADOS mejores."""
    clubes = _clubes_por_nombre(estado)
    candidatos = []
    for mov in movimientos or []:
        tipo = mov.get('tipo')
        if tipo == excluir_tipo:
            continue
        for nombre in mov.get('descendidos') or []:
            eq = clubes.get(nombre)
            try:
                nivel = int(_nivel(eq)) if eq is not None else 0
            except Exception as e:
                logger.debug(f"noticias_gen: sin nivel para {nombre}: {e}")
                nivel = 0
            estrellas = float(getattr(eq, 'estrellas', 0) or 0)
            candidatos.append((estrellas, nivel, str(nombre), PAIS_POR_LIGA.get(tipo, tipo)))
    candidatos.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [(nombre, pais) for _e, _n, nombre, pais in candidatos[:MAX_DESCENSOS_DESTACADOS]]


def publicar_descensos_destacados(estado: dict, movimientos, excluir_tipo: Optional[str] = None,
                                  ambito: str = "las otras ligas", **kw) -> int:
    """Una noticia con los mejores clubes que descienden en `ambito` (sin la lista completa de ascensos y descensos)."""
    top = descensos_destacados(estado, movimientos, excluir_tipo)
    if not top:
        return 0
    nombres = [nombre for nombre, _p in top]
    uno = len(nombres) == 1
    cabeza = N.titular(f"Descienden {', '.join(nombres[:-1])} y {nombres[-1]}" if not uno else f"Desciende {nombres[0]}",
                       f"Descienden {nombres[0]} y {nombres[1]}" if not uno else f"Desciende {nombres[0]}",
                       f"Descenso de {nombres[0]}")
    lineas = "\n".join(f"{nombre} ({pais})" for nombre, pais in top)
    N.publicar(estado, 'descenso', cabeza,
               f"Entre los clubes que pierden la categoría en {ambito}, los de más peso:\n\n" + lineas,
               importancia=4, categoria='descenso', **kw)
    return 1


def _cierre_movimientos(estado: dict, liga, movimientos, kw: dict) -> int:
    n = 0
    for mov in movimientos or []:
        asc, des = list(mov.get('ascendidos') or []), list(mov.get('descendidos') or [])
        if mov.get('tipo') != liga.tipo:
            continue
        pais = PAIS_POR_LIGA.get(liga.tipo, liga.tipo)
        if asc:
            N.publicar(estado, 'descenso', f"Ascienden a Primera: {', '.join(asc)}",
                       f"{', '.join(asc)} suben de categoría en {pais}.",
                       importancia=5, categoria='ascenso', **kw)
            n += 1
        if des:
            N.publicar(estado, 'descenso', f"Descienden a Segunda: {', '.join(des)}",
                       f"{', '.join(des)} pierden la categoría en {pais}.",
                       importancia=5, categoria='descenso', **kw)
            n += 1
    # v0.4.25.0: de las otras ligas, solo los mejores clubes que bajan (antes, la lista de todos los ascensos y descensos)
    n += publicar_descensos_destacados(estado, movimientos, excluir_tipo=liga.tipo, ambito="las otras ligas", **kw)
    return n


SECCIONES_ONCE = (('POR', 1, "PORTERO"), ('DEF', 4, "DEFENSAS"), ('MED', 3, "MEDIOS"), ('DEL', 3, "ATACANTES"))


def _cierre_equipo_del_anio(estado: dict, liga, kw: dict) -> int:
    """El once ideal: un portero, cuatro defensas, tres medios y tres atacantes por nota media. El cuerpo va en
    bloques por línea (cada jugador en su renglón, con su club y su nota) para que se lea de un vistazo."""
    min_pj = max(3, int(liga.num_jornadas) // 2)
    por_pos = {pos: [] for pos, _n, _t in SECCIONES_ONCE}
    for eq, j in _jugadores(liga):
        if int(getattr(j, 'partidos_jugados', 0) or 0) >= min_pj and getattr(j, 'posicion', '') in por_pos:
            por_pos[j.posicion].append((float(getattr(j, 'promedio_nota', 0) or 0), int(getattr(j, 'goles', 0) or 0), eq, j))
    if any(len(por_pos[pos]) < n for pos, n, _t in SECCIONES_ONCE):
        return 0
    once, bloques = [], []
    for pos, n, titulo in SECCIONES_ONCE:
        elegidos = sorted(por_pos[pos], key=lambda x: (x[0], x[1]), reverse=True)[:n]
        once += elegidos
        renglones = [f"{_nombre(x[3])} · {x[2].nombre} · {x[0]:.1f}" for x in elegidos]
        bloques.append(titulo + "\n" + "\n".join(renglones))
    nombre_t = N.nombre_temporada(estado, kw['temporada'])
    titular = N.titular(f"Equipo del año {nombre_t} de {liga.nombre}", f"Equipo del año de {liga.nombre}")
    N.publicar(estado, 'premio', titular, "\n\n".join(bloques), importancia=4,
               equipos=[x[2] for x in once], jugadores=[x[3] for x in once], **kw)
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
