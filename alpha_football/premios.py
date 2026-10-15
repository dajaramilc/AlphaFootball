# -*- coding: utf-8 -*-
"""
Alpha Football v2.3.6 — BALÓN DE ORO.

Al cerrar la temporada se elige al mejor jugador de TODAS las ligas (1ª y 2ª de los
5 países) según su rendimiento de la temporada: nota media, goles, asistencias,
vallas invictas, títulos (liga y copa) y el peso de la liga donde jugó.
Mecánica pura y testeable: recibe las ligas y devuelve un dict serializable.

v0.4.17.0: los premios se CALCULAN al cerrar la temporada pero se ENTREGAN en una fecha: el Balón de
Oro el último lunes de octubre y el Jugador Sudamericano del Año (los que juegan en las ligas
sudamericanas) el 15 de enero. Mientras tanto esperan en datos_carrera['premios_pendientes'].
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)

# v3.8.0: peso de cada liga de 1ª desde el registro de países (Europa 1.0; Brasil y Argentina 0.85;
# el resto 0.75) y de cualquier 2ª (0.6).
def _pesos_1a() -> dict:
    try:
        from alpha_football.paises import PAISES
        return {p['liga_id']: 1.0 if p['region'] == 'europa' else 0.85 if p['liga_id'] in ('brasil', 'argentina')
                else 0.75 for p in PAISES}
    except Exception as e_p:
        logger.error(f"Balón de Oro: no se pudo leer paises: {e_p}")
        return {'premier': 1.0, 'laliga': 1.0, 'seriea': 1.0, 'brasil': 0.85, 'argentina': 0.85}


PESO_LIGA_1A = _pesos_1a()
PESO_LIGA_2A = 0.6
BONO_CAMPEON_LIGA = 15.0          # v3.8.0: liga de 1ª ganada
BONO_CAMPEON_COPA = 20.0          # v3.8.0: Champions o Libertadores ganada
MIN_PARTIDOS_PCT = 0.5   # hay que haber jugado al menos la mitad de la liga


def _clave_tabla(e: Any) -> tuple:
    return (getattr(e, 'puntos', 0), getattr(e, 'gf', 0) - getattr(e, 'gc', 0), getattr(e, 'gf', 0))


def puntaje_jugador(j: Any, peso_liga: float, campeon_liga: bool, campeon_copa: bool,
                    goles_copa: int = 0, asist_copa: int = 0, vallas_copa: int = 0) -> float:
    """
    v3.8.0: goles×4 + asistencias×2 + max(0, nota−6)×10 + liga 15 + copa 20 + (POR) vallas×1.5,
    todo × peso de la liga. Los goles/asistencias/vallas de copa se suman a los de liga.
    """
    nota = float(getattr(j, 'promedio_nota', 0) or 0)
    goles = int(getattr(j, 'goles', 0) or 0) + int(goles_copa or 0)
    asist = int(getattr(j, 'asistencias', 0) or 0) + int(asist_copa or 0)
    base = goles * 4.0 + asist * 2.0 + max(0.0, nota - 6.0) * 10.0
    if getattr(j, 'posicion', '') == 'POR':
        base += (int(getattr(j, 'porterias_cero', 0) or 0) + int(vallas_copa or 0)) * 1.5
    if campeon_liga:
        base += BONO_CAMPEON_LIGA
    if campeon_copa:
        base += BONO_CAMPEON_COPA
    return round(base * peso_liga, 2)


def _stats_copa_por_jugador(datos_copas: Optional[dict]) -> dict:
    """{(club, nombre): {'goles','asist','vallas'}} sumando las dos copas de la temporada."""
    res: dict = {}
    for c in (datos_copas or {}).values():
        for s in ((c or {}).get('stats') or {}).values():
            try:
                k = (s.get('club', ''), s.get('nombre', ''))
                d = res.setdefault(k, {'goles': 0, 'asist': 0, 'vallas': 0, 'pj': 0})
                d['pj'] += int(s.get('pj', 0) or 0)            # v4.3.0: partidos de copa
                d['goles'] += int(s.get('goles', 0) or 0)
                d['asist'] += int(s.get('asist', 0) or 0)
                d['vallas'] += int(s.get('vallas', 0) or 0)
            except Exception as e_s:
                logger.debug(f"Balón de Oro: fila de copa inválida {s}: {e_s}")
    return res


def calcular_balon_de_oro(primeras: dict, segundas: dict, temporada: int,
                          campeon_copa=None, n_podio: int = 3,
                          datos_copas: Optional[dict] = None) -> Optional[dict]:
    """
    Recorre las 10 ligas y devuelve {'temporada', 'ganador', 'podio'} (cada jugador como
    dict con nombre, equipo, liga, posición, OVR, goles, asistencias, nota, PJ y puntaje),
    o None si nadie jugó lo suficiente.
    """
    # v3.8.0: campeon_copa puede ser un nombre o una colección (campeones de las dos copas);
    # datos_copas = datos_carrera['copas'] (goles/asistencias/vallas de copa por jugador).
    if isinstance(campeon_copa, str) or campeon_copa is None:
        campeones_copa = {campeon_copa} if campeon_copa else set()
    else:
        campeones_copa = {x for x in campeon_copa if x}
    stats_copa = _stats_copa_por_jugador(datos_copas)
    candidatos = []
    for division, mapa in ((1, primeras or {}), (2, segundas or {})):
        for tipo, liga in mapa.items():
            if liga is None or not getattr(liga, 'equipos', None):
                continue
            try:
                peso = PESO_LIGA_1A.get(tipo, 0.75) if division == 1 else PESO_LIGA_2A
                jornadas = int(getattr(liga, 'num_jornadas', 10) or 10)
                campeon = max(liga.equipos, key=_clave_tabla)
                for eq in liga.equipos:
                    # v4.3.0: el mínimo es el % sobre liga + copa; los partidos de copa del club se
                    # toman del jugador que más jugó en ella
                    pj_copa_eq = max((stats_copa.get((eq.nombre, getattr(x, 'nombre_completo', '')), {}).get('pj', 0)
                                      for x in eq.jugadores), default=0)
                    min_pj = max(3, int((jornadas + pj_copa_eq) * MIN_PARTIDOS_PCT))
                    for j in eq.jugadores:
                        sc = stats_copa.get((eq.nombre, getattr(j, 'nombre_completo', '')), {})
                        if int(getattr(j, 'partidos_jugados', 0) or 0) + int(sc.get('pj', 0) or 0) < min_pj:
                            continue
                        pts = puntaje_jugador(j, peso, eq is campeon, eq.nombre in campeones_copa,
                                              sc.get('goles', 0), sc.get('asist', 0), sc.get('vallas', 0))
                        candidatos.append((pts, j, eq, liga, sc))
            except Exception as e_liga:
                logger.error(f"Balón de Oro: error revisando la liga '{tipo}': {e_liga}")
    if not candidatos:
        return None
    candidatos.sort(key=lambda c: c[0], reverse=True)

    def _ficha(pts, j, eq, liga, sc) -> dict:
        return {
            'nombre': getattr(j, 'nombre_completo', f"{j.nombre} {j.apellido}"),
            'equipo': eq.nombre,
            'liga': getattr(liga, 'nombre', getattr(liga, 'tipo', '?')),
            'posicion': getattr(j, 'posicion', '?'),
            'ovr': int(getattr(j, 'overall', 0) or 0),
            'goles': int(getattr(j, 'goles', 0) or 0),
            'asistencias': int(getattr(j, 'asistencias', 0) or 0),
            'nota': round(float(getattr(j, 'promedio_nota', 0) or 0), 2),
            'pj': int(getattr(j, 'partidos_jugados', 0) or 0) + int(sc.get('pj', 0) or 0),   # v4.3.0: liga + copa
            'goles_copa': int(sc.get('goles', 0) or 0),        # v3.8.0
            'asistencias_copa': int(sc.get('asist', 0) or 0),
            'puntaje': pts,
        }

    podio = [_ficha(*c) for c in candidatos[:n_podio]]
    return {'temporada': int(temporada), 'ganador': podio[0], 'podio': podio}


# ── v0.4.17.0: premios por fecha ─────────────────────────────────────────────────

PREMIOS = {
    'balon_oro': {'nombre': "Balón de Oro", 'palmares': 'balon_oro', 'frase': "gana el Balón de Oro"},
    'sudamericano': {'nombre': "Jugador Sudamericano del Año", 'palmares': 'sudamericano',
                     'frase': "es elegido Jugador Sudamericano del Año"},
}


def calcular_sudamericano(primeras: dict, segundas: dict, temporada: int, campeon_libertadores=None,
                          datos_copas: Optional[dict] = None, n_podio: int = 3) -> Optional[dict]:
    """El mejor de los que juegan en las ligas sudamericanas (1ª y 2ª), con su Libertadores. Misma
    fórmula y mismo dict que el Balón de Oro."""
    from alpha_football.paises import SUDAMERICA
    solo = lambda mapa: {t: l for t, l in (mapa or {}).items() if t in SUDAMERICA}
    copas = {k: v for k, v in (datos_copas or {}).items() if k == 'libertadores'}
    return calcular_balon_de_oro(solo(primeras), solo(segundas), temporada, campeon_libertadores, n_podio, copas)


def _gala_en(premio: str, anio: int) -> date:
    if premio == 'sudamericano':
        return date(anio, 1, 15)
    d = date(anio, 10, 31)                               # Balón de Oro: último lunes de octubre
    return d - timedelta(days=d.weekday())


def fecha_entrega(estado: dict, premio: str) -> date:
    """La primera gala de ese premio en o después del inicio de la temporada en curso (al cerrar una
    temporada, la que acaba de empezar)."""
    from alpha_football import temporada as T
    ini = T.inicio(estado)
    d = _gala_en(premio, ini.year)
    return d if d >= ini else _gala_en(premio, ini.year + 1)


def _pendientes(estado: dict) -> list:
    dc = estado.setdefault('datos_carrera', {})
    if not isinstance(dc.get('premios_pendientes'), list):
        dc['premios_pendientes'] = []
    return dc['premios_pendientes']


def _entregar(estado: dict, p: dict, gala: bool = True, frenar: bool = True) -> bool:
    """Entrega un premio: palmarés, noticia de Prensa y, si alguien del podio juega en tu club, la gala.
    Un pendiente dañado (premio desconocido o sin ganador) se descarta. Con `frenar`, la gala además
    detiene a CONTINUAR ese día."""
    cfg, datos = PREMIOS.get(p.get('premio')), p.get('datos') or {}
    g = datos.get('ganador') or {}
    if cfg is None or not g:
        return False
    dc = estado.setdefault('datos_carrera', {})
    dc.setdefault(cfg['palmares'], []).append(datos)
    podio = datos.get('podio') or [g]
    try:    # v0.4.23.0: es una noticia (antes, un correo de Prensa)
        from alpha_football import correo as C, noticias
        otros = "".join(f" {i + 2}º: {x.get('nombre', '?')} ({x.get('equipo', '?')})."
                        for i, x in enumerate(podio[1:3]))
        # v0.4.25.0: la temporada con su año real ("2036/37"), no con su número de carrera
        nombre_t = noticias.nombre_temporada(estado, datos.get('temporada', 1),
                                             'sudamerica' if p.get('premio') == 'sudamericano' else None)
        noticias.publicar(estado, 'premio', f"{cfg['nombre']}: {g.get('nombre', '?')}",
                          f"{g.get('nombre', '?')} ({g.get('equipo', '?')}, {g.get('liga', '?')}) {cfg['frase']} de la "
                          f"temporada {nombre_t}: {g.get('goles', 0)} goles, {g.get('asistencias', 0)} "
                          f"asistencias y nota {float(g.get('nota', 0) or 0):.2f}.{otros}",
                          importancia=5, accion=C.accion('career_screen', "VER PALMARÉS"))
    except Exception as e:
        logger.error(f"No se pudo anunciar el {cfg['nombre']}: {e}")
    club = estado.get('mi_equipo')
    mi = getattr(club, 'nombre', None)
    # "tuyo": lo ganó con tu club o ya juega en él (lo fichaste entre el cierre y la gala). La ficha no
    # cambia: el palmarés conserva el club con el que lo ganó.
    plantilla = {getattr(j, 'nombre_completo', '') for j in getattr(club, 'jugadores', None) or []} - {''}
    tuyos = [x.get('nombre') for x in podio if x.get('equipo') == mi or x.get('nombre') in plantilla] if mi else []
    if mi and p.get('premio') == 'balon_oro' and (g.get('equipo') == mi or g.get('nombre') in plantilla):
        try:    # v0.4.25.0: logro "Balón de Oro en casa"
            from alpha_football import logros
            logros.desbloquear(estado, 'balon_oro')
        except Exception as e:
            logger.error(f"No se pudo desbloquear el logro del Balón de Oro: {e}")
    if gala and tuyos:
        dc.setdefault('gala_premio_pendiente', []).append(
            {'premio': p['premio'], 'fecha': p.get('fecha_entrega'), 'datos': datos, 'tuyos': tuyos})
        if frenar:
            estado['_parar_avance'] = True               # dias.continuar frena el día de la gala
    return True


def cerrar_temporada(estado: dict, primeras: dict, segundas: dict, temporada: int,
                     campeones_copas: Optional[dict] = None) -> list:
    """Cierre de temporada, con las tablas finales intactas: calcula los premios de `temporada` y los
    deja pendientes hasta su gala. Lo que siguiera pendiente de la anterior se entrega ya, sin gala."""
    pend = _pendientes(estado)
    for p in list(pend):
        try:
            if isinstance(p, dict):
                _entregar(estado, p, gala=False)
        except Exception as e:
            logger.error(f"No se pudo entregar un premio atrasado: {e}")
    del pend[:]
    campeones = campeones_copas or {}
    datos_copas = (estado.get('datos_carrera') or {}).get('copas')
    calculos = (
        ('balon_oro', lambda: calcular_balon_de_oro(primeras, segundas, temporada,
                                                   [c for c in campeones.values() if c], datos_copas=datos_copas)),
        ('sudamericano', lambda: calcular_sudamericano(primeras, segundas, temporada,
                                                       campeones.get('libertadores'), datos_copas)),
    )
    for premio, calcular in calculos:
        try:
            datos = calcular()
            if datos:
                pend.append({'premio': premio, 'fecha_entrega': fecha_entrega(estado, premio).isoformat(),
                             'datos': datos})
                logger.info(f"{PREMIOS[premio]['nombre']} T{temporada}: {datos['ganador']['nombre']} "
                            f"({datos['ganador']['equipo']}), se entrega el {pend[-1]['fecha_entrega']}")
        except Exception as e:
            logger.error(f"Error calculando el {PREMIOS[premio]['nombre']}: {e}")
    return pend


def revisar_jornada(estado: dict, rng=None, frenar: bool = True) -> int:
    """Entrega los premios cuya gala ya llegó. Idempotente y sin UI: se llama cada día (dias.revisar_dia)
    y después de cada partido. Devuelve cuántos entregó. Con `frenar=False` (cierre de un partido) la gala
    queda pendiente igual, pero sin la marca que frena a CONTINUAR: esa la consume el reloj del día y, puesta
    fuera de él, frenaría el avance un día después."""
    if estado.get('liga') is None or estado.get('mi_equipo') is None:
        return 0
    pend = _pendientes(estado)                           # un save dañado (no es lista) queda como lista vacía
    if not pend:
        return 0
    from alpha_football import temporada as T
    hoy = T.fecha(estado).isoformat()
    vencen = [p for p in pend if not isinstance(p, dict) or str(p.get('fecha_entrega') or '') <= hoy]
    entregados = 0
    for p in vencen:
        pend.remove(p)
        try:
            entregados += int(isinstance(p, dict) and _entregar(estado, p, frenar=frenar))
        except Exception as e:
            logger.error(f"No se pudo entregar un premio: {e}", exc_info=True)
    return entregados
