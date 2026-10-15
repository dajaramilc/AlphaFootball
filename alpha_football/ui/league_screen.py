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
from alpha_football.sanciones import sancionado_en_algo  # noqa: E402
from alpha_football.energia import texto_lesion as _texto_lesion  # noqa: E402  v0.4.19.0

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


def _ligas_de_fondo(estado: dict, paises=None) -> list:
    """v2.3.5: ligas que avanzan en background: las 1ª y 2ª de los 5 países.
    Nunca incluye la liga del user (esa la juega él). v0.4.16.0: con `paises`, solo las de esos países."""
    liga_user = estado.get('liga')
    filtro = set(paises) if paises is not None else None
    ligas = (list((estado.get('primera_division') or {}).values())
             + list((estado.get('segunda_division') or {}).values()))
    return [l for l in ligas if l is not None and l is not liga_user
            and len(getattr(l, 'equipos', []) or []) >= 2
            and (filtro is None or getattr(l, 'tipo', None) in filtro)]


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


def simular_jornada_segunda_division(estado: dict, paises=None) -> None:
    """
    v2.3 (Fase 7) / v2.3.5: avanza UNA jornada de cada liga de fondo (2ª divisiones y,
    si el user está en 2ª, la 1ª de su país) al terminar cada jornada del usuario.
    """
    for liga_b in _ligas_de_fondo(estado, paises):
        try:
            _simular_jornada_liga_fondo(liga_b)
        except Exception as e_liga:
            logger.error(f"Error en simulación de fondo de {getattr(liga_b, 'nombre', '?')}: {e_liga}")


def completar_ligas_de_fondo(estado: dict, paises=None) -> None:
    """v2.3.5: al cerrar la temporada, juega lo que falte de cada liga de fondo para que
    el ascenso/descenso se decida con la tabla final (las ligas tienen distinto largo)."""
    for liga_b in _ligas_de_fondo(estado, paises):
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
        ("CANTERA", "Juveniles del club: súbelos o libéralos", 'cantera_screen'),   # v4.8.0
        ("CALENDARIO", "Tus partidos de liga y copa, día por día", 'calendario_screen'),   # v0.4.11.0
    ],
    'negociaciones': [
        ("NEGOCIAR", "Buscador de jugadores de todas las ligas", 'buscador_screen'),
        ("FAVORITOS", "Jugadores que sigues para ficharlos después", 'favoritos_screen'),
        ("OFERTAS", "Ofertas recibidas por tus jugadores", 'ofertas_screen'),
        ("HISTORIAL", "Pases de todas las ligas y los tuyos", 'historial_pases_screen'),
        ("OJEADOR", "3 fichajes recomendados por ventana", 'ojeador_screen'),
    ],
    'oficina': [
        ("NOTIFICACIONES", "Mensajes de jugadores y presidente, y correo del club", 'notificaciones_screen'),   # v0.4.10.0
        ("NOTICIAS", "Titulares de tu liga y del mundo", 'noticias_screen'),   # v0.4.23.0
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
        ("PATROCINIOS", "Marcas, objetivos y ofertas", 'patrocinios_screen'),   # v4.9.0
    ],
}

# Layout de Inicio
R_TABLA = pygame.Rect(16, 106, 640, 400)
R_HIST = pygame.Rect(16, 516, 640, 180)       # v3.6.0: termina en y=696 (barra de atajos)
R_JUGAR = pygame.Rect(672, 106, 592, 96)
R_DIA = pygame.Rect(R_JUGAR.right - 116, R_JUGAR.bottom - 30, 100, 24)   # v0.4.12.0: botón +1 DÍA (dentro de JUGAR)
R_HORA = pygame.Rect(R_JUGAR.x + 20, R_JUGAR.bottom - 32, 200, 26)        # v0.4.14.0: AVANZAR 1 HORA (último día)
R_CERRAR = pygame.Rect(R_JUGAR.x + 232, R_JUGAR.bottom - 32, 200, 26)     # v0.4.14.0: CERRAR MERCADO
MS_DIA_AVANCE = 1000      # v0.4.14.1: pausa entre día y día mientras CONTINUAR avanza a la vista; v0.4.18.0: 1 s por día (antes 40 ms)
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
    if n > 8:       # v0.4.23.0: con NOTICIAS, OFICINA ya no cabe en 2 columnas × 4 filas: 3 columnas
        w, cols = 392, 3
        if n > 9:
            h, gap = 108, 12
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
            if getattr(j, 'lesion_dias', 0) > 0:
                avisos.append((f"Lesionado en tu once: {j.nombre} {j.apellido} ({_texto_lesion(j.lesion_dias, corto=True)})", 'rojo'))
            elif sancionado_en_algo(j):
                from alpha_football.sanciones import sancionado as _sc
                cual = " y ".join(c for c in ('liga', 'copa') if _sc(j, c))
                avisos.append((f"Sancionado en tu once ({cual}): {j.nombre} {j.apellido}", 'rojo'))
        liga = estado.get('liga')
        if liga is not None and getattr(liga, 'jornada_actual', 1) >= getattr(liga, 'num_jornadas', 10) - 3:
            vencen = sum(1 for j in jugadores if int(getattr(j, 'contrato_anios', 2) or 2) <= 1)
            if vencen:
                avisos.append((f"{vencen} contrato{'s' if vencen != 1 else ''} vence{'n' if vencen != 1 else ''} "
                               f"al final de la temporada (FINANZAS > CONTRATOS)", 'dorado'))
        from alpha_football.correo import no_leidos       # v3.1.0: correo sin leer primero
        k = no_leidos(estado)
        if k:
            avisos.insert(0, (f"{k} notificaci{'ones' if k != 1 else 'ón'} sin leer (OFICINA > NOTIFICACIONES)", 'dorado'))
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
    elif destino in ('negociaciones', 'market_screen'):
        # el mercado es la pestaña NEGOCIACIONES del hub ('market_screen' = correos viejos)
        estado['hub_tab'] = 'negociaciones'
        estado['hub_bar_foco'] = PESTANAS.index('negociaciones')
        estado['hub_foco'] = 0
        return 'league_screen'
    return destino


