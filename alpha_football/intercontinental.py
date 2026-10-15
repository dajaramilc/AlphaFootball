# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Copa Intercontinental (v0.4.26.0)
En diciembre, una semana después de la final de la Libertadores: el campeón de la Libertadores contra el
último campeón de la Champions, a partido único (empate = penales). Premio: 20 M€ al campeón y 6 M€ al
finalista.
- Solo con los continentes desfasados (temporadas.activo) y reloj (dias.activo): la Libertadores termina en
  diciembre y la Champions ya tiene campeón desde junio.
- Estado: datos_carrera['intercontinental'] = {'anio', 'fecha', 'local', 'visitante', 'jugado', 'gl', 'gv',
  'penales', 'campeon', 'historial': [{'anio', 'campeon', 'finalista', 'marcador'}]}.
- Si tu club la juega es un partido tuyo más (calendario.eventos_user) y se juega desde JUGAR como uno de copa
  (copa_screen.preparar_partido_copa); si no, se simula sola ese día (dias.revisar_dia → revisar_jornada).
Sin UI.
"""
from __future__ import annotations

import logging
import random
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

PREMIO_CAMPEON = 20_000_000
PREMIO_FINALISTA = 6_000_000
MORAL_CAMPEON = 25
NOMBRE = "Copa Intercontinental"


def _reg(estado: dict) -> dict:
    dc = estado.setdefault('datos_carrera', {})
    reg = dc.get('intercontinental')
    if not isinstance(reg, dict):
        reg = dc['intercontinental'] = {}
    if not isinstance(reg.get('historial'), list):
        reg['historial'] = []
    return reg


def _activo(estado: dict) -> bool:
    try:
        from alpha_football import dias, temporadas
        return (estado.get('liga') is not None and estado.get('mi_equipo') is not None
                and temporadas.activo(estado) and dias.activo(estado))
    except Exception as e:
        logger.error(f"intercontinental: no se pudo saber si corre: {e}")
        return False


def _user(estado: dict) -> str:
    return str(getattr(estado.get('mi_equipo'), 'nombre', '') or '')


def _mm(monto: int) -> str:
    return f"{int(monto) / 1_000_000:.0f} M€"


def fecha_base(anio: int) -> date:
    """Una semana después de la final base de la Libertadores (el sábado siguiente a su última jornada,
    que cae a más tardar el 13 de diciembre). Nunca el 24 ni el 25: pasa al 27."""
    from alpha_football import calendario as CAL
    d = CAL._sabado_hasta(date(anio, 12, 13)) + timedelta(days=14)
    return date(anio, 12, 27) if d.month == 12 and d.day in (24, 25) else d


def _campeon_libertadores(estado: dict, anio: int) -> Optional[str]:
    from alpha_football import competiciones as CP
    c = CP.copa(estado, 'libertadores')
    if c and c.get('campeon') and c.get('anio') in (None, anio):
        return c['campeon']
    return None


def _campeon_champions(estado: dict) -> Optional[str]:
    """El último campeón de Europa; en la primera temporada (todavía no terminó ninguna Champions), el club
    de mayor media de la Champions en curso hace de campeón vigente."""
    from alpha_football import competiciones as CP
    mundo = (estado.get('datos_carrera') or {}).get('mundo') or {}
    nombre = (mundo.get('campeones') or {}).get('champions')
    if nombre:
        return nombre
    c = CP.copa(estado, 'champions') or {}
    if c.get('campeon'):
        return c['campeon']
    clubes = [x for x in c.get('clubes') or [] if x.get('nombre')]
    return max(clubes, key=lambda x: float(x.get('ovr', 0) or 0))['nombre'] if clubes else None


def programar(estado: dict) -> Optional[dict]:
    """Arma la final del año apenas se conoce al campeón de la Libertadores (una sola vez por año)."""
    from alpha_football import temporadas, dias, calendario as CAL
    anio = temporadas.anio(estado, 'sudamerica')
    reg = _reg(estado)
    if reg.get('anio') == anio:
        return reg
    lib = _campeon_libertadores(estado, anio)
    ucl = _campeon_champions(estado) if lib else None
    if not lib or not ucl or lib == ucl:
        return None
    hoy = dias.hoy(estado)
    fecha = max(fecha_base(anio), hoy + timedelta(days=7))
    if fecha > date(anio, 12, 30):                            # final de la Libertadores muy tarde: igual en diciembre
        fecha = max(date(anio, 12, 30), hoy + timedelta(days=CAL.MIN_DIAS))
    reg.update({'anio': anio, 'fecha': fecha.isoformat(), 'local': lib, 'visitante': ucl, 'jugado': False,
                'gl': 0, 'gv': 0, 'penales': None, 'campeon': None})
    texto_f = CAL.texto_fecha(fecha, False)
    try:
        from alpha_football import noticias
        noticias.publicar(estado, 'otro', f"{NOMBRE}: {lib} vs {ucl}",
                          f"El campeón de la Libertadores y el campeón de Europa se verán las caras el {texto_f} "
                          f"a partido único en cancha neutral. El ganador se lleva {_mm(PREMIO_CAMPEON)} y el "
                          f"finalista {_mm(PREMIO_FINALISTA)}.", importancia=4)
    except Exception as e:
        logger.error(f"intercontinental: no se pudo publicar la previa: {e}")
    user = _user(estado)
    if user in (lib, ucl):
        try:
            from alpha_football import correo as C
            rival = ucl if user == lib else lib
            C.enviar(estado, 'directiva', f"Jugarás la {NOMBRE}",
                     f"Como campeones vigentes juegan la {NOMBRE} contra {rival} el {texto_f}. Es a partido único "
                     f"en cancha neutral: si termina empatado se define por penales. El campeón cobra "
                     f"{_mm(PREMIO_CAMPEON)} y el finalista {_mm(PREMIO_FINALISTA)}.",
                     C.accion('calendario_screen', "VER CALENDARIO"))
        except Exception as e:
            logger.error(f"intercontinental: no se pudo avisar al DT: {e}")
    logger.info(f"Intercontinental {anio}: {lib} vs {ucl} el {fecha}.")
    return reg


def _clave(reg: dict) -> str:
    return f"intercontinental:{reg.get('anio')}"


def fecha(estado: dict) -> Optional[date]:
    """Día de la final programada (respeta la reprogramación del calendario); None si no hay."""
    reg = (estado.get('datos_carrera') or {}).get('intercontinental') or {}
    if not reg.get('fecha'):
        return None
    try:
        from alpha_football import calendario as CAL
        return CAL._movido(estado, _clave(reg)) or date.fromisoformat(reg['fecha'])
    except Exception as e:
        logger.error(f"intercontinental: fecha inválida: {e}")
        return None


def evento_user(estado: dict) -> Optional[dict]:
    """El partido como evento de calendario.eventos_user (solo si tu club la juega)."""
    reg = (estado.get('datos_carrera') or {}).get('intercontinental') or {}
    user = _user(estado)
    if not user or user not in (reg.get('local'), reg.get('visitante')):
        return None
    f = fecha(estado)
    if f is None:
        return None
    loc, jugado = reg['local'] == user, bool(reg.get('jugado'))
    gf, gc = (reg.get('gl'), reg.get('gv')) if loc else (reg.get('gv'), reg.get('gl'))
    return {'clave': _clave(reg), 'tipo': 'copa', 'num': 0, 'fecha': f, 'jugado': jugado, 'local': loc,
            'rival': reg['visitante'] if loc else reg['local'], 'gf': gf if jugado else None,
            'gc': gc if jugado else None, 'etiqueta': 'INT'}


def pendiente_user(estado: dict) -> Optional[dict]:
    """Tu final de hoy (o atrasada) como partido de copa ({'id', 'tipo', 'fase', ...}); None si no toca."""
    try:
        ev = evento_user(estado)
        if ev is None or ev['jugado'] or not _activo(estado):
            return None
        from alpha_football import dias
        if dias.hoy(estado) < ev['fecha']:
            return None
        reg = _reg(estado)
        return {'id': f"intercontinental-{reg['anio']}", 'tipo': 'intercontinental', 'fase': 'Final',
                'fecha': None, 'local': reg['local'], 'visitante': reg['visitante'], 'gl': 0, 'gv': 0,
                'jugado': False}
    except Exception as e:
        logger.error(f"intercontinental: error leyendo tu partido: {e}")
        return None


def registrar_resultado(estado: dict, gl: int, gv: int, penales: Optional[dict] = None) -> None:
    """Resultado de la final ({'a': penales del local, 'b': del visitante} si hubo). No pisa una ya jugada."""
    reg = _reg(estado)
    if not reg.get('anio') or reg.get('jugado'):
        return
    reg['gl'], reg['gv'], reg['jugado'] = int(gl or 0), int(gv or 0), True
    if reg['gl'] == reg['gv']:
        pen = penales if isinstance(penales, dict) else None
        if pen is None:
            from alpha_football import competiciones as CP
            pa, pb = CP.penales(75, 75)
            pen = {'a': pa, 'b': pb}
        reg['penales'] = {'a': int(pen.get('a', 0) or 0), 'b': int(pen.get('b', 0) or 0)}
        gana_local = reg['penales']['a'] > reg['penales']['b']
    else:
        gana_local = reg['gl'] > reg['gv']
    reg['campeon'] = reg['local'] if gana_local else reg['visitante']
    _cerrar(estado, reg)


def _simular(estado: dict, rng=None) -> None:
    """La final sin el user: motor de partido (o marcador por media si falla) y penales si hay empate."""
    from alpha_football import competiciones as CP
    reg = _reg(estado)
    rng = rng or random.Random()
    loc, vis = CP.equipo_por_nombre(estado, reg['local']), CP.equipo_por_nombre(estado, reg['visitante'])
    gl = gv = None
    if loc is not None and vis is not None:
        try:
            from alpha_football.engine import simular_partido
            from alpha_football.partido_ctx import stats_de_equipo
            from alpha_football.sanciones import en_competicion
            with en_competicion('copa'):
                res = simular_partido(loc, vis, con_eventos_caoticos=False)
            gl, gv = int(res.goles_local), int(res.goles_visitante)
            CP._desarrollo_copa(loc, gl, gv, stats_de_equipo(res.ctx, res.notas, 'l'))
            CP._desarrollo_copa(vis, gv, gl, stats_de_equipo(res.ctx, res.notas, 'v'))
        except Exception as e:
            logger.error(f"intercontinental: error simulando la final: {e}", exc_info=True)
    if gl is None:
        d = (CP._ovr(loc) - CP._ovr(vis)) / 20.0 if loc is not None and vis is not None else 0.0
        gl = max(0, int(round(rng.gauss(1.2 + d, 1.0))))
        gv = max(0, int(round(rng.gauss(1.2 - d, 1.0))))
    pen = None
    if gl == gv:
        pa, pb = CP.penales(CP._ovr(loc) if loc is not None else 75, CP._ovr(vis) if vis is not None else 75, rng)
        pen = {'a': pa, 'b': pb}
    registrar_resultado(estado, gl, gv, pen)


def marcador(reg: dict) -> str:
    txt = f"{reg.get('local')} {reg.get('gl', 0)}-{reg.get('gv', 0)} {reg.get('visitante')}"
    pen = reg.get('penales')
    return txt + (f" ({pen['a']}-{pen['b']} en penales)" if isinstance(pen, dict) else "")


def _cerrar(estado: dict, reg: dict) -> None:
    """Premios, moral del campeón, historial, noticia y correo. Cada paso bajo su propio control de errores."""
    from alpha_football import competiciones as CP
    campeon = reg['campeon']
    finalista = reg['visitante'] if campeon == reg['local'] else reg['local']
    mi = estado.get('mi_equipo')
    user = _user(estado)
    for club, monto in ((campeon, PREMIO_CAMPEON), (finalista, PREMIO_FINALISTA)):
        try:
            eq = mi if club == user else CP.equipo_por_nombre(estado, club)
            if eq is None:
                continue
            eq.balance = int(getattr(eq, 'balance', 0) or 0) + monto
            if club == user:
                from alpha_football.finanzas import registrar
                from alpha_football import correo as C
                registrar(estado, 'premios', monto)
                C.enviar(estado, 'directiva', f"Premio de la {NOMBRE}",
                         f"{'¡Campeones del mundo!' if club == campeon else 'Fuimos finalistas.'} Ingresaron "
                         f"{_mm(monto)} a las arcas del club por la {NOMBRE} ({marcador(reg)}).",
                         C.accion('finanzas_screen', "VER FINANZAS"))
        except Exception as e:
            logger.error(f"intercontinental: no se pudo pagar el premio de {club}: {e}")
    try:
        from alpha_football import vestuario
        eq = mi if campeon == user else CP.equipo_por_nombre(estado, campeon)
        if eq is not None:
            vestuario.impulso_moral(estado, eq, MORAL_CAMPEON, 'titulo')
    except Exception as e:
        logger.error(f"intercontinental: no se pudo subir la moral del campeón: {e}")
    reg['historial'].append({'anio': reg['anio'], 'campeon': campeon, 'finalista': finalista,
                             'marcador': marcador(reg)})
    try:
        from alpha_football import noticias
        noticias.publicar(estado, 'campeon', f"¡{campeon} gana la {NOMBRE}!",
                          f"{marcador(reg)}. {campeon} es el mejor club del mundo y se lleva {_mm(PREMIO_CAMPEON)}; "
                          f"{finalista} cobra {_mm(PREMIO_FINALISTA)} como finalista.", importancia=5)
    except Exception as e:
        logger.error(f"intercontinental: no se pudo publicar al campeón: {e}")
    logger.info(f"Intercontinental {reg['anio']}: campeón {campeon} ({marcador(reg)}).")


def revisar_jornada(estado: dict) -> None:
    """Cada día (dias.revisar_dia): programa la final cuando hay campeón de la Libertadores y, llegado su día,
    la simula si no es tuya (la tuya se juega desde JUGAR; si quedó atrasada, también se simula)."""
    try:
        if not _activo(estado):
            return
        reg = programar(estado)
        if not reg or reg.get('jugado'):
            return
        from alpha_football import dias
        f, hoy = fecha(estado), dias.hoy(estado)
        if f is None or hoy < f:
            return
        if _user(estado) in (reg.get('local'), reg.get('visitante')) and hoy == f:
            return
        _simular(estado)
    except Exception as e:
        logger.error(f"intercontinental: error revisando el día: {e}", exc_info=True)
