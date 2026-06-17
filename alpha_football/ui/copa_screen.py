# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Pantalla de la Copa (Pygame)
Muestra la fase de grupos (tabla de clasificación y partidos) y el bracket visual
de eliminación directa (Octavos, Cuartos, Semis, Final) con líneas conectoras y paneles.
"""

import sys
import os
import random

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

def inicializar_copa_si_falta(estado: dict) -> None:
    """Inicializa la Copa en el estado de forma segura si no ha sido creada."""
    try:
        mi_equipo = estado.get('mi_equipo')
        liga = estado.get('liga')
        if not mi_equipo or not liga:
            return
            
        if 'copa_tipo' not in estado:
            if liga.tipo in ['premier', 'laliga']:
                estado['copa_tipo'] = 'Champions'
            else:
                estado['copa_tipo'] = 'Libertadores'
                
        copa_tipo = estado['copa_tipo']
        
        # Rivales según tipo de copa
        if copa_tipo == 'Champions':
            rival_grupo_1 = "Bayerna de Munich"
            rival_grupo_2 = "Borussia Dormund"
            rival_grupo_3 = "Piamonte Calcio"
            rival_octavos = "Inter de Milan Roto"
            rival_cuartos = "Paris Saint-Germain Sin Champions"
            rival_semis = "Benfica Maldito"
            rival_final = "Puerto FC"
        else:
            rival_grupo_1 = "Boca Amargo"
            rival_grupo_2 = "Palmeirras"
            rival_grupo_3 = "Nacionall de Montevideo"
            rival_octavos = "Penarol Roto"
            rival_cuartos = "Colo Colo Roto"
            rival_semis = "Liga de Quito Rota"
            rival_final = "Barcelona Falso de Guayaquil"
            
        estado.setdefault('copa_fase_actual', 'grupos')
        
        # Inicializar standing de grupo
        if 'copa_grupo_standing' not in estado:
            try:
                from alpha_football.models import Standing
                standing_init = [
                    Standing(equipo=mi_equipo.nombre, pj=0, g=0, e=0, p=0, gf=0, gc=0, pts=0),
                    Standing(equipo=rival_grupo_1, pj=0, g=0, e=0, p=0, gf=0, gc=0, pts=0),
                    Standing(equipo=rival_grupo_2, pj=0, g=0, e=0, p=0, gf=0, gc=0, pts=0),
                    Standing(equipo=rival_grupo_3, pj=0, g=0, e=0, p=0, gf=0, gc=0, pts=0)
                ]
                estado['copa_grupo_standing'] = standing_init
            except Exception:
                estado['copa_grupo_standing'] = [
                    {"equipo": mi_equipo.nombre, "pj":0, "g":0, "e":0, "p":0, "gf":0, "gc":0, "pts":0},
                    {"equipo": rival_grupo_1, "pj":0, "g":0, "e":0, "p":0, "gf":0, "gc":0, "pts":0},
                    {"equipo": rival_grupo_2, "pj":0, "g":0, "e":0, "p":0, "gf":0, "gc":0, "pts":0},
                    {"equipo": rival_grupo_3, "pj":0, "g":0, "e":0, "p":0, "gf":0, "gc":0, "pts":0}
                ]
                
        # Inicializar brackets
        if 'copa_bracket' not in estado:
            estado['copa_bracket'] = {
                'octavos': {'rival': rival_octavos, 'goles_l': 0, 'goles_v': 0, 'jugado': False, 'avanza': None},
                'cuartos': {'rival': rival_cuartos, 'goles_l': 0, 'goles_v': 0, 'jugado': False, 'avanza': None},
                'semis': {'rival': rival_semis, 'goles_l': 0, 'goles_v': 0, 'jugado': False, 'avanza': None},
                'final': {'rival': rival_final, 'goles_l': 0, 'goles_v': 0, 'jugado': False, 'avanza': None}
            }

        # Inicializar fixture de grupo (6 partidos)
        if 'copa_grupo_partidos' not in estado:
            estado['copa_grupo_partidos'] = [
                {"jornada": 1, "local": mi_equipo.nombre, "visitante": rival_grupo_1, "goles_l": "-", "goles_v": "-", "jugado": False},
                {"jornada": 1, "local": rival_grupo_2, "visitante": rival_grupo_3, "goles_l": "-", "goles_v": "-", "jugado": False},
                {"jornada": 2, "local": rival_grupo_3, "visitante": mi_equipo.nombre, "goles_l": "-", "goles_v": "-", "jugado": False},
                {"jornada": 2, "local": rival_grupo_1, "visitante": rival_grupo_2, "goles_l": "-", "goles_v": "-", "jugado": False},
                {"jornada": 3, "local": mi_equipo.nombre, "visitante": rival_grupo_2, "goles_l": "-", "goles_v": "-", "jugado": False},
                {"jornada": 3, "local": rival_grupo_3, "visitante": rival_grupo_1, "goles_l": "-", "goles_v": "-", "jugado": False}
            ]
    except Exception as e:
        print(f"Error al inicializar Copa de forma segura: {e}", file=sys.stderr)

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
            'octavos': max(5, int(num_jornadas * 0.7)),
            'cuartos': max(6, int(num_jornadas * 0.8)),
            'semis': max(7, int(num_jornadas * 0.9)),
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
                    
        elif fase_actual in ['octavos', 'cuartos', 'semis', 'final']:
            limite_fase = limites[fase_actual]
            if jornada_actual >= limite_fase:
                fase_data = estado['copa_bracket'][fase_actual]
                if not fase_data['jugado']:
                    user_sigue_vivo = True
                    if fase_actual == 'cuartos': user_sigue_vivo = (estado['copa_bracket']['octavos']['avanza'] == 'user')
                    elif fase_actual == 'semis': user_sigue_vivo = (estado['copa_bracket']['cuartos']['avanza'] == 'user')
                    elif fase_actual == 'final': user_sigue_vivo = (estado['copa_bracket']['semis']['avanza'] == 'user')
                    
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

def recalcular_standings_copa(estado: dict) -> None:
    """Recalcula la tabla de posiciones del grupo de Copa en base a los partidos jugados."""
    try:
        standings = estado.get('copa_grupo_standing', [])
        partidos = estado.get('copa_grupo_partidos', [])
        
        # Reiniciar estadísticas
        for st in standings:
            if hasattr(st, 'pj'):
                st.pj = st.g = st.e = st.p = st.gf = st.gc = st.pts = 0
                st.dg = 0
            else:
                st['pj'] = st['g'] = st['e'] = st['p'] = st['gf'] = st['gc'] = st['pts'] = 0
                
        mapa_st = {}
        for st in standings:
            name = st.equipo if hasattr(st, 'equipo') else st.get('equipo')
            mapa_st[name] = st
            
        for p in partidos:
            if not p.get('jugado'):
                continue
                
            loc = p['local']
            vis = p['visitante']
            
            try:
                gl = int(p['goles_l'])
                gv = int(p['goles_v'])
            except (ValueError, TypeError):
                continue
                
            st_l = mapa_st.get(loc)
            st_v = mapa_st.get(vis)
            
            if st_l is not None:
                if hasattr(st_l, 'pj'):
                    st_l.pj += 1
                    st_l.gf += gl
                    st_l.gc += gv
                    if gl > gv:
                        st_l.g += 1
                        st_l.pts += 3
                    elif gl < gv:
                        st_l.p += 1
                    else:
                        st_l.e += 1
                        st_l.pts += 1
                    st_l.dg = st_l.gf - st_l.gc
                else:
                    st_l['pj'] += 1
                    st_l['gf'] += gl
                    st_l['gc'] += gv
                    if gl > gv:
                        st_l['g'] += 1
                        st_l['pts'] += 3
                    elif gl < gv:
                        st_l['p'] += 1
                    else:
                        st_l['e'] += 1
                        st_l['pts'] += 1
                        
            if st_v is not None:
                if hasattr(st_v, 'pj'):
                    st_v.pj += 1
                    st_v.gf += gv
                    st_v.gc += gl
                    if gv > gl:
                        st_v.g += 1
                        st_v.pts += 3
                    elif gv < gl:
                        st_v.p += 1
                    else:
                        st_v.e += 1
                        st_v.pts += 1
                    st_v.dg = st_v.gf - st_v.gc
                else:
                    st_v['pj'] += 1
                    st_v['gf'] += gv
                    st_v['gc'] += gl
                    if gv > gl:
                        st_v['g'] += 1
                        st_v['pts'] += 3
                    elif gv < gl:
                        st_v['p'] += 1
                    else:
                        st_v['e'] += 1
                        st_v['pts'] += 1
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
        
        # Rivales según tipo de copa para evitar cruces extraños
        if copa_tipo == 'Champions':
            rival_grupo_1 = "Bayerna de Munich"
            rival_grupo_2 = "Borussia Dormund"
            rival_grupo_3 = "Piamonte Calcio"
            rival_octavos = "Inter de Milan Roto"
            rival_cuartos = "Paris Saint-Germain Sin Champions"
            rival_semis = "Benfica Maldito"
            rival_final = "Puerto FC"
        else:
            rival_grupo_1 = "Boca Amargo"
            rival_grupo_2 = "Palmeirras"
            rival_grupo_3 = "Nacionall de Montevideo"
            rival_octavos = "Penarol Roto"
            rival_cuartos = "Colo Colo Roto"
            rival_semis = "Liga de Quito Rota"
            rival_final = "Barcelona Falso de Guayaquil"
            
        estado.setdefault('copa_tab', 'Grupo A')
        estado.setdefault('copa_jornada_grupo', 1)

        # Verificar avance automático de la fase de grupos a eliminatorias
        if estado.get('copa_fase_actual') == 'grupos':
            todos_jugados = all(p.get('jugado', False) for p in estado['copa_grupo_partidos'])
            if todos_jugados:
                recalcular_standings_copa(estado)
                standings = estado['copa_grupo_standing']
                try:
                    sorted_standings = sorted(standings, key=lambda s: (s.pts, s.dg, s.gf), reverse=True)
                except Exception:
                    sorted_standings = sorted(standings, key=lambda s: (s.get('pts',0), s.get('gf',0)-s.get('gc',0), s.get('gf',0)), reverse=True)
                
                top_2_names = []
                for st in sorted_standings[:2]:
                    name = st.equipo if hasattr(st, 'equipo') else st.get('equipo')
                    top_2_names.append(name)
                
                user_name = mi_equipo.nombre if mi_equipo else "Mi Equipo"
                if user_name in top_2_names:
                    estado['copa_fase_actual'] = 'octavos'
                    estado['copa_tab'] = 'Fase Final'
                else:
                    estado['copa_fase_actual'] = 'eliminado'

        # Dibujar fondo base
        draw_gradient_bg(screen)
        
        # Título de la Copa
        titulo_copa = f"COPA {copa_tipo.upper()}"
        draw_text(screen, titulo_copa, (40, 20), size='xl', color='dorado')
        
        sub_desc = "Fase de Grupos en progreso" if estado['copa_fase_actual'] == 'grupos' else f"Fase de Eliminación Directa — {estado['copa_fase_actual'].upper()}"
        draw_text(screen, sub_desc, (40, 65), size='sm', color='azul')
        
        # Pestañas: 'Grupo A' y 'Fase Final'
        tab_names = ['Grupo A', 'Fase Final']
        tab_rects = {}
        tab_x = 40
        tab_y = 100
        tab_w = 150
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

        # RENDERIZADO SEGÚN PESTAÑA ACTIVA
        if tab_active == 'Grupo A':
            # --- PANEL IZQUIERDO: STANDINGS DEL GRUPO ---
            left_rect = pygame.Rect(40, 150, 600, 440)
            draw_panel(screen, left_rect)
            draw_text(screen, "CLASIFICACIÓN — GRUPO A", (60, 165), size='md', color='azul')
            
            # Encabezados de tabla
            headers = ["#", "Equipo", "PJ", "G", "E", "P", "GF", "GC", "PTS"]
            header_x = [60, 100, 310, 350, 390, 430, 470, 510, 560]
            for h, x_pos in zip(headers, header_x):
                draw_text(screen, h, (x_pos, 205), size='sm', color='dorado')
                
            pygame.draw.line(screen, (0, 191, 255), (60, 225), (620, 225), 1)
            
            # Obtener standings ordenados
            standings = estado['copa_grupo_standing']
            # Asegurar que se puedan ordenar por puntos, dg, gf de forma robusta
            try:
                # Si son objetos de tipo Standing
                sorted_standings = sorted(standings, key=lambda s: (s.pts, s.dg, s.gf), reverse=True)
            except Exception:
                # Si es un dict
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
                
                # Marcar en verde los clasificados (Top 2), rojo el resto
                pos_color = 'verde' if i <= 2 else 'rojo'
                is_user = (mi_equipo and eq_name == mi_equipo.nombre)
                text_color = 'azul' if is_user else 'blanco'
                
                draw_text(screen, str(i), (60, y_pos), size='md', color=pos_color)
                draw_text(screen, eq_name[:22], (100, y_pos), size='md', color=text_color)
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
            draw_text(screen, "PARTIDOS DE LA FASE DE GRUPOS", (680, 165), size='md', color='azul')
            
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
            
            # Listar partidos de la jornada seleccionada
            partidos_filtrados = [p for p in estado['copa_grupo_partidos'] if p['jornada'] == jornada_sel]
            match_y = 260
            
            for m in partidos_filtrados:
                match_rect = pygame.Rect(680, match_y, 540, 70)
                draw_panel(screen, match_rect)
                
                # Resaltar si es partido del usuario
                es_del_usuario = (mi_equipo and (m['local'] == mi_equipo.nombre or m['visitante'] == mi_equipo.nombre))
                local_color = 'azul' if (mi_equipo and m['local'] == mi_equipo.nombre) else 'blanco'
                visitor_color = 'azul' if (mi_equipo and m['visitante'] == mi_equipo.nombre) else 'blanco'
                
                draw_text(screen, m['local'][:18], (700, match_y + 23), size='md', color=local_color)
                draw_text(screen, f"{m['goles_l']}", (880, match_y + 23), size='lg', color='dorado')
                draw_text(screen, "vs", (930, match_y + 23), size='md', color='blanco')
                draw_text(screen, f"{m['goles_v']}", (980, match_y + 23), size='lg', color='dorado')
                draw_text(screen, m['visitante'][:18], (1030, match_y + 23), size='md', color=visitor_color)
                
                match_y += 85

        else: # FASE FINAL (BRACKET)
            # Renders de árbol con nodos conectores
            # Dibujar un panel gigante para el bracket
            bracket_panel = pygame.Rect(40, 150, 1200, 440)
            draw_panel(screen, bracket_panel)
            
            draw_text(screen, "BRACKET DE ELIMINACIÓN DIRECTA", (60, 165), size='md', color='azul')
            
            # Coordenadas de los nodos (X, Y)
            # 4 fases: Octavos (X=80), Cuartos (X=360), Semis (X=660), Final (X=960)
            box_w, box_h = 220, 75
            
            # Posiciones de los nodos del árbol (Octavos a Final)
            # Para simplificar y dar una vista premium espectacular, mostraremos el camino del usuario
            # y los rivales que cruzan en cada etapa.
            node_x = {
                'octavos': 80,
                'cuartos': 370,
                'semis': 660,
                'final': 950
            }
            
            # Alturas
            # Octavos tiene dos entradas que convergen a Cuartos
            # Para el usuario, mostramos su cruce de Octavos y otro cruce de donde saldrá el rival de Cuartos
            y_oct1 = 200
            y_oct2 = 460
            y_cua = 330
            y_sem = 330
            y_fin = 330
            
            # Obtener datos de la Copa
            b_data = estado['copa_bracket']
            
            # Dibujar líneas de conexión del Bracket
            # Octavos 1 a Cuartos
            pygame.draw.line(screen, (0, 191, 255), (node_x['octavos'] + box_w, y_oct1 + box_h//2), (node_x['cuartos'], y_cua + box_h//2), 2)
            # Octavos 2 a Cuartos
            pygame.draw.line(screen, (0, 191, 255), (node_x['octavos'] + box_w, y_oct2 + box_h//2), (node_x['cuartos'], y_cua + box_h//2), 2)
            # Cuartos a Semis
            pygame.draw.line(screen, (0, 191, 255), (node_x['cuartos'] + box_w, y_cua + box_h//2), (node_x['semis'], y_sem + box_h//2), 2)
            # Semis a Final
            pygame.draw.line(screen, (0, 191, 255), (node_x['semis'] + box_w, y_sem + box_h//2), (node_x['final'], y_fin + box_h//2), 2)
            
            # RENDERIZAR NODOS
            # 1. Octavos Nodo Superior (Match del Usuario)
            rect_oct1 = pygame.Rect(node_x['octavos'], y_oct1, box_w, box_h)
            draw_panel(screen, rect_oct1)
            draw_text(screen, "Octavos - Llave A", (node_x['octavos'] + 10, y_oct1 + 5), size='sm', color='azul')
            o_data = b_data['octavos']
            g_l = str(o_data['goles_l']) if o_data['jugado'] else "-"
            g_v = str(o_data['goles_v']) if o_data['jugado'] else "-"
            draw_text(screen, mi_equipo.nombre[:14] if mi_equipo else "Mi Club", (node_x['octavos'] + 10, y_oct1 + 25), size='sm', color='blanco')
            draw_text(screen, o_data['rival'][:14], (node_x['octavos'] + 10, y_oct1 + 48), size='sm', color='blanco')
            draw_text(screen, g_l, (node_x['octavos'] + 175, y_oct1 + 25), size='md', color='dorado')
            draw_text(screen, g_v, (node_x['octavos'] + 175, y_oct1 + 48), size='md', color='dorado')

            # 2. Octavos Nodo Inferior (Rival simulado)
            rect_oct2 = pygame.Rect(node_x['octavos'], y_oct2, box_w, box_h)
            draw_panel(screen, rect_oct2)
            draw_text(screen, "Octavos - Llave B", (node_x['octavos'] + 10, y_oct2 + 5), size='sm', color='azul')
            draw_text(screen, "Palmeirras", (node_x['octavos'] + 10, y_oct2 + 25), size='sm', color='blanco')
            draw_text(screen, "Boca Amargo", (node_x['octavos'] + 10, y_oct2 + 48), size='sm', color='blanco')
            # Si octavos ya fue jugado, Palmeirras o Boca ganó
            oct2_gl = "3" if o_data['jugado'] else "-"
            oct2_gv = "1" if o_data['jugado'] else "-"
            draw_text(screen, oct2_gl, (node_x['octavos'] + 175, y_oct2 + 25), size='md', color='dorado')
            draw_text(screen, oct2_gv, (node_x['octavos'] + 175, y_oct2 + 48), size='md', color='dorado')

            # 3. Cuartos Nodo
            rect_cua = pygame.Rect(node_x['cuartos'], y_cua, box_w, box_h)
            draw_panel(screen, rect_cua)
            draw_text(screen, "Cuartos de Final", (node_x['cuartos'] + 10, y_cua + 5), size='sm', color='azul')
            c_data = b_data['cuartos']
            # Determinar local de cuartos (Usuario si pasó)
            user_paso_oct = (o_data['jugado'] and o_data['avanza'] == 'user')
            local_cua = mi_equipo.nombre[:14] if (mi_equipo and user_paso_oct) else ("Ind. Valle" if o_data['jugado'] else "?")
            visitor_cua = c_data['rival'][:14] if o_data['jugado'] else "?"
            
            cua_gl = str(c_data['goles_l']) if c_data['jugado'] else "-"
            cua_gv = str(c_data['goles_v']) if c_data['jugado'] else "-"
            
            draw_text(screen, local_cua, (node_x['cuartos'] + 10, y_cua + 25), size='sm', color='blanco' if not user_paso_oct else 'verde')
            draw_text(screen, visitor_cua, (node_x['cuartos'] + 10, y_cua + 48), size='sm', color='blanco')
            draw_text(screen, cua_gl, (node_x['cuartos'] + 175, y_cua + 25), size='md', color='dorado')
            draw_text(screen, cua_gv, (node_x['cuartos'] + 175, y_cua + 48), size='md', color='dorado')

            # 4. Semis Nodo
            rect_sem = pygame.Rect(node_x['semis'], y_sem, box_w, box_h)
            draw_panel(screen, rect_sem)
            draw_text(screen, "Semifinales", (node_x['semis'] + 10, y_sem + 5), size='sm', color='azul')
            s_data = b_data['semis']
            user_paso_cua = (c_data['jugado'] and c_data['avanza'] == 'user')
            
            local_sem = mi_equipo.nombre[:14] if (mi_equipo and user_paso_cua) else ("Boca Amargo" if c_data['jugado'] else "?")
            visitor_sem = s_data['rival'][:14] if c_data['jugado'] else "?"
            
            sem_gl = str(s_data['goles_l']) if s_data['jugado'] else "-"
            sem_gv = str(s_data['goles_v']) if s_data['jugado'] else "-"
            
            draw_text(screen, local_sem, (node_x['semis'] + 10, y_sem + 25), size='sm', color='blanco' if not user_paso_cua else 'verde')
            draw_text(screen, visitor_sem, (node_x['semis'] + 10, y_sem + 48), size='sm', color='blanco')
            draw_text(screen, sem_gl, (node_x['semis'] + 175, y_sem + 25), size='md', color='dorado')
            draw_text(screen, sem_gv, (node_x['semis'] + 175, y_sem + 48), size='md', color='dorado')

            # 5. Final Nodo
            rect_fin = pygame.Rect(node_x['final'], y_fin, box_w, box_h)
            draw_panel(screen, rect_fin)
            draw_text(screen, "Gran Final", (node_x['final'] + 10, y_fin + 5), size='sm', color='azul')
            f_data = b_data['final']
            user_paso_sem = (s_data['jugado'] and s_data['avanza'] == 'user')
            
            local_fin = mi_equipo.nombre[:14] if (mi_equipo and user_paso_sem) else ("Rivera Plate" if s_data['jugado'] else "?")
            visitor_fin = f_data['rival'][:14] if s_data['jugado'] else "?"
            
            fin_gl = str(f_data['goles_l']) if f_data['jugado'] else "-"
            fin_gv = str(f_data['goles_v']) if f_data['jugado'] else "-"
            
            draw_text(screen, local_fin, (node_x['final'] + 10, y_fin + 25), size='sm', color='blanco' if not user_paso_sem else 'verde')
            draw_text(screen, visitor_fin, (node_x['final'] + 10, y_fin + 48), size='sm', color='blanco')
            draw_text(screen, fin_gl, (node_x['final'] + 175, y_fin + 25), size='md', color='dorado')
            draw_text(screen, fin_gv, (node_x['final'] + 175, y_fin + 48), size='md', color='dorado')
            
            # Campeón corona visual
            if f_data['jugado']:
                campeon_camino = mi_equipo.nombre if f_data['avanza'] == 'user' else f_data['rival']
                draw_text(screen, f"¡CAMPEÓN: {campeon_camino.upper()}!", (node_x['final'] + 10, y_fin + 95), size='sm', color='dorado')

        # 10. Botones de Acción Inferiores
        # Botón Volver a Liga
        back_rect = pygame.Rect(40, 610, 200, 50)
        back_hover = back_rect.collidepoint(mouse_pos)
        draw_button(screen, back_rect, "VOLVER A LIGA", back_hover)
        
        # Botón para jugar/simular el partido de la Copa si está activo
        # Si el usuario sigue vivo y hay un partido pendiente de Copa en su fase
        fase_actual = estado['copa_fase_actual']
        jugar_rect = pygame.Rect(1000, 610, 240, 50)
        jugar_hover = jugar_rect.collidepoint(mouse_pos)
        
        jornada_actual = getattr(liga, "jornada_actual", 1)
        num_jornadas = getattr(liga, "num_jornadas", 10)
        limites = {
            1: 2,
            2: max(3, int(num_jornadas * 0.3)),
            3: max(4, int(num_jornadas * 0.5)),
            'octavos': max(5, int(num_jornadas * 0.7)),
            'cuartos': max(6, int(num_jornadas * 0.8)),
            'semis': max(7, int(num_jornadas * 0.9)),
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
                # Buscar el partido del usuario de la jornada seleccionada
                partidos_pend_user = [p for p in estado['copa_grupo_partidos'] if p['jornada'] == jornada_copa_sel and not p['jugado'] and mi_equipo and (p['local'] == mi_equipo.nombre or p['visitante'] == mi_equipo.nombre)]
                if partidos_pend_user:
                    tiene_partido_pendiente = True
                    btn_text = f"JUGAR PARTIDO G{jornada_copa_sel}"
                    action_to_return = "jugar_partido_copa"
                    partido_a_jugar = partidos_pend_user[0]
                else:
                    # Otros partidos a simular de la jornada seleccionada
                    partidos_otros_pend = [p for p in estado['copa_grupo_partidos'] if p['jornada'] == jornada_copa_sel and not p['jugado']]
                    if partidos_otros_pend:
                        tiene_partido_pendiente = True
                        btn_text = "SIMULAR OTROS PARTIDOS"
                        action_to_return = "simular_partidos_copa"
            else:
                # Dibujar cartelera informativa si está bloqueada
                draw_text(screen, f"Bloqueado: Juega la Jornada {jornada_copa_limite} de Liga para desbloquear.", (710, 620), size='sm', color='rojo')
        elif fase_actual in ['octavos', 'cuartos', 'semis', 'final']:
            limite_fase = limites[fase_actual]
            if jornada_actual >= limite_fase:
                fase_data = estado['copa_bracket'][fase_actual]
                user_sigue_vivo = True
                if fase_actual == 'cuartos': user_sigue_vivo = (estado['copa_bracket']['octavos']['avanza'] == 'user')
                elif fase_actual == 'semis': user_sigue_vivo = (estado['copa_bracket']['cuartos']['avanza'] == 'user')
                elif fase_actual == 'final': user_sigue_vivo = (estado['copa_bracket']['semis']['avanza'] == 'user')
                
                if user_sigue_vivo and not fase_data['jugado']:
                    tiene_partido_pendiente = True
                    btn_text = f"JUGAR {fase_actual.upper()}"
                    action_to_return = f"jugar_copa_{fase_actual}"
                elif not user_sigue_vivo:
                    tiene_partido_pendiente = True
                    btn_text = "SIMULAR RESTO DE COPA"
                    action_to_return = "simular_resto_copa"
            else:
                # Dibujar cartelera informativa si está bloqueada
                draw_text(screen, f"Bloqueado: Juega la Jornada {limite_fase} de Liga para desbloquear.", (710, 620), size='sm', color='rojo')
                
        if tiene_partido_pendiente:
            draw_button(screen, jugar_rect, btn_text, jugar_hover)

        # 11. Manejo de Eventos de la Copa de forma resiliente
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
                
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # A. Manejar clics de pestañas (Tabs)
                for name, rect in tab_rects.items():
                    if rect.collidepoint(event.pos):
                        estado['copa_tab'] = name
                        
                # B. Manejar controles de jornada de grupo
                if tab_active == 'Grupo A':
                    if jornada_sel > 1 and btn_prev_j.collidepoint(event.pos):
                        estado['copa_jornada_grupo'] -= 1
                    elif jornada_sel < 3 and btn_next_j.collidepoint(event.pos):
                        estado['copa_jornada_grupo'] += 1

                # C. Botón Volver
                if back_rect.collidepoint(event.pos):
                    # Limpiar variables temporales antes de salir
                    estado.pop('copa_tab', None)
                    estado.pop('copa_jornada_grupo', None)
                    return "volver"
                    
                # D. Botón de Acción Principal (Jugar / Simular)
                if tiene_partido_pendiente and jugar_rect.collidepoint(event.pos):
                    if action_to_return == "jugar_partido_copa":
                        partido = partido_a_jugar
                        local_obj = encontrar_equipo_copa(partido['local'], estado)
                        visitante_obj = encontrar_equipo_copa(partido['visitante'], estado)
                        
                        estado['match_mode'] = 'copa'
                        estado['partido_actual'] = None
                        estado['partido_local_obj'] = local_obj
                        estado['partido_visitante_obj'] = visitante_obj
                        estado['partido_copa_dict'] = partido
                        
                        estado.pop('sim_resultado', None)
                        estado.pop('sim_estado', None)
                        return "match_screen"
                        
                    elif action_to_return == "simular_partidos_copa":
                        from alpha_football.engine import simular_partido as engine_simular
                        partidos_a_simular = [p for p in estado['copa_grupo_partidos'] if p['jornada'] == estado['copa_jornada_grupo'] and not p['jugado']]
                        for p in partidos_a_simular:
                            loc_obj = encontrar_equipo_copa(p['local'], estado)
                            vis_obj = encontrar_equipo_copa(p['visitante'], estado)
                            res = engine_simular(loc_obj, vis_obj, con_eventos_caoticos=False)
                            p['goles_l'] = res.goles_local
                            p['goles_v'] = res.goles_visitante
                            p['jugado'] = True
                        
                        recalcular_standings_copa(estado)
                        
                    elif action_to_return.startswith("jugar_copa_"):
                        rival_nombre = fase_data['rival']
                        rival_obj = encontrar_equipo_copa(rival_nombre, estado)
                        
                        estado['match_mode'] = 'copa'
                        estado['partido_actual'] = None
                        estado['partido_local_obj'] = mi_equipo
                        estado['partido_visitante_obj'] = rival_obj
                        estado['partido_copa_bracket_fase'] = fase_actual
                        
                        estado.pop('sim_resultado', None)
                        estado.pop('sim_estado', None)
                        return "match_screen"
                        
                    elif action_to_return == "simular_resto_copa":
                        from alpha_football.engine import simular_partido as engine_simular
                        fases = ['octavos', 'cuartos', 'semis', 'final']
                        idx_start = fases.index(fase_actual)
                        for f in fases[idx_start:]:
                            fd = estado['copa_bracket'][f]
                            if not fd['jugado']:
                                r1_name = fd['rival']
                                if copa_tipo == 'Champions':
                                    r2_name = "Bayerna de Munich" if r1_name != "Bayerna de Munich" else "Borussia Dormund"
                                else:
                                    r2_name = "Palmeirras" if r1_name != "Palmeirras" else "Boca Amargo"
                                    
                                r1_obj = encontrar_equipo_copa(r1_name, estado)
                                r2_obj = encontrar_equipo_copa(r2_name, estado)
                                
                                res = engine_simular(r1_obj, r2_obj, con_eventos_caoticos=False)
                                fd['goles_l'] = res.goles_local
                                fd['goles_v'] = res.goles_visitante
                                fd['jugado'] = True
                                fd['avanza'] = 'rival'
                                
                        estado['copa_fase_actual'] = 'eliminado'

    except Exception as general_error:
        print(f"Error general en copa_screen.py renderizado: {general_error}. Recuperando...", file=sys.stderr)
        try:
            screen.fill((10, 20, 30))
            emerg_rect = pygame.Rect(490, 330, 300, 60)
            pygame.draw.rect(screen, (255, 0, 0), emerg_rect, border_radius=5)
            font = pygame.font.Font(None, 24)
            txt = font.render("ERROR EN COPA. CLIC PARA VOLVER", True, (255, 255, 255))
            screen.blit(txt, txt.get_rect(center=emerg_rect.center))
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if emerg_rect.collidepoint(event.pos):
                        return "volver"
        except Exception:
            return "volver"

    return None
