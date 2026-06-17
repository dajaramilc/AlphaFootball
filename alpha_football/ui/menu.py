# -*- coding: utf-8 -*-
"""
Módulo del Menú Principal Rediseñado para Alpha Football.
Permite iniciar una nueva partida, seleccionar liga y equipo, y cargar partidas guardadas.
Implementa una interfaz alineada a la izquierda, efectos de fútbol alegre en el fondo,
sistema de partículas animadas y soporte para el nuevo logotipo.
"""

import pygame
import sys
import logging
import math
import random
import os
from typing import Dict, List, Any

from alpha_football.ui.theme import (
    COLORS, SCREEN_W, SCREEN_H, get_font,
    draw_gradient_bg, draw_panel, draw_button, draw_text
)

# Configuración del logging para el seguimiento de la interfaz
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
logger = logging.getLogger(__name__)

# Definición de las ligas oficiales del juego
LIGAS_DISPONIBLES = [
    {'id': 'betplay', 'name': 'Liga BetPlay (Colombia)'},
    {'id': 'laliga', 'name': 'LaLiga (España)'},
    {'id': 'premier', 'name': 'Premier League (Inglaterra)'},
    {'id': 'brasil', 'name': 'Brasileirão (Brasil)'},
    {'id': 'argentina', 'name': 'Liga Argentina (Argentina)'}
]

def load_league_teams(league_id: str):
    """
    Importa dinámicamente el módulo correspondiente a la liga y obtiene el objeto Liga.
    Implementa un mecanismo de resiliencia con fallback a datos simulados si falla la importación.
    """
    try:
        # Importaciones dinámicas según la liga seleccionada
        if league_id == 'betplay':
            from alpha_football.data.betplay import get_liga
        elif league_id == 'laliga':
            from alpha_football.data.laliga import get_liga
        elif league_id == 'premier':
            from alpha_football.data.premier import get_liga
        elif league_id == 'brasil':
            from alpha_football.data.brasil import get_liga
        elif league_id == 'argentina':
            from alpha_football.data.argentina import get_liga
        else:
            raise ValueError(f"Liga no soportada por el sistema: {league_id}")
            
        liga_obj = get_liga()
        if liga_obj is not None:
            return liga_obj
        else:
            raise ValueError("El cargador de liga retornó un objeto nulo.")
        
    except Exception as e:
        logger.error(f"Error al cargar liga '{league_id}': {e}. Usando datos de simulación fallback.")
        
        # Intentamos importar las clases de models.py para el fallback
        try:
            from alpha_football.models import Liga, Equipo, Jugador
        except Exception as e_models:
            logger.warning(f"No se pudo importar models.py: {e_models}. Creando clases mock.")
            # Definimos clases locales en caso de fallo absoluto de dependencias
            from dataclasses import dataclass
            @dataclass
            class Jugador:
                nombre: str
                apellido: str
                posicion: str
                ataque: int
                defensa: int
                fisico: int
                tecnica: int
                mental: int
                moral: int = 70
                lesion_partidos: int = 0
                @property
                def overall(self): return (self.ataque + self.defensa + self.fisico + self.tecnica + self.mental) // 5
                @property
                def nombre_completo(self): return f"{self.nombre} {self.apellido}"
            @dataclass
            class Equipo:
                nombre: str
                ciudad: str
                estrellas: float
                estilo_dt: str
                balance: int
                jugadores: list
            @dataclass
            class Liga:
                nombre: str
                tipo: str
                equipos: list
                num_jornadas: int

        # Generamos equipos y liga de fallback de manera segura
        try:
            mock_equipos = [
                Equipo(nombre="Millonarios F.C.", ciudad="Bogotá", estrellas=3.5, estilo_dt="Posesión", balance=12000000, jugadores=[]),
                Equipo(nombre="Atlético Nacional", ciudad="Medellín", estrellas=4.0, estilo_dt="Ofensivo", balance=15000000, jugadores=[]),
                Equipo(nombre="Junior de Barranquilla", ciudad="Barranquilla", estrellas=3.5, estilo_dt="Contraataque", balance=18000000, jugadores=[]),
                Equipo(nombre="América de Cali", ciudad="Cali", estrellas=3.5, estilo_dt="Presión Alta", balance=10000000, jugadores=[])
            ]
            return Liga(nombre=f"Liga Ficticia {league_id.upper()}", tipo=league_id, equipos=mock_equipos, num_jornadas=6)
        except Exception as e_build:
            logger.critical(f"Fallo crítico al construir liga fallback: {e_build}")
            return None


