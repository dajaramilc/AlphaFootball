# -*- coding: utf-8 -*-
"""
Módulo de Tema y Estilos Visuales para Alpha Football.
Define la paleta de colores, tamaños de fuentes, fondos y componentes básicos reutilizables (paneles, botones, textos).
"""

import pygame
import logging

# Configuración básica del logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
logger = logging.getLogger(__name__)

# Dimensiones fijas de la pantalla según contrato
SCREEN_W = 1280
SCREEN_H = 720

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  EDITA AQUÍ EL LOOK DEL JUEGO (un solo lugar)                              ║
# ║  Cambia colores y tamaños de fuente aquí y se reflejan en TODAS las        ║
# ║  pantallas, sin tener que buscar por el resto del código.                  ║
# ╚══════════════════════════════════════════════════════════════════════════╝

# Tamaños de fuente en píxeles por etiqueta ('sm','md','lg','xl'). Súbelos/bájalos
# para agrandar o achicar TODOS los textos del juego de una sola vez.
FONT_SIZES = {
    'sm': 18,
    'md': 24,
    'lg': 32,
    'xl': 48,
}

# Paleta de colores oficiales (convertidos de Hex a tuplas RGB para Pygame)
COLORS = {
    'bg': (10, 14, 26),        # #0A0E1A (Azul marino muy oscuro para el fondo)
    'verde': (0, 255, 136),    # #00FF88 (Verde neón para clasificados, botones hover y acentos positivos)
    'dorado': (255, 215, 0),   # #FFD700 (Dorado para campeón, estrellas y copas)
    'rojo': (255, 68, 68),     # #FF4444 (Rojo para descenso y alertas)
    'azul': (0, 191, 255),     # #00BFFF (Azul celeste brillante para bordes y títulos)
    'blanco': (255, 255, 255), # #FFFFFF (Blanco puro para textos normales)
    'panel': (20, 26, 46)      # #141A2E (Azul oscuro para fondos de paneles y cards)
}

# --- Constantes de color nombradas (Bug B) ---
# La pantalla de Dirección de Equipo (team_screen) usa estos nombres para el campo
# táctico y las alertas. Antes no existían -> NameError. Centralizadas aquí.
BLANCO = COLORS['blanco']          # (255, 255, 255)
AMARILLO = (255, 215, 0)           # amarillo/dorado para mensajes flash
GRIS_CLAR = (200, 200, 200)        # gris claro para textos/posiciones secundarias
VERDE_CAMPO = (34, 110, 45)        # verde césped del campo
VERDE_CAMPO2 = (40, 125, 52)       # verde alterno para las franjas del césped

# Cache de fuentes: crear una pygame.font.Font es caro y antes se hacía en CADA frame
# por cada texto. Se memoiza por tamaño en píxeles (clave entera).
_FONT_CACHE: dict = {}

def get_font(size: str) -> pygame.font.Font:
    """
    Retorna un objeto pygame.font.Font según el tamaño solicitado ('sm', 'md', 'lg', 'xl').
    Implementa un mecanismo de resiliencia con fallbacks para evitar caídas si falla la inicialización.
    """
    # Tamaños centralizados en FONT_SIZES (editables arriba). Fallback a 24 si la etiqueta no existe.
    pixel_size = FONT_SIZES.get(size, 24)

    # Si ya creamos esta fuente, reutilizarla (clave = tamaño en píxeles).
    cached = _FONT_CACHE.get(pixel_size)
    if cached is not None:
        return cached

    try:
        # Asegurarse de que el módulo de fuentes de pygame esté inicializado
        if not pygame.font.get_init():
            try:
                pygame.font.init()
            except Exception as e_init:
                logger.error(f"Error al inicializar pygame.font: {e_init}. Reintentando inicializar pygame global...")
                pygame.init()

        # Intentar cargar una fuente del sistema legible y moderna
        try:
            font = pygame.font.SysFont("arial", pixel_size)
            if font is not None:
                _FONT_CACHE[pixel_size] = font
                return font
        except Exception as e_sysfont:
            logger.warning(f"No se pudo cargar la fuente del sistema 'arial': {e_sysfont}. Intentando fuente por defecto.")

        # Fallback a la fuente por defecto de pygame
        fuente_default = pygame.font.Font(None, pixel_size)
        _FONT_CACHE[pixel_size] = fuente_default
        return fuente_default
        
    except Exception as e_global:
        logger.error(f"Fallo crítico en get_font para tamaño {size}: {e_global}. Usando fuente simulada de emergencia.")
        # Como último recurso, si pygame de verdad está roto, retornamos un objeto simulado (Mock)
        # para que el sistema siga ejecutándose sin romperse (continuidad de ejecución).
        class MockFont:
            def render(self, text, antialias, color, background=None):
                return pygame.Surface((10, 10))
            def size(self, text):
                return (len(text) * 10, 20)
        return MockFont()

