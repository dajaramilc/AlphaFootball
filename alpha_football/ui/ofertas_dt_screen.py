# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Ofertas de banquillo (Pygame)
v3.4.0: clubes que echaron a su DT y te quieren. ACEPTAR = cambio inmediato + contrato;
RECHAZAR = contratan a otro. Las ofertas duran 3 jornadas.
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

from alpha_football import entrenadores as EN

logger = logging.getLogger(__name__)

R_VOLVER = pygame.Rect(SCREEN_W - 216, 12, 200, 44)


def _fila(i: int) -> pygame.Rect:
    return pygame.Rect(16, 110 + i * 130, SCREEN_W - 32, 116)


def rect_aceptar(i: int) -> pygame.Rect:
    r = _fila(i); return pygame.Rect(r.right - 440, r.y + 34, 200, 48)


def rect_rechazar(i: int) -> pygame.Rect:
    r = _fila(i); return pygame.Rect(r.right - 220, r.y + 34, 200, 48)


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """Lista de ofertas (máx. 4) con ACEPTAR / RECHAZAR."""
    try:
        ofertas = EN.ofertas_activas(estado)[:4]
        mouse_pos = pygame.mouse.get_pos()
        from alpha_football.ui.foco import traducir_eventos, marcar   # v4.2.0: teclado
        rects_foco = [r for i in range(len(ofertas)) for r in (rect_aceptar(i), rect_rechazar(i))] + [R_VOLVER]
        foco, eventos = traducir_eventos(estado, 'foco_ofertas_dt', rects_foco, list(pygame.event.get()), columnas=2)
        for ev in eventos:
            if ev.type == pygame.QUIT:
                return 'menu'
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                return 'league_screen'
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if R_VOLVER.collidepoint(ev.pos):
                    return 'league_screen'
                for i, o in enumerate(ofertas):
                    if rect_aceptar(i).collidepoint(ev.pos) and EN.aceptar_oferta(estado, o['club_id']) is not None:
                        estado['contrato_modo'] = 'alta'
                        return 'contrato_dt_screen'
                    if rect_rechazar(i).collidepoint(ev.pos):
                        EN.rechazar_oferta(estado, o['club_id'])
                        return None
        draw_gradient_bg(screen)
        draw_text(screen, "OFERTAS DE BANQUILLO", (16, 16), size='xl', color='dorado')
        draw_button(screen, R_VOLVER, "VOLVER", R_VOLVER.collidepoint(mouse_pos))
        if not ofertas:
            draw_text(screen, "Ningún club te busca por ahora. Cuando un club que va mal eche a su DT",
                      (16, 120), size='md', color='blanco')
            draw_text(screen, "y tu calificación alcance, te escribirán.", (16, 150), size='md', color='blanco')
        for i, o in enumerate(ofertas):
            r = _fila(i); draw_panel(screen, r)
            eq, liga = EN._club_por_id(estado, o['club_id'])
            draw_text(screen, o['club'][:26], (r.x + 20, r.y + 14), size='lg', color='dorado')
            if eq is not None:
                draw_text(screen, f"{o['liga'][:28]}  ·  MEDIA {eq.ovr_promedio}  ·  va {EN.posicion(liga, eq)}º",
                          (r.x + 20, r.y + 60), size='sm', color='azul')
            draw_text(screen, f"Vence en {o['jornadas']} jornada{'s' if o['jornadas'] != 1 else ''}",
                      (r.x + 20, r.y + 86), size='sm', color='rojo')
            draw_button(screen, rect_aceptar(i), "ACEPTAR", rect_aceptar(i).collidepoint(mouse_pos))
            draw_button(screen, rect_rechazar(i), "RECHAZAR", rect_rechazar(i).collidepoint(mouse_pos))
        marcar(screen, rects_foco[foco])
        return None
    except Exception as e:
        logger.error(f"Error en ofertas_dt_screen: {e}", exc_info=True)
        return 'league_screen'
