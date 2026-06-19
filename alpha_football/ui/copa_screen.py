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
    try:
        if tipo_liga == 'premier':
            from alpha_football.data import premier
            return premier.get_liga().equipos
        elif tipo_liga == 'laliga':
            from alpha_football.data import laliga
            return laliga.get_liga().equipos
        elif tipo_liga == 'betplay':
            from alpha_football.data import betplay
            return betplay.get_liga().equipos
        elif tipo_liga == 'brasil':
            from alpha_football.data import brasil
            return brasil.get_liga().equipos
        elif tipo_liga == 'argentina':
            from alpha_football.data import argentina
            return argentina.get_liga().equipos
    except Exception as e:
        logger.error(f"Error al cargar liga de datos para {tipo_liga}: {e}")
    return []

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
                # Usuario eliminado de copa
                estado['copa_fase_actual'] = 'eliminado'
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
            
            q1 = estado['copa_bracket']['cuartos']
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
                # Usuario eliminado
                estado['copa_bracket']['semis'] = {
                    'local': win_q1, 'visitante': win_q3, 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None, 'rival': win_q3
                }
                estado['copa_bracket_otros']['semis'] = [
                    {'local': win_q2, 'visitante': win_q4, 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None}
                ]
                estado['copa_fase_actual'] = 'eliminado'

        # 3. De Semis a Final
        elif fase_actual == 'semis':
            simular_partidos_ia_bracket(estado, 'semis')
            
            s1 = estado['copa_bracket']['semis']
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
                estado['copa_bracket']['final'] = {
                    'local': win_s1, 'visitante': win_s2, 'goles_l': '-', 'goles_v': '-', 'jugado': False, 'avanza': None, 'rival': win_s2
                }
                estado['copa_bracket_otros']['final'] = []
                estado['copa_fase_actual'] = 'eliminado'
    except Exception as e:
        logger.error(f"Error en avanzar_fase_bracket: {e}", exc_info=True)

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
            
            try:
                desarrollar_plantilla_post_partido(loc_obj, res.goles_local, res.goles_visitante)
                desarrollar_plantilla_post_partido(vis_obj, res.goles_visitante, res.goles_local)
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
        )
        if estructura_ok:
            return

        # Estado ausente, incompleto o de otra copa: purgar TODO lo de copa y reconstruir limpio.
        for _k in ('copa_grupos', 'copa_grupos_standings', 'copa_grupo_standing',
                   'copa_grupo_partidos', 'copa_bracket', 'copa_bracket_otros',
                   'copa_fase_actual', 'copa_tab', 'copa_jornada_grupo'):
            estado.pop(_k, None)
        estado['copa_tipo'] = copa_tipo_correcto
        copa_tipo = copa_tipo_correcto
            
        # 1. Seleccionar 16 equipos según el tipo de copa
        teams = [mi_equipo]
        nombres_vistos = {mi_equipo.nombre}
        
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
            from alpha_football.data.internacional import POOL_CHAMPIONS
            banco = [e for e in POOL_CHAMPIONS if e.nombre != mi_equipo.nombre]
            random.shuffle(banco)
            _agregar(banco)
        else:
            # 3 clasificados de Brasil + 3 de Argentina; el resto, banco LATAM (BetPlay + POOL_LIBERTADORES).
            _agregar(_clasificados(obtener_equipos_de_liga('brasil', estado)))
            _agregar(_clasificados(obtener_equipos_de_liga('argentina', estado)))
            from alpha_football.data.internacional import POOL_LIBERTADORES
            banco = [e for e in obtener_equipos_de_liga('betplay', estado) if e.nombre != mi_equipo.nombre]
            banco += [e for e in POOL_LIBERTADORES if e.nombre != mi_equipo.nombre]
            random.shuffle(banco)
            _agregar(banco)

        # Relleno extra si faltan
        if len(teams) < 16:
            from alpha_football.models import Equipo
            ficticios = ["Colo Colo Roto", "Penarol Roto", "Olimpia Abuelo", "Bolivar Sin Aire", "Universitario de la U"]
            for f_name in ficticios:
                if len(teams) >= 16:
                    break
                if f_name not in nombres_vistos:
                    nombres_vistos.add(f_name)
                    teams.append(Equipo(nombre=f_name, ciudad="Internacional", estrellas=3.5, estilo_dt="anchelottismo", balance=10000000))

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
    """
    try:
        mi_equipo = estado.get('mi_equipo')
        liga = estado.get('liga')
        if not mi_equipo or not liga:
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
            if jornada_actual >= limites['g1']:
                p1 = next((p for p in estado['copa_grupo_partidos'] if p['jornada'] == 1 and not p['jugado'] and (p['local'] == mi_equipo.nombre or p['visitante'] == mi_equipo.nombre)), None)
                if p1:
                    return "Copa Jornada 1", p1
            if jornada_actual >= limites['g2']:
                p2 = next((p for p in estado['copa_grupo_partidos'] if p['jornada'] == 2 and not p['jugado'] and (p['local'] == mi_equipo.nombre or p['visitante'] == mi_equipo.nombre)), None)
                if p2:
                    return "Copa Jornada 2", p2
            if jornada_actual >= limites['g3']:
                p3 = next((p for p in estado['copa_grupo_partidos'] if p['jornada'] == 3 and not p['jugado'] and (p['local'] == mi_equipo.nombre or p['visitante'] == mi_equipo.nombre)), None)
                if p3:
                    return "Copa Jornada 3", p3
                    
        elif fase_actual in ['cuartos', 'semis', 'final']:
            limite_fase = limites.get(fase_actual, 99)
            if jornada_actual >= limite_fase:
                fase_data = estado['copa_bracket'].get(fase_actual)
                if fase_data and not fase_data.get('jugado'):
                    user_sigue_vivo = True
                    if fase_actual == 'semis':
                        user_sigue_vivo = (estado['copa_bracket']['cuartos']['avanza'] == 'user')
                    elif fase_actual == 'final':
                        user_sigue_vivo = (estado['copa_bracket']['semis']['avanza'] == 'user')
                    
                    if user_sigue_vivo:
                        return f"Copa {fase_actual.capitalize()}", fase_data
                        
        return None, None
    except Exception as e:
        print(f"Error al obtener partido de copa pendiente: {e}", file=sys.stderr)
        return None, None

def encontrar_equipo_copa(nombre_equipo: str, estado: dict):
    """Busca y devuelve el objeto Equipo correspondiente a un nombre en el estado o en los pools."""
    try:
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
    """
    try:
        partidos = estado.get('copa_grupo_partidos', [])
        mi = estado.get('mi_equipo')
        mi_nombre = mi.nombre if mi else None
        if not mi_nombre:
            return
        jornadas_user = {
            p['jornada'] for p in partidos
            if p.get('jugado') and mi_nombre in (p.get('local'), p.get('visitante'))
        }
        from alpha_football.engine import simular_partido as eng_sim
        for p in partidos:
            if p.get('jugado'):
                continue
            if p['jornada'] in jornadas_user and mi_nombre not in (p.get('local'), p.get('visitante')):
                loc = encontrar_equipo_copa(p['local'], estado)
                vis = encontrar_equipo_copa(p['visitante'], estado)
                res = eng_sim(loc, vis, con_eventos_caoticos=False)
                p['goles_l'] = res.goles_local
                p['goles_v'] = res.goles_visitante
                p['jugado'] = True
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
        copa_tipo = estado['copa_tipo']
        
        estado.setdefault('copa_tab', 'Grupo A')
        estado.setdefault('copa_jornada_grupo', 1)

        # v0.7: tabla FIEL — autosimular el rival de cada jornada ya jugada por el usuario y
        # recalcular la tabla SIEMPRE al entrar (no solo al completar todo el grupo).
        if estado.get('copa_fase_actual') == 'grupos':
            _autosimular_rivales(estado)
            recalcular_standings_copa(estado)

        # Verificar avance automático de la fase de grupos a eliminatorias
        if estado.get('copa_fase_actual') == 'grupos':
            todos_jugados = all(p.get('jugado', False) for p in estado['copa_grupo_partidos'])
            if todos_jugados:
                avanzar_fase_bracket(estado)
                estado['copa_tab'] = 'Fase Final'

        # Dibujar fondo base
        draw_gradient_bg(screen)
        
        titulo_copa = f"COPA {copa_tipo.upper()}"
        draw_text(screen, titulo_copa, (40, 20), size='xl', color='dorado')
        
        sub_desc = "Fase de Grupos en progreso" if estado['copa_fase_actual'] == 'grupos' else f"Fase de Eliminación Directa — {estado['copa_fase_actual'].upper()}"
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
            q_match = estado['copa_bracket']['cuartos']
            q_otros = estado['copa_bracket_otros'].get('cuartos', [])
            
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
                    partidos_otros_pend = [p for p in estado['copa_grupo_partidos'] if p['jornada'] == jornada_copa_sel and not p['jugado']]
                    if partidos_otros_pend:
                        tiene_partido_pendiente = True
                        btn_text = "SIMULAR OTROS PARTIDOS"
                        action_to_return = "simular_partidos_copa"
            else:
                draw_text(screen, f"Bloqueado: Juega la Jornada {jornada_copa_limite} de Liga para desbloquear.", (710, 620), size='sm', color='rojo')
        elif fase_actual in ['cuartos', 'semis', 'final']:
            limite_fase = limites.get(fase_actual, 99)
            if jornada_actual >= limite_fase:
                fase_data = estado['copa_bracket'].get(fase_actual)
                user_sigue_vivo = True
                if fase_actual == 'semis': user_sigue_vivo = (estado['copa_bracket']['cuartos']['avanza'] == 'user')
                elif fase_actual == 'final': user_sigue_vivo = (estado['copa_bracket']['semis']['avanza'] == 'user')
                
                if user_sigue_vivo and fase_data and not fase_data.get('jugado'):
                    tiene_partido_pendiente = True
                    btn_text = f"JUGAR {fase_actual.upper()}"
                    action_to_return = f"jugar_copa_{fase_actual}"
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
                        
                    elif action_to_return == "simular_partidos_copa":
                        from alpha_football.engine import simular_partido as engine_simular
                        from alpha_football.desarrollo import desarrollar_plantilla_post_partido
                        partidos_a_simular = [p for p in estado['copa_grupo_partidos'] if p['jornada'] == estado['copa_jornada_grupo'] and not p['jugado']]
                        for p in partidos_a_simular:
                            loc_obj = encontrar_equipo_copa(p['local'], estado)
                            vis_obj = encontrar_equipo_copa(p['visitante'], estado)
                            res = engine_simular(loc_obj, vis_obj, con_eventos_caoticos=False)
                            p['goles_l'], p['goles_v'], p['jugado'] = res.goles_local, res.goles_visitante, True
                            try:
                                desarrollar_plantilla_post_partido(loc_obj, res.goles_local, res.goles_visitante)
                                desarrollar_plantilla_post_partido(vis_obj, res.goles_visitante, res.goles_local)
                            except: pass
                        recalcular_standings_copa(estado)
                        
                    elif action_to_return.startswith("jugar_copa_"):
                        fase = action_to_return.split('_')[-1]
                        estado['match_mode'] = 'copa'
                        estado['partido_actual'] = None
                        estado['partido_local_obj'] = mi_equipo
                        estado['partido_visitante_obj'] = encontrar_equipo_copa(estado['copa_bracket'][fase]['rival'], estado)
                        estado['partido_copa_bracket_fase'] = fase
                        estado.pop('sim_resultado', None)
                        return "prepartido_screen"
                        
                    elif action_to_return == "simular_resto_copa":
                        from alpha_football.engine import simular_partido as engine_simular
                        from alpha_football.desarrollo import desarrollar_plantilla_post_partido
                        fases = ['cuartos', 'semis', 'final']
                        idx_start = fases.index(fase_actual) if fase_actual in fases else 0
                        for idx in range(idx_start, len(fases)):
                            f = fases[idx]
                            simular_partidos_ia_bracket(estado, f)
                            fd = estado['copa_bracket'].get(f)
                            if fd and not fd.get('jugado'):
                                t_l_name, t_v_name = fd['local'], fd['visitante']
                                t_l_obj, t_v_obj = encontrar_equipo_copa(t_l_name, estado), encontrar_equipo_copa(t_v_name, estado)
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
