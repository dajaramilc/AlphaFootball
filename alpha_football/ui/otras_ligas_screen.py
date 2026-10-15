# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Pantalla "OTRAS LIGAS" (v2.3.5).

Muestra las ligas de la carrera (v3.7.0: 1ª y 2ª de los 8 países = 16), todas simuladas en
vivo. A la izquierda el selector país + división (primero tu país), a la derecha la tabla y
los partidos de la última jornada jugada de la liga elegida.
"""
from __future__ import annotations

import logging
from typing import Optional

import pygame

from alpha_football.ui.theme import SCREEN_W, COLORS, draw_gradient_bg, draw_panel, draw_text, draw_button, get_font
from alpha_football.ui.menu import PAISES_DISPONIBLES, TIPOS_LIGA
from alpha_football import paises as _paises

logger = logging.getLogger(__name__)


def ligas_disponibles(estado: dict) -> list:
    """[(etiqueta, liga)] de las 16 ligas (v3.7.0); primero las del país del user."""
    liga_user = estado.get('liga')
    tipo_user = getattr(liga_user, 'tipo', None)
    primeras = estado.get('primera_division') or {}
    segunda = estado.get('segunda_division') or {}
    pais = {p['liga_id']: p['nombre'] for p in PAISES_DISPONIBLES}
    orden = sorted(TIPOS_LIGA, key=lambda t: t != tipo_user)
    res = []
    for tipo in orden:
        for div, mapa in ((1, primeras), (2, segunda)):
            liga = mapa.get(tipo)
            if liga is not None:
                marca = "  (tu liga)" if liga is liga_user else ""
                res.append((f"{pais.get(tipo, tipo)} {div}ª{marca}", liga))
    return res


FILA = 24   # v3.7.0: alto de fila de la tabla (12 equipos + 6 resultados caben en el panel)


def rect_division(k: int) -> pygame.Rect:
    """v3.7.0: pestaña 1ª (k=0) / 2ª (k=1) arriba de la lista de países."""
    return pygame.Rect(34 + k * 158, 122, 152, 40)


def rect_pais(i: int) -> pygame.Rect:
    """v3.7.0: fila del país i (8 países)."""
    return pygame.Rect(34, 176 + i * 54, 310, 46)


def rect_tab_copas() -> pygame.Rect:
    """v3.8.0: pestaña COPAS (Champions y Libertadores) arriba a la derecha."""
    return pygame.Rect(SCREEN_W - 244, 56, 220, 44)


COPAS_OTRAS = ('champions', 'libertadores', 'intercontinental')     # v0.4.26.0: + Intercontinental
# v3.9.0: rects expuestos (ayuda H). VOLVER con alto 44 en ambas vistas (antes 50: tocaba la barra).
R_LISTA = pygame.Rect(24, 110, 330, 520)
R_PANEL = pygame.Rect(370, 110, SCREEN_W - 394, 520)
R_VOLVER = pygame.Rect(24, 646, 220, 44)


def _nombre_copa(tipo: str) -> str:
    from alpha_football import competiciones as CP
    return "Intercontinental" if tipo == 'intercontinental' else CP.NOMBRE_COPA[tipo]


def _texto_intercontinental(estado: dict) -> str:
    """v0.4.26.0: línea corta de la Intercontinental para la lista (última edición o la próxima final)."""
    from alpha_football import intercontinental as INT, calendario as CAL
    reg = (estado.get('datos_carrera') or {}).get('intercontinental') or {}
    if reg.get('jugado') and reg.get('campeon'):
        return f"Campeón {reg.get('anio')}: {reg['campeon']}"
    f = INT.fecha(estado) if reg.get('anio') else None
    return f"Final: {CAL.texto_fecha(f, False)}" if f else "Se juega en diciembre"


def _render_intercontinental(screen, estado: dict, panel: pygame.Rect) -> None:
    """v0.4.26.0: la final del año (o la última jugada) y el historial de campeones."""
    from alpha_football import intercontinental as INT, calendario as CAL
    from alpha_football.ui import copa_screen as S
    reg = (estado.get('datos_carrera') or {}).get('intercontinental') or {}
    x, ancho = panel.x + 16, panel.width - 32
    draw_text(screen, "COPA INTERCONTINENTAL", (x, panel.y + 10), size='md', color='dorado')
    S._txt(screen, f"Campeón de la Libertadores vs campeón de Europa · partido único en diciembre · "
                   f"{INT._mm(INT.PREMIO_CAMPEON)} al campeón y {INT._mm(INT.PREMIO_FINALISTA)} al finalista",
           (x, panel.y + 46), 16, 'azul', ancho)
    y = panel.y + 90
    if reg.get('anio'):
        draw_text(screen, f"EDICIÓN {reg['anio']}", (x, y), size='sm', color='dorado')
        S._txt(screen, f"{reg['local']}  ·  campeón de la Libertadores", (x, y + 32), 18, 'blanco', ancho)
        S._txt(screen, f"{reg['visitante']}  ·  campeón de Europa", (x, y + 60), 18, 'blanco', ancho)
        if reg.get('jugado'):
            S._txt(screen, f"Resultado: {INT.marcador(reg)}", (x, y + 98), 17, 'azul', ancho)
            S._txt(screen, f"CAMPEÓN: {reg.get('campeon')}", (x, y + 126), 20, 'verde', ancho)
        else:
            f = INT.fecha(estado)
            S._txt(screen, f"Final: {CAL.texto_fecha(f) if f else 'por definir'}", (x, y + 98), 17, 'azul', ancho)
    else:
        S._txt(screen, "Todavía no se conocen los finalistas: la Libertadores define al primero.", (x, y), 17,
               'blanco', ancho)
        europa = INT._campeon_champions(estado)
        if europa:
            S._txt(screen, f"Campeón de Europa vigente: {europa}", (x, y + 30), 17, 'azul', ancho)
    historial = [h for h in reg.get('historial') or [] if isinstance(h, dict)]
    y = panel.y + 290
    draw_text(screen, "HISTORIAL", (x, y), size='sm', color='dorado')
    if not historial:
        S._txt(screen, "Todavía no se jugó ninguna edición.", (x, y + 30), 16, 'blanco', ancho)
    for k, h in enumerate(reversed(historial[-7:])):
        S._txt(screen, f"{h.get('anio')}  ·  {h.get('campeon')}  ·  {h.get('marcador', '')}", (x, y + 30 + k * 26), 16,
               'blanco', ancho)


def _render_copas(screen, estado: dict, mouse_pos, click_pos, teclas: list) -> None:
    """v3.8.0: estado de las dos copas: fase actual y tabla/grupos o llaves.
    v0.4.26.0: + la Copa Intercontinental (su final y el historial)."""
    from alpha_football import competiciones as CP
    from alpha_football.ui import copa_screen as S
    sel = estado.get('otras_ligas_copa_sel') if estado.get('otras_ligas_copa_sel') in COPAS_OTRAS else 'champions'
    for k in teclas:
        if k in (pygame.K_UP, pygame.K_DOWN):
            paso = -1 if k == pygame.K_UP else 1
            sel = COPAS_OTRAS[(COPAS_OTRAS.index(sel) + paso) % len(COPAS_OTRAS)]
    draw_text(screen, "Las copas internacionales se juegan en paralelo a tu carrera  ·  ↑↓ copa  ·  C ligas",
              (32, 74), size='sm', color='azul')
    lista = R_LISTA
    draw_panel(screen, lista)
    draw_text(screen, "COPAS INTERNACIONALES", (34, 124), size='sm', color='dorado')
    user = getattr(estado.get('mi_equipo'), 'nombre', '')
    reg_int = (estado.get('datos_carrera') or {}).get('intercontinental') or {}
    for i, tipo in enumerate(COPAS_OTRAS):
        r = rect_pais(i)
        if click_pos and r.collidepoint(click_pos):
            sel = tipo
        activo = tipo == sel
        hover = r.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (30, 45, 75) if (activo or hover) else (15, 22, 40), r, border_radius=6)
        pygame.draw.rect(screen, COLORS['dorado'] if activo else COLORS['azul'], r,
                         width=3 if activo else 1, border_radius=6)
        if tipo == 'intercontinental':
            tuya = bool(user) and user in (reg_int.get('local'), reg_int.get('visitante')) and not reg_int.get('jugado')
        else:
            tuya = CP.tipo_copa_user(estado) == tipo
        draw_text(screen, f"{_nombre_copa(tipo).upper()}{'  (tu copa)' if tuya else ''}", (r.x + 12, r.y + 10),
                  size='sm', color='dorado' if activo else ('verde' if hover else 'blanco'))
    for i, tipo in enumerate(COPAS_OTRAS):          # resumen de cada copa debajo del selector
        y = rect_pais(len(COPAS_OTRAS)).y + i * 70
        draw_text(screen, _nombre_copa(tipo), (40, y), size='sm', color='azul')
        if tipo == 'intercontinental':
            estado_txt = _texto_intercontinental(estado)
        else:
            c = CP.copa(estado, tipo) or {}
            estado_txt = f"Campeón: {c['campeon']}" if c.get('campeon') else f"En juego: {c.get('fase_actual', '—')}"
        S._txt(screen, estado_txt, (40, y + 24), 15, 'blanco', 300)
    estado['otras_ligas_copa_sel'] = sel

    panel = R_PANEL
    draw_panel(screen, panel)
    if sel == 'intercontinental':
        _render_intercontinental(screen, estado, panel)
        return
    c = CP.copa(estado, sel)
    titulo = "CHAMPIONS LEAGUE" if sel == 'champions' else "COPA LIBERTADORES"
    draw_text(screen, f"{titulo} · T{estado.get('temporada', 1)}", (panel.x + 16, panel.y + 10), size='md', color='dorado')
    if not c:
        draw_text(screen, "La copa todavía no se sorteó.", (panel.x + 16, panel.y + 60), size='sm', color='blanco')
        return
    fase = c.get('fase_actual', '')
    sub = f"Campeón: {c['campeon']}" if c.get('campeon') else f"Fase actual: {fase}"
    if c.get('llaves'):
        sub += "  ·  llaves (global y penales)"
    else:
        sub += "  ·  " + ("tabla de la fase de liga" if sel == 'champions' else "grupos (pasan 1º y 2º)")
    draw_text(screen, sub, (panel.x + 16, panel.y + 44), size='sm', color='azul')
    S.dibujar_resumen_copa(screen, pygame.Rect(panel.x + 12, panel.y + 76, panel.width - 24, panel.height - 86),
                           c, user, compacto=True)


def _tipos_en_orden(ligas: list) -> list:
    orden = []
    for _e, l in ligas:
        t = getattr(l, 'tipo', None)
        if t not in orden:
            orden.append(t)
    return orden


def _indice(ligas: list, tipo, division: int) -> int:
    """v3.7.0: índice de (tipo, división) en `ligas`; si esa división no existe, la otra del país."""
    alt = None
    for i, (_e, l) in enumerate(ligas):
        if getattr(l, 'tipo', None) == tipo:
            if (getattr(l, 'division', 1) or 1) == division:
                return i
            alt = i if alt is None else alt
    return alt if alt is not None else 0


def _mover_pais(ligas: list, sel: int, paso: int) -> int:
    tipos = _tipos_en_orden(ligas)
    l = ligas[sel][1]
    t = getattr(l, 'tipo', None)
    i = tipos.index(t) if t in tipos else 0
    return _indice(ligas, tipos[(i + paso) % len(tipos)], getattr(l, 'division', 1) or 1)


def _cambiar_division(ligas: list, sel: int) -> int:
    l = ligas[sel][1]
    return _indice(ligas, getattr(l, 'tipo', None), 2 if (getattr(l, 'division', 1) or 1) == 1 else 1)


def _cupo_copa(liga) -> int:
    """v3.8.0: cupos reales de copa de esa 1ª (motor de competiciones)."""
    try:
        from alpha_football.ui.copa_screen import cupos_copa
        return cupos_copa(getattr(liga, 'tipo', ''))
    except Exception:
        return 3


def _clave_tabla(eq):
    return (getattr(eq, 'puntos', 0), getattr(eq, 'gf', 0) - getattr(eq, 'gc', 0), getattr(eq, 'gf', 0))


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    try:
        ligas = ligas_disponibles(estado)
        if not ligas:
            return "league_screen"
        liga_user = estado.get('liga')
        mi_equipo = estado.get('mi_equipo')

        # Por defecto: la otra división de tu país (lo primero que no es tu liga)
        if 'otras_ligas_sel' not in estado:
            estado['otras_ligas_sel'] = next((i for i, (_e, l) in enumerate(ligas) if l is not liga_user), 0)
        sel = max(0, min(int(estado['otras_ligas_sel']), len(ligas) - 1))

        mouse_pos = pygame.mouse.get_pos()
        click_pos = None
        teclas = []
        modo_copas = bool(estado.get('otras_ligas_copas'))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "menu"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                click_pos = event.pos
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    estado.pop('otras_ligas_sel', None)
                    return "league_screen"
                teclas.append(event.key)
                if event.key == pygame.K_c:                  # v3.8.0: C alterna LIGAS / COPAS
                    modo_copas = not modo_copas
                    continue
                if modo_copas:
                    continue
                # v3.7.0: flechas arriba/abajo cambian de país; izquierda/derecha o Tab, de división.
                if event.key in (pygame.K_UP, pygame.K_DOWN):
                    sel = _mover_pais(ligas, sel, -1 if event.key == pygame.K_UP else 1)
                elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB):
                    sel = _cambiar_division(ligas, sel)

        # v3.8.0: pestaña COPAS
        if click_pos and rect_tab_copas().collidepoint(click_pos):
            modo_copas = not modo_copas
            click_pos = None
        estado['otras_ligas_copas'] = modo_copas

        draw_gradient_bg(screen)
        draw_text(screen, "OTRAS LIGAS", (32, 20), size='xl', color='dorado')
        r_copas = rect_tab_copas()
        pygame.draw.rect(screen, COLORS['azul'] if modo_copas else ((30, 45, 75) if r_copas.collidepoint(mouse_pos)
                                                                     else (15, 22, 40)), r_copas, border_radius=8)
        pygame.draw.rect(screen, COLORS['dorado'] if modo_copas else COLORS['azul'], r_copas, width=2, border_radius=8)
        _s = get_font('sm').render("VER LIGAS" if modo_copas else "COPAS", True,
                                   COLORS['bg'] if modo_copas else COLORS['blanco'])
        screen.blit(_s, _s.get_rect(center=r_copas.center))
        if modo_copas:
            _render_copas(screen, estado, mouse_pos, click_pos, [k for k in teclas if k != pygame.K_c])
            btn_volver = R_VOLVER
            draw_button(screen, btn_volver, "VOLVER", btn_volver.collidepoint(mouse_pos))
            if click_pos and btn_volver.collidepoint(click_pos):
                estado.pop('otras_ligas_sel', None)
                return "league_screen"
            return None
        draw_text(screen, f"Las {len(ligas)} ligas se juegan en paralelo a tu carrera  ·  ↑↓ país  ·  "
                          f"←→ división  ·  C copas", (32, 74), size='sm', color='azul')

        # --- v3.7.0: selector división (1ª / 2ª) + país (8 filas) ---
        lista = R_LISTA
        draw_panel(screen, lista)
        div_sel = getattr(ligas[sel][1], 'division', 1) or 1
        for k, div in enumerate((1, 2)):
            r = rect_division(k)
            activo = div == div_sel
            hover = r.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (30, 45, 75) if (activo or hover) else (15, 22, 40), r, border_radius=6)
            pygame.draw.rect(screen, COLORS['dorado'] if activo else COLORS['azul'], r,
                             width=3 if activo else 1, border_radius=6)
            draw_text(screen, f"{div}ª DIVISIÓN", (r.x + 22, r.y + 9), size='sm',
                      color='dorado' if activo else ('verde' if hover else 'blanco'))
            if click_pos and r.collidepoint(click_pos) and not activo:
                sel = _cambiar_division(ligas, sel)
        tipo_sel = getattr(ligas[sel][1], 'tipo', None)
        div_sel = getattr(ligas[sel][1], 'division', 1) or 1
        tipo_user = getattr(liga_user, 'tipo', None)
        nombres_pais = {p['liga_id']: p['nombre'] for p in PAISES_DISPONIBLES}
        for i, tipo in enumerate(_tipos_en_orden(ligas)):
            r = rect_pais(i)
            activo = tipo == tipo_sel
            hover = r.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (30, 45, 75) if (activo or hover) else (15, 22, 40), r, border_radius=6)
            pygame.draw.rect(screen, COLORS['dorado'] if activo else COLORS['azul'], r,
                             width=3 if activo else 1, border_radius=6)
            marca = "  (tu país)" if tipo == tipo_user else ""
            draw_text(screen, f"{nombres_pais.get(tipo, tipo)}{marca}", (r.x + 12, r.y + 10), size='sm',
                      color='dorado' if activo else ('verde' if hover else 'blanco'))
            if click_pos and r.collidepoint(click_pos):
                sel = _indice(ligas, tipo, div_sel)
        estado['otras_ligas_sel'] = sel

        # --- Tabla de la liga elegida ---
        etiqueta, liga = ligas[sel]
        panel = R_PANEL
        draw_panel(screen, panel)
        es_segunda = getattr(liga, 'division', 1) == 2
        jugados = [p for p in getattr(liga, 'calendario', []) if p.jugado]
        ult_jornada = max((p.jornada for p in jugados), default=0)
        nombre_l = _paises.nombre_liga(getattr(liga, 'tipo', ''), getattr(liga, 'division', 1) or 1)   # v3.7.0
        draw_text(screen, (nombre_l or getattr(liga, 'nombre', etiqueta)).upper()[:48],
                  (panel.x + 16, panel.y + 10), size='md', color='dorado')
        draw_text(screen, f"Jornadas jugadas: {ult_jornada}/{getattr(liga, 'num_jornadas', '?')}  ·  "
                          f"{'Top 2 ascienden' if es_segunda else f'Top {_cupo_copa(liga)} a copa · últimos 2 descienden'}",
                  (panel.x + 16, panel.y + 42), size='sm', color='azul')

        headers = ["#", "Equipo", "PJ", "PG", "PE", "PP", "GF", "GC", "DG", "PTS", "DT"]   # v3.4.0: + DT
        xs = [0, 34, 300, 345, 390, 435, 480, 525, 570, 615, 672]
        tx, ty = panel.x + 16, panel.y + 76
        for h, dx in zip(headers, xs):
            draw_text(screen, h, (tx + dx, ty), size='sm', color='dorado')
        pygame.draw.line(screen, COLORS['azul'], (tx, ty + 22), (tx + 650, ty + 22), 1)
        equipos = sorted(liga.equipos, key=_clave_tabla, reverse=True)
        n = len(equipos)
        for idx, eq in enumerate(equipos, 1):
            y = ty + 28 + (idx - 1) * FILA   # v3.7.0: 12 equipos → filas más bajas
            if es_segunda:
                col = 'verde' if idx <= 2 else 'blanco'
            else:
                col = 'verde' if idx <= _cupo_copa(liga) else ('rojo' if idx >= n - 1 else 'blanco')
            if mi_equipo is not None and eq.id == mi_equipo.id:
                pygame.draw.rect(screen, (30, 45, 75), pygame.Rect(tx - 6, y - 3, 850, FILA - 2), border_radius=4)
            dg = eq.gf - eq.gc
            try:  # v3.4.0: DT de cada club (el tuyo eres tú)
                from alpha_football.entrenadores import dt_de
                if mi_equipo is not None and eq.id == mi_equipo.id:
                    nom_dt = "Tú"
                else:
                    nom_dt = ((dt_de(estado, eq) or {}).get('nombre') or "—")[:18]
            except Exception as e_dt:
                logger.error(f"Error al leer el DT de {eq.nombre}: {e_dt}")
                nom_dt = "—"
            vals = [str(idx), eq.nombre[:24], str(eq.pj), str(eq.pg), str(eq.pe), str(eq.pp),
                    str(eq.gf), str(eq.gc), f"+{dg}" if dg > 0 else str(dg), str(eq.puntos), nom_dt]
            for v, dx in zip(vals, xs):
                draw_text(screen, v, (tx + dx, y), size='sm', color=col)

        # --- Resultados de la última jornada jugada (debajo de la tabla) ---
        ry = ty + 28 + n * FILA + 12
        pygame.draw.line(screen, COLORS['azul'], (tx, ry - 6), (tx + 650, ry - 6), 1)
        draw_text(screen, f"RESULTADOS JORNADA {ult_jornada}" if ult_jornada else "SIN PARTIDOS AÚN",
                  (tx, ry), size='sm', color='dorado')
        por_id = {e.id: e for e in liga.equipos}
        for k, p in enumerate([p for p in jugados if p.jornada == ult_jornada]):
            loc, vis = por_id.get(p.local_id), por_id.get(p.visitante_id)
            draw_text(screen, f"{getattr(loc, 'nombre', '?')[:22]}  {p.goles_local} - {p.goles_visitante}  "
                              f"{getattr(vis, 'nombre', '?')[:22]}",
                      (tx + (k % 2) * 430, ry + 24 + (k // 2) * 22), size='sm', color='blanco')

        btn_volver = R_VOLVER
        draw_button(screen, btn_volver, "VOLVER", btn_volver.collidepoint(mouse_pos))
        if click_pos and btn_volver.collidepoint(click_pos):
            estado.pop('otras_ligas_sel', None)
            return "league_screen"
        return None
    except Exception as e:
        logger.error(f"Error en otras_ligas_screen: {e}", exc_info=True)
        return "league_screen"
