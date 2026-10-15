# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Finanzas (Pygame)
v2.9.0: saldo, ingresos y gastos de la temporada (taquilla, patrocinio, salarios,
fichajes, ventas, premios), proyección al cierre, masa salarial y aviso de quiebra.
v4.7.0: valor del club, barra de masa salarial y espaldarazo financiero (antes en OBJETIVOS);
los contratos que vencen ya no se muestran aquí.
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

from alpha_football import finanzas as F

logger = logging.getLogger(__name__)

R_SALDO = pygame.Rect(16, 76, 400, 300)
R_LIBRO = pygame.Rect(432, 76, 832, 300)
R_ESP = pygame.Rect(16, 392, 1248, 304)        # v4.7.0: espaldarazo (antes contratos); termina en y=696
R_ESPALDARAZO = pygame.Rect(R_ESP.x + 20, R_ESP.y + 150, 460, 44)
R_CAMISETAS = pygame.Rect(R_ESP.x + 608, R_ESP.y + 96, 624, 164)     # v0.4.26.0: venta de camisetas (mitad derecha de R_ESP)
R_OVERLAY = pygame.Rect(SCREEN_W // 2 - 360, 180, 720, 340)
R_HISTORIAL = pygame.Rect(664, 12, 440, 40)       # v0.4.27.0: botón HISTORIAL DE TRANSACCIONES (junto a VOLVER)
R_LISTA = pygame.Rect(16, 76, 1248, 620)          # v0.4.27.0: la lista del historial; termina en y=696
FILAS_HISTORIAL, ALTO_FILA = 17, 30


def _rects_espaldarazo() -> list:
    return [pygame.Rect(R_OVERLAY.x + 20, R_OVERLAY.y + 70 + i * 64, R_OVERLAY.width - 40, 54) for i in range(3)]


def _volver() -> pygame.Rect:
    return pygame.Rect(1116, 12, 148, 40)


def _texto_fecha_mov(mov: dict) -> str:
    """'sáb 15 ago 2026' (la fecha real del reloj del juego); sin ella (partida sin reloj), 'T2 · J7'."""
    try:
        if mov.get('fecha'):
            from datetime import date
            from alpha_football.calendario import texto_fecha
            return texto_fecha(date.fromisoformat(str(mov['fecha'])))
    except Exception as e:
        logger.debug(f"finanzas_screen: fecha ilegible en un movimiento: {e}")
    return f"T{mov.get('temporada', '?')} · J{mov.get('jornada', '?')}"


def _ajustar(texto: str, ancho: int) -> str:
    """Recorta `texto` (con …) para que entre en `ancho` píxeles con la fuente chica."""
    fuente = get_font('sm')
    if fuente.size(texto)[0] <= ancho:
        return texto
    while texto and fuente.size(texto + "…")[0] > ancho:
        texto = texto[:-1]
    return texto.rstrip(" ·") + "…"


def _paso_scroll(ev) -> int:
    """Cuántas filas mueve este evento la lista del historial (rueda, flechas, RePág/AvPág, Inicio/Fin)."""
    if ev.type == pygame.MOUSEWHEEL:
        return -int(ev.y) * 3
    if ev.type == pygame.KEYDOWN:
        return {pygame.K_UP: -1, pygame.K_DOWN: 1, pygame.K_PAGEUP: -FILAS_HISTORIAL,
                pygame.K_PAGEDOWN: FILAS_HISTORIAL, pygame.K_HOME: -10 ** 9, pygame.K_END: 10 ** 9}.get(ev.key, 0)
    return 0


def _dibujar_historial(screen: pygame.Surface, estado: dict, mi, liga, mouse_pos) -> None:
    """v0.4.27.0: HISTORIAL DE TRANSACCIONES: cada movimiento de dinero del club (fecha real, concepto, importe),
    el más reciente arriba y con scroll."""
    movs = F.transacciones(estado)
    maximo = max(0, len(movs) - FILAS_HISTORIAL)
    desde = max(0, min(maximo, int(estado.get('historial_trans_scroll', 0) or 0)))
    estado['historial_trans_scroll'] = desde
    draw_gradient_bg(screen)
    draw_text(screen, "HISTORIAL DE TRANSACCIONES", (16, 12), size='lg', color='dorado')
    draw_text(screen, f"{mi.nombre}  ·  {liga.nombre}  ·  Temporada {estado.get('temporada', 1)}",
              (16, 48), size='sm', color='verde')
    draw_button(screen, _volver(), "VOLVER", _volver().collidepoint(mouse_pos))
    draw_panel(screen, R_LISTA)
    x, y = R_LISTA.x + 20, R_LISTA.y + 12
    draw_text(screen, "FECHA", (x, y), size='sm', color='azul')
    draw_text(screen, "CONCEPTO", (x + 250, y), size='sm', color='azul')
    cuenta = f"{len(movs)} movimiento{'s' if len(movs) != 1 else ''}"
    draw_text(screen, cuenta, (R_LISTA.right - 40 - get_font('sm').size(cuenta)[0], y), size='sm', color='azul')
    y += 34
    if not movs:
        draw_text(screen, "Aún no hay movimientos: aparecerán aquí desde el próximo pago, cobro o fichaje.",
                  (x, y + 10), size='sm', color='blanco')
    for i, mov in enumerate(movs[desde:desde + FILAS_HISTORIAL]):
        fila_y = y + i * ALTO_FILA
        importe = int(mov.get('importe', 0) or 0)
        draw_text(screen, _texto_fecha_mov(mov), (x, fila_y), size='sm', color='blanco')
        draw_text(screen, _ajustar(str(mov.get('concepto', '')), 780), (x + 250, fila_y), size='sm', color='blanco')
        txt = ("+" if importe >= 0 else "") + _m(importe)
        ancho_txt = get_font('sm').size(txt)[0]
        draw_text(screen, txt, (R_LISTA.right - 60 - ancho_txt, fila_y), size='sm',
                  color='verde' if importe >= 0 else 'rojo')
    if maximo > 0:      # barra de desplazamiento
        pista = pygame.Rect(R_LISTA.right - 16, y, 6, FILAS_HISTORIAL * ALTO_FILA)
        alto_dedo = max(24, int(pista.height * FILAS_HISTORIAL / len(movs)))
        dedo = pygame.Rect(pista.x, pista.y + int((pista.height - alto_dedo) * desde / maximo), pista.width, alto_dedo)
        pygame.draw.rect(screen, (30, 40, 60), pista, border_radius=3)
        pygame.draw.rect(screen, COLORS['azul'], dedo, border_radius=3)
    draw_text(screen, "↑ ↓ RePág AvPág o la rueda del ratón desplazan  ·  T o ESC para volver a FINANZAS",
              (x, R_LISTA.bottom - 30), size='sm', color='azul')


def _m(v) -> str:
    v = int(v or 0)
    signo = "−" if v < 0 else ""
    v = abs(v)
    return f"{signo}${v / 1_000_000:.1f}M" if v >= 1_000_000 else f"{signo}${v / 1000:.0f}K"


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """Retorna 'league_screen' al salir o None para seguir aquí."""
    try:
        mi, liga = estado.get('mi_equipo'), estado.get('liga')
        if mi is None or liga is None:
            return 'league_screen'
        from alpha_football import directiva as D
        from alpha_football.ui.objetivos_screen import barra, color_barra_tope, _velo
        obj = D.definir_objetivo(estado) or {}
        mouse_pos = pygame.mouse.get_pos()
        abierto = bool(estado.get('espaldarazo_abierto'))
        historial = bool(estado.get('historial_trans_abierto'))      # v0.4.27.0
        nivel = None
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return 'menu'
            clic = ev.pos if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 else None
            esc = ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE)
            tecla_t = ev.type == pygame.KEYDOWN and ev.key == pygame.K_t
            if historial:     # v0.4.27.0: HISTORIAL DE TRANSACCIONES (T, ESC o VOLVER cierran; scroll con rueda/flechas)
                if esc or tecla_t or (clic and _volver().collidepoint(clic)):
                    estado.pop('historial_trans_abierto', None)
                    estado.pop('historial_trans_scroll', None)
                    historial = False
                else:
                    paso = _paso_scroll(ev)
                    if paso:
                        estado['historial_trans_scroll'] = max(0, int(estado.get('historial_trans_scroll', 0) or 0) + paso)
                continue
            if not abierto and (tecla_t or (clic and R_HISTORIAL.collidepoint(clic))):
                estado['historial_trans_abierto'] = historial = True
                estado['historial_trans_scroll'] = 0
                continue
            if abierto:       # overlay del espaldarazo (1/2/3 o clic; ESC cierra)
                if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    nivel = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2}[ev.key]
                elif esc:
                    estado.pop('espaldarazo_abierto', None)
                    abierto = False
                elif clic:
                    nivel = next((i for i, r in enumerate(_rects_espaldarazo()) if r.collidepoint(clic)), None)
                continue
            if esc or (clic and _volver().collidepoint(clic)):
                estado.pop('espaldarazo_msg', None)
                return 'league_screen'
            if clic and R_ESPALDARAZO.collidepoint(clic) and not obj.get('espaldarazo'):
                estado['espaldarazo_abierto'] = abierto = True
        if abierto and nivel is not None:
            try:
                _ok, estado['espaldarazo_msg'] = D.pedir_espaldarazo(estado, nivel)
            except Exception as e_esp:
                logger.error(f"Error al pedir el espaldarazo: {e_esp}")
            estado.pop('espaldarazo_abierto', None)
            abierto = False
            obj = D.definir_objetivo(estado) or {}

        if historial:     # v0.4.27.0: la pantalla del historial ocupa FINANZAS entera
            _dibujar_historial(screen, estado, mi, liga, mouse_pos)
            return None

        lib = F.libro(estado)
        n = max(1, int(liga.num_jornadas or 10))
        restantes = max(0, n - sum(1 for p in liga.calendario if p.jugado and mi.id in (p.local_id, p.visitante_id)))
        medio = F.presupuesto_medio(liga)
        masa = F.masa_salarial(mi, estado)
        try:   # v4.9.0: el patrocinio por jornada sale de los contratos
            from alpha_football import patrocinios as _P
            patro_jornada = _P.cobro_jornada(estado)
        except Exception:
            patro_jornada = int(medio * F.PATROCINIO_FRAC / n)
        por_jornada = patro_jornada + int(medio * F.TAQUILLA_FRAC / n) - masa // n
        proyeccion = mi.balance + por_jornada * restantes
        dc = estado.get('datos_carrera') or {}

        draw_gradient_bg(screen)
        draw_text(screen, "FINANZAS", (16, 12), size='lg', color='dorado')
        draw_text(screen, f"{mi.nombre}  ·  {liga.nombre}  ·  Temporada {estado.get('temporada', 1)}",
                  (16, 48), size='sm', color='verde')
        draw_button(screen, _volver(), "VOLVER", _volver().collidepoint(mouse_pos))
        draw_button(screen, R_HISTORIAL, "HISTORIAL DE TRANSACCIONES",     # v0.4.27.0
                    (not abierto) and R_HISTORIAL.collidepoint(mouse_pos))

        # --- Saldo ---
        draw_panel(screen, R_SALDO)
        x, y = R_SALDO.x + 20, R_SALDO.y + 14
        draw_text(screen, "SALDO", (x, y), size='sm', color='azul')
        draw_text(screen, _m(mi.balance), (x, y + 26), size='xl', color='verde' if mi.balance >= 0 else 'rojo')
        draw_text(screen, f"Proyección al cierre ({restantes} jornadas): {_m(proyeccion)}",
                  (x, y + 90), size='sm', color='verde' if proyeccion >= 0 else 'rojo')
        # v4.7.0: valor del club = valor de mercado de la plantilla + saldo
        valor = F.valor_club(mi, estado)      # v0.4.26.0: con la venta de camisetas
        draw_text(screen, "VALOR DEL CLUB", (x, y + 124), size='sm', color='azul')
        draw_text(screen, _m(valor), (x, y + 146), size='lg', color='verde' if valor >= 0 else 'rojo')
        proy_valor = valor - mi.balance + proyeccion
        draw_text(screen, f"Proyección al cierre: {_m(proy_valor)}", (x, y + 184), size='sm',
                  color='verde' if proy_valor >= 0 else 'rojo')
        try:   # v4.7.0: barra de masa salarial contra el tope de la directiva
            tope = int(obj.get('tope_salarial', 0) or 0)
            frac_m = masa / tope if tope else 0.0
            draw_text(screen, f"MASA SALARIAL  {_m(masa)} / tope {_m(tope)}", (x, y + 218), size='sm', color='blanco')
            barra(screen, pygame.Rect(x, y + 244, R_SALDO.width - 40, 18), frac_m, color_barra_tope(frac_m))
        except Exception as e_masa:
            logger.error(f"No se pudo mostrar la barra de masa salarial: {e_masa}")

        # --- Libro de la temporada ---
        draw_panel(screen, R_LIBRO)
        lx, ly = R_LIBRO.x + 20, R_LIBRO.y + 14
        draw_text(screen, "INGRESOS Y GASTOS DE LA TEMPORADA", (lx, ly), size='sm', color='azul')
        ingresos = [("Taquilla", lib['taquilla']), ("Patrocinio", lib['patrocinio']),
                    ("Camisetas", lib.get('camisetas', 0)),      # v0.4.26.0: venta de camisetas
                    ("Ventas", lib['ventas']), ("Premios", lib['premios']),
                    ("Directiva", lib.get('directiva', 0))]      # v3.2.0: espaldarazo
        gastos = [("Salarios", lib['salarios']), ("Fichajes", lib['fichajes'])]
        for i, (t, v) in enumerate(ingresos):      # v0.4.26.0: paso 24 para que quepan 6 líneas
            draw_text(screen, t, (lx, ly + 34 + i * 24), size='md', color='blanco')
            draw_text(screen, "+" + _m(v), (lx + 180, ly + 34 + i * 24), size='md', color='verde')
        for i, (t, v) in enumerate(gastos):
            draw_text(screen, t, (lx + 420, ly + 34 + i * 30), size='md', color='blanco')
            draw_text(screen, "−" + _m(v), (lx + 600, ly + 34 + i * 30), size='md', color='rojo')
        neto = sum(v for _t, v in ingresos) - sum(v for _t, v in gastos)
        draw_text(screen, f"NETO DE LA TEMPORADA: {'+' if neto >= 0 else ''}{_m(neto)}", (lx, ly + 176),
                  size='lg', color='verde' if neto >= 0 else 'rojo')
        deuda = D.deuda_espaldarazo(estado)      # v4.6.0: deuda del espaldarazo financiero
        if deuda:
            draw_text(screen, f"Deuda con la directiva: {_m(deuda)} (se descuenta al cierre)",
                      (lx + 420, ly + 110), size='sm', color='rojo')
        try:   # v0.4.17.0: la sanción de la liga a la vista toda la temporada sancionada
            from alpha_football import sancion_liga as _SL
            sancion = _SL.activa(estado)
            if sancion:
                draw_text(screen, _SL.texto_corto(sancion), (lx, ly + 216), size='sm', color='rojo')
        except Exception as e_san:
            logger.error(f"No se pudo mostrar la sanción de la liga: {e_san}")
        if mi.balance < 0:
            rojo = int(dc.get('jornadas_en_rojo', 0) or 0)
            draw_text(screen, f"¡EN ROJO! {rojo}/{F.JORNADAS_ROJO_VENTA} jornadas: al llegar a {F.JORNADAS_ROJO_VENTA} "
                              f"venden a tu mejor jugador. Cerrar así: −{F.PUNTOS_QUIEBRA} pts.",
                      (lx, ly + 242), size='sm', color='rojo')

        # --- v4.7.0: espaldarazo financiero (antes en OBJETIVOS) ---
        draw_panel(screen, R_ESP)
        ex, ey = R_ESP.x + 20, R_ESP.y + 14
        draw_text(screen, "ESPALDARAZO FINANCIERO", (ex, ey), size='sm', color='dorado')
        draw_text(screen, "Dinero de la directiva ahora a cambio de una meta de liga más alta. "
                          "La mitad se descuenta de las ganancias al cierre.", (ex, ey + 34), size='sm', color='blanco')
        draw_text(screen, f"Una vez por temporada, hasta la mitad de la liga, con calificación de DT de "
                          f"{D.CALIF_ESPALDARAZO} o más.", (ex, ey + 62), size='sm', color='azul')
        draw_text(screen, f"Meta de liga actual: {obj.get('texto', '—')}", (ex, ey + 96), size='sm', color='dorado')
        pedido_esp = bool(obj.get('espaldarazo'))
        draw_button(screen, R_ESPALDARAZO, "ESPALDARAZO YA PEDIDO" if pedido_esp else "PEDIR ESPALDARAZO FINANCIERO",
                    (not pedido_esp) and R_ESPALDARAZO.collidepoint(mouse_pos))
        msg_esp = estado.get('espaldarazo_msg')
        if msg_esp:
            draw_text(screen, msg_esp[:110], (ex, R_ESPALDARAZO.bottom + 16), size='sm',
                      color='verde' if msg_esp.startswith(("Aprobado", "Ahora")) else 'rojo')

        try:   # v0.4.26.0: venta de camisetas: popularidad, ingreso y lo que suma al valor del club
            cam = F.info_camisetas(estado)
            cx, cy = R_CAMISETAS.x + 16, R_CAMISETAS.y + 8
            sube = cam['tendencia']
            tendencia = f"subiendo {sube:+.1f}" if sube > 0.05 else f"bajando {sube:+.1f}" if sube < -0.05 else "estable"
            draw_text(screen, "VENTA DE CAMISETAS", (cx, cy), size='sm', color='dorado')
            draw_text(screen, f"Popularidad {cam['popularidad']:.0f}/100 · {tendencia}", (cx, cy + 26), size='sm',
                      color='verde' if sube >= 0 else 'rojo')
            barra(screen, pygame.Rect(cx, cy + 52, 560, 16), cam['popularidad'] / 100.0, 'dorado')
            draw_text(screen, f"Con la de hoy: {_m(cam['ingreso_anual'])} al año · cobrado esta temporada: "
                              f"{_m(cam['cobrado'])}", (cx, cy + 78), size='sm', color='blanco')
            # v0.4.27.0: sin las dos líneas de abajo ("Suma X al valor del club…", "Se dispara si rindes…")
        except Exception as e_cam:
            logger.error(f"No se pudo mostrar la venta de camisetas: {e_cam}")

        if abierto:     # overlay con las 3 opciones del espaldarazo
            _velo(screen)
            draw_panel(screen, R_OVERLAY)
            pygame.draw.rect(screen, COLORS['dorado'], R_OVERLAY, width=2, border_radius=8)
            draw_text(screen, "PEDIR ESPALDARAZO FINANCIERO", (R_OVERLAY.x + 20, R_OVERLAY.y + 18),
                      size='md', color='dorado')
            for op, r in zip(D.opciones_espaldarazo(estado), _rects_espaldarazo()):
                disp = op['disponible']
                if disp and r.collidepoint(mouse_pos):
                    pygame.draw.rect(screen, COLORS['dorado'], r, width=2, border_radius=6)
                t = (f"{op['nivel'] + 1}) +{int(op['pct'] * 100)}% (${op['monto'] / 1_000_000:.1f}M) → meta "
                     f"{op['puestos']} puesto{'s' if op['puestos'] > 1 else ''} más alta"
                     + ("" if disp else " (no disponible)"))
                # el theme no tiene gris: las opciones no disponibles van en rojo
                draw_text(screen, t, (r.x + 16, r.y + 14), size='md', color='verde' if disp else 'rojo')
            draw_text(screen, "También sube el tope de masa salarial, en el mismo porcentaje.",     # v0.4.26.0
                      (R_OVERLAY.x + 20, R_OVERLAY.bottom - 66), size='sm', color='dorado')
            draw_text(screen, "La mitad se descuenta de las ganancias al cerrar la temporada.  ·  ESC para cerrar",
                      (R_OVERLAY.x + 20, R_OVERLAY.bottom - 40), size='sm', color='azul')
        return None
    except Exception as e:
        logger.error(f"Error en finanzas_screen: {e}", exc_info=True)
        return 'league_screen'
