# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Submenú Pre-Partido (Pygame).

Al pulsar "JUGAR JORNADA", jugar Copa o amistoso, se abre este menú con 3 opciones:
  1. Jugar partido          -> simulación en vivo (match_screen)
  2. Simular instantáneamente-> resuelve el partido al instante y cierra la jornada/copa
  3. Dirección equipo        -> team_screen (formación / táctica / once)
"""
from __future__ import annotations

import logging
from typing import Optional
import pygame
import random

try:
    from alpha_football.ui.theme import (
        SCREEN_W, SCREEN_H, COLORS, get_font, draw_gradient_bg, draw_panel, draw_button, draw_text
    )
except Exception:
    SCREEN_W, SCREEN_H = 1280, 720
    COLORS = {'bg': (10, 14, 26), 'verde': (0, 255, 136), 'dorado': (255, 215, 0),
              'rojo': (255, 68, 68), 'azul': (0, 191, 255), 'blanco': (255, 255, 255), 'panel': (20, 26, 46)}
    def get_font(size): return pygame.font.Font(None, 24)
    def draw_gradient_bg(screen): screen.fill((10, 14, 26))
    def draw_panel(screen, rect): pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=8)
    def draw_button(screen, rect, text, hover): pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=6); return rect
    def draw_text(screen, text, pos, size='md', color='blanco', shadow=True): pass

logger = logging.getLogger(__name__)


def _simular_instantaneo(estado: dict, local: any, visitante: any) -> None:
    """Resuelve el partido al instante de forma segura y consistente según el match_mode."""
    try:
        match_mode = estado.get('match_mode', 'liga')
        mi_equipo = estado.get('mi_equipo')
        from alpha_football.engine import simular_partido
        
        # Simular el partido usando el motor
        res = simular_partido(local, visitante)
        gl, gv = res.goles_local, res.goles_visitante
        goles_ev = [e for e in getattr(res, 'eventos', []) if e.get('tipo') == 'gol']
        
        if match_mode == 'liga':
            liga = estado.get('liga')
            partido = estado.get('partido_actual')
            if not liga or not partido:
                return
                
            estado['prepartido_resultado'] = {
                'titulo': f"{getattr(local, 'corto', local.nombre)} {gl} - {gv} {getattr(visitante, 'corto', visitante.nombre)}",
                'goles': [f"{e.get('minuto', 0)}'  {e.get('detalle', 'Gol')}" for e in sorted(goles_ev, key=lambda x: x.get('minuto', 0))],
            }
            
            # Desarrollo de la plantilla del usuario
            try:
                from alpha_football.desarrollo import desarrollar_plantilla_post_partido
                user_is_local = (mi_equipo.id == local.id)
                gf = gl if user_is_local else gv
                gc = gv if user_is_local else gl
                desarrollar_plantilla_post_partido(mi_equipo, gf, gc)
            except Exception as e_dev:
                logger.error(f"Error de desarrollo en sim instantánea de liga: {e_dev}")
                
            # Cierre de jornada en liga
            from alpha_football.ui.match_screen import finalizar_jornada_liga
            finalizar_jornada_liga(estado, liga, mi_equipo, partido, gl, gv)
            
        elif match_mode == 'copa':
            partido_copa = estado.get('partido_copa_dict')
            penales_str = None
            
            if partido_copa: # Fase de grupos
                partido_copa['goles_l'] = gl
                partido_copa['goles_v'] = gv
                partido_copa['jugado'] = True
                from alpha_football.ui.match_screen import recalcular_standings_copa
                recalcular_standings_copa(estado)
            else: # Fase de eliminatoria directa (Bracket)
                fase_actual = estado.get('partido_copa_bracket_fase')
                if fase_actual and 'copa_bracket' in estado:
                    fase_data = estado['copa_bracket'][fase_actual]
                    fase_data['goles_l'] = gl
                    fase_data['goles_v'] = gv
                    fase_data['jugado'] = True
                    
                    if gl == gv:
                        # Tanda de penales simulada por atributos
                        from alpha_football.engine import tanda_penales_jugadores
                        cobradores_l = sorted(local.jugadores, key=lambda j: j.penales, reverse=True)[:5]
                        cobradores_v = sorted(visitante.jugadores, key=lambda j: j.penales, reverse=True)[:5]
                        marcador, gana_local = tanda_penales_jugadores(cobradores_l, cobradores_v)
                        penales_str = marcador
                        fase_data['avanza'] = 'user' if gana_local else 'rival'
                        fase_data['penales'] = penales_str
                    else:
                        fase_data['avanza'] = 'user' if gl > gv else 'rival'
                    
                    # Avanzar de fase si el usuario ganó
                    if fase_data['avanza'] == 'user':
                        fases = ['cuartos', 'semis', 'final']
                        if fase_actual in fases:
                            curr_idx = fases.index(fase_actual)
                            if curr_idx < len(fases) - 1:
                                estado['copa_fase_actual'] = fases[curr_idx + 1]
                            else:
                                estado['copa_fase_actual'] = 'campeon'
                    else:
                        estado['copa_fase_actual'] = 'eliminado'
            
            # Desarrollo de la plantilla en Copa si el usuario es participante
            if mi_equipo and (mi_equipo.id == local.id or mi_equipo.id == visitante.id):
                try:
                    from alpha_football.desarrollo import desarrollar_plantilla_post_partido
                    user_is_local = (mi_equipo.id == local.id)
                    gf = gl if user_is_local else gv
                    gc = gv if user_is_local else gl
                    desarrollar_plantilla_post_partido(mi_equipo, gf, gc)
                except Exception as e_dev:
                    logger.error(f"Error de desarrollo en sim instantánea copa: {e_dev}")
            
            estado['prepartido_resultado'] = {
                'titulo': f"{local.corto} {gl} - {gv} {visitante.corto}" + (f" ({penales_str} PEN)" if penales_str else ""),
                'goles': [f"{e.get('minuto', 0)}'  {e.get('detalle', 'Gol')}" for e in sorted(goles_ev, key=lambda x: x.get('minuto', 0))],
            }
            
            # Limpiar variables temporales de copa
            estado.pop('partido_copa_dict', None)
            estado.pop('partido_copa_bracket_fase', None)
            
        elif match_mode == 'amistoso':
            # Amistoso no tiene consecuencias de liga/copa ni desarrollo de plantilla
            estado['prepartido_resultado'] = {
                'titulo': f"{local.corto} {gl} - {gv} {visitante.corto}",
                'goles': [f"{e.get('minuto', 0)}'  {e.get('detalle', 'Gol')}" for e in sorted(goles_ev, key=lambda x: x.get('minuto', 0))],
            }
            
    except Exception as e:
        logger.error(f"Error en simulación instantánea general: {e}")


def _render_resultado(screen: pygame.Surface, estado: dict, mouse_pos, click_pos) -> Optional[str]:
    """Muestra el marcador y los goleadores tras una simulación instantánea."""
    r = estado.get('prepartido_resultado') or {}
    draw_gradient_bg(screen)
    draw_text(screen, "RESULTADO", (SCREEN_W // 2 - 110, 55), size='xl', color='dorado')

    panel = pygame.Rect(SCREEN_W // 2 - 360, 130, 720, 90)
    draw_panel(screen, panel)
    titulo = r.get('titulo', '0 - 0')
    tw = get_font('xl').size(titulo)[0]
    draw_text(screen, titulo, (SCREEN_W // 2 - tw // 2, 150), size='xl', color='verde')

    gp = pygame.Rect(SCREEN_W // 2 - 360, 240, 720, 330)
    draw_panel(screen, gp)
    draw_text(screen, "GOLES", (gp.x + 20, gp.y + 12), size='md', color='azul')
    y = gp.y + 50
    goles = r.get('goles', [])
    if not goles:
        draw_text(screen, "Sin goles.", (gp.x + 20, y), size='sm', color='blanco')
    for linea in goles[:9]:
        draw_text(screen, linea[:84], (gp.x + 20, y), size='sm', color='blanco')
        y += 30

    btn = pygame.Rect(SCREEN_W // 2 - 120, 588, 240, 52)
    draw_button(screen, btn, "CONTINUAR", btn.collidepoint(mouse_pos))
    if click_pos and btn.collidepoint(click_pos):
        estado.pop('prepartido_resultado', None)
        mode = estado.get('match_mode', 'liga')
        estado.pop('match_mode', None)
        if mode == 'copa':
            return "copa_screen"
        elif mode == 'amistoso':
            return "menu"
        return "league_screen"
    return None


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    try:
        liga = estado.get('liga')
        mi_equipo = estado.get('mi_equipo')
        partido = estado.get('partido_actual')
        match_mode = estado.get('match_mode', 'liga')

        # Determinar equipos local y visitante según el ámbito del partido
        if match_mode == 'liga':
            if not liga or not mi_equipo or not partido:
                return "league_screen"
            local = next((e for e in liga.equipos if e.id == partido.local_id), None)
            visitante = next((e for e in liga.equipos if e.id == partido.visitante_id), None)
        elif match_mode == 'copa':
            local = estado.get('partido_local_obj')
            visitante = estado.get('partido_visitante_obj')
        elif match_mode == 'amistoso':
            local = estado.get('amis_local')
            visitante = estado.get('amis_visitante')
        else:
            return "menu"

        if not local or not visitante:
            return "menu"

        mouse_pos = pygame.mouse.get_pos()
        click_pos = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "menu"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                click_pos = event.pos

        # Tras una simulación instantánea, mostrar el resultado y los goleadores.
        if estado.get('prepartido_resultado'):
            return _render_resultado(screen, estado, mouse_pos, click_pos)

        draw_gradient_bg(screen)
        draw_text(screen, "PREPARAR PARTIDO", (SCREEN_W // 2 - 180, 70), size='xl', color='dorado')

        # Cartel del enfrentamiento
        panel = pygame.Rect(SCREEN_W // 2 - 320, 140, 640, 130)
        draw_panel(screen, panel)
        l_name = (getattr(local, 'corto', None) or (local.nombre if local else "Local"))
        v_name = (getattr(visitante, 'corto', None) or (visitante.nombre if visitante else "Visitante"))
        draw_text(screen, l_name, (panel.x + 30, panel.y + 25), size='lg', color='verde')
        draw_text(screen, "VS", (SCREEN_W // 2 - 18, panel.y + 28), size='lg', color='blanco')
        v_w = get_font('lg').size(v_name)[0]
        draw_text(screen, v_name, (panel.right - 30 - v_w, panel.y + 25), size='lg', color='rojo')

        # Mostrar estilos tácticos del DT de cada equipo
        estilo_l = f"Estilo: {getattr(local, 'estilo_dt', 'Equilibrado').capitalize()}"
        estilo_v = f"Estilo: {getattr(visitante, 'estilo_dt', 'Equilibrado').capitalize()}"
        v_estilo_w = get_font('sm').size(estilo_v)[0]
        draw_text(screen, estilo_l, (panel.x + 30, panel.y + 80), size='sm', color='blanco')
        draw_text(screen, estilo_v, (panel.right - 30 - v_estilo_w, panel.y + 80), size='sm', color='blanco')

        # Botones de opción
        btn_jugar = pygame.Rect(SCREEN_W // 2 - 260, 290, 520, 60)
        btn_sim = pygame.Rect(SCREEN_W // 2 - 260, 370, 520, 60)
        btn_dir = pygame.Rect(SCREEN_W // 2 - 260, 450, 520, 60)
        btn_volver = pygame.Rect(SCREEN_W // 2 - 125, 550, 250, 48)

        draw_button(screen, btn_jugar, "1. JUGAR PARTIDO (en vivo)", btn_jugar.collidepoint(mouse_pos))
        draw_button(screen, btn_sim, "2. SIMULAR INSTANTÁNEAMENTE", btn_sim.collidepoint(mouse_pos))
        
        # Deshabilitar dirección de equipo en amistoso si no hay carrera cargada
        dir_hab = (mi_equipo is not None)
        draw_button(screen, btn_dir, "3. DIRECCIÓN DE EQUIPO" if dir_hab else "3. DIRECCIÓN DE EQUIPO [Bloqueado]", btn_dir.collidepoint(mouse_pos) and dir_hab)
        
        draw_button(screen, btn_volver, "VOLVER", btn_volver.collidepoint(mouse_pos))

        if click_pos:
            if btn_jugar.collidepoint(click_pos):
                estado.pop('sim_resultado', None)
                estado.pop('sim_estado', None)
                return "match_screen"
            elif btn_sim.collidepoint(click_pos):
                _simular_instantaneo(estado, local, visitante)
            elif btn_dir.collidepoint(click_pos) and dir_hab:
                return "team_screen"
            elif btn_volver.collidepoint(click_pos):
                if match_mode == 'copa':
                    return "copa_screen"
                elif match_mode == 'amistoso':
                    return "menu"
                return "league_screen"
        return None
    except Exception as e:
        logger.error(f"Error en prepartido_screen: {e}")
        return "menu"
