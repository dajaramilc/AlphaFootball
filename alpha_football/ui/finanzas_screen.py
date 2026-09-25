# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Finanzas (Pygame)
v2.9.0: saldo, ingresos y gastos de la temporada (taquilla, patrocinio, salarios,
fichajes, ventas, premios), proyección al cierre, masa salarial, contratos que vencen
y aviso de quiebra.
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

from alpha_football import finanzas as F

logger = logging.getLogger(__name__)

R_SALDO = pygame.Rect(16, 76, 400, 300)
R_LIBRO = pygame.Rect(432, 76, 832, 300)
R_CONTR = pygame.Rect(16, 392, 1248, 304)      # v3.6.0: termina en y=696 (barra de atajos)


def _volver() -> pygame.Rect:
    return pygame.Rect(1116, 12, 148, 40)


def _m(v) -> str:
    v = int(v or 0)
    signo = "−" if v < 0 else ""
    v = abs(v)
    return f"{signo}${v / 1_000_000:.1f}M" if v >= 1_000_000 else f"{signo}${v / 1000:.0f}K"


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """Retorna 'league_screen' al salir o None para seguir aquí."""
    try:
        mi, liga = estado.get('mi_equipo'), estado.get('liga')
        if mi is None or liga is None:
            return 'league_screen'
        mouse_pos = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return 'menu'
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                return 'league_screen'
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and _volver().collidepoint(ev.pos):
                return 'league_screen'

        lib = F.libro(estado)
        n = max(1, int(liga.num_jornadas or 10))
        restantes = max(0, n - sum(1 for p in liga.calendario if p.jugado and mi.id in (p.local_id, p.visitante_id)))
        medio = F.presupuesto_medio(liga)
        masa = F.masa_salarial(mi)
        por_jornada = int(medio * F.PATROCINIO_FRAC / n) + int(medio * F.TAQUILLA_FRAC / n) - masa // n
        proyeccion = mi.balance + por_jornada * restantes
        dc = estado.get('datos_carrera') or {}

        draw_gradient_bg(screen)
        draw_text(screen, "FINANZAS", (16, 12), size='lg', color='dorado')
        draw_text(screen, f"{mi.nombre}  ·  {liga.nombre}  ·  Temporada {estado.get('temporada', 1)}",
                  (16, 48), size='sm', color='verde')
        draw_button(screen, _volver(), "VOLVER", _volver().collidepoint(mouse_pos))

        # --- Saldo ---
        draw_panel(screen, R_SALDO)
        x, y = R_SALDO.x + 20, R_SALDO.y + 14
        draw_text(screen, "SALDO", (x, y), size='sm', color='azul')
        draw_text(screen, _m(mi.balance), (x, y + 26), size='xl', color='verde' if mi.balance >= 0 else 'rojo')
        draw_text(screen, f"Masa salarial {_m(masa)} / año", (x, y + 96), size='sm', color='blanco')
        draw_text(screen, f"Por jornada (promedio): {'+' if por_jornada >= 0 else ''}{_m(por_jornada)}",
                  (x, y + 124), size='sm', color='verde' if por_jornada >= 0 else 'rojo')
        draw_text(screen, f"Proyección al cierre ({restantes} jornadas): {_m(proyeccion)}",
                  (x, y + 152), size='sm', color='verde' if proyeccion >= 0 else 'rojo')
        rojo = int(dc.get('jornadas_en_rojo', 0) or 0)
        if mi.balance < 0:
            draw_text(screen, f"¡EN ROJO! {rojo}/{F.JORNADAS_ROJO_VENTA} jornadas.", (x, y + 196), size='sm', color='rojo')
            draw_text(screen, "Al llegar a 3 venden a tu mejor jugador.", (x, y + 220), size='sm', color='rojo')
            draw_text(screen, "Cerrar la temporada así = despido.", (x, y + 244), size='sm', color='rojo')
        else:
            draw_text(screen, "Saldo negativo: no puedes fichar.", (x, y + 196), size='sm', color='azul')
            draw_text(screen, "3 jornadas en rojo = venta forzada.", (x, y + 220), size='sm', color='azul')
            draw_text(screen, "Cerrar la temporada en rojo = despido.", (x, y + 244), size='sm', color='azul')

        # --- Libro de la temporada ---
        draw_panel(screen, R_LIBRO)
        lx, ly = R_LIBRO.x + 20, R_LIBRO.y + 14
        draw_text(screen, "INGRESOS Y GASTOS DE LA TEMPORADA", (lx, ly), size='sm', color='azul')
        ingresos = [("Taquilla", lib['taquilla']), ("Patrocinio", lib['patrocinio']),
                    ("Ventas", lib['ventas']), ("Premios", lib['premios']),
                    ("Directiva", lib.get('directiva', 0))]      # v3.2.0: espaldarazo
        gastos = [("Salarios", lib['salarios']), ("Fichajes", lib['fichajes'])]
        for i, (t, v) in enumerate(ingresos):      # v3.2.0: paso 27 para que quepan 5 líneas
            draw_text(screen, t, (lx, ly + 34 + i * 27), size='md', color='blanco')
            draw_text(screen, "+" + _m(v), (lx + 180, ly + 34 + i * 27), size='md', color='verde')
        for i, (t, v) in enumerate(gastos):
            draw_text(screen, t, (lx + 420, ly + 34 + i * 30), size='md', color='blanco')
            draw_text(screen, "−" + _m(v), (lx + 600, ly + 34 + i * 30), size='md', color='rojo')
        neto = sum(v for _t, v in ingresos) - sum(v for _t, v in gastos)
        draw_text(screen, f"NETO DE LA TEMPORADA: {'+' if neto >= 0 else ''}{_m(neto)}", (lx, ly + 170),
                  size='lg', color='verde' if neto >= 0 else 'rojo')
        ant = dc.get('finanzas_anterior')
        if ant:
            neto_ant = sum(ant.get(k, 0) for k in ('taquilla', 'patrocinio', 'ventas', 'premios', 'directiva')) \
                       - sum(ant.get(k, 0) for k in ('salarios', 'fichajes'))
            draw_text(screen, f"Temporada {ant.get('temporada')}: neto {'+' if neto_ant >= 0 else ''}{_m(neto_ant)}",
                      (lx, ly + 222), size='sm', color='azul')
        draw_text(screen, "Taquilla solo de local (más si ganas) · patrocinio fijo por jornada · premios al cierre",
                  (lx, ly + 250), size='sm', color='azul')

        # --- Contratos ---
        draw_panel(screen, R_CONTR)
        draw_text(screen, "CONTRATOS QUE VENCEN (1 año o menos) — se van libres al cerrar la temporada si no renuevas",
                  (R_CONTR.x + 20, R_CONTR.y + 12), size='sm', color='dorado')
        vencen = sorted([j for j in mi.jugadores if int(getattr(j, 'contrato_anios', 2) or 2) <= 1],
                        key=lambda j: -j.overall)
        if not vencen:
            draw_text(screen, "Ninguno. (Renovaciones: FINANZAS > CONTRATOS o la ficha en PLANTILLA)",
                      (R_CONTR.x + 20, R_CONTR.y + 46), size='sm', color='blanco')
        for i, j in enumerate(vencen[:9]):
            draw_text(screen, f"{j.posicion}  {j.nombre_completo[:28]}  ·  {j.edad} años  ·  media {j.overall}  ·  "
                              f"salario {_m(j.salario)}/año  ·  cláusula {_m(j.clausula)}",
                      (R_CONTR.x + 20, R_CONTR.y + 44 + i * 28), size='sm', color='blanco')
        return None
    except Exception as e:
        logger.error(f"Error en finanzas_screen: {e}", exc_info=True)
        return 'league_screen'
