# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Pantalla de la Carrera del DT (Pygame)
Muestra las estadísticas globales del DT (títulos, goles, temporadas)
y un historial detallado por temporada con récords y fallbacks resilientes.
Implementa una barra lateral consistente con league_screen y previene bugs de clics.
"""

import sys
import os
import logging

# Configuración del logger para seguimiento de eventos y errores
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
logger = logging.getLogger(__name__)

# Intentar importar pygame de manera segura
try:
    import pygame
except ImportError as error_pygame:
    logger.critical(f"Error crítico al importar pygame en career_screen: {error_pygame}. La UI no podrá renderizarse.")
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
    logger.warning(f"Advertencia: No se pudo importar alpha_football.ui.theme ({error_import_theme}). Usando fallback local.")
    
    # Fallback local para garantizar la continuidad del sistema si falla el tema
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
    
    def get_font(size):
        try:
            if size == 'sm': return pygame.font.SysFont("Arial", 16)
            elif size == 'md': return pygame.font.SysFont("Arial", 20)
            elif size == 'lg': return pygame.font.SysFont("Arial", 28)
            elif size == 'xl': return pygame.font.SysFont("Arial", 42)
        except Exception as e_font:
            logger.error(f"Fallo en get_font local: {e_font}")
        return pygame.font.Font(None, 24)
        
    def draw_gradient_bg(screen):
        try:
            screen.fill((10, 14, 26))
        except Exception as e_bg:
            logger.error(f"Error en draw_gradient_bg local: {e_bg}")
        
    def draw_panel(screen, rect):
        try:
            pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=8)
            pygame.draw.rect(screen, (0, 191, 255), rect, width=1, border_radius=8)
        except Exception:
            try:
                pygame.draw.rect(screen, (20, 26, 46), rect)
            except Exception as e_panel:
                logger.error(f"Error al dibujar panel local: {e_panel}")
        
    def draw_button(screen, rect, text, hover):
        try:
            color_bg = (0, 191, 255) if hover else (20, 26, 46)
            color_fg = (10, 14, 26) if hover else (255, 255, 255)
            pygame.draw.rect(screen, color_bg, rect, border_radius=5)
            pygame.draw.rect(screen, (255, 255, 255), rect, width=1, border_radius=5)
            
            font = get_font('md')
            txt_surf = font.render(text, True, color_fg)
            txt_rect = txt_surf.get_rect(center=rect.center)
            screen.blit(txt_surf, txt_rect)
        except Exception as error_local_btn:
            logger.error(f"Error en draw_button fallback local: {error_local_btn}")
        return rect
        
    def draw_text(screen, text, pos, size='md', color='blanco', shadow=True):
        try:
            rgb_color = COLORS.get(color, (255, 255, 255))
            font = get_font(size)
            if shadow:
                shadow_surf = font.render(text, True, (0, 0, 0))
                screen.blit(shadow_surf, (pos[0] + 1, pos[1] + 1))
            txt_surf = font.render(text, True, rgb_color)
            screen.blit(txt_surf, pos)
        except Exception as error_local_txt:
            logger.error(f"Error en draw_text fallback local: {error_local_txt}")

def draw_pitch_lines(screen: pygame.Surface) -> None:
    """
    Dibuja de forma sutil las marcas de un campo de fútbol en el fondo.
    Proporciona un ambiente alegre y deportivo sin interferir con la interfaz.
    """
    try:
        # Color verde azulado muy tenue sobre el fondo azul marino profundo
        pitch_color = (20, 38, 62)
        
        # Círculo central en la parte derecha
        pygame.draw.circle(screen, pitch_color, (750, 360), 120, 2)
        pygame.draw.circle(screen, pitch_color, (750, 360), 6)
        
        # Línea divisoria de centro de campo
        pygame.draw.line(screen, pitch_color, (750, 20), (750, 700), 2)
        
        # Áreas grandes de juego de ambos lados
        pygame.draw.rect(screen, pitch_color, pygame.Rect(260, 110, 160, 500), 2)
        pygame.draw.rect(screen, pitch_color, pygame.Rect(1080, 110, 160, 500), 2)
        
    except Exception as error_pitch:
        # En caso de error, capturamos para no interrumpir el flujo visual
        logger.error(f"Error al dibujar líneas del campo en carrera: {error_pitch}. Continuando con ejecución.")

def draw_styled_button(screen: pygame.Surface, rect: pygame.Rect, text: str, hover: bool, accent_color: tuple[int, int, int] | str, enabled: bool = True) -> pygame.Rect:
    """
    Dibuja un botón interactivo de acuerdo con la nueva identidad de colores.
    Soporta botones deshabilitados/bloqueados y colores de acento dinámicos.
    """
    try:
        button_rect = pygame.Rect(rect)
        
        # Conversión del color de acento si viene como Hex string o tipo diferente
        real_accent = accent_color
        if isinstance(accent_color, str) and accent_color.startswith('#'):
            try:
                real_accent = (int(accent_color[1:3], 16), int(accent_color[3:5], 16), int(accent_color[5:7], 16))
            except Exception:
                real_accent = (0, 191, 255) # Fallback azul celeste
        
        # Obtener los colores básicos RGB
        color_panel = COLORS.get('panel', (20, 26, 46))
        color_azul = COLORS.get('azul', (0, 191, 255))
        color_blanco = COLORS.get('blanco', (255, 255, 255))

        if not enabled:
            # Color gris oscuro apagado para botones deshabilitados o bloqueados
            bg_color = (25, 25, 35)
            border_color = (75, 75, 85)
            text_color = (110, 110, 120)
        elif hover:
            # Estilo hover activo con el color de acento asignado al botón
            bg_color = (30, 45, 75)
            border_color = real_accent
            text_color = real_accent
        else:
            # Estilo normal inactivo
            bg_color = color_panel
            border_color = color_azul
            text_color = color_blanco
            
        # Dibujar fondo y borde con esquinas redondeadas
        try:
            pygame.draw.rect(screen, bg_color, button_rect, border_radius=8)
            pygame.draw.rect(screen, border_color, button_rect, width=2, border_radius=8)
        except TypeError:
            pygame.draw.rect(screen, bg_color, button_rect)
            pygame.draw.rect(screen, border_color, button_rect, width=2)
            
        # Dibujar texto del botón centrado
        try:
            font = get_font('md')
            text_surf = font.render(text, True, text_color)
            text_rect = text_surf.get_rect(center=button_rect.center)
            screen.blit(text_surf, text_rect)
        except Exception as error_texto:
            logger.error(f"Error renderizando texto de botón '{text}': {error_texto}")
            
        return button_rect
    except Exception as error_btn:
        logger.error(f"Error general en draw_styled_button: {error_btn}. Utilizando dibujo plano de emergencia.")
        try:
            pygame.draw.rect(screen, (50, 50, 50), rect)
        except Exception:
            pass
        return rect

def _norm_str(s) -> str:
    """Normaliza string removiendo acentos para comparaciones robustas."""
    return (
        str(s).lower()
        .replace('á', 'a').replace('é', 'e').replace('í', 'i')
        .replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n')
    )


def _resumen_historial(historial: list) -> dict:
    """Totales de la carrera a partir del historial por temporada."""
    tot = {'temporadas': len(historial), 'ligas': 0, 'copas': 0, 'pts': 0, 'gf': 0, 'gc': 0,
           'mejor_pts': 0, 'mejor_temp': '-'}
    for h in historial:
        try:
            if h.get('pos', 99) == 1:
                tot['ligas'] += 1
            lib = _norm_str(h.get('libertadores', ''))
            if 'campeon' in lib and 'sub' not in lib:
                tot['copas'] += 1
            tot['pts'] += h.get('pts', 0)
            tot['gf'] += h.get('gf', 0)
            tot['gc'] += h.get('gc', 0)
            if h.get('pts', 0) > tot['mejor_pts']:
                tot['mejor_pts'] = h.get('pts', 0)
                tot['mejor_temp'] = f"T{h.get('temporada', 1)}"
        except Exception as e_calc:
            logger.error(f"Error procesando registro de historial de carrera: {e_calc}")
    return tot


# v3.9.0: rects expuestos (ayuda H). Las cajas terminan en y=696 (antes 700: pisaban la barra de atajos).
R_VOLVER = pygame.Rect(SCREEN_W - 230, 22, 200, 48)
R_TOTALES = pygame.Rect(30, 105, 360, 290)
R_BALON_ORO = pygame.Rect(30, 410, 360, 286)
R_TEMPORADAS = pygame.Rect(410, 105, SCREEN_W - 440, 591)


def render(screen: pygame.Surface, estado: dict) -> str | None:
    """
    Pantalla de Historial de Carrera del DT.
    v2.3.6: solo el historial (sin el menú lateral viejo, que ahora vive en la barra
    superior de la liga): totales, temporada por temporada y palmarés del Balón de Oro.
    VOLVER / Esc regresa a la liga. Rueda o flechas para desplazar las temporadas.
    """
    try:
        liga = estado.get('liga')
        mi_equipo = estado.get('mi_equipo')
        historial = [h for h in (estado.get('historial') or []) if isinstance(h, dict)]
        if not liga or not mi_equipo:
            logger.error("No hay liga o equipo cargado en el estado de carrera.")
            return "menu"

        mouse_pos = pygame.mouse.get_pos()
        click_pos = None
        scroll_delta = 0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                click_pos = event.pos
            elif event.type == pygame.MOUSEWHEEL:
                scroll_delta -= event.y
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_RETURN):
                    estado.pop('career_scroll_offset', None)
                    return "volver"
                if event.key == pygame.K_UP:
                    scroll_delta -= 1
                elif event.key == pygame.K_DOWN:
                    scroll_delta += 1

        draw_gradient_bg(screen)
        draw_text(screen, "HISTORIAL DE CARRERA", (30, 18), size='xl', color='dorado')
        draw_text(screen, f"{estado.get('dt_nombre', 'Mister')[:20]} con {mi_equipo.nombre[:28]}  ·  "
                          f"Temporada actual {estado.get('temporada', 1)}", (32, 70), size='sm', color='azul')
        btn_volver = R_VOLVER
        draw_styled_button(screen, btn_volver, "VOLVER", btn_volver.collidepoint(mouse_pos), COLORS['verde'])

        # --- Totales ---
        tot = _resumen_historial(historial)
        dg = tot['gf'] - tot['gc']
        caja_tot = R_TOTALES
        draw_panel(screen, caja_tot)
        draw_text(screen, "TOTALES", (caja_tot.x + 18, caja_tot.y + 12), size='md', color='azul')
        filas_tot = [
            ("Temporadas", str(tot['temporadas']), 'blanco'),
            ("Ligas ganadas", str(tot['ligas']), 'dorado' if tot['ligas'] else 'blanco'),
            ("Copas internacionales", str(tot['copas']), 'dorado' if tot['copas'] else 'blanco'),
            ("Puntos totales", str(tot['pts']), 'blanco'),
            ("Goles (GF-GC)", f"{tot['gf']}-{tot['gc']} ({'+' if dg > 0 else ''}{dg})", 'verde' if dg >= 0 else 'rojo'),
            ("Récord de puntos", f"{tot['mejor_pts']} ({tot['mejor_temp']})", 'blanco'),
        ]
        for i, (k, v, col) in enumerate(filas_tot):
            yy = caja_tot.y + 50 + i * 38
            draw_text(screen, k, (caja_tot.x + 18, yy), size='sm', color='blanco')
            draw_text(screen, v, (caja_tot.x + 220, yy), size='sm', color=col)

        # --- Balón de Oro (palmarés de todas las ligas) ---
        balones = list(((estado.get('datos_carrera') or {}).get('balon_oro') or []))
        caja_bo = R_BALON_ORO
        draw_panel(screen, caja_bo)
        draw_text(screen, "BALÓN DE ORO", (caja_bo.x + 18, caja_bo.y + 12), size='md', color='dorado')
        if not balones:
            draw_text(screen, "Se entrega al cerrar cada", (caja_bo.x + 18, caja_bo.y + 56), size='sm', color='blanco')
            draw_text(screen, "temporada al mejor de las 10 ligas.", (caja_bo.x + 18, caja_bo.y + 80), size='sm', color='blanco')
        for i, b in enumerate(reversed(balones[-6:])):
            g = b.get('ganador') or {}
            yy = caja_bo.y + 50 + i * 38
            es_mio = g.get('equipo') == mi_equipo.nombre
            draw_text(screen, f"T{b.get('temporada', '?')}  {str(g.get('nombre', '?'))[:22]}", (caja_bo.x + 18, yy),
                      size='sm', color='verde' if es_mio else 'blanco')
            draw_text(screen, f"{str(g.get('equipo', '?'))[:18]} · {g.get('goles', 0)} G · {g.get('nota', 0):.1f}",
                      (caja_bo.x + 40, yy + 18), size='sm', color='azul', shadow=False)

        # --- Temporada por temporada ---
        caja_h = R_TEMPORADAS
        draw_panel(screen, caja_h)
        draw_text(screen, "TEMPORADA POR TEMPORADA", (caja_h.x + 18, caja_h.y + 12), size='md', color='azul')
        cols = [("Temp", 18), ("Equipo", 80), ("Pos.", 300), ("PTS", 370), ("GF-GC", 430),
                ("Campeón de liga", 520), ("Copa internac.", 700)]
        for titulo, dx in cols:
            draw_text(screen, titulo, (caja_h.x + dx, caja_h.y + 48), size='sm', color='dorado')
        pygame.draw.line(screen, COLORS.get('azul', (0, 191, 255)),
                         (caja_h.x + 16, caja_h.y + 72), (caja_h.right - 16, caja_h.y + 72), 1)

        visibles = 13
        max_scroll = max(0, len(historial) - visibles)
        scroll = max(0, min(max_scroll, int(estado.get('career_scroll_offset', 0) or 0) + scroll_delta))
        estado['career_scroll_offset'] = scroll
        if not historial:
            draw_text(screen, "Aún no has completado ninguna temporada.", (caja_h.x + 18, caja_h.y + 96),
                      size='md', color='blanco')
        for i, h in enumerate(historial[scroll:scroll + visibles]):
            try:
                yy = caja_h.y + 84 + i * 38
                pos = h.get('pos', h.get('posicion', '?'))
                lib = str(h.get('libertadores', '-') or '-')
                lib_n = _norm_str(lib)
                lib_col = 'dorado' if ('campeon' in lib_n or 'final' in lib_n) else 'blanco'
                pos_col = 'dorado' if pos == 1 else ('verde' if isinstance(pos, int) and pos <= 3 else 'blanco')
                draw_text(screen, f"T{h.get('temporada', '?')}", (caja_h.x + 18, yy), size='sm', color='azul')
                draw_text(screen, str(h.get('equipo', mi_equipo.nombre))[:20], (caja_h.x + 80, yy), size='sm', color='blanco')
                draw_text(screen, f"{pos}º", (caja_h.x + 300, yy), size='sm', color=pos_col)
                draw_text(screen, str(h.get('pts', h.get('puntos', 0))), (caja_h.x + 370, yy), size='sm', color='blanco')
                draw_text(screen, f"{h.get('gf', 0)}-{h.get('gc', 0)}", (caja_h.x + 430, yy), size='sm', color='blanco')
                draw_text(screen, str(h.get('campeon_liga', '-'))[:18], (caja_h.x + 520, yy), size='sm', color='blanco')
                draw_text(screen, lib[:18], (caja_h.x + 700, yy), size='sm', color=lib_col)
            except Exception as e_row:
                logger.error(f"Error al dibujar fila de historial: {e_row}")
        if max_scroll:
            draw_text(screen, f"Flechas / rueda: {scroll + 1}-{min(len(historial), scroll + visibles)} de {len(historial)}",
                      (caja_h.right - 280, caja_h.bottom - 30), size='sm', color='azul', shadow=False)

        if click_pos and btn_volver.collidepoint(click_pos):
            estado.pop('career_scroll_offset', None)
            return "volver"
    except Exception as general_error:
        logger.error(f"Error en career_screen: {general_error}", exc_info=True)
        return "volver"
    return None
