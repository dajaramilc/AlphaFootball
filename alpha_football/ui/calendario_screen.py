# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Calendario (Pygame)
v0.4.11.0: mes en cuadrícula con tus partidos de liga y copa, los cierres de mercado y el día en
que estás parado (el de tu próximo partido). ← → cambia de mes, ESC vuelve.
v0.4.14.1: clic en un día futuro = simular hasta ahí (simulacion.py): pide confirmación y los días pasan
de a uno en esta misma pantalla, con el segundo entrenador dirigiendo tus partidos.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
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

from alpha_football import calendario as CAL
from alpha_football import simulacion as SIM

logger = logging.getLogger(__name__)

MESES_LARGO = ('ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO', 'JULIO', 'AGOSTO', 'SEPTIEMBRE',
               'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE')
DIAS_CABECERA = ('LUN', 'MAR', 'MIÉ', 'JUE', 'VIE', 'SÁB', 'DOM')
R_GRILLA = pygame.Rect(16, 110, 1248, 586)       # termina en y=696 (barra de atajos)
CABECERA_H = 28
COLS, FILAS = 7, 6
MS_PASO_SIM, MS_TRAS_PARTIDO = 500, 1000    # v0.4.14.1: ritmo de la simulación (ms por día y pausa tras un partido); v0.4.18.0: 0,5 s por día (antes 70 y 450)
R_DIALOGO = pygame.Rect(320, 240, 640, 220)
MOTIVOS_FIN = {'llego': "Simulación terminada", 'temporada': "Terminó la temporada",
               'despido': "La directiva detuvo la simulación", 'bloqueo': "La simulación no pudo seguir"}


def _rects() -> dict:
    return {'volver': pygame.Rect(1116, 12, 148, 40),
            'prev': pygame.Rect(16, 62, 44, 36), 'next': pygame.Rect(68, 62, 44, 36)}


