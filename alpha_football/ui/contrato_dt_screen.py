# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Contrato del DT (Pygame)
v3.2.0: firma estilo FIFA al llegar a un club ('alta'), oferta de renovación ('renovacion')
y consulta del contrato vigente ('ver', tarjeta MI CONTRATO en OFICINA).
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

from alpha_football import carrera_dt as CD
from alpha_football import directiva as D

logger = logging.getLogger(__name__)

R_RECHAZAR = pygame.Rect(16, 620, 320, 52)
R_VOLVER = pygame.Rect(SCREEN_W - 216, 12, 200, 44)


def _rects(n: int) -> list:
    return [pygame.Rect(16 + i * 422, 200, 404, 360) for i in range(n)]


def modo(estado: dict) -> str:
    """'alta' / 'renovacion' / 'ver' (sin modo explícito: renovación si hay una oferta vigente)."""
    m = estado.get('contrato_modo')
    if m in ('alta', 'renovacion', 'ver'):
        return m
    r = (estado.get('datos_carrera') or {}).get('renovacion_dt') or {}
    if r.get('estado') == 'ofrecida' and r.get('temporada') == int(estado.get('temporada', 1) or 1):
        return 'renovacion'
    return 'ver'


def _m(v) -> str:
    return f"${int(v) / 1_000_000:.2f}M"


def _salir(estado: dict, m: str) -> str:
    estado.pop('contrato_modo', None)
    estado.pop('contrato_sel', None)
    if m == 'alta' and estado.get('promo_releg_data'):
        return 'promo_releg_screen'
    return 'league_screen'


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    try:
        mi = estado.get('mi_equipo')
        if mi is None:
            return 'league_screen'
        m = modo(estado)
        ofertas = CD.ofertas_contrato(estado, mi, renovacion=(m == 'renovacion')) if m != 'ver' else []
        sel = max(0, min(int(estado.get('contrato_sel', 1) or 0), max(0, len(ofertas) - 1)))
        rects = _rects(len(ofertas))
        mouse_pos = pygame.mouse.get_pos()
        elegido = None
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return 'menu'
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_LEFT:
                    sel = max(0, sel - 1)
                elif ev.key == pygame.K_RIGHT:
                    sel = min(max(0, len(ofertas) - 1), sel + 1)
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and ofertas:
                    elegido = sel
                elif ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE) and m != 'alta':
                    return _salir(estado, m)
                elif ev.key == pygame.K_r and m == 'renovacion':   # v4.2.0: R = RECHAZAR
                    CD.rechazar_renovacion(estado)
                    return _salir(estado, m)
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                for i, r in enumerate(rects):
                    if r.collidepoint(ev.pos):
                        elegido = i
                if m == 'renovacion' and R_RECHAZAR.collidepoint(ev.pos):
                    CD.rechazar_renovacion(estado)
                    return _salir(estado, m)
                if m != 'alta' and R_VOLVER.collidepoint(ev.pos):
                    return _salir(estado, m)
        estado['contrato_sel'] = sel
        if elegido is not None:
            CD.firmar(estado, mi, ofertas[elegido], renovacion=(m == 'renovacion'))
            return _salir(estado, m)

        draw_gradient_bg(screen)
        titulo = {'alta': "CONTRATO DE DT", 'renovacion': "RENOVACIÓN DE CONTRATO", 'ver': "MI CONTRATO"}[m]
        draw_text(screen, titulo, (16, 16), size='xl', color='dorado')
        draw_text(screen, f"{mi.nombre}  ·  {getattr(estado.get('liga'), 'nombre', '')}  ·  "
                          f"Calificación de DT {D.calif_dt(estado)}", (16, 84), size='md', color='verde')
        if m != 'alta':
            draw_button(screen, R_VOLVER, "VOLVER", R_VOLVER.collidepoint(mouse_pos))
        if m == 'ver':
            c = CD.contrato(estado) or {}
            ren = (estado.get('datos_carrera') or {}).get('renovacion_dt') or {}
            lineas = [(f"Sueldo anual: {_m(c.get('sueldo', 0))}", 'blanco'),
                      (f"Contrato: temporada {c.get('desde', '?')} a {c.get('hasta', '?')}", 'blanco'),
                      (f"Patrimonio personal: {_m(CD.patrimonio(estado))}", 'dorado'),
                      (f"Renovación: {ren.get('estado', 'sin novedades')}", 'azul')]
            for i, (t, col) in enumerate(lineas):
                draw_text(screen, t, (32, 160 + i * 44), size='lg', color=col)
            clubes = (estado.get('datos_carrera') or {}).get('clubes_dirigidos') or []
            draw_text(screen, "CLUBES DIRIGIDOS", (32, 360), size='md', color='azul')
            for i, cd in enumerate(clubes[-6:]):
                draw_text(screen, f"T{cd.get('temporada')}: {cd.get('de')} → {cd.get('a')}", (32, 396 + i * 30),
                          size='sm', color='blanco')
            return None
        draw_text(screen, "Elige tu contrato (← → y Enter, o clic):", (16, 140), size='md', color='blanco')
        for i, (of, r) in enumerate(zip(ofertas, rects)):
            activo = i == sel or r.collidepoint(mouse_pos)
            draw_panel(screen, r)
            if activo:
                pygame.draw.rect(screen, COLORS['dorado'], r, width=3, border_radius=8)
            x, y = r.x + 24, r.y + 24
            draw_text(screen, f"{of['anios']} AÑO{'S' if of['anios'] > 1 else ''}", (x, y), size='xl', color='dorado')
            draw_text(screen, f"Sueldo anual {_m(of['sueldo'])}", (x, y + 90), size='md', color='verde')
            draw_text(screen, f"Total {_m(of['sueldo'] * of['anios'])}", (x, y + 130), size='md', color='blanco')
            draw_text(screen, "Más estabilidad" if of['anios'] == 3 else "Más sueldo" if of['anios'] == 1
                      else "Equilibrado", (x, y + 180), size='sm', color='azul')
            draw_button(screen, pygame.Rect(r.x + 20, r.bottom - 68, r.width - 40, 48), "FIRMAR", activo)
        if m == 'renovacion':
            draw_button(screen, R_RECHAZAR, "RECHAZAR (me voy al final)", R_RECHAZAR.collidepoint(mouse_pos))
        return None
    except Exception as e:
        logger.error(f"Error en contrato_dt_screen: {e}", exc_info=True)
        return 'league_screen'
