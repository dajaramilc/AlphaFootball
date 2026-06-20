# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Bandeja de Ofertas Recibidas (Pygame).

Sección propia para gestionar TODAS las ofertas pendientes por jugadores del usuario
(IA local + clubes del exterior). Cada oferta es un dict {jugador, comprador, monto, exterior?}.
Aceptar traspasa al jugador y cobra; rechazar la descarta.
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

# v0.8.x: import tolerante de `calcular_valor` para mostrar el valor real cuando el
# campo guardado del jugador sigue en 0 (p.ej. un jugador que nunca jugó).
try:
    from alpha_football.market import calcular_valor
except Exception:
    def calcular_valor(_jugador):
        """Fallback local si `market` no se puede importar."""
        try:
            return max(50_000, int(_jugador.overall) * 1000)
        except Exception:
            return 50_000


def _aceptar(estado: dict, of: dict) -> None:
    """Acepta una oferta: traspasa el jugador, cobra y trae un reemplazo SOLO si la plantilla cae por debajo de 15."""
    mi_equipo = estado.get('mi_equipo')
    jug = of.get('jugador'); comp = of.get('comprador'); monto = of.get('monto', 0)
    if not mi_equipo or not jug or not comp:
        return
    try:
        mi_equipo.balance += monto
        if jug in mi_equipo.jugadores:
            mi_equipo.jugadores.remove(jug)
        comp.jugadores.append(jug)
        try:
            comp.balance = max(0, comp.balance - monto)
        except Exception:
            pass
        # v0.8.2: solo generar suplente si la plantilla cae por debajo de 15.
        # Antes siempre se rellenaba; ahora vender deja la plantilla con menos jugadores
        # (es una decisión del manager).
        try:
            if len(mi_equipo.jugadores) < 15:
                from alpha_football.ui.market_screen import generar_reemplazo_resiliente
                suplente = generar_reemplazo_resiliente(jug.posicion, getattr(mi_equipo, 'estrellas', 3.0))
                mi_equipo.jugadores.append(suplente)
            estado.setdefault('transfer_log', []).append(
                f"Venta: {jug.nombre_completo} -> {comp.nombre} por ${monto:,}")
        except Exception as e_rep:
            logger.error(f"No se pudo generar reemplazo: {e_rep}")
    except Exception as e:
        logger.error(f"Error al aceptar oferta: {e}")


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    try:
        mi_equipo = estado.get('mi_equipo')
        ofertas = estado.setdefault('ofertas_recibidas', [])

        mouse_pos = pygame.mouse.get_pos()
        click_pos = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "menu"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                click_pos = event.pos

        draw_gradient_bg(screen)
        draw_text(screen, "OFERTAS RECIBIDAS", (40, 25), size='xl', color='dorado')
        draw_text(screen, f"Pendientes: {len(ofertas)}  ·  Presupuesto: ${getattr(mi_equipo, 'balance', 0):,}",
                  (40, 70), size='sm', color='azul')

        btn_volver = pygame.Rect(40, 640, 200, 50)
        draw_button(screen, btn_volver, "VOLVER", btn_volver.collidepoint(mouse_pos))

        if not ofertas:
            draw_panel(screen, pygame.Rect(SCREEN_W // 2 - 280, 250, 560, 120))
            draw_text(screen, "No hay ofertas pendientes por tus jugadores.",
                      (SCREEN_W // 2 - 250, 300), size='md', color='blanco')
            if click_pos and btn_volver.collidepoint(click_pos):
                return "league_screen"
            return None

        # Listar ofertas como tarjetas con ACEPTAR / RECHAZAR
        y = 120
        acciones = []  # (rect_acc, rect_rej, indice)
        for i, of in enumerate(ofertas[:6]):
            jug = of.get('jugador'); comp = of.get('comprador'); monto = of.get('monto', 0)
            card = pygame.Rect(40, y, 1200, 78)
            draw_panel(screen, card)
            es_ext = of.get('exterior')
            etiqueta = "EXTERIOR" if es_ext else "LOCAL"
            col_et = 'dorado' if es_ext else 'azul'
            draw_text(screen, etiqueta, (card.x + 15, card.y + 8), size='sm', color=col_et)
            if jug and comp:
                draw_text(screen, f"{comp.nombre[:26]} ofrece ${monto:,}", (card.x + 15, card.y + 32), size='md', color='verde')
                # v0.8.x: si el `valor` guardado es 0, mostramos el calculado on-the-fly
                # para no imprimir "Valor $0" junto a un monto de $200M.
                _valor_mostrar = getattr(jug, 'valor', 0) or calcular_valor(jug)
                draw_text(screen, f"por {jug.nombre_completo}  ·  {jug.posicion}  ·  OVR {jug.overall}  ·  Valor ${_valor_mostrar:,}",
                          (card.x + 15, card.y + 54), size='sm', color='blanco')
            rect_acc = pygame.Rect(card.right - 320, card.y + 20, 140, 40)
            rect_rej = pygame.Rect(card.right - 165, card.y + 20, 140, 40)
            draw_button(screen, rect_acc, "ACEPTAR", rect_acc.collidepoint(mouse_pos))
            draw_button(screen, rect_rej, "RECHAZAR", rect_rej.collidepoint(mouse_pos))
            acciones.append((rect_acc, rect_rej, i))
            y += 88

        if click_pos:
            if btn_volver.collidepoint(click_pos):
                return "league_screen"
            for rect_acc, rect_rej, idx in acciones:
                if rect_acc.collidepoint(click_pos):
                    if 0 <= idx < len(ofertas):
                        _aceptar(estado, ofertas.pop(idx))
                    break
                elif rect_rej.collidepoint(click_pos):
                    if 0 <= idx < len(ofertas):
                        ofertas.pop(idx)
                    break
        return None
    except Exception as e:
        logger.error(f"Error en ofertas_screen: {e}")
        return "league_screen"
