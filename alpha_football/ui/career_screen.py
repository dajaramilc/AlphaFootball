# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Pantalla de la Carrera del DT (Pygame)
Muestra las estadísticas globales del DT (títulos, goles, temporadas)
y un historial detallado por temporada con récords y fallbacks resilientes.
Implementa una barra lateral consistente con league_screen y previene bugs de clics.
"""

import sys
import os
import logging

# Configuración del logger para seguimiento de eventos y errores
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
logger = logging.getLogger(__name__)

# Intentar importar pygame de manera segura
try:
    import pygame
except ImportError as error_pygame:
    logger.critical(f"Error crítico al importar pygame en career_screen: {error_pygame}. La UI no podrá renderizarse.")
    raise error_pygame

# Importación resiliente del tema visual
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
except Exception as error_import_theme:
    logger.warning(f"Advertencia: No se pudo importar alpha_football.ui.theme ({error_import_theme}). Usando fallback local.")
    
    # Fallback local para garantizar la continuidad del sistema si falla el tema
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
        except Exception as e_font:
            logger.error(f"Fallo en get_font local: {e_font}")
        return pygame.font.Font(None, 24)
        
    def draw_gradient_bg(screen):
        try:
            screen.fill((10, 14, 26))
        except Exception as e_bg:
            logger.error(f"Error en draw_gradient_bg local: {e_bg}")
        
    def draw_panel(screen, rect):
        try:
            pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=8)
            pygame.draw.rect(screen, (0, 191, 255), rect, width=1, border_radius=8)
        except Exception:
            try:
                pygame.draw.rect(screen, (20, 26, 46), rect)
            except Exception as e_panel:
                logger.error(f"Error al dibujar panel local: {e_panel}")
        
    def draw_button(screen, rect, text, hover):
        try:
            color_bg = (0, 191, 255) if hover else (20, 26, 46)
            color_fg = (10, 14, 26) if hover else (255, 255, 255)
            pygame.draw.rect(screen, color_bg, rect, border_radius=5)
            pygame.draw.rect(screen, (255, 255, 255), rect, width=1, border_radius=5)
            
            font = get_font('md')
            txt_surf = font.render(text, True, color_fg)
            txt_rect = txt_surf.get_rect(center=rect.center)
            screen.blit(txt_surf, txt_rect)
        except Exception as error_local_btn:
            logger.error(f"Error en draw_button fallback local: {error_local_btn}")
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
        except Exception as error_local_txt:
            logger.error(f"Error en draw_text fallback local: {error_local_txt}")

def draw_pitch_lines(screen: pygame.Surface) -> None:
    """
    Dibuja de forma sutil las marcas de un campo de fútbol en el fondo.
    Proporciona un ambiente alegre y deportivo sin interferir con la interfaz.
    """
    try:
        # Color verde azulado muy tenue sobre el fondo azul marino profundo
        pitch_color = (20, 38, 62)
        
        # Círculo central en la parte derecha
        pygame.draw.circle(screen, pitch_color, (750, 360), 120, 2)
        pygame.draw.circle(screen, pitch_color, (750, 360), 6)
        
        # Línea divisoria de centro de campo
        pygame.draw.line(screen, pitch_color, (750, 20), (750, 700), 2)
        
        # Áreas grandes de juego de ambos lados
        pygame.draw.rect(screen, pitch_color, pygame.Rect(260, 110, 160, 500), 2)
        pygame.draw.rect(screen, pitch_color, pygame.Rect(1080, 110, 160, 500), 2)
        
    except Exception as error_pitch:
        # En caso de error, capturamos para no interrumpir el flujo visual
        logger.error(f"Error al dibujar líneas del campo en carrera: {error_pitch}. Continuando con ejecución.")

def draw_styled_button(screen: pygame.Surface, rect: pygame.Rect, text: str, hover: bool, accent_color: tuple[int, int, int] | str, enabled: bool = True) -> pygame.Rect:
    """
    Dibuja un botón interactivo de acuerdo con la nueva identidad de colores.
    Soporta botones deshabilitados/bloqueados y colores de acento dinámicos.
    """
    try:
        button_rect = pygame.Rect(rect)
        
        # Conversión del color de acento si viene como Hex string o tipo diferente
        real_accent = accent_color
        if isinstance(accent_color, str) and accent_color.startswith('#'):
            try:
                real_accent = (int(accent_color[1:3], 16), int(accent_color[3:5], 16), int(accent_color[5:7], 16))
            except Exception:
                real_accent = (0, 191, 255) # Fallback azul celeste
        
        # Obtener los colores básicos RGB
        color_panel = COLORS.get('panel', (20, 26, 46))
        color_azul = COLORS.get('azul', (0, 191, 255))
        color_blanco = COLORS.get('blanco', (255, 255, 255))

        if not enabled:
            # Color gris oscuro apagado para botones deshabilitados o bloqueados
            bg_color = (25, 25, 35)
            border_color = (75, 75, 85)
            text_color = (110, 110, 120)
        elif hover:
            # Estilo hover activo con el color de acento asignado al botón
            bg_color = (30, 45, 75)
            border_color = real_accent
            text_color = real_accent
        else:
            # Estilo normal inactivo
            bg_color = color_panel
            border_color = color_azul
            text_color = color_blanco
            
        # Dibujar fondo y borde con esquinas redondeadas
        try:
            pygame.draw.rect(screen, bg_color, button_rect, border_radius=8)
            pygame.draw.rect(screen, border_color, button_rect, width=2, border_radius=8)
        except TypeError:
            pygame.draw.rect(screen, bg_color, button_rect)
            pygame.draw.rect(screen, border_color, button_rect, width=2)
            
        # Dibujar texto del botón centrado
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

def render(screen: pygame.Surface, estado: dict) -> str | None:
    """
    Renderiza la pantalla de Carrera del DT en Pygame.
    Muestra estadísticas agregadas y la lista de temporadas históricas.
    Incorpora la barra lateral izquierda y los colores oficiales de la nueva identidad visual.
    Previene bugs de clics al utilizar una única definición consistente del menú lateral.
    """
    try:
        # Recuperación segura del estado principal
        liga = estado.get('liga')
        mi_equipo = estado.get('mi_equipo')
        historial = estado.get('historial', [])
        
        # Resiliencia si no se han cargado datos clave
        if not liga or not mi_equipo:
            logger.error("Error resiliente: No hay liga o equipo cargado en el estado de carrera.")
            return "menu"
            
        # Inicialización segura de offsets temporales de scroll para evitar nulos
        estado.setdefault('career_scroll_offset', 0)
        
        # 1. Dibujar fondo base con gradiente y marcas del campo de fútbol alegre
        try:
            draw_gradient_bg(screen)
            draw_pitch_lines(screen)
        except Exception as e_bg:
            logger.error(f"Error al dibujar fondo: {str(e_bg)}. Rellenando con color plano.")
            screen.fill(COLORS.get('bg', (10, 14, 26)))
            
        # Decoración visual RGB tricolor alegre en el borde superior de la pantalla
        try:
            pygame.draw.rect(screen, COLORS.get('rojo', (255, 68, 68)), pygame.Rect(0, 0, SCREEN_W, 4))
            pygame.draw.rect(screen, COLORS.get('verde', (0, 255, 136)), pygame.Rect(0, 4, SCREEN_W, 4))
            pygame.draw.rect(screen, COLORS.get('azul', (0, 191, 255)), pygame.Rect(0, 8, SCREEN_W, 4))
        except Exception as e_deco:
            logger.warning(f"No se pudieron dibujar las franjas decorativas: {str(e_deco)}")
            
        # --- MENÚ LATERAL IZQUIERDO (Consistencia visual 100% con league_screen) ---
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
            jornada_actual = getattr(liga, "jornada_actual", 1)
            draw_text(screen, f"Jornada: {jornada_actual}/{getattr(liga, 'num_jornadas', 14)}", (45, 210), size='sm', color='dorado')
        except Exception as e_logo:
            logger.error(f"Error al dibujar textos de logo/datos en lateral: {str(e_logo)}")
            
        # --- ENCABEZADO DE CONTENIDO PRINCIPAL (DERECHA) ---
        draw_text(screen, "PERFIL DE CARRERA DEL DT", (300, 20), size='xl', color='dorado')
        dt_desc = f"Historial y logros de {estado.get('dt_nombre', 'Mister')[:16]} con {mi_equipo.nombre}"
        draw_text(screen, dt_desc, (300, 65), size='sm', color='azul')
        
        # --- CÁLCULO DE ESTADÍSTICAS AGREGADAS (Resiliente) ---
        seasons_count = len(historial)
        leagues_won = 0
        copas_won = 0
        total_pts = 0
        total_gf = 0
        total_gc = 0
        best_pts = 0
        best_season = "-"
        
        for h in historial:
            try:
                pos = h.get('pos', 8)
                pts = h.get('pts', 0)
                gf = h.get('gf', 0)
                gc = h.get('gc', 0)
                lib = h.get('libertadores', '')
                temp = h.get('temporada', 1)
                
                if pos == 1:
                    leagues_won += 1
                if 'campeon' in str(lib).lower() and 'sub' not in str(lib).lower():
                    copas_won += 1
                    
                total_pts += pts
                total_gf += gf
                total_gc += gc
                
                if pts > best_pts:
                    best_pts = pts
                    best_season = f"T{temp}"
            except Exception as e_calc:
                logger.error(f"Error procesando registro de historial de carrera: {e_calc}. Continuando con datos restantes.")
                
        dg_total = total_gf - total_gc
        
        # --- DETECCIÓN Y ADVERTENCIA DE FECHA INTERNACIONAL ---
        tiene_copa_pendiente = False
        fase_nombre_pend = None
        try:
            from alpha_football.ui.copa_screen import obtener_partido_copa_pendiente
            fase_nombre_pend, _ = obtener_partido_copa_pendiente(estado)
            tiene_copa_pendiente = (fase_nombre_pend is not None)
        except Exception as error_copas:
            logger.error(f"Error al verificar advertencia de copa en carrera: {error_copas}")
            
        # Banner de advertencia parpadeante en la esquina superior derecha (Consistente con league_screen)
        if tiene_copa_pendiente and fase_nombre_pend:
            try:
                alert_rect = pygame.Rect(820, 20, 420, 65)
                pulso = (pygame.time.get_ticks() // 500) % 2
                color_borde = COLORS.get('rojo', (255, 68, 68)) if pulso == 0 else COLORS.get('dorado', (255, 215, 0))
                pygame.draw.rect(screen, (35, 15, 15), alert_rect, border_radius=6)
                pygame.draw.rect(screen, color_borde, alert_rect, width=2, border_radius=6)
                draw_text(screen, "⚠️ ¡FECHA INTERNACIONAL DETECTADA!", (835, 25), size='sm', color='rojo')
                draw_text(screen, f"Copa pendiente: {fase_nombre_pend}. Juega Copa primero.", (835, 48), size='sm', color='blanco')
            except Exception as e_alert:
                logger.error(f"Error al renderizar banner de alerta en carrera: {str(e_alert)}")
                
        # --- BOTONES EN EL MENÚ IZQUIERDO (Mismas posiciones que league_screen) ---
        btn_liga = pygame.Rect(40, 250, 220, 50)
        btn_mercado = pygame.Rect(40, 320, 220, 50)
        btn_copa = pygame.Rect(40, 390, 220, 50)
        btn_career = pygame.Rect(40, 460, 220, 50)
        btn_equipo = pygame.Rect(40, 530, 220, 50)
        btn_salir = pygame.Rect(40, 630, 220, 50)
        
        # Procesar hovers de los botones
        mouse_pos = pygame.mouse.get_pos()
        click_pos = None
        
        # Consumir eventos del frame de forma limpia
        try:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    click_pos = event.pos
        except Exception as e_events:
            logger.error(f"Error al procesar eventos en career_screen: {str(e_events)}")
            
        hov_liga = btn_liga.collidepoint(mouse_pos)
        hov_mercado = btn_mercado.collidepoint(mouse_pos)
        hov_copa = btn_copa.collidepoint(mouse_pos)
        hov_equipo = btn_equipo.collidepoint(mouse_pos)
        hov_salir = btn_salir.collidepoint(mouse_pos)
        
        # Renderizar botones en menú lateral
        draw_styled_button(screen, btn_liga, "VOLVER A LIGA", hov_liga, COLORS.get('verde', (0, 255, 136)))
        draw_styled_button(screen, btn_mercado, "MERCADO DE PASES", hov_mercado, COLORS.get('azul', (0, 191, 255)))
        draw_styled_button(screen, btn_copa, "COPA INTERNACIONAL", hov_copa, COLORS.get('dorado', (255, 215, 0)))
        # Pestaña activa (resaltada en dorado)
        draw_styled_button(screen, btn_career, "HISTORIAL CARRERA", True, COLORS.get('dorado', (255, 215, 0)))
        draw_styled_button(screen, btn_equipo, "DIRECCIÓN EQUIPO", hov_equipo, COLORS.get('azul', (0, 191, 255)))
        draw_styled_button(screen, btn_salir, "GUARDAR Y SALIR", hov_salir, COLORS.get('rojo', (255, 68, 68)))
        
        # --- PANEL CENTRAL: ESTADÍSTICAS GLOBALES ---
        left_rect = pygame.Rect(300, 100, 380, 580)
        try:
            draw_panel(screen, left_rect)
            draw_text(screen, "ESTADÍSTICAS GLOBALES", (320, 115), size='md', color='azul')
            pygame.draw.line(screen, COLORS.get('azul', (0, 191, 255)), (320, 145), (660, 145), 1)
            
            stats_data = [
                ("Temporadas Jugadas:", str(seasons_count), 'blanco'),
                ("Ligas Ganadas:", f"{leagues_won} 🏆", 'dorado' if leagues_won > 0 else 'blanco'),
                ("Copas Internacionales:", f"{copas_won} 🌎", 'dorado' if copas_won > 0 else 'blanco'),
                ("Puntos Totales:", str(total_pts), 'blanco'),
                ("Goles a Favor (GF):", str(total_gf), 'verde'),
                ("Goles en Contra (GC):", str(total_gc), 'rojo'),
                ("Diferencia de Goles:", f"{'+' if dg_total > 0 else ''}{dg_total}", 'verde' if dg_total >= 0 else 'rojo'),
                ("Récord de Puntos:", f"{best_pts} ({best_season})", 'dorado' if best_pts > 0 else 'blanco')
            ]
            
            y_stat = 175
            for label, val, color in stats_data:
                draw_text(screen, label, (320, y_stat), size='sm', color='blanco')
                draw_text(screen, val, (550, y_stat), size='md', color=color)
                y_stat += 48
        except Exception as e_left_panel:
            logger.error(f"Error al renderizar panel de estadísticas globales: {e_left_panel}")
            
        # --- PANEL DERECHO: HISTORIAL POR TEMPORADA ---
        right_rect = pygame.Rect(700, 100, 560, 580)
        try:
            draw_panel(screen, right_rect)
            draw_text(screen, "HISTORIAL POR TEMPORADA", (720, 115), size='md', color='azul')
            
            # Encabezados de columnas del historial
            headers = ["Temp", "Posición", "PTS", "GF-GC", "Liga", "Copa Internac."]
            header_x = [720, 775, 865, 920, 990, 1115]
            for h, x_pos in zip(headers, header_x):
                draw_text(screen, h, (x_pos, 150), size='sm', color='dorado')
                
            pygame.draw.line(screen, COLORS.get('azul', (0, 191, 255)), (720, 170), (1240, 170), 1)
            
            if not historial:
                draw_text(screen, "Aún no has completado ninguna temporada.", (720, 200), size='md', color='blanco')
                draw_text(screen, "¡El historial se llenará al completar una temporada!", (720, 230), size='sm', color='azul')
            else:
                y_row = 185
                row_height = 37
                items_visibles = 11
                scroll = estado['career_scroll_offset']
                
                # Control de límites de scroll seguro
                if scroll < 0:
                    scroll = 0
                if scroll > max(0, len(historial) - items_visibles):
                    scroll = max(0, len(historial) - items_visibles)
                estado['career_scroll_offset'] = scroll
                
                temp_list = historial[scroll:scroll + items_visibles]
                
                for h in temp_list:
                    try:
                        temp_num = f"T{h.get('temporada', 1)}"
                        pos = h.get('pos', 8)
                        pts = h.get('pts', 0)
                        gf = h.get('gf', 0)
                        gc = h.get('gc', 0)
                        campeon = h.get('campeon_liga', 'Desconocido')
                        lib = h.get('libertadores', '-')
                        
                        lib_txt = str(lib)
                        lib_color = 'blanco'
                        if 'campeon' in lib_txt.lower() and 'sub' not in lib_txt.lower():
                            lib_txt = "¡CAMPEÓN! 🌎"
                            lib_color = 'dorado'
                        elif 'subcampeon' in lib_txt.lower():
                            lib_txt = "Subcampeón 🥈"
                            lib_color = 'dorado'
                            
                        pos_txt = f"{pos}° Lugar"
                        pos_color = 'dorado' if pos == 1 else ('verde' if pos <= 2 else ('rojo' if pos >= 7 else 'blanco'))
                        
                        draw_text(screen, temp_num, (720, y_row), size='sm', color='azul')
                        draw_text(screen, pos_txt, (775, y_row), size='sm', color=pos_color)
                        draw_text(screen, str(pts), (865, y_row), size='sm', color='blanco')
                        draw_text(screen, f"{gf}-{gc}", (920, y_row), size='sm', color='blanco')
                        draw_text(screen, campeon[:14], (990, y_row), size='sm', color='blanco')
                        draw_text(screen, lib_txt[:14], (1115, y_row), size='sm', color=lib_color)
                        
                        y_row += row_height
                    except Exception as e_row:
                        logger.error(f"Error al renderizar fila de historial: {e_row}")
                        
                # Controles de scroll en el historial
                if len(historial) > items_visibles:
                    btn_up = pygame.Rect(1215, 185, 22, 22)
                    btn_down = pygame.Rect(1215, 550, 22, 22)
                    
                    up_hover = btn_up.collidepoint(mouse_pos)
                    down_hover = btn_down.collidepoint(mouse_pos)
                    
                    try:
                        pygame.draw.rect(screen, (30, 45, 75) if up_hover else (20, 26, 46), btn_up, border_radius=4)
                        pygame.draw.rect(screen, COLORS.get('azul', (0, 191, 255)), btn_up, width=1, border_radius=4)
                        
                        pygame.draw.rect(screen, (30, 45, 75) if down_hover else (20, 26, 46), btn_down, border_radius=4)
                        pygame.draw.rect(screen, COLORS.get('azul', (0, 191, 255)), btn_down, width=1, border_radius=4)
                    except TypeError:
                        pygame.draw.rect(screen, (20, 26, 46), btn_up)
                        pygame.draw.rect(screen, (20, 26, 46), btn_down)
                        
                    draw_text(screen, "▲", (1220, 187), size='sm', color='verde' if up_hover else 'blanco')
                    draw_text(screen, "▼", (1220, 552), size='sm', color='verde' if down_hover else 'blanco')
        except Exception as e_right_panel:
            logger.error(f"Error al renderizar panel de historial por temporada: {e_right_panel}")
            
        # --- PROCESAMIENTO DE CLICS Y NAVEGACIÓN ---
        if click_pos:
            # Volver a Liga
            if btn_liga.collidepoint(click_pos):
                estado.pop('career_scroll_offset', None)
                return "volver"
                
            # Ir a Mercado de Pases
            elif btn_mercado.collidepoint(click_pos):
                estado.pop('career_scroll_offset', None)
                return "market_screen"
                
            # Ir a Copa Internacional
            elif btn_copa.collidepoint(click_pos):
                estado.pop('career_scroll_offset', None)
                return "copa_screen"
                
            # Pestaña activa actual (Historial carrera)
            elif btn_career.collidepoint(click_pos):
                pass
                
            # Ir a Dirección de Equipo
            elif btn_equipo.collidepoint(click_pos):
                estado.pop('career_scroll_offset', None)
                return "team_screen"
                
            # Guardar partida y salir al menú principal
            elif btn_salir.collidepoint(click_pos):
                try:
                    from alpha_football.save import guardar_partida
                    from alpha_football.models import EstadoJuego
                    
                    alin = estado.get('alineacion_activa')
                    datos_estado = {
                        "ligas": [liga.to_dict()] if liga else [],
                        "copas": [c.to_dict() for c in estado.get("copas", [])],
                        "equipo_usuario_id": mi_equipo.id if mi_equipo else None,
                        "liga_usuario_id": liga.tipo if liga else None,
                        "temporada": estado.get("temporada", 1),
                        "historial": estado.get("transfer_log", []),
                        "pantalla_actual": "temporada",
                        "alineacion_activa": {
                            "titulares": list(alin.titulares),
                            "formacion": str(alin.formacion)
                        } if alin else None
                    }
                    estado_juego = EstadoJuego.from_dict(datos_estado)
                    guardar_partida(estado_juego)
                    logger.info("Partida guardada de forma segura al salir de career_screen.")
                except Exception as error_guardar:
                    logger.error(f"Error al guardar la partida desde la pantalla de carrera: {error_guardar}")
                estado.pop('career_scroll_offset', None)
                return "menu"
                
            # Lógica de Scroll en el historial
            if len(historial) > items_visibles:
                btn_up = pygame.Rect(1215, 185, 22, 22)
                btn_down = pygame.Rect(1215, 550, 22, 22)
                if btn_up.collidepoint(click_pos) and scroll > 0:
                    estado['career_scroll_offset'] -= 1
                elif btn_down.collidepoint(click_pos) and scroll < len(historial) - items_visibles:
                    estado['career_scroll_offset'] += 1
                    
    except Exception as general_error:
        # En caso de error inesperado, loggeamos la excepción real e intentamos dibujar pantalla de recuperación
        logger.error(f"Error general en career_screen.py renderizado: {general_error}. Intentando recuperación de UI.")
        try:
            screen.fill((10, 20, 30))
            emerg_rect = pygame.Rect(490, 330, 300, 60)
            pygame.draw.rect(screen, (255, 68, 68), emerg_rect, border_radius=8)
            font = pygame.font.Font(None, 24)
            txt = font.render(f"ERROR: {str(general_error)[:25]}. VOLVER", True, (255, 255, 255))
            screen.blit(txt, txt.get_rect(center=emerg_rect.center))
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if emerg_rect.collidepoint(event.pos):
                        return "volver"
        except Exception as error_emergencia:
            logger.critical(f"Fallo crítico en pantalla de emergencia de carrera: {error_emergencia}")
            return "volver"
            
    return None
