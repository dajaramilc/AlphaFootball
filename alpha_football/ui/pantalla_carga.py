# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Pantalla de carga (guardar, cargar, pasar de temporada, iniciar carrera).
Sin hilos: cada `mostrar` dibuja sobre la pantalla actual, hace flip() y event.pump() para que
Windows no marque la ventana como "no responde". `cerrar` respeta un mínimo visible (0.4 s) para
que no sea un parpadeo. Si algo falla, solo se loggea: el proceso de fondo nunca se corta.
v0.4.23.0: al pasar de temporada pueden desfilar titulares de noticias a la derecha (`fijar_titulares`); como los
pasos largos bloquean sin redibujar, el desfile se anima de verdad en la espera final de `cerrar(minimo=...)`.
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

# v0.4.23.0: titulares que desfilan (una tarjeta 9:16 a la derecha, fuera del título y de la barra, que ocupan 340-940)
R_TITULARES = pygame.Rect(980, 160, 225, 400)
SEGUNDOS_POR_TITULAR = 3.5
SEGUNDOS_FUNDIDO = 0.4
MAX_TITULARES = 10
_titulares: list = []
_t_titulares: Optional[float] = None
_ultimo: Optional[tuple] = None        # (titulo, paso, avance) del último cuadro, para redibujar mientras espera


def _minimo_temporada(real: bool) -> float:
    """Mínimo visible de la carga de temporada: 3 s en el juego real (se leen los titulares), 0 en los tests."""
    return 3.0 if real else 0.0


MINIMO_TEMPORADA = _minimo_temporada(os.environ.get('SDL_VIDEODRIVER') != 'dummy')


def fijar_titulares(noticias) -> None:
    """Las noticias (dicts de `noticias.py`) que desfilan durante la carga; None o [] las quita."""
    global _titulares, _t_titulares
    _titulares = [n for n in (noticias or []) if isinstance(n, dict)][:MAX_TITULARES]
    _t_titulares = time.monotonic() if _titulares else None


def titular_vigente(n: int, transcurrido: float) -> tuple:
    """(índice de la noticia que toca, alfa 0-255) a los `transcurrido` segundos: cada una dura
    SEGUNDOS_POR_TITULAR, entra y sale con un fundido de SEGUNDOS_FUNDIDO."""
    if n <= 0:
        return 0, 0
    t = max(0.0, float(transcurrido))
    fase = t % SEGUNDOS_POR_TITULAR
    k = min(1.0, fase / SEGUNDOS_FUNDIDO, (SEGUNDOS_POR_TITULAR - fase) / SEGUNDOS_FUNDIDO)
    return int(t // SEGUNDOS_POR_TITULAR) % n, max(0, min(255, int(255 * k)))


def _dibujar_titulares(screen, transcurrido: Optional[float] = None) -> None:
    """La noticia que toca, en una tarjeta con fundido (superficie cacheada de noticias_visual)."""
    if not _titulares:
        return
    try:
        from alpha_football.ui import noticias_visual as V
        from alpha_football.ui.theme import draw_text
        if transcurrido is None:
            transcurrido = time.monotonic() - (_t_titulares if _t_titulares is not None else time.monotonic())
        i, alfa = titular_vigente(len(_titulares), transcurrido)
        draw_text(screen, "ÚLTIMAS NOTICIAS", (R_TITULARES.x, R_TITULARES.y - 34), size='sm', color='dorado')
        tarjeta = V.tarjeta(_titulares[i], R_TITULARES.width, R_TITULARES.height)
        tarjeta.set_alpha(alfa)
        screen.blit(tarjeta, R_TITULARES.topleft)
        tarjeta.set_alpha(None)
    except Exception as e:
        logger.error(f"No se pudo dibujar el titular de la carga: {e}")


def _dibujar(screen, titulo: str, paso: str, avance: Optional[float], transcurrido: Optional[float] = None) -> None:
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
    _dibujar_titulares(screen, transcurrido)


def mostrar(titulo: str, paso: str = "", avance: Optional[float] = None) -> None:
    """Dibuja la pantalla de carga (avance 0..1 = barra; None = sin barra) y la muestra ya."""
    global _inicio, _ultimo
    try:
        screen = pygame.display.get_surface()
        if screen is None:
            return
        if _inicio is None:
            _inicio = time.monotonic()
        _ultimo = (titulo, paso, avance)
        _dibujar(screen, titulo, paso, avance)
        pygame.display.flip()
        pygame.event.pump()
    except Exception as e:
        logger.error(f"No se pudo mostrar la pantalla de carga '{titulo}': {e}")


def _redibujar() -> None:
    """Vuelve a dibujar el último cuadro (con los titulares avanzados) mientras `cerrar` espera."""
    screen = pygame.display.get_surface()
    if screen is not None and _ultimo is not None:
        _dibujar(screen, *_ultimo)
        pygame.display.flip()


def cerrar(minimo: Optional[float] = None) -> None:
    """Fin del proceso: espera lo que falte para el mínimo visible (`minimo` en segundos; sin él, MINIMO) sin
    congelar la ventana: redibuja ~30 veces por segundo, que es lo que anima los titulares."""
    global _inicio, _ultimo
    try:
        if _inicio is None:
            return
        espera = MINIMO if minimo is None else float(minimo)
        resto = espera - (time.monotonic() - _inicio)
        while resto > 0:
            try:
                _redibujar()
            except Exception as e_dib:
                logger.error(f"No se pudo redibujar la pantalla de carga: {e_dib}")
            pygame.event.pump()
            time.sleep(min(0.033, resto))
            resto = espera - (time.monotonic() - _inicio)
    except Exception as e:
        logger.error(f"Error cerrando la pantalla de carga: {e}")
    finally:
        _inicio = None
        _ultimo = None
        try:    # lo pulsado durante la carga no se ejecuta en la pantalla siguiente (QUIT se conserva)
            pygame.event.clear((pygame.KEYDOWN, pygame.KEYUP, pygame.MOUSEBUTTONDOWN,
                                pygame.MOUSEBUTTONUP, pygame.MOUSEWHEEL))
        except Exception as e:
            logger.error(f"No se pudo descartar la entrada acumulada: {e}")
