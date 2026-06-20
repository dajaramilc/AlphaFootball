# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Pantalla de la Copa (Pygame)
Muestra la fase de grupos (tabla de clasificación y partidos) y el bracket visual
de eliminación directa (Octavos, Cuartos, Semis, Final) con líneas conectoras y paneles.
"""

import sys
import os
import random
import logging
from typing import Optional  # Bug A: usado en la anotación de obtener_partido_copa_pendiente

logger = logging.getLogger(__name__)

# Intentar importar pygame de manera segura
try:
    import pygame
except ImportError as error_pygame:
    print(f"Error crítico al importar pygame en copa_screen: {error_pygame}. La UI no podrá renderizarse.", file=sys.stderr)
    raise error_pygame

# Importación resiliente del tema visual
try:
    from alpha_football.ui.theme import (
        SCREEN_W,
        SCREEN_H,
        COLORS,
        get_font,
        draw_gradient_bg,
        draw_panel,
        draw_button,
        draw_text
    )
except Exception as error_import_theme:
    print(f"Advertencia: No se pudo importar alpha_football.ui.theme ({error_import_theme}). Usando fallback local.", file=sys.stderr)
    
    # Fallback local para garantizar la continuidad del sistema
    SCREEN_W = 1280
    SCREEN_H = 720
    COLORS = {
        'bg': '#0A0E1A',
        'verde': '#00FF88',
        'dorado': '#FFD700',
        'rojo': '#FF4444',
        'azul': '#00BFFF',
        'blanco': '#FFFFFF',
        'panel': '#141A2E'
    }
    
    def get_font(size):
        try:
            if size == 'sm': return pygame.font.SysFont("Arial", 16)
            elif size == 'md': return pygame.font.SysFont("Arial", 20)
            elif size == 'lg': return pygame.font.SysFont("Arial", 28)
            elif size == 'xl': return pygame.font.SysFont("Arial", 42)
        except Exception:
            pass
        return pygame.font.Font(None, 24)
        
    def draw_gradient_bg(screen):
        screen.fill((10, 14, 26))
        
    def draw_panel(screen, rect):
        pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=8)
        pygame.draw.rect(screen, (0, 191, 255), rect, width=1, border_radius=8)
        
    def draw_button(screen, rect, text, hover):
        color_bg = (0, 191, 255) if hover else (20, 26, 46)
        color_fg = (10, 14, 26) if hover else (255, 255, 255)
        pygame.draw.rect(screen, color_bg, rect, border_radius=5)
        pygame.draw.rect(screen, (255, 255, 255), rect, width=1, border_radius=5)
        
        font = get_font('md')
        txt_surf = font.render(text, True, color_fg)
        txt_rect = txt_surf.get_rect(center=rect.center)
        screen.blit(txt_surf, txt_rect)
        return rect
        
    def draw_text(screen, text, pos, size='md', color='blanco', shadow=True):
        hex_color = COLORS.get(color, '#FFFFFF')
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        
        font = get_font(size)
        if shadow:
            shadow_surf = font.render(text, True, (0, 0, 0))
            screen.blit(shadow_surf, (pos[0] + 1, pos[1] + 1))
        txt_surf = font.render(text, True, (r, g, b))
        screen.blit(txt_surf, pos)

def obtener_equipos_de_liga(tipo_liga: str, estado: dict) -> list:
    """Obtiene de forma resiliente la lista de equipos de una liga."""
    if 'ligas' in estado:
        for l in estado['ligas']:
            l_tipo = l.tipo if hasattr(l, 'tipo') else l.get('tipo', '')
            if l_tipo == tipo_liga:
                l_equipos = l.equipos if hasattr(l, 'equipos') else l.get('equipos', [])
                res = []
                for eq in l_equipos:
                    if isinstance(eq, dict):
                        from alpha_football.models import Equipo
                        res.append(Equipo.from_dict(eq))
                    else:
                        res.append(eq)
                return res
    equipos_fresh = []
    try:
        if tipo_liga == 'premier':
            from alpha_football.data import premier
            equipos_fresh = premier.get_liga().equipos
        elif tipo_liga == 'laliga':
            from alpha_football.data import laliga
            equipos_fresh = laliga.get_liga().equipos
        elif tipo_liga == 'betplay':
            from alpha_football.data import betplay
            equipos_fresh = betplay.get_liga().equipos
        elif tipo_liga == 'brasil':
            from alpha_football.data import brasil
            equipos_fresh = brasil.get_liga().equipos
        elif tipo_liga == 'argentina':
            from alpha_football.data import argentina
            equipos_fresh = argentina.get_liga().equipos
    except Exception as e:
        logger.error(f"Error al cargar liga de datos para {tipo_liga}: {e}")
        return []
    # v0.8.8: estos equipos son copias frescas (NO la liga persistida del usuario), así
    # que aplicamos el envejecimiento pasivo por temporada de forma determinista para que
    # su rating en la copa refleje las temporadas transcurridas.
    try:
        anios = max(0, int(estado.get('temporada', 1)) - 1)
        if anios > 0 and equipos_fresh:
            from alpha_football.desarrollo import progresar_pasivo
            rng = random.Random(hash((tipo_liga, anios)) & 0xFFFFFFFF)
            for eq in equipos_fresh:
                progresar_pasivo(eq, anios, rng)
    except Exception as e_age:
        logger.error(f"Error al envejecer liga '{tipo_liga}' para copa: {e_age}")
    return equipos_fresh

def generar_fixture_grupo(t: list[str]) -> list[dict]:
    """Genera fixture a 3 jornadas para un grupo de 4 equipos."""
    return [
        {"jornada": 1, "local": t[0], "visitante": t[1], "goles_l": "-", "goles_v": "-", "jugado": False},
        {"jornada": 1, "local": t[2], "visitante": t[3], "goles_l": "-", "goles_v": "-", "jugado": False},
        {"jornada": 2, "local": t[3], "visitante": t[0], "goles_l": "-", "goles_v": "-", "jugado": False},
        {"jornada": 2, "local": t[1], "visitante": t[2], "goles_l": "-", "goles_v": "-", "jugado": False},
        {"jornada": 3, "local": t[0], "visitante": t[2], "goles_l": "-", "goles_v": "-", "jugado": False},
        {"jornada": 3, "local": t[3], "visitante": t[1], "goles_l": "-", "goles_v": "-", "jugado": False}
    ]

def obtener_partidos_fase(estado: dict, fase: str) -> list[dict]:
    """Retorna la lista completa de partidos para una fase de eliminación directa."""
    res = []
    try:
        mi_equipo = estado.get('mi_equipo')
        user_name = mi_equipo.nombre if mi_equipo else "Mi Club"
        b_dict = estado.get('copa_bracket', {})
        otros_dict = estado.get('copa_bracket_otros', {})
        
        fase_user = b_dict.get(fase, {})
        fase_otros = otros_dict.get(fase, [])
        
        user_participa = False
        if fase_user and isinstance(fase_user, dict):
            loc = fase_user.get('local', '')
            vis = fase_user.get('visitante', '')
            if loc and vis and (loc != '—' and vis != '—'):
                user_participa = True
                
        if fase == 'cuartos':
            candidatos = []
            if user_participa:
                candidatos.append(fase_user)
            candidatos.extend(fase_otros)
            
            # Ordenar para que sea consistente con la vista
            grupos = estado.get('copa_grupos', {})
            def idx_partido(m):
                loc, vis = m.get('local', ''), m.get('visitante', '')
                if loc in grupos.get('Grupo A', []) or vis in grupos.get('Grupo A', []):
                    if loc in grupos.get('Grupo A', []): return 0
                    else: return 1
                if loc in grupos.get('Grupo C', []) or vis in grupos.get('Grupo C', []):
                    if loc in grupos.get('Grupo C', []): return 2
                    else: return 3
                return 0
            try:
                res = sorted(candidatos, key=idx_partido)
            except Exception:
                res = candidatos
        elif fase == 'semis':
            candidatos = []
            if user_participa:
                candidatos.append(fase_user)
            candidatos.extend(fase_otros)
            res = candidatos
        elif fase == 'final':
            if user_participa:
                res = [fase_user]
            elif fase_otros:
                res = [fase_otros[0]]
    except Exception as e:
        logger.error(f"Error en obtener_partidos_fase: {e}")
    return res

def obtener_ganador_match(m, name_user):
    """Retorna el nombre real del equipo ganador de un partido del bracket."""
    if not m:
        return ""
    av = m.get('avanza')
    if av == 'user':
        return name_user
    elif av == 'rival':
        return m.get('rival', '')
    elif av: # Si es el nombre del equipo de la IA
        return av
    else:
        # Fallback al local si no se ha determinado
        return m.get('local', '')

def _fase_tiene_bracket_normalizado(estado: dict, fase: str) -> bool:
    """
    v0.8.2: comprueba si `copa_bracket[fase]` ya está en la forma plana
    {'local': str, 'visitante': str, 'goles_l': ..., 'goles_v': ..., 'jugado': bool, 'avanza': str|None, 'rival': str}
    (la que produce `avanzar_fase_bracket`). Devuelve True si es así.
    Si está en la forma placeholder {'m1': ..., 'm2': ...} (la de `inicializar_copa_si_falta`),
    devuelve False y el llamador debe invocar `avanzar_fase_bracket` para reconstruirla.
    """
    try:
        bd = estado.get('copa_bracket') or {}
        fdata = bd.get(fase)
        if not isinstance(fdata, dict):
            return False
        # Forma normalizada: tiene 'local' como string en la raíz
        if isinstance(fdata.get('local'), str):
            return True
        return False
    except Exception:
        return False


def obtener_match_usuario_bracket(estado: dict, fase: str) -> dict:
    """
    v0.8.2: devuelve el match de la fase del bracket en el que participa el usuario.
    Busca tanto en `copa_bracket[fase]` (forma normalizada) como en `copa_bracket_otros[fase]`
    (lista de los otros matches). Garantiza fallback a un dict vacío si no encuentra.
    """
    try:
        mi_equipo = estado.get('mi_equipo')
        name_user = getattr(mi_equipo, 'nombre', '') if mi_equipo else ''
        bd = estado.get('copa_bracket') or {}
        bo = estado.get('copa_bracket_otros') or {}
        # 1. Mirar primero en copa_bracket[fase]
        fdata = bd.get(fase) or {}
        if isinstance(fdata, dict) and isinstance(fdata.get('local'), str):
            if fdata.get('local') == name_user or fdata.get('visitante') == name_user:
                return fdata
        # 2. Si no, buscar en la lista de copa_bracket_otros[fase]
        for m in (bo.get(fase) or []):
            if isinstance(m, dict) and (m.get('local') == name_user or m.get('visitante') == name_user):
                return m
        # 3. Si el usuario juega esta fase pero no se encontró (bug de estado), devolver el primero normalizado
        if isinstance(fdata, dict) and isinstance(fdata.get('local'), str):
            return fdata
        for m in (bo.get(fase) or []):
            if isinstance(m, dict):
                return m
    except Exception:
        pass
    return {}


# ── v0.8.8: invariantes de integridad de la copa ──────────────────────────────
# Causa raíz de los bugs reportados: las fases se desbloqueaban por umbrales
# INDEPENDIENTES de jornada de liga, sin verificar que la fase anterior terminó
# realmente ni que el bracket estuviera bien sembrado. Estos helpers cierran eso.

_PLACEHOLDERS_EQUIPO = ('', '?', '—', '-')


def _equipo_valido(nombre) -> bool:
    """Un nombre de equipo es válido si es string real (no placeholder)."""
    return isinstance(nombre, str) and nombre.strip() not in _PLACEHOLDERS_EQUIPO


def _match_valido(m) -> bool:
    """Un cruce es válido si local/visitante son equipos reales y distintos."""
    if not isinstance(m, dict):
        return False
    loc, vis = m.get('local'), m.get('visitante')
    return _equipo_valido(loc) and _equipo_valido(vis) and loc != vis


def _grupos_completos(estado: dict) -> bool:
    """True si TODOS los partidos de la fase de grupos están jugados."""
    partidos = estado.get('copa_grupo_partidos') or []
    if not partidos:
        return False
    return all(p.get('jugado', False) for p in partidos)


def _bracket_fase_valida(estado: dict, fase: str) -> bool:
    """
    True si la fase del bracket está completamente sembrada: el match 'featured'
    (copa_bracket[fase]) y todos los de copa_bracket_otros[fase] tienen equipos
    reales y sin duplicados a lo largo de la fase.
    """
    bd = estado.get('copa_bracket') or {}
    bo = estado.get('copa_bracket_otros') or {}
    featured = bd.get(fase)
    otros = bo.get(fase) or []
    matches = []
    if isinstance(featured, dict) and isinstance(featured.get('local'), str):
        matches.append(featured)
    matches.extend(m for m in otros if isinstance(m, dict))
    if not matches:
        return False
    vistos = set()
    for m in matches:
        if not _match_valido(m):
            return False
        for nombre in (m.get('local'), m.get('visitante')):
            if nombre in vistos:
                return False  # equipo duplicado dentro de la fase
            vistos.add(nombre)
    return True


def _fase_completamente_jugada(estado: dict, fase: str) -> bool:
    """True si todos los cruces de la fase (featured + otros) están jugados con ganador."""
    bd = estado.get('copa_bracket') or {}
    bo = estado.get('copa_bracket_otros') or {}
    featured = bd.get(fase)
    otros = bo.get(fase) or []
    matches = []
    if isinstance(featured, dict) and isinstance(featured.get('local'), str):
        matches.append(featured)
    matches.extend(m for m in otros if isinstance(m, dict))
    if not matches:
        return False
    return all(
        m.get('jugado') and (m.get('avanza') not in (None, '', '?'))
        for m in matches
    )


def _fase_anterior_completa(estado: dict, fase: str) -> bool:
    """
    True si la fase previa a `fase` ya terminó (precondición para desbloquearla):
    cuartos -> grupos completos; semis -> cuartos (featured) jugado;
    final -> semis (featured) jugado. Para 'grupos' siempre True.
    """
    if fase == 'cuartos':
        return _grupos_completos(estado)
    bd = estado.get('copa_bracket') or {}
    if fase == 'semis':
        return bool((bd.get('cuartos') or {}).get('jugado'))
    if fase == 'final':
        return bool((bd.get('semis') or {}).get('jugado'))
    return True


def cargar_pools_internacionales(estado: dict, copa_tipo: str) -> list:
    """
    v0.8.8: devuelve los clubes internacionales (Champions o Libertadores) frescos,
    PREFIRIENDO la base de datos editada por el usuario (claves 'champions'/'libertadores'
    en alpha_football_edited_db.json, igual que menu.load_league_teams hace con las ligas).
    Aplica además el envejecimiento pasivo por temporada (determinista) para que el
    rating refleje la temporada actual sin inflar el guardado.
    """
    es_champions = (copa_tipo == 'Champions')
    clave_db = 'champions' if es_champions else 'libertadores'
    equipos = []
    # 1. Intentar desde la base editada
    try:
        import os
        import json
        ruta = "alpha_football_edited_db.json"
        if os.path.exists(ruta):
            with open(ruta, "r", encoding="utf-8") as f:
                db = json.load(f)
            if clave_db in db and db[clave_db]:
                from alpha_football.models import Equipo
                for d in db[clave_db]:
                    try:
                        equipos.append(Equipo.from_dict(d))
                    except Exception as e_eq:
                        logger.warning(f"No se pudo reconstruir club internacional editado: {e_eq}")
    except Exception as e_db:
        logger.error(f"Error al leer pools internacionales editados: {e_db}")
    # 2. Fallback a las plantillas por defecto (copias frescas)
    if not equipos:
        try:
            from alpha_football.data.internacional import get_pool_champions, get_pool_libertadores
            equipos = get_pool_champions() if es_champions else get_pool_libertadores()
        except Exception as e_pool:
            logger.error(f"Error al cargar pools internacionales por defecto: {e_pool}")
            equipos = []
    # 3. Envejecer pasivamente según la temporada (determinista por tipo+temporada)
    try:
        anios = max(0, int(estado.get('temporada', 1)) - 1)
        if anios > 0 and equipos:
            from alpha_football.desarrollo import progresar_pasivo
            rng = random.Random(hash((clave_db, anios)) & 0xFFFFFFFF)
            for eq in equipos:
                progresar_pasivo(eq, anios, rng)
    except Exception as e_age:
        logger.error(f"Error al envejecer pools internacionales: {e_age}")
    return equipos


def _asegurar_bracket_normalizado(estado: dict) -> None:
    """
    v0.8.2: si el estado de la copa está en una fase de eliminatorias y
    `copa_bracket[fase]` aún tiene la forma placeholder (m1/m2/m3/m4), invoca
    `avanzar_fase_bracket` para reconstruirla. Silencioso si falla.

    v0.8.7: si la fase actual es semis/final pero su bracket está en placeholder
    Y la fase previa (cuartos/semis) TAMBIÉN está en placeholder, hacemos
    backtrack hasta encontrar una fase con datos utilizables (o hasta 'grupos').
    Anti-bucle: si la bandera `_copa_bracket_normalizando` ya está puesta,
    salimos silenciosamente para cortar el bucle de logs del mismo frame.
    """
    try:
        if estado.get('_copa_bracket_normalizando'):
            return
        estado['_copa_bracket_normalizando'] = True
        try:
            fase = estado.get('copa_fase_actual', 'grupos')
            if fase not in ('cuartos', 'semis', 'final'):
                return
            if _fase_tiene_bracket_normalizado(estado, fase):
                return
            # Bracket de la fase actual está en placeholder. Hay que reconstruirlo
            # desde la fase previa más antigua que tenga datos o desde grupos.
            if fase == 'final':
                if not _fase_tiene_bracket_normalizado(estado, 'semis'):
                    estado['copa_fase_actual'] = 'cuartos'
                    if not _fase_tiene_bracket_normalizado(estado, 'cuartos'):
                        estado['copa_fase_actual'] = 'grupos'
            elif fase == 'semis':
                if not _fase_tiene_bracket_normalizado(estado, 'cuartos'):
                    estado['copa_fase_actual'] = 'grupos'
            elif fase == 'cuartos':
                estado['copa_fase_actual'] = 'grupos'
            logger.info(f"Reconstruyendo bracket para fase '{fase}' (estructura placeholder detectada).")
            avanzar_fase_bracket(estado)
        finally:
            estado['_copa_bracket_normalizando'] = False
    except Exception as e:
        logger.error(f"Error al normalizar bracket de copa: {e}")
        estado['_copa_bracket_normalizando'] = False


def avanzar_fase_bracket(estado: dict) -> None:
    """
    Construye las llaves de la siguiente fase del torneo de forma dinámica.
    - Si se pasa de grupos a cuartos: ordena las tablas de todos los grupos y crea los cruces de cuartos.
    - Si se pasa de cuartos a semis: simula los otros partidos de cuartos y crea semis.
    - Si se pasa de semis a final: simula los otros partidos de semis y crea la final.
    """
    try:
        mi_equipo = estado.get('mi_equipo')
        name_user = mi_equipo.nombre if mi_equipo else "Mi Club"
        fase_actual = estado.get('copa_fase_actual', 'grupos')
        
        # 1. De Grupos a Cuartos
        if fase_actual == 'grupos':
            # v0.8.8: NO sembrar cuartos si la fase de grupos no terminó del todo.
            # Esta es la causa raíz del bug "jugar cuartos sin simular los grupos":
            # antes se avanzaba mirando solo `fase_actual`, sin verificar los partidos.
            if not _grupos_completos(estado):
                logger.warning("avanzar_fase_bracket: grupos incompletos; no se siembra cuartos.")
                return
            recalcular_standings_copa(estado)
            grupos_st = estado.get('copa_grupos_standings', {})
            if not grupos_st:
                logger.warning("No se encontraron standings de copa para avanzar de fase.")
                return
                
            def get_top_2(standings):
                def key_fn(s):
                    if hasattr(s, 'pts'):
                        return (s.pts, s.gf - s.gc, s.gf)
                    else:
                        return (s.get('pts', 0), s.get('gf', 0) - s.get('gc', 0), s.get('gf', 0))
                sorted_s = sorted(standings, key=key_fn, reverse=True)
                return [s.equipo if hasattr(s, 'equipo') else s.get('equipo') for s in sorted_s[:2]]
                
            tops = {}
            for g_name, st_list in grupos_st.items():
                tops[g_name] = get_top_2(st_list)
                
            A1, A2 = tops.get('Grupo A', ['', ''])
            B1, B2 = tops.get('Grupo B', ['', ''])
            C1, C2 = tops.get('Grupo C', ['', ''])
            D1, D2 = tops.get('Grupo D', ['', ''])
            
            # Cruces de Cuartos:
            # Q1: A1 vs B2
            # Q2: B1 vs A2
            # Q3: C1 vs D2
            # Q4: D1 vs C2
            
            # Determinar en qué llave juega el usuario
            if name_user == A1:
                # El usuario juega Q1
                estado['copa_bracket']['cuartos'] = {
                    'local': name_user, 'visitante': B2, 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None, 'rival': B2
                }
                estado['copa_bracket_otros']['cuartos'] = [
                    {'local': B1, 'visitante': A2, 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None},
                    {'local': C1, 'visitante': D2, 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None},
                    {'local': D1, 'visitante': C2, 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None}
                ]
                estado['copa_fase_actual'] = 'cuartos'
            elif name_user == A2:
                # El usuario juega Q2
                estado['copa_bracket']['cuartos'] = {
                    'local': B1, 'visitante': name_user, 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None, 'rival': B1
                }
                estado['copa_bracket_otros']['cuartos'] = [
                    {'local': A1, 'visitante': B2, 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None},
                    {'local': C1, 'visitante': D2, 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None},
                    {'local': D1, 'visitante': C2, 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None}
                ]
                estado['copa_fase_actual'] = 'cuartos'
            else:
                # v0.8.7: distinguir entre "usuario eliminado en grupos" (estado
                # histórico) y "modo espectador, el user nunca estuvo en la copa".
                # En modo espectador NO marcamos 'eliminado' para que la copa
                # pueda avanzar a cuartos normalmente con la simulación.
                if estado.get('copa_user_en_copa', True):
                    estado['copa_fase_actual'] = 'eliminado'
                else:
                    estado['copa_fase_actual'] = 'cuartos'
                # Poblamos cuartos de todas formas para la simulación
                estado['copa_bracket']['cuartos'] = {
                    'local': A1, 'visitante': B2, 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None, 'rival': B2
                }
                estado['copa_bracket_otros']['cuartos'] = [
                    {'local': B1, 'visitante': A2, 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None},
                    {'local': C1, 'visitante': D2, 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None},
                    {'local': D1, 'visitante': C2, 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None}
                ]

        # 2. De Cuartos a Semis
        elif fase_actual == 'cuartos':
            simular_partidos_ia_bracket(estado, 'cuartos')

            q1 = estado['copa_bracket'].get('cuartos')
            # v0.8.7: defensivo — si el bracket de cuartos sigue en placeholder,
            # no podemos avanzar a semis. Salimos silenciosamente (la red de
            # seguridad `_asegurar_bracket_normalizado` lo intentará otra vez
            # desde una fase anterior).
            if not isinstance(q1, dict) or not isinstance(q1.get('local'), str) or not q1.get('local'):
                logger.warning("avanzar_fase_bracket(cuartos): bracket de cuartos inválido, saltando")
                return
            # v0.8.8: simular también el featured (si el user no lo juega) y exigir que
            # TODOS los cuartos estén jugados y válidos antes de sembrar semis. Así no se
            # propagan equipos '?'/vacíos hacia adelante (bug del bracket en espectador).
            _simular_featured_si_no_user(estado, 'cuartos')
            if not _bracket_fase_valida(estado, 'cuartos') or not _fase_completamente_jugada(estado, 'cuartos'):
                logger.warning("avanzar_fase_bracket(cuartos): cuartos incompletos/inválidos; no se siembran semis.")
                return
            q_otros = estado['copa_bracket_otros'].get('cuartos', [])
            grupos = estado.get('copa_grupos', {})
            
            # Reconstruir Q1, Q2, Q3, Q4
            # Si el usuario jugó Q1 (era local en copa_bracket['cuartos'])
            if q1['local'] == name_user:
                partido_q1 = q1
                partido_q2 = q_otros[0] if len(q_otros) > 0 else {'local': '?', 'visitante': '?', 'goles_l': '-', 'goles_v': '-', 'jugado': False}
            elif q1['visitante'] == name_user:
                partido_q1 = q_otros[0] if len(q_otros) > 0 else {'local': '?', 'visitante': '?', 'goles_l': '-', 'goles_v': '-', 'jugado': False}
                partido_q2 = q1
            else:
                partido_q1 = q1
                partido_q2 = q_otros[0] if len(q_otros) > 0 else {'local': '?', 'visitante': '?', 'goles_l': '-', 'goles_v': '-', 'jugado': False}
                
            partido_q3 = q_otros[1] if len(q_otros) > 1 else {'local': '?', 'visitante': '?', 'goles_l': '-', 'goles_v': '-', 'jugado': False}
            partido_q4 = q_otros[2] if len(q_otros) > 2 else {'local': '?', 'visitante': '?', 'goles_l': '-', 'goles_v': '-', 'jugado': False}
            
            win_q1 = obtener_ganador_match(partido_q1, name_user)
            win_q2 = obtener_ganador_match(partido_q2, name_user)
            win_q3 = obtener_ganador_match(partido_q3, name_user)
            win_q4 = obtener_ganador_match(partido_q4, name_user)
            
            # Semis:
            # S1: win_q1 vs win_q3
            # S2: win_q2 vs win_q4
            
            user_in_s1 = (win_q1 == name_user)
            user_in_s2 = (win_q2 == name_user)
            
            if user_in_s1:
                estado['copa_bracket']['semis'] = {
                    'local': name_user, 'visitante': win_q3, 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None, 'rival': win_q3
                }
                estado['copa_bracket_otros']['semis'] = [
                    {'local': win_q2, 'visitante': win_q4, 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None}
                ]
                estado['copa_fase_actual'] = 'semis'
            elif user_in_s2:
                estado['copa_bracket']['semis'] = {
                    'local': win_q4, 'visitante': name_user, 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None, 'rival': win_q4
                }
                estado['copa_bracket_otros']['semis'] = [
                    {'local': win_q1, 'visitante': win_q3, 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None}
                ]
                estado['copa_fase_actual'] = 'semis'
            else:
                # v0.8.7: si es modo espectador (user no en copa), avanzar a 'semis'
                # para que la simulación pueda continuar. Si no, marcar eliminado.
                if estado.get('copa_user_en_copa', True):
                    estado['copa_fase_actual'] = 'eliminado'
                else:
                    estado['copa_fase_actual'] = 'semis'
                estado['copa_bracket']['semis'] = {
                    'local': win_q1, 'visitante': win_q3, 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None, 'rival': win_q3
                }
                estado['copa_bracket_otros']['semis'] = [
                    {'local': win_q2, 'visitante': win_q4, 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None}
                ]

        # 3. De Semis a Final
        elif fase_actual == 'semis':
            simular_partidos_ia_bracket(estado, 'semis')

            s1 = estado['copa_bracket'].get('semis')
            # v0.8.7: defensivo — si el bracket de semis sigue en placeholder,
            # no podemos construir la final. Salimos silenciosamente.
            if not isinstance(s1, dict) or not isinstance(s1.get('local'), str) or not s1.get('local'):
                logger.warning("avanzar_fase_bracket(semis): bracket de semis inválido, saltando")
                return
            # v0.8.8: mismas garantías que en cuartos antes de construir la final.
            _simular_featured_si_no_user(estado, 'semis')
            if not _bracket_fase_valida(estado, 'semis') or not _fase_completamente_jugada(estado, 'semis'):
                logger.warning("avanzar_fase_bracket(semis): semis incompletas/inválidas; no se construye final.")
                return
            s_otros = estado['copa_bracket_otros'].get('semis', [])
            s2 = s_otros[0] if len(s_otros) > 0 else {'local': '?', 'visitante': '?', 'goles_l': '-', 'goles_v': '-', 'jugado': False}
            
            # Identificar S1 y S2
            user_was_s1 = True
            if s1['local'] == name_user or s1['visitante'] == name_user:
                if s1['local'] == name_user:
                    user_was_s1 = True
                else:
                    user_was_s1 = False
            else:
                user_was_s1 = True
                
            if user_was_s1:
                partido_s1 = s1
                partido_s2 = s2
            else:
                partido_s1 = s2
                partido_s2 = s1
                
            win_s1 = obtener_ganador_match(partido_s1, name_user)
            win_s2 = obtener_ganador_match(partido_s2, name_user)
            
            user_in_final = (win_s1 == name_user or win_s2 == name_user)
            
            if user_in_final:
                if win_s1 == name_user:
                    estado['copa_bracket']['final'] = {
                        'local': name_user, 'visitante': win_s2, 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None, 'rival': win_s2
                    }
                else:
                    estado['copa_bracket']['final'] = {
                        'local': win_s1, 'visitante': name_user, 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None, 'rival': win_s1
                    }
                estado['copa_bracket_otros']['final'] = []
                estado['copa_fase_actual'] = 'final'
            else:
                # v0.8.7: en modo espectador, el "else" aquí NO marca eliminado
                # (el user nunca estuvo en la copa). Avanza a 'final' para
                # que `simular_copa_entera_ia` pueda simularla.
                if estado.get('copa_user_en_copa', True):
                    estado['copa_fase_actual'] = 'eliminado'
                else:
                    estado['copa_fase_actual'] = 'final'
                estado['copa_bracket']['final'] = {
                    'local': win_s1, 'visitante': win_s2, 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None, 'rival': win_s2
                }
                estado['copa_bracket_otros']['final'] = []
    except Exception as e:
        logger.error(f"Error en avanzar_fase_bracket: {e}", exc_info=True)

def _simular_featured_si_no_user(estado: dict, fase: str) -> None:
    """
    v0.8.7: simula el partido 'featured' de la fase (`copa_bracket[fase]`) si
    el usuario NO participa en él. Por defecto `simular_partidos_ia_bracket`
    solo itera `copa_bracket_otros[fase]`, lo que deja sin simular el match
    que se quedó en el slot 'featured' cuando el user no clasificó (modo
    espectador) o fue eliminado en grupos. Esto lo arregla.
    """
    try:
        mi = estado.get('mi_equipo')
        name_user = getattr(mi, 'nombre', '') if mi else ''
        featured = estado.get('copa_bracket', {}).get(fase, {})
        if not isinstance(featured, dict) or not featured.get('local') or not featured.get('visitante'):
            return
        if featured.get('local') == name_user or featured.get('visitante') == name_user:
            return  # el user juega este; no tocar
        if featured.get('jugado'):
            return
        from alpha_football.engine import simular_partido
        from alpha_football.desarrollo import desarrollar_plantilla_post_partido
        loc_obj = encontrar_equipo_copa(featured['local'], estado)
        vis_obj = encontrar_equipo_copa(featured['visitante'], estado)
        if loc_obj is None or vis_obj is None:
            return
        res = simular_partido(loc_obj, vis_obj, con_eventos_caoticos=False)
        featured['goles_l'] = res.goles_local
        featured['goles_v'] = res.goles_visitante
        featured['jugado'] = True
        if res.goles_local == res.goles_visitante:
            gana_l = random.random() < 0.5
            featured['avanza'] = featured['local'] if gana_l else featured['visitante']
            featured['penales'] = '5-4' if gana_l else '4-5'
        else:
            featured['avanza'] = featured['local'] if res.goles_local > res.goles_visitante else featured['visitante']
        # Acumular stats
        try:
            rep_l = desarrollar_plantilla_post_partido(loc_obj, res.goles_local, res.goles_visitante)
            rep_v = desarrollar_plantilla_post_partido(vis_obj, res.goles_visitante, res.goles_local)
            registrar_stats_copa(estado, featured['local'], res.goles_visitante, rep_l)
            registrar_stats_copa(estado, featured['visitante'], res.goles_local, rep_v)
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Error en _simular_featured_si_no_user({fase}): {e}")


def _get_cup_state_str(estado: dict) -> str:
    """
    v0.8.7.2: devuelve una descripción corta de la fase actual de la copa
    para mostrarla en el panel 'NO CLASIFICADO'. Maneja fallback resiliente.
    """
    try:
        fase = estado.get('copa_fase_actual', 'grupos')
        if fase == 'grupos':
            jn = estado.get('copa_jornada_grupo', 1) or 1
            # Ver si la jornada ya está jugada
            partidos = estado.get('copa_grupo_partidos') or []
            jugados = sum(1 for p in partidos if p.get('jornada') == jn and p.get('jugado'))
            return f"Fase de grupos (J{jn} - {jugados} partidos jugados)"
        if fase == 'cuartos':
            return "Cuartos de final"
        if fase == 'semis':
            return "Semifinales"
        if fase == 'final':
            return "Final"
        if fase == 'campeon':
            camp = estado.get('copa_campeon', '')
            return f"Copa finalizada - Campeón: {camp}" if camp else "Copa finalizada"
        return str(fase).capitalize()
    except Exception as e:
        logger.error(f"Error en _get_cup_state_str: {e}")
        return "En progreso"


def simular_copa_fondo(estado: dict) -> None:
    """
    v0.8.7.2: avanza la copa en background cuando el user NO clasificó.
    Usa los MISMOS gates que la copa del user (J2 de liga = J1 de copa,
    30% = J2, 50% = J3, 70% = cuartos, 85% = semis, 100% = final).
    Si el cup está detrás del target, hace catch-up simulando los pasos
    necesarios en esta llamada. Es idempotente: 2 llamadas con la misma
    jornada_actual no simulan el doble.
    """
    try:
        if estado.get('copa_user_en_copa', True):
            return  # el user SÍ está en la copa, no tocar
        liga = estado.get('liga')
        if not liga:
            return

        jornada_actual = getattr(liga, 'jornada_actual', 1)
        num_jornadas = getattr(liga, 'num_jornadas', 10) or 10
        if jornada_actual < 2:
            return  # la copa no se desbloquea antes de J2 de liga

        # Mismos gates que copa_screen.py usa para la copa del user
        limites = {
            1: 2,
            2: max(3, int(num_jornadas * 0.3)),
            3: max(4, int(num_jornadas * 0.5)),
            'cuartos': max(6, int(num_jornadas * 0.7)),
            'semis': max(8, int(num_jornadas * 0.85)),
            'final': num_jornadas,
        }

        # Calcular el target según la jornada de liga actual
        if jornada_actual >= limites['final']:
            target = 'campeon'
        elif jornada_actual >= limites['semis']:
            target = 'semis'
        elif jornada_actual >= limites['cuartos']:
            target = 'cuartos'
        elif jornada_actual >= limites[3]:
            target = 'grupos_J3'
        elif jornada_actual >= limites[2]:
            target = 'grupos_J2'
        else:
            target = 'grupos_J1'

        fase_actual = estado.get('copa_fase_actual', 'grupos')
        if fase_actual == 'campeon':
            return  # ya terminó

        # --- Catch-up: simular hasta alcanzar el target ---

        # 1. GRUPOS
        if fase_actual == 'grupos':
            target_jn = {'grupos_J1': 1, 'grupos_J2': 2, 'grupos_J3': 3}.get(target, 0)
            for jn in (1, 2, 3):
                if jn > target_jn:
                    break
                # Solo simular si hay partidos pendientes en esa jornada
                partidos = estado.get('copa_grupo_partidos') or []
                pendientes = [p for p in partidos if p.get('jornada') == jn and not p.get('jugado')]
                if pendientes:
                    _autosimular_otros_grupo(estado, jn)
                    estado['copa_jornada_grupo'] = jn
            # Si target >= J3 y todos los grupos están jugados, avanzar a cuartos
            if target in ('grupos_J3', 'cuartos', 'semis', 'final', 'campeon'):
                todos = estado.get('copa_grupo_partidos') or []
                if todos and all(p.get('jugado', False) for p in todos):
                    if estado.get('copa_fase_actual', 'grupos') == 'grupos':
                        avanzar_fase_bracket(estado)

        # 2. CUARTOS
        fase_actual = estado.get('copa_fase_actual', 'grupos')
        if target in ('cuartos', 'semis', 'final', 'campeon') and fase_actual == 'cuartos':
            _simular_featured_si_no_user(estado, 'cuartos')
            simular_partidos_ia_bracket(estado, 'cuartos')
            avanzar_fase_bracket(estado)

        # 3. SEMIS
        fase_actual = estado.get('copa_fase_actual', 'grupos')
        if target in ('semis', 'final', 'campeon') and fase_actual == 'semis':
            _simular_featured_si_no_user(estado, 'semis')
            simular_partidos_ia_bracket(estado, 'semis')
            avanzar_fase_bracket(estado)

        # 4. FINAL
        fase_actual = estado.get('copa_fase_actual', 'grupos')
        if target in ('final', 'campeon') and fase_actual == 'final':
            _simular_featured_si_no_user(estado, 'final')
            simular_partidos_ia_bracket(estado, 'final')
            # Determinar campeón
            try:
                final_bracket = estado.get('copa_bracket', {}).get('final', {}) or {}
                otros_final = estado.get('copa_bracket_otros', {}).get('final', []) or []
                ganador = final_bracket.get('avanza')
                if not ganador and otros_final:
                    ganador = otros_final[0].get('avanza')
                if ganador:
                    estado['copa_campeon'] = ganador
                    estado['copa_fase_actual'] = 'campeon'
                    try:
                        import pygame
                        estado['copa_campeon_toast_until'] = pygame.time.get_ticks() + 6000
                    except Exception:
                        estado['copa_campeon_toast_until'] = None
                    logger.info(f"Copa finalizada en background. Campeón: {ganador}")
            except Exception as e_camp:
                logger.error(f"Error al setear campeón de copa en background: {e_camp}")
    except Exception as e:
        logger.error(f"Error en simular_copa_fondo: {e}")


def simular_copa_entera_ia(estado: dict) -> None:
    """
    v0.8.7: simula la copa completa de forma automática.
    Pensado para el modo espectador (cuando el usuario no clasificó), pero
    también sirve como utilidad general. Avanza por grupos → cuartos → semis
    → final y deja `copa_fase_actual = 'campeon'` con `copa_campeon` poblado.
    """
    try:
        # 1. Simular grupos
        if estado.get('copa_fase_actual') == 'grupos':
            for _jn in (1, 2, 3):
                _autosimular_otros_grupo(estado, _jn)
            # Forzar avance a cuartos (los grupos ya están todos jugados)
            if all(p.get('jugado', False) for p in (estado.get('copa_grupo_partidos') or [])):
                avanzar_fase_bracket(estado)

        # 2. Simular cuartos
        if estado.get('copa_fase_actual') == 'cuartos':
            _simular_featured_si_no_user(estado, 'cuartos')
            simular_partidos_ia_bracket(estado, 'cuartos')
            avanzar_fase_bracket(estado)

        # 3. Simular semis
        if estado.get('copa_fase_actual') == 'semis':
            _simular_featured_si_no_user(estado, 'semis')
            simular_partidos_ia_bracket(estado, 'semis')
            avanzar_fase_bracket(estado)

        # 4. Simular final
        if estado.get('copa_fase_actual') == 'final':
            _simular_featured_si_no_user(estado, 'final')
            simular_partidos_ia_bracket(estado, 'final')
            # Determinar el campeón: ganador de la final
            final = estado.get('copa_bracket', {}).get('final', {}) or {}
            otros_final = estado.get('copa_bracket_otros', {}).get('final', []) or []
            ganador = final.get('avanza')
            if not ganador and otros_final:
                ganador = otros_final[0].get('avanza')
            if ganador:
                estado['copa_campeon'] = ganador
                estado['copa_fase_actual'] = 'campeon'
                try:
                    import pygame
                    estado['copa_campeon_toast_until'] = pygame.time.get_ticks() + 6000
                except Exception:
                    estado['copa_campeon_toast_until'] = None
                logger.info(f"🏆 Copa finalizada en modo espectador. Campeón: {ganador}")
            else:
                logger.warning("No se pudo determinar el campeón de la copa en modo espectador.")
    except Exception as e:
        logger.error(f"Error en simular_copa_entera_ia: {e}")


def simular_partidos_ia_bracket(estado: dict, fase: str) -> None:
    """Simula de forma resiliente partidos del bracket en los que el usuario no participa."""
    try:
        from alpha_football.engine import simular_partido as eng_sim
        from alpha_football.desarrollo import desarrollar_plantilla_post_partido
        
        otros = estado.setdefault('copa_bracket_otros', {}).setdefault(fase, [])
        for m in otros:
            if m.get('jugado'):
                continue
            loc_name = m['local']
            vis_name = m['visitante']
            
            loc_obj = encontrar_equipo_copa(loc_name, estado)
            vis_obj = encontrar_equipo_copa(vis_name, estado)
            
            res = eng_sim(loc_obj, vis_obj, con_eventos_caoticos=False)
            m['goles_l'] = res.goles_local
            m['goles_v'] = res.goles_visitante
            m['jugado'] = True
            
            # v0.8.6 (Tarea 4): capturar reportes de desarrollo para acumular estadísticas de copa
            try:
                rep_l = desarrollar_plantilla_post_partido(loc_obj, res.goles_local, res.goles_visitante)
                rep_v = desarrollar_plantilla_post_partido(vis_obj, res.goles_visitante, res.goles_local)
                registrar_stats_copa(estado, loc_name, res.goles_visitante, rep_l)
                registrar_stats_copa(estado, vis_name, res.goles_local, rep_v)
            except Exception:
                pass
                
            if res.goles_local == res.goles_visitante:
                gana_l = random.random() < 0.5
                m['avanza'] = loc_name if gana_l else vis_name
                m['penales'] = '5-4' if gana_l else '4-5'
            else:
                m['avanza'] = loc_name if res.goles_local > res.goles_visitante else vis_name
    except Exception as e:
        logger.error(f"Error al simular partidos de IA en bracket ({fase}): {e}")

def simular_toda_la_copa_ia(estado: dict) -> None:
    """Simula de forma atómica y resiliente todo el resto de la Copa si el usuario ya no participa."""
    try:
        from alpha_football.engine import simular_partido as eng_sim
        
        # 1. Si está en grupos, avanzar a cuartos
        if estado.get('copa_fase_actual') == 'grupos':
            avanzar_fase_bracket(estado)
            
        # 2. Si está en cuartos, simular y avanzar a semis
        cuartos = obtener_partidos_fase(estado, 'cuartos')
        for m in cuartos:
            if not m.get('jugado'):
                loc = encontrar_equipo_copa(m['local'], estado)
                vis = encontrar_equipo_copa(m['visitante'], estado)
                res = eng_sim(loc, vis, con_eventos_caoticos=False)
                m['goles_l'] = res.goles_local
                m['goles_v'] = res.goles_visitante
                m['jugado'] = True
                if res.goles_local == res.goles_visitante:
                    m['avanza'] = m['local'] if random.random() < 0.5 else m['visitante']
                    m['penales'] = '5-4'
                else:
                    m['avanza'] = m['local'] if res.goles_local > res.goles_visitante else m['visitante']
                    
        # Construir semis
        sm1 = {'local': cuartos[0]['avanza'], 'visitante': cuartos[2]['avanza'], 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None}
        sm2 = {'local': cuartos[1]['avanza'], 'visitante': cuartos[3]['avanza'], 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None}
        estado.setdefault('copa_bracket_otros', {})['semis'] = [sm1, sm2]
            
        # Simular semis
        semis = obtener_partidos_fase(estado, 'semis')
        for m in semis:
            if not m.get('jugado'):
                loc = encontrar_equipo_copa(m['local'], estado)
                vis = encontrar_equipo_copa(m['visitante'], estado)
                res = eng_sim(loc, vis, con_eventos_caoticos=False)
                m['goles_l'] = res.goles_local
                m['goles_v'] = res.goles_visitante
                m['jugado'] = True
                if res.goles_local == res.goles_visitante:
                    m['avanza'] = m['local'] if random.random() < 0.5 else m['visitante']
                    m['penales'] = '5-4'
                else:
                    m['avanza'] = m['local'] if res.goles_local > res.goles_visitante else m['visitante']
                    
        # Construir final
        fn = {'local': semis[0]['avanza'], 'visitante': semis[1]['avanza'], 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None}
        estado['copa_bracket_otros']['final'] = [fn]
        
        # Simular final
        loc = encontrar_equipo_copa(fn['local'], estado)
        vis = encontrar_equipo_copa(fn['visitante'], estado)
        res = eng_sim(loc, vis, con_eventos_caoticos=False)
        fn['goles_l'] = res.goles_local
        fn['goles_v'] = res.goles_visitante
        fn['jugado'] = True
        if res.goles_local == res.goles_visitante:
            fn['avanza'] = fn['local'] if random.random() < 0.5 else fn['visitante']
            fn['penales'] = '5-4'
        else:
            fn['avanza'] = fn['local'] if res.goles_local > res.goles_visitante else fn['visitante']
            
        estado['copa_fase_actual'] = 'eliminado'
    except Exception as e:
        logger.error(f"Error al simular toda la copa IA: {e}")


def draw_bracket_node(screen: pygame.Surface, rect: pygame.Rect, titulo: str, partido: dict, name_user: str, estado: dict) -> None:
    """
    Dibuja un nodo del bracket de eliminación directa con el enfrentamiento y resultado.
    Resalta en dorado el partido del usuario y muestra el marcador si ya fue jugado.
    """
    try:
        # Panel de fondo del nodo
        draw_panel(screen, rect)

        # Verificar si el usuario participa en este partido
        loc = str(partido.get('local', '?'))
        vis = str(partido.get('visitante', '?'))
        jugado = partido.get('jugado', False)
        user_participa = (loc == name_user or vis == name_user)

        # Si el usuario participa, dibujar borde dorado especial para resaltarlo
        if user_participa:
            try:
                pygame.draw.rect(screen, (255, 215, 0), rect, width=2, border_radius=8)
            except Exception:
                # Fallback para versiones de pygame que no admiten border_radius en draw.rect
                pygame.draw.rect(screen, (255, 215, 0), rect, width=2)

        # Título del partido (ej. "Cuartos - Q1")
        draw_text(screen, titulo, (rect.x + 6, rect.y + 4), size='sm', color='azul')

        # Nombres de los equipos truncados para que quepan dentro del nodo
        loc_corto = loc[:16] if len(loc) > 16 else loc
        vis_corto = vis[:16] if len(vis) > 16 else vis

        # El equipo del usuario se muestra en verde para diferenciarlo
        col_loc = 'verde' if loc == name_user else 'blanco'
        col_vis = 'verde' if vis == name_user else 'blanco'

        draw_text(screen, loc_corto, (rect.x + 8, rect.y + 22), size='sm', color=col_loc)
        draw_text(screen, 'vs', (rect.x + rect.width // 2 - 8, rect.y + 22), size='sm', color='dorado')
        draw_text(screen, vis_corto, (rect.x + 8, rect.y + 38), size='sm', color=col_vis)

        # Si el partido ya se jugó, mostrar el marcador con color según resultado del usuario
        if jugado:
            goles_local = partido.get('goles_l', '-')
            goles_visitante = partido.get('goles_v', '-')
            marcador = f"{goles_local} - {goles_visitante}"

            # Agregar información de penales si el partido llegó a esa instancia
            penales = partido.get('penales', None)
            if penales:
                marcador += f" (P: {penales})"

            # Determinar el color del marcador según si el usuario avanzó o fue eliminado
            avanza = partido.get('avanza', None)
            if user_participa:
                if avanza == 'user' or avanza == name_user:
                    color_marcador = 'verde'   # El usuario ganó
                else:
                    color_marcador = 'rojo'    # El usuario perdió
            else:
                color_marcador = 'dorado'      # Partido entre equipos IA

            draw_text(screen, marcador, (rect.x + rect.width // 2 - 25, rect.y + 54), size='sm', color=color_marcador)
        else:
            # El partido aún no se ha disputado
            draw_text(screen, "Pendiente", (rect.x + 8, rect.y + 54), size='sm', color='blanco')

    except Exception as error_nodo:
        logger.error(f"Error al dibujar nodo del bracket '{titulo}': {error_nodo}")
        # Fallback: dibujar solo un rectángulo básico para no romper el renderizado
        try:
            pygame.draw.rect(screen, (20, 26, 46), rect)
            pygame.draw.rect(screen, (0, 191, 255), rect, width=1)
        except Exception:
            pass  # Si hasta el fallback falla, ignorar silenciosamente


def inicializar_copa_si_falta(estado: dict) -> None:
    """Inicializa la Copa en el estado con 4 grupos de 4 equipos (16 equipos total) de forma resiliente."""
    try:
        mi_equipo = estado.get('mi_equipo')
        liga = estado.get('liga')
        if not mi_equipo or not liga:
            return
            
        # Derivar SIEMPRE el tipo de copa de la liga actual: evita que se crucen datos
        # de Champions en Libertadores (y viceversa) por estado heredado.
        copa_tipo_correcto = 'Champions' if liga.tipo in ['premier', 'laliga'] else 'Libertadores'

        # Si ya hay una estructura válida del tipo correcto, no la pisamos.
        estructura_ok = (
            estado.get('copa_tipo') == copa_tipo_correcto
            and estado.get('copa_grupos')
            and estado.get('copa_grupos_standings')
            and estado.get('copa_bracket')  # v0.8.5: si falta el bracket, reconstruir todo (evita KeyError 'cuartos')
        )
        if estructura_ok:
            return

        # Estado ausente, incompleto o de otra copa: purgar TODO lo de copa y reconstruir limpio.
        for _k in ('copa_grupos', 'copa_grupos_standings', 'copa_grupo_standing',
                   'copa_grupo_partidos', 'copa_bracket', 'copa_bracket_otros',
                   'copa_fase_actual', 'copa_tab', 'copa_jornada_grupo',
                   'copa_campeon', 'copa_campeon_toast_until'):
            estado.pop(_k, None)
        estado['copa_tipo'] = copa_tipo_correcto
        copa_tipo = copa_tipo_correcto

        # v0.8.7: si el usuario no clasificó a esta edición, la copa se construye
        # SIN su equipo (modo espectador). El user podrá entrar a la pantalla de
        # copa para ver la simulación correr, pero no tendrá partidos pendientes.
        _user_clasificado = bool(estado.get('copa_clasificado', True))
        estado['copa_user_en_copa'] = _user_clasificado

        # 1. Seleccionar 16 equipos según el tipo de copa
        teams = []
        nombres_vistos = set()
        if _user_clasificado:
            teams.append(mi_equipo)
            nombres_vistos.add(mi_equipo.nombre)
        
        def _clasificados(equipos, n=3):
            # "Clasificados" = los mejores por puntos y, en empate, por OVR del plantel.
            elegibles = [e for e in equipos if e.nombre != mi_equipo.nombre]
            return sorted(elegibles, key=lambda e: (getattr(e, 'puntos', 0), getattr(e, 'ovr_promedio', 0)),
                          reverse=True)[:n]

        def _agregar(equipos):
            for e in equipos:
                if len(teams) >= 16:
                    break
                if e.nombre not in nombres_vistos:
                    nombres_vistos.add(e.nombre)
                    teams.append(e)

        if copa_tipo == 'Champions':
            # 3 clasificados de LaLiga + 3 de Premier; el resto, banco europeo (POOL_CHAMPIONS).
            _agregar(_clasificados(obtener_equipos_de_liga('laliga', estado)))
            _agregar(_clasificados(obtener_equipos_de_liga('premier', estado)))
            # v0.8.8: banco europeo con plantillas reales (y respetando edits del usuario).
            banco = [e for e in cargar_pools_internacionales(estado, 'Champions') if e.nombre != mi_equipo.nombre]
            random.shuffle(banco)
            _agregar(banco)
        else:
            # 3 clasificados de Brasil + 3 de Argentina; el resto, banco LATAM (BetPlay + pool real).
            _agregar(_clasificados(obtener_equipos_de_liga('brasil', estado)))
            _agregar(_clasificados(obtener_equipos_de_liga('argentina', estado)))
            banco = [e for e in obtener_equipos_de_liga('betplay', estado) if e.nombre != mi_equipo.nombre]
            banco += [e for e in cargar_pools_internacionales(estado, 'Libertadores') if e.nombre != mi_equipo.nombre]
            random.shuffle(banco)
            _agregar(banco)

        # Relleno extra si faltan
        if len(teams) < 16:
            from alpha_football.models import Equipo
            # v0.8.3: el relleno ficticio debe coincidir con el tipo de copa.
            # Champions = equipos europeos; Libertadores = equipos sudamericanos.
            if copa_tipo == 'Champions':
                ficticios = ["Ajax Legendario", "Celtic Ancestral", "Shakhtar de Donetsk",
                              "Salzburgo de la Montaña", "Brujas del Norte"]
            else:
                ficticios = ["Colo Colo Roto", "Penarol Roto", "Olimpia Abuelo",
                              "Bolivar Sin Aire", "Universitario de la U"]
            # v0.8.5: los rellenos DEBEN tener plantilla. Antes se creaban sin jugadores y la
            # autosimulación de la copa reventaba con "list index out of range" en el motor.
            try:
                from alpha_football.data.internacional import _generar_jugadores_equipo
            except Exception:
                _generar_jugadores_equipo = None
            _fill_id = 2000
            for f_name in ficticios:
                if len(teams) >= 16:
                    break
                if f_name not in nombres_vistos:
                    nombres_vistos.add(f_name)
                    _jug_fill = []
                    if _generar_jugadores_equipo is not None:
                        try:
                            _jug_fill = _generar_jugadores_equipo(72, _fill_id)
                            _fill_id += 50
                        except Exception:
                            _jug_fill = []
                    teams.append(Equipo(nombre=f_name, ciudad="Internacional", estrellas=3.5,
                                        estilo_dt="anchelottismo", balance=10000000, jugadores=_jug_fill))

        # v0.8.5: cachear los objetos Equipo participantes por nombre (tienen su plantilla real).
        # encontrar_equipo_copa los consulta PRIMERO; antes los equipos de otras ligas y los
        # rellenos no se encontraban y se devolvía un Equipo mock SIN jugadores -> IndexError.
        estado['copa_equipos_obj'] = {getattr(t, 'nombre', ''): t for t in teams if getattr(t, 'nombre', '')}

        # Distribuir en 4 grupos (mi_equipo en Grupo A)
        grupo_a = [teams[0].nombre]
        resto_nombres = [t.nombre for t in teams[1:]]
        random.shuffle(resto_nombres)
        grupo_a.extend(resto_nombres[:3])
        
        estado['copa_grupos'] = {
            'Grupo A': grupo_a,
            'Grupo B': resto_nombres[3:7],
            'Grupo C': resto_nombres[7:11],
            'Grupo D': resto_nombres[11:15]
        }
        
        # Inicializar standings y partidos
        from alpha_football.models import Standing
        grupos_standings = {}
        for g_name, g_teams in estado['copa_grupos'].items():
            grupos_standings[g_name] = [
                Standing(equipo=t_name, pj=0, g=0, e=0, p=0, gf=0, gc=0, pts=0)
                for t_name in g_teams
            ]
        estado['copa_grupos_standings'] = grupos_standings
        estado['copa_grupo_standing'] = grupos_standings['Grupo A']
        
        partidos = []
        for g_name, g_teams in estado['copa_grupos'].items():
            partidos.extend(generar_fixture_grupo(g_teams))
        estado['copa_grupo_partidos'] = partidos
        
        estado['copa_fase_actual'] = 'grupos'
        
        estado['copa_bracket'] = {
            'cuartos': {
                'm1': {'local': '', 'visitante': '', 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None},
                'm2': {'local': '', 'visitante': '', 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None},
                'm3': {'local': '', 'visitante': '', 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None},
                'm4': {'local': '', 'visitante': '', 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None}
            },
            'semis': {
                'm1': {'local': '', 'visitante': '', 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None},
                'm2': {'local': '', 'visitante': '', 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None}
            },
            'final': {
                'local': '', 'visitante': '', 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None
            }
        }
        estado.setdefault('copa_bracket_otros', {
            'cuartos': [],
            'semis': [],
            'final': []
        })
    except Exception as e:
        logger.error(f"Error al inicializar Copa de forma segura: {e}")

def obtener_partido_copa_pendiente(estado: dict) -> tuple[Optional[str], Optional[dict]]:
    """
    Determina si hay un partido de copa pendiente de jugar en la jornada de liga actual.
    Retorna (nombre_fase_o_jornada, partido_dict_o_bracket_dict) o (None, None).

    v0.8.7: si el usuario no clasificó a la copa (`copa_user_en_copa == False`,
    modo espectador), retorna (None, None) inmediatamente.
    """
    try:
        mi_equipo = estado.get('mi_equipo')
        liga = estado.get('liga')
        if not mi_equipo or not liga:
            return None, None

        # v0.8.7: en modo espectador el user no tiene partidos pendientes
        if estado.get('copa_user_en_copa') is False:
            return None, None

        inicializar_copa_si_falta(estado)
        
        jornada_actual = getattr(liga, "jornada_actual", 1)
        num_jornadas = getattr(liga, "num_jornadas", 10)
        fase_actual = estado.get('copa_fase_actual', 'grupos')
        
        limites = {
            'g1': 2,
            'g2': max(3, int(num_jornadas * 0.3)),
            'g3': max(4, int(num_jornadas * 0.5)),
            'cuartos': max(6, int(num_jornadas * 0.7)),
            'semis': max(8, int(num_jornadas * 0.85)),
            'final': num_jornadas
        }
        
        if fase_actual == 'grupos':
            # v0.8.1: usar .get() defensivo para no crashear si la copa aún no se inicializó
            # (por ejemplo, en el primer render antes de que inicializar_copa_si_falta termine).
            partidos_copa = estado.get('copa_grupo_partidos') or []
            if jornada_actual >= limites['g1']:
                p1 = next((p for p in partidos_copa if p['jornada'] == 1 and not p['jugado'] and (p['local'] == mi_equipo.nombre or p['visitante'] == mi_equipo.nombre)), None)
                if p1:
                    return "Copa Jornada 1", p1
            if jornada_actual >= limites['g2']:
                p2 = next((p for p in partidos_copa if p['jornada'] == 2 and not p['jugado'] and (p['local'] == mi_equipo.nombre or p['visitante'] == mi_equipo.nombre)), None)
                if p2:
                    return "Copa Jornada 2", p2
            if jornada_actual >= limites['g3']:
                p3 = next((p for p in partidos_copa if p['jornada'] == 3 and not p['jugado'] and (p['local'] == mi_equipo.nombre or p['visitante'] == mi_equipo.nombre)), None)
                if p3:
                    return "Copa Jornada 3", p3
                    
        elif fase_actual in ['cuartos', 'semis', 'final']:
            limite_fase = limites.get(fase_actual, 99)
            # v0.8.8: además del umbral de jornada, exigir que la fase ANTERIOR haya
            # terminado y que el bracket de esta fase esté bien sembrado. Sin esto se
            # podía jugar (p.ej.) cuartos sin haber completado los grupos.
            if (jornada_actual >= limite_fase
                    and _fase_anterior_completa(estado, fase_actual)
                    and _bracket_fase_valida(estado, fase_actual)):
                fase_data = estado['copa_bracket'].get(fase_actual)
                if fase_data and not fase_data.get('jugado'):
                    user_sigue_vivo = True
                    _bracket = estado.get('copa_bracket') or {}
                    if fase_actual == 'semis':
                        user_sigue_vivo = ((_bracket.get('cuartos') or {}).get('avanza') == 'user')
                    elif fase_actual == 'final':
                        user_sigue_vivo = ((_bracket.get('semis') or {}).get('avanza') == 'user')

                    if user_sigue_vivo:
                        return f"Copa {fase_actual.capitalize()}", fase_data
                        
        return None, None
    except Exception as e:
        print(f"Error al obtener partido de copa pendiente: {e}", file=sys.stderr)
        return None, None

def encontrar_equipo_copa(nombre_equipo: str, estado: dict):
    """Busca y devuelve el objeto Equipo correspondiente a un nombre en el estado o en los pools."""
    try:
        # v0.8.3: defensivo contra None o vacío
        if not nombre_equipo or not isinstance(nombre_equipo, str):
            return None

        # v0.8.5: PRIMERO el cache de equipos de la copa. Tienen su plantilla real, así que
        # evita devolver un mock vacío (equipos de otras ligas / rellenos) que rompía el motor.
        cache_copa = estado.get('copa_equipos_obj') or {}
        eq_cache = cache_copa.get(nombre_equipo)
        if eq_cache is not None and getattr(eq_cache, 'jugadores', None):
            return eq_cache

        # 1. Buscar en la liga actual del usuario
        if estado.get('liga'):
            for eq in estado['liga'].equipos:
                if eq.nombre == nombre_equipo:
                    return eq

        # 2. Buscar en pools internacionales
        from alpha_football.data.internacional import POOL_LIBERTADORES, POOL_CHAMPIONS
        for eq in POOL_LIBERTADORES:
            if eq.nombre == nombre_equipo:
                return eq
        for eq in POOL_CHAMPIONS:
            if eq.nombre == nombre_equipo:
                return eq

        # 3. Buscar en todas las ligas guardadas
        if 'ligas' in estado:
            for l in estado['ligas']:
                for eq in l.get('equipos', []):
                    if eq.nombre == nombre_equipo:
                        return eq

        # 4. Fallback si no existe
        from alpha_football.models import Equipo
        return Equipo(nombre=nombre_equipo, ciudad="Internacional", estrellas=3.5, estilo_dt="flickismo", balance=10000000)
    except Exception as e:
        print(f"Error al encontrar equipo '{nombre_equipo}': {e}. Retornando mock.", file=sys.stderr)
        from alpha_football.models import Equipo
        return Equipo(nombre=nombre_equipo, ciudad="Internacional", estrellas=3.5, estilo_dt="flickismo", balance=10000000)

def _corto_equipo(nombre: str, estado: dict) -> str:
    """Nombre corto de un equipo de copa (anti-solapamiento); recorta si no se encuentra."""
    try:
        eq = encontrar_equipo_copa(nombre, estado)
        return (getattr(eq, 'corto', None) or nombre)[:16]
    except Exception:
        return str(nombre)[:16]


def _autosimular_rivales(estado: dict) -> None:
    """
    v0.7: para que la tabla sea FIEL, autosimula el partido rival-vs-rival de cada
    jornada que el usuario YA jugó (antes ese partido quedaba sin jugar y la tabla
    no reflejaba todos los resultados).

    v0.8.3: blindado contra None/equipos faltantes — si un partido referencia un
    equipo que ya no existe en el estado (p.ej. por una limpieza de carrera), se
    salta con un warning en vez de crashear con TypeError/IndexError.
    """
    try:
        partidos = estado.get('copa_grupo_partidos') or []
        if not partidos:
            return
        mi = estado.get('mi_equipo')
        mi_nombre = getattr(mi, 'nombre', None) if mi else None
        if not mi_nombre:
            return
        jornadas_user = set()
        for p in partidos:
            if not isinstance(p, dict):
                continue
            if not p.get('jugado'):
                continue
            loc_p = p.get('local')
            vis_p = p.get('visitante')
            if not (loc_p and vis_p):
                continue
            if mi_nombre in (loc_p, vis_p):
                try:
                    jornadas_user.add(int(p.get('jornada', 0)))
                except (TypeError, ValueError):
                    continue
        if not jornadas_user:
            return
        from alpha_football.engine import simular_partido as eng_sim
        for p in partidos:
            if not isinstance(p, dict):
                continue
            if p.get('jugado'):
                continue
            try:
                jn = int(p.get('jornada', 0))
            except (TypeError, ValueError):
                continue
            if jn not in jornadas_user:
                continue
            loc_n = p.get('local')
            vis_n = p.get('visitante')
            if not (loc_n and vis_n):
                continue
            if mi_nombre in (loc_n, vis_n):
                continue
            loc = encontrar_equipo_copa(loc_n, estado)
            vis = encontrar_equipo_copa(vis_n, estado)
            if loc is None or vis is None:
                # No se puede simular si no encontramos los equipos. Saltar.
                continue
            try:
                res = eng_sim(loc, vis, con_eventos_caoticos=False)
            except Exception as e_sim:
                print(f"Error simulando partido {loc_n} vs {vis_n}: {e_sim}", file=sys.stderr)
                continue
            try:
                p['goles_l'] = int(getattr(res, 'goles_local', 0))
                p['goles_v'] = int(getattr(res, 'goles_visitante', 0))
                p['jugado'] = True
            except Exception:
                continue
            # v0.8.6 (Tarea 4): desarrollo + registro de estadísticas de copa para rivales autosimulados
            try:
                from alpha_football.desarrollo import desarrollar_plantilla_post_partido
                rep_l = desarrollar_plantilla_post_partido(loc, res.goles_local, res.goles_visitante)
                rep_v = desarrollar_plantilla_post_partido(vis, res.goles_visitante, res.goles_local)
                registrar_stats_copa(estado, loc_n, res.goles_visitante, rep_l)
                registrar_stats_copa(estado, vis_n, res.goles_local, rep_v)
            except Exception:
                pass
    except Exception as e:
        print(f"Error al autosimular rivales de copa: {e}", file=sys.stderr)


def _aplicar_resultado_st(st, gf: int, gc: int) -> None:
    """Suma un resultado a una fila de standing (objeto Standing o dict)."""
    if st is None:
        return
    if hasattr(st, 'pj'):
        st.pj += 1; st.gf += gf; st.gc += gc
        if gf > gc:
            st.g += 1; st.pts += 3
        elif gf < gc:
            st.p += 1
        else:
            st.e += 1; st.pts += 1
    else:
        st['pj'] += 1; st['gf'] += gf; st['gc'] += gc
        if gf > gc:
            st['g'] += 1; st['pts'] += 3
        elif gf < gc:
            st['p'] += 1
        else:
            st['e'] += 1; st['pts'] += 1


def recalcular_standings_copa(estado: dict) -> None:
    """
    Recalcula las tablas de TODOS los grupos de la Copa según los partidos jugados.
    (Antes solo recalculaba el Grupo A, por eso B/C/D nunca sumaban puntos.)
    """
    try:
        grupos_st = estado.get('copa_grupos_standings', {})
        partidos = estado.get('copa_grupo_partidos', [])

        if not grupos_st:
            # Compatibilidad con estructura antigua de un solo grupo.
            single = estado.get('copa_grupo_standing', [])
            if single:
                grupos_st = {'Grupo A': single}
            else:
                return

        # Reiniciar todas las filas y armar un mapa global equipo -> fila
        # (cada equipo pertenece a un solo grupo). NOTA: Standing.dg es property calculada.
        mapa_st = {}
        for _g, standings in grupos_st.items():
            for st in standings:
                if hasattr(st, 'pj'):
                    st.pj = st.g = st.e = st.p = st.gf = st.gc = st.pts = 0
                    mapa_st[st.equipo] = st
                else:
                    st['pj'] = st['g'] = st['e'] = st['p'] = st['gf'] = st['gc'] = st['pts'] = 0
                    mapa_st[st['equipo']] = st

        for p in partidos:
            if not p.get('jugado'):
                continue
            try:
                gl = int(p['goles_l'])
                gv = int(p['goles_v'])
            except (ValueError, TypeError):
                continue
            _aplicar_resultado_st(mapa_st.get(p['local']), gl, gv)
            _aplicar_resultado_st(mapa_st.get(p['visitante']), gv, gl)
    except Exception as e:
        print(f"Error en recalcular_standings_copa: {e}", file=sys.stderr)

def _autosimular_otros_grupo(estado: dict, jornada: Optional[int] = None) -> bool:
    """
    v0.8.5: simula AUTOMÁTICAMENTE los partidos de grupo pendientes en los que NO juega el
    usuario (antes había que pulsar "SIMULAR OTROS PARTIDOS"). Si `jornada` es None abarca todas;
    si se pasa, solo esa. Devuelve True si simuló algo. Resiliente: salta partidos no resolubles.
    """
    try:
        from alpha_football.engine import simular_partido as engine_simular
        from alpha_football.desarrollo import desarrollar_plantilla_post_partido
        mi = estado.get('mi_equipo')
        mi_nombre = getattr(mi, 'nombre', '') if mi else ''
        pendientes = [
            p for p in (estado.get('copa_grupo_partidos') or [])
            if not p.get('jugado') and p.get('local') and p.get('visitante')
            and mi_nombre not in (p.get('local'), p.get('visitante'))
            and (jornada is None or p.get('jornada') == jornada)
        ]
        if not pendientes:
            return False
        for p in pendientes:
            loc_obj = encontrar_equipo_copa(p['local'], estado)
            vis_obj = encontrar_equipo_copa(p['visitante'], estado)
            if loc_obj is None or vis_obj is None:
                continue
            try:
                res = engine_simular(loc_obj, vis_obj, con_eventos_caoticos=False)
                p['goles_l'] = int(getattr(res, 'goles_local', 0))
                p['goles_v'] = int(getattr(res, 'goles_visitante', 0))
                p['jugado'] = True
            except Exception as e_sim:
                print(f"Error simulando partido de copa {p.get('local')} vs {p.get('visitante')}: {e_sim}", file=sys.stderr)
                continue
            # v0.8.6 (Tarea 4): capturar reportes para acumular estadísticas de copa
            try:
                rep_l = desarrollar_plantilla_post_partido(loc_obj, res.goles_local, res.goles_visitante)
                rep_v = desarrollar_plantilla_post_partido(vis_obj, res.goles_visitante, res.goles_local)
                registrar_stats_copa(estado, p['local'], int(getattr(res, 'goles_visitante', 0)), rep_l)
                registrar_stats_copa(estado, p['visitante'], int(getattr(res, 'goles_local', 0)), rep_v)
            except Exception:
                pass
        recalcular_standings_copa(estado)
        return True
    except Exception as e:
        print(f"Error en _autosimular_otros_grupo: {e}", file=sys.stderr)
        return False


def registrar_stats_copa(estado: dict, equipo_nombre: str, goles_contra: int, reporte: list) -> None:
    """v0.8.6 (Tarea 4): acumula estadísticas de copa por jugador (goles, asist, porterías, notas)."""
    try:
        # Validar que el reporte sea iterable y no None
        if not reporte or not isinstance(reporte, (list, tuple)):
            return
        stats = estado.setdefault('copa_stats', {})
        for r in reporte:
            # Cada entrada del reporte es un dict con datos del jugador
            jid = str(r.get('id', ''))
            if not jid:
                continue
            # Inicializar la ficha del jugador si es la primera vez
            if jid not in stats:
                stats[jid] = {
                    'nombre': r.get('jugador', ''),
                    'equipo': equipo_nombre,
                    'pos': r.get('posicion', ''),
                    'goles': 0, 'asist': 0, 'porterias': 0,
                    'suma_notas': 0.0, 'pj': 0,
                }
            s = stats[jid]
            # Acumular goles, asistencias, notas y partidos jugados
            s['goles'] += r.get('goles', 0)
            s['asist'] += r.get('asistencias', 0)
            s['suma_notas'] += r.get('nota', 0.0)
            s['pj'] += 1
            # Portería a cero: si el equipo no recibió goles, los porteros suman
            if goles_contra == 0 and r.get('posicion') == 'POR':
                s['porterias'] += 1
    except Exception as e:
        logger.error(f"Error en registrar_stats_copa: {e}")


def render(screen, estado: dict) -> str | None:
    """
    Renderiza la pantalla de la Copa (Libertadores o Champions) en Pygame.
    Retorna la acción elegida ("volver", "jugar_partido", "simular_partido") o None.
    """
    try:
        # 1. Asegurar estado de la copa según la liga del usuario
        mi_equipo = estado.get('mi_equipo')
        liga = estado.get('liga')

        inicializar_copa_si_falta(estado)
        # v0.8.2: si el bracket aún no se reconstruyó para la fase actual (p. ej. el usuario
        # avanza de fase a cuartos pero nunca se llamó avanzar_fase_bracket), lo arreglamos
        # silenciosamente para que la UI no crashee.
        _asegurar_bracket_normalizado(estado)
        copa_tipo = estado['copa_tipo']

        # v0.8.7: si el modo espectador está activo, no autosimular nada todavía.
        # Se autosimulará cuando el user pulse el botón del overlay.
        # (Override del comportamiento por defecto que asume user en copa.)
        
        estado.setdefault('copa_tab', 'Grupo A')
        estado.setdefault('copa_jornada_grupo', 1)

        # v0.7: tabla FIEL — autosimular el rival de cada jornada ya jugada por el usuario y
        # recalcular la tabla SIEMPRE al entrar (no solo al completar todo el grupo).
        if estado.get('copa_fase_actual') == 'grupos':
            _autosimular_rivales(estado)

            recalcular_standings_copa(estado)

            # v0.8.6 (Tarea 3): avance automático de la jornada de copa. Tras jugar la jornada
            # del usuario en una jornada, al volver a la pantalla de Copa el selector
            # debe apuntar a la siguiente jornada pendiente y desbloqueada, sin que el
            # usuario tenga que pulsar Ant./Sig. a mano.
            try:
                mi = estado.get('mi_equipo')
                mi_nombre = getattr(mi, 'nombre', '') if mi else ''
                num_jornadas = getattr(liga, 'num_jornadas', 10) if liga else 10
                _limites = {
                    1: 2,
                    2: max(3, int(num_jornadas * 0.3)),
                    3: max(4, int(num_jornadas * 0.5)),
                }
                _jornada_actual = getattr(liga, 'jornada_actual', 1) if liga else 1
                _partidos = estado.get('copa_grupo_partidos') or []
                _objetivo = None
                for _jn in (1, 2, 3):
                    if _jornada_actual < _limites.get(_jn, 99):
                        # Esta jornada aún no está desbloqueada
                        continue
                    _pend_user = [
                        p for p in _partidos
                        if isinstance(p, dict) and p.get('jornada') == _jn and not p.get('jugado')
                        and p.get('local') and p.get('visitante')
                        and mi_nombre in (p.get('local'), p.get('visitante'))
                    ]
                    if _pend_user:
                        _objetivo = _jn
                        break
                if _objetivo is not None and estado.get('copa_jornada_grupo') != _objetivo:
                    estado['copa_jornada_grupo'] = _objetivo
            except Exception as _e_autoj:
                logger.error(f"Error en autoposicionamiento de jornada de copa: {_e_autoj}")

        # Verificar avance automático de la fase de grupos a eliminatorias
        if estado.get('copa_fase_actual') == 'grupos':
            todos_jugados = all(p.get('jugado', False) for p in estado['copa_grupo_partidos'])
            if todos_jugados:
                avanzar_fase_bracket(estado)
                estado['copa_tab'] = 'Fase Final'

        # Dibujar fondo base
        draw_gradient_bg(screen)

        # v0.8.3.4: hard guard contra None en copa_tipo / copa_fase_actual para
        # cortar el spam de "'NoneType' object has no attribute 'upper'".
        try:
            _tipo = str(copa_tipo) if copa_tipo else "COPA"
            titulo_copa = f"COPA {_tipo.upper()}"
        except Exception:
            titulo_copa = "COPA"
        draw_text(screen, titulo_copa, (40, 20), size='xl', color='dorado')

        try:
            _fase = estado.get('copa_fase_actual') or 'grupos'
            if _fase == 'grupos':
                sub_desc = "Fase de Grupos en progreso"
            else:
                sub_desc = f"Fase de Eliminación Directa — {str(_fase).upper()}"
        except Exception:
            sub_desc = "Copa Internacional"
        draw_text(screen, sub_desc, (40, 65), size='sm', color='azul')
        
        tab_names = ['Grupo A', 'Grupo B', 'Grupo C', 'Grupo D', 'Fase Final']
        tab_rects = {}
        tab_x = 40
        tab_y = 100
        tab_w = 130
        tab_h = 35
        
        mouse_pos = pygame.mouse.get_pos()
        tab_active = estado['copa_tab']
        
        for name in tab_names:
            rect = pygame.Rect(tab_x, tab_y, tab_w, tab_h)
            tab_rects[name] = rect
            
            is_active = (name == tab_active)
            is_hover = rect.collidepoint(mouse_pos)
            
            color_bg = (0, 191, 255) if is_active else ((20, 26, 46) if is_hover else (10, 14, 26))
            color_border = (255, 215, 0) if is_active else (0, 191, 255)
            color_txt = 'bg' if is_active else 'blanco'
            
            pygame.draw.rect(screen, color_bg, rect, border_radius=5)
            pygame.draw.rect(screen, color_border, rect, width=1, border_radius=5)
            
            font = get_font('md')
            txt_surf = font.render(name, True, COLORS.get(color_txt, (255, 255, 255)))
            txt_rect = txt_surf.get_rect(center=rect.center)
            screen.blit(txt_surf, txt_rect)
            
            tab_x += tab_w + 10

        if tab_active in ['Grupo A', 'Grupo B', 'Grupo C', 'Grupo D']:
            # --- PANEL IZQUIERDO: STANDINGS DEL GRUPO ---
            left_rect = pygame.Rect(40, 150, 600, 440)
            draw_panel(screen, left_rect)
            draw_text(screen, f"CLASIFICACIÓN — {tab_active.upper()}", (60, 165), size='md', color='azul')
            
            # Encabezados de tabla
            headers = ["#", "Equipo", "PJ", "G", "E", "P", "GF", "GC", "PTS"]
            header_x = [60, 100, 310, 350, 390, 430, 470, 510, 560]
            for h, x_pos in zip(headers, header_x):
                draw_text(screen, h, (x_pos, 205), size='sm', color='dorado')
                
            pygame.draw.line(screen, (0, 191, 255), (60, 225), (620, 225), 1)
            
            # Obtener standings ordenados para el grupo activo
            standings = estado['copa_grupos_standings'].get(tab_active, [])
            try:
                sorted_standings = sorted(standings, key=lambda s: (s.pts, s.gf - s.gc, s.gf), reverse=True)
            except Exception:
                sorted_standings = sorted(standings, key=lambda s: (s.get('pts',0), s.get('gf',0)-s.get('gc',0), s.get('gf',0)), reverse=True)
                
            y_pos = 235
            for i, st in enumerate(sorted_standings, 1):
                try:
                    eq_name = st.equipo if hasattr(st, 'equipo') else st.get('equipo', 'Equipo')
                    pj = st.pj if hasattr(st, 'pj') else st.get('pj', 0)
                    g = st.g if hasattr(st, 'g') else st.get('g', 0)
                    e = st.e if hasattr(st, 'e') else st.get('e', 0)
                    p = st.p if hasattr(st, 'p') else st.get('p', 0)
                    gf = st.gf if hasattr(st, 'gf') else st.get('gf', 0)
                    gc = st.gc if hasattr(st, 'gc') else st.get('gc', 0)
                    pts = st.pts if hasattr(st, 'pts') else st.get('pts', 0)
                except Exception:
                    eq_name, pj, g, e, p, gf, gc, pts = "Error", 0, 0, 0, 0, 0, 0, 0
                
                pos_color = 'verde' if i <= 2 else 'rojo'
                is_user = (mi_equipo and eq_name == mi_equipo.nombre)
                text_color = 'azul' if is_user else 'blanco'
                
                draw_text(screen, str(i), (60, y_pos), size='md', color=pos_color)
                draw_text(screen, _corto_equipo(eq_name, estado), (100, y_pos), size='md', color=text_color)
                draw_text(screen, str(pj), (310, y_pos), size='md', color='blanco')
                draw_text(screen, str(g), (350, y_pos), size='md', color='blanco')
                draw_text(screen, str(e), (390, y_pos), size='md', color='blanco')
                draw_text(screen, str(p), (430, y_pos), size='md', color='blanco')
                draw_text(screen, str(gf), (470, y_pos), size='md', color='blanco')
                draw_text(screen, str(gc), (510, y_pos), size='md', color='blanco')
                draw_text(screen, str(pts), (560, y_pos), size='md', color='dorado')
                
                y_pos += 45
            
            # --- PANEL DERECHO: PARTIDOS DEL GRUPO ---
            right_rect = pygame.Rect(660, 150, 580, 440)
            draw_panel(screen, right_rect)
            draw_text(screen, f"PARTIDOS — {tab_active.upper()}", (680, 165), size='md', color='azul')
            
            pygame.draw.line(screen, (0, 191, 255), (680, 195), (1220, 195), 1)
            
            # Controles de Jornada del grupo
            jornada_sel = estado['copa_jornada_grupo']
            btn_prev_j = pygame.Rect(680, 205, 110, 30)
            btn_next_j = pygame.Rect(1110, 205, 110, 30)
            
            prev_j_hover = btn_prev_j.collidepoint(mouse_pos)
            next_j_hover = btn_next_j.collidepoint(mouse_pos)
            
            if jornada_sel > 1:
                draw_button(screen, btn_prev_j, "Jornada Ant.", prev_j_hover)
            if jornada_sel < 3:
                draw_button(screen, btn_next_j, "Jornada Sig.", next_j_hover)
                
            draw_text(screen, f"Jornada {jornada_sel} de 3", (890, 210), size='md', color='dorado')
            
            # Listar partidos de la jornada seleccionada para este grupo
            teams_of_group = estado['copa_grupos'].get(tab_active, [])
            partidos_filtrados = [p for p in estado['copa_grupo_partidos'] if p['jornada'] == jornada_sel and p['local'] in teams_of_group]
            match_y = 260
            
            for m in partidos_filtrados:
                match_rect = pygame.Rect(680, match_y, 540, 70)
                draw_panel(screen, match_rect)
                
                es_del_usuario = (mi_equipo and (m['local'] == mi_equipo.nombre or m['visitante'] == mi_equipo.nombre))
                local_color = 'azul' if (mi_equipo and m['local'] == mi_equipo.nombre) else 'blanco'
                visitor_color = 'azul' if (mi_equipo and m['visitante'] == mi_equipo.nombre) else 'blanco'
                
                draw_text(screen, _corto_equipo(m['local'], estado), (700, match_y + 23), size='md', color=local_color)
                draw_text(screen, f"{m['goles_l']}", (880, match_y + 23), size='lg', color='dorado')
                draw_text(screen, "vs", (930, match_y + 23), size='md', color='blanco')
                draw_text(screen, f"{m['goles_v']}", (980, match_y + 23), size='lg', color='dorado')
                draw_text(screen, _corto_equipo(m['visitante'], estado), (1030, match_y + 23), size='md', color=visitor_color)
                
                match_y += 85

        else: # FASE FINAL (BRACKET)
            bracket_panel = pygame.Rect(40, 150, 1200, 440)
            draw_panel(screen, bracket_panel)
            
            draw_text(screen, "BRACKET DE ELIMINACIÓN DIRECTA", (60, 165), size='md', color='azul')
            
            box_w, box_h = 240, 70
            y_q1, y_q3, y_q2, y_q4 = 180, 270, 400, 490
            y_s1, y_s2 = 225, 445
            y_final = 335
            node_x = {'cuartos': 80, 'semis': 480, 'final': 880}
            
            pygame.draw.line(screen, (0, 191, 255), (node_x['cuartos'] + box_w, y_q1 + box_h//2), (node_x['semis'], y_s1 + box_h//2), 2)
            pygame.draw.line(screen, (0, 191, 255), (node_x['cuartos'] + box_w, y_q3 + box_h//2), (node_x['semis'], y_s1 + box_h//2), 2)
            pygame.draw.line(screen, (0, 191, 255), (node_x['cuartos'] + box_w, y_q2 + box_h//2), (node_x['semis'], y_s2 + box_h//2), 2)
            pygame.draw.line(screen, (0, 191, 255), (node_x['cuartos'] + box_w, y_q4 + box_h//2), (node_x['semis'], y_s2 + box_h//2), 2)
            pygame.draw.line(screen, (0, 191, 255), (node_x['semis'] + box_w, y_s1 + box_h//2), (node_x['final'], y_final + box_h//2), 2)
            pygame.draw.line(screen, (0, 191, 255), (node_x['semis'] + box_w, y_s2 + box_h//2), (node_x['final'], y_final + box_h//2), 2)
            
            name_user = mi_equipo.nombre if mi_equipo else "Mi Club"
            # v0.8.5: acceso defensivo. Si el bracket aún no tiene 'cuartos' (estado parcial / save
            # incompleto), antes reventaba con KeyError 'cuartos' cada frame (143× en el log).
            q_match = (estado.get('copa_bracket') or {}).get('cuartos') or {'local': '', 'visitante': '', 'goles_l': '-', 'goles_v': '-', 'jugado': False}
            q_otros = (estado.get('copa_bracket_otros') or {}).get('cuartos', [])
            
            if q_match.get('local') == name_user:
                partido_q1, partido_q2 = q_match, (q_otros[0] if len(q_otros) > 0 else {'local': '?', 'visitante': '?', 'goles_l': '-', 'goles_v': '-', 'jugado': False})
            elif q_match.get('visitante') == name_user:
                partido_q1, partido_q2 = (q_otros[0] if len(q_otros) > 0 else {'local': '?', 'visitante': '?', 'goles_l': '-', 'goles_v': '-', 'jugado': False}), q_match
            else:
                partido_q1, partido_q2 = q_match, (q_otros[0] if len(q_otros) > 0 else {'local': '?', 'visitante': '?', 'goles_l': '-', 'goles_v': '-', 'jugado': False})
                
            partido_q3 = q_otros[1] if len(q_otros) > 1 else {'local': '?', 'visitante': '?', 'goles_l': '-', 'goles_v': '-', 'jugado': False}
            partido_q4 = q_otros[2] if len(q_otros) > 2 else {'local': '?', 'visitante': '?', 'goles_l': '-', 'goles_v': '-', 'jugado': False}
            
            s_match = estado['copa_bracket'].get('semis', {'local': '', 'visitante': '', 'goles_l': '-', 'goles_v': '-', 'jugado': False})
            s_otros = estado['copa_bracket_otros'].get('semis', [])
            
            if s_match.get('local') == name_user or s_match.get('visitante') == name_user:
                if s_match.get('local') == name_user:
                    partido_s1, partido_s2 = s_match, (s_otros[0] if len(s_otros) > 0 else {'local': '?', 'visitante': '?', 'goles_l': '-', 'goles_v': '-', 'jugado': False})
                else:
                    partido_s1, partido_s2 = (s_otros[0] if len(s_otros) > 0 else {'local': '?', 'visitante': '?', 'goles_l': '-', 'goles_v': '-', 'jugado': False}), s_match
            else:
                partido_s1, partido_s2 = s_match, (s_otros[0] if len(s_otros) > 0 else {'local': '?', 'visitante': '?', 'goles_l': '-', 'goles_v': '-', 'jugado': False})
                
            partido_final = estado['copa_bracket'].get('final', {'local': '', 'visitante': '', 'goles_l': '-', 'goles_v': '-', 'jugado': False})
            
            draw_bracket_node(screen, pygame.Rect(node_x['cuartos'], y_q1, box_w, box_h), "Cuartos - Q1", partido_q1, name_user, estado)
            draw_bracket_node(screen, pygame.Rect(node_x['cuartos'], y_q3, box_w, box_h), "Cuartos - Q3", partido_q3, name_user, estado)
            draw_bracket_node(screen, pygame.Rect(node_x['cuartos'], y_q2, box_w, box_h), "Cuartos - Q2", partido_q2, name_user, estado)
            draw_bracket_node(screen, pygame.Rect(node_x['cuartos'], y_q4, box_w, box_h), "Cuartos - Q4", partido_q4, name_user, estado)
            
            draw_bracket_node(screen, pygame.Rect(node_x['semis'], y_s1, box_w, box_h), "Semifinal - S1", partido_s1, name_user, estado)
            draw_bracket_node(screen, pygame.Rect(node_x['semis'], y_s2, box_w, box_h), "Semifinal - S2", partido_s2, name_user, estado)
            
            draw_bracket_node(screen, pygame.Rect(node_x['final'], y_final, box_w, box_h), "Gran Final", partido_final, name_user, estado)
            
            if partido_final.get('jugado'):
                campeon_camino = obtener_ganador_match(partido_final, name_user)
                draw_text(screen, f"¡CAMPEÓN: {campeon_camino.upper()}!", (node_x['final'] + 10, y_final + 95), size='sm', color='dorado')

        # v0.8.6 (Tarea 4): botón de estadísticas de copa
        stats_btn_rect = pygame.Rect(1040, 20, 200, 40)
        stats_btn_hover = stats_btn_rect.collidepoint(mouse_pos)
        draw_button(screen, stats_btn_rect, "📊 ESTADÍSTICAS", stats_btn_hover)

        # v0.8.6 (Tarea 4): overlay de estadísticas de copa cuando está abierto
        overlay_consumio_click = False
        if estado.get('copa_stats_abierto'):
            try:
                # Dibujar fondo semi-transparente para el overlay
                overlay_bg = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
                overlay_bg.fill((0, 0, 0, 160))
                screen.blit(overlay_bg, (0, 0))

                # Panel principal del overlay de estadísticas
                panel_x, panel_y, panel_w, panel_h = 80, 40, 1120, 620
                panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
                draw_panel(screen, panel_rect)
                draw_text(screen, "ESTADÍSTICAS DE COPA", (panel_x + 20, panel_y + 10), size='lg', color='dorado')

                # Botón CERRAR dentro del overlay
                cerrar_rect = pygame.Rect(panel_x + panel_w - 120, panel_y + 10, 100, 30)
                cerrar_hover = cerrar_rect.collidepoint(mouse_pos)
                draw_button(screen, cerrar_rect, "CERRAR", cerrar_hover)

                # Obtener datos de estadísticas acumuladas
                copa_stats = estado.get('copa_stats', {})
                lista_stats = list(copa_stats.values())

                # Definir las 4 secciones de estadísticas
                secciones = [
                    ('⚽ GOLEADORES', 'goles', lambda s: s.get('goles', 0)),
                    ('🅰️ ASISTENTES', 'asist', lambda s: s.get('asist', 0)),
                    ('🧤 PORTERÍAS A CERO', 'porterias', lambda s: s.get('porterias', 0)),
                    ('⭐ RENDIMIENTO', 'rendimiento', lambda s: (s.get('suma_notas', 0) / s.get('pj', 1)) if s.get('pj', 0) >= 1 else 0),
                ]

                # Calcular posiciones de las columnas (2 columnas × 2 filas)
                col_w = (panel_w - 60) // 2
                posiciones = [
                    (panel_x + 20, panel_y + 55),
                    (panel_x + 20 + col_w + 20, panel_y + 55),
                    (panel_x + 20, panel_y + 340),
                    (panel_x + 20 + col_w + 20, panel_y + 340),
                ]

                for idx_sec, (titulo_sec, clave_sec, fn_sort) in enumerate(secciones):
                    sx, sy = posiciones[idx_sec]
                    draw_text(screen, titulo_sec, (sx, sy), size='md', color='azul')

                    # Ordenar jugadores por la métrica de esta sección (descendente)
                    if clave_sec == 'rendimiento':
                        # Solo jugadores con al menos 1 partido jugado
                        candidatos = [s for s in lista_stats if s.get('pj', 0) >= 1]
                    else:
                        candidatos = [s for s in lista_stats if fn_sort(s) > 0]
                    top_jugadores = sorted(candidatos, key=fn_sort, reverse=True)[:8]

                    fila_y = sy + 28
                    # Encabezados de la mini-tabla
                    draw_text(screen, "Jugador", (sx, fila_y), size='sm', color='dorado')
                    draw_text(screen, "Equipo", (sx + 220, fila_y), size='sm', color='dorado')
                    valor_label = 'Nota' if clave_sec == 'rendimiento' else clave_sec.capitalize()
                    draw_text(screen, valor_label, (sx + 420, fila_y), size='sm', color='dorado')
                    fila_y += 22

                    # Filas de datos
                    for j_stat in top_jugadores:
                        nombre_jug = str(j_stat.get('nombre', ''))[:22]
                        equipo_jug = str(j_stat.get('equipo', ''))[:18]
                        if clave_sec == 'rendimiento':
                            pj_val = j_stat.get('pj', 1)
                            promedio = j_stat.get('suma_notas', 0) / max(pj_val, 1)
                            valor_str = f"{promedio:.1f}"
                        else:
                            valor_str = str(int(fn_sort(j_stat)))
                        draw_text(screen, nombre_jug, (sx, fila_y), size='sm', color='blanco')
                        draw_text(screen, equipo_jug, (sx + 220, fila_y), size='sm', color='blanco')
                        draw_text(screen, valor_str, (sx + 420, fila_y), size='sm', color='verde')
                        fila_y += 22

                    # Si no hay datos aún, mostrar mensaje informativo
                    if not top_jugadores:
                        draw_text(screen, "Sin datos aún", (sx, fila_y), size='sm', color='rojo')

                overlay_consumio_click = True
            except Exception as e_stats_overlay:
                logger.error(f"Error al dibujar overlay de estadísticas de copa: {e_stats_overlay}")

        # v0.8.7.2: overlay de "NO CLASIFICADO" (cuando el user no clasificó a la copa).
        # Aparece ENCIMA del fondo de copa, debajo de las stats. Solo se muestra si
        # la copa todavía no terminó y el user aún no la ha descartado en esta sesión.
        # La copa avanza en background via simular_copa_fondo() en finalizar_jornada_liga.
        _spectator_open = False
        if not estado.get('copa_user_en_copa', True) and not estado.get('_spectator_dismissed', False):
            _fase_now = estado.get('copa_fase_actual', 'grupos')
            if _fase_now in ('grupos', 'cuartos', 'semis', 'final'):
                _spectator_open = True
        if _spectator_open:
            try:
                # Fondo semi-transparente
                overlay_bg = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
                overlay_bg.fill((0, 0, 0, 150))
                screen.blit(overlay_bg, (0, 0))
                # Panel central
                _sp_rect = pygame.Rect(SCREEN_W // 2 - 380, 180, 760, 380)
                draw_panel(screen, _sp_rect)
                pygame.draw.rect(screen, COLORS.get('rojo', (255, 68, 68)), _sp_rect, width=3, border_radius=8)
                # Título
                draw_text(screen, "NO CLASIFICADO", (_sp_rect.x + _sp_rect.w // 2 - 140, _sp_rect.y + 30),
                          size='xl', color='rojo')
                # Subtítulo
                draw_text(screen, "Tu equipo no participa en esta edición de la copa.",
                          (_sp_rect.x + 60, _sp_rect.y + 90), size='md', color='blanco')
                # Motivo
                _motivo = estado.get('copa_clasificado_motivo', '')
                if _motivo:
                    draw_text(screen, f"Motivo: {_motivo}",
                              (_sp_rect.x + 60, _sp_rect.y + 125), size='sm', color='azul')
                # Estado actual de la copa
                _cup_state = _get_cup_state_str(estado)
                draw_text(screen, f"Copa en curso: {_cup_state}",
                          (_sp_rect.x + 60, _sp_rect.y + 175), size='md', color='dorado')
                # Botón VER (centrado, abajo)
                _btn_ver_rect = pygame.Rect(_sp_rect.x + 280, _sp_rect.y + 240, 200, 60)
                _btn_ver_hover = _btn_ver_rect.collidepoint(mouse_pos)
                try:
                    bg_btn = COLORS.get('azul', (0, 191, 255)) if _btn_ver_hover else (40, 50, 80)
                    pygame.draw.rect(screen, bg_btn, _btn_ver_rect, border_radius=8)
                except Exception:
                    pass
                try:
                    pygame.draw.rect(screen, COLORS.get('azul', (0, 191, 255)), _btn_ver_rect, width=2, border_radius=8)
                except Exception:
                    pass
                draw_text(screen, "VER",
                          (_btn_ver_rect.x + 80, _btn_ver_rect.y + 18), size='lg', color='blanco')
            except Exception as e_spec:
                logger.error(f"Error al dibujar overlay de no clasificado: {e_spec}")

        # v0.8.7: toast de CAMPEÓN (cuando termina la copa en modo espectador).
        # Se muestra arriba a la derecha durante 6 segundos.
        try:
            _toast_until = estado.get('copa_campeon_toast_until')
            _now = pygame.time.get_ticks()
            if _toast_until and _now < _toast_until:
                _camp = estado.get('copa_campeon', '')
                if _camp:
                    _toast_rect = pygame.Rect(SCREEN_W - 470, 12, 450, 60)
                    draw_panel(screen, _toast_rect)
                    pygame.draw.rect(screen, COLORS.get('verde', (0, 255, 136)), _toast_rect, width=2, border_radius=8)
                    draw_text(screen, "🏆 CAMPEÓN DE LA COPA", (_toast_rect.x + 16, _toast_rect.y + 8),
                              size='sm', color='dorado')
                    draw_text(screen, str(_camp)[:34], (_toast_rect.x + 16, _toast_rect.y + 30),
                              size='lg', color='verde')
        except Exception as e_toast:
            logger.error(f"Error al dibujar toast de campeón: {e_toast}")

        back_rect = pygame.Rect(40, 610, 200, 50)
        back_hover = back_rect.collidepoint(mouse_pos)
        draw_button(screen, back_rect, "VOLVER A LIGA", back_hover)
        
        fase_actual = estado['copa_fase_actual']
        jugar_rect = pygame.Rect(1000, 610, 240, 50)
        jugar_hover = jugar_rect.collidepoint(mouse_pos)
        
        jornada_actual = getattr(liga, "jornada_actual", 1)
        num_jornadas = getattr(liga, "num_jornadas", 10)
        limites = {
            1: 2,
            2: max(3, int(num_jornadas * 0.3)),
            3: max(4, int(num_jornadas * 0.5)),
            'cuartos': max(6, int(num_jornadas * 0.7)),
            'semis': max(8, int(num_jornadas * 0.85)),
            'final': num_jornadas
        }

        fase_nombre_pend, partido_pend = obtener_partido_copa_pendiente(estado)

        tiene_partido_pendiente = False
        btn_text = "CONTINUAR COPA"
        action_to_return = "jugar_partido"
        partido_a_jugar = None
        
        jornada_copa_sel = estado.get('copa_jornada_grupo', 1)
        jornada_copa_limite = limites.get(jornada_copa_sel, 99)
        jornada_copa_desbloqueada = (jornada_actual >= jornada_copa_limite)

        if fase_actual == 'grupos':
            if jornada_copa_desbloqueada:
                partidos_pend_user = [p for p in estado['copa_grupo_partidos'] if p['jornada'] == jornada_copa_sel and not p['jugado'] and mi_equipo and (p['local'] == mi_equipo.nombre or p['visitante'] == mi_equipo.nombre)]
                if partidos_pend_user:
                    tiene_partido_pendiente = True
                    btn_text = f"JUGAR PARTIDO G{jornada_copa_sel}"
                    action_to_return = "jugar_partido_copa"
                    partido_a_jugar = partidos_pend_user[0]
                else:
                    # v0.8.5: sin botón "SIMULAR OTROS PARTIDOS". Los demás partidos de esta
                    # jornada (ya desbloqueada y sin partido pendiente del usuario) se simulan
                    # SOLOS y sus resultados aparecen automáticamente.
                    _autosimular_otros_grupo(estado, jornada_copa_sel)
            else:
                draw_text(screen, f"Bloqueado: Juega la Jornada {jornada_copa_limite} de Liga para desbloquear.", (710, 620), size='sm', color='rojo')
        elif fase_actual in ['cuartos', 'semis', 'final']:
            limite_fase = limites.get(fase_actual, 99)
            # v0.8.8: gating secuencial — la fase previa debe estar completa y el bracket válido.
            _fase_ok = (jornada_actual >= limite_fase
                        and _fase_anterior_completa(estado, fase_actual)
                        and _bracket_fase_valida(estado, fase_actual))
            if _fase_ok:
                fase_data = estado['copa_bracket'].get(fase_actual)
                user_sigue_vivo = True
                _bracket = estado.get('copa_bracket') or {}
                if fase_actual == 'semis': user_sigue_vivo = ((_bracket.get('cuartos') or {}).get('avanza') == 'user')
                elif fase_actual == 'final': user_sigue_vivo = ((_bracket.get('semis') or {}).get('avanza') == 'user')

                if user_sigue_vivo and fase_data and not fase_data.get('jugado'):
                    tiene_partido_pendiente = True
                    _fase = str(fase_actual) if fase_actual else ''
                    btn_text = f"JUGAR {_fase.upper()}"
                    action_to_return = f"jugar_copa_{_fase}"
                elif not user_sigue_vivo:
                    tiene_partido_pendiente = True
                    btn_text = "SIMULAR RESTO DE COPA"
                    action_to_return = "simular_resto_copa"
            else:
                draw_text(screen, f"Bloqueado: Juega la Jornada {limite_fase} de Liga para desbloquear.", (710, 620), size='sm', color='rojo')
                
        if tiene_partido_pendiente:
            draw_button(screen, jugar_rect, btn_text, jugar_hover)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # v0.8.7.2: si el overlay de "NO CLASIFICADO" está abierto, consumir el clic
                # y manejar el botón VER antes que cualquier otro.
                if _spectator_open:
                    if _btn_ver_rect.collidepoint(event.pos):
                        # VER: dismissa el overlay para esta sesión. El user puede
                        # navegar la copa en modo lectura (sin partidos pendientes).
                        estado['_spectator_dismissed'] = True
                        continue
                    # Cualquier clic dentro del panel del overlay: consumir
                    if _sp_rect.collidepoint(event.pos):
                        continue
                # v0.8.6 (Tarea 4): manejar clic en botón de estadísticas
                if stats_btn_rect.collidepoint(event.pos):
                    estado['copa_stats_abierto'] = not estado.get('copa_stats_abierto', False)
                    continue
                # Si el overlay está abierto, consumir clics para que no atraviesen
                if overlay_consumio_click:
                    if cerrar_rect.collidepoint(event.pos):
                        estado['copa_stats_abierto'] = False
                    continue
                for name, rect in tab_rects.items():
                    if rect.collidepoint(event.pos):
                        estado['copa_tab'] = name
                        if name in ['Grupo A', 'Grupo B', 'Grupo C', 'Grupo D']:
                            recalcular_standings_copa(estado)
                        
                if tab_active in ['Grupo A', 'Grupo B', 'Grupo C', 'Grupo D']:
                    if jornada_sel > 1 and btn_prev_j.collidepoint(event.pos):
                        estado['copa_jornada_grupo'] -= 1
                    elif jornada_sel < 3 and btn_next_j.collidepoint(event.pos):
                        estado['copa_jornada_grupo'] += 1

                if back_rect.collidepoint(event.pos):
                    estado.pop('copa_tab', None)
                    estado.pop('copa_jornada_grupo', None)
                    return "volver"
                    
                if tiene_partido_pendiente and jugar_rect.collidepoint(event.pos):
                    if action_to_return == "jugar_partido_copa":
                        partido = partido_a_jugar
                        estado['match_mode'] = 'copa'
                        estado['partido_actual'] = None
                        estado['partido_local_obj'] = encontrar_equipo_copa(partido['local'], estado)
                        estado['partido_visitante_obj'] = encontrar_equipo_copa(partido['visitante'], estado)
                        estado['partido_copa_dict'] = partido
                        estado.pop('sim_resultado', None)
                        return "prepartido_screen"
                        
                    elif action_to_return.startswith("jugar_copa_"):
                        fase = action_to_return.split('_')[-1]
                        # v0.8.2: usar el helper que encuentra el match del usuario en la
                        # estructura del bracket (sea la forma normalizada de copa_bracket[fase]
                        # o las llaves de copa_bracket_otros[fase]). Antes leía
                        # 'copa_bracket[fase]['rival']' directo, que crasheaba cuando el
                        # bracket aún tenía la forma placeholder {m1, m2, m3, m4}.
                        match_user = obtener_match_usuario_bracket(estado, fase)
                        rival_nombre = (match_user.get('visitante')
                                          if getattr(match_user, 'get', None) and match_user.get('local') == mi_equipo.nombre
                                          else match_user.get('local')) or match_user.get('rival') or ''
                        if not rival_nombre:
                            # Fallback extremo: usar el primer match que encontremos
                            otros = (estado.get('copa_bracket_otros') or {}).get(fase) or []
                            if otros and isinstance(otros[0], dict):
                                rival_nombre = (otros[0].get('visitante') if otros[0].get('local') == mi_equipo.nombre else otros[0].get('local')) or ''
                        estado['match_mode'] = 'copa'
                        estado['partido_actual'] = None
                        estado['partido_local_obj'] = mi_equipo
                        estado['partido_visitante_obj'] = encontrar_equipo_copa(rival_nombre, estado) if rival_nombre else None
                        estado['partido_copa_bracket_fase'] = fase
                        estado.pop('sim_resultado', None)
                        if estado['partido_visitante_obj'] is None:
                            # Si no pudimos encontrar rival, evitamos enviar al prepartido
                            # con datos rotos; el partido es inválido.
                            return None
                        return "prepartido_screen"
                        
                    elif action_to_return == "simular_resto_copa":
                        from alpha_football.engine import simular_partido as engine_simular
                        from alpha_football.desarrollo import desarrollar_plantilla_post_partido
                        fases = ['cuartos', 'semis', 'final']
                        idx_start = fases.index(fase_actual) if fase_actual in fases else 0
                        for idx in range(idx_start, len(fases)):
                            f = fases[idx]
                            simular_partidos_ia_bracket(estado, f)
                            # v0.8.2: garantizar estructura normalizada antes de leer 'local'/'visitante'
                            if not _fase_tiene_bracket_normalizado(estado, f):
                                avanzar_fase_bracket(estado)
                            fd = estado['copa_bracket'].get(f)
                            if fd and isinstance(fd.get('local'), str) and not fd.get('jugado'):
                                t_l_name, t_v_name = fd['local'], fd['visitante']
                                t_l_obj, t_v_obj = encontrar_equipo_copa(t_l_name, estado), encontrar_equipo_copa(t_v_name, estado)
                                if t_l_obj is not None and t_v_obj is not None:
                                    res = engine_simular(t_l_obj, t_v_obj, con_eventos_caoticos=False)
                                    fd['goles_l'], fd['goles_v'], fd['jugado'] = res.goles_local, res.goles_visitante, True
                                    try:
                                        desarrollar_plantilla_post_partido(t_l_obj, res.goles_local, res.goles_visitante)
                                        desarrollar_plantilla_post_partido(t_v_obj, res.goles_visitante, res.goles_local)
                                    except: pass
                                    if res.goles_local == res.goles_visitante:
                                        gana_l = random.random() < 0.5
                                        fd['avanza'] = 'user' if ((gana_l and t_l_name == name_user) or (not gana_l and t_v_name == name_user)) else 'rival'
                                        fd['penales'] = '5-4' if gana_l else '4-5'
                                    else:
                                        gana_l = res.goles_local > res.goles_visitante
                                        fd['avanza'] = 'user' if ((gana_l and t_l_name == name_user) or (not gana_l and t_v_name == name_user)) else 'rival'
                            if f != 'final':
                                estado['copa_fase_actual'] = f
                                avanzar_fase_bracket(estado)
                        estado['copa_fase_actual'] = 'eliminado'

    except Exception as general_error:
        print(f"Error general en copa_screen.py: {general_error}", file=sys.stderr)
        try:
            screen.fill((10, 20, 30))
            emerg_rect = pygame.Rect(490, 330, 300, 60)
            pygame.draw.rect(screen, (255, 0, 0), emerg_rect, border_radius=5)
            font = pygame.font.Font(None, 24)
            txt = font.render("ERROR EN COPA. CLIC PARA VOLVER", True, (255, 255, 255))
            screen.blit(txt, txt.get_rect(center=emerg_rect.center))
            for event in pygame.event.get():
                if event.type == pygame.QUIT: return "quit"
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if emerg_rect.collidepoint(event.pos): return "volver"
        except: return "volver"
    return None