def _dibujar_balon_decorativo(screen: pygame.Surface, cx: int, cy: int, radio: int, angulo: float):
    """
    Dibuja un balón de fútbol alegre dinámicamente usando comandos de dibujo de Pygame.
    El balón se compone de un círculo blanco y pentágonos internos orientados según el ángulo.
    """
    try:
        # Dibujar círculo exterior blanco con borde negro
        pygame.draw.circle(screen, (255, 255, 255), (cx, cy), radio)
        pygame.draw.circle(screen, (10, 14, 26), (cx, cy), radio, width=2)
        
        # Pentágono central
        largo_pent = radio * 0.35
        puntos_pent = []
        for i in range(5):
            ang = i * 2 * math.pi / 5 + angulo
            x = cx + int(largo_pent * math.cos(ang))
            y = cy + int(largo_pent * math.sin(ang))
            puntos_pent.append((x, y))
        
        try:
            pygame.draw.polygon(screen, (20, 26, 46), puntos_pent)
        except Exception:
            # Fallback si falla el polígono
            pass
        
        # Conectar vértices centrales a la periferia y dibujar gajos externos
        for i in range(5):
            x_centro, y_centro = puntos_pent[i]
            # Dirección radial
            ang_per = i * 2 * math.pi / 5 + angulo
            x_per = cx + int(radio * math.cos(ang_per))
            y_per = cy + int(radio * math.sin(ang_per))
            pygame.draw.line(screen, (10, 14, 26), (x_centro, y_centro), (x_per, y_per), 2)
            
            # Dibujar pequeños triángulos en la periferia para simular los gajos del balón
            ang_der = ang_per + math.pi / 5
            x_der = cx + int(radio * math.cos(ang_der))
            y_der = cy + int(radio * math.sin(ang_der))
            
            ang_izq = ang_per - math.pi / 5
            x_izq = cx + int(radio * math.cos(ang_izq))
            y_izq = cy + int(radio * math.sin(ang_izq))
            
            # Líneas del gajo externo
            try:
                pygame.draw.polygon(screen, (10, 14, 26), [puntos_pent[i], (x_der, y_der), (x_izq, y_izq)], width=1)
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Error al dibujar balón decorativo: {e}")


