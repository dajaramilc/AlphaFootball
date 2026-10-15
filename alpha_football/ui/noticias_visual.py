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
import re
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


_NEGRITAS: dict = {}


def fuente_negrita(nombre: str):
    """v0.4.27.0: la fuente en negrita del tamaño `nombre` ('xs'/'sm'/'md'...). Es una fuente propia (la de
    theme.get_font se comparte y no se toca), cacheada por tamaño en píxeles."""
    from alpha_football.ui.theme import FONT_SIZES, get_font
    get_font(nombre)                                  # asegura pygame.font inicializado
    px = FONT_SIZES.get(nombre, 24)
    f = _NEGRITAS.get(px)
    if f is None:
        try:
            f = pygame.font.SysFont("arial", px, bold=True)
        except Exception as e:
            logger.error(f"No se pudo crear la fuente en negrita de {px} px: {e}")
            f = pygame.font.Font(None, px)
            f.set_bold(True)
        _NEGRITAS[px] = f
    return f


def _negrita_de(fuente):
    """La versión en negrita de `fuente` si salió de theme.get_font; si no, la misma (sin distinguir la negrita)."""
    try:
        from alpha_football.ui.theme import FONT_SIZES, get_font
        for nombre in FONT_SIZES:
            if get_font(nombre) is fuente:
                return fuente_negrita(nombre)
    except Exception as e:
        logger.debug(f"noticias_visual: sin fuente en negrita: {e}")
    return fuente


def tramos(linea) -> list:
    """[(texto, negrita)] de una línea con marcas '**' (las impares son negrita; una marca sin cerrar deja
    en negrita hasta el final de la línea)."""
    return [(t, i % 2 == 1) for i, t in enumerate(str(linea or '').split(N.NEGRITA)) if t]


def _serializar(trozos) -> str:
    return ''.join(N.negrita(t) if neg else t for t, neg in trozos)


def _ancho_tramos(trozos, fuente, f_neg) -> int:
    return sum((f_neg if neg else fuente).size(t)[0] for t, neg in trozos)


def _palabras_marcadas(parrafo: str) -> list:
    """Las palabras del párrafo, cada una como [(texto, negrita)] (una negrita que cruza un espacio se corta ahí)."""
    palabras, actual = [], []
    for i, pieza in enumerate(parrafo.split(N.NEGRITA)):
        for trozo in re.split(r'(\s+)', pieza):
            if not trozo:
                continue
            if trozo.isspace():
                if actual:
                    palabras.append(actual)
                    actual = []
            else:
                actual.append((trozo, i % 2 == 1))
    if actual:
        palabras.append(actual)
    return palabras


def _envolver_marcado(parrafo: str, fuente, ancho: int) -> list:
    """Como el ajuste normal, pero midiendo las palabras en negrita con la fuente en negrita. Cada línea sale con
    sus marcas balanceadas (una negrita que cruza dos líneas se cierra y se reabre)."""
    f_neg = _negrita_de(fuente)
    espacio = fuente.size(" ")[0]
    lineas, actual, ancho_actual = [], [], 0
    for p in _palabras_marcadas(parrafo):
        w = _ancho_tramos(p, fuente, f_neg)
        if not actual:
            actual, ancho_actual = [p], w
        elif ancho_actual + espacio + w <= ancho:
            actual.append(p)
            ancho_actual += espacio + w
        else:
            lineas.append(" ".join(_serializar(x) for x in actual))
            actual, ancho_actual = [p], w
    lineas.append(" ".join(_serializar(x) for x in actual))
    return lineas


def _con_elipsis(linea: str, fuente, ancho: int) -> str:
    """La línea recortada para que, con "…" al final, quepa en `ancho` px."""
    if N.NEGRITA not in linea:
        while linea and fuente.size(linea + "…")[0] > ancho:
            linea = linea[:-1]
        return linea.rstrip() + "…"
    f_neg = _negrita_de(fuente)
    trozos = tramos(linea)
    while trozos and _ancho_tramos(trozos + [("…", False)], fuente, f_neg) > ancho:
        t, neg = trozos[-1]
        if len(t) > 1:
            trozos[-1] = (t[:-1], neg)
        else:
            trozos.pop()
    if trozos:
        t, neg = trozos[-1]
        trozos[-1] = (t.rstrip(), neg)
    return _serializar(trozos + [("…", False)])


