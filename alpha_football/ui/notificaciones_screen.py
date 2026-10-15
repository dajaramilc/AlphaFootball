# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Notificaciones (v0.4.10.0). OFICINA > NOTIFICACIONES (tecla M).
Portada del buzón: MENSAJES (jugadores y presidente) a la izquierda y CORREO (el club) a la
derecha, con los últimos 5 de cada lado. Clic/Enter abre la lista completa de ese canal
(correo_screen filtrada). Teclado: ← → panel, ↑ ↓ elegir, Enter abrir, Esc volver.
"""
from __future__ import annotations

import logging
from typing import Optional
import pygame

try:
    from alpha_football.ui.theme import SCREEN_W, get_font, draw_gradient_bg, draw_panel, draw_button, draw_text
except Exception:
    SCREEN_W = 1280
    def get_font(size): return pygame.font.Font(None, 24)
    def draw_gradient_bg(screen): screen.fill((10, 14, 26))
    def draw_panel(screen, rect): pygame.draw.rect(screen, (20, 26, 46), rect)
    def draw_button(screen, rect, text, hover): return rect
    def draw_text(screen, text, pos, size='md', color='blanco', shadow=True): pass

from alpha_football import correo as C

logger = logging.getLogger(__name__)

R_MENSAJES = pygame.Rect(16, 76, 618, 620)
R_CORREO = pygame.Rect(646, 76, 618, 620)
PANELES = (('mensaje', "MENSAJES", R_MENSAJES), ('correo', "CORREO", R_CORREO))
N_PREVIA = 5
ALTO_ITEM = 100


def _volver() -> pygame.Rect:
    return pygame.Rect(SCREEN_W - 196, 16, 180, 44)


def rect_item(panel: int, i: int) -> pygame.Rect:
    r = PANELES[panel][2]
    return pygame.Rect(r.x + 10, r.y + 52 + i * ALTO_ITEM, r.width - 20, ALTO_ITEM - 8)


def rect_todos(panel: int) -> pygame.Rect:
    r = PANELES[panel][2]
    return pygame.Rect(r.x + 10, r.bottom - 58, 220, 46)


def ultimos(estado: dict, canal: str) -> list:
    return C.de_canal(estado, canal)[:N_PREVIA]


def abrir(estado: dict, canal: str, msg: Optional[dict] = None) -> str:
    """Abre la lista completa del canal, con `msg` seleccionado (o el más reciente)."""
    lista = C.de_canal(estado, canal)
    estado['correo_canal'] = canal
    estado['correo_sel'] = next((i for i, m in enumerate(lista) if m is msg), 0)
    return 'correo_screen'


def _pendiente(m: dict) -> bool:
    ev = m.get('evento')
    return bool(ev) and ev.get('resuelto') is None


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    try:
        foco = list(estado.get('notif_foco') or [0, 0])
        listas = [ultimos(estado, c) for c, _t, _r in PANELES]
        mouse_pos = pygame.mouse.get_pos()
        click = None
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return 'menu'
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    return 'league_screen'
                if ev.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    foco[0] = 0 if ev.key == pygame.K_LEFT else 1
                elif ev.key == pygame.K_DOWN:
                    foco[1] += 1
                elif ev.key == pygame.K_UP:
                    foco[1] -= 1
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    lista = listas[foco[0]]
                    estado['notif_foco'] = foco
                    return abrir(estado, PANELES[foco[0]][0], lista[max(0, min(foco[1], len(lista) - 1))] if lista else None)
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                click = ev.pos
        foco[1] = max(0, min(foco[1], len(listas[foco[0]]) - 1))
        estado['notif_foco'] = foco
        if click:
            if _volver().collidepoint(click):
                return 'league_screen'
            for p, (canal, _t, _r) in enumerate(PANELES):
                if rect_todos(p).collidepoint(click):
                    return abrir(estado, canal)
                for i, m in enumerate(listas[p]):
                    if rect_item(p, i).collidepoint(click):
                        estado['notif_foco'] = [p, i]
                        return abrir(estado, canal, m)

        draw_gradient_bg(screen)
        draw_text(screen, "NOTIFICACIONES", (16, 12), size='lg', color='dorado')
        draw_text(screen, f"{C.no_leidos(estado)} sin leer  ·  ← → panel · ↑ ↓ elegir · Enter abrir · Esc volver",
                  (16, 48), size='sm', color='azul')
        draw_button(screen, _volver(), "VOLVER", _volver().collidepoint(mouse_pos))
        for p, (canal, titulo, r) in enumerate(PANELES):
            draw_panel(screen, r)
            k = C.no_leidos(estado, canal)
            draw_text(screen, titulo + (f"  ·  {k} sin leer" if k else ""), (r.x + 16, r.y + 14), size='md',
                      color='dorado' if k else 'blanco')
            if not listas[p]:
                draw_text(screen, "Nada por aquí.", (r.x + 16, r.y + 64), size='sm', color='blanco')
            for i, m in enumerate(listas[p]):
                ri = rect_item(p, i)
                if foco == [p, i] or ri.collidepoint(mouse_pos):
                    pygame.draw.rect(screen, (40, 60, 95), ri, border_radius=6)
                cab = f"{C.REMITENTES.get(m['remitente'], m['remitente'])}  ·  {C.texto_fecha(m)}"   # v0.4.14.1
                if _pendiente(m):
                    cab += "  ·  DECISIÓN PENDIENTE"
                draw_text(screen, cab, (ri.x + 8, ri.y + 4), size='sm', color='rojo' if _pendiente(m) else 'azul',
                          shadow=False)
                draw_text(screen, m['asunto'][:56], (ri.x + 8, ri.y + 28), size='sm',
                          color='blanco' if m.get('leido') else 'dorado', shadow=False)
                previa = " ".join(C.sin_marcas(m.get('cuerpo', '')).split())[:64]    # v0.4.27.0: sin las marcas de negrita
                draw_text(screen, previa, (ri.x + 8, ri.y + 54), size='sm', color='azul', shadow=False)
            draw_button(screen, rect_todos(p), "VER TODOS", rect_todos(p).collidepoint(mouse_pos))
        return None
    except Exception as e:
        logger.error(f"Error en notificaciones_screen: {e}", exc_info=True)
        return 'league_screen'
