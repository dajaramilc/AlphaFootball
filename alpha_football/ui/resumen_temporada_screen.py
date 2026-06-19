# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Pantalla de Resumen de Temporada.
Muestra felicitaciones si el usuario quedó campeón, la tabla final, estadísticas individuales (MVP, goleadores, asistencias, vallas invictas)
y permite avanzar de forma segura a la temporada 2 (reiniciando stats y fixtures).
"""
from __future__ import annotations

import logging
import pygame
from typing import Optional

try:
    from alpha_football.ui.theme import (
        SCREEN_W, SCREEN_H, COLORS, get_font, draw_gradient_bg, draw_panel, draw_button, draw_text
    )
except Exception:
    SCREEN_W, SCREEN_H = 1280, 720
    COLORS = {
        'bg': (10, 14, 26), 'verde': (0, 255, 136), 'dorado': (255, 215, 0),
        'rojo': (255, 68, 68), 'azul': (0, 191, 255), 'blanco': (255, 255, 255), 'panel': (20, 26, 46)
    }
    def get_font(size): return pygame.font.Font(None, 24)
    def draw_gradient_bg(screen): screen.fill((10, 14, 26))
    def draw_panel(screen, rect): pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=8)
    def draw_button(screen, rect, text, hover): 
        pygame.draw.rect(screen, (20, 26, 46), rect, border_radius=6)
        return rect
    def draw_text(screen, text, pos, size='md', color='blanco', shadow=True): pass

logger = logging.getLogger(__name__)


def avanzar_nueva_temporada(estado: dict) -> None:
    """Restablece los fixtures, jornadas, estadísticas de liga y avanza a la siguiente temporada."""
    try:
        liga = estado.get('liga')
        mi_equipo = estado.get('mi_equipo')
        if not liga or not mi_equipo:
            return

        # 1. Incrementar la temporada actual en la sesión
        temp_anterior = estado.get('temporada', 1)
        nueva_temp = temp_anterior + 1
        estado['temporada'] = nueva_temp

        # 2. Guardar registro en el historial de campañas (Career Screen)
        try:
            # Ordenar para ver la posición final del usuario
            def clave_tabla(eq):
                dg = getattr(eq, 'gf', 0) - getattr(eq, 'gc', 0)
                return (getattr(eq, 'puntos', 0), dg, getattr(eq, 'gf', 0))
            equipos_ord = sorted(liga.equipos, key=clave_tabla, reverse=True)
            posicion = next((idx + 1 for idx, s in enumerate(equipos_ord) if s.id == mi_equipo.id), 1)
            
            registro = {
                "temporada": temp_anterior,
                "equipo": mi_equipo.nombre,
                "posicion": posicion,
                "puntos": mi_equipo.puntos,
                "pg": mi_equipo.pg,
                "pe": mi_equipo.pe,
                "pp": mi_equipo.pp
            }
            estado.setdefault('historial', []).append(registro)
        except Exception as e_hist:
            logger.error(f"Error al guardar historial de campaña: {e_hist}")

        # 3. Limpiar estadísticas de todos los equipos y jugadores de la liga
        for eq in liga.equipos:
            eq.puntos = 0
            eq.pj = 0
            eq.pg = 0
            eq.pe = 0
            eq.pp = 0
            eq.gf = 0
            eq.gc = 0
            
            for j in eq.jugadores:
                j.goles = 0
                j.asistencias = 0
                j.partidos_jugados = 0
                j.porterias_cero = 0
                j.moral = max(70, j.moral) # Restaurar moral a buen nivel base
                j.lesion_partidos = 0
                j.partidos_sancion = 0

        # 4. Limpiar el calendario de partidos para obligar a regenerar un fixture nuevo
        liga.calendario = []
        liga.jornada_actual = 1

        # 5. Reiniciar la Copa Internacional para la nueva temporada
        estado.pop('copa_fase_actual', None)
        estado.pop('copa_tab', None)
        estado.pop('copa_jornada_grupo', None)
        estado.pop('copa_grupo_standing', None)
        estado.pop('copa_bracket', None)
        estado.pop('copa_grupo_partidos', None)

        # 6. Autoguardar la partida de forma automática y atómica en el slot activo
        try:
            from alpha_football import save as _save
            from alpha_football.models import EstadoJuego
            
            alin = estado.get('alineacion_activa')
            datos_estado = {
                "ligas": [liga.to_dict()],
                "copas": [],
                "equipo_usuario_id": mi_equipo.id,
                "liga_usuario_id": liga.tipo,
                "temporada": nueva_temp,
                "historial": estado.get("historial", []),
                "transfer_log": estado.get("transfer_log", []),
                "pantalla_actual": "temporada",
                "alineacion_activa": {
                    "titulares": list(alin.titulares),
                    "formacion": str(alin.formacion)
                } if alin else None,
                "dt_nombre": estado.get("dt_nombre", ""),
                "dt_nacionalidad": estado.get("dt_nacionalidad", "")
            }
            estado_juego = EstadoJuego.from_dict(datos_estado)
            slot = estado.get('slot_activo', 1)
            nombre_save = f"{mi_equipo.corto} (T{nueva_temp} J1)"
            _save.guardar_en_slot(estado_juego, slot, nombre_save)
            logger.info(f"Partida autoguardada en slot {slot} al avanzar a Temporada {nueva_temp}.")
        except Exception as e_save:
            logger.error(f"Fallo al autoguardar al avanzar de temporada: {e_save}")

    except Exception as e:
        logger.error(f"Error crítico en avanzar_nueva_temporada: {e}")


def render(screen: pygame.Surface, estado: dict) -> Optional[str]:
    """Renderiza la pantalla de resumen de temporada."""
    try:
        liga = estado.get('liga')
        mi_equipo = estado.get('mi_equipo')
        if not liga or not mi_equipo:
            return "menu"

        # 1. Calcular clasificación final
        def clave_tabla(eq):
            dg = getattr(eq, 'gf', 0) - getattr(eq, 'gc', 0)
            return (getattr(eq, 'puntos', 0), dg, getattr(eq, 'gf', 0))
        equipos_ordenados = sorted(liga.equipos, key=clave_tabla, reverse=True)
        
        campeon = equipos_ordenados[0]
        usuario_es_campeon = (campeon.id == mi_equipo.id)

        # 2. Encontrar estadísticas individuales de jugadores de toda la liga
        todos_jugadores = []
        for eq in liga.equipos:
            for j in eq.jugadores:
                # Guardamos el club junto al jugador para mostrarlo
                todos_jugadores.append((j, eq))

        goleador_j, goleador_eq = max(todos_jugadores, key=lambda x: x[0].goles, default=(None, None))
        asistidor_j, asistidor_eq = max(todos_jugadores, key=lambda x: x[0].asistencias, default=(None, None))
        portero_j, portero_eq = max([x for x in todos_jugadores if x[0].posicion == 'POR'], key=lambda x: x[0].porterias_cero, default=(None, None))
        mvp_j, mvp_eq = max([x for x in todos_jugadores if x[0].partidos_jugados >= 4], key=lambda x: x[0].promedio_nota, default=(None, None))

        # Eventos y clics
        mouse_pos = pygame.mouse.get_pos()
        click_pos = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                click_pos = event.pos

        # Dibujar fondo base
        draw_gradient_bg(screen)

        # Título
        draw_text(screen, "RESUMEN DE LA TEMPORADA", (SCREEN_W // 2 - 260, 35), size='xl', color='azul')

        # Banner de Campeón / Felicitaciones
        banner_rect = pygame.Rect(100, 95, 1080, 100)
        draw_panel(screen, banner_rect)
        if usuario_es_campeon:
            # Felicitaciones neón brillante al usuario por ganar la liga
            pygame.draw.rect(screen, COLORS['verde'], banner_rect, width=3, border_radius=8)
            draw_text(screen, "🏆 ¡¡¡FELICITACIONES, ERES EL CAMPEÓN DE LA LIGA!!! 🏆", (260, 115), size='lg', color='verde')
            draw_text(screen, f"Has llevado a {mi_equipo.nombre} a la cima del fútbol local. ¡Una campaña histórica!", (230, 155), size='sm', color='blanco')
        else:
            # El campeón es otro club de la IA
            draw_text(screen, f"🏆 ¡EL CAMPEÓN ES {campeon.nombre.upper()}! 🏆", (300, 115), size='lg', color='dorado')
            pos_user = next((idx + 1 for idx, eq in enumerate(equipos_ordenados) if eq.id == mi_equipo.id), 1)
            draw_text(screen, f"Tu equipo ({mi_equipo.corto}) finalizó en la posición #{pos_user}. ¡A por la revancha la próxima temporada!", (250, 155), size='sm', color='blanco')

        # PANEL IZQUIERDO: Clasificación Final
        panel_izq = pygame.Rect(100, 220, 520, 360)
        draw_panel(screen, panel_izq)
        draw_text(screen, "CLASIFICACIÓN FINAL 📊", (120, 235), size='md', color='azul')
        
        headers = ["#", "Equipo", "PJ", "DG", "PTS"]
        h_x = [120, 160, 430, 480, 540]
        for h, x in zip(headers, h_x):
            draw_text(screen, h, (x, 275), size='sm', color='dorado')
            
        pygame.draw.line(screen, COLORS['azul'], (120, 295), (600, 295), 1)
        
        # Filas de la clasificación
        for idx, eq in enumerate(equipos_ordenados[:6], 1):
            y = 305 + (idx - 1) * 42
            color_row = 'verde' if eq.id == mi_equipo.id else ('dorado' if idx == 1 else 'blanco')
            
            draw_text(screen, str(idx), (120, y), size='sm', color=color_row)
            draw_text(screen, eq.nombre[:22], (160, y), size='sm', color=color_row)
            draw_text(screen, str(eq.pj), (430, y), size='sm', color=color_row)
            dg = eq.gf - eq.gc
            dg_str = f"+{dg}" if dg > 0 else str(dg)
            draw_text(screen, dg_str, (480, y), size='sm', color=color_row)
            draw_text(screen, str(eq.puntos), (540, y), size='sm', color=color_row)

        # PANEL DERECHO: Premios de la Temporada
        panel_der = pygame.Rect(660, 220, 520, 360)
        draw_panel(screen, panel_der)
        draw_text(screen, "PREMIOS Y DISTINCIONES 🏅", (680, 235), size='md', color='azul')
        
        awards_y = 280
        
        # 1. Goleador
        if goleador_j:
            draw_text(screen, "⭐ BOTA DE ORO (MÁX. GOLEADOR)", (680, awards_y), size='sm', color='dorado')
            g_str = f"{goleador_j.nombre_completo} ({goleador_eq.corto}) — {goleador_j.goles} Goles"
            draw_text(screen, g_str, (680, awards_y + 20), size='sm', color='blanco')
            
        # 2. Asistidor
        if asistidor_j:
            draw_text(screen, "⭐ MÁXIMO ASISTENTE", (680, awards_y + 55), size='sm', color='dorado')
            a_str = f"{asistidor_j.nombre_completo} ({asistidor_eq.corto}) — {asistidor_j.asistencias} Asist."
            draw_text(screen, a_str, (680, awards_y + 75), size='sm', color='blanco')

        # 3. Valla Invicta
        if portero_j:
            draw_text(screen, "⭐ GUANTE DE ORO (VALLAS INVICTAS)", (680, awards_y + 110), size='sm', color='dorado')
            p_str = f"{portero_j.nombre_completo} ({portero_eq.corto}) — {portero_j.porterias_cero} Vallas"
            draw_text(screen, p_str, (680, awards_y + 130), size='sm', color='blanco')

        # 4. MVP Nota
        if mvp_j:
            draw_text(screen, "⭐ JUGADOR MVP (MEJOR RENDIMIENTO)", (680, awards_y + 165), size='sm', color='dorado')
            m_str = f"{mvp_j.nombre_completo} ({mvp_eq.corto}) — Nota: {mvp_j.promedio_nota}"
            draw_text(screen, m_str, (680, awards_y + 185), size='sm', color='blanco')

        # Hito del DT
        dt_text = f"Director Técnico: {estado.get('dt_nombre', 'DT')} ({estado.get('dt_nacionalidad', 'Colombia')})"
        draw_text(screen, dt_text, (680, awards_y + 240), size='sm', color='verde')

        # Botón Avanzar a Temporada 2
        btn_avanzar = pygame.Rect(SCREEN_W // 2 - 200, 615, 400, 52)
        hover_av = btn_avanzar.collidepoint(mouse_pos)
        
        texto_sig_temp = f"EMPEZAR TEMPORADA {estado.get('temporada', 1) + 1}"
        draw_button(screen, btn_avanzar, texto_sig_temp, hover_av)

        if click_pos and btn_avanzar.collidepoint(click_pos):
            avanzar_nueva_temporada(estado)
            return "league_screen"

        return None
    except Exception as e_render:
        logger.error(f"Error al renderizar resumen_temporada_screen: {e_render}")
        return "menu"
