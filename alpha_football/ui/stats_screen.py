# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Estadísticas / Tablas de la temporada (Pygame).

Tablas accesibles desde el hub de carrera:
  - Goleadores (goles)
  - Asistencias (asistencias)
  - Vallas invictas (porterías a cero)
  - Mejores calificaciones (promedio de nota, con mínimo de partidos)
Agrega sobre todos los jugadores de la liga del usuario.
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

logger = logging.getLogger(__name__)

# (clave de pestaña, etiqueta, atributo, encabezado de la métrica, filtro_min_partidos)
TABS = [
    ("goles", "GOLEADORES", "goles", "GOL", 0),
    ("asist", "ASISTENCIAS", "asistencias", "ASI", 0),
    ("vallas", "VALLAS INVICTAS", "porterias_cero", "VI", 0),
    ("notas", "MEJORES NOTAS", "promedio_nota", "NOTA", 1),
]


def _jugadores_con_club(estado: dict) -> list:
    """Lista de (jugador, club_corto) de todos los equipos de la liga del usuario."""
    out = []
    liga = estado.get('liga')
    if not liga:
        return out
    for eq in getattr(liga, 'equipos', []):
        club = getattr(eq, 'corto', None) or getattr(eq, 'nombre', '?')
        for j in getattr(eq, 'jugadores', []):
            out.append((j, club))
    return out


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    try:
        estado.setdefault('stats_tab', 'goles')
        estado.setdefault('stats_scope', 'liga')  # 'liga' (predomina) o 'mi_equipo'

        mouse_pos = pygame.mouse.get_pos()
        click_pos = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "menu"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                click_pos = event.pos

        draw_gradient_bg(screen)
        draw_text(screen, "ESTADÍSTICAS DE LA TEMPORADA", (40, 22), size='xl', color='dorado')

        # Alcance: TODA LA LIGA (por defecto) / MI EQUIPO
        sc_liga = pygame.Rect(760, 20, 230, 40)
        sc_mi = pygame.Rect(1000, 20, 230, 40)
        for r, clave, txt in ((sc_liga, 'liga', 'TODA LA LIGA'), (sc_mi, 'mi_equipo', 'MI EQUIPO')):
            act = (estado['stats_scope'] == clave)
            try:
                pygame.draw.rect(screen, (0, 191, 255) if act else (20, 26, 46), r, border_radius=6)
                pygame.draw.rect(screen, (255, 215, 0) if act else (0, 191, 255), r, width=1, border_radius=6)
            except Exception:
                pass
            s = get_font('sm').render(txt, True, (10, 14, 26) if act else (255, 255, 255))
            screen.blit(s, s.get_rect(center=r.center))
            if click_pos and r.collidepoint(click_pos):
                estado['stats_scope'] = clave

        # Pestañas
        tab_rects = {}
        tx = 40
        for clave, etiqueta, _attr, _h, _m in TABS:
            r = pygame.Rect(tx, 80, 250, 38)
            tab_rects[clave] = r
            activo = (estado['stats_tab'] == clave)
            try:
                pygame.draw.rect(screen, (0, 191, 255) if activo else (20, 26, 46), r, border_radius=6)
                pygame.draw.rect(screen, (255, 215, 0) if activo else (0, 191, 255), r, width=1, border_radius=6)
            except Exception:
                pass
            s = get_font('sm').render(etiqueta, True, (10, 14, 26) if activo else (255, 255, 255))
            screen.blit(s, s.get_rect(center=r.center))
            tx += 260

        # Configuración de la pestaña activa
        cfg = next((t for t in TABS if t[0] == estado['stats_tab']), TABS[0])
        _clave, etiqueta, attr, header_metric, min_pj = cfg

        jugadores = _jugadores_con_club(estado)
        # Filtro de alcance: solo mi equipo si así se eligió.
        if estado['stats_scope'] == 'mi_equipo':
            mi = estado.get('mi_equipo')
            plantilla = getattr(mi, 'jugadores', []) if mi else []
            jugadores = [(j, c) for (j, c) in jugadores if j in plantilla]
        if min_pj > 0:
            jugadores = [(j, c) for (j, c) in jugadores if getattr(j, 'partidos_jugados', 0) >= min_pj]
        jugadores = [(j, c) for (j, c) in jugadores if float(getattr(j, attr, 0)) > 0]
        jugadores.sort(key=lambda t: float(getattr(t[0], attr, 0)), reverse=True)

        # Tabla
        panel = pygame.Rect(40, 140, 1200, 510)
        draw_panel(screen, panel)
        draw_text(screen, "#", (panel.x + 20, panel.y + 15), size='sm', color='dorado')
        draw_text(screen, "Jugador", (panel.x + 70, panel.y + 15), size='sm', color='dorado')
        draw_text(screen, "Club", (panel.x + 520, panel.y + 15), size='sm', color='dorado')
        draw_text(screen, "Pos", (panel.x + 760, panel.y + 15), size='sm', color='dorado')
        draw_text(screen, "PJ", (panel.x + 860, panel.y + 15), size='sm', color='dorado')
        draw_text(screen, header_metric, (panel.x + 1050, panel.y + 15), size='sm', color='dorado')
        pygame.draw.line(screen, (0, 191, 255), (panel.x + 20, panel.y + 40), (panel.right - 20, panel.y + 40), 1)

        y = panel.y + 52
        if not jugadores:
            draw_text(screen, "Aún no hay datos. ¡Juega partidos para llenar las tablas!",
                      (panel.x + 30, y + 10), size='md', color='blanco')
        for i, (j, club) in enumerate(jugadores[:13], 1):
            val = getattr(j, attr, 0)
            val_txt = f"{val:.2f}" if attr == 'promedio_nota' else str(int(val))
            col = 'dorado' if i == 1 else 'blanco'
            draw_text(screen, str(i), (panel.x + 20, y), size='sm', color=col)
            draw_text(screen, j.nombre_completo[:32], (panel.x + 70, y), size='sm', color=col)
            draw_text(screen, str(club)[:20], (panel.x + 520, y), size='sm', color='azul')
            draw_text(screen, j.posicion, (panel.x + 760, y), size='sm', color='blanco')
            draw_text(screen, str(getattr(j, 'partidos_jugados', 0)), (panel.x + 860, y), size='sm', color='blanco')
            draw_text(screen, val_txt, (panel.x + 1050, y), size='sm', color='verde')
            y += 35

        btn_volver = pygame.Rect(40, 660, 200, 48)
        draw_button(screen, btn_volver, "VOLVER", btn_volver.collidepoint(mouse_pos))

        if click_pos:
            for clave, r in tab_rects.items():
                if r.collidepoint(click_pos):
                    estado['stats_tab'] = clave
            if btn_volver.collidepoint(click_pos):
                return "league_screen"
        return None
    except Exception as e:
        logger.error(f"Error en stats_screen: {e}")
        return "league_screen"
