# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Correo (v3.1.0). OFICINA > CORREO.
Lista a la izquierda (no leídos en dorado), mensaje a la derecha y botón de acción que lleva a
la pantalla donde se resuelve. Teclado: ↑/↓ elegir, Enter = acción, Esc = volver.
"""
from __future__ import annotations

import logging
from typing import Optional
import pygame

try:
    from alpha_football.ui.theme import SCREEN_W, COLORS, get_font, draw_gradient_bg, draw_panel, draw_button, draw_text
except Exception:
    SCREEN_W = 1280
    COLORS = {'blanco': (255, 255, 255)}
    def get_font(size): return pygame.font.Font(None, 24)
    def draw_gradient_bg(screen): screen.fill((10, 14, 26))
    def draw_panel(screen, rect): pygame.draw.rect(screen, (20, 26, 46), rect)
    def draw_button(screen, rect, text, hover): return rect
    def draw_text(screen, text, pos, size='md', color='blanco', shadow=True): pass

from alpha_football import correo as C

logger = logging.getLogger(__name__)

R_LISTA = pygame.Rect(16, 76, 560, 620)        # v3.6.0: terminan en y=696 (barra de atajos)
R_MSG = pygame.Rect(588, 76, 676, 620)
ALTO_FILA = 44
FILAS = (R_LISTA.height - 16) // ALTO_FILA


def _volver() -> pygame.Rect:
    return pygame.Rect(SCREEN_W - 196, 16, 180, 44)


def _rect_fila(i: int) -> pygame.Rect:
    return pygame.Rect(R_LISTA.x + 8, R_LISTA.y + 8 + i * ALTO_FILA, R_LISTA.width - 16, ALTO_FILA - 4)


def _rect_accion() -> pygame.Rect:
    return pygame.Rect(R_MSG.x + 20, R_MSG.bottom - 70, 360, 50)


R_BORRAR = pygame.Rect(R_MSG.right - 200, R_MSG.bottom - 70, 180, 50)   # v4.7.0
LINEAS_CUERPO = 18
ALTO_OPCION = 46            # v0.4.10.0: botones de decisión de un evento (uno por opción, apilados)


def rects_evento(n: int) -> list:
    base = _rect_accion()
    return [pygame.Rect(base.x, base.y - (n - 1 - i) * ALTO_OPCION, 420, ALTO_OPCION - 6) for i in range(n)]


def _evento_pendiente(m: dict) -> Optional[dict]:
    ev = m.get('evento')
    return ev if ev and ev.get('resuelto') is None else None


def _borrar(estado: dict, m: dict) -> None:
    """v0.4.10.0: borrar un evento sin responder no esquiva la consecuencia: se aplica la de por defecto."""
    if _evento_pendiente(m):
        from alpha_football import eventos as EV
        EV.resolver_pendientes(estado)
    C.borrar(estado, m['id'])


def _envolver(texto: str, ancho_px: int, size: str = 'sm') -> list:
    """Parte el texto en líneas que caben en `ancho_px`; v4.7.0: respeta los saltos de párrafo."""
    fuente, lineas = get_font(size), []
    for parrafo in str(texto).split('\n'):
        linea = ""
        for palabra in parrafo.split():
            prueba = (linea + " " + palabra).strip()
            if fuente.size(prueba)[0] > ancho_px and linea:
                lineas.append(linea)
                linea = palabra
            else:
                linea = prueba
        lineas.append(linea)
    while lineas and not lineas[-1]:
        lineas.pop()
    return lineas


def _ir(estado: dict, msg: dict) -> Optional[str]:
    acc = msg.get('accion') or {}
    if acc.get('compra'):          # v3.5.0: el club aceptó tu oferta → contrato con el jugador
        from alpha_football.negociacion import reanudar_compra
        destino = reanudar_compra(estado, acc['compra'])
        if destino is None:
            estado['correo_aviso_vis'] = (msg.get('id'), estado.pop('correo_aviso', ''))
        return destino
    if acc.get('renovar'):         # v4.4.0: el jugador pide renovar → negociación de su contrato
        mi = estado.get('mi_equipo')
        j = next((x for x in getattr(mi, 'jugadores', []) or [] if x.id == acc['renovar']), None)
        if j is None:
            estado['correo_aviso_vis'] = (msg.get('id'), "Ese jugador ya no está en tu plantilla.")
            return None
        from alpha_football.negociacion import iniciar_negociacion
        return iniciar_negociacion(estado, j, None, 'renovar', 'correo_screen')
    if not acc.get('pantalla'):
        return None
    from alpha_football.ui.league_screen import _abrir
    destino = _abrir(estado, acc['pantalla'])
    estado['volver_notif'] = destino            # v0.4.11.0: VOLVER/ESC regresa a este mensaje
    if destino == 'league_screen':              # el destino es una pestaña del hub
        estado['volver_notif_tab'] = estado.get('hub_tab')
    if destino == 'plantilla_screen':           # v0.4.14.1: la plantilla abre con el jugador del mensaje elegido
        j = C.jugador_de(estado, msg)
        plantel = getattr(estado.get('mi_equipo'), 'jugadores', []) or []
        idx = next((i for i, x in enumerate(plantel) if x is j), None) if j is not None else None
        if idx is not None:
            estado['plantilla_sel'], estado['plantilla_centrar'] = idx, True
    return destino


def _mensajes(estado: dict) -> list:
    """v0.4.10.0: la lista del canal abierto desde NOTIFICACIONES (sin canal: toda la bandeja)."""
    cual = estado.get('correo_canal')
    return C.de_canal(estado, cual) if cual else C.bandeja(estado)


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    try:
        mensajes = _mensajes(estado)
        sel = max(0, min(int(estado.get('correo_sel', 0) or 0), len(mensajes) - 1))
        opc = int(estado.get('correo_opc', 0) or 0)
        mouse_pos = pygame.mouse.get_pos()
        click = None
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return 'menu'
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    return 'notificaciones_screen'
                pend = _evento_pendiente(mensajes[sel]) if mensajes else None
                if pend and ev.key in (pygame.K_LEFT, pygame.K_RIGHT):      # v0.4.10.0: elegir opción
                    opc = max(0, min(len(pend['opciones']) - 1, opc + (1 if ev.key == pygame.K_RIGHT else -1)))
                    continue
                if pend and ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    from alpha_football import eventos as EV
                    EV.resolver(estado, mensajes[sel]['id'], opc)
                    opc = 0
                    continue
                if ev.key == pygame.K_DOWN:
                    sel = min(len(mensajes) - 1, sel + 1)
                    opc = 0
                elif ev.key == pygame.K_UP:
                    sel = max(0, sel - 1)
                    opc = 0
                elif ev.key == pygame.K_DELETE and mensajes:        # v4.7.0: borrar
                    _borrar(estado, mensajes[sel])
                    mensajes = _mensajes(estado)
                    sel = max(0, min(sel, len(mensajes) - 1))
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and mensajes:
                    destino = _ir(estado, mensajes[sel])
                    if destino:
                        return destino
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                click = ev.pos
        inicio = max(0, sel - FILAS + 1)
        if click:
            if _volver().collidepoint(click):
                return 'notificaciones_screen'
            for i in range(min(FILAS, len(mensajes) - inicio)):
                if _rect_fila(i).collidepoint(click):
                    sel = inicio + i
                    opc = 0
            pend = _evento_pendiente(mensajes[sel]) if (click and mensajes) else None
            if pend:                                          # v0.4.10.0: clic en una opción de la decisión
                for i, r in enumerate(rects_evento(len(pend['opciones']))):
                    if r.collidepoint(click):
                        from alpha_football import eventos as EV
                        EV.resolver(estado, mensajes[sel]['id'], i)
                        opc = 0
                click = None            # con decisión pendiente no hay botón de acción
            if click and mensajes and R_BORRAR.collidepoint(click):     # v4.7.0
                _borrar(estado, mensajes[sel])
                mensajes = _mensajes(estado)
                sel = max(0, min(sel, len(mensajes) - 1))
                click = None
            if click and mensajes and _rect_accion().collidepoint(click):
                destino = _ir(estado, mensajes[sel])
                if destino:
                    return destino
        estado['correo_sel'] = sel
        estado['correo_opc'] = opc
        if mensajes:
            C.marcar_leido(estado, mensajes[sel]['id'])

        draw_gradient_bg(screen)
        cual = estado.get('correo_canal')
        draw_text(screen, {'mensaje': "MENSAJES", 'correo': "CORREO"}.get(cual, "CORREO"), (16, 12), size='lg', color='dorado')
        draw_text(screen, f"{len(mensajes)} en total  ·  {C.no_leidos(estado, cual)} sin leer  ·  "
                          f"↑/↓ elegir · Enter acción · Supr borrar · Esc volver", (16, 48), size='sm', color='azul')
        draw_button(screen, _volver(), "VOLVER", _volver().collidepoint(mouse_pos))
        draw_panel(screen, R_LISTA)
        draw_panel(screen, R_MSG)
        if not mensajes:
            draw_text(screen, "No tienes mensajes.", (R_LISTA.x + 20, R_LISTA.y + 20), size='sm', color='blanco')
            return None
        for i, m in enumerate(mensajes[inicio:inicio + FILAS]):
            r = _rect_fila(i)
            if inicio + i == sel:
                pygame.draw.rect(screen, (40, 60, 95), r, border_radius=6)
            col = 'dorado' if not m.get('leido') else 'blanco'
            draw_text(screen, f"{C.REMITENTES.get(m['remitente'], m['remitente'])}  ·  {C.texto_fecha(m)}",   # v0.4.14.1
                      (r.x + 8, r.y + 2), size='sm', color='azul', shadow=False)
            draw_text(screen, m['asunto'][:52], (r.x + 8, r.y + 20), size='sm', color=col, shadow=False)
        m = mensajes[sel]
        x, y = R_MSG.x + 20, R_MSG.y + 16
        draw_text(screen, f"{C.REMITENTES.get(m['remitente'], m['remitente'])}  ·  {C.texto_fecha(m)}", (x, y),
                  size='sm', color='azul')
        ancho_ficha = 0                 # v0.4.14.1: el que escribe, con su posición y su media de hoy
        j_msg = C.jugador_de(estado, m) if m.get('remitente') == 'jugador' else None
        if j_msg is not None:
            ficha = f"{j_msg.posicion} · {j_msg.overall}"
            ancho_ficha = get_font('md').size(ficha)[0] + 16
            draw_text(screen, ficha, (R_MSG.right - 4 - ancho_ficha, y), size='md', color='verde')
        for k, linea in enumerate(_envolver(m['asunto'], R_MSG.width - 40 - ancho_ficha, 'md')[:2]):
            draw_text(screen, linea, (x, y + 26 + k * 30), size='md', color='dorado')
        for k, linea in enumerate(_envolver(C.formatear(estado, m), R_MSG.width - 40)[:LINEAS_CUERPO - (6 if m.get('evento') else 0)]):
            draw_text(screen, linea, (x, y + 96 + k * 23), size='sm', color='blanco')
        acc = m.get('accion') or {}
        if acc.get('pantalla'):
            draw_button(screen, _rect_accion(), acc.get('texto', 'IR'), _rect_accion().collidepoint(mouse_pos))
        evd = m.get('evento')                              # v0.4.10.0: decisión o su resultado
        if evd and evd.get('resuelto') is None:
            for i, r in enumerate(rects_evento(len(evd['opciones']))):
                draw_button(screen, r, evd['opciones'][i], r.collidepoint(mouse_pos) or i == opc)
        elif evd:
            elegido = evd['opciones'][evd['resuelto']] if 0 <= int(evd['resuelto']) < len(evd['opciones']) else "—"
            y0 = _rect_accion().y - 3 * 24
            draw_text(screen, f"Decidiste: {elegido}", (x, y0), size='sm', color='dorado')
            for k, linea in enumerate(_envolver(" · ".join(evd.get('resumen') or []), R_MSG.width - 240)[:4]):
                draw_text(screen, linea, (x, y0 + 24 + k * 22), size='sm', color='azul')
        draw_button(screen, R_BORRAR, "BORRAR", R_BORRAR.collidepoint(mouse_pos))
        aviso = estado.get('correo_aviso_vis')     # v3.5.0: acuerdo de compra que ya no vale
        if aviso and aviso[0] == m.get('id') and aviso[1]:
            draw_text(screen, str(aviso[1])[:60], (_rect_accion().right + 16, _rect_accion().y + 14), size='sm', color='rojo')
        return None
    except Exception as e:
        logger.error(f"Error en correo_screen: {e}", exc_info=True)
        return 'league_screen'
