# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Pantalla de Promoción / Relegación (v2.3.3).

Se muestra al FINAL de cada temporada, ANTES de empezar la siguiente.
Lista los equipos que ASCIENDEN de 2ª a 1ª y los que DESCIENDEN de 1ª a 2ª.
Botón "CONTINUAR" (Enter / Space / click) confirma y avanza al resumen de temporada.

Estado esperado:
    estado['promo_releg_data'] = {
        'ascendidos':  [ {nombre, ovr, division_origen, division_destino}, ... ],
        'descendidos': [ {nombre, ovr, division_origen, division_destino}, ... ],
        'user_ascendio': bool,
        'user_descendio': bool,
    }

Cuando no hay datos en el estado, esta pantalla se salta sin error.
"""
from __future__ import annotations

import logging
import pygame
from typing import Optional

try:
    from alpha_football.ui.theme import (
        SCREEN_W, SCREEN_H, COLORS, get_font, draw_gradient_bg, draw_panel, draw_text, draw_button
    )
except Exception:
    SCREEN_W, SCREEN_H = 1280, 720
    COLORS = {'bg': (10, 14, 26), 'verde': (0, 255, 136), 'dorado': (255, 215, 0),
              'rojo': (255, 68, 68), 'azul': (0, 191, 255), 'blanco': (255, 255, 255),
              'panel': (20, 26, 46)}
    def get_font(size): return pygame.font.Font(None, 24)
    def draw_gradient_bg(screen): screen.fill((10, 14, 26))
    def draw_panel(screen, rect): pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=8)
    def draw_button(screen, rect, text, hover): pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=6)
    def draw_text(screen, text, pos, size='md', color='blanco', shadow=True): pass

logger = logging.getLogger(__name__)


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """Renderiza la pantalla de promo/releg. Retorna:
       - 'resumen_temporada_screen' si el usuario pulsa CONTINUAR / Enter / Esc
       - None para quedarse en esta pantalla
       - 'menu' como fallback defensivo
    """
    try:
        data = estado.get('promo_releg_data') or {}
        ascendidos = data.get('ascendidos', []) or []
        descendidos = data.get('descendidos', []) or []
        user_asc = bool(data.get('user_ascendio'))
        user_des = bool(data.get('user_descendio'))

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

        # Layout
        draw_gradient_bg(screen)

        # Banner segun si el user ascendio/descendio/nada
        if user_asc:
            banner_text = "¡ASCENDISTE A 1ª DIVISIÓN!"
            banner_color = 'verde'
        elif user_des:
            banner_text = "¡DESCENDISTE A 2ª DIVISIÓN!"
            banner_color = 'rojo'
        else:
            banner_text = "PROMOCIÓN / RELEGACIÓN"
            banner_color = 'dorado'

        # Cabecera
        draw_panel(screen, pygame.Rect(0, 0, SCREEN_W, 90))
        draw_text(screen, banner_text, (SCREEN_W // 2 - 350, 22), size='xl', color=banner_color)
        sub = "Resumen de movimientos entre 1ª y 2ª división"
        draw_text(screen, sub, (SCREEN_W // 2 - 220, 60), size='sm', color='azul')

        # 2 columnas: izquierda ascendidos (verde), derecha descendidos (rojo)
        col_w = 540
        col_h = 460
        gap = 40
        total_w = col_w * 2 + gap
        x_left = (SCREEN_W - total_w) // 2
        x_right = x_left + col_w + gap
        y_top = 130

        # Columna ASCENDIDOS
        draw_panel(screen, pygame.Rect(x_left, y_top, col_w, col_h))
        draw_text(screen, "⬆ ASCENDEN A 1ª", (x_left + 20, y_top + 14), size='lg', color='verde')
        pygame.draw.line(screen, COLORS.get('verde', (0, 255, 136)),
                         (x_left + 20, y_top + 56), (x_left + col_w - 20, y_top + 56), 2)
        if not ascendidos:
            draw_text(screen, "Sin ascensos esta temporada.", (x_left + 30, y_top + 90),
                      size='sm', color='azul')
        else:
            for i, eq in enumerate(ascendidos[:8]):
                yy = y_top + 80 + i * 40
                nombre = eq.get('nombre', '?') if isinstance(eq, dict) else getattr(eq, 'nombre', '?')
                ovr = eq.get('ovr', '?') if isinstance(eq, dict) else getattr(eq, 'ovr_promedio', '?')
                draw_text(screen, f"{i + 1}. {nombre[:26]}", (x_left + 30, yy), size='md', color='verde')
                draw_text(screen, f"OVR {ovr}", (x_left + col_w - 100, yy), size='sm', color='blanco')

        # Columna DESCENDIDOS
        draw_panel(screen, pygame.Rect(x_right, y_top, col_w, col_h))
        draw_text(screen, "⬇ DESCIENDEN A 2ª", (x_right + 20, y_top + 14), size='lg', color='rojo')
        pygame.draw.line(screen, COLORS.get('rojo', (255, 68, 68)),
                         (x_right + 20, y_top + 56), (x_right + col_w - 20, y_top + 56), 2)
        if not descendidos:
            draw_text(screen, "Sin descensos esta temporada.", (x_right + 30, y_top + 90),
                      size='sm', color='azul')
        else:
            for i, eq in enumerate(descendidos[:8]):
                yy = y_top + 80 + i * 40
                nombre = eq.get('nombre', '?') if isinstance(eq, dict) else getattr(eq, 'nombre', '?')
                ovr = eq.get('ovr', '?') if isinstance(eq, dict) else getattr(eq, 'ovr_promedio', '?')
                draw_text(screen, f"{i + 1}. {nombre[:26]}", (x_right + 30, yy), size='md', color='rojo')
                draw_text(screen, f"OVR {ovr}", (x_right + col_w - 100, yy), size='sm', color='blanco')

        # Boton CONTINUAR centrado abajo
        btn_w, btn_h = 360, 56
        btn_cont = pygame.Rect((SCREEN_W - btn_w) // 2, SCREEN_H - 80, btn_w, btn_h)
        cont_hover = btn_cont.collidepoint(mouse_pos)
        draw_button(screen, btn_cont, "CONTINUAR ▶", cont_hover)
        # Borde dorado cuando el boton tiene foco de teclado
        if cont_hover:
            pygame.draw.rect(screen, COLORS.get('dorado', (255, 215, 0)), btn_cont, width=3, border_radius=8)

        # Hint de teclado
        draw_text(screen, "[Enter / Space / Esc = continuar]", (SCREEN_W // 2 - 130, SCREEN_H - 22),
                  size='sm', color='azul')

        # v2.3.3: teclado
        try:
            for ev in key_events:
                if ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                    click_pos = (btn_cont.x + btn_cont.width // 2, btn_cont.y + btn_cont.height // 2)
                    break
        except Exception as e_kbd:
            logger.error(f"Error en teclado de promo_releg: {e_kbd}")

        if click_pos and btn_cont.collidepoint(click_pos):
            # Limpiar data para que no se re-muestre en otra ocasion
            estado.pop('promo_releg_data', None)
            return "resumen_temporada_screen"

        return None
    except Exception as e:
        logger.error(f"Error en promo_releg_screen: {e}")
        # Fallback defensivo: si algo explota, avanzamos al resumen
        estado.pop('promo_releg_data', None)
        return "resumen_temporada_screen"