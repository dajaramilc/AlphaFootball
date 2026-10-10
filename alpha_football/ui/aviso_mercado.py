# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Aviso de mercado en INICIO (v4.4.0)
Cartel modal al abrirse (J1 y J n−2) y cerrarse (J4) el mercado + franja con la cuenta regresiva
mientras está abierto. Se engancha en league_screen.render (manejar + dibujar).
"""
from __future__ import annotations

import logging
from typing import Optional

import pygame

logger = logging.getLogger(__name__)

try:
    from alpha_football.ui.theme import COLORS, get_font, draw_panel, draw_button
except Exception as e_imp:  # pragma: no cover - fallback como el resto de las pantallas
    logger.warning(f"aviso_mercado sin theme ({e_imp})")
    COLORS = {'verde': (0, 255, 136), 'rojo': (255, 68, 68), 'dorado': (255, 215, 0), 'blanco': (255, 255, 255)}
    def get_font(size): return pygame.font.Font(None, 24)
    def draw_panel(screen, rect): pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=8)
    def draw_button(screen, rect, text, hover): pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=6); return rect

SCREEN_W, SCREEN_H = 1280, 720
R_CARTEL = pygame.Rect(SCREEN_W // 2 - 280, 220, 560, 260)
R_IR = pygame.Rect(R_CARTEL.x + 40, R_CARTEL.bottom - 76, 230, 52)
R_CONTINUAR = pygame.Rect(R_CARTEL.right - 270, R_CARTEL.bottom - 76, 230, 52)
FRANJA_Y, FRANJA_H, MARGEN_DER = 80, 22, 16


def _hasta(estado: dict) -> str:
    """Último día de la ventana abierta hoy ('vie 31 ene')."""
    from alpha_football import temporada as T, calendario as CAL
    n = T.ventana_actual(estado)
    return CAL.texto_fecha(T.ventanas(estado)[n][1], False) if n else CAL.texto_fecha(T.fecha(estado), False)


def _reabre(estado: dict) -> str:
    from alpha_football import temporada as T, calendario as CAL
    return f"Reabre el {CAL.texto_fecha(T.proxima_apertura(estado))}."


def _liga(estado):
    return estado.get('liga')


def evento_pendiente(estado: dict) -> Optional[tuple]:
    """v0.4.13.0: ('abre', 'AAAA-MM-DD') el primer día de una ventana, ('cierra', …) el día siguiente a su
    cierre; None el resto o si ya se vio. Solo con reloj (en el hub); sin él no hay cartel."""
    if _liga(estado) is None:
        return None
    from alpha_football import dias, temporada as T
    if not dias.activo(estado):
        return None
    d = T.fecha(estado)
    tipo = T.hito_del_dia(estado, d)
    if not tipo:
        return None
    clave = [int(estado.get('temporada', 1) or 1), d.isoformat()]
    if (estado.get('datos_carrera') or {}).get('aviso_mercado_visto') == clave:
        return None
    return tipo, d.isoformat()


def _abrir(estado: dict, tipo: str, fecha: str) -> None:
    dc = estado.setdefault('datos_carrera', {})
    dc['aviso_mercado_visto'] = [int(estado.get('temporada', 1) or 1), fecha]
    # con el mercado cerrado no hay a qué ir: el foco arranca en CONTINUAR
    estado['aviso_mercado_activo'] = {'tipo': tipo, 'fecha': fecha, 'foco': 0 if tipo in ('abre', 'ultimo') else 1}
    try:
        from alpha_football import correo as C
        if tipo == 'abre':
            C.enviar(estado, 'club', "Se abrió el mercado de pases",
                     f"Hasta el {_hasta(estado)} se pueden cerrar fichajes, recibir ofertas y pagar cláusulas.",
                     C.accion('negociaciones', "IR A NEGOCIACIONES"))
        elif tipo == 'ultimo':
            C.enviar(estado, 'club', "Último día de fichajes",
                     "Hoy cierra el mercado: quedan 20 horas para concretar tus operaciones. Lo que no llegue a "
                     "inscribirse queda acordado para la próxima ventana.",       # v0.4.14.1: sin anunciar costos
                     C.accion('negociaciones', "IR A NEGOCIACIONES"))
        else:
            C.enviar(estado, 'club', "Se cerró el mercado de pases",
                     "El mercado de pases ha cerrado. " + _reabre(estado))
    except Exception as e:
        logger.error(f"No se pudo enviar el correo del mercado: {e}")


def manejar(estado: dict, key_events: list, click_pos, bloqueado: bool = False) -> tuple:
    """(destino, key_events, click_pos). Con el cartel abierto consume todo."""
    act = estado.get('aviso_mercado_activo')
    if not act:
        if bloqueado or estado.get('ayuda_abierta'):
            return None, key_events, click_pos
        ev = evento_pendiente(estado)
        if ev is None:
            return None, key_events, click_pos
        _abrir(estado, *ev)
        return None, [], None
    for e in key_events or []:
        if e.key in (pygame.K_LEFT, pygame.K_RIGHT):
            act['foco'] = 1 - int(act.get('foco', 0))
        elif e.key == pygame.K_ESCAPE:
            estado['aviso_mercado_activo'] = None
            return None, [], None
        elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            destino = 'negociaciones' if int(act.get('foco', 0)) == 0 else None
            estado['aviso_mercado_activo'] = None
            return destino, [], None
    if click_pos:
        if R_IR.collidepoint(click_pos):
            estado['aviso_mercado_activo'] = None
            return 'negociaciones', [], None
        if R_CONTINUAR.collidepoint(click_pos):
            estado['aviso_mercado_activo'] = None
    return None, [], None


def _ancho_cabecera(estado: dict) -> int:
    """Ancho de la cabecera del hub (texto 'sm' en (16, 82)), armada igual que league_screen."""
    try:
        liga, mi = _liga(estado), estado.get('mi_equipo')
        from alpha_football.paises import nombre_liga
        cab = (f"{nombre_liga(liga.tipo, getattr(liga, 'division', 1) or 1).upper()[:32]}  ·  {mi.nombre[:22]}  ·  "
               f"{'2ª' if getattr(liga, 'division', 1) == 2 else '1ª'} Div.  ·  T{estado.get('temporada', 1)}  ·  "
               f"{fecha_corta(estado)} · J{getattr(liga, 'jornada_actual', 1)}/{getattr(liga, 'num_jornadas', 14)}  ·  "
               f"${getattr(mi, 'balance', 0) / 1_000_000:.1f}M")
        return get_font('sm').size(cab)[0]
    except Exception as e:
        logger.debug(f"No se pudo medir la cabecera del hub: {e}")
        return 965                                   # peor caso medido


def fecha_corta(estado: dict) -> str:
    """'15 ago' (la fecha de hoy sin día de la semana ni año), para la cabecera del hub."""
    try:
        from alpha_football import temporada as T, calendario as CAL
        d = T.fecha(estado)
        return f"{d.day} {CAL.MESES[d.month - 1]}"
    except Exception:
        return "-"


def _texto_franja(estado: dict, corto: bool = False) -> Optional[tuple]:
    if _liga(estado) is None:
        return None
    from alpha_football import temporada as T
    from alpha_football import dia_final as DF          # v0.4.14.0
    if DF.activo(estado):
        h = DF.horas(estado)
        return (f"ÚLTIMO DÍA · {h} h" if corto else f"ÚLTIMO DÍA · quedan {h} h"), 'dorado'
    if not T.ventana_abierta(estado):
        return None
    d = T.dias_para_cierre(estado)
    if d <= 0:
        return ("MERCADO · ÚLTIMO DÍA" if corto else "MERCADO ABIERTO · ÚLTIMO DÍA"), 'dorado'
    return (f"MERCADO ABIERTO · {d} d." if corto
            else f"MERCADO ABIERTO · cierra en {d} día{'s' if d != 1 else ''}"), 'verde'


def _franja(estado: dict, ancho_cabecera: Optional[int] = None) -> tuple:
    """(texto, color, rect) a la derecha de la cabecera, en su misma línea; texto corto si no entra."""
    libre_desde = 16 + (ancho_cabecera if ancho_cabecera is not None else _ancho_cabecera(estado)) + 12
    for corto in (False, True):
        t = _texto_franja(estado, corto)
        if not t:
            return None, None, None
        w = get_font('sm').size(t[0])[0] + 24
        r = pygame.Rect(SCREEN_W - MARGEN_DER - w, FRANJA_Y, w, FRANJA_H)
        if r.left >= libre_desde or corto:
            return t[0], t[1], r
    return None, None, None


def rect_franja(estado: dict, ancho_cabecera: Optional[int] = None) -> Optional[pygame.Rect]:
    return _franja(estado, ancho_cabecera)[2]


def linea_cartel(estado: dict, tipo: str) -> str:
    """La línea bajo el título del cartel. v0.4.14.1: el último día solo dice las horas que quedan (los
    costos de cada operación se aplican, pero no se anuncian)."""
    if tipo == 'ultimo':
        from alpha_football import dia_final as _DF
        h = _DF.horas(estado) or _DF.HORAS_DIA
        return "Queda 1 hora." if h == 1 else f"Quedan {h} horas."
    if tipo == 'abre':
        return f"Hasta el {_hasta(estado)}: fichajes, ofertas y cláusulas."
    return _reabre(estado)


def dibujar(screen: pygame.Surface, estado: dict, mouse_pos) -> None:
    try:
        texto, col, r = _franja(estado)
        t = (texto, col) if texto else None
        if t and r:
            color = COLORS.get(t[1], (0, 255, 136))
            pygame.draw.rect(screen, (10, 14, 26), r, border_radius=6)
            pygame.draw.rect(screen, color, r, width=2, border_radius=6)
            surf = get_font('sm').render(t[0], True, color)
            screen.blit(surf, surf.get_rect(center=r.center))
        act = estado.get('aviso_mercado_activo')
        if not act:
            return
        velo = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        velo.fill((0, 0, 0, 170))
        screen.blit(velo, (0, 0))
        draw_panel(screen, R_CARTEL)
        tipo_c = act.get('tipo')
        abre = tipo_c in ('abre', 'ultimo')
        color = COLORS.get({'abre': 'verde', 'ultimo': 'dorado'}.get(tipo_c, 'rojo'), (0, 255, 136))
        pygame.draw.rect(screen, color, R_CARTEL, width=3, border_radius=8)
        s = get_font('xl').render({'abre': "MERCADO ABIERTO", 'ultimo': "ÚLTIMO DÍA DE FICHAJES"}.get(tipo_c, "MERCADO CERRADO"), True, color)
        screen.blit(s, s.get_rect(center=(R_CARTEL.centerx, R_CARTEL.y + 50)))
        linea = linea_cartel(estado, tipo_c)
        s2 = get_font('md').render(linea, True, COLORS.get('blanco', (255, 255, 255)))
        screen.blit(s2, s2.get_rect(center=(R_CARTEL.centerx, R_CARTEL.y + 104)))
        salen = sum(1 for j in getattr(estado.get('mi_equipo'), 'jugadores', []) or [] if getattr(j, 'pide_salir', False))
        if abre and salen:
            s3 = get_font('sm').render(f"{salen} jugador{'es piden' if salen != 1 else ' pide'} salir.", True,
                                       COLORS.get('dorado', (255, 215, 0)))
            screen.blit(s3, s3.get_rect(center=(R_CARTEL.centerx, R_CARTEL.y + 138)))
        foco = int(act.get('foco', 0))
        for i, (rb, txt) in enumerate(((R_IR, "IR AL MERCADO"), (R_CONTINUAR, "CONTINUAR"))):
            draw_button(screen, rb, txt, rb.collidepoint(mouse_pos) or foco == i)
            if foco == i:
                pygame.draw.rect(screen, COLORS.get('dorado', (255, 215, 0)), rb, width=2, border_radius=6)
    except Exception as e:
        logger.error(f"Error al dibujar el aviso de mercado: {e}")