# Cache del fondo con gradiente: construirlo dibuja una línea por fila (720 draws), así que
# antes costaba ~720 draw.line POR FRAME en cada pantalla. Ahora se construye una sola vez
# por tamaño y se reutiliza la Surface (1 blit por frame).
_GRADIENT_CACHE: dict = {}

def _build_gradient(width: int, height: int) -> "pygame.Surface":
    """Construye (una vez) la Surface del gradiente vertical."""
    surf = pygame.Surface((width, height))
    color_top = COLORS['bg']
    color_bottom = (15, 25, 45)  # Azul marino un poco más claro que #0A0E1A
    for y in range(height):
        ratio = y / height
        r = max(0, min(255, int(color_top[0] * (1 - ratio) + color_bottom[0] * ratio)))
        g = max(0, min(255, int(color_top[1] * (1 - ratio) + color_bottom[1] * ratio)))
        b = max(0, min(255, int(color_top[2] * (1 - ratio) + color_bottom[2] * ratio)))
        pygame.draw.line(surf, (r, g, b), (0, y), (width, y))
    return surf

def draw_gradient_bg(screen):
    """
    Pinta el fondo con gradiente vertical premium reutilizando una Surface cacheada
    (se construye una sola vez por tamaño de pantalla).
    """
    try:
        width, height = screen.get_size()
    except Exception as e_size:
        logger.error(f"No se pudo obtener el tamaño de la pantalla en draw_gradient_bg: {e_size}. Usando dimensiones por defecto.")
        width, height = SCREEN_W, SCREEN_H

    try:
        key = (width, height)
        surf = _GRADIENT_CACHE.get(key)
        if surf is None:
            surf = _build_gradient(width, height)
            try:
                surf = surf.convert()  # acelera los blits posteriores
            except Exception:
                pass
            _GRADIENT_CACHE[key] = surf
        screen.blit(surf, (0, 0))
    except Exception as e_draw:
        logger.error(f"Error al pintar el gradiente: {e_draw}. Usando color de fondo plano como fallback.")
        try:
            screen.fill(COLORS['bg'])
        except Exception as e_fill:
            logger.critical(f"Fallo crítico insalvable en draw_gradient_bg: {e_fill}")

def draw_panel(screen, rect):
    """
    Dibuja un panel rectangular contenedor elegante con fondo oscuro y borde azul.
    """
    try:
        # Color del fondo del panel y del borde
        panel_color = COLORS['panel']
        border_color = COLORS['azul']
        
        rect_obj = pygame.Rect(rect)
        
        # Dibujar fondo del panel (relleno) con esquinas redondeadas si es soportado
        try:
            pygame.draw.rect(screen, panel_color, rect_obj, border_radius=8)
        except TypeError:
            # Fallback a esquinas rectas si la versión de pygame no soporta border_radius
            pygame.draw.rect(screen, panel_color, rect_obj)
            
        # Dibujar borde fino decorativo
        try:
            pygame.draw.rect(screen, border_color, rect_obj, width=2, border_radius=8)
        except TypeError:
            pygame.draw.rect(screen, border_color, rect_obj, width=2)
            
    except Exception as e_panel:
        logger.error(f"Error al dibujar panel: {e_panel}. Reintentando con dibujo plano simplificado.")
        try:
            # Fallback simplificado: caja plana básica sin florituras
            pygame.draw.rect(screen, COLORS['panel'], rect)
        except Exception as e_fallback:
            logger.error(f"Fallo en fallback de draw_panel: {e_fallback}")

