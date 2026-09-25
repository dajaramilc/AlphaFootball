# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Hub de carrera (Pygame)
v2.4.0: columnas arriba (INICIO, DIRECCIÓN, NEGOCIACIONES, OFICINA, OPCIONES, GUARDAR).
INICIO es el tablero (JUGAR, tabla, jornada, tu club); las demás muestran tarjetas.
También contiene el fixture de la liga y la simulación de las ligas de fondo.
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


def _ligas_de_fondo(estado: dict) -> list:
    """v2.3.5: ligas que avanzan en background: las 1ª y 2ª de los 5 países.
    Nunca incluye la liga del user (esa la juega él)."""
    liga_user = estado.get('liga')
    ligas = (list((estado.get('primera_division') or {}).values())
             + list((estado.get('segunda_division') or {}).values()))
    return [l for l in ligas if l is not None and l is not liga_user
            and len(getattr(l, 'equipos', []) or []) >= 2]


def _desarrollar_equipo_fondo(engine, equipo, gf: int, gc: int, stats: Optional[dict] = None) -> None:
    """Desarrollo post-partido de un equipo de fondo con el mismo once que usó el motor.
    v4.0.0: `stats` = partido_ctx.stats_de_equipo (quiénes jugaron, goles y notas reales)."""
    try:
        from alpha_football.desarrollo import desarrollar_plantilla_post_partido
        if stats is not None:
            desarrollar_plantilla_post_partido(equipo, gf, gc, stats_partido=stats)
            return
        pos = {id(j): i for i, j in enumerate(equipo.jugadores)}
        jugaron = [pos[id(j)] for j in engine._once_titular(equipo) if id(j) in pos]
        desarrollar_plantilla_post_partido(equipo, gf, gc, jugaron or None)
    except Exception as e_dev:
        logger.error(f"Error en desarrollo de fondo de {getattr(equipo, 'nombre', '?')}: {e_dev}")


def _simular_jornada_liga_fondo(liga_b) -> bool:
    """Simula la jornada actual de una liga de fondo. Retorna False si ya terminó."""
    from alpha_football import engine  # import perezoso para evitar ciclos

    if not getattr(liga_b, 'calendario', None):
        inicializar_calendario_liga(liga_b)
    pendientes = [p for p in liga_b.calendario if not p.jugado]
    if not pendientes:
        return False
    jornada = min(p.jornada for p in pendientes)
    for p in pendientes:
        if p.jornada != jornada:
            continue
        local = next((e for e in liga_b.equipos if e.id == p.local_id), None)
        visitante = next((e for e in liga_b.equipos if e.id == p.visitante_id), None)
        if not local or not visitante:
            p.jugado = True  # equipo ya no está en la liga: no bloquear el calendario
            continue
        try:
            res = engine.simular_partido(local, visitante)
            p.goles_local = res.goles_local
            p.goles_visitante = res.goles_visitante
            p.jugado = True
            p.ganador_id = (local.id if res.goles_local > res.goles_visitante
                            else visitante.id if res.goles_visitante > res.goles_local else None)
            local.gf += res.goles_local
            local.gc += res.goles_visitante
            visitante.gf += res.goles_visitante
            visitante.gc += res.goles_local
            local.pj += 1
            visitante.pj += 1
            if res.goles_local > res.goles_visitante:
                local.puntos += 3
                local.pg += 1
                visitante.pp += 1
            elif res.goles_local < res.goles_visitante:
                visitante.puntos += 3
                visitante.pg += 1
                local.pp += 1
            else:
                local.puntos += 1
                visitante.puntos += 1
                local.pe += 1
                visitante.pe += 1
            # v2.3.6: en las ligas de fondo los jugadores también suben/bajan partido a
            # partido (antes solo en la liga del user) y acumulan goles/notas (Balón de Oro).
            from alpha_football.partido_ctx import stats_de_equipo
            _desarrollar_equipo_fondo(engine, local, res.goles_local, res.goles_visitante,
                                      stats_de_equipo(res.ctx, res.notas, 'l'))
            _desarrollar_equipo_fondo(engine, visitante, res.goles_visitante, res.goles_local,
                                      stats_de_equipo(res.ctx, res.notas, 'v'))
        except Exception as e_match:
            p.jugado = True
            logger.error(f"Error simulando partido de fondo {liga_b.nombre} j{jornada}: {e_match}")
    liga_b.jornada_actual = min(jornada + 1, getattr(liga_b, 'num_jornadas', jornada + 1))
    return True


def simular_jornada_segunda_division(estado: dict) -> None:
    """
    v2.3 (Fase 7) / v2.3.5: avanza UNA jornada de cada liga de fondo (2ª divisiones y,
    si el user está en 2ª, la 1ª de su país) al terminar cada jornada del usuario.
    """
    for liga_b in _ligas_de_fondo(estado):
        try:
            _simular_jornada_liga_fondo(liga_b)
        except Exception as e_liga:
            logger.error(f"Error en simulación de fondo de {getattr(liga_b, 'nombre', '?')}: {e_liga}")


def completar_ligas_de_fondo(estado: dict) -> None:
    """v2.3.5: al cerrar la temporada, juega lo que falte de cada liga de fondo para que
    el ascenso/descenso se decida con la tabla final (las ligas tienen distinto largo)."""
    for liga_b in _ligas_de_fondo(estado):
        try:
            for _ in range(200):  # tope de seguridad
                if not _simular_jornada_liga_fondo(liga_b):
                    break
        except Exception as e_liga:
            logger.error(f"Error completando liga de fondo {getattr(liga_b, 'nombre', '?')}: {e_liga}")


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

# --- Hub por columnas (v2.4.0) ═══════════════════════════════════════════════

# (clave, línea 1, línea 2, color de acento). Las 5 primeras son pestañas con contenido;
# OPCIONES y GUARDAR abren su pantalla directo.
BARRA_MENU = [
    ('inicio',        "INICIO",    "",        'verde'),
    ('direccion',     "DIRECCIÓN", "EQUIPO",  'azul'),
    ('negociaciones', "NEGOCIA-",  "CIONES",  'dorado'),
    ('oficina',       "OFICINA",   "",        'azul'),
    ('finanzas',      "FINANZAS",  "",        'verde'),
    ('opciones',      "OPCIONES",  "",        'verde'),
]   # v4.2.0: GUARDAR vive dentro de OPCIONES (en carrera)
PESTANAS = [item[0] for item in BARRA_MENU[:5]]
DESTINO_DIRECTO = {'opciones': 'options_screen'}
TITULOS = {'direccion': "DIRECCIÓN DE EQUIPO", 'negociaciones': "NEGOCIACIONES", 'oficina': "OFICINA",
           'finanzas': "FINANZAS"}

