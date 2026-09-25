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
        
        # Simular el partido usando el motor (v2.5.0: el user con su mentalidad, el rival con IA)
        from alpha_football.ui.match_screen import _ments
        user_eq = local if match_mode == 'amistoso' else mi_equipo
        # v3.1.0: el físico del user se cierra en vestuario (y el amistoso no gasta nada)
        from alpha_football.engine import _once_titular
        from alpha_football.models import asegurar_ids_unicos
        if user_eq is not None:
            asegurar_ids_unicos(user_eq)
        minutos_user = {j.id: 90 for j in _once_titular(user_eq)} if user_eq is not None else {}
        res = simular_partido(local, visitante, aplicar_fisico=False, **_ments(local, visitante, user_eq))
        gl, gv = res.goles_local, res.goles_visitante
        # v4.0.0: lo que pasó de verdad (goleadores, notas, minutos, lesiones y rojas del partido)
        from alpha_football.partido_ctx import stats_de_equipo, minutos_por_id, incidencias_de
        ctx = res.ctx
        lado_u = 'l' if user_eq is not None and getattr(user_eq, 'id', None) == local.id else 'v'
        lado_r = 'v' if lado_u == 'l' else 'l'
        if ctx is not None:
            minutos_user = minutos_por_id(ctx, lado_u)
        cierre_fisico = ({'incidencias': incidencias_de(ctx, lado_u), 'incidencias_rival': incidencias_de(ctx, lado_r),
                          'minutos_rival': minutos_por_id(ctx, lado_r)} if ctx is not None else {})
        # v4.1.0: línea de tiempo (goles, tarjetas, lesiones, cambios) y pantalla post-partido
        from alpha_football.ui import postpartido as PP
        linea = PP.linea_de_tiempo(getattr(res, 'eventos', []), local, visitante)
        estado['prepartido_paso'] = 'resumen'
        estado['prepartido_scroll'] = 0
        goles_ev = [e for e in getattr(res, 'eventos', []) if e.get('tipo') == 'gol']
        
        if match_mode == 'liga':
            liga = estado.get('liga')
            partido = estado.get('partido_actual')
            # Intentar recuperar el partido si no está en el estado
            if not partido and liga:
                jornada = getattr(liga, 'jornada_actual', 1)
                partido = next((p for p in liga.calendario if p.jornada == jornada
                                and (p.local_id == local.id or p.visitante_id == local.id)), None)
            if not liga or not partido or getattr(partido, 'jugado', False):
                logger.warning("_simular_instantaneo: falta liga o partido (o ya jugado), no se cierra jornada")
                return
                
            estado['prepartido_resultado'] = {
                'titulo': f"{getattr(local, 'corto', local.nombre)} {gl} - {gv} {getattr(visitante, 'corto', visitante.nombre)}",
                'goles': [f"{e.get('minuto', 0)}'  {e.get('detalle', 'Gol')}" for e in sorted(goles_ev, key=lambda x: x.get('minuto', 0))],
                'linea': linea,
            }
            
            # Desarrollo de la plantilla del usuario
            user_is_local = (mi_equipo.id == local.id)
            gf = gl if user_is_local else gv
            gc = gv if user_is_local else gl
            rep = []
            try:
                from alpha_football.desarrollo import desarrollar_plantilla_post_partido
                rep = desarrollar_plantilla_post_partido(
                    mi_equipo, gf, gc, stats_partido=stats_de_equipo(ctx, res.notas, lado_u) if ctx else None)
            except Exception as e_dev:
                logger.error(f"Error de desarrollo en sim instantánea de liga: {e_dev}")
            try:  # v3.1.0: físico, moral, correo del partido del user
                from alpha_football.vestuario import post_partido_user
                post_partido_user(estado, mi_equipo, visitante if user_is_local else local, gf, gc,
                                  rep or [], minutos_user, **cierre_fisico)
            except Exception as e_ves:
                logger.error(f"Error de vestuario en sim instantánea de liga: {e_ves}")
                
            # Cierre de jornada en liga
            from alpha_football.ui.match_screen import finalizar_jornada_liga
            pos_antes = PP.posicion_liga(liga, mi_equipo.id)
            finalizar_jornada_liga(estado, liga, mi_equipo, partido, gl, gv)
            PP.armar_datos(estado, 'liga', local, visitante, gl, gv, ctx, res.notas, res.eventos, pos_antes=pos_antes)
            
        elif match_mode == 'copa':
            # v3.8.0: el partido de copa (partido_copa_dict) se registra en el motor de competiciones.
            from alpha_football.ui import copa_screen as _copa
            penales_str = None
            secuencia, cobradores_l, cobradores_v = [], [], []
            if _copa.necesita_penales(estado, gl, gv):
                # Tanda simulada por atributos (final única empatada o global empatado)
                from alpha_football.engine import tanda_penales_jugadores
                cobradores_l = sorted(local.jugadores, key=lambda j: j.penales, reverse=True)[:5]
                cobradores_v = sorted(visitante.jugadores, key=lambda j: j.penales, reverse=True)[:5]
                _gana_local, penales_str, secuencia = tanda_penales_jugadores(cobradores_l, cobradores_v)
            # Desarrollo de AMBOS equipos sin tocar las estadísticas de liga + stats de copa
            rep_l = _copa.desarrollo_copa(local, gl, gv,
                                          stats_partido=stats_de_equipo(ctx, res.notas, 'l') if ctx else None)
            rep_v = _copa.desarrollo_copa(visitante, gv, gl,
                                          stats_partido=stats_de_equipo(ctx, res.notas, 'v') if ctx else None)
            _copa.registrar_stats_copa(estado, getattr(local, 'nombre', ''), gv, rep_l)
            _copa.registrar_stats_copa(estado, getattr(visitante, 'nombre', ''), gl, rep_v)
            pen_user = None
            if penales_str:
                pl, pv = _copa._marcador_a_tupla(penales_str) or (0, 0)
                pen_user = (pl, pv) if mi_equipo.id == local.id else (pv, pl)
            _copa.registrar_resultado_copa(estado, gl, gv, pen_user)
            try:  # v3.1.0: físico, moral, correo del partido del user
                from alpha_football.vestuario import post_partido_user
                user_is_local = mi_equipo.id == local.id
                post_partido_user(estado, mi_equipo, visitante if user_is_local else local,
                                  gl if user_is_local else gv, gv if user_is_local else gl,
                                  (rep_l if user_is_local else rep_v) or [], minutos_user, **cierre_fisico)
            except Exception as e_ves:
                logger.error(f"Error de vestuario en sim instantánea de copa: {e_ves}")
            
            # v0.8.7: si hubo penales, agregamos la secuencia y los cobradores
            # para que la UI de resultado los muestre ronda a ronda.
            penales_payload = None
            if penales_str:
                penales_payload = {
                    'marcador': penales_str,
                    'secuencia': secuencia or [],
                    'cobrador_l': [getattr(j, 'apellido', '?') for j in cobradores_l],
                    'cobrador_v': [getattr(j, 'apellido', '?') for j in cobradores_v],
                }
            estado['prepartido_resultado'] = {
                'titulo': f"{local.corto} {gl} - {gv} {visitante.corto}" + (f" ({penales_str} PEN)" if penales_str else ""),
                'goles': [f"{e.get('minuto', 0)}'  {e.get('detalle', 'Gol')}" for e in sorted(goles_ev, key=lambda x: x.get('minuto', 0))],
                'penales': penales_payload,
                'linea': linea,
            }
            PP.armar_datos(estado, 'copa', local, visitante, gl, gv, ctx, res.notas, res.eventos, penales=penales_str)
            
            # Limpiar variables temporales de copa
            estado.pop('partido_copa_dict', None)
            estado.pop('partido_copa_bracket_fase', None)
            
        elif match_mode == 'amistoso':
            # Amistoso no tiene consecuencias de liga/copa ni desarrollo de plantilla
            estado['prepartido_resultado'] = {
                'titulo': f"{local.corto} {gl} - {gv} {visitante.corto}",
                'goles': [f"{e.get('minuto', 0)}'  {e.get('detalle', 'Gol')}" for e in sorted(goles_ev, key=lambda x: x.get('minuto', 0))],
                'linea': linea,
            }
            PP.armar_datos(estado, 'amistoso', local, visitante, gl, gv, ctx, res.notas, res.eventos)
            
    except Exception as e:
        logger.error(f"Error en simulación instantánea general: {e}")


