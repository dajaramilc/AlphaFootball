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

def estado_juego_actual(estado: dict):
    """v3.6.0: EstadoJuego de la partida en curso (lo que se guarda en un slot)."""
    from alpha_football import save
    from alpha_football.models import EstadoJuego
    liga, mi_equipo = estado.get('liga'), estado.get('mi_equipo')
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
            "formacion": str(alin.formacion),
            "convocados": list(getattr(alin, 'convocados', []) or []),
        } if alin else None,
        "dt_nombre": estado.get("dt_nombre", ""),
        "dt_nacionalidad": estado.get("dt_nacionalidad", ""),
        # v3.8.0: la copa se guarda en datos_carrera["copas"]; las claves viejas copa_* ya no.
        "copa_clasificado": estado.get("copa_clasificado"),
        "copa_user_en_copa": estado.get("copa_user_en_copa"),
        "copa_clasificado_motivo": estado.get("copa_clasificado_motivo", ""),
        "copa_mejor_fase_temp": estado.get("copa_mejor_fase_temp"),
        # v2.3.5: 1ª/2ª división (antes no se guardaban aquí)
        **save.campos_divisiones(estado),
    }
    estado_juego = EstadoJuego.from_dict(datos_estado)
    return estado_juego


def guardar_slot(estado: dict, slot_n: int) -> None:
    """v3.6.0: guarda la partida en el slot `slot_n` y lo marca como activo (lanza si falla)."""
    from alpha_football import save
    estado_juego = estado_juego_actual(estado)
    liga, mi_equipo = estado.get('liga'), estado.get('mi_equipo')
    nombre_guardado = f"{mi_equipo.corto} (T{estado_juego.temporada} J{liga.jornada_actual})"
    save.guardar_en_slot(estado_juego, slot_n, nombre_guardado)
    estado['slot_activo'] = slot_n


# v3.9.0: rects expuestos (ayuda H)
R_PANEL = pygame.Rect(100, 80, 1080, 560)
R_VOLVER = pygame.Rect(140, 560, 200, 48)
R_SALIR = pygame.Rect(360, 560, 240, 48)
R_DETALLES = pygame.Rect(680, 186, 480, 340)