# Tarjetas de cada pestaña: (título, subtítulo, pantalla destino). Las de sub-proyectos
# futuros se agregan cuando existan.
TARJETAS = {
    'direccion': [
        ("FORMACIÓN", "Once, banco, formación y táctica", 'team_screen'),
        ("PLANTILLA", "Todos tus jugadores, ficha y transferibles", 'plantilla_screen'),
    ],
    'negociaciones': [
        ("NEGOCIAR", "Buscador de jugadores de las 10 ligas", 'buscador_screen'),
        ("OFERTAS", "Ofertas recibidas por tus jugadores", 'ofertas_screen'),
        ("HISTORIAL", "Pases de todas las ligas y los tuyos", 'historial_pases_screen'),
        ("OJEADOR", "3 fichajes recomendados por ventana", 'ojeador_screen'),
    ],
    'oficina': [
        ("CORREO", "Mensajes de la directiva, jugadores y clubes", 'correo_screen'),   # v3.1.0
        ("ESTADÍSTICAS", "Goleadores, asistencias, vallas", 'stats_screen'),
        ("COPA INTERNACIONAL", "Grupos, llaves y estadísticas", 'copa_screen'),
        ("HISTORIAL DE CARRERA", "Tus temporadas y títulos", 'career_screen'),
        ("OTRAS LIGAS", "Las 10 ligas en vivo", 'otras_ligas_screen'),
        ("OBJETIVOS", "Lo que exige la directiva y su confianza", 'objetivos_screen'),
        ("MI CONTRATO", "Sueldo, años, patrimonio y renovación", 'contrato_dt_screen'),   # v3.2.0
        ("OFERTAS DT", "Clubes que te quieren como DT", 'ofertas_dt_screen'),   # v3.4.0
    ],
    'finanzas': [
        ("RESUMEN", "Ingresos, gastos, masa salarial y saldo", 'finanzas_screen'),
        ("CONTRATOS", "Salarios, vencimientos y renovaciones", 'contratos'),
    ],
}

# Layout de Inicio
R_TABLA = pygame.Rect(16, 106, 640, 400)
R_HIST = pygame.Rect(16, 516, 640, 180)       # v3.6.0: termina en y=696 (barra de atajos)
R_JUGAR = pygame.Rect(672, 106, 592, 96)
Y_AVISOS = 210
R_JORNADA = pygame.Rect(672, 296, 592, 252)
R_CLUB = pygame.Rect(672, 558, 592, 138)       # v3.6.0: termina en y=696
PARTIDOS_VISIBLES = 6

# v3.6.0: diálogo de salida (ESC en INICIO) y pantallas tras las que el foco vuelve a JUGAR
R_DIALOGO_SALIR = pygame.Rect(290, 250, 700, 230)
R_SALIR_GUARDAR = pygame.Rect(312, 380, 236, 56)
R_SALIR_SIN = pygame.Rect(560, 380, 236, 56)
R_SALIR_CANCELAR = pygame.Rect(808, 380, 160, 56)
VUELVEN_A_JUGAR = ('copa_screen', 'match_screen', 'prepartido_screen')


def _manejar_dialogo_salir(estado, key_events, click_pos) -> Optional[str]:
    """v3.6.0: GUARDAR Y SALIR (Enter) / SALIR SIN GUARDAR (S) / CANCELAR (Esc). Devuelve el destino."""
    accion = None
    for ev in key_events:
        if ev.key == pygame.K_ESCAPE:
            accion = 'cancelar'
        elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            accion = 'guardar'
        elif ev.key == pygame.K_s:
            accion = 'sin'
        if accion:
            break
    if accion is None and click_pos:
        for rect, acc in ((R_SALIR_GUARDAR, 'guardar'), (R_SALIR_SIN, 'sin'), (R_SALIR_CANCELAR, 'cancelar')):
            if rect.collidepoint(click_pos):
                accion = acc
    if accion is None:
        return None
    estado['dialogo_salir'] = False
    if accion == 'sin':
        return 'menu'
    if accion == 'guardar':
        slot = estado.get('slot_activo')
        if not slot:                                   # sin slot: se elige uno y luego se sale
            estado['salir_tras_guardar'] = True
            estado['save_slots_return'] = 'league_screen'
            return 'save_slots_screen'
        try:
            from alpha_football.ui.save_slots_screen import guardar_slot
            guardar_slot(estado, slot)
            return 'menu'
        except Exception as e_save:
            logger.error(f"No se pudo guardar al salir (slot {slot}): {e_save}", exc_info=True)
            _toast(estado, "No se pudo guardar la partida", color='rojo')
    return None


def _dibujar_dialogo_salir(screen, mouse_pos) -> None:
    """v3.6.0: velo + panel con las 3 opciones de salida."""
    velo = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    velo.fill((0, 0, 0, 170))
    screen.blit(velo, (0, 0))
    draw_panel(screen, R_DIALOGO_SALIR)
    pygame.draw.rect(screen, COLORS.get('dorado', (255, 215, 0)), R_DIALOGO_SALIR, width=2, border_radius=8)
    draw_text(screen, "¿SALIR AL MENÚ PRINCIPAL?", (R_DIALOGO_SALIR.x + 24, R_DIALOGO_SALIR.y + 22),
              size='lg', color='dorado')
    draw_text(screen, "Lo que no guardes se pierde (el autoguardado solo corre al cerrar el juego).",
              (R_DIALOGO_SALIR.x + 24, R_DIALOGO_SALIR.y + 70), size='sm', color='blanco')
    for rect, texto, tecla in ((R_SALIR_GUARDAR, "GUARDAR Y SALIR", "Enter"),
                               (R_SALIR_SIN, "SALIR SIN GUARDAR", "S"), (R_SALIR_CANCELAR, "CANCELAR", "Esc")):
        draw_button(screen, rect, texto, rect.collidepoint(mouse_pos))
        s = get_font('sm').render(tecla, True, COLORS.get('azul', (0, 191, 255)))
        screen.blit(s, s.get_rect(center=(rect.centerx, rect.bottom + 14)))


R_SOBRE = pygame.Rect(SCREEN_W - 16 - 62, 20, 62, 52)   # v4.2.0: sobre de correo arriba a la derecha


def texto_badge(n: int):
    """v4.2.0: número del círculo rojo del sobre (None si no hay no leídos)."""
    return None if n <= 0 else ('9+' if n > 9 else str(n))


def dibujar_sobre(screen, rect, n: int, hover: bool) -> None:
    """v4.2.0: sobre dibujado (la fuente no tiene emojis) con los no leídos en un círculo rojo."""
    try:
        cuerpo = pygame.Rect(rect.x + 6, rect.y + 12, rect.width - 16, rect.height - 20)
        pygame.draw.rect(screen, (30, 45, 75) if hover else (20, 26, 46), cuerpo, border_radius=4)
        borde = COLORS.get('verde' if hover else 'azul', (0, 191, 255))
        pygame.draw.rect(screen, borde, cuerpo, width=2, border_radius=4)
        pygame.draw.lines(screen, borde, False, [cuerpo.topleft, cuerpo.center, cuerpo.topright], 2)
        txt = texto_badge(n)
        if txt:
            c = (cuerpo.right - 2, cuerpo.top - 2)
            pygame.draw.circle(screen, (230, 40, 40), c, 12)
            s = get_font('sm').render(txt, True, (255, 255, 255))
            screen.blit(s, s.get_rect(center=c))
    except Exception as e:
        logger.error(f"No se pudo dibujar el sobre de correo: {e}")


def _rects_barra() -> list:
    """Reparte las columnas de la barra superior a todo lo ancho (v4.2.0: deja lugar al sobre)."""
    margen, gap, alto, y = 16, 6, 56, 18
    reserva = R_SOBRE.width + 10
    ancho = (SCREEN_W - 2 * margen - reserva - gap * (len(BARRA_MENU) - 1)) // len(BARRA_MENU)
    return [pygame.Rect(margen + i * (ancho + gap), y, ancho, alto) for i in range(len(BARRA_MENU))]


