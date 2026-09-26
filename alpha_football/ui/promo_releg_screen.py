# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Pantalla de Promoción / Relegación (v2.3.3).

Se muestra al FINAL de cada temporada, justo después de avanzarla (ver resumen_temporada_screen).
Lista los equipos que ASCIENDEN de 2ª a 1ª y los que DESCIENDEN de 1ª a 2ª.
Botón "CONTINUAR" (Enter / Space / click) vuelve a la pantalla de liga.

Estado esperado:
    estado['promo_releg_data'] = {
        'ascendidos':  [ {nombre, ovr, division_origen, division_destino}, ... ],
        'descendidos': [ {nombre, ovr, division_origen, division_destino}, ... ],
        'user_ascendio': bool,
        'user_descendio': bool,
    }

Cuando no hay datos en el estado, esta pantalla se salta sin error.
"""
from __future__ import annotations

import logging
import pygame
from typing import Optional

try:
    from alpha_football.ui.theme import (
        SCREEN_W, SCREEN_H, COLORS, get_font, draw_gradient_bg, draw_panel, draw_text, draw_button
    )
except Exception:
    SCREEN_W, SCREEN_H = 1280, 720
    COLORS = {'bg': (10, 14, 26), 'verde': (0, 255, 136), 'dorado': (255, 215, 0),
              'rojo': (255, 68, 68), 'azul': (0, 191, 255), 'blanco': (255, 255, 255),
              'panel': (20, 26, 46)}
    def get_font(size): return pygame.font.Font(None, 24)
    def draw_gradient_bg(screen): screen.fill((10, 14, 26))
    def draw_panel(screen, rect): pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=8)
    def draw_button(screen, rect, text, hover): pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=6)
    def draw_text(screen, text, pos, size='md', color='blanco', shadow=True): pass

logger = logging.getLogger(__name__)


def rects_promo() -> dict:
    """v3.9.0: rects de la pantalla de ascensos/descensos (los usa también la ayuda H)."""
    col_w, col_h, gap, y_top = 580, 150, 40, 210
    x_left = (SCREEN_W - (col_w * 2 + gap)) // 2
    btn_w, btn_h = 360, 56
    return {
        'cabecera': pygame.Rect(40, 8, SCREEN_W - 80, 84),
        'balon': pygame.Rect(40, 100, SCREEN_W - 80, 96),
        'ascienden': pygame.Rect(x_left, y_top, col_w, col_h),
        'descienden': pygame.Rect(x_left + col_w + gap, y_top, col_w, col_h),
        'paises': pygame.Rect(x_left, y_top + col_h + 14, col_w * 2 + gap, 230),
        'retiros': pygame.Rect(36, 608, SCREEN_W - 72, 26),
        'continuar': pygame.Rect((SCREEN_W - btn_w) // 2, 694 - btn_h, btn_w, btn_h),
    }


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """Renderiza la pantalla de promo/releg. Retorna:
       - 'league_screen' si el usuario pulsa CONTINUAR / Enter / Esc (la temporada ya avanzó)
       - None para quedarse en esta pantalla
       - 'menu' como fallback defensivo
    """
    try:
        data = estado.get('promo_releg_data') or {}
        ascendidos = data.get('ascendidos', []) or []
        descendidos = data.get('descendidos', []) or []
        user_asc = bool(data.get('user_ascendio'))
        user_des = bool(data.get('user_descendio'))

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

        # Layout
        draw_gradient_bg(screen)

        # Banner segun si el user ascendio/descendio/nada
        if user_asc:
            banner_text = "¡ASCENDISTE A 1ª DIVISIÓN!"
            banner_color = 'verde'
        elif user_des:
            banner_text = "¡DESCENDISTE A 2ª DIVISIÓN!"
            banner_color = 'rojo'
        else:
            banner_text = "PROMOCIÓN / RELEGACIÓN"
            banner_color = 'dorado'

        # Cabecera
        def _centrado(txt, y, size, color):   # v3.0.0: cabecera centrada y separada del borde
            draw_text(screen, txt, ((SCREEN_W - get_font(size).size(txt)[0]) // 2, y), size=size, color=color)

        _rp = rects_promo()                                  # v3.9.0
        draw_panel(screen, _rp['cabecera'])
        _centrado(banner_text, 12, 'xl', banner_color)
        sub = "Resumen de movimientos entre 1ª y 2ª división"
        if user_asc and data.get('premio_ascenso_user'):
            sub = f"Tu plantilla sube de nivel (+3 a +6) y cobras ${data['premio_ascenso_user']:,} por el ascenso"
        elif user_des:
            sub = "Tu plantilla baja de nivel (−2 a −5) por el descenso"
        _centrado(sub, 64, 'sm', 'azul')

        # v2.3.6: Balón de Oro de la temporada que terminó (mejor rendimiento de las 10 ligas)
        balon = estado.get('balon_oro_ultimo')
        caja_balon = _rp['balon']
        draw_panel(screen, caja_balon)
        pygame.draw.rect(screen, COLORS.get('dorado', (255, 215, 0)), caja_balon, width=2, border_radius=8)
        if balon and balon.get('ganador'):
            g = balon['ganador']
            draw_text(screen, f"BALÓN DE ORO T{balon.get('temporada', '?')}: {g['nombre'][:28]}",
                      (caja_balon.x + 20, caja_balon.y + 10), size='lg', color='dorado')
            draw_text(screen, f"{g['equipo'][:24]} · {g['liga'][:32]} · {g['posicion']} {g['ovr']} · "
                              f"{g['goles']} goles · {g['asistencias']} asist. · nota {g['nota']:.2f}",
                      (caja_balon.x + 20, caja_balon.y + 44), size='sm', color='blanco')
            otros = balon.get('podio', [])[1:3]
            if otros:
                podio_txt = "   ".join(f"{i + 2}º {p['nombre'][:20]} ({p['equipo'][:16]})" for i, p in enumerate(otros))
                draw_text(screen, podio_txt, (caja_balon.x + 20, caja_balon.y + 68), size='sm', color='azul')
        else:
            draw_text(screen, "BALÓN DE ORO: sin candidatos esta temporada", (caja_balon.x + 20, caja_balon.y + 34),
                      size='md', color='azul')

        # Tu país: ascendidos (izq.) y descendidos (der.)
        col_w = 580
        col_h = 150
        gap = 40
        x_left = (SCREEN_W - (col_w * 2 + gap)) // 2
        x_right = x_left + col_w + gap
        y_top = 210
        for x_col, titulo, color, lista in ((x_left, "ASCENDEN A 1ª (tu país)", 'verde', ascendidos),
                                            (x_right, "DESCIENDEN A 2ª (tu país)", 'rojo', descendidos)):
            draw_panel(screen, pygame.Rect(x_col, y_top, col_w, col_h))
            draw_text(screen, titulo, (x_col + 20, y_top + 12), size='md', color=color)
            if not lista:
                draw_text(screen, "Sin movimientos.", (x_col + 30, y_top + 60), size='sm', color='azul')
            for i, eq in enumerate(lista[:3]):
                yy = y_top + 52 + i * 32
                nombre = eq.get('nombre', '?') if isinstance(eq, dict) else getattr(eq, 'nombre', '?')
                ovr = eq.get('ovr', '?') if isinstance(eq, dict) else getattr(eq, 'ovr_promedio', '?')
                draw_text(screen, f"{i + 1}. {nombre[:28]}", (x_col + 30, yy), size='md', color=color)
                draw_text(screen, f"OVR {ovr}", (x_col + col_w - 100, yy), size='sm', color='blanco')

        # Los 5 países (v2.3.6: el ascenso/descenso ya no es solo en el país del user)
        caja_paises = _rp['paises']
        draw_panel(screen, caja_paises)
        draw_text(screen, "ASCENSOS Y DESCENSOS EN TODAS LAS LIGAS", (caja_paises.x + 20, caja_paises.y + 10),
                  size='md', color='dorado')
        from alpha_football.paises import PAISES as _PAISES   # v3.7.0
        nombres_pais = {p['liga_id']: p['nombre'] for p in _PAISES}
        for i, mov in enumerate((data.get('todos_paises') or [])[:5]):
            yy = caja_paises.y + 48 + i * 34
            draw_text(screen, nombres_pais.get(mov.get('tipo'), mov.get('tipo', '?')), (caja_paises.x + 20, yy),
                      size='sm', color='blanco')
            draw_text(screen, "Suben: " + ", ".join(n[:20] for n in mov.get('ascendidos', [])),
                      (caja_paises.x + 150, yy), size='sm', color='verde')
            draw_text(screen, "Bajan: " + ", ".join(n[:20] for n in mov.get('descendidos', [])),
                      (caja_paises.x + 640, yy), size='sm', color='rojo')

        # v2.3.8: retiros de la temporada (los del user primero)
        retiros = estado.get('retiros_ultimos') or []
        if retiros:
            mios = [r for r in retiros if r.get('es_user')]
            if mios:
                txt = "Se retiran de tu club: " + ", ".join(
                    f"{r['nombre'][:18]} ({r['edad']}) → {r['regen'][:18]} ({r['regen_edad']}, pot {r['regen_pot']})"
                    for r in mios[:2])
            else:
                txt = f"{len(retiros)} retiros en las 10 ligas, p. ej. " + ", ".join(
                    f"{r['nombre'][:18]} ({r['edad']}, {r['equipo'][:14]})" for r in retiros[:2])
            draw_text(screen, txt[:130], (40, 612), size='sm', color='azul', shadow=False)

        # Boton CONTINUAR centrado abajo
        btn_w, btn_h = 360, 56
        btn_cont = _rp['continuar']   # v3.6.0: sobre la barra
        cont_hover = btn_cont.collidepoint(mouse_pos)
        draw_button(screen, btn_cont, "CONTINUAR  (Enter)", cont_hover)
        # Borde dorado cuando el boton tiene foco de teclado
        if cont_hover:
            pygame.draw.rect(screen, COLORS.get('dorado', (255, 215, 0)), btn_cont, width=3, border_radius=8)

        # v2.3.3: teclado
        try:
            for ev in key_events:
                if ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                    click_pos = (btn_cont.x + btn_cont.width // 2, btn_cont.y + btn_cont.height // 2)
                    break
        except Exception as e_kbd:
            logger.error(f"Error en teclado de promo_releg: {e_kbd}")

        if click_pos and btn_cont.collidepoint(click_pos):
            # Limpiar data para que no se re-muestre en otra ocasion
            estado.pop('promo_releg_data', None)
            estado.pop('balon_oro_ultimo', None)
            # v2.3.5: la temporada YA avanzó antes de llegar aquí; volver al resumen
            # mostraba la tabla vacía y al pulsar de nuevo avanzaba OTRA temporada.
            return "league_screen"

        return None
    except Exception as e:
        logger.error(f"Error en promo_releg_screen: {e}")
        # Fallback defensivo: si algo explota, avanzamos al resumen
        estado.pop('promo_releg_data', None)
        return "league_screen"