# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — PANTALLA POST-PARTIDO (v4.1.0)
Antes de CONTINUAR (partido en vivo o simulado): pestañas CALIFICACIONES (notas de ambos equipos
con goles, asistencias, tarjetas, lesiones y cambios) y TABLA (liga: tu posición y si subiste o
bajaste; copa: tu grupo / fase de liga o la llave a la que pasas). La usan match_screen y
prepartido_screen: arman los datos con `armar_datos` y dibujan con `render`.
"""
from __future__ import annotations

import logging
from typing import Optional

import pygame

from alpha_football.partido_ctx import clave, minutos_jugados, nota_en_vivo

try:
    from alpha_football.ui.theme import SCREEN_W, COLORS, get_font, draw_gradient_bg, draw_panel, draw_button, draw_text
except Exception:
    SCREEN_W = 1280
    COLORS = {'verde': (0, 255, 136), 'rojo': (255, 68, 68), 'azul': (0, 191, 255), 'dorado': (255, 215, 0),
              'blanco': (255, 255, 255), 'panel': (20, 26, 46)}
    def get_font(size): return pygame.font.Font(None, 24)
    def draw_gradient_bg(screen): screen.fill((10, 14, 26))
    def draw_panel(screen, rect): pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=8)
    def draw_button(screen, rect, text, hover): pygame.draw.rect(screen, (20, 26, 46), rect); return rect
    def draw_text(screen, text, pos, size='md', color='blanco', shadow=True): pass

logger = logging.getLogger(__name__)

R_TAB_CALIF = pygame.Rect(SCREEN_W // 2 - 380, 128, 240, 34)
R_TAB_TABLA = pygame.Rect(SCREEN_W // 2 - 120, 128, 240, 34)
R_TAB_RES = pygame.Rect(SCREEN_W // 2 + 140, 128, 240, 34)
PESTANAS = ('calificaciones', 'tabla', 'resultados')
R_PANEL = pygame.Rect(40, 172, 1200, 462)
R_CONTINUAR = pygame.Rect(SCREEN_W // 2 - 120, 648, 240, 44)

TIPOS_LINEA = ('gol', 'amarilla', 'roja', 'lesion', 'cambio', 'penal_fallado')
_ORDEN_POS = {'POR': 0, 'DEF': 1, 'MED': 2, 'DEL': 3}
FILAS_VISIBLES = 16
FILA_H = 26


def _nombre(j) -> str:
    return getattr(j, 'nombre_completo', None) or getattr(j, 'apellido', None) or '?'


def fmt_minuto(minuto) -> str:
    """El minuto como se lee en la tele: la adición (solo al final) va como 90+X'."""
    try:
        m = int(minuto or 0)
    except (TypeError, ValueError):
        return f"{minuto}'"
    return f"90+{m - 90}'" if m > 90 else f"{m}'"


def _rgb(nombre, defecto=(255, 255, 255)):
    return COLORS.get(nombre, defecto)


# ------------------------------------------------------------------ datos
def linea_de_tiempo(eventos: list, local, visitante) -> list:
    """Goles, tarjetas, lesiones, cambios y penales fallados en orden: {'minuto','tipo','lado','texto'}."""
    out = []
    for ev in eventos or []:
        try:
            t = ev.get('tipo')
            if t not in TIPOS_LINEA:
                continue
            lado = ev.get('lado') or ('l' if ev.get('equipo_id') == getattr(local, 'id', None) else 'v')
            j = ev.get('jugador')
            nom = _nombre(j) if j is not None else (ev.get('detalle') or '')
            if t == 'gol':
                texto = nom + (" (penal)" if ev.get('penal') else
                               f" (asist. {getattr(ev['asistente'], 'apellido', '')})" if ev.get('asistente') else "")
            elif t == 'roja':
                texto = nom + (" (2ª amarilla)" if ev.get('motivo') == 'doble amarilla' else " (roja directa)")
            elif t == 'lesion':
                texto = f"{nom} (lesión)"
            elif t == 'cambio':
                sale = ev.get('sale_obj') or ev.get('sale')
                texto = f"Entra {getattr(j, 'apellido', nom)}, sale {getattr(sale, 'apellido', None) or _nombre(sale)}"
            elif t == 'penal_fallado':
                texto = f"{nom} falla un penal"
            else:
                texto = nom
            out.append({'minuto': int(ev.get('minuto', 0) or 0), 'tipo': t, 'lado': lado, 'texto': texto})
        except Exception as e:
            logger.error(f"linea_de_tiempo: evento inválido {ev.get('tipo')}: {e}")
    out.sort(key=lambda x: x['minuto'])
    return out