def dibujar_linea(screen, linea, pos: tuple, size: str = 'sm', color: str = 'blanco', shadow: bool = False) -> None:
    """v0.4.27.0: dibuja una línea del cuerpo de una noticia o de un correo; lo que va entre '**' sale en negrita.
    Sin marcas es un draw_text normal."""
    from alpha_football.ui.theme import COLORS, draw_text, get_font
    linea = str(linea or '')
    if N.NEGRITA not in linea:
        draw_text(screen, linea, pos, size=size, color=color, shadow=shadow)
        return
    try:
        f_n, f_b = get_font(size), fuente_negrita(size)
        rgb = COLORS.get(color, COLORS['blanco'])
        x, y = pos
        for texto, neg in tramos(linea):
            f = f_b if neg else f_n
            if shadow:
                screen.blit(f.render(texto, True, (0, 0, 0)), (x + 2, y + 2))
            screen.blit(f.render(texto, True, rgb), (x, y))
            x += f.size(texto)[0]
    except Exception as e:
        logger.error(f"No se pudo dibujar la línea con negrita '{linea}': {e}")


def envolver(texto, fuente, ancho: int, max_lineas: int) -> list:
    """Parte `texto` en líneas que caben en `ancho` px; si sobran líneas, la última termina en "…".
    Los saltos de línea del texto se respetan (un "\n" corta la línea y una línea en blanco queda como "").
    Una palabra más ancha que `ancho` se deja entera en su línea (el recorte lo hace la superficie).
    v0.4.27.0: lo que va entre '**' es negrita y se mide con la fuente en negrita (`dibujar_linea` lo dibuja)."""
    lineas = []
    for parrafo in str(texto or '').split('\n'):
        if N.NEGRITA in parrafo and parrafo.replace(N.NEGRITA, '').strip():
            lineas.extend(_envolver_marcado(parrafo, fuente, ancho))
            continue
        palabras = parrafo.replace(N.NEGRITA, '').split()
        if not palabras:
            lineas.append("")                      # línea en blanco: separa bloques del cuerpo
            continue
        actual = ""
        for p in palabras:
            prueba = (actual + " " + p).strip()
            if not actual or fuente.size(prueba)[0] <= ancho:
                actual = prueba
            else:
                lineas.append(actual)
                actual = p
        lineas.append(actual)
    while lineas and not lineas[0]:                # sin líneas en blanco al principio ni al final
        lineas.pop(0)
    while lineas and not lineas[-1]:
        lineas.pop()
    if len(lineas) > max_lineas:
        lineas = lineas[:max_lineas]
        lineas[-1] = _con_elipsis(lineas[-1], fuente, ancho)
    return lineas


_ORDEN_FUENTES = ('lg', 'md', 'sm', 'xs')


def ajustar(texto, ancho: int, max_lineas: int, fuente: str = 'sm') -> tuple:
    """(nombre de la fuente, fuente, líneas): `fuente` si el texto cabe en `max_lineas` sin recortarse; si no, la
    siguiente más pequeña ('md' → 'sm' → 'xs'). Si en ninguna cabe, la más pequeña con el recorte "…"."""
    from alpha_football.ui.theme import get_font
    nombres = _ORDEN_FUENTES[_ORDEN_FUENTES.index(fuente):] if fuente in _ORDEN_FUENTES else (fuente,)
    for nombre in nombres:
        f = get_font(nombre)
        if len(envolver(texto, f, ancho, max_lineas + 1)) <= max_lineas:      # una de más: ¿sobra algo?
            return nombre, f, envolver(texto, f, ancho, max_lineas)
    f = get_font(nombres[-1])
    return nombres[-1], f, envolver(texto, f, ancho, max_lineas)


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
            fuente: str = 'sm', max_lineas: int = 5) -> pygame.Surface:
    """Tarjeta w × h de la noticia (cacheada). `titular=False` deja solo imagen y etiqueta; `dim` la atenúa.
    v0.4.25.0: el titular va en letra pequeña y, si aun así no cabe, en la más pequeña."""
    clave = (noticia.get('id'), w, h, bool(titular), bool(dim), fuente, max_lineas)
    s = _CACHE.get(clave)
    if s is not None:
        return s
    from alpha_football.ui.theme import get_font
    s = _fondo(noticia, w, h)
    try:
        if titular:
            _degradado(s, h * 2 // 3)
        if titular:
            _n, f_t, lineas = ajustar(noticia.get('titular'), w - 24, max_lineas, fuente)
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
