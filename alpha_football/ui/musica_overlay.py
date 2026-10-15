# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Aviso de música no instalada (v0.4.24.0). Overlay modal que main.py abre al iniciar cuando
la carpeta de música no tiene ninguna pista reproducible, y que explica cómo conseguirla: OPCIONES > IMPORTAR
MÚSICA o copiar archivos a la carpeta `music`. No es una pantalla: main le entrega los eventos
(`manejar_evento`, que consume teclas y clics) y lo dibuja al final del frame (`dibujar`).
Teclado: Enter / Espacio / Esc cierran. Se cierra solo si aparece música (p. ej. la descarga automática).
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from typing import Optional

import pygame

from alpha_football import audio
from alpha_football.ui import noticias_visual as V

try:
    from alpha_football.ui.theme import SCREEN_W, SCREEN_H, get_font, draw_panel, draw_button, draw_text
except Exception:
    SCREEN_W, SCREEN_H = 1280, 720
    def get_font(size): return pygame.font.Font(None, 24)
    def draw_panel(screen, rect): pygame.draw.rect(screen, (20, 26, 46), rect)
    def draw_button(screen, rect, text, hover): return rect
    def draw_text(screen, text, pos, size='md', color='blanco', shadow=True): pass

logger = logging.getLogger(__name__)

R_PANEL = pygame.Rect(200, 140, 880, 440)
_Y_BOTONES = R_PANEL.bottom - 72
R_OPCIONES = pygame.Rect(R_PANEL.x + 24, _Y_BOTONES, 260, 48)
R_CARPETA = pygame.Rect(R_PANEL.x + 24 + 280, _Y_BOTONES, 260, 48)
R_CERRAR = pygame.Rect(R_PANEL.x + 24 + 560, _Y_BOTONES, 260, 48)
_TECLAS_CERRAR = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_ESCAPE)
_EVENTOS_ENTRADA = (pygame.KEYUP, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION, pygame.MOUSEWHEEL, pygame.TEXTINPUT)
_REVISAR_CADA_MS = 1000

_velo: Optional[pygame.Surface] = None
_ultima_revision = 0


def activo(estado: dict) -> bool:
    return bool(estado.get('aviso_musica'))


def preparar(estado: dict) -> None:
    """Llamar tras `audio.init_audio()`: deja el aviso abierto si no hay música reproducible."""
    try:
        if not audio.hay_musica():
            estado['aviso_musica'] = True
    except Exception as e:
        logger.error(f"No se pudo comprobar si hay música: {e}")


def revisar(estado: dict) -> None:
    """Cierra el aviso si ya hay música (la descarga automática o el usuario la dejó en la carpeta)."""
    if activo(estado) and audio.hay_musica():
        estado.pop('aviso_musica', None)


def _cerrar(estado: dict) -> None:
    estado.pop('aviso_musica', None)


def _abrir_carpeta(ruta: str) -> None:
    """Abre la carpeta de música en el explorador (la crea si no existe)."""
    try:
        os.makedirs(ruta, exist_ok=True)
        if hasattr(os, 'startfile'):
            os.startfile(ruta)
        else:
            subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', ruta])
    except Exception as e:
        logger.warning(f"No se pudo abrir la carpeta de música {ruta}: {e}")


def manejar_evento(estado: dict, ev) -> bool:
    """True si el aviso consume el evento (main no lo pasa a la pantalla). Abierto consume teclas y ratón;
    QUIT y los eventos de audio (fin de pista) siguen su camino."""
    if not activo(estado):
        return False
    try:
        tipo = getattr(ev, 'type', None)
        if tipo == pygame.KEYDOWN:
            if ev.key in _TECLAS_CERRAR:
                _cerrar(estado)
            return True
        if tipo == pygame.MOUSEBUTTONDOWN:
            if ev.button == 1:
                if R_CERRAR.collidepoint(ev.pos):
                    _cerrar(estado)
                elif R_OPCIONES.collidepoint(ev.pos):
                    estado['options_return'] = estado.get('current_screen', 'menu')
                    estado['current_screen'] = 'options_screen'
                    _cerrar(estado)
                elif R_CARPETA.collidepoint(ev.pos):
                    _abrir_carpeta(audio.MUSIC_DIR)
            return True
        return tipo in _EVENTOS_ENTRADA
    except Exception as e:
        logger.error(f"Error en el aviso de música: {e}")
        return True


def _velo_superficie() -> pygame.Surface:
    global _velo
    if _velo is None or _velo.get_size() != (SCREEN_W, SCREEN_H):
        _velo = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        _velo.fill((0, 0, 0, 170))
    return _velo


def _lineas(screen, texto: str, x: int, y: int, ancho: int, fuente: str, color: str, maximo: int, paso: int) -> int:
    for linea in V.envolver(texto, get_font(fuente), ancho, maximo):
        draw_text(screen, linea, (x, y), size=fuente, color=color, shadow=False)
        y += paso
    return y


def dibujar(screen, estado: dict, mouse_pos: Optional[tuple] = None) -> None:
    global _ultima_revision
    if not activo(estado):
        return
    try:
        ahora = pygame.time.get_ticks()
        if ahora - _ultima_revision >= _REVISAR_CADA_MS:
            _ultima_revision = ahora
            revisar(estado)
            if not activo(estado):
                return
        mouse_pos = mouse_pos or pygame.mouse.get_pos()
        screen.blit(_velo_superficie(), (0, 0))
        draw_panel(screen, R_PANEL)
        x, ancho = R_PANEL.x + 28, R_PANEL.w - 56
        draw_text(screen, "NO HAY MÚSICA INSTALADA", (x, R_PANEL.y + 20), size='xl', color='dorado')
        y = _lineas(screen, "El juego no encontró canciones en su carpeta de música y va a sonar en silencio. "
                            "Para tener música:", x, R_PANEL.y + 78, ancho, 'md', 'blanco', 2, 30)
        y = _lineas(screen, "1. Entra a OPCIONES → IMPORTAR MÚSICA, pega la URL de un video de YouTube (o escribe "
                            "el nombre de la canción) y pulsa BAJAR o BUSCAR.", x, y + 16, ancho, 'sm', 'blanco', 3, 24)
        y = _lineas(screen, "2. O copia tus propios archivos .mp3, .wav, .ogg o .m4a a esta carpeta:",
                    x, y + 12, ancho, 'sm', 'blanco', 2, 24)
        y = _lineas(screen, audio.MUSIC_DIR, x + 16, y + 4, ancho - 16, 'sm', 'azul', 2, 24)
        _lineas(screen, "El juego también intenta bajar una lista inicial por su cuenta cuando hay internet. "
                        "Este aviso se cierra solo en cuanto aparezca música.",
                x, y + 16, ancho, 'sm', 'verde', 3, 24)
        draw_button(screen, R_OPCIONES, "ABRIR OPCIONES", R_OPCIONES.collidepoint(mouse_pos))
        draw_button(screen, R_CARPETA, "ABRIR CARPETA", R_CARPETA.collidepoint(mouse_pos))
        draw_button(screen, R_CERRAR, "ENTENDIDO", R_CERRAR.collidepoint(mouse_pos))
    except Exception as e:
        logger.error(f"Error al dibujar el aviso de música: {e}", exc_info=True)