def filas_calificaciones(ctx, notas: dict, lado: str) -> list:
    """Titulares (por puesto) y luego los que entraron, con nota, goles, asistencias y tarjetas."""
    if ctx is None:
        return []
    mins = minutos_jugados(ctx)
    inc = {i['jugador_id']: i['tipo'] for i in ctx.incidencias}
    filas = []
    for k, ld in ctx.lado_jugador.items():
        if ld != lado or (mins.get(k, 0) <= 0 and k not in ctx.fuera):
            continue
        j = ctx.jugadores.get(k)
        entro = int(ctx.entrada.get(k, 0))
        filas.append({
            'clave': k, 'nombre': _nombre(j), 'pos': ctx.posicion.get(k, getattr(j, 'posicion', 'MED')),
            'nota': float(notas.get(k, nota_en_vivo(ctx, k))), 'g': ctx.goles.get(k, 0), 'a': ctx.asist.get(k, 0),
            'amar': ctx.amarillas.get(k, 0), 'roja': inc.get(k) == 'sancion', 'lesion': inc.get(k) == 'lesion',
            'entro': entro if entro > 0 else None,
            'salio': ctx.salida.get(k) if k in ctx.salida and k not in ctx.fuera else None,
        })
    filas.sort(key=lambda f: (f['entro'] is not None, f['entro'] or 0, _ORDEN_POS.get(f['pos'], 9)))
    return filas


def posicion_liga(liga, equipo_id) -> int:
    """Posición (1 = primero) por puntos, diferencia y goles a favor; 0 si no está."""
    try:
        orden = sorted(getattr(liga, 'equipos', []) or [],
                       key=lambda e: (getattr(e, 'puntos', 0), getattr(e, 'gf', 0) - getattr(e, 'gc', 0),
                                      getattr(e, 'gf', 0)), reverse=True)
        return next((i + 1 for i, e in enumerate(orden) if e.id == equipo_id), 0)
    except Exception as e:
        logger.error(f"posicion_liga: {e}")
        return 0


def armar_datos(estado: dict, modo: str, local, visitante, gl: int, gv: int, ctx, notas: dict,
                eventos: list, penales: Optional[str] = None, pos_antes: Optional[int] = None) -> dict:
    """Guarda en estado['postpartido'] lo que muestra la pantalla y deja la pestaña en CALIFICACIONES."""
    try:
        filas_l = filas_calificaciones(ctx, notas or {}, 'l')
        filas_v = filas_calificaciones(ctx, notas or {}, 'v')
        todas = filas_l + filas_v
        fig = max(todas, key=lambda f: f['nota']) if todas else None
        datos = {
            'modo': modo or 'liga',
            'titulo': (f"{getattr(local, 'corto', None) or local.nombre} {gl} - {gv} "
                       f"{getattr(visitante, 'corto', None) or visitante.nombre}"
                       + (f"  ({penales} PEN)" if penales else "")),
            'local': getattr(local, 'nombre', ''), 'visitante': getattr(visitante, 'nombre', ''),
            'filas_l': filas_l, 'filas_v': filas_v,
            'figura': (fig['nombre'], fig['nota']) if fig else None,
            'linea': linea_de_tiempo(eventos, local, visitante),
            'pos_antes': pos_antes,
            'resultados_ref': _ref_resultados(estado, modo, local, visitante),
        }
    except Exception as e:
        logger.error(f"armar_datos del post-partido: {e}")
        datos = {'modo': modo or 'liga', 'titulo': f"{gl} - {gv}", 'filas_l': [], 'filas_v': [],
                 'figura': None, 'linea': [], 'pos_antes': pos_antes, 'local': '', 'visitante': ''}
    estado['postpartido'] = datos
    estado['postpartido_tab'] = 'calificaciones'
    estado['postpartido_scroll'] = 0
    return datos


