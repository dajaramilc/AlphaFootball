# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Pantalla de Opciones (Fase 7).
Centraliza el control de volumen (ya no hay widget flotante global), el toggle de
música y el importador de música de YouTube (yt-dlp asíncrono). Persiste preferencias.
"""
from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)


def render(screen, estado: dict):
    """Pantalla de opciones. Retorna estado['options_return'] (def. 'menu') al salir, o None."""
    try:
        from alpha_football import audio
    except Exception:
        audio = None

    # Inicialización perezosa del campo de texto del importador
    estado.setdefault('opt_url', "")
    estado.setdefault('opt_input_activo', False)

    mouse_pos = pygame.mouse.get_pos()
    volumen = getattr(audio, 'CURRENT_VOLUME', estado.get('volumen', 0.5)) if audio else 0.5

    # --- Rects de la UI ---
    panel = pygame.Rect(SCREEN_W // 2 - 360, 90, 720, 540)
    rect_menos = pygame.Rect(panel.left + 60, 210, 60, 50)
    rect_mute = pygame.Rect(panel.left + 130, 210, 70, 50)
    rect_mas = pygame.Rect(panel.left + 210, 210, 60, 50)
    rect_input = pygame.Rect(panel.left + 60, 360, 500, 50)
    rect_descargar = pygame.Rect(panel.left + 575, 360, 90, 50)
    rect_volver = pygame.Rect(panel.left + 60, panel.bottom - 80, 200, 55)

    # --- Eventos ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.event.post(event)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            cp = event.pos
            estado['opt_input_activo'] = rect_input.collidepoint(cp)
            if audio and rect_menos.collidepoint(cp):
                audio.set_volume(max(0.0, volumen - 0.1)); _persistir(audio, estado)
            elif audio and rect_mas.collidepoint(cp):
                audio.set_volume(min(1.0, volumen + 0.1)); _persistir(audio, estado)
            elif audio and rect_mute.collidepoint(cp):
                if volumen > 0.0:
                    estado['last_non_zero_volume'] = volumen; audio.set_volume(0.0)
                else:
                    audio.set_volume(estado.get('last_non_zero_volume', 0.5))
                _persistir(audio, estado)
            elif rect_descargar.collidepoint(cp):
                if audio:
                    audio.descargar_url_async(estado['opt_url'])
                    estado['opt_url'] = ""
            elif rect_volver.collidepoint(cp):
                _persistir(audio, estado)
                return estado.get('options_return', 'menu')
        elif event.type == pygame.KEYDOWN and estado['opt_input_activo']:
            es_ctrl = bool(event.mod & pygame.KMOD_CTRL)
            if es_ctrl and event.key == pygame.K_v:
                # Pegar desde el portapapeles (Ctrl+V): es lo que pedía Diego, antes no existía.
                pegado = _leer_portapapeles()
                if pegado:
                    pegado = pegado.replace("\n", "").replace("\r", "").strip()
                    estado['opt_url'] = (estado['opt_url'] + pegado)[:200]
            elif event.key == pygame.K_BACKSPACE:
                estado['opt_url'] = estado['opt_url'][:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if audio:
                    audio.descargar_url_async(estado['opt_url']); estado['opt_url'] = ""
            elif event.unicode and event.unicode.isprintable() and len(estado['opt_url']) < 200:
                estado['opt_url'] += event.unicode

    # --- Dibujo ---
    draw_gradient_bg(screen)
    draw_panel(screen, panel)
    draw_text(screen, "OPCIONES", (panel.left + 40, 110), size='xl', color='dorado')

    # Volumen
    draw_text(screen, f"VOLUMEN: {int(volumen * 100)}%", (panel.left + 60, 175), size='md', color='blanco')
    draw_button(screen, rect_menos, "-", rect_menos.collidepoint(mouse_pos))
    draw_button(screen, rect_mute, "M", rect_mute.collidepoint(mouse_pos))
    draw_button(screen, rect_mas, "+", rect_mas.collidepoint(mouse_pos))
    # Barra de volumen
    barra = pygame.Rect(panel.left + 290, 225, 360, 16)
    pygame.draw.rect(screen, (40, 50, 75), barra, border_radius=4)
    relleno = pygame.Rect(barra.left, barra.top, int(barra.width * volumen), barra.height)
    pygame.draw.rect(screen, COLORS.get('verde', (0, 255, 136)), relleno, border_radius=4)
    draw_text(screen, "Atajos globales en el juego: + / - / M", (panel.left + 60, 280), size='sm', color='azul')

    # Importador de música
    draw_text(screen, "IMPORTAR MÚSICA (YouTube)", (panel.left + 60, 320), size='md', color='blanco')
    borde_input = COLORS.get('verde', (0, 255, 136)) if estado['opt_input_activo'] else COLORS.get('azul', (0, 191, 255))
    pygame.draw.rect(screen, (12, 18, 36), rect_input, border_radius=6)
    pygame.draw.rect(screen, borde_input, rect_input, width=2, border_radius=6)
    txt = estado['opt_url'] or "Pega aquí una URL de YouTube (Ctrl+V)…"
    txt_color = 'blanco' if estado['opt_url'] else 'azul'
    mostrado = txt[-46:] if len(txt) > 46 else txt
    draw_text(screen, mostrado, (rect_input.left + 10, rect_input.top + 14), size='sm', color=txt_color)
    draw_button(screen, rect_descargar, "BAJAR", rect_descargar.collidepoint(mouse_pos))

    # Estado de la descarga
    if audio:
        st = audio.estado_descarga()
        if st.get('mensaje'):
            color_msg = 'dorado' if st.get('activo') else ('verde' if 'Listo' in st['mensaje'] else 'blanco')
            draw_text(screen, st['mensaje'], (panel.left + 60, 425), size='sm', color=color_msg)

    draw_button(screen, rect_volver, "VOLVER", rect_volver.collidepoint(mouse_pos))
    return None


def _leer_portapapeles() -> str:
    """
    Lee el texto del portapapeles del sistema (para Ctrl+V). Resiliente:
    intenta primero Tkinter (fiable en Windows y en la stdlib) y cae a pygame.scrap.
    Devuelve "" si no se puede leer, sin romper la pantalla de opciones.
    """
    # Opción 1: Tkinter — disponible en la librería estándar y estable en Windows.
    try:
        import tkinter
        raiz = tkinter.Tk()
        raiz.withdraw()
        try:
            contenido = raiz.clipboard_get()
        finally:
            raiz.destroy()
        if contenido:
            return str(contenido)
    except Exception as e_tk:
        logger.debug(f"No se pudo leer el portapapeles vía Tkinter: {e_tk}")

    # Opción 2 (fallback): pygame.scrap, que puede no estar inicializado en todos los entornos.
    try:
        import pygame.scrap as scrap
        if not scrap.get_init():
            scrap.init()
        datos = scrap.get(pygame.SCRAP_TEXT)
        if datos:
            return datos.decode("utf-8", errors="ignore").replace("\x00", "")
    except Exception as e_scrap:
        logger.debug(f"No se pudo leer el portapapeles vía pygame.scrap: {e_scrap}")

    return ""


def _persistir(audio, estado: dict) -> None:
    """Guarda el volumen actual en preferencias (fail-soft)."""
    try:
        if audio:
            audio.guardar_preferencias({"volumen": getattr(audio, 'CURRENT_VOLUME', 0.5)})
    except Exception as e:
        logger.debug(f"No se pudo persistir preferencia de volumen: {e}")
