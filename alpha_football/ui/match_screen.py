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

from alpha_football import formaciones as F

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

# Fase 5: reloj calibrado — 1 segundo real = 1 minuto de juego (partido de 90 seg).
MS_POR_MINUTO = 1000

# Multiplicadores de la 2ª mitad según la charla de medio tiempo (afectan al MOTOR).
# Se aplican al lado del USUARIO; el rival queda en 1.0.
CHARLAS_MT = {
    1: {"atk": 1.05, "def": 1.05, "msg": "DT: Charla motivacional. ¡Salen enchufados!"},
    2: {"atk": 1.20, "def": 0.90, "msg": "DT: Planteamiento ofensivo. ¡Al ataque!"},
    3: {"atk": 0.85, "def": 1.25, "msg": "DT: Autobús atrás. Cerramos filas."},
    4: {"atk": 1.00, "def": 1.00, "msg": "DT: Mantenemos el plan original."},
}

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
        from alpha_football.desarrollo import desarrollar_plantilla_post_partido
        
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
                
                # Desarrollar los jugadores de ambos equipos de la IA
                try:   # v4.0.0: con goleadores, asistentes y notas reales del partido
                    from alpha_football.partido_ctx import stats_de_equipo
                    desarrollar_plantilla_post_partido(loc_eq, res.goles_local, res.goles_visitante,
                                                       stats_partido=stats_de_equipo(res.ctx, res.notas, 'l'))
                    desarrollar_plantilla_post_partido(vis_eq, res.goles_visitante, res.goles_local,
                                                       stats_partido=stats_de_equipo(res.ctx, res.notas, 'v'))
                except Exception as e_dev_ia:
                    logger.error(f"Error al desarrollar equipo de la IA: {e_dev_ia}")
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

# v3.8.0: recalcular_standings_copa se fue con la copa vieja (las tablas las calcula competiciones).

# --- v0.7: cierre de jornada de liga reutilizable (live + simulación instantánea) ═══

def _correo_oferta(estado: dict, oferta: dict, prefijo: str) -> None:
    """v3.1.0: cada oferta recibida llega también al correo, con enlace a OFERTAS."""
    try:
        from alpha_football import correo as C
        jo, comp = oferta.get('jugador'), oferta.get('comprador')
        C.enviar(estado, 'club', f"{prefijo} {jo.nombre} {jo.apellido}",
                 f"{getattr(comp, 'nombre', 'Un club')} ofrece ${int(oferta.get('monto', 0)):,}.",
                 C.accion('ofertas_screen', "VER OFERTAS"))
    except Exception as e:
        logger.error(f"No se pudo enviar el correo de la oferta: {e}")


def _depurar_titulares(user_eq: Any, user_alin: Any) -> None:
    """v3.1.0: un titular lesionado o sancionado no juega: se reemplaza (en su mismo puesto de la
    lista) por el jugador que el motor mete en su lugar, así los minutos y el físico son reales."""
    if user_eq is None or user_alin is None:
        return
    from alpha_football.engine import _once_titular
    from alpha_football.models import asegurar_ids_unicos
    asegurar_ids_unicos(user_eq)
    js = list(getattr(user_eq, 'jugadores', []) or [])
    tit = list(getattr(user_alin, 'titulares', []) or [])
    en_lista = {id(js[i]) for i in tit if 0 <= i < len(js)}
    relevos = [j for j in _once_titular(user_eq) if id(j) not in en_lista]
    for k, i in enumerate(tit):
        if (not (0 <= i < len(js)) or not js[i].disponible) and relevos:
            tit[k] = js.index(relevos.pop(0))
    user_alin.titulares = tit


def _minutos_previos(estado: dict, user_eq: Any, user_alin: Any) -> dict:
    """v3.1.0: {id(jugador): minutos ya jugados} de los titulares actuales del user."""
    mins = estado.get('sim_minuto_por_jugador') or {}
    js = list(getattr(user_eq, 'jugadores', []) or [])
    return {id(js[i]): int(mins.get(js[i].id, 0)) for i in (getattr(user_alin, 'titulares', []) or [])
            if 0 <= i < len(js)}


def finalizar_jornada_liga(estado: dict, liga: Any, mi_equipo: Any, partido: Any,
                           goles_l: int, goles_v: int) -> None:
    """
    Cierra el partido del usuario: guarda goles, simula el resto de la jornada,
    recuenta la tabla, avanza la jornada y genera posibles ofertas (local y exterior).
    Lo usan tanto la pantalla en vivo como la "Simulación instantánea" del pre-partido.
    """
    try:
        # v3.0.0: un partido ya cerrado no se vuelve a cerrar (evita doble jornada/marcador pisado)
        if getattr(partido, 'jugado', False):
            logger.warning("finalizar_jornada_liga: el partido ya estaba jugado, no se cierra otra vez")
            return
        partido.goles_local = goles_l
        partido.goles_visitante = goles_v
        partido.jugado = True
        try:  # v2.8.0: la directiva ajusta su confianza con cada resultado de liga
            from alpha_football.directiva import actualizar_confianza
            es_local = partido.local_id == mi_equipo.id
            actualizar_confianza(estado, goles_l if es_local else goles_v, goles_v if es_local else goles_l)
        except Exception as e_conf:
            logger.error(f"Error al actualizar la confianza de la directiva: {e_conf}")
        try:  # v2.9.0: taquilla, patrocinio, salarios y control de quiebra
            from alpha_football.finanzas import procesar_jornada
            es_local = partido.local_id == mi_equipo.id
            procesar_jornada(estado, es_local, goles_l if es_local else goles_v, goles_v if es_local else goles_l)
        except Exception as e_fin:
            logger.error(f"Error en las finanzas de la jornada: {e_fin}")
        simular_otros_partidos(liga, liga.jornada_actual)
        actualizar_estadisticas_liga(liga)
        if liga.jornada_actual < liga.num_jornadas:
            liga.jornada_actual += 1
        else:
            logger.info("Fin de temporada alcanzado.")
        # v3.8.0: las dos copas juegan sus fechas vencidas tras la jornada (salvo el partido del
        # user, que queda pendiente para JUGAR).
        try:
            from alpha_football.ui.copa_screen import simular_copa_fondo
            simular_copa_fondo(estado)
        except Exception as e_bg:
            logger.error(f"Error al simular copa de fondo: {e_bg}")
        # v2.3 (Fase 7): avanzar la jornada de TODAS las 2ª divisiones en background.
        # Mismo ritmo que 1ª división: 1 jornada por jornada del user. Si el user
        # descendió, su partido en la 2ª división se salta (lo juega él).
        try:
            from alpha_football.ui.league_screen import simular_jornada_segunda_division
            simular_jornada_segunda_division(estado)
        except Exception as e_bg2:
            logger.error(f"Error al simular jornada de 2ª división: {e_bg2}")
        # traspasos acordados con el mercado cerrado: se concretan al abrirse (antes que la IA)
        try:
            from alpha_football import traspasos_pendientes as _tp
            _tp.ejecutar(estado)
            _tp.limpiar_ofertas(estado)
        except Exception as e_tp:
            logger.error(f"Error con los traspasos pendientes: {e_tp}")
        import random as _rnd
        _azar_pr = _rnd.Random()
        try:  # préstamos acordados / regresos: también antes de que fiche la IA
            from alpha_football import prestamos as _pr
            _pr.revisar_jornada(estado, _azar_pr)
        except Exception as e_pr0:
            logger.error(f"Error con los préstamos pendientes: {e_pr0}")
        # v2.3.7: con el mercado abierto, los clubes de la IA fichan entre ellos.
        try:
            from alpha_football import market as _mk
            if _mk.ventana_mercado_abierta(liga.jornada_actual, liga.num_jornadas):
                from alpha_football.mercado_ia import ronda_fichajes_ia
                ronda_fichajes_ia(estado, 'ventana')
        except Exception as e_mia:
            logger.error(f"Error en el mercado de la IA: {e_mia}")
        # Ofertas tras la jornada (IA local + posible oferta del exterior por buen rendimiento)
        try:
            from alpha_football import market
            if mi_equipo:
                rivales = [e for e in liga.equipos if e.id != mi_equipo.id]
                oferta_ia = market.crear_oferta_ui(mi_equipo, rivales, liga.jornada_actual, liga.num_jornadas)
                if oferta_ia:
                    estado.setdefault('ofertas_recibidas', []).append(oferta_ia)
                    _correo_oferta(estado, oferta_ia, "Oferta por")
                _crear_ext = getattr(market, 'crear_oferta_exterior', None)
                if _crear_ext:
                    oferta_ext = _crear_ext(mi_equipo, estado)
                    if oferta_ext:
                        estado.setdefault('ofertas_recibidas', []).append(oferta_ext)
                        _correo_oferta(estado, oferta_ext, "Oferta del exterior por")
        except Exception as e_of:
            logger.error(f"Error al generar ofertas tras la jornada: {e_of}")
        try:  # v4.4.0: descontento, pide salir, escalada y ofertas garantizadas (salidas.py)
            from alpha_football.salidas import cierre_jornada as _salidas_cierre
            _salidas_cierre(estado)
        except Exception as e_sal:
            logger.error(f"Error en las salidas de jugadores: {e_sal}")
        try:  # v3.1.0: recuperación física de todos, pedidos de la directiva y cláusulas
            from alpha_football.energia import recuperar_todos
            recuperar_todos(estado)
            from alpha_football.directiva import revisar_pedido
            revisar_pedido(estado)
            from alpha_football import market as _mk2
            if _mk2.ventana_mercado_abierta(liga.jornada_actual, liga.num_jornadas):
                from alpha_football.mercado_ia import pago_clausulas
                pago_clausulas(estado)
        except Exception as e_v31:
            logger.error(f"Error en el cierre de jornada v3.1.0: {e_v31}")
        try:  # v3.2.0: sueldo y renovación del DT
            from alpha_football import carrera_dt as _cd
            _cd.pagar_jornada(estado)
            _cd.revisar_renovacion(estado)
            _cd.revisar_renovacion_por_hito(estado)     # te negaron renovar pero ganaste algo
        except Exception as e_v32:
            logger.error(f"Error en el cierre de jornada v3.2.0: {e_v32}")
        try:  # v3.4.0: vencen ofertas de banquillo y los clubes IA que van mal echan a su DT
            from alpha_football.entrenadores import revisar_jornada as _dts_jornada
            _dts_jornada(estado)
        except Exception as e_v34:
            logger.error(f"Error en el cierre de jornada v3.4.0: {e_v34}")
        try:  # v3.5.0: respuestas "lo analizamos" (ventas y compras)
            from alpha_football.contraofertas import resolver_analisis
            resolver_analisis(estado)
        except Exception as e_co:
            logger.error(f"Error al resolver contraofertas: {e_co}")
        try:  # préstamos: análisis, ofertas de préstamo y purga de ofertas (idas/vueltas: arriba)
            from alpha_football import prestamos as _pr
            _pr.resolver_analisis(estado, _azar_pr)
            _pr.generar_ofertas(estado, _azar_pr)
            _pr.limpiar_ofertas(estado)
        except Exception as e_pr:
            logger.error(f"Error con los préstamos de la jornada: {e_pr}")
        try:  # v4.3.0: correo cuando la meta de liga ya está asegurada
            from alpha_football.directiva import revisar_objetivo_liga_asegurado
            revisar_objetivo_liga_asegurado(estado)
        except Exception as e_obj:
            logger.error(f"Error al revisar el objetivo de liga: {e_obj}")
    except Exception as e:
        logger.error(f"Error en finalizar_jornada_liga: {e}")