def _ref_resultados(estado: dict, modo: str, local, visitante) -> Optional[dict]:
    """Qué fecha mostrar en RESULTADOS: la jornada de liga del partido o la fecha de copa.
    Se guarda la referencia (no los marcadores) porque en copa el resto de la fecha puede
    jugarse después de armar el post-partido."""
    try:
        if modo == 'copa':
            p = estado.get('partido_copa_dict') or {}
            from alpha_football import competiciones as K
            t = p.get('tipo') or K.tipo_copa_user(estado)
            return {'tipo': 'copa', 'copa': t, 'fecha': int(p['fecha'])} if t and p.get('fecha') is not None else None
        if modo == 'liga':
            liga = estado.get('liga')
            ids = {getattr(local, 'id', None), getattr(visitante, 'id', None)}
            p = next((x for x in reversed(getattr(liga, 'calendario', []) or [])
                      if {x.local_id, x.visitante_id} == ids and x.jugado), None)
            return {'tipo': 'liga', 'jornada': int(p.jornada)} if p is not None else None
    except Exception as e:
        logger.error(f"No se pudo ubicar la fecha del partido para RESULTADOS: {e}")
    return None


def resultados_fecha(estado: dict, ref: Optional[dict]) -> list:
    """[(local, goles_l, goles_v, visitante, jugado, es_del_user)] de la jornada/fecha del partido."""
    if not ref:
        return []
    user = getattr(estado.get('mi_equipo'), 'nombre', '')
    try:
        if ref.get('tipo') == 'liga':
            liga = estado.get('liga')
            nombres = {e.id: e.nombre for e in getattr(liga, 'equipos', []) or []}
            return [(nombres.get(p.local_id, '?'), p.goles_local, p.goles_visitante, nombres.get(p.visitante_id, '?'),
                     bool(p.jugado), user in (nombres.get(p.local_id), nombres.get(p.visitante_id)))
                    for p in getattr(liga, 'calendario', []) or [] if p.jornada == ref['jornada']]
        from alpha_football import competiciones as K
        c = K.copa(estado, ref.get('copa')) or {}
        return [(p['local'], p.get('gl', 0), p.get('gv', 0), p['visitante'], bool(p.get('jugado')),
                 user in (p['local'], p['visitante']))
                for p in c.get('partidos', []) if p.get('fecha') == ref.get('fecha')]
    except Exception as e:
        logger.error(f"No se pudieron leer los resultados de la fecha: {e}")
        return []


# ------------------------------------------------------------------ dibujo
def dibujar_icono(screen, tipo: str, centro: tuple) -> None:
    """Íconos dibujados (la fuente no tiene emojis): gol, amarilla, roja, lesión, cambio, penal fallado."""
    try:
        x, y = int(centro[0]), int(centro[1])
        if tipo == 'gol':
            pygame.draw.circle(screen, (255, 255, 255), (x, y), 7)
            pygame.draw.circle(screen, (20, 20, 20), (x, y), 7, 2)
            pygame.draw.circle(screen, (20, 20, 20), (x, y), 2)
        elif tipo in ('amarilla', 'roja'):
            col = (255, 215, 0) if tipo == 'amarilla' else (230, 40, 40)
            pygame.draw.rect(screen, col, pygame.Rect(x - 5, y - 7, 10, 14), border_radius=2)
        elif tipo == 'lesion':
            pygame.draw.circle(screen, (255, 255, 255), (x, y), 8)
            pygame.draw.rect(screen, (230, 40, 40), pygame.Rect(x - 5, y - 1, 10, 3))
            pygame.draw.rect(screen, (230, 40, 40), pygame.Rect(x - 1, y - 5, 3, 10))
        elif tipo == 'cambio':
            pygame.draw.polygon(screen, (0, 220, 120), [(x - 7, y), (x - 3, y - 7), (x + 1, y)])
            pygame.draw.polygon(screen, (230, 60, 60), [(x - 1, y), (x + 3, y + 7), (x + 7, y)])
        elif tipo == 'penal_fallado':
            pygame.draw.line(screen, (230, 40, 40), (x - 6, y - 6), (x + 6, y + 6), 3)
            pygame.draw.line(screen, (230, 40, 40), (x - 6, y + 6), (x + 6, y - 6), 3)
    except Exception as e:
        logger.error(f"No se pudo dibujar el ícono {tipo}: {e}")


