# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Objetivos de la directiva (Pygame)
v2.8.0: objetivo de la temporada, cómo vas, confianza de la directiva, qué pasa si lo
cumples o no, e historial de objetivos de temporadas anteriores.
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

# v3.2.0: paneles de arriba 60 px más altos (botón de espaldarazo y meta internacional)
R_OBJ = pygame.Rect(16, 76, 620, 372)
R_CONF = pygame.Rect(648, 76, 616, 372)
R_HIST = pygame.Rect(16, 460, 1248, 236)      # v3.6.0: termina en y=696 (barra de atajos)
R_ESPALDARAZO = pygame.Rect(R_OBJ.x + 20, R_OBJ.y + 292, 320, 40)
R_OVERLAY = pygame.Rect(SCREEN_W // 2 - 360, 180, 720, 340)


def _rects_espaldarazo() -> list:
    return [pygame.Rect(R_OVERLAY.x + 20, R_OVERLAY.y + 70 + i * 64, R_OVERLAY.width - 40, 54) for i in range(3)]


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


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """Retorna 'league_screen' al salir o None para seguir aquí."""
    try:
        liga, mi = estado.get('liga'), estado.get('mi_equipo')
        if liga is None or mi is None:
            return 'league_screen'
        obj = D.definir_objetivo(estado) or {}
        mouse_pos = pygame.mouse.get_pos()
        abierto = bool(estado.get('espaldarazo_abierto'))
        nivel = None
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return 'menu'
            if abierto:     # v3.2.0: overlay del espaldarazo (1/2/3 o clic; ESC cierra)
                if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    nivel = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2}[ev.key]
                elif ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    estado.pop('espaldarazo_abierto', None)
                    abierto = False
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    nivel = next((i for i, r in enumerate(_rects_espaldarazo()) if r.collidepoint(ev.pos)), None)
                continue
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                estado.pop('espaldarazo_msg', None)
                return 'league_screen'
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and _volver().collidepoint(ev.pos):
                estado.pop('espaldarazo_msg', None)
                return 'league_screen'
            if (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and R_ESPALDARAZO.collidepoint(ev.pos)
                    and not obj.get('espaldarazo')):
                estado['espaldarazo_abierto'] = abierto = True
        if abierto and nivel is not None:
            try:
                ok, msg = D.pedir_espaldarazo(estado, nivel)
                estado['espaldarazo_msg'] = msg
            except Exception as e_esp:
                logger.error(f"Error al pedir el espaldarazo: {e_esp}")
            estado.pop('espaldarazo_abierto', None)
            abierto = False
            obj = D.definir_objetivo(estado) or {}

        draw_gradient_bg(screen)
        draw_text(screen, "OBJETIVOS DE LA DIRECTIVA", (16, 12), size='lg', color='dorado')
        draw_text(screen, f"{mi.nombre}  ·  {liga.nombre}  ·  Temporada {estado.get('temporada', 1)}",
                  (16, 48), size='sm', color='verde')
        draw_button(screen, _volver(), "VOLVER", _volver().collidepoint(mouse_pos))

        # --- Objetivo ---
        draw_panel(screen, R_OBJ)
        x, y = R_OBJ.x + 20, R_OBJ.y + 14
        draw_text(screen, "OBJETIVO DE LA TEMPORADA", (x, y), size='sm', color='azul')
        draw_text(screen, obj.get('texto', '—'), (x, y + 26), size='lg', color='dorado')
        pos = _posicion_actual(liga, mi)
        meta = int(obj.get('pos_max', 99))
        en_camino = pos <= meta
        jugado = any(p.jugado for p in getattr(liga, 'calendario', []) or [])
        estado_txt = (f"Vas {pos}º de {len(liga.equipos)}  ·  meta: puesto {meta} o mejor" if jugado
                      else f"La liga aún no empezó  ·  meta: puesto {meta} o mejor")
        draw_text(screen, estado_txt, (x, y + 72), size='md',
                  color='azul' if not jugado else 'verde' if en_camino else 'rojo')
        ref = int(obj.get('presupuesto_ref', 0) or 0)
        c = D.confianza(estado)
        lineas = [
            (f"Si lo superas: +{int(D.PREMIO['superado'] * 100)}% del presupuesto inicial (+{_m(ref * D.PREMIO['superado'])})", 'verde'),
            (f"Si lo cumples: +{int(D.PREMIO['cumplido'] * 100)}% (+{_m(ref * D.PREMIO['cumplido'])})", 'verde'),
            (f"Si fallas: −{abs(int(D.PREMIO['fallado'] * 100))}% (−{_m(ref * D.PREMIO['fallado'])}) y "
             + ("TE ECHAN (ya tenías advertencia)" if (estado.get('datos_carrera') or {}).get('advertencia_dt')
                else "advertencia (segunda oportunidad)"), 'rojo'),
            ("Descender o quedar 4+ puestos por debajo de la meta = despido directo", 'rojo'),
        ]
        for i, (t, col) in enumerate(lineas):
            draw_text(screen, t, (x, y + 118 + i * 26), size='sm', color=col)
        draw_text(screen, f"Ranking de tu plantilla al empezar: {obj.get('ranking_inicial', '?')}º por media",
                  (x, y + 226), size='sm', color='azul')
        # v3.2.0: objetivo internacional (solo si estás en la copa)
        oc = D.definir_objetivo_copa(estado)
        t_int = (f"INTERNACIONAL: {oc['texto']} · vas: {estado.get('copa_mejor_fase_temp') or 'Fase de liga'}"
                 if oc else "INTERNACIONAL: sin competición esta temporada, no hay meta.")
        draw_text(screen, t_int, (x, y + 252), size='sm', color='dorado' if oc else 'azul')
        # v3.2.0: espaldarazo financiero
        pedido_esp = bool(obj.get('espaldarazo'))
        draw_button(screen, R_ESPALDARAZO, "ESPALDARAZO YA PEDIDO" if pedido_esp else "PEDIR ESPALDARAZO",
                    (not pedido_esp) and R_ESPALDARAZO.collidepoint(mouse_pos))
        msg_esp = estado.get('espaldarazo_msg')
        if msg_esp:
            draw_text(screen, msg_esp[:64], (x, R_ESPALDARAZO.bottom + 6), size='sm',
                      color='verde' if msg_esp.startswith("Aprobado") else 'rojo')

        # --- Confianza ---
        draw_panel(screen, R_CONF)
        x2, y2 = R_CONF.x + 20, R_CONF.y + 14
        draw_text(screen, "CONFIANZA DE LA DIRECTIVA", (x2, y2), size='sm', color='azul')
        color = COLORS['verde'] if c >= 70 else COLORS['dorado'] if c >= 45 else COLORS['rojo']
        draw_text(screen, f"{c} / 100  ·  {D.texto_confianza(c)}", (x2, y2 + 26), size='lg',
                  color='verde' if c >= 70 else 'dorado' if c >= 45 else 'rojo')
        barra = pygame.Rect(x2, y2 + 80, R_CONF.width - 40, 22)
        pygame.draw.rect(screen, (30, 40, 60), barra, border_radius=6)
        lleno = barra.copy(); lleno.width = int(barra.width * c / 100)
        pygame.draw.rect(screen, color, lleno, border_radius=6)
        # v3.1.0: calificación de DT y pedido de la directiva
        cal = D.calif_dt(estado)
        draw_text(screen, f"CALIFICACIÓN DE DT: {cal} / 100", (x2, y2 + 118), size='md',
                  color='verde' if cal >= 70 else 'dorado' if cal >= 40 else 'rojo')
        ped = D.pedido_activo(estado)
        draw_text(screen, (texto_pedido(ped, D._jugadas(liga, mi))[:70] if ped
                           else "Sin pedido activo de la directiva"), (x2, y2 + 156), size='sm', color='dorado')
        for i, t in enumerate(["Victoria de liga +3  ·  derrota −3  ·  clásico ±6",
                               "Calif.: objetivo ±8/+4 · título +10 · copa +12 · pedido +3/−4",
                               "La calificación define qué clubes te llaman si te despiden."]):
            draw_text(screen, t, (x2, y2 + 190 + i * 28), size='sm', color='blanco')

        # --- Historial ---
        draw_panel(screen, R_HIST)
        draw_text(screen, "HISTORIAL DE OBJETIVOS", (R_HIST.x + 20, R_HIST.y + 12), size='sm', color='dorado')
        regs = [r for r in estado.get('historial', []) or [] if r.get('objetivo')]
        if not regs:
            draw_text(screen, "Todavía no terminaste ninguna temporada con objetivo.",
                      (R_HIST.x + 20, R_HIST.y + 46), size='sm', color='blanco')
        for i, r in enumerate(regs[-7:][::-1]):      # v3.2.0: panel más bajo (7 filas)
            res = r.get('objetivo_resultado', '')
            col = 'verde' if res in ('cumplido', 'superado') else 'rojo'
            monto = int(r.get('directiva_monto', 0) or 0)
            t = (f"T{r.get('temporada', '?')}  ·  {r.get('equipo', '')[:22]}  ·  {r.get('objetivo', '')[:44]}  ·  "
                 f"terminó {r.get('pos', '?')}º  ·  {res.upper()}  ·  {'+' if monto >= 0 else '−'}{_m(monto)}"
                 + ("  ·  DESPEDIDO" if r.get('despedido') else ""))
            draw_text(screen, t, (R_HIST.x + 20, R_HIST.y + 44 + i * 28), size='sm', color=col)

        if abierto:     # v3.2.0: overlay con las 3 opciones del espaldarazo
            velo = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            velo.fill((0, 0, 0, 170))
            screen.blit(velo, (0, 0))
            draw_panel(screen, R_OVERLAY)
            pygame.draw.rect(screen, COLORS['dorado'], R_OVERLAY, width=2, border_radius=8)
            draw_text(screen, "PEDIR ESPALDARAZO A LA DIRECTIVA", (R_OVERLAY.x + 20, R_OVERLAY.y + 18),
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
            draw_text(screen, "Si fallas: segunda oportunidad como siempre.  ·  ESC para cerrar",
                      (R_OVERLAY.x + 20, R_OVERLAY.bottom - 40), size='sm', color='azul')
        return None
    except Exception as e:
        logger.error(f"Error en objetivos_screen: {e}", exc_info=True)
        return 'league_screen'
