# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Noticias (v0.4.23.0). OFICINA > NOTICIAS.
Lista de las noticias vigentes a la izquierda (primero las más recientes, dentro del mismo día las más importantes) y el
detalle a la derecha: imagen 9:16 de la categoría, etiqueta, titular, la fecha real ("sáb 12 sep 2026") y el cuerpo.
Al elegir una noticia se marca leída. Si trae `accion` ({'pantalla', 'texto'}) hay un botón que navega allí.
Teclado: ↑ ↓ elegir · RePág AvPág saltar 10 · Inicio / Fin · Enter ir (si hay botón) · Esc volver.
"""
from __future__ import annotations

import logging
from typing import Optional

import pygame

from alpha_football import noticias as N
from alpha_football.ui import noticias_visual as V

try:
    from alpha_football.ui.theme import (SCREEN_W, COLORS, get_font, draw_gradient_bg, draw_panel,
                                         draw_button, draw_text)
except Exception:
    SCREEN_W = 1280
    COLORS = {}
    def get_font(size): return pygame.font.Font(None, 24)
    def draw_gradient_bg(screen): screen.fill((10, 14, 26))
    def draw_panel(screen, rect): pygame.draw.rect(screen, (20, 26, 46), rect)
    def draw_button(screen, rect, text, hover): return rect
    def draw_text(screen, text, pos, size='md', color='blanco', shadow=True): pass

logger = logging.getLogger(__name__)

R_LISTA = pygame.Rect(16, 76, 500, 620)
R_DETALLE = pygame.Rect(528, 76, 736, 620)
R_IMAGEN = pygame.Rect(544, 92, 330, 586)
R_TEXTO = pygame.Rect(892, 92, 356, 586)
R_ACCION = pygame.Rect(892, 620, 356, 48)
ALTO_FILA = 56
FILAS_VISIBLES = 10


def _volver() -> pygame.Rect:
    return pygame.Rect(SCREEN_W - 196, 16, 180, 44)


def rect_fila(i: int) -> pygame.Rect:
    """Fila visible i (0-9) de la lista."""
    return pygame.Rect(R_LISTA.x + 8, R_LISTA.y + 48 + i * ALTO_FILA, R_LISTA.width - 16, ALTO_FILA - 4)


def abrir(estado: dict, noticia_id=None) -> str:
    """Abre la pantalla; con `noticia_id` esa noticia queda elegida (y leída)."""
    if noticia_id is not None:
        estado['noticias_sel_id'] = noticia_id
    estado.pop('_noticias_activas', None)
    return 'noticias_screen'


def _activas(estado: dict) -> list:
    """Las noticias vigentes, recalculadas solo cuando cambia la lista (recorrer el calendario cuesta)."""
    lista = N.lista(estado)
    clave = (len(lista), lista[0]['id'] if lista else None)
    cache = estado.get('_noticias_activas')
    if not cache or cache[0] != clave:
        cache = (clave, N.activas(estado))
        estado['_noticias_activas'] = cache
    return cache[1]


def _a_la_vista(estado: dict, sel: int, total: int) -> None:
    desde = int(estado.get('noticias_scroll', 0) or 0)
    if sel < desde:
        desde = sel
    elif sel >= desde + FILAS_VISIBLES:
        desde = sel - FILAS_VISIBLES + 1
    estado['noticias_scroll'] = max(0, min(desde, max(0, total - FILAS_VISIBLES)))


def _titular_de_fila(texto: str, ancho: int) -> tuple:
    """(tamaño, texto) del titular en una sola línea: en 'sm' si cabe y, si no, en 'xs' (recortado solo si
    tampoco cabe así)."""
    nombre, _f, lineas = V.ajustar(texto, ancho, 1, 'sm')
    return nombre, (lineas[0] if lineas else "")


def _dibujar_lista(screen, estado: dict, lista: list, sel: int, mouse_pos) -> None:
    draw_panel(screen, R_LISTA)
    draw_text(screen, f"NOTICIAS  ·  {len(lista)} vigentes  ·  {sum(1 for n in lista if not n.get('leida'))} sin leer",
              (R_LISTA.x + 16, R_LISTA.y + 12), size='sm', color='dorado')
    if not lista:
        draw_text(screen, "No hay noticias vigentes.", (R_LISTA.x + 16, R_LISTA.y + 64), size='md', color='blanco')
        draw_text(screen, "Caducan a las 3 jornadas; llegan con cada jornada.", (R_LISTA.x + 16, R_LISTA.y + 100),
                  size='sm', color='azul')
        return
    f_sm = get_font('sm')
    desde = int(estado.get('noticias_scroll', 0) or 0)
    for fila, n in enumerate(lista[desde:desde + FILAS_VISIBLES]):
        r = rect_fila(fila)
        idx = desde + fila
        if idx == sel or r.collidepoint(mouse_pos):
            pygame.draw.rect(screen, (40, 60, 95), r, border_radius=6)
        pygame.draw.rect(screen, tuple(N.COLOR.get(n.get('categoria')) or N.COLOR['general']),
                         pygame.Rect(r.x, r.y, 6, r.height), border_radius=3)
        draw_text(screen, N.etiqueta(n), (r.x + 16, r.y + 3), size='sm', color='azul', shadow=False)
        fecha = N.fecha_texto(n, largo=False)
        draw_text(screen, fecha, (r.right - f_sm.size(fecha)[0] - 32, r.y + 3), size='sm', color='azul', shadow=False)
        tam, titular = _titular_de_fila(n.get('titular', ''), r.width - 52)
        draw_text(screen, titular, (r.x + 16, r.y + 27 + (2 if tam == 'xs' else 0)), size=tam,
                  color='blanco' if n.get('leida') else 'dorado', shadow=False)
        if not n.get('leida'):
            pygame.draw.circle(screen, (255, 215, 0), (r.right - 16, r.y + r.height // 2), 5)
    if len(lista) > FILAS_VISIBLES:
        draw_text(screen, f"{desde + 1}-{min(len(lista), desde + FILAS_VISIBLES)} de {len(lista)}",
                  (R_LISTA.right - 140, R_LISTA.y + 12), size='sm', color='azul', shadow=False)


def _dibujar_detalle(screen, n: Optional[dict], mouse_pos) -> None:
    draw_panel(screen, R_DETALLE)
    if not n:
        draw_text(screen, "Elige una noticia de la lista.", (R_DETALLE.x + 20, R_DETALLE.y + 24), size='md', color='blanco')
        return
    screen.blit(V.tarjeta(n, R_IMAGEN.width, R_IMAGEN.height, titular=False), R_IMAGEN.topleft)
    pygame.draw.rect(screen, (0, 191, 255), R_IMAGEN, width=1)
    x, y, ancho = R_TEXTO.x, R_TEXTO.y, R_TEXTO.width
    draw_text(screen, N.etiqueta(n), (x, y), size='sm', color='dorado')
    y += 32
    # v0.4.25.0: el titular va en 'md' (antes 'lg') y baja a 'sm' o 'xs' si es largo, para que quepa entero
    tam_t, f_t, lineas_t = V.ajustar(n.get('titular'), ancho, 4, 'md')
    for ln in lineas_t:
        draw_text(screen, ln, (x, y), size=tam_t, color='blanco')
        y += f_t.get_linesize()
    y += 6
    draw_text(screen, N.fecha_texto(n), (x, y), size='sm', color='azul')
    y += 34
    limite = (R_ACCION.y - 12) if n.get('accion') else (R_TEXTO.bottom - 8)
    # el cuerpo respeta sus saltos de línea (equipo del año, campeones...). Baja de 'sm' a 'xs' cuando así cada
    # renglón cabe sin partirse (listas legibles); si ni así, la primera letra en que el texto entra completo
    cuerpo = n.get('cuerpo')
    primera_que_cabe = None
    for candidata in ('sm', 'xs'):
        f_c = get_font(candidata)
        cupo = max(1, (limite - y) // f_c.get_linesize())
        propias = len(V.envolver(cuerpo, f_c, 10 ** 6, 10 ** 4))        # renglones del texto sin partir ninguno
        cabe = len(V.envolver(cuerpo, f_c, ancho, cupo + 1)) <= cupo
        if cabe and len(V.envolver(cuerpo, f_c, ancho, cupo)) == propias:
            tam_c = candidata
            break
        if cabe and primera_que_cabe is None:
            primera_que_cabe = candidata
    else:
        tam_c = primera_que_cabe or 'xs'
    f_c = get_font(tam_c)
    lineas = V.envolver(cuerpo, f_c, ancho, max(1, (limite - y) // f_c.get_linesize()))
    for ln in lineas:
        es_seccion = 0 < len(ln) <= 16 and ln.isupper()           # PORTERO, DEFENSAS... (equipo del año)
        draw_text(screen, ln, (x, y), size=tam_c, color='dorado' if es_seccion else 'blanco', shadow=False)
        y += f_c.get_linesize()
    accion = n.get('accion')
    if accion:
        draw_button(screen, R_ACCION, str(accion.get('texto') or "ABRIR"), R_ACCION.collidepoint(mouse_pos))


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    try:
        lista = _activas(estado)
        total = len(lista)
        sel = int(estado.get('noticias_sel', 0) or 0)
        objetivo = estado.pop('noticias_sel_id', None)
        if objetivo is not None:
            sel = next((i for i, n in enumerate(lista) if n.get('id') == objetivo), sel)
        mouse_pos = pygame.mouse.get_pos()
        click = None
        rueda = 0
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return 'menu'
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    return 'league_screen'
                if ev.key == pygame.K_UP:
                    sel -= 1
                elif ev.key == pygame.K_DOWN:
                    sel += 1
                elif ev.key == pygame.K_PAGEUP:
                    sel -= 10
                elif ev.key == pygame.K_PAGEDOWN:
                    sel += 10
                elif ev.key == pygame.K_HOME:
                    sel = 0
                elif ev.key == pygame.K_END:
                    sel = total - 1
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    accion = (lista[max(0, min(sel, total - 1))].get('accion') if total else None)
                    if accion and accion.get('pantalla'):
                        estado['noticias_sel'] = max(0, min(sel, total - 1))
                        return accion['pantalla']
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                click = ev.pos
            elif ev.type == pygame.MOUSEWHEEL:
                rueda -= ev.y
        sel = max(0, min(sel, max(0, total - 1)))
        if objetivo is not None or sel != int(estado.get('noticias_sel', 0) or 0):
            _a_la_vista(estado, sel, total)
        if rueda:
            estado['noticias_scroll'] = max(0, min(int(estado.get('noticias_scroll', 0) or 0) + rueda,
                                                   max(0, total - FILAS_VISIBLES)))
        if click:
            if _volver().collidepoint(click):
                return 'league_screen'
            desde = int(estado.get('noticias_scroll', 0) or 0)
            for fila in range(min(FILAS_VISIBLES, max(0, total - desde))):
                if rect_fila(fila).collidepoint(click):
                    sel = desde + fila
                    break
            else:
                accion = lista[sel].get('accion') if total else None
                if accion and accion.get('pantalla') and R_ACCION.collidepoint(click):
                    estado['noticias_sel'] = sel
                    return accion['pantalla']
        estado['noticias_sel'] = sel
        if click:
            _a_la_vista(estado, sel, total)
        actual = lista[sel] if total else None
        if actual:
            N.marcar_leida(estado, actual['id'])

        draw_gradient_bg(screen)
        draw_text(screen, "NOTICIAS", (16, 12), size='lg', color='dorado')
        draw_text(screen, "↑ ↓ elegir · RePág AvPág saltar · Enter ir al botón · Esc volver", (16, 48), size='sm',
                  color='azul')
        draw_button(screen, _volver(), "VOLVER", _volver().collidepoint(mouse_pos))
        _dibujar_lista(screen, estado, lista, sel, mouse_pos)
        _dibujar_detalle(screen, actual, mouse_pos)
        return None
    except Exception as e:
        logger.error(f"Error en noticias_screen: {e}", exc_info=True)
        return 'league_screen'