def _color_nota(n: float) -> str:
    return 'verde' if n >= 8.0 else 'blanco' if n >= 6.5 else 'dorado' if n >= 5.5 else 'rojo'


def _dibujar_calificaciones(screen, datos: dict, scroll: int) -> None:
    draw_panel(screen, R_PANEL)
    ancho = (R_PANEL.width - 30) // 2
    for i, (titulo, filas) in enumerate(((datos.get('local', ''), datos.get('filas_l', [])),
                                         (datos.get('visitante', ''), datos.get('filas_v', [])))):
        x0 = R_PANEL.x + 10 + i * (ancho + 10)
        draw_text(screen, str(titulo)[:40].upper(), (x0 + 6, R_PANEL.y + 8), size='sm', color='azul')
        y = R_PANEL.y + 38
        for f in filas[scroll:scroll + FILAS_VISIBLES]:
            draw_text(screen, f['pos'], (x0 + 6, y), size='sm', color='azul', shadow=False)
            nombre = f['nombre'][:24]
            if f['entro']:
                nombre = f"{nombre[:18]} ({fmt_minuto(f['entro'])})"
            draw_text(screen, nombre, (x0 + 54, y), size='sm', color='blanco', shadow=False)
            ix = x0 + 360
            for _ in range(min(3, f['g'])):
                dibujar_icono(screen, 'gol', (ix, y + 10)); ix += 18
            if f['a']:
                draw_text(screen, f"A{f['a']}", (ix - 4, y), size='sm', color='verde', shadow=False); ix += 28
            if f['amar'] and not f['roja']:
                dibujar_icono(screen, 'amarilla', (ix, y + 10)); ix += 16
            if f['roja']:
                dibujar_icono(screen, 'roja', (ix, y + 10)); ix += 16
            if f['lesion']:
                dibujar_icono(screen, 'lesion', (ix, y + 10)); ix += 20
            if f['salio']:
                dibujar_icono(screen, 'cambio', (ix, y + 10))
            nota = f"{f['nota']:.1f}"
            draw_text(screen, nota, (x0 + ancho - 14 - get_font('sm').size(nota)[0], y), size='sm',
                      color=_color_nota(f['nota']), shadow=False)
            y += FILA_H
    total = max(len(datos.get('filas_l', [])), len(datos.get('filas_v', [])))
    if total > FILAS_VISIBLES:
        draw_text(screen, "↑ ↓ para ver más", (R_PANEL.right - 170, R_PANEL.bottom - 26), size='sm', color='azul')


