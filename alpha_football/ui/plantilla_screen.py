# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Plantilla (Pygame)
v2.6.0: todos los jugadores del user en una lista ordenable; clic / ↑↓ muestran la ficha
(atributos, estadísticas, estado) y desde ahí se marca o quita como transferible.
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

from alpha_football.vestuario import PERSONALIDAD_TXT   # v3.1.0

logger = logging.getLogger(__name__)

# v3.6.0: claves de orden por columna ('ovr' queda como alias viejo de 'media' descendente)
ORDENES = ['pos', 'media', 'edad', 'valor', 'contrato']
CLAVES_ORDEN = ('pos', 'nombre', 'media', 'pot', 'edad', 'valor', 'contrato', 'moral', 'energia')
NOMBRE_ORDEN = {'pos': "POSICIÓN", 'nombre': "NOMBRE", 'media': "MEDIA", 'pot': "POTENCIAL", 'edad': "EDAD",
                'valor': "VALOR", 'contrato': "CONTRATO", 'moral': "MORAL", 'energia': "ENERGÍA"}
_ORDEN_POS = {'POR': 0, 'DEF': 1, 'MED': 2, 'DEL': 3}
MORAL_AL_TRANSFERIR = 5

R_LISTA = pygame.Rect(16, 80, 820, 616)      # v3.6.0: terminan en y=696 (barra de atajos)
R_FICHA = pygame.Rect(848, 80, 416, 616)
FILA_Y0, FILA_H = 120, 26
FILAS_VISIBLES = (R_LISTA.bottom - 30 - FILA_Y0) // FILA_H   # deja lugar a la ayuda
# v3.6.0: (clave de orden | None, título, x). Las columnas con clave se ordenan con clic en el encabezado.
# v3.9.0: JUGADOR 84 / EDAD 236 / MED 310 / POT 362 / VALOR 412: la flecha de orden de EDAD quedaba pegada a "MED".
COLUMNAS = [('pos', "POS", 32), ('nombre', "JUGADOR", 84), ('edad', "EDAD", 236), ('media', "MED", 310),
            ('pot', "POT", 362), ('valor', "VALOR", 412), ('contrato', "CONT.", 486), ('moral', "MOR", 560),
            ('energia', "ENE", 618), (None, "PJ", 672), (None, "G/A", 702), (None, "NOTA", 756), (None, "", 800)]


def _rects() -> dict:
    return {
        'orden': pygame.Rect(704, 18, 300, 44),        # v3.9.0: "ORDEN: POSICIÓN (S)" no cabía en 260
        'volver': pygame.Rect(1016, 18, 248, 44),
        'transferible': pygame.Rect(R_FICHA.x + 20, R_FICHA.bottom - 64, R_FICHA.width - 40, 48),
        'renovar': pygame.Rect(R_FICHA.x + 20, R_FICHA.bottom - 122, R_FICHA.width - 40, 48),
    }


def _rect_fila(i: int) -> pygame.Rect:
    """Fila visible i de la lista (0 = primera fila bajo la cabecera)."""
    return pygame.Rect(R_LISTA.x + 8, FILA_Y0 + i * FILA_H, R_LISTA.width - 16, FILA_H - 2)


def _valor(j) -> int:
    v = int(getattr(j, 'valor', 0) or 0)
    if v <= 0:
        try:
            from alpha_football.market import calcular_valor
            v = int(calcular_valor(j))
        except Exception:
            v = 0
    return v


def _siguiente_orden(orden_act: tuple) -> tuple:
    """v3.6.0: tecla S / botón ORDEN ciclan ORDENES (media y valor de mayor a menor)."""
    clave = orden_act[0] if orden_act[0] in ORDENES else ORDENES[-1]
    sig = ORDENES[(ORDENES.index(clave) + 1) % len(ORDENES)]
    return (sig, sig in ('media', 'valor'))


def rect_columna(clave: str) -> pygame.Rect:
    """v3.6.0: zona clicable del encabezado de la columna `clave` (hasta la columna siguiente)."""
    for n, (c, _t, x) in enumerate(COLUMNAS):
        if c == clave:
            x_sig = COLUMNAS[n + 1][2] if n + 1 < len(COLUMNAS) else R_LISTA.right - 8
            return pygame.Rect(x - 4, R_LISTA.y + 6, x_sig - x, FILA_Y0 - 10 - (R_LISTA.y + 6))
    return pygame.Rect(0, 0, 0, 0)


