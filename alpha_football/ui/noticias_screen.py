# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Noticias (v0.4.23.0). OFICINA > NOTICIAS.
Lista de las noticias vigentes a la izquierda (primero las más recientes, dentro del mismo día las más importantes) y el
detalle a la derecha: imagen 9:16 de la categoría, etiqueta, titular, la fecha real ("sáb 12 sep 2026") y el cuerpo.
Al elegir una noticia se marca leída. Si trae `accion` ({'pantalla', 'texto'}) hay un botón que navega allí.
v0.4.27.0: si la noticia trata de jugadores hay un botón VER FICHA (Enter): abre su ficha en un overlay
(`ui/ficha_jugador.dibujar_ficha`; ← → pasan de un jugador a otro cuando son varios). El cuerpo admite negrita
('**Nombre**') y baja la letra / aprieta las líneas en blanco para que las listas largas quepan.
Teclado: ↑ ↓ elegir · RePág AvPág saltar 10 · Inicio / Fin · Enter ver ficha o ir al botón · Esc volver.
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
R_OVERLAY_FICHA = pygame.Rect(380, 20, 520, 680)       # v0.4.27.0: la ficha de un jugador de la noticia
ALTO_FILA = 56
FILAS_VISIBLES = 10
AVISO_MS = 3000


def _volver() -> pygame.Rect:
    return pygame.Rect(SCREEN_W - 196, 16, 180, 44)


def tiene_jugadores(n: Optional[dict]) -> bool:
    """v0.4.27.0: la noticia trata de al menos un jugador (guarda sus ids)."""
    return bool(n and n.get('jugadores_ids'))


def rect_ver_ficha(n: Optional[dict] = None) -> pygame.Rect:
    """v0.4.27.0: el botón VER FICHA ocupa el sitio del botón de acción; si la noticia trae los dos, va encima."""
    if n and n.get('accion'):
        return pygame.Rect(R_ACCION.x, R_ACCION.y - 56, R_ACCION.width, R_ACCION.height)
    return pygame.Rect(R_ACCION)


def rects_overlay_ficha() -> dict:
    """v0.4.27.0: botones del overlay de la ficha: favoritos, jugador anterior / siguiente y cerrar."""
    r = R_OVERLAY_FICHA
    return {'favorito': pygame.Rect(r.x + 20, r.bottom - 170, r.width - 40, 44),
            'anterior': pygame.Rect(r.x + 20, r.bottom - 58, 70, 44),
            'cerrar': pygame.Rect(r.centerx - 90, r.bottom - 58, 180, 44),
            'siguiente': pygame.Rect(r.right - 90, r.bottom - 58, 70, 44)}


def abrir_ficha(estado: dict, noticia: Optional[dict]) -> bool:
    """v0.4.27.0: abre el overlay con la ficha del primer jugador de la noticia que todavía existe. False (con un
    aviso breve) si ninguno sigue en el juego."""
    if not tiene_jugadores(noticia):
        return False
    try:
        refs = N.jugadores_de(estado, noticia)
    except Exception as e:
        logger.error(f"noticias_screen: no se pudo buscar a los jugadores de la noticia: {e}", exc_info=True)
        refs = []
    if not refs:
        estado['noticias_aviso'] = ("Ese jugador ya no está en el juego.", pygame.time.get_ticks() + AVISO_MS)
        return False
    estado['_noticias_ficha'] = {'refs': refs, 'idx': 0}
    return True


