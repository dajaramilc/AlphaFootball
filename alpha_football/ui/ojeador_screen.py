# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Ojeador (Pygame)
v2.7.0: en cada ventana de mercado el ojeador recomienda 3 fichajes que mejoran los
puestos más flojos de tu once y que puedes pagar.
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

from alpha_football import negociacion as N

logger = logging.getLogger(__name__)


def _rects_tarjetas(n: int) -> list:
    return [pygame.Rect(16 + i * 422, 120, 404, 520) for i in range(n)]


def _rects_fichar(n: int) -> list:
    return [pygame.Rect(r.x + 20, r.bottom - 68, r.width - 40, 48) for r in _rects_tarjetas(n)]


def _volver() -> pygame.Rect:
    return pygame.Rect(1116, 12, 148, 40)


def _envolver(texto: str, ancho: int) -> list:
    palabras, lineas, actual = texto.split(), [], ""
    for p in palabras:
        prueba = (actual + " " + p).strip()
        if get_font('sm').size(prueba)[0] > ancho and actual:
            lineas.append(actual)
            actual = p
        else:
            actual = prueba
    return lineas + ([actual] if actual else [])


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """Retorna 'league_screen' al salir o None para seguir aquí."""
    try:
        mi = estado.get('mi_equipo')
        if mi is None:
            return 'league_screen'
        recs = N.recomendaciones_ojeador(estado)
        mouse_pos = pygame.mouse.get_pos()
        from alpha_football.ui.foco import traducir_eventos, marcar   # v4.2.0: teclado
        rects_foco = list(_rects_fichar(len(recs))) + [_volver()]
        foco, eventos = traducir_eventos(estado, 'foco_ojeador', rects_foco, list(pygame.event.get()))
        for ev in eventos:
            if ev.type == pygame.QUIT:
                return 'menu'
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                return 'league_screen'
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if _volver().collidepoint(ev.pos):
                    return 'league_screen'
                for (j, club, _et, precio, _m), r in zip(recs, _rects_fichar(len(recs))):
                    if r.collidepoint(ev.pos):
                        # v2.9.0: se negocia con el club y con el jugador.
                        return N.iniciar_negociacion(estado, j, club, 'fichaje', 'ojeador_screen')

        draw_gradient_bg(screen)
        draw_text(screen, "OJEADOR", (16, 12), size='lg', color='dorado')
        liga = estado.get('liga')
        try:
            from alpha_football.market import ventana_mercado_abierta
            abierta = ventana_mercado_abierta(liga.jornada_actual, liga.num_jornadas)
        except Exception:
            abierta = True
        temporada, ventana = N._clave_ventana(estado)
        draw_text(screen, f"Informe para la ventana de {'inicio' if ventana == 'inicio' else 'cierre'} de la T{temporada}"
                          f"  ·  Mercado {'ABIERTO' if abierta else 'cerrado (puedes fichar igual)'}"
                          f"  ·  Presupuesto ${mi.balance / 1_000_000:.1f}M",
                  (16, 56), size='sm', color='verde' if abierta else 'azul')
        draw_text(screen, "Refuerza los puestos más flojos de tu mejor once, dentro de tu presupuesto.",
                  (16, 82), size='sm', color='azul')
        draw_button(screen, _volver(), "VOLVER", _volver().collidepoint(mouse_pos))

        if not recs:
            draw_text(screen, "El ojeador no encontró fichajes que mejoren tu once con tu presupuesto.",
                      (16, 160), size='md', color='blanco')
        for (j, club, etiqueta, precio, motivo), caja, bf in zip(recs, _rects_tarjetas(len(recs)), _rects_fichar(len(recs))):
            draw_panel(screen, caja)
            x, y = caja.x + 20, caja.y + 16
            draw_text(screen, f"{j.nombre} {j.apellido}"[:24], (x, y), size='lg', color='dorado')
            y += 42
            draw_text(screen, f"{getattr(club, 'nombre', 'Agente libre')[:26]}  ·  {etiqueta}", (x, y), size='sm', color='azul')
            y += 28
            draw_text(screen, f"{j.posicion}  ·  {j.edad} años", (x, y), size='md', color='blanco')
            y += 34
            draw_text(screen, f"MEDIA {j.overall}   POT {getattr(j, 'potencial', 0) or '?'}", (x, y), size='lg', color='verde')
            y += 46
            draw_text(screen, f"Precio ${precio / 1_000_000:.1f}M", (x, y), size='md', color='blanco')
            y += 40
            draw_text(screen, "Por qué:", (x, y), size='sm', color='dorado')
            y += 24
            for linea in _envolver(motivo, caja.width - 40):
                draw_text(screen, linea, (x, y), size='sm', color='blanco')
                y += 22
            draw_button(screen, bf, "FICHAR", bf.collidepoint(mouse_pos))

        marcar(screen, rects_foco[foco])
        msg = estado.get('ojeador_msg')
        if msg and pygame.time.get_ticks() < msg[1]:
            s = get_font('md').render(msg[0], True, COLORS['bg'])
            caja = s.get_rect(center=(SCREEN_W // 2, 680)).inflate(40, 16)
            pygame.draw.rect(screen, COLORS.get(msg[2], COLORS['verde']), caja, border_radius=8)
            screen.blit(s, s.get_rect(center=caja.center))
        return None
    except Exception as e:
        logger.error(f"Error en ojeador_screen: {e}", exc_info=True)
        return 'league_screen'
