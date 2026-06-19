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

def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """
    Renderiza la pantalla de Dirección de Equipo en Pygame.
    Retorna la pantalla de destino ('league_screen', 'market_screen', etc.) o None.
    """
    try:
        # Recuperación de datos del estado
        liga = estado.get('liga')
        mi_equipo = estado.get('mi_equipo')
        
        if not liga or not mi_equipo:
            logger.error("Error: No hay liga o equipo en el estado de dirección de equipo.")
            return "menu"

        # Inicialización de alineación activa si no existe
        alin = estado.get('alineacion_activa')
        if not alin:
            from alpha_football.models import alineacion_por_defecto
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
        # Cicladores de formación y táctica (en la cabecera derecha, sobre el campo).
        rect_f_prev = pygame.Rect(770, 28, 30, 30)
        rect_f_box = pygame.Rect(804, 28, 150, 30)
        rect_f_next = pygame.Rect(958, 28, 30, 30)
        rect_t_prev = pygame.Rect(770, 64, 30, 30)
        rect_t_box = pygame.Rect(804, 64, 150, 30)
        rect_t_next = pygame.Rect(958, 64, 30, 30)

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
        draw_text(screen, "DIRECCIÓN TÁCTICA DEL EQUIPO", (300, 20), size='xl', color='dorado')
        draw_text(screen, "Define tu once, formación y táctica.", (300, 66), size='sm', color='azul')

        # --- v0.7: CICLADORES DE FORMACIÓN Y TÁCTICA ---
        _mp = pygame.mouse.get_pos()

        def _cycler(prev_r, box_r, next_r, valor, etiqueta, color_acc):
            draw_styled_button(screen, prev_r, "<", prev_r.collidepoint(_mp), color_acc)
            draw_styled_button(screen, next_r, ">", next_r.collidepoint(_mp), color_acc)
            try:
                pygame.draw.rect(screen, (15, 22, 40), box_r, border_radius=6)
                pygame.draw.rect(screen, color_acc, box_r, width=2, border_radius=6)
            except Exception:
                pass
            vs = get_font('sm').render(str(valor), True, (255, 255, 255))
            screen.blit(vs, vs.get_rect(center=box_r.center))
            draw_text(screen, etiqueta, (box_r.right + 6, box_r.y + 6), size='sm', color='azul')

        _cycler(rect_f_prev, rect_f_box, rect_f_next, alin.formacion, "FORMACIÓN",
                COLORS.get('verde', (0, 255, 136)))
        _fam_pct = int(float((mi_equipo.tactica_familiaridad or {}).get(mi_equipo.estilo_dt, 0.0)) * 100)
        _cycler(rect_t_prev, rect_t_box, rect_t_next, mi_equipo.estilo_dt, "TÁCTICA",
                COLORS.get('dorado', (255, 215, 0)))
        draw_text(screen, f"Preferida de {alin.formacion}: {F.pref(alin.formacion)}  ·  Familiaridad: {_fam_pct}%",
                  (1000, 70), size='sm', color='blanco')

        # --- BOTONES EN EL MENÚ IZQUIERDO ---
        btn_jugar = pygame.Rect(40, 232, 220, 44)
        btn_mercado = pygame.Rect(40, 288, 220, 44)
        btn_copa = pygame.Rect(40, 344, 220, 44)
        btn_ofertas = pygame.Rect(40, 400, 220, 44)
        btn_stats = pygame.Rect(40, 456, 220, 44)
        btn_career = pygame.Rect(40, 512, 220, 44)
        btn_equipo = pygame.Rect(40, 568, 220, 44)
        btn_salir = pygame.Rect(40, 632, 220, 44)

        mouse_pos = pygame.mouse.get_pos()
        click_pos = None

        # Captura de Eventos de entrada
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
        hov_jugar = btn_jugar.collidepoint(mouse_pos)
        hov_mercado = btn_mercado.collidepoint(mouse_pos)
        hov_copa = btn_copa.collidepoint(mouse_pos)
        hov_career = btn_career.collidepoint(mouse_pos)
        hov_salir = btn_salir.collidepoint(mouse_pos)

        # Dibujar botones de la barra lateral
        draw_styled_button(screen, btn_jugar, "JUGAR JORNADA", hov_jugar, COLORS.get('verde', (0, 255, 136)))
        draw_styled_button(screen, btn_mercado, "MERCADO DE PASES", hov_mercado, COLORS.get('azul', (0, 191, 255)))
        draw_styled_button(screen, btn_copa, "COPA INTERNACIONAL", hov_copa, COLORS.get('dorado', (255, 215, 0)))
        draw_styled_button(screen, btn_ofertas, "OFERTAS", btn_ofertas.collidepoint(mouse_pos), COLORS.get('verde', (0, 255, 136)))
        draw_styled_button(screen, btn_stats, "ESTADÍSTICAS", btn_stats.collidepoint(mouse_pos), COLORS.get('dorado', (255, 215, 0)))
        draw_styled_button(screen, btn_career, "HISTORIAL CARRERA", hov_career, COLORS.get('azul', (0, 191, 255)))
        draw_styled_button(screen, btn_equipo, "DIRECCIÓN EQUIPO", True, COLORS.get('dorado', (255, 215, 0)))
        draw_styled_button(screen, btn_salir, "GUARDAR Y SALIR", hov_salir, COLORS.get('rojo', (255, 68, 68)))

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

        # Controlar hover sobre las filas de jugadores
        estado['team_player_hover'] = -1
        if rect_lista.collidepoint(mouse_pos):
            rel_y = mouse_pos[1] - rect_lista.y - encabezado_h
            if rel_y >= 0:
                hover_idx = (rel_y // fila_alto) + scroll
                if 0 <= hover_idx < len(mi_equipo.jugadores):
                    estado['team_player_hover'] = hover_idx

        # Renderizar cada fila de la plantilla
        old_clip = screen.get_clip()
        clip_rect = pygame.Rect(rect_lista.x, rect_lista.y + encabezado_h, rect_lista.width, visible_h)
        screen.set_clip(clip_rect)

        for i, jugador in enumerate(mi_equipo.jugadores):
            fi = i - scroll
            if fi < 0 or fi >= n_visible:
                continue

            fy = rect_lista.y + encabezado_h + fi * fila_alto
            fila_rect = pygame.Rect(rect_lista.x + 6, fy + 4, rect_lista.width - 12, fila_alto - 8)
            es_titular = i in titulares
            es_hover = (i == estado['team_player_hover'])

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
                        # Guardar la alineación activa
                        mi_equipo.alineacion_activa = alin
                        estado.pop('_original_alignment', None)
                        return "league_screen"
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
                    return "league_screen"
                except Exception as e_canc:
                    logger.error(f"Error al cancelar cambios: {e_canc}")
                    return "league_screen"

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
            elif btn_jugar.collidepoint(click_pos):
                estado.pop('_original_alignment', None)
                return "league_screen"
            elif btn_mercado.collidepoint(click_pos):
                estado.pop('_original_alignment', None)
                return "market_screen"
            elif btn_copa.collidepoint(click_pos):
                estado.pop('_original_alignment', None)
                return "copa_screen"
            elif btn_ofertas.collidepoint(click_pos):
                estado.pop('_original_alignment', None)
                return "ofertas_screen"
            elif btn_stats.collidepoint(click_pos):
                estado.pop('_original_alignment', None)
                return "stats_screen"
            elif btn_career.collidepoint(click_pos):
                estado.pop('_original_alignment', None)
                return "career_screen"
            elif btn_salir.collidepoint(click_pos):
                estado.pop('_original_alignment', None)
                estado['save_slots_return'] = 'team_screen'
                return "save_slots_screen"

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