def _dibujar_overlay_ficha(screen, estado: dict, mouse_pos) -> None:
    """v0.4.27.0: velo oscuro, la ficha del jugador y los botones ← CERRAR →."""
    datos = estado.get('_noticias_ficha') or {}
    refs = datos.get('refs') or []
    if not refs:
        return
    idx = max(0, min(int(datos.get('idx', 0) or 0), len(refs) - 1))
    jugador, club = refs[idx]
    velo = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    velo.fill((0, 0, 0, 175))
    screen.blit(velo, (0, 0))
    try:
        from alpha_football.ui.ficha_jugador import dibujar_ficha
        dibujar_ficha(screen, R_OVERLAY_FICHA, jugador, club)
    except Exception as e:
        logger.error(f"noticias_screen: no se pudo dibujar la ficha: {e}", exc_info=True)
    rs = rects_overlay_ficha()
    from alpha_football.ui import ficha_jugador as FJ
    FJ.dibujar_boton_favorito(screen, rs['favorito'], estado, jugador, mouse_pos)      # AGREGAR / QUITAR DE FAVORITOS
    aviso = datos.get('msg')
    pistas = ([f"Jugador {idx + 1} de {len(refs)}", "← → cambiar"] if len(refs) > 1 else []) \
        + (["F favorito"] if FJ.puede_ser_favorito(estado, jugador) else [])
    if aviso and pygame.time.get_ticks() < aviso[1]:
        draw_text(screen, str(aviso[0]), (R_OVERLAY_FICHA.x + 20, rs['cerrar'].y - 30), size='sm', color='verde',
                  shadow=False)
    elif pistas:
        draw_text(screen, "  ·  ".join(pistas), (R_OVERLAY_FICHA.x + 20, rs['cerrar'].y - 30), size='sm',
                  color='azul', shadow=False)
    if len(refs) > 1:
        draw_button(screen, rs['anterior'], "←", rs['anterior'].collidepoint(mouse_pos))
        draw_button(screen, rs['siguiente'], "→", rs['siguiente'].collidepoint(mouse_pos))
    draw_button(screen, rs['cerrar'], "CERRAR (Esc)", rs['cerrar'].collidepoint(mouse_pos))


def _favorito_del_overlay(estado: dict, datos: dict, idx: int) -> None:
    """v0.4.27.0: F / clic en el botón: agrega o quita de favoritos al jugador que muestra la ficha (sin duplicar;
    los de tu plantilla no se siguen) y deja el aviso en la ventana unos segundos."""
    refs = datos.get('refs') or []
    if not refs:
        return
    from alpha_football.ui import ficha_jugador as FJ
    texto = FJ.alternar_favorito(estado, refs[max(0, min(idx, len(refs) - 1))][0])
    if texto:
        datos['msg'] = (texto, pygame.time.get_ticks() + AVISO_MS)


def _manejar_overlay_ficha(estado: dict, tecla=None, click=None) -> None:
    """v0.4.27.0: el overlay de la ficha se come las teclas y los clics: Esc / Enter / clic fuera lo cierran."""
    datos = estado.get('_noticias_ficha') or {}
    n = len(datos.get('refs') or [])
    idx = int(datos.get('idx', 0) or 0)
    rs = rects_overlay_ficha()
    cerrar = False
    if tecla is not None:
        if tecla in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
            cerrar = True
        elif tecla in (pygame.K_LEFT, pygame.K_UP) and n > 1:
            idx = (idx - 1) % n
        elif tecla in (pygame.K_RIGHT, pygame.K_DOWN) and n > 1:
            idx = (idx + 1) % n
        elif tecla == pygame.K_f:
            _favorito_del_overlay(estado, datos, idx)
    elif click is not None:
        if n > 1 and rs['anterior'].collidepoint(click):
            idx = (idx - 1) % n
        elif n > 1 and rs['siguiente'].collidepoint(click):
            idx = (idx + 1) % n
        elif rs['favorito'].collidepoint(click):
            _favorito_del_overlay(estado, datos, idx)
        elif rs['cerrar'].collidepoint(click) or not R_OVERLAY_FICHA.collidepoint(click):
            cerrar = True
    if cerrar:
        estado.pop('_noticias_ficha', None)
    else:
        datos['idx'] = idx


def rect_fila(i: int) -> pygame.Rect:
    """Fila visible i (0-9) de la lista."""
    return pygame.Rect(R_LISTA.x + 8, R_LISTA.y + 48 + i * ALTO_FILA, R_LISTA.width - 16, ALTO_FILA - 4)


def abrir(estado: dict, noticia_id=None) -> str:
    """Abre la pantalla; con `noticia_id` esa noticia queda elegida (y leída)."""
    if noticia_id is not None:
        estado['noticias_sel_id'] = noticia_id
    estado.pop('_noticias_activas', None)
    estado.pop('_noticias_ficha', None)
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


