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


# v2.3 (Fase 2): tabla de bono de 2ª división DUPLICADO (×2) en todas las ligas.
# Expuesta a nivel de módulo para que los tests la puedan importar.
# Pedido de Diego: "en bono de 2da division duplicalo en todas las ligas".
_BONO_LIGA_2A_X2 = {
    'premier':    [30_000_000, 16_000_000,  8_000_000, 4_000_000, 4_000_000, 2_000_000],
    'laliga':     [24_000_000, 12_000_000,  6_000_000, 3_000_000, 3_000_000, 1_600_000],
    'brasil':     [12_000_000,  6_000_000,  3_000_000, 1_600_000, 1_600_000, 1_000_000],
    'argentina':  [ 6_000_000,  3_000_000,  1_600_000, 1_000_000, 1_000_000,   600_000],
    'betplay':    [ 4_000_000,  2_000_000,  1_000_000,   600_000,   600_000,   400_000],
}


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
        #    v0.8.1: claves correctas (pos/pts/gf/gc/campeon_liga/libertadores) +
        #    bono de fin de temporada + reset de la mejor fase de copa.
        try:
            # Ordenar para ver la posición final del usuario
            def clave_tabla(eq):
                dg = getattr(eq, 'gf', 0) - getattr(eq, 'gc', 0)
                return (getattr(eq, 'puntos', 0), dg, getattr(eq, 'gf', 0))
            equipos_ord = sorted(liga.equipos, key=clave_tabla, reverse=True)
            posicion = next((idx + 1 for idx, s in enumerate(equipos_ord) if s.id == mi_equipo.id), 1)
            campeon = equipos_ord[0] if equipos_ord else None
            campeon_nombre = getattr(campeon, 'nombre', 'Desconocido') if campeon else 'Desconocido'

            # Mejor fase alcanzada en copa esta temporada
            # v0.8.7.3: si el user no clasificó, mostrar "No clasificado" en el
            # historial. Sin este check, la simulación en background de la copa
            # (v0.8.7.2) deja copa_fase_actual='campeon' aunque el user no jugó.
            if not estado.get('copa_user_en_copa', True):
                mejor_fase = 'No clasificado'
            else:
                mejor_fase = estado.get('copa_mejor_fase_temp')
                if not mejor_fase:
                    # Derivar del estado de la copa si no se trackeó explícitamente
                    fase_actual = estado.get('copa_fase_actual', 'grupos')
                    if fase_actual == 'campeon':
                        mejor_fase = 'Campeón'
                    elif fase_actual == 'eliminado':
                        mejor_fase = 'Fase de grupos'
                    else:
                        mejor_fase = 'Fase de grupos'

            # F6/F7 (v0.8.2): bono de fin de temporada VARIABLE por país del usuario
            # (liga) y por continente (copa).
            # Recompensas de LIGA (per-country, ya acordadas):
            _BONO_LIGA_POR_PAIS = {
                'premier':    [150_000_000, 90_000_000, 50_000_000, 50_000_000, 25_000_000, 25_000_000, 10_000_000, 10_000_000, 10_000_000, 10_000_000, 10_000_000, 10_000_000],
                'laliga':     [100_000_000, 60_000_000, 30_000_000, 30_000_000, 15_000_000, 15_000_000,  5_000_000,  5_000_000,  5_000_000,  5_000_000,  5_000_000,  5_000_000],
                'brasil':     [ 60_000_000, 35_000_000, 20_000_000, 20_000_000, 10_000_000, 10_000_000,  3_000_000,  3_000_000,  3_000_000,  3_000_000,  3_000_000,  3_000_000],
                'argentina':  [ 30_000_000, 18_000_000, 10_000_000, 10_000_000,  5_000_000,  5_000_000,  2_000_000,  2_000_000,  2_000_000,  2_000_000,  2_000_000,  2_000_000],
                'betplay':    [ 20_000_000, 12_000_000,  7_000_000,  7_000_000,  3_000_000,  3_000_000,  1_000_000,  1_000_000,  1_000_000,  1_000_000,  1_000_000,  1_000_000],
            }
            # v2.3 (Fase 2): tabla de 2ª división ×2 (declarada a nivel de módulo arriba)
            # — _BONO_LIGA_2A_X2
            tipo_liga = getattr(liga, 'tipo', '') or ''
            # v2.3: si la liga es de 2ª división, usar la tabla ×2 (más modesta).
            liga_division = getattr(liga, 'division', 1)
            if liga_division == 2:
                tabla_bonos = _BONO_LIGA_2A_X2.get(tipo_liga) or _BONO_LIGA_2A_X2['betplay']
            else:
                tabla_bonos = _BONO_LIGA_POR_PAIS.get(tipo_liga) or _BONO_LIGA_POR_PAIS['betplay']
            # índice por posición (1..N) con cap a la longitud de la tabla
            idx_liga = max(0, min(len(tabla_bonos) - 1, posicion - 1))
            bono_liga = tabla_bonos[idx_liga]

            # Recompensas de COPA (Europa vs América, agresiva):
            _BONO_COPA_EUROPA = {'Campeón': 75_000_000, 'Finalista': 40_000_000, 'Semifinal': 15_000_000}
            _BONO_COPA_AMERICA = {'Campeón': 25_000_000, 'Finalista': 12_000_000, 'Semifinal': 5_000_000}
            _es_europa = tipo_liga in ('premier', 'laliga')
            tabla_copa = _BONO_COPA_EUROPA if _es_europa else _BONO_COPA_AMERICA
            bono_copa = tabla_copa.get(mejor_fase, 0)
            bono_total = bono_liga + bono_copa

            # Acreditar el bono al balance del usuario
            try:
                mi_equipo.balance = int(getattr(mi_equipo, 'balance', 0)) + bono_total
            except Exception as e_bal:
                logger.error(f"Error al acreditar bono de fin de temporada: {e_bal}")

            registro = {
                "temporada": temp_anterior,
                "equipo": mi_equipo.nombre,
                # v0.8.1: claves que lee career_screen.py
                "pos": posicion,
                "pts": getattr(mi_equipo, 'puntos', 0),
                "gf": getattr(mi_equipo, 'gf', 0),
                "gc": getattr(mi_equipo, 'gc', 0),
                "campeon_liga": campeon_nombre,
                "libertadores": mejor_fase,
                # Información del bono (se muestra en el resumen de la temporada)
                "bono_liga": bono_liga,
                "bono_copa": bono_copa,
                "bono_total": bono_total,
                # Compatibilidad con saves viejos que usaban 'posicion' y 'puntos'
                "posicion": posicion,
                "puntos": getattr(mi_equipo, 'puntos', 0),
            }
            estado.setdefault('historial', []).append(registro)
            logger.info(
                f"Fin T{temp_anterior}: pos {posicion}, pts {mi_equipo.puntos}, "
                f"copa {mejor_fase}, bono €{bono_total:,}"
            )
        except Exception as e_hist:
            logger.error(f"Error al guardar historial de campaña: {e_hist}")

        # 2b. Reset del tracking de copa para la nueva temporada
        try:
            estado['copa_mejor_fase_temp'] = None
        except Exception:
            pass

        # 2c. v0.8.7: clasificación a copa para la próxima temporada.
        # El usuario clasifica si quedó en el TOP 3 por puntos de la liga
        # (la T1 se clasifica por OVR top 3 al alta de carrera).
        try:
            equipos_orden_pts = sorted(
                liga.equipos,
                key=lambda e: (
                    getattr(e, 'puntos', 0),
                    getattr(e, 'gf', 0) - getattr(e, 'gc', 0),
                    getattr(e, 'gf', 0),
                ),
                reverse=True,
            )
            _top3_pts = {e.nombre for e in equipos_orden_pts[:3]}
            _pos_user = next(
                (i + 1 for i, e in enumerate(equipos_orden_pts) if e.id == mi_equipo.id),
                len(equipos_orden_pts),
            )
            estado['copa_clasificado'] = (mi_equipo.nombre in _top3_pts)
            estado['copa_clasificado_motivo'] = (
                f"Top 3 en liga (posición {_pos_user}, {getattr(mi_equipo, 'puntos', 0)} pts)"
                if estado['copa_clasificado']
                else f"Posición {_pos_user} de {len(equipos_orden_pts)} (fuera del top 3)"
            )
            estado['copa_user_en_copa'] = estado['copa_clasificado']
            logger.info(
                f"Clasificación T{nueva_temp}: pos={_pos_user}, clasificado={estado['copa_clasificado']}"
            )
        except Exception as e_clasif:
            logger.error(f"Error al calcular clasificación para nueva temporada: {e_clasif}")
            estado['copa_clasificado'] = True
            estado['copa_user_en_copa'] = True

        # 3a. v2.3 (Fase 6): SWAP promoción/relegación BIDIRECCIONAL entre 1ª y 2ª.
        # DEBE ejecutarse ANTES de limpiar stats, porque usa puntos/GF/GC para ordenar.
        try:
            segunda = estado.get('segunda_division') or {}
            liga_division = getattr(liga, 'division', 1)
            liga_tipo = getattr(liga, 'tipo', '')

            # Determinar cuál es 1ª y cuál es 2ª según dónde está el user.
            if liga_division == 1:
                liga_1a = liga
                liga_2a = segunda.get(liga_tipo) if liga_tipo in segunda else None
            else:
                # User está en 2ª: cargar 1ª on-demand para el swap.
                # La 1ª no se simuló en background (TODO: simular contraparte),
                # así que sus stats están frescas. El swap se basa en los datos
                # de la 2ª (simulados) y los de la 1ª (frescos al cargar).
                liga_2a = liga
                liga_1a = None
                if liga_tipo:
                    try:
                        from alpha_football.ui.menu import load_league_teams
                        liga_1a = load_league_teams(liga_tipo)
                        if liga_1a:
                            liga_1a.division = 1
                            for eq in liga_1a.equipos:
                                eq.division = 1
                    except Exception as e_load_1a:
                        logger.error(f"No se pudo cargar 1ª división {liga_tipo} para swap: {e_load_1a}")

            if liga_1a and liga_2a and len(liga_2a.equipos) >= 2 and len(liga_1a.equipos) >= 2:
                # Top 2 de 2ª (descendente por puntos; en empates por DG)
                equipos_2_ord = sorted(
                    liga_2a.equipos,
                    key=lambda e: (
                        -getattr(e, 'puntos', 0),
                        -(getattr(e, 'gf', 0) - getattr(e, 'gc', 0)),
                        -getattr(e, 'gf', 0),
                    )
                )
                # Bottom 2 de 1ª (ascendente por puntos; en empates por DG inverso)
                equipos_1_ord = sorted(
                    liga_1a.equipos,
                    key=lambda e: (
                        getattr(e, 'puntos', 0),
                        (getattr(e, 'gf', 0) - getattr(e, 'gc', 0)),
                        getattr(e, 'gf', 0),
                    )
                )
                ascenden = equipos_2_ord[:2]
                descienden = equipos_1_ord[:2]

                # v2.3.3: armar payload para promo_releg_screen ANTES del swap.
                try:
                    _asc_payload = [
                        {
                            'nombre': getattr(e, 'nombre', '?'),
                            'ovr': getattr(e, 'ovr_promedio', 0),
                            'origen': 2, 'destino': 1,
                            'es_user': (getattr(e, 'id', None) == getattr(mi_equipo, 'id', None)),
                        }
                        for e in ascenden
                    ]
                    _des_payload = [
                        {
                            'nombre': getattr(e, 'nombre', '?'),
                            'ovr': getattr(e, 'ovr_promedio', 0),
                            'origen': 1, 'destino': 2,
                            'es_user': (getattr(e, 'id', None) == getattr(mi_equipo, 'id', None)),
                        }
                        for e in descienden
                    ]
                    estado['promo_releg_data'] = {
                        'ascendidos': _asc_payload,
                        'descendidos': _des_payload,
                        'user_ascendio': any(x['es_user'] for x in _asc_payload),
                        'user_descendio': any(x['es_user'] for x in _des_payload),
                    }
                except Exception as e_pr_data:
                    logger.error(f"Error armando promo_releg_data: {e_pr_data}")

                # Swap atómico de referencias (no copiamos, movemos)
                for eq in ascenden:
                    if eq in liga_2a.equipos:
                        liga_2a.equipos.remove(eq)
                        liga_1a.equipos.append(eq)
                        eq.division = 1
                for eq in descienden:
                    if eq in liga_1a.equipos:
                        liga_1a.equipos.remove(eq)
                        liga_2a.equipos.append(eq)
                        eq.division = 2

                # Determinar si el user ascendió/descendió
                user_asc = any(e.id == mi_equipo.id for e in ascenden)
                user_des = any(e.id == mi_equipo.id for e in descienden)

                # Actualizar estado['liga'] y la división del user
                if user_asc or user_des:
                    estado['liga_usuario_division'] = 2 if user_des else 1
                    estado['liga'] = liga_2a if user_des else liga_1a
                    # Actualizar liga y mi_equipo para el resto de avanzar_nueva_temporada
                    liga = estado['liga']
                    # Reubicar mi_equipo en la liga correcta
                    for eq in liga.equipos:
                        if eq.id == mi_equipo.id:
                            mi_equipo = eq
                            estado['mi_equipo'] = eq
                            break
                    if user_des:
                        estado['copa_user_en_copa'] = False
                        estado['copa_clasificado'] = False
                        estado['copa_clasificado_motivo'] = "Descendiste a 2ª división."
                    elif user_asc:
                        # Al ascender a 1ª, recalcular clasificación a copa
                        estado['copa_user_en_copa'] = True
                        estado['copa_clasificado'] = True
                        estado['copa_clasificado_motivo'] = "Ascendiste a 1ª división."
                    logger.info(
                        f"Promo/releg T{nueva_temp}: user "
                        f"{'ascendió' if user_asc else 'descendió'} "
                        f"a {estado['liga_usuario_division']}ª división"
                    )
                # Guardar resultado del swap (para banner en el resumen)
                estado['promo_releg_resultado'] = {
                    'ascendieron': [getattr(e, 'nombre', '?') for e in ascenden],
                    'descendieron': [getattr(e, 'nombre', '?') for e in descienden],
                    'user_ascendio': user_asc,
                    'user_descendio': user_des,
                }
                # Actualizar el dict de segunda_division con la liga modificada
                # (siempre, no solo cuando el user está involucrado — los swaps
                # modifican ambas ligas aunque el user no ascienda/descienda).
                if liga_tipo:
                    estado['segunda_division'][liga_tipo] = liga_2a
                logger.info(
                    f"Promo/releg T{nueva_temp}: ascendieron {[e.nombre for e in ascenden]} "
                    f"/ descendieron {[e.nombre for e in descienden]}"
                )
        except Exception as e_promo:
            logger.error(f"Error en swap promoción/relegación: {e_promo}")

        # 4. Limpiar estadísticas de la liga del usuario (post-swap, para no borrar datos que usa el ordenamiento).
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
                j.moral = max(70, j.moral)
                j.lesion_partidos = 0
                j.partidos_sancion = 0

        # 4b. Desarrollo pasivo de fin de temporada (envejecimiento + OVR).
        try:
            from alpha_football.desarrollo import progresar_liga_pasivo
            progresar_liga_pasivo(liga, 1)
        except Exception as e_dev_pasivo:
            logger.error(f"Error en desarrollo pasivo de fin de temporada: {e_dev_pasivo}")

        # 5. Limpiar el calendario de partidos para obligar a regenerar un fixture nuevo
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
                "dt_nacionalidad": estado.get("dt_nacionalidad", ""),
                # v0.8.7.5: persistir clasificación a copa de la NUEVA temporada (recién
                # calculada arriba) para que al recargar este autosave el historial
                # muestre "No clasificado" si el usuario no clasificó.
                "copa_clasificado": estado.get("copa_clasificado"),
                "copa_user_en_copa": estado.get("copa_user_en_copa"),
                "copa_clasificado_motivo": estado.get("copa_clasificado_motivo", ""),
                "copa_mejor_fase_temp": estado.get("copa_mejor_fase_temp"),
                # v2.3: división del usuario tras el swap de promo/releg (1 o 2)
                "liga_usuario_division": estado.get("liga_usuario_division", 1),
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
        # v2.3 (Fase 1): inicializar pos_user ANTES del if para que esté disponible
        # en el bloque del bono (líneas abajo) incluso si el user es campeón
        # (rama del if no asignaba pos_user → UnboundLocalError por frame).
        pos_user = 1
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

        # v0.8.2: F6/F7 — banner de bono de fin de temporada (variables por país/continente)
        try:
            # v0.8.7.3: si el user no clasificó, no hay bono de copa.
            if not estado.get('copa_user_en_copa', True):
                mejor_fase = 'No clasificado'
            else:
                mejor_fase = estado.get('copa_mejor_fase_temp')
                if not mejor_fase:
                    fase_actual = estado.get('copa_fase_actual', 'grupos')
                    if fase_actual == 'campeon':
                        mejor_fase = 'Campeón'
                    elif fase_actual == 'eliminado':
                        mejor_fase = 'Fase de grupos'
                    else:
                        mejor_fase = 'Fase de grupos'
            # Reutilizamos las mismas tablas (deben coincidir con las de avanzar_nueva_temporada)
            _BONO_LIGA_POR_PAIS = {
                'premier':    [150_000_000, 90_000_000, 50_000_000, 50_000_000, 25_000_000, 25_000_000, 10_000_000, 10_000_000, 10_000_000, 10_000_000, 10_000_000, 10_000_000],
                'laliga':     [100_000_000, 60_000_000, 30_000_000, 30_000_000, 15_000_000, 15_000_000,  5_000_000,  5_000_000,  5_000_000,  5_000_000,  5_000_000,  5_000_000],
                'brasil':     [ 60_000_000, 35_000_000, 20_000_000, 20_000_000, 10_000_000, 10_000_000,  3_000_000,  3_000_000,  3_000_000,  3_000_000,  3_000_000,  3_000_000],
                'argentina':  [ 30_000_000, 18_000_000, 10_000_000, 10_000_000,  5_000_000,  5_000_000,  2_000_000,  2_000_000,  2_000_000,  2_000_000,  2_000_000,  2_000_000],
                'betplay':    [ 20_000_000, 12_000_000,  7_000_000,  7_000_000,  3_000_000,  3_000_000,  1_000_000,  1_000_000,  1_000_000,  1_000_000,  1_000_000,  1_000_000],
            }
            # v2.3: tabla de 2ª división ×2 (declarada a nivel de módulo arriba)
            # — _BONO_LIGA_2A_X2
            _BONO_COPA_EUROPA = {'Campeón': 75_000_000, 'Finalista': 40_000_000, 'Semifinal': 15_000_000}
            _BONO_COPA_AMERICA = {'Campeón': 25_000_000, 'Finalista': 12_000_000, 'Semifinal': 5_000_000}
            tipo_liga_b = getattr(liga, 'tipo', '') or ''
            # v2.3: si la liga es de 2ª división, usar tabla ×2
            liga_division_b = getattr(liga, 'division', 1)
            if liga_division_b == 2:
                tabla_bonos_b = _BONO_LIGA_2A_X2.get(tipo_liga_b) or _BONO_LIGA_2A_X2['betplay']
            else:
                tabla_bonos_b = _BONO_LIGA_POR_PAIS.get(tipo_liga_b) or _BONO_LIGA_POR_PAIS['betplay']
            idx_b = max(0, min(len(tabla_bonos_b) - 1, pos_user - 1))
            bono_liga = tabla_bonos_b[idx_b]
            _es_europa_b = tipo_liga_b in ('premier', 'laliga')
            tabla_copa_b = _BONO_COPA_EUROPA if _es_europa_b else _BONO_COPA_AMERICA
            bono_copa = tabla_copa_b.get(mejor_fase, 0)
            bono_total = bono_liga + bono_copa
            if bono_total > 0:
                bono_rect = pygame.Rect(100, 615, 1080, 50)
                draw_panel(screen, bono_rect)
                pygame.draw.rect(screen, COLORS['verde'], bono_rect, width=2, border_radius=8)
                draw_text(
                    screen,
                    f"💰 BONO DE FIN DE TEMPORADA: +€{bono_total:,}  "
                    f"(Liga: €{bono_liga:,}  ·  Copa: €{bono_copa:,})",
                    (120, 628), size='md', color='verde'
                )

            # v2.3 (Fase 6): banner de promoción/relegación tras el swap.
            # Si el user ascendió o descendió, mensaje destacado.
            pr = estado.get('promo_releg_resultado') or {}
            if pr.get('user_ascendio'):
                pr_rect = pygame.Rect(100, 555, 1080, 50)
                draw_panel(screen, pr_rect)
                pygame.draw.rect(screen, COLORS.get('dorado', (255, 215, 0)), pr_rect, width=3, border_radius=8)
                draw_text(
                    screen,
                    f"🎉 ¡ASCENDISTE A LA 1ª DIVISIÓN! Tu club vuelve a codearse con los grandes.",
                    (120, 568), size='md', color='dorado'
                )
            elif pr.get('user_descendio'):
                pr_rect = pygame.Rect(100, 555, 1080, 50)
                draw_panel(screen, pr_rect)
                pygame.draw.rect(screen, COLORS.get('rojo', (255, 68, 68)), pr_rect, width=3, border_radius=8)
                draw_text(
                    screen,
                    f"⬇️ DESCENDISTE A LA 2ª DIVISIÓN. Volverás con todo la próxima temporada.",
                    (120, 568), size='md', color='rojo'
                )
        except Exception as e_bono:
            logger.error(f"Error al mostrar banner de bono: {e_bono}")

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
            # v2.3.3: si hay datos de promo/releg (1ª division con 2ª cargada),
            # mostrar la pantalla de promocion/relegacion ANTES del resumen.
            if estado.get('promo_releg_data'):
                # El swap ya se hizo dentro de avanzar_nueva_temporada? No — todavía no.
                # Hacemos el swap acá y luego redirigimos a promo_releg_screen.
                avanzar_nueva_temporada(estado)
                return "promo_releg_screen"
            avanzar_nueva_temporada(estado)
            return "league_screen"

        return None
    except Exception as e_render:
        logger.error(f"Error al renderizar resumen_temporada_screen: {e_render}")
        return "menu"
