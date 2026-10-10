# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Logros del DT (v0.4.23.0).
Nueve hitos de la carrera. Cada uno que se desbloquea queda en `datos_carrera['logros']` y publica una noticia
'logro' de importancia 5 con un botón que abre HISTORIAL DE CARRERA. Lógica pura sobre `estado`: nada de pygame
(el overlay vive en ui/career_screen.py).

    datos_carrera['logros'] = {'obtenidos': {id: {'temporada', 'jornada'}},
                               'contadores': {'pj', 'racha', 'clasicos_seguidos'}}
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
    ('final_continental', "Final continental", "Llega a una final de copa internacional."),
    ('pj_50', "50 partidos", "Dirige 50 partidos oficiales (liga y copa)."),
    ('pj_100', "100 partidos", "Dirige 100 partidos oficiales (liga y copa)."),
    ('pj_200', "200 partidos", "Dirige 200 partidos oficiales (liga y copa)."),
    ('racha_8', "Racha de ocho", "Gana 8 partidos oficiales seguidos."),
    ('salvado', "Salvado sobre la hora", "Sal de la zona de descenso en la última jornada de la liga."),
    ('clasicos_3', "Dueño del clásico", "Gana 3 clásicos seguidos."),
    ('fichaje_84', "Fichaje de lujo", "Ficha a un jugador de media 84 o más."),
]
_INFO = {i: (titulo, desc) for i, titulo, desc in LOGROS}
_UMBRAL_PJ = (('pj_50', 50), ('pj_100', 100), ('pj_200', 200))
_RACHA = 8
_CLASICOS = 3
_MEDIA_LUJO = 84
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
    for clave in ('pj', 'racha', 'clasicos_seguidos'):
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
        c['racha'] = c['racha'] + 1 if gano else 0              # un empate o una derrota corta la racha
        from alpha_football.data.clasicos import es_clasico
        if es_clasico(local, visitante):                         # los partidos que no son clásico no tocan la cuenta
            c['clasicos_seguidos'] = c['clasicos_seguidos'] + 1 if gano else 0
        candidatos = [i for i, umbral in _UMBRAL_PJ if c['pj'] >= umbral]
        if c['racha'] >= _RACHA:
            candidatos.append('racha_8')
        if c['clasicos_seguidos'] >= _CLASICOS:
            candidatos.append('clasicos_3')
        if modo == 'liga' and _salvado(estado, pos_antes):
            candidatos.append('salvado')
        for logro_id in candidatos:
            if desbloquear(estado, logro_id):
                nuevos.append(logro_id)
    except Exception as e:
        logger.error(f"logros: no se pudo registrar el partido: {e}", exc_info=True)
    return nuevos


def _es_final(texto) -> bool:
    """'Final', 'Finalista', 'Subcampeón' o 'Campeón' sí; 'Semifinal' y el resto no."""
    t = unicodedata.normalize('NFKD', str(texto or '')).encode('ascii', 'ignore').decode().lower()
    return bool(re.search(r'\bfinal(ista)?\b|campe', t))


def _hay_fichaje_de_lujo(estado: dict) -> bool:
    """Una compra tuya (propio, con tu club de destino) de media >= 84 EN EL MOMENTO de fichar: lee el historial de
    pases, que guarda la media de entonces; un jugador que llegó con 80 y creció no cuenta. Un guardado viejo sin
    historial no lo desbloquea hasta el próximo fichaje."""
    club = getattr(estado.get('mi_equipo'), 'nombre', None)
    historial = (estado.get('datos_carrera') or {}).get('historial_pases') or []
    return bool(club) and any(
        isinstance(p, dict) and p.get('propio') and str(p.get('a')) == club
        and int(p.get('media', 0) or 0) >= _MEDIA_LUJO for p in historial)


def revisar(estado: dict, temporada: Optional[int] = None, jornada: Optional[int] = None) -> list:
    """Los logros que salen de mirar el estado (título de liga, final continental, fichaje de lujo).
    Se llama al cerrar cada jornada y al cerrar la temporada; devuelve los ids recién desbloqueados."""
    nuevos: list = []
    historial = [h for h in (estado.get('historial') or []) if isinstance(h, dict)]
    comprobaciones = (
        ('titulo_liga', lambda: any(h.get('pos') == 1 for h in historial)),
        ('final_continental', lambda: any(_es_final(t) for t in
                                          [h.get('libertadores') for h in historial] + [estado.get('copa_mejor_fase_temp')])),
        ('fichaje_84', lambda: _hay_fichaje_de_lujo(estado)),
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