# --- v0.7: menú táctico en partido (medio tiempo + cambio en vivo) ═══════════════
# v3.3.0: se borró _TACTICAS_MENU (sin uso); el selector de estilo es el de team_screen.


def _menu_tactico(screen: pygame.Surface, estado: dict, equipo: Any, alin: Any,
                  mouse_pos: tuple, click_pos: Optional[tuple], titulo: str = "",
                  key_events: Optional[list] = None) -> Optional[str]:
    """
    v2.3.6: dirección EN VIVO con la misma pantalla que "Dirección de equipo" (campo con
    los 11, banco de convocados y ficha). Reglas del partido: máx. 5 cambios, el que sale
    no vuelve a entrar, las reservas no entran; formación, táctica y cambios de puesto
    son libres. Devuelve 'reanudar' al pulsar REANUDAR (el reloj sigue en pausa mientras).
    Todo lo que se cambie aquí vale SOLO para este partido: render() restaura la
    alineación, la formación y la táctica de antes del partido al terminar.
    """
    # Foto al abrir: DESHACER vuelve a este punto (no al inicio del partido).
    if not estado.get('sim_dir_snapshot'):
        estado['sim_dir_snapshot'] = True
        estado['_original_alignment'] = list(alin.titulares)
        estado['_original_convocados'] = list(getattr(alin, 'convocados', []) or [])
        estado['_original_formacion'] = alin.formacion
        estado['_original_estilo'] = equipo.estilo_dt
        estado['_original_mentalidad'] = getattr(equipo, 'mentalidad', 'normal')
        estado['_original_subs'] = int(estado.get('sim_subs_realizadas', 0) or 0)
        estado['_original_salieron'] = list(estado.get('sim_salieron', []) or [])
    try:
        from alpha_football.ui.team_screen import _render_direccion
        res = _render_direccion(screen, estado, equipo, alin, False, False, 'reanudar',
                                mouse_pos, click_pos, en_partido=True,
                                key_events=key_events if key_events is not None else [])   # v4.2.0
    except Exception as e_dir:
        logger.error(f"Error en la dirección en vivo: {e_dir}")
        res = 'reanudar'
    if res == 'reanudar':
        estado.pop('sim_dir_snapshot', None)
    return res


def _ments(local: Any, visitante: Any, user_eq: Any) -> dict:
    """v2.5.0: mentalidad para el motor: la del user fija, la del rival la decide la IA."""
    ml = mv = 'ia'
    if user_eq is not None:
        m = getattr(user_eq, 'mentalidad', 'normal') or 'normal'
        uid = getattr(user_eq, 'id', None)
        if user_eq is local or (uid is not None and uid == getattr(local, 'id', None)):
            ml = m
        elif user_eq is visitante or (uid is not None and uid == getattr(visitante, 'id', None)):
            mv = m
    return {'ment_l': ml, 'ment_v': mv}


