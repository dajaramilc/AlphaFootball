# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Patrocinios (Pygame)
v4.9.0: los 3 espacios (camiseta, manga, estadio) con su contrato, objetivo y años; reputación
comercial; y las ofertas del espacio elegido: firmar (con o sin prima), negociar o rechazar.
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

from alpha_football import patrocinios as P
from alpha_football.ui.objetivos_screen import barra

logger = logging.getLogger(__name__)

ESPACIOS = [esp for esp, _w in P.ESPACIOS]
R_OFERTAS = pygame.Rect(16, 392, 1248, 304)        # termina en y=696 (barra de atajos)
OFERTA_Y0, OFERTA_H = 430, 86
PERFIL_TXT = {'conservadora': "Conservadora", 'equilibrada': "Equilibrada", 'ambiciosa': "Ambiciosa"}


def _rects() -> dict:
    return {'volver': pygame.Rect(1116, 12, 148, 40), 'reputacion': pygame.Rect(16, 54, 760, 24)}


def _rect_espacio(i: int) -> pygame.Rect:
    return pygame.Rect(16 + i * 421, 110, 405, 270)


def _rect_rescindir(i: int) -> pygame.Rect:
    r = _rect_espacio(i)
    return pygame.Rect(r.x + 16, r.bottom - 48, 170, 36)


def _rects_oferta(k: int) -> dict:
    y = OFERTA_Y0 + k * OFERTA_H
    return {'fila': pygame.Rect(24, y, R_OFERTAS.width - 16, OFERTA_H - 6),
            'firmar': pygame.Rect(770, y + 20, 104, 40), 'prima': pygame.Rect(882, y + 20, 104, 40),
            'n1': pygame.Rect(994, y + 20, 80, 40), 'n2': pygame.Rect(1082, y + 20, 80, 40),
            'rechazar': pygame.Rect(1170, y + 20, 86, 40)}


def _corto(texto: str, ancho: int, size: str = 'sm') -> str:
    try:
        f = get_font(size)
        if f.size(texto)[0] <= ancho:
            return texto
        while texto and f.size(texto + "…")[0] > ancho:
            texto = texto[:-1]
        return texto + "…"
    except Exception:
        return texto[:48]


