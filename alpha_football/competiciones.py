# -*- coding: utf-8 -*-
"""
v3.8.0: motor de competiciones internacionales (sub-proyecto 6).

- Champions: fase de liga suiza de 36 (4 bombos de 9, 8 partidos por club), playoff 9º-24º,
  octavos/cuartos/semis a ida y vuelta y final única. 17 fechas.
- Libertadores: 8 grupos de 4 (ida y vuelta, 6 fechas), octavos 1º vs 2º de otro grupo,
  cuartos/semis a ida y vuelta y final única. 13 fechas.

Lógica pura y serializable: el estado de cada copa vive en `datos_carrera['copas'][tipo]`
(solo dicts/listas/str/int, va al JSON del save). Los objetos `Equipo` se resuelven por nombre
(ligas vivas de la partida o pool internacional) y se cachean fuera del save.
"""
from __future__ import annotations

import logging
import math
import random
from typing import Any, Optional

logger = logging.getLogger(__name__)

# v3.8.0: fases (etiquetas de "mejor fase alcanzada") y cantidad de fechas por copa.
FASES = {'champions': ['Fase de liga', 'Playoff', 'Octavos', 'Cuartos', 'Semifinal', 'Finalista', 'Campeón'],
         'libertadores': ['Fase de grupos', 'Octavos', 'Cuartos', 'Semifinal', 'Finalista', 'Campeón']}
N_FECHAS = {'champions': 17, 'libertadores': 13}
NOMBRE_COPA = {'champions': 'Champions', 'libertadores': 'Libertadores'}

# v3.8.0: calendario de etapas: (etiqueta del partido, fechas que ocupa). La fase de liga/grupos
# se sortea al iniciar la temporada; las llaves se arman cuando termina la etapa anterior.
ETAPAS = {
    'champions': [('Fase de liga', list(range(8))), ('Playoff', [8, 9]), ('Octavos', [10, 11]),
                  ('Cuartos', [12, 13]), ('Semifinal', [14, 15]), ('Final', [16])],
    'libertadores': [('Fase de grupos', list(range(6))), ('Octavos', [6, 7]), ('Cuartos', [8, 9]),
                     ('Semifinal', [10, 11]), ('Final', [12])],
}

# v3.8.0: cuadro fijo tras octavos (índices de la ronda anterior que se cruzan).
# Champions: 1º-8º sembrados de modo que 1º y 2º solo se crucen en la final.
# Libertadores: los dos de un mismo grupo recién pueden reencontrarse en la final.
CUADRO = {
    'champions': {'Cuartos': [(0, 7), (3, 4), (1, 6), (2, 5)], 'Semifinal': [(0, 1), (2, 3)], 'Final': [(0, 1)]},
    'libertadores': {'Cuartos': [(0, 2), (1, 3), (4, 6), (5, 7)], 'Semifinal': [(0, 2), (1, 3)],
                     'Final': [(0, 1)]},
}


# ════════════════════════════════════════════════════════════════════════════
# Fechas en el calendario de liga
# ════════════════════════════════════════════════════════════════════════════

def jornada_de_fecha(i: int, n_fechas: int, num_jornadas: int) -> int:
    """v3.8.0: la fecha i (0-based) se juega tras la jornada ceil((i+1)(J-1)/N); la final tras la J-1."""
    try:
        return max(1, math.ceil((int(i) + 1) * (int(num_jornadas) - 1) / max(1, int(n_fechas))))
    except Exception:
        return 1


# ════════════════════════════════════════════════════════════════════════════
# Sorteo de la fase de liga (Champions)
# ════════════════════════════════════════════════════════════════════════════

def _bombos(clubes: list, n_bombos: int) -> list:
    """Bombos por media (orden estable): el 1º con los n/k mejores, etc."""
    orden = sorted(clubes, key=lambda c: -float(c.get('ovr', 0) or 0))
    t = len(orden) // n_bombos
    return [orden[k * t:(k + 1) * t] for k in range(n_bombos)]


def _mismo_pais(a: dict, b: dict) -> bool:
    pa, pb = a.get('pais'), b.get('pais')
    return bool(pa) and pa == pb


def _matching_bipartito(izq: list, der: list, permitido, rng, limite: int = 5000) -> Optional[list]:
    """Emparejamiento perfecto izq→der (backtracking con MRV). Devuelve [(i, d)] o None."""
    n = len(izq)
    opciones = {i: [d for d in range(n) if permitido(i, d)] for i in range(n)}
    for i in opciones:
        rng.shuffle(opciones[i])
    usados_d: set = set()
    asignado: dict = {}
    pasos = [0]

    def bt() -> bool:
        pasos[0] += 1
        if pasos[0] > limite:
            return False
        libres = [i for i in range(n) if i not in asignado]
        if not libres:
            return True
        i = min(libres, key=lambda x: sum(1 for d in opciones[x] if d not in usados_d))
        for d in opciones[i]:
            if d in usados_d:
                continue
            asignado[i] = d; usados_d.add(d)
            if bt():
                return True
            del asignado[i]; usados_d.discard(d)
        return False

    return [(i, asignado[i]) for i in range(n)] if bt() else None


def _cruces_entre_bombos(bi: list, bj: list, rng, estricto: bool) -> Optional[list]:
    """
    v3.8.0: dos emparejamientos perfectos disjuntos entre el bombo i y el j: con el primero
    local el de i, con el segundo local el de j. Así cada club juega 1 de local y 1 de visitante
    contra cada otro bombo.
    """
    for _ in range(60):
        m1 = _matching_bipartito(bi, bj, lambda a, b: not (estricto and _mismo_pais(bi[a], bj[b])), rng)
        if m1 is None:
            return None                                # sin la regla de país no hay forma
        usados = set(m1)
        m2 = _matching_bipartito(bi, bj, lambda a, b: (a, b) not in usados
                                 and not (estricto and _mismo_pais(bi[a], bj[b])), rng)
        if m2 is not None:
            return ([(bi[a]['nombre'], bj[b]['nombre']) for a, b in m1]
                    + [(bj[b]['nombre'], bi[a]['nombre']) for a, b in m2])
    return None


