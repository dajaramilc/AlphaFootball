# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Bandeja de Ofertas Recibidas (Pygame).

Sección propia para gestionar TODAS las ofertas pendientes por jugadores del usuario
(IA local + clubes del exterior). Cada oferta es un dict {jugador, comprador, monto, exterior?}.
Aceptar traspasa al jugador y cobra; rechazar la descarta.
v3.5.0: lista a la izquierda, ficha del jugador a la derecha y CONTRAOFERTAR (contraofertas.py).
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


def _aceptar(estado: dict, of: dict) -> bool:
    """Acepta una oferta. v3.5.0: la lógica vive en contraofertas.vender."""
    from alpha_football.contraofertas import vender
    return vender(estado, of)


# --- v3.5.0: lista de ofertas + ficha del jugador + contraoferta ────────────────

MAX_VISIBLES = 5
R_VOLVER = pygame.Rect(1064, 24, 200, 48)
R_FICHA = pygame.Rect(672, 110, 592, 440)
R_ACEPTAR = pygame.Rect(672, 566, 170, 48)       # anchos según el texto (CONTRAOFERTAR no entra en 186)
R_RECHAZAR = pygame.Rect(854, 566, 170, 48)
R_CONTRA = pygame.Rect(1036, 566, 228, 48)
R_PANEL = pygame.Rect(688, 276, 560, 264)
R_MONTO = pygame.Rect(712, 336, 360, 48)
R_MAS5 = pygame.Rect(712, 400, 120, 44)
R_MAS10 = pygame.Rect(846, 400, 120, 44)
R_MAS25 = pygame.Rect(980, 400, 120, 44)
R_ENVIAR = pygame.Rect(900, 470, 240, 48)
R_VACIO = pygame.Rect(SCREEN_W // 2 - 280, 250, 560, 120)     # v3.9.0: aviso sin ofertas
_COLOR_RESULTADO = {'aceptada': 'verde', 'analizando': 'azul', 'rechazada': 'rojo', 'invalida': 'rojo'}


def rect_oferta(i: int) -> pygame.Rect:
    """Tarjeta visible i de la lista (0 = primera)."""
    return pygame.Rect(16, 110 + i * 96, 640, 84)


def _dinero(v) -> str:
    try:
        from alpha_football.negociacion import dinero_exacto
        return dinero_exacto(v)
    except Exception:
        return f"${int(v or 0):,}"


def _abrir_contra(estado: dict, of: dict) -> None:
    estado['contra_abierta'] = True
    estado['contra_monto'] = int(int(of.get('monto', 0) or 0) * 1.10)    # arranca en +10%


def _cerrar_contra(estado: dict) -> None:
    estado['contra_abierta'] = False
    estado.pop('contra_monto', None)


def _aceptar_sel(estado: dict, of: dict) -> None:
    jug, comp = of.get('jugador'), of.get('comprador')
    if _aceptar(estado, of):
        estado['oferta_msg'] = (f"Vendiste a {jug.nombre_completo} a {comp.nombre} por {_dinero(of.get('monto', 0))}.", 'verde')
    else:
        estado['ofertas_recibidas'] = [o for o in (estado.get('ofertas_recibidas') or []) if o is not of]
        estado['oferta_msg'] = ("La oferta ya no es válida: el jugador no está en tu plantilla.", 'rojo')
    _cerrar_contra(estado)


def _rechazar_sel(estado: dict, of: dict) -> None:
    estado['ofertas_recibidas'] = [o for o in (estado.get('ofertas_recibidas') or []) if o is not of]
    comp = getattr(of.get('comprador'), 'nombre', 'el club')
    estado['oferta_msg'] = (f"Rechazaste la oferta de {comp}.", 'blanco')
    _cerrar_contra(estado)
    try:  # v4.4.0: rechazar por un jugador que pide salir enoja al jugador y a la directiva
        from alpha_football.salidas import oferta_rechazada
        oferta_rechazada(estado, of.get('jugador'))
    except Exception as e_sal:
        logger.error(f"No se pudo registrar el rechazo: {e_sal}")


def _enviar_contra(estado: dict, of: dict) -> None:
    from alpha_football import contraofertas as CO
    resultado, msg = CO.contraofertar(estado, of, int(estado.get('contra_monto', 0) or 0))
    estado['oferta_msg'] = (msg, _COLOR_RESULTADO.get(resultado, 'blanco'))
    if resultado != 'invalida':
        _cerrar_contra(estado)


def _dibujar_tarjeta(screen, r: pygame.Rect, of: dict, seleccionada: bool, mouse_pos) -> None:
    draw_panel(screen, r)
    if seleccionada or r.collidepoint(mouse_pos):
        pygame.draw.rect(screen, COLORS.get('dorado', (255, 215, 0)) if seleccionada else COLORS.get('azul', (0, 191, 255)),
                         r, width=2, border_radius=8)
    jug, comp, monto = of.get('jugador'), of.get('comprador'), of.get('monto', 0)
    es_ext = of.get('exterior')
    draw_text(screen, "EXTERIOR" if es_ext else "LOCAL", (r.x + 14, r.y + 6), size='sm',
              color='dorado' if es_ext else 'azul')
    if not jug or not comp:
        return
    draw_text(screen, f"{comp.nombre[:24]} ofrece {_dinero(monto)}", (r.x + 120, r.y + 6), size='sm', color='verde')
    _valor_mostrar = getattr(jug, 'valor', 0) or calcular_valor(jug)
    draw_text(screen, f"{jug.nombre_completo[:24]}  ·  {jug.posicion}  ·  MED {jug.overall}  ·  Valor {_dinero(_valor_mostrar)}",
              (r.x + 14, r.y + 32), size='sm', color='blanco')
    c = of.get('contra') or {}
    if c.get('estado') == 'analizando':
        draw_text(screen, f"ANALIZANDO: pediste {_dinero(c.get('pedido', 0))}", (r.x + 14, r.y + 58),
                  size='sm', color='azul')


def _dibujar_panel_contra(screen, estado: dict, of: dict, mouse_pos) -> None:
    pygame.draw.rect(screen, (14, 20, 38), R_PANEL, border_radius=10)
    pygame.draw.rect(screen, COLORS.get('dorado', (255, 215, 0)), R_PANEL, width=2, border_radius=10)
    draw_text(screen, f"CONTRAOFERTA (ofrecen {_dinero(of.get('monto', 0))})", (R_PANEL.x + 24, R_PANEL.y + 12),
              size='sm', color='dorado')
    pygame.draw.rect(screen, (15, 22, 40), R_MONTO, border_radius=6)
    pygame.draw.rect(screen, COLORS.get('azul', (0, 191, 255)), R_MONTO, width=1, border_radius=6)
    s = get_font('md').render(_dinero(estado.get('contra_monto', 0)), True, COLORS.get('verde', (0, 255, 136)))
    screen.blit(s, s.get_rect(center=R_MONTO.center))
    draw_text(screen, "Escribe la cifra", (R_MONTO.right + 16, R_MONTO.y + 14), size='sm', color='azul')
    for r, t in ((R_MAS5, "+5%"), (R_MAS10, "+10%"), (R_MAS25, "+25%")):
        draw_button(screen, r, t, r.collidepoint(mouse_pos))
    draw_text(screen, "Esc cierra", (R_PANEL.x + 24, R_ENVIAR.y + 14), size='sm', color='blanco')
    draw_button(screen, R_ENVIAR, "ENVIAR (Enter)", R_ENVIAR.collidepoint(mouse_pos))


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    try:
        from alpha_football.ui.entrada_monto import editar_valor
        mi_equipo = estado.get('mi_equipo')
        ofertas = estado.setdefault('ofertas_recibidas', [])
        mouse_pos = pygame.mouse.get_pos()
        click_pos = None
        key_events = []
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "menu"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                click_pos = event.pos
            elif event.type == pygame.KEYDOWN:
                key_events.append(event)

        sel = max(0, min(int(estado.get('oferta_sel', 0) or 0), len(ofertas) - 1))
        of = ofertas[sel] if ofertas else None
        if of is None:
            _cerrar_contra(estado)

        # --- Teclado ---
        for ev in key_events:
            if estado.get('contra_abierta') and of is not None:
                if ev.key == pygame.K_ESCAPE:
                    _cerrar_contra(estado)
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    _enviar_contra(estado, of)
                else:
                    estado['contra_monto'] = editar_valor(estado.get('contra_monto', 0), ev)
                continue
            if ev.key == pygame.K_ESCAPE:
                return "league_screen"
            if of is None:
                if ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return "league_screen"
                continue
            if ev.key == pygame.K_DOWN:
                sel = min(len(ofertas) - 1, sel + 1)
            elif ev.key == pygame.K_UP:
                sel = max(0, sel - 1)
            elif ev.key == pygame.K_a:
                _aceptar_sel(estado, of)
            elif ev.key == pygame.K_r:
                _rechazar_sel(estado, of)
            elif ev.key == pygame.K_c and not of.get('contra'):
                _abrir_contra(estado, of)
            ofertas = estado.get('ofertas_recibidas') or []
            sel = max(0, min(sel, len(ofertas) - 1))
            of = ofertas[sel] if ofertas else None

        # --- Mouse ---
        inicio = max(0, sel - MAX_VISIBLES + 1)
        if click_pos:
            if R_VOLVER.collidepoint(click_pos):
                return "league_screen"
            if of is not None and estado.get('contra_abierta') and R_PANEL.collidepoint(click_pos):
                base = int(of.get('monto', 0) or 0)
                for r, pct in ((R_MAS5, 0.05), (R_MAS10, 0.10), (R_MAS25, 0.25)):
                    if r.collidepoint(click_pos):
                        estado['contra_monto'] = int(estado.get('contra_monto', 0) or 0) + int(base * pct)
                if R_ENVIAR.collidepoint(click_pos):
                    _enviar_contra(estado, of)
            elif of is not None and R_ACEPTAR.collidepoint(click_pos):
                _aceptar_sel(estado, of)
            elif of is not None and R_RECHAZAR.collidepoint(click_pos):
                _rechazar_sel(estado, of)
            elif of is not None and R_CONTRA.collidepoint(click_pos):
                if not of.get('contra'):
                    _abrir_contra(estado, of)
            else:
                for i in range(min(MAX_VISIBLES, len(ofertas) - inicio)):
                    if rect_oferta(i).collidepoint(click_pos) and inicio + i != sel:
                        sel = inicio + i
                        _cerrar_contra(estado)
            ofertas = estado.get('ofertas_recibidas') or []
            sel = max(0, min(sel, len(ofertas) - 1))
            of = ofertas[sel] if ofertas else None
            inicio = max(0, sel - MAX_VISIBLES + 1)
        estado['oferta_sel'] = sel

        # --- Dibujo ---
        draw_gradient_bg(screen)
        draw_text(screen, "OFERTAS RECIBIDAS", (40, 25), size='xl', color='dorado')
        draw_text(screen, f"Pendientes: {len(ofertas)}  ·  Presupuesto: {_dinero(getattr(mi_equipo, 'balance', 0))}"
                          f"  ·  ↑/↓ elegir · A aceptar · R rechazar · C contraofertar · Esc volver",
                  (40, 70), size='sm', color='azul')
        draw_button(screen, R_VOLVER, "VOLVER", R_VOLVER.collidepoint(mouse_pos))
        msg = estado.get('oferta_msg')
        if msg:
            draw_text(screen, str(msg[0])[:110], (16, 660), size='sm', color=msg[1])

        if of is None:
            draw_panel(screen, R_VACIO)
            draw_text(screen, "No hay ofertas pendientes por tus jugadores.",
                      (SCREEN_W // 2 - 250, 300), size='md', color='blanco')
            return None

        for i, o in enumerate(ofertas[inicio:inicio + MAX_VISIBLES]):
            _dibujar_tarjeta(screen, rect_oferta(i), o, inicio + i == sel, mouse_pos)
        if len(ofertas) > MAX_VISIBLES:
            draw_text(screen, f"{inicio + 1}-{min(len(ofertas), inicio + MAX_VISIBLES)} de {len(ofertas)}",
                      (16, 594), size='sm', color='azul')

        try:
            from alpha_football.ui.ficha_jugador import dibujar_ficha
            dibujar_ficha(screen, R_FICHA, of['jugador'], f"Oferta de {getattr(of.get('comprador'), 'nombre', '?')}"[:34])
        except Exception as e_ficha:
            logger.error(f"No se pudo dibujar la ficha de la oferta: {e_ficha}")
        draw_button(screen, R_ACEPTAR, "ACEPTAR", R_ACEPTAR.collidepoint(mouse_pos))
        draw_button(screen, R_RECHAZAR, "RECHAZAR", R_RECHAZAR.collidepoint(mouse_pos))
        if of.get('contra'):
            draw_button(screen, R_CONTRA, "EN ANÁLISIS", False)
        else:
            draw_button(screen, R_CONTRA, "CONTRAOFERTAR", R_CONTRA.collidepoint(mouse_pos))
        if estado.get('contra_abierta'):
            _dibujar_panel_contra(screen, estado, of, mouse_pos)
        return None
    except Exception as e:
        logger.error(f"Error en ofertas_screen: {e}", exc_info=True)
        return "league_screen"