def _boton_barra(screen, rect, linea1, linea2, hover, color, enabled=True, foco=False):
    """Botón de la barra superior con texto en 1 o 2 líneas centradas."""
    draw_styled_button(screen, rect, "", hover or foco, color, enabled)
    if foco:
        pygame.draw.rect(screen, COLORS.get('dorado', (255, 215, 0)), rect, width=3, border_radius=8)
    if not enabled:
        txt_color = (110, 110, 120)
    elif hover or foco:
        txt_color = color
    else:
        txt_color = COLORS.get('blanco', (255, 255, 255))
    font = get_font('sm')
    lineas = [l for l in (linea1, linea2) if l]
    alto_total = len(lineas) * 20
    for i, texto in enumerate(lineas):
        surf = font.render(texto, True, txt_color)
        screen.blit(surf, surf.get_rect(center=(rect.centerx, rect.centery - alto_total // 2 + 10 + i * 20)))


def _rects_tarjetas(n: int) -> list:
    """Grilla de 2 columnas centrada para las tarjetas de una pestaña."""
    w, h, gap, cols, y0 = 440, 150, 28, 2, 170
    if n > 6:       # v3.2.0: 4 filas (OFICINA) → tarjetas más bajas para que quepan en 720
        h, gap = 120, 16
    x0 = (SCREEN_W - (cols * w + (cols - 1) * gap)) // 2
    return [pygame.Rect(x0 + (i % cols) * (w + gap), y0 + (i // cols) * (h + gap), w, h) for i in range(n)]


def _rects_jornada() -> tuple:
    """Botones < > del panel de jornada de Inicio."""
    prev = pygame.Rect(R_JORNADA.right - 92, R_JORNADA.y + 8, 36, 28)
    nxt = pygame.Rect(R_JORNADA.right - 48, R_JORNADA.y + 8, 36, 28)
    return prev, nxt


def partidos_historial(estado: dict) -> list:
    """
    v4.3.0: tus partidos de la temporada, liga y copa, del más reciente al más viejo:
    {'orden': (jornada, 0 liga | 1 copa), 'etiqueta': 'J5' | 'UCL' | 'LIB', 'local', 'visitante',
    'gl', 'gv', 'es_local', 'penales'}. La copa va después de la liga en la misma jornada.
    """
    out = []
    liga, mi = estado.get('liga'), estado.get('mi_equipo')
    if liga is None or mi is None:
        return out
    try:
        nombres = {e.id: e.nombre for e in liga.equipos}
        for p in getattr(liga, 'calendario', []) or []:
            if p.jugado and mi.id in (p.local_id, p.visitante_id):
                out.append({'orden': (p.jornada, 0), 'etiqueta': f"J{p.jornada}",
                            'local': nombres.get(p.local_id, '?'), 'visitante': nombres.get(p.visitante_id, '?'),
                            'gl': p.goles_local, 'gv': p.goles_visitante,
                            'es_local': p.local_id == mi.id, 'penales': None})
    except Exception as e_l:
        logger.error(f"partidos_historial (liga): {e_l}")
    try:
        from alpha_football import competiciones as CP
        t = CP.tipo_copa_user(estado)
        c = CP.copa(estado, t) if t else None
        if c:
            user = CP._nombre_user(estado)
            fj = c.get('fechas_jornada') or []
            for p in c.get('partidos', []):
                if not p.get('jugado') or user not in (p['local'], p['visitante']):
                    continue
                f = int(p.get('fecha', 0))
                pen = CP._penales_de(p)
                out.append({'orden': (fj[f] if 0 <= f < len(fj) else 0, 1),
                            'etiqueta': 'UCL' if t == 'champions' else 'LIB',
                            'local': p['local'], 'visitante': p['visitante'], 'gl': p['gl'], 'gv': p['gv'],
                            'es_local': p['local'] == user,
                            'penales': (pen[0], pen[1]) if pen else None})
    except Exception as e_c:
        logger.error(f"partidos_historial (copa): {e_c}")
    out.sort(key=lambda x: x['orden'], reverse=True)
    return out


def rects_historial() -> tuple:
    """v3.9.0: botones ▲ ▼ del historial de partidos de Inicio."""
    return (pygame.Rect(R_HIST.right - 80, R_HIST.y + 6, 32, 26),
            pygame.Rect(R_HIST.right - 42, R_HIST.y + 6, 32, 26))


def _clave_tabla(eq):
    return (getattr(eq, 'puntos', 0), getattr(eq, 'gf', 0) - getattr(eq, 'gc', 0), getattr(eq, 'gf', 0))


def _ultima_jornada_jugada(liga) -> int:
    """Última jornada con partidos jugados (0 si la temporada no empezó)."""
    jugadas = [p.jornada for p in getattr(liga, 'calendario', []) or [] if p.jugado]
    return max(jugadas) if jugadas else 0


def _jornada_por_defecto(liga) -> int:
    """La jornada actual si ya tiene resultados; si no, la última jugada; en la J1, la J1."""
    ja = int(getattr(liga, 'jornada_actual', 1) or 1)
    if any(p.jugado for p in getattr(liga, 'calendario', []) or [] if p.jornada == ja):
        return ja
    ultima = _ultima_jornada_jugada(liga)
    return ultima if ultima > 0 else ja


def _jornada_vista(estado, liga) -> int:
    """Jornada que muestra el panel; vuelve al default cada vez que avanza la liga
    (o se juega la última jornada, donde jornada_actual ya no cambia)."""
    ja = getattr(liga, 'jornada_actual', 1)
    ref = (ja, any(p.jugado for p in getattr(liga, 'calendario', []) or [] if p.jornada == ja))
    if estado.get('hub_jornada_ref') != ref or not estado.get('hub_jornada_vista'):
        estado['hub_jornada_ref'] = ref
        estado['hub_jornada_vista'] = _jornada_por_defecto(liga)
    return int(estado['hub_jornada_vista'])


def _mover_jornada(estado, liga, paso: int) -> None:
    n = int(getattr(liga, 'num_jornadas', 1) or 1)
    estado['hub_jornada_vista'] = max(1, min(n, _jornada_vista(estado, liga) + paso))


def _alertas_inicio(estado, mi_equipo) -> list:
    """Avisos antes de jugar: lesionados/sancionados del once y ofertas sin responder (máx. 3)."""
    avisos = []
    try:
        if estado.get('aviso_finanzas'):
            avisos.append((str(estado['aviso_finanzas'])[:72], 'rojo'))
        alin = getattr(mi_equipo, 'alineacion_activa', None) or estado.get('alineacion_activa')
        jugadores = list(getattr(mi_equipo, 'jugadores', []) or [])
        for i in list(getattr(alin, 'titulares', []) or []):
            if not (0 <= i < len(jugadores)):
                continue
            j = jugadores[i]
            if getattr(j, 'lesion_partidos', 0) > 0:
                avisos.append((f"Lesionado en tu once: {j.nombre} {j.apellido} ({j.lesion_partidos} p.)", 'rojo'))
            elif getattr(j, 'partidos_sancion', 0) > 0:
                avisos.append((f"Sancionado en tu once: {j.nombre} {j.apellido}", 'rojo'))
        liga = estado.get('liga')
        if liga is not None and getattr(liga, 'jornada_actual', 1) >= getattr(liga, 'num_jornadas', 10) - 3:
            vencen = sum(1 for j in jugadores if int(getattr(j, 'contrato_anios', 2) or 2) <= 1)
            if vencen:
                avisos.append((f"{vencen} contrato{'s' if vencen != 1 else ''} vence{'n' if vencen != 1 else ''} "
                               f"al final de la temporada (FINANZAS > CONTRATOS)", 'dorado'))
        from alpha_football.correo import no_leidos       # v3.1.0: correo sin leer primero
        k = no_leidos(estado)
        if k:
            avisos.insert(0, (f"{k} correo{'s' if k != 1 else ''} sin leer (OFICINA > CORREO)", 'dorado'))
        try:  # v3.4.0: clubes que te ofrecen el banquillo
            from alpha_football.entrenadores import ofertas_activas
            k_dt = len(ofertas_activas(estado))
            if k_dt:
                avisos.insert(0, (f"{k_dt} club{'es' if k_dt != 1 else ''} te quiere{'n' if k_dt != 1 else ''} "
                                  f"como DT (OFICINA > OFERTAS DT)", 'dorado'))
        except Exception as e_odt:
            logger.error(f"Error al leer las ofertas de banquillo: {e_odt}")
        n = len(estado.get('ofertas_recibidas') or [])
        avisos = avisos[:2 if n else 3]
        if n:
            avisos.append((f"{n} oferta{'s' if n != 1 else ''} sin responder", 'dorado'))
    except Exception as e_av:
        logger.error(f"Error al calcular alertas de Inicio: {e_av}")
    return avisos


def _toast(estado, texto: str, color: str = 'verde', ms: int = 3000) -> None:
    """Aviso temporal que Inicio muestra abajo al centro."""
    estado['hub_toast'] = (texto, pygame.time.get_ticks() + ms, color)


def _abrir(estado, destino: str) -> str:
    """Prepara el contexto que cada pantalla espera y devuelve su nombre."""
    if destino == 'team_screen':
        estado['team_contexto'] = 'carrera'
    elif destino == 'options_screen':
        estado['options_return'] = 'league_screen'
    elif destino == 'save_slots_screen':
        estado['save_slots_return'] = 'league_screen'
    elif destino == 'contrato_dt_screen':   # v3.2.0: sin modo → 'ver' o 'renovacion'
        estado.pop('contrato_modo', None)
    elif destino == 'contratos':        # v2.9.0: la plantilla ordenada por contrato
        estado['plantilla_orden'] = 'contrato'
        return 'plantilla_screen'
    return destino


def _info_partido(estado, liga, mi_equipo) -> tuple:
    """(partido_usuario, esta_finalizada, fase_copa, rival_copa) de la jornada actual."""
    jornada_actual = getattr(liga, "jornada_actual", 1)
    num_jornadas = getattr(liga, "num_jornadas", 14)
    partidos_jornada = [p for p in getattr(liga, "calendario", []) if p.jornada == jornada_actual]
    partido_usuario = next((p for p in partidos_jornada
                            if mi_equipo.id in (p.local_id, p.visitante_id)), None)
    esta_finalizada = (jornada_actual == num_jornadas and all(p.jugado for p in partidos_jornada))
    fase_copa, rival_copa = None, None
    try:
        from alpha_football.ui.copa_screen import rival_copa_pendiente
        fase_copa, rival_copa = rival_copa_pendiente(estado)
    except Exception as e_copa:
        logger.error(f"Error al consultar la copa pendiente: {e_copa}")
    return partido_usuario, esta_finalizada, fase_copa, rival_copa


def _accion_jugar(estado, partido_usuario, esta_finalizada, fase_copa) -> Optional[str]:
    """JUGAR: primero la copa si toca, después la liga o el cierre de temporada."""
    if fase_copa:
        from alpha_football.ui.copa_screen import preparar_partido_copa
        if preparar_partido_copa(estado):
            return "prepartido_screen"
        _toast(estado, "No se pudo preparar el partido de copa", color='rojo')
        return None
    if esta_finalizada:
        return "resumen_temporada_screen"
    if partido_usuario is None or partido_usuario.jugado:
        return None
    estado['partido_actual'] = partido_usuario
    estado['match_mode'] = 'liga'
    return "prepartido_screen"


def _textos_jugar(liga, mi_equipo, info) -> tuple:
    """(línea grande, línea 2, línea 3, habilitado) del botón JUGAR."""
    partido_usuario, esta_finalizada, fase_copa, rival_copa = info
    if fase_copa:
        return "JUGAR", f"{fase_copa} vs {(rival_copa or '?')[:26]}", "", True   # v3.8.0
    if esta_finalizada:
        return "AVANZAR TEMPORADA", "La liga terminó: cerrar la temporada", "", True
    if partido_usuario is None or partido_usuario.jugado:
        return "JUGAR", "Sin rival programado", "", False
    es_local = partido_usuario.local_id == mi_equipo.id
    op_id = partido_usuario.visitante_id if es_local else partido_usuario.local_id
    op = next((e for e in liga.equipos if e.id == op_id), None)
    l2 = (f"LIGA · J{partido_usuario.jornada} vs {getattr(op, 'nombre', '?')[:24]} "
          f"({'LOCAL' if es_local else 'VISITANTE'})")
    l3 = (f"DT {(getattr(op, 'estilo_dt', '') or '?').upper()}  ·  OVR {getattr(op, 'ovr_promedio', '?')}  ·  "
          f"Tu OVR {getattr(mi_equipo, 'ovr_promedio', '?')}")
    return "JUGAR", l2, l3, True


class _TablaDibujada(Exception):
    """v3.8.0: corta el bloque de la tabla de liga cuando se dibujó la de copa."""


def rect_tab_tabla(clave: str) -> pygame.Rect:
    """v3.8.0: pestañas LIGA / COPA arriba a la derecha del panel de la tabla."""
    return pygame.Rect(R_TABLA.right - 212 + (0 if clave == 'liga' else 104), R_TABLA.y + 8, 96, 28)


def _dibujar_tabs_tabla(screen, activa: str, mouse_pos) -> None:
    for clave, texto in (('liga', "LIGA"), ('copa', "COPA")):
        r = rect_tab_tabla(clave)
        on = clave == activa
        pygame.draw.rect(screen, COLORS.get('azul', (0, 191, 255)) if on else
                         ((30, 45, 75) if r.collidepoint(mouse_pos) else (15, 22, 40)), r, border_radius=6)
        pygame.draw.rect(screen, COLORS.get('dorado', (255, 215, 0)) if on else COLORS.get('azul', (0, 191, 255)),
                         r, width=1, border_radius=6)
        s = get_font('sm').render(texto, True, COLORS.get('bg', (10, 14, 26)) if on else COLORS.get('blanco', (255, 255, 255)))
        screen.blit(s, s.get_rect(center=r.center))


def _render_tabla_copa(screen, estado) -> None:
    """v3.8.0: tabla de la fase de liga (Champions) o tu grupo / los grupos (Libertadores)."""
    from alpha_football import competiciones as CP
    from alpha_football.ui import copa_screen as S
    tipo = S.copa_de_region(estado)
    c = CP.copa(estado, tipo)
    user = getattr(estado.get('mi_equipo'), 'nombre', '')
    draw_text(screen, CP.NOMBRE_COPA.get(tipo, 'COPA').upper(), (32, R_TABLA.y + 10), size='md', color='azul')
    cuerpo = pygame.Rect(R_TABLA.x + 12, R_TABLA.y + 46, R_TABLA.width - 24, R_TABLA.height - 54)
    if not c:
        draw_text(screen, "La copa todavía no se sorteó.", (cuerpo.x + 8, cuerpo.y + 20), size='sm', color='blanco')
        return
    if tipo == 'champions':
        S.dibujar_tabla_liga(screen, cuerpo, c, user, compacto=True)
    else:
        S.dibujar_grupos(screen, cuerpo, c, user, compacto=True, solo=S.grupo_de(c, user))


def _render_inicio(screen, estado, liga, mi_equipo, info, jugados, mouse_pos, click_pos) -> Optional[str]:
    """Tablero de Inicio: tabla, historial, JUGAR, avisos, panel de jornada y tu club."""
    partido_usuario, esta_finalizada, fase_copa, _rival = info
    foco = int(estado.get('hub_foco', 0))
    es_segunda = getattr(liga, 'division', 1) == 2
    azul = COLORS.get('azul', (0, 191, 255))
    dorado = COLORS.get('dorado', (255, 215, 0))

    # --- Tabla de posiciones (v3.8.0: pestañas LIGA / COPA) ---
    tabla_tab = 'copa' if estado.get('hub_tabla_tab') == 'copa' else 'liga'
    try:
        draw_panel(screen, R_TABLA)
        _dibujar_tabs_tabla(screen, tabla_tab, mouse_pos)
        if tabla_tab == 'copa':
            _render_tabla_copa(screen, estado)
            raise _TablaDibujada()
        ty = R_TABLA.y
        draw_text(screen, "TABLA DE POSICIONES", (32, ty + 10), size='md', color='azul')
        equipos_ordenados = sorted(liga.equipos, key=_clave_tabla, reverse=True)
        headers = ["#", "Equipo", "PJ", "PG", "PE", "PP", "GF", "GC", "DG", "PTS"]
        header_x = [32, 70, 318, 360, 402, 444, 486, 528, 570, 612]
        for h, x_pos in zip(headers, header_x):
            draw_text(screen, h, (x_pos, ty + 44), size='sm', color='dorado')
        pygame.draw.line(screen, azul, (28, ty + 66), (644, ty + 66), 1)
        n_total = len(equipos_ordenados)
        try:
            from alpha_football.ui.copa_screen import cupos_copa
            cupo_copa = cupos_copa(getattr(liga, 'tipo', ''))
        except Exception:
            cupo_copa = 3
        row_h = min(36, (R_TABLA.bottom - ty - 82) // max(1, n_total))
        for idx, eq in enumerate(equipos_ordenados, 1):
            y_pos = ty + 76 + (idx - 1) * row_h
            if es_segunda:
                row_color = 'verde' if idx <= 2 else 'blanco'           # suben 2
            else:
                row_color = ('verde' if idx <= cupo_copa else          # copa (v3.8.0: cupos reales)
                             'rojo' if idx >= n_total - 1 else 'blanco')  # bajan 2
            if eq.id == mi_equipo.id:
                sub = pygame.Rect(24, y_pos - 4, 624, max(4, row_h - 4))
                pygame.draw.rect(screen, (30, 45, 75), sub, border_radius=4)
                pygame.draw.rect(screen, COLORS.get('verde', (0, 255, 136)), sub, width=1, border_radius=4)
            dg = eq.gf - eq.gc
            valores = [str(idx), eq.nombre[:24], str(eq.pj), str(eq.pg), str(eq.pe), str(eq.pp),
                       str(eq.gf), str(eq.gc), f"+{dg}" if dg > 0 else str(dg), str(eq.puntos)]
            for v, x_pos in zip(valores, header_x):
                draw_text(screen, v, (x_pos, y_pos), size='sm', color=row_color)
    except _TablaDibujada:
        pass
    except Exception as e_table:
        logger.error(f"Error al renderizar la tabla: {e_table}")

    # --- Historial de tus partidos (v4.3.0: liga + copa) ---
    historial = partidos_historial(estado)
    max_offset = max(0, len(historial) - PARTIDOS_VISIBLES)
    r_up, r_down = rects_historial()
    try:
        draw_panel(screen, R_HIST)
        draw_text(screen, f"HISTORIAL DE PARTIDOS ({len(historial)} jugados)",
                  (32, R_HIST.y + 8), size='sm', color='dorado')
        offset = min(estado.setdefault('hist_scroll_offset', 0), max_offset)
        estado['hist_scroll_offset'] = offset
        draw_styled_button(screen, r_up, "▲", r_up.collidepoint(mouse_pos), azul)
        draw_styled_button(screen, r_down, "▼", r_down.collidepoint(mouse_pos), azul)
        hy = R_HIST.y + 38
        if not historial:
            draw_text(screen, "Aún no has jugado partidos esta temporada.", (32, hy), size='sm', color='blanco')
        for p in historial[offset:offset + PARTIDOS_VISIBLES]:
            ug, rg = (p['gl'], p['gv']) if p['es_local'] else (p['gv'], p['gl'])
            col = 'verde' if ug > rg else ('rojo' if ug < rg else 'azul')
            pen_txt = ""
            if p['penales']:   # definido por penales: color según quién pasó
                a, b = p['penales']
                pen_txt = f"  ({a}-{b} pen.)"
                if ug == rg:
                    col = 'verde' if (a > b) == p['es_local'] else 'rojo'
            ln = (f"{p['etiqueta']}:  {str(p['local'])[:20]}  {p['gl']} - {p['gv']}  {str(p['visitante'])[:20]}"
                  + pen_txt)
            draw_text(screen, ln, (32, hy), size='sm', color=col)
            hy += 23
    except Exception as e_hist:
        logger.error(f"Error al renderizar historial: {e_hist}")

    # --- JUGAR ---
    l1, l2, l3, habilitado = _textos_jugar(liga, mi_equipo, info)
    try:
        hover = R_JUGAR.collidepoint(mouse_pos) and habilitado
        draw_styled_button(screen, R_JUGAR, "", hover or foco == 0, COLORS.get('verde', (0, 255, 136)), habilitado)
        if foco == 0 and not hover:
            pygame.draw.rect(screen, dorado, R_JUGAR, width=3, border_radius=8)
        draw_text(screen, l1, (R_JUGAR.x + 20, R_JUGAR.y + 10), size='lg',
                  color='verde' if habilitado else 'blanco')
        draw_text(screen, l2, (R_JUGAR.x + 20, R_JUGAR.y + 48), size='sm',
                  color='dorado' if fase_copa else 'blanco')
        if l3:
            draw_text(screen, l3, (R_JUGAR.x + 20, R_JUGAR.y + 70), size='sm', color='azul')
    except Exception as e_jugar:
        logger.error(f"Error al dibujar JUGAR: {e_jugar}")

    # --- Línea de copa + alertas ---
    try:
        lineas = []
        if not fase_copa:
            from alpha_football.ui.copa_screen import linea_copa_user
            linea = linea_copa_user(estado)
            if linea:
                lineas.append((linea, 'dorado'))
        lineas += _alertas_inicio(estado, mi_equipo)
        for i, (texto, color) in enumerate(lineas[:4]):
            draw_text(screen, texto[:72], (R_JUGAR.x + 4, Y_AVISOS + i * 20), size='sm', color=color)
    except Exception as e_avisos:
        logger.error(f"Error al dibujar avisos: {e_avisos}")

    # --- Panel de jornada (reemplaza "otros partidos" y el overlay de resumen) ---
    r_prev, r_next = _rects_jornada()
    try:
        draw_panel(screen, R_JORNADA)
        if foco == 1:
            pygame.draw.rect(screen, dorado, R_JORNADA, width=2, border_radius=8)
        j = _jornada_vista(estado, liga)
        draw_text(screen, f"JORNADA {j} de {getattr(liga, 'num_jornadas', '?')}",
                  (R_JORNADA.x + 18, R_JORNADA.y + 10), size='md', color='dorado')
        draw_styled_button(screen, r_prev, "<", r_prev.collidepoint(mouse_pos), azul)
        draw_styled_button(screen, r_next, ">", r_next.collidepoint(mouse_pos), azul)
        equipos = {e.id: e for e in liga.equipos}
        partidos = sorted((p for p in getattr(liga, 'calendario', []) or [] if p.jornada == j),
                          key=lambda p: mi_equipo.id not in (p.local_id, p.visitante_id))
        row_h = min(24, (R_JORNADA.height - 56) // max(1, len(partidos)))
        y = R_JORNADA.y + 48
        if not partidos:
            draw_text(screen, "No hay partidos en esta jornada.", (R_JORNADA.x + 18, y), size='sm', color='blanco')
        cx = R_JORNADA.centerx
        for p in partidos:
            if mi_equipo.id in (p.local_id, p.visitante_id):
                pygame.draw.rect(screen, (30, 45, 75),
                                 pygame.Rect(R_JORNADA.x + 10, y - 2, R_JORNADA.width - 20, row_h), border_radius=4)
            n_loc = getattr(equipos.get(p.local_id), 'nombre', '?')[:24]
            n_vis = getattr(equipos.get(p.visitante_id), 'nombre', '?')[:24]
            if p.jugado:
                gl, gv = int(p.goles_local), int(p.goles_visitante)
                marcador = f"{gl} - {gv}"
                c_loc = 'verde' if gl > gv else ('rojo' if gl < gv else 'blanco')
                c_vis = 'verde' if gv > gl else ('rojo' if gv < gl else 'blanco')
            else:
                marcador, c_loc, c_vis = "vs", 'blanco', 'blanco'
            s_loc = get_font('sm').render(n_loc, True, COLORS.get(c_loc, (255, 255, 255)))
            screen.blit(s_loc, s_loc.get_rect(topright=(cx - 40, y)))
            s_res = get_font('sm').render(marcador, True, dorado)
            screen.blit(s_res, s_res.get_rect(midtop=(cx, y)))
            draw_text(screen, n_vis, (cx + 40, y), size='sm', color=c_vis)
            y += row_h
    except Exception as e_jor:
        logger.error(f"Error al dibujar el panel de jornada: {e_jor}")

    # --- Tu club: forma, goleador y presupuesto ---
    try:
        draw_panel(screen, R_CLUB)
        cx0, cy0 = R_CLUB.x + 18, R_CLUB.y + 10
        draw_text(screen, "TU CLUB", (cx0, cy0), size='sm', color='dorado')
        draw_text(screen, "Forma:", (cx0, cy0 + 28), size='sm', color='azul')
        fx = cx0 + 70
        for p in list(reversed(jugados[:5])):
            es_local = p.local_id == mi_equipo.id
            ug, rg = (p.goles_local, p.goles_visitante) if es_local else (p.goles_visitante, p.goles_local)
            letra, col = ('G', 'verde') if ug > rg else (('P', 'rojo') if ug < rg else ('E', 'azul'))
            caja = pygame.Rect(fx, cy0 + 26, 26, 24)
            pygame.draw.rect(screen, COLORS.get(col, azul), caja, width=2, border_radius=4)
            draw_text(screen, letra, (fx + 7, cy0 + 28), size='sm', color=col, shadow=False)
            fx += 32
        if not jugados:
            draw_text(screen, "sin partidos", (cx0 + 70, cy0 + 28), size='sm', color='blanco')
        goleador = max(mi_equipo.jugadores, key=lambda jj: getattr(jj, 'goles', 0), default=None)
        if goleador is not None and getattr(goleador, 'goles', 0) > 0:
            draw_text(screen, f"Goleador: {goleador.nombre} {goleador.apellido} ({goleador.goles})",
                      (cx0, cy0 + 56), size='sm', color='blanco')
        from alpha_football.directiva import calif_dt                  # v3.1.0
        draw_text(screen, f"OVR {getattr(mi_equipo, 'ovr_promedio', 0)}  ·  Plantilla {len(mi_equipo.jugadores)}  ·  "
                          f"${getattr(mi_equipo, 'balance', 0) / 1_000_000:.1f}M  ·  Calif. DT {calif_dt(estado)}",
                  (cx0, cy0 + 82), size='sm', color='blanco')
        obj = (estado.get('datos_carrera') or {}).get('objetivo') or {}
        if obj:
            from alpha_football.directiva import confianza
            draw_text(screen, f"Objetivo: {obj.get('texto', '')[:40]}  ·  Confianza {confianza(estado)}",
                      (cx0, cy0 + 106), size='sm', color='dorado')
    except Exception as e_club:
        logger.error(f"Error al dibujar Tu club: {e_club}")

    # --- Clics ---
    if click_pos:
        if rect_tab_tabla('liga').collidepoint(click_pos):
            estado['hub_tabla_tab'] = 'liga'
        elif rect_tab_tabla('copa').collidepoint(click_pos):
            estado['hub_tabla_tab'] = 'copa'
        elif R_JUGAR.collidepoint(click_pos):
            estado['hub_foco'] = 0
            if habilitado:
                return _accion_jugar(estado, partido_usuario, esta_finalizada, fase_copa)
        elif r_up.collidepoint(click_pos):
            estado['hist_scroll_offset'] = max(0, estado.get('hist_scroll_offset', 0) - 1)
        elif r_down.collidepoint(click_pos):
            estado['hist_scroll_offset'] = min(max_offset, estado.get('hist_scroll_offset', 0) + 1)
        elif r_prev.collidepoint(click_pos):
            estado['hub_foco'] = 1
            _mover_jornada(estado, liga, -1)
        elif r_next.collidepoint(click_pos):
            estado['hub_foco'] = 1
            _mover_jornada(estado, liga, 1)
    return None


def _render_tarjetas(screen, estado, tab, mouse_pos, click_pos) -> Optional[str]:
    """Pestañas DIRECCIÓN / NEGOCIACIONES / OFICINA: tarjetas grandes que abren cada pantalla."""
    tarjetas = TARJETAS.get(tab, [])
    rects = _rects_tarjetas(len(tarjetas))
    foco = int(estado.get('hub_foco', 0))
    try:
        draw_text(screen, TITULOS.get(tab, tab.upper()), (32, 112), size='lg', color='dorado')
        n_ofertas = len(estado.get('ofertas_recibidas') or [])
        from alpha_football.correo import no_leidos
        n_correo = no_leidos(estado)                                  # v3.1.0
        try:  # v3.4.0: badge de OFERTAS DT
            from alpha_football.entrenadores import ofertas_activas
            n_ofertas_dt = len(ofertas_activas(estado))
        except Exception as e_odt:
            logger.error(f"Error al contar las ofertas de banquillo: {e_odt}")
            n_ofertas_dt = 0
        for i, ((titulo, sub, destino), rect) in enumerate(zip(tarjetas, rects)):
            hover = rect.collidepoint(mouse_pos)
            draw_styled_button(screen, rect, "", hover or i == foco, COLORS.get('azul', (0, 191, 255)))
            if i == foco and not hover:
                pygame.draw.rect(screen, COLORS.get('dorado', (255, 215, 0)), rect, width=3, border_radius=8)
            draw_text(screen, titulo, (rect.x + 24, rect.y + 40), size='lg', color='blanco')
            draw_text(screen, sub, (rect.x + 24, rect.y + 90), size='sm', color='azul')
            n_badge = n_ofertas if destino == 'ofertas_screen' else (n_correo if destino == 'correo_screen' else 0)
            if destino == 'ofertas_dt_screen':     # v3.4.0
                n_badge = n_ofertas_dt
            if n_badge > 0:
                bx, by = rect.right - 30, rect.top + 30
                pygame.draw.circle(screen, (255, 68, 68), (bx, by), 16)
                bs = get_font('md').render(str(n_badge), True, (255, 255, 255))
                screen.blit(bs, bs.get_rect(center=(bx, by)))
    except Exception as e_tarj:
        logger.error(f"Error al dibujar las tarjetas de {tab}: {e_tarj}")
    if click_pos:
        for i, ((_t, _s, destino), rect) in enumerate(zip(tarjetas, rects)):
            if rect.collidepoint(click_pos):
                estado['hub_foco'] = i
                return _abrir(estado, destino)
    return None


# --- Renderizador del hub ═════════════════════════════════════════════════════

def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """
    Hub de carrera (v2.4.0): columnas arriba y el contenido de la pestaña activa.
    Retorna la siguiente pantalla o None para seguir aquí.
    """
    try:
        liga = estado.get('liga')
        mi_equipo = estado.get('mi_equipo')
        if not liga or not mi_equipo:
            logger.error("Error resiliente: No hay liga o equipo cargado en el estado de liga.")
            return "menu"

        try:
            inicializar_calendario_liga(liga)
        except Exception as error_fixtures:
            logger.error(f"Error al inicializar fixtures de liga: {error_fixtures}")

        try:  # v2.9.1: un despido pendiente (también de un save) no se puede esquivar
            from alpha_football.directiva import restaurar_despido
            if restaurar_despido(estado):
                return "despido_screen"
        except Exception as e_desp:
            logger.error(f"Error al revisar el despido pendiente: {e_desp}")

        # v3.8.0: las copas (motor de competiciones) avanzan sin abrir su pantalla. Solo se
        # sincroniza cuando cambia la temporada, la jornada o el club del user.
        try:
            from alpha_football.ui.copa_screen import sincronizar_copa_user

            def _clave_copa():
                return (estado.get('temporada', 1), getattr(liga, 'jornada_actual', 1),
                        getattr(mi_equipo, 'nombre', ''))
            if estado.get('_hub_copa_sync') != _clave_copa():
                sincronizar_copa_user(estado)
                estado['_hub_copa_sync'] = _clave_copa()
        except Exception as e_sync:
            logger.error(f"Error al sincronizar la copa: {e_sync}")

        try:  # v2.8.0: objetivo de la temporada (una vez por temporada / club)
            from alpha_football.directiva import definir_objetivo
            definir_objetivo(estado)
        except Exception as e_obj:
            logger.error(f"Error al definir el objetivo: {e_obj}")
        try:  # v3.2.0: contrato del DT (saves viejos) y objetivo internacional
            from alpha_football.carrera_dt import asegurar_contrato
            asegurar_contrato(estado)
            from alpha_football.directiva import definir_objetivo_copa
            definir_objetivo_copa(estado)
            from alpha_football.entrenadores import asegurar_dts   # v3.4.0: DT en cada club IA
            asegurar_dts(estado)
        except Exception as e_dt:
            logger.error(f"Error en contrato/objetivo de copa: {e_dt}")
        try:  # v2.9.0: contratos para toda la partida (una vez; saves viejos incluidos)
            dc = estado.setdefault('datos_carrera', {})
            if not dc.get('contratos_v290'):
                from alpha_football.finanzas import asegurar_contratos
                asegurar_contratos(estado)
                dc['contratos_v290'] = True
        except Exception as e_con:
            logger.error(f"Error al asignar contratos: {e_con}")

        info = _info_partido(estado, liga, mi_equipo)
        partido_usuario, esta_finalizada, fase_copa, _rival = info
        jugados = sorted(
            (p for p in getattr(liga, 'calendario', [])
             if p.jugado and mi_equipo.id in (p.local_id, p.visitante_id)),
            key=lambda p: p.jornada, reverse=True)
        max_offset = max(0, len(partidos_historial(estado)) - PARTIDOS_VISIBLES)   # v4.3.0: liga + copa

        tab = estado.get('hub_tab') if estado.get('hub_tab') in PESTANAS else 'inicio'
        bar_foco = int(estado.get('hub_bar_foco', 0)) % len(BARRA_MENU)
        # Al volver de otra pantalla (o de OPCIONES/GUARDAR) el foco vuelve a la pestaña activa.
        if bar_foco >= len(PESTANAS) or PESTANAS[bar_foco] != tab:
            bar_foco = PESTANAS.index(tab)
        foco = int(estado.get('hub_foco', 0))
        # v3.6.0: al volver de la copa / un partido, el foco queda en JUGAR (y nunca fuera de rango)
        anterior = estado.pop('pantalla_anterior', None)
        if tab == 'inicio' and (anterior in VUELVEN_A_JUGAR or foco not in (0, 1)):
            foco, bar_foco = 0, 0

        # --- Eventos ---
        mouse_pos = pygame.mouse.get_pos()
        click_pos = None
        key_events = []
        try:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "menu"
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        click_pos = event.pos
                    elif event.button in (4, 5) and tab == 'inicio' and R_HIST.collidepoint(mouse_pos):
                        paso = -1 if event.button == 4 else 1
                        estado['hist_scroll_offset'] = max(0, min(max_offset, estado.get('hist_scroll_offset', 0) + paso))
                elif event.type == pygame.KEYDOWN:
                    key_events.append(event)
        except Exception as e_events:
            logger.error(f"Error al procesar eventos en league_screen: {e_events}")

        def _guardar_foco():
            estado['hub_tab'], estado['hub_bar_foco'], estado['hub_foco'] = tab, bar_foco, foco

        # v3.6.0: con el diálogo de salida abierto, teclas y clics solo van al diálogo
        if estado.get('dialogo_salir'):
            try:
                destino_dlg = _manejar_dialogo_salir(estado, key_events, click_pos)
            except Exception as e_dlg:
                logger.error(f"Error en el diálogo de salida: {e_dlg}", exc_info=True)
                estado['dialogo_salir'], destino_dlg = False, None
            if destino_dlg:
                _guardar_foco()
                return destino_dlg
            key_events, click_pos = [], None
            dialogo_visible = bool(estado.get('dialogo_salir'))
        else:
            dialogo_visible = False

        try:  # v4.4.0: cartel de apertura/cierre del mercado (consume teclas y clics mientras está abierto)
            from alpha_football.ui import aviso_mercado as _am
            destino_am, key_events, click_pos = _am.manejar(estado, key_events, click_pos, dialogo_visible)
            if destino_am:
                _guardar_foco()
                return destino_am
        except Exception as e_am:
            logger.error(f"Error en el aviso de mercado: {e_am}")

        # --- Teclado ---
        for ev in key_events:
            if ev.key == pygame.K_j:
                _guardar_foco()
                return _accion_jugar(estado, partido_usuario, esta_finalizada, fase_copa)
            if ev.key == pygame.K_r:
                tab, bar_foco, foco = 'inicio', 0, 1
            elif ev.key in (pygame.K_LEFT, pygame.K_RIGHT):
                paso = -1 if ev.key == pygame.K_LEFT else 1
                if tab == 'inicio' and foco == 1 and bar_foco == 0:
                    _mover_jornada(estado, liga, paso)
                else:
                    bar_foco = (bar_foco + paso) % len(BARRA_MENU)
                    if bar_foco < len(PESTANAS):
                        tab, foco = PESTANAS[bar_foco], 0
            elif ev.key in (pygame.K_UP, pygame.K_DOWN):
                if tab == 'inicio':
                    foco = 0 if ev.key == pygame.K_UP else 1
                else:
                    n = max(1, len(TARJETAS.get(tab, [])))
                    foco = (foco + (-1 if ev.key == pygame.K_UP else 1)) % n
            elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                _guardar_foco()
                if bar_foco >= len(PESTANAS):
                    return _abrir(estado, DESTINO_DIRECTO[BARRA_MENU[bar_foco][0]])
                if tab == 'inicio':
                    if foco == 0:
                        return _accion_jugar(estado, partido_usuario, esta_finalizada, fase_copa)
                else:
                    tarjetas = TARJETAS.get(tab, [])
                    if tarjetas:
                        return _abrir(estado, tarjetas[foco % len(tarjetas)][2])
            elif ev.key == pygame.K_ESCAPE:
                if tab != 'inicio':
                    tab, bar_foco, foco = 'inicio', 0, 0
                else:
                    estado['dialogo_salir'] = True       # v3.6.0: ¿salir? en vez de salir directo
                    dialogo_visible = True
                    break

        # v4.2.0: clic en el sobre de correo
        if click_pos and R_SOBRE.collidepoint(click_pos):
            _guardar_foco()
            return 'correo_screen'

        # --- Clic en la barra ---
        rects = _rects_barra()
        if click_pos:
            for i, rect in enumerate(rects):
                if rect.collidepoint(click_pos):
                    if i < len(PESTANAS):
                        tab, bar_foco, foco = PESTANAS[i], i, 0
                        click_pos = None
                    else:
                        bar_foco = i
                        _guardar_foco()
                        return _abrir(estado, DESTINO_DIRECTO[BARRA_MENU[i][0]])
                    break
        _guardar_foco()

        # --- Fondo ---
        try:
            draw_gradient_bg(screen)
            draw_pitch_lines(screen)
        except Exception:
            screen.fill(COLORS.get('bg', (10, 14, 26)))
        try:
            pygame.draw.rect(screen, COLORS.get('rojo', (255, 68, 68)), pygame.Rect(0, 0, SCREEN_W, 4))
            pygame.draw.rect(screen, COLORS.get('verde', (0, 255, 136)), pygame.Rect(0, 4, SCREEN_W, 4))
            pygame.draw.rect(screen, COLORS.get('azul', (0, 191, 255)), pygame.Rect(0, 8, SCREEN_W, 4))
        except Exception:
            pass

        # --- Barra de columnas ---
        try:
            try:   # v4.2.0: sobre de correo con los no leídos
                from alpha_football import correo as _correo
                dibujar_sobre(screen, R_SOBRE, _correo.no_leidos(estado), R_SOBRE.collidepoint(mouse_pos))
            except Exception as e_sobre:
                logger.error(f"No se pudo dibujar el sobre de correo: {e_sobre}")
            n_ofertas = len(estado.get('ofertas_recibidas', []) or [])
            for i, ((clave, l1, l2, col), rect) in enumerate(zip(BARRA_MENU, rects)):
                color = COLORS.get(col, (0, 191, 255))
                activa = clave == tab
                _boton_barra(screen, rect, l1, l2, rect.collidepoint(mouse_pos) or activa, color,
                             foco=(i == bar_foco and not rect.collidepoint(mouse_pos)))
                if activa:
                    pygame.draw.rect(screen, color, pygame.Rect(rect.x + 8, rect.bottom + 2, rect.width - 16, 4))
                if clave == 'negociaciones' and n_ofertas > 0:
                    bx, by = rect.right - 12, rect.top + 10
                    pygame.draw.circle(screen, (255, 68, 68), (bx, by), 10)
                    bs = get_font('sm').render(str(n_ofertas), True, (255, 255, 255))
                    screen.blit(bs, bs.get_rect(center=(bx, by)))
        except Exception as e_barra:
            logger.error(f"Error al dibujar la barra: {e_barra}")

        # --- Cabecera ---
        try:
            pres_m = getattr(mi_equipo, 'balance', 0) / 1_000_000
            es_segunda = getattr(liga, 'division', 1) == 2
            from alpha_football.paises import nombre_liga as _nombre_liga   # v3.7.0: nombre del editor
            cabecera = (f"{_nombre_liga(liga.tipo, getattr(liga, 'division', 1) or 1).upper()[:32]}  ·  {mi_equipo.nombre[:22]}  ·  "
                        f"{'2ª' if es_segunda else '1ª'} División  ·  T{estado.get('temporada', 1)}  ·  "
                        f"Jornada {getattr(liga, 'jornada_actual', 1)}/{getattr(liga, 'num_jornadas', 14)}  ·  "
                        f"${pres_m:.1f}M")
            draw_text(screen, cabecera, (16, 82), size='sm', color='azul')
        except Exception as e_header:
            logger.error(f"Error al dibujar cabecera: {e_header}")

        if tab == 'inicio':
            destino = _render_inicio(screen, estado, liga, mi_equipo, info, jugados, mouse_pos, click_pos)
        else:
            destino = _render_tarjetas(screen, estado, tab, mouse_pos, click_pos)

        # --- Aviso temporal ---
        try:
            toast = estado.get('hub_toast')
            if toast and pygame.time.get_ticks() < toast[1]:
                texto, _hasta, color = (list(toast) + ['verde'])[:3]
                surf = get_font('md').render(texto, True, COLORS.get('bg', (10, 14, 26)))
                caja = surf.get_rect(center=(SCREEN_W // 2, SCREEN_H - 40)).inflate(40, 20)
                pygame.draw.rect(screen, COLORS.get(color, (0, 255, 136)), caja, border_radius=8)
                screen.blit(surf, surf.get_rect(center=caja.center))
            elif toast:
                estado.pop('hub_toast', None)
        except Exception as e_toast:
            logger.error(f"Error al dibujar el aviso: {e_toast}")

        try:  # v4.4.0: franja del mercado abierto y cartel de apertura/cierre
            from alpha_football.ui import aviso_mercado as _am2
            _am2.dibujar(screen, estado, mouse_pos)
        except Exception as e_am2:
            logger.error(f"Error al dibujar el aviso de mercado: {e_am2}")

        if dialogo_visible or estado.get('dialogo_salir'):
            try:
                _dibujar_dialogo_salir(screen, mouse_pos)
            except Exception as e_dlg:
                logger.error(f"Error al dibujar el diálogo de salida: {e_dlg}")
            return None
        return destino
    except Exception as error_general:
        logger.error(f"Error crítico en render de league_screen: {error_general}", exc_info=True)
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
