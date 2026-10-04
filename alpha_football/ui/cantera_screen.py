# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Cantera (Pygame)
v4.8.0: juveniles del club aparte de la plantilla. Lista a la izquierda, ficha a la derecha;
SUBIR lo pasa al primer equipo con contrato y LIBERAR (con confirmación) lo saca de la cantera.
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

from alpha_football import cantera as K

logger = logging.getLogger(__name__)

R_LISTA = pygame.Rect(16, 110, 760, 586)       # termina en y=696 (barra de atajos)
R_FICHA = pygame.Rect(792, 110, 472, 470)
FILA_Y0, FILA_H = 148, 30
COLUMNAS = [("POS", 32), ("JUGADOR", 100), ("EDAD", 470), ("MED", 550), ("POT", 620), ("", 690)]


def _rects() -> dict:
    return {'volver': pygame.Rect(1116, 12, 148, 40),
            'subir': pygame.Rect(792, 596, 228, 48), 'liberar': pygame.Rect(1036, 596, 228, 48)}


def _rect_fila(i: int) -> pygame.Rect:
    return pygame.Rect(24, FILA_Y0 + i * FILA_H - 2, R_LISTA.width - 16, FILA_H - 2)


def ordenar(jugadores: list) -> list:
    """De mayor a menor media; a igual media, el de más potencial."""
    return sorted(jugadores, key=lambda j: (-j.overall, -int(getattr(j, 'potencial', 0) or 0), j.id))


def _salir(estado: dict) -> str:
    estado.pop('cantera_msg', None)
    estado.pop('cantera_confirma', None)
    return 'league_screen'


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """Retorna 'league_screen' al salir o None para seguir aquí."""
    try:
        jugadores = ordenar(K.cantera(estado))
        sel = int(estado.get('cantera_sel', 0) or 0)
        confirma = estado.get('cantera_confirma')
        rects = _rects()
        mouse_pos = pygame.mouse.get_pos()
        accion = None
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return 'menu'
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if rects['volver'].collidepoint(ev.pos):
                    return _salir(estado)
                if rects['subir'].collidepoint(ev.pos):
                    accion = 'subir'
                elif rects['liberar'].collidepoint(ev.pos):
                    accion = 'liberar'
                else:
                    for i in range(len(jugadores)):
                        if _rect_fila(i).collidepoint(ev.pos):
                            sel, confirma = i, None
            elif ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    if confirma is None:
                        return _salir(estado)
                    confirma = None
                    estado.pop('cantera_msg', None)
                elif ev.key == pygame.K_UP:
                    sel, confirma = sel - 1, None
                elif ev.key == pygame.K_DOWN:
                    sel, confirma = sel + 1, None
                elif ev.key == pygame.K_s:
                    accion = 'subir'
                elif ev.key == pygame.K_l or (ev.key == pygame.K_RETURN and confirma is not None):
                    accion = 'liberar'

        sel = max(0, min(sel, len(jugadores) - 1))
        if accion and jugadores:
            j = jugadores[sel]
            if accion == 'subir':
                _ok, estado['cantera_msg'] = K.subir(estado, j.id)
                confirma = None
            elif confirma == j.id:
                K.liberar(estado, j.id)
                estado['cantera_msg'] = f"{j.nombre_completo} deja la cantera."
                confirma = None
            else:
                confirma = j.id
                estado['cantera_msg'] = (f"¿Liberar a {j.nombre_completo}? Pulsa LIBERAR otra vez (o Enter) "
                                         "para confirmar · ESC cancela.")
            jugadores = ordenar(K.cantera(estado))
            sel = max(0, min(sel, len(jugadores) - 1))
        estado['cantera_sel'], estado['cantera_confirma'] = sel, confirma

        draw_gradient_bg(screen)
        draw_text(screen, "CANTERA", (16, 12), size='lg', color='dorado')
        draw_text(screen, f"{len(jugadores)} canteranos  ·  Próximo informe: {K.proximo_informe(estado)}",
                  (16, 58), size='sm', color='azul')
        if estado.get('cantera_msg'):
            draw_text(screen, str(estado['cantera_msg']), (16, 82), size='sm',
                      color='rojo' if confirma is not None else 'verde')
        draw_button(screen, rects['volver'], "VOLVER", rects['volver'].collidepoint(mouse_pos))

        draw_panel(screen, R_LISTA)
        for titulo, x in COLUMNAS:
            draw_text(screen, titulo, (x, R_LISTA.y + 10), size='sm', color='dorado')
        if not jugadores:
            draw_text(screen, "No hay canteranos. Llegarán en el próximo informe.", (32, FILA_Y0), size='md', color='blanco')
        for i, j in enumerate(jugadores):
            fila = _rect_fila(i)
            if i == sel:
                pygame.draw.rect(screen, (30, 45, 75), fila, border_radius=4)
            color = 'dorado' if getattr(j, 'joya', False) else 'blanco'
            valores = [j.posicion, j.nombre_completo[:34], str(j.edad), str(j.overall),
                       str(getattr(j, 'potencial', 0) or '?'), "JOYA" if getattr(j, 'joya', False) else ""]
            for (_t, x), v in zip(COLUMNAS, valores):
                draw_text(screen, v, (x, fila.y + 4), size='sm', color=color, shadow=False)

        if jugadores:
            from alpha_football.ui.ficha_jugador import dibujar_ficha
            dibujar_ficha(screen, R_FICHA, jugadores[sel], "Cantera")
            draw_button(screen, rects['subir'], "SUBIR (S)", rects['subir'].collidepoint(mouse_pos))
            draw_button(screen, rects['liberar'], "CONFIRMAR" if confirma is not None else "LIBERAR (L)",
                        rects['liberar'].collidepoint(mouse_pos) or confirma is not None)
        else:
            draw_panel(screen, R_FICHA)
        return None
    except Exception as e:
        logger.error(f"Error en cantera_screen: {e}", exc_info=True)
        return 'league_screen'
