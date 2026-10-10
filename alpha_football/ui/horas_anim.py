# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Animación de las horas del último día de fichajes (v0.4.18.0)
Cuando un fichaje o una venta se concreta el último día (dia_final.gastar), las horas que cuesta corren a la
vista: 3 por un fichaje, 2 por una venta. dia_final deja anotado estado['anim_horas'] =
{'desde', 'hasta', 'motivo', 'inicio'} y main.py llama a dibujar() después de cada pantalla, así se ve igual
en la negociación, las ofertas o el hub. No bloquea nada: el panel se retira solo.
"""
from __future__ import annotations

import logging
from typing import Optional

import pygame

try:
    from alpha_football.ui.theme import SCREEN_W, COLORS, draw_text, draw_panel
except Exception:
    SCREEN_W = 1280
    COLORS = {'dorado': (255, 215, 0), 'rojo': (255, 68, 68), 'blanco': (255, 255, 255), 'azul': (0, 191, 255)}
    def draw_text(screen, text, pos, size='md', color='blanco', shadow=True): pass
    def draw_panel(screen, rect): pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=8)

logger = logging.getLogger(__name__)

MS_POR_HORA = 500            # cada hora que corre tarda medio segundo
MS_PAUSA_FINAL = 800         # el resultado se queda a la vista un momento antes de retirarse
MS_PULSO = 200               # el número se pone rojo este rato cada vez que cae una hora
HORAS_DIA = 20
R_PANEL = pygame.Rect((SCREEN_W - 560) // 2, 84, 560, 168)


def estado_anim(anim: dict, ahora: int) -> dict:
    """Qué toca mostrar en `ahora` (ms): {'horas': las que se ven, 'pulso': cae una hora justo ahora,
    'terminada': ya pasó la pausa final}. Sin `inicio` todavía no empezó: se ven las de partida."""
    desde, hasta = int(anim.get('desde', 0) or 0), int(anim.get('hasta', 0) or 0)
    if anim.get('inicio') is None:
        return {'horas': desde, 'pulso': False, 'terminada': False}
    pasado = max(0, int(ahora) - int(anim['inicio']))
    total = max(0, desde - hasta)
    corridas = min(total, pasado // MS_POR_HORA)
    pulso = corridas >= 1 and pasado - corridas * MS_POR_HORA < MS_PULSO       # justo después de caer una hora
    return {'horas': desde - corridas, 'pulso': pulso, 'terminada': pasado >= total * MS_POR_HORA + MS_PAUSA_FINAL}


def dibujar(screen: pygame.Surface, estado: dict, ahora: Optional[int] = None) -> None:
    """Dibuja el panel de las horas corriendo si hay una animación anotada; la retira al terminar."""
    anim = estado.get('anim_horas')
    if not isinstance(anim, dict):
        return
    try:
        ahora = pygame.time.get_ticks() if ahora is None else int(ahora)
        if anim.get('inicio') is None:
            anim['inicio'] = ahora                      # empieza a contar en el primer cuadro que se dibuja
        st = estado_anim(anim, ahora)
        if st['terminada']:
            estado.pop('anim_horas', None)
            return
        desde, hasta, horas = int(anim['desde']), int(anim['hasta']), st['horas']
        dorado, rojo = COLORS.get('dorado', (255, 215, 0)), COLORS.get('rojo', (255, 68, 68))
        velo = pygame.Surface((R_PANEL.width, R_PANEL.height), pygame.SRCALPHA)
        velo.fill((10, 14, 26, 235))
        screen.blit(velo, R_PANEL.topleft)
        pygame.draw.rect(screen, dorado, R_PANEL, width=3, border_radius=10)
        draw_text(screen, f"ÚLTIMO DÍA · {anim.get('motivo', 'Horas')}", (R_PANEL.x + 20, R_PANEL.y + 12),
                  size='md', color='dorado')
        draw_text(screen, f"-{max(0, desde - hasta)} h", (R_PANEL.right - 90, R_PANEL.y + 12), size='md', color='rojo')
        corriendo = horas > hasta
        draw_text(screen, f"{horas} h", (R_PANEL.x + 20, R_PANEL.y + 46), size='xl',
                  color='rojo' if st['pulso'] else ('blanco' if corriendo else 'dorado'))
        # las 20 horas del día: doradas las que quedan, rojas las que están corriendo, apagadas las ya gastadas
        ancho, sep = 20, 6
        x0 = R_PANEL.x + (R_PANEL.width - (HORAS_DIA * ancho + (HORAS_DIA - 1) * sep)) // 2
        for i in range(HORAS_DIA):
            r = pygame.Rect(x0 + i * (ancho + sep), R_PANEL.bottom - 52, ancho, 30)
            if i < horas:
                color = dorado
            elif i < desde:
                color = rojo if i >= hasta else (70, 78, 100)
            else:
                color = (40, 46, 66)
            pygame.draw.rect(screen, color, r, border_radius=4)
    except Exception as e:
        logger.error(f"No se pudo dibujar la animación de las horas: {e}")
        estado.pop('anim_horas', None)
