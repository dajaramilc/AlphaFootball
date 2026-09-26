# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Pantalla de las copas internacionales (Pygame).

v3.8.0: la lógica vive en `alpha_football/competiciones.py` (Champions con fase de liga de 36 y
Libertadores con 8 grupos de 4). Este módulo es:
  1. la FACHADA que usan hub, prepartido, match, resumen de temporada, menú y directiva
     (mismos nombres de funciones que antes, ahora sobre el motor), y
  2. la VISTA: pestañas FASE DE LIGA / GRUPOS, LLAVES, PARTIDOS y ESTADÍSTICAS, con selector
     CHAMPIONS / LIBERTADORES. Las funciones de dibujo se reutilizan en el hub y en OTRAS LIGAS.
"""

import sys
import random
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import pygame
except ImportError as error_pygame:
    print(f"Error crítico al importar pygame en copa_screen: {error_pygame}.", file=sys.stderr)
    raise error_pygame

# Importación resiliente del tema visual
try:
    from alpha_football.ui.theme import (SCREEN_W, SCREEN_H, COLORS, get_font, draw_gradient_bg,
                                         draw_panel, draw_button, draw_text)
except Exception as error_import_theme:
    print(f"Advertencia: No se pudo importar alpha_football.ui.theme ({error_import_theme}). "
          f"Usando fallback local.", file=sys.stderr)
    SCREEN_W, SCREEN_H = 1280, 720
    COLORS = {'bg': (10, 14, 26), 'verde': (0, 255, 136), 'dorado': (255, 215, 0), 'rojo': (255, 68, 68),
              'azul': (0, 191, 255), 'blanco': (255, 255, 255), 'panel': (20, 26, 46)}

    def get_font(size):
        try:
            return pygame.font.SysFont("arial", {'sm': 18, 'md': 24, 'lg': 32, 'xl': 48}.get(size, 24))
        except Exception:
            return pygame.font.Font(None, 24)

    def draw_gradient_bg(screen):
        screen.fill((10, 14, 26))

    def draw_panel(screen, rect):
        pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=8)
        pygame.draw.rect(screen, (0, 191, 255), rect, width=1, border_radius=8)

    def draw_button(screen, rect, text, hover):
        pygame.draw.rect(screen, (0, 191, 255) if hover else (20, 26, 46), rect, border_radius=5)
        pygame.draw.rect(screen, (255, 255, 255), rect, width=1, border_radius=5)
        s = get_font('md').render(text, True, (10, 14, 26) if hover else (255, 255, 255))
        screen.blit(s, s.get_rect(center=rect.center))
        return rect

    def draw_text(screen, text, pos, size='md', color='blanco', shadow=True):
        s = get_font(size).render(str(text), True, COLORS.get(color, (255, 255, 255)))
        screen.blit(s, pos)

from alpha_football import competiciones as CP  # noqa: E402
from alpha_football.paises import EUROPA as _EUROPA, SUDAMERICA as _SUDAMERICA, es_europa  # noqa: E402

# v3.8.0: cupos por liga de 1ª = los del motor (1 más que en v3.7: premier/laliga/seriea 5,
# brasil 7, argentina 6, betplay/uruguay/ecuador 5).
CUPOS_COPA = {**CP.CUPOS['champions'], **CP.CUPOS['libertadores']}
LIGAS_COPA = {'Champions': _EUROPA, 'Libertadores': _SUDAMERICA}

# Identidad del club real detrás de cada parodia (tests de clasificados sin parodias repetidas).
_IDENTIDAD_CLUB = {
    'real_madrid': ('real madriz', 'real vadrid', 'real madrid'),
    'barcelona': ('farcelona',),
    'atletico': ('patetico',),
    'boca': ('boca',),
    'river': ('river',),
    'palmeiras': ('palmeir', 'palmerinha', 'palmeras de sao'),
    'flamengo': ('flamengu',),
    'man_city': ('manchester billete', 'manchester city'),
    'man_utd': ('manchester desunido', 'manchester united'),
    'liverpool': ('pool de higado', 'liverpool'),
    'arsenal': ('arsenal',),
    'chelsea': ('chelsea',),
    'tottenham': ('spurs',),
    'psg': ('paris saint',),
    'bayern': ('bayern',),
    'dortmund': ('dormund', 'dortmund'),
    'juventus': ('piamonte', 'juventus'),
    'inter': ('inter de milan',),
    'milan': ('milan abuelo', 'ac milan'),
    'benfica': ('benfica',),
    'porto': ('puerto fc',),
}

# v3.8.0: claves del estado de la copa vieja (v0.x–v3.7). Se borran al sincronizar; si había una
# copa vieja a mitad de temporada, el motor la regenera y juega las fechas ya pasadas.
CLAVES_VIEJAS = ('copa_tipo', 'copa_fase_actual', 'copa_grupo_standing', 'copa_bracket',
                 'copa_grupo_partidos', 'copa_jornada_grupo', 'copa_tab', 'copa_grupos',
                 'copa_grupos_standings', 'copa_bracket_otros', 'copa_stats', 'copa_stats_abierto',
                 'copa_equipos_obj', 'copa_campeon_toast_until', '_spectator_dismissed',
                 'partido_copa_bracket_fase')
_CLAVES_COPA_EN_CURSO = ('copa_bracket', 'copa_grupo_partidos', 'copa_fase_actual', 'copa_grupos')

# v3.8.0: premios en dinero por fase alcanzada (acumulativos). Libertadores: la mitad.
PREMIO_FASE_CHAMPIONS = {'Fase de liga': 2_000_000, 'Playoff': 1_000_000, 'Octavos': 3_000_000,
                         'Cuartos': 5_000_000, 'Semifinal': 8_000_000, 'Finalista': 12_000_000,
                         'Campeón': 20_000_000}
PREMIO_FASE_LIBERTADORES = {'Fase de grupos': 1_000_000, 'Octavos': 1_500_000, 'Cuartos': 2_500_000,
                            'Semifinal': 4_000_000, 'Finalista': 6_000_000, 'Campeón': 10_000_000}


def premio_total(tipo: str) -> int:
    """v4.3.0: suma de los premios de todas las fases (lo que cobra el campeón)."""
    return int(sum((PREMIO_FASE_CHAMPIONS if tipo == 'champions' else PREMIO_FASE_LIBERTADORES).values()))


def texto_premio(tipo: str, fase: str, acumulado: int) -> str:
    """v4.3.0: cuerpo del correo de premio: monto de la fase, su % del total y el % acumulado."""
    total = max(1, premio_total(tipo))
    monto = premio_fase(tipo, fase)
    return (f"Premio por alcanzar {fase}: ${monto:,} ({round(monto * 100 / total)}% del premio total; "
            f"acumulado {round(acumulado * 100 / total)}%).")


def premio_fase(tipo: str, fase: str) -> int:
    tabla = PREMIO_FASE_CHAMPIONS if tipo == 'champions' else PREMIO_FASE_LIBERTADORES
    return int(tabla.get(fase, 0))


def cupos_copa(tipo_liga: str) -> int:
    """Cuántos equipos de esa liga (1ª) clasifican a la copa internacional."""
    return CUPOS_COPA.get(tipo_liga, 3)


def identidad_club(nombre: str) -> str:
    """Clave del club real que parodia `nombre` ('' si no se reconoce)."""
    n = str(nombre or '').lower()
    for clave, alias in _IDENTIDAD_CLUB.items():
        if any(a in n for a in alias):
            return clave
    return ''


def guardar_ranking_copas(estado: dict) -> None:
    """v2.3.6: guarda la tabla final de cada 1ª división (define los clasificados de la
    próxima copa). Se llama al cerrar la temporada, antes del ascenso/descenso."""
    ranking = {}
    for tipo, liga_x in (estado.get('primera_division') or {}).items():
        if liga_x is None:
            continue
        ordenados = sorted(
            liga_x.equipos,
            key=lambda e: (getattr(e, 'puntos', 0), getattr(e, 'gf', 0) - getattr(e, 'gc', 0), getattr(e, 'gf', 0)),
            reverse=True)
        ranking[tipo] = [e.nombre for e in ordenados]
    estado.setdefault('datos_carrera', {})['copa_ranking'] = ranking


# ════════════════════════════════════════════════════════════════════════════
# v3.8.0: fachada sobre el motor
# ════════════════════════════════════════════════════════════════════════════

def _mi_nombre(estado: dict) -> str:
    return str(getattr(estado.get('mi_equipo'), 'nombre', '') or '')


def copa_de_region(estado: dict) -> str:
    """La copa del user (si clasificó) o la de su continente."""
    t = CP.tipo_copa_user(estado)
    if t:
        return t
    return 'champions' if es_europa(getattr(estado.get('liga'), 'tipo', '')) else 'libertadores'


def actualizar_claves(estado: dict) -> None:
    """
    v3.8.0: claves derivadas del motor que siguen leyendo otras pantallas (compatibilidad):
    copa_user_en_copa / copa_clasificado / copa_clasificado_motivo / copa_mejor_fase_temp / copa_campeon.
    """
    try:
        t = CP.tipo_copa_user(estado)
        estado['copa_user_en_copa'] = estado['copa_clasificado'] = bool(t)
        estado['copa_mejor_fase_temp'] = CP.fase_user(estado) if t else None
        estado['copa_campeon'] = CP.campeon(estado, t) if t else None
        if t:
            estado['copa_clasificado_motivo'] = f"Clasificado a la {CP.NOMBRE_COPA[t]}"
        elif not estado.get('copa_clasificado_motivo') or str(estado.get('copa_clasificado_motivo')).startswith("Clasificado"):
            estado['copa_clasificado_motivo'] = ("En 2ª división no se clasifica a copa."
                                                 if getattr(estado.get('liga'), 'division', 1) == 2
                                                 else "Tu club no está entre los clasificados de esta temporada.")
    except Exception as e:
        logger.error(f"Error al actualizar las claves de copa: {e}")


def cobrar_premios_copa(estado: dict) -> int:
    """
    v3.8.0: acredita al club del user los premios de cada fase alcanzada que aún no cobró esta
    temporada (se registran en finanzas como 'premios'). Devuelve lo cobrado en esta llamada.
    """
    try:
        t = CP.tipo_copa_user(estado)
        mi = estado.get('mi_equipo')
        if not t or mi is None:
            return 0
        temporada = int(estado.get('temporada', 1) or 1)
        dc = estado.setdefault('datos_carrera', {})
        reg = dc.get('premios_copa')
        if (not isinstance(reg, dict) or reg.get('temporada') != temporada or reg.get('tipo') != t
                or reg.get('club') != mi.nombre):
            reg = dc['premios_copa'] = {'temporada': temporada, 'tipo': t, 'club': mi.nombre,
                                        'fases': [], 'total': 0}
        fases = CP.FASES[t]
        alcanzada = CP.fase_user(estado)
        idx = fases.index(alcanzada) if alcanzada in fases else 0
        cobrado = 0
        for f in fases[:idx + 1]:
            if f in reg['fases']:
                continue
            monto = premio_fase(t, f)
            reg['fases'].append(f)
            reg['total'] = int(reg.get('total', 0)) + monto
            cobrado += monto
            try:   # v4.3.0: un correo por fase cobrada, con el % del premio total
                from alpha_football import correo as _C
                _C.enviar(estado, 'directiva', f"Premio de {CP.NOMBRE_COPA[t]}: {f}",
                          texto_premio(t, f, reg['total']), _C.accion('finanzas_screen', "VER FINANZAS"))
            except Exception as e_mail:
                logger.error(f"No se pudo enviar el correo del premio de copa: {e_mail}")
        if cobrado:
            mi.balance = int(getattr(mi, 'balance', 0) or 0) + cobrado
            try:
                from alpha_football.finanzas import registrar
                registrar(estado, 'premios', cobrado)
            except Exception as e_fin:
                logger.error(f"No se pudo registrar el premio de copa en finanzas: {e_fin}")
            logger.info(f"Premio de {CP.NOMBRE_COPA[t]} ({alcanzada}): ${cobrado:,}")
        try:   # v4.3.0: aviso de objetivo de copa cumplido en el momento
            from alpha_football.directiva import revisar_objetivo_copa_cumplido
            revisar_objetivo_copa_cumplido(estado)
            if alcanzada == 'Campeón':        # campeón de copa: si te negaron renovar, se disculpan
                from alpha_football.carrera_dt import revisar_renovacion_por_hito
                revisar_renovacion_por_hito(estado)
        except Exception as e_obj:
            logger.error(f"No se pudo revisar el objetivo de copa: {e_obj}")
        return cobrado
    except Exception as e:
        logger.error(f"Error al cobrar los premios de copa: {e}")
        return 0


def _migrar_claves_viejas(estado: dict) -> bool:
    """Borra el estado de la copa vieja. True si había una copa vieja en curso."""
    habia = any(estado.get(k) for k in _CLAVES_COPA_EN_CURSO)
    for k in CLAVES_VIEJAS:
        estado.pop(k, None)
    return habia


def sincronizar_copa_user(estado: dict) -> None:
    """
    v3.8.0: al entrar al hub (y cuando cambia la jornada): crea las copas de la temporada si
    faltan, juega las fechas vencidas de ambas (salvo el partido del user, que queda para JUGAR),
    actualiza las claves derivadas y cobra premios. Un save viejo con la copa vieja a mitad de
    temporada se regenera: las fechas ya pasadas se simulan, incluidas las del user.
    """
    try:
        if not estado.get('liga') or not estado.get('mi_equipo'):
            return
        temporada = int(estado.get('temporada', 1) or 1)
        existia = all((CP.copa(estado, t) or {}).get('temporada') == temporada for t in CP.N_FECHAS)
        vieja = _migrar_claves_viejas(estado)
        CP.avanzar(estado)
        if vieja and not existia:
            jornada = int(getattr(estado['liga'], 'jornada_actual', 1) or 1)
            rng = random.Random()
            for t in CP.N_FECHAS:
                try:
                    CP._avanzar_copa(estado, CP.copa(estado, t), rng, jornada, jugar_user=True)
                except Exception as e_mig:
                    logger.error(f"Error regenerando la {t} de un save viejo: {e_mig}")
            logger.info("Copa vieja migrada al motor v3.8.0 (fechas pasadas simuladas).")
        actualizar_claves(estado)
        cobrar_premios_copa(estado)
    except Exception as e:
        logger.error(f"Error en sincronizar_copa_user: {e}")


def simular_copa_fondo(estado: dict) -> None:
    """v3.8.0: hook de finalizar_jornada_liga: juega las fechas vencidas de las dos copas."""
    try:
        CP.avanzar(estado)
        actualizar_claves(estado)
        cobrar_premios_copa(estado)
    except Exception as e:
        logger.error(f"Error al simular las copas de fondo: {e}")


def avanzar_fase_bracket(estado: dict) -> None:
    """Compatibilidad (v0.8.x): el motor arma solo la fase siguiente; equivale a sincronizar."""
    simular_copa_fondo(estado)


def simular_copa_entera(estado: dict) -> None:
    """v3.8.0: termina las dos copas (fin de temporada o "simular resto" con el user fuera)."""
    try:
        CP.simular_todo(estado)
        actualizar_claves(estado)
        cobrar_premios_copa(estado)
    except Exception as e:
        logger.error(f"Error al simular las copas enteras: {e}")


def iniciar_copas_temporada(estado: dict, forzar: bool = False) -> None:
    """v3.8.0: sortea las dos copas de la temporada actual (alta de carrera / temporada nueva)."""
    try:
        for k in ('_copas_pool', '_copas_generados', '_hub_copa_sync', '_copa_premio_aviso'):
            estado.pop(k, None)
        CP.iniciar_temporada(estado, forzar=forzar)
        actualizar_claves(estado)
    except Exception as e:
        logger.error(f"Error al iniciar las copas de la temporada: {e}")


def etiqueta_partido(p: dict) -> str:
    """"Champions · Fase de liga F3" / "Libertadores · Octavos (vuelta)" / "Champions · Final"."""
    try:
        nombre = CP.NOMBRE_COPA.get(p.get('tipo'), 'Copa')
        fase = p.get('fase', '')
        if fase in ('Fase de liga', 'Fase de grupos'):
            return f"{nombre} · {fase} F{int(p.get('fecha', 0)) + 1}"
        if fase == 'Final':
            return f"{nombre} · Final"
        return f"{nombre} · {fase} ({'vuelta' if p.get('ida_de') else 'ida'})"
    except Exception:
        return "Copa"


def rival_copa_pendiente(estado: dict) -> tuple:
    """v3.8.0: (etiqueta de la fecha, rival) del partido de copa que toca ahora, o (None, None)."""
    try:
        pend = CP.partido_pendiente_user(estado)
        if not pend:
            return None, None
        mi = _mi_nombre(estado)
        rival = pend['visitante'] if pend['local'] == mi else pend['local']
        return etiqueta_partido(pend), rival
    except Exception as e:
        logger.error(f"Error en rival_copa_pendiente: {e}")
        return None, None


def preparar_partido_copa(estado: dict) -> bool:
    """
    v3.8.0: deja `estado` listo para prepartido_screen con el partido de copa pendiente
    (partido_copa_dict = copia del partido del motor, con 'id' y 'tipo'). False si no hay.
    """
    try:
        pend = CP.partido_pendiente_user(estado)
        if not pend:
            return False
        local = CP.equipo_por_nombre(estado, pend['local'])
        visitante = CP.equipo_por_nombre(estado, pend['visitante'])
        if local is None or visitante is None:
            logger.error(f"preparar_partido_copa: no se encontró un equipo ({pend['local']} vs {pend['visitante']}).")
            return False
        estado['match_mode'] = 'copa'
        estado['partido_actual'] = None
        estado['partido_local_obj'] = local
        estado['partido_visitante_obj'] = visitante
        estado.pop('sim_resultado', None)
        estado['partido_copa_dict'] = pend
        estado.pop('partido_copa_bracket_fase', None)
        return True
    except Exception as e:
        logger.error(f"Error en preparar_partido_copa: {e}")
        return False


def _ida_de(estado: dict, p: dict) -> Optional[dict]:
    c = CP.copa(estado, p.get('tipo')) if p.get('tipo') else None
    if not c or not p.get('ida_de'):
        return None
    return next((x for x in c['partidos'] if x.get('id') == p['ida_de']), None)


def necesita_penales(estado: dict, gl: int, gv: int) -> bool:
    """
    v3.8.0: ¿el partido de copa en juego (partido_copa_dict) se define por penales con este
    marcador? Final única empatada, o vuelta con el global empatado (sin gol de visitante).
    """
    try:
        p = estado.get('partido_copa_dict') or {}
        if p.get('fase') == 'Final':
            return int(gl) == int(gv)
        ida = _ida_de(estado, p)
        if ida and ida.get('jugado'):
            a_es_local_ahora = p.get('local') == ida.get('local')
            goles_a = int(ida.get('gl', 0) or 0) + int(gl if a_es_local_ahora else gv)
            goles_b = int(ida.get('gv', 0) or 0) + int(gv if a_es_local_ahora else gl)
            return goles_a == goles_b
        return False
    except Exception as e:
        logger.error(f"Error en necesita_penales: {e}")
        return False


def _marcador_a_tupla(marcador) -> Optional[tuple]:
    """'5-4' / (5, 4) → (5, 4)."""
    try:
        if isinstance(marcador, (list, tuple)) and len(marcador) == 2:
            return int(marcador[0]), int(marcador[1])
        a, b = str(marcador).replace(' ', '').split('-')[:2]
        return int(a), int(b)
    except Exception:
        return None


def registrar_resultado_copa(estado: dict, gl: int, gv: int, penales_user=None) -> None:
    """
    v3.8.0: guarda en el motor el resultado del partido de copa del user (partido_copa_dict).
    `penales_user`: (goles del user, goles del rival) o "X-Y" desde el punto de vista del user.
    """
    try:
        p = estado.get('partido_copa_dict')
        if not p or not p.get('id'):
            logger.error("registrar_resultado_copa: no hay partido de copa en juego")
            return
        pen = None
        tupla = _marcador_a_tupla(penales_user) if penales_user is not None else None
        if tupla is not None:
            pu, pr = tupla
            pen = {'a': pu, 'b': pr} if p.get('local') == _mi_nombre(estado) else {'a': pr, 'b': pu}
        CP.registrar_resultado_user(estado, p['id'], int(gl), int(gv), pen)
        actualizar_claves(estado)
        cobrar_premios_copa(estado)
    except Exception as e:
        logger.error(f"Error al registrar el resultado de copa: {e}")


def registrar_stats_copa(estado: dict, equipo_nombre: str, goles_contra: int, reporte: list) -> None:
    """v3.8.0: goles/asistencias/vallas del partido de copa del user → copa['stats'] del motor."""
    try:
        if not reporte or not isinstance(reporte, (list, tuple)):
            return
        t = (estado.get('partido_copa_dict') or {}).get('tipo') or CP.tipo_copa_user(estado)
        if t:
            CP.registrar_stats(estado, t, equipo_nombre, list(reporte), goles_contra)
    except Exception as e:
        logger.error(f"Error en registrar_stats_copa: {e}")


def desarrollo_copa(equipo, gf: int, gc: int, jugaron: Optional[list] = None,
                    stats_partido: Optional[dict] = None) -> list:
    """
    v3.8.0: desarrollo post-partido de un partido de copa sin tocar las estadísticas de LIGA
    (goles, asistencias, PJ y nota de copa van a copa['stats']; el Balón de Oro las suma aparte).
    """
    try:
        from alpha_football.desarrollo import desarrollar_plantilla_post_partido
        campos = CP._CAMPOS_LIGA
        previo = {id(j): tuple(getattr(j, k, 0) for k in campos) for j in getattr(equipo, 'jugadores', []) or []}
        reporte = desarrollar_plantilla_post_partido(equipo, gf, gc, jugaron, stats_partido=stats_partido)
        for j in getattr(equipo, 'jugadores', []) or []:
            if id(j) in previo:
                for k, v in zip(campos, previo[id(j)]):
                    setattr(j, k, v)
        return reporte or []
    except Exception as e:
        logger.error(f"Error en el desarrollo de copa de {getattr(equipo, 'nombre', '?')}: {e}")
        return []


def linea_copa_user(estado: dict) -> Optional[str]:
    """
    v3.8.0: texto corto del estado de la copa del user para Inicio (None si no la juega):
    "Copa · Champions · Octavos (ida) vs X (tras J12)" / "Copa: eliminado en Cuartos (Champions)" /
    "Copa: ¡CAMPEONES de la Champions!".
    """
    try:
        t = CP.tipo_copa_user(estado)
        if not t:
            return None
        nombre = CP.NOMBRE_COPA[t]
        linea = CP.linea_estado_user(estado)
        if linea.endswith("¡campeón!"):
            return f"Copa: ¡CAMPEONES de la {nombre}!"
        if " · subcampeón" in linea:
            return f"Copa: subcampeón de la {nombre}"
        if " · eliminado en " in linea:
            return f"Copa: eliminado en {linea.split(' · eliminado en ', 1)[1]} ({nombre})"
        c, mi = CP.copa(estado, t), _mi_nombre(estado)
        prox = next((p for p in sorted(c['partidos'], key=lambda x: x['fecha'])
                     if not p['jugado'] and mi in (p['local'], p['visitante'])), None)
        sufijo = ""
        if prox is not None and prox['fecha'] < len(c.get('fechas_jornada') or []):
            sufijo = f" (tras J{c['fechas_jornada'][prox['fecha']]})"
        return f"Copa · {linea}{sufijo}"
    except Exception as e:
        logger.error(f"Error en linea_copa_user: {e}")
        return None


# ════════════════════════════════════════════════════════════════════════════
# v3.8.0: dibujo (reutilizado por el hub y por OTRAS LIGAS)
# ════════════════════════════════════════════════════════════════════════════

_FUENTES: dict = {}
GRIS = (120, 130, 150)
FONDO_FILA_USER = (30, 45, 75)
FRANJAS = {'verde': (0, 200, 110), 'azul': (0, 150, 220), 'gris': (90, 96, 112)}


def _col(nombre, defecto=(255, 255, 255)):
    c = COLORS.get(nombre, defecto) if isinstance(nombre, str) else nombre
    return c if isinstance(c, (tuple, list)) else defecto


def _fuente(px: int):
    """Arial del tamaño pedido (cacheada); las tablas densas usan 13-16 px."""
    f = _FUENTES.get(px)
    if f is None:
        try:
            f = pygame.font.SysFont("arial", px)
        except Exception:
            f = pygame.font.Font(None, px + 4)
        _FUENTES[px] = f
    return f


def _recortar(fuente, texto: str, ancho: int) -> str:
    texto = str(texto)
    if ancho <= 0 or fuente.size(texto)[0] <= ancho:
        return texto
    while texto and fuente.size(texto + "…")[0] > ancho:
        texto = texto[:-1]
    return texto + "…"


def _txt(screen, texto, pos, px: int = 16, color='blanco', ancho: int = 0, ancla: str = 'topleft') -> None:
    try:
        f = _fuente(px)
        s = f.render(_recortar(f, texto, ancho), True, _col(color))
        screen.blit(s, s.get_rect(**{ancla: pos}))
    except Exception as e:
        logger.debug(f"_txt: {e}")


def _alto_fila(px: int) -> int:
    return _fuente(px).get_linesize()


def _mismo(n, user) -> bool:
    return bool(user) and n == user


def _partidos_etapa(c: dict, etiqueta: str) -> list:
    return [p for p in c.get('partidos', []) if p.get('fase') == etiqueta]


def tabla_fase_liga(c: dict) -> list:
    """Tabla de la fase de liga (Champions) con los partidos jugados hasta ahora."""
    return CP.tabla([x['nombre'] for x in c.get('clubes', [])], _partidos_etapa(c, 'Fase de liga'))


def tablas_grupos(c: dict) -> list:
    """Tablas de los 8 grupos (Libertadores)."""
    etapa = _partidos_etapa(c, 'Fase de grupos')
    return [CP.tabla(g, [p for p in etapa if p.get('grupo') == gi]) for gi, g in enumerate(c.get('grupos') or [])]


def grupo_de(c: dict, nombre: str) -> Optional[int]:
    for gi, g in enumerate(c.get('grupos') or []):
        if nombre in g:
            return gi
    return None


def dibujar_tabla_liga(screen, rect, c: dict, user: str, compacto: bool = False) -> None:
    """
    FASE DE LIGA: tabla de 36 en 2 columnas de 18, con franjas verde (1-8, octavos), azul (9-24,
    playoff) y gris (25-36, eliminados); tu club resaltado.
    """
    try:
        t = tabla_fase_liga(c)
        px = 14 if compacto else 16
        col_w = (rect.width - 12) // 2
        cab_h = _alto_fila(px) + 4
        fila_h = max(12, (rect.height - cab_h) // 18)
        if compacto:
            cols = [('#', 8), ('Club', 30), ('PJ', col_w - 92), ('DG', col_w - 62), ('PTS', col_w - 30)]
        else:
            cols = [('#', 10), ('Club', 40), ('PJ', col_w - 230), ('G', col_w - 195), ('E', col_w - 165),
                    ('P', col_w - 135), ('DG', col_w - 100), ('PTS', col_w - 50)]
        ancho_club = cols[2][1] - cols[1][1] - 6
        for k in range(2):
            x0 = rect.x + k * (col_w + 12)
            for h, dx in cols:
                _txt(screen, h, (x0 + dx, rect.y), px, 'dorado')
            for i, f in enumerate(t[k * 18:(k + 1) * 18]):
                pos = k * 18 + i + 1
                y = rect.y + cab_h + i * fila_h
                franja = FRANJAS['verde'] if pos <= 8 else (FRANJAS['azul'] if pos <= 24 else FRANJAS['gris'])
                if _mismo(f['nombre'], user):
                    pygame.draw.rect(screen, FONDO_FILA_USER, pygame.Rect(x0, y - 1, col_w, fila_h - 1), border_radius=3)
                pygame.draw.rect(screen, franja, pygame.Rect(x0, y, 4, fila_h - 3))
                color = 'dorado' if _mismo(f['nombre'], user) else ('blanco' if pos <= 24 else GRIS)
                dg = f['dif']
                vals = {'#': str(pos), 'Club': f['nombre'], 'PJ': str(f['pj']), 'G': str(f['g']),
                        'E': str(f['e']), 'P': str(f['p']), 'DG': f"+{dg}" if dg > 0 else str(dg),
                        'PTS': str(f['pts'])}
                for h, dx in cols:
                    _txt(screen, vals[h], (x0 + dx, y), px, color, ancho_club if h == 'Club' else 0)
    except Exception as e:
        logger.error(f"Error al dibujar la tabla de la fase de liga: {e}")


def dibujar_grupos(screen, rect, c: dict, user: str, compacto: bool = False, solo: Optional[int] = None) -> None:
    """GRUPOS: 8 mini-tablas 4×2 (o solo el grupo `solo`); pasan 1º y 2º (franja verde)."""
    try:
        tablas = tablas_grupos(c)
        indices = [solo] if solo is not None and 0 <= solo < len(tablas) else list(range(len(tablas)))
        px = 14 if compacto else 16
        ncol = 1 if len(indices) == 1 else 4
        nfil = 1 if len(indices) == 1 else 2
        w = (rect.width - (ncol - 1) * 10) // ncol
        h = (rect.height - (nfil - 1) * 10) // nfil
        for n, gi in enumerate(indices):
            caja = pygame.Rect(rect.x + (n % ncol) * (w + 10), rect.y + (n // ncol) * (h + 10), w, h)
            pygame.draw.rect(screen, (16, 22, 40), caja, border_radius=6)
            pygame.draw.rect(screen, _col('azul'), caja, width=1, border_radius=6)
            _txt(screen, f"GRUPO {chr(65 + gi)}", (caja.x + 8, caja.y + 4), px + 1, 'azul')
            cab_y = caja.y + 6 + _alto_fila(px + 1)
            for hd, dx in (('Club', 22), ('PJ', w - 92), ('DG', w - 62), ('PTS', w - 32)):
                _txt(screen, hd, (caja.x + dx, cab_y), px - 1, 'dorado')
            y_ini = cab_y + _alto_fila(px - 1) + 4
            fila_h = max(12, min(40, (caja.bottom - y_ini - 4) // 4))
            for i, f in enumerate(tablas[gi]):
                y = y_ini + i * fila_h
                if _mismo(f['nombre'], user):
                    pygame.draw.rect(screen, FONDO_FILA_USER, pygame.Rect(caja.x + 4, y - 1, w - 8, fila_h - 1), border_radius=3)
                pygame.draw.rect(screen, FRANJAS['verde'] if i < 2 else FRANJAS['gris'],
                                 pygame.Rect(caja.x + 6, y, 4, fila_h - 3))
                color = 'dorado' if _mismo(f['nombre'], user) else ('blanco' if i < 2 else GRIS)
                dg = f['dif']
                _txt(screen, f"{i + 1} {f['nombre']}", (caja.x + 14, y), px, color, w - 92 - 20)
                _txt(screen, str(f['pj']), (caja.x + w - 92, y), px, color)
                _txt(screen, f"+{dg}" if dg > 0 else str(dg), (caja.x + w - 62, y), px, color)
                _txt(screen, str(f['pts']), (caja.x + w - 32, y), px, color)
    except Exception as e:
        logger.error(f"Error al dibujar los grupos: {e}")


def global_llave(c: dict, ll: dict) -> tuple:
    """
    (goles de A, goles de B, penales (A, B) o None, jugado algo) de una llave. A = ll['a'] (el mejor
    clasificado, que cierra de local). Los penales del motor van como {'a': local, 'b': visitante}
    del partido decisivo; acá se devuelven desde A y B.
    """
    por_id = {p['id']: p for p in c.get('partidos', [])}
    ga = gb = 0
    jugado = False
    pen = None
    for pid in (ll.get('ida'), ll.get('vuelta')):
        p = por_id.get(pid) if pid else None
        if not p or not p.get('jugado'):
            continue
        jugado = True
        if p['local'] == ll['a']:
            ga += int(p.get('gl', 0) or 0); gb += int(p.get('gv', 0) or 0)
        else:
            ga += int(p.get('gv', 0) or 0); gb += int(p.get('gl', 0) or 0)
        pp = p.get('penales')
        if isinstance(pp, dict):
            pen = (pp.get('a', 0), pp.get('b', 0)) if p['local'] == ll['a'] else (pp.get('b', 0), pp.get('a', 0))
    return ga, gb, pen, jugado


def dibujar_llaves(screen, rect, c: dict, user: str, compacto: bool = False) -> None:
    """LLAVES: columnas playoff/octavos/cuartos/semis/final con el global y "(pen. a-b)"."""
    try:
        etapas = [e for e, _f in CP.ETAPAS[c['tipo']][1:]]
        px = 13 if compacto else 15
        n = len(etapas)
        col_w = (rect.width - (n - 1) * 8) // n
        titulo_h = _alto_fila(px + 1) + 4
        lh = _alto_fila(px)
        for k, etapa in enumerate(etapas):
            x0 = rect.x + k * (col_w + 8)
            _txt(screen, etapa.upper(), (x0 + col_w // 2, rect.y), px + 1, 'azul', ancla='midtop')
            llaves = [ll for ll in c.get('llaves', []) if ll.get('fase') == etapa]
            esperadas = {'Playoff': 8, 'Octavos': 8, 'Cuartos': 4, 'Semifinal': 2, 'Final': 1}.get(etapa, 1)
            paso = (rect.height - titulo_h) // esperadas
            caja_h = min(3 * lh + 6, paso - 6)
            for i in range(esperadas):
                y = rect.y + titulo_h + i * paso + (paso - caja_h) // 2
                caja = pygame.Rect(x0, y, col_w, caja_h)
                pygame.draw.rect(screen, (16, 22, 40), caja, border_radius=6)
                if i >= len(llaves):
                    pygame.draw.rect(screen, GRIS, caja, width=1, border_radius=6)
                    _txt(screen, "Por definir", caja.center, px, GRIS, ancla='center')
                    continue
                ll = llaves[i]
                es_user = user in (ll['a'], ll['b'])
                pygame.draw.rect(screen, _col('dorado') if es_user else _col('azul'), caja, width=1, border_radius=6)
                ga, gb, pen, jugado = global_llave(c, ll)
                cabe_pen = caja_h >= 3 * lh
                y1 = caja.y + 3 if (pen and cabe_pen) else caja.y + max(2, (caja_h - 2 * lh) // 2)
                ancho_nom = col_w - (96 if (pen and not cabe_pen) else 44)
                for j, (nom, g) in enumerate(((ll['a'], ga), (ll['b'], gb))):
                    gano = ll.get('ganador') == nom
                    color = ('dorado' if _mismo(nom, user) else
                             'verde' if gano else ('blanco' if not ll.get('ganador') else GRIS))
                    _txt(screen, nom, (caja.x + 6, y1 + j * lh), px, color, ancho_nom)
                    _txt(screen, str(g) if jugado else "-", (caja.right - 8, y1 + j * lh), px, color, ancla='topright')
                if pen and cabe_pen:
                    _txt(screen, f"(pen. {pen[0]}-{pen[1]})", (caja.right - 8, y1 + 2 * lh), px - 2,
                         'dorado', ancla='topright')
                elif pen:
                    _txt(screen, f"pen. {pen[0]}-{pen[1]}", (caja.right - 24, caja.centery), px - 3, 'dorado',
                         ancla='midright')
        if c.get('campeon'):
            y_c = rect.y + titulo_h + (rect.height - titulo_h) // 2 + 40
            _txt(screen, "CAMPEÓN", (rect.right - col_w // 2, y_c), px + 2, 'dorado', ancla='midtop')
            _txt(screen, c['campeon'], (rect.right - col_w // 2, y_c + _alto_fila(px + 2)), px + 2, 'dorado',
                 col_w, ancla='midtop')
    except Exception as e:
        logger.error(f"Error al dibujar las llaves: {e}")


def etiqueta_fecha(c: dict, i: int) -> str:
    """"Fase de liga · fecha 3/8" / "Octavos · ida" / "Final"."""
    for etapa, fechas in CP.ETAPAS[c['tipo']]:
        if i in fechas:
            if etapa in ('Fase de liga', 'Fase de grupos'):
                return f"{etapa} · fecha {fechas.index(i) + 1}/{len(fechas)}"
            if etapa == 'Final':
                return "Final"
            return f"{etapa} · {'ida' if fechas.index(i) == 0 else 'vuelta'}"
    return f"Fecha {i + 1}"


def fecha_por_defecto(c: dict) -> int:
    """La primera fecha con partidos sin jugar (o la última armada)."""
    pend = [p['fecha'] for p in c.get('partidos', []) if not p.get('jugado')]
    if pend:
        return min(pend)
    jug = [p['fecha'] for p in c.get('partidos', [])]
    return max(jug) if jug else 0


def dibujar_partidos(screen, rect, c: dict, user: str, fecha: int) -> None:
    """PARTIDOS de una fecha (2 columnas), tu partido resaltado y primero."""
    try:
        ps = [p for p in c.get('partidos', []) if p.get('fecha') == fecha]
        if not ps:
            _txt(screen, "Los cruces de esta fecha se arman cuando termina la fase anterior.",
                 (rect.centerx, rect.y + 60), 18, GRIS, ancla='midtop')
            return
        ps.sort(key=lambda p: (user not in (p['local'], p['visitante']), p.get('grupo', 0) or 0, p['id']))
        por_col = (len(ps) + 1) // 2
        col_w = (rect.width - 16) // 2
        fila_h = min(52, rect.height // max(1, por_col))
        px = 16
        for i, p in enumerate(ps):
            x0 = rect.x + (i // por_col) * (col_w + 16)
            y = rect.y + (i % por_col) * fila_h
            fila = pygame.Rect(x0, y, col_w, fila_h - 4)
            es_user = user in (p['local'], p['visitante'])
            pygame.draw.rect(screen, FONDO_FILA_USER if es_user else (16, 22, 40), fila, border_radius=5)
            if es_user:
                pygame.draw.rect(screen, _col('dorado'), fila, width=1, border_radius=5)
            cy = fila.centery
            if p.get('grupo') is not None:
                _txt(screen, chr(65 + int(p['grupo'])), (fila.x + 8, cy), px - 2, 'azul', ancla='midleft')
            if p.get('jugado'):
                gl, gv = int(p.get('gl', 0) or 0), int(p.get('gv', 0) or 0)
                marcador = f"{gl} - {gv}"
                c_l = 'verde' if gl > gv else ('rojo' if gl < gv else 'blanco')
                c_v = 'verde' if gv > gl else ('rojo' if gv < gl else 'blanco')
            else:
                marcador, c_l, c_v = "vs", 'blanco', 'blanco'
            c_l = 'dorado' if _mismo(p['local'], user) else c_l
            c_v = 'dorado' if _mismo(p['visitante'], user) else c_v
            mitad = col_w // 2
            _txt(screen, p['local'], (fila.x + mitad - 30, cy), px, c_l, mitad - 56, ancla='midright')
            _txt(screen, marcador, (fila.x + mitad, cy), px + 1, 'dorado', ancla='center')
            _txt(screen, p['visitante'], (fila.x + mitad + 30, cy), px, c_v, mitad - 56, ancla='midleft')
            pen = p.get('penales')
            if isinstance(pen, dict) and p.get('jugado'):
                _txt(screen, f"pen. {pen.get('a', 0)}-{pen.get('b', 0)}", (fila.x + mitad, fila.bottom),
                     12, 'dorado', ancla='midbottom')
    except Exception as e:
        logger.error(f"Error al dibujar los partidos de la copa: {e}")


def dibujar_estadisticas(screen, rect, c: dict, user: str) -> None:
    """ESTADÍSTICAS: top 10 goleadores, asistidores y vallas invictas (porteros) de la copa."""
    try:
        stats = list((c.get('stats') or {}).values())
        secciones = [("GOLEADORES", 'goles'), ("ASISTENCIAS", 'asist'), ("VALLAS INVICTAS", 'vallas')]
        col_w = (rect.width - 2 * 16) // 3
        px = 16
        lh = max(1, (rect.height - 34) // 10)
        for k, (titulo, clave) in enumerate(secciones):
            x0 = rect.x + k * (col_w + 16)
            _txt(screen, titulo, (x0, rect.y), 20, 'azul')
            cands = [s for s in stats if int(s.get(clave, 0) or 0) > 0
                     and (clave != 'vallas' or s.get('pos') == 'POR')]
            top = sorted(cands, key=lambda s: (-int(s.get(clave, 0) or 0), s.get('nombre', '')))[:10]
            if not top:
                _txt(screen, "Sin datos aún", (x0, rect.y + 34), px, GRIS)
            for i, s in enumerate(top):
                y = rect.y + 32 + i * lh
                es_user = _mismo(s.get('club'), user)
                if es_user:
                    pygame.draw.rect(screen, FONDO_FILA_USER, pygame.Rect(x0 - 4, y - 2, col_w, lh - 3), border_radius=4)
                color = 'dorado' if es_user else 'blanco'
                _txt(screen, f"{i + 1}. {s.get('nombre', '?')}", (x0, y), px, color, col_w - 50)
                _txt(screen, s.get('club', ''), (x0 + 20, y + _alto_fila(px) - 2), 13, GRIS, col_w - 60)
                _txt(screen, str(int(s.get(clave, 0) or 0)), (x0 + col_w - 10, y + 4), px + 2, 'verde',
                     ancla='topright')
    except Exception as e:
        logger.error(f"Error al dibujar las estadísticas de la copa: {e}")


def dibujar_resumen_copa(screen, rect, c: dict, user: str, compacto: bool = True) -> None:
    """Vista corta de una copa (hub / OTRAS LIGAS): llaves si ya empezaron, si no tabla o grupos."""
    if c.get('llaves'):
        dibujar_llaves(screen, rect, c, user, compacto)
    elif c.get('tipo') == 'champions':
        dibujar_tabla_liga(screen, rect, c, user, compacto)
    else:
        dibujar_grupos(screen, rect, c, user, compacto)


# ════════════════════════════════════════════════════════════════════════════
# v3.8.0: pantalla de copa
# ════════════════════════════════════════════════════════════════════════════

PESTANAS = ['liga_grupos', 'llaves', 'partidos', 'estadisticas']
R_SELECTOR_COPA = pygame.Rect(900, 22, 340, 40)      # clic = alterna CHAMPIONS / LIBERTADORES
R_CONTENIDO = pygame.Rect(40, 150, 1200, 486)        # termina en y=636
R_VOLVER = pygame.Rect(40, 646, 200, 42)             # termina en y=688 (barra de atajos en 698)
R_SIMULAR = pygame.Rect(1000, 646, 240, 42)
R_FECHA_ANT = pygame.Rect(40, 150, 44, 32)
R_FECHA_SIG = pygame.Rect(1196, 150, 44, 32)


def rect_pestana(clave: str) -> pygame.Rect:
    i = PESTANAS.index(clave) if clave in PESTANAS else 0
    return pygame.Rect(40 + i * 205, 100, 195, 38)


def _titulo_pestana(clave: str, tipo: str) -> str:
    return {'liga_grupos': "FASE DE LIGA" if tipo == 'champions' else "GRUPOS", 'llaves': "LLAVES",
            'partidos': "PARTIDOS", 'estadisticas': "ESTADÍSTICAS"}.get(clave, clave.upper())


def _user_vivo(estado: dict) -> bool:
    """¿El user todavía tiene partidos por jugar en su copa?"""
    t = CP.tipo_copa_user(estado)
    if not t:
        return False
    linea = CP.linea_estado_user(estado)
    return not (linea.endswith("¡campeón!") or " · subcampeón" in linea or " · eliminado en " in linea)


def _puede_simular_resto(estado: dict) -> bool:
    copas = [CP.copa(estado, t) for t in CP.N_FECHAS]
    return not _user_vivo(estado) and any(c and not c.get('campeon') for c in copas)


def render(screen, estado: dict) -> Optional[str]:
    """
    v3.8.0: pantalla de copa (solo consulta; el partido del user se juega desde JUGAR en Inicio).
    Retorna "volver" / "quit" o None.
    """
    try:
        user = _mi_nombre(estado)
        clave_sync = (estado.get('temporada'), getattr(estado.get('liga'), 'jornada_actual', 1))
        if estado.get('_copa_sync_clave') != clave_sync:        # una vez por jornada, no por frame
            sincronizar_copa_user(estado)
            estado['_copa_sync_clave'] = clave_sync
        tipo = estado.get('copa_vista')
        if tipo not in CP.N_FECHAS:
            tipo = estado['copa_vista'] = copa_de_region(estado)
        pestana = estado.get('copa_pestana') if estado.get('copa_pestana') in PESTANAS else 'liga_grupos'
        c = CP.copa(estado, tipo)
        fechas_sel = estado.setdefault('copa_fecha_sel', {})
        n_fechas = CP.N_FECHAS[tipo]
        fecha = fechas_sel.get(tipo)
        if not isinstance(fecha, int) or not 0 <= fecha < n_fechas:
            fecha = fecha_por_defecto(c) if c else 0
        puede_simular = _puede_simular_resto(estado)

        # --- Eventos ---
        mouse_pos = pygame.mouse.get_pos()
        click_pos = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    estado['hub_tab'] = 'oficina'   # v2.4.0: la copa se consulta desde OFICINA
                    return "volver"
                if event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                    pestana = PESTANAS[event.key - pygame.K_1]
                elif event.key == pygame.K_TAB:
                    pestana = PESTANAS[(PESTANAS.index(pestana) + 1) % len(PESTANAS)]
                elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    if pestana == 'partidos':
                        fecha = max(0, min(n_fechas - 1, fecha + (-1 if event.key == pygame.K_LEFT else 1)))
                    else:
                        paso = -1 if event.key == pygame.K_LEFT else 1
                        pestana = PESTANAS[(PESTANAS.index(pestana) + paso) % len(PESTANAS)]
                elif event.key == pygame.K_c:
                    tipo = 'libertadores' if tipo == 'champions' else 'champions'
                elif event.key == pygame.K_r and puede_simular:
                    simular_copa_entera(estado)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                click_pos = event.pos

        if click_pos:
            if R_VOLVER.collidepoint(click_pos):
                estado['hub_tab'] = 'oficina'
                return "volver"
            if R_SELECTOR_COPA.collidepoint(click_pos):
                tipo = 'libertadores' if tipo == 'champions' else 'champions'
            for clave in PESTANAS:
                if rect_pestana(clave).collidepoint(click_pos):
                    pestana = clave
            if pestana == 'partidos':
                if R_FECHA_ANT.collidepoint(click_pos):
                    fecha = max(0, fecha - 1)
                elif R_FECHA_SIG.collidepoint(click_pos):
                    fecha = min(n_fechas - 1, fecha + 1)
            if puede_simular and R_SIMULAR.collidepoint(click_pos):
                simular_copa_entera(estado)
        if tipo != estado.get('copa_vista'):
            estado['copa_vista'] = tipo
            c = CP.copa(estado, tipo)
            n_fechas = CP.N_FECHAS[tipo]
            fecha = fechas_sel.get(tipo) if isinstance(fechas_sel.get(tipo), int) else (fecha_por_defecto(c) if c else 0)
        else:
            fechas_sel[tipo] = fecha
        estado['copa_pestana'] = pestana
        puede_simular = _puede_simular_resto(estado)

        # --- Dibujo ---
        draw_gradient_bg(screen)
        nombre_largo = "CHAMPIONS LEAGUE" if tipo == 'champions' else "COPA LIBERTADORES"
        draw_text(screen, f"{nombre_largo} · T{estado.get('temporada', 1)}", (40, 16), size='xl', color='dorado')
        if c:
            fase = c.get('fase_actual', '')
            sub = f"Campeón: {c['campeon']}" if c.get('campeon') else f"En juego: {fase}"
            if CP.tipo_copa_user(estado) == tipo:
                sub += f"   ·   Tu club: {CP.linea_estado_user(estado).split(' · ', 1)[-1]}"
            elif user:
                sub += "   ·   Tu club no juega esta copa"
            _txt(screen, sub, (40, 70), 17, 'azul', 850)

        # selector CHAMPIONS / LIBERTADORES
        pygame.draw.rect(screen, (15, 22, 40), R_SELECTOR_COPA, border_radius=8)
        mitad = R_SELECTOR_COPA.width // 2
        for k, (t, etiqueta) in enumerate((('champions', "CHAMPIONS"), ('libertadores', "LIBERTADORES"))):
            r = pygame.Rect(R_SELECTOR_COPA.x + k * mitad, R_SELECTOR_COPA.y, mitad, R_SELECTOR_COPA.height)
            activo = t == tipo
            if activo:
                pygame.draw.rect(screen, _col('azul'), r.inflate(-6, -6), border_radius=6)
            _txt(screen, etiqueta, r.center, 17, 'bg' if activo else 'blanco', ancla='center')
        pygame.draw.rect(screen, _col('azul'), R_SELECTOR_COPA, width=1, border_radius=8)

        # pestañas
        for clave in PESTANAS:
            r = rect_pestana(clave)
            activa = clave == pestana
            hover = r.collidepoint(mouse_pos)
            pygame.draw.rect(screen, _col('azul') if activa else ((20, 26, 46) if hover else (10, 14, 26)), r,
                             border_radius=6)
            pygame.draw.rect(screen, _col('dorado') if activa else _col('azul'), r, width=1, border_radius=6)
            _txt(screen, f"{PESTANAS.index(clave) + 1} {_titulo_pestana(clave, tipo)}", r.center, 18,
                 'bg' if activa else 'blanco', ancla='center')

        draw_panel(screen, R_CONTENIDO.inflate(16, 12))
        cuerpo = R_CONTENIDO.inflate(-8, -8)
        if not c:
            _txt(screen, "La copa de esta temporada todavía no se sorteó.", cuerpo.center, 20, GRIS, ancla='center')
        elif pestana == 'liga_grupos':
            if tipo == 'champions':
                dibujar_tabla_liga(screen, cuerpo, c, user)
            else:
                dibujar_grupos(screen, cuerpo, c, user)
        elif pestana == 'llaves':
            dibujar_llaves(screen, cuerpo, c, user)
        elif pestana == 'partidos':
            fj = c.get('fechas_jornada') or []
            jornada = fj[fecha] if fecha < len(fj) else '?'
            for r, flecha, activo in ((R_FECHA_ANT, "<", fecha > 0), (R_FECHA_SIG, ">", fecha < n_fechas - 1)):
                pygame.draw.rect(screen, (20, 26, 46), r, border_radius=6)
                pygame.draw.rect(screen, _col('azul') if activo else GRIS, r, width=1, border_radius=6)
                _txt(screen, flecha, r.center, 20, 'blanco' if activo else GRIS, ancla='center')
            _txt(screen, f"FECHA {fecha + 1}/{n_fechas} · {etiqueta_fecha(c, fecha)} · se juega tras la jornada {jornada} de liga",
                 (R_CONTENIDO.centerx, R_FECHA_ANT.centery), 18, 'dorado', 1080, ancla='center')
            dibujar_partidos(screen, pygame.Rect(cuerpo.x, R_FECHA_ANT.bottom + 8, cuerpo.width,
                                                 cuerpo.bottom - R_FECHA_ANT.bottom - 8), c, user, fecha)
        else:
            dibujar_estadisticas(screen, cuerpo, c, user)

        # pie: volver, ayuda y simular resto
        draw_button(screen, R_VOLVER, "VOLVER", R_VOLVER.collidepoint(mouse_pos))
        if pestana == 'liga_grupos':
            pie = ("Verde 1-8: octavos · Azul 9-24: playoff · Gris 25-36: eliminados" if tipo == 'champions'
                   else "Pasan a octavos el 1º y el 2º de cada grupo")
        elif _user_vivo(estado):
            pie = "Tu partido de copa se juega desde JUGAR en Inicio."
        else:
            pie = "La copa se juega en paralelo a la liga, jornada a jornada."
        _txt(screen, pie, (620, R_VOLVER.centery), 16, 'azul', 700, ancla='center')
        if puede_simular:
            draw_button(screen, R_SIMULAR, "SIMULAR RESTO", R_SIMULAR.collidepoint(mouse_pos))
        return None
    except Exception as general_error:
        logger.error(f"Error general en copa_screen: {general_error}", exc_info=True)
        try:
            screen.fill((10, 20, 30))
            emerg_rect = pygame.Rect(490, 330, 300, 60)
            pygame.draw.rect(screen, (255, 0, 0), emerg_rect, border_radius=5)
            txt = pygame.font.Font(None, 24).render("ERROR EN COPA. CLIC PARA VOLVER", True, (255, 255, 255))
            screen.blit(txt, txt.get_rect(center=emerg_rect.center))
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and emerg_rect.collidepoint(event.pos):
                    return "volver"
        except Exception:
            return "volver"
    return None