def rect_slot(i: int) -> pygame.Rect:
    """v3.9.0: botón del slot i (0-4)."""
    return pygame.Rect(140, 190 + i * 70, 520, 52)


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
        # v3.6.0: teclado — ↑/↓ slot, Enter guarda, Supr borra (con confirmación), Esc vuelve
        foco = int(estado.get('slot_foco', 0) or 0) % 5
        elegido = None
        retorno = 'menu' if estado.get('salir_tras_guardar') else estado.get('save_slots_return', 'league_screen')

        try:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    # Enviar el evento de salida para que sea procesado por main.py
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
                    return "quit"
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    click_pos = event.pos
                elif event.type == pygame.KEYDOWN:
                    if estado.get('slot_borrar'):
                        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_DELETE):
                            n_borrar = estado.pop('slot_borrar')
                            try:
                                save.eliminar_slot(n_borrar)
                                if estado.get('slot_activo') == n_borrar:
                                    estado.pop('slot_activo', None)
                                cabeceras = save.listar_slots()
                            except Exception as e_del:
                                logger.error(f"No se pudo borrar el slot {n_borrar}: {e_del}")
                        elif event.key == pygame.K_ESCAPE:
                            estado.pop('slot_borrar', None)
                        continue
                    if event.key == pygame.K_ESCAPE:
                        estado.pop('salir_tras_guardar', None)
                        return estado.get('save_slots_return', 'league_screen')
                    if event.key in (pygame.K_UP, pygame.K_DOWN):
                        foco = (foco + (-1 if event.key == pygame.K_UP else 1)) % 5
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        elegido = foco
                    elif event.key == pygame.K_DELETE:
                        estado['slot_borrar'] = foco + 1
            estado['slot_foco'] = foco
        except Exception as e_events:
            logger.error(f"Error en el ciclo de eventos del frame en save_slots_screen: {e_events}")

        # 1. Dibujar el fondo con gradiente
        draw_gradient_bg(screen)
        
        # 2. Dibujar el panel principal centrado
        panel_rect = R_PANEL
        draw_panel(screen, panel_rect)

        # 3. Dibujar títulos
        draw_text(screen, "GUARDAR PARTIDA — SELECCIONAR SLOT", (140, 110), size='lg', color='verde')
        draw_text(screen, "Guarda tu progreso en uno de los 5 slots. Sigues jugando después de guardar.", (140, 145), size='sm', color='blanco')

        # 4. Dibujar la lista de slots
        for i in range(5):
            slot_n = i + 1
            slot_rect = rect_slot(i)
            
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
            if i == foco:                                   # v3.6.0: foco de teclado
                pygame.draw.rect(screen, COLORS.get('dorado', (255, 215, 0)), slot_rect.inflate(8, 8),
                                 width=2, border_radius=8)

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
            if (click_pos and slot_rect.collidepoint(click_pos)) or elegido == i:
                try:
                    estado_juego = None
                    estado_juego = estado_juego_actual(estado)
                    
                    # Nombre descriptivo para el slot (ej. "Millonarios (T1 J3)")
                    nombre_guardado = f"{mi_equipo.corto} (T{estado_juego.temporada} J{liga.jornada_actual})"
                    save.guardar_en_slot(estado_juego, slot_n, nombre_guardado)
                    logger.info(f"Partida guardada de forma atómica en el slot {slot_n}.")
                    
                    # Recordar el slot activo para futuros autoguardados
                    estado['slot_activo'] = slot_n
                    # v2.4.0: guardar ya no saca de la partida; se vuelve al hub con un aviso.
                    from alpha_football.ui.league_screen import _toast
                    _toast(estado, f"Guardado en slot {slot_n}")
                    estado.pop('salir_tras_guardar', None)      # v3.6.0: GUARDAR Y SALIR sin slot
                    return retorno
                except Exception as e_save_error:
                    logger.error(f"Fallo al guardar en el slot {slot_n}: {e_save_error}. Intentando fallback.")
                    from alpha_football.ui.league_screen import _toast
                    # Fallback de emergencia: guardar en el slot por defecto alpha_football_save.json
                    try:
                        save.guardar_partida(estado_juego)
                        logger.info("Guardado alternativo en ruta por defecto exitoso.")
                        _toast(estado, "Guardado en el archivo por defecto (falló el slot)", color='dorado')
                    except Exception as e_fatal:
                        logger.critical(f"No se pudo guardar la partida con ningún método: {e_fatal}.")
                        _toast(estado, "No se pudo guardar la partida", color='rojo')
                    estado.pop('salir_tras_guardar', None)
                    return estado.get('save_slots_return', 'league_screen')

        # 5. Botón VOLVER para cancelar la acción
        volver_rect = R_VOLVER
        hover_volver = volver_rect.collidepoint(mouse_pos)
        draw_button(screen, volver_rect, "VOLVER", hover_volver)

        if click_pos and volver_rect.collidepoint(click_pos):
            estado.pop('salir_tras_guardar', None)
            pantalla_retorno = estado.get('save_slots_return', 'league_screen')
            return pantalla_retorno

        # v2.4.0: salir al menú es una acción aparte (guardar ya no sale).
        salir_rect = R_SALIR
        draw_button(screen, salir_rect, "SALIR AL MENÚ", salir_rect.collidepoint(mouse_pos))
        if click_pos and salir_rect.collidepoint(click_pos):
            estado.pop('salir_tras_guardar', None)
            return "menu"

        # v3.6.0: ayuda de teclado / confirmación de borrado
        if estado.get('slot_borrar'):
            draw_text(screen, f"¿Borrar el slot {estado['slot_borrar']}? Enter/Supr confirma · Esc cancela",
                      (630, 574), size='sm', color='rojo')
        else:
            draw_text(screen, "↑↓ elegir · Enter guardar · Supr borrar · Esc volver", (630, 574),
                      size='sm', color='azul', shadow=False)

        return None
    except Exception as e_fatal_render:
        logger.error(f"Error catastrófico en el render de save_slots_screen: {e_fatal_render}. Continuando al menú.")
        return "menu"
