# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — NEGOCIAR: buscador de jugadores (Pygame)
v2.7.0: busca en las 10 ligas vivas y los agentes libres por nombre, posición, liga, edad,
media, potencial y precio. Sin buscar muestra los mejores; tras buscar se puede ordenar.
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

from alpha_football import negociacion as N

logger = logging.getLogger(__name__)

POSICIONES = ['TODAS', 'POR', 'DEF', 'MED', 'DEL']
NOMBRE_ORDEN = {'ovr': "MEDIA", 'pot': "POTENCIAL", 'edad': "EDAD", 'precio': "PRECIO"}
# v3.6.0: filtros min/max (un máximo en 0/None = sin tope) + solo agentes libres
FILTROS_BASE = {'nombre': '', 'pos': 'TODAS', 'liga': 'TODAS', 'edad_min': 16, 'edad_max': 40,
                'media_min': 0, 'media_max': 99, 'pot_min': 0, 'pot_max': 99,
                'precio_min': 0, 'precio_max': None, 'solo_libres': False}

# v3.6.0: overlay de filtros (760×420 centrado) y botones de la barra de filtros
R_FILTROS = pygame.Rect(16, 108, 200, 34)
R_SOLO_LIBRES = pygame.Rect(226, 108, 340, 34)
R_OVERLAY = pygame.Rect(260, 150, 760, 420)
FILAS_FILTRO = [("EDAD", 'edad', 1), ("MEDIA", 'media', 1), ("POTENCIAL", 'pot', 1), ("PRECIO", 'precio', 500_000)]
CAMPOS = [f"{base}_{lado}" for _t, base, _p in FILAS_FILTRO for lado in ('min', 'max')]
R_POS_F = pygame.Rect(430, 414, 256, 36)
R_LIGA_F = pygame.Rect(720, 414, 256, 36)
R_LIMPIAR = pygame.Rect(430, 504, 256, 48)
R_APLICAR = pygame.Rect(720, 504, 256, 48)


def rect_campo(clave: str) -> pygame.Rect:
    """v3.6.0: caja tecleable del campo `clave` ('edad_min', 'precio_max'...) en el overlay."""
    base, lado = clave.rsplit('_', 1)
    fila = next((i for i, (_t, b, _p) in enumerate(FILAS_FILTRO) if b == base), 0)
    x = 468 if lado == 'min' else 758
    return pygame.Rect(x, 214 + fila * 50, 180, 36)


def _rect_paso(clave: str, paso: int) -> pygame.Rect:
    """Botón − (paso -1) o + (paso 1) junto a la caja del campo."""
    r = rect_campo(clave)
    return pygame.Rect(r.x - 38, r.y, 34, 36) if paso < 0 else pygame.Rect(r.right + 4, r.y, 34, 36)


R_LISTA = pygame.Rect(16, 190, 820, 506)      # v3.6.0: terminan en y=696 (barra de atajos)
R_FICHA = pygame.Rect(848, 190, 416, 506)
FILA_Y0, FILA_H = 228, 26
FILAS_VISIBLES = (R_LISTA.bottom - 6 - FILA_Y0) // FILA_H
# v3.9.0: MED 358 / POT 406 (antes "EDAD" y "MED" quedaban pegados)
COLUMNAS = [("JUGADOR", 28), ("POS", 250), ("EDAD", 300), ("MED", 358), ("POT", 406),
            ("CLUB", 452), ("LIGA", 636), ("PRECIO", 712)]


def _rects() -> dict:
    r = {
        'volver': pygame.Rect(1116, 12, 148, 40),
        'nombre': pygame.Rect(16, 64, 300, 36),
        'pos': pygame.Rect(326, 64, 170, 36),
        'liga': pygame.Rect(506, 64, 200, 36),
        'buscar': pygame.Rect(946, 64, 150, 36),
        'limpiar': pygame.Rect(1106, 64, 158, 36),
        'fichar': pygame.Rect(R_FICHA.x + 20, R_FICHA.bottom - 64, R_FICHA.width - 40, 48),
    }
    for i, orden in enumerate(N.ORDENES):
        r[f'orden_{orden}'] = pygame.Rect(120 + i * 170, 152, 160, 30)
    return r


def _rect_fila(i: int) -> pygame.Rect:
    return pygame.Rect(R_LISTA.x + 8, FILA_Y0 + i * FILA_H, R_LISTA.width - 16, FILA_H - 2)