def _cruces_dentro_bombo(b: list, rng, estricto: bool) -> Optional[list]:
    """
    v3.8.0: permutación sin puntos fijos ni 2-ciclos: cada club recibe a uno de su bombo y
    visita a otro distinto (1 L + 1 V dentro del bombo).
    """
    n = len(b)
    for _ in range(60):
        destino: dict = {}
        origen: dict = {}
        orden = list(range(n)); rng.shuffle(orden)
        pasos = [0]

        def bt(k: int) -> bool:
            pasos[0] += 1
            if pasos[0] > 3000:
                return False
            if k == n:
                return True
            a = orden[k]
            cands = [d for d in range(n) if d != a and d not in origen
                     and destino.get(d) != a and not (estricto and _mismo_pais(b[a], b[d]))]
            rng.shuffle(cands)
            for d in cands:
                destino[a] = d; origen[d] = a
                if bt(k + 1):
                    return True
                del destino[a]; del origen[d]
            return False

        if bt(0):
            return [(b[a]['nombre'], b[d]['nombre']) for a, d in destino.items()]
    return None


def _colorear_fechas(aristas: list, n_fechas: int, rng, max_pasos: int = 400) -> Optional[list]:
    """
    v3.8.0: reparte los partidos en `n_fechas` fechas con cada club una sola vez por fecha
    (coloreo de aristas con Δ colores). Greedy + cadenas de Kempe; si una arista se traba, se
    libera una vecina al azar y se sigue (búsqueda local). Devuelve la fecha de cada arista o None.
    """
    color: list = [None] * len(aristas)
    en: dict = {}                                   # club -> {fecha: índice de arista}
    for l, v in aristas:
        en.setdefault(l, {}); en.setdefault(v, {})
    pendientes = list(range(len(aristas)))
    rng.shuffle(pendientes)
    colores = list(range(n_fechas))

    def poner(e: int, c: int) -> None:
        color[e] = c
        a, b = aristas[e]
        en[a][c] = e; en[b][c] = e

    def quitar(e: int) -> None:
        c = color[e]
        a, b = aristas[e]
        if en[a].get(c) == e:
            del en[a][c]
        if en[b].get(c) == e:
            del en[b][c]
        color[e] = None

    def otro(e: int, x: str) -> str:
        a, b = aristas[e]
        return b if a == x else a

    def kempe(inicio: str, c1: str, c2: str) -> list:
        """Aristas de la cadena alternante c1/c2 que parte de `inicio` por su arista c1."""
        cadena, x, c = [], inicio, c1
        vistos = set()
        while c in en[x] and en[x][c] not in vistos:
            e = en[x][c]
            vistos.add(e); cadena.append(e)
            x = otro(e, x)
            c = c2 if c == c1 else c1
        return cadena

    pasos = 0
    while pendientes:
        pasos += 1
        if pasos > max_pasos:
            return None
        e = pendientes.pop()
        u, v = aristas[e]
        libres_u = [c for c in colores if c not in en[u]]
        libres_v = [c for c in colores if c not in en[v]]
        comunes = [c for c in libres_u if c in libres_v]
        if comunes:
            poner(e, rng.choice(comunes))
            continue
        hecho = False
        pares = [(a, b) for a in libres_u for b in libres_v]
        rng.shuffle(pares)
        for a, b in pares:
            # a libre en u y usado en v; b libre en v y usado en u. Cadena a/b desde v.
            cadena = kempe(v, a, b)
            if cadena and u in {x for ed in cadena for x in aristas[ed]}:
                continue                              # la cadena llega a u: el intercambio no sirve
            previos = [color[ed] for ed in cadena]         # intercambio a↔b en toda la cadena
            for ed in cadena:
                quitar(ed)
            for ed, c_prev in zip(cadena, previos):
                poner(ed, b if c_prev == a else a)
            if a not in en[v] and a not in en[u]:
                poner(e, a); hecho = True
                break
        if not hecho:
            # búsqueda local: se libera una arista de u al azar y se coloca esta en su lugar
            c = rng.choice(libres_v) if libres_v else rng.choice(colores)
            if c in en[u]:
                vieja = en[u][c]
                quitar(vieja); pendientes.insert(0, vieja)
            if c in en[v]:
                vieja = en[v][c]
                quitar(vieja); pendientes.insert(0, vieja)
            poner(e, c)
    return color


def sorteo_fase_liga(clubes: list, rng=None) -> list:
    """
    v3.8.0: sorteo de la fase de liga de 36: cada club juega 8 partidos (2 rivales de cada bombo,
    uno de local y otro de visitante), nunca contra uno de su país (si en un cruce de bombos no se
    puede, se relaja solo ahí) y uno por fecha (8 fechas).
    Devuelve [{'fecha', 'local', 'visitante'}] (144 partidos).
    """
    rng = rng or random.Random()
    bombos = _bombos(clubes, 4)
    for _intento in range(200):              # cada intento: cruces nuevos + coloreo corto
        aristas: list = []
        for i in range(4):
            for j in range(i, 4):
                cr = None
                for estricto in (True, False):
                    cr = (_cruces_dentro_bombo(bombos[i], rng, estricto) if i == j
                          else _cruces_entre_bombos(bombos[i], bombos[j], rng, estricto))
                    if cr is not None:
                        break
                if cr is None:
                    logger.error(f"sorteo_fase_liga: sin cruces posibles entre bombos {i}-{j}")
                    return []
                aristas.extend(cr)
        fechas = _colorear_fechas(aristas, 8, rng)
        if fechas is not None:
            return [{'fecha': f, 'local': l, 'visitante': v} for (l, v), f in zip(aristas, fechas)]
    logger.error("sorteo_fase_liga: no se pudieron repartir las fechas")
    return []


# ════════════════════════════════════════════════════════════════════════════
# Sorteo de grupos (Libertadores)
# ════════════════════════════════════════════════════════════════════════════

