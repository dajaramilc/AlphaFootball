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
    draw_text(screen, f"ALINEACIÓN DEL RIVAL — {team_objetivo.nombre.upper()}",
              (300, 20), size='xl', color='dorado')
    est_l = getattr(team_objetivo, 'estilo_dt', 'anchelottismo') or 'anchelottismo'
    draw_text(screen, f"Estilo: {est_l.capitalize()}  ·  Formación: {f_riv.formacion}  ·  Vista de solo lectura",
              (300, 66), size='sm', color='azul')

    # Botón "VOLVER A MI ONCE" (arriba a la derecha)
    btn_volver = pygame.Rect(SCREEN_W - 260, 22, 240, 44)
    btn_volver_hover = btn_volver.collidepoint(mouse_pos)
    draw_styled_button(screen, btn_volver, "← VOLVER A MI ONCE", btn_volver_hover, COLORS.get('verde', (0, 255, 136)))
    if click_pos and btn_volver.collidepoint(click_pos):
        estado['team_equipo_objetivo'] = None
        return "prepartido_screen" if estado.get('match_mode') else "league_screen"

    # Lista de jugadores (read-only, no clicable)
    rect_lista = pygame.Rect(40, 100, 440, 580)
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
    for j in jugadores_ordenados[:15]:
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
                badge = pygame.Rect(fila_r.x + 10, fila_r.y + 4, 36, 18)
                pygame.draw.rect(screen, pc, badge, border_radius=3)
                draw_text(screen, j.posicion, (badge.x + 5, badge.y + 2), size='sm', color='blanco', shadow=False)
            except Exception:
                pass
            draw_text(screen, _truncar(j.nombre_completo, 20), (fila_r.x + 55, fila_r.y + 4), size='sm',
                      color='verde' if is_t else 'blanco')
            draw_text(screen, f"OVR {j.overall}", (fila_r.x + 55, fila_r.y + 18), size='sm', color='dorado')
        except Exception:
            pass
        y += fila_alto

    # Campo con los 11 mejores
    rect_campo = pygame.Rect(500, 100, 740, 480)
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
            ap = j.apellido[:10] if hasattr(j, 'apellido') else ''
            draw_text(screen, ap, (cx - 30, cy - 6), size='sm', color='blanco', shadow=True)
            draw_text(screen, f"#{j.overall}", (cx - 12, cy + 6), size='sm', color='dorado', shadow=True)
        except Exception:
            pass

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

        # Respaldar alineación para opción 'Cancelar'
        if '_original_alignment' not in estado:
            estado['_original_alignment'] = list(alin.titulares)

        # v0.7: formación válida del registro y posiciones del campo según ella.
        if not getattr(alin, 'formacion', None) or not F.existe(alin.formacion):
            alin.formacion = F.FORMACION_DEFECTO
        posiciones_campo = F.posiciones(alin.formacion)
        tacticas = ["anchelottismo", "cruyffismo", "flickismo", "haramball"]
        form_lista = F.lista_formaciones()

        # v0.8.3 (F1): si estamos en MODO VISOR (viendo al rival), saltamos toda la
        # sección de edición y dibujamos un layout simplificado: solo lista de jugadores
        # del rival + campo con su mejor 11 + botón "VOLVER A MI ONCE".
        if view_mode:
            return _render_team_view_mode(screen, estado, team_objetivo, _f_riv, _mejores,
                                           _jugadores_riv, mouse_pos, click_pos)

        # Cicladores de formación y táctica (en la cabecera derecha, sobre el campo).
        # v0.8.3: los rects dejan espacio ARRIBA para la etiqueta (no se superpone con
        # el texto "Preferida de X: Y · Fam Z%" que va más abajo).
        # v0.8.6 (Tarea 1): en modo_prepartido los cicladores se mueven al panel compacto
        # de la izquierda (más visibles y con el espacio del HUB libre).
        if modo_prepartido:
            rect_f_prev = pygame.Rect(50, 240, 28, 30)
            rect_f_box = pygame.Rect(82, 240, 130, 30)
            rect_f_next = pygame.Rect(216, 240, 28, 30)
            rect_t_prev = pygame.Rect(50, 320, 28, 30)
            rect_t_box = pygame.Rect(82, 320, 130, 30)
            rect_t_next = pygame.Rect(216, 320, 28, 30)
        else:
            rect_f_prev = pygame.Rect(770, 48, 30, 30)
            rect_f_box = pygame.Rect(804, 48, 150, 30)
            rect_f_next = pygame.Rect(958, 48, 30, 30)
            rect_t_prev = pygame.Rect(770, 98, 30, 30)
            rect_t_box = pygame.Rect(804, 98, 150, 30)
            rect_t_next = pygame.Rect(958, 98, 30, 30)

        rect_scr_up = pygame.Rect(740 - 80, 95 + 4, 32, 28)
        rect_scr_down = pygame.Rect(740 - 42, 95 + 4, 32, 28)

        # Inicializar variables auxiliares en el estado si faltan
        estado.setdefault('team_scroll_offset', 0)
        estado.setdefault('team_player_hover', -1)
        estado.setdefault('team_flash_msg', "")
        estado.setdefault('team_flash_timer', 0.0)

        # Descontar tiempo del mensaje de alerta
        dt = 1.0 / 60.0
        if estado['team_flash_timer'] > 0:
            estado['team_flash_timer'] -= dt
            if estado['team_flash_timer'] <= 0:
                estado['team_flash_msg'] = ""

        # 1. Dibujar fondo base con gradiente y líneas decorativas
        try:
            draw_gradient_bg(screen)
            draw_pitch_lines(screen)
        except Exception as e_bg:
            logger.error(f"Error de dibujo de fondo: {e_bg}")
            screen.fill(COLORS.get('bg', (10, 14, 26)))

        # Dibujar franjas decorativas superiores
        pygame.draw.rect(screen, COLORS.get('rojo', (255, 68, 68)), pygame.Rect(0, 0, SCREEN_W, 4))
        pygame.draw.rect(screen, COLORS.get('verde', (0, 255, 136)), pygame.Rect(0, 4, SCREEN_W, 4))
        pygame.draw.rect(screen, COLORS.get('azul', (0, 191, 255)), pygame.Rect(0, 8, SCREEN_W, 4))

        # --- MENÚ LATERAL IZQUIERDO (Consistencia visual 100%) ---
        # v0.8.6 (Tarea 1): en modo_prepartido el HUB de carrera NO se dibuja — el área izquierda
        # se reasigna a un panel compacto de "DIRECCIÓN DE EQUIPO" (ver bloque más abajo).
        if not modo_prepartido:
            menu_rect = pygame.Rect(20, 20, 260, 680)
            try:
                draw_panel(screen, menu_rect)
                pygame.draw.rect(screen, COLORS.get('rojo', (255, 68, 68)), pygame.Rect(22, 22, 4, 676))
                pygame.draw.rect(screen, COLORS.get('verde', (0, 255, 136)), pygame.Rect(26, 22, 4, 676))
                pygame.draw.rect(screen, COLORS.get('azul', (0, 191, 255)), pygame.Rect(30, 22, 4, 676))
            except Exception as e_menu:
                logger.error(f"Error al dibujar panel de menú: {e_menu}")

            # Títulos de la barra lateral
            draw_text(screen, "★ ALPHA ★", (45, 45), size='lg', color='verde')
            draw_text(screen, "FOOTBALL", (45, 80), size='md', color='blanco')
            pygame.draw.line(screen, COLORS.get('azul', (0, 191, 255)), (40, 120), (260, 120), 1)

            # Datos del Club
            draw_text(screen, mi_equipo.nombre.upper()[:18], (45, 135), size='sm', color='verde')
            pres_m = getattr(mi_equipo, 'balance', 0) / 1_000_000
            draw_text(screen, f"Presupuesto: ${pres_m:.1f}M", (45, 160), size='sm', color='blanco')
            draw_text(screen, f"Temporada: {estado.get('temporada', 1)}", (45, 185), size='sm', color='azul')
            jornada_actual = getattr(liga, "jornada_actual", 1)
            draw_text(screen, f"Jornada: {jornada_actual}/{getattr(liga, 'num_jornadas', 14)}", (45, 210), size='sm', color='dorado')

        # --- ENCABEZADO DE CONTENIDO (DERECHA) ---
        # v0.8.6 (Tarea 1): en modo_prepartido el título se acorta (estamos en el submenú
        # de prepartido, no en la pantalla principal de dirección).
        if modo_prepartido:
            draw_text(screen, "DIRECCIÓN DE EQUIPO", (300, 20), size='xl', color='dorado')
            draw_text(screen, "Elegí formación, táctica y once para el próximo partido.", (300, 66), size='sm', color='azul')
        else:
            draw_text(screen, "DIRECCIÓN TÁCTICA DEL EQUIPO", (300, 20), size='xl', color='dorado')
            draw_text(screen, "Define tu once, formación y táctica.", (300, 66), size='sm', color='azul')

        # --- v0.7: CICLADORES DE FORMACIÓN Y TÁCTICA ---
        # v0.8.3: las etiquetas ("FORMACIÓN", "TÁCTICA") se dibujan ARRIBA del box
        # en vez de a la derecha. Antes chocaban con el texto "Preferida..." y se
        # cortaban.
        # v0.8.6 (Tarea 1): en modo_prepartido los cicladores se dibujaron en la izquierda
        # (ver bloque rect_f_* más arriba); en modo normal siguen arriba a la derecha.
        _mp = pygame.mouse.get_pos()

        def _cycler(prev_r, box_r, next_r, valor, etiqueta, color_acc, label_y_above=True):
            draw_styled_button(screen, prev_r, "<", prev_r.collidepoint(_mp), color_acc)
            draw_styled_button(screen, next_r, ">", next_r.collidepoint(_mp), color_acc)
            try:
                pygame.draw.rect(screen, (15, 22, 40), box_r, border_radius=6)
                pygame.draw.rect(screen, color_acc, box_r, width=2, border_radius=6)
            except Exception:
                pass
            vs = get_font('sm').render(str(valor), True, (255, 255, 255))
            screen.blit(vs, vs.get_rect(center=box_r.center))
            if label_y_above:
                # Etiqueta ARRIBA del box (no choca con el texto "Preferida...").
                draw_text(screen, etiqueta, (box_r.x, box_r.y - 18), size='sm', color='azul')
            else:
                draw_text(screen, etiqueta, (box_r.right + 6, box_r.y + 6), size='sm', color='azul')

        _cycler(rect_f_prev, rect_f_box, rect_f_next, alin.formacion, "FORMACIÓN",
                COLORS.get('verde', (0, 255, 136)))
        _fam_pct = int(float((mi_equipo.tactica_familiaridad or {}).get(mi_equipo.estilo_dt, 0.0)) * 100)
        _cycler(rect_t_prev, rect_t_box, rect_t_next, mi_equipo.estilo_dt, "TÁCTICA",
                COLORS.get('dorado', (255, 215, 0)))
        # v0.8.3: el texto "Preferida..." se mueve más abajo para no chocar con los
        # cyclers de táctica.
        # v0.8.6 (Tarea 1): en modo_prepartido va debajo de los cicladores (que están a
        # la izquierda); en modo normal sigue a la derecha.
        if modo_prepartido:
            draw_text(screen, f"Preferida: {F.pref(alin.formacion)}  ·  Fam {_fam_pct}%",
                      (50, 370), size='sm', color='blanco')
        else:
            draw_text(screen, f"Preferida de {alin.formacion}: {F.pref(alin.formacion)}  ·  Familiaridad: {_fam_pct}%",
                      (1000, 145), size='sm', color='blanco')

        # --- BOTONES EN EL MENÚ IZQUIERDO ---
        # v0.8.6 (Tarea 1): en modo_prepartido NO se dibujan los 8 botones de la barra
        # lateral (son navegación del HUB de carrera). En su lugar, el área izquierda
        # muestra un panel compacto con cicladores, AUTO ONCE y VOLVER (ver bloque más
        # abajo). Las variables quedan definidas como None para que el handler de clics
        # no falle.
        btn_jugar = btn_mercado = btn_copa = btn_ofertas = btn_stats = btn_career = btn_equipo = btn_salir = None
        btn_auto_pp = None
        btn_volver_pp = None
        if not modo_prepartido:
            btn_jugar = pygame.Rect(40, 232, 220, 44)
            btn_mercado = pygame.Rect(40, 288, 220, 44)
            btn_copa = pygame.Rect(40, 344, 220, 44)
            btn_ofertas = pygame.Rect(40, 400, 220, 44)
            btn_stats = pygame.Rect(40, 456, 220, 44)
            btn_career = pygame.Rect(40, 512, 220, 44)
            btn_equipo = pygame.Rect(40, 568, 220, 44)
            btn_salir = pygame.Rect(40, 632, 220, 44)

        # v0.8.3: mouse_pos/click_pos ya se capturaron arriba (modo visor los usa).
        # Refrescar para los eventos de scroll/click que faltan en este punto.
        mouse_pos = pygame.mouse.get_pos()
        click_pos = None
        try:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        click_pos = event.pos
                    elif event.button == 4:  # Rueda arriba (scroll plantilla)
                        estado['team_scroll_offset'] = max(0, estado['team_scroll_offset'] - 1)
                    elif event.button == 5:  # Rueda abajo (scroll plantilla)
                        total_j = len(mi_equipo.jugadores)
                        n_visible = 8  # 440 de altura visible / 55
                        max_sc = max(0, total_j - n_visible)
                        estado['team_scroll_offset'] = min(max_sc, estado['team_scroll_offset'] + 1)
        except Exception as e_ev:
            logger.error(f"Error procesando eventos en team_screen: {e_ev}")

        # Hover states de los botones de la barra lateral
        hov_jugar = hov_mercado = hov_copa = hov_career = hov_salir = False
        if not modo_prepartido:
            hov_jugar = btn_jugar.collidepoint(mouse_pos)
            hov_mercado = btn_mercado.collidepoint(mouse_pos)
            hov_copa = btn_copa.collidepoint(mouse_pos)
            hov_career = btn_career.collidepoint(mouse_pos)
            hov_salir = btn_salir.collidepoint(mouse_pos)

        # Dibujar botones de la barra lateral (solo en HUB normal; en prepartido va el panel compacto)
        if not modo_prepartido:
            draw_styled_button(screen, btn_jugar, "JUGAR JORNADA", hov_jugar, COLORS.get('verde', (0, 255, 136)))
            draw_styled_button(screen, btn_mercado, "MERCADO DE PASES", hov_mercado, COLORS.get('azul', (0, 191, 255)))
            draw_styled_button(screen, btn_copa, "COPA INTERNACIONAL", hov_copa, COLORS.get('dorado', (255, 215, 0)))
            draw_styled_button(screen, btn_ofertas, "OFERTAS", btn_ofertas.collidepoint(mouse_pos), COLORS.get('verde', (0, 255, 136)))
            draw_styled_button(screen, btn_stats, "ESTADÍSTICAS", btn_stats.collidepoint(mouse_pos), COLORS.get('dorado', (255, 215, 0)))
            draw_styled_button(screen, btn_career, "HISTORIAL CARRERA", hov_career, COLORS.get('azul', (0, 191, 255)))
            draw_styled_button(screen, btn_equipo, "DIRECCIÓN EQUIPO", True, COLORS.get('dorado', (255, 215, 0)))
            draw_styled_button(screen, btn_salir, "GUARDAR Y SALIR", hov_salir, COLORS.get('rojo', (255, 68, 68)))

        # v0.8.6 (Tarea 1): PANEL COMPACTO DE DIRECCIÓN DE EQUIPO (modo prepartido)
        # Reemplaza la barra lateral de carrera con: nombre del club, cicladores
        # (formación + táctica) bien visibles, AUTO ONCE y VOLVER a prepartido.
        if modo_prepartido:
            try:
                # Fondo del panel compacto
                panel_pp = pygame.Rect(20, 20, 260, 680)
                draw_panel(screen, panel_pp)
                try:
                    pygame.draw.rect(screen, COLORS.get('dorado', (255, 215, 0)), pygame.Rect(22, 22, 4, 676))
                    pygame.draw.rect(screen, COLORS.get('verde', (0, 255, 136)), pygame.Rect(26, 22, 4, 676))
                    pygame.draw.rect(screen, COLORS.get('azul', (0, 191, 255)), pygame.Rect(30, 22, 4, 676))
                except Exception:
                    pass

                # Título del panel
                draw_text(screen, "DIRECCIÓN", (45, 45), size='lg', color='dorado')
                draw_text(screen, "DE EQUIPO", (45, 80), size='md', color='blanco')
                pygame.draw.line(screen, COLORS.get('azul', (0, 191, 255)), (40, 120), (260, 120), 1)

                # Nombre del club
                draw_text(screen, mi_equipo.nombre.upper()[:20], (45, 135), size='sm', color='verde')

                # Subtexto de ayuda (los cicladores se dibujan más abajo en el flujo normal)
                draw_text(screen, "Elegí formación y táctica,", (45, 160), size='sm', color='blanco')
                draw_text(screen, "luego VOLVER para volver", (45, 180), size='sm', color='blanco')
                draw_text(screen, "a la pantalla del partido.", (45, 200), size='sm', color='blanco')

                # Etiquetas de los cicladores (los rects ya están definidos arriba)
                # Los cicladores en sí ya se dibujaron con _cycler() usando las posiciones
                # de la izquierda. Acá solo agregamos la nota "Preferida..." debajo.

                # Botón AUTO ONCE (en el panel compacto — equivalente al del fondo pero
                # sin contar como cambio porque es prepartido, no partido)
                btn_auto_pp = pygame.Rect(40, 410, 220, 44)
                hov_auto_pp = btn_auto_pp.collidepoint(mouse_pos)
                draw_styled_button(screen, btn_auto_pp, "AUTO ONCE", hov_auto_pp,
                                    COLORS.get('azul', (0, 191, 255)))

                # Botón VOLVER (regresa a prepartido, sin guardar la alineación)
                btn_volver_pp = pygame.Rect(40, 470, 220, 44)
                hov_volver_pp = btn_volver_pp.collidepoint(mouse_pos)
                draw_styled_button(screen, btn_volver_pp, "VOLVER", hov_volver_pp,
                                    COLORS.get('rojo', (255, 68, 68)))

                # Mini ayuda inferior
                draw_text(screen, "TIP: tocá un jugador en la", (45, 540), size='sm', color='azul')
                draw_text(screen, "lista para alternarlo entre", (45, 560), size='sm', color='azul')
                draw_text(screen, "titulares y suplentes.", (45, 580), size='sm', color='azul')
            except Exception as e_pp:
                logger.error(f"Error dibujando panel compacto prepartido: {e_pp}")

        # --- SECCIONES DE CONTENIDO PRINCIPAL ---
        rect_lista = pygame.Rect(300, 95, 440, 500)
        rect_campo = pygame.Rect(760, 95, 480, 500)

        # DIBUJAR LISTA DE JUGADORES
        draw_panel(screen, rect_lista)
        encabezado_h = 36
        pygame.draw.rect(screen, (15, 22, 40), pygame.Rect(rect_lista.x, rect_lista.y, rect_lista.width, encabezado_h), border_top_left_radius=8, border_top_right_radius=8)
        
        titulares = alin.titulares
        draw_text(screen, f"PLANTILLA — {len(titulares)}/11 TITULARES", (rect_lista.x + 15, rect_lista.y + 8), size='sm', color='dorado')
        
        # Botones de scroll físico para la plantilla
        draw_styled_button(screen, rect_scr_up, "▲", rect_scr_up.collidepoint(_mp), COLORS.get('azul', (0, 191, 255)))
        draw_styled_button(screen, rect_scr_down, "▼", rect_scr_down.collidepoint(_mp), COLORS.get('azul', (0, 191, 255)))

        fila_alto = 55
        visible_h = rect_lista.height - encabezado_h
        n_visible = visible_h // fila_alto
        total_j = len(mi_equipo.jugadores)
        max_sc = max(0, total_j - n_visible)
        
        scroll = estado['team_scroll_offset']
        if scroll > max_sc:
            scroll = max_sc
            estado['team_scroll_offset'] = scroll

        # v0.8.4: ordenar la lista ANTES del hover. Antes se calculaba DESPUÉS del bloque de
        # hover, así que el hover leía una lista vacía (y, peor, antes del fix v0.8.3.4 reventaba
        # con UnboundLocalError). TITULARES primero, luego SUPLENTES por posición
        # (POR -> DEF -> MED -> DEL) y dentro de cada posición por OVR descendente.
        pos_orden = {'POR': 0, 'DEF': 1, 'MED': 2, 'DEL': 3}
        titulares_set = set(alin.titulares)
        jugadores_ordenados = (
            [mi_equipo.jugadores[i] for i in alin.titulares
             if 0 <= i < len(mi_equipo.jugadores)]
            + sorted(
                [j for i, j in enumerate(mi_equipo.jugadores) if i not in titulares_set],
                key=lambda j: (pos_orden.get(getattr(j, 'posicion', ''), 9), -getattr(j, 'overall', 0))
            )
        )
        # Mapear jugador -> índice original en mi_equipo.jugadores (para hover/selección)
        jugador_a_idx = {id(j): i for i, j in enumerate(mi_equipo.jugadores)}

        # Controlar hover sobre las filas de jugadores (usa la lista ordenada ya calculada)
        estado['team_player_hover'] = -1
        if rect_lista.collidepoint(mouse_pos):
            rel_y = mouse_pos[1] - rect_lista.y - encabezado_h
            if rel_y >= 0:
                hover_idx_visual = (rel_y // fila_alto) + scroll
                if 0 <= hover_idx_visual < len(jugadores_ordenados):
                    # Mapear de índice visual a índice original en mi_equipo.jugadores
                    estado['team_player_hover'] = jugador_a_idx.get(
                        id(jugadores_ordenados[hover_idx_visual]), -1)

        # Renderizar cada fila de la plantilla
        old_clip = screen.get_clip()
        clip_rect = pygame.Rect(rect_lista.x, rect_lista.y + encabezado_h, rect_lista.width, visible_h)
        screen.set_clip(clip_rect)

        for i, jugador in enumerate(jugadores_ordenados):
            fi = i - scroll
            if fi < 0 or fi >= n_visible:
                continue

            fy = rect_lista.y + encabezado_h + fi * fila_alto
            fila_rect = pygame.Rect(rect_lista.x + 6, fy + 4, rect_lista.width - 12, fila_alto - 8)
            idx_orig = jugador_a_idx.get(id(jugador), -1)
            es_titular = idx_orig in titulares_set
            es_hover = (idx_orig == estado['team_player_hover'])

            if es_titular:
                bg_col = (30, 65, 45) if not es_hover else (40, 85, 55)
            else:
                bg_col = (20, 26, 46) if not es_hover else (32, 40, 68)

            pygame.draw.rect(screen, bg_col, fila_rect, border_radius=6)
            
            # Línea de estado
            ind_col = COLORS.get('verde', (0, 255, 136)) if es_titular else COLORS.get('rojo', (255, 68, 68))
            pygame.draw.rect(screen, ind_col, pygame.Rect(fila_rect.x, fila_rect.y, 6, fila_rect.height), border_radius=3)

            # Badge de posición
            pos_col = POS_COLOR.get(jugador.posicion, GRIS_CLAR)
            badge_r = pygame.Rect(fila_rect.x + 15, fila_rect.y + 8, 42, 22)
            pygame.draw.rect(screen, pos_col, badge_r, border_radius=4)
            draw_text(screen, jugador.posicion, (badge_r.x + 6, badge_r.y + 3), size='sm', color='blanco', shadow=False)

            # Nombre
            col_name = 'verde' if es_titular else 'blanco'
            nombre_c = _truncar(jugador.nombre_completo, 20)
            draw_text(screen, nombre_c, (fila_rect.x + 70, fy + 8), size='sm', color=col_name)

            # Stats / Rasgos / Lesiones
            det_str = f"OVR: {jugador.overall}"
            if jugador.rasgo:
                det_str += f" | {jugador.rasgo}"
            
            color_det = 'blanco'
            if jugador.lesion_partidos > 0:
                det_str += f" | Lesionado: {jugador.lesion_partidos}p"
                color_det = 'rojo'
            
            draw_text(screen, det_str, (fila_rect.x + 70, fy + 26), size='sm', color=color_det)

        screen.set_clip(old_clip)

        # DIBUJAR CAMPO DE JUEGO (DERECHA)
        pygame.draw.rect(screen, VERDE_CAMPO, rect_campo, border_radius=8)
        franja_h = rect_campo.height // 8
        for i in range(8):
            col = VERDE_CAMPO if i % 2 == 0 else VERDE_CAMPO2
            franja = pygame.Rect(rect_campo.x + 2, rect_campo.y + i * franja_h + 2, rect_campo.width - 4, franja_h - 2)
            pygame.draw.rect(screen, col, franja)
        pygame.draw.rect(screen, BLANCO, rect_campo, width=2, border_radius=8)

        # Líneas de cancha
        centro_y = rect_campo.y + rect_campo.height // 2
        pygame.draw.line(screen, (220, 220, 220), (rect_campo.x + 8, centro_y), (rect_campo.right - 8, centro_y), 1)
        radio_c = min(rect_campo.width, rect_campo.height) // 8
        pygame.draw.circle(screen, (220, 220, 220), rect_campo.center, radio_c, 1)

        # Áreas
        area_w, area_h = rect_campo.width * 0.45, rect_campo.height * 0.15
        area_top = pygame.Rect(rect_campo.centerx - area_w // 2, rect_campo.y + 4, area_w, area_h)
        area_bot = pygame.Rect(rect_campo.centerx - area_w // 2, rect_campo.bottom - area_h - 4, area_w, area_h)
        pygame.draw.rect(screen, (220, 220, 220), area_top, 1)
        pygame.draw.rect(screen, (220, 220, 220), area_bot, 1)

        # Renderizar jugadores sobre la formación 4-3-3
        jugadores_titulares = [mi_equipo.jugadores[idx] for idx in titulares if idx < len(mi_equipo.jugadores)]
        jugadores_titulares_ord = sorted(
            jugadores_titulares,
            key=lambda j: (POS_ORDEN.get(j.posicion, 2), -j.overall)
        )

        radio_circ = 20
        for slot_idx, jugador in enumerate(jugadores_titulares_ord[:11]):
            if slot_idx >= len(posiciones_campo):
                break
            fx, fy_frac = posiciones_campo[slot_idx]
            cx = int(rect_campo.x + rect_campo.width * fx)
            cy = int(rect_campo.y + rect_campo.height * fy_frac)

            # Sombra
            sombra = pygame.Rect(cx - radio_circ + 2, cy - radio_circ + 2, radio_circ*2, radio_circ*2)
            pygame.draw.ellipse(screen, (0, 0, 0, 110), sombra)

            # Círculo del Jugador
            col_circ = POS_COLOR.get(jugador.posicion, GRIS_CLAR)
            pygame.draw.circle(screen, col_circ, (cx, cy), radio_circ)
            pygame.draw.circle(screen, BLANCO, (cx, cy), radio_circ, 2)

            # Abreviación de Posición e Overall
            draw_text(screen, jugador.posicion, (cx - 13, cy - 13), size='sm', color='blanco', shadow=False)
            draw_text(screen, str(jugador.overall), (cx - 10, cy + 1), size='sm', color='blanco', shadow=False)

            # Nombre arriba de la ficha
            ap_trunc = _truncar(jugador.apellido, 9)
            draw_text(screen, ap_trunc, (cx - 24, cy - radio_circ - 18), size='sm', color='dorado')

        # Formación de la esquina
        draw_text(screen, f"FORMACIÓN {alin.formacion}", (rect_campo.right - 150, rect_campo.y + 10), size='sm', color='dorado')

        # --- BOTONES DE ACCIÓN (ABAJO) ---
        btn_auto = pygame.Rect(300, 615, 180, 45)
        btn_confirmar = pygame.Rect(860, 615, 180, 45)
        btn_cancelar = pygame.Rect(1060, 615, 180, 45)

        hov_auto = btn_auto.collidepoint(mouse_pos)
        hov_confirmar = btn_confirmar.collidepoint(mouse_pos)
        hov_cancelar = btn_cancelar.collidepoint(mouse_pos)

        draw_styled_button(screen, btn_auto, "AUTO ONCE", hov_auto, COLORS.get('azul', (0, 191, 255)))
        draw_styled_button(screen, btn_confirmar, "CONFIRMAR", hov_confirmar, COLORS.get('verde', (0, 255, 136)))
        draw_styled_button(screen, btn_cancelar, "CANCELAR", hov_cancelar, COLORS.get('rojo', (255, 68, 68)))

        # --- LÓGICA DE PROCESAMIENTO DE CLICS ---
        if click_pos:
            # 0. Cicladores de formación / táctica (tienen prioridad sobre el resto)
            if rect_f_prev.collidepoint(click_pos) or rect_f_next.collidepoint(click_pos):
                paso = -1 if rect_f_prev.collidepoint(click_pos) else 1
                f_idx = form_lista.index(alin.formacion) if alin.formacion in form_lista else 0
                alin.formacion = form_lista[(f_idx + paso) % len(form_lista)]
                # Al cambiar de formación, re-balancear el once a sus cuotas.
                alin.titulares = F.mejor_once(mi_equipo.jugadores, alin.formacion)
                estado['team_flash_msg'] = f"Formación: {alin.formacion}"
                estado['team_flash_timer'] = 1.5
            elif rect_t_prev.collidepoint(click_pos) or rect_t_next.collidepoint(click_pos):
                paso = -1 if rect_t_prev.collidepoint(click_pos) else 1
                t_idx = tacticas.index(mi_equipo.estilo_dt) if mi_equipo.estilo_dt in tacticas else 0
                mi_equipo.estilo_dt = tacticas[(t_idx + paso) % len(tacticas)]
                estado['team_flash_msg'] = f"Táctica: {mi_equipo.estilo_dt}"
                estado['team_flash_timer'] = 1.5
            elif rect_scr_up.collidepoint(click_pos):
                estado['team_scroll_offset'] = max(0, estado['team_scroll_offset'] - 1)
            elif rect_scr_down.collidepoint(click_pos):
                total_j = len(mi_equipo.jugadores)
                n_visible = 8  # 440 de altura visible / 55
                max_sc = max(0, total_j - n_visible)
                estado['team_scroll_offset'] = min(max_sc, estado['team_scroll_offset'] + 1)

            # 1. Clic en los botones de acción inferior
            elif btn_auto.collidepoint(click_pos):
                try:
                    alin.titulares = F.mejor_once(mi_equipo.jugadores, alin.formacion)
                    estado['team_flash_msg'] = f"Once óptimo para {alin.formacion}"
                    estado['team_flash_timer'] = 2.0
                except Exception as e_auto:
                    logger.error(f"Fallo en autoselección: {e_auto}")

            elif btn_confirmar.collidepoint(click_pos):
                try:
                    if alin.es_valida(mi_equipo.jugadores):
                        estado['team_flash_msg'] = "¡Alineación guardada con éxito!"
                        estado['team_flash_timer'] = 2.0
                        # Guardar la alineación activa (en amistoso queda en amis_local)
                        mi_equipo.alineacion_activa = alin
                        estado.pop('_original_alignment', None)
                        if es_amistoso:
                            estado.pop('team_contexto', None)
                        # v0.8.6 (Tarea 1): limpiar bandera de modo prepartido al salir
                        if modo_prepartido:
                            estado.pop('team_modo_prepartido', None)
                        return ret_screen
                    else:
                        estado['team_flash_msg'] = "Necesitas: 1 POR, 3+ DEF, 2+ MED, 1+ DEL"
                        estado['team_flash_timer'] = 2.5
                except Exception as e_conf:
                    logger.error(f"Error al confirmar alineación: {e_conf}")

            elif btn_cancelar.collidepoint(click_pos):
                try:
                    original = estado.get('_original_alignment', [])
                    alin.titulares = list(original)
                    estado.pop('_original_alignment', None)
                    if es_amistoso:
                        estado.pop('team_contexto', None)
                    # v0.8.6 (Tarea 1): limpiar bandera de modo prepartido al salir
                    if modo_prepartido:
                        estado.pop('team_modo_prepartido', None)
                    return ret_screen
                except Exception as e_canc:
                    logger.error(f"Error al cancelar cambios: {e_canc}")
                    estado.pop('team_contexto', None)
                    if modo_prepartido:
                        estado.pop('team_modo_prepartido', None)
                    return ret_screen

            # 2. Clic en un renglón de la lista de la plantilla
            elif rect_lista.collidepoint(click_pos):
                try:
                    rel_y = click_pos[1] - rect_lista.y - encabezado_h
                    if rel_y >= 0:
                        click_idx = (rel_y // fila_alto) + scroll
                        if 0 <= click_idx < len(mi_equipo.jugadores):
                            jugador = mi_equipo.jugadores[click_idx]
                            if jugador.lesion_partidos > 0:
                                estado['team_flash_msg'] = f"¡{jugador.nombre} está lesionado!"
                                estado['team_flash_timer'] = 2.0
                            else:
                                if click_idx in titulares:
                                    # Permitir desmarcar titulares siempre que quede al menos uno
                                    if len(titulares) > 1:
                                        titulares.remove(click_idx)
                                else:
                                    if len(titulares) < 11:
                                        titulares.append(click_idx)
                                    else:
                                        estado['team_flash_msg'] = "Ya tienes 11 titulares. Quita uno primero."
                                        estado['team_flash_timer'] = 2.0
                except Exception as e_click_row:
                    logger.error(f"Error al alternar jugador en lista: {e_click_row}")

            # 3. Clic en las opciones de la barra de navegación lateral (descartar cambios no guardados)
            # v0.8.6 (Tarea 1): en modo_prepartido estos botones son None; el handler de la
            # barra lateral se procesa SOLO en HUB normal.
            elif not modo_prepartido and btn_jugar is not None and btn_jugar.collidepoint(click_pos):
                estado.pop('_original_alignment', None)
                if es_amistoso:
                    estado.pop('team_contexto', None)
                return ret_screen
            elif not modo_prepartido and btn_mercado is not None and btn_mercado.collidepoint(click_pos):
                estado.pop('_original_alignment', None)
                return "market_screen"
            elif not modo_prepartido and btn_copa is not None and btn_copa.collidepoint(click_pos):
                estado.pop('_original_alignment', None)
                return "copa_screen"
            elif not modo_prepartido and btn_ofertas is not None and btn_ofertas.collidepoint(click_pos):
                estado.pop('_original_alignment', None)
                return "ofertas_screen"
            elif not modo_prepartido and btn_stats is not None and btn_stats.collidepoint(click_pos):
                estado.pop('_original_alignment', None)
                return "stats_screen"
            elif not modo_prepartido and btn_career is not None and btn_career.collidepoint(click_pos):
                estado.pop('_original_alignment', None)
                return "career_screen"
            elif not modo_prepartido and btn_salir is not None and btn_salir.collidepoint(click_pos):
                estado.pop('_original_alignment', None)
                estado['save_slots_return'] = 'team_screen'
                return "save_slots_screen"

            # v0.8.6 (Tarea 1): botones del panel compacto en modo prepartido
            elif modo_prepartido and btn_auto_pp is not None and btn_auto_pp.collidepoint(click_pos):
                try:
                    alin.titulares = F.mejor_once(mi_equipo.jugadores, alin.formacion)
                    estado['team_flash_msg'] = f"Once óptimo para {alin.formacion}"
                    estado['team_flash_timer'] = 2.0
                except Exception as e_auto_pp:
                    logger.error(f"Fallo en autoselección (panel prepartido): {e_auto_pp}")
            elif modo_prepartido and btn_volver_pp is not None and btn_volver_pp.collidepoint(click_pos):
                # VOLVER del panel compacto: vuelve a prepartido descartando cambios
                # (mismo comportamiento que CANCELAR, para coherencia).
                try:
                    original = estado.get('_original_alignment', [])
                    alin.titulares = list(original)
                except Exception:
                    pass
                estado.pop('_original_alignment', None)
                estado.pop('team_modo_prepartido', None)
                estado.pop('team_contexto', None)
                return "prepartido_screen"

        # --- RENDERIZAR NOTIFICACIÓN FLASH ---
        flash_msg = estado.get('team_flash_msg', "")
        if flash_msg and estado.get('team_flash_timer', 0.0) > 0.0:
            try:
                # Dibujar panel de flash centrado
                alpha = min(255, int(estado['team_flash_timer'] * 180))
                font = get_font('md')
                s = font.render(flash_msg, True, AMARILLO)
                x = (SCREEN_W - s.get_width()) // 2
                y = SCREEN_H // 2 - 30
                bg = pygame.Surface((s.get_width() + 24, s.get_height() + 14), pygame.SRCALPHA)
                bg.fill((0, 0, 0, min(200, alpha)))
                screen.blit(bg, (x - 12, y - 7))
                screen.blit(s, (x, y))
            except Exception as e_flash:
                logger.error(f"Error renderizando mensaje flash: {e_flash}")

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
