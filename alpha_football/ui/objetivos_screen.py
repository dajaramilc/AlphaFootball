# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Objetivos de la directiva (Pygame)
v2.8.0: objetivo de la temporada, cómo vas, confianza de la directiva, qué pasa si lo
cumples o no, e historial de objetivos de temporadas anteriores.
v4.6.0: objetivos financieros con barras (masa salarial y saldo), reglas en un overlay "?",
barra de calificación de DT, espaldarazo financiero (deuda) y ofertas de otros clubes.
v4.7.0: secciones Local/Internacional/Finanzas/Marca/Juveniles; sin historial ni ofertas (van en OFERTAS DT).
v4.7.0: el botón del espaldarazo se movió a FINANZAS.
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

from alpha_football import directiva as D

logger = logging.getLogger(__name__)

# v4.7.0: franja de directiva arriba; fila 1 Local/Internacional/Finanzas; fila 2 Marca/Juveniles.
# Sin historial ni ofertas de otros clubes (van en OFERTAS DT).
R_TOP = pygame.Rect(16, 76, 1248, 96)
R_LOCAL = pygame.Rect(16, 184, 408, 250)
R_INTER = pygame.Rect(436, 184, 408, 250)
R_FIN = pygame.Rect(856, 184, 408, 250)
R_MARCA = pygame.Rect(16, 446, 616, 250)
R_JUV = pygame.Rect(648, 446, 616, 250)          # termina en y=696 (barra de atajos)
R_AYUDA_META = pygame.Rect(R_LOCAL.right - 56, R_LOCAL.y + 12, 36, 36)
R_REGLAS = pygame.Rect(SCREEN_W // 2 - 380, 150, 760, 368)   # v0.4.11.0: una fila más (antes 330)
# v0.4.17.0: pasarse del tope además trae la sanción de la liga (sancion_liga.py)
TEXTO_REGLA_TOPE = "Pasar el tope o el saldo mínimo = objetivo fallado; el tope, además, un año sin fichar"


def _volver() -> pygame.Rect:
    return pygame.Rect(1116, 12, 148, 40)


def _m(v: int) -> str:
    return f"${abs(v) / 1_000_000:.1f}M"


def _posicion_actual(liga, mi) -> int:
    orden = sorted(liga.equipos, key=lambda e: (e.puntos, e.gf - e.gc, e.gf), reverse=True)
    return next((i + 1 for i, e in enumerate(orden) if e is mi or e.id == mi.id), len(orden))


def texto_pedido(ped: dict, jugados: int) -> str:
    """v3.1.0: el plazo de un pedido se cuenta en partidos de liga del user."""
    quedan = max(0, int(ped.get('hasta', 0)) - int(jugados))
    return f"Pedido: {ped['texto']} (quedan {quedan} partido{'s' if quedan != 1 else ''})"


def color_barra_tope(frac: float) -> str:
    """v4.6.0: verde hasta el 85% del tope, dorado hasta el 100%, rojo por encima."""
    return 'verde' if frac < 0.85 else 'dorado' if frac <= 1.0 else 'rojo'


def barra(screen, rect: pygame.Rect, frac: float, color: str) -> None:
    pygame.draw.rect(screen, (30, 40, 60), rect, border_radius=6)
    lleno = rect.copy(); lleno.width = int(rect.width * max(0.0, min(1.0, frac)))
    pygame.draw.rect(screen, COLORS[color], lleno, border_radius=6)


def _velo(screen) -> None:
    velo = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    velo.fill((0, 0, 0, 170))
    screen.blit(velo, (0, 0))


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """Retorna 'league_screen' al salir o None para seguir aquí."""
    try:
        liga, mi = estado.get('liga'), estado.get('mi_equipo')
        if liga is None or mi is None:
            return 'league_screen'
        obj = D.definir_objetivo(estado) or {}
        mouse_pos = pygame.mouse.get_pos()
        reglas = bool(estado.get('objetivos_reglas_abierto'))
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return 'menu'
            clic = ev.pos if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 else None
            esc = ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE)
            if reglas:        # v4.6.0: overlay "?" con las reglas del objetivo
                if esc or clic:
                    estado.pop('objetivos_reglas_abierto', None)
                    reglas = False
                continue
            if esc or (clic and _volver().collidepoint(clic)):
                estado.pop('espaldarazo_msg', None)
                return 'league_screen'
            if (clic and R_AYUDA_META.collidepoint(clic)) or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_i):
                estado['objetivos_reglas_abierto'] = reglas = True

        draw_gradient_bg(screen)
        draw_text(screen, "OBJETIVOS DE LA DIRECTIVA", (16, 12), size='lg', color='dorado')
        draw_text(screen, f"{mi.nombre}  ·  {liga.nombre}  ·  Temporada {estado.get('temporada', 1)}",
                  (16, 48), size='sm', color='verde')
        draw_button(screen, _volver(), "VOLVER", _volver().collidepoint(mouse_pos))

        def _titulo(r, t):
            draw_panel(screen, r)
            draw_text(screen, t, (r.x + 20, r.y + 14), size='sm', color='azul')

        # --- Directiva: confianza, calificación y pedido ---
        draw_panel(screen, R_TOP)
        c, cal = D.confianza(estado), D.calif_dt(estado)
        tx, ty, ancho = R_TOP.x + 20, R_TOP.y + 12, 400
        draw_text(screen, f"CONFIANZA  {c}/100 · {D.texto_confianza(c)}", (tx, ty), size='sm', color='azul')
        barra(screen, pygame.Rect(tx, ty + 26, ancho, 18), c / 100,
              'verde' if c >= 70 else 'dorado' if c >= 45 else 'rojo')
        draw_text(screen, f"CALIFICACIÓN DE DT  {cal}/100", (tx + 430, ty), size='sm', color='azul')
        barra(screen, pygame.Rect(tx + 430, ty + 26, ancho, 18), cal / 100,
              'verde' if cal >= 70 else 'dorado' if cal >= 40 else 'rojo')
        ped = D.pedido_activo(estado)
        draw_text(screen, (texto_pedido(ped, D._jugadas(liga, mi)) if ped else "Sin pedido de la directiva")[:44],
                  (tx + 860, ty + 14), size='sm', color='dorado')

        # --- Local ---
        _titulo(R_LOCAL, "LOCAL")
        x, y = R_LOCAL.x + 20, R_LOCAL.y + 14
        # la meta va en hasta 2 líneas y no pisa el botón "?"
        lineas, actual = [], ""
        for palabra in str(obj.get('texto', '—')).split():
            prueba = (actual + " " + palabra).strip()
            if actual and get_font('md').size(prueba)[0] > R_LOCAL.width - 40:
                lineas.append(actual); actual = palabra
            else:
                actual = prueba
        lineas.append(actual)
        for i, linea in enumerate(lineas[:2]):
            draw_text(screen, linea, (x, y + 40 + i * 30), size='md', color='dorado')
        draw_button(screen, R_AYUDA_META, "?", R_AYUDA_META.collidepoint(mouse_pos))
        pos, meta = _posicion_actual(liga, mi), int(obj.get('pos_max', 99))
        jugado = any(p.jugado for p in getattr(liga, 'calendario', []) or [])
        draw_text(screen, f"Vas {pos}º de {len(liga.equipos)}" if jugado else "La liga aún no empezó",
                  (x, y + 110), size='md', color='azul' if not jugado else 'verde' if pos <= meta else 'rojo')
        draw_text(screen, f"Meta: puesto {meta} o mejor", (x, y + 146), size='sm', color='blanco')

        # --- Internacional ---
        _titulo(R_INTER, "INTERNACIONAL")
        x = R_INTER.x + 20
        oc = D.definir_objetivo_copa(estado)
        if oc:
            draw_text(screen, oc['texto'][:34], (x, y + 40), size='md', color='dorado')
            draw_text(screen, f"Vas: {estado.get('copa_mejor_fase_temp') or 'Fase de liga'}", (x, y + 84),
                      size='md', color='verde')
        else:
            draw_text(screen, "Sin competición esta temporada.", (x, y + 40), size='sm', color='azul')

        # --- Finanzas ---
        _titulo(R_FIN, "FINANZAS")
        x = R_FIN.x + 20
        from alpha_football.finanzas import masa_salarial
        masa, tope = masa_salarial(mi, estado), int(obj.get('tope_salarial', 0) or 0)
        frac_m = masa / tope if tope else 0.0
        draw_text(screen, f"MASA SALARIAL  {_m(masa)} / {_m(tope)}", (x, y + 40), size='sm', color='blanco')
        barra(screen, pygame.Rect(x, y + 64, R_FIN.width - 40, 18), frac_m, color_barra_tope(frac_m))
        minimo, saldo = int(obj.get('saldo_minimo', 0) or 0), int(mi.balance)
        frac_s = saldo / minimo if minimo > 0 else (1.0 if saldo >= 0 else 0.0)
        draw_text(screen, f"SALDO  {'−' if saldo < 0 else ''}{_m(saldo)} / mín. {_m(minimo)}", (x, y + 96),
                  size='sm', color='blanco')
        barra(screen, pygame.Rect(x, y + 120, R_FIN.width - 40, 18), frac_s,
              'verde' if frac_s >= 1.0 else 'dorado' if frac_s >= 0.5 else 'rojo')
        deuda = D.deuda_espaldarazo(estado)
        if deuda:
            draw_text(screen, f"Deuda espaldarazo: {_m(deuda)} (al cierre)", (x, y + 152), size='sm', color='rojo')

        # --- v4.7.0: Marca y Juveniles ---
        for r, titulo, oc2 in ((R_MARCA, "MARCA", D.definir_objetivo_marca(estado)),
                               (R_JUV, "JUVENILES", D.definir_objetivo_juveniles(estado))):
            _titulo(r, titulo)
            if not oc2:
                continue
            x2 = r.x + 20
            hecho = D.cumplido_secundario(estado, oc2)
            draw_text(screen, oc2['texto'][:52], (x2, r.y + 54), size='md', color='dorado')
            barra(screen, pygame.Rect(x2, r.y + 100, r.width - 40, 18), D.progreso_secundario(estado, oc2),
                  'verde' if hecho else 'dorado')
            draw_text(screen, "CUMPLIDO" if hecho else "EN CURSO", (x2, r.y + 132), size='sm',
                      color='verde' if hecho else 'azul')
            draw_text(screen, f"Cumplir: +{D.CALIF_SECUNDARIO['cumplido']} calificación · fallar: "
                              f"{D.CALIF_SECUNDARIO['fallado']}", (x2, r.y + 200), size='sm', color='blanco')

        if reglas:      # v4.6.0: reglas del objetivo (antes ocupaban el panel)
            _velo(screen)
            draw_panel(screen, R_REGLAS)
            pygame.draw.rect(screen, COLORS['dorado'], R_REGLAS, width=2, border_radius=8)
            ref = int(obj.get('presupuesto_ref', 0) or 0)
            filas = [("REGLAS DEL OBJETIVO", 'dorado'),
                     (f"Si lo superas: +{int(D.PREMIO['superado'] * 100)}% del presupuesto inicial "
                      f"(+{_m(ref * D.PREMIO['superado'])})", 'verde'),
                     (f"Si lo cumples: +{int(D.PREMIO['cumplido'] * 100)}% (+{_m(ref * D.PREMIO['cumplido'])})", 'verde'),
                     (f"Si fallas: −{abs(int(D.PREMIO['fallado'] * 100))}% (−{_m(ref * D.PREMIO['fallado'])}) y "
                      + ("TE ECHAN (ya tenías advertencia)" if (estado.get('datos_carrera') or {}).get('advertencia_dt')
                         else "advertencia (segunda oportunidad)"), 'rojo'),
                     ("Descender o quedar 4+ puestos por debajo de la meta = despido directo", 'rojo'),
                     (TEXTO_REGLA_TOPE, 'rojo'),
                     (f"Ranking de tu plantilla al empezar: {obj.get('ranking_inicial', '?')}º por media", 'azul'),
                     ("El saldo no pasa de temporada: el presupuesto siguiente sube 25% / 10% o baja 15%", 'azul'),   # v0.4.11.0
                     ("Clic o ESC para cerrar", 'blanco')]
            for i, (t, col) in enumerate(filas):
                draw_text(screen, t, (R_REGLAS.x + 20, R_REGLAS.y + 18 + i * 38), size='md' if i == 0 else 'sm',
                          color=col)
        return None
    except Exception as e:
        logger.error(f"Error en objetivos_screen: {e}", exc_info=True)
        return 'league_screen'
