# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Pantalla de Dirección de Equipo (Pygame)
Permite al usuario gestionar su plantilla, seleccionar la alineación inicial
de 11 titulares para el próximo partido, usar selección automática y validar
la distribución táctica (1 POR, 3+ DEF, 2+ MED, 1+ DEL).
"""

import sys
import os
import random
import logging
from typing import Optional, Any, Dict, List

from alpha_football import formaciones as F
from alpha_football.vestuario import PERSONALIDAD_TXT

# Configurar logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
logger = logging.getLogger(__name__)

try:
    import pygame
except ImportError as error_pygame:
    logger.critical(f"Error crítico al importar pygame en team_screen: {error_pygame}.")
    raise error_pygame

# Importación del tema visual con fallbacks locales seguros
try:
    from alpha_football.ui.theme import (
        SCREEN_W,
        SCREEN_H,
        COLORS,
        get_font,
        draw_gradient_bg,
        draw_panel,
        draw_button,
        draw_text,
        BLANCO,
        AMARILLO,
        GRIS_CLAR,
        VERDE_CAMPO,
        VERDE_CAMPO2
    )
except Exception as error_theme:
    logger.warning(f"No se pudo cargar el tema visual ({error_theme}). Usando fallback.")
    # Bug B: constantes de color del campo/alertas, también en el fallback para no romper.
    BLANCO = (255, 255, 255)
    AMARILLO = (255, 215, 0)
    GRIS_CLAR = (200, 200, 200)
    VERDE_CAMPO = (34, 110, 45)
    VERDE_CAMPO2 = (40, 125, 52)
    SCREEN_W = 1280
    SCREEN_H = 720
    COLORS = {
        'bg': (10, 14, 26),
        'verde': (0, 255, 136),
        'dorado': (255, 215, 0),
        'rojo': (255, 68, 68),
        'azul': (0, 191, 255),
        'blanco': (255, 255, 255),
        'panel': (20, 26, 46)
    }
    
    def get_font(size):
        try:
            if size == 'sm': return pygame.font.SysFont("Arial", 16)
            elif size == 'md': return pygame.font.SysFont("Arial", 20)
            elif size == 'lg': return pygame.font.SysFont("Arial", 28)
            elif size == 'xl': return pygame.font.SysFont("Arial", 42)
        except Exception:
            pass
        return pygame.font.Font(None, 24)
        
    def draw_gradient_bg(screen):
        screen.fill((10, 14, 26))
        
    def draw_panel(screen, rect):
        pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=8)
        pygame.draw.rect(screen, (0, 191, 255), rect, width=2, border_radius=8)
        
    def draw_button(screen, rect, text, hover):
        return rect
        
    def draw_text(screen, text, pos, size='md', color='blanco', shadow=True):
        try:
            rgb_color = COLORS.get(color, (255, 255, 255))
            font = get_font(size)
            if shadow:
                shadow_surf = font.render(text, True, (0, 0, 0))
                screen.blit(shadow_surf, (pos[0] + 1, pos[1] + 1))
            txt_surf = font.render(text, True, rgb_color)
            screen.blit(txt_surf, pos)
        except Exception:
            pass

# Posiciones en campo para formacion 4-3-3 (Fracciones relativas)
POSICIONES_CAMPO_433 = [
    (0.50, 0.88),   # POR
    (0.18, 0.68),   # DEF izq
    (0.38, 0.68),   # DEF centro-izq
    (0.62, 0.68),   # DEF centro-der
    (0.82, 0.68),   # DEF der
    (0.22, 0.45),   # MED izq
    (0.50, 0.45),   # MED centro
    (0.78, 0.45),   # MED der
    (0.22, 0.22),   # DEL izq
    (0.50, 0.22),   # DEL centro
    (0.78, 0.22),   # DEL der
]

POS_ORDEN = {"POR": 0, "DEF": 1, "MED": 2, "DEL": 3}
POS_COLOR = {
    "POR": (255, 170,  30),
    "DEF": ( 30, 120, 220),
    "MED": ( 30, 190,  80),
    "DEL": (220,  50,  50),
}

def draw_pitch_lines(screen: pygame.Surface) -> None:
    """Dibuja marcas decorativas del campo en el fondo."""
    try:
        pitch_color = (20, 38, 62)
        pygame.draw.circle(screen, pitch_color, (750, 360), 120, 2)
        pygame.draw.circle(screen, pitch_color, (750, 360), 6)
        pygame.draw.line(screen, pitch_color, (750, 20), (750, 700), 2)
        pygame.draw.rect(screen, pitch_color, pygame.Rect(260, 110, 160, 500), 2)
        pygame.draw.rect(screen, pitch_color, pygame.Rect(1080, 110, 160, 500), 2)
    except Exception as e:
        logger.error(f"Error en draw_pitch_lines: {e}")

def draw_styled_button(screen: pygame.Surface, rect: pygame.Rect, text: str, hover: bool, accent_color: tuple[int, int, int] | str, enabled: bool = True) -> pygame.Rect:
    """Dibuja un botón interactivo con acento de color dinámico."""
    try:
        button_rect = pygame.Rect(rect)
        real_accent = accent_color
        if isinstance(accent_color, str) and accent_color.startswith('#'):
            try:
                real_accent = (int(accent_color[1:3], 16), int(accent_color[3:5], 16), int(accent_color[5:7], 16))
            except Exception:
                real_accent = (0, 191, 255)
        
        color_panel = COLORS.get('panel', (20, 26, 46))
        color_azul = COLORS.get('azul', (0, 191, 255))
        color_blanco = COLORS.get('blanco', (255, 255, 255))

        if not enabled:
            bg_color = (25, 25, 35)
            border_color = (75, 75, 85)
            text_color = (110, 110, 120)
        elif hover:
            bg_color = (30, 45, 75)
            border_color = real_accent
            text_color = real_accent
        else:
            bg_color = color_panel
            border_color = color_azul
            text_color = color_blanco
            
        pygame.draw.rect(screen, bg_color, button_rect, border_radius=8)
        pygame.draw.rect(screen, border_color, button_rect, width=2, border_radius=8)
        
        font = get_font('md')
        text_surf = font.render(text, True, text_color)
        text_rect = text_surf.get_rect(center=button_rect.center)
        screen.blit(text_surf, text_rect)
        return button_rect
    except Exception as e:
        logger.error(f"Error en draw_styled_button: {e}")
        return rect

def _truncar(texto: str, max_chars: int) -> str:
    try:
        return texto if len(texto) <= max_chars else texto[:max_chars - 1] + "."
    except Exception:
        return ""


def _render_team_view_mode(screen, estado, team_objetivo, f_riv, mejores, jugadores_riv, mouse_pos, click_pos):
    """
    v0.8.3 (F1): vista simplificada de team_screen cuando el DT quiere ver la
    alineación del RIVAL (sin posibilidad de editar formación, táctica ni hacer
    cambios). Dibuja solo el panel del club, la lista de jugadores y el campo con
    los 11 mejores por posición, más un botón "VOLVER A MI ONCE".
    """
    try:
        draw_gradient_bg(screen)
        draw_pitch_lines(screen)
    except Exception:
        screen.fill((10, 14, 26))

    # Franjas decorativas
    try:
        pygame.draw.rect(screen, COLORS.get('rojo', (255, 68, 68)), pygame.Rect(0, 0, SCREEN_W, 4))
        pygame.draw.rect(screen, COLORS.get('verde', (0, 255, 136)), pygame.Rect(0, 4, SCREEN_W, 4))
        pygame.draw.rect(screen, COLORS.get('azul', (0, 191, 255)), pygame.Rect(0, 8, SCREEN_W, 4))
    except Exception:
        pass

    # Encabezado
    # v3.9.0: en 'xl' el título pisaba el botón VOLVER A MI ONCE
    draw_text(screen, f"ALINEACIÓN DEL RIVAL — {_truncar(team_objetivo.nombre.upper(), 15)}",
              (300, 22), size='lg', color='dorado')
    est_l = getattr(team_objetivo, 'estilo_dt', 'anchelottismo') or 'anchelottismo'
    est_l = NOMBRE_ESTILO.get(est_l, est_l.capitalize())   # v3.3.0
    draw_text(screen, f"Estilo: {est_l}  ·  Formación: {f_riv.formacion}  ·  Vista de solo lectura",
              (300, 66), size='sm', color='azul')

    # Botón "VOLVER A MI ONCE" (arriba a la derecha)
    btn_volver = R_VISOR_VOLVER
    btn_volver_hover = btn_volver.collidepoint(mouse_pos)
    draw_styled_button(screen, btn_volver, "VOLVER A MI ONCE", btn_volver_hover, COLORS.get('verde', (0, 255, 136)))
    if click_pos and btn_volver.collidepoint(click_pos):
        estado['team_equipo_objetivo'] = None
        return "prepartido_screen" if estado.get('match_mode') else "league_screen"

    # Lista de jugadores (read-only, no clicable)
    rect_lista = R_VISOR_LISTA
    draw_panel(screen, rect_lista)
    encabezado_h = 36
    try:
        pygame.draw.rect(screen, (15, 22, 40), pygame.Rect(rect_lista.x, rect_lista.y, rect_lista.width, encabezado_h), border_top_left_radius=8, border_top_right_radius=8)
    except Exception:
        pass
    titulares_idx_set = set(f_riv.titulares)
    draw_text(screen, f"PLANTILLA — {len(titulares_idx_set)}/11 TITULARES",
              (rect_lista.x + 15, rect_lista.y + 8), size='sm', color='dorado')

    # Ordenar: titulares primero, luego banco por posición
    pos_orden = {'POR': 0, 'DEF': 1, 'MED': 2, 'DEL': 3}
    jugadores_ordenados = (
        [j for i, j in enumerate(jugadores_riv) if i in titulares_idx_set]
        + sorted(
            [j for i, j in enumerate(jugadores_riv) if i not in titulares_idx_set],
            key=lambda j: (pos_orden.get(getattr(j, 'posicion', ''), 9), -getattr(j, 'overall', 0))
        )
    )

    fila_alto = 38
    y = rect_lista.y + encabezado_h + 6
    filas_max = (rect_lista.height - encabezado_h - 10) // fila_alto     # v3.9.0: 15 filas se salían del panel
    for j in jugadores_ordenados[:filas_max]:
        try:
            fila_r = pygame.Rect(rect_lista.x + 6, y, rect_lista.width - 12, fila_alto - 4)
            is_t = id(j) in {id(jugadores_riv[i]) for i in titulares_idx_set}
            bg = (30, 65, 45) if is_t else (20, 26, 46)
            pygame.draw.rect(screen, bg, fila_r, border_radius=4)
            # Indicador
            ind = COLORS.get('verde', (0, 255, 136)) if is_t else COLORS.get('rojo', (255, 68, 68))
            pygame.draw.rect(screen, ind, pygame.Rect(fila_r.x, fila_r.y, 4, fila_r.height), border_radius=2)
            # Posición
            try:
                pc = POS_COLOR.get(j.posicion, GRIS_CLAR)
                badge = pygame.Rect(fila_r.x + 10, fila_r.y + 7, 42, 20)    # v3.9.0: "MED" no cabía en 36
                pygame.draw.rect(screen, pc, badge, border_radius=3)
                draw_text(screen, j.posicion, (badge.x + 5, badge.y + 2), size='sm', color='blanco', shadow=False)
            except Exception:
                pass
            # v3.9.0: nombre y OVR en la misma línea (antes el OVR se montaba sobre el nombre)
            draw_text(screen, _truncar(j.nombre_completo, 24), (fila_r.x + 60, fila_r.y + 7), size='sm',
                      color='verde' if is_t else 'blanco')
            draw_text(screen, f"OVR {j.overall}", (fila_r.right - 78, fila_r.y + 7), size='sm', color='dorado')
        except Exception:
            pass
        y += fila_alto

    # Campo con los 11 mejores
    rect_campo = R_VISOR_CAMPO
    try:
        pygame.draw.rect(screen, VERDE_CAMPO, rect_campo, border_radius=8)
        franja_h = rect_campo.height // 8
        for i in range(8):
            col = VERDE_CAMPO if i % 2 == 0 else VERDE_CAMPO2
            pygame.draw.rect(screen, col, pygame.Rect(rect_campo.x + 2, rect_campo.y + i * franja_h + 2, rect_campo.width - 4, franja_h - 2))
        pygame.draw.rect(screen, BLANCO, rect_campo, width=2, border_radius=8)
        cy = rect_campo.y + rect_campo.height // 2
        pygame.draw.line(screen, (220, 220, 220), (rect_campo.x + 8, cy), (rect_campo.right - 8, cy), 1)
        radio_c = min(rect_campo.width, rect_campo.height) // 8
        pygame.draw.circle(screen, (220, 220, 220), rect_campo.center, radio_c, 1)
    except Exception:
        pass

    # Posiciones en el campo (mismo layout que el equipo del usuario)
    pos_field = f_riv.formacion or '4-4-2'
    try:
        from alpha_football import formaciones as _F
        posiciones_campo = _F.posiciones(pos_field)
    except Exception:
        posiciones_campo = []
    # Ordenar los 11 mejores por posición usando las posiciones del campo
    radio_circ = 22
    for idx_pos, pxy in enumerate(posiciones_campo):
        if idx_pos >= len(mejores):
            break
        j = mejores[idx_pos]
        try:
            px_rel, py_rel = pxy
            cx = rect_campo.x + int(rect_campo.width * px_rel)
            cy = rect_campo.y + int(rect_campo.height * py_rel)
            pygame.draw.circle(screen, COLORS.get('verde', (0, 255, 136)), (cx, cy), radio_circ)
            pygame.draw.circle(screen, (10, 14, 26), (cx, cy), radio_circ, width=2)
            # v3.9.0: la media dentro del círculo y el apellido debajo (antes se pisaban)
            ap = j.apellido[:12] if hasattr(j, 'apellido') else ''
            s_ovr = get_font('sm').render(str(j.overall), True, (10, 14, 26))
            screen.blit(s_ovr, s_ovr.get_rect(center=(cx, cy)))
            draw_text(screen, ap, (cx - get_font('sm').size(ap)[0] // 2, cy + radio_circ + 2), size='sm',
                      color='blanco', shadow=True)
        except Exception:
            pass

    return None


from alpha_football.estilos import ESTILOS_UI as TACTICAS, NOMBRE_ESTILO, DESC_ESTILO  # v3.3.0: los 9 estilos
MENTALIDADES = ["autobus", "defensiva", "normal", "ofensiva", "todo_o_nada"]
NOMBRE_MENTALIDAD = {"autobus": "AUTOBÚS", "defensiva": "DEFENSIVA", "normal": "NORMAL",
                     "ofensiva": "OFENSIVA", "todo_o_nada": "TODO O NADA"}
_CARD_W, _CARD_H = 119, 104          # tarjetas de banco/reservas
_BANCO_Y = 572
_CAMPO = pygame.Rect(16, 100, 930, 452)
_FICHA = pygame.Rect(962, 100, 302, 452)


# v3.9.0: rects expuestos (ayuda H); render los usa tal cual.
R_VISOR_VOLVER = pygame.Rect(SCREEN_W - 260, 22, 240, 44)
R_VISOR_LISTA = pygame.Rect(40, 100, 440, 580)
R_VISOR_CAMPO = pygame.Rect(500, 100, 740, 480)
R_BANCO_TOGGLE = pygame.Rect(1050, _BANCO_Y - 20, 214, 34)
R_BANCO_PREV = pygame.Rect(958, _BANCO_Y - 20, 40, 34)
R_BANCO_NEXT = pygame.Rect(1004, _BANCO_Y - 20, 40, 34)


def rect_tarjeta_banco(n: int) -> pygame.Rect:
    """v3.9.0: tarjeta n (0-9) de la fila del banco / reservas."""
    return pygame.Rect(16 + n * (_CARD_W + 6), _BANCO_Y + 20, _CARD_W, _CARD_H)


def _salir_direccion(estado, es_amistoso, modo_prepartido):
    for k in ('_original_alignment', '_original_convocados', '_original_formacion',
              '_original_estilo', '_original_mentalidad', '_original_subs', '_original_salieron',
              'team_sel', 'team_res_page', 'team_view'):
        estado.pop(k, None)
    if es_amistoso:
        estado.pop('team_contexto', None)
    if modo_prepartido:
        estado.pop('team_modo_prepartido', None)


def _rects_cabecera() -> dict:
    """v2.5.0: controles de la cabecera de dirección (formación, estilo, mentalidad y botones)."""
    return {
        'form_prev': pygame.Rect(300, 22, 30, 40), 'form_box': pygame.Rect(334, 22, 80, 40),
        'form_next': pygame.Rect(418, 22, 30, 40),
        'tact_prev': pygame.Rect(456, 22, 30, 40), 'tact_box': pygame.Rect(490, 22, 127, 40),
        'tact_next': pygame.Rect(621, 22, 30, 40),
        'ment_prev': pygame.Rect(659, 22, 30, 40), 'ment_box': pygame.Rect(693, 22, 127, 40),
        'ment_next': pygame.Rect(824, 22, 30, 40),
        'auto': pygame.Rect(862, 18, 80, 48), 'ok': pygame.Rect(948, 18, 160, 48),
        'cancel': pygame.Rect(1114, 18, 150, 48),
    }


def _flash(estado, msg, seg=2.0):
    estado['team_flash_msg'] = msg
    estado['team_flash_timer'] = seg
    estado['team_flash_hasta'] = pygame.time.get_ticks() + int(seg * 1000)


def _jugador_de(alin, jugadores, sel):
    """Jugador (objeto) de una selección (zona, i) o None si es inválida."""
    try:
        zona, i = sel
        idx = alin.titulares[i] if zona == 'campo' else alin.convocados[i] if zona == 'banco' else i
        return jugadores[idx] if 0 <= idx < len(jugadores) else None
    except Exception:
        return None


def _energia_de(estado, j, en_partido: bool) -> float:
    """v3.1.0: energía a mostrar (en vivo = la del minuto actual según lo que lleva jugado)."""
    from alpha_football import energia as E
    if en_partido:
        # v3.3.0: mismo multiplicador de gasto que el motor (Kloppismo gasta más).
        from alpha_football.estilos import factor_gasto_estilo
        mult = factor_gasto_estilo(getattr(estado.get('mi_equipo'), 'estilo_dt', ''))
        return E.energia_en_minuto(j, (estado.get('sim_minuto_por_jugador') or {}).get(j.id, 0), mult)
    return float(getattr(j, 'energia', 100.0))


def texto_nota_vivo(j, estado):
    """v3.6.0: nota en vivo del titular (fuente: estado['sim_nota_por_jugador'] de match_screen,
    que arranca en 6.0) como (texto, color): ≥ 7.5 verde, ≥ 6 blanco, < 6 rojo. None sin partido."""
    try:
        notas = (estado or {}).get('sim_nota_por_jugador')
        if not isinstance(notas, dict):
            return None
        n = float(notas.get(getattr(j, 'id', None), 6.0) or 6.0)
        return (f"{n:.1f}", 'verde' if n >= 7.5 else ('blanco' if n >= 6 else 'rojo'))
    except Exception as e:
        logger.error(f"No se pudo leer la nota en vivo: {e}")
        return None


def _barra_energia(screen, x, y, ancho, e) -> None:
    from alpha_football.energia import UMBRAL_AMARILLO, UMBRAL_ROJO   # v4.4.0
    col = COLORS['verde'] if e >= UMBRAL_AMARILLO else (COLORS['dorado'] if e >= UMBRAL_ROJO else COLORS['rojo'])
    pygame.draw.rect(screen, (40, 50, 70), pygame.Rect(x, y, ancho, 5), border_radius=2)
    pygame.draw.rect(screen, col, pygame.Rect(x, y, int(ancho * max(0.0, min(100.0, e)) / 100), 5), border_radius=2)


def _dibujar_tarjeta(screen, rect, j, seleccionada, hover, sustituido=False, energia=None):
    col = POS_COLOR.get(getattr(j, 'posicion', 'MED'), GRIS_CLAR) if not sustituido else (70, 70, 80)
    pygame.draw.rect(screen, (30, 45, 75) if hover else (15, 22, 40), rect, border_radius=6)
    pygame.draw.rect(screen, col, pygame.Rect(rect.x, rect.y, rect.width, 22),
                     border_top_left_radius=6, border_top_right_radius=6)
    draw_text(screen, f"{j.posicion}  {j.overall}", (rect.x + 8, rect.y + 2), size='sm', color='blanco', shadow=False)
    draw_text(screen, _truncar(getattr(j, 'apellido', '') or j.nombre, 11), (rect.x + 8, rect.y + 30), size='sm', color='blanco')
    draw_text(screen, _truncar(getattr(j, 'nombre', ''), 11), (rect.x + 8, rect.y + 52), size='sm', color='azul', shadow=False)
    if sustituido:
        draw_text(screen, "SUSTITUIDO", (rect.x + 8, rect.y + 76), size='sm', color='rojo', shadow=False)
    elif getattr(j, 'lesion_partidos', 0) > 0:
        draw_text(screen, f"LESIÓN {j.lesion_partidos}", (rect.x + 8, rect.y + 76), size='sm', color='rojo', shadow=False)
    else:
        draw_text(screen, f"Moral {getattr(j, 'moral', 70)}", (rect.x + 8, rect.y + 76), size='sm', color='verde', shadow=False)
    _barra_energia(screen, rect.x + 8, rect.bottom - 9, rect.width - 16,
                   float(getattr(j, 'energia', 100.0)) if energia is None else energia)   # v3.1.0
    pygame.draw.rect(screen, AMARILLO if seleccionada else (60, 80, 110), rect,
                     width=4 if seleccionada else 1, border_radius=6)


SUBS_MAX_PARTIDO = 5


def _cambio_en_partido(estado, alin, jugadores, sel, hit, subs_hechas, salieron):
    """v2.3.6: aplica un intercambio EN VIVO respetando las reglas del partido.
    campo↔campo = cambio de puesto (gratis); campo↔banco = sustitución (cuenta,
    máx. 5, el que sale no puede volver a entrar); banco↔banco no aplica."""
    zonas = {sel[0], hit[0]}
    if zonas == {'campo'}:
        F.intercambiar(alin, sel, hit)
        _flash(estado, "Cambio de puesto", 1.2)
        return
    if zonas != {'campo', 'banco'}:
        _flash(estado, "Elige un titular y un suplente del banco", 1.8)
        return
    campo = sel if sel[0] == 'campo' else hit
    banco = hit if campo is sel else sel
    idx_sale = alin.titulares[campo[1]]
    idx_entra = alin.convocados[banco[1]]
    # v4.1.0: un expulsado (o lesionado sin cambio) ya no está en la cancha: no se reemplaza
    if id(jugadores[idx_sale]) in getattr(estado.get('sim_ctx'), 'fuera', set()):
        _flash(estado, f"{jugadores[idx_sale].apellido} ya no está en la cancha", 2.2)
        return
    if idx_entra in salieron:
        _flash(estado, f"{jugadores[idx_entra].apellido} ya fue sustituido: no puede volver", 2.2)
        return
    if subs_hechas >= SUBS_MAX_PARTIDO:
        _flash(estado, f"Ya hiciste los {SUBS_MAX_PARTIDO} cambios permitidos", 2.2)
        return
    if getattr(jugadores[idx_entra], 'lesion_partidos', 0) > 0:
        _flash(estado, f"{jugadores[idx_entra].apellido} está lesionado", 2.0)
        return
    F.intercambiar(alin, campo, banco)
    salieron.add(idx_sale)
    estado['sim_salieron'] = sorted(salieron)
    estado['sim_subs_realizadas'] = subs_hechas + 1
    sale, entra = jugadores[idx_sale].apellido, jugadores[idx_entra].apellido
    estado.setdefault('sim_comentarios', []).append(
        f"CAMBIO ({subs_hechas + 1}/{SUBS_MAX_PARTIDO}): SALE {sale}, ENTRA {entra}")
    _flash(estado, f"Sale {sale} · entra {entra}", 1.6)


def _render_direccion(screen, estado, mi_equipo, alin, es_amistoso, modo_prepartido,
                      ret_screen, mouse_pos, click_pos, en_partido=False, key_events=None):
    """
    v2.3.5: Dirección de equipo estilo FIFA. Una sola pantalla: los 11 en el campo,
    el banco (10) abajo y la ficha del jugador seleccionado a la derecha.
    Clic en un jugador = seleccionarlo; clic en otro = intercambiarlos
    (campo↔campo cambia de puesto, campo/banco↔banco/reserva cambia de jugador).
    Nunca se borra a nadie: siempre hay 11 titulares.

    en_partido=True (dirección EN VIVO desde match_screen): sin reservas (solo entran
    los convocados), máximo 5 cambios, el que sale no vuelve y sin AUTO. REANUDAR
    devuelve `ret_screen`; DESHACER revierte lo hecho desde que se abrió. Todo vale solo
    para ese partido (match_screen restaura la alineación al terminar).
    """
    jugadores = mi_equipo.jugadores
    subs_hechas = int(estado.get('sim_subs_realizadas', 0) or 0)
    salieron = set(estado.get('sim_salieron', []) or [])
    form_lista = F.lista_formaciones()
    if key_events is None:   # v4.2.0: en vivo, match_screen ya leyó los eventos y los pasa
        key_events = [e for e in pygame.event.get() if e.type == pygame.KEYDOWN]
    sel = estado.get('team_sel')
    if sel is not None and _jugador_de(alin, jugadores, sel) is None:
        sel = estado['team_sel'] = None
    ver_reservas = estado.get('team_view') == 'reservas' and not en_partido

    # --- Cabecera: título, cicladores y acciones ---
    draw_gradient_bg(screen)
    draw_text(screen, "DIRECCIÓN EN VIVO" if en_partido else "DIRECCIÓN DE EQUIPO", (16, 16), size='md', color='dorado')
    if en_partido:
        draw_text(screen, f"Cambios: {subs_hechas}/{SUBS_MAX_PARTIDO}", (16, 50), size='sm',
                  color='verde' if subs_hechas < SUBS_MAX_PARTIDO else 'rojo')
        draw_text(screen, _truncar(mi_equipo.nombre.upper(), 22), (150, 50), size='sm', color='verde')
    else:
        draw_text(screen, _truncar(mi_equipo.nombre.upper(), 30), (16, 50), size='sm', color='verde')

    rc = _rects_cabecera()
    r_f_prev, r_f_box, r_f_next = rc['form_prev'], rc['form_box'], rc['form_next']
    r_t_prev, r_t_box, r_t_next = rc['tact_prev'], rc['tact_box'], rc['tact_next']
    r_m_prev, r_m_box, r_m_next = rc['ment_prev'], rc['ment_box'], rc['ment_next']
    b_auto, b_ok, b_cancel = rc['auto'], rc['ok'], rc['cancel']
    ment = getattr(mi_equipo, 'mentalidad', 'normal')
    ment = ment if ment in MENTALIDADES else 'normal'
    for prev, box, nxt, valor, etiqueta, color in (
            (r_f_prev, r_f_box, r_f_next, alin.formacion, "FORMACIÓN", COLORS['verde']),
            (r_t_prev, r_t_box, r_t_next, NOMBRE_ESTILO.get(mi_equipo.estilo_dt or TACTICAS[0],
                                                             (mi_equipo.estilo_dt or TACTICAS[0]).capitalize()),
             "ESTILO", COLORS['dorado']),
            (r_m_prev, r_m_box, r_m_next, NOMBRE_MENTALIDAD[ment], "MENTALIDAD", COLORS['rojo'])):
        draw_styled_button(screen, prev, "<", prev.collidepoint(mouse_pos), color)
        draw_styled_button(screen, nxt, ">", nxt.collidepoint(mouse_pos), color)
        pygame.draw.rect(screen, (15, 22, 40), box, border_radius=6)
        pygame.draw.rect(screen, color, box, width=2, border_radius=6)
        draw_text(screen, etiqueta, (box.x + 4, box.y - 16), size='sm', color='azul', shadow=False)
        f = get_font('md' if get_font('md').size(valor)[0] <= box.width - 8 else 'sm')
        s = f.render(valor, True, color)
        screen.blit(s, s.get_rect(center=box.center))
    if not en_partido:
        draw_styled_button(screen, b_auto, "AUTO", b_auto.collidepoint(mouse_pos), COLORS['azul'])
    draw_styled_button(screen, b_ok, "REANUDAR" if en_partido else "CONFIRMAR", b_ok.collidepoint(mouse_pos), COLORS['verde'])
    draw_styled_button(screen, b_cancel, "DESHACER" if en_partido else "CANCELAR", b_cancel.collidepoint(mouse_pos), COLORS['rojo'])

    fam = int(float((mi_equipo.tactica_familiaridad or {}).get(mi_equipo.estilo_dt, 0.0)) * 100)
    ayuda = ("Titular↔banco = cambio (máx. 5, el que sale no vuelve)  ·  titular↔titular = cambio de puesto"
             if en_partido else "Clic en un jugador para seleccionarlo y clic en otro para intercambiarlos")
    pref_f = F.pref(alin.formacion)
    draw_text(screen, f"{ayuda}  ·  Estilo preferido de {alin.formacion}: {NOMBRE_ESTILO.get(pref_f, pref_f)}  ·  Familiaridad {fam}%",
              (16, 76), size='sm', color='azul', shadow=False)

    # --- Campo con los 11 (slot k = titulares[k]) ---
    pygame.draw.rect(screen, VERDE_CAMPO, _CAMPO, border_radius=8)
    franja = _CAMPO.height // 8
    for i in range(8):
        if i % 2:
            pygame.draw.rect(screen, VERDE_CAMPO2, pygame.Rect(_CAMPO.x + 2, _CAMPO.y + i * franja + 2, _CAMPO.width - 4, franja))
    pygame.draw.rect(screen, BLANCO, _CAMPO, width=2, border_radius=8)
    pygame.draw.line(screen, (220, 220, 220), (_CAMPO.x + 8, _CAMPO.centery), (_CAMPO.right - 8, _CAMPO.centery), 1)
    pygame.draw.circle(screen, (220, 220, 220), _CAMPO.center, 56, 1)
    pygame.draw.rect(screen, (220, 220, 220), pygame.Rect(_CAMPO.centerx - 150, _CAMPO.bottom - 80, 300, 80), 1)
    pygame.draw.rect(screen, (220, 220, 220), pygame.Rect(_CAMPO.centerx - 150, _CAMPO.y, 300, 80), 1)

    tipos = F.puestos(alin.formacion)
    hits = []   # (rect, seleccion)
    for k, (px, py) in enumerate(F.posiciones(alin.formacion)):
        if k >= len(alin.titulares) or not (0 <= alin.titulares[k] < len(jugadores)):
            continue
        j = jugadores[alin.titulares[k]]
        cx, cy = _CAMPO.x + int(_CAMPO.width * px), _CAMPO.y + int(_CAMPO.height * py)
        area = pygame.Rect(cx - 50, cy - 28, 100, 70)
        hits.append((area, ('campo', k)))
        es_sel = sel == ('campo', k)
        fuera = tipos[k] != j.posicion           # jugando fuera de su puesto
        pygame.draw.circle(screen, (0, 0, 0), (cx + 2, cy + 3), 25)
        pygame.draw.circle(screen, POS_COLOR.get(j.posicion, GRIS_CLAR), (cx, cy), 25)
        pygame.draw.circle(screen, AMARILLO if es_sel else (BLANCO if not area.collidepoint(mouse_pos) else COLORS['verde']),
                           (cx, cy), 25, 4 if es_sel else 2)
        f = get_font('sm')
        s = f.render(str(j.overall), True, BLANCO)
        screen.blit(s, s.get_rect(center=(cx, cy)))
        nombre = _truncar(getattr(j, 'apellido', '') or j.nombre, 12)
        s = f.render(nombre, True, AMARILLO if es_sel else BLANCO)
        fondo = s.get_rect(center=(cx, cy + 38)).inflate(8, 2)
        pygame.draw.rect(screen, (10, 14, 26), fondo, border_radius=4)
        screen.blit(s, s.get_rect(center=(cx, cy + 38)))
        _barra_energia(screen, cx - 30, cy + 50, 60, _energia_de(estado, j, en_partido))   # v3.1.0
        nota = texto_nota_vivo(j, estado) if en_partido else None       # v3.6.0: nota en vivo
        if nota:
            s = f.render(nota[0], True, COLORS.get(nota[1], BLANCO))
            caja = s.get_rect(midleft=(cx + 30, cy - 14)).inflate(8, 2)
            pygame.draw.rect(screen, (10, 14, 26), caja, border_radius=4)
            screen.blit(s, s.get_rect(center=caja.center))
        etiqueta_puesto = f"{tipos[k]}" + (" !" if fuera else "")
        draw_text(screen, etiqueta_puesto, (cx - 16, cy - 44), size='sm', color='rojo' if fuera else 'blanco', shadow=True)

    # --- Ficha del jugador seleccionado ---
    draw_panel(screen, _FICHA)
    jsel = _jugador_de(alin, jugadores, sel) if sel else None
    if jsel is None:
        draw_text(screen, "FICHA DEL JUGADOR", (_FICHA.x + 16, _FICHA.y + 14), size='md', color='dorado')
        for n, linea in enumerate(["Haz clic en un jugador del", "campo, del banco o de las",
                                   "reservas para seleccionarlo.", "", "Luego clic en otro para",
                                   "intercambiarlos."]):
            draw_text(screen, linea, (_FICHA.x + 16, _FICHA.y + 60 + n * 26), size='sm', color='blanco')
        # v3.3.0: descripción del estilo elegido (bajo el selector no hay lugar: y=76 es la ayuda).
        try:
            est = mi_equipo.estilo_dt if mi_equipo.estilo_dt in TACTICAS else TACTICAS[0]
            draw_text(screen, f"ESTILO: {NOMBRE_ESTILO[est].upper()}", (_FICHA.x + 16, _FICHA.y + 240),
                      size='md', color='dorado')
            f_d, linea, lineas = get_font('sm'), "", []
            for palabra in DESC_ESTILO[est].split():
                prueba = f"{linea} {palabra}".strip()
                if f_d.size(prueba)[0] > _FICHA.width - 32 and linea:
                    lineas.append(linea)
                    prueba = palabra
                linea = prueba
            lineas.append(linea)
            for n, l_ in enumerate(lineas[:4]):
                draw_text(screen, l_, (_FICHA.x + 16, _FICHA.y + 276 + n * 24), size='sm', color='blanco', shadow=False)
        except Exception as e_est:
            logger.error(f"Error al dibujar la descripción del estilo: {e_est}")
    else:
        zona_txt = {'campo': "TITULAR", 'banco': "BANCO", 'reserva': "RESERVA"}[sel[0]]
        draw_text(screen, _truncar(f"{jsel.nombre} {jsel.apellido}", 20), (_FICHA.x + 16, _FICHA.y + 14), size='md', color='dorado')
        draw_text(screen, f"{jsel.posicion}  ·  OVR {jsel.overall}  ·  {zona_txt}", (_FICHA.x + 16, _FICHA.y + 48), size='sm', color='verde')
        datos = [("Edad", getattr(jsel, 'edad', '?')), ("Potencial", getattr(jsel, 'potencial', 0) or '?'),
                 ("Ataque", jsel.ataque), ("Defensa", jsel.defensa), ("Físico", jsel.fisico),
                 ("Técnica", jsel.tecnica), ("Mental", jsel.mental), ("Moral", getattr(jsel, 'moral', 70)),
                 ("Goles", getattr(jsel, 'goles', 0)), ("Rasgo", getattr(jsel, 'rasgo', '') or '-'),
                 ("Resistencia", getattr(jsel, 'resistencia', 50)),                        # v3.1.0
                 ("Energía", int(_energia_de(estado, jsel, en_partido))),
                 ("Personalidad", PERSONALIDAD_TXT.get(getattr(jsel, 'personalidad', ''), '-'))]
        for n, (k_, v) in enumerate(datos):
            yy = _FICHA.y + 84 + n * 23
            draw_text(screen, k_, (_FICHA.x + 16, yy), size='sm', color='azul', shadow=False)
            draw_text(screen, _truncar(str(v), 16), (_FICHA.x + 130, yy), size='sm', color='blanco', shadow=False)
            if isinstance(v, int) and k_ in ("Ataque", "Defensa", "Físico", "Técnica", "Mental", "Moral",
                                             "Resistencia", "Energía"):
                barra = pygame.Rect(_FICHA.x + 180, yy + 4, 100, 10)
                pygame.draw.rect(screen, (40, 50, 70), barra, border_radius=3)
                pygame.draw.rect(screen, COLORS['verde'], pygame.Rect(barra.x, barra.y, int(barra.width * max(0, min(99, v)) / 99), 10), border_radius=3)
        if getattr(jsel, 'lesion_partidos', 0) > 0:
            draw_text(screen, f"LESIONADO ({jsel.lesion_partidos} partidos)", (_FICHA.x + 16, _FICHA.bottom - 60), size='sm', color='rojo')
        draw_text(screen, "Clic de nuevo para soltarlo", (_FICHA.x + 16, _FICHA.bottom - 30), size='sm', color='azul', shadow=False)

    # --- Banco (10) o reservas abajo ---
    en_listas = set(alin.titulares) | set(alin.convocados)
    reservas = sorted((i for i in range(len(jugadores)) if i not in en_listas),
                      key=lambda i: (POS_ORDEN.get(jugadores[i].posicion, 9), -jugadores[i].overall))
    pag = int(estado.get('team_res_page', 0))
    n_pag = max(1, (len(reservas) + 9) // 10)
    pag = max(0, min(pag, n_pag - 1))
    estado['team_res_page'] = pag

    b_toggle, b_prev, b_next = R_BANCO_TOGGLE, R_BANCO_PREV, R_BANCO_NEXT
    titulo = (f"RESERVAS ({len(reservas)})  ·  pág. {pag + 1}/{n_pag}" if ver_reservas
              else f"BANCO ({len(alin.convocados)}/10)  ·  pueden entrar en el partido")
    if sel is not None and sel[0] == 'reserva' and not ver_reservas:
        titulo += "  ·  elige a quién reemplaza la reserva"
    draw_text(screen, titulo, (16, _BANCO_Y - 16), size='sm', color='dorado')
    if not en_partido:
        draw_styled_button(screen, b_toggle, "VER BANCO" if ver_reservas else "VER RESERVAS",
                           b_toggle.collidepoint(mouse_pos), COLORS['azul'])
    if ver_reservas and n_pag > 1:
        draw_styled_button(screen, b_prev, "◀", b_prev.collidepoint(mouse_pos), COLORS['azul'])
        draw_styled_button(screen, b_next, "▶", b_next.collidepoint(mouse_pos), COLORS['azul'])

    fila = ([('reserva', i) for i in reservas[pag * 10:pag * 10 + 10]] if ver_reservas
            else [('banco', i) for i in range(len(alin.convocados))])
    for n, s_ in enumerate(fila):
        rect = rect_tarjeta_banco(n)
        j = _jugador_de(alin, jugadores, s_)
        if j is None:
            continue
        hits.append((rect, s_))
        fuera_partido = en_partido and s_[0] == 'banco' and alin.convocados[s_[1]] in salieron
        _dibujar_tarjeta(screen, rect, j, sel == s_, rect.collidepoint(mouse_pos), fuera_partido,
                         _energia_de(estado, j, en_partido))
    if ver_reservas and not reservas:
        draw_text(screen, "No hay reservas: toda la plantilla está en el once o en el banco.",
                  (16, _BANCO_Y + 50), size='sm', color='blanco')

    # Mensaje flash
    if pygame.time.get_ticks() < estado.get('team_flash_hasta', 0) and estado.get('team_flash_msg'):
        s = get_font('md').render(estado['team_flash_msg'], True, AMARILLO)
        caja = s.get_rect(center=(_CAMPO.centerx, _CAMPO.y + 24)).inflate(24, 12)
        pygame.draw.rect(screen, (10, 14, 26), caja, border_radius=8)
        pygame.draw.rect(screen, AMARILLO, caja, width=2, border_radius=8)
        screen.blit(s, s.get_rect(center=caja.center))

    # v4.2.0: cursor de teclado sobre las tarjetas (← → mueve, ↑ ↓ cambia campo/banco,
    # Espacio = clic en la tarjeta: seleccionar / intercambiar)
    if hits:
        cur = max(0, min(int(estado.get('team_cursor', 0) or 0), len(hits) - 1))
        for ev in key_events:
            if ev.key == pygame.K_RIGHT:
                cur = (cur + 1) % len(hits)
            elif ev.key == pygame.K_LEFT:
                cur = (cur - 1) % len(hits)
            elif ev.key == pygame.K_DOWN:
                cur = next((i for i, (_r, s_) in enumerate(hits) if s_[0] != 'campo'), cur)
            elif ev.key == pygame.K_UP:
                cur = next((i for i, (_r, s_) in enumerate(hits) if s_[0] == 'campo'), cur)
            elif ev.key == pygame.K_SPACE and click_pos is None:
                click_pos = hits[cur][0].center
        estado['team_cursor'] = cur
        pygame.draw.rect(screen, (255, 255, 255), hits[cur][0].inflate(6, 6), width=2, border_radius=8)

    # --- Teclado ---
    accion = None
    for ev in key_events:
        if ev.key == pygame.K_ESCAPE:
            accion = 'soltar' if sel is not None else 'cancelar'
        elif ev.key == pygame.K_RETURN:
            accion = 'confirmar'
        elif ev.key == pygame.K_a and not en_partido:
            accion = 'auto'
        elif ev.key == pygame.K_r and not en_partido:
            accion = 'toggle'
        elif ev.key in (pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET):
            accion = ('form', -1 if ev.key == pygame.K_LEFTBRACKET else 1)
        elif ev.key in (pygame.K_MINUS, pygame.K_EQUALS):
            accion = ('tact', -1 if ev.key == pygame.K_MINUS else 1)
        elif ev.key in (pygame.K_COMMA, pygame.K_PERIOD):
            accion = ('ment', -1 if ev.key == pygame.K_COMMA else 1)

    # --- Clics ---
    if click_pos and accion is None:
        if r_f_prev.collidepoint(click_pos) or r_f_next.collidepoint(click_pos):
            accion = ('form', -1 if r_f_prev.collidepoint(click_pos) else 1)
        elif r_t_prev.collidepoint(click_pos) or r_t_next.collidepoint(click_pos):
            accion = ('tact', -1 if r_t_prev.collidepoint(click_pos) else 1)
        elif r_m_prev.collidepoint(click_pos) or r_m_next.collidepoint(click_pos):
            accion = ('ment', -1 if r_m_prev.collidepoint(click_pos) else 1)
        elif b_auto.collidepoint(click_pos) and not en_partido:
            accion = 'auto'
        elif b_ok.collidepoint(click_pos):
            accion = 'confirmar'
        elif b_cancel.collidepoint(click_pos):
            accion = 'cancelar'
        elif b_toggle.collidepoint(click_pos) and not en_partido:
            accion = 'toggle'
        elif ver_reservas and b_prev.collidepoint(click_pos):
            estado['team_res_page'] = (pag - 1) % n_pag
        elif ver_reservas and b_next.collidepoint(click_pos):
            estado['team_res_page'] = (pag + 1) % n_pag
        else:
            hit = next((s_ for r, s_ in hits if r.collidepoint(click_pos)), None)
            if hit is None:
                pass
            elif sel is None:
                estado['team_sel'] = hit
            elif hit == sel:
                estado['team_sel'] = None
            elif sel[0] == 'reserva' and hit[0] == 'reserva':
                estado['team_sel'] = hit          # cambiar de reserva seleccionada
            elif en_partido:
                _cambio_en_partido(estado, alin, jugadores, sel, hit, subs_hechas, salieron)
                estado['team_sel'] = None
            else:
                entra_a_lista = [s_ for s_ in (sel, hit) if s_[0] == 'reserva']
                otro = hit if sel[0] == 'reserva' else sel
                j_res = _jugador_de(alin, jugadores, entra_a_lista[0]) if entra_a_lista else None
                if j_res is not None and getattr(j_res, 'lesion_partidos', 0) > 0:
                    _flash(estado, f"{j_res.apellido} está lesionado: no puede jugar")
                else:
                    a_nombre = _jugador_de(alin, jugadores, sel).apellido
                    b_nombre = _jugador_de(alin, jugadores, hit).apellido
                    F.intercambiar(alin, sel, hit)
                    _flash(estado, f"{a_nombre} ⇄ {b_nombre}", 1.5)
                estado['team_sel'] = None

    if accion == 'soltar':
        estado['team_sel'] = None
    elif accion == 'toggle':
        # v2.3.6: la selección se conserva al cambiar de vista para poder cambiar una
        # reserva por un jugador del banco (antes se soltaba y era imposible).
        estado['team_view'] = 'once' if ver_reservas else 'reservas'
    elif accion == 'auto':
        alin.titulares = F.mejor_once(jugadores, alin.formacion)
        alin.convocados = []
        F.normalizar_convocados(alin, jugadores)
        estado['team_sel'] = None
        _flash(estado, f"Mejor once y banco para {alin.formacion}")
    elif isinstance(accion, tuple) and accion[0] == 'form':
        i = form_lista.index(alin.formacion) if alin.formacion in form_lista else 0
        alin.formacion = form_lista[(i + accion[1]) % len(form_lista)]
        alin.titulares = F.acomodar_en_puestos(alin.titulares, jugadores, alin.formacion)
        estado['team_sel'] = None
        _flash(estado, f"Formación {alin.formacion}", 1.2)
    elif isinstance(accion, tuple) and accion[0] == 'tact':
        actual = mi_equipo.estilo_dt if mi_equipo.estilo_dt in TACTICAS else TACTICAS[0]
        mi_equipo.estilo_dt = TACTICAS[(TACTICAS.index(actual) + accion[1]) % len(TACTICAS)]
    elif isinstance(accion, tuple) and accion[0] == 'ment':
        mi_equipo.mentalidad = MENTALIDADES[(MENTALIDADES.index(ment) + accion[1]) % len(MENTALIDADES)]
    elif accion == 'confirmar' and en_partido:
        _salir_direccion(estado, es_amistoso, modo_prepartido)
        return ret_screen
    elif accion == 'cancelar' and en_partido:
        alin.titulares = list(estado.get('_original_alignment', alin.titulares))
        alin.convocados = list(estado.get('_original_convocados', alin.convocados))
        alin.formacion = estado.get('_original_formacion', alin.formacion)
        mi_equipo.estilo_dt = estado.get('_original_estilo', mi_equipo.estilo_dt)
        mi_equipo.mentalidad = estado.get('_original_mentalidad', ment)
        estado['sim_subs_realizadas'] = int(estado.get('_original_subs', subs_hechas) or 0)
        estado['sim_salieron'] = list(estado.get('_original_salieron', []) or [])
        estado['team_sel'] = None
        _flash(estado, "Cambios deshechos", 1.2)
    elif accion == 'confirmar':
        F.normalizar_convocados(alin, jugadores)
        if alin.es_valida(jugadores):
            mi_equipo.alineacion_activa = alin
            _salir_direccion(estado, es_amistoso, modo_prepartido)
            return ret_screen
        _flash(estado, "El once necesita 1 POR, 3+ DEF, 2+ MED y 1+ DEL", 2.5)
    elif accion == 'cancelar':
        alin.titulares = list(estado.get('_original_alignment', alin.titulares))
        alin.convocados = list(estado.get('_original_convocados', alin.convocados))
        alin.formacion = estado.get('_original_formacion', alin.formacion)
        mi_equipo.mentalidad = estado.get('_original_mentalidad', ment)
        _salir_direccion(estado, es_amistoso, modo_prepartido)
        return ret_screen
    return None


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """
    Renderiza la pantalla de Dirección de Equipo en Pygame.
    Retorna la pantalla de destino ('league_screen', 'market_screen', etc.) o None.

    v0.8.3 (F1): si estado['team_equipo_objetivo'] apunta a un equipo distinto del
    usuario, team_screen funciona en MODO VISOR (read-only): muestra la formación y
    alineación del rival en el mismo esquema de campo, sin permitir editar formación,
    táctica ni hacer cambios. Un botón "VOLVER A MI ONCE" permite regresar al modo
    edición del equipo del usuario.
    """
    try:
        # Recuperación de datos del estado
        liga = estado.get('liga')
        mi_equipo = estado.get('mi_equipo')

        # v0.8.5: en AMISTOSO, dirección de equipo gestiona el equipo ELEGIDO para el amistoso
        # (amis_local), no el de la última carrera. Aislamiento total de datos entre modos.
        es_amistoso = (estado.get('team_contexto') == 'amistoso')
        # v0.8.6 (Tarea 1): modo prepartido — team_screen muestra un panel compacto sin HUB de
        # carrera, porque se llega aquí desde prepartido (liga/copa/amistoso) y el usuario
        # todavía está eligiendo cómo encarar el partido. La bandera team_modo_prepartido la
        # setea prepartido_screen al pulsar "DIRECCIÓN DE EQUIPO".
        modo_prepartido = bool(estado.get('team_modo_prepartido'))
        ret_screen = "prepartido_screen" if (modo_prepartido or es_amistoso) else "league_screen"
        if es_amistoso:
            mi_equipo = estado.get('amis_local') or mi_equipo

        if not mi_equipo or (not es_amistoso and not liga):
            # v0.8.7.4: si estamos en modo visor (viendo al rival), NUNCA devolver "menu".
            # El usuario explícitamente pidió ver al rival, así que volver a prepartido
            # (si match_mode está seteado) o a league_screen si no.
            _tobj = estado.get('team_equipo_objetivo')
            if _tobj and _tobj is not mi_equipo:
                return "prepartido_screen" if estado.get('match_mode') else "league_screen"
            logger.error("Error: No hay equipo (o liga) en el estado de dirección de equipo.")
            return "prepartido_screen" if (modo_prepartido or es_amistoso) else "menu"

        # Capturar mouse_pos/click_pos ANTES de cualquier early return (v0.8.3:
        # el modo visor sale antes de la sección de eventos y necesita ambos).
        mouse_pos = pygame.mouse.get_pos()
        click_pos = None
        # v2.3.5: el modo visor (rival) necesita el clic de "VOLVER A MI ONCE".
        # main.py cachea los eventos por frame, así que leerlos aquí NO se los
        # quita al loop de teclado de más abajo (v2.3.2 lo había borrado y el
        # visor quedaba sin salida).
        try:
            for _ev in pygame.event.get():
                if _ev.type == pygame.QUIT:
                    return "quit"
                if _ev.type == pygame.MOUSEBUTTONDOWN and _ev.button == 1:
                    click_pos = _ev.pos
        except Exception:
            pass

        # v0.8.3: detectar si estamos en modo visor (viendo el rival)
        team_objetivo = estado.get('team_equipo_objetivo') or mi_equipo
        view_mode = (team_objetivo is not mi_equipo)

        # En modo visor, generar/recuperar una alineación del rival: los 11 mejores
        # por posición (POR,DEF,MED,DEL) según OVR descendente.
        if view_mode:
            from types import SimpleNamespace
            from alpha_football import formaciones as _F
            # Generar titulares ficticios del rival para mostrar en el campo
            _cuotas = {'POR': 1, 'DEF': 4, 'MED': 4, 'DEL': 2}
            # Objeto alineación "ficticio" para el rival: solo necesitamos los
            # atributos `formacion` y `titulares` que consume _render_team_view_mode.
            # v0.8.3 fix: `Equipo` no tiene `alineacion_activa` y `formaciones` no
            # expone `_Alineacion`; usamos SimpleNamespace como stand-in ligero.
            _f_riv = SimpleNamespace(formacion='4-4-2', titulares=[])
            # Calcular los 11 mejores por posición (los titulares del campo)
            _jugadores_riv = list(getattr(team_objetivo, 'jugadores', []) or [])
            _mejores = []
            for _pos, _qty in _cuotas.items():
                _cands = sorted(
                    [j for j in _jugadores_riv if getattr(j, 'posicion', '') == _pos],
                    key=lambda j: -getattr(j, 'overall', 0)
                )[:_qty]
                _mejores.extend(_cands)
            # Si faltan (p.ej. equipo con 0 jugadores en alguna posición), completar
            if len(_mejores) < 11:
                _resto = sorted(
                    [j for j in _jugadores_riv if j not in _mejores],
                    key=lambda j: -getattr(j, 'overall', 0)
                )
                _mejores.extend(_resto[:11 - len(_mejores)])
            _mejores = _mejores[:11]
            # Mapear los jugadores del rival a índices en su propia lista
            _riv_a_idx = {id(j): i for i, j in enumerate(_jugadores_riv)}
            _f_riv.titulares = [_riv_a_idx.get(id(j), 0) for j in _mejores]

        # Inicialización de alineación activa si no existe (modo edición normal).
        # v0.8.5: en amistoso la alineación vive en el PROPIO equipo (amis_local.alineacion_activa),
        # nunca en estado['alineacion_activa'] (que es la de la carrera) — así no se mezclan datos.
        from alpha_football.models import alineacion_por_defecto
        if es_amistoso:
            alin = getattr(mi_equipo, 'alineacion_activa', None)
            if not alin:
                alin = alineacion_por_defecto(mi_equipo)
                mi_equipo.alineacion_activa = alin
        else:
            alin = estado.get('alineacion_activa')
            if not alin:
                alin = alineacion_por_defecto(mi_equipo)
                estado['alineacion_activa'] = alin

        # v0.7: formación válida del registro.
        if not getattr(alin, 'formacion', None) or not F.existe(alin.formacion):
            alin.formacion = F.FORMACION_DEFECTO

        # v0.8.3 (F1): si estamos en MODO VISOR (viendo al rival), saltamos toda la
        # sección de edición y dibujamos un layout simplificado: solo lista de jugadores
        # del rival + campo con su mejor 11 + botón "VOLVER A MI ONCE".
        if view_mode:
            return _render_team_view_mode(screen, estado, team_objetivo, _f_riv, _mejores,
                                           _jugadores_riv, mouse_pos, click_pos)

        # v2.3.5: al entrar se respalda todo para CANCELAR, el banco queda válido
        # (índices corridos por ventas, lesionados), el once completo y cada titular
        # en un puesto de su posición (slot k del campo = titulares[k]).
        if '_original_formacion' not in estado:
            estado['_original_formacion'] = alin.formacion
            estado['_original_alignment'] = list(alin.titulares)
            estado['_original_convocados'] = list(getattr(alin, 'convocados', []) or [])
            estado['_original_mentalidad'] = getattr(mi_equipo, 'mentalidad', 'normal')
            F.normalizar_convocados(alin, mi_equipo.jugadores)
            if len(set(alin.titulares)) != 11 or not all(0 <= i < len(mi_equipo.jugadores) for i in alin.titulares):
                alin.titulares = F.mejor_once(mi_equipo.jugadores, alin.formacion)
                F.normalizar_convocados(alin, mi_equipo.jugadores)
            alin.titulares = F.acomodar_en_puestos(alin.titulares, mi_equipo.jugadores, alin.formacion)

        return _render_direccion(screen, estado, mi_equipo, alin, es_amistoso, modo_prepartido,
                                 ret_screen, mouse_pos, click_pos)
    except Exception as error_general:
        logger.error(f"Error general catastrófico en team_screen.render: {error_general}", exc_info=True)
        try:
            screen.fill((10, 20, 30))
            emerg_rect = pygame.Rect(490, 330, 300, 60)
            pygame.draw.rect(screen, (255, 68, 68), emerg_rect, border_radius=8)
            font = pygame.font.Font(None, 24)
            txt = font.render(f"ERROR: {str(error_general)[:25]}. CLIC PARA VOLVER", True, (255, 255, 255))
            screen.blit(txt, txt.get_rect(center=emerg_rect.center))
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if emerg_rect.collidepoint(event.pos):
                        return "league_screen"
        except Exception:
            return "league_screen"

    return None
