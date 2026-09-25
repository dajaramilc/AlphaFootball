# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Veredicto de fin de temporada (Pygame)
v3.2.0: paso 1 = el correo de rendimiento abierto; Enter → paso 2 = veredicto a pantalla completa
(felicitación / cumplida / regaño / despido / fin de contrato); Enter → despido, ascensos o hub.
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

from alpha_football import correo as C

logger = logging.getLogger(__name__)

VEREDICTOS = {'felicitacion': ("¡FELICITACIONES!", 'dorado'), 'neutro': ("TEMPORADA CUMPLIDA", 'azul'),
              'regano': ("LA DIRECTIVA NO ESTÁ CONFORME", 'rojo'), 'despido': ("¡DESPEDIDO!", 'rojo'),
              'fin_contrato': ("FIN DE CONTRATO", 'blanco')}


R_CORREO = pygame.Rect(16, 80, SCREEN_W - 32, 540)     # v3.9.0: expuesto (ayuda H)


def _siguiente(estado: dict) -> str:
    estado.pop('veredicto_pendiente', None)
    estado.pop('veredicto_paso', None)
    if estado.get('despido_pendiente'):
        return 'despido_screen'
    if estado.get('promo_releg_data'):
        return 'promo_releg_screen'
    return 'league_screen'


def _envolver(texto: str, ancho: int = 92) -> list:
    lineas, linea = [], ""
    for p in texto.split():
        if len(linea) + len(p) + 1 > ancho:
            lineas.append(linea)
            linea = p
        else:
            linea = (linea + " " + p).strip()
    return lineas + ([linea] if linea else [])


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    try:
        vp = estado.get('veredicto_pendiente')
        if not vp:
            return _siguiente(estado)
        paso = int(estado.get('veredicto_paso', 0) or 0)
        msg = next((m for m in C.bandeja(estado) if m.get('id') == vp.get('correo_id')), None)
        avanzar = False
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return 'menu'
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                avanzar = True
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                avanzar = True
        if avanzar:
            if paso == 0:
                if msg:
                    C.marcar_leido(estado, msg['id'])
                estado['veredicto_paso'] = 1
                return None
            return _siguiente(estado)

        draw_gradient_bg(screen)
        info = vp.get('info') or {}
        if paso == 0:
            draw_text(screen, "CORREO NUEVO", (16, 16), size='lg', color='azul')
            r = R_CORREO
            draw_panel(screen, r)
            draw_text(screen, "De: Directiva", (r.x + 24, r.y + 20), size='sm', color='azul')
            draw_text(screen, (msg or {}).get('asunto', 'Evaluación de la temporada'), (r.x + 24, r.y + 50),
                      size='lg', color='dorado')
            for i, linea in enumerate(_envolver((msg or {}).get('cuerpo', ''))):
                draw_text(screen, linea, (r.x + 24, r.y + 110 + i * 32), size='md', color='blanco')
            draw_text(screen, "Enter para continuar", (16, 660), size='md', color='verde')
            return None
        titulo, color = VEREDICTOS.get(vp.get('tipo'), ("TEMPORADA TERMINADA", 'blanco'))
        draw_text(screen, titulo, (SCREEN_W // 2 - get_font('xl').size(titulo)[0] // 2, 200), size='xl', color=color)
        m = int(info.get('monto', 0) or 0)
        lineas = [f"Terminaste {info.get('posicion', '?')}º  ·  meta: {info.get('texto', '')}",
                  f"{'Premio' if m >= 0 else 'Multa'}: ${abs(m) / 1_000_000:.1f}M",
                  f"Calificación de DT: {info.get('calif', '?')}  ·  confianza: {info.get('confianza', '?')}"]
        if info.get('copa'):
            lineas.insert(1, f"Copa: {info['copa']['alcanzada']}  ·  meta: {info['copa']['texto']}")
        for i, t in enumerate(lineas):
            draw_text(screen, t, (SCREEN_W // 2 - get_font('md').size(t)[0] // 2, 320 + i * 40), size='md', color='blanco')
        draw_text(screen, "Enter para continuar", (16, 660), size='md', color='verde')
        return None
    except Exception as e:
        logger.error(f"Error en veredicto_screen: {e}", exc_info=True)
        return _siguiente(estado)