def _info_partido(estado, liga, mi_equipo) -> tuple:
    """(partido_usuario, esta_finalizada, fase_copa, rival_copa) de la jornada actual."""
    jornada_actual = getattr(liga, "jornada_actual", 1)
    num_jornadas = getattr(liga, "num_jornadas", 14)
    partidos_jornada = [p for p in getattr(liga, "calendario", []) if p.jornada == jornada_actual]
    partido_usuario = next((p for p in partidos_jornada
                            if mi_equipo.id in (p.local_id, p.visitante_id)), None)
    esta_finalizada = (jornada_actual == num_jornadas and all(p.jugado for p in partidos_jornada))
    if esta_finalizada:
        try:   # v0.4.13.0: con reloj, la temporada termina en su fecha (30 jun / 31 dic), no al jugar la última jornada
            from alpha_football import dias as _dias_f, temporada as _T_f
            if _dias_f.activo(estado) and not _T_f.es_fin(estado):
                esta_finalizada = False
        except Exception as e_fin:
            logger.error(f"Error al leer el fin de temporada: {e_fin}")
    fase_copa, rival_copa = None, None
    try:
        from alpha_football.ui.copa_screen import rival_copa_pendiente
        fase_copa, rival_copa = rival_copa_pendiente(estado)
    except Exception as e_copa:
        logger.error(f"Error al consultar la copa pendiente: {e_copa}")
    return partido_usuario, esta_finalizada, fase_copa, rival_copa


def _iniciar_avance(estado) -> None:
    """v0.4.14.1: CONTINUAR ya no corre todos los días de golpe (cruzar una ronda de fichajes de la IA
    congelaba la pantalla varios segundos): los pasa de a uno por cuadro, a la vista."""
    from alpha_football import dias as _dias, calendario as _cal, temporada as _T
    prox = _cal.proximo_evento(estado)
    meta = prox['fecha'] if prox else _T.fin(estado)
    estado['hub_avance'] = {'desde': _dias.hoy(estado).isoformat(), 'meta': meta.isoformat(), 'sig': 0,
                            'total': {'dias': 0, 'correos': 0, 'ofertas': 0, 'eventos': 0}}


def _terminar_avance(estado) -> None:
    """Cierra el avance a la vista y deja el resumen de lo que pasó en el aviso de Inicio."""
    av = estado.pop('hub_avance', None)
    if av:
        from alpha_football import dias as _dias, noticias as _noticias
        _toast(estado, _dias.texto_resumen(av.get('total') or {}), color='azul')
        _noticias.reiniciar_feed(estado)       # v0.4.25.0: cada parada, el feed vuelve a las 3 noticias más recientes


def _paso_avance(estado, ahora: Optional[int] = None) -> bool:
    """Pasa un día más del avance de CONTINUAR, si ya toca. True mientras el avance siga; se detiene con las
    reglas de dias.continuar (llegó tu partido, una oferta, un evento o el último día de fichajes)."""
    av = estado.get('hub_avance')
    if not av:
        return False
    try:
        from alpha_football import dias as _dias
        ahora = pygame.time.get_ticks() if ahora is None else int(ahora)
        if ahora < int(av.get('sig', 0) or 0):
            return True
        r = _dias.avanzar_dia(estado)
        total = av['total']
        for k in ('dias', 'correos', 'ofertas', 'eventos'):
            total[k] = int(total.get(k, 0) or 0) + int(r.get(k, 0) or 0)
        if r.get('hito'):
            total['hito'] = r['hito']
        if r['dias'] and not _dias.debe_parar(r) and _dias.es_dia_de_continuar(estado):
            av['sig'] = ahora + MS_DIA_AVANCE
            return True
    except Exception as e_av:
        logger.error(f"Error en el avance de los días: {e_av}", exc_info=True)
    _terminar_avance(estado)
    return False


def avance_visible(estado) -> Optional[tuple]:
    """(fecha de hoy, días que van, días hasta tu próximo partido) mientras CONTINUAR avanza a la vista."""
    av = estado.get('hub_avance')
    if not av:
        return None
    try:
        from datetime import date
        from alpha_football import dias as _dias
        hoy, desde = _dias.hoy(estado), date.fromisoformat(av['desde'])
        return hoy, (hoy - desde).days, max(1, (date.fromisoformat(av['meta']) - desde).days)
    except Exception as e_av:
        logger.error(f"Avance de los días dañado: {e_av}")
        estado.pop('hub_avance', None)
        return None


