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
from alpha_football.sanciones import sancionado_en_algo  # noqa: E402

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
        'renovar': pygame.Rect(R_FICHA.x + 20, R_FICHA.bottom - 122, (R_FICHA.width - 50) // 2, 48),
        'lista_prestamo': pygame.Rect(R_FICHA.x + 30 + (R_FICHA.width - 50) // 2, R_FICHA.bottom - 122,
                                      (R_FICHA.width - 50) // 2, 48),
        'prestamos': pygame.Rect(440, 18, 250, 44),     # abre el panel de PRÉSTAMOS
    }


R_OVERLAY_PR = pygame.Rect(140, 120, 1000, 480)


FILAS_PR = 10                    # filas visibles del panel PRÉSTAMOS (el resto con rueda o ↑↓)


def rects_overlay_prestamos(n: int) -> list:
    """[(fila, botón CONCLUIR)] de cada préstamo visible en el overlay."""
    out = []
    for i in range(min(n, FILAS_PR)):
        fila = pygame.Rect(R_OVERLAY_PR.x + 20, R_OVERLAY_PR.y + 70 + i * 38, R_OVERLAY_PR.width - 40, 34)
        out.append((fila, pygame.Rect(fila.right - 150, fila.y + 2, 140, 30)))
    return out


def _filas_prestamos(estado: dict) -> list:
    """[(jugador o acuerdo pendiente, texto)]: los que tienes a préstamo, los tuyos cedidos y los
    acordados que esperan la ventana (estos con CANCELAR)."""
    from alpha_football import prestamos as PR
    from alpha_football.traspasos_pendientes import jornada_apertura
    filas = []
    mi = getattr(estado.get('mi_equipo'), 'nombre', None)
    # con regreso acordado, la fila del jugador pasa a ser la del acuerdo (una sola fila, con CANCELAR)
    fin = {p.get('jugador'): p for p in PR._pendientes(estado) if p.get('tipo') == 'fin'}
    for j in PR.entrantes(estado):
        p = j.prestamo
        if j.nombre_completo in fin:
            filas.append((fin[j.nombre_completo], f"REGRESO ACORDADO · {j.nombre_completo[:22]} · a {p['dueno'][:20]}"
                                                  f" · en J{jornada_apertura(estado)}"))
            continue
        filas.append((j, f"A PRÉSTAMO · {j.nombre_completo[:22]} · de {p['dueno'][:20]} · pagas {100 - p['pct_dueno']}%"
                         f" · vuelve J{p['vuelve'][1]} T{p['vuelve'][0]}"))
    for j, eq in PR.cedidos(estado):
        p = j.prestamo
        if j.nombre_completo in fin:
            filas.append((fin[j.nombre_completo], f"REGRESO ACORDADO · {j.nombre_completo[:22]} · desde {eq.nombre[:20]}"
                                                  f" · en J{jornada_apertura(estado)}"))
            continue
        filas.append((j, f"CEDIDO · {j.nombre_completo[:22]} · en {eq.nombre[:20]} · pagas {p['pct_dueno']}%"
                         f" · vuelve J{p['vuelve'][1]} T{p['vuelve'][0]}"))
    for p in PR._pendientes(estado):
        if p.get('tipo') == 'fin':
            continue
        if mi in (p.get('dueno'), p.get('club')):
            sentido = f"llega de {p['dueno'][:20]}" if p.get('club') == mi else f"se va a {p['club'][:20]}"
            filas.append((p, f"ACORDADO · {str(p.get('jugador'))[:22]} · {sentido} en J{jornada_apertura(estado)}"))
    return filas


def _dibujar_overlay_prestamos(screen, estado: dict, mouse_pos) -> None:
    pygame.draw.rect(screen, (14, 20, 38), R_OVERLAY_PR, border_radius=10)
    pygame.draw.rect(screen, COLORS['dorado'], R_OVERLAY_PR, width=2, border_radius=10)
    draw_text(screen, "PRÉSTAMOS", (R_OVERLAY_PR.x + 20, R_OVERLAY_PR.y + 16), size='lg', color='dorado')
    draw_text(screen, "CONCLUIR PRÉSTAMO: vuelve a su club (ya, o al abrir el mercado)  ·  Esc cierra",
              (R_OVERLAY_PR.x + 250, R_OVERLAY_PR.y + 24), size='sm', color='azul')
    filas = _filas_prestamos(estado)
    if not filas:
        draw_text(screen, "No tienes préstamos.", (R_OVERLAY_PR.x + 20, R_OVERLAY_PR.y + 76), size='md', color='blanco')
    ini = _scroll_prestamos(estado, len(filas))
    visibles = filas[ini:ini + FILAS_PR]
    for (j, texto), (fila, boton) in zip(visibles, rects_overlay_prestamos(len(visibles))):
        pygame.draw.rect(screen, (24, 32, 54), fila, border_radius=4)
        color = 'verde' if texto.startswith("A PRÉSTAMO") else 'dorado' if isinstance(j, dict) else 'azul'
        draw_text(screen, texto, (fila.x + 10, fila.y + 7), size='sm', color=color, shadow=False)
        draw_button(screen, boton, "CANCELAR" if isinstance(j, dict) else "CONCLUIR", boton.collidepoint(mouse_pos))
    msg = estado.get('plantilla_msg')
    if msg and pygame.time.get_ticks() < msg[1]:
        draw_text(screen, str(msg[0])[:100], (R_OVERLAY_PR.x + 20, R_OVERLAY_PR.bottom - 34), size='sm', color='verde')
    elif len(filas) > FILAS_PR:
        draw_text(screen, f"{ini + 1}-{ini + len(visibles)} de {len(filas)}  ·  rueda o ↑↓ para ver más",
                  (R_OVERLAY_PR.x + 20, R_OVERLAY_PR.bottom - 34), size='sm', color='azul', shadow=False)


def _scroll_prestamos(estado: dict, n: int) -> int:
    s = max(0, min(max(0, n - FILAS_PR), int(estado.get('prestamos_scroll', 0) or 0)))
    estado['prestamos_scroll'] = s
    return s


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
    if getattr(jugador, 'prestamo', None):   # a préstamo: no se toca
        return False
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


def _dibujar_ficha(screen, j, titular: bool, mouse_pos, estado: Optional[dict] = None) -> None:
    # v3.5.0: la ficha vive en ui/ficha_jugador (compartida con OFERTAS); aquí solo el estado y los botones
    from alpha_football import sanciones as S
    sanc = "SAN " + " · ".join(f"{c} {S.partidos_sancion(j, c)}" for c in ('liga', 'copa') if S.sancionado(j, c))
    sanc = sanc if S.sancionado_en_algo(j) else ""
    estado_txt = ("Lesionado " + str(j.lesion_partidos) + " p." if j.lesion_partidos > 0
                  else sanc if sanc
                  else "Titular" if titular else "Suplente")
    amar = f"Amarillas: {S.texto_amarillas(j)}"         # línea propia dentro de la ficha (no entra en la de estado)
    if getattr(j, 'transferible', False):
        estado_txt += " · TRANSF."
    if getattr(j, 'pide_salir', False):
        estado_txt += " · PIDE SALIR"                                    # v3.1.0
    try:   # vendido con el mercado cerrado: sigue aquí hasta que se abra la ventana
        from alpha_football.traspasos_pendientes import pendiente_de
        p = pendiente_de(estado or {}, j)
        if p is not None and p.get('tipo') == 'venta':
            estado_txt += f" · VENDIDO (se va J{p['jornada']})"
    except Exception as e_tp:
        logger.error(f"No se pudo leer el traspaso pendiente: {e_tp}")
    p_pr = getattr(j, 'prestamo', None)
    en_lista = False
    try:
        from alpha_football import prestamos as PR
        en_lista = PR.en_lista(estado or {}, j)
    except Exception as e_pr:
        logger.error(f"No se pudo leer la lista de préstamo: {e_pr}")
    try:
        from alpha_football.ui.ficha_jugador import dibujar_ficha
        dibujar_ficha(screen, R_FICHA, j, estado_txt, extra=[(amar, 'azul')])
    except Exception as e:
        logger.error(f"No se pudo dibujar la ficha: {e}")
    # préstamo en su propia línea (la de estado ya viene llena con sanciones y amarillas)
    lineas_pr = ([f"A PRÉSTAMO de {p_pr['dueno']}"[:40],
                  f"Vuelve en la jornada {p_pr['vuelve'][1]} de la temporada {p_pr['vuelve'][0]}"] if p_pr
                 else ["EN LISTA DE PRÉSTAMO"] if en_lista else [])
    for k, txt_pr in enumerate(reversed(lineas_pr)):
        draw_text(screen, txt_pr, (R_FICHA.x + 20, _rects()['renovar'].y - 30 - k * 24), size='sm', color='dorado')
    r = _rects()['transferible']
    texto = ("PIDE SALIR" if getattr(j, 'pide_salir', False)                  # v4.4.0: bloqueado
             else "QUITAR DE TRANSFERIBLES" if getattr(j, 'transferible', False) else "PONER EN TRANSFERIBLES (T)")
    draw_button(screen, r, texto, r.collidepoint(mouse_pos))
    rr = _rects()['renovar']
    draw_button(screen, rr, "RENOVAR (R)", rr.collidepoint(mouse_pos) and not p_pr)
    rl = _rects()['lista_prestamo']
    draw_button(screen, rl, "A PRÉSTAMO" if p_pr else "EN LISTA (P)" if en_lista else "PRÉSTAMO (P)",
                rl.collidepoint(mouse_pos) and not p_pr)


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
                elif ev.button in (4, 5) and estado.get('prestamos_abierto'):      # rueda: scroll del panel
                    estado['prestamos_scroll'] = int(estado.get('prestamos_scroll', 0) or 0) + (-1 if ev.button == 4 else 1)
                elif ev.button in (4, 5) and R_LISTA.collidepoint(mouse_pos):
                    scroll += -1 if ev.button == 4 else 1
            elif ev.type == pygame.KEYDOWN:
                if estado.get('prestamos_abierto'):              # panel PRÉSTAMOS: Esc lo cierra
                    if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                        estado['prestamos_abierto'] = False
                    elif ev.key in (pygame.K_UP, pygame.K_DOWN):
                        estado['prestamos_scroll'] = (int(estado.get('prestamos_scroll', 0) or 0)
                                                      + (-1 if ev.key == pygame.K_UP else 1))
                    continue
                if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    return 'league_screen'
                if ev.key == pygame.K_p:                          # lista de préstamo
                    from alpha_football.prestamos import alternar_lista
                    alternar_lista(estado, jugadores[orden[pos_sel]])
                elif ev.key == pygame.K_UP:
                    pos_sel = max(0, pos_sel - 1)
                elif ev.key == pygame.K_DOWN:
                    pos_sel = min(len(orden) - 1, pos_sel + 1)
                elif ev.key == pygame.K_t:
                    alternar_transferible(jugadores[orden[pos_sel]])
                elif ev.key == pygame.K_r:
                    if getattr(jugadores[orden[pos_sel]], 'prestamo', None):   # a préstamo: no se renueva
                        continue
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

        if click_pos and estado.get('prestamos_abierto'):      # el panel PRÉSTAMOS se come los clics
            filas = _filas_prestamos(estado)
            ini = _scroll_prestamos(estado, len(filas))
            visibles = filas[ini:ini + FILAS_PR]
            for (j_pr, _txt), (_fila, boton) in zip(visibles, rects_overlay_prestamos(len(visibles))):
                if boton.collidepoint(click_pos):
                    from alpha_football.prestamos import terminar, cancelar_pendiente
                    txt = cancelar_pendiente(estado, j_pr) if isinstance(j_pr, dict) else terminar(estado, j_pr)
                    estado['plantilla_msg'] = (txt, pygame.time.get_ticks() + 3000)
            if rects['prestamos'].collidepoint(click_pos):
                estado['prestamos_abierto'] = False
            click_pos = None
        if click_pos:
            if rects['volver'].collidepoint(click_pos):
                return 'league_screen'
            if rects['prestamos'].collidepoint(click_pos):
                estado['prestamos_abierto'], estado['prestamos_scroll'] = True, 0
            elif rects['lista_prestamo'].collidepoint(click_pos):
                from alpha_football.prestamos import alternar_lista
                alternar_lista(estado, jugadores[orden[pos_sel]])
            col = next((c for c, _t, _x in COLUMNAS if c and rect_columna(c).collidepoint(click_pos)), None)
            if col:                                                     # v3.6.0: clic en encabezado
                estado['plantilla_orden'] = (col, not orden_act[1]) if col == orden_act[0] else (col, False)
            elif rects['orden'].collidepoint(click_pos):
                estado['plantilla_orden'] = _siguiente_orden(orden_act)
            elif rects['transferible'].collidepoint(click_pos):
                alternar_transferible(jugadores[orden[pos_sel]])
            elif rects['renovar'].collidepoint(click_pos):
                if not getattr(jugadores[orden[pos_sel]], 'prestamo', None):   # a préstamo: no se renueva
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
        try:
            n_pr = len(_filas_prestamos(estado))
        except Exception as e_npr:
            logger.error(f"No se pudieron contar los préstamos: {e_npr}")
            n_pr = 0
        draw_button(screen, rects['prestamos'], f"PRÉSTAMOS ({n_pr})", rects['prestamos'].collidepoint(mouse_pos))

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
            elif sancionado_en_algo(j):                 # liga o copa
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
        draw_text(screen, "↑↓ elegir · T transferible · R renovar · P préstamo · clic encabezado ordena · verde = titular",
                  (R_LISTA.x + 12, R_LISTA.bottom - 22), size='sm', color='azul', shadow=False)

        _dibujar_ficha(screen, jugadores[orden[pos_sel]], orden[pos_sel] in titulares, mouse_pos, estado)
        if estado.get('prestamos_abierto'):
            _dibujar_overlay_prestamos(screen, estado, mouse_pos)
        return None
    except Exception as e:
        logger.error(f"Error en plantilla_screen: {e}", exc_info=True)
        return 'league_screen'
