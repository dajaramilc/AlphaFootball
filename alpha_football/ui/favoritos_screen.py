# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — NEGOCIACIONES > FAVORITOS (Pygame)
Lista de los jugadores que marcaste en NEGOCIAR para ficharlos después: búsqueda por nombre,
su ficha, NEGOCIAR (fichaje con su club y con el jugador) y QUITAR DE FAVORITOS.
Teclado: ↑ ↓ elegir · Enter negociar · Supr quitar · clic en la caja para escribir · Esc volver.
"""
from __future__ import annotations

import logging
from typing import Optional

import pygame

from alpha_football import negociacion as N
from alpha_football.ui import buscador_screen as B
from alpha_football.ui.buscador_screen import (
    COLORS, SCREEN_W, get_font, draw_gradient_bg, draw_panel, draw_button, draw_text,
    R_LISTA, R_FICHA, FILA_H, dibujar_estrella, dibujar_boton_favorito,
)

logger = logging.getLogger(__name__)

R_VOLVER = pygame.Rect(1116, 12, 148, 40)
R_NOMBRE = pygame.Rect(16, 64, 400, 36)
FILA_Y0 = 228
FILAS_VISIBLES = (R_LISTA.bottom - 6 - FILA_Y0) // FILA_H
COLUMNAS = [("JUGADOR", 50), ("POS", 250), ("EDAD", 300), ("MED", 358), ("POT", 406),
            ("CLUB", 452), ("LIGA", 636), ("PRECIO", 712)]


def _rect_fila(i: int) -> pygame.Rect:
    return pygame.Rect(R_LISTA.x + 8, FILA_Y0 + i * FILA_H, R_LISTA.width - 16, FILA_H - 2)


def _estado(estado: dict) -> dict:
    return estado.setdefault('fav', {'nombre': '', 'texto_activo': False, 'sel': 0, 'scroll': 0})


def lista(estado: dict) -> list:
    """Favoritos vigentes filtrados por el texto de búsqueda (sin tildes ni mayúsculas)."""
    f = _estado(estado)
    favs = N.favoritos(estado)
    if not f['nombre'].strip():
        return favs
    return N.filtrar(favs, {'nombre': f['nombre']})


def _mensaje(estado, texto, color='verde') -> None:
    estado['fav_msg'] = (texto, pygame.time.get_ticks() + 3000, color)


def _negociar(estado: dict, item) -> Optional[str]:
    j, club, _et = item
    try:
        from alpha_football.market import puede_fichar
        ok, motivo = puede_fichar(estado['mi_equipo'], j, 0)
    except Exception as e:
        logger.error(f"puede_fichar falló en favoritos: {e}")
        ok, motivo = True, ""
    if ok:
        return N.iniciar_negociacion(estado, j, club, 'fichaje', 'favoritos_screen')
    _mensaje(estado, motivo, 'rojo')
    return None


def _quitar(estado: dict, item) -> None:
    N.quitar_favorito(estado, item[0])
    _mensaje(estado, f"{item[0].nombre_completo} quitado de favoritos")


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """Pantalla de favoritos. Retorna 'league_screen' al salir o None para seguir aquí."""
    try:
        mi = estado.get('mi_equipo')
        if mi is None:
            return 'league_screen'
        f = _estado(estado)
        estado['texto_activo'] = bool(f['texto_activo'])     # H y los atajos no se comen las letras
        res = lista(estado)
        rects = B._rects()
        mouse_pos = pygame.mouse.get_pos()
        click_pos = None

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return 'menu'
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if ev.button == 1:
                    click_pos = ev.pos
                elif ev.button in (4, 5) and R_LISTA.collidepoint(mouse_pos):
                    f['scroll'] += -1 if ev.button == 4 else 1
            elif ev.type == pygame.KEYDOWN:
                if f['texto_activo']:
                    if ev.key == pygame.K_BACKSPACE:
                        f['nombre'] = f['nombre'][:-1]
                    elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                        f['texto_activo'] = False
                    elif ev.unicode and ev.unicode.isprintable() and len(f['nombre']) < 24:
                        f['nombre'] += ev.unicode
                    f['sel'] = 0
                    continue
                if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    estado['texto_activo'] = False
                    return 'league_screen'
                if ev.key == pygame.K_UP:
                    f['sel'] = max(0, f['sel'] - 1)
                elif ev.key == pygame.K_DOWN:
                    f['sel'] = min(max(0, len(res) - 1), f['sel'] + 1)
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and res:
                    destino = _negociar(estado, res[min(f['sel'], len(res) - 1)])
                    if destino:
                        return destino
                elif ev.key == pygame.K_DELETE and res:
                    _quitar(estado, res[min(f['sel'], len(res) - 1)])
                    res = lista(estado)

        if click_pos:
            f['texto_activo'] = R_NOMBRE.collidepoint(click_pos)
            if R_VOLVER.collidepoint(click_pos):
                estado['texto_activo'] = False
                return 'league_screen'
            if res and rects['fichar'].collidepoint(click_pos):
                destino = _negociar(estado, res[min(f['sel'], len(res) - 1)])
                if destino:
                    estado['texto_activo'] = False
                    return destino
            elif res and rects['prestamo'].collidepoint(click_pos):      # pedir a préstamo
                j, club, _et = res[min(f['sel'], len(res) - 1)]
                if club is None:
                    _mensaje(estado, "Un agente libre no se pide a préstamo: fíchalo.", 'rojo')
                else:
                    estado['texto_activo'] = False
                    return N.iniciar_negociacion(estado, j, club, 'prestamo', 'favoritos_screen')
            elif res and rects['favorito'].collidepoint(click_pos):
                _quitar(estado, res[min(f['sel'], len(res) - 1)])
                res = lista(estado)
            else:
                for i in range(FILAS_VISIBLES):
                    if f['scroll'] + i < len(res) and _rect_fila(i).collidepoint(click_pos):
                        f['sel'] = f['scroll'] + i

        f['sel'] = max(0, min(f['sel'], len(res) - 1))
        if f['sel'] < f['scroll']:
            f['scroll'] = f['sel']
        elif f['sel'] >= f['scroll'] + FILAS_VISIBLES:
            f['scroll'] = f['sel'] - FILAS_VISIBLES + 1
        f['scroll'] = max(0, min(f['scroll'], max(0, len(res) - FILAS_VISIBLES)))

        # --- Dibujo ---
        draw_gradient_bg(screen)
        draw_text(screen, "FAVORITOS · JUGADORES QUE SIGUES", (16, 10), size='md', color='dorado')
        draw_text(screen, f"{mi.nombre}  ·  Presupuesto {B._dinero(mi.balance)}  ·  {len(N._favs(estado))} favoritos",
                  (16, 38), size='sm', color='verde')
        draw_button(screen, R_VOLVER, "VOLVER", R_VOLVER.collidepoint(mouse_pos))
        pygame.draw.rect(screen, (15, 22, 40), R_NOMBRE, border_radius=6)
        pygame.draw.rect(screen, COLORS['dorado'] if f['texto_activo'] else COLORS['azul'], R_NOMBRE, width=2, border_radius=6)
        cursor = "|" if f['texto_activo'] and (pygame.time.get_ticks() // 500) % 2 == 0 else ""
        texto = f['nombre'] + cursor if (f['nombre'] or f['texto_activo']) else "Buscar entre tus favoritos..."
        draw_text(screen, texto, (R_NOMBRE.x + 10, R_NOMBRE.y + 8), size='sm',
                  color='blanco' if f['nombre'] else 'azul', shadow=False)
        draw_text(screen, "Marca jugadores con AGREGAR A FAVORITOS en NEGOCIAR.  Enter negocia · Supr quita · Esc vuelve",
                  (16, 158), size='sm', color='azul')

        draw_panel(screen, R_LISTA)
        for titulo, x in COLUMNAS:
            draw_text(screen, titulo, (x, R_LISTA.y + 8), size='sm', color='dorado')
        for i in range(FILAS_VISIBLES):
            k = f['scroll'] + i
            if k >= len(res):
                break
            j, club, etiqueta = res[k]
            fila = _rect_fila(i)
            if k == f['sel']:
                pygame.draw.rect(screen, (30, 45, 75), fila, border_radius=4)
                pygame.draw.rect(screen, COLORS['dorado'], fila, width=1, border_radius=4)
            dibujar_estrella(screen, (fila.x + 12, fila.centery), 7, COLORS['dorado'])
            valores = [f"{j.nombre[:1]}. {j.apellido}"[:22], j.posicion, str(j.edad), str(j.overall),
                       str(getattr(j, 'potencial', 0) or '?'), getattr(club, 'nombre', 'Libre')[:20],
                       etiqueta, B._dinero(N.precio_fichaje(j))]
            for (_t, x), v in zip(COLUMNAS, valores):
                draw_text(screen, v, (x, fila.y + 2), size='sm', color='blanco', shadow=False)
        if not res:
            vacio = ("Ningún favorito coincide con la búsqueda." if f['nombre'].strip()
                     else "Todavía no tienes favoritos.")
            draw_text(screen, vacio, (R_LISTA.x + 20, FILA_Y0), size='md', color='blanco')

        item = res[f['sel']] if res else None
        B._dibujar_ficha(screen, estado, item, mouse_pos)
        if item is not None:
            r = rects['fichar']
            draw_button(screen, r, "FICHAR", r.collidepoint(mouse_pos))   # PRÉSTAMO lo dibuja B._dibujar_ficha
            dibujar_boton_favorito(screen, rects['favorito'], True, mouse_pos)

        msg = estado.get('fav_msg')
        if msg and pygame.time.get_ticks() < msg[1]:
            s = get_font('md').render(msg[0], True, COLORS['bg'])
            caja = s.get_rect(center=(SCREEN_W // 2, 40)).inflate(40, 16)
            pygame.draw.rect(screen, COLORS.get(msg[2], COLORS['verde']), caja, border_radius=8)
            screen.blit(s, s.get_rect(center=caja.center))
        return None
    except Exception as e:
        logger.error(f"Error en favoritos_screen: {e}", exc_info=True)
        estado['texto_activo'] = False
        return 'league_screen'