def _dinero(v) -> str:
    v = int(v or 0)
    return f"${v / 1_000_000:.1f}M" if v >= 1_000_000 else f"${v / 1000:.0f}K"


def _texto_campo(clave, valor) -> str:
    """v3.6.0: texto de una caja del overlay (máximos en 0/None = SIN TOPE)."""
    v = int(valor or 0) if valor != 'presupuesto' else 0
    if clave.endswith('_max') and v <= 0:
        return "SIN TOPE"
    return f"${v:,}".replace(',', '.') if clave.startswith('precio') else str(v)


def _resumen_filtros(f: dict) -> str:
    """v3.6.0: filtros activos en una línea (junto al botón FILTROS)."""
    partes = []
    for titulo, base, _p in FILAS_FILTRO:
        lo, hi = int(f.get(f'{base}_min', 0) or 0), f.get(f'{base}_max')
        hi = int(hi or 0) if hi != 'presupuesto' else 0
        lo_base, hi_base = int(FILTROS_BASE.get(f'{base}_min', 0) or 0), int(FILTROS_BASE.get(f'{base}_max') or 0)
        if lo != lo_base or hi != hi_base:
            fmt = _dinero if base == 'precio' else str
            partes.append(f"{titulo} {fmt(lo)}-{fmt(hi)}" if hi > 0 else f"{titulo} ≥ {fmt(lo)}")
    return "  ·  ".join(partes) if partes else "Sin filtros de rango"


def _manejar_overlay(estado, b, eventos_teclado: list, click_pos) -> bool:
    """v3.6.0: eventos del overlay de filtros (consume todo). Devuelve True si hay que recalcular."""
    d = b.setdefault('borrador', dict(b['filtros']))
    campo = b.get('campo')

    def cerrar():
        estado['filtros_abierto'] = False
        estado.pop('texto_activo', None)
        b.pop('borrador', None); b.pop('campo', None); b.pop('campo_nuevo', None)

    def aplicar():
        b['filtros'].update(d)
        b['buscado'], b['sel'], b['scroll'] = True, 0, 0
        cerrar()

    for ev in eventos_teclado:
        if ev.key == pygame.K_ESCAPE:
            cerrar()
            return False
        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            aplicar()
            return True
        if ev.key == pygame.K_TAB:
            i = CAMPOS.index(campo) if campo in CAMPOS else -1
            b['campo'] = campo = CAMPOS[(i + 1) % len(CAMPOS)]
            b['campo_nuevo'] = True
        elif campo in CAMPOS and (ev.key == pygame.K_BACKSPACE or (ev.unicode or '').isdigit()):
            try:
                from alpha_football.ui.entrada_monto import editar_valor
                v = d.get(campo)
                v = 0 if v in (None, 'presupuesto') else int(v)
                if b.get('campo_nuevo') and (ev.unicode or '').isdigit():
                    v = 0                                      # el primer dígito reemplaza el valor
                d[campo] = editar_valor(v, ev)
                b['campo_nuevo'] = False
            except Exception as e:
                logger.error(f"No se pudo editar el filtro {campo}: {e}")

    if click_pos:
        if R_APLICAR.collidepoint(click_pos):
            aplicar()
            return True
        if R_LIMPIAR.collidepoint(click_pos):
            nombre, libres = d.get('nombre', ''), d.get('solo_libres', False)
            d.clear(); d.update(FILTROS_BASE); d['nombre'], d['solo_libres'] = nombre, libres
            b['campo'] = None
        elif R_POS_F.collidepoint(click_pos):
            d['pos'] = _ciclar(POSICIONES, d.get('pos', 'TODAS'), 1)
        elif R_LIGA_F.collidepoint(click_pos):
            d['liga'] = _ciclar(_ligas(estado), d.get('liga', 'TODAS'), 1)
        elif not R_OVERLAY.collidepoint(click_pos):
            cerrar()                                   # clic fuera = cerrar sin aplicar
        else:
            b['campo'] = None
            for clave in CAMPOS:
                paso = next((_p for _t, base, _p in FILAS_FILTRO if clave.startswith(base + '_')), 1)
                if rect_campo(clave).collidepoint(click_pos):
                    b['campo'], b['campo_nuevo'] = clave, True
                for signo in (-1, 1):
                    if _rect_paso(clave, signo).collidepoint(click_pos):
                        v = d.get(clave)
                        v = 0 if v in (None, 'presupuesto') else int(v)
                        d[clave] = max(0, v + signo * paso)
                        b['campo'] = clave
    return False