# v3.9.0: rects expuestos (ayuda H); render los usa tal cual.
R_MARCADOR = pygame.Rect(40, 20, 1200, 150)
R_VELOCIDAD = pygame.Rect(1085, 112, 115, 42)
R_TACTICA = pygame.Rect(948, 112, 128, 42)
R_TRANSMISION = pygame.Rect(40, 190, 1200, 360)
R_FIN_PANEL = pygame.Rect(40, 570, 1200, 80)
R_FIN_SALIR = pygame.Rect(1000, 585, 220, 50)
R_PENALES = pygame.Rect(SCREEN_W // 2 - 320, 70, 640, 580)
R_PENALES_DEFINIR = pygame.Rect(R_PENALES.x + 200, R_PENALES.bottom - 60, 240, 46)
FILAS_PENALES = 11      # v3.9.0: con 14 filas las últimas quedaban debajo de DEFINIR EN PENALES


def _rects_tira_mentalidad() -> list:
    """v2.5.0: los 5 botones de mentalidad bajo la transmisión."""
    return [pygame.Rect(230 + i * 202, 562, 192, 40) for i in range(5)]


def _cambiar_mentalidad_en_vivo(estado: dict, user_eq: Any, local: Any, visitante: Any,
                                nueva: str, minuto: int) -> None:
    """
    v2.5.0: cambia la mentalidad del user sin pausar y re-simula el resto de la mitad en
    curso desde el minuto actual (mismo mecanismo que el REANUDAR del ajuste táctico).
    """
    from alpha_football.engine import NOMBRE_MENTALIDAD
    user_eq.mentalidad = nueva
    _resimular(estado, local, visitante, user_eq, minuto)
    estado.setdefault('sim_comentarios', []).append(
        f"Min {minuto}: » DT: mentalidad {NOMBRE_MENTALIDAD.get(nueva, nueva)}")


# v4.1.0: pausas del reloj en vivo (ms a velocidad x1; se dividen por la velocidad).
# duración de cada aviso; NO depende de la velocidad del reloj (en x5 duraban 0.2 s y parecían saltarse solos)
PAUSA_MS = {'gol': 4000, 'roja': 3500, 'lesion': 3500, 'amarilla': 2500}
R_AVISO = pygame.Rect(SCREEN_W // 2 - 330, 250, 660, 130)
R_SELECTOR = pygame.Rect(SCREEN_W // 2 - 300, 120, 600, 470)


def _lado_user(local: Any, user_eq: Any) -> Optional[str]:
    if user_eq is None:
        return None
    return 'l' if getattr(user_eq, 'id', None) == getattr(local, 'id', None) else 'v'


def _resimular(estado: dict, local: Any, visitante: Any, user_eq: Any, minuto: int,
               fin: Optional[int] = None) -> None:
    """
    v4.1.0: re-simula desde `minuto + 1` hasta el fin de la mitad (o `fin`) partiendo del estado
    REVELADO del partido (estado['sim_ctx']): un expulsado o lesionado ya visto no vuelve. Los
    cambios que el user hizo en el menú táctico entran primero al ctx revelado (eventos 'cambio').
    """
    from alpha_football.engine import simular_rango, _once_titular, evento_cambio
    from alpha_football import partido_ctx as PCX
    fin = fin if fin is not None else (45 if minuto < 45 else int(estado.get('sim_fin', 90)))   # v4.4.0
    ctx = estado.get('sim_ctx')
    previos = [e for e in estado.get('sim_eventos', []) if e['minuto'] <= minuto]
    try:
        lado = _lado_user(local, user_eq)
        if ctx is not None and lado is not None:
            salen, entran = PCX.resincronizar_user(ctx, lado, _once_titular(user_eq), minuto)
            for s_, e_ in zip(salen, entran):
                ev = evento_cambio(minuto, lado, user_eq, s_, e_, ya_fuera=True)
                ev['_aplicado'] = True
                ctx.cambios[lado] = ctx.cambios.get(lado, 0) + 1
                previos.append(ev)
                estado.setdefault('sim_eventos_procesados', []).append(ev)
        nuevos = []
        if minuto < fin:
            ctx_sim = ctx.copia() if ctx is not None else None
            _gl, _gv, nuevos = simular_rango(
                local, visitante, minuto + 1, fin, mult=estado.get("sim_suerte"),
                goles_previos=(estado.get("sim_goles_l", 0), estado.get("sim_goles_v", 0)),
                minutos_previos=_minutos_previos(estado, user_eq, getattr(user_eq, 'alineacion_activa', None)),
                ctx=ctx_sim,
                **_ments(local, visitante, user_eq))
            if ctx is not None and ctx_sim is not None:
                # los cambios que planea la IA quedan fijos: otra re-simulación no los vuelve a sortear
                for lado_ia, n_cambios in ctx_sim.objetivo_cambios.items():
                    ctx.objetivo_cambios.setdefault(lado_ia, n_cambios)
        estado['sim_eventos'] = previos + nuevos
    except Exception as e_resim:
        logger.error(f"Error al re-simular el partido en vivo: {e_resim}")


def _pausar(estado: dict, tipo: str, texto: str, color: str) -> None:
    """v4.1.0: detiene el reloj con un aviso grande (Enter/Espacio lo salta). Si ya hay uno en
    pantalla (dos incidencias en el mismo minuto), el nuevo espera su turno en la cola."""
    aviso = {'tipo': tipo, 'texto': texto, 'color': color}
    if pygame.time.get_ticks() < estado.get('sim_pausa_hasta', 0) and estado.get('sim_aviso'):
        estado.setdefault('sim_avisos_cola', []).append(aviso)
        return
    _mostrar_aviso(estado, aviso)


def _mostrar_aviso(estado: dict, aviso: dict) -> None:
    estado['sim_aviso'] = aviso
    estado['sim_pausa_hasta'] = pygame.time.get_ticks() + PAUSA_MS.get(aviso.get('tipo'), 2500)


def _siguiente_aviso(estado: dict) -> bool:
    """Pasa al próximo aviso de la cola (al vencer o al saltar el actual). True si mostró otro."""
    cola = estado.get('sim_avisos_cola') or []
    if not cola:
        return False
    _mostrar_aviso(estado, cola.pop(0))
    return True


def _dibujar_aviso(screen: pygame.Surface, estado: dict) -> None:
    try:
        av = estado.get('sim_aviso') or {}
        draw_glass_panel(screen, R_AVISO, bg_color=(15, 20, 35), border_color=(255, 215, 0), alpha=235)
        from alpha_football.ui.postpartido import dibujar_icono
        dibujar_icono(screen, av.get('tipo', ''), (R_AVISO.x + 44, R_AVISO.centery))
        titulo = {'gol': "¡GOL!", 'amarilla': "TARJETA AMARILLA", 'roja': "¡EXPULSADO!",
                  'lesion': "LESIÓN"}.get(av.get('tipo'), "")
        draw_text(screen, titulo, (R_AVISO.x + 80, R_AVISO.y + 18), size='lg', color=av.get('color', 'dorado'))
        draw_text(screen, str(av.get('texto', ''))[:52], (R_AVISO.x + 80, R_AVISO.y + 62), size='md', color='blanco')
        draw_text(screen, "Enter para seguir", (R_AVISO.right - 190, R_AVISO.bottom - 30), size='sm', color='azul')
    except Exception as e:
        logger.error(f"No se pudo dibujar el aviso del partido: {e}")


def _selector_cambio(screen: pygame.Surface, estado: dict, user_eq: Any, local: Any, visitante: Any,
                     teclas: list, mouse_pos: tuple, click_pos: Optional[tuple]) -> None:
    """
    v4.1.0: se lesionó un jugador del user y le quedan cambios: elige quién entra (↑/↓ + Enter o
    clic). Aplica el cambio en la alineación, lo suma al ctx revelado y re-simula el resto de la mitad.
    """
    from alpha_football.engine import suplentes_disponibles, evento_cambio
    from alpha_football.partido_ctx import aplicar_evento
    ctx = estado.get('sim_ctx')
    lado = _lado_user(local, user_eq)
    lesionado = ctx.jugadores.get(estado.get('sim_cambio_forzado')) if ctx is not None else None
    cands = suplentes_disponibles(ctx, lado, user_eq) if lesionado is not None else []
    # primero los de su mismo puesto, luego por media
    cands = sorted(cands, key=lambda j: (j.posicion != getattr(lesionado, 'posicion', ''), -j.overall))[:10]
    if lesionado is None or not cands:
        estado['sim_cambio_forzado'] = None
        return
    sel = max(0, min(int(estado.get('sim_cambio_sel', 0) or 0), len(cands) - 1))
    elegido = None
    for k in teclas:
        if k == pygame.K_DOWN:
            sel = (sel + 1) % len(cands)
        elif k == pygame.K_UP:
            sel = (sel - 1) % len(cands)
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            elegido = cands[sel]
    filas = [pygame.Rect(R_SELECTOR.x + 20, R_SELECTOR.y + 96 + i * 34, R_SELECTOR.width - 40, 30)
             for i in range(len(cands))]
    for i, r in enumerate(filas):
        if click_pos and r.collidepoint(click_pos):
            elegido = cands[i]
    estado['sim_cambio_sel'] = sel
    draw_glass_panel(screen, R_SELECTOR, bg_color=(15, 20, 35), border_color=(255, 68, 68), alpha=240)
    draw_text(screen, f"LESIÓN: {lesionado.nombre_completo}"[:44], (R_SELECTOR.x + 20, R_SELECTOR.y + 16),
              size='lg', color='rojo')
    draw_text(screen, "Elige quién entra (↑ ↓ + Enter o clic)", (R_SELECTOR.x + 20, R_SELECTOR.y + 60),
              size='sm', color='azul')
    for i, r in enumerate(filas):
        j = cands[i]
        foco = i == sel or r.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (40, 60, 90) if foco else (20, 26, 46), r, border_radius=6)
        draw_text(screen, f"{j.posicion}  {j.nombre_completo}"[:40], (r.x + 10, r.y + 4), size='sm',
                  color='verde' if foco else 'blanco', shadow=False)
        draw_text(screen, f"OVR {j.overall}", (r.right - 90, r.y + 4), size='sm', color='dorado', shadow=False)
    if elegido is None:
        return
    try:
        alin = user_eq.alineacion_activa
        js = list(user_eq.jugadores)
        idx_sale = next(i for i, x in enumerate(js) if x is lesionado)
        idx_entra = next(i for i, x in enumerate(js) if x is elegido)
        F.intercambiar(alin, ('campo', alin.titulares.index(idx_sale)), ('banco', alin.convocados.index(idx_entra)))
        salieron = set(estado.get('sim_salieron', []) or [])
        salieron.add(idx_sale)
        estado['sim_salieron'] = sorted(salieron)
        estado['sim_subs_realizadas'] = int(estado.get('sim_subs_realizadas', 0) or 0) + 1
        minuto = estado.get('sim_minuto', 0)
        ev = evento_cambio(minuto, lado, user_eq, lesionado, elegido, ya_fuera=True)
        ev['_aplicado'] = True
        aplicar_evento(ctx, ev)
        estado.setdefault('sim_eventos_procesados', []).append(ev)
        estado['sim_eventos'].append(ev)
        estado.setdefault('sim_comentarios', []).append(f"Min {minuto}: {ev['detalle']}")
    except Exception as e_cf:
        logger.error(f"No se pudo hacer el cambio por lesión: {e_cf}")
    estado['sim_cambio_forzado'] = None
    _resimular(estado, local, visitante, user_eq, estado.get('sim_minuto', 0))
    estado['sim_last_tick'] = pygame.time.get_ticks()


def _snapshot_alineacion(equipo: Any, alin: Any) -> dict:
    """Foto de la alineación y la táctica del usuario ANTES del partido."""
    return {
        'titulares': list(alin.titulares),
        'convocados': list(getattr(alin, 'convocados', []) or []),
        'formacion': alin.formacion,
        'estilo': equipo.estilo_dt,
        'mentalidad': getattr(equipo, 'mentalidad', 'normal'),
    }


def _restaurar_alineacion(equipo: Any, alin: Any, foto: Optional[dict]) -> None:
    """v2.3.6: los cambios hechos en vivo solo valen para ese partido."""
    if not foto or equipo is None or alin is None:
        return
    alin.titulares = list(foto['titulares'])
    alin.convocados = list(foto['convocados'])
    alin.formacion = foto['formacion']
    equipo.estilo_dt = foto['estilo']
    equipo.mentalidad = foto.get('mentalidad', 'normal')


def _menu_penales(screen: pygame.Surface, estado: dict, user_eq: Any,
                  mouse_pos: tuple, click_pos: Optional[tuple], teclas: Optional[list] = None) -> Optional[list]:
    """
    Selección de cobradores antes de la tanda. Pre-selecciona el top-5 por atributo
    `penales`; el usuario puede alternar (máx 5). Devuelve la lista de Jugador al
    pulsar 'DEFINIR EN PENALES'.
    """
    try:
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((20, 8, 8, 210))
        screen.blit(ov, (0, 0))
    except Exception:
        pass

    panel = R_PENALES
    draw_glass_panel(screen, panel, bg_color=(28, 14, 14), border_color=(255, 215, 0), alpha=235)
    # v3.8.0: en una vuelta puede haber penales sin empate en el partido (global empatado)
    _empate = estado.get('sim_goles_l') == estado.get('sim_goles_v')
    draw_text(screen, f"{'EMPATE' if _empate else 'GLOBAL EMPATADO'} — ELIGE TUS 5 COBRADORES",
              (panel.x + 30, panel.y + 18 if _empate else panel.y + 24), size='lg' if _empate else 'md', color='dorado')
    draw_text(screen, "Ordenados por atributo de penales. Clic para alternar (máx 5).",
              (panel.x + 30, panel.y + 56), size='sm', color='azul')

    jugadores = list(getattr(user_eq, 'jugadores', []) or [])
    orden = sorted(range(len(jugadores)), key=lambda i: getattr(jugadores[i], 'penales', 0), reverse=True)

    # Pre-selección por defecto: top-5
    if 'sim_penales_sel' not in estado:
        estado['sim_penales_sel'] = orden[:5]
    sel = estado['sim_penales_sel']

    fila_rects = []
    y = panel.y + 95
    for idx in orden[:FILAS_PENALES]:
        j = jugadores[idx]
        r = pygame.Rect(panel.x + 30, y, 580, 32)
        elegido = idx in sel
        bg = (30, 65, 45) if elegido else (24, 26, 40)
        try:
            pygame.draw.rect(screen, bg, r, border_radius=5)
            pygame.draw.rect(screen, (0, 255, 136) if elegido else (60, 70, 95), r, width=1, border_radius=5)
        except Exception:
            pass
        orden_txt = f"{sel.index(idx) + 1}. " if elegido else "   "
        draw_text(screen, f"{orden_txt}[{j.posicion}] {j.nombre_completo[:24]}", (r.x + 10, r.y + 7), size='sm',
                  color='verde' if elegido else 'blanco')
        draw_text(screen, f"PEN {getattr(j, 'penales', 0)}", (r.right - 80, r.y + 7), size='sm', color='dorado')
        fila_rects.append((r, idx))
        y += 36

    btn_def = R_PENALES_DEFINIR
    draw_button(screen, btn_def, "DEFINIR EN PENALES", btn_def.collidepoint(mouse_pos))
    draw_text(screen, "↑ ↓ Mover · Espacio Elegir · A Automático · Enter Definir",
              (panel.x + 30, btn_def.y - 26), size='sm', color='azul')

    # v4.2.0: teclado (cursor sobre la lista, Espacio alterna, A = los 5 mejores, Enter = DEFINIR)
    cursor = max(0, min(int(estado.get('sim_penales_cursor', 0) or 0), len(fila_rects) - 1))
    for k in teclas or []:
        if k == pygame.K_DOWN and fila_rects:
            cursor = (cursor + 1) % len(fila_rects)
        elif k == pygame.K_UP and fila_rects:
            cursor = (cursor - 1) % len(fila_rects)
        elif k == pygame.K_SPACE and fila_rects:
            click_pos = fila_rects[cursor][0].center
        elif k == pygame.K_a:
            sel[:] = orden[:5]
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER) and sel:
            click_pos = btn_def.center
    estado['sim_penales_cursor'] = cursor
    if fila_rects:
        pygame.draw.rect(screen, (255, 215, 0), fila_rects[cursor][0], width=2, border_radius=5)

    if click_pos:
        for r, idx in fila_rects:
            if r.collidepoint(click_pos):
                if idx in sel:
                    sel.remove(idx)
                elif len(sel) < 5:
                    sel.append(idx)
                break
        if btn_def.collidepoint(click_pos) and sel:
            return [jugadores[i] for i in sel]
    return None


# --- Renderizador de la Pantalla ══════════════════════════════════════════════

# v4.1.0: claves del partido en vivo que se limpian al salir
_CLAVES_SIM = ('sim_resultado', 'sim_eventos', 'sim_desarrollo', 'sim_desarrollo_done', 'sim_minuto',
               'sim_goles_l', 'sim_goles_v', 'sim_comentarios', 'sim_eventos_procesados', 'sim_estado',
               'sim_tactico_abierto', 'sim_sub_out', 'sim_ctx', 'sim_pausa_hasta', 'sim_aviso', 'sim_avisos_cola',
               'sim_cambio_forzado', 'sim_cambio_sel', 'postpartido', 'postpartido_tab', 'postpartido_scroll',
               'sim_penales_resuelto', 'sim_penales_marcador', 'sim_penales_gana_user', 'sim_penales_sel',
               'sim_penales_secuencia', 'sim_penales_cobradores_l', 'sim_penales_cobradores_v',
               'sim_ment')   # la mentalidad de la IA no pasa al marcador del próximo partido


def _cerrar_partido_vivo(estado: dict, match_mode: str, liga: Any, mi_equipo: Any, partido: Any,
                         local: Any, visitante: Any, user_eq: Any, user_alin: Any,
                         goles_l: int, goles_v: int) -> None:
    """
    v4.1.0: al terminar el partido en vivo: notas finales, desarrollo de ambos equipos con los
    goleadores/notas reales, físico y correo del user, y el cierre de la jornada (liga) o el
    registro del resultado (copa) ANTES del post-partido, para que la tabla ya muestre dónde quedas.
    """
    from alpha_football import partido_ctx as PCX
    from alpha_football.ui import postpartido as PP
    ctx = estado.get('sim_ctx')
    notas = PCX.notas_finales(ctx, goles_l, goles_v) if ctx is not None else {}
    pos_antes = None

    def restaurar():
        # la alineación de antes del partido vuelve ANTES de cerrar la jornada: una venta por
        # cláusula o quiebra al cerrar reindexa la plantilla y la foto de índices quedaría vieja
        if 'sim_alin_partido' not in estado:
            return
        try:
            _restaurar_alineacion(user_eq, user_alin, estado.pop('sim_alin_partido', None))
        except Exception as e_rest:
            logger.error(f"No se pudo restaurar la alineación previa al partido: {e_rest}")

    try:
        if (match_mode != 'amistoso' and mi_equipo is not None and ctx is not None
                and mi_equipo.id in (local.id, visitante.id)):
            from alpha_football.desarrollo import desarrollar_plantilla_post_partido
            user_is_local = mi_equipo.id == local.id
            lu, lr = ('l', 'v') if user_is_local else ('v', 'l')
            st_l, st_v = PCX.stats_de_equipo(ctx, notas, 'l'), PCX.stats_de_equipo(ctx, notas, 'v')
            if match_mode == 'copa':
                # v3.8.0: en copa no se tocan las estadísticas de liga (van a copa['stats'])
                from alpha_football.ui.copa_screen import desarrollo_copa
                rep_l = desarrollo_copa(local, goles_l, goles_v, stats_partido=st_l)
                rep_v = desarrollo_copa(visitante, goles_v, goles_l, stats_partido=st_v)
            else:
                rep_l = desarrollar_plantilla_post_partido(local, goles_l, goles_v, stats_partido=st_l)
                rep_v = desarrollar_plantilla_post_partido(visitante, goles_v, goles_l, stats_partido=st_v)
            estado['sim_desarrollo'] = rep_l if user_is_local else rep_v
            try:  # v3.1.0: físico, moral y correo del partido del user
                from alpha_football.vestuario import post_partido_user
                post_partido_user(estado, mi_equipo, visitante if user_is_local else local,
                                  goles_l if user_is_local else goles_v,
                                  goles_v if user_is_local else goles_l,
                                  estado['sim_desarrollo'] or [], PCX.minutos_por_id(ctx, lu),
                                  incidencias=PCX.incidencias_de(ctx, lu),
                                  incidencias_rival=PCX.incidencias_de(ctx, lr),
                                  minutos_rival=PCX.minutos_por_id(ctx, lr))
            except Exception as e_ves:
                logger.error(f"Error de vestuario tras el partido en vivo: {e_ves}")
            restaurar()
            if match_mode == 'copa':
                try:
                    from alpha_football.ui.copa_screen import registrar_stats_copa, registrar_resultado_copa
                    registrar_stats_copa(estado, getattr(local, 'nombre', ''), goles_v, rep_l)
                    registrar_stats_copa(estado, getattr(visitante, 'nombre', ''), goles_l, rep_v)
                    pen_user = estado.get('sim_penales_marcador') if estado.get('sim_penales_resuelto') else None
                    registrar_resultado_copa(estado, goles_l, goles_v, pen_user)
                except Exception as e_reg:
                    logger.error(f"Error al registrar el partido de copa: {e_reg}")
            else:
                pos_antes = PP.posicion_liga(liga, mi_equipo.id)
                finalizar_jornada_liga(estado, liga, mi_equipo, partido, goles_l, goles_v)
    except Exception as e_dev:
        logger.error(f"Error al cerrar el partido en vivo: {e_dev}")
    restaurar()   # amistoso o sin carrera: igual se deja la alineación como estaba
    pen = estado.get('sim_penales_marcador') if estado.get('sim_penales_resuelto') else None
    if pen and mi_equipo is not None and mi_equipo.id == visitante.id:
        # el marcador de la tanda está en el punto de vista del user; el título va local-visitante
        partes = str(pen).split('-')
        if len(partes) == 2:
            pen = f"{partes[1].strip()}-{partes[0].strip()}"
    PP.armar_datos(estado, match_mode, local, visitante, goles_l, goles_v, ctx, notas,
                   estado.get('sim_eventos', []), penales=pen, pos_antes=pos_antes)


def _salir_partido(estado: dict, match_mode: str) -> str:
    """v4.1.0: limpia el partido en vivo y devuelve la pantalla de destino."""
    for k in _CLAVES_SIM:
        estado.pop(k, None)
    if match_mode == 'amistoso':
        # Fase 6: amistoso sin consecuencias; limpiar y volver al menú.
        for k in ('match_mode', 'amis_local', 'amis_visitante', 'amistoso_liga'):
            estado.pop(k, None)
        return "menu"
    if match_mode == 'copa':
        for k in ('match_mode', 'partido_local_obj', 'partido_visitante_obj', 'partido_copa_dict',
                  'partido_copa_bracket_fase'):
            estado.pop(k, None)
        estado['hub_tab'] = 'inicio'   # v2.4.0: la copa se juega desde Inicio
    return "league_screen"


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """Con un partido de copa en curso, las sanciones que cuentan son las de copa (sanciones.py)."""
    from alpha_football.sanciones import en_competicion
    with en_competicion('copa' if estado.get('match_mode') == 'copa' else 'liga'):
        return _render(screen, estado)


def _render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """
    Simula y anima el partido en vivo.
    Retorna "league_screen" al terminar, o None para seguir en pantalla.
    """
    try:
        liga = estado.get('liga')
        mi_equipo = estado.get('mi_equipo')
        # v0.8.4: `or 'liga'` (no el default de .get) porque una nueva carrera deja
        # estado['match_mode'] = None y .get(..., 'liga') devolvería None, no el default.
        match_mode = estado.get('match_mode') or 'liga'

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
        elif match_mode == 'amistoso':
            # Fase 6: partido suelto, sin impacto en liga/copa/carrera.
            local = estado.get('amis_local')
            visitante = estado.get('amis_visitante')
            partido = None
        else:
            partido = estado.get('partido_actual')
            if not liga or not mi_equipo or not partido:
                logger.error("Faltan datos para simular el partido en el estado.")
                return "league_screen"
            local = next((e for e in liga.equipos if e.id == partido.local_id), None)
            visitante = next((e for e in liga.equipos if e.id == partido.visitante_id), None)

        if not local or not visitante:
            logger.error("No se encontraron los equipos del partido.")
            if match_mode == 'copa':
                estado['hub_tab'] = 'inicio'   # v2.4.0
                return "league_screen"
            if match_mode == 'amistoso':
                return "menu"
            return "league_screen"

        # v0.7: equipo que el usuario controla en este partido (menús tácticos / penales).
        user_eq = None
        if mi_equipo and mi_equipo.id in (local.id, visitante.id):
            user_eq = mi_equipo
        elif match_mode == 'amistoso':
            user_eq = local
        user_alin = None
        if user_eq is not None:
            user_alin = getattr(user_eq, 'alineacion_activa', None)
            if user_alin is None:
                from alpha_football.models import alineacion_por_defecto
                user_alin = alineacion_por_defecto(user_eq)
                user_eq.alineacion_activa = user_alin

        # 1. Simulación de la PRIMERA MITAD al entrar. La 2ª mitad se simula DESPUÉS de la
        #    charla de medio tiempo, para que la decisión táctica afecte de verdad al motor.
        if 'sim_resultado' not in estado:
            if match_mode != 'amistoso':
                try:
                    _depurar_titulares(user_eq, user_alin)
                except Exception as e_dep:
                    logger.error(f"No se pudieron depurar los titulares: {e_dep}")
            from alpha_football.engine import simular_rango
            from alpha_football.engine import sortear_suerte
            _sl, _sv = sortear_suerte(local, visitante)
            estado["sim_suerte"] = {"suerte_l": _sl, "suerte_v": _sv}  # v2.3.6: misma suerte en todo el partido
            # v4.1.0: estado REVELADO del partido; el motor simula sobre copias
            from alpha_football.partido_ctx import nuevo_estado
            from alpha_football.engine import _once_titular
            _lu = _lado_user(local, user_eq)
            estado['sim_ctx'] = nuevo_estado(local, visitante, _once_titular(local), _once_titular(visitante),
                                             auto_l=_lu != 'l', auto_v=_lu != 'v')
            _gl1, _gv1, ev1 = simular_rango(local, visitante, 1, 45, mult=estado["sim_suerte"],
                                            minutos_previos=_minutos_previos(estado, user_eq, getattr(user_eq, 'alineacion_activa', None)),
                                            ctx=estado['sim_ctx'].copia(),
                **_ments(local, visitante, user_eq))
            # Sabor: evento caótico ocasional en la 1ª mitad
            try:
                if random.random() < 0.3:
                    ev1.append({
                        "minuto": random.randint(8, 44),
                        "tipo": "caotico",
                        "equipo_id": local.id if random.random() < 0.5 else visitante.id,
                        "detalle": random.choice([
                            "¡El DT le grita al árbitro con un megáfono!",
                            "¡Una invasión de palomas interrumpe el juego!",
                            "¡La afición hace la ola y motiva al equipo!",
                        ]),
                    })
                    ev1.sort(key=lambda e: e['minuto'])
            except Exception:
                pass
            estado['sim_resultado'] = True            # marca de inicialización
            estado['sim_eventos'] = ev1               # eventos a revelar (crece con la 2ª mitad)
            estado['sim_minuto'] = 0
            estado['sim_fin'] = 90 + random.randint(3, 10)   # v4.4.0: minutos de adición
            estado['sim_ctx'].fin = estado['sim_fin']
            estado['sim_goles_l'] = 0
            estado['sim_goles_v'] = 0
            estado['sim_comentarios'] = []
            estado['sim_eventos_procesados'] = []
            estado['sim_estado'] = 'jugando' # 'jugando', 'medio_tiempo', 'segundo_tiempo', 'finalizado'
            estado['sim_flash_goles'] = 0 # contador de frames para animación de gol
            estado['sim_goleador_flash'] = ""
            estado['sim_ajuste_realizado'] = False
            estado['sim_pausa_hasta'] = 0          # v4.1.0: pausa con aviso (gol, tarjeta, lesión)
            estado['sim_aviso'] = None
            estado['sim_avisos_cola'] = []
            estado['sim_cambio_forzado'] = None    # v4.1.0: lesión del user pendiente de cambio
            # Velocidad de simulación: factor 1 = normal, 2 = el doble de rápido. Se conserva
            # entre partidos (estado), por eso se lee con get en vez de fijarlo siempre a 1.
            # v0.8.5: una carrera nueva deja sim_velocidad_factor=None (la clave EXISTE), por lo que
            # setdefault no lo reemplaza y `MS_POR_MINUTO // None` reventaba el partido EN VIVO
            # (devolvía al usuario al menú de carrera). Normalizamos con `or 1`.
            factor_vel = estado.get('sim_velocidad_factor') or 1
            estado['sim_velocidad_factor'] = factor_vel
            estado['sim_speed'] = max(40, MS_POR_MINUTO // factor_vel)
            estado['sim_last_tick'] = pygame.time.get_ticks()
            # v0.8.1: tracking de cambios realizados por el usuario (máx 5 por partido, como en el fútbol real).
            estado['sim_subs_realizadas'] = 0
            estado['sim_salieron'] = []
            estado.pop('sim_dir_snapshot', None)
            estado['sim_alin_partido'] = (_snapshot_alineacion(user_eq, user_alin)
                                          if user_eq is not None and user_alin is not None else None)
            # v0.8.1: tracking per-jugador para F4 (cansancio y nota).
            estado['sim_minuto_por_jugador'] = {}   # {id_jugador: minutos_en_cancha}
            estado['sim_nota_por_jugador'] = {}     # {id_jugador: nota_actual}
            estado['sim_titulares_iniciales'] = list(getattr(user_alin, 'titulares', []) or []) if user_alin else []
            # v2.3.5: banco válido al arrancar (índices corridos por ventas, lesionados).
            if user_alin and user_eq is not None:
                try:
                    F.normalizar_convocados(user_alin, user_eq.jugadores)
                except Exception as e_conv:
                    logger.error(f"No se pudieron normalizar convocados: {e_conv}")

        minuto = estado['sim_minuto']
        goles_l = estado['sim_goles_l']
        goles_v = estado['sim_goles_v']
        sim_state = estado['sim_estado']
        
        # 2. Lógica del Ticker del Reloj
        now = pygame.time.get_ticks()
        if (now >= estado.get('sim_pausa_hasta', 0) and estado['sim_flash_goles'] == 0
                and estado.get('sim_cambio_forzado') is None):
            _siguiente_aviso(estado)          # venció el aviso: si hay otro en cola, se muestra
            now = pygame.time.get_ticks()
        if (sim_state in ('jugando', 'segundo_tiempo') and estado['sim_flash_goles'] == 0
                and now >= estado.get('sim_pausa_hasta', 0)                # v4.1.0
                and estado.get('sim_cambio_forzado') is None
                and not estado.get('sim_tactico_abierto')
                and not estado.get('ayuda_abierta')):          # v3.9.0: con la ayuda H abierta el reloj se pausa
            if now - estado['sim_last_tick'] >= estado['sim_speed']:
                estado['sim_minuto'] += 1
                minuto = estado['sim_minuto']
                estado['sim_last_tick'] = now
                # v0.8.1: acumular minuto jugado por cada titular en cancha del USUARIO
                # (alimenta el medidor de cansancio del menú táctico).
                try:
                    if user_eq is not None and user_alin is not None:
                        mins = estado.setdefault('sim_minuto_por_jugador', {})
                        js = list(getattr(user_eq, 'jugadores', []) or [])
                        fuera = getattr(estado.get('sim_ctx'), 'fuera', set())
                        for idx in user_alin.titulares:
                            if 0 <= idx < len(js) and id(js[idx]) not in fuera:   # v4.1.0: expulsados/lesionados no suman
                                jid = getattr(js[idx], 'id', None)
                                if jid is not None:
                                    mins[jid] = mins.get(jid, 0) + 1
                except Exception:
                    pass
                
                # Comprobar eventos de este minuto
                eventos_este_min = [e for e in estado['sim_eventos'] if e['minuto'] == minuto]
                for e in eventos_este_min:
                    if e not in estado['sim_eventos_procesados']:
                        estado['sim_eventos_procesados'].append(e)
                        
                        # Agregar comentario a la lista de scroll
                        detalle = e['detalle']
                        tipo = e['tipo']
                        # v4.1.0: el ctx revelado sigue exactamente lo que se ve en pantalla
                        if not e.get('_aplicado'):
                            try:
                                from alpha_football.partido_ctx import aplicar_evento as _aplicar
                                _aplicar(estado['sim_ctx'], e)
                            except Exception as e_ap:
                                logger.error(f"No se pudo aplicar el evento revelado: {e_ap}")
                        lado_ev = e.get('lado') or ('l' if e.get('equipo_id') == local.id else 'v')
                        eq_ev = local if lado_ev == 'l' else visitante
                        j_ev = e.get('jugador')
                        nombre_ev = getattr(j_ev, 'nombre_completo', None) or "Jugador"

                        if tipo == 'gol':
                            # v4.1.0: goleador y asistente vienen del motor (ya no se sortean aquí)
                            if e.get('equipo_id') == local.id:
                                estado['sim_goles_l'] += 1
                                goles_l = estado['sim_goles_l']
                            else:
                                estado['sim_goles_v'] += 1
                                goles_v = estado['sim_goles_v']
                            detalle = f"{e['detalle']} ({goles_l}-{goles_v})"
                            estado['sim_flash_goles'] = 25 # frames de duración
                            estado['sim_goleador_flash'] = f"{nombre_ev.upper()} ({eq_ev.nombre.upper()})"
                            _pausar(estado, 'gol', f"{nombre_ev} ({eq_ev.nombre})", 'verde')

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

                        elif tipo in ('amarilla', 'roja', 'lesion'):
                            # v4.1.0: tarjetas y lesiones detienen el reloj con un aviso
                            _pausar(estado, tipo, f"{nombre_ev} ({eq_ev.nombre})",
                                    'dorado' if tipo == 'amarilla' else 'rojo')
                            detalle = {'amarilla': "AMARILLA: ", 'roja': "ROJA: ", 'lesion': "LESIÓN: "}[tipo] + detalle
                            if tipo == 'lesion' and lado_ev == _lado_user(local, user_eq):
                                try:
                                    from alpha_football.engine import suplentes_disponibles
                                    from alpha_football.partido_ctx import clave as _clave
                                    if (int(estado.get('sim_subs_realizadas', 0) or 0) < 5
                                            and suplentes_disponibles(estado['sim_ctx'], lado_ev, user_eq)):
                                        estado['sim_cambio_forzado'] = _clave(j_ev)
                                        estado['sim_cambio_sel'] = 0
                                    else:
                                        estado['sim_comentarios'].append(
                                            f"Min {minuto}: Sin cambios disponibles: {eq_ev.nombre} sigue con uno menos")
                                except Exception as e_les:
                                    logger.error(f"Error al preparar el cambio por lesión: {e_les}")
                        elif tipo == 'cambio':
                            detalle = f"CAMBIO: {detalle}"
                        elif tipo == 'caotico':
                            detalle = f"(!) {detalle}"   # v4.1.0: sin emoji (la fuente no lo tiene)
                        elif tipo == 'mentalidad':
                            # v2.5.0: la IA cambió de mentalidad (se ve en el marcador).
                            estado.setdefault('sim_ment', {})[e.get('equipo_id')] = e.get('mentalidad')
                            detalle = f"» {detalle}"
                            
                        estado['sim_comentarios'].append(f"Min {minuto}: {detalle}")
                
                # v4.1.0: nota en vivo del user desde el ctx (la muestra la dirección en vivo)
                try:
                    from alpha_football.partido_ctx import nota_en_vivo as _nv
                    _c, _lu = estado['sim_ctx'], _lado_user(local, user_eq)
                    estado['sim_nota_por_jugador'] = {getattr(jj, 'id', None): _nv(_c, k)
                                                      for k, jj in _c.jugadores.items() if _c.lado_jugador.get(k) == _lu}
                except Exception as e_nv:
                    logger.error(f"No se pudo actualizar la nota en vivo: {e_nv}")

                # Medio tiempo
                if minuto == 45 and sim_state == 'jugando':
                    estado['sim_estado'] = 'medio_tiempo'
                    sim_state = 'medio_tiempo'
                    
                if minuto == 90 and estado.get('sim_fin', 90) > 90:   # v4.4.0
                    estado['sim_comentarios'].append(f"Min 90: Se adicionan {estado['sim_fin'] - 90} minutos.")
                # Fin del partido
                if minuto >= estado.get('sim_fin', 90):
                    estado['sim_estado'] = 'finalizado'
                    sim_state = 'finalizado'
                    
        # 3. Dibujar interfaz alegre de fútbol
        draw_happy_pitch(screen)
        
        # A. Scoreboard Grande con Glassmorphism y borde neón dorado
        board_rect = R_MARCADOR
        draw_glass_panel(screen, board_rect, bg_color=(10, 25, 20), border_color=(255, 215, 0), alpha=210)
        
        # Nombre corto (v0.7) para evitar solapamiento con el marcador.
        local_nombre_trunc = (getattr(local, 'corto', None) or local.nombre)[:20].upper()
        visitante_nombre_trunc = (getattr(visitante, 'corto', None) or visitante.nombre)[:20].upper()
        
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
        _fin = int(estado.get('sim_fin', 90))   # v4.4.0: 90+X' en la adición
        reloj_str = ("FINAL" if minuto >= _fin else f"90+{minuto - 90}'" if minuto > 90 else f"{minuto}'")
        r_w = get_font('md').size(reloj_str)[0]
        draw_text(screen, reloj_str, (SCREEN_W // 2 - r_w // 2, 115), size='md', color='azul')

        # v2.5.0: mentalidad actual de cada equipo bajo su nombre (la del user es la suya;
        # la del rival, la del último cambio revelado o la que decide la IA al empezar).
        try:
            from alpha_football.engine import NOMBRE_MENTALIDAD, mentalidad_ia
            ments_vis = estado.setdefault('sim_ment', {})
            for eq, rival, es_local in ((local, visitante, True), (visitante, local, False)):
                if user_eq is not None and getattr(eq, 'id', None) == getattr(user_eq, 'id', None):
                    m = getattr(user_eq, 'mentalidad', 'normal')
                else:
                    if eq.id not in ments_vis:
                        ments_vis[eq.id] = mentalidad_ia(eq, rival, 1, 0, 0, es_local)
                    m = ments_vis[eq.id]
                txt = NOMBRE_MENTALIDAD.get(m, 'NORMAL')
                x = 95 if es_local else 1220 - get_font('sm').size(txt)[0]
                draw_text(screen, txt, (x, 84), size='sm', color='rojo' if m == 'todo_o_nada' else 'azul')
        except Exception as e_ment:
            logger.error(f"Error al dibujar mentalidades: {e_ment}")

        # Botón de velocidad: cicla x1 / x2 / x5 para acelerar la simulación.
        factor_vel = estado.get('sim_velocidad_factor', 1)
        rect_velocidad = R_VELOCIDAD
        draw_button(screen, rect_velocidad, f"VEL x{factor_vel}", rect_velocidad.collidepoint(pygame.mouse.get_pos()))

        # Botón TÁCTICA: abre el menú de formación/táctica/dirección durante el partido.
        rect_tactica = R_TACTICA
        mostrar_tactica = (user_eq is not None and sim_state in ('jugando', 'segundo_tiempo')
                           and not estado.get('sim_tactico_abierto')
                           and estado.get('sim_cambio_forzado') is None)   # selector de lesión abierto
        if mostrar_tactica:
            draw_button(screen, rect_tactica, "TÁCTICA", rect_tactica.collidepoint(pygame.mouse.get_pos()))
        
        # Barra de progreso del partido interactiva con pelotita corriendo
        try:
            progress_x_start = 80
            progress_x_end = 1200
            progress_width = progress_x_end - progress_x_start
            progress_y = 110
            
            # Fondo de la barra
            pygame.draw.line(screen, (40, 70, 50), (progress_x_start, progress_y), (progress_x_end, progress_y), width=6)
            
            # Progreso verde neón
            progreso_actual = min(1.0, max(0.0, minuto / float(estado.get('sim_fin', 90))))
            current_ball_x = int(progress_x_start + progreso_actual * progress_width)
            pygame.draw.line(screen, (0, 255, 136), (progress_x_start, progress_y), (current_ball_x, progress_y), width=6)
            
            # Pequeña pelotita corriendo sobre la barra
            pygame.draw.circle(screen, (255, 255, 255), (current_ball_x, progress_y), 8)
            pygame.draw.circle(screen, (0, 0, 0), (current_ball_x, progress_y), 8, width=1)
        except Exception as e_progress:
            logger.error(f"Error al dibujar barra de progreso del marcador: {e_progress}")
            
        # B. Panel de Comentarios Scrolling con Glassmorphism y borde azul
        comm_rect = R_TRANSMISION
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
        teclas = []
        teclas_ev = []     # v4.2.0: los eventos completos van al menú táctico (dirección en vivo)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "menu"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                click_pos = event.pos
            elif event.type == pygame.KEYDOWN:
                teclas.append(event.key)
                teclas_ev.append(event)

        # v4.1.0: Enter/Espacio salta la pausa del aviso (con el selector abierto, las teclas son suyas)
        if estado.get('sim_cambio_forzado') is not None:
            estado['sim_pausa_hasta'] = 0
        elif (any(k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE) for k in teclas)
              and (pygame.time.get_ticks() < estado.get('sim_pausa_hasta', 0) or estado['sim_flash_goles'] > 0)):
            estado['sim_pausa_hasta'] = 0
            estado['sim_flash_goles'] = 0
            _siguiente_aviso(estado)          # Enter salta solo el aviso actual, no toda la cola
            teclas = [k for k in teclas if k not in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)]
            teclas_ev = [ev for ev in teclas_ev if ev.key not in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)]

        # Clic en velocidad: cicla x1 -> x2 -> x5 y actualiza el ritmo del reloj al instante.
        if click_pos and rect_velocidad.collidepoint(click_pos):
            nuevo_factor = {1: 2, 2: 5, 5: 1}.get(estado.get('sim_velocidad_factor', 1), 1)
            estado['sim_velocidad_factor'] = nuevo_factor
            estado['sim_speed'] = max(40, MS_POR_MINUTO // nuevo_factor)
            click_pos = None  # consumir el clic para que no active otra cosa debajo

        # v4.2.0: teclado en vivo: V velocidad, T táctica, 1-5 mentalidad
        if (sim_state in ('jugando', 'segundo_tiempo') and not estado.get('sim_tactico_abierto')
                and estado.get('sim_cambio_forzado') is None):
            for k in teclas:
                if k == pygame.K_v:
                    nuevo_factor = {1: 2, 2: 5, 5: 1}.get(estado.get('sim_velocidad_factor', 1), 1)
                    estado['sim_velocidad_factor'] = nuevo_factor
                    estado['sim_speed'] = max(40, MS_POR_MINUTO // nuevo_factor)
                elif k == pygame.K_t and mostrar_tactica:
                    estado['sim_tactico_abierto'] = True
                elif pygame.K_1 <= k <= pygame.K_5 and mostrar_tactica:
                    try:
                        from alpha_football.engine import MENTALIDADES
                        nueva_m = MENTALIDADES[k - pygame.K_1]
                        if nueva_m != getattr(user_eq, 'mentalidad', 'normal'):
                            _cambiar_mentalidad_en_vivo(estado, user_eq, local, visitante, nueva_m, minuto)
                    except Exception as e_tm:
                        logger.error(f"Error al cambiar la mentalidad con el teclado: {e_tm}")
        if mostrar_tactica:
            draw_text(screen, "V Velocidad · T Táctica · 1-5 Mentalidad · Enter Saltar aviso · H Ayuda",
                      (60, 612), size='sm', color='blanco')

        # v2.5.0: tira de MENTALIDAD (sin pausar; re-simula el resto de la mitad).
        if mostrar_tactica:
            try:
                from alpha_football.engine import MENTALIDADES, NOMBRE_MENTALIDAD
                draw_text(screen, "MENTALIDAD", (60, 572), size='sm', color='dorado')
                actual = getattr(user_eq, 'mentalidad', 'normal')
                for m, r in zip(MENTALIDADES, _rects_tira_mentalidad()):
                    draw_button(screen, r, NOMBRE_MENTALIDAD[m], r.collidepoint(pygame.mouse.get_pos()) or m == actual)
                    if m == actual:
                        pygame.draw.rect(screen, (255, 215, 0), r, width=3, border_radius=8)
                    if click_pos and r.collidepoint(click_pos):
                        click_pos = None
                        if m != actual:
                            _cambiar_mentalidad_en_vivo(estado, user_eq, local, visitante, m, minuto)
            except Exception as e_tira:
                logger.error(f"Error en la tira de mentalidad: {e_tira}")

        # Clic en TÁCTICA: abre el overlay de ajuste táctico en vivo (pausa el reloj).
        if mostrar_tactica and click_pos and rect_tactica.collidepoint(click_pos):
            estado['sim_tactico_abierto'] = True
            click_pos = None

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
            
        # B. Ajuste táctico EN VIVO (botón TÁCTICA durante el juego) — pausa el reloj.
        elif (estado.get('sim_tactico_abierto') and user_eq is not None
              and estado.get('sim_cambio_forzado') is None):   # v4.1.0: primero el cambio por lesión
            res = _menu_tactico(screen, estado, user_eq, user_alin, mouse_pos, click_pos,
                                "AJUSTE TÁCTICO EN VIVO", key_events=teclas_ev)
            if res == 'reanudar':
                estado['sim_tactico_abierto'] = False
                # Re-simular SOLO el tramo restante de la mitad en curso con la nueva config.
                _resimular(estado, local, visitante, user_eq, minuto)   # v4.1.0: desde lo revelado
                estado['sim_last_tick'] = pygame.time.get_ticks()

        # C. Medio Tiempo: menú de formación / táctica / dirección + REANUDAR.
        elif sim_state == 'medio_tiempo' and estado.get('sim_cambio_forzado') is None:
            if user_eq is not None:
                res = _menu_tactico(screen, estado, user_eq, user_alin, mouse_pos, click_pos,
                                    "MEDIO TIEMPO — FORMACIÓN / TÁCTICA / DIRECCIÓN", key_events=teclas_ev)
                if res == 'reanudar':
                    estado['sim_comentarios'].append(
                        f"DT: {user_eq.estilo_dt} en {user_alin.formacion}. ¡A la segunda mitad!")
                    _resimular(estado, local, visitante, user_eq, 45, int(estado.get('sim_fin', 90)))   # v4.1.0: 2ª mitad desde lo revelado
                    estado['sim_estado'] = 'segundo_tiempo'
                    estado['sim_last_tick'] = pygame.time.get_ticks()
            else:
                # Sin equipo controlable (caso raro): simular la 2ª mitad y continuar.
                _resimular(estado, local, visitante, user_eq, 45, int(estado.get('sim_fin', 90)))
                estado['sim_estado'] = 'segundo_tiempo'
                estado['sim_last_tick'] = pygame.time.get_ticks()

        # D. Pantalla Finalizada
        elif sim_state == 'finalizado':
            # v3.8.0: definición por penales si el motor lo pide (final empatada o global empatado).
            es_bracket_copa = False
            if match_mode == 'copa' and not estado.get('sim_penales_resuelto'):
                try:
                    from alpha_football.ui.copa_screen import necesita_penales
                    es_bracket_copa = necesita_penales(estado, goles_l, goles_v)
                except Exception as e_np:
                    logger.error(f"Error al consultar si hay penales: {e_np}")
            if es_bracket_copa and user_eq is not None and not estado.get('sim_penales_resuelto'):
                cobradores = _menu_penales(screen, estado, user_eq, mouse_pos, click_pos, teclas)
                if cobradores is not None:
                    try:
                        from alpha_football.engine import tanda_penales_jugadores
                        rival_eq = visitante if user_eq.id == local.id else local
                        rivales_pen = sorted(getattr(rival_eq, 'jugadores', []),
                                             key=lambda j: getattr(j, 'penales', 0), reverse=True)[:5]
                        # v0.8.7: la firma ahora devuelve (gana_user, marcador, secuencia)
                        gana_user, marcador, secuencia = tanda_penales_jugadores(cobradores, rivales_pen)
                        estado['sim_penales_resuelto'] = True
                        estado['sim_penales_marcador'] = marcador
                        estado['sim_penales_gana_user'] = gana_user
                        estado['sim_penales_secuencia'] = secuencia
                        estado['sim_penales_cobradores_l'] = [getattr(j, 'apellido', '?') for j in cobradores]
                        estado['sim_penales_cobradores_v'] = [getattr(j, 'apellido', '?') for j in rivales_pen]
                        estado.pop('sim_penales_sel', None)
                        estado['sim_comentarios'].append(f"¡Definición por penales {marcador}!")
                    except Exception as e_pen:
                        logger.error(f"Error en la tanda de penales: {e_pen}")
                        estado['sim_penales_resuelto'] = True
                return None  # mientras se eligen cobradores no se dibuja el panel final

            # v4.1.0: cierre UNA sola vez (desarrollo con lo que pasó en la cancha, físico,
            # jornada o copa) y pantalla post-partido: calificaciones + tabla antes de continuar.
            if not estado.get('sim_desarrollo_done'):
                estado['sim_desarrollo_done'] = True
                _cerrar_partido_vivo(estado, match_mode, liga, mi_equipo, partido, local, visitante,
                                     user_eq, user_alin, goles_l, goles_v)
            from alpha_football.ui import postpartido as _pp
            if _pp.render(screen, estado, mouse_pos, click_pos, teclas) == 'continuar':
                return _salir_partido(estado, match_mode)
            return None

        # v4.1.0: selector de cambio por lesión o aviso de incidencia (encima de todo)
        if estado.get('sim_cambio_forzado') is not None and user_eq is not None:
            _selector_cambio(screen, estado, user_eq, local, visitante, teclas, mouse_pos, click_pos)
        elif (pygame.time.get_ticks() < estado.get('sim_pausa_hasta', 0) and estado['sim_flash_goles'] == 0
              and estado.get('sim_aviso')):
            _dibujar_aviso(screen, estado)

        return None
    except Exception as e:
        logger.error(f"Error crítico en render de match_screen: {e}")
        return "league_screen"
