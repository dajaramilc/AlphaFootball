# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Tarjetas visuales de noticias (v0.4.23.0).

Una sola fuente para el feed del hub, la pantalla Noticias y la carga de temporada: la imagen 9:16 de la
categoría (`noticias.imagen`) recortada para cubrir la tarjeta, o el color de la categoría si no hay imagen;
la etiqueta del tipo arriba y el titular sobre un degradado oscuro en el tercio inferior.
Las Surfaces se cachean por (id, ancho, alto, ...): el id de una noticia nunca se reutiliza, así que la
caché es segura y el dibujo por cuadro no hace trabajo.
"""
from __future__ import annotations

import logging
from typing import Optional

import pygame

from alpha_football import noticias as N

logger = logging.getLogger(__name__)

_CACHE: dict = {}
_MAX_CACHE = 160
_COLOR_POR_DEFECTO = (58, 66, 82)
_DORADO = (255, 215, 0)


def vaciar_cache() -> None:
    _CACHE.clear()


def envolver(texto, fuente, ancho: int, max_lineas: int) -> list:
    """Parte `texto` en líneas que caben en `ancho` px; si sobran líneas, la última termina en "…".
    Una palabra más ancha que `ancho` se deja entera en su línea (el recorte lo hace la superficie)."""
    palabras = str(texto or '').split()
    lineas, actual = [], ""
    for p in palabras:
        prueba = (actual + " " + p).strip()
        if not actual or fuente.size(prueba)[0] <= ancho:
            actual = prueba
        else:
            lineas.append(actual)
            actual = p
    if actual:
        lineas.append(actual)
    if len(lineas) > max_lineas:
        lineas = lineas[:max_lineas]
        ultima = lineas[-1]
        while ultima and fuente.size(ultima + "…")[0] > ancho:
            ultima = ultima[:-1]
        lineas[-1] = ultima.rstrip() + "…"
    return lineas


def _color_de(noticia: dict) -> tuple:
    cat = noticia.get('categoria') or N.CATEGORIA.get(noticia.get('tipo'), 'general')
    return tuple(N.COLOR.get(cat) or N.COLOR.get('general') or _COLOR_POR_DEFECTO)


def _fondo(noticia: dict, w: int, h: int) -> pygame.Surface:
    """La imagen de la categoría recortada para cubrir w × h, o el color de la categoría."""
    s = pygame.Surface((w, h))
    ruta = None
    try:
        ruta = N.imagen(noticia)
    except Exception as e:
        logger.error(f"No se pudo elegir la imagen de la noticia {noticia.get('id')}: {e}")
    if ruta:
        try:
            img = pygame.image.load(ruta)
            iw, ih = img.get_size()
            k = max(w / iw, h / ih)
            img = pygame.transform.smoothscale(img, (max(w, int(iw * k) + 1), max(h, int(ih * k) + 1)))
            s.blit(img, (0, 0), pygame.Rect((img.get_width() - w) // 2, (img.get_height() - h) // 2, w, h))
            return s
        except Exception as e:
            logger.error(f"No se pudo cargar la imagen '{ruta}': {e}")
    s.fill(_color_de(noticia))
    return s


def _degradado(s: pygame.Surface, y0: int) -> None:
    """Oscurece de y0 al borde inferior (alfa 0 → 215) para que el titular se lea sobre cualquier imagen."""
    w, h = s.get_size()
    alto = max(1, h - y0)
    velo = pygame.Surface((w, alto), pygame.SRCALPHA)
    for i in range(alto):
        pygame.draw.line(velo, (0, 0, 0, int(215 * i / max(1, alto - 1))), (0, i), (w, i))
    s.blit(velo, (0, y0))


def _etiqueta(s: pygame.Surface, noticia: dict, fuente) -> None:
    texto = N.etiqueta(noticia)
    img = fuente.render(texto, True, _DORADO)
    chip = pygame.Rect(8, 8, min(s.get_width() - 16, img.get_width() + 14), img.get_height() + 6)
    pygame.draw.rect(s, (8, 12, 24), chip, border_radius=4)
    pygame.draw.rect(s, _DORADO, chip, width=1, border_radius=4)
    s.blit(img, (chip.x + 7, chip.y + 3), pygame.Rect(0, 0, chip.width - 10, img.get_height()))


def tarjeta(noticia: dict, w: int, h: int, titular: bool = True, dim: bool = False,
            fuente: str = 'md', max_lineas: int = 5) -> pygame.Surface:
    """Tarjeta w × h de la noticia (cacheada). `titular=False` deja solo imagen y etiqueta; `dim` la atenúa."""
    clave = (noticia.get('id'), w, h, bool(titular), bool(dim), fuente, max_lineas)
    s = _CACHE.get(clave)
    if s is not None:
        return s
    from alpha_football.ui.theme import get_font
    s = _fondo(noticia, w, h)
    try:
        if titular:
            _degradado(s, h * 2 // 3)
        f_t = get_font(fuente)
        if titular:
            lineas = envolver(noticia.get('titular'), f_t, w - 24, max_lineas)
            alto_l = f_t.get_linesize()
            y = h - 12 - alto_l * len(lineas)
            for ln in lineas:
                s.blit(f_t.render(ln, True, (0, 0, 0)), (13, y + 1), pygame.Rect(0, 0, w - 14, alto_l))
                s.blit(f_t.render(ln, True, (255, 255, 255)), (12, y), pygame.Rect(0, 0, w - 14, alto_l))
                y += alto_l
        _etiqueta(s, noticia, get_font('sm'))
        if dim:
            velo = pygame.Surface((w, h), pygame.SRCALPHA)
            velo.fill((0, 0, 0, 150))
            s.blit(velo, (0, 0))
    except Exception as e:
        logger.error(f"No se pudo dibujar la tarjeta de la noticia {noticia.get('id')}: {e}")
    if len(_CACHE) >= _MAX_CACHE:
        _CACHE.clear()
    _CACHE[clave] = s
    return s