def _cuerpo_ajustado(cuerpo, ancho: int, disponible: int) -> tuple:
    """v0.4.27.0: (tamaño de letra, líneas, alto de una línea en blanco) para que el cuerpo quepa en `disponible`
    px de alto. Prueba 'sm', 'xs' y 'xs' con las líneas en blanco a la mitad: se queda con la primera donde todo
    cabe sin partir ningún renglón; si en ninguna, con la primera donde cabe aunque parta renglones; y si ni así,
    recorta con "…". (Antes: solo 'sm' → 'xs', con las líneas en blanco a altura completa.)"""
    primera = None
    for tam, mitad in (('sm', False), ('xs', False), ('xs', True)):
        f = get_font(tam)
        paso = f.get_linesize()
        blanco = max(1, paso // 2) if mitad else paso
        lineas = V.envolver(cuerpo, f, ancho, 10 ** 4)
        propias = len(V.envolver(cuerpo, f, 10 ** 6, 10 ** 4))        # renglones del texto sin partir ninguno
        alto = sum(paso if ln else blanco for ln in lineas)
        if alto <= disponible:
            if len(lineas) == propias:
                return tam, lineas, blanco
            if primera is None:
                primera = (tam, lineas, blanco)
    if primera is not None:
        return primera
    f = get_font('xs')
    paso, blanco = f.get_linesize(), max(1, f.get_linesize() // 2)
    lineas, alto, quedan = V.envolver(cuerpo, f, ancho, 10 ** 4), 0, []
    for ln in lineas:
        alto += paso if ln else blanco
        if alto > disponible:
            break
        quedan.append(ln)
    if quedan and len(quedan) < len(lineas):
        quedan[-1] = V._con_elipsis(quedan[-1], f, ancho) if quedan[-1] else "…"
    return 'xs', quedan or lineas[:1], blanco


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
    ficha = tiene_jugadores(n)
    if ficha:
        limite = rect_ver_ficha(n).y - 12
    else:
        limite = (R_ACCION.y - 12) if n.get('accion') else (R_TEXTO.bottom - 8)
    # v0.4.27.0: el cuerpo se ajusta al alto que queda (listas con línea en blanco entre jugadores y negrita)
    tam_c, lineas, hueco = _cuerpo_ajustado(n.get('cuerpo'), ancho, limite - y)
    f_c = get_font(tam_c)
    for ln in lineas:
        plano = N.sin_marcas(ln)
        es_seccion = N.NEGRITA not in ln and 0 < len(plano) <= 16 and plano.isupper()   # PORTERO, DEFENSAS...
        V.dibujar_linea(screen, ln, (x, y), size=tam_c, color='dorado' if es_seccion else 'blanco', shadow=False)
        y += f_c.get_linesize() if ln else hueco
    accion = n.get('accion')
    if accion:
        draw_button(screen, R_ACCION, str(accion.get('texto') or "ABRIR"), R_ACCION.collidepoint(mouse_pos))
    if ficha:
        r_f = rect_ver_ficha(n)
        draw_button(screen, r_f, "VER FICHA (Enter)", r_f.collidepoint(mouse_pos))


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
            if estado.get('_noticias_ficha') and ev.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                # v0.4.27.0: con la ficha abierta, ella se queda con las teclas y los clics
                if ev.type == pygame.KEYDOWN:
                    _manejar_overlay_ficha(estado, tecla=ev.key)
                elif ev.button == 1:
                    _manejar_overlay_ficha(estado, click=ev.pos)
                continue
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
                    elegida = lista[max(0, min(sel, total - 1))] if total else None
                    if abrir_ficha(estado, elegida):              # v0.4.27.0: la noticia de un jugador abre su ficha
                        continue
                    accion = elegida.get('accion') if elegida else None
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
                elegida = lista[sel] if total else None
                if tiene_jugadores(elegida) and rect_ver_ficha(elegida).collidepoint(click):
                    abrir_ficha(estado, elegida)                  # v0.4.27.0: botón VER FICHA
                else:
                    accion = elegida.get('accion') if elegida else None
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
        aviso = estado.get('noticias_aviso')
        if aviso and pygame.time.get_ticks() < aviso[1]:
            draw_text(screen, str(aviso[0]), (16, 48), size='sm', color='rojo')
        else:
            draw_text(screen, "↑ ↓ elegir · RePág AvPág saltar · Enter ver ficha / ir al botón · Esc volver", (16, 48),
                      size='sm', color='azul')
        draw_button(screen, _volver(), "VOLVER", _volver().collidepoint(mouse_pos))
        _dibujar_lista(screen, estado, lista, sel, mouse_pos)
        _dibujar_detalle(screen, actual, mouse_pos)
        if estado.get('_noticias_ficha'):
            _dibujar_overlay_ficha(screen, estado, mouse_pos)
        return None
    except Exception as e:
        logger.error(f"Error en noticias_screen: {e}", exc_info=True)
        return 'league_screen'
