# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Logros del DT (v0.4.25.0: de 9 a 29 hitos).
Hitos de la carrera. Cada uno que se desbloquea queda en `datos_carrera['logros']` y publica una noticia
'logro' de importancia 5 con un botón que abre HISTORIAL DE CARRERA. Lógica pura sobre `estado`: nada de pygame
(el overlay vive en ui/career_screen.py).

    datos_carrera['logros'] = {'obtenidos': {id: {'temporada', 'jornada'}},
                               'contadores': {'pj', 'racha', 'clasicos_seguidos', 'victorias', 'invicto',
                                              'derrotas_seguidas', 'sin_ganar', 'porteria_cero',
                                              'visitante_ganados'}}
"""
from __future__ import annotations

import logging
import re
import unicodedata
from typing import Optional

logger = logging.getLogger(__name__)

# (id, título, descripción)
LOGROS = [
    ('titulo_liga', "Campeón de liga", "Gana un título de liga."),
    ('bicampeon', "Bicampeón", "Gana 2 títulos de liga."),
    ('tricampeon', "Tricampeón", "Gana 3 títulos de liga."),
    ('final_continental', "Final continental", "Llega a una final de copa internacional."),
    ('campeon_continental', "Campeón continental", "Gana la copa internacional de tu continente."),
    ('balon_oro', "Balón de Oro en casa", "Un jugador de tu club gana el Balón de Oro."),
    ('pj_50', "50 partidos", "Dirige 50 partidos oficiales (liga y copa)."),
    ('pj_100', "100 partidos", "Dirige 100 partidos oficiales (liga y copa)."),
    ('pj_200', "200 partidos", "Dirige 200 partidos oficiales (liga y copa)."),
    ('pj_300', "300 partidos", "Dirige 300 partidos oficiales (liga y copa)."),
    ('pj_500', "500 partidos", "Dirige 500 partidos oficiales (liga y copa)."),
    ('victorias_50', "50 victorias", "Gana 50 partidos oficiales."),
    ('victorias_100', "100 victorias", "Gana 100 partidos oficiales."),
    ('racha_5', "Cinco de cinco", "Gana 5 partidos oficiales seguidos."),
    ('racha_8', "Racha de ocho", "Gana 8 partidos oficiales seguidos."),
    ('racha_12', "Imparable", "Gana 12 partidos oficiales seguidos."),
    ('invicto_10', "Diez sin perder", "Pasa 10 partidos oficiales seguidos sin perder."),
    ('invicto_20', "La muralla", "Pasa 20 partidos oficiales seguidos sin perder."),
    ('manita', "La manita", "Gana un partido oficial por 5 goles de diferencia o más."),
    ('muro_5', "El muro", "Deja la portería a cero en 5 partidos oficiales seguidos."),
    ('viajero_5', "Ganador de visitante", "Gana 5 partidos oficiales seguidos como visitante."),
    ('salvado', "Salvado sobre la hora", "Sal de la zona de descenso en la última jornada de la liga."),
    ('clasicos_3', "Dueño del clásico", "Gana 3 clásicos seguidos."),
    ('clasicos_5', "Rey de los clásicos", "Gana 5 clásicos seguidos."),
    ('fichaje_84', "Fichaje de lujo", "Ficha a un jugador de media 84 o más."),
    ('goleador_30', "Goleador de 30", "Que uno de tus jugadores marque 30 goles en una temporada."),
    ('millonario', "Caja fuerte", "Junta 1.000 millones de euros en la caja del club."),
    ('temporadas_5', "Cinco temporadas", "Completa 5 temporadas al frente del club."),
    ('temporadas_10', "Una década", "Completa 10 temporadas al frente del club."),
]
_INFO = {i: (titulo, desc) for i, titulo, desc in LOGROS}
# (logro, contador, umbral): se desbloquea cuando el contador llega al umbral
_UMBRALES = (('pj_50', 'pj', 50), ('pj_100', 'pj', 100), ('pj_200', 'pj', 200), ('pj_300', 'pj', 300),
             ('pj_500', 'pj', 500), ('victorias_50', 'victorias', 50), ('victorias_100', 'victorias', 100),
             ('racha_5', 'racha', 5), ('racha_8', 'racha', 8), ('racha_12', 'racha', 12),
             ('invicto_10', 'invicto', 10), ('invicto_20', 'invicto', 20), ('muro_5', 'porteria_cero', 5),
             ('viajero_5', 'visitante_ganados', 5), ('clasicos_3', 'clasicos_seguidos', 3),
             ('clasicos_5', 'clasicos_seguidos', 5))
_CONTADORES = ('pj', 'racha', 'clasicos_seguidos', 'victorias', 'invicto', 'derrotas_seguidas', 'sin_ganar',
               'porteria_cero', 'visitante_ganados')
_DIFERENCIA_MANITA = 5
_MEDIA_LUJO = 84
_GOLES_GOLEADOR = 30
_CAJA_MILLONARIO = 1_000_000_000
_ACCION = {'pantalla': 'career_screen', 'texto': "VER LOGROS"}


def logros(estado: dict) -> dict:
    """datos_carrera['logros'], creado y completado si falta (guardados viejos)."""
    dc = estado.get('datos_carrera')
    if not isinstance(dc, dict):
        dc = estado['datos_carrera'] = {}
    est = dc.get('logros')
    if not isinstance(est, dict):
        est = dc['logros'] = {}
    if not isinstance(est.get('obtenidos'), dict):
        est['obtenidos'] = {}
    if not isinstance(est.get('contadores'), dict):
        est['contadores'] = {}
    for clave in _CONTADORES:
        try:
            est['contadores'][clave] = int(est['contadores'].get(clave) or 0)
        except (TypeError, ValueError):
            est['contadores'][clave] = 0
    return est


def desbloquear(estado: dict, logro_id: str, temporada: Optional[int] = None,
                jornada: Optional[int] = None) -> Optional[dict]:
    """Marca el logro como obtenido y publica su noticia. None si ya estaba o no existe."""
    info = _INFO.get(logro_id)
    if info is None:
        return None
    est = logros(estado)
    if logro_id in est['obtenidos']:
        return None
    liga = estado.get('liga')
    t = int(temporada if temporada is not None else (estado.get('temporada', 1) or 1))
    j = int(jornada if jornada is not None else (getattr(liga, 'jornada_actual', 0) or 0))
    est['obtenidos'][logro_id] = {'temporada': t, 'jornada': j}
    titulo, descripcion = info
    try:
        from alpha_football import noticias
        return noticias.publicar(estado, 'logro', f"Logro: {titulo}", descripcion, importancia=5,
                                 accion=dict(_ACCION), clave=f"logro:{logro_id}", temporada=t, jornada=j)
    except Exception as e:
        # el logro ya quedó guardado: solo falta la noticia, que no debe tumbar el cierre del partido
        logger.error(f"logros: no se pudo publicar la noticia de {logro_id}: {e}", exc_info=True)
        return {'tipo': 'logro', 'logro': logro_id}


def _es_mi(estado: dict, equipo) -> bool:
    mi = estado.get('mi_equipo')
    return mi is not None and equipo is not None and (
        equipo is mi or getattr(equipo, 'id', None) == getattr(mi, 'id', -1))


def _posicion(liga, mi) -> int:
    """Puesto en la tabla (puntos, diferencia, goles a favor); 0 si el club no está."""
    tabla = sorted(getattr(liga, 'equipos', []) or [],
                   key=lambda x: (getattr(x, 'puntos', 0), getattr(x, 'gf', 0) - getattr(x, 'gc', 0),
                                  getattr(x, 'gf', 0)), reverse=True)
    return next((i + 1 for i, x in enumerate(tabla) if x.id == mi.id), 0)


def _salvado(estado: dict, pos_antes: Optional[int]) -> bool:
    """Última jornada de la 1ª división: entraba en los dos últimos puestos y termina fuera de ellos."""
    liga, mi = estado.get('liga'), estado.get('mi_equipo')
    if liga is None or mi is None or pos_antes is None or getattr(liga, 'division', 1) != 1:
        return False
    jugadas = [p.jornada for p in getattr(liga, 'calendario', []) or [] if getattr(p, 'jugado', False)]
    if not jugadas or max(jugadas) != int(getattr(liga, 'num_jornadas', 0) or 0):
        return False
    n = len(liga.equipos)
    pos = _posicion(liga, mi)
    return bool(pos) and int(pos_antes) >= n - 1 and pos <= n - 2


def registrar_partido(estado: dict, local, visitante, gl: int, gv: int, modo: str,
                      pos_antes: Optional[int] = None) -> list:
    """Cuenta un partido oficial del user (liga o copa) y devuelve los ids desbloqueados con él.
    `pos_antes` = puesto de liga antes del partido (para 'salvado')."""
    nuevos: list = []
    try:
        if modo not in ('liga', 'copa') or estado.get('mi_equipo') is None:
            return nuevos
        es_local = _es_mi(estado, local)
        gf, gc = (int(gl), int(gv)) if es_local else (int(gv), int(gl))
        gano = gf > gc
        c = logros(estado)['contadores']
        c['pj'] += 1
        c['victorias'] += 1 if gano else 0
        c['racha'] = c['racha'] + 1 if gano else 0              # un empate o una derrota corta la racha
        c['invicto'] = c['invicto'] + 1 if gf >= gc else 0
        c['derrotas_seguidas'] = c['derrotas_seguidas'] + 1 if gf < gc else 0
        c['sin_ganar'] = 0 if gano else c['sin_ganar'] + 1
        c['porteria_cero'] = c['porteria_cero'] + 1 if gc == 0 else 0
        if not es_local:                                         # solo los partidos de visitante cuentan para esta racha
            c['visitante_ganados'] = c['visitante_ganados'] + 1 if gano else 0
        from alpha_football.data.clasicos import es_clasico
        if es_clasico(local, visitante):                         # los partidos que no son clásico no tocan la cuenta
            c['clasicos_seguidos'] = c['clasicos_seguidos'] + 1 if gano else 0
        candidatos = [i for i, contador, umbral in _UMBRALES if c[contador] >= umbral]
        if gf - gc >= _DIFERENCIA_MANITA:
            candidatos.append('manita')
        if modo == 'liga' and _salvado(estado, pos_antes):
            candidatos.append('salvado')
        for logro_id in candidatos:
            if desbloquear(estado, logro_id):
                nuevos.append(logro_id)
    except Exception as e:
        logger.error(f"logros: no se pudo registrar el partido: {e}", exc_info=True)
    return nuevos


def _normal(texto) -> str:
    return unicodedata.normalize('NFKD', str(texto or '')).encode('ascii', 'ignore').decode().lower()


def _es_final(texto) -> bool:
    """'Final', 'Finalista', 'Subcampeón' o 'Campeón' sí; 'Semifinal' y el resto no."""
    return bool(re.search(r'\bfinal(ista)?\b|campe', _normal(texto)))


def _es_campeon(texto) -> bool:
    """'Campeón' sí; 'Subcampeón', 'Finalista' y el resto no."""
    return bool(re.search(r'\bcampe', _normal(texto)))


def _hay_fichaje_de_lujo(estado: dict) -> bool:
    """Una compra tuya (propio, con tu club de destino) de media >= 84 EN EL MOMENTO de fichar: lee el historial de
    pases, que guarda la media de entonces; un jugador que llegó con 80 y creció no cuenta. Un guardado viejo sin
    historial no lo desbloquea hasta el próximo fichaje."""
    club = getattr(estado.get('mi_equipo'), 'nombre', None)
    historial = (estado.get('datos_carrera') or {}).get('historial_pases') or []
    return bool(club) and any(
        isinstance(p, dict) and p.get('propio') and str(p.get('a')) == club
        and int(p.get('media', 0) or 0) >= _MEDIA_LUJO for p in historial)


def _titulos_de_liga(historial: list) -> int:
    return sum(1 for h in historial if h.get('pos') == 1)


def _hay_goleador(estado: dict) -> bool:
    jugadores = getattr(estado.get('mi_equipo'), 'jugadores', None) or []
    return any(int(getattr(j, 'goles', 0) or 0) >= _GOLES_GOLEADOR for j in jugadores)


def _caja(estado: dict) -> int:
    return int(getattr(estado.get('mi_equipo'), 'balance', 0) or 0)


def revisar(estado: dict, temporada: Optional[int] = None, jornada: Optional[int] = None) -> list:
    """Los logros que salen de mirar el estado (títulos, finales y copas, fichaje de lujo, goleador, caja,
    temporadas cumplidas). Se llama al cerrar cada jornada y al cerrar la temporada; devuelve los ids
    recién desbloqueados. 'balon_oro' lo desbloquea la gala del premio (premios.py), no esta revisión."""
    nuevos: list = []
    historial = [h for h in (estado.get('historial') or []) if isinstance(h, dict)]
    fases = [h.get('libertadores') for h in historial] + [estado.get('copa_mejor_fase_temp')]
    comprobaciones = (
        ('titulo_liga', lambda: _titulos_de_liga(historial) >= 1),
        ('bicampeon', lambda: _titulos_de_liga(historial) >= 2),
        ('tricampeon', lambda: _titulos_de_liga(historial) >= 3),
        ('final_continental', lambda: any(_es_final(t) for t in fases)),
        ('campeon_continental', lambda: any(_es_campeon(t) for t in fases)),
        ('fichaje_84', lambda: _hay_fichaje_de_lujo(estado)),
        ('goleador_30', lambda: _hay_goleador(estado)),
        ('millonario', lambda: _caja(estado) >= _CAJA_MILLONARIO),
        ('temporadas_5', lambda: len(historial) >= 5),
        ('temporadas_10', lambda: len(historial) >= 10),
    )
    for logro_id, se_cumple in comprobaciones:
        try:
            if se_cumple() and desbloquear(estado, logro_id, temporada, jornada):
                nuevos.append(logro_id)
        except Exception as e:
            logger.error(f"logros: no se pudo revisar {logro_id}: {e}", exc_info=True)
    return nuevos


def para_overlay(estado: dict) -> list:
    """[{'id','titulo','descripcion','obtenido','temporada','jornada'}]: los obtenidos primero (el más reciente
    arriba) y después los pendientes en el orden de LOGROS."""
    obtenidos = logros(estado)['obtenidos']
    orden = {i: n for n, i in enumerate(obtenidos)}
    filas = []
    for logro_id, titulo, descripcion in LOGROS:
        ob = obtenidos.get(logro_id) if isinstance(obtenidos.get(logro_id), dict) else None
        filas.append({'id': logro_id, 'titulo': titulo, 'descripcion': descripcion, 'obtenido': ob is not None,
                      'temporada': int((ob or {}).get('temporada', 0) or 0),
                      'jornada': int((ob or {}).get('jornada', 0) or 0)})
    hechos = sorted((f for f in filas if f['obtenido']),
                    key=lambda f: (-f['temporada'], -f['jornada'], -orden.get(f['id'], 0)))
    return hechos + [f for f in filas if not f['obtenido']]
