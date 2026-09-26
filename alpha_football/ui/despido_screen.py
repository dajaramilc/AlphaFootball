# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Despido (Pygame)
v2.8.0: la directiva te echó por no cumplir el objetivo. Eliges uno de los 3 clubes de
menor nivel que te ofrecen y la carrera sigue ahí.
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

from alpha_football import directiva as D

logger = logging.getLogger(__name__)


def _rects_opciones(n: int) -> list:
    """Tarjetas en una fila; con 4 (renovar + 3 clubes) se angostan para entrar en 1280."""
    gap = 18
    w = min(404, (SCREEN_W - 32 - gap * max(0, n - 1)) // max(1, n))
    return [pygame.Rect(16 + i * (w + gap), 210, w, 380) for i in range(n)]


RENOVAR = 'renovar'       # primera tarjeta cuando el club mantiene su oferta de renovación


def items(pend: dict) -> list:
    """Tarjetas de la pantalla: RENOVAR (si había oferta sin responder) y los clubes que te quieren."""
    return ([RENOVAR] if pend.get('renovable') else []) + list(pend.get('opciones') or [])


def _liga_de(estado, equipo):
    for clave in ('primera_division', 'segunda_division'):
        for liga in (estado.get(clave) or {}).values():
            if liga is not None and any(e is equipo for e in liga.equipos):
                return liga
    return None


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """Elige club y sigue (ascensos/descensos si hay, si no al hub)."""
    try:
        pend = estado.get('despido_pendiente')
        if not pend:
            return 'league_screen'
        opciones = items(pend)
        rects = _rects_opciones(len(opciones))
        mouse_pos = pygame.mouse.get_pos()
        from alpha_football.ui.foco import traducir_eventos, marcar   # v4.2.0: teclado
        foco, eventos = traducir_eventos(estado, 'foco_despido', rects, list(pygame.event.get()))
        for ev in eventos:
            if ev.type == pygame.QUIT:
                return 'menu'
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if not opciones:
                    estado.pop('despido_pendiente', None)
                    (estado.get('datos_carrera') or {}).pop('despido_pendiente', None)
                    if pend.get('titulo') == "FIN DE CONTRATO":   # v3.2.0: nadie llama → renuevas donde estás
                        estado['contrato_modo'] = 'alta'
                        return 'contrato_dt_screen'
                    return 'promo_releg_screen' if estado.get('promo_releg_data') else 'league_screen'
                for eq, r in zip(opciones, rects):
                    if r.collidepoint(ev.pos) and eq == RENOVAR:
                        # se sigue en el club: contrato de renovación (si lo rechazas vuelves aquí)
                        estado['renovacion_tardia'] = True
                        estado['contrato_modo'] = 'renovacion'
                        return 'contrato_dt_screen'
                    if r.collidepoint(ev.pos):
                        D.cambiar_de_club(estado, eq)
                        estado['contrato_modo'] = 'alta'      # v3.2.0: contrato con el club nuevo
                        return 'contrato_dt_screen'

        draw_gradient_bg(screen)
        draw_text(screen, pend.get('titulo', "¡DESPEDIDO!"), (16, 20), size='xl', color='rojo')   # v3.2.0
        # el motivo puede ser largo: se parte en hasta 2 líneas que entren entre y=78 y y=140
        motivo = str(pend.get('motivo', ''))
        palabras, lineas = motivo.split(), ['']
        if get_font('md').size(motivo)[0] <= SCREEN_W - 32:
            palabras, lineas = [], [motivo]
        for p in palabras:
            prueba = f"{lineas[-1]} {p}".strip()
            if get_font('sm').size(prueba)[0] <= SCREEN_W - 32 or not lineas[-1]:
                lineas[-1] = prueba
            elif len(lineas) < 2:
                lineas.append(p)
            else:
                lineas[-1] = lineas[-1].rstrip('.') + '…'
                break
        for k, linea in enumerate(lineas):
            draw_text(screen, linea, (16, 84 + k * 26), size='sm' if palabras else 'md', color='blanco')
        draw_text(screen, ("Renueva con tu club o elige otra oferta:" if pend.get('renovable')
                           else "Te ofrecen el banquillo. Elige dónde sigue tu carrera:"),
                  (16, 150), size='md', color='dorado')
        if not opciones:
            draw_text(screen, "Nadie más te ofrece trabajo: la directiva te da otra oportunidad (clic para seguir).",
                      (16, 220), size='md', color='rojo')
        for eq, r in zip(opciones, rects):
            hover = r.collidepoint(mouse_pos) or r is rects[foco]
            draw_panel(screen, r)
            if hover:
                pygame.draw.rect(screen, COLORS['dorado'], r, width=3, border_radius=8)
            if eq == RENOVAR:
                mi = estado.get('mi_equipo')
                x, y = r.x + 20, r.y + 20
                pygame.draw.rect(screen, COLORS['verde'], r, width=2, border_radius=8)
                draw_text(screen, "RENOVAR", (x, y), size='lg', color='verde')
                draw_text(screen, getattr(mi, 'nombre', 'Tu club')[:24], (x, y + 46), size='md', color='dorado')
                draw_text(screen, "Tu club mantiene su oferta.", (x, y + 110), size='sm', color='blanco')
                draw_text(screen, "Sigues con tu plantilla", (x, y + 140), size='sm', color='blanco')
                draw_text(screen, "y con sueldo de renovación.", (x, y + 164), size='sm', color='blanco')
                boton = pygame.Rect(r.x + 20, r.bottom - 68, r.width - 40, 48)
                draw_button(screen, boton, "VER RENOVACIÓN", hover)
                continue
            liga = _liga_de(estado, eq)
            x, y = r.x + 20, r.y + 20
            draw_text(screen, eq.nombre[:24], (x, y), size='lg', color='dorado')
            draw_text(screen, f"{getattr(liga, 'nombre', '?')[:30]}", (x, y + 46), size='sm', color='azul')
            draw_text(screen, f"{'2ª' if getattr(liga, 'division', 1) == 2 else '1ª'} división", (x, y + 70), size='sm', color='azul')
            draw_text(screen, f"MEDIA {eq.ovr_promedio}", (x, y + 110), size='lg', color='verde')
            draw_text(screen, f"Presupuesto ${eq.balance / 1_000_000:.1f}M", (x, y + 160), size='md', color='blanco')
            draw_text(screen, f"Plantilla {len(eq.jugadores)} jugadores", (x, y + 194), size='md', color='blanco')
            estrella = max(eq.jugadores, key=lambda j: j.overall, default=None)
            if estrella is not None:
                draw_text(screen, f"Figura: {estrella.nombre_completo[:22]} ({estrella.overall})", (x, y + 228),
                          size='sm', color='blanco')
            boton = pygame.Rect(r.x + 20, r.bottom - 68, r.width - 40, 48)
            draw_button(screen, boton, "ACEPTAR OFERTA", hover)
        return None
    except Exception as e:
        logger.error(f"Error en despido_screen: {e}", exc_info=True)
        return 'league_screen'
