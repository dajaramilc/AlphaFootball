# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Pantalla de Guardado en Slots.
Permite elegir un slot del 1 al 5 para guardar la partida actual antes de salir.
"""
from __future__ import annotations

import logging
import pygame
from typing import Any

# Importación de estilos y utilidades visuales con fallback en caso de error
try:
    from alpha_football.ui.theme import (
        SCREEN_W, SCREEN_H, COLORS, get_font, draw_gradient_bg, draw_panel, draw_button, draw_text
    )
except Exception as e_import:
    logger = logging.getLogger(__name__)
    logger.warning(f"Error al importar el tema visual: {e_import}. Usando fallback local en save_slots_screen.")
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

def render(screen: pygame.Surface, estado: dict) -> str | None:
    """
    Dibuja la interfaz de selección de slots para guardar partida.
    Retorna la siguiente pantalla a cargar, o None para seguir en esta pantalla.
    """
    try:
        from alpha_football import save
        from alpha_football.models import EstadoJuego
    except Exception as e_models:
        logger.critical(f"Error crítico al importar modelos y save: {e_models}. Volviendo al menú principal.")
        # Retorno de fallback seguro para asegurar la continuidad de ejecución
        return "menu"

    try:
        # Obtener los objetos del estado actual
        liga = estado.get('liga')
        mi_equipo = estado.get('mi_equipo')

        # Si no hay partida cargada para guardar, volvemos de inmediato
        if not liga or not mi_equipo:
            logger.warning("No hay partida activa para guardar en save_slots_screen. Retornando al menú.")
            return "menu"

        # Intentar listar las cabeceras de los 5 slots
        try:
            cabeceras = save.listar_slots()
        except Exception as e_list:
            logger.error(f"No se pudieron listar los slots de guardado: {e_list}. Inicializando lista vacía.")
            cabeceras = [None] * 5

        # Capturar la posición del mouse y procesar la cola de eventos del frame
        mouse_pos = pygame.mouse.get_pos()
        click_pos = None

        try:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    # Enviar el evento de salida para que sea procesado por main.py
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
                    return "quit"
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    click_pos = event.pos
        except Exception as e_events:
            logger.error(f"Error en el ciclo de eventos del frame en save_slots_screen: {e_events}")

        # 1. Dibujar el fondo con gradiente
        draw_gradient_bg(screen)
        
        # 2. Dibujar el panel principal centrado
        panel_rect = pygame.Rect(100, 80, 1080, 560)
        draw_panel(screen, panel_rect)

        # 3. Dibujar títulos
        draw_text(screen, "GUARDAR PARTIDA — SELECCIONAR SLOT", (140, 110), size='lg', color='verde')
        draw_text(screen, "Guarda tu progreso de la campaña actual en uno de los 5 slots disponibles.", (140, 145), size='sm', color='blanco')

        # 4. Dibujar la lista de slots
        for i in range(5):
            slot_n = i + 1
            slot_rect = pygame.Rect(140, 190 + i * 70, 520, 52)
            
            hdr = cabeceras[i] if i < len(cabeceras) else None
            es_activo = (estado.get('slot_activo') == slot_n)

            # Etiqueta descriptiva del slot
            if hdr:
                nombre_partida = hdr.get('nombre_partida', 'Partida')
                etiqueta = f"Slot {slot_n}: {nombre_partida}"
                if es_activo:
                    etiqueta += " (Activo)"
            else:
                etiqueta = f"Slot {slot_n}: [Slot Libre]"

            # Dibujar el botón para el slot
            hover_slot = slot_rect.collidepoint(mouse_pos)
            draw_button(screen, slot_rect, etiqueta, hover_slot)

            # Mostrar los detalles de la partida del slot en la columna derecha
            if hdr:
                # v0.8.7.2: dos líneas con DT + equipo y temp/jor/presupuesto
                nombre_dt = hdr.get('dt_nombre', '—')
                nombre_club = hdr.get('equipo_nombre', '—')
                draw_text(screen, f"DT: {nombre_dt}  ·  {nombre_club}",
                          (690, 190 + i * 70 + 6), size='md', color='dorado')
                pres = int(hdr.get('presupuesto', 0) or 0)
                pres_m = pres / 1_000_000
                info_linea = f"Temp {hdr.get('temporada', 1)}  ·  Jor {hdr.get('jornada', 1)}  ·  ${pres_m:.1f}M"
                draw_text(screen, info_linea, (690, 190 + i * 70 + 30), size='sm', color='azul')
            else:
                draw_text(screen, "Espacio vacío y disponible", (690, 190 + i * 70 + 15), size='md', color='blanco')

            # Procesar el click en un slot para realizar el guardado
            if click_pos and slot_rect.collidepoint(click_pos):
                try:
                    alin = estado.get('alineacion_activa')
                    datos_estado = {
                        "ligas": [liga.to_dict()],
                        "copas": [c.to_dict() for c in estado.get("copas", [])],
                        "equipo_usuario_id": mi_equipo.id,
                        "liga_usuario_id": liga.tipo,
                        "temporada": estado.get("temporada", 1),
                        "historial": estado.get("historial", []),
                        "transfer_log": estado.get("transfer_log", []),
                        "pantalla_actual": "temporada",
                        "alineacion_activa": {
                            "titulares": list(alin.titulares),
                            "formacion": str(alin.formacion)
                        } if alin else None,
                        "dt_nombre": estado.get("dt_nombre", ""),
                        "dt_nacionalidad": estado.get("dt_nacionalidad", ""),
                        "copa_tipo": estado.get("copa_tipo"),
                        "copa_fase_actual": estado.get("copa_fase_actual"),
                        "copa_grupo_standing": estado.get("copa_grupo_standing", []),
                        "copa_bracket": estado.get("copa_bracket", {}),
                        "copa_grupo_partidos": estado.get("copa_grupo_partidos", []),
                        "copa_jornada_grupo": estado.get("copa_jornada_grupo", 1),
                        "copa_tab": estado.get("copa_tab"),
                        "copa_grupos": estado.get("copa_grupos", {}),
                        "copa_grupos_standings": estado.get("copa_grupos_standings", {}),
                        "copa_bracket_otros": estado.get("copa_bracket_otros", {})
                    }
                    estado_juego = EstadoJuego.from_dict(datos_estado)
                    
                    # Nombre descriptivo para el slot (ej. "Millonarios (T1 J3)")
                    nombre_guardado = f"{mi_equipo.corto} (T{estado_juego.temporada} J{liga.jornada_actual})"
                    save.guardar_en_slot(estado_juego, slot_n, nombre_guardado)
                    logger.info(f"Partida guardada de forma atómica en el slot {slot_n}.")
                    
                    # Recordar el slot activo para futuros autoguardados
                    estado['slot_activo'] = slot_n
                    return "menu"
                except Exception as e_save_error:
                    logger.error(f"Fallo al guardar en el slot {slot_n}: {e_save_error}. Intentando fallback.")
                    # Fallback de emergencia: guardar en el slot por defecto alpha_football_save.json
                    try:
                        save.guardar_partida(estado_juego)
                        logger.info("Guardado alternativo en ruta por defecto exitoso.")
                        return "menu"
                    except Exception as e_fatal:
                        logger.critical(f"No se pudo guardar la partida con ningún método: {e_fatal}.")

        # 5. Botón VOLVER para cancelar la acción
        volver_rect = pygame.Rect(140, 560, 200, 48)
        hover_volver = volver_rect.collidepoint(mouse_pos)
        draw_button(screen, volver_rect, "VOLVER", hover_volver)

        if click_pos and volver_rect.collidepoint(click_pos):
            pantalla_retorno = estado.get('save_slots_return', 'league_screen')
            return pantalla_retorno

        return None
    except Exception as e_fatal_render:
        logger.error(f"Error catastrófico en el render de save_slots_screen: {e_fatal_render}. Continuando al menú.")
        return "menu"
