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


def _ovr_dots_render(screen, ovr, x, y, side='left'):
    """
    v0.8.3: dibuja 5+5 esferitas para visualizar el OVR antes del partido.
    - 5 esferas base en gris (representan OVR ~70).
    - Cada esfera blanca añadida = +2 OVR sobre la base.
    - Cada esfera roja faltante = -2 OVR bajo la base.
    Lado 'left' = las esferas se alinean hacia la derecha desde x; lado 'right' = hacia la izquierda.
    """
    try:
        DOT_R = 7
        DOT_GAP = 4
        # Base OVR ~70. Cada +2 OVR = una esfera blanca extra (hasta 10 esferas max).
        base = 70
        # Calcular número de esferas blancas y rojas
        delta = ovr - base
        blancas = max(0, min(5, int(delta // 2) + 5 // 2))  # centro en 5
        rojas = max(0, min(5, 5 - (int(delta // 2) + 5 // 2)))
        # Si OVR es muy bajo (< 65), puede haber menos de 5 grises
        grises = 10 - blancas - rojas
        # Construir la lista de colores: empezamos con [rojas] luego [5 grises] luego [blancas]
        colores = ([(220, 60, 60)] * rojas
                   + [(80, 80, 95)] * grises
                   + [(255, 255, 255)] * blancas)
        # Limitar a 10 esferas totales
        colores = colores[:10]
        if not colores:
            return
        total_w = len(colores) * (DOT_R * 2 + DOT_GAP) - DOT_GAP
        if side == 'right':
            start_x = x - total_w + DOT_R
            for i, color in enumerate(colores):
                cx = start_x + i * (DOT_R * 2 + DOT_GAP)
                try:
                    pygame.draw.circle(screen, color, (cx, y), DOT_R)
                    pygame.draw.circle(screen, (10, 14, 26), (cx, y), DOT_R, width=1)
                except Exception:
                    pass
        else:
            start_x = x
            for i, color in enumerate(colores):
                cx = start_x + i * (DOT_R * 2 + DOT_GAP)
                try:
                    pygame.draw.circle(screen, color, (cx, y), DOT_R)
                    pygame.draw.circle(screen, (10, 14, 26), (cx, y), DOT_R, width=1)
                except Exception:
                    pass
    except Exception as e:
        logger.error(f"Error en _ovr_dots_render: {e}")


def _simular_instantaneo(estado: dict, local: any, visitante: any) -> None:
    """Resuelve el partido al instante de forma segura y consistente según el match_mode."""
    try:
        # v0.8.4: `or 'liga'` — nueva carrera deja match_mode=None y el default de .get no aplica.
        match_mode = estado.get('match_mode') or 'liga'
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
                        # v0.8.7: la firma ahora devuelve (gana_local, marcador, secuencia)
                        gana_local, marcador, secuencia = tanda_penales_jugadores(cobradores_l, cobradores_v)
                        penales_str = marcador
                        fase_data['avanza'] = 'user' if gana_local else 'rival'
                        fase_data['penales'] = penales_str
                        fase_data['penales_secuencia'] = secuencia
                        fase_data['penales_cobradores_l'] = [getattr(j, 'apellido', '?') for j in cobradores_l]
                        fase_data['penales_cobradores_v'] = [getattr(j, 'apellido', '?') for j in cobradores_v]
                    else:
                        fase_data['avanza'] = 'user' if gl > gv else 'rival'
                    
                    # v0.8.6 (Tarea 5): si el usuario avanza, llamar a avanzar_fase_bracket
                    # para simular los OTROS partidos de esta fase y construir la siguiente llave.
                    if fase_data['avanza'] == 'user':
                        if fase_actual in ('cuartos', 'semis'):
                            try:
                                from alpha_football.ui.copa_screen import avanzar_fase_bracket
                                avanzar_fase_bracket(estado)
                            except Exception as e_avz:
                                logger.error(f"Error al avanzar fase del bracket (sim inst): {e_avz}")
                                fases_fb = ['cuartos', 'semis', 'final']
                                curr_idx = fases_fb.index(fase_actual)
                                if curr_idx < len(fases_fb) - 1:
                                    estado['copa_fase_actual'] = fases_fb[curr_idx + 1]
                        elif fase_actual == 'final':
                            estado['copa_fase_actual'] = 'campeon'
                            estado['copa_mejor_fase_temp'] = 'Campeón'
                    else:
                        estado['copa_fase_actual'] = 'eliminado'
                        # v0.8.1: tracking de la mejor fase alcanzada
                        # v0.8.2: defensivo contra None/valores no-string
                        fase_label = {'cuartos': 'Cuartos', 'semis': 'Semifinal',
                                      'final': 'Finalista', 'grupos': 'Fase de grupos'}
                        _mejor_fase_actual = estado.get('copa_mejor_fase_temp') or ''
                        if not _mejor_fase_actual or _mejor_fase_actual in ('No clasificó', 'Fase de grupos') or fase_actual not in _mejor_fase_actual:
                            estado['copa_mejor_fase_temp'] = fase_label.get(fase_actual, 'Fase de grupos')
            
            # v0.8.6 (Tarea 4+5): desarrollo de AMBOS equipos en copa y registro de stats
            try:
                from alpha_football.desarrollo import desarrollar_plantilla_post_partido
                rep_l = desarrollar_plantilla_post_partido(local, gl, gv)
                rep_v = desarrollar_plantilla_post_partido(visitante, gv, gl)
                # Registrar estadísticas de copa
                try:
                    from alpha_football.ui.copa_screen import registrar_stats_copa
                    registrar_stats_copa(estado, getattr(local, 'nombre', ''), gv, rep_l)
                    registrar_stats_copa(estado, getattr(visitante, 'nombre', ''), gl, rep_v)
                except Exception:
                    pass
            except Exception as e_dev:
                logger.error(f"Error de desarrollo en sim instantánea copa: {e_dev}")
            
            # v0.8.7: si hubo penales, agregamos la secuencia y los cobradores
            # para que la UI de resultado los muestre ronda a ronda.
            penales_payload = None
            if penales_str:
                try:
                    fase_actual = estado.get('partido_copa_bracket_fase')
                    fase_data = estado.get('copa_bracket', {}).get(fase_actual) or {}
                    penales_payload = {
                        'marcador': penales_str,
                        'secuencia': fase_data.get('penales_secuencia', []) or [],
                        'cobrador_l': fase_data.get('penales_cobradores_l', []) or [],
                        'cobrador_v': fase_data.get('penales_cobradores_v', []) or [],
                    }
                except Exception:
                    penales_payload = {'marcador': penales_str, 'secuencia': [], 'cobrador_l': [], 'cobrador_v': []}
            estado['prepartido_resultado'] = {
                'titulo': f"{local.corto} {gl} - {gv} {visitante.corto}" + (f" ({penales_str} PEN)" if penales_str else ""),
                'goles': [f"{e.get('minuto', 0)}'  {e.get('detalle', 'Gol')}" for e in sorted(goles_ev, key=lambda x: x.get('minuto', 0))],
                'penales': penales_payload,
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
    """Muestra el marcador y los goleadores tras una simulación instantánea.
    v0.8.7: si el partido terminó en empate y se jugó tanda de penales (modo
    copa en eliminación directa), agrega un panel lateral con la secuencia
    ronda a ronda y los nombres de los cobradores.
    """
    r = estado.get('prepartido_resultado') or {}
    draw_gradient_bg(screen)
    draw_text(screen, "RESULTADO", (SCREEN_W // 2 - 110, 55), size='xl', color='dorado')

    panel = pygame.Rect(SCREEN_W // 2 - 360, 130, 720, 90)
    draw_panel(screen, panel)
    titulo = r.get('titulo', '0 - 0')
    tw = get_font('xl').size(titulo)[0]
    draw_text(screen, titulo, (SCREEN_W // 2 - tw // 2, 150), size='xl', color='verde')

    # v0.8.7: layout con DOS paneles (goles + penales) si hubo penales, o
    # UN panel ancho (goles) si no los hubo.
    penales = r.get('penales')
    if penales and penales.get('secuencia'):
        gp = pygame.Rect(40, 240, 590, 400)
        draw_panel(screen, gp)
        draw_text(screen, "GOLES", (gp.x + 20, gp.y + 12), size='md', color='azul')
        y = gp.y + 50
        goles = r.get('goles', [])
        if not goles:
            draw_text(screen, "Sin goles en el tiempo regular.", (gp.x + 20, y), size='sm', color='blanco')
        for linea in goles[:9]:
            draw_text(screen, linea[:78], (gp.x + 20, y), size='sm', color='blanco')
            y += 30

        # Panel de penales a la derecha
        pp = pygame.Rect(650, 240, 590, 400)
        draw_panel(screen, pp)
        pp_title = f"DEFINICIÓN POR PENALES — {penales.get('marcador', '?')}"
        draw_text(screen, pp_title, (pp.x + 20, pp.y + 12), size='md', color='dorado')
        # Encabezado: cobradores
        cob_l = penales.get('cobrador_l', []) or []
        cob_v = penales.get('cobrador_v', []) or []
        header_y = pp.y + 42
        draw_text(screen, "COBRADORES (local)", (pp.x + 20, header_y), size='sm', color='verde')
        draw_text(screen, "COBRADORES (visit.)", (pp.x + 320, header_y), size='sm', color='rojo')
        cob_l_txt = "  ·  ".join(cob_l[:5]) if cob_l else "—"
        cob_v_txt = "  ·  ".join(cob_v[:5]) if cob_v else "—"
        draw_text(screen, cob_l_txt[:46], (pp.x + 20, header_y + 20), size='sm', color='blanco')
        draw_text(screen, cob_v_txt[:46], (pp.x + 320, header_y + 20), size='sm', color='blanco')

        # Línea separadora
        try:
            pygame.draw.line(screen, COLORS.get('azul', (0, 191, 255)),
                             (pp.x + 20, header_y + 50), (pp.right - 20, header_y + 50), 1)
        except Exception:
            pass

        # Secuencia ronda a ronda
        draw_text(screen, "SECUENCIA (local ⚽ / visitante ⚽)", (pp.x + 20, header_y + 60), size='sm', color='azul')
        seq = penales['secuencia'][:10]
        col_x_l = pp.x + 24
        col_x_v = pp.x + 70
        col_x_n = pp.x + 130
        ronda_y = header_y + 84
        gl = gv = 0
        for disp in seq:
            try:
                # Emoji grande del disparo
                sym_l = "⚽" if disp.get('local_mete') else "❌"
                sym_v = "⚽" if disp.get('visitante_mete') else "❌"
                if disp.get('local_mete'):
                    gl += 1
                if disp.get('visitante_mete'):
                    gv += 1
                ronda = disp.get('ronda', 0)
                # Ronda + par de emojis
                draw_text(screen, f"R{ronda:>2}", (col_x_l, ronda_y), size='sm', color='dorado')
                draw_text(screen, sym_l, (col_x_l + 40, ronda_y), size='sm', color='verde' if disp.get('local_mete') else 'rojo')
                draw_text(screen, sym_v, (col_x_v, ronda_y), size='sm', color='verde' if disp.get('visitante_mete') else 'rojo')
                # Nombres de los cobradores (truncados)
                nom_l = (disp.get('cobrador_local') or '?')[:16]
                nom_v = (disp.get('cobrador_visitante') or '?')[:16]
                draw_text(screen, nom_l, (col_x_n, ronda_y), size='sm', color='blanco')
                draw_text(screen, nom_v, (col_x_n + 200, ronda_y), size='sm', color='blanco')
                # Acumulado al final de la línea
                draw_text(screen, f"({gl}-{gv})", (pp.right - 60, ronda_y), size='sm', color='dorado')
                ronda_y += 24
            except Exception as e_seq:
                logger.error(f"Error dibujando disparo {disp}: {e_seq}")
        if len(penales['secuencia']) > 10:
            draw_text(screen, f"... +{len(penales['secuencia']) - 10} rondas más", (col_x_l, ronda_y), size='sm', color='azul')
            ronda_y += 24
        if len(penales['secuencia']) > 5:
            draw_text(screen, "Muerte súbita a partir de la ronda 6", (col_x_l, ronda_y), size='sm', color='rojo')
    else:
        # Sin penales: panel de goles ancho clásico
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

    btn = pygame.Rect(SCREEN_W // 2 - 120, 670, 240, 44)
    draw_button(screen, btn, "CONTINUAR", btn.collidepoint(mouse_pos))
    if click_pos and btn.collidepoint(click_pos):
        estado.pop('prepartido_resultado', None)
        mode = estado.get('match_mode', 'liga')
        estado.pop('match_mode', None)
        # v0.8.7: limpiamos también los datos de penales para no contaminar el estado
        for k in ('sim_penales_resuelto', 'sim_penales_marcador', 'sim_penales_gana_user',
                  'sim_penales_secuencia', 'sim_penales_cobradores_l', 'sim_penales_cobradores_v',
                  'sim_penales_sel'):
            estado.pop(k, None)
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
        # v0.8.4: `or 'liga'` — nueva carrera deja match_mode=None y el default de .get no aplica.
        match_mode = estado.get('match_mode') or 'liga'

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
        panel = pygame.Rect(SCREEN_W // 2 - 320, 140, 640, 160)
        draw_panel(screen, panel)
        l_name = (getattr(local, 'corto', None) or (local.nombre if local else "Local"))
        v_name = (getattr(visitante, 'corto', None) or (visitante.nombre if visitante else "Visitante"))
        draw_text(screen, l_name, (panel.x + 30, panel.y + 25), size='lg', color='verde')
        draw_text(screen, "VS", (SCREEN_W // 2 - 18, panel.y + 28), size='lg', color='blanco')
        v_w = get_font('lg').size(v_name)[0]
        draw_text(screen, v_name, (panel.right - 30 - v_w, panel.y + 25), size='lg', color='rojo')

        # v0.8.3: OVR del mejor 11 de cada equipo (usando nivel_club de market.py).
        # Indicador visual con esferitas (5 negras = base ~70, cada blanca añadida = +2 OVR)
        # para que el DT vea de un vistazo si el partido es favorable.
        try:
            from alpha_football.market import nivel_club
            ovr_l = nivel_club(local) if local else 0
            ovr_v = nivel_club(visitante) if visitante else 0
        except Exception:
            ovr_l = ovr_v = 0
        # Esferitas a la izquierda (local) y derecha (visitante)
        _ovr_dots_render(screen, ovr_l, panel.x + 30, panel.y + 60, side='left')
        _ovr_dots_render(screen, ovr_v, panel.right - 30, panel.y + 60, side='right')
        # OVR numérico centrado entre los dos equipos
        if ovr_l or ovr_v:
            color_ovr_l = 'verde' if ovr_l > ovr_v else ('blanco' if ovr_l == ovr_v else 'rojo')
            color_ovr_v = 'verde' if ovr_v > ovr_l else ('blanco' if ovr_v == ovr_l else 'rojo')
            draw_text(screen, f"OVR {ovr_l}", (panel.x + 30, panel.y + 90), size='md', color=color_ovr_l)
            draw_text(screen, f"OVR {ovr_v}", (panel.right - 30 - get_font('md').size(f"OVR {ovr_v}")[0], panel.y + 90), size='md', color=color_ovr_v)
            # Diferencia centrada
            diff = ovr_l - ovr_v
            if diff > 0:
                msg = f"+{diff} a tu favor"
                c = 'verde'
            elif diff < 0:
                msg = f"{diff} en contra"
                c = 'rojo'
            else:
                msg = "Igualados"
                c = 'dorado'
            msg_w = get_font('sm').size(msg)[0]
            draw_text(screen, msg, (SCREEN_W // 2 - msg_w // 2, panel.y + 65), size='sm', color=c)

        # Mostrar estilos tácticos del DT de cada equipo
        estilo_l = f"Estilo: {getattr(local, 'estilo_dt', 'Equilibrado').capitalize()}"
        estilo_v = f"Estilo: {getattr(visitante, 'estilo_dt', 'Equilibrado').capitalize()}"
        v_estilo_w = get_font('sm').size(estilo_v)[0]
        draw_text(screen, estilo_l, (panel.x + 30, panel.y + 120), size='sm', color='blanco')
        draw_text(screen, estilo_v, (panel.right - 30 - v_estilo_w, panel.y + 120), size='sm', color='blanco')

        # Botones de opción
        btn_jugar = pygame.Rect(SCREEN_W // 2 - 260, 290, 520, 60)
        btn_sim = pygame.Rect(SCREEN_W // 2 - 260, 370, 520, 60)
        btn_dir = pygame.Rect(SCREEN_W // 2 - 260, 450, 520, 60)
        btn_ver_rival = pygame.Rect(SCREEN_W // 2 - 260, 510, 250, 48)
        btn_volver = pygame.Rect(SCREEN_W // 2 + 10, 510, 250, 48)

        draw_button(screen, btn_jugar, "1. JUGAR PARTIDO (en vivo)", btn_jugar.collidepoint(mouse_pos))
        draw_button(screen, btn_sim, "2. SIMULAR INSTANTÁNEAMENTE", btn_sim.collidepoint(mouse_pos))

        # v0.8.5: en AMISTOSO, dirección gestiona el equipo elegido para el amistoso (local),
        # no la carrera; así se habilita aunque no haya carrera cargada.
        dir_hab = (local is not None) if match_mode == 'amistoso' else (mi_equipo is not None)
        draw_button(screen, btn_dir, "3. DIRECCIÓN DE EQUIPO" if dir_hab else "3. DIRECCIÓN DE EQUIPO [Bloqueado]", btn_dir.collidepoint(mouse_pos) and dir_hab)

        # v0.8.3 (F1): botón extra para VER la alineación del RIVAL
        rival_disponible = visitante is not None and visitante is not local
        draw_button(screen, btn_ver_rival, "4. VER ALINEACIÓN RIVAL" if rival_disponible else "4. RIVAL NO DISPONIBLE",
                    btn_ver_rival.collidepoint(mouse_pos) and rival_disponible)

        draw_button(screen, btn_volver, "VOLVER", btn_volver.collidepoint(mouse_pos))

        if click_pos:
            if btn_jugar.collidepoint(click_pos):
                estado.pop('sim_resultado', None)
                estado.pop('sim_estado', None)
                return "match_screen"
            elif btn_sim.collidepoint(click_pos):
                _simular_instantaneo(estado, local, visitante)
            elif btn_dir.collidepoint(click_pos) and dir_hab:
                # Limpiar objetivo rival si está activo (vista de MI equipo)
                estado['team_equipo_objetivo'] = None
                # v0.8.5: marcar contexto para que team_screen gestione el equipo correcto
                # (amis_local en amistoso, la carrera en liga/copa) — datos totalmente separados.
                estado['team_contexto'] = 'amistoso' if match_mode == 'amistoso' else 'carrera'
                # v0.8.6 (Tarea 1): modo prepartido — team_screen muestra panel compacto sin HUB
                estado['team_modo_prepartido'] = True
                return "team_screen"
            elif btn_ver_rival.collidepoint(click_pos) and rival_disponible:
                # v0.8.3 (F1): abrir team_screen en modo visor del rival
                estado['team_equipo_objetivo'] = visitante
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