def _num(v) -> int:
    """v3.6.0: número tolerante (None/'' → 0)."""
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def normalizar_orden(orden) -> tuple:
    """v3.6.0: acepta la clave vieja (str, p. ej. 'contrato' u 'ovr') o la tupla (clave, desc)."""
    if isinstance(orden, (tuple, list)) and len(orden) == 2 and orden[0] in CLAVES_ORDEN:
        return (orden[0], bool(orden[1]))
    if orden == 'ovr':
        return ('media', True)
    return (orden, False) if orden in CLAVES_ORDEN else ('pos', False)


def ordenar_plantilla(jugadores: list, orden, desc: bool = False) -> list:
    """Índices de `jugadores` ordenados por la columna `orden` (v3.6.0: CLAVES_ORDEN, asc o desc).
    'pos' ordena por línea y luego media desc (su reversa no es exacta). Acepta las claves viejas."""
    if isinstance(orden, (tuple, list)) or orden == 'ovr':
        orden, desc = normalizar_orden(orden)
    idx = list(range(len(jugadores)))
    js = jugadores
    if orden == 'pos' or orden not in CLAVES_ORDEN:
        signo = -1 if desc else 1
        return sorted(idx, key=lambda i: (signo * _ORDEN_POS.get(js[i].posicion, 9), -_num(js[i].overall)))
    claves = {
        'nombre': lambda j: (str(getattr(j, 'apellido', '') or '').lower(), str(getattr(j, 'nombre', '') or '').lower()),
        'media': lambda j: _num(getattr(j, 'overall', 0)),
        'pot': lambda j: _num(getattr(j, 'potencial', 0)),
        'edad': lambda j: _num(getattr(j, 'edad', 0)),
        'valor': lambda j: _valor(j),
        'contrato': lambda j: (_num(getattr(j, 'contrato_anios', 0)), _num(getattr(j, 'salario', 0))),
        'moral': lambda j: _num(getattr(j, 'moral', 0)),
        'energia': lambda j: _num(getattr(j, 'energia', 0)),
    }
    k = claves[orden]
    asc = sorted(idx, key=lambda i: (k(js[i]), i))
    return list(reversed(asc)) if desc else asc


def alternar_transferible(jugador) -> bool:
    """Marca/quita al jugador como transferible. Marcarlo le baja la moral. Devuelve el nuevo estado."""
    if getattr(jugador, 'pide_salir', False):   # v4.4.0: el que pide salir queda bloqueado en transferibles
        jugador.transferible = True
        return True
    nuevo = not bool(getattr(jugador, 'transferible', False))
    jugador.transferible = nuevo
    if nuevo:
        jugador.moral = max(0, int(getattr(jugador, 'moral', 70)) - MORAL_AL_TRANSFERIR)
    return nuevo


def _dinero(v: int) -> str:
    return f"${v / 1_000_000:.1f}M" if v >= 1_000_000 else f"${v / 1000:.0f}K"


