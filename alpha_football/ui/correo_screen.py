# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Correo (v3.1.0). OFICINA > CORREO.
Lista a la izquierda (no leídos en dorado), mensaje a la derecha y botón de acción que lleva a
la pantalla donde se resuelve. Teclado: ↑/↓ elegir, Enter = acción, Esc = volver.
"""
from __future__ import annotations

import logging
from typing import Optional
import pygame

try:
    from alpha_football.ui.theme import SCREEN_W, COLORS, get_font, draw_gradient_bg, draw_panel, draw_button, draw_text
except Exception:
    SCREEN_W = 1280
    COLORS = {'blanco': (255, 255, 255)}
    def get_font(size): return pygame.font.Font(None, 24)
    def draw_gradient_bg(screen): screen.fill((10, 14, 26))
    def draw_panel(screen, rect): pygame.draw.rect(screen, (20, 26, 46), rect)
    def draw_button(screen, rect, text, hover): return rect
    def draw_text(screen, text, pos, size='md', color='blanco', shadow=True): pass

from alpha_football import correo as C

logger = logging.getLogger(__name__)

R_LISTA = pygame.Rect(16, 76, 560, 620)        # v3.6.0: terminan en y=696 (barra de atajos)
R_MSG = pygame.Rect(588, 76, 676, 620)
ALTO_FILA = 44
FILAS = (R_LISTA.height - 16) // ALTO_FILA


def _volver() -> pygame.Rect:
    return pygame.Rect(SCREEN_W - 196, 16, 180, 44)


def _rect_fila(i: int) -> pygame.Rect:
    return pygame.Rect(R_LISTA.x + 8, R_LISTA.y + 8 + i * ALTO_FILA, R_LISTA.width - 16, ALTO_FILA - 4)


def _rect_accion() -> pygame.Rect:
    return pygame.Rect(R_MSG.x + 20, R_MSG.bottom - 70, 360, 50)


def _envolver(texto: str, ancho_px: int, size: str = 'sm') -> list:
    fuente, lineas, linea = get_font(size), [], ""
    for palabra in str(texto).split():
        prueba = (linea + " " + palabra).strip()
        if fuente.size(prueba)[0] > ancho_px and linea:
            lineas.append(linea)
            linea = palabra
        else:
            linea = prueba
    return lineas + ([linea] if linea else [])


def _ir(estado: dict, msg: dict) -> Optional[str]:
    acc = msg.get('accion') or {}
    if acc.get('compra'):          # v3.5.0: el club aceptó tu oferta → contrato con el jugador
        from alpha_football.negociacion import reanudar_compra
        destino = reanudar_compra(estado, acc['compra'])
        if destino is None:
            estado['correo_aviso_vis'] = (msg.get('id'), estado.pop('correo_aviso', ''))
        return destino
    if acc.get('renovar'):         # v4.4.0: el jugador pide renovar → negociación de su contrato
        mi = estado.get('mi_equipo')
        j = next((x for x in getattr(mi, 'jugadores', []) or [] if x.id == acc['renovar']), None)
        if j is None:
            estado['correo_aviso_vis'] = (msg.get('id'), "Ese jugador ya no está en tu plantilla.")
            return None
        from alpha_football.negociacion import iniciar_negociacion
        return iniciar_negociacion(estado, j, None, 'renovar', 'correo_screen')
    if not acc.get('pantalla'):
        return None
    from alpha_football.ui.league_screen import _abrir
    return _abrir(estado, acc['pantalla'])


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    try:
        mensajes = C.bandeja(estado)
        sel = max(0, min(int(estado.get('correo_sel', 0) or 0), len(mensajes) - 1))
        mouse_pos = pygame.mouse.get_pos()
        click = None
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return 'menu'
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    return 'league_screen'
                if ev.key == pygame.K_DOWN:
                    sel = min(len(mensajes) - 1, sel + 1)
                elif ev.key == pygame.K_UP:
                    sel = max(0, sel - 1)
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and mensajes:
                    destino = _ir(estado, mensajes[sel])
                    if destino:
                        return destino
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                click = ev.pos
        inicio = max(0, sel - FILAS + 1)
        if click:
            if _volver().collidepoint(click):
                return 'league_screen'
            for i in range(min(FILAS, len(mensajes) - inicio)):
                if _rect_fila(i).collidepoint(click):
                    sel = inicio + i
            if mensajes and _rect_accion().collidepoint(click):
                destino = _ir(estado, mensajes[sel])
                if destino:
                    return destino
        estado['correo_sel'] = sel
        if mensajes:
            C.marcar_leido(estado, mensajes[sel]['id'])

        draw_gradient_bg(screen)
        draw_text(screen, "CORREO", (16, 12), size='lg', color='dorado')
        draw_text(screen, f"{len(mensajes)} mensajes  ·  {C.no_leidos(estado)} sin leer  ·  "
                          f"↑/↓ elegir · Enter acción · Esc volver", (16, 48), size='sm', color='azul')
        draw_button(screen, _volver(), "VOLVER", _volver().collidepoint(mouse_pos))
        draw_panel(screen, R_LISTA)
        draw_panel(screen, R_MSG)
        if not mensajes:
            draw_text(screen, "No tienes mensajes.", (R_LISTA.x + 20, R_LISTA.y + 20), size='sm', color='blanco')
            return None
        for i, m in enumerate(mensajes[inicio:inicio + FILAS]):
            r = _rect_fila(i)
            if inicio + i == sel:
                pygame.draw.rect(screen, (40, 60, 95), r, border_radius=6)
            col = 'dorado' if not m.get('leido') else 'blanco'
            draw_text(screen, f"{C.REMITENTES.get(m['remitente'], m['remitente'])}  ·  T{m['temporada']} J{m['jornada']}",
                      (r.x + 8, r.y + 2), size='sm', color='azul', shadow=False)
            draw_text(screen, m['asunto'][:52], (r.x + 8, r.y + 20), size='sm', color=col, shadow=False)
        m = mensajes[sel]
        x, y = R_MSG.x + 20, R_MSG.y + 16
        draw_text(screen, C.REMITENTES.get(m['remitente'], m['remitente']), (x, y), size='sm', color='azul')
        for k, linea in enumerate(_envolver(m['asunto'], R_MSG.width - 40, 'md')[:2]):
            draw_text(screen, linea, (x, y + 26 + k * 30), size='md', color='dorado')
        for k, linea in enumerate(_envolver(m['cuerpo'], R_MSG.width - 40)[:14]):
            draw_text(screen, linea, (x, y + 100 + k * 26), size='sm', color='blanco')
        acc = m.get('accion') or {}
        if acc.get('pantalla'):
            draw_button(screen, _rect_accion(), acc.get('texto', 'IR'), _rect_accion().collidepoint(mouse_pos))
        aviso = estado.get('correo_aviso_vis')     # v3.5.0: acuerdo de compra que ya no vale
        if aviso and aviso[0] == m.get('id') and aviso[1]:
            draw_text(screen, str(aviso[1])[:60], (_rect_accion().right + 16, _rect_accion().y + 14), size='sm', color='rojo')
        return None
    except Exception as e:
        logger.error(f"Error en correo_screen: {e}", exc_info=True)
        return 'league_screen'
