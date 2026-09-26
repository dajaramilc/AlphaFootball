# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Aviso de mercado en INICIO (v4.4.0)
Cartel modal al abrirse (J1 y J n−2) y cerrarse (J4) el mercado + franja con la cuenta regresiva
mientras está abierto. Se engancha en league_screen.render (manejar + dibujar).
"""
from __future__ import annotations

import logging
from typing import Optional

import pygame

logger = logging.getLogger(__name__)

try:
    from alpha_football.ui.theme import COLORS, get_font, draw_panel, draw_button
except Exception as e_imp:  # pragma: no cover - fallback como el resto de las pantallas
    logger.warning(f"aviso_mercado sin theme ({e_imp})")
    COLORS = {'verde': (0, 255, 136), 'rojo': (255, 68, 68), 'dorado': (255, 215, 0), 'blanco': (255, 255, 255)}
    def get_font(size): return pygame.font.Font(None, 24)
    def draw_panel(screen, rect): pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=8)
    def draw_button(screen, rect, text, hover): pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=6); return rect

SCREEN_W, SCREEN_H = 1280, 720
R_CARTEL = pygame.Rect(SCREEN_W // 2 - 280, 220, 560, 260)
R_IR = pygame.Rect(R_CARTEL.x + 40, R_CARTEL.bottom - 76, 230, 52)
R_CONTINUAR = pygame.Rect(R_CARTEL.right - 270, R_CARTEL.bottom - 76, 230, 52)
FRANJA_Y, FRANJA_H, MARGEN_DER = 80, 22, 16


def eventos_ventana(num_jornadas: int) -> dict:
    """{jornada: 'abre'|'cierra'}: abre el primer día de cada ventana y cierra el día siguiente
    al último (la de cierre de temporada no tiene cartel de cierre)."""
    from alpha_football.market import ventanas_mercado
    n = int(num_jornadas or 22)
    ev = {}
    for a, b, _nombre in ventanas_mercado(n):
        ev[a] = 'abre'
        if b < n:
            ev[b + 1] = 'cierra'
    return ev


def _hasta(jornada: int, n: int) -> int:
    """Última jornada de la ventana abierta en `jornada`."""
    from alpha_football.market import ventana_actual
    v = ventana_actual(jornada, n)
    return v[1] if v else n


def _reabre(jornada: int, n: int) -> str:
    from alpha_football.market import proxima_apertura
    p = proxima_apertura(jornada, n)
    return f"Reabre en la jornada {p}." if p > jornada else "Reabre al empezar la próxima temporada."


def _liga(estado):
    return estado.get('liga')


def evento_pendiente(estado: dict) -> Optional[tuple]:
    liga = _liga(estado)
    if liga is None:
        return None
    j = int(getattr(liga, 'jornada_actual', 1) or 1)
    tipo = eventos_ventana(getattr(liga, 'num_jornadas', 22)).get(j)
    if not tipo:
        return None
    clave = [int(estado.get('temporada', 1) or 1), j]
    if (estado.get('datos_carrera') or {}).get('aviso_mercado_visto') == clave:
        return None
    return tipo, j


def _abrir(estado: dict, tipo: str, jornada: int) -> None:
    dc = estado.setdefault('datos_carrera', {})
    dc['aviso_mercado_visto'] = [int(estado.get('temporada', 1) or 1), jornada]
    # con el mercado cerrado no hay a qué ir: el foco arranca en CONTINUAR
    estado['aviso_mercado_activo'] = {'tipo': tipo, 'jornada': jornada, 'foco': 0 if tipo == 'abre' else 1}
    try:
        from alpha_football import correo as C
        n = int(getattr(_liga(estado), 'num_jornadas', 22) or 22)
        if tipo == 'abre':
            C.enviar(estado, 'club', "Se abrió el mercado de pases",
                     f"Hasta la jornada {_hasta(jornada, n)}: fichajes, ofertas y cláusulas.",
                     C.accion('negociaciones', "IR A NEGOCIACIONES"))
        else:
            C.enviar(estado, 'club', "Se cerró el mercado de pases", _reabre(jornada, n))
    except Exception as e:
        logger.error(f"No se pudo enviar el correo del mercado: {e}")


def manejar(estado: dict, key_events: list, click_pos, bloqueado: bool = False) -> tuple:
    """(destino, key_events, click_pos). Con el cartel abierto consume todo."""
    act = estado.get('aviso_mercado_activo')
    if not act:
        if bloqueado or estado.get('ayuda_abierta'):
            return None, key_events, click_pos
        ev = evento_pendiente(estado)
        if ev is None:
            return None, key_events, click_pos
        _abrir(estado, *ev)
        return None, [], None
    for e in key_events or []:
        if e.key in (pygame.K_LEFT, pygame.K_RIGHT):
            act['foco'] = 1 - int(act.get('foco', 0))
        elif e.key == pygame.K_ESCAPE:
            estado['aviso_mercado_activo'] = None
            return None, [], None
        elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            destino = 'negociaciones' if int(act.get('foco', 0)) == 0 else None
            estado['aviso_mercado_activo'] = None
            return destino, [], None
    if click_pos:
        if R_IR.collidepoint(click_pos):
            estado['aviso_mercado_activo'] = None
            return 'negociaciones', [], None
        if R_CONTINUAR.collidepoint(click_pos):
            estado['aviso_mercado_activo'] = None
    return None, [], None


def _ancho_cabecera(estado: dict) -> int:
    """Ancho de la cabecera del hub (texto 'sm' en (16, 82)), armada igual que league_screen."""
    try:
        liga, mi = _liga(estado), estado.get('mi_equipo')
        from alpha_football.paises import nombre_liga
        cab = (f"{nombre_liga(liga.tipo, getattr(liga, 'division', 1) or 1).upper()[:32]}  ·  {mi.nombre[:22]}  ·  "
               f"{'2ª' if getattr(liga, 'division', 1) == 2 else '1ª'} División  ·  T{estado.get('temporada', 1)}  ·  "
               f"Jornada {getattr(liga, 'jornada_actual', 1)}/{getattr(liga, 'num_jornadas', 14)}  ·  "
               f"${getattr(mi, 'balance', 0) / 1_000_000:.1f}M")
        return get_font('sm').size(cab)[0]
    except Exception as e:
        logger.debug(f"No se pudo medir la cabecera del hub: {e}")
        return 965                                   # peor caso medido


def _texto_franja(estado: dict, corto: bool = False) -> Optional[tuple]:
    liga = _liga(estado)
    if liga is None:
        return None
    from alpha_football.market import ventana_mercado_abierta
    j = int(getattr(liga, 'jornada_actual', 1) or 1)
    n = int(getattr(liga, 'num_jornadas', 22) or 22)
    if not ventana_mercado_abierta(j, n):
        return None
    # la última jornada ya jugada = temporada terminada: no hay cuenta regresiva que mostrar
    if j >= n and all(getattr(p, 'jugado', False) for p in getattr(liga, 'calendario', []) or []
                      if getattr(p, 'jornada', 0) == j):
        return None
    fin = _hasta(j, n)
    quedan = fin - j
    if quedan <= 0:
        return ("MERCADO · ÚLTIMA J." if corto else "MERCADO ABIERTO · ÚLTIMA JORNADA"), 'dorado'
    return (f"MERCADO ABIERTO · {quedan + 1} J." if corto
            else f"MERCADO ABIERTO · cierra en {quedan + 1} jornadas"), 'verde'


def _franja(estado: dict, ancho_cabecera: Optional[int] = None) -> tuple:
    """(texto, color, rect) a la derecha de la cabecera, en su misma línea; texto corto si no entra."""
    libre_desde = 16 + (ancho_cabecera if ancho_cabecera is not None else _ancho_cabecera(estado)) + 12
    for corto in (False, True):
        t = _texto_franja(estado, corto)
        if not t:
            return None, None, None
        w = get_font('sm').size(t[0])[0] + 24
        r = pygame.Rect(SCREEN_W - MARGEN_DER - w, FRANJA_Y, w, FRANJA_H)
        if r.left >= libre_desde or corto:
            return t[0], t[1], r
    return None, None, None


def rect_franja(estado: dict, ancho_cabecera: Optional[int] = None) -> Optional[pygame.Rect]:
    return _franja(estado, ancho_cabecera)[2]


def dibujar(screen: pygame.Surface, estado: dict, mouse_pos) -> None:
    try:
        texto, col, r = _franja(estado)
        t = (texto, col) if texto else None
        if t and r:
            color = COLORS.get(t[1], (0, 255, 136))
            pygame.draw.rect(screen, (10, 14, 26), r, border_radius=6)
            pygame.draw.rect(screen, color, r, width=2, border_radius=6)
            surf = get_font('sm').render(t[0], True, color)
            screen.blit(surf, surf.get_rect(center=r.center))
        act = estado.get('aviso_mercado_activo')
        if not act:
            return
        velo = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        velo.fill((0, 0, 0, 170))
        screen.blit(velo, (0, 0))
        draw_panel(screen, R_CARTEL)
        abre = act.get('tipo') == 'abre'
        color = COLORS.get('verde' if abre else 'rojo', (0, 255, 136))
        pygame.draw.rect(screen, color, R_CARTEL, width=3, border_radius=8)
        s = get_font('xl').render("MERCADO ABIERTO" if abre else "MERCADO CERRADO", True, color)
        screen.blit(s, s.get_rect(center=(R_CARTEL.centerx, R_CARTEL.y + 50)))
        n = int(getattr(_liga(estado), 'num_jornadas', 22) or 22)
        if abre:
            linea = f"Hasta la jornada {_hasta(int(act.get('jornada', 1)), n)}: fichajes, ofertas y cláusulas."
        else:
            linea = _reabre(int(act.get('jornada', 1)), n)
        s2 = get_font('md').render(linea, True, COLORS.get('blanco', (255, 255, 255)))
        screen.blit(s2, s2.get_rect(center=(R_CARTEL.centerx, R_CARTEL.y + 104)))
        salen = sum(1 for j in getattr(estado.get('mi_equipo'), 'jugadores', []) or [] if getattr(j, 'pide_salir', False))
        if abre and salen:
            s3 = get_font('sm').render(f"{salen} jugador{'es piden' if salen != 1 else ' pide'} salir.", True,
                                       COLORS.get('dorado', (255, 215, 0)))
            screen.blit(s3, s3.get_rect(center=(R_CARTEL.centerx, R_CARTEL.y + 138)))
        foco = int(act.get('foco', 0))
        for i, (rb, txt) in enumerate(((R_IR, "IR AL MERCADO"), (R_CONTINUAR, "CONTINUAR"))):
            draw_button(screen, rb, txt, rb.collidepoint(mouse_pos) or foco == i)
            if foco == i:
                pygame.draw.rect(screen, COLORS.get('dorado', (255, 215, 0)), rb, width=2, border_radius=6)
    except Exception as e:
        logger.error(f"Error al dibujar el aviso de mercado: {e}")