def sorteo_grupos(clubes: list, rng=None, n_grupos: int = 8) -> list:
    """
    v3.8.0: 8 grupos de 4 con bombos por media (uno de cada bombo por grupo), sin dos clubes del
    mismo país en un grupo cuando se pueda (500 intentos; si no, se relaja la regla).
    Devuelve [[nombres]] (el 1º de cada grupo es el cabeza de serie).
    """
    rng = rng or random.Random()
    n_bombos = max(1, len(clubes) // max(1, n_grupos))
    bombos = _bombos(clubes, n_bombos)
    for estricto in (True, False):
        for _ in range(500):
            grupos: list = [[] for _ in range(n_grupos)]
            ok = True
            for bombo in bombos:
                # emparejamiento bombo → grupos (cada grupo recibe exactamente uno)
                m = _matching_bipartito(
                    bombo, grupos,
                    lambda a, g: not (estricto and any(_mismo_pais(bombo[a], x) for x in grupos[g])),
                    rng, limite=2000)
                if m is None:
                    ok = False
                    break
                for a, g in m:
                    grupos[g].append(bombo[a])
            if ok:
                return [[c['nombre'] for c in g] for g in grupos]
    # último recurso (no debería pasar): reparto directo por bombos
    return [[b[g]['nombre'] for b in bombos if g < len(b)] for g in range(n_grupos)]


def _round_robin(nombres: list) -> list:
    """Fixture ida y vuelta (reutiliza el de la liga; si no está disponible, uno propio)."""
    try:
        from alpha_football.ui.league_screen import generar_fixture
        fx = generar_fixture(list(nombres))
        if fx:
            return fx
    except Exception as e_fx:
        logger.debug(f"generar_fixture no disponible: {e_fx}")
    lista, n, jornadas = list(nombres), len(nombres), []
    for r in range(n - 1):
        jornadas.append([(lista[i], lista[n - 1 - i]) if r % 2 == 0 else (lista[n - 1 - i], lista[i])
                         for i in range(n // 2)])
        lista = [lista[0]] + [lista[-1]] + lista[1:-1]
    return jornadas + [[(v, l) for l, v in j] for j in jornadas]


def partidos_grupos(grupos: list) -> list:
    """v3.8.0: todos contra todos ida y vuelta en cada grupo: 6 fechas × 2 partidos × 8 grupos = 96."""
    partidos = []
    for g, nombres in enumerate(grupos):
        for f, jornada in enumerate(_round_robin(nombres)):
            for l, v in jornada:
                partidos.append({'fecha': f, 'local': l, 'visitante': v, 'grupo': g})
    return partidos


# ════════════════════════════════════════════════════════════════════════════
# Tablas, penales y llaves
# ════════════════════════════════════════════════════════════════════════════

def tabla(nombres: list, partidos: list) -> list:
    """v3.8.0: tabla 3/1/0 ordenada por puntos, diferencia, goles a favor y nombre."""
    filas = {n: {'nombre': n, 'pj': 0, 'g': 0, 'e': 0, 'p': 0, 'gf': 0, 'gc': 0, 'dif': 0, 'pts': 0}
             for n in nombres}
    for p in partidos or []:
        try:
            if not p.get('jugado'):
                continue
            l, v = filas.get(p.get('local')), filas.get(p.get('visitante'))
            gl, gv = int(p.get('gl', 0) or 0), int(p.get('gv', 0) or 0)
            for fila, gf, gc in ((l, gl, gv), (v, gv, gl)):
                if fila is None:
                    continue
                fila['pj'] += 1; fila['gf'] += gf; fila['gc'] += gc
                if gf > gc:
                    fila['g'] += 1; fila['pts'] += 3
                elif gf == gc:
                    fila['e'] += 1; fila['pts'] += 1
                else:
                    fila['p'] += 1
        except Exception as e_p:
            logger.debug(f"tabla: partido inválido {p}: {e_p}")
    for f in filas.values():
        f['dif'] = f['gf'] - f['gc']
    return sorted(filas.values(), key=lambda f: (-f['pts'], -f['dif'], -f['gf'], f['nombre']))


def penales(fuerza_a: float, fuerza_b: float, rng=None) -> tuple:
    """v3.8.0: tanda de 5 + muerte súbita; prob. de gol 0.75 ± (fuerza − 75)/200. Devuelve (a, b)."""
    rng = rng or random.Random()

    def prob(f):
        try:
            return min(0.95, max(0.5, 0.75 + (float(f) - 75.0) / 200.0))
        except Exception:
            return 0.75

    pa, pb = prob(fuerza_a), prob(fuerza_b)
    a = b = 0
    for tiro in range(5):
        a += rng.random() < pa
        if a > b + (5 - tiro) or b > a + (4 - tiro):     # ya no se alcanza
            return a, b
        b += rng.random() < pb
        if a > b + (4 - tiro) or b > a + (4 - tiro):
            return a, b
    for _ in range(100):                                 # muerte súbita
        ga, gb = rng.random() < pa, rng.random() < pb
        a += ga; b += gb
        if ga != gb:
            return a, b
    return a + 1, b


def _penales_de(partido: dict) -> Optional[tuple]:
    """Penales guardados en un partido como {'a': local, 'b': visitante} (acepta lista/tupla)."""
    pen = partido.get('penales') if isinstance(partido, dict) else None
    try:
        if isinstance(pen, dict):
            return int(pen.get('a', 0)), int(pen.get('b', 0))
        if isinstance(pen, (list, tuple)) and len(pen) == 2:
            return int(pen[0]), int(pen[1])
    except Exception:
        pass
    return None


def resolver_llave(ida: dict, vuelta: Optional[dict], rng=None, fuerza: Optional[dict] = None) -> str:
    """
    v3.8.0: ganador de una llave. A = local de la ida. Ida y vuelta: gana el global (sin gol de
    visitante); final única: el marcador. Si empata, penales en el partido decisivo (la vuelta o la
    final), guardados como {'a': goles del LOCAL de ese partido, 'b': del visitante}. Si el partido
    ya trae penales (jugado en vivo por el user) se respetan.
    """
    rng = rng or random.Random()
    fuerza = fuerza or {}
    a, b = ida.get('local'), ida.get('visitante')
    goles_a = int(ida.get('gl', 0) or 0)
    goles_b = int(ida.get('gv', 0) or 0)
    decisivo = ida
    if vuelta:
        decisivo = vuelta
        if vuelta.get('local') == a:
            goles_a += int(vuelta.get('gl', 0) or 0); goles_b += int(vuelta.get('gv', 0) or 0)
        else:
            goles_a += int(vuelta.get('gv', 0) or 0); goles_b += int(vuelta.get('gl', 0) or 0)
    if goles_a != goles_b:
        return a if goles_a > goles_b else b
    loc, vis = decisivo.get('local'), decisivo.get('visitante')
    pen = _penales_de(decisivo)
    if pen is None or pen[0] == pen[1]:
        pen = penales(fuerza.get(loc, 75), fuerza.get(vis, 75), rng)
        decisivo['penales'] = {'a': pen[0], 'b': pen[1]}
    return loc if pen[0] > pen[1] else vis


def cruces_playoff(tabla36: list) -> list:
    """v3.8.0: playoff 9º v 24º, 10º v 23º, …, 16º v 17º como (mejor, peor)."""
    nombres = [f['nombre'] for f in tabla36]
    return [(nombres[8 + k], nombres[23 - k]) for k in range(8)]


def cruces_octavos_champions(tabla36: list, ganadores_playoff: dict) -> list:
    """
    v3.8.0: 1º vs ganador de 16-17, 2º vs ganador de 15-18, …, 8º vs ganador de 9-24.
    `ganadores_playoff`: {(mejor, peor): ganador}; sin dato pasa el mejor clasificado.
    """
    nombres = [f['nombre'] for f in tabla36]
    playoff = cruces_playoff(tabla36)
    return [(nombres[i], ganadores_playoff.get(playoff[7 - i], playoff[7 - i][0])) for i in range(8)]


def cruces_octavos_libertadores(grupos_tablas: list) -> list:
    """v3.8.0: A1-B2, B1-A2, C1-D2, D1-C2, … (el 1º cierra de local). grupos_tablas: tablas ordenadas."""
    cruces = []
    for g in range(0, len(grupos_tablas) - 1, 2):
        t1, t2 = grupos_tablas[g], grupos_tablas[g + 1]
        cruces.append((t1[0]['nombre'], t2[1]['nombre']))
        cruces.append((t2[0]['nombre'], t1[1]['nombre']))
    return cruces


# ════════════════════════════════════════════════════════════════════════════
# Clasificados y equipos (ligas vivas + pool internacional)
# ════════════════════════════════════════════════════════════════════════════

# v3.8.0: cupos por liga de 1ª (1 más que en v3.7) y tamaño de cada copa.
CUPOS = {'champions': {'premier': 5, 'laliga': 5, 'seriea': 5},
         'libertadores': {'brasil': 7, 'argentina': 6, 'betplay': 5, 'uruguay': 5, 'ecuador': 5}}
N_CLUBES = {'champions': 36, 'libertadores': 32}


def _ovr(eq) -> float:
    try:
        return float(getattr(eq, 'ovr_promedio', 0) or 0)
    except Exception:
        return 0.0


def _ligas_vivas(estado: dict) -> list:
    """Todas las ligas de la partida (la del user primero, luego 1ª y 2ª de cada país)."""
    ligas, vistas = [], set()
    candidatas = [estado.get('liga')]
    for div in ('primera_division', 'segunda_division'):
        candidatas += list((estado.get(div) or {}).values())
    for lg in candidatas:
        if lg is not None and id(lg) not in vistas:
            vistas.add(id(lg)); ligas.append(lg)
    return ligas


def _equipos_1a(estado: dict, liga_id: str) -> list:
    """Clubes de la 1ª división `liga_id`: la liga viva; si no está, los datos (cacheados)."""
    viva = (estado.get('primera_division') or {}).get(liga_id)
    if viva is not None and getattr(viva, 'equipos', None):
        return list(viva.equipos)
    liga_user = estado.get('liga')
    if liga_user is not None and getattr(liga_user, 'tipo', None) == liga_id \
            and int(getattr(liga_user, 'division', 1) or 1) == 1:
        return list(liga_user.equipos)
    cache = estado.setdefault('_copas_ligas_cache', {})
    if liga_id not in cache:
        try:
            from alpha_football.paises import cargar_datos_liga
            lg = cargar_datos_liga(liga_id, 1)
            cache[liga_id] = list(getattr(lg, 'equipos', None) or [])
        except Exception as e_lg:
            logger.error(f"competiciones: no se pudo cargar la liga {liga_id}: {e_lg}")
            cache[liga_id] = []
    return list(cache[liga_id])


def _ordenar_por_clasificacion(estado: dict, liga_id: str, equipos: list) -> list:
    """T1 por media; desde la T2 por la tabla final de 1ª (datos_carrera['copa_ranking'])."""
    ranking = ((estado.get('datos_carrera') or {}).get('copa_ranking') or {}).get(liga_id) or []
    pos = {n: i for i, n in enumerate(ranking)}
    return sorted(equipos, key=lambda e: (pos.get(getattr(e, 'nombre', ''), 999), -_ovr(e)))


def _datos_intl(tipo: str) -> tuple:
    """(nombres de relleno, dict de datos crudos) del banco internacional."""
    try:
        from alpha_football.data import internacional as I
        if tipo == 'champions':
            return list(I.RELLENO_CHAMPIONS), dict(I.DATOS_CHAMPIONS)
        return list(I.RELLENO_LIBERTADORES), dict(I.DATOS_LIBERTADORES)
    except Exception as e_i:
        logger.error(f"competiciones: banco internacional no disponible: {e_i}")
        return [], {}


def _pool(estado: dict, tipo: str) -> dict:
    """
    v3.8.0: clubes del banco internacional {nombre: Equipo}. Base = datos del juego; si la base
    editada trae ese mismo club, manda la versión editada. Techo sudamericano y envejecimiento
    pasivo por temporada (determinista). Se cachea fuera del save (estado['_copas_pool']).
    """
    temporada = int(estado.get('temporada', 1) or 1)
    cache = estado.setdefault('_copas_pool', {})
    if tipo in cache and cache[tipo].get('_temporada') == temporada:
        return cache[tipo]['equipos']
    equipos: dict = {}
    try:
        from alpha_football.data.internacional import get_pool_champions, get_pool_libertadores
        for eq in (get_pool_champions() if tipo == 'champions' else get_pool_libertadores()):
            equipos[eq.nombre] = eq
    except Exception as e_pool:
        logger.error(f"competiciones: no se pudo construir el pool {tipo}: {e_pool}")
    try:
        import json
        import os
        ruta = "alpha_football_edited_db.json"
        if os.path.exists(ruta):
            with open(ruta, 'r', encoding='utf-8') as f:
                db = json.load(f)
            from alpha_football.models import Equipo
            for d in (db.get(tipo) or []) if isinstance(db, dict) else []:
                try:
                    if isinstance(d, dict) and d.get('nombre') in equipos:
                        eq = Equipo.from_dict(d)
                        if getattr(eq, 'jugadores', None):
                            equipos[eq.nombre] = eq
                except Exception as e_eq:
                    logger.warning(f"competiciones: club editado inválido en {tipo}: {e_eq}")
    except Exception as e_db:
        logger.error(f"competiciones: no se pudo leer la base editada: {e_db}")
    try:
        from alpha_football.plantilla import aplicar_techo_region
        aplicar_techo_region(tipo, list(equipos.values()))
    except Exception as e_techo:
        logger.error(f"competiciones: techo regional: {e_techo}")
    try:
        anios = max(0, temporada - 1)
        if anios and equipos:
            from alpha_football.desarrollo import progresar_pasivo
            rng = random.Random(hash((tipo, anios)) & 0xFFFFFFFF)
            for eq in equipos.values():
                progresar_pasivo(eq, anios, rng)
    except Exception as e_age:
        logger.error(f"competiciones: envejecimiento del pool {tipo}: {e_age}")
    fichados = {tuple(x) for x in (estado.get('datos_carrera') or {}).get('fichados_intl', []) if len(x) == 2}
    if fichados:   # los que el user les fichó (el pool se rehace desde los datos del juego)
        for eq in equipos.values():
            eq.jugadores = [j for j in eq.jugadores if (eq.nombre, j.nombre_completo) not in fichados]
    cache[tipo] = {'_temporada': temporada, 'equipos': equipos}
    return equipos


def _nombre_pais(liga_id: str) -> str:
    try:
        from alpha_football.paises import pais_de
        return (pais_de(liga_id) or {}).get('nombre', liga_id)
    except Exception:
        return liga_id


def clasificados(estado: dict, tipo: str) -> list:
    """
    v3.8.0: 36 (Champions) / 32 (Libertadores) clubes {'nombre','ovr','pais','liga'}: los cupos de
    cada 1ª división (T1 por media, luego por la tabla final) + el relleno del banco internacional.
    Nunca repite nombres ni mete del banco un club que ya juega en alguna liga de la partida.
    """
    n_total = N_CLUBES.get(tipo, 0)
    res: list = []
    usados: set = set()

    def agregar(nombre, ovr, pais, liga) -> None:
        if nombre and nombre not in usados and len(res) < n_total:
            usados.add(nombre)
            res.append({'nombre': nombre, 'ovr': round(float(ovr), 1), 'pais': pais, 'liga': liga})

    ordenados = {}
    for liga_id, cupo in CUPOS.get(tipo, {}).items():
        ordenados[liga_id] = _ordenar_por_clasificacion(estado, liga_id, _equipos_1a(estado, liga_id))
        tomados = 0
        for eq in ordenados[liga_id]:
            if tomados >= cupo:
                break
            if eq.nombre not in usados:
                agregar(eq.nombre, _ovr(eq), _nombre_pais(liga_id), liga_id)
                tomados += 1
    # nombres de clubes de liga: el banco no puede duplicarlos (p. ej. "Penarol Roto" vive en Uruguay)
    en_ligas = {e.nombre for lg in _ligas_vivas(estado) for e in (getattr(lg, 'equipos', None) or [])}
    en_ligas |= {e.nombre for eqs in ordenados.values() for e in eqs}
    relleno, datos = _datos_intl(tipo)
    pool = _pool(estado, tipo)
    extra = sorted((n for n in pool if n not in relleno), key=lambda n: -_ovr(pool[n]))
    for nombre in relleno + extra:
        if nombre in pool and nombre not in en_ligas:
            agregar(nombre, _ovr(pool[nombre]), (datos.get(nombre) or {}).get('pais', ''), 'internacional')
    # último recurso: los siguientes de cada liga con cupo
    for liga_id, eqs in ordenados.items():
        for eq in eqs:
            agregar(eq.nombre, _ovr(eq), _nombre_pais(liga_id), liga_id)
    if len(res) < n_total:
        logger.error(f"competiciones: {tipo} con {len(res)}/{n_total} clubes")
    return res


def equipo_por_nombre(estado: dict, nombre: str):
    """
    v3.8.0: Equipo por nombre: el del user, las 16 ligas vivas, el pool internacional (cacheado) y,
    si nada lo tiene, un club generado con la media de la copa (nunca un mock sin plantel).
    """
    if not nombre:
        return None
    mi = estado.get('mi_equipo')
    if mi is not None and getattr(mi, 'nombre', None) == nombre:
        return mi
    for lg in _ligas_vivas(estado):
        for eq in (getattr(lg, 'equipos', None) or []):
            if eq.nombre == nombre:
                return eq
    for tipo in ('champions', 'libertadores'):
        eq = _pool(estado, tipo).get(nombre)
        if eq is not None:
            return eq
    generados = estado.setdefault('_copas_generados', {})
    if nombre not in generados:
        ovr = 72
        for c in (copa(estado, 'champions') or {}).get('clubes', []) + \
                (copa(estado, 'libertadores') or {}).get('clubes', []):
            if c.get('nombre') == nombre:
                ovr = int(c.get('ovr', 72) or 72)
        try:
            from alpha_football.models import Equipo
            from alpha_football.data.internacional import _generar_jugadores_equipo
            generados[nombre] = Equipo(nombre=nombre, ciudad="Internacional", estrellas=3.5,
                                       estilo_dt="flickismo", balance=10000000,
                                       jugadores=_generar_jugadores_equipo(ovr, 9000 + len(generados) * 60))
        except Exception as e_gen:
            logger.error(f"competiciones: no se pudo generar el club '{nombre}': {e_gen}")
            return None
    return generados[nombre]


# ════════════════════════════════════════════════════════════════════════════
# Temporada de copa: estado, etapas y avance
# ════════════════════════════════════════════════════════════════════════════

def _nombre_user(estado: dict) -> str:
    mi = estado.get('mi_equipo')
    return str(getattr(mi, 'nombre', '') or '') if mi is not None else ''


def _jornada_actual(estado: dict) -> int:
    try:
        return int(getattr(estado.get('liga'), 'jornada_actual', 1) or 1)
    except Exception:
        return 1


def _num_jornadas(estado: dict) -> int:
    """Jornadas de la liga del user (saves viejos pueden tener 10); por defecto 22."""
    try:
        j = int(getattr(estado.get('liga'), 'num_jornadas', 0) or 0)
    except Exception:
        j = 0
    return j if j >= 2 else 22


def _agregar_partido(c: dict, fecha: int, fase: str, local: str, visitante: str, **extra) -> dict:
    k = sum(1 for p in c['partidos'] if p['fecha'] == fecha)
    p = {'id': f"{c['tipo']}-{fecha}-{k}", 'fecha': int(fecha), 'fase': fase, 'local': local,
         'visitante': visitante, 'gl': 0, 'gv': 0, 'jugado': False}
    p.update(extra)
    c['partidos'].append(p)
    return p


def _nueva_copa(estado: dict, tipo: str, rng) -> dict:
    """v3.8.0: clasificados + sorteo de la 1ª etapa + mapeo de fechas al calendario de liga."""
    clubes = clasificados(estado, tipo)
    n, jornadas = N_FECHAS[tipo], _num_jornadas(estado)
    c = {'tipo': tipo, 'temporada': int(estado.get('temporada', 1) or 1), 'clubes': clubes,
         'num_jornadas': jornadas, 'fechas_jornada': [jornada_de_fecha(i, n, jornadas) for i in range(n)],
         'partidos': [], 'llaves': [], 'fase_actual': ETAPAS[tipo][0][0], 'campeon': None,
         'mejor_fase': {x['nombre']: FASES[tipo][0] for x in clubes}, 'ranking': {}, 'stats': {}}
    etiqueta = ETAPAS[tipo][0][0]
    if tipo == 'champions':
        for p in sorteo_fase_liga(clubes, rng):
            _agregar_partido(c, p['fecha'], etiqueta, p['local'], p['visitante'])
    else:
        c['grupos'] = sorteo_grupos(clubes, rng)
        for p in partidos_grupos(c['grupos']):
            _agregar_partido(c, p['fecha'], etiqueta, p['local'], p['visitante'], grupo=p['grupo'])
    return c


def iniciar_temporada(estado: dict, rng=None, forzar: bool = False) -> None:
    """
    v3.8.0: crea datos_carrera['copas'] = {'champions': {...}, 'libertadores': {...}} para la
    temporada actual. Idempotente: si ya están las de esta temporada no hace nada (salvo `forzar`).
    """
    dc = estado.get('datos_carrera')
    if not isinstance(dc, dict):
        dc = estado['datos_carrera'] = {}
    temporada = int(estado.get('temporada', 1) or 1)
    actuales = dc.get('copas') or {}
    if not forzar and all(isinstance(actuales.get(t), dict) and actuales[t].get('temporada') == temporada
                          for t in N_FECHAS):
        return
    rng = rng or random.Random()
    copas = {}
    for tipo in ('champions', 'libertadores'):
        try:
            copas[tipo] = _nueva_copa(estado, tipo, rng)
        except Exception as e_c:
            logger.error(f"competiciones: no se pudo iniciar la {tipo}: {e_c}")
    dc['copas'] = copas
    estado.pop('_copas_generados', None)


def _asegurar(estado: dict, rng=None) -> None:
    """Crea las copas si faltan o si son de otra temporada (save viejo / cambio de temporada)."""
    try:
        temporada = int(estado.get('temporada', 1) or 1)
        copas = (estado.get('datos_carrera') or {}).get('copas') or {}
        if any(not isinstance(copas.get(t), dict) or copas[t].get('temporada') != temporada for t in N_FECHAS):
            iniciar_temporada(estado, rng, forzar=True)
    except Exception as e_a:
        logger.error(f"competiciones: no se pudieron asegurar las copas: {e_a}")


def copa(estado: dict, tipo: str) -> Optional[dict]:
    """Estado serializable de la copa `tipo` de esta temporada (None si no existe)."""
    c = ((estado.get('datos_carrera') or {}).get('copas') or {}).get(tipo)
    return c if isinstance(c, dict) else None


def tipo_copa_user(estado: dict) -> Optional[str]:
    """'champions' / 'libertadores' si el club del user está en esa copa; si no, None."""
    user = _nombre_user(estado)
    if not user:
        return None
    for t in ('champions', 'libertadores'):
        c = copa(estado, t)
        if c and any(x.get('nombre') == user for x in c.get('clubes', [])):
            return t
    return None


def campeon(estado: dict, tipo: str) -> Optional[str]:
    return (copa(estado, tipo) or {}).get('campeon')


def _subir_fase(c: dict, nombre: str, fase: str) -> None:
    """Mejor fase alcanzada: solo sube."""
    orden = FASES[c['tipo']]
    if fase not in orden:
        return
    actual = c['mejor_fase'].get(nombre, orden[0])
    if actual not in orden or orden.index(fase) > orden.index(actual):
        c['mejor_fase'][nombre] = fase


def _fuerza(c: dict) -> dict:
    return {x['nombre']: float(x.get('ovr', 75) or 75) for x in c.get('clubes', [])}


def _resolver_llaves(c: dict, rng) -> None:
    """Define el ganador de cada llave con sus partidos jugados; la final da el campeón."""
    por_id = {p['id']: p for p in c['partidos']}
    fuerza = _fuerza(c)
    for ll in c['llaves']:
        if ll.get('ganador'):
            continue
        ida = por_id.get(ll.get('ida'))
        vuelta = por_id.get(ll.get('vuelta')) if ll.get('vuelta') else None
        if not ida or not ida.get('jugado') or (ll.get('vuelta') and not (vuelta and vuelta.get('jugado'))):
            continue
        ll['ganador'] = resolver_llave(ida, vuelta, rng, fuerza)
        if ll['fase'] == 'Final':
            c['campeon'] = ll['ganador']
            _subir_fase(c, ll['ganador'], 'Campeón')
            c['fase_actual'] = 'Terminada'


def _etapa_completa(c: dict, etiqueta: str) -> bool:
    ps = [p for p in c['partidos'] if p['fase'] == etiqueta]
    return bool(ps) and all(p['jugado'] for p in ps) \
        and all(ll.get('ganador') for ll in c['llaves'] if ll['fase'] == etiqueta)


def _cruces_siguiente(c: dict, ultima: str) -> list:
    """Cruces de la etapa que sigue a `ultima` (que ya terminó)."""
    tipo = c['tipo']
    etapa = [p for p in c['partidos'] if p['fase'] == ultima]
    if ultima == 'Fase de liga':
        t = tabla([x['nombre'] for x in c['clubes']], etapa)
        c['ranking'] = {f['nombre']: i for i, f in enumerate(t)}
        for f in t[:8]:
            _subir_fase(c, f['nombre'], 'Octavos')           # 1º-8º directo a octavos
        return cruces_playoff(t)
    if ultima == 'Fase de grupos':
        tablas = [tabla(g, [p for p in etapa if p.get('grupo') == gi]) for gi, g in enumerate(c.get('grupos') or [])]
        filas = sorted(((pos, f) for tb in tablas for pos, f in enumerate(tb)),
                       key=lambda x: (x[0], -x[1]['pts'], -x[1]['dif'], -x[1]['gf'], x[1]['nombre']))
        c['ranking'] = {f['nombre']: i for i, (_pos, f) in enumerate(filas)}
        return cruces_octavos_libertadores(tablas)
    llaves = [ll for ll in c['llaves'] if ll['fase'] == ultima]
    if ultima == 'Playoff':
        orden = sorted(c['ranking'], key=c['ranking'].get)
        return cruces_octavos_champions([{'nombre': n} for n in orden],
                                        {(ll['a'], ll['b']): ll['ganador'] for ll in llaves})
    etiquetas = [e for e, _f in ETAPAS[tipo]]
    siguiente = etiquetas[etiquetas.index(ultima) + 1]
    ganadores = [ll['ganador'] for ll in llaves]
    return [(ganadores[i], ganadores[j]) for i, j in CUADRO[tipo].get(siguiente, [])
            if i < len(ganadores) and j < len(ganadores)]


def _armar_llave(c: dict, etiqueta: str, fechas: list, x: str, y: str) -> None:
    """Ida y vuelta (cierra de local el mejor clasificado) o final única (local nominal el mejor)."""
    rk = c.get('ranking') or {}
    a, b = sorted((x, y), key=lambda n: rk.get(n, 999))
    idx = len(c['llaves'])
    if len(fechas) >= 2:
        ida = _agregar_partido(c, fechas[0], etiqueta, b, a, llave=idx)
        vuelta = _agregar_partido(c, fechas[1], etiqueta, a, b, llave=idx, ida_de=ida['id'])
    else:
        ida = _agregar_partido(c, fechas[0], etiqueta, a, b, llave=idx)
        vuelta = None
    c['llaves'].append({'fase': etiqueta, 'a': a, 'b': b, 'ida': ida['id'],
                        'vuelta': vuelta['id'] if vuelta else None, 'ganador': None})


def _armar_siguiente(c: dict, rng) -> bool:
    """Si la última etapa armada terminó, arma la siguiente. True si armó algo."""
    etapas = ETAPAS[c['tipo']]
    armadas = [i for i, (e, _f) in enumerate(etapas) if any(p['fase'] == e for p in c['partidos'])]
    if not armadas:
        return False
    i = armadas[-1]
    if i + 1 >= len(etapas) or not _etapa_completa(c, etapas[i][0]):
        return False
    cruces = _cruces_siguiente(c, etapas[i][0])
    if not cruces:
        return False
    etiqueta, fechas = etapas[i + 1]
    for x, y in cruces:
        _armar_llave(c, etiqueta, fechas, x, y)
        for n in (x, y):
            _subir_fase(c, n, 'Finalista' if etiqueta == 'Final' else etiqueta)
    c['fase_actual'] = etiqueta
    return True


# ── simulación de partidos de la IA ─────────────────────────────────────────────

_CAMPOS_LIGA = ('goles', 'asistencias', 'partidos_jugados', 'promedio_nota')


def _desarrollo_copa(equipo, gf: int, gc: int, stats_partido: Optional[dict] = None) -> list:
    """
    v3.8.0: desarrollo post-partido (progreso, forma) sin tocar las estadísticas de LIGA: los goles,
    asistencias, PJ y nota de copa van a copa['stats'] (el Balón de Oro los suma aparte).
    """
    try:
        from alpha_football.desarrollo import desarrollar_plantilla_post_partido
        previo = {id(j): tuple(getattr(j, k, 0) for k in _CAMPOS_LIGA) for j in equipo.jugadores}
        reporte = desarrollar_plantilla_post_partido(equipo, gf, gc, stats_partido=stats_partido)
        for j in equipo.jugadores:
            if id(j) in previo:
                for k, v in zip(_CAMPOS_LIGA, previo[id(j)]):
                    setattr(j, k, v)
        return reporte or []
    except Exception as e_dev:
        logger.debug(f"competiciones: desarrollo de copa de {getattr(equipo, 'nombre', '?')}: {e_dev}")
        return []


def _acumular_stats(c: dict, club: str, reporte: list, goles_contra: int) -> None:
    stats = c.setdefault('stats', {})
    for r in reporte or []:
        try:
            nombre = str(r.get('jugador', '') or '')
            if not nombre:
                continue
            s = stats.setdefault(f"{club}|{nombre}", {'nombre': nombre, 'club': club,
                                                     'pos': r.get('posicion', ''), 'goles': 0,
                                                     'asist': 0, 'pj': 0, 'vallas': 0})
            s['goles'] += int(r.get('goles', 0) or 0)
            s['asist'] += int(r.get('asistencias', 0) or 0)
            s['pj'] += 1
            if goles_contra == 0 and r.get('posicion') == 'POR':
                s['vallas'] += 1
        except Exception as e_r:
            logger.debug(f"competiciones: fila de stats inválida {r}: {e_r}")


def registrar_stats(estado: dict, tipo: str, club: str, reporte: list, goles_contra: int = 1) -> None:
    """
    v3.8.0: suma a copa['stats'] el reporte de desarrollo de un partido de copa (el del user, que se
    juega en vivo fuera del motor). Claves "club|jugador" → {'nombre','club','pos','goles','asist','pj','vallas'}.
    """
    c = copa(estado, tipo)
    if c is not None:
        _acumular_stats(c, club, reporte, goles_contra)


def _simular(estado: dict, c: dict, p: dict, rng) -> None:
    """Juega un partido de copa con el motor de la liga (misma función que simular_otros_partidos)."""
    loc = equipo_por_nombre(estado, p['local'])
    vis = equipo_por_nombre(estado, p['visitante'])
    gl = gv = None
    st_l = st_v = None
    if loc is not None and vis is not None:
        try:
            from alpha_football.engine import simular_partido
            from alpha_football.partido_ctx import stats_de_equipo
            from alpha_football.sanciones import en_competicion
            with en_competicion('copa'):          # rojas y amarillas de copa se cumplen en copa
                res = simular_partido(loc, vis, con_eventos_caoticos=False)
            gl, gv = int(res.goles_local), int(res.goles_visitante)
            st_l, st_v = stats_de_equipo(res.ctx, res.notas, 'l'), stats_de_equipo(res.ctx, res.notas, 'v')
        except Exception as e_sim:
            logger.error(f"competiciones: error simulando {p['local']} vs {p['visitante']}: {e_sim}")
    if gl is None:                                        # respaldo: marcador por media
        fz = _fuerza(c)
        d = (fz.get(p['local'], 75) - fz.get(p['visitante'], 75)) / 20.0
        gl = max(0, int(round(rng.gauss(1.4 + d, 1.0))))
        gv = max(0, int(round(rng.gauss(1.1 - d, 1.0))))
    p['gl'], p['gv'], p['jugado'] = gl, gv, True
    if loc is not None:
        _acumular_stats(c, p['local'], _desarrollo_copa(loc, gl, gv, st_l), gv)
    if vis is not None:
        _acumular_stats(c, p['visitante'], _desarrollo_copa(vis, gv, gl, st_v), gl)


def _avanzar_copa(estado: dict, c: Optional[dict], rng, jornada: Optional[int], jugar_user: bool) -> None:
    """
    v3.8.0: juega en orden las fechas vencidas (`jornada` > fechas_jornada[i]; None = todas). El
    partido del user queda pendiente (salvo `jugar_user`) y las fechas siguientes lo esperan.
    """
    if not c or c.get('campeon'):
        return
    user = _nombre_user(estado)
    fj = c.get('fechas_jornada') or []
    for f in range(len(fj)):
        if jornada is not None and not jornada > fj[f]:
            break
        ps = [p for p in c['partidos'] if p['fecha'] == f]
        if not ps:
            _armar_siguiente(c, rng)
            ps = [p for p in c['partidos'] if p['fecha'] == f]
            if not ps:
                break                                     # la etapa anterior no terminó
        espera_user = False
        for p in ps:
            if p['jugado']:
                continue
            if user and user in (p['local'], p['visitante']) and not jugar_user:
                espera_user = True
                continue
            _simular(estado, c, p, rng)
        _resolver_llaves(c, rng)
        _armar_siguiente(c, rng)
        if espera_user:
            break


def avanzar(estado: dict, rng=None) -> None:
    """v3.8.0: tras cada jornada de liga del user: juega las fechas vencidas de ambas copas."""
    _asegurar(estado, rng)
    rng = rng or random.Random()
    jornada = _jornada_actual(estado)
    for t in ('champions', 'libertadores'):
        try:
            _avanzar_copa(estado, copa(estado, t), rng, jornada, jugar_user=False)
        except Exception as e_av:
            logger.error(f"competiciones: error avanzando la {t}: {e_av}")


def simular_todo(estado: dict, rng=None) -> None:
    """v3.8.0: termina ambas copas (fin de temporada), incluido el partido del user si no lo jugó."""
    _asegurar(estado, rng)
    rng = rng or random.Random()
    for t in ('champions', 'libertadores'):
        try:
            _avanzar_copa(estado, copa(estado, t), rng, None, jugar_user=True)
        except Exception as e_st:
            logger.error(f"competiciones: error simulando la {t}: {e_st}")


# ── API del user ────────────────────────────────────────────────────────────────

def partido_pendiente_user(estado: dict) -> Optional[dict]:
    """
    v3.8.0: el partido del user de la próxima fecha vencida (copia con 'tipo'), o None. Antes juega
    lo ajeno vencido de su copa para que la llave siguiente ya esté armada.
    """
    _asegurar(estado)
    t = tipo_copa_user(estado)
    c = copa(estado, t) if t else None
    if not c or c.get('campeon'):
        return None
    jornada = _jornada_actual(estado)
    try:
        _avanzar_copa(estado, c, random.Random(), jornada, jugar_user=False)
    except Exception as e_av:
        logger.error(f"competiciones: error avanzando la copa del user: {e_av}")
    user = _nombre_user(estado)
    fj = c.get('fechas_jornada') or []
    for p in sorted(c['partidos'], key=lambda x: x['fecha']):
        if not p['jugado'] and user in (p['local'], p['visitante']) \
                and p['fecha'] < len(fj) and jornada > fj[p['fecha']]:
            return dict(p, tipo=t)
    return None


def _penales_normalizados(penales) -> Optional[dict]:
    try:
        if isinstance(penales, dict):
            a = penales.get('a', penales.get('local'))
            b = penales.get('b', penales.get('visitante'))
            return {'a': int(a), 'b': int(b)}
        if isinstance(penales, (list, tuple)) and len(penales) == 2:
            return {'a': int(penales[0]), 'b': int(penales[1])}
    except Exception:
        pass
    return None


def registrar_resultado_user(estado: dict, partido_id: str, gl: int, gv: int, penales=None) -> None:
    """
    v3.8.0: guarda el resultado del partido de copa jugado en vivo (goles del local y del visitante
    de ESE partido; penales como {'a': local, 'b': visitante} o (local, visitante)). Un partido ya
    jugado no se pisa.
    """
    for t in ('champions', 'libertadores'):
        c = copa(estado, t)
        if not c:
            continue
        for p in c['partidos']:
            if p.get('id') != partido_id:
                continue
            if p.get('jugado'):
                logger.info(f"competiciones: {partido_id} ya estaba jugado; no se pisa")
                return
            p['gl'], p['gv'], p['jugado'] = int(gl or 0), int(gv or 0), True
            pen = _penales_normalizados(penales)
            if pen is not None:
                p['penales'] = pen
            rng = random.Random()
            _resolver_llaves(c, rng)
            _armar_siguiente(c, rng)
            return
    logger.warning(f"competiciones: partido {partido_id} no encontrado")


def _eliminado(c: dict, nombre: str) -> bool:
    if c.get('campeon') and c['campeon'] != nombre:
        return True
    if any(ll.get('ganador') and ll['ganador'] != nombre and nombre in (ll['a'], ll['b']) for ll in c['llaves']):
        return True
    # terminó la 1ª etapa (hay llaves) y no pasó
    return bool(c['llaves']) and c['mejor_fase'].get(nombre) == FASES[c['tipo']][0]


def fase_user(estado: dict) -> str:
    """Mejor fase alcanzada por el user en su copa (etiqueta de FASES); '' si no juega copa."""
    t = tipo_copa_user(estado)
    if not t:
        return ''
    return copa(estado, t)['mejor_fase'].get(_nombre_user(estado), FASES[t][0])


def linea_estado_user(estado: dict) -> str:
    """"Champions · Octavos (ida) vs X" / "Champions · eliminado en Cuartos" / "Champions · ¡campeón!"."""
    try:
        t = tipo_copa_user(estado)
        if not t:
            return "Sin copa internacional esta temporada"
        c, user, nombre = copa(estado, t), _nombre_user(estado), NOMBRE_COPA[t]
        if c.get('campeon') == user:
            return f"{nombre} · ¡campeón!"
        fase = fase_user(estado)
        if _eliminado(c, user):
            return f"{nombre} · subcampeón" if fase == 'Finalista' else f"{nombre} · eliminado en {fase}"
        prox = next((p for p in sorted(c['partidos'], key=lambda x: x['fecha'])
                     if not p['jugado'] and user in (p['local'], p['visitante'])), None)
        if prox is None:
            return f"{nombre} · {fase} (esperando rival)"
        rival = prox['visitante'] if prox['local'] == user else prox['local']
        if prox['fase'] in ('Fase de liga', 'Fase de grupos'):
            etapa_fechas = dict(ETAPAS[t])[prox['fase']]
            return f"{nombre} · {prox['fase']} (fecha {prox['fecha'] + 1}/{len(etapa_fechas)}) vs {rival}"
        if prox['fase'] == 'Final':
            return f"{nombre} · Final vs {rival}"
        return f"{nombre} · {prox['fase']} ({'vuelta' if prox.get('ida_de') else 'ida'}) vs {rival}"
    except Exception as e_l:
        logger.error(f"competiciones: linea_estado_user: {e_l}")
        return ""