def _dibujar_overlay(screen, estado, b, mouse_pos) -> None:
    """v3.6.0: panel de filtros sobre el buscador."""
    d = b.get('borrador') or b['filtros']
    velo = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    velo.fill((0, 0, 0, 170))
    screen.blit(velo, (0, 0))
    draw_panel(screen, R_OVERLAY)
    pygame.draw.rect(screen, COLORS['dorado'], R_OVERLAY, width=2, border_radius=8)
    draw_text(screen, "FILTROS", (R_OVERLAY.x + 24, R_OVERLAY.y + 16), size='md', color='dorado')
    draw_text(screen, "MÍNIMO", (rect_campo('edad_min').x + 50, 184), size='sm', color='azul')
    draw_text(screen, "MÁXIMO", (rect_campo('edad_max').x + 50, 184), size='sm', color='azul')
    for titulo, base, _p in FILAS_FILTRO:
        y = rect_campo(f'{base}_min').y
        draw_text(screen, titulo, (R_OVERLAY.x + 24, y + 8), size='sm', color='blanco')
        for lado in ('min', 'max'):
            clave = f'{base}_{lado}'
            for signo, txt in ((-1, '-'), (1, '+')):
                rp = _rect_paso(clave, signo)
                draw_button(screen, rp, txt, rp.collidepoint(mouse_pos))
            caja = rect_campo(clave)
            activo = b.get('campo') == clave
            pygame.draw.rect(screen, (15, 22, 40), caja, border_radius=6)
            pygame.draw.rect(screen, COLORS['dorado'] if activo else COLORS['azul'], caja,
                             width=2 if activo else 1, border_radius=6)
            cursor = "|" if activo and (pygame.time.get_ticks() // 500) % 2 == 0 else ""
            s = get_font('sm').render(_texto_campo(clave, d.get(clave)) + cursor, True, COLORS['blanco'])
            screen.blit(s, s.get_rect(center=caja.center))
    draw_text(screen, "POSICIÓN / LIGA", (R_OVERLAY.x + 24, R_POS_F.y + 8), size='sm', color='blanco')
    draw_button(screen, R_POS_F, f"POS: {d.get('pos', 'TODAS')}", R_POS_F.collidepoint(mouse_pos))
    draw_button(screen, R_LIGA_F, f"LIGA: {d.get('liga', 'TODAS')}", R_LIGA_F.collidepoint(mouse_pos))
    draw_text(screen, "Clic en un campo y escribe (Tab siguiente) · Enter aplica · Esc cierra",
              (R_OVERLAY.x + 24, 468), size='sm', color='azul', shadow=False)
    draw_button(screen, R_LIMPIAR, "LIMPIAR", R_LIMPIAR.collidepoint(mouse_pos))
    draw_button(screen, R_APLICAR, "APLICAR (Enter)", R_APLICAR.collidepoint(mouse_pos))


def _ligas(estado) -> list:
    etiquetas = sorted({et for _j, _c, et in N.pool_buscador(estado)})
    return ['TODAS'] + etiquetas


def _estado_busq(estado) -> dict:
    b = estado.get('busq')
    if not isinstance(b, dict):
        b = estado['busq'] = {'filtros': dict(FILTROS_BASE), 'buscado': False, 'orden': 'ovr',
                              'desc': True, 'sel': 0, 'scroll': 0, 'texto_activo': False}
    return b


def _actualizar(estado) -> None:
    """Recalcula la lista: los mejores si no se buscó; si no, filtros + orden."""
    b = _estado_busq(estado)
    pool = N.pool_buscador(estado)
    if not b['buscado']:
        res = N.mejores(pool)
    else:
        f = dict(b['filtros'])
        if f.get('precio_max') == 'presupuesto':
            f['precio_max'] = int(getattr(estado.get('mi_equipo'), 'balance', 0) or 0)
        res = N.ordenar(N.filtrar(pool, f), b['orden'], b['desc'])
    estado['busq_resultados'] = res
    b['sel'] = min(b['sel'], max(0, len(res) - 1))
    b['scroll'] = min(b['scroll'], max(0, len(res) - FILAS_VISIBLES))


def _mensaje(estado, texto, color='verde') -> None:
    estado['busq_msg'] = (texto, pygame.time.get_ticks() + 3000, color)


def _ciclar(lista, valor, paso):
    i = lista.index(valor) if valor in lista else 0
    return lista[(i + paso) % len(lista)]


def _dibujar_ficha(screen, estado, item, mouse_pos) -> None:
    draw_panel(screen, R_FICHA)
    if item is None:
        draw_text(screen, "Sin resultados.", (R_FICHA.x + 20, R_FICHA.y + 20), size='md', color='blanco')
        return
    j, club, etiqueta = item
    mi = estado.get('mi_equipo')
    x, y = R_FICHA.x + 20, R_FICHA.y + 14
    draw_text(screen, f"{j.nombre} {j.apellido}"[:26], (x, y), size='lg', color='dorado')
    y += 40
    draw_text(screen, f"{getattr(club, 'nombre', 'Agente libre')[:26]}  ·  {etiqueta}", (x, y), size='sm', color='azul')
    y += 26
    draw_text(screen, f"{j.posicion}  ·  {j.edad} años  ·  {getattr(j, 'nacionalidad', '') or '—'}", (x, y), size='sm', color='blanco')
    y += 30
    draw_text(screen, f"MEDIA {j.overall}   POTENCIAL {getattr(j, 'potencial', 0) or '?'}", (x, y), size='md', color='verde')
    y += 34
    for nombre, val in (("Ataque", j.ataque), ("Defensa", j.defensa), ("Físico", j.fisico),
                        ("Técnica", j.tecnica), ("Mental", j.mental)):
        draw_text(screen, nombre, (x, y), size='sm', color='blanco')
        barra = pygame.Rect(x + 100, y + 4, 220, 12)
        pygame.draw.rect(screen, (30, 40, 60), barra, border_radius=4)
        lleno = barra.copy(); lleno.width = int(barra.width * max(0, min(99, int(val))) / 99)
        pygame.draw.rect(screen, COLORS['verde'] if val >= 80 else COLORS['dorado'] if val >= 65 else COLORS['rojo'],
                         lleno, border_radius=4)
        draw_text(screen, str(val), (barra.right + 12, y), size='sm', color='blanco')
        y += 26
    y += 8
    precio = N.precio_fichaje(j)
    draw_text(screen, f"Precio {_dinero(precio)}  ·  Tu presupuesto {_dinero(getattr(mi, 'balance', 0))}",
              (x, y), size='sm', color='blanco')
    y += 26
    try:
        from alpha_football.market import puede_fichar
        ok, motivo = puede_fichar(mi, j, precio)
    except Exception:
        ok, motivo = True, "OK"
    if not ok:
        draw_text(screen, motivo[:44], (x, y), size='sm', color='rojo')
    r = _rects()['fichar']
    draw_button(screen, r, "FICHAR" if ok else "NO DISPONIBLE", r.collidepoint(mouse_pos))


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """Buscador de NEGOCIAR. Retorna 'league_screen' al salir o None para seguir aquí."""
    try:
        if estado.get('mi_equipo') is None:
            return 'league_screen'
        b = _estado_busq(estado)
        # v3.9.0: H escribe (no abre la ayuda) solo mientras un campo recibe teclas: el nombre o un
        # campo del overlay de filtros con foco. Los atajos de volumen ya se suprimen en esta pantalla.
        estado['texto_activo'] = bool(b.get('texto_activo')) or bool(estado.get('filtros_abierto') and b.get('campo'))
        # Al entrar (o volver tras un rato) se recalcula: los jugadores cambian de club.
        ahora = pygame.time.get_ticks()
        if 'busq_resultados' not in estado or ahora - int(estado.get('_busq_tick', 0) or 0) > 1000:
            _actualizar(estado)
        estado['_busq_tick'] = ahora
        res = estado['busq_resultados']
        rects = _rects()
        f = b['filtros']
        mouse_pos = pygame.mouse.get_pos()
        click_pos = None
        recalcular = False
        overlay = bool(estado.get('filtros_abierto'))
        teclas_overlay = []

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return 'menu'
            if overlay:                                  # v3.6.0: el overlay consume todo
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    click_pos = ev.pos
                elif ev.type == pygame.KEYDOWN:
                    teclas_overlay.append(ev)
                continue
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if ev.button == 1:
                    click_pos = ev.pos
                elif ev.button in (4, 5) and R_LISTA.collidepoint(mouse_pos):
                    b['scroll'] += -1 if ev.button == 4 else 1
            elif ev.type == pygame.KEYDOWN:
                if b['texto_activo']:
                    if ev.key == pygame.K_BACKSPACE:
                        f['nombre'] = f['nombre'][:-1]
                    elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        b['texto_activo'] = False
                        b['buscado'], recalcular = True, True
                    elif ev.key == pygame.K_ESCAPE:
                        b['texto_activo'] = False
                    elif ev.unicode and ev.unicode.isprintable() and len(f['nombre']) < 24:
                        f['nombre'] += ev.unicode
                    continue
                if ev.key == pygame.K_ESCAPE:
                    return 'league_screen'
                if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    b['buscado'], recalcular = True, True
                elif ev.key == pygame.K_UP:
                    b['sel'] = max(0, b['sel'] - 1)
                elif ev.key == pygame.K_DOWN:
                    b['sel'] = min(max(0, len(res) - 1), b['sel'] + 1)

        if overlay:
            try:
                recalcular = _manejar_overlay(estado, b, teclas_overlay, click_pos)
            except Exception as e:
                logger.error(f"Error en el overlay de filtros: {e}", exc_info=True)
                estado['filtros_abierto'] = False
                estado.pop('texto_activo', None)
            click_pos = None
            f = b['filtros']

        if click_pos:
            b['texto_activo'] = rects['nombre'].collidepoint(click_pos)
            if rects['volver'].collidepoint(click_pos):
                return 'league_screen'
            if rects['buscar'].collidepoint(click_pos):
                b['buscado'], recalcular = True, True
            elif rects['limpiar'].collidepoint(click_pos):
                b['filtros'] = f = dict(FILTROS_BASE)
                b['buscado'], b['sel'], b['scroll'], recalcular = False, 0, 0, True
            elif rects['pos'].collidepoint(click_pos):
                f['pos'] = _ciclar(POSICIONES, f['pos'], 1)
            elif rects['liga'].collidepoint(click_pos):
                f['liga'] = _ciclar(_ligas(estado), f['liga'], 1)
            elif R_FILTROS.collidepoint(click_pos):          # v3.6.0
                estado['filtros_abierto'] = True
                estado['texto_activo'] = True
                b['borrador'] = dict(FILTROS_BASE, **f)
                b['campo'] = None
            elif R_SOLO_LIBRES.collidepoint(click_pos):
                f['solo_libres'] = not f.get('solo_libres', False)
                b['buscado'], b['sel'], b['scroll'], recalcular = True, 0, 0, True
            elif rects['fichar'].collidepoint(click_pos) and res:
                # v2.9.0: fichar ya no es directo: se negocia con el club y con el jugador.
                j, club, _et = res[b['sel']]
                try:
                    from alpha_football.market import puede_fichar
                    ok, motivo = puede_fichar(estado['mi_equipo'], j, 0)
                except Exception:
                    ok, motivo = True, ""
                if ok:
                    return N.iniciar_negociacion(estado, j, club, 'fichaje', 'buscador_screen')
                _mensaje(estado, motivo, 'rojo')
            else:
                if b['buscado']:
                    for orden in N.ORDENES:
                        if rects[f'orden_{orden}'].collidepoint(click_pos):
                            b['desc'] = (not b['desc']) if b['orden'] == orden else (orden != 'edad')
                            b['orden'], recalcular = orden, True
                for i in range(FILAS_VISIBLES):
                    if b['scroll'] + i < len(res) and _rect_fila(i).collidepoint(click_pos):
                        b['sel'] = b['scroll'] + i

        if recalcular:
            _actualizar(estado)
            res = estado['busq_resultados']
        b['sel'] = max(0, min(b['sel'], len(res) - 1))
        if b['sel'] < b['scroll']:
            b['scroll'] = b['sel']
        elif b['sel'] >= b['scroll'] + FILAS_VISIBLES:
            b['scroll'] = b['sel'] - FILAS_VISIBLES + 1
        b['scroll'] = max(0, min(b['scroll'], max(0, len(res) - FILAS_VISIBLES)))

        # --- Dibujo ---
        draw_gradient_bg(screen)
        mi = estado['mi_equipo']
        draw_text(screen, "NEGOCIAR · BUSCADOR DE JUGADORES", (16, 10), size='md', color='dorado')
        draw_text(screen, f"{mi.nombre}  ·  Presupuesto {_dinero(mi.balance)}  ·  Plantilla {len(mi.jugadores)}",
                  (16, 38), size='sm', color='verde')
        draw_button(screen, rects['volver'], "VOLVER", rects['volver'].collidepoint(mouse_pos))

        caja = rects['nombre']
        pygame.draw.rect(screen, (15, 22, 40), caja, border_radius=6)
        pygame.draw.rect(screen, COLORS['dorado'] if b['texto_activo'] else COLORS['azul'], caja, width=2, border_radius=6)
        cursor = "|" if b['texto_activo'] and (pygame.time.get_ticks() // 500) % 2 == 0 else ""
        texto = f['nombre'] + cursor if (f['nombre'] or b['texto_activo']) else "Nombre del jugador..."
        draw_text(screen, texto, (caja.x + 10, caja.y + 8), size='sm',
                  color='blanco' if f['nombre'] else 'azul', shadow=False)
        draw_button(screen, rects['pos'], f"POS: {f['pos']}", rects['pos'].collidepoint(mouse_pos))
        draw_button(screen, rects['liga'], f"LIGA: {f['liga']}", rects['liga'].collidepoint(mouse_pos))
        draw_button(screen, rects['buscar'], "BUSCAR", rects['buscar'].collidepoint(mouse_pos))
        draw_button(screen, rects['limpiar'], "LIMPIAR", rects['limpiar'].collidepoint(mouse_pos))
        # v3.6.0: FILTROS (overlay) + toggle SOLO AGENTES LIBRES + resumen de rangos activos
        draw_button(screen, R_FILTROS, "FILTROS...", R_FILTROS.collidepoint(mouse_pos))
        libres = bool(f.get('solo_libres', False))
        draw_button(screen, R_SOLO_LIBRES, "    SOLO AGENTES LIBRES", libres or R_SOLO_LIBRES.collidepoint(mouse_pos))
        chk = pygame.Rect(R_SOLO_LIBRES.x + 8, R_SOLO_LIBRES.centery - 7, 14, 14)
        pygame.draw.rect(screen, COLORS['verde'] if libres else COLORS['azul'], chk, width=0 if libres else 1)
        draw_text(screen, _resumen_filtros(f)[:90], (R_SOLO_LIBRES.right + 14, R_FILTROS.y + 8), size='sm',
                  color='blanco', shadow=False)

        if b['buscado']:
            draw_text(screen, "ORDENAR:", (16, 156), size='sm', color='dorado')
            for orden in N.ORDENES:
                r = rects[f'orden_{orden}']
                flecha = (" ▼" if b['desc'] else " ▲") if b['orden'] == orden else ""
                draw_button(screen, r, NOMBRE_ORDEN[orden] + flecha, r.collidepoint(mouse_pos) or b['orden'] == orden)
            draw_text(screen, f"{len(res)} resultados", (820, 158), size='sm', color='azul')
        else:
            draw_text(screen, f"Los {N.N_MEJORES} mejores jugadores disponibles · usa los filtros y BUSCAR",
                      (16, 158), size='sm', color='azul')

        draw_panel(screen, R_LISTA)
        for titulo, x in COLUMNAS:
            draw_text(screen, titulo, (x, R_LISTA.y + 8), size='sm', color='dorado')
        for i in range(FILAS_VISIBLES):
            k = b['scroll'] + i
            if k >= len(res):
                break
            j, club, etiqueta = res[k]
            fila = _rect_fila(i)
            if k == b['sel']:
                pygame.draw.rect(screen, (30, 45, 75), fila, border_radius=4)
                pygame.draw.rect(screen, COLORS['dorado'], fila, width=1, border_radius=4)
            valores = [f"{j.nombre[:1]}. {j.apellido}"[:24], j.posicion, str(j.edad), str(j.overall),
                       str(getattr(j, 'potencial', 0) or '?'), getattr(club, 'nombre', 'Libre')[:20],
                       etiqueta, _dinero(N.precio_fichaje(j))]
            for (_t, x), v in zip(COLUMNAS, valores):
                draw_text(screen, v, (x, fila.y + 2), size='sm', color='blanco', shadow=False)
        if not res:
            draw_text(screen, "Ningún jugador cumple los filtros.", (R_LISTA.x + 20, FILA_Y0), size='md', color='blanco')

        _dibujar_ficha(screen, estado, res[b['sel']] if res else None, mouse_pos)
        if estado.get('filtros_abierto'):
            _dibujar_overlay(screen, estado, b, mouse_pos)

        msg = estado.get('busq_msg')
        if msg and pygame.time.get_ticks() < msg[1]:
            s = get_font('md').render(msg[0], True, COLORS['bg'])
            caja = s.get_rect(center=(SCREEN_W // 2, 40)).inflate(40, 16)
            pygame.draw.rect(screen, COLORS.get(msg[2], COLORS['verde']), caja, border_radius=8)
            screen.blit(s, s.get_rect(center=caja.center))
        return None
    except Exception as e:
        logger.error(f"Error en buscador_screen: {e}", exc_info=True)
        return 'league_screen'
