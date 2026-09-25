# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — FOCO DE TECLADO COMPARTIDO (v4.2.0)
Para que cada pantalla se use sin mouse: las flechas (y Tab) mueven un foco sobre una lista de
botones y Enter/Espacio hace un clic en el botón con foco. Las pantallas que ya procesan clics
con su propio bucle de eventos usan `traducir_eventos`: devuelve los eventos con Enter cambiado por
un clic sintético, así su lógica de clic no cambia.
"""
from __future__ import annotations

import logging
from typing import Optional

import pygame

logger = logging.getLogger(__name__)

TECLAS_OK = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)


def mover_foco(estado: dict, clave: str, n: int, key_events: list, columnas: int = 1) -> tuple:
    """Mueve estado[clave] con flechas/Tab. Devuelve (foco, pulsó_enter, pulsó_esc)."""
    if n <= 0:
        return 0, False, any(ev.key == pygame.K_ESCAPE for ev in key_events)
    foco = int(estado.get(clave, 0) or 0) % n
    enter = esc = False
    for ev in key_events:
        if ev.key in (pygame.K_RIGHT, pygame.K_TAB) or (ev.key == pygame.K_DOWN and columnas == 1):
            foco = (foco + 1) % n
        elif ev.key == pygame.K_LEFT or (ev.key == pygame.K_UP and columnas == 1):
            foco = (foco - 1) % n
        elif ev.key == pygame.K_DOWN:
            foco = min(n - 1, foco + columnas)
        elif ev.key == pygame.K_UP:
            foco = max(0, foco - columnas)
        elif ev.key in TECLAS_OK:
            enter = True
        elif ev.key == pygame.K_ESCAPE:
            esc = True
    estado[clave] = foco
    return foco, enter, esc


def teclado_a_clic(estado: dict, clave: str, rects: list, key_events: list, columnas: int = 1,
                   esc_rect=None) -> tuple:
    """Foco sobre `rects`; Enter = clic virtual en el botón con foco, ESC = clic en `esc_rect`.
    Devuelve (foco, posición del clic o None)."""
    foco, enter, esc = mover_foco(estado, clave, len(rects), key_events, columnas)
    if enter and rects:
        return foco, rects[foco].center
    if esc and esc_rect is not None:
        return foco, esc_rect.center
    return foco, None


def traducir_eventos(estado: dict, clave: str, rects: list, eventos: list, columnas: int = 1,
                     esc_rect=None) -> tuple:
    """
    Para pantallas con su propio bucle de eventos: consume flechas/Tab/Enter (y ESC si hay
    `esc_rect`) y devuelve (foco, eventos) con Enter reemplazado por un clic en el botón con foco.
    Sin botones, Enter hace clic en el centro de la pantalla ("clic para seguir").
    """
    try:
        navegacion = (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB) + TECLAS_OK
        teclas = [ev for ev in eventos if ev.type == pygame.KEYDOWN and (
            ev.key in navegacion or (ev.key == pygame.K_ESCAPE and esc_rect is not None))]
        foco, pos = teclado_a_clic(estado, clave, rects, teclas, columnas, esc_rect)
        if pos is None and not rects and any(ev.key in TECLAS_OK for ev in teclas):
            pos = pygame.display.get_surface().get_rect().center if pygame.display.get_surface() else (640, 360)
        salida = [ev for ev in eventos if ev not in teclas]
        if pos is not None:
            salida.append(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))
        return foco, salida
    except Exception as e:
        logger.error(f"No se pudo traducir el teclado a clic en {clave}: {e}")
        return 0, eventos


def marcar(screen, rect, color=(255, 215, 0)) -> None:
    """Marco del botón con foco de teclado."""
    try:
        pygame.draw.rect(screen, color, rect.inflate(6, 6), width=2, border_radius=8)
    except Exception:
        pass