def _dibujar_avance(screen, anim: tuple) -> None:
    """v0.4.14.1: tapa el botón grande con el día que va pasando: la fecha, la semana alrededor y el avance."""
    from datetime import timedelta
    from alpha_football import calendario as _cal
    fecha, k, total = anim
    dorado, azul = COLORS.get('dorado', (255, 215, 0)), COLORS.get('azul', (0, 191, 255))
    pygame.draw.rect(screen, (12, 18, 34), R_JUGAR, border_radius=8)
    pygame.draw.rect(screen, dorado, R_JUGAR, width=2, border_radius=8)
    draw_text(screen, "AVANZANDO", (R_JUGAR.x + 20, R_JUGAR.y + 8), size='sm', color='azul')
    draw_text(screen, _cal.texto_fecha(fecha), (R_JUGAR.x + 20, R_JUGAR.y + 28), size='lg', color='dorado')
    draw_text(screen, f"día {k} de {total} · una tecla lo detiene", (R_JUGAR.x + 20, R_JUGAR.y + 64), size='sm',
              color='blanco')
    x0 = R_JUGAR.right - 20 - 7 * 44                 # la semana alrededor del día: la casilla del centro es hoy
    for i in range(7):
        d = fecha + timedelta(days=i - 3)
        rc = pygame.Rect(x0 + i * 44, R_JUGAR.y + 14, 40, 54)
        centro = i == 3
        pygame.draw.rect(screen, (40, 60, 95) if centro else (20, 26, 46), rc, border_radius=6)
        if centro:
            pygame.draw.rect(screen, dorado, rc, width=2, border_radius=6)
        s1 = get_font('sm').render(_cal.DIAS_SEM[d.weekday()], True, azul)
        s2 = get_font('md').render(str(d.day), True, (255, 255, 255) if centro else (150, 160, 180))
        screen.blit(s1, s1.get_rect(center=(rc.centerx, rc.y + 13)))
        screen.blit(s2, s2.get_rect(center=(rc.centerx, rc.y + 37)))
    barra = pygame.Rect(R_JUGAR.x + 20, R_JUGAR.bottom - 10, R_JUGAR.width - 40, 4)
    pygame.draw.rect(screen, (30, 40, 60), barra, border_radius=2)
    pygame.draw.rect(screen, dorado, pygame.Rect(barra.x, barra.y, barra.width * min(k, total) // max(1, total), 4),
                     border_radius=2)


def _avanzar_un_dia(estado) -> None:
    """v0.4.12.0: +1 DÍA (tecla D). Pasa un día y avisa lo que llegó; el día de un partido no hace nada."""
    try:
        from alpha_football import dias as _dias
        if _dias.es_dia_de_continuar(estado):
            _toast(estado, _dias.texto_resumen(_dias.avanzar_dia(estado)), color='azul')
            from alpha_football import noticias as _noticias
            _noticias.reiniciar_feed(estado)
    except Exception as e_dias:
        logger.error(f"Error al avanzar un día: {e_dias}")


def _avanzar_hora(estado) -> None:
    """v0.4.14.0: AVANZAR 1 HORA el último día. Cancela una confirmación de cierre pendiente."""
    try:
        from alpha_football import dia_final as _DF
        estado.pop('confirmar_cierre_mercado', None)
        if _DF.activo(estado):
            _toast(estado, _DF.texto_hora(_DF.avanzar_hora(estado)), color='azul')
            from alpha_football import noticias as _noticias
            _noticias.reiniciar_feed(estado)   # v0.4.25.0: cada hora del último día trae noticias nuevas
    except Exception as e_df:
        logger.error(f"Error al avanzar una hora: {e_df}")


def _momento_cierre(estado) -> list:
    """[día, horas que quedan]: el momento del último día en que se pide la confirmación de cierre."""
    from alpha_football import dia_final as _DF
    return [_DF._hoy_iso(estado), _DF.horas(estado)]


def _cierre_pedido(estado) -> bool:
    """v0.4.14.0: ¿sigue en pie la confirmación de CERRAR MERCADO? Solo si no pasó ni una hora ni un día desde
    que se pidió (también la cancelan cambiar de pestaña y salir del hub: render)."""
    try:
        if estado.get('confirmar_cierre_mercado') == _momento_cierre(estado):
            return True
    except Exception as e_df:
        logger.error(f"Error al leer la confirmación de cierre: {e_df}")
    estado.pop('confirmar_cierre_mercado', None)
    return False


def _pedir_cierre(estado) -> None:
    """v0.4.14.0: CERRAR MERCADO: la primera vez pide confirmación; la segunda (Enter, C o clic) cierra."""
    try:
        from alpha_football import dia_final as _DF
        if not _DF.activo(estado):
            return
        if _cierre_pedido(estado):
            estado.pop('confirmar_cierre_mercado', None)
            _DF.cerrar(estado)
            _toast(estado, "Mercado cerrado", color='rojo')
        else:
            estado['confirmar_cierre_mercado'] = _momento_cierre(estado)
    except Exception as e_df:
        logger.error(f"Error al cerrar el mercado: {e_df}")


def _accion_jugar(estado, partido_usuario, esta_finalizada, fase_copa) -> Optional[str]:
    """JUGAR: primero la copa si toca, después la liga o el cierre de temporada."""
    try:   # v0.4.14.0: el último día, JUGAR avanza una hora (o confirma el cierre si estaba pedido)
        from alpha_football import dia_final as _DF
        if _DF.activo(estado):
            if _cierre_pedido(estado):
                _pedir_cierre(estado)
            else:
                _avanzar_hora(estado)
            return None
    except Exception as e_df:
        logger.error(f"Error en el último día: {e_df}")
    try:   # v0.4.12.0: sin partido hoy, JUGAR corre los días hasta que pase algo
        from alpha_football import dias as _dias
        if _dias.es_dia_de_continuar(estado):
            _iniciar_avance(estado)        # v0.4.14.1: los días pasan a la vista, uno por cuadro (render)
            return None
    except Exception as e_dias:
        logger.error(f"Error al continuar los días: {e_dias}")
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


def _nombre_dt_rival(estado: Optional[dict], equipo) -> str:
    """Nombre del DT del club (el del motor de DTs, el puesto en el editor o el estilo como último recurso)."""
    try:
        from alpha_football import entrenadores as EN
        dt = EN.dt_de(estado or {}, equipo)
        if dt and dt.get('nombre'):
            return dt['nombre']
    except Exception as e:
        logger.error(f"No se pudo leer el DT de {getattr(equipo, 'nombre', '?')}: {e}")
    return getattr(equipo, 'dt_nombre', '') or (getattr(equipo, 'estilo_dt', '') or '?').capitalize()


def _nivel(equipo) -> int:
    """Media del mejor once actual (la media de toda la plantilla la bajan los juveniles)."""
    try:
        from alpha_football.market import nivel_club
        return nivel_club(equipo)
    except Exception as e:
        logger.error(f"No se pudo calcular el nivel de {getattr(equipo, 'nombre', '?')}: {e}")
        return int(getattr(equipo, 'ovr_promedio', 0) or 0)


def _textos_jugar(liga, mi_equipo, info, estado: Optional[dict] = None) -> tuple:
    """(línea grande, línea 2, línea 3, habilitado) del botón JUGAR."""
    try:   # v0.4.12.0: sin partido hoy, el botón grande es CONTINUAR
        from alpha_football import dias as _dias
        t = _dias.textos_hub(estado) if estado else None
        if t:
            return t[0], t[1], t[2], True
    except Exception as e_dias:
        logger.error(f"Error en los textos de CONTINUAR: {e_dias}")
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
    from alpha_football.ui.postpartido import posicion_liga
    puesto = posicion_liga(liga, op_id) if op is not None else 0
    l2 = (f"LIGA · J{partido_usuario.jornada} vs {getattr(op, 'nombre', '?')[:24]}"
          + (f" ({puesto}º)" if puesto else "") + f" · {'LOCAL' if es_local else 'VISITANTE'}")
    l3 = (f"DT {_nombre_dt_rival(estado, op)[:22]}  ·  OVR {_nivel(op) if op is not None else '?'}  ·  "
          f"Tu OVR {_nivel(mi_equipo)}")
    return "JUGAR", l2, l3, True


class _TablaDibujada(Exception):
    """v3.8.0: corta el bloque de la tabla de liga cuando se dibujó la de copa."""


def rect_tab_tabla(clave: str) -> pygame.Rect:
    """v3.8.0: pestañas LIGA / COPA arriba a la derecha del panel de la tabla. v0.4.23.0: NOTICIAS a su izquierda."""
    if clave == 'noticias':
        return pygame.Rect(R_TABLA.right - 324, R_TABLA.y + 8, 104, 28)
    return pygame.Rect(R_TABLA.right - 212 + (0 if clave == 'liga' else 104), R_TABLA.y + 8, 96, 28)


# --- v0.4.23.0: feed de noticias en el panel de la tabla -------------------------------------------------
INTERVALO_FEED_MS = 5000          # la ventana de tarjetas corre una noticia cada 5 s
FUNDIDO_MS = 180                  # fundido de entrada al cambiar a la pestaña NOTICIAS
VISIBLES_FEED = 3                 # v0.4.25.0: tarjetas a la vez (la más reciente a la izquierda)
HUECO_FEED = 12
R_TARJETA_FEED = pygame.Rect(R_TABLA.centerx - 99, R_TABLA.y + 40, 198, 352)    # 9:16 bajo la fila de pestañas (la del centro)


def rects_feed(n: int) -> list:
    """Los rectángulos de las `n` (0-3) tarjetas visibles, de izquierda (la más reciente) a derecha y centrados en
    el panel: con una sola, R_TARJETA_FEED."""
    n = max(0, min(VISIBLES_FEED, int(n)))
    ancho, alto = R_TARJETA_FEED.size
    x0 = R_TABLA.centerx - (n * ancho + max(0, n - 1) * HUECO_FEED) // 2
    return [pygame.Rect(x0 + k * (ancho + HUECO_FEED), R_TARJETA_FEED.y, ancho, alto) for k in range(n)]


def feed_actual(estado: dict, ahora: int) -> tuple:
    """(noticias del feed, índice de la primera tarjeta visible). Se ven VISIBLES_FEED a la vez, la más reciente a la
    izquierda: arrancan las 3 últimas y, cada INTERVALO_FEED_MS (`ahora` en ms), la ventana corre una hacia las más
    viejas; al llegar a la más vieja vuelve a empezar. Vuelve al principio cuando llega una noticia nueva o cuando el
    juego se detiene (`noticias.reiniciar_feed`). `noticias.para_feed` recorre el calendario, así que la lista se
    guarda en `estado` y solo se recalcula al rotar o si cambia la lista."""
    from alpha_football import noticias as _N
    lista = _N.lista(estado)
    ultima = lista[0]['id'] if lista else None
    if estado.get('_feed_ultima') != ultima:          # llegó una noticia nueva: se empieza por ella
        estado['_feed_ultima'] = ultima
        estado['feed_t0'] = ahora
    t0 = estado.setdefault('feed_t0', ahora)
    paso = max(0, (ahora - t0) // INTERVALO_FEED_MS)
    clave = (len(lista), ultima)
    cache = estado.get('_feed_cache')
    if not cache or cache[0] != clave or cache[1] != paso:
        cache = (clave, paso, _N.para_feed(estado))
        estado['_feed_cache'] = cache
    feed = cache[2]
    posiciones = max(1, len(feed) - VISIBLES_FEED + 1)
    return feed, (paso % posiciones if feed else 0)


def noticia_del_feed_en(estado: dict, pos, ahora: Optional[int] = None) -> Optional[dict]:
    """La noticia cuya tarjeta del feed está en `pos` (None si el clic no cae en ninguna)."""
    feed, s = feed_actual(estado, pygame.time.get_ticks() if ahora is None else int(ahora))
    visibles = feed[s:s + VISIBLES_FEED]
    for n, r in zip(visibles, rects_feed(len(visibles))):
        if r.collidepoint(pos):
            return n
    return None


TABLA_TAB_INICIAL = 'noticias'     # v0.4.26.0: el panel de INICIO abre en NOTICIAS mientras no se elija otra pestaña


def _tabla_tab(estado: dict) -> str:
    """Pestaña activa del panel de la tabla de INICIO: la elegida o, sin elección todavía, NOTICIAS."""
    guardada = estado.get('hub_tabla_tab') or TABLA_TAB_INICIAL
    return guardada if guardada in ('copa', 'noticias') else 'liga'


def alternar_noticias(estado: dict, ahora: Optional[int] = None) -> None:
    """Tecla N: noticias ↔ la pestaña anterior de la tabla (LIGA o COPA), con fundido."""
    ahora = pygame.time.get_ticks() if ahora is None else int(ahora)
    actual = _tabla_tab(estado)
    if actual == 'noticias':
        estado['hub_tabla_tab'] = estado.get('hub_tabla_prev') if estado.get('hub_tabla_prev') in ('liga', 'copa') else 'liga'
    else:
        estado['hub_tabla_prev'] = 'copa' if actual == 'copa' else 'liga'
        estado['hub_tabla_tab'] = 'noticias'
    estado['feed_fade_ms'] = ahora
    estado['feed_t0'] = ahora        # la tarjeta arranca desde la primera


def _fijar_tabla_tab(estado: dict, clave: str, ahora: Optional[int] = None) -> None:
    """Clic en una pestaña de la tabla; LIGA y COPA se recuerdan para volver con la tecla N."""
    if clave == 'noticias':
        if _tabla_tab(estado) != 'noticias':
            alternar_noticias(estado, ahora)
        return
    estado['hub_tabla_tab'] = clave
    estado['hub_tabla_prev'] = clave


def _render_feed(screen, estado: dict, ahora: int) -> None:
    """Contenido del panel de la tabla en la pestaña NOTICIAS: tres tarjetas a la vez, las más recientes primero
    (a la izquierda); la ventana corre hacia las más viejas y vuelve a empezar en cada parada del juego."""
    from alpha_football.ui import noticias_visual as V
    draw_text(screen, "NOTICIAS", (32, R_TABLA.y + 10), size='md', color='azul')
    feed, s = feed_actual(estado, ahora)
    cuerpo = pygame.Rect(R_TABLA.x, R_TABLA.y + 40, R_TABLA.width, R_TABLA.height - 40)
    if not feed:
        draw_text(screen, "Sin noticias destacadas.", (R_TABLA.centerx - 110, R_TABLA.centery - 20), size='md', color='blanco')
        draw_text(screen, "Se publican con cada jornada.", (R_TABLA.centerx - 118, R_TABLA.centery + 14), size='sm', color='azul')
    else:
        visibles = feed[s:s + VISIBLES_FEED]
        cuenta = (f"{len(feed)} noticia{'s' if len(feed) != 1 else ''}" if len(feed) <= VISIBLES_FEED
                  else f"{s + 1}-{s + len(visibles)} / {len(feed)}")
        draw_text(screen, cuenta, (172, R_TABLA.y + 14), size='sm', color='azul', shadow=False)
        for noticia, r in zip(visibles, rects_feed(len(visibles))):
            screen.blit(V.tarjeta(noticia, r.w, r.h), r.topleft)
            pygame.draw.rect(screen, COLORS.get('dorado', (255, 215, 0)), r, width=2)
    t = ahora - int(estado.get('feed_fade_ms', -FUNDIDO_MS) or 0)
    if 0 <= t < FUNDIDO_MS:          # fundido de entrada: un velo del color del panel que se va aclarando
        velo = pygame.Surface(cuerpo.size, pygame.SRCALPHA)
        velo.fill((20, 26, 46, 255 - 255 * t // FUNDIDO_MS))
        screen.blit(velo, cuerpo.topleft)


def _dibujar_tabs_tabla(screen, activa: str, mouse_pos) -> None:
    for clave, texto in (('noticias', "NOTICIAS"), ('liga', "LIGA"), ('copa', "COPA")):
        r = rect_tab_tabla(clave)
        on = clave == activa
        pygame.draw.rect(screen, COLORS.get('azul', (0, 191, 255)) if on else
                         ((30, 45, 75) if r.collidepoint(mouse_pos) else (15, 22, 40)), r, border_radius=6)
        pygame.draw.rect(screen, COLORS.get('dorado', (255, 215, 0)) if on else COLORS.get('azul', (0, 191, 255)),
                         r, width=1, border_radius=6)
        s = get_font('sm').render(texto, True, COLORS.get('bg', (10, 14, 26)) if on else COLORS.get('blanco', (255, 255, 255)))
        screen.blit(s, s.get_rect(center=r.center))


R_VER_COPA = pygame.Rect(R_TABLA.centerx - 130, R_TABLA.centery - 24, 260, 48)    # v0.4.26.0


def _sin_copa_continental(estado: dict) -> bool:
    """v0.4.26.0: True si tu club no juega la copa continental de la temporada (no clasificó o está en 2ª)."""
    try:
        from alpha_football import competiciones as CP
        return CP.tipo_copa_user(estado) is None
    except Exception as e:
        logger.error(f"Error al ver si juegas la copa continental: {e}")
        return False


def _abrir_copa_en_otras_ligas(estado: dict) -> str:
    """v0.4.26.0: VER COPA lleva a Otras ligas › Copas, con la copa de tu continente elegida."""
    from alpha_football.ui import copa_screen as S
    estado['otras_ligas_copas'] = True
    estado['otras_ligas_copa_sel'] = S.copa_de_region(estado)
    return 'otras_ligas_screen'


def _render_tabla_copa(screen, estado, mouse_pos=(0, 0)) -> None:
    """v3.8.0: tabla de la fase de liga (Champions) o tu grupo / los grupos (Libertadores).
    v0.4.26.0: si tu club no juega la copa, solo el botón VER COPA."""
    from alpha_football import competiciones as CP
    from alpha_football.ui import copa_screen as S
    tipo = S.copa_de_region(estado)
    c = CP.copa(estado, tipo)
    user = getattr(estado.get('mi_equipo'), 'nombre', '')
    draw_text(screen, CP.NOMBRE_COPA.get(tipo, 'COPA').upper(), (32, R_TABLA.y + 10), size='md', color='azul')
    if _sin_copa_continental(estado):
        draw_button(screen, R_VER_COPA, "VER COPA", R_VER_COPA.collidepoint(mouse_pos))
        return
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
    tabla_tab = _tabla_tab(estado)   # v0.4.23.0: + noticias; v0.4.26.0: NOTICIAS es la pestaña inicial
    try:
        draw_panel(screen, R_TABLA)
        _dibujar_tabs_tabla(screen, tabla_tab, mouse_pos)
        if tabla_tab == 'noticias':
            _render_feed(screen, estado, pygame.time.get_ticks())
            raise _TablaDibujada()
        if tabla_tab == 'copa':
            _render_tabla_copa(screen, estado, mouse_pos)
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
    l1, l2, l3, habilitado = _textos_jugar(liga, mi_equipo, info, estado)
    try:
        hover = R_JUGAR.collidepoint(mouse_pos) and habilitado
        draw_styled_button(screen, R_JUGAR, "", hover or foco == 0, COLORS.get('verde', (0, 255, 136)), habilitado)
        if foco == 0 and not hover:
            pygame.draw.rect(screen, dorado, R_JUGAR, width=3, border_radius=8)
        draw_text(screen, l1, (R_JUGAR.x + 20, R_JUGAR.y + 10), size='lg',
                  color='verde' if habilitado else 'blanco')
        try:   # v0.4.11.0: fecha del partido, arriba a la derecha del botón
            from alpha_football import calendario as _cal_j
            if habilitado and l1 == "CONTINUAR":
                _txt_fecha = ""                                 # v0.4.13.0: la fecha y la fase van en la línea 2
            else:
                _txt_fecha = _cal_j.texto_proximo(estado) if habilitado and l1 == "JUGAR" else ""
            if _txt_fecha:
                _w_fecha = get_font('sm').size(_txt_fecha)[0]
                draw_text(screen, _txt_fecha, (R_JUGAR.right - 20 - _w_fecha, R_JUGAR.y + 16), size='sm', color='dorado')
        except Exception as e_fecha:
            logger.error(f"Error al dibujar la fecha del partido: {e_fecha}")
        if l1 == "ÚLTIMO DÍA":     # v0.4.14.0: la fecha y las horas van arriba a la derecha (abajo están los botones)
            draw_text(screen, l2, (R_JUGAR.right - 20 - get_font('sm').size(l2)[0], R_JUGAR.y + 16), size='sm',
                      color='dorado')
        else:
            draw_text(screen, l2, (R_JUGAR.x + 20, R_JUGAR.y + 48), size='sm',
                      color='dorado' if (fase_copa or l1 == "CONTINUAR") else 'blanco')
        if l3:
            draw_text(screen, l3, (R_JUGAR.x + 20, R_JUGAR.y + 70), size='sm', color='azul')
        if l1 == "CONTINUAR":      # v0.4.12.0: avanzar de a un día
            pygame.draw.rect(screen, (30, 45, 75) if R_DIA.collidepoint(mouse_pos) else (15, 22, 40), R_DIA, border_radius=6)
            pygame.draw.rect(screen, COLORS.get('azul', (0, 191, 255)), R_DIA, width=1, border_radius=6)
            _s_dia = get_font('sm').render("+1 DÍA", True, (255, 255, 255))
            screen.blit(_s_dia, _s_dia.get_rect(center=R_DIA.center))
        if l1 == "ÚLTIMO DÍA":      # v0.4.14.0: AVANZAR 1 HORA y CERRAR MERCADO
            for _rb, _tb in ((R_HORA, "AVANZAR 1 HORA"),
                             (R_CERRAR, "¿CERRAR? ENTER" if _cierre_pedido(estado) else "CERRAR MERCADO")):
                pygame.draw.rect(screen, (30, 45, 75) if _rb.collidepoint(mouse_pos) else (15, 22, 40), _rb, border_radius=6)
                pygame.draw.rect(screen, COLORS.get('dorado', (255, 215, 0)), _rb, width=1, border_radius=6)
                _sb = get_font('sm').render(_tb, True, (255, 255, 255))
                screen.blit(_sb, _sb.get_rect(center=_rb.center))
    except Exception as e_jugar:
        logger.error(f"Error al dibujar JUGAR: {e_jugar}")
    try:   # v0.4.14.1: los días de CONTINUAR pasando sobre el botón
        _anim = avance_visible(estado)
        if _anim:
            _dibujar_avance(screen, _anim)
    except Exception as e_anim:
        logger.error(f"Error al dibujar el avance de los días: {e_anim}")

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
        draw_text(screen, f"OVR {_nivel(mi_equipo)}  ·  Plantilla {len(mi_equipo.jugadores)}  ·  "
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
        if rect_tab_tabla('noticias').collidepoint(click_pos):         # v0.4.23.0
            _fijar_tabla_tab(estado, 'noticias')
        elif rect_tab_tabla('liga').collidepoint(click_pos):
            _fijar_tabla_tab(estado, 'liga')
        elif rect_tab_tabla('copa').collidepoint(click_pos):
            _fijar_tabla_tab(estado, 'copa')
        elif tabla_tab == 'copa' and R_VER_COPA.collidepoint(click_pos) and _sin_copa_continental(estado):
            return _abrir_copa_en_otras_ligas(estado)                  # v0.4.26.0: VER COPA
        elif tabla_tab == 'noticias' and noticia_del_feed_en(estado, click_pos) is not None:
            from alpha_football.ui import noticias_screen as _NS
            return _NS.abrir(estado, noticia_del_feed_en(estado, click_pos)['id'])
        elif l1 == "ÚLTIMO DÍA" and R_HORA.collidepoint(click_pos):      # v0.4.14.0
            estado['hub_foco'] = 0
            _avanzar_hora(estado)
        elif l1 == "ÚLTIMO DÍA" and R_CERRAR.collidepoint(click_pos):
            estado['hub_foco'] = 0
            _pedir_cierre(estado)
        elif l1 == "CONTINUAR" and R_DIA.collidepoint(click_pos):      # v0.4.12.0
            estado['hub_foco'] = 0
            _avanzar_un_dia(estado)
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


def _ajustar_texto(texto: str, fuente, ancho: int) -> str:
    """v0.4.23.0: el texto recortado con "…" para que quepa en `ancho` px (las tarjetas de 3 columnas son más angostas)."""
    texto = str(texto)
    if fuente.size(texto)[0] <= ancho:
        return texto
    while texto and fuente.size(texto + "…")[0] > ancho:
        texto = texto[:-1]
    return texto.rstrip() + "…"


def _no_leidas_noticias(estado) -> int:
    """v0.4.23.0: contador de la tarjeta NOTICIAS. `noticias.no_leidas` recorre el calendario, así que solo se
    recalcula cuando cambia la lista (alta, baja o una noticia leída); por cuadro solo se cuentan ≤ 50 dicts."""
    from alpha_football import noticias as _N
    lista = _N.lista(estado)
    clave = (len(lista), lista[0]['id'] if lista else None, sum(1 for n in lista if n.get('leida')))
    cache = estado.get('_hub_no_leidas_noticias')
    if not cache or cache[0] != clave:
        cache = (clave, _N.no_leidas(estado))
        estado['_hub_no_leidas_noticias'] = cache
    return cache[1]


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
        try:  # v3.4.0: badge de OFERTAS DT (v4.7.0: + la oferta por calificación)
            from alpha_football.ui.ofertas_dt_screen import filas as _filas_dt
            n_ofertas_dt = len(_filas_dt(estado))
        except Exception as e_odt:
            logger.error(f"Error al contar las ofertas de banquillo: {e_odt}")
            n_ofertas_dt = 0
        for i, ((titulo, sub, destino), rect) in enumerate(zip(tarjetas, rects)):
            hover = rect.collidepoint(mouse_pos)
            draw_styled_button(screen, rect, "", hover or i == foco, COLORS.get('azul', (0, 191, 255)))
            if i == foco and not hover:
                pygame.draw.rect(screen, COLORS.get('dorado', (255, 215, 0)), rect, width=3, border_radius=8)
            tam_titulo = 'lg' if get_font('lg').size(titulo)[0] <= rect.width - 48 else 'md'    # v0.4.23.0: tarjetas de 392 px
            draw_text(screen, titulo, (rect.x + 24, rect.y + (40 if tam_titulo == 'lg' else 44)), size=tam_titulo, color='blanco')
            draw_text(screen, _ajustar_texto(sub, get_font('sm'), rect.width - 48), (rect.x + 24, rect.y + 90),
                      size='sm', color='azul')
            n_badge = n_ofertas if destino == 'ofertas_screen' else (n_correo if destino == 'notificaciones_screen' else 0)
            if destino == 'ofertas_dt_screen':     # v3.4.0
                n_badge = n_ofertas_dt
            elif destino == 'noticias_screen':     # v0.4.23.0
                n_badge = _no_leidas_noticias(estado)
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

        # v0.4.17.0: gala del Balón de Oro / Sudamericano del Año (solo si alguien del podio es de tu club)
        if (estado.get('datos_carrera') or {}).get('gala_premio_pendiente'):
            return 'gala_balon_screen'

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

        try:  # v2.9.0: contratos para toda la partida (una vez; saves viejos incluidos)
            dc = estado.setdefault('datos_carrera', {})
            from alpha_football.finanzas import asegurar_contratos, migrar_economia
            if not dc.get('contratos_v290'):
                asegurar_contratos(estado)
                dc['contratos_v290'] = True
                dc['economia_v2'] = True          # v4.6.0: carrera nueva: ya nace con los sueldos nuevos
            else:
                migrar_economia(estado)           # v4.6.0: save viejo: sueldos ×1.6 una sola vez
        except Exception as e_con:
            logger.error(f"Error al asignar contratos: {e_con}")
        try:  # v0.4.25.0: partidas guardadas con clubes por encima del techo (hoy 350 M€; el reloj lo repite cada día)
            dc = estado.setdefault('datos_carrera', {})
            if not dc.get('techo_presupuesto_v0425'):
                from alpha_football.finanzas import limitar_presupuestos
                limitar_presupuestos(estado)
                dc['techo_presupuesto_v0425'] = True
        except Exception as e_techo:
            logger.error(f"Error al limitar los presupuestos: {e_techo}")
        try:  # v2.8.0 (v4.6.0: después de migrar sueldos): objetivo de la temporada (una vez por temporada / club)
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

        info = _info_partido(estado, liga, mi_equipo)
        partido_usuario, esta_finalizada, fase_copa, _rival = info
        jugados = sorted(
            (p for p in getattr(liga, 'calendario', [])
             if p.jugado and mi_equipo.id in (p.local_id, p.visitante_id)),
            key=lambda p: p.jornada, reverse=True)
        max_offset = max(0, len(partidos_historial(estado)) - PARTIDOS_VISIBLES)   # v4.3.0: liga + copa

        tab = estado.get('hub_tab') if estado.get('hub_tab') in PESTANAS else 'inicio'
        # v0.4.11.0: pestaña abierta desde un mensaje; si ya está en otra, no vuelve al correo
        if estado.get('volver_notif') == 'league_screen' and tab != estado.get('volver_notif_tab'):
            estado.pop('volver_notif', None)
        bar_foco = int(estado.get('hub_bar_foco', 0)) % len(BARRA_MENU)
        # Al volver de otra pantalla (o de OPCIONES/GUARDAR) el foco vuelve a la pestaña activa.
        if bar_foco >= len(PESTANAS) or PESTANAS[bar_foco] != tab:
            bar_foco = PESTANAS.index(tab)
        foco = int(estado.get('hub_foco', 0))
        # v3.6.0: al volver de la copa / un partido, el foco queda en JUGAR (y nunca fuera de rango)
        anterior = estado.pop('pantalla_anterior', None)
        if anterior is not None:       # v0.4.14.0: se vuelve de otra pantalla: la confirmación de cierre ya no vale
            estado.pop('confirmar_cierre_mercado', None)
        if tab == 'inicio' and (anterior in VUELVEN_A_JUGAR or foco not in (0, 1)):
            foco, bar_foco = 0, 0

        try:  # v0.4.11.0: la primera vez que se ve el calendario de la temporada, revisa los choques
            from alpha_football import calendario as _cal
            _c = _cal.asegurar(estado)
            if not _c.get('revisado'):
                _c['revisado'] = True
                _cal.revisar_choques(estado)
        except Exception as e_cal:
            logger.error(f"Error preparando el calendario: {e_cal}")

        try:  # v0.4.12.0: el reloj del juego (hoy) nace aquí, al abrir el hub de la temporada
            from alpha_football import dias as _dias_r
            _dias_r.hoy(estado)
        except Exception as e_dia:
            logger.error(f"Error creando el reloj del juego: {e_dia}")

        try:  # v0.4.14.0: un save cargado un día de cierre con el mercado abierto arranca con 20 horas
            from alpha_football import dia_final as _DF_r
            _DF_r.abrir(estado)
        except Exception as e_df:
            logger.error(f"Error abriendo el último día: {e_df}")

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

        # v0.4.14.1: CONTINUAR avanza a la vista, un día por cuadro; una tecla o un clic lo detiene ahí
        animando = bool(estado.get('hub_avance'))
        if animando and (key_events or click_pos or tab != 'inicio'):
            _terminar_avance(estado)
            animando, key_events, click_pos = False, [], None
        elif animando:
            animando = _paso_avance(estado)

        try:  # v4.4.0: cartel de apertura/cierre del mercado (consume teclas y clics mientras está abierto)
            from alpha_football.ui import aviso_mercado as _am
            destino_am, key_events, click_pos = _am.manejar(estado, key_events, click_pos,
                                                            dialogo_visible or animando)   # espera a la animación
            if destino_am:
                _guardar_foco()
                return _abrir(estado, destino_am)
        except Exception as e_am:
            logger.error(f"Error en el aviso de mercado: {e_am}")

        # --- Teclado ---
        for ev in key_events:
            if ev.key == pygame.K_j:
                _guardar_foco()
                return _accion_jugar(estado, partido_usuario, esta_finalizada, fase_copa)
            if ev.key == pygame.K_n and tab == 'inicio':     # v0.4.23.0: noticias ↔ tabla
                alternar_noticias(estado)
                continue
            if ev.key == pygame.K_d and tab == 'inicio':     # v0.4.12.0: +1 DÍA
                _avanzar_un_dia(estado)
                continue
            if ev.key == pygame.K_c and tab == 'inicio':     # v0.4.14.0: CERRAR MERCADO
                _pedir_cierre(estado)
                continue
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
                if tab != 'inicio' and estado.get('volver_notif') == 'league_screen':   # v0.4.11.0
                    estado.pop('volver_notif', None)
                    tab, bar_foco, foco = 'inicio', 0, 0
                    _guardar_foco()
                    return 'correo_screen'
                if tab != 'inicio':
                    tab, bar_foco, foco = 'inicio', 0, 0
                else:
                    estado['dialogo_salir'] = True       # v3.6.0: ¿salir? en vez de salir directo
                    dialogo_visible = True
                    break

        # v4.2.0: clic en el sobre de correo
        if click_pos and R_SOBRE.collidepoint(click_pos):
            _guardar_foco()
            return 'notificaciones_screen'

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
        if tab != 'inicio':            # v0.4.14.0: en otra pestaña la confirmación de cierre se cancela
            estado.pop('confirmar_cierre_mercado', None)

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
            from alpha_football.ui.aviso_mercado import fecha_corta     # v0.4.13.0: la fecha primero; la jornada, chica
            cabecera = (f"{_nombre_liga(liga.tipo, getattr(liga, 'division', 1) or 1).upper()[:32]}  ·  {mi_equipo.nombre[:22]}  ·  "
                        f"{'2ª' if es_segunda else '1ª'} Div.  ·  T{estado.get('temporada', 1)}  ·  "
                        f"{fecha_corta(estado)} · J{getattr(liga, 'jornada_actual', 1)}/{getattr(liga, 'num_jornadas', 14)}  ·  "
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
