# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Historial de pases (Pygame)
v2.7.0: GENERAL (todos los pases de las 10 ligas, incluidos los tuyos) y PROPIO (tus
compras y ventas), del más reciente al más viejo, con scroll.
v4.4.0: clic en el título de una columna ordena por ella (otro clic invierte el orden).
"""
from __future__ import annotations

import logging
from typing import Optional
import pygame

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

from alpha_football import negociacion as N

logger = logging.getLogger(__name__)

R_LISTA = pygame.Rect(16, 110, 1248, 586)      # v3.6.0: termina en y=696 (barra de atajos)
FILA_Y0, FILA_H = 148, 26
FILAS_VISIBLES = (R_LISTA.bottom - 6 - FILA_Y0) // FILA_H
COLUMNAS = [("CUÁNDO", 32), ("JUGADOR", 130), ("POS", 400), ("MED", 450), ("DE", 510),
            ("A", 790), ("MONTO", 1080)]
CLAVES = ['cuando', 'jugador', 'posicion', 'media', 'de', 'a', 'monto']   # v4.4.0: campo de cada columna
NUMERICAS = ('cuando', 'media', 'monto')


def _rect_columna(i: int) -> pygame.Rect:
    x = COLUMNAS[i][1]
    fin = COLUMNAS[i + 1][1] - 8 if i + 1 < len(COLUMNAS) else R_LISTA.right - 8
    return pygame.Rect(x - 4, R_LISTA.y + 4, fin - x, 30)


def ordenar(pases: list, clave: str, desc: bool) -> list:
    """v4.4.0: `pases` viene del más reciente al más viejo (N.historial); estable ante empates."""
    if clave == 'cuando':
        return list(pases) if desc else list(reversed(pases))
    if clave in NUMERICAS:
        return sorted(pases, key=lambda h: int(h.get(clave, 0) or 0), reverse=desc)
    return sorted(pases, key=lambda h: str(h.get(clave, '') or '').lower(), reverse=desc)


def _rects() -> dict:
    return {'general': pygame.Rect(16, 60, 200, 40), 'propio': pygame.Rect(226, 60, 200, 40),
            'volver': pygame.Rect(1116, 12, 148, 40)}


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """Retorna 'league_screen' al salir o None para seguir aquí."""
    try:
        tab = estado.get('hist_pases_tab') if estado.get('hist_pases_tab') in ('general', 'propio') else 'general'
        orden_col, orden_desc = estado.get('hist_pases_orden') or ('cuando', True)
        scroll = int(estado.get('hist_pases_scroll', 0) or 0)
        rects = _rects()
        mouse_pos = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return 'menu'
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if ev.button == 1:
                    if rects['volver'].collidepoint(ev.pos):
                        return 'league_screen'
                    for t in ('general', 'propio'):
                        if rects[t].collidepoint(ev.pos) and t != tab:
                            tab, scroll = t, 0
                    for i, k in enumerate(CLAVES):      # v4.4.0: ordenar por columna
                        if _rect_columna(i).collidepoint(ev.pos):
                            orden_desc = (not orden_desc) if k == orden_col else (k in NUMERICAS)
                            orden_col, scroll = k, 0
                elif ev.button in (4, 5):
                    scroll += -3 if ev.button == 4 else 3
            elif ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    return 'league_screen'
                if ev.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB):
                    tab, scroll = ('propio' if tab == 'general' else 'general'), 0
                elif ev.key == pygame.K_UP:
                    scroll -= 1
                elif ev.key == pygame.K_DOWN:
                    scroll += 1
                elif ev.key == pygame.K_PAGEUP:
                    scroll -= FILAS_VISIBLES
                elif ev.key == pygame.K_PAGEDOWN:
                    scroll += FILAS_VISIBLES

        pases = ordenar(N.historial(estado, propio=True if tab == 'propio' else None), orden_col, orden_desc)
        scroll = max(0, min(scroll, max(0, len(pases) - FILAS_VISIBLES)))
        estado['hist_pases_tab'], estado['hist_pases_scroll'] = tab, scroll
        estado['hist_pases_orden'] = (orden_col, orden_desc)

        draw_gradient_bg(screen)
        draw_text(screen, "HISTORIAL DE PASES", (16, 12), size='lg', color='dorado')
        for t, nombre in (('general', "GENERAL"), ('propio', "PROPIO")):
            draw_button(screen, rects[t], nombre, rects[t].collidepoint(mouse_pos) or t == tab)
            if t == tab:
                pygame.draw.rect(screen, COLORS['dorado'], rects[t], width=2, border_radius=8)
        draw_text(screen, f"{len(pases)} pases  ·  rueda / ↑↓ desplaza  ·  ←→ pestaña  ·  clic en columna ordena",
                  (446, 70), size='sm', color='azul')
        draw_button(screen, rects['volver'], "VOLVER", rects['volver'].collidepoint(mouse_pos))

        draw_panel(screen, R_LISTA)
        for i, (titulo, x) in enumerate(COLUMNAS):
            activa = CLAVES[i] == orden_col
            if _rect_columna(i).collidepoint(mouse_pos) or activa:
                pygame.draw.rect(screen, (30, 45, 75), _rect_columna(i), border_radius=4)
            draw_text(screen, titulo + ((" ↓" if orden_desc else " ↑") if activa else ""),
                      (x, R_LISTA.y + 10), size='sm', color='verde' if activa else 'dorado')
        mi_nombre = getattr(estado.get('mi_equipo'), 'nombre', '')
        if not pases:
            draw_text(screen, "Todavía no hay pases registrados.", (32, FILA_Y0), size='md', color='blanco')
        for i, h in enumerate(pases[scroll:scroll + FILAS_VISIBLES]):
            y = FILA_Y0 + i * FILA_H
            if h.get('propio'):
                pygame.draw.rect(screen, (30, 45, 75), pygame.Rect(24, y - 2, R_LISTA.width - 16, FILA_H - 2), border_radius=4)
            color = 'verde' if h.get('a') == mi_nombre else ('rojo' if h.get('de') == mi_nombre else 'blanco')
            m = int(h.get('monto', 0) or 0)
            valores = [f"T{h.get('temporada', '?')} J{h.get('jornada', '?')}", str(h.get('jugador', ''))[:30],
                       h.get('posicion', ''), str(h.get('media', '')), str(h.get('de', ''))[:30],
                       str(h.get('a', ''))[:30], f"${m / 1_000_000:.1f}M" if m >= 1_000_000 else f"${m / 1000:.0f}K"]
            for (_t, x), v in zip(COLUMNAS, valores):
                draw_text(screen, v, (x, y), size='sm', color=color, shadow=False)
        return None
    except Exception as e:
        logger.error(f"Error en historial_pases_screen: {e}", exc_info=True)
        return 'league_screen'