def _dibujar_logo_fallback(screen: pygame.Surface, x: int, y: int):
    """
    Dibuja un logo dinámico y alegre directamente en pantalla con Pygame
    si no está disponible el archivo logo.png.
    """
    try:
        # Caja contenedora del logo (estilo mini campo de fútbol)
        ancho, alto = 400, 100
        rect_caja = pygame.Rect(x, y, ancho, alto)
        
        # Fondo verde césped y borde brillante con esquinas redondeadas
        try:
            pygame.draw.rect(screen, (15, 80, 45), rect_caja, border_radius=10)
            pygame.draw.rect(screen, COLORS.get('verde', (0, 255, 136)), rect_caja, width=3, border_radius=10)
        except TypeError:
            pygame.draw.rect(screen, (15, 80, 45), rect_caja)
            pygame.draw.rect(screen, COLORS.get('verde', (0, 255, 136)), rect_caja, width=3)
        
        # Líneas de campo de fútbol de adorno
        pygame.draw.line(screen, (255, 255, 255), (x + ancho // 2, y), (x + ancho // 2, y + alto), 2)
        try:
            pygame.draw.circle(screen, (255, 255, 255), (x + ancho // 2, y + alto // 2), 22, width=2)
        except Exception:
            pass
        
        # Balón animado en el centro
        _dibujar_balon_decorativo(screen, x + ancho // 2, y + alto // 2, 12, pygame.time.get_ticks() / 1000.0)
        
        # Textos a los lados
        font = get_font('lg')
        # Lado izquierdo
        texto_izq = font.render("ALPHA", True, COLORS.get('blanco', (255, 255, 255)))
        rect_izq = texto_izq.get_rect(center=(x + ancho // 4, y + alto // 2))
        screen.blit(texto_izq, rect_izq)
        
        # Lado derecho
        texto_der = font.render("FOOTBALL", True, COLORS.get('verde', (0, 255, 136)))
        rect_der = texto_der.get_rect(center=(x + 3 * ancho // 4, y + alto // 2))
        screen.blit(texto_der, rect_der)
        
    except Exception as e:
        logger.error(f"Error al dibujar logo fallback: {e}")
        # Dibujar un texto de respaldo básico si todo falla
        draw_text(screen, "ALPHA FOOTBALL", (x, y), size='xl', color='verde')


def _dibujar_logo_principal(screen: pygame.Surface, x: int, y: int, estado: dict):
    """
    Intenta cargar y dibujar el logotipo oficial en formato imagen PNG.
    Si el archivo no está en disco, delega en el renderizado vectorial de respaldo.
    """
    try:
        # Cachear en el estado para optimizar lecturas de disco
        if 'cached_logo' in estado:
            if estado['cached_logo'] is not None:
                screen.blit(estado['cached_logo'], (x, y))
                return
            else:
                _dibujar_logo_fallback(screen, x, y)
                return
                
        # Ruta de búsqueda de la imagen
        ruta_logo = os.path.join("alpha_football", "assets", "logo.png")
        
        if os.path.exists(ruta_logo):
            try:
                logo_img = pygame.image.load(ruta_logo).convert_alpha()
                # Escalar suavemente al tamaño de la interfaz a la izquierda (400x100)
                logo_img = pygame.transform.smoothscale(logo_img, (400, 100))
                estado['cached_logo'] = logo_img
                screen.blit(logo_img, (x, y))
                return
            except Exception as e_load:
                logger.error(f"Error cargando imagen del logo: {e_load}. Usando fallback.")
                estado['cached_logo'] = None
        else:
            logger.info("El archivo de logotipo no se encuentra en disco. Usando fallback vectorial.")
            estado['cached_logo'] = None
            
        _dibujar_logo_fallback(screen, x, y)
        
    except Exception as e:
        logger.error(f"Error general en _dibujar_logo_principal: {e}. Dibujando texto básico.")
        draw_text(screen, "ALPHA FOOTBALL", (x, y), size='xl', color='verde')


def _inicializar_y_dibujar_particulas(screen: pygame.Surface, estado: dict):
    """
    Actualiza y dibuja partículas alegres flotantes de fondo para ambientar el juego.
    Las partículas pueden ser balones pequeños, estrellas doradas o confeti multicolor.
    """
    try:
        # Inicializar partículas si no existen en el estado
        if 'particulas' not in estado or not estado['particulas']:
            particulas = []
            for _ in range(25):  # 25 partículas es un buen balance de rendimiento
                particulas.append({
                    'x': random.randint(0, SCREEN_W),
                    'y': random.randint(0, SCREEN_H),
                    'vx': random.uniform(-0.8, 0.8),
                    'vy': random.uniform(0.4, 1.2),  # Movimiento hacia abajo
                    'tipo': random.choice(['balon', 'estrella', 'confeti']),
                    'tamano': random.randint(8, 14),
                    'angulo': random.uniform(0, 360),
                    'rotacion': random.uniform(-1.5, 1.5),
                    'color': random.choice([COLORS['verde'], COLORS['azul'], COLORS['dorado'], COLORS['rojo']])
                })
            estado['particulas'] = particulas
            
        # Actualizar y dibujar cada partícula
        for p in estado['particulas']:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['angulo'] += p['rotacion']
            
            # Reposicionar si sale de la pantalla
            if p['y'] > SCREEN_H + 20:
                p['y'] = -20
                p['x'] = random.randint(0, SCREEN_W)
                p['vy'] = random.uniform(0.4, 1.2)
            if p['x'] < -20 or p['x'] > SCREEN_W + 20:
                p['x'] = random.randint(0, SCREEN_W)
                
            px, py = int(p['x']), int(p['y'])
            tam = p['tamano']
            
            if p['tipo'] == 'balon':
                # Dibujar un pequeño balón de fútbol
                pygame.draw.circle(screen, (255, 255, 255), (px, py), tam)
                pygame.draw.circle(screen, (10, 14, 26), (px, py), tam, width=1)
                for i in range(3):
                    rad = i * math.pi / 3 + p['angulo']
                    ex = px + int(tam * math.cos(rad))
                    ey = py + int(tam * math.sin(rad))
                    pygame.draw.line(screen, (10, 14, 26), (px, py), (ex, ey), 1)
            elif p['tipo'] == 'estrella':
                # Dibujar estrella de 5 puntas
                puntos = []
                for i in range(10):
                    r = tam if i % 2 == 0 else tam // 2
                    rad = i * math.pi / 5 + p['angulo']
                    puntos.append((px + r * math.cos(rad), py + r * math.sin(rad)))
                try:
                    pygame.draw.polygon(screen, p['color'], puntos)
                except Exception:
                    pass
            else:
                # Dibujar confeti rectangular
                ancho_c, alto_c = tam, tam // 2
                rad = p['angulo']
                cos_a, sin_a = math.cos(rad), math.sin(rad)
                puntos_rect = [
                    (px + int(-ancho_c*cos_a - -alto_c*sin_a), py + int(-ancho_c*sin_a + -alto_c*cos_a)),
                    (px + int(ancho_c*cos_a - -alto_c*sin_a), py + int(ancho_c*sin_a + -alto_c*cos_a)),
                    (px + int(ancho_c*cos_a - alto_c*sin_a), py + int(ancho_c*sin_a + alto_c*cos_a)),
                    (px + int(-ancho_c*cos_a - alto_c*sin_a), py + int(-ancho_c*sin_a + alto_c*cos_a))
                ]
                try:
                    pygame.draw.polygon(screen, p['color'], puntos_rect)
                except Exception:
                    pass
                
    except Exception as e:
        logger.error(f"Error al procesar partículas en el menú: {e}. Limpiando lista para evitar caídas.")
        estado['particulas'] = []


def _dibujar_fondo_futbol(screen: pygame.Surface):
    """
    Dibuja un fondo futbolístico alegre con bandas de césped verde alternantes y líneas de campo
    sobre el gradiente azul base para mantener una atmósfera de estadio premium.
    """
    try:
        # 1. Dibujar el gradiente azul base de fondo
        draw_gradient_bg(screen)
        
        # 2. Dibujar franjas de césped semi-transparentes
        ancho_franja = 80
        surf_patron = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        
        # Bandas verdes neón extremadamente sutiles
        for x in range(0, SCREEN_W, ancho_franja * 2):
            pygame.draw.rect(surf_patron, (0, 255, 136, 8), (x, 0, ancho_franja, SCREEN_H))
            
        # 3. Dibujar líneas de cal del campo de fútbol con brillo semi-transparente
        color_linea = (255, 255, 255, 20)
        
        # Línea de medio campo
        pygame.draw.line(surf_patron, color_linea, (SCREEN_W // 2, 0), (SCREEN_W // 2, SCREEN_H), 2)
        # Círculo central
        try:
            pygame.draw.circle(surf_patron, color_linea, (SCREEN_W // 2, SCREEN_H // 2), 160, width=2)
            pygame.draw.circle(surf_patron, color_linea, (SCREEN_W // 2, SCREEN_H // 2), 6)
        except Exception:
            pass
        
        # Área de portería izquierda (cerca de los menús alineados a la izquierda)
        try:
            pygame.draw.rect(surf_patron, color_linea, (-2, SCREEN_H // 2 - 200, 220, 400), width=2)
            pygame.draw.rect(surf_patron, color_linea, (-2, SCREEN_H // 2 - 100, 80, 200), width=2)
            pygame.draw.arc(surf_patron, color_linea, (120, SCREEN_H // 2 - 80, 200, 160), -math.pi/2, math.pi/2, width=2)
        except Exception:
            pass
        
        # Área de portería derecha
        try:
            pygame.draw.rect(surf_patron, color_linea, (SCREEN_W - 218, SCREEN_H // 2 - 200, 220, 400), width=2)
            pygame.draw.rect(surf_patron, color_linea, (SCREEN_W - 78, SCREEN_H // 2 - 100, 80, 200), width=2)
            pygame.draw.arc(surf_patron, color_linea, (SCREEN_W - 320, SCREEN_H // 2 - 80, 200, 160), math.pi/2, 3*math.pi/2, width=2)
        except Exception:
            pass
        
        screen.blit(surf_patron, (0, 0))
        
    except Exception as e:
        logger.error(f"Error al dibujar fondo de fútbol alegre: {e}. Usando color de fondo plano como fallback.")
        try:
            screen.fill(COLORS.get('bg', (10, 14, 26)))
        except Exception:
            pass


def _dibujar_boton_premium(screen: pygame.Surface, rect: pygame.Rect, texto: str, hover: bool) -> pygame.Rect:
    """
    Dibuja un botón interactivo elegante y premium con bordes redondeados y efectos interactivos.
    Si hay hover, el botón se desplaza ligeramente, el borde brilla en verde neón y aparece un balón alegre girando.
    """
    button_rect = pygame.Rect(rect)
    try:
        # Desplazamiento interactivo suave cuando hay hover
        if hover:
            dibujo_rect = pygame.Rect(button_rect.left + 8, button_rect.top, button_rect.width - 8, button_rect.height)
            bg_color = (25, 38, 70)          # Fondo azulado/verde brillante
            border_color = COLORS.get('verde', (0, 255, 136))   # Borde verde neón
            text_color = COLORS.get('verde', (0, 255, 136))     # Texto verde
        else:
            dibujo_rect = button_rect
            bg_color = COLORS.get('panel', (20, 26, 46))       # Fondo azul oscuro
            border_color = COLORS.get('azul', (0, 191, 255))    # Borde azul celeste
            text_color = COLORS.get('blanco', (255, 255, 255))  # Texto blanco
            
        # Dibujar sombra del botón para efecto tridimensional
        sombra_rect = pygame.Rect(dibujo_rect.left + 3, dibujo_rect.top + 3, dibujo_rect.width, dibujo_rect.height)
        try:
            pygame.draw.rect(screen, (5, 8, 15), sombra_rect, border_radius=8)
        except TypeError:
            pygame.draw.rect(screen, (5, 8, 15), sombra_rect)
            
        # Dibujar el cuerpo del botón
        try:
            pygame.draw.rect(screen, bg_color, dibujo_rect, border_radius=8)
            pygame.draw.rect(screen, border_color, dibujo_rect, width=2, border_radius=8)
        except TypeError:
            pygame.draw.rect(screen, bg_color, dibujo_rect)
            pygame.draw.rect(screen, border_color, dibujo_rect, width=2)
            
        # Dibujo del texto e iconos
        font = get_font('md')
        text_surf = font.render(texto, True, text_color)
        text_rect = text_surf.get_rect()
        
        if hover:
            # Dibujar el balón flotando y girando al lado del texto
            angulo_balon = pygame.time.get_ticks() / 200.0
            bx = dibujo_rect.left + 25
            by = dibujo_rect.centery
            _dibujar_balon_decorativo(screen, bx, by, 10, angulo_balon)
            # Centrar texto en el espacio restante del botón
            text_rect.center = (dibujo_rect.left + (dibujo_rect.width + 35) // 2, dibujo_rect.centery)
        else:
            text_rect.center = dibujo_rect.center
            
        screen.blit(text_surf, text_rect)
        
    except Exception as e:
        logger.error(f"Error en _dibujar_boton_premium para '{texto}': {e}. Usando fallback.")
        # Fallback a draw_button de theme.py
        try:
            draw_button(screen, rect, texto, hover)
        except Exception:
            pass
            
    return button_rect


def _dibujar_panel_derecho(screen: pygame.Surface, estado: dict):
    """
    Dibuja un panel informativo premium y alegre sobre el fútbol en el lado derecho de la pantalla
    para equilibrar visualmente el menú principal alineado a la izquierda.
    """
    try:
        panel_rect = pygame.Rect(640, 100, 520, 520)
        
        # Dibujar panel con esquinas redondeadas y brillo dual
        try:
            pygame.draw.rect(screen, (15, 22, 40, 200), panel_rect, border_radius=15) # Fondo semi-transparente
            pygame.draw.rect(screen, COLORS.get('azul', (0, 191, 255)), panel_rect, width=2, border_radius=15) # Borde exterior
            
            borde_interno = pygame.Rect(panel_rect.left + 4, panel_rect.top + 4, panel_rect.width - 8, panel_rect.height - 8)
            pygame.draw.rect(screen, (0, 255, 136, 40), borde_interno, width=1, border_radius=12)
        except TypeError:
            pygame.draw.rect(screen, COLORS.get('panel', (20, 26, 46)), panel_rect)
            pygame.draw.rect(screen, COLORS.get('azul', (0, 191, 255)), panel_rect, width=2)

        # Frases de fútbol alegres y tácticas
        frases = [
            "¡El fútbol se juega con la mente, pero se siente con el corazón!",
            "¡Diseña la táctica perfecta, domina el mediocampo y alcanza la copa!",
            "¡El verdadero estratega ve el espacio donde otros solo ven rivales!",
            "¡Precios reales en el mercado! Ficha con inteligencia y cabeza.",
            "¡Las copas internacionales te esperan para escribir tu nombre en la gloria!",
            "¡Alinea tu equipo con alegría y entrena a las futuras estrellas mundiales!",
            "¡El grito de gol es el idioma universal de la alegría táctica!"
        ]
        
        # Elegir frase basándose en los ticks de pygame
        indice_frase = (pygame.time.get_ticks() // 8000) % len(frases)
        frase_actual = frases[indice_frase]
        
        # Dibujar título del panel
        draw_text(screen, "DIARIO DE ESTRATEGIA", (670, 130), size='lg', color='verde')
        
        # Dibujar gran balón de fútbol alegre en el centro del panel con levitación suave
        levitacion = int(10 * math.sin(pygame.time.get_ticks() / 500.0))
        cx, cy = 900, 310 + levitacion
        angulo_giro = pygame.time.get_ticks() / 1000.0
        
        # Sombra del balón
        try:
            pygame.draw.ellipse(screen, (5, 8, 15), (cx - 60, 410, 120, 20))
        except Exception:
            pass
        
        # Balón principal
        _dibujar_balon_decorativo(screen, cx, cy, 70, angulo_giro)
        
        # Dibujar la frase motivadora envuelta
        font_sm = get_font('sm')
        
        # Envoltura de texto
        palabras = frase_actual.split(' ')
        lineas = []
        linea_actual = ""
        for palabra in palabras:
            test_linea = linea_actual + palabra + " "
            if font_sm.size(test_linea)[0] > 440:
                lineas.append(linea_actual.strip())
                linea_actual = palabra + " "
            else:
                linea_actual = test_linea
        if linea_actual:
            lineas.append(linea_actual.strip())
            
        # Dibujar líneas de texto
        y_texto = 450
        for linea in lineas:
            text_surf = font_sm.render(linea, True, COLORS.get('blanco', (255, 255, 255)))
            text_rect = text_surf.get_rect(center=(900, y_texto))
            screen.blit(text_surf, text_rect)
            y_texto += 22
            
    except Exception as e:
        logger.error(f"Error al dibujar panel derecho decorativo: {e}")


def _dibujar_estrellas_prestigio(screen: pygame.Surface, x: int, y: int, estrellas_count: float, estado: dict):
    """
    Dibuja el prestigio del equipo usando las imágenes de estrellas de st-1,
    o cae a caracteres dorados si los assets no están disponibles.
    """
    try:
        # Carga perezosa de imágenes de estrella en el estado
        if 'star_active' not in estado:
            import os
            ruta_act = os.path.join("alpha_football", "assets", "star_active.png")
            ruta_inact = os.path.join("alpha_football", "assets", "star_inactive.png")
            
            estado['star_active'] = None
            estado['star_inactive'] = None
            
            if os.path.exists(ruta_act):
                try:
                    estado['star_active'] = pygame.image.load(ruta_act).convert_alpha()
                except Exception:
                    pass
            if os.path.exists(ruta_inact):
                try:
                    estado['star_inactive'] = pygame.image.load(ruta_inact).convert_alpha()
                except Exception:
                    pass
                    
        img_act = estado.get('star_active')
        img_inact = estado.get('star_inactive')
        
        # Dibujar las estrellas
        if img_act and img_inact:
            pos_x = x
            for i in range(5):
                # Decidir si la estrella se muestra activa
                if i < estrellas_count:
                    screen.blit(img_act, (pos_x, y))
                else:
                    screen.blit(img_inact, (pos_x, y))
                pos_x += 36
        else:
            # Fallback a caracteres unicode dorados "★"
            stars_int = int(estrellas_count)
            stars_str = "★" * stars_int
            if estrellas_count % 1 >= 0.5:
                stars_str += "½"
            stars_str += "☆" * (5 - len(stars_str))
            draw_text(screen, stars_str, (x, y), size='md', color='dorado')
            
    except Exception as e:
        logger.error(f"Error al dibujar estrellas de prestigio: {e}")


def render(screen: pygame.Surface, estado: dict) -> str | None:
    """
    Dibuja la pantalla del menú y gestiona los clics e interacciones del usuario.
    Retorna la acción elegida (por ejemplo, 'league_screen') o None si permanece en el menú.
    """
    # 1. Inicialización y validación del paso actual del menú
    if 'menu_step' not in estado:
        estado['menu_step'] = 'main'
        
    # Inicialización del audio si no se ha iniciado
    if not estado.get('music_started', False):
        try:
            from alpha_football import audio
            try:
                audio.init_audio()
            except Exception as e_init:
                logger.warning(f"No se pudo inicializar sistema de audio: {e_init}")
            try:
                audio.start_music()
                estado['music_started'] = True
            except Exception as e_start:
                logger.warning(f"No se pudo reproducir música de fondo: {e_start}")
        except Exception as e_import:
            logger.debug(f"Módulo de audio no disponible para el menú: {e_import}")

    # 2. Captura segura de posición de ratón y clics del frame actual
    mouse_pos = pygame.mouse.get_pos()
    click_pos = None
    
    try:
        # Extraemos eventos del cache (manejado por el orquestador principal main.py)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # Re-postear para que main.py actúe ante el quit
                pygame.event.post(event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Clic izquierdo
                    click_pos = event.pos
    except Exception as e_events:
        logger.error(f"Error al procesar eventos en render de menú: {e_events}")

    # 3. Dibujar fondo de fútbol y partículas alegres
    _dibujar_fondo_futbol(screen)
    _inicializar_y_dibujar_particulas(screen, estado)

    # --- PANTALLA PRINCIPAL DEL MENÚ (ALINEADO A LA IZQUIERDA) ---
    if estado['menu_step'] == 'main':
        # Dibujar logo y eslogan alineados a la izquierda
        _dibujar_logo_principal(screen, 100, 100, estado)
        draw_text(screen, "La revolución táctica pixelada", (100, 215), size='sm', color='azul')

        # Rectángulos de los botones principales alineados a la izquierda
        btn_nueva_rect = pygame.Rect(100, 280, 320, 55)
        btn_cargar_rect = pygame.Rect(100, 355, 320, 55)
        btn_salir_rect = pygame.Rect(100, 430, 320, 55)

        # Hover states
        hover_nueva = btn_nueva_rect.collidepoint(mouse_pos)
        hover_cargar = btn_cargar_rect.collidepoint(mouse_pos)
        hover_salir = btn_salir_rect.collidepoint(mouse_pos)

        # Dibujar botones premium
        _dibujar_boton_premium(screen, btn_nueva_rect, "NUEVA PARTIDA", hover_nueva)
        _dibujar_boton_premium(screen, btn_cargar_rect, "CARGAR PARTIDA", hover_cargar)
        _dibujar_boton_premium(screen, btn_salir_rect, "SALIR", hover_salir)

        # Dibujar panel de ambientación a la derecha
        _dibujar_panel_derecho(screen, estado)

        # Lógica de clics
        if click_pos:
            if btn_nueva_rect.collidepoint(click_pos):
                estado['menu_step'] = 'select_league'
            elif btn_cargar_rect.collidepoint(click_pos):
                try:
                    from alpha_football.save import cargar_partida
                    loaded = cargar_partida()
                    if loaded:
                        liga = loaded.ligas[0] if loaded.ligas else None
                        mi_equipo = None
                        if liga and loaded.equipo_usuario_id:
                            for eq in liga.equipos:
                                if eq.id == loaded.equipo_usuario_id:
                                    mi_equipo = eq
                                    break
                        estado.clear()
                        estado['liga'] = liga
                        estado['mi_equipo'] = mi_equipo
                        estado['equipos'] = liga.equipos if liga else []
                        estado['temporada'] = loaded.temporada
                        estado['jornada'] = liga.jornada_actual if liga else 1
                        estado['copas'] = loaded.copas
                        estado['transfer_log'] = loaded.historial
                        
                        # Cargar alineación activa guardada o generar la por defecto
                        if loaded.alineacion_activa:
                            estado['alineacion_activa'] = loaded.alineacion_activa
                            if mi_equipo:
                                mi_equipo.alineacion_activa = loaded.alineacion_activa
                        elif mi_equipo:
                            from alpha_football.models import alineacion_por_defecto
                            def_alin = alineacion_por_defecto(mi_equipo)
                            estado['alineacion_activa'] = def_alin
                            mi_equipo.alineacion_activa = def_alin

                        estado['current_screen'] = "league_screen"
                        return "league_screen"
                    else:
                        estado['menu_error'] = "No hay partida guardada."
                        estado['menu_error_ticks'] = pygame.time.get_ticks()
                except Exception as e_load:
                    logger.error(f"Error al cargar partida desde el menú: {e_load}")
                    estado['menu_error'] = "Error al leer archivo."
                    estado['menu_error_ticks'] = pygame.time.get_ticks()
            elif btn_salir_rect.collidepoint(click_pos):
                pygame.event.post(pygame.event.Event(pygame.QUIT))

        # Render de errores temporales
        if 'menu_error' in estado:
            if pygame.time.get_ticks() - estado.get('menu_error_ticks', 0) > 3000:
                estado.pop('menu_error', None)
                estado.pop('menu_error_ticks', None)
            else:
                draw_text(screen, estado['menu_error'], (100, 505), size='md', color='rojo')

    # --- SELECCIÓN DE LIGA (ALINEADO A LA IZQUIERDA) ---
    elif estado['menu_step'] == 'select_league':
        # Mostrar cabecera del logo y título alineados a la izquierda
        _dibujar_logo_principal(screen, 100, 80, estado)
        draw_text(screen, "SELECCIONA UNA LIGA", (100, 195), size='lg', color='verde')

        start_y = 250
        btn_w, btn_h = 400, 52
        spacing_y = 12
        
        volver_rect = pygame.Rect(100, 600, 200, 50)
        hover_volver = volver_rect.collidepoint(mouse_pos)

        # Dibujar las ligas
        for i, liga_data in enumerate(LIGAS_DISPONIBLES):
            btn_rect = pygame.Rect(100, start_y + i * (btn_h + spacing_y), btn_w, btn_h)
            hover_liga = btn_rect.collidepoint(mouse_pos)
            _dibujar_boton_premium(screen, btn_rect, liga_data['name'], hover_liga)

            if click_pos and btn_rect.collidepoint(click_pos):
                estado['selected_league_id'] = liga_data['id']
                liga_obj = load_league_teams(liga_data['id'])
                if liga_obj:
                    estado['selected_liga_obj'] = liga_obj
                    estado['menu_step'] = 'select_team'
                else:
                    estado['menu_error'] = "Error al inicializar liga."
                    estado['menu_error_ticks'] = pygame.time.get_ticks()

        # Botón Volver
        _dibujar_boton_premium(screen, volver_rect, "VOLVER", hover_volver)
        if click_pos and volver_rect.collidepoint(click_pos):
            estado['menu_step'] = 'main'

        # Panel de ambientación a la derecha para consistencia
        _dibujar_panel_derecho(screen, estado)

        # Mostrar error si existe
        if 'menu_error' in estado:
            if pygame.time.get_ticks() - estado.get('menu_error_ticks', 0) > 3000:
                estado.pop('menu_error', None)
                estado.pop('menu_error_ticks', None)
            else:
                draw_text(screen, estado['menu_error'], (100, 570), size='sm', color='rojo')

    # --- SELECCIÓN DE EQUIPO ---
    elif estado['menu_step'] == 'select_team':
        # Cabecera de logo y título alineados a la izquierda
        _dibujar_logo_principal(screen, 100, 50, estado)
        draw_text(screen, "SELECCIONA TU EQUIPO", (100, 160), size='lg', color='verde')

        # Cargar equipos de la liga activa
        equipos = []
        if 'selected_liga_obj' in estado and estado['selected_liga_obj']:
            equipos = estado['selected_liga_obj'].equipos

        # Coordenadas del grid de equipos (2 columnas a la izquierda)
        grid_x = 100
        grid_y = 220
        col_w = 300
        row_h = 50
        spacing_x = 30
        spacing_y = 15

        hovered_team = None

        # Renderizar cada botón de equipo
        for i, equipo in enumerate(equipos):
            col = i % 2
            row = i // 2
            bx = grid_x + col * (col_w + spacing_x)
            by = grid_y + row * (row_h + spacing_y)
            
            btn_rect = pygame.Rect(bx, by, col_w, row_h)
            hover_eq = btn_rect.collidepoint(mouse_pos)
            
            if hover_eq:
                hovered_team = equipo

            _dibujar_boton_premium(screen, btn_rect, equipo.nombre, hover_eq)

            if click_pos and btn_rect.collidepoint(click_pos):
                try:
                    estado['liga'] = estado['selected_liga_obj']
                    estado['mi_equipo'] = equipo
                    estado['equipos'] = estado['selected_liga_obj'].equipos
                    estado['temporada'] = 1
                    estado['jornada'] = 1
                    estado['historial'] = []
                    estado['dt_nombre'] = "DT Parodia"
                    
                    # Generar alineación activa por defecto para el nuevo equipo
                    from alpha_football.models import alineacion_por_defecto
                    def_alin = alineacion_por_defecto(equipo)
                    estado['alineacion_activa'] = def_alin
                    equipo.alineacion_activa = def_alin

                    estado['current_screen'] = "league_screen"

                    # Limpieza de variables temporales del menú
                    estado.pop('menu_step', None)
                    estado.pop('selected_league_id', None)
                    estado.pop('selected_liga_obj', None)
                    
                    return "league_screen"
                except Exception as e_select:
                    logger.critical(f"Error al asignar equipo y liga elegida: {e_select}")

        # Panel de detalles en la derecha
        panel_rect = pygame.Rect(760, 220, 420, 380)
        draw_panel(screen, panel_rect)

        if hovered_team:
            # Detalles del equipo sobre el que está el mouse
            draw_text(screen, hovered_team.nombre, (780, 240), size='lg', color='verde')
            draw_text(screen, f"Ciudad: {hovered_team.ciudad}", (780, 295), size='md', color='blanco')
            
            # Dibujar estrellas de prestigio (usando assets o fallback)
            draw_text(screen, "Prestigio: ", (780, 335), size='md', color='blanco')
            _dibujar_estrellas_prestigio(screen, 880, 330, hovered_team.estrellas, estado)
            
            draw_text(screen, f"Estilo de Juego: {hovered_team.estilo_dt}", (780, 375), size='md', color='azul')
            draw_text(screen, f"Presupuesto: ${hovered_team.balance:,}", (780, 415), size='md', color='verde')
            
            # Mostrar primer jugador estrella disponible
            if hasattr(hovered_team, 'jugadores') and hovered_team.jugadores:
                try:
                    estrella = max(hovered_team.jugadores, key=lambda j: getattr(j, 'overall', 70))
                    draw_text(screen, f"Estrella: {estrella.nombre_completo} (OVR {getattr(estrella, 'overall', 70)})", (780, 465), size='sm', color='dorado')
                except Exception:
                    pass
        else:
            # Texto informativo predeterminado
            draw_text(screen, "INFORMACIÓN DEL CLUB", (780, 240), size='lg', color='azul')
            draw_text(screen, "Pasa el mouse sobre", (780, 300), size='md', color='blanco')
            draw_text(screen, "un equipo para ver sus", (780, 340), size='md', color='blanco')
            draw_text(screen, "estadísticas detalladas.", (780, 380), size='md', color='blanco')

        # Botón Volver
        volver_rect = pygame.Rect(grid_x, 590, 180, 48)
        hover_vol = volver_rect.collidepoint(mouse_pos)
        _dibujar_boton_premium(screen, volver_rect, "VOLVER", hover_vol)
        if click_pos and volver_rect.collidepoint(click_pos):
            estado['menu_step'] = 'select_league'

    return None