def _salir(estado: dict) -> str:
    estado.pop('patro_msg', None)
    estado.pop('patro_confirma', None)
    return 'league_screen'


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """Retorna 'league_screen' al salir o None para seguir aquí."""
    try:
        p = P.datos(estado)
        esp_i = max(0, min(int(estado.get('patro_esp', 0) or 0), 2))
        of_i = int(estado.get('patro_of', 0) or 0)
        confirma = estado.get('patro_confirma')
        rects = _rects()
        mouse_pos = pygame.mouse.get_pos()
        ofertas = P.ofertas_de(estado, ESPACIOS[esp_i])
        accion = None                                    # ('firmar'|'prima'|'n1'|'n2'|'rechazar', k) o ('rescindir', i)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return 'menu'
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if rects['volver'].collidepoint(ev.pos):
                    return _salir(estado)
                hecho = False
                for i in range(3):
                    if p['contratos'].get(ESPACIOS[i]) and _rect_rescindir(i).collidepoint(ev.pos):
                        esp_i, accion, hecho = i, ('rescindir', i), True
                    elif _rect_espacio(i).collidepoint(ev.pos) and not hecho:
                        if i != esp_i:
                            of_i = 0
                        esp_i, confirma, hecho = i, None, True
                if not hecho:
                    for k in range(len(ofertas)):
                        ro = _rects_oferta(k)
                        for nombre in ('firmar', 'prima', 'n1', 'n2', 'rechazar'):
                            if ro[nombre].collidepoint(ev.pos):
                                of_i, accion = k, (nombre, k)
                        if accion is None and ro['fila'].collidepoint(ev.pos):
                            of_i = k
            elif ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    if confirma is None:
                        return _salir(estado)
                    confirma = None
                    estado.pop('patro_msg', None)
                elif ev.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    esp_i, of_i, confirma = (esp_i + (1 if ev.key == pygame.K_RIGHT else -1)) % 3, 0, None
                elif ev.key == pygame.K_UP:
                    of_i -= 1
                elif ev.key == pygame.K_DOWN:
                    of_i += 1
                elif ev.key == pygame.K_x or (ev.key == pygame.K_RETURN and confirma is not None):
                    accion = ('rescindir', esp_i)
                elif ev.key in (pygame.K_f, pygame.K_p, pygame.K_1, pygame.K_2, pygame.K_r):
                    accion = ({pygame.K_f: 'firmar', pygame.K_p: 'prima', pygame.K_1: 'n1', pygame.K_2: 'n2',
                               pygame.K_r: 'rechazar'}[ev.key], of_i)

        espacio = ESPACIOS[esp_i]
        ofertas = P.ofertas_de(estado, espacio)
        of_i = max(0, min(of_i, len(ofertas) - 1))
        if accion is not None:
            tipo, idx = accion
            if tipo == 'rescindir':
                if p['contratos'].get(espacio) is None:
                    confirma = None
                elif confirma == espacio:
                    _ok, estado['patro_msg'] = P.rescindir(estado, espacio)
                    confirma = None
                else:
                    confirma = espacio
                    estado['patro_msg'] = (f"¿Rescindir con {p['contratos'][espacio]['marca']}? Multa de "
                                           f"{P._m(P.multa_rescision(estado, espacio))} y −8 de reputación. "
                                           "Pulsa RESCINDIR otra vez (o Enter) · ESC cancela.")
            elif ofertas and 0 <= idx < len(ofertas):
                o = ofertas[idx]
                confirma = None
                if tipo == 'firmar':
                    _ok, estado['patro_msg'] = P.firmar(estado, o['id'])
                elif tipo == 'prima':
                    _ok, estado['patro_msg'] = P.firmar(estado, o['id'], con_prima=True)
                elif tipo in ('n1', 'n2'):
                    _ok, estado['patro_msg'] = P.negociar(estado, o['id'], 1 if tipo == 'n1' else 2)
                else:
                    P.rechazar(estado, o['id'])
                    estado['patro_msg'] = f"Rechazaste la oferta de {o['marca']}."
            ofertas = P.ofertas_de(estado, espacio)
            of_i = max(0, min(of_i, len(ofertas) - 1))
        estado['patro_esp'], estado['patro_of'], estado['patro_confirma'] = esp_i, of_i, confirma

        # --- dibujo ---
        draw_gradient_bg(screen)
        draw_text(screen, "PATROCINIOS", (16, 12), size='lg', color='dorado')
        draw_button(screen, rects['volver'], "VOLVER", rects['volver'].collidepoint(mouse_pos))
        rep = int(p.get('reputacion', 50))
        draw_text(screen, f"Reputación comercial {rep}/100", (16, 56), size='sm', color='azul')
        barra(screen, pygame.Rect(270, 62, 200, 12), rep / 100, 'verde' if rep >= 50 else 'dorado' if rep >= 15 else 'rojo')
        draw_text(screen, f"Fijo anual: {P._m(P.ingreso_anual(estado))}  ·  Por jornada: {P._m(P.cobro_jornada(estado))}",
                  (490, 56), size='sm', color='blanco')
        if estado.get('patro_msg'):
            draw_text(screen, _corto(str(estado['patro_msg']), 1240), (16, 84), size='sm',
                      color='rojo' if confirma is not None else 'verde')

        n = max(1, int(getattr(estado.get('liga'), 'num_jornadas', 22) or 22))
        for i, esp in enumerate(ESPACIOS):
            r = _rect_espacio(i)
            draw_panel(screen, r)
            if i == esp_i:
                pygame.draw.rect(screen, COLORS['dorado'], r, width=2, border_radius=8)
            x, y = r.x + 16, r.y + 12
            n_of = len(P.ofertas_de(estado, esp))
            draw_text(screen, P.NOMBRE_ESPACIO[esp].upper() + (f"  ·  {n_of} oferta{'s' if n_of != 1 else ''}" if n_of else ""),
                      (x, y), size='sm', color='dorado')
            c = p['contratos'].get(esp)
            if not c:
                draw_text(screen, "SIN PATROCINADOR", (x, y + 34), size='md', color='rojo')
                draw_text(screen, f"Dejas de cobrar {P._m(P.valor_referencia(estado, esp) // n)} por jornada",
                          (x, y + 74), size='sm', color='blanco')
                draw_text(screen, "Las ofertas llegan en las ventanas de pases." if not n_of else "Elige una oferta abajo.",
                          (x, y + 100), size='sm', color='azul')
                continue
            draw_text(screen, _corto(c['marca'], r.width - 32, 'lg'), (x, y + 28), size='lg', color='blanco')
            draw_text(screen, f"{c['rubro'].capitalize()}  ·  {PERFIL_TXT.get(c['perfil'], c['perfil'])}", (x, y + 68), size='sm', color='azul')
            draw_text(screen, f"Fijo {P._m(c['fijo'])}/año  ·  Bono {P._m(c['bono'])}", (x, y + 94), size='sm', color='verde')
            draw_text(screen, _corto(c['objetivo']['texto'], r.width - 32), (x, y + 122), size='sm', color='blanco')
            frac = P.progreso(estado, c)
            barra(screen, pygame.Rect(x, y + 150, r.width - 32, 12), frac, 'verde' if frac >= 1.0 else 'dorado')
            anios = int(c.get('anios', 1))
            draw_text(screen, f"Le queda{'n' if anios != 1 else ''} {anios} año{'s' if anios != 1 else ''}",
                      (x, y + 172), size='sm', color='rojo' if anios <= 1 else 'blanco')
            rr = _rect_rescindir(i)
            draw_button(screen, rr, "CONFIRMAR" if confirma == esp else "RESCINDIR",
                        rr.collidepoint(mouse_pos) or confirma == esp)

        draw_panel(screen, R_OFERTAS)
        draw_text(screen, f"OFERTAS PARA {P.NOMBRE_ESPACIO[espacio].upper()}", (R_OFERTAS.x + 16, R_OFERTAS.y + 10),
                  size='sm', color='dorado')
        if not ofertas:
            texto = ("Este espacio ya tiene patrocinador." if p['contratos'].get(espacio)
                     else "No hay ofertas. Llegan al abrir la ventana de pases de inicio o de invierno.")
            draw_text(screen, texto, (R_OFERTAS.x + 16, OFERTA_Y0 + 8), size='md', color='blanco')
        for k, o in enumerate(ofertas[:3]):
            ro = _rects_oferta(k)
            if k == of_i:
                pygame.draw.rect(screen, (30, 45, 75), ro['fila'], border_radius=4)
            x, y = ro['fila'].x + 10, ro['fila'].y + 4
            titulo = f"{o['marca']}  ·  {o['rubro'].capitalize()}  ·  {PERFIL_TXT.get(o['perfil'], o['perfil'])}"
            draw_text(screen, _corto(titulo + ("  ·  RENOVACIÓN" if o.get('renovacion') else ""), 720, 'md'), (x, y),
                      size='md', color='dorado' if o.get('renovacion') else 'blanco')
            draw_text(screen, f"Fijo {P._m(o['fijo'])}/año  ·  Bono {P._m(o['bono'])}  ·  {o['anios']} año{'s' if o['anios'] != 1 else ''}"
                              f"  ·  Prima {P._m(int(o['fijo'] * P.PRIMA_FRAC))}", (x, y + 31), size='sm', color='verde')
            draw_text(screen, _corto("Objetivo: " + o['objetivo']['texto'], 720), (x, y + 54), size='sm', color='blanco')
            draw_button(screen, ro['firmar'], "FIRMAR", ro['firmar'].collidepoint(mouse_pos))
            draw_button(screen, ro['prima'], "PRIMA", ro['prima'].collidepoint(mouse_pos))
            if not o.get('negociada'):
                draw_button(screen, ro['n1'], "+10%", ro['n1'].collidepoint(mouse_pos))
                draw_button(screen, ro['n2'], "+20%", ro['n2'].collidepoint(mouse_pos))
            draw_button(screen, ro['rechazar'], "NO", ro['rechazar'].collidepoint(mouse_pos))
        return None
    except Exception as e:
        logger.error(f"Error en patrocinios_screen: {e}", exc_info=True)
        return 'league_screen'
