# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Pantalla de carga (guardar, cargar, pasar de temporada, iniciar carrera).
Sin hilos: cada `mostrar` dibuja sobre la pantalla actual, hace flip() y event.pump() para que
Windows no marque la ventana como "no responde". `cerrar` respeta un mínimo visible (0.4 s) para
que no sea un parpadeo. Si algo falla, solo se loggea: el proceso de fondo nunca se corta.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Optional

import pygame

logger = logging.getLogger(__name__)

# en los tests (SDL dummy) no se espera; el juego real siempre corre con video
MINIMO = 0.0 if os.environ.get('SDL_VIDEODRIVER') == 'dummy' else 0.4
R_BARRA = pygame.Rect(340, 400, 600, 22)
COLOR_BARRA = (0, 255, 136)
_inicio: Optional[float] = None


def _dibujar(screen, titulo: str, paso: str, avance: Optional[float]) -> None:
    from alpha_football.ui.theme import draw_gradient_bg, draw_text, get_font, COLORS
    draw_gradient_bg(screen)
    w = screen.get_width()
    for txt, y, size, color in ((titulo, 300, 'lg', 'dorado'), (paso, 350, 'md', 'blanco')):
        if txt:
            draw_text(screen, txt, ((w - get_font(size).size(txt)[0]) // 2, y), size=size, color=color)
    if avance is not None:
        pygame.draw.rect(screen, (24, 32, 54), R_BARRA, border_radius=6)
        lleno = R_BARRA.copy()
        lleno.width = int(R_BARRA.width * max(0.0, min(1.0, float(avance))))
        if lleno.width > 0:
            pygame.draw.rect(screen, COLOR_BARRA, lleno, border_radius=6)
        pygame.draw.rect(screen, COLORS['azul'], R_BARRA, width=1, border_radius=6)


def mostrar(titulo: str, paso: str = "", avance: Optional[float] = None) -> None:
    """Dibuja la pantalla de carga (avance 0..1 = barra; None = sin barra) y la muestra ya."""
    global _inicio
    try:
        screen = pygame.display.get_surface()
        if screen is None:
            return
        if _inicio is None:
            _inicio = time.monotonic()
        _dibujar(screen, titulo, paso, avance)
        pygame.display.flip()
        pygame.event.pump()
    except Exception as e:
        logger.error(f"No se pudo mostrar la pantalla de carga '{titulo}': {e}")


def cerrar() -> None:
    """Fin del proceso: espera lo que falte para el mínimo visible (sin congelar la ventana)."""
    global _inicio
    try:
        if _inicio is None:
            return
        resto = MINIMO - (time.monotonic() - _inicio)
        while resto > 0:
            pygame.event.pump()
            time.sleep(min(0.05, resto))
            resto = MINIMO - (time.monotonic() - _inicio)
    except Exception as e:
        logger.error(f"Error cerrando la pantalla de carga: {e}")
    finally:
        _inicio = None
        try:    # lo pulsado durante la carga no se ejecuta en la pantalla siguiente (QUIT se conserva)
            pygame.event.clear((pygame.KEYDOWN, pygame.KEYUP, pygame.MOUSEBUTTONDOWN,
                                pygame.MOUSEBUTTONUP, pygame.MOUSEWHEEL))
        except Exception as e:
            logger.error(f"No se pudo descartar la entrada acumulada: {e}")