def _dibujar_ficha(screen, j, titular: bool, mouse_pos) -> None:
    # v3.5.0: la ficha vive en ui/ficha_jugador (compartida con OFERTAS); aquí solo el estado y los botones
    estado_txt = ("Lesionado " + str(j.lesion_partidos) + " p." if j.lesion_partidos > 0
                  else "Sancionado" if getattr(j, 'partidos_sancion', 0) > 0
                  else "Titular" if titular else "Suplente")
    if getattr(j, 'transferible', False):
        estado_txt += " · TRANSFERIBLE"
    if getattr(j, 'pide_salir', False):
        estado_txt += " · PIDE SALIR"                                    # v3.1.0
    try:
        from alpha_football.ui.ficha_jugador import dibujar_ficha
        dibujar_ficha(screen, R_FICHA, j, estado_txt)
    except Exception as e:
        logger.error(f"No se pudo dibujar la ficha: {e}")
    r = _rects()['transferible']
    texto = ("PIDE SALIR" if getattr(j, 'pide_salir', False)                  # v4.4.0: bloqueado
             else "QUITAR DE TRANSFERIBLES" if getattr(j, 'transferible', False) else "PONER EN TRANSFERIBLES (T)")
    draw_button(screen, r, texto, r.collidepoint(mouse_pos))
    rr = _rects()['renovar']
    draw_button(screen, rr, "RENOVAR CONTRATO (R)", rr.collidepoint(mouse_pos))


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """Pantalla de plantilla. Retorna 'league_screen' al salir o None para seguir aquí."""
    try:
        mi_equipo = estado.get('mi_equipo')
        if mi_equipo is None:
            return 'league_screen'
        jugadores = list(getattr(mi_equipo, 'jugadores', []) or [])
        orden_act = normalizar_orden(estado.get('plantilla_orden'))     # v3.6.0: (clave, desc)
        estado['plantilla_orden'] = orden_act
        orden = ordenar_plantilla(jugadores, orden_act[0], orden_act[1])
        if not orden:
            return 'league_screen'
        sel = estado.get('plantilla_sel')
        if sel not in orden:
            sel = orden[0]
        pos_sel = orden.index(sel)
        scroll = int(estado.get('plantilla_scroll', 0) or 0)
        rects = _rects()

        mouse_pos = pygame.mouse.get_pos()
        click_pos = None
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return 'menu'
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if ev.button == 1:
                    click_pos = ev.pos
                elif ev.button in (4, 5) and R_LISTA.collidepoint(mouse_pos):
                    scroll += -1 if ev.button == 4 else 1
            elif ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    return 'league_screen'
                if ev.key == pygame.K_UP:
                    pos_sel = max(0, pos_sel - 1)
                elif ev.key == pygame.K_DOWN:
                    pos_sel = min(len(orden) - 1, pos_sel + 1)
                elif ev.key == pygame.K_t:
                    alternar_transferible(jugadores[orden[pos_sel]])
                elif ev.key == pygame.K_r:
                    from alpha_football.negociacion import iniciar_negociacion
                    estado['plantilla_sel'] = orden[pos_sel]
                    return iniciar_negociacion(estado, jugadores[orden[pos_sel]], None, 'renovar', 'plantilla_screen')
                elif ev.key == pygame.K_s:
                    estado['plantilla_orden'] = _siguiente_orden(orden_act)
                # la selección debe quedar visible
                if pos_sel < scroll:
                    scroll = pos_sel
                elif pos_sel >= scroll + FILAS_VISIBLES:
                    scroll = pos_sel - FILAS_VISIBLES + 1

        if click_pos:
            if rects['volver'].collidepoint(click_pos):
                return 'league_screen'
            col = next((c for c, _t, _x in COLUMNAS if c and rect_columna(c).collidepoint(click_pos)), None)
            if col:                                                     # v3.6.0: clic en encabezado
                estado['plantilla_orden'] = (col, not orden_act[1]) if col == orden_act[0] else (col, False)
            elif rects['orden'].collidepoint(click_pos):
                estado['plantilla_orden'] = _siguiente_orden(orden_act)
            elif rects['transferible'].collidepoint(click_pos):
                alternar_transferible(jugadores[orden[pos_sel]])
            elif rects['renovar'].collidepoint(click_pos):
                from alpha_football.negociacion import iniciar_negociacion
                estado['plantilla_sel'] = orden[pos_sel]
                return iniciar_negociacion(estado, jugadores[orden[pos_sel]], None, 'renovar', 'plantilla_screen')
            else:
                for i in range(FILAS_VISIBLES):
                    if scroll + i < len(orden) and _rect_fila(i).collidepoint(click_pos):
                        pos_sel = scroll + i
                        break

        scroll = max(0, min(max(0, len(orden) - FILAS_VISIBLES), scroll))
        estado['plantilla_scroll'] = scroll
        estado['plantilla_sel'] = orden[pos_sel]

        # --- Dibujo ---
        draw_gradient_bg(screen)
        draw_text(screen, "PLANTILLA", (16, 12), size='lg', color='dorado')
        transf = sum(1 for j in jugadores if getattr(j, 'transferible', False))
        draw_text(screen, f"{mi_equipo.nombre}  ·  {len(jugadores)} jugadores  ·  {transf} transferibles",
                  (16, 50), size='sm', color='verde')
        draw_button(screen, rects['orden'], f"ORDEN: {NOMBRE_ORDEN.get(estado['plantilla_orden'][0], '')} (S)",
                    rects['orden'].collidepoint(mouse_pos))
        draw_button(screen, rects['volver'], "VOLVER", rects['volver'].collidepoint(mouse_pos))

        draw_panel(screen, R_LISTA)
        orden_vis = normalizar_orden(estado['plantilla_orden'])
        for clave, titulo, x in COLUMNAS:
            activo = clave is not None and clave == orden_vis[0]
            r_col = rect_columna(clave) if clave else None
            if r_col is not None and r_col.collidepoint(mouse_pos):
                pygame.draw.rect(screen, (24, 32, 54), r_col, border_radius=4)
            draw_text(screen, titulo, (x, R_LISTA.y + 10), size='sm', color='verde' if activo else 'dorado')
            if activo:                                                  # v3.6.0: flecha ▲/▼ dibujada
                ax = x + get_font('sm').size(titulo)[0] + 3
                cy = R_LISTA.y + 20
                pts = ([(ax, cy - 3), (ax + 8, cy - 3), (ax + 4, cy + 3)] if orden_vis[1]
                       else [(ax, cy + 3), (ax + 8, cy + 3), (ax + 4, cy - 3)])
                pygame.draw.polygon(screen, COLORS['verde'], pts)
        pygame.draw.line(screen, COLORS['azul'], (R_LISTA.x + 8, FILA_Y0 - 6), (R_LISTA.right - 8, FILA_Y0 - 6), 1)
        alin = getattr(mi_equipo, 'alineacion_activa', None) or estado.get('alineacion_activa')
        titulares = set(getattr(alin, 'titulares', []) or [])
        for i in range(FILAS_VISIBLES):
            k = scroll + i
            if k >= len(orden):
                break
            idx = orden[k]
            j = jugadores[idx]
            fila = _rect_fila(i)
            if k == pos_sel:
                pygame.draw.rect(screen, (30, 45, 75), fila, border_radius=4)
                pygame.draw.rect(screen, COLORS['dorado'], fila, width=1, border_radius=4)
            elif fila.collidepoint(mouse_pos):
                pygame.draw.rect(screen, (24, 32, 54), fila, border_radius=4)
            nota = float(getattr(j, 'promedio_nota', 0.0) or 0.0)
            marca, c_marca = ("T", 'dorado') if getattr(j, 'transferible', False) else ("", 'blanco')
            if j.lesion_partidos > 0:
                marca, c_marca = "LES", 'rojo'
            elif getattr(j, 'partidos_sancion', 0) > 0:
                marca, c_marca = "SAN", 'rojo'
            valores = [j.posicion, f"{j.nombre[:1]}. {j.apellido}"[:18], str(j.edad), str(j.overall),
                       str(getattr(j, 'potencial', 0) or '?'), _dinero(_valor(j)),
                       f"{_num(getattr(j, 'contrato_anios', 0))} a", str(_num(getattr(j, 'moral', 0))),
                       str(_num(getattr(j, 'energia', 100))),
                       str(j.partidos_jugados), f"{j.goles}/{getattr(j, 'asistencias', 0)}",
                       f"{nota:.1f}" if j.partidos_jugados else "-", marca]
            for n, ((_c, _t, x), v) in enumerate(zip(COLUMNAS, valores)):
                color = c_marca if n == len(valores) - 1 else ('verde' if n == 1 and idx in titulares else 'blanco')
                draw_text(screen, v, (x, fila.y + 2), size='sm', color=color, shadow=False)
        draw_text(screen, "↑↓ elegir · T transferible · R renovar · clic encabezado ordena · verde = titular",
                  (R_LISTA.x + 12, R_LISTA.bottom - 22), size='sm', color='azul', shadow=False)

        _dibujar_ficha(screen, jugadores[orden[pos_sel]], orden[pos_sel] in titulares, mouse_pos)
        return None
    except Exception as e:
        logger.error(f"Error en plantilla_screen: {e}", exc_info=True)
        return 'league_screen'