def rect_celda(i: int) -> pygame.Rect:
    w = R_GRILLA.width // COLS
    h = (R_GRILLA.height - CABECERA_H) // FILAS
    return pygame.Rect(R_GRILLA.x + (i % COLS) * w, R_GRILLA.y + CABECERA_H + (i // COLS) * h, w - 4, h - 4)


def celdas_mes(anio: int, mes: int) -> list:
    """Los 42 días (6 semanas de lunes a domingo) de la cuadrícula de ese mes."""
    primero = date(anio, mes, 1)
    inicio = primero - timedelta(days=primero.weekday())
    return [inicio + timedelta(days=k) for k in range(COLS * FILAS)]


def eventos_por_dia(estado: dict) -> dict:
    out: dict = {}
    for ev in CAL.eventos_user(estado):
        out.setdefault(ev['fecha'], []).append(ev)
    return out


def limites(estado: dict) -> tuple:
    """((año, mes) del inicio de la temporada o del primer partido, (año, mes) del fin o del último partido)."""
    from alpha_football import temporada as T      # v0.4.13.0
    fechas = [ev['fecha'] for ev in CAL.eventos_user(estado)]
    h = T.hitos(estado)
    fechas += [h['inicio'], h['fin']]
    return (min(fechas).year, min(fechas).month), (max(fechas).year, max(fechas).month)


def _mover(estado: dict, paso: int) -> None:
    a, m = estado['cal_mes']
    m += paso
    if m < 1:
        a, m = a - 1, 12
    elif m > 12:
        a, m = a + 1, 1
    lo, hi = limites(estado)
    if lo <= (a, m) <= hi:
        estado['cal_mes'] = [a, m]


def _texto_evento(ev: dict) -> tuple:
    """(línea 1, línea 2, color) de un partido dentro de su celda."""
    l1 = f"{ev['etiqueta']} {'vs' if ev['local'] else 'en'} {str(ev['rival'])[:13]}"
    if ev['jugado']:
        gf, gc = int(ev['gf'] or 0), int(ev['gc'] or 0)
        return l1, f"{gf}-{gc}", 'verde' if gf > gc else 'rojo' if gf < gc else 'blanco'
    return l1, "LOCAL" if ev['local'] else "VISITANTE", 'dorado' if ev['tipo'] == 'copa' else 'azul'


def _salir(estado: dict) -> str:
    estado.pop('cal_mes', None)
    estado.pop('cal_sim', None)
    return 'league_screen'


# --- v0.4.14.1: simulación hasta el día elegido ───────────────────────────────

def rects_dialogo() -> dict:
    return {'si': pygame.Rect(R_DIALOGO.x + 40, R_DIALOGO.bottom - 68, 260, 46),
            'no': pygame.Rect(R_DIALOGO.right - 300, R_DIALOGO.bottom - 68, 260, 46)}


def _dia_en(estado: dict, pos) -> Optional[date]:
    """El día de la cuadrícula que está bajo ese punto (None si no hay ninguno)."""
    a, m = estado['cal_mes']
    return next((d for i, d in enumerate(celdas_mes(a, m)) if rect_celda(i).collidepoint(pos)), None)


def _aviso(estado: dict, texto: str, ms: int = 7000) -> None:
    estado['cal_msg'] = (texto, pygame.time.get_ticks() + ms)


def _empezar(estado: dict, sim: dict) -> None:
    estado['cal_sim'] = {'fase': 'corriendo', 'hasta': sim['hasta'], 'sig': 0,
                         'dias': 0, 'pj': 0, 'g': 0, 'e': 0, 'p': 0}


def texto_resumen(sim: dict, cabecera: str) -> str:
    """'Simulación terminada: 12 días, 2 partidos (1G 1E 0P)'."""
    d, pj = int(sim.get('dias', 0) or 0), int(sim.get('pj', 0) or 0)
    partes = [f"{d} día{'s' if d != 1 else ''}"]
    if pj:
        partes.append(f"{pj} partido{'s' if pj != 1 else ''} "
                      f"({sim.get('g', 0)}G {sim.get('e', 0)}E {sim.get('p', 0)}P)")
    return f"{cabecera}: {', '.join(partes)}"


def _terminar(estado: dict, sim: dict, cabecera: str) -> None:
    estado.pop('cal_sim', None)
    _aviso(estado, texto_resumen(sim, cabecera))


def _paso_sim(estado: dict, sim: dict) -> Optional[str]:
    """Un paso de la simulación, si ya toca. Devuelve la pantalla a la que hay que salir (solo si la
    directiva te despidió por el camino) o None."""
    ahora = pygame.time.get_ticks()
    if ahora < int(sim.get('sig', 0) or 0):
        return None
    r = SIM.paso(estado, date.fromisoformat(sim['hasta']))
    if r['tipo'] == 'dia':
        sim['dias'] = int(sim.get('dias', 0) or 0) + 1
        sim['sig'] = ahora + MS_PASO_SIM
    elif r['tipo'] == 'partido':
        pt = r['partido']
        gf, gc = int(pt.get('gf') or 0), int(pt.get('gc') or 0)
        clave = 'g' if gf > gc else 'p' if gf < gc else 'e'
        sim['pj'], sim[clave] = int(sim.get('pj', 0) or 0) + 1, int(sim.get(clave, 0) or 0) + 1
        sim['ultimo'] = f"{pt['etiqueta']} {'vs' if pt['local'] else 'en'} {str(pt['rival'])[:16]} {gf}-{gc}"
        sim['sig'] = ahora + MS_TRAS_PARTIDO
    else:
        _terminar(estado, sim, MOTIVOS_FIN.get(r.get('motivo'), MOTIVOS_FIN['bloqueo']))
        if r.get('motivo') == 'despido':
            return _salir(estado)                # el hub muestra el despido
    from alpha_football import dias as DIAS
    hoy = DIAS.hoy(estado)
    estado['cal_mes'] = [hoy.year, hoy.month]    # el mes sigue al día en que va la simulación
    return None


def _dibujar_dialogo(screen: pygame.Surface, estado: dict, sim: dict, mouse_pos) -> None:
    hasta = date.fromisoformat(sim['hasta'])
    velo = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    velo.fill((0, 0, 0, 170))
    screen.blit(velo, (0, 0))
    draw_panel(screen, R_DIALOGO)
    pygame.draw.rect(screen, COLORS['dorado'], R_DIALOGO, width=2, border_radius=8)
    x, y = R_DIALOGO.x + 28, R_DIALOGO.y + 22
    draw_text(screen, f"¿SIMULAR HASTA EL {CAL.texto_fecha(hasta).upper()}?", (x, y), size='md', color='dorado')
    n = SIM.partidos_hasta(estado, hasta)
    if n:
        draw_text(screen, f"El segundo entrenador arma el once y dirige {n} partido{'s' if n != 1 else ''}.",
                  (x, y + 44), size='sm', color='blanco')
    else:
        draw_text(screen, "No juegas antes de ese día: solo pasan los días.", (x, y + 44), size='sm', color='blanco')
    draw_text(screen, "Las ofertas quedan en tu bandeja. Una tecla detiene la simulación.", (x, y + 70), size='sm',
              color='azul')
    r = rects_dialogo()
    draw_button(screen, r['si'], "SIMULAR (Enter)", r['si'].collidepoint(mouse_pos))
    draw_button(screen, r['no'], "CANCELAR (Esc)", r['no'].collidepoint(mouse_pos))


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """Retorna 'league_screen' al salir o None para seguir aquí."""
    try:
        if estado.get('liga') is None or estado.get('mi_equipo') is None:
            return 'league_screen'
        from alpha_football import dias as DIAS            # v0.4.12.0: "hoy" es el día del reloj
        hoy = DIAS.hoy(estado)
        if not estado.get('cal_mes'):
            estado['cal_mes'] = [hoy.year, hoy.month]
        r = _rects()
        mouse_pos = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return 'menu'
            sim = estado.get('cal_sim')
            tecla = ev.key if ev.type == pygame.KEYDOWN else None
            clic = ev.pos if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 else None
            if sim and sim.get('fase') == 'confirmar':     # v0.4.14.1: el diálogo se come teclas y clics
                rd = rects_dialogo()
                if tecla in (pygame.K_RETURN, pygame.K_KP_ENTER) or (clic and rd['si'].collidepoint(clic)):
                    _empezar(estado, sim)
                elif tecla in (pygame.K_ESCAPE, pygame.K_BACKSPACE) or (clic and rd['no'].collidepoint(clic)):
                    estado.pop('cal_sim', None)
                continue
            if sim:                                        # simulando: una tecla o un clic la detiene ahí
                if tecla is not None or clic:
                    _terminar(estado, sim, "Simulación detenida")
                continue
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    return _salir(estado)
                if ev.key == pygame.K_LEFT:
                    _mover(estado, -1)
                elif ev.key == pygame.K_RIGHT:
                    _mover(estado, 1)
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if r['volver'].collidepoint(ev.pos):
                    return _salir(estado)
                if r['prev'].collidepoint(ev.pos):
                    _mover(estado, -1)
                elif r['next'].collidepoint(ev.pos):
                    _mover(estado, 1)
                else:                                      # v0.4.14.1: clic en un día futuro = simular hasta ahí
                    dia = _dia_en(estado, ev.pos)
                    if dia is not None and SIM.puede_simular_hasta(estado, dia):
                        estado['cal_sim'] = {'fase': 'confirmar', 'hasta': dia.isoformat()}

        sim = estado.get('cal_sim')
        if sim and sim.get('fase') == 'corriendo':
            destino = _paso_sim(estado, sim)
            if destino:
                return destino
            hoy = DIAS.hoy(estado)
            sim = estado.get('cal_sim')
        try:
            destino_sim = date.fromisoformat(sim['hasta']) if sim else None
        except Exception as e_sim:
            logger.error(f"Simulación del calendario dañada: {e_sim}")
            estado.pop('cal_sim', None)
            sim, destino_sim = None, None

        a, m = estado['cal_mes']
        draw_gradient_bg(screen)
        draw_text(screen, "CALENDARIO", (16, 14), size='lg', color='dorado')
        draw_button(screen, r['prev'], "<", r['prev'].collidepoint(mouse_pos))
        draw_button(screen, r['next'], ">", r['next'].collidepoint(mouse_pos))
        draw_button(screen, r['volver'], "VOLVER", r['volver'].collidepoint(mouse_pos))
        draw_text(screen, f"{MESES_LARGO[m - 1]} {a}", (128, 68), size='md', color='blanco')
        draw_text(screen, f"Hoy: {CAL.texto_fecha(hoy)} · Próximo: {CAL.texto_proximo(estado) or '-'}",
                  (520, 70), size='sm', color='azul')
        aviso = estado.get('cal_msg')                      # v0.4.14.1: cómo va (o cómo terminó) la simulación
        if sim and sim.get('fase') == 'corriendo':
            ultimo = f" · {sim['ultimo']}" if sim.get('ultimo') else ""
            draw_text(screen, f"SIMULANDO hasta el {CAL.texto_fecha(destino_sim, False)}{ultimo} · una tecla detiene",
                      (300, 22), size='sm', color='dorado')
        elif aviso and pygame.time.get_ticks() < aviso[1]:
            draw_text(screen, str(aviso[0])[:80], (300, 22), size='sm', color='verde')

        por_dia = eventos_por_dia(estado)
        dias_cierre = set(CAL.cierres(CAL.continente(estado), CAL.anio(estado)))
        ancho = R_GRILLA.width // COLS
        for c, nombre in enumerate(DIAS_CABECERA):
            draw_text(screen, nombre, (R_GRILLA.x + c * ancho + 8, R_GRILLA.y + 4), size='sm', color='azul', shadow=False)
        for i, d in enumerate(celdas_mes(a, m)):
            rc = rect_celda(i)
            del_mes = d.month == m
            pygame.draw.rect(screen, (20, 26, 46) if del_mes else (14, 18, 32), rc, border_radius=6)
            if d == hoy:
                pygame.draw.rect(screen, COLORS['dorado'], rc, width=2, border_radius=6)
            elif d == destino_sim:                         # v0.4.14.1: hasta dónde se simula
                pygame.draw.rect(screen, COLORS['verde'], rc, width=2, border_radius=6)
            draw_text(screen, str(d.day), (rc.x + 6, rc.y + 4), size='sm',
                      color='blanco' if del_mes else 'azul', shadow=False)
            try:   # v0.4.13.0: franja verde en los días con el mercado abierto; fin de temporada
                from alpha_football import temporada as _T
                if _T.ventana_en(estado, d):
                    pygame.draw.rect(screen, (0, 140, 80), pygame.Rect(rc.x, rc.y, rc.width, 4), border_radius=2)
                if d == _T.fin(estado):
                    draw_text(screen, "FIN TEMPORADA", (rc.x + 6, rc.y + 26), size='sm', color='azul', shadow=False)
            except Exception as e_vent:
                logger.error(f"Error al marcar las ventanas en el calendario: {e_vent}")
            y = rc.y + 26
            if d in dias_cierre:
                draw_text(screen, "CIERRE MERCADO", (rc.x + 6, y), size='sm', color='rojo', shadow=False)
                y += 20
            for ev in por_dia.get(d, [])[:1 if d in dias_cierre else 2]:
                l1, l2, col = _texto_evento(ev)
                draw_text(screen, l1, (rc.x + 6, y), size='sm', color=col, shadow=False)
                draw_text(screen, l2, (rc.x + 6, y + 20), size='sm', color='blanco', shadow=False)
                y += 40
        if sim and sim.get('fase') == 'confirmar':
            _dibujar_dialogo(screen, estado, sim, mouse_pos)
        return None
    except Exception as e:
        logger.error(f"Error en calendario_screen: {e}", exc_info=True)
        return 'league_screen'