def draw_button(screen, rect, text, hover) -> pygame.Rect:
    """
    Dibuja un botón interactivo y estilizado en la pantalla.
    Retorna el objeto pygame.Rect del botón.
    """
    button_rect = pygame.Rect(rect)
    try:
        # Elegir colores según el estado de hover (foco del mouse)
        if hover:
            bg_color = (30, 40, 70)          # Azul grisáceo brillante para hover
            border_color = COLORS['verde']   # Borde verde neón activo
            text_color = COLORS['verde']     # Texto verde
        else:
            bg_color = COLORS['panel']       # Color normal del panel
            border_color = COLORS['azul']    # Borde azul
            text_color = COLORS['blanco']    # Texto blanco
            
        # Dibujar el cuerpo del botón
        try:
            pygame.draw.rect(screen, bg_color, button_rect, border_radius=6)
        except TypeError:
            pygame.draw.rect(screen, bg_color, button_rect)
            
        # Dibujar el borde del botón
        try:
            pygame.draw.rect(screen, border_color, button_rect, width=2, border_radius=6)
        except TypeError:
            pygame.draw.rect(screen, border_color, button_rect, width=2)
            
        # Obtener y renderizar el texto centrado en el botón
        try:
            font = get_font('md')
            text_surf = font.render(text, True, text_color)
            text_rect = text_surf.get_rect(center=button_rect.center)
            screen.blit(text_surf, text_rect)
        except Exception as e_text:
            logger.error(f"Error al renderizar texto del botón '{text}': {e_text}")
            
    except Exception as e_btn:
        logger.error(f"Error general en draw_button: {e_btn}. Retornando rect básico sin dibujar.")
        
    return button_rect

# Cache de texto renderizado: font.render() es caro y antes se ejecutaba en cada frame
# (con sombra = 2 renders por texto). Las Surfaces se reutilizan entre frames. Se acota el
# tamaño porque algunos textos son dinámicos (reloj, %), para no crecer sin límite.
_TEXT_CACHE: dict = {}
_TEXT_CACHE_MAX = 2000

def _render_text_cached(text, size, rgb_color, shadow):
    """Devuelve (surf_principal, surf_sombra|None) cacheadas por (texto, size, color, sombra)."""
    key = (text, size, rgb_color, shadow)
    entry = _TEXT_CACHE.get(key)
    if entry is not None:
        return entry
    font = get_font(size)
    main_surf = font.render(text, True, rgb_color)
    shadow_surf = font.render(text, True, (0, 0, 0)) if shadow else None
    if len(_TEXT_CACHE) > _TEXT_CACHE_MAX:
        _TEXT_CACHE.clear()
    _TEXT_CACHE[key] = (main_surf, shadow_surf)
    return (main_surf, shadow_surf)

def draw_text(screen, text, pos, size='md', color='blanco', shadow=True):
    """
    Dibuja texto en pantalla con fuente del tamaño seleccionado y color.
    Admite sombra negra desplazada para mejorar la legibilidad sobre fondos complejos.
    Reutiliza superficies cacheadas (no re-renderiza el mismo texto cada frame).
    """
    try:
        # Color RGB real del diccionario, con fallback a blanco
        rgb_color = COLORS.get(color, COLORS['blanco'])
        main_surf, shadow_surf = _render_text_cached(text, size, rgb_color, shadow)

        # Sombra desplazada 2 px abajo-derecha (si corresponde)
        if shadow and shadow_surf is not None:
            screen.blit(shadow_surf, (pos[0] + 2, pos[1] + 2))

        # Texto principal
        screen.blit(main_surf, pos)

    except Exception as e_text_draw:
        logger.error(f"Error al dibujar texto '{text}' en pos {pos}: {e_text_draw}")
