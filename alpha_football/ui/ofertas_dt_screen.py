# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Ofertas de banquillo (Pygame)
v3.4.0: clubes que echaron a su DT y te quieren. ACEPTAR = cambio inmediato + contrato;
RECHAZAR = contratan a otro. Las ofertas duran 3 jornadas.
v4.7.0: también la oferta por tu calificación (ofertas_dt, antes en OBJETIVOS) y el motivo de cada una.
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
    return pygame.Rect(16, 110 + i * 134, SCREEN_W - 32, 124)      # v4.7.0: +1 línea (objetivo y presupuesto)


def _m(v) -> str:
    return f"${int(v or 0) / 1_000_000:.1f}M"


def _detalle(objetivo: str, presupuesto) -> str:
    return f"Objetivo: {objetivo or '—'}  ·  Presupuesto: {_m(presupuesto)}"



def rect_aceptar(i: int) -> pygame.Rect:
    r = _fila(i); return pygame.Rect(r.right - 440, r.y + 34, 200, 48)


def rect_rechazar(i: int) -> pygame.Rect:
    r = _fila(i); return pygame.Rect(r.right - 220, r.y + 34, 200, 48)


def filas(estado: dict) -> list:
    """v4.7.0: la oferta por calificación (ofertas_dt) primero y luego las de banquillo; máx. 4."""
    out = []
    try:
        from alpha_football import ofertas_dt as ODT
        from alpha_football.directiva import _jugadas
        of = ODT.oferta_vigente(estado)
        if of is not None:
            liga, mi = estado.get('liga'), estado.get('mi_equipo')
            quedan = max(0, int(of.get('vence', 0)) - _jugadas(liga, mi)) if liga is not None and mi is not None else 0
            out.append({'origen': 'calif', 'club': of['club'], 'liga': of.get('liga', ''), 'club_id': of['club_id'],
                        'motivo': "Por tu calificación como DT", 'plazo': quedan,
                        'detalle': _detalle(of.get('objetivo'), of.get('presupuesto', 0))})
            if 'objetivo' not in of:        # oferta de un save viejo: se calcula del club
                eq, lg = EN._club_por_id(estado, of['club_id'])
                if eq is not None:
                    out[-1]['detalle'] = _detalle(ODT._objetivo_de(eq, lg), getattr(eq, 'balance', 0))
    except Exception as e:
        logger.error(f"No se pudo leer la oferta por calificación: {e}")
    for o in EN.ofertas_activas(estado):
        detalle = ""
        try:   # mismo criterio de objetivo que la oferta por calificación
            from alpha_football.ofertas_dt import _objetivo_de
            eq, lg = EN._club_por_id(estado, o['club_id'])
            if eq is not None:
                detalle = _detalle(_objetivo_de(eq, lg), getattr(eq, 'balance', 0))
        except Exception as e:
            logger.error(f"No se pudo calcular el detalle de la oferta de {o.get('club')}: {e}")
        out.append({'origen': 'banquillo', 'club': o['club'], 'liga': o.get('liga', ''), 'club_id': o['club_id'],
                    'motivo': o.get('causa') or "Despidieron a su DT" + (f" ({o['motivo']})" if o.get('motivo') else ""),
                    'plazo': int(o.get('jornadas', 0)), 'detalle': detalle})
    return out[:4]


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """Lista de ofertas (máx. 4) con ACEPTAR / RECHAZAR."""
    try:
        ofertas = filas(estado)
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
                    if rect_aceptar(i).collidepoint(ev.pos):
                        if o['origen'] == 'calif':       # v4.7.0: oferta por calificación (ofertas_dt)
                            from alpha_football import ofertas_dt as ODT
                            estado['espaldarazo_msg'] = ODT.aceptar(estado)
                            estado['contrato_modo'] = 'alta'
                            return 'contrato_dt_screen'
                        if EN.aceptar_oferta(estado, o['club_id']) is not None:
                            estado['contrato_modo'] = 'alta'
                            return 'contrato_dt_screen'
                    if rect_rechazar(i).collidepoint(ev.pos):
                        if o['origen'] == 'calif':
                            from alpha_football import ofertas_dt as ODT
                            ODT.rechazar(estado)
                        else:
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
                          (r.x + 20, r.y + 52), size='sm', color='azul')
            if o.get('detalle'):
                draw_text(screen, o['detalle'][:84], (r.x + 20, r.y + 76), size='sm', color='blanco')
            draw_text(screen, o['motivo'][:60], (r.x + 20, r.y + 100), size='sm', color='dorado')   # v4.7.0
            draw_text(screen, f"Vence en {o['plazo']} jornada{'s' if o['plazo'] != 1 else ''}",
                      (r.x + 560, r.y + 100), size='sm', color='rojo')
            draw_button(screen, rect_aceptar(i), "ACEPTAR", rect_aceptar(i).collidepoint(mouse_pos))
            draw_button(screen, rect_rechazar(i), "RECHAZAR", rect_rechazar(i).collidepoint(mouse_pos))
        marcar(screen, rects_foco[foco])
        return None
    except Exception as e:
        logger.error(f"Error en ofertas_dt_screen: {e}", exc_info=True)
        return 'league_screen'
