# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Conferencia de prensa (v0.4.23.0). Overlay modal sobre el prepartido (previa) y el postpartido.
No es una pantalla: no tiene destino ni se registra en main. Quien lo usa le entrega las teclas y el clic de su
cuadro (`manejar`, que los consume) y lo dibuja al final (`dibujar`). Teclado: 1-4 responder (cada pregunta
ofrece cuatro tonos de los ocho: motivador, provocador, humilde, agresivo, irónico, diplomático, elogioso y
"sin comentarios") · S o Esc saltar; tras responder, Enter / Espacio / Esc o CONTINUAR cierra.
La lógica (efectos, noticias, tensión) vive en `prensa.py`.
"""
from __future__ import annotations

import logging
from typing import Optional

import pygame

from alpha_football import prensa
from alpha_football.ui import noticias_visual as V

try:
    from alpha_football.ui.theme import SCREEN_W, SCREEN_H, COLORS, get_font, draw_panel, draw_button, draw_text
except Exception:
    SCREEN_W, SCREEN_H = 1280, 720
    COLORS = {}
    def get_font(size): return pygame.font.Font(None, 24)
    def draw_panel(screen, rect): pygame.draw.rect(screen, (20, 26, 46), rect)
    def draw_button(screen, rect, text, hover): return rect
    def draw_text(screen, text, pos, size='md', color='blanco', shadow=True): pass

logger = logging.getLogger(__name__)

R_PANEL = pygame.Rect(190, 120, 900, 480)
R_SALTAR = pygame.Rect(R_PANEL.right - 190, R_PANEL.bottom - 62, 170, 44)     # SALTAR, y CONTINUAR tras responder
_Y_RESPUESTAS = R_PANEL.y + 190
_X_TEXTO = 170                         # dónde empieza el texto de la respuesta dentro de su caja
_TECLAS_RESPUESTA = {pygame.K_1: 0, pygame.K_KP1: 0, pygame.K_2: 1, pygame.K_KP2: 1,
                     pygame.K_3: 2, pygame.K_KP3: 2, pygame.K_4: 3, pygame.K_KP4: 3}
_TECLAS_CERRAR = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_ESCAPE, pygame.K_BACKSPACE)
_ETIQUETA_TONO = {'motivador': "MOTIVADOR", 'provocador': "PROVOCADOR", 'humilde': "HUMILDE", 'agresivo': "AGRESIVO",
                  'ironico': "IRÓNICO", 'diplomatico': "DIPLOMÁTICO", 'elogioso': "ELOGIOSO", 'evasivo': "EVASIVO"}


def tonos_de(ov: dict) -> list:
    """Los tonos que ofrece esta pregunta (cuatro, en el orden del banco): los que encajan con el momento."""
    return [t for t in (ov.get('pregunta') or {}).get('respuestas', {}) if t in prensa.TONOS][:4]
_velo: Optional[pygame.Surface] = None


def rect_respuesta(i: int) -> pygame.Rect:
    return pygame.Rect(R_PANEL.x + 24, _Y_RESPUESTAS + i * 54, R_PANEL.w - 48, 48)


def activo(estado: dict, fase: Optional[str] = None) -> bool:
    """¿Hay una conferencia abierta (de esa fase, si se indica)?"""
    ov = estado.get('prensa_overlay')
    return bool(ov) and (fase is None or ov.get('fase') == fase)


def manejar(estado: dict, teclas: list, click_pos) -> None:
    """Modal: quien llama descarta sus propias teclas y su clic cuando el overlay está activo."""
    ov = estado.get('prensa_overlay')
    if not ov:
        return
    try:
        if ov.get('respuesta') is not None:               # ya respondió: ver las consecuencias y cerrar
            if any(k in _TECLAS_CERRAR for k in teclas or []) or (click_pos and R_SALTAR.collidepoint(click_pos)):
                prensa.saltar(estado)
            return
        for k in teclas or []:
            if k in _TECLAS_RESPUESTA:
                tonos = tonos_de(ov)
                if _TECLAS_RESPUESTA[k] < len(tonos):
                    prensa.responder(estado, ov, tonos[_TECLAS_RESPUESTA[k]])
                    return
            if k in (pygame.K_ESCAPE, pygame.K_s):
                prensa.saltar(estado)
                return
        if click_pos:
            if R_SALTAR.collidepoint(click_pos):
                prensa.saltar(estado)
                return
            for i, tono in enumerate(tonos_de(ov)):
                if rect_respuesta(i).collidepoint(click_pos):
                    prensa.responder(estado, ov, tono)
                    return
    except Exception as e:
        logger.error(f"Error al manejar la conferencia de prensa: {e}", exc_info=True)
        estado.pop('prensa_overlay', None)                # un overlay roto no debe dejar al usuario atrapado


def _velo_superficie() -> pygame.Surface:
    global _velo
    if _velo is None or _velo.get_size() != (SCREEN_W, SCREEN_H):
        _velo = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        _velo.fill((0, 0, 0, 170))
    return _velo


def _lineas(screen, texto: str, x: int, y: int, ancho: int, fuente: str, color: str, maximo: int, paso: int) -> int:
    """Dibuja `texto` envuelto en `ancho` (hasta `maximo` líneas) y devuelve la y siguiente."""
    for linea in V.envolver(texto, get_font(fuente), ancho, maximo):
        draw_text(screen, linea, (x, y), size=fuente, color=color, shadow=False)
        y += paso
    return y


def dibujar(screen, estado: dict, mouse_pos=(0, 0)) -> None:
    """La conferencia: pregunta y cuatro respuestas; tras responder, lo que dijiste y las consecuencias."""
    ov = estado.get('prensa_overlay')
    if not ov:
        return
    try:
        screen.blit(_velo_superficie(), (0, 0))
        draw_panel(screen, R_PANEL)
        x, ancho = R_PANEL.x + 24, R_PANEL.w - 48
        fase = "PREVIA" if ov.get('fase') == 'pre' else "POSTPARTIDO"
        draw_text(screen, f"CONFERENCIA DE PRENSA — {fase}", (x, R_PANEL.y + 14), size='lg', color='dorado')
        motivo = prensa.MOTIVO_TEXTO.get(ov.get('motivo'), "")
        contra = f"{motivo} · {ov.get('club', '')} vs {ov.get('rival', '')}"
        if ov.get('marcador'):
            contra += f" ({ov['marcador']})"
        draw_text(screen, contra, (x, R_PANEL.y + 52), size='sm', color='azul', shadow=False)
        if ov.get('declaracion') and ov.get('respuesta') is None:
            _lineas(screen, f"{ov.get('dt_rival', '')}: «{ov['declaracion']}»", x, R_PANEL.y + 78, ancho, 'sm',
                    'blanco', 2, 22)
        y = _lineas(screen, ov.get('pregunta', {}).get('texto', ""), x, R_PANEL.y + 124, ancho, 'md', 'blanco', 2, 28)
        resp = ov.get('respuesta')
        if resp is None:
            for i, tono in enumerate(tonos_de(ov)):
                r = rect_respuesta(i)
                draw_button(screen, r, "", r.collidepoint(mouse_pos))
                draw_text(screen, f"{i + 1} {_ETIQUETA_TONO[tono]}", (r.x + 12, r.centery - 10), size='sm',
                          color='dorado', shadow=False)
                _lineas(screen, ov['pregunta']['respuestas'][tono], r.x + _X_TEXTO, r.y + 5, r.w - _X_TEXTO - 12,
                        'sm', 'blanco', 2, 20)
            draw_button(screen, R_SALTAR, "SALTAR", R_SALTAR.collidepoint(mouse_pos))
            draw_text(screen, "1-4 Responder · S / Esc Saltar", (x, R_PANEL.bottom - 40), size='sm', color='azul',
                      shadow=False)
        else:
            draw_text(screen, f"Respondiste ({_ETIQUETA_TONO.get(resp.get('tono'), '')}):", (x, R_PANEL.y + 200),
                      size='sm', color='dorado', shadow=False)
            yy = _lineas(screen, f"«{resp.get('texto', '')}»", x, R_PANEL.y + 228, ancho, 'md', 'blanco', 3, 28)
            draw_text(screen, "Consecuencias:", (x, yy + 14), size='sm', color='dorado', shadow=False)
            yy += 40
            for efecto in resp.get('efectos') or ["Sin efectos."]:
                yy = _lineas(screen, f"• {efecto}", x + 8, yy, ancho - 8, 'sm', 'verde', 2, 22)
            draw_button(screen, R_SALTAR, "CONTINUAR", R_SALTAR.collidepoint(mouse_pos))
    except Exception as e:
        logger.error(f"Error al dibujar la conferencia de prensa: {e}", exc_info=True)
