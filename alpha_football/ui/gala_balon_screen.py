# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Gala de premios (Pygame, v0.4.17.0)
Balón de Oro (octubre) y Jugador Sudamericano del Año (enero). Solo se abre si el ganador o alguien
del podio juega en tu club: el hub la muestra una vez por gala (datos_carrera['gala_premio_pendiente']).
Enter, Espacio o clic pasa a la siguiente gala o vuelve al hub.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Optional
import pygame

try:
    from alpha_football.ui.theme import SCREEN_W, SCREEN_H, get_font, draw_gradient_bg, draw_text
except Exception:
    SCREEN_W, SCREEN_H = 1280, 720
    def get_font(size): return pygame.font.Font(None, 24)
    def draw_gradient_bg(screen): screen.fill((10, 14, 26))
    def draw_text(screen, text, pos, size='md', color='blanco', shadow=True): pass

logger = logging.getLogger(__name__)

MESES = ('enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre',
         'noviembre', 'diciembre')
R_PREMIO = pygame.Rect(140, 70, 1000, 110)       # expuestos (ayuda H)
R_GANADOR = pygame.Rect(140, 210, 1000, 170)
R_PODIO = pygame.Rect(140, 410, 1000, 120)


def _pendientes(estado: dict) -> list:
    dc = estado.setdefault('datos_carrera', {})
    if not isinstance(dc.get('gala_premio_pendiente'), list):
        dc['gala_premio_pendiente'] = []
    return dc['gala_premio_pendiente']


def _valida(g) -> bool:
    return isinstance(g, dict) and bool(((g.get('datos') or {}).get('ganador') or {}).get('nombre'))


def _fecha_larga(txt) -> str:
    try:
        d = date.fromisoformat(str(txt))
        return f"Gala del {d.day} de {MESES[d.month - 1]} de {d.year}"
    except Exception:
        return ""


def _centrado(screen, txt: str, y: int, size: str, color: str) -> None:
    draw_text(screen, txt, (SCREEN_W // 2 - get_font(size).size(txt)[0] // 2, y), size=size, color=color)


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    try:
        pend = _pendientes(estado)
        while pend and not _valida(pend[0]):         # gala dañada: se descarta y no traba el hub
            pend.pop(0)
        if not pend:
            return 'league_screen'
        avanzar = False
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return 'menu'
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE,
                                                        pygame.K_ESCAPE):
                avanzar = True
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                avanzar = True
        if avanzar:
            pend.pop(0)
            while pend and not _valida(pend[0]):
                pend.pop(0)
            return None if pend else 'league_screen'

        from alpha_football.premios import PREMIOS
        gala = pend[0]
        datos = gala['datos']
        g = datos['ganador']
        nombre = (PREMIOS.get(gala.get('premio')) or {}).get('nombre', "Premio de la temporada")
        mi = getattr(estado.get('mi_equipo'), 'nombre', None)
        tuyos = gala.get('tuyos')                    # los de tu club hoy; una gala guardada sin la clave: por club
        color = lambda x: 'verde' if (x.get('nombre') in tuyos if isinstance(tuyos, list)
                                      else mi and x.get('equipo') == mi) else 'blanco'

        draw_gradient_bg(screen)
        _centrado(screen, nombre.upper(), 90, 'xl', 'dorado')
        _centrado(screen, " · ".join(t for t in (f"Temporada {datos.get('temporada', '?')}",
                                                 _fecha_larga(gala.get('fecha'))) if t), 150, 'sm', 'azul')
        _centrado(screen, str(g.get('nombre', '?'))[:40], 230, 'xl', color(g))
        _centrado(screen, f"{str(g.get('equipo', '?'))[:28]} · {str(g.get('liga', '?'))[:32]} · "
                          f"{g.get('posicion', '?')} {g.get('ovr', '?')}", 300, 'md', 'blanco')
        _centrado(screen, f"{g.get('goles', 0)} goles · {g.get('asistencias', 0)} asistencias · "
                          f"nota {float(g.get('nota', 0) or 0):.2f} · {g.get('pj', 0)} partidos", 340, 'md', 'azul')
        for i, x in enumerate((datos.get('podio') or [])[1:3]):
            _centrado(screen, f"{i + 2}º  {str(x.get('nombre', '?'))[:30]} ({str(x.get('equipo', '?'))[:24]}) · "
                              f"{x.get('goles', 0)} G · nota {float(x.get('nota', 0) or 0):.2f}",
                      430 + i * 44, 'md', color(x))
        draw_text(screen, "Enter para continuar", (16, 660), size='md', color='verde')
        return None
    except Exception as e:
        logger.error(f"Error en gala_balon_screen: {e}", exc_info=True)
        estado.setdefault('datos_carrera', {})['gala_premio_pendiente'] = []
        return 'league_screen'
