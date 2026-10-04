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
R_OVERLAY = pygame.Rect(SCREEN_W // 2 - 360, 180, 720, 340)


def _rects_espaldarazo() -> list:
    return [pygame.Rect(R_OVERLAY.x + 20, R_OVERLAY.y + 70 + i * 64, R_OVERLAY.width - 40, 54) for i in range(3)]


def _volver() -> pygame.Rect:
    return pygame.Rect(1116, 12, 148, 40)


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
        nivel = None
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return 'menu'
            clic = ev.pos if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 else None
            esc = ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE)
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

        # --- Saldo ---
        draw_panel(screen, R_SALDO)
        x, y = R_SALDO.x + 20, R_SALDO.y + 14
        draw_text(screen, "SALDO", (x, y), size='sm', color='azul')
        draw_text(screen, _m(mi.balance), (x, y + 26), size='xl', color='verde' if mi.balance >= 0 else 'rojo')
        draw_text(screen, f"Proyección al cierre ({restantes} jornadas): {_m(proyeccion)}",
                  (x, y + 90), size='sm', color='verde' if proyeccion >= 0 else 'rojo')
        # v4.7.0: valor del club = valor de mercado de la plantilla + saldo
        valor = F.valor_club(mi)
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
                    ("Ventas", lib['ventas']), ("Premios", lib['premios']),
                    ("Directiva", lib.get('directiva', 0))]      # v3.2.0: espaldarazo
        gastos = [("Salarios", lib['salarios']), ("Fichajes", lib['fichajes'])]
        for i, (t, v) in enumerate(ingresos):      # v3.2.0: paso 27 para que quepan 5 líneas
            draw_text(screen, t, (lx, ly + 34 + i * 27), size='md', color='blanco')
            draw_text(screen, "+" + _m(v), (lx + 180, ly + 34 + i * 27), size='md', color='verde')
        for i, (t, v) in enumerate(gastos):
            draw_text(screen, t, (lx + 420, ly + 34 + i * 30), size='md', color='blanco')
            draw_text(screen, "−" + _m(v), (lx + 600, ly + 34 + i * 30), size='md', color='rojo')
        neto = sum(v for _t, v in ingresos) - sum(v for _t, v in gastos)
        draw_text(screen, f"NETO DE LA TEMPORADA: {'+' if neto >= 0 else ''}{_m(neto)}", (lx, ly + 170),
                  size='lg', color='verde' if neto >= 0 else 'rojo')
        deuda = D.deuda_espaldarazo(estado)      # v4.6.0: deuda del espaldarazo financiero
        if deuda:
            draw_text(screen, f"Deuda con la directiva: {_m(deuda)} (se descuenta al cierre)",
                      (lx + 420, ly + 110), size='sm', color='rojo')
        if mi.balance < 0:
            rojo = int(dc.get('jornadas_en_rojo', 0) or 0)
            draw_text(screen, f"¡EN ROJO! {rojo}/{F.JORNADAS_ROJO_VENTA} jornadas: al llegar a {F.JORNADAS_ROJO_VENTA} "
                              f"venden a tu mejor jugador. Cerrar así: −{F.PUNTOS_QUIEBRA} pts.",
                      (lx, ly + 236), size='sm', color='rojo')

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
            draw_text(screen, "La mitad se descuenta de las ganancias al cerrar la temporada.  ·  ESC para cerrar",
                      (R_OVERLAY.x + 20, R_OVERLAY.bottom - 40), size='sm', color='azul')
        return None
    except Exception as e:
        logger.error(f"Error en finanzas_screen: {e}", exc_info=True)
        return 'league_screen'