def _dibujar_tabla_liga(screen, estado: dict, datos: dict) -> None:
    liga = estado.get('liga')
    mi = estado.get('mi_equipo')
    draw_panel(screen, R_PANEL)
    if liga is None or not getattr(liga, 'equipos', None):
        draw_text(screen, "Sin tabla disponible.", (R_PANEL.x + 20, R_PANEL.y + 20), size='md')
        return
    orden = sorted(liga.equipos, key=lambda e: (getattr(e, 'puntos', 0), getattr(e, 'gf', 0) - getattr(e, 'gc', 0),
                                                getattr(e, 'gf', 0)), reverse=True)
    cols = [('#', 20), ('CLUB', 70), ('PJ', 520), ('GF', 610), ('GC', 700), ('DG', 790), ('PTS', 880)]
    y = R_PANEL.y + 10
    for t, dx in cols:
        draw_text(screen, t, (R_PANEL.x + dx, y), size='sm', color='azul', shadow=False)
    fila_h = min(34, (R_PANEL.height - 44) // max(1, len(orden)))
    y += 30
    pos_antes = datos.get('pos_antes')
    for i, eq in enumerate(orden):
        es_mio = mi is not None and eq.id == mi.id
        if es_mio:
            pygame.draw.rect(screen, (30, 60, 50), pygame.Rect(R_PANEL.x + 8, y - 3, R_PANEL.width - 16, fila_h))
        col = 'verde' if es_mio else 'blanco'
        vals = [str(i + 1), str(eq.nombre)[:34], str(getattr(eq, 'pj', 0)), str(getattr(eq, 'gf', 0)),
                str(getattr(eq, 'gc', 0)), str(getattr(eq, 'gf', 0) - getattr(eq, 'gc', 0)), str(getattr(eq, 'puntos', 0))]
        for (t, dx), v in zip(cols, vals):
            draw_text(screen, v, (R_PANEL.x + dx, y), size='sm', color=col, shadow=False)
        if es_mio and pos_antes:
            cx, cy = R_PANEL.x + 960, y + 10
            if i + 1 < pos_antes:
                pygame.draw.polygon(screen, _rgb('verde'), [(cx - 7, cy + 5), (cx + 7, cy + 5), (cx, cy - 6)])
            elif i + 1 > pos_antes:
                pygame.draw.polygon(screen, _rgb('rojo'), [(cx - 7, cy - 5), (cx + 7, cy - 5), (cx, cy + 6)])
            else:
                pygame.draw.rect(screen, _rgb('azul'), pygame.Rect(cx - 7, cy - 2, 14, 4))
            txt = "Subes" if i + 1 < pos_antes else "Bajas" if i + 1 > pos_antes else "Sin cambios"
            draw_text(screen, f"{txt} (antes {pos_antes}º)", (cx + 14, y), size='sm', color=col, shadow=False)
        y += fila_h


def _dibujar_tabla_copa(screen, estado: dict) -> None:
    draw_panel(screen, R_PANEL)
    try:
        from alpha_football import competiciones as K
        from alpha_football.ui import copa_screen as CS
        t = K.tipo_copa_user(estado)
        if not t:
            draw_text(screen, "Sin copa esta temporada.", (R_PANEL.x + 20, R_PANEL.y + 20), size='md')
            return
        c, user = K.copa(estado, t), K._nombre_user(estado)
        draw_text(screen, K.linea_estado_user(estado)[:90], (R_PANEL.x + 16, R_PANEL.y + 10), size='md', color='dorado')
        interior = pygame.Rect(R_PANEL.x + 10, R_PANEL.y + 48, R_PANEL.width - 20, R_PANEL.height - 58)
        if c.get('llaves'):
            CS.dibujar_llaves(screen, interior, c, user, compacto=True)
        elif t == 'champions':
            CS.dibujar_tabla_liga(screen, interior, c, user, compacto=True)
        else:
            CS.dibujar_grupos(screen, interior, c, user, compacto=True, solo=CS.grupo_de(c, user))
    except Exception as e:
        logger.error(f"No se pudo dibujar la tabla de copa del post-partido: {e}")


def _dibujar_resultados(screen, estado: dict, datos: dict) -> None:
    """Los demás partidos de la jornada (liga) o de la fecha (copa); el tuyo resaltado."""
    draw_panel(screen, R_PANEL)
    ref = datos.get('resultados_ref') or {}
    filas = resultados_fecha(estado, ref)
    titulo = (f"RESULTADOS DE LA JORNADA {ref['jornada']}" if ref.get('tipo') == 'liga'
              else "RESULTADOS DE LA FECHA DE COPA" if ref else "RESULTADOS")
    draw_text(screen, titulo, (R_PANEL.x + 20, R_PANEL.y + 10), size='md', color='dorado')
    if not filas:
        draw_text(screen, "No hay otros resultados para mostrar.", (R_PANEL.x + 20, R_PANEL.y + 56), size='md')
        return
    fila_h, y0 = 30, R_PANEL.y + 50
    por_col = max(1, (R_PANEL.bottom - 10 - y0) // fila_h)
    cols = 1 if len(filas) <= por_col else 2
    ancho = (R_PANEL.width - 40) // cols
    f = get_font('sm')
    for i, (loc, gl, gv, vis, jugado, mio) in enumerate(filas[:por_col * cols]):
        cx = R_PANEL.x + 20 + (i // por_col) * ancho + ancho // 2
        y = y0 + (i % por_col) * fila_h
        if mio:
            pygame.draw.rect(screen, (30, 60, 50), pygame.Rect(cx - ancho // 2 + 4, y - 3, ancho - 8, fila_h - 2),
                             border_radius=4)
        col = 'verde' if mio else 'blanco'
        marcador = f"{gl} - {gv}" if jugado else "vs"
        corte = max(8, (ancho // 2 - 60) // 9)                 # nombres que entran a cada lado
        izq, der = str(loc)[:corte], str(vis)[:corte]
        draw_text(screen, izq, (cx - 42 - f.size(izq)[0], y), size='sm', color=col, shadow=False)
        draw_text(screen, marcador, (cx - f.size(marcador)[0] // 2, y), size='sm',
                  color='dorado' if jugado else 'azul', shadow=False)
        draw_text(screen, der, (cx + 42, y), size='sm', color=col, shadow=False)


def render(screen, estado: dict, mouse_pos, click_pos, teclas: list) -> Optional[str]:
    """Dibuja el post-partido. Devuelve 'continuar' con Enter/Espacio o CONTINUAR; None si sigue."""
    try:
        datos = estado.get('postpartido') or {}
        con_tabla = datos.get('modo') != 'amistoso'
        tab = estado.get('postpartido_tab', 'calificaciones')
        total = max(len(datos.get('filas_l', [])), len(datos.get('filas_v', [])))
        for k in teclas or []:
            if k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return 'continuar'
            if k in (pygame.K_LEFT, pygame.K_RIGHT) and con_tabla:
                i = PESTANAS.index(tab) if tab in PESTANAS else 0
                tab = PESTANAS[(i + (1 if k == pygame.K_RIGHT else -1)) % len(PESTANAS)]
            elif k == pygame.K_DOWN:
                estado['postpartido_scroll'] = min(max(0, total - FILAS_VISIBLES), estado.get('postpartido_scroll', 0) + 1)
            elif k == pygame.K_UP:
                estado['postpartido_scroll'] = max(0, estado.get('postpartido_scroll', 0) - 1)
        if click_pos:
            if R_CONTINUAR.collidepoint(click_pos):
                return 'continuar'
            if R_TAB_CALIF.collidepoint(click_pos):
                tab = 'calificaciones'
            elif R_TAB_TABLA.collidepoint(click_pos) and con_tabla:
                tab = 'tabla'
            elif R_TAB_RES.collidepoint(click_pos) and con_tabla:
                tab = 'resultados'
        estado['postpartido_tab'] = tab

        draw_gradient_bg(screen)
        titulo = datos.get('titulo', '')
        tw = get_font('xl').size(titulo)[0]
        draw_text(screen, titulo, (SCREEN_W // 2 - tw // 2, 30), size='xl', color='verde')
        if datos.get('figura'):
            fig = f"FIGURA: {datos['figura'][0]} ({datos['figura'][1]:.1f})"
            draw_text(screen, fig, (SCREEN_W // 2 - get_font('sm').size(fig)[0] // 2, 94), size='sm', color='dorado')
        draw_button(screen, R_TAB_CALIF, "CALIFICACIONES", tab == 'calificaciones')
        if con_tabla:
            draw_button(screen, R_TAB_TABLA, "TABLA" if datos.get('modo') != 'copa' else "COPA", tab == 'tabla')
            draw_button(screen, R_TAB_RES, "RESULTADOS", tab == 'resultados')
        if tab == 'resultados' and con_tabla:
            _dibujar_resultados(screen, estado, datos)
        elif tab == 'tabla' and con_tabla:
            if datos.get('modo') == 'copa':
                _dibujar_tabla_copa(screen, estado)
            else:
                _dibujar_tabla_liga(screen, estado, datos)
        else:
            _dibujar_calificaciones(screen, datos, estado.get('postpartido_scroll', 0))
        draw_button(screen, R_CONTINUAR, "CONTINUAR", True)
        return None
    except Exception as e:
        logger.error(f"Error en el post-partido: {e}")
        return 'continuar' if teclas else None
