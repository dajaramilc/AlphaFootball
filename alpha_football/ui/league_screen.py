# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Pantalla de la Liga (Pygame)
Muestra la tabla de clasificación con código de colores (verde = clasificación, rojo = descenso),
el próximo partido del usuario, los demás partidos de la jornada y botones de navegación.
Incorpora barra de navegación lateral a la izquierda, marcas de campo de fútbol y estilos tricolores.
"""

from __future__ import annotations

import sys
import os
import random
import logging
from typing import Any, Optional
import pygame

# Configuración básica del logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
logger = logging.getLogger(__name__)

# Importación resiliente del tema visual con fallback local si falla
try:
    from alpha_football.ui.theme import (
        SCREEN_W,
        SCREEN_H,
        COLORS,
        get_font,
        draw_gradient_bg,
        draw_panel,
        draw_button,
        draw_text
    )
except Exception as e_import:
    logger.warning(f"Advertencia: No se pudo importar alpha_football.ui.theme ({e_import}). Usando fallback local en league_screen.")
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
        try:
            screen.fill((10, 14, 26))
        except Exception:
            pass
            
    def draw_panel(screen, rect):
        try:
            pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=8)
            pygame.draw.rect(screen, (0, 191, 255), rect, width=2, border_radius=8)
        except Exception:
            try:
                pygame.draw.rect(screen, (20, 26, 46), rect)
            except Exception:
                pass
                
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

from alpha_football.models import Partido

# --- Generación de Calendario Round-Robin ═════════════════════════════════════

def generar_fixture(equipos: list[Any]) -> list[list[tuple[Any, Any]]]:
    """Genera un calendario Round-Robin de ida y vuelta de forma resiliente."""
    try:
        n = len(equipos)
        if n % 2 != 0:
            logger.warning("Cantidad de equipos impar al generar fixture. Se requiere número par.")
            return []
        
        lista = list(equipos)
        jornadas = []
        
        for r in range(n - 1):
            jornada = []
            for i in range(n // 2):
                local = lista[i]
                visitante = lista[n - 1 - i]
                if r % 2 == 0:
                    jornada.append((local, visitante))
                else:
                    jornada.append((visitante, local))
            jornadas.append(jornada)
            lista = [lista[0]] + [lista[-1]] + lista[1:-1]
            
        fixture_completo = []
        for j in jornadas:
            fixture_completo.append(j)
        for j in jornadas:
            j_vuelta = [(visitante, local) for (local, visitante) in j]
            fixture_completo.append(j_vuelta)
            
        return fixture_completo
    except Exception as error_fixture:
        logger.error(f"Error al generar fixture: {error_fixture}. Retornando lista vacía como alternativa.")
        return []

def inicializar_calendario_liga(liga: Any) -> None:
    """Rellena el calendario de la liga si está vacío."""
    try:
        if not liga or getattr(liga, "calendario", None):
            return

        fixture = generar_fixture(liga.equipos)
        partidos = []
        for idx_jornada, jornada_partidos in enumerate(fixture, 1):
            for local, visitante in jornada_partidos:
                partidos.append(Partido(
                    local_id=local.id,
                    visitante_id=visitante.id,
                    jornada=idx_jornada,
                    jugado=False
                ))
        liga.calendario = partidos
        logger.info(f"Calendario inicializado para la liga '{liga.nombre}' ({len(partidos)} partidos).")
    except Exception as error_cal:
        logger.error(f"Error al inicializar calendario de liga: {error_cal}")


def simular_jornada_segunda_division(estado: dict) -> None:
    """
    v2.3 (Fase 7): simula la jornada actual de TODAS las 2ª divisiones en background
    al finalizar cada jornada de liga del usuario. Mismo ritmo que 1ª división.
    Si el calendario está vacío (primera vez o tras swap), se inicializa primero.

    NO incluye partidos donde participa el equipo del usuario (si descendió): esos
    los juega el user desde match_screen.
    """
    try:
        segunda = estado.get('segunda_division') or {}
        if not segunda:
            return
        mi_equipo = estado.get('mi_equipo')

        from alpha_football import engine  # import perezoso para evitar ciclos

        for tipo, liga_b in segunda.items():
            try:
                if not liga_b or len(getattr(liga_b, 'equipos', []) or []) < 2:
                    continue
                # Asegurar calendario (idempotente)
                if not getattr(liga_b, 'calendario', None):
                    inicializar_calendario_liga(liga_b)
                jornada_actual = getattr(liga_b, 'jornada_actual', 1) or 1
                # Si la liga de 2ª división ya terminó, no simular más
                num_jornadas = getattr(liga_b, 'num_jornadas', 10) or 10
                if jornada_actual > num_jornadas:
                    continue
                # Filtrar partidos de la jornada actual (no jugados y sin user)
                partidos_j = [p for p in liga_b.calendario if p.jornada == jornada_actual and not p.jugado]
                for p in partidos_j:
                    # Si el user participa, lo salta (lo juega el user en su liga)
                    if mi_equipo and (p.local_id == getattr(mi_equipo, 'id', None)
                                       or p.visitante_id == getattr(mi_equipo, 'id', None)):
                        continue
                    local = next((e for e in liga_b.equipos if e.id == p.local_id), None)
                    visitante = next((e for e in liga_b.equipos if e.id == p.visitante_id), None)
                    if not local or not visitante:
                        continue
                    try:
                        res = engine.simular_partido(local, visitante)
                        p.goles_local = res.goles_local
                        p.goles_visitante = res.goles_visitante
                        p.jugado = True
                        if hasattr(res, 'ganador') and res.ganador:
                            p.ganador_id = local.id if res.ganador == local.nombre else visitante.id
                        else:
                            p.ganador_id = None
                        # Actualizar estadísticas manualmente (engine no exporta helper)
                        local.gf = getattr(local, 'gf', 0) + res.goles_local
                        local.gc = getattr(local, 'gc', 0) + res.goles_visitante
                        visitante.gf = getattr(visitante, 'gf', 0) + res.goles_visitante
                        visitante.gc = getattr(visitante, 'gc', 0) + res.goles_local
                        local.pj = getattr(local, 'pj', 0) + 1
                        visitante.pj = getattr(visitante, 'pj', 0) + 1
                        if res.goles_local > res.goles_visitante:
                            local.puntos = getattr(local, 'puntos', 0) + 3
                            local.pg = getattr(local, 'pg', 0) + 1
                            visitante.pp = getattr(visitante, 'pp', 0) + 1
                        elif res.goles_local < res.goles_visitante:
                            visitante.puntos = getattr(visitante, 'puntos', 0) + 3
                            visitante.pg = getattr(visitante, 'pg', 0) + 1
                            local.pp = getattr(local, 'pp', 0) + 1
                        else:
                            local.puntos = getattr(local, 'puntos', 0) + 1
                            visitante.puntos = getattr(visitante, 'puntos', 0) + 1
                            local.pe = getattr(local, 'pe', 0) + 1
                            visitante.pe = getattr(visitante, 'pe', 0) + 1
                    except Exception as e_match:
                        logger.error(f"Error simulando partido 2ª {tipo} j{jornada_actual}: {e_match}")
                # Avanzar jornada si todos los partidos están jugados
                if all(p.jugado for p in liga_b.calendario if p.jornada == jornada_actual):
                    liga_b.jornada_actual = jornada_actual + 1
                    # Si llegó al final, deja de avanzar
                    if liga_b.jornada_actual > num_jornadas:
                        liga_b.jornada_actual = num_jornadas
                        logger.info(f"2ª división {tipo} terminó la temporada (jornada {num_jornadas})")
            except Exception as e_liga:
                logger.error(f"Error en simulación de 2ª división {tipo}: {e_liga}")
    except Exception as e_gen:
        logger.error(f"Error general en simular_jornada_segunda_division: {e_gen}")


# --- Funciones de Dibujo Auxiliares ═══════════════════════════════════════════

def draw_pitch_lines(screen: pygame.Surface) -> None:
    """
    Dibuja de forma sutil las marcas de un campo de fútbol en el fondo.
    Proporciona un ambiente alegre y deportivo sin interferir con la interfaz.
    """
    try:
        # Color verde azulado muy tenue que resalta suavemente sobre el fondo marino
        pitch_color = (20, 38, 62)
        
        # Círculo central en la zona derecha de la pantalla
        pygame.draw.circle(screen, pitch_color, (750, 360), 120, 2)
        pygame.draw.circle(screen, pitch_color, (750, 360), 6)
        
        # Línea divisoria central
        pygame.draw.line(screen, pitch_color, (750, 20), (750, 700), 2)
        
        # Áreas grandes de juego (izquierda y derecha)
        pygame.draw.rect(screen, pitch_color, pygame.Rect(260, 110, 160, 500), 2)
        pygame.draw.rect(screen, pitch_color, pygame.Rect(1080, 110, 160, 500), 2)
        
    except Exception as error_pitch:
        logger.error(f"Error al dibujar líneas de campo: {error_pitch}. Continuando con ejecución normal.")

def draw_styled_button(screen: pygame.Surface, rect: pygame.Rect, text: str, hover: bool, accent_color: tuple[int, int, int], enabled: bool = True) -> pygame.Rect:
    """
    Dibuja un botón interactivo y premium de acuerdo con la nueva identidad de colores.
    Soporta botones deshabilitados/bloqueados y colores de acento dinámicos.
    """
    try:
        button_rect = pygame.Rect(rect)
        if not enabled:
            # Color apagado para botones deshabilitados/bloqueados
            bg_color = (25, 25, 35)
            border_color = (75, 75, 85)
            text_color = (110, 110, 120)
        elif hover:
            # Estilo hover activo con el color de acento del botón
            bg_color = (30, 45, 75)
            border_color = accent_color
            text_color = accent_color
        else:
            # Estilo pasivo por defecto
            bg_color = COLORS.get('panel', (20, 26, 46))
            border_color = COLORS.get('azul', (0, 191, 255))
            text_color = COLORS.get('blanco', (255, 255, 255))
            
        # Dibujar fondo y borde con esquinas redondeadas si es posible
        try:
            pygame.draw.rect(screen, bg_color, button_rect, border_radius=8)
            pygame.draw.rect(screen, border_color, button_rect, width=2, border_radius=8)
        except TypeError:
            pygame.draw.rect(screen, bg_color, button_rect)
            pygame.draw.rect(screen, border_color, button_rect, width=2)
            
        # Dibujar texto centrado en el botón
        try:
            font = get_font('md')
            text_surf = font.render(text, True, text_color)
            text_rect = text_surf.get_rect(center=button_rect.center)
            screen.blit(text_surf, text_rect)
        except Exception as error_texto:
            logger.error(f"Error renderizando texto de botón '{text}': {error_texto}")
            
        return button_rect
    except Exception as error_btn:
        logger.error(f"Error general en draw_styled_button: {error_btn}. Utilizando dibujo plano de emergencia.")
        try:
            pygame.draw.rect(screen, (50, 50, 50), rect)
        except Exception:
            pass
        return rect

# --- Renderizador de la Pantalla Principal ════════════════════════════════════

def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """
    Renderiza la pantalla de la Liga en Pygame con un menú lateral izquierdo.
    Retorna la acción de pantalla ("match_screen", "market_screen", "copa_screen", "career_screen", "menu")
    o None para continuar en esta pantalla.
    """
    try:
        # Recuperar datos esenciales del estado de forma segura
        liga = estado.get('liga')
        mi_equipo = estado.get('mi_equipo')

        # En caso de que no existan los datos clave, asignamos valores por defecto o salimos de forma segura
        if not liga or not mi_equipo:
            logger.error("Error resiliente: No hay liga o equipo cargado en el estado de liga.")
            return "menu"

        # v2.3 (Fase 11): decidir qué división mostrar. Por defecto la del usuario;
        # si `liga_view == 2`, mostrar la 2ª división del mismo país (si existe).
        liga_view = int(estado.get('liga_view', estado.get('liga_usuario_division', 1)) or 1)
        segunda = estado.get('segunda_division') or {}
        liga_tipo = getattr(liga, 'tipo', '')
        liga_vista = liga  # Por defecto, la del user
        if liga_view == 2 and liga_tipo in segunda and segunda[liga_tipo] is not None:
            liga_vista = segunda[liga_tipo]
            # Inicializar calendario de la 2ª división si está vacío
            try:
                if not getattr(liga_vista, 'calendario', None):
                    inicializar_calendario_liga(liga_vista)
            except Exception:
                pass

        # v2.3.1 (FIX BUG CRITICO): mouse_pos y click_pos se capturan AQUI para
        # que esten disponibles antes de cualquier uso (toggle 1a/2a, banner de
        # alerta de copa, etc). Antes se capturaban en linea 657 y el bloque del
        # toggle (linea 431) reventaba con UnboundLocalError.
        mouse_pos = pygame.mouse.get_pos()
        click_pos = None
        key_events = []

        # Aseguramos que la liga tenga su fixture inicializado de manera de no colgar la partida
        try:
            inicializar_calendario_liga(liga_vista)
        except Exception as error_fixtures:
            logger.error(f"Error al inicializar fixtures de liga: {str(error_fixtures)}. Intentando continuar.")
        
        # 1. Obtener la jornada actual y partidos
        mouse_pos = pygame.mouse.get_pos()
        # Panel de historial más grande para mostrar más partidos con scroll
        hist_rect = pygame.Rect(300, 510, 560, 175)
        rect_hist_up = pygame.Rect(300 + 560 - 80, 510 + 4, 32, 28)
        rect_hist_down = pygame.Rect(300 + 560 - 42, 510 + 4, 32, 28)
        
        jornada_actual = getattr(liga_vista, "jornada_actual", 1)
        partidos_jornada = [p for p in getattr(liga_vista, "calendario", []) if p.jornada == jornada_actual]

        # v2.3.3 (FIX): el partido del usuario depende de la division que estamos VIENDO.
        # - Si veo 1ª -> busco en liga.calendario (la del user en 1ª)
        # - Si veo 2ª -> busco en liga_vista.calendario (la del user en 2ª)
        # Antes siempre buscaba en liga.calendario, por eso veia "Sin rival programado"
        # cuando el user estaba en 2ª división y miraba el calendario de la 2ª.
        partido_usuario = None
        if liga_view == 2:
            for p in getattr(liga_vista, 'calendario', []):
                if p.jornada == jornada_actual and (
                    p.local_id == mi_equipo.id or p.visitante_id == mi_equipo.id
                ):
                    partido_usuario = p
                    break
        if partido_usuario is None:
            for p in getattr(liga, 'calendario', []):
                if p.jornada == getattr(liga, 'jornada_actual', 1) and (
                    p.local_id == mi_equipo.id or p.visitante_id == mi_equipo.id
                ):
                    partido_usuario = p
                    break
                
        # 2. Dibujar fondo general y marcas de campo
        try:
            draw_gradient_bg(screen)
            draw_pitch_lines(screen)
        except Exception as e_bg:
            logger.error(f"Error al dibujar fondo: {str(e_bg)}. Rellenando con color plano.")
            screen.fill(COLORS.get('bg', (10, 14, 26)))
            
        # --- DECORACIÓN VISUAL RGB DE FÚTBOL ALEGRE ---
        # Dibujamos líneas de colores rojo, verde y azul en los bordes de la pantalla para el tema RGB
        try:
            pygame.draw.rect(screen, COLORS.get('rojo', (255, 68, 68)), pygame.Rect(0, 0, SCREEN_W, 4))
            pygame.draw.rect(screen, COLORS.get('verde', (0, 255, 136)), pygame.Rect(0, 4, SCREEN_W, 4))
            pygame.draw.rect(screen, COLORS.get('azul', (0, 191, 255)), pygame.Rect(0, 8, SCREEN_W, 4))
        except Exception as e_deco:
            logger.warning(f"No se pudieron dibujar las franjas decorativas: {str(e_deco)}")
            
        # --- PANEL LATERAL IZQUIERDO (MENÚ A LA IZQUIERDA) ---
        menu_rect = pygame.Rect(20, 20, 260, 680)
        try:
            draw_panel(screen, menu_rect)
            # Decoración vertical RGB dentro del panel izquierdo
            pygame.draw.rect(screen, COLORS.get('rojo', (255, 68, 68)), pygame.Rect(22, 22, 4, 676))
            pygame.draw.rect(screen, COLORS.get('verde', (0, 255, 136)), pygame.Rect(26, 22, 4, 676))
            pygame.draw.rect(screen, COLORS.get('azul', (0, 191, 255)), pygame.Rect(30, 22, 4, 676))
        except Exception as e_menu_panel:
            logger.error(f"Error al dibujar panel de menú: {str(e_menu_panel)}")
            
        # Logo de Fútbol Alegre (Temática tricolor) y Datos del club
        try:
            draw_text(screen, "★ ALPHA ★", (45, 45), size='lg', color='verde')
            draw_text(screen, "FOOTBALL", (45, 80), size='md', color='blanco')
            pygame.draw.line(screen, COLORS.get('azul', (0, 191, 255)), (40, 120), (260, 120), 1)
            
            # Datos del club
            draw_text(screen, mi_equipo.nombre.upper()[:18], (45, 135), size='sm', color='verde')
            pres_m = getattr(mi_equipo, 'balance', 0) / 1_000_000
            draw_text(screen, f"Presupuesto: ${pres_m:.1f}M", (45, 160), size='sm', color='blanco')
            draw_text(screen, f"Temporada: {estado.get('temporada', 1)}", (45, 185), size='sm', color='azul')
            draw_text(screen, f"Jornada: {jornada_actual}/{getattr(liga, 'num_jornadas', 14)}", (45, 210), size='sm', color='dorado')
        except Exception as e_logo:
            logger.error(f"Error al dibujar textos de logo/datos: {str(e_logo)}")
            
        # --- ENCABEZADOS DEL CONTENIDO PRINCIPAL (DERECHA) ---
        try:
            draw_text(screen, f"{liga.nombre.upper()}", (300, 20), size='xl', color='dorado')
            draw_text(screen, f"Temporada {estado.get('temporada', 1)}  |  Jornada {jornada_actual} de {getattr(liga, 'num_jornadas', 14)}", (300, 65), size='sm', color='azul')
        except Exception as e_header:
            logger.error(f"Error al dibujar cabecera principal: {str(e_header)}")

        # v2.3 (Fase 11): toggle 1ª⇄2ª División en la cabecera.
        # Por defecto muestra la división del usuario; click cambia.
        segunda = estado.get('segunda_division') or {}
        liga_tipo = getattr(liga, 'tipo', '')
        liga_view = estado.get('liga_view', estado.get('liga_usuario_division', 1))
        if liga_tipo in segunda and segunda[liga_tipo] is not None:
            toggle_rect = pygame.Rect(SCREEN_W - 240, 22, 220, 44)
            toggle_hover = toggle_rect.collidepoint(mouse_pos)
            label_toggle = f"VER {'2ª' if liga_view == 1 else '1ª'} DIVISIÓN"
            draw_styled_button(screen, toggle_rect, label_toggle, toggle_hover,
                                 COLORS.get('dorado', (255, 215, 0)))
            if click_pos and toggle_rect.collidepoint(click_pos):
                # Alternar vista entre 1ª (estado['liga']) y 2ª (segunda_division[tipo])
                if liga_view == 1:
                    estado['liga_view'] = 2
                    # No cambiamos estado['liga'] (la del user); solo un flag.
                    # La pantalla lee liga_view para mostrar la tabla/calendario.
                else:
                    estado['liga_view'] = 1
        # v2.3.3: Tecla V = toggle 1ª/2ª division (atajo de teclado).
        try:
            for ev in key_events:
                if ev.key == pygame.K_v:
                    if liga_view == 1:
                        estado['liga_view'] = 2
                    else:
                        estado['liga_view'] = 1
        except Exception:
            pass
            
        # --- AVISO Y BLOQUEO DE JUEGOS INTERNACIONALES PENDIENTES ---
        tiene_copa_pendiente = False
        fase_nombre_pend = None
        try:
            from alpha_football.ui.copa_screen import obtener_partido_copa_pendiente
            fase_nombre_pend, _ = obtener_partido_copa_pendiente(estado)
            tiene_copa_pendiente = (fase_nombre_pend is not None)
        except Exception as error_copas:
            logger.error(f"Error al verificar advertencia de copa: {str(error_copas)}")
            tiene_copa_pendiente = False
            
        # Banner de advertencia de Copa parpadeante
        if tiene_copa_pendiente and fase_nombre_pend:
            try:
                alert_rect = pygame.Rect(820, 20, 420, 65)
                # Fondo rojo oscuro con borde parpadeante
                pulso = (pygame.time.get_ticks() // 500) % 2
                color_borde = COLORS.get('rojo', (255, 68, 68)) if pulso == 0 else COLORS.get('dorado', (255, 215, 0))
                pygame.draw.rect(screen, (35, 15, 15), alert_rect, border_radius=6)
                pygame.draw.rect(screen, color_borde, alert_rect, width=2, border_radius=6)
                draw_text(screen, "⚠️ ¡FECHA INTERNACIONAL DETECTADA!", (835, 25), size='sm', color='rojo')
                draw_text(screen, f"Copa pendiente: {fase_nombre_pend}. Juega Copa primero.", (835, 48), size='sm', color='blanco')
            except Exception as e_alert:
                logger.error(f"Error al renderizar banner de alerta: {str(e_alert)}")
                
        # --- PANEL IZQUIERDO DE CONTENIDO: CLASIFICACIÓN ---
        # Tabla de posiciones: ligeramente más pequeña para dar espacio al historial
        left_rect = pygame.Rect(300, 100, 560, 395)
        try:
            draw_panel(screen, left_rect)
            draw_text(screen, "TABLA DE POSICIONES ⚽", (320, 115), size='md', color='azul')
        except Exception as e_left_panel:
            logger.error(f"Error al dibujar panel izquierdo: {str(e_left_panel)}")
            
        # Ordenación y dibujo de la Tabla de Posiciones
        try:
            equipos_ordenados = []
            try:
                def clave_tabla(eq):
                    try:
                        dg = getattr(eq, 'gf', 0) - getattr(eq, 'gc', 0)
                        return (getattr(eq, 'puntos', 0), dg, getattr(eq, 'gf', 0))
                    except Exception as e_eq:
                        logger.error(f"Error al obtener atributos de equipo en ordenación: {e_eq}")
                        return (0, 0, 0)
                equipos_ordenados = sorted(liga_vista.equipos, key=clave_tabla, reverse=True)
            except Exception as e_sort:
                logger.error(f"Error al ordenar la tabla de posiciones: {e_sort}. Usando orden original de equipos como alternativa.")
                equipos_ordenados = getattr(liga, "equipos", [])
            
            # Encabezados de tabla
            headers = ["#", "Equipo", "PJ", "PG", "PE", "PP", "GF", "GC", "DG", "PTS"]
            header_x = [320, 355, 545, 585, 625, 665, 705, 745, 785, 825]
            for h, x_pos in zip(headers, header_x):
                draw_text(screen, h, (x_pos, 150), size='sm', color='dorado')
                
            pygame.draw.line(screen, COLORS.get('azul', (0, 191, 255)), (320, 170), (840, 170), 1)
            
            # Render de las filas
            start_y = 185
            row_height = 37
            # v2.3.3 (FIX): colores segun la division que se esta VIENDO.
            #  - 1ª division: top 3 verde (clasifican a Champions/Libertadores),
            #                 bottom 2 rojo (descienden a 2ª).
            #  - 2ª division: top 2 verde (ascienden a 1ª), sin descensos (no hay 3ª).
            n_total = len(equipos_ordenados)
            es_segunda = (liga_view == 2)
            for idx, eq in enumerate(equipos_ordenados, 1):
                y_pos = start_y + (idx - 1) * row_height

                # Colores segun division.
                if es_segunda:
                    # 2ª: top 2 sube, resto blanco (sin descensos).
                    if idx <= 2:
                        row_color = 'verde'
                    else:
                        row_color = 'blanco'
                else:
                    # 1ª: top 3 verde (clasifica a copa), bottom 2 rojo (desciende).
                    if idx <= 3:
                        row_color = 'verde'
                    elif idx >= n_total - 1:
                        row_color = 'rojo'
                    else:
                        row_color = 'blanco'
                    
                # Si es el equipo del usuario, dibujamos un fondo destacado
                if eq.id == mi_equipo.id:
                    sub_rect = pygame.Rect(310, y_pos - 4, 540, 30)
                    try:
                        pygame.draw.rect(screen, (30, 45, 75), sub_rect, border_radius=4)
                        pygame.draw.rect(screen, COLORS.get('verde', (0, 255, 136)), sub_rect, width=1, border_radius=4)
                    except TypeError:
                        pygame.draw.rect(screen, (30, 45, 75), sub_rect)
                        pygame.draw.rect(screen, COLORS.get('verde', (0, 255, 136)), sub_rect, width=1)
                    
                draw_text(screen, str(idx), (320, y_pos), size='sm', color=row_color)
                nombre_truncado = eq.nombre[:20]
                draw_text(screen, nombre_truncado, (355, y_pos), size='sm', color=row_color)
                draw_text(screen, str(eq.pj), (545, y_pos), size='sm', color=row_color)
                draw_text(screen, str(eq.pg), (585, y_pos), size='sm', color=row_color)
                draw_text(screen, str(eq.pe), (625, y_pos), size='sm', color=row_color)
                draw_text(screen, str(eq.pp), (665, y_pos), size='sm', color=row_color)
                draw_text(screen, str(eq.gf), (705, y_pos), size='sm', color=row_color)
                draw_text(screen, str(eq.gc), (745, y_pos), size='sm', color=row_color)
                
                dg = eq.gf - eq.gc
                dg_str = f"+{dg}" if dg > 0 else str(dg)
                draw_text(screen, dg_str, (785, y_pos), size='sm', color=row_color)
                draw_text(screen, str(eq.puntos), (825, y_pos), size='sm', color=row_color)

        except Exception as e_table:
            logger.error(f"Error crítico al renderizar la tabla de posiciones: {str(e_table)}")
            draw_text(screen, "Error al cargar clasificación. Intente reiniciar.", (320, 200), size='md', color='rojo')

        # --- HISTORIAL DE PARTIDOS (debajo de la tabla, más grande para ver hasta 6 partidos) ---
        try:
            # Panel expandido para mostrar más partidos con scroll
            draw_panel(screen, hist_rect)
            jugados = [p for p in getattr(liga, 'calendario', [])
                       if p.jugado and (p.local_id == mi_equipo.id or p.visitante_id == mi_equipo.id)]
            jugados.sort(key=lambda p: p.jornada, reverse=True)
            total_jugados = len(jugados)
            
            # Título con contador de partidos
            titulo_hist = f"HISTORIAL DE PARTIDOS ⚽ ({total_jugados} jugados)"
            draw_text(screen, titulo_hist, (320, hist_rect.y + 8), size='sm', color='dorado')
            
            # Paginación: mostrar hasta 6 partidos a la vez
            PARTIDOS_VISIBLES = 6
            offset = estado.setdefault('hist_scroll_offset', 0)
            max_offset = max(0, total_jugados - PARTIDOS_VISIBLES)
            if offset > max_offset:
                offset = max_offset
                estado['hist_scroll_offset'] = offset
            
            # Botones de scroll visibles y funcionales
            draw_styled_button(screen, rect_hist_up, "▲", rect_hist_up.collidepoint(mouse_pos), COLORS.get('azul', (0, 191, 255)))
            draw_styled_button(screen, rect_hist_down, "▼", rect_hist_down.collidepoint(mouse_pos), COLORS.get('azul', (0, 191, 255)))

            hy = hist_rect.y + 34
            if not jugados:
                draw_text(screen, "Aún no has jugado partidos esta temporada.", (320, hy), size='sm', color='blanco')
            else:
                # Indicador de página si hay más de los visibles
                if total_jugados > PARTIDOS_VISIBLES:
                    pag_texto = f"[{offset + 1}-{min(offset + PARTIDOS_VISIBLES, total_jugados)} de {total_jugados}]"
                    draw_text(screen, pag_texto, (hist_rect.right - 140, hist_rect.y + 8), size='sm', color='azul')
                    
                for p in jugados[offset:offset + PARTIDOS_VISIBLES]:
                    loc = next((e for e in liga.equipos if e.id == p.local_id), None)
                    vis = next((e for e in liga.equipos if e.id == p.visitante_id), None)
                    ln = f"{(getattr(loc, 'corto', None) or '?')} {p.goles_local}-{p.goles_visitante} {(getattr(vis, 'corto', None) or '?')}"
                    col = 'blanco'
                    if loc and vis:
                        user_is_local = (p.local_id == mi_equipo.id)
                        ug = p.goles_local if user_is_local else p.goles_visitante
                        rg = p.goles_visitante if user_is_local else p.goles_local
                        col = 'verde' if ug > rg else ('rojo' if ug < rg else 'azul')
                    draw_text(screen, f"J{p.jornada}:  {ln}", (320, hy), size='sm', color=col)
                    hy += 23
        except Exception as e_hist:
            logger.error(f"Error al renderizar historial de partidos: {str(e_hist)}")

        # --- PANEL DERECHO DE CONTENIDO: ENCUENTROS ---
        right_rect = pygame.Rect(880, 100, 360, 580)
        try:
            draw_panel(screen, right_rect)
            draw_text(screen, "PRÓXIMO ENCUENTRO ⚔️", (900, 115), size='md', color='dorado')
        except Exception as e_right_panel:
            logger.error(f"Error al dibujar panel derecho: {str(e_right_panel)}")
            
        # A. Próximo Rival
        try:
            if partido_usuario:
                oponente_id = partido_usuario.visitante_id if partido_usuario.local_id == mi_equipo.id else partido_usuario.local_id
                # v2.3.3: el oponente se busca en la division que se esta VIENDO.
                # Si veo 2ª, los equipos son los de la 2ª.
                equipos_a_buscar = liga_vista.equipos if liga_view == 2 else liga.equipos
                oponente = next((e for e in equipos_a_buscar if e.id == oponente_id), None)
                
                if oponente:
                    draw_text(screen, mi_equipo.nombre[:22], (900, 155), size='md', color='verde')
                    draw_text(screen, "vs", (900, 185), size='sm', color='blanco')
                    draw_text(screen, oponente.nombre[:22], (900, 210), size='md', color='rojo')
                    
                    # Detalles del rival
                    estilo_op = getattr(oponente, 'estilo_dt', 'desconocido').upper()
                    draw_text(screen, f"DT: {estilo_op}  |  OVR: {getattr(oponente, 'ovr_promedio', 70)}", (900, 250), size='sm', color='azul')
                    pres_op = getattr(oponente, 'balance', 0) / 1_000_000
                    draw_text(screen, f"Presupuesto: ${pres_op:.1f}M", (900, 275), size='sm', color='blanco')
            else:
                draw_text(screen, "Sin rival programado", (900, 155), size='md', color='rojo')
        except Exception as e_rival:
            logger.error(f"Error al procesar próximo rival: {str(e_rival)}")
            draw_text(screen, "Error al cargar rival", (900, 155), size='md', color='rojo')
            
        # B. Otros partidos de la fecha
        try:
            pygame.draw.line(screen, COLORS.get('azul', (0, 191, 255)), (900, 310), (1220, 310), 1)
            draw_text(screen, "OTROS PARTIDOS DE LA FECHA", (900, 325), size='sm', color='dorado')
            
            oy = 360
            # v2.3.3: los "otros partidos" son los de la division vista, no siempre liga.
            equipos_a_buscar_otros = liga_vista.equipos if liga_view == 2 else liga.equipos
            for p in partidos_jornada:
                if p == partido_usuario:
                    continue
                loc = next((e for e in equipos_a_buscar_otros if e.id == p.local_id), None)
                vis = next((e for e in equipos_a_buscar_otros if e.id == p.visitante_id), None)
                
                loc_name = loc.nombre[:14] if loc else f"Eq.{p.local_id}"
                vis_name = vis.nombre[:14] if vis else f"Eq.{p.visitante_id}"
                
                if p.jugado:
                    res_str = f"{p.goles_local} - {p.goles_visitante}"
                else:
                    res_str = "vs"
                    
                draw_text(screen, f"{loc_name} {res_str} {vis_name}", (900, oy), size='sm', color='blanco')
                oy += 28
        except Exception as e_other_matches:
            logger.error(f"Error al renderizar otros partidos: {str(e_other_matches)}")
            
        # --- BOTONES EN EL MENÚ IZQUIERDO ---
        btn_jugar = pygame.Rect(40, 232, 220, 44)
        btn_mercado = pygame.Rect(40, 288, 220, 44)
        btn_copa = pygame.Rect(40, 344, 220, 44)
        btn_ofertas = pygame.Rect(40, 400, 220, 44)
        btn_stats = pygame.Rect(40, 456, 220, 44)
        btn_career = pygame.Rect(40, 512, 220, 44)
        btn_equipo = pygame.Rect(40, 568, 220, 44)
        btn_salir = pygame.Rect(40, 632, 220, 44)

        # v2.3.3: lista ordenada de botones del sidebar para navegacion por teclado.
        # ↑↓ mueve el foco, Enter dispara el handler del boton, Esc vuelve al menu.
        sidebar_buttons = [
            (btn_jugar, 'jugar'),
            (btn_mercado, 'mercado'),
            (btn_copa, 'copa'),
            (btn_ofertas, 'ofertas'),
            (btn_stats, 'stats'),
            (btn_career, 'career'),
            (btn_equipo, 'equipo'),
            (btn_salir, 'salir'),
        ]
        if 'league_kbd_focus' not in estado:
            estado['league_kbd_focus'] = 0

        mouse_pos = pygame.mouse.get_pos()  # refresh por si el tamano cambio
        # click_pos ya esta declarado arriba; refrescar con el evento actual.
        # Eventos
        try:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "menu"
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        click_pos = event.pos
                    elif event.button == 4:  # Rueda arriba
                        if hist_rect.collidepoint(mouse_pos):
                            estado['hist_scroll_offset'] = max(0, estado.get('hist_scroll_offset', 0) - 1)
                    elif event.button == 5:  # Rueda abajo
                        if hist_rect.collidepoint(mouse_pos):
                            jugados_wh = [p for p in getattr(liga, 'calendario', [])
                                       if p.jugado and (p.local_id == mi_equipo.id or p.visitante_id == mi_equipo.id)]
                            max_offset = max(0, len(jugados_wh) - 6)
                            estado['hist_scroll_offset'] = min(max_offset, estado.get('hist_scroll_offset', 0) + 1)
                elif event.type == pygame.KEYDOWN:
                    key_events.append(event)
        except Exception as e_events:
            logger.error(f"Error al procesar eventos en league_screen: {str(e_events)}")

        # v2.3.3: Navegacion por teclado del sidebar. ↑↓ mueve el foco entre
        # los 8 botones, Enter simula click en el boton enfocado.
        try:
            for ev in key_events:
                if ev.key == pygame.K_UP:
                    estado['league_kbd_focus'] = (int(estado.get('league_kbd_focus', 0)) - 1) % len(sidebar_buttons)
                elif ev.key == pygame.K_DOWN:
                    estado['league_kbd_focus'] = (int(estado.get('league_kbd_focus', 0)) + 1) % len(sidebar_buttons)
                elif ev.key == pygame.K_RETURN or ev.key == pygame.K_SPACE:
                    # Forzar click sintetico en el boton enfocado.
                    idx = int(estado.get('league_kbd_focus', 0))
                    if 0 <= idx < len(sidebar_buttons):
                        rect, _name = sidebar_buttons[idx]
                        click_pos = (rect.x + rect.width // 2, rect.y + rect.height // 2)
                elif ev.key == pygame.K_j:
                    click_pos = (btn_jugar.x + btn_jugar.width // 2, btn_jugar.y + btn_jugar.height // 2)
                    estado['league_kbd_focus'] = 0
                elif ev.key == pygame.K_m:
                    click_pos = (btn_mercado.x + btn_mercado.width // 2, btn_mercado.y + btn_mercado.height // 2)
                    estado['league_kbd_focus'] = 1
                elif ev.key == pygame.K_c:
                    # No pisar si hay Copa pendiente visible (texto)
                    if not tiene_copa_pendiente:
                        click_pos = (btn_copa.x + btn_copa.width // 2, btn_copa.y + btn_copa.height // 2)
                        estado['league_kbd_focus'] = 2
                elif ev.key == pygame.K_o:
                    click_pos = (btn_ofertas.x + btn_ofertas.width // 2, btn_ofertas.y + btn_ofertas.height // 2)
                    estado['league_kbd_focus'] = 3
                elif ev.key == pygame.K_s:
                    # 's' se reserva para Salir (last). Stats va con 't' (stats)
                    click_pos = (btn_stats.x + btn_stats.width // 2, btn_stats.y + btn_stats.height // 2)
                    estado['league_kbd_focus'] = 4
                elif ev.key == pygame.K_h:
                    click_pos = (btn_career.x + btn_career.width // 2, btn_career.y + btn_career.height // 2)
                    estado['league_kbd_focus'] = 5
                elif ev.key == pygame.K_e:
                    click_pos = (btn_equipo.x + btn_equipo.width // 2, btn_equipo.y + btn_equipo.height // 2)
                    estado['league_kbd_focus'] = 6
                elif ev.key == pygame.K_ESCAPE:
                    estado['current_screen'] = 'menu'
                    return 'menu'
        except Exception as e_kbd:
            logger.error(f"Error en navegacion por teclado de league_screen: {e_kbd}")
            
        # Hover states (Si está bloqueado por copa, JUGAR JORNADA no tiene hover activo)
        hov_jugar = btn_jugar.collidepoint(mouse_pos) and not tiene_copa_pendiente
        hov_mercado = btn_mercado.collidepoint(mouse_pos)
        hov_copa = btn_copa.collidepoint(mouse_pos)
        hov_career = btn_career.collidepoint(mouse_pos)
        hov_equipo = btn_equipo.collidepoint(mouse_pos)
        hov_salir = btn_salir.collidepoint(mouse_pos)
        
        jornada_maxima = getattr(liga, "num_jornadas", 10)
        esta_finalizada = (jornada_actual == jornada_maxima and all(p.jugado for p in getattr(liga, "calendario", []) if p.jornada == jornada_actual))

        # Dibujar botones
        # A. Jugar Jornada (puede estar bloqueado o finalizado)
        if tiene_copa_pendiente:
            try:
                pygame.draw.rect(screen, (40, 20, 20), btn_jugar, border_radius=8)
                pygame.draw.rect(screen, COLORS.get('rojo', (255, 68, 68)), btn_jugar, width=2, border_radius=8)
            except TypeError:
                pygame.draw.rect(screen, (40, 20, 20), btn_jugar)
                pygame.draw.rect(screen, COLORS.get('rojo', (255, 68, 68)), btn_jugar, width=2)
            font = get_font('md')
            txt_surf = font.render("JUGAR JORNADA 🔒", True, (150, 150, 150))
            txt_rect = txt_surf.get_rect(center=btn_jugar.center)
            screen.blit(txt_surf, txt_rect)
        elif esta_finalizada:
            draw_styled_button(screen, btn_jugar, "AVANZAR TEMP", hov_jugar, COLORS.get('verde', (0, 255, 136)))
        else:
            draw_styled_button(screen, btn_jugar, "JUGAR JORNADA", hov_jugar, COLORS.get('verde', (0, 255, 136)))
            
        draw_styled_button(screen, btn_mercado, "MERCADO DE PASES", hov_mercado, COLORS.get('azul', (0, 191, 255)))
        draw_styled_button(screen, btn_copa, "COPA INTERNACIONAL", hov_copa, COLORS.get('dorado', (255, 215, 0)))
        draw_styled_button(screen, btn_ofertas, "OFERTAS", btn_ofertas.collidepoint(mouse_pos), COLORS.get('verde', (0, 255, 136)))
        draw_styled_button(screen, btn_stats, "ESTADÍSTICAS", btn_stats.collidepoint(mouse_pos), COLORS.get('dorado', (255, 215, 0)))
        draw_styled_button(screen, btn_career, "HISTORIAL CARRERA", hov_career, COLORS.get('azul', (0, 191, 255)))
        draw_styled_button(screen, btn_equipo, "DIRECCIÓN EQUIPO", hov_equipo, COLORS.get('azul', (0, 191, 255)))
        draw_styled_button(screen, btn_salir, "GUARDAR Y SALIR", hov_salir, COLORS.get('rojo', (255, 68, 68)))

        # v2.3.3: indicador de foco por teclado (borde dorado brillante + flecha ▶)
        # Se dibuja sobre el boton enfocado, igual de visible que el hover del mouse.
        try:
            kbd_idx = int(estado.get('league_kbd_focus', 0))
            if 0 <= kbd_idx < len(sidebar_buttons):
                kbd_rect, _kbd_name = sidebar_buttons[kbd_idx]
                # Borde dorado brillante (3px) sobre el boton enfocado
                pygame.draw.rect(screen, COLORS.get('dorado', (255, 215, 0)), kbd_rect, width=3, border_radius=8)
                # Indicador "▶" a la izquierda del boton
                draw_text(screen, "▶", (kbd_rect.x - 22, kbd_rect.y + 14), size='lg', color='dorado')
        except Exception:
            pass

        # Badge con el número de ofertas pendientes
        _n_of = len(estado.get('ofertas_recibidas', []) or [])
        if _n_of > 0:
            try:
                bx, by = btn_ofertas.right - 18, btn_ofertas.top + 6
                pygame.draw.circle(screen, (255, 68, 68), (bx, by), 11)
                bs = get_font('sm').render(str(_n_of), True, (255, 255, 255))
                screen.blit(bs, bs.get_rect(center=(bx, by)))
            except Exception:
                pass
        
        # Lógica de clicks
        if click_pos:
            if rect_hist_up.collidepoint(click_pos):
                estado['hist_scroll_offset'] = max(0, estado.get('hist_scroll_offset', 0) - 1)
            elif rect_hist_down.collidepoint(click_pos):
                jugados_cl = [p for p in getattr(liga, 'calendario', [])
                           if p.jugado and (p.local_id == mi_equipo.id or p.visitante_id == mi_equipo.id)]
                max_offset = max(0, len(jugados_cl) - 6)
                estado['hist_scroll_offset'] = min(max_offset, estado.get('hist_scroll_offset', 0) + 1)
            elif btn_jugar.collidepoint(click_pos):
                if tiene_copa_pendiente:
                    logger.warning("Intento de jugar jornada de liga cuando hay copa internacional pendiente. Bloqueado.")
                elif esta_finalizada:
                    return "resumen_temporada_screen"
                else:
                    estado['partido_actual'] = partido_usuario
                    # v0.8.4: marcar explícitamente que es un partido de LIGA. Antes se confiaba
                    # solo en el default de .get('match_mode', 'liga'); pero una nueva carrera deja
                    # match_mode=None (clave existe) y prepartido/partido caían al menú.
                    estado['match_mode'] = 'liga'
                    return "prepartido_screen"
            elif btn_mercado.collidepoint(click_pos):
                return "market_screen"
            elif btn_copa.collidepoint(click_pos):
                return "copa_screen"
            elif btn_ofertas.collidepoint(click_pos):
                return "ofertas_screen"
            elif btn_stats.collidepoint(click_pos):
                return "stats_screen"
            elif btn_career.collidepoint(click_pos):
                return "career_screen"
            elif btn_equipo.collidepoint(click_pos):
                estado['team_contexto'] = 'carrera'  # v0.8.5: dirección de carrera (no amistoso)
                return "team_screen"
            elif btn_salir.collidepoint(click_pos):
                estado['save_slots_return'] = 'league_screen'
                return "save_slots_screen"
        return None
    except Exception as error_general:
        logger.error(f"Error crítico en render de league_screen: {error_general}. Recuperando pantalla al menú principal.")
        try:
            screen.fill((10, 20, 30))
            emerg_rect = pygame.Rect(490, 330, 300, 60)
            pygame.draw.rect(screen, (255, 68, 68), emerg_rect, border_radius=8)
            font = pygame.font.Font(None, 24)
            txt = font.render(f"ERROR: {str(error_general)[:25]}. VOLVER", True, (255, 255, 255))
            screen.blit(txt, txt.get_rect(center=emerg_rect.center))
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "menu"
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if emerg_rect.collidepoint(event.pos):
                        return "menu"
        except Exception as error_emergencia:
            logger.critical(f"Fallo crítico en pantalla de emergencia de liga: {error_emergencia}")
            return "menu"
        return "menu"
