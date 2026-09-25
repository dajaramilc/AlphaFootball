# -*- coding: utf-8 -*-
"""v3.5.0: montos tecleables. Dígito = v·10 + d (máx. 12 dígitos), Backspace = v // 10."""
import pygame

MAX_MONTO = 10 ** 12 - 1


def editar_valor(v: int, ev) -> int:
    v = int(v or 0)
    if getattr(ev, 'type', None) != pygame.KEYDOWN:
        return v
    if ev.key == pygame.K_BACKSPACE:
        return v // 10
    u = getattr(ev, 'unicode', '') or ''
    if len(u) == 1 and u.isdigit():
        nuevo = v * 10 + int(u)
        return nuevo if nuevo <= MAX_MONTO else v
    return v
