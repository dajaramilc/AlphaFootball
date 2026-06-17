# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Pantalla del Partido (Pygame)
Simula el partido minuto a minuto con marcador grande, comentarios en scroll,
animación de gol (flash y texto gigante con goleador parodiado), medio tiempo interactivo y finalización.
"""

from __future__ import annotations

import sys
import os
import random
import logging
from typing import Any, Optional
import pygame

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
except Exception:
    SCREEN_W = 1280
    SCREEN_H = 720
    COLORS = {
        'bg': (10, 14, 26),
        'verde': (0, 255, 136),
        'dorado': (255, 215, 0),
        'rojo': (255, 68, 68),
        'azul': (0, 191, 255),
        'blanco': (255, 255, 255),
        'panel': (20, 26, 46)
    }
    def get_font(size): return pygame.font.Font(None, 24)
    def draw_gradient_bg(screen): screen.fill((10, 14, 26))
    def draw_panel(screen, rect): pygame.draw.rect(screen, (20, 26, 46), rect)
    def draw_button(screen, rect, text, hover): return rect
    def draw_text(screen, text, pos, size='md', color='blanco', shadow=True): pass

logger = logging.getLogger(__name__)

# --- Funciones Auxiliares de Dibujo y Resiliencia ═════════════════════════════

def get_team_color(team_id: str) -> tuple[int, int, int]:
    """
    Retorna un color RGB de forma determinista para los escudos de los equipos.
    Asegura que si ocurre algún error se retorne un color por defecto (azul).
    """
    try:
        if not team_id:
            return (0, 191, 255)
            
        hash_val = sum(ord(character) for character in team_id)
        # Paleta de colores vivos y alegres de fútbol
        palette = [
            (255, 68, 68),    # Rojo brillante
            (0, 120, 255),    # Azul vibrante
            (255, 165, 0),    # Naranja energético
            (128, 0, 128),    # Púrpura real
            (0, 180, 180),    # Verde azulado
            (255, 215, 0),    # Oro campeón
            (180, 0, 0),      # Vinotinto clásico
            (0, 100, 80),     # Verde pasto profundo
            (255, 105, 180),  # Rosa alegre
            (70, 130, 180),   # Azul acero
            (154, 205, 50),   # Verde lima
            (210, 105, 30)    # Chocolate/marrón
        ]
        return palette[hash_val % len(palette)]
    except Exception as e_color:
        logger.warning(f"Error al calcular color del equipo para '{team_id}': {e_color}. Usando azul por defecto.")
        return (0, 191, 255)

def draw_team_shield(screen: pygame.Surface, pos: tuple[int, int], color: tuple[int, int, int]) -> None:
    """
    Dibuja un pequeño y vistoso escudo de fútbol (24x28 px) con el color de equipo.
    Implementa fallbacks para asegurar que el juego continúe aunque falle el renderizado.
    """
    try:
        x, y = pos
        # Puntos que definen la geometría del escudo de fútbol tradicional
        shield_points = [
            (x, y),
            (x + 24, y),
            (x + 24, y + 16),
            (x + 12, y + 28),
            (x, y + 16)
        ]
        # Dibujar relleno de color de equipo
        pygame.draw.polygon(screen, color, shield_points)
        # Dibujar borde blanco
        pygame.draw.polygon(screen, (255, 255, 255), shield_points, width=2)
        # Detalle de línea vertical decorativa en el centro del escudo
        pygame.draw.line(screen, (255, 255, 255), (x + 12, y), (x + 12, y + 26), width=1)
    except Exception as e_shield:
        logger.error(f"Error al dibujar escudo del equipo en pos {pos}: {e_shield}. Intentando dibujar círculo alternativo.")
        try:
            pygame.draw.circle(screen, color, (pos[0] + 12, pos[1] + 14), 12)
            pygame.draw.circle(screen, (255, 255, 255), (pos[0] + 12, pos[1] + 14), 12, width=2)
        except Exception as e_fallback:
            logger.critical(f"Fallo en fallback de dibujo de escudo: {e_fallback}")

def draw_happy_pitch(screen: pygame.Surface) -> None:
    """
    Dibuja un fondo de campo de fútbol alegre y vibrante (cancha verde con rayas y líneas de campo).
    Usa bloques try-except para asegurar que no falle la simulación del partido.
    """
    try:
        width, height = screen.get_size()
    except Exception as e_size:
        logger.error(f"Error al obtener tamaño de pantalla en draw_happy_pitch: {e_size}. Usando dimensiones por defecto.")
        width, height = 1280, 720

    try:
        # Colores vivos inspirados en una temática futbolera alegre
        color_verde_claro = (46, 204, 113) # Verde brillante
        color_verde_oscuro = (39, 174, 96) # Verde pasto
        
        # 1. Dibujar rayas horizontales en el césped para dar realismo
        num_rayas = 10
        alto_raya = height // num_rayas
        for i in range(num_rayas):
            color_seleccionado = color_verde_claro if i % 2 == 0 else color_verde_oscuro
            pygame.draw.rect(screen, color_seleccionado, (0, i * alto_raya, width, alto_raya))
            
        # 2. Dibujar líneas de campo clásicas (blanco suave)
        color_linea = (240, 248, 240)
        
        # Borde exterior de la cancha
        margen = 20
        pygame.draw.rect(screen, color_linea, (margen, margen, width - 2 * margen, height - 2 * margen), width=2)
        
        # Línea central
        medio_x = width // 2
        pygame.draw.line(screen, color_linea, (medio_x, margen), (medio_x, height - margen), width=2)
        
        # Círculo central y punto central
        pygame.draw.circle(screen, color_linea, (medio_x, height // 2), 80, width=2)
        pygame.draw.circle(screen, color_linea, (medio_x, height // 2), 6, width=0)
        
        # Áreas grandes e interiores
        # Área izquierda (Local)
        pygame.draw.rect(screen, color_linea, (margen, height // 2 - 120, 100, 240), width=2)
        pygame.draw.rect(screen, color_linea, (margen, height // 2 - 60, 40, 120), width=2)
        # Área derecha (Visitante)
        pygame.draw.rect(screen, color_linea, (width - margen - 100, height // 2 - 120, 100, 240), width=2)
        pygame.draw.rect(screen, color_linea, (width - margen - 40, height // 2 - 60, 40, 120), width=2)
        
    except Exception as e_draw:
        logger.error(f"Error al dibujar la cancha de fútbol: {e_draw}. Reintentando con color de fondo plano.")
        try:
            screen.fill((39, 174, 96))
        except Exception as e_fatal:
            logger.critical(f"Fallo crítico insalvable en draw_happy_pitch: {e_fatal}")

def draw_glass_panel(screen: pygame.Surface, rect: pygame.Rect, bg_color: tuple[int, int, int], border_color: tuple[int, int, int], alpha: int = 220) -> None:
    """
    Dibuja un panel moderno de cristal (glassmorphism) semi-transparente.
    Si falla, utiliza draw_panel estándar como fallback robusto.
    """
    try:
        rect_obj = pygame.Rect(rect)
        panel_surf = pygame.Surface((rect_obj.width, rect_obj.height), pygame.SRCALPHA)
        panel_surf.fill((*bg_color, alpha))
        screen.blit(panel_surf, rect_obj.topleft)
        pygame.draw.rect(screen, border_color, rect_obj, width=2, border_radius=8)
    except Exception as e_glass:
        logger.warning(f"Error al dibujar panel de cristal en rect {rect}: {e_glass}. Usando panel común.")
        try:
            draw_panel(screen, rect)
        except Exception as e_panel:
            logger.error(f"Error en fallback draw_panel de panel de cristal: {e_panel}. Dibujando rectángulo plano.")
            try:
                pygame.draw.rect(screen, bg_color, rect)
                pygame.draw.rect(screen, border_color, rect, width=2)
            except Exception as e_emerg:
                logger.critical(f"No se pudo completar el renderizado del panel: {e_emerg}")

def draw_tactical_board(screen: pygame.Surface, rect: pygame.Rect) -> None:
    """
    Dibuja un panel interactivo que imita una pizarra táctica escolar/de entrenador.
    Fondo verde pizarra, marco de madera y anotaciones de tiza decorativas.
    """
    try:
        rect_obj = pygame.Rect(rect)
        wood_color = (110, 55, 20)
        pygame.draw.rect(screen, wood_color, rect_obj, border_radius=12)
        
        board_rect = rect_obj.inflate(-20, -20)
        chalk_color = (33, 90, 50)
        pygame.draw.rect(screen, chalkboard_color if 'chalkboard_color' in locals() else chalk_color, board_rect, border_radius=8)
        
        white_chalk = (210, 230, 215)
        
        mid_y = board_rect.centery
        pygame.draw.line(screen, white_chalk, (board_rect.left, mid_y), (board_rect.right, mid_y), width=1)
        pygame.draw.circle(screen, white_chalk, board_rect.center, 50, width=1)
        
        arrow_start = (board_rect.left + 60, board_rect.bottom - 40)
        arrow_end = (board_rect.left + 90, board_rect.top + 60)
        pygame.draw.line(screen, white_chalk, arrow_start, arrow_end, width=2)
        pygame.draw.polygon(screen, white_chalk, [arrow_end, (arrow_end[0]-5, arrow_end[1]+8), (arrow_end[0]+5, arrow_end[1]+8)])
        
        pygame.draw.circle(screen, (230, 90, 90), (board_rect.right - 80, board_rect.top + 80), 8, width=2)
        px, py = board_rect.right - 110, board_rect.bottom - 80
        pygame.draw.line(screen, (100, 180, 240), (px - 6, py - 6), (px + 6, py + 6), width=2)
        pygame.draw.line(screen, (100, 180, 240), (px + 6, py - 6), (px - 6, py + 6), width=2)
        
    except Exception as e_board:
        logger.error(f"Error al dibujar pizarra táctica en rect {rect}: {e_board}. Reintentando con panel básico.")
        try:
            draw_panel(screen, rect)
        except Exception as e_fallback:
            logger.critical(f"Fallo total al intentar dibujar panel de pizarra: {e_fallback}")

def draw_tactical_option_button(screen: pygame.Surface, rect: pygame.Rect, text: str, hover: bool, border_color: tuple[int, int, int]) -> pygame.Rect:
    """
    Dibuja un botón de opción táctica de la pizarra con fondo oscuro y bordes coloreados interactivos.
    """
    try:
        button_rect = pygame.Rect(rect)
        bg_color = (25, 75, 40) if hover else (18, 55, 30)
        text_color = (255, 255, 255)
        
        pygame.draw.rect(screen, bg_color, button_rect, border_radius=6)
        
        border_width = 3 if hover else 1
        pygame.draw.rect(screen, border_color, button_rect, width=border_width, border_radius=6)
        
        font = get_font('md')
        text_surf = font.render(text, True, text_color)
        text_rect = text_surf.get_rect(center=button_rect.center)
        screen.blit(text_surf, text_rect)
        
        return button_rect
    except Exception as e_btn:
        logger.error(f"Error al dibujar botón táctico personalizado '{text}': {e_btn}. Usando botón estándar.")
        try:
            return draw_button(screen, rect, text, hover)
        except Exception as e_std:
            logger.critical(f"Fallo en dibujo estándar de botón táctico: {e_std}")
            return rect

# --- Simulación de otros partidos y Recuento de Tabla ═════════════════════════

def simular_otros_partidos(liga: Any, jornada_actual: int) -> None:
    """Simula los demás partidos de la jornada actual que no sean del usuario."""
    try:
        from alpha_football.engine import simular_partido
        
        partidos_jornada = [p for p in liga.calendario if p.jornada == jornada_actual]
        for p in partidos_jornada:
            if p.jugado:
                continue
            loc_eq = next((e for e in liga.equipos if e.id == p.local_id), None)
            vis_eq = next((e for e in liga.equipos if e.id == p.visitante_id), None)
            if loc_eq and vis_eq:
                res = simular_partido(loc_eq, vis_eq, con_eventos_caoticos=False)
                p.goles_local = res.goles_local
                p.goles_visitante = res.goles_visitante
                p.jugado = True
    except Exception as e:
        logger.error(f"Error al simular otros partidos de la jornada: {e}")

def actualizar_estadisticas_liga(liga: Any) -> None:
    """Recuenta los puntos y estadísticas de la tabla a partir del calendario."""
    try:
        for eq in liga.equipos:
            eq.puntos = 0
            eq.pj = 0
            eq.pg = 0
            eq.pe = 0
            eq.pp = 0
            eq.gf = 0
            eq.gc = 0
            
        for p in liga.calendario:
            if not p.jugado:
                continue
            loc_eq = next((e for e in liga.equipos if e.id == p.local_id), None)
            vis_eq = next((e for e in liga.equipos if e.id == p.visitante_id), None)
            if loc_eq and vis_eq:
                loc_eq.pj += 1
                vis_eq.pj += 1
                loc_eq.gf += p.goles_local
                loc_eq.gc += p.goles_visitante
                vis_eq.gf += p.goles_visitante
                vis_eq.gc += p.goles_local
                
                if p.goles_local > p.goles_visitante:
                    loc_eq.pg += 1
                    loc_eq.puntos += 3
                    vis_eq.pp += 1
                elif p.goles_visitante > p.goles_local:
                    vis_eq.pg += 1
                    vis_eq.puntos += 3
                    loc_eq.pp += 1
                else:
                    loc_eq.pe += 1
                    vis_eq.pe += 1
                    loc_eq.puntos += 1
                    vis_eq.puntos += 1
    except Exception as e:
        logger.error(f"Error al actualizar estadísticas de la tabla: {e}")

def recalcular_standings_copa(estado: dict) -> None:
    """Recalcula las posiciones de la fase de grupos de la Copa de forma robusta."""
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
    except Exception as err:
        logger.error(f"Fallo en recalcular_standings_copa: {err}")

# --- Renderizador de la Pantalla ══════════════════════════════════════════════

def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """
    Simula y anima el partido en vivo.
    Retorna "league_screen" al terminar, o None para seguir en pantalla.
    """
    try:
        liga = estado.get('liga')
        mi_equipo = estado.get('mi_equipo')
        match_mode = estado.get('match_mode', 'liga')

        if match_mode == 'copa':
            local = estado.get('partido_local_obj')
            visitante = estado.get('partido_visitante_obj')
            partido = estado.get('partido_copa_dict')
            if not partido:
                class StubPartido:
                    local_id = local.id if local else "local"
                    visitante_id = visitante.id if visitante else "visitante"
                    goles_local = 0
                    goles_visitante = 0
                    jugado = False
                partido = StubPartido()
        else:
            partido = estado.get('partido_actual')
            if not liga or not mi_equipo or not partido:
                logger.error("Faltan datos para simular el partido en el estado.")
                return "league_screen"
            local = next((e for e in liga.equipos if e.id == partido.local_id), None)
            visitante = next((e for e in liga.equipos if e.id == partido.visitante_id), None)

        if not local or not visitante:
            logger.error("No se encontraron los equipos del partido.")
            return "league_screen" if match_mode != 'copa' else "copa_screen"
            
        # 1. Simulación atómica al entrar
        if 'sim_resultado' not in estado:
            from alpha_football.engine import simular_partido
            res = simular_partido(local, visitante, con_eventos_caoticos=True)
            estado['sim_resultado'] = res
            estado['sim_minuto'] = 0
            estado['sim_goles_l'] = 0
            estado['sim_goles_v'] = 0
            estado['sim_comentarios'] = []
            estado['sim_eventos_procesados'] = []
            estado['sim_estado'] = 'jugando' # 'jugando', 'medio_tiempo', 'segundo_tiempo', 'finalizado'
            estado['sim_flash_goles'] = 0 # contador de frames para animación de gol
            estado['sim_goleador_flash'] = ""
            estado['sim_ajuste_realizado'] = False
            estado['sim_speed'] = 80 # ms por minuto simulado
            estado['sim_last_tick'] = pygame.time.get_ticks()
            
        res = estado['sim_resultado']
        minuto = estado['sim_minuto']
        goles_l = estado['sim_goles_l']
        goles_v = estado['sim_goles_v']
        sim_state = estado['sim_estado']
        
        # 2. Lógica del Ticker del Reloj
        now = pygame.time.get_ticks()
        if sim_state in ('jugando', 'segundo_tiempo') and estado['sim_flash_goles'] == 0:
            if now - estado['sim_last_tick'] >= estado['sim_speed']:
                estado['sim_minuto'] += 1
                minuto = estado['sim_minuto']
                estado['sim_last_tick'] = now
                
                # Comprobar eventos de este minuto
                eventos_este_min = [e for e in res.eventos if e['minuto'] == minuto]
                for e in eventos_este_min:
                    if e not in estado['sim_eventos_procesados']:
                        estado['sim_eventos_procesados'].append(e)
                        
                        # Agregar comentario a la lista de scroll
                        detalle = e['detalle']
                        tipo = e['tipo']
                        
                        if tipo == 'gol':
                            # Determinar quién anotó
                            equipo_gol_id = e['equipo_id']
                            goleador = "Goleador estrella"
                            scoring_team = local if equipo_gol_id == local.id else visitante
                            if scoring_team and scoring_team.jugadores:
                                possible_scorers = [j for j in scoring_team.jugadores if j.posicion in ('DEL', 'MED')]
                                if not possible_scorers:
                                    possible_scorers = scoring_team.jugadores
                                j_score = random.choice(possible_scorers)
                                goleador = j_score.nombre_completo
                                
                            if equipo_gol_id == local.id:
                                estado['sim_goles_l'] += 1
                                goles_l = estado['sim_goles_l']
                            else:
                                estado['sim_goles_v'] += 1
                                goles_v = estado['sim_goles_v']
                                
                            # Modificar detalle para incluir goleador
                            detalle = f"⚽ ¡GOOOL de {scoring_team.nombre}! {goleador} marca con clase. ({goles_l}-{goles_v})"
                            
                            # Disparar flash de gol
                            estado['sim_flash_goles'] = 25 # frames de duración
                            estado['sim_goleador_flash'] = f"{goleador.upper()} ({scoring_team.nombre.upper()})"
                            
                            # Inicializar confeti y animación alegre
                            try:
                                estado['sim_confeti'] = []
                                for _ in range(120):
                                    estado['sim_confeti'].append({
                                        'x': random.randint(20, SCREEN_W - 20),
                                        'y': random.randint(-150, 0),
                                        'vx': random.uniform(-3.0, 3.0),
                                        'vy': random.uniform(4.0, 9.0),
                                        'color': random.choice([
                                            (255, 215, 0),   # Dorado
                                            (0, 255, 136),   # Verde
                                            (0, 191, 255),   # Azul
                                            (255, 68, 68),    # Rojo
                                            (255, 255, 255), # Blanco
                                            (255, 105, 180)  # Rosa alegre
                                        ]),
                                        'size': random.randint(6, 14)
                                    })
                            except Exception as e_confetti:
                                logger.error(f"Error al inicializar confeti de gol: {e_confetti}")
                                
                        elif tipo == 'caotico':
                            detalle = f"⚠️ {detalle}"
                            
                        estado['sim_comentarios'].append(f"Min {minuto}: {detalle}")
                
                # Medio tiempo
                if minuto == 45 and sim_state == 'jugando':
                    estado['sim_estado'] = 'medio_tiempo'
                    sim_state = 'medio_tiempo'
                    
                # Fin del partido
                if minuto == 90:
                    estado['sim_estado'] = 'finalizado'
                    sim_state = 'finalizado'
                    
        # 3. Dibujar interfaz alegre de fútbol
        draw_happy_pitch(screen)
        
        # A. Scoreboard Grande con Glassmorphism y borde neón dorado
        board_rect = pygame.Rect(40, 20, 1200, 150)
        draw_glass_panel(screen, board_rect, bg_color=(10, 25, 20), border_color=(255, 215, 0), alpha=210)
        
        # Nombre de equipos truncados a 20 caracteres para evitar solapamiento con el marcador
        local_nombre_trunc = local.nombre[:20].upper()
        visitante_nombre_trunc = visitante.nombre[:20].upper()
        
        # Dibujar escudos decorativos al lado de los nombres de los equipos
        color_local = get_team_color(local.id)
        color_visitante = get_team_color(visitante.id)
        
        draw_team_shield(screen, (60, 48), color_local)
        draw_text(screen, local_nombre_trunc, (95, 50), size='lg', color='blanco')
        
        visitante_text_w = get_font('lg').size(visitante_nombre_trunc)[0]
        draw_team_shield(screen, (1220 - visitante_text_w - 35, 48), color_visitante)
        draw_text(screen, visitante_nombre_trunc, (1220 - visitante_text_w, 50), size='lg', color='blanco')
        
        # Marcador gigante
        marcador_str = f"{goles_l} - {goles_v}"
        m_w = get_font('xl').size(marcador_str)[0]
        draw_text(screen, marcador_str, (SCREEN_W // 2 - m_w // 2, 35), size='xl', color='dorado')
        
        # Reloj
        reloj_str = f"{minuto}'" if minuto < 90 else "FINAL"
        r_w = get_font('md').size(reloj_str)[0]
        draw_text(screen, reloj_str, (SCREEN_W // 2 - r_w // 2, 115), size='md', color='azul')
        
        # Barra de progreso del partido interactiva con pelotita corriendo
        try:
            progress_x_start = 80
            progress_x_end = 1200
            progress_width = progress_x_end - progress_x_start
            progress_y = 110
            
            # Fondo de la barra
            pygame.draw.line(screen, (40, 70, 50), (progress_x_start, progress_y), (progress_x_end, progress_y), width=6)
            
            # Progreso verde neón
            progreso_actual = min(1.0, max(0.0, minuto / 90.0))
            current_ball_x = int(progress_x_start + progreso_actual * progress_width)
            pygame.draw.line(screen, (0, 255, 136), (progress_x_start, progress_y), (current_ball_x, progress_y), width=6)
            
            # Pequeña pelotita corriendo sobre la barra
            pygame.draw.circle(screen, (255, 255, 255), (current_ball_x, progress_y), 8)
            pygame.draw.circle(screen, (0, 0, 0), (current_ball_x, progress_y), 8, width=1)
        except Exception as e_progress:
            logger.error(f"Error al dibujar barra de progreso del marcador: {e_progress}")
            
        # B. Panel de Comentarios Scrolling con Glassmorphism y borde azul
        comm_rect = pygame.Rect(40, 190, 1200, 360)
        draw_glass_panel(screen, comm_rect, bg_color=(12, 18, 36), border_color=(0, 191, 255), alpha=210)
        draw_text(screen, "TRANSMISIÓN MINUTO A MINUTO", (60, 205), size='sm', color='dorado')
        
        # Mostrar los últimos 9 comentarios con barra lateral estilizada y fondo translúcido
        try:
            comentarios_mostrar = estado['sim_comentarios'][-9:]
            cy = 245
            for c_text in comentarios_mostrar:
                # Elegir color y fondo según el tipo de evento de partido
                if "⚽" in c_text:
                    bar_color = (0, 255, 136)   # Verde neón para goles
                    bg_row_color = (15, 45, 30) # Fondo verde translúcido
                elif "⚠️" in c_text:
                    bar_color = (255, 68, 68)   # Rojo brillante para caos
                    bg_row_color = (45, 15, 20) # Fondo rojo translúcido
                else:
                    bar_color = (0, 191, 255)   # Azul celeste para juego
                    bg_row_color = (20, 26, 46) # Fondo azul oscuro translúcido
                
                # Dibujar fondo rectangular para la fila del comentario
                row_rect = pygame.Rect(60, cy - 2, 1160, 26)
                try:
                    row_surf = pygame.Surface((row_rect.width, row_rect.height), pygame.SRCALPHA)
                    row_surf.fill((*bg_row_color, 120))
                    screen.blit(row_surf, row_rect.topleft)
                except Exception:
                    pass
                
                # Dibujar barra vertical indicadora a la izquierda
                pygame.draw.line(screen, bar_color, (60, cy - 2), (60, cy + 24), width=3)
                
                # Mostrar el texto indentado
                draw_text(screen, c_text, (75, cy + 2), size='sm', color='blanco', shadow=True)
                cy += 30
        except Exception as e_comm_render:
            logger.error(f"Error al renderizar los comentarios del partido: {e_comm_render}")
            # Fallback simple
            comentarios_mostrar = estado.get('sim_comentarios', [])[-9:]
            cy = 245
            for c_text in comentarios_mostrar:
                draw_text(screen, c_text, (60, cy), size='sm', color='blanco')
                cy += 30
            
        # 4. Render de Modales (Goles y Medio Tiempo)
        mouse_pos = pygame.mouse.get_pos()
        click_pos = None
        
        # Procesar eventos
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "menu"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                click_pos = event.pos
                
        # A. Animación de Flash de Gol con Confeti y Balón Rebotando
        if estado['sim_flash_goles'] > 0:
            estado['sim_flash_goles'] -= 1
            
            # Dibujar un overlay blanco/amarillo festivo intermitente
            if estado['sim_flash_goles'] % 2 == 0:
                try:
                    flash_overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
                    flash_overlay.fill((255, 255, 200, 80)) # Toque amarillo alegre
                    screen.blit(flash_overlay, (0, 0))
                except Exception:
                    pass
            
            # Actualizar y dibujar confeti flotante alegre
            try:
                confeti_lista = estado.get('sim_confeti', [])
                for p in confeti_lista:
                    p['y'] += p['vy']
                    p['x'] += p['vx']
                    if p['x'] < 10 or p['x'] > SCREEN_W - 10:
                        p['vx'] = -p['vx']
                    pygame.draw.rect(screen, p['color'], (int(p['x']), int(p['y']), p['size'], p['size']))
            except Exception as e_confetti_update:
                logger.error(f"Error al procesar confeti de celebración de gol: {e_confetti_update}")
                
            # Banner gigante de GOOOL con diseño de franja de estadio
            gol_banner = pygame.Rect(0, SCREEN_H // 2 - 90, SCREEN_W, 180)
            pygame.draw.rect(screen, (0, 255, 136), gol_banner)
            pygame.draw.rect(screen, (255, 215, 0), gol_banner, width=6)
            
            # Dibujar balón de fútbol rebotando animado
            try:
                import math
                tick_anim = 25 - estado['sim_flash_goles']
                bounce_ratio = abs(math.sin(tick_anim * 0.25))
                bounce_y = int((SCREEN_H // 2 + 160) - bounce_ratio * 140)
                
                # Cuerpo de la pelota blanca
                pygame.draw.circle(screen, (255, 255, 255), (SCREEN_W // 2, bounce_y), 32)
                pygame.draw.circle(screen, (0, 0, 0), (SCREEN_W // 2, bounce_y), 32, width=2)
                # Dibujar gajos decorativos
                pygame.draw.circle(screen, (0, 0, 0), (SCREEN_W // 2, bounce_y), 10)
                for angle in range(0, 360, 72):
                    rad = (angle + tick_anim * 8) * math.pi / 180.0
                    target_x = int(SCREEN_W // 2 + 22 * math.cos(rad))
                    target_y = int(bounce_y + 22 * math.sin(rad))
                    pygame.draw.line(screen, (0, 0, 0), (SCREEN_W // 2, bounce_y), (target_x, target_y), width=2)
            except Exception as e_ball_anim:
                logger.error(f"Error al animar balón de gol: {e_ball_anim}")
                
            # Texto animado de ¡GOOOL! con sombra
            t1 = "¡¡¡GOOOOOOOOOOL!!!"
            t1_w = get_font('xl').size(t1)[0]
            draw_text(screen, t1, (SCREEN_W // 2 - t1_w // 2, SCREEN_H // 2 - 70), size='xl', color='bg', shadow=False)
            
            t2 = estado['sim_goleador_flash']
            t2_w = get_font('lg').size(t2)[0]
            draw_text(screen, t2, (SCREEN_W // 2 - t2_w // 2, SCREEN_H // 2 + 15), size='lg', color='bg', shadow=False)
            
        # B. Medio Tiempo Interactividad con Pizarra Táctica y Estilo Pizarra/Madera
        elif sim_state == 'medio_tiempo':
            # Capa de oscurecimiento verde oscuro translúcido
            try:
                mid_overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
                mid_overlay.fill((10, 40, 20, 180))
                screen.blit(mid_overlay, (0, 0))
            except Exception:
                pass
            
            # Pizarra táctica de entrenador
            panel_mid = pygame.Rect(SCREEN_W // 2 - 320, SCREEN_H // 2 - 220, 640, 440)
            draw_tactical_board(screen, panel_mid)
            
            draw_text(screen, "MEDIO TIEMPO — CHARLA TÁCTICA", (SCREEN_W // 2 - 280, SCREEN_H // 2 - 190), size='lg', color='dorado')
            draw_text(screen, "Selecciona una estrategia para la segunda mitad:", (SCREEN_W // 2 - 280, SCREEN_H // 2 - 145), size='sm', color='blanco')
            
            # Botones tácticos rediseñados como tarjetas de la pizarra
            b1 = pygame.Rect(SCREEN_W // 2 - 280, SCREEN_H // 2 - 90, 560, 45)
            b2 = pygame.Rect(SCREEN_W // 2 - 280, SCREEN_H // 2 - 35, 560, 45)
            b3 = pygame.Rect(SCREEN_W // 2 - 280, SCREEN_H // 2 + 20, 560, 45)
            b4 = pygame.Rect(SCREEN_W // 2 - 280, SCREEN_H // 2 + 75, 560, 45)
            
            hov1 = b1.collidepoint(mouse_pos)
            hov2 = b2.collidepoint(mouse_pos)
            hov3 = b3.collidepoint(mouse_pos)
            hov4 = b4.collidepoint(mouse_pos)
            
            # Dibujamos las opciones con bordes de color neón y texto
            draw_tactical_option_button(screen, b1, "1. CHARLA MOTIVACIONAL (+Moral del equipo)", hov1, border_color=(255, 215, 0))
            draw_tactical_option_button(screen, b2, "2. PLANTEAMIENTO OFENSIVO (+Ocasiones de Gol)", hov2, border_color=(255, 68, 68))
            draw_tactical_option_button(screen, b3, "3. AUTOBÚS ATRÁS (Cerrar filas defensivas)", hov3, border_color=(0, 191, 255))
            draw_tactical_option_button(screen, b4, "4. MANTENER PLAN DE JUEGO ORIGINAL", hov4, border_color=(255, 255, 255))
            
            if click_pos:
                # Aplicamos la estrategia elegida alterando sutilmente la simulación
                if b1.collidepoint(click_pos):
                    # Charla motivacional
                    for j in mi_equipo.jugadores:
                        j.moral = min(100, j.moral + 15)
                    estado['sim_comentarios'].append("DT: Charla motivacional exitosa. ¡Los jugadores salen motivados!")
                elif b2.collidepoint(click_pos):
                    # Más agresividad (Añadimos gol al usuario con 65% probabilidad o forzamos el marcador)
                    if random.random() < 0.65:
                        if mi_equipo.id == local.id:
                            estado['sim_goles_l'] += 1
                        else:
                            estado['sim_goles_v'] += 1
                        estado['sim_comentarios'].append("DT: Planteamiento ofensivo de riesgo. ¡Marcamos de contra!")
                    else:
                        estado['sim_comentarios'].append("DT: Intentamos buscar el arco rival con todo, sin fortuna.")
                elif b3.collidepoint(click_pos):
                    # Autobús atrás (Si el rival iba a meter gol en el segundo tiempo, le bajamos un gol)
                    # En la práctica, si el rival tiene goles > 0, quitamos uno para representar solidez defensiva
                    if mi_equipo.id == local.id and estado['sim_goles_v'] > 0:
                        estado['sim_goles_v'] -= 1
                    elif mi_equipo.id == visitante.id and estado['sim_goles_l'] > 0:
                        estado['sim_goles_l'] -= 1
                    estado['sim_comentarios'].append("DT: Cerramos filas en defensa. Planteamiento de contención.")
                elif b4.collidepoint(click_pos):
                    estado['sim_comentarios'].append("DT: Seguimos con el plan de juego original.")
                    
                # Reanudar
                estado['sim_estado'] = 'segundo_tiempo'
                estado['sim_last_tick'] = pygame.time.get_ticks()
                
        # C. Pantalla Finalizada
        elif sim_state == 'finalizado':
            # Panel inferior de navegación para volver con estilo Glassmorphism
            panel_vol = pygame.Rect(40, 570, 1200, 80)
            draw_glass_panel(screen, panel_vol, bg_color=(20, 30, 50), border_color=(255, 215, 0), alpha=210)
            
            draw_text(screen, "¡PARTIDO FINALIZADO!", (60, 595), size='lg', color='dorado')
            
            # Mostrar resumen del resultado para el usuario de forma vistosa
            try:
                user_is_local = (mi_equipo.id == local.id)
                user_goles = goles_l if user_is_local else goles_v
                rival_goles = goles_v if user_is_local else goles_l
                
                if user_goles > rival_goles:
                    resultado_str = "🏆 ¡VICTORIA DE ALTA CLASE!"
                    res_color = 'verde'
                elif user_goles < rival_goles:
                    resultado_str = "💔 DERROTA... ¡A SEGUIR LUCHANDO!"
                    res_color = 'rojo'
                else:
                    resultado_str = "🤝 EMPATE DISPUTADO Y VALIOSO"
                    res_color = 'azul'
                draw_text(screen, resultado_str, (320, 595), size='md', color=res_color)
            except Exception as e_res_summary:
                logger.error(f"Error al resumir resultado en pantalla finalizada: {e_res_summary}")
            
            btn_exit = pygame.Rect(1000, 585, 220, 50)
            hov_exit = btn_exit.collidepoint(mouse_pos)
            draw_button(screen, btn_exit, "VOLVER A LA LIGA", hov_exit)
            
            if click_pos and btn_exit.collidepoint(click_pos):
                if match_mode == 'copa':
                    # Guardar resultado del partido de copa
                    partido_copa = estado.get('partido_copa_dict')
                    if partido_copa: # Fase de grupos
                        partido_copa['goles_l'] = goles_l
                        partido_copa['goles_v'] = goles_v
                        partido_copa['jugado'] = True
                        recalcular_standings_copa(estado)
                    else: # Fase de eliminatoria directa
                        fase_actual = estado.get('partido_copa_bracket_fase')
                        if fase_actual and 'copa_bracket' in estado:
                            fase_data = estado['copa_bracket'][fase_actual]
                            fase_data['goles_l'] = goles_l
                            fase_data['goles_v'] = goles_v
                            fase_data['jugado'] = True
                            
                            if goles_l == goles_v:
                                if random.random() < 0.55:
                                    fase_data['avanza'] = 'user'
                                    fase_data['penales'] = '5-4'
                                else:
                                    fase_data['avanza'] = 'rival'
                                    fase_data['penales'] = '4-5'
                            else:
                                if goles_l > goles_v:
                                    fase_data['avanza'] = 'user'
                                else:
                                    fase_data['avanza'] = 'rival'
                                    
                            # Si el usuario avanza, mover la copa a la siguiente fase
                            if fase_data['avanza'] == 'user':
                                fases = ['octavos', 'cuartos', 'semis', 'final']
                                if fase_actual in fases:
                                    curr_idx = fases.index(fase_actual)
                                    if curr_idx < len(fases) - 1:
                                        estado['copa_fase_actual'] = fases[curr_idx + 1]
                                    else:
                                        estado['copa_fase_actual'] = 'campeon'
                            else:
                                estado['copa_fase_actual'] = 'eliminado'

                    # Limpiar variables de simulación de este partido
                    estado.pop('sim_resultado', None)
                    estado.pop('sim_minuto', None)
                    estado.pop('sim_goles_l', None)
                    estado.pop('sim_goles_v', None)
                    estado.pop('sim_comentarios', None)
                    estado.pop('sim_eventos_procesados', None)
                    estado.pop('sim_estado', None)
                    estado.pop('match_mode', None)
                    estado.pop('partido_local_obj', None)
                    estado.pop('partido_visitante_obj', None)
                    estado.pop('partido_copa_dict', None)
                    estado.pop('partido_copa_bracket_fase', None)
                    
                    return "copa_screen"
                else:
                    # Guardamos los goles oficiales de liga
                    partido.goles_local = goles_l
                    partido.goles_visitante = goles_v
                    partido.jugado = True
                    
                    # Simular los otros partidos de la jornada
                    simular_otros_partidos(liga, liga.jornada_actual)
                    
                    # Recuento de la tabla a partir de todos los partidos jugados
                    actualizar_estadisticas_liga(liga)
                    
                    # Avanzar jornada
                    if liga.jornada_actual < liga.num_jornadas:
                        liga.jornada_actual += 1
                    else:
                        logger.info("Fin de temporada alcanzado.")
                        
                    # Limpiar variables de simulación de este partido
                    estado.pop('sim_resultado', None)
                    estado.pop('sim_minuto', None)
                    estado.pop('sim_goles_l', None)
                    estado.pop('sim_goles_v', None)
                    estado.pop('sim_comentarios', None)
                    estado.pop('sim_eventos_procesados', None)
                    estado.pop('sim_estado', None)
                    
                    return "league_screen"
                
        return None
    except Exception as e:
        logger.error(f"Error crítico en render de match_screen: {e}")
        return "league_screen"