def botones_menu(dir_hab: bool = True, rival_disponible: bool = True) -> list:
    """v3.6.0: botones numerados del prepartido como (texto, rect), en orden de foco de teclado."""
    # v3.6.0: la columna arranca bajo el panel de equipos (que termina en y=300)
    x = SCREEN_W // 2 - 260
    return [
        ("1. JUGAR PARTIDO (en vivo)", pygame.Rect(x, 316, 520, 60)),
        ("2. SIMULAR INSTANTÁNEAMENTE", pygame.Rect(x, 392, 520, 60)),
        ("3. DIRECCIÓN DE EQUIPO" if dir_hab else "3. DIRECCIÓN DE EQUIPO [Bloqueado]", pygame.Rect(x, 468, 520, 60)),
        ("4. VER ONCE RIVAL" if rival_disponible else "4. SIN RIVAL", pygame.Rect(x, 544, 255, 48)),
        ("VOLVER", pygame.Rect(x + 265, 544, 255, 48)),
    ]


# v3.9.0: rects expuestos (ayuda H)
R_CARTEL = pygame.Rect(SCREEN_W // 2 - 320, 140, 640, 160)


def rects_resultado(con_penales: bool) -> dict:
    """v3.9.0: marcador, goles, penales y CONTINUAR de la pantalla de resultado instantáneo.
    CONTINUAR sube a y=648 (antes 670: quedaba debajo de la barra de atajos)."""
    d = {'marcador': pygame.Rect(SCREEN_W // 2 - 360, 130, 720, 90),
         'continuar': pygame.Rect(SCREEN_W // 2 - 120, 648, 240, 44)}
    if con_penales:
        d['goles'], d['penales'] = pygame.Rect(40, 240, 590, 400), pygame.Rect(650, 240, 590, 400)
    else:
        d['goles'] = pygame.Rect(SCREEN_W // 2 - 500, 236, 1000, 396)   # v4.1.0: línea de tiempo más ancha
    return d


def _marca_penal(screen, cx: int, cy: int, mete: bool) -> None:
    """v3.6.0: círculo verde = gol, cruz roja = falla (reemplaza los emojis ⚽/❌)."""
    try:
        if mete:
            pygame.draw.circle(screen, COLORS.get('verde', (0, 255, 136)), (cx, cy), 7)
        else:
            rojo = COLORS.get('rojo', (255, 68, 68))
            pygame.draw.line(screen, rojo, (cx - 6, cy - 6), (cx + 6, cy + 6), 3)
            pygame.draw.line(screen, rojo, (cx - 6, cy + 6), (cx + 6, cy - 6), 3)
    except Exception as e:
        logger.error(f"No se pudo dibujar la marca del penal: {e}")


def _dibujar_linea(screen: pygame.Surface, rect: pygame.Rect, linea: list, scroll: int) -> None:
    """v4.1.0: línea de tiempo del partido: minuto al centro, local a la izquierda, visitante a la derecha."""
    from alpha_football.ui.postpartido import dibujar_icono
    draw_panel(screen, rect)
    draw_text(screen, "EL PARTIDO", (rect.x + 20, rect.y + 12), size='md', color='azul')
    if not linea:
        draw_text(screen, "Sin goles ni incidencias.", (rect.x + 20, rect.y + 50), size='sm', color='blanco')
        return
    visibles = max(1, (rect.height - 56) // 28)
    y = rect.y + 50
    cx = rect.centerx
    ancho = rect.width // 2 - 60
    for x in linea[scroll:scroll + visibles]:
        m = f"{x['minuto']}'"
        draw_text(screen, m, (cx - get_font('sm').size(m)[0] // 2, y), size='sm', color='dorado', shadow=False)
        txt = x['texto']
        while txt and get_font('sm').size(txt)[0] > ancho:
            txt = txt[:-1]
        if x['lado'] == 'l':
            dibujar_icono(screen, x['tipo'], (cx - 36, y + 11))
            draw_text(screen, txt, (cx - 50 - get_font('sm').size(txt)[0], y), size='sm', color='blanco', shadow=False)
        else:
            dibujar_icono(screen, x['tipo'], (cx + 36, y + 11))
            draw_text(screen, txt, (cx + 50, y), size='sm', color='blanco', shadow=False)
        y += 28
    if len(linea) > visibles:
        draw_text(screen, "↑ ↓ para ver más", (rect.right - 170, rect.bottom - 26), size='sm', color='azul')


def _salir_resultado(estado: dict) -> str:
    """Limpia la simulación instantánea y devuelve la pantalla de destino."""
    estado.pop('prepartido_resultado', None)
    mode = estado.get('match_mode', 'liga')
    estado.pop('match_mode', None)
    # v0.8.7: limpiamos también los datos de penales para no contaminar el estado
    for k in ('sim_penales_resuelto', 'sim_penales_marcador', 'sim_penales_gana_user',
              'sim_penales_secuencia', 'sim_penales_cobradores_l', 'sim_penales_cobradores_v',
              'sim_penales_sel', 'postpartido', 'postpartido_tab', 'postpartido_scroll',   # v4.1.0
              'prepartido_paso', 'prepartido_scroll'):
        estado.pop(k, None)
    if mode == 'copa':
        estado['hub_tab'] = 'inicio'   # v2.4.0: la copa se juega desde Inicio
        return "league_screen"
    elif mode == 'amistoso':
        return "menu"
    return "league_screen"


def _render_resultado(screen: pygame.Surface, estado: dict, mouse_pos, click_pos,
                      teclas: Optional[list] = None) -> Optional[str]:
    """Muestra el marcador y los goleadores tras una simulación instantánea.
    v0.8.7: si el partido terminó en empate y se jugó tanda de penales (modo
    copa en eliminación directa), agrega un panel lateral con la secuencia
    ronda a ronda y los nombres de los cobradores.
    """
    r = estado.get('prepartido_resultado') or {}
    teclas = list(teclas or [])
    # v4.1.0: 2º paso = post-partido (calificaciones + tabla)
    if estado.get('prepartido_paso') == 'post' and estado.get('postpartido'):
        from alpha_football.ui import postpartido as PP
        if PP.render(screen, estado, mouse_pos, click_pos, teclas) == 'continuar':
            return _salir_resultado(estado)
        return None
    linea = r.get('linea')
    for k in teclas:
        if k == pygame.K_DOWN and linea:
            estado['prepartido_scroll'] = min(max(0, len(linea) - 1), estado.get('prepartido_scroll', 0) + 1)
        elif k == pygame.K_UP:
            estado['prepartido_scroll'] = max(0, estado.get('prepartido_scroll', 0) - 1)
    draw_gradient_bg(screen)
    draw_text(screen, "RESULTADO", (SCREEN_W // 2 - 110, 55), size='xl', color='dorado')

    penales = r.get('penales')
    _rr = rects_resultado(bool(penales and penales.get('secuencia')))      # v3.9.0
    panel = _rr['marcador']
    draw_panel(screen, panel)
    titulo = r.get('titulo', '0 - 0')
    tw = get_font('xl').size(titulo)[0]
    draw_text(screen, titulo, (SCREEN_W // 2 - tw // 2, 150), size='xl', color='verde')

    # v0.8.7: layout con DOS paneles (goles + penales) si hubo penales, o
    # UN panel ancho (goles) si no los hubo.
    penales = r.get('penales')
    if penales and penales.get('secuencia'):
        gp = _rr['goles']
        if linea is not None:   # v4.1.0
            _dibujar_linea(screen, gp, linea, estado.get('prepartido_scroll', 0))
        else:
            draw_panel(screen, gp)
            draw_text(screen, "GOLES", (gp.x + 20, gp.y + 12), size='md', color='azul')
            y = gp.y + 50
            for linea_g in r.get('goles', [])[:9]:
                draw_text(screen, linea_g[:78], (gp.x + 20, y), size='sm', color='blanco')
                y += 30

        # Panel de penales a la derecha
        pp = _rr['penales']
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
        draw_text(screen, "SECUENCIA (local / visitante: verde = gol, rojo = falla)", (pp.x + 20, header_y + 60),   # v3.6.0: sin emojis
                  size='sm', color='azul')
        seq = penales['secuencia'][:10]
        col_x_l = pp.x + 24
        col_x_v = pp.x + 70
        col_x_n = pp.x + 130
        ronda_y = header_y + 84
        gl = gv = 0
        for disp in seq:
            try:
                if disp.get('local_mete'):
                    gl += 1
                if disp.get('visitante_mete'):
                    gv += 1
                ronda = disp.get('ronda', 0)
                # Ronda + par de emojis
                draw_text(screen, f"R{ronda:>2}", (col_x_l, ronda_y), size='sm', color='dorado')
                # v3.6.0: marcas dibujadas (la fuente no tiene ⚽/❌ y salían como cuadros)
                _marca_penal(screen, col_x_l + 52, ronda_y + 11, bool(disp.get('local_mete')))
                _marca_penal(screen, col_x_v + 26, ronda_y + 11, bool(disp.get('visitante_mete')))
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
        gp = _rr['goles']
        if linea is not None:   # v4.1.0
            _dibujar_linea(screen, gp, linea, estado.get('prepartido_scroll', 0))
        else:
            draw_panel(screen, gp)
            draw_text(screen, "GOLES", (gp.x + 20, gp.y + 12), size='md', color='azul')
            y = gp.y + 50
            for linea_g in r.get('goles', [])[:9]:
                draw_text(screen, linea_g[:84], (gp.x + 20, y), size='sm', color='blanco')
                y += 30

    btn = _rr['continuar']
    draw_button(screen, btn, "CONTINUAR", btn.collidepoint(mouse_pos))
    avanzar = (click_pos and btn.collidepoint(click_pos)) or any(
        k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE) for k in teclas)
    if avanzar:
        if estado.get('postpartido'):   # v4.1.0: antes de salir, calificaciones y tabla
            estado['prepartido_paso'] = 'post'
            return None
        return _salir_resultado(estado)
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
        key_events = []
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "menu"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                click_pos = event.pos
            elif event.type == pygame.KEYDOWN:
                key_events.append(event)

        # Tras una simulación instantánea, mostrar el resultado y los goleadores.
        if estado.get('prepartido_resultado'):
            return _render_resultado(screen, estado, mouse_pos, click_pos, [e.key for e in key_events])

        draw_gradient_bg(screen)
        draw_text(screen, "PREPARAR PARTIDO", (SCREEN_W // 2 - get_font('xl').size("PREPARAR PARTIDO")[0] // 2, 70),
                  size='xl', color='dorado')        # v3.9.0: centrado (antes quedaba corrido a la derecha)

        # Cartel del enfrentamiento
        panel = R_CARTEL
        draw_panel(screen, panel)
        l_name = (getattr(local, 'corto', None) or (local.nombre if local else "Local"))
        v_name = (getattr(visitante, 'corto', None) or (visitante.nombre if visitante else "Visitante"))
        draw_text(screen, l_name, (panel.x + 30, panel.y + 25), size='lg', color='verde')
        draw_text(screen, "VS", (SCREEN_W // 2 - 18, panel.y + 28), size='lg', color='blanco')
        v_w = get_font('lg').size(v_name)[0]
        draw_text(screen, v_name, (panel.right - 30 - v_w, panel.y + 25), size='lg', color='rojo')
        try:  # v3.1.0: clásico y titulares cansados
            from alpha_football.data.clasicos import es_clasico
            if es_clasico(local, visitante):
                draw_text(screen, "CLÁSICO", (SCREEN_W // 2 - get_font('sm').size("CLÁSICO")[0] // 2, panel.y + 4),
                          size='sm', color='rojo')
            controlado = estado.get('amis_local') if match_mode == 'amistoso' else mi_equipo
            alin_c = getattr(controlado, 'alineacion_activa', None)
            js_c = list(getattr(controlado, 'jugadores', []) or [])
            cansados = [js_c[i] for i in (getattr(alin_c, 'titulares', []) or [])
                        if 0 <= i < len(js_c) and float(getattr(js_c[i], 'energia', 100)) < 60]
            if cansados and match_mode != 'amistoso':
                txt = (f"{len(cansados)} titular{'es' if len(cansados) != 1 else ''} cansado{'s' if len(cansados) != 1 else ''}"
                       f" (energía < 60): " + ", ".join(j.apellido for j in cansados[:3]))
                draw_text(screen, txt, (SCREEN_W // 2 - get_font('sm').size(txt)[0] // 2, 30),
                          size='sm', color='dorado')
        except Exception as e_v31:
            logger.error(f"Error al dibujar avisos de prepartido: {e_v31}")

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
            # v0.8.7.4: diff desde la perspectiva del USUARIO (no siempre local - visitante).
            # Cuando el user es visitante, ovr_v = user, ovr_l = rival → hay que invertir.
            user_is_local = bool(
                mi_equipo and local and getattr(mi_equipo, 'id', None) == getattr(local, 'id', None)
            )
            ovr_user = ovr_l if user_is_local else ovr_v
            ovr_rival = ovr_v if user_is_local else ovr_l
            diff = ovr_user - ovr_rival
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
        try:  # v3.4.0: el club IA muestra a su DT ("DT: Pep Guardiolo · Cruyffismo")
            from alpha_football import entrenadores as _EN
            from alpha_football.estilos import NOMBRE_ESTILO as _NE
            from alpha_football.data.entrenadores import DT_REALES as _DTR
            _mi = estado.get('mi_equipo')

            def _linea_dt(eq):
                if eq is None or eq is _mi:
                    return None
                dt = _EN.dt_de(estado, eq)
                if dt is None and eq.nombre in _DTR:        # clubes de copa: DT real de la tabla
                    dt = {'nombre': _DTR[eq.nombre][0], 'estilo': _DTR[eq.nombre][1]}
                if not dt:
                    return None
                return f"DT: {dt['nombre'][:18]} · {_NE.get(dt['estilo'], '')}"
            estilo_l = _linea_dt(local) or estilo_l
            estilo_v = _linea_dt(visitante) or estilo_v
        except Exception as e_dt:
            logger.error(f"Error al mostrar el DT del rival: {e_dt}")
        v_estilo_w = get_font('sm').size(estilo_v)[0]
        draw_text(screen, estilo_l, (panel.x + 30, panel.y + 120), size='sm', color='blanco')
        draw_text(screen, estilo_v, (panel.right - 30 - v_estilo_w, panel.y + 120), size='sm', color='blanco')

        # Botones de opción
        # v3.6.0: textos y rects salen de botones_menu() (textos que caben en su botón)
        dir_hab = (local is not None) if match_mode == 'amistoso' else (mi_equipo is not None)
        rival_disponible = visitante is not None and visitante is not local
        ((t_jugar, btn_jugar), (t_sim, btn_sim), (t_dir, btn_dir), (t_rival, btn_ver_rival),
         (t_volver, btn_volver)) = botones_menu(dir_hab, rival_disponible)

        # v2.3.3 (FIX): dir_hab y rival_disponible deben estar definidos ANTES de la
        # lista prepartido_buttons, porque alli los usamos como flag de habilitacion.
        # Antes la lista los referenciaba antes de su definicion -> UnboundLocalError.
        # v0.8.5: en AMISTOSO, dirección gestiona el equipo elegido para el amistoso (local),
        # no la carrera; así se habilita aunque no haya carrera cargada.
        # v0.8.3 (F1): botón extra para VER la alineación del RIVAL (rival_disponible, arriba)

        # v2.3.3: navegacion por teclado. 5 botones en orden:
        # 0=JUGAR, 1=SIMULAR, 2=DIRECCION, 3=VER RIVAL, 4=VOLVER.
        if 'prepartido_kbd_focus' not in estado:
            estado['prepartido_kbd_focus'] = 0
        _pp_kbd = int(estado.get('prepartido_kbd_focus', 0))
        prepartido_buttons = [
            (btn_jugar, 'jugar', True),
            (btn_sim, 'sim', True),
            (btn_dir, 'dir', dir_hab),
            (btn_ver_rival, 'rival', rival_disponible),
            (btn_volver, 'volver', True),
        ]

        draw_button(screen, btn_jugar, t_jugar,
                    btn_jugar.collidepoint(mouse_pos) or _pp_kbd == 0)
        draw_button(screen, btn_sim, t_sim,
                    btn_sim.collidepoint(mouse_pos) or _pp_kbd == 1)

        # (dir_hab y rival_disponible ya están definidos arriba para el flag de teclado)
        draw_button(screen, btn_dir, t_dir,
                    (btn_dir.collidepoint(mouse_pos) and dir_hab) or (_pp_kbd == 2 and dir_hab))

        draw_button(screen, btn_ver_rival, t_rival,
                    (btn_ver_rival.collidepoint(mouse_pos) and rival_disponible) or (_pp_kbd == 3 and rival_disponible))

        draw_button(screen, btn_volver, t_volver,
                    btn_volver.collidepoint(mouse_pos) or _pp_kbd == 4)

        # v2.3.3: indicador visual de foco por teclado
        try:
            if 0 <= _pp_kbd < len(prepartido_buttons):
                rect, _n, _habilitado = prepartido_buttons[_pp_kbd]
                if _habilitado and not rect.collidepoint(mouse_pos):
                    pygame.draw.rect(screen, COLORS.get('dorado', (255, 215, 0)), rect, width=3, border_radius=8)
                    cy_f = rect.centery                                    # v3.6.0: flecha dibujada (▶ salía en cuadro)
                    pygame.draw.polygon(screen, COLORS.get('dorado', (255, 215, 0)),
                                        [(rect.x - 22, cy_f - 9), (rect.x - 8, cy_f), (rect.x - 22, cy_f + 9)])
        except Exception:
            pass

        # v2.3.3: navegacion por teclado. ↑↓ mueve el foco entre los 5 botones,
        # Enter dispara el handler del boton enfocado (solo si esta habilitado).
        try:
            for ev in key_events:
                if ev.key == pygame.K_UP:
                    estado['prepartido_kbd_focus'] = (_pp_kbd - 1) % len(prepartido_buttons)
                elif ev.key == pygame.K_DOWN:
                    estado['prepartido_kbd_focus'] = (_pp_kbd + 1) % len(prepartido_buttons)
                elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                    rect, _n, habilitado = prepartido_buttons[_pp_kbd]
                    if habilitado:
                        click_pos = (rect.x + rect.width // 2, rect.y + rect.height // 2)
                elif ev.key == pygame.K_1:
                    estado['prepartido_kbd_focus'] = 0
                    click_pos = (btn_jugar.x + btn_jugar.width // 2, btn_jugar.y + btn_jugar.height // 2)
                elif ev.key == pygame.K_2:
                    estado['prepartido_kbd_focus'] = 1
                    click_pos = (btn_sim.x + btn_sim.width // 2, btn_sim.y + btn_sim.height // 2)
                elif ev.key == pygame.K_3:
                    if dir_hab:
                        estado['prepartido_kbd_focus'] = 2
                        click_pos = (btn_dir.x + btn_dir.width // 2, btn_dir.y + btn_dir.height // 2)
                elif ev.key == pygame.K_4:
                    if rival_disponible:
                        estado['prepartido_kbd_focus'] = 3
                        click_pos = (btn_ver_rival.x + btn_ver_rival.width // 2, btn_ver_rival.y + btn_ver_rival.height // 2)
                elif ev.key == pygame.K_ESCAPE:
                    click_pos = (btn_volver.x + btn_volver.width // 2, btn_volver.y + btn_volver.height // 2)
                    estado['prepartido_kbd_focus'] = 4
        except Exception as e_kbd_pp:
            logger.error(f"Error en teclado de prepartido_screen: {e_kbd_pp}")

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
                # v0.8.3 (F1): abrir team_screen en modo visor del rival.
                # v0.8.7.5 FIX: el rival es el OPONENTE del equipo que dirige el usuario,
                # no siempre el "visitante". En liga/copa el user juega de local o de
                # visitante según el fixture; si juega de visitante, ese "visitante" ES
                # su propio equipo y abrir team_screen con él dispara el modo EDICIÓN
                # (DIRECCIÓN DE EQUIPO) en vez del visor (view_mode queda en False).
                # Elegimos el equipo que el usuario NO controla.
                controlado = estado.get('amis_local') if match_mode == 'amistoso' else mi_equipo
                user_es_visitante = bool(
                    controlado is visitante
                    or (getattr(controlado, 'id', None) is not None
                        and getattr(controlado, 'id', None) == getattr(visitante, 'id', None))
                )
                estado['team_equipo_objetivo'] = local if user_es_visitante else visitante
                # v0.8.7.4: marcar contexto igual que el botón DIRECCIÓN DE EQUIPO,
                # para que team_screen no caiga al menú si liga/mi_equipo están stale.
                estado['team_contexto'] = 'amistoso' if match_mode == 'amistoso' else 'carrera'
                return "team_screen"
            elif btn_volver.collidepoint(click_pos):
                if match_mode == 'copa':
                    estado['hub_tab'] = 'inicio'   # v2.4.0
                    return "league_screen"
                elif match_mode == 'amistoso':
                    return "menu"
                return "league_screen"
        return None
    except Exception as e:
        logger.error(f"Error en prepartido_screen: {e}")
        return "menu"
