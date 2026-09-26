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
    'seriea':     [24_000_000, 12_000_000,  6_000_000, 3_000_000, 3_000_000, 1_600_000],   # v3.7.0
    'brasil':     [12_000_000,  6_000_000,  3_000_000, 1_600_000, 1_600_000, 1_000_000],
    'argentina':  [ 6_000_000,  3_000_000,  1_600_000, 1_000_000, 1_000_000,   600_000],
    'betplay':    [ 4_000_000,  2_000_000,  1_000_000,   600_000,   600_000,   400_000],
}


def _swap_promocion(liga_1a, liga_2a) -> tuple[list, list]:
    """v2.3.6: los 2 primeros de la 2ª suben y los 2 últimos de la 1ª bajan (un país)."""
    if not liga_1a or not liga_2a or len(liga_2a.equipos) < 2 or len(liga_1a.equipos) < 2:
        return [], []

    def _clave(e):
        return (getattr(e, 'puntos', 0), getattr(e, 'gf', 0) - getattr(e, 'gc', 0), getattr(e, 'gf', 0))
    ascenden = sorted(liga_2a.equipos, key=_clave, reverse=True)[:2]
    descienden = sorted(liga_1a.equipos, key=_clave)[:2]
    for eq in ascenden:
        liga_2a.equipos.remove(eq)
        liga_1a.equipos.append(eq)
        eq.division = 1
    for eq in descienden:
        liga_1a.equipos.remove(eq)
        liga_2a.equipos.append(eq)
        eq.division = 2
    return ascenden, descienden


def siguiente_pantalla_tras_temporada(estado: dict) -> str:
    """v3.2.0: veredicto → despido → ascensos/descensos → hub."""
    if estado.get('veredicto_pendiente'):
        return "veredicto_screen"
    if estado.get('despido_pendiente'):
        return "despido_screen"
    if estado.get('promo_releg_data'):
        return "promo_releg_screen"
    return "league_screen"


def _premios_copa_temporada(estado: dict) -> int:
    """v3.8.0: premios de copa (por fase) que el club del user ya cobró esta temporada."""
    reg = (estado.get('datos_carrera') or {}).get('premios_copa') or {}
    if reg.get('temporada') == estado.get('temporada', 1) and reg.get('club') == getattr(estado.get('mi_equipo'), 'nombre', None):
        return int(reg.get('total', 0) or 0)
    return 0


def avanzar_nueva_temporada(estado: dict) -> None:
    """Restablece los fixtures, jornadas, estadísticas de liga y avanza a la siguiente temporada."""
    from alpha_football.ui import pantalla_carga as _pc     # pasos reales con barra
    liga = mi_equipo = None
    try:
        liga = estado.get('liga')
        mi_equipo = estado.get('mi_equipo')
        if not liga or not mi_equipo:
            return

        _pc.mostrar("PASANDO DE TEMPORADA", "Cerrando las copas", 0.05)
        # 0. v3.8.0: las dos copas terminan ANTES de subir la temporada (si no, el motor las
        #    reemplazaría por las de la temporada nueva). Se guardan sus campeones.
        campeones_copas = {}
        bono_copa_cobrado = 0
        try:
            from alpha_football import competiciones as CP
            from alpha_football.ui.copa_screen import simular_copa_entera
            simular_copa_entera(estado)
            campeones_copas = {t: CP.campeon(estado, t) for t in CP.N_FECHAS}
            bono_copa_cobrado = _premios_copa_temporada(estado)
            estado.setdefault('datos_carrera', {}).setdefault('campeones_copas', []).append(
                {'temporada': int(estado.get('temporada', 1) or 1), **campeones_copas})
        except Exception as e_copas:
            logger.error(f"Error al cerrar las copas de la temporada: {e_copas}")

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
            # v3.8.0: la mejor fase sale del motor (claves derivadas tras simular_copa_entera)
            if not estado.get('copa_user_en_copa'):
                mejor_fase = 'No clasificado'
            else:
                mejor_fase = estado.get('copa_mejor_fase_temp') or 'Fase de liga'

            # F6/F7 (v0.8.2): bono de fin de temporada VARIABLE por país del usuario
            # (liga) y por continente (copa).
            # Recompensas de LIGA (per-country, ya acordadas):
            _BONO_LIGA_POR_PAIS = {
                'premier':    [150_000_000, 90_000_000, 50_000_000, 50_000_000, 25_000_000, 25_000_000, 10_000_000, 10_000_000, 10_000_000, 10_000_000, 10_000_000, 10_000_000],
                'laliga':     [100_000_000, 60_000_000, 30_000_000, 30_000_000, 15_000_000, 15_000_000,  5_000_000,  5_000_000,  5_000_000,  5_000_000,  5_000_000,  5_000_000],
                'seriea':     [100_000_000, 60_000_000, 30_000_000, 30_000_000, 15_000_000, 15_000_000,  5_000_000,  5_000_000,  5_000_000,  5_000_000,  5_000_000,  5_000_000],   # v3.7.0
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

            # v3.8.0: los premios de COPA se cobran por fase durante la temporada
            # (copa_screen.cobrar_premios_copa); acá solo se informan.
            bono_copa = bono_copa_cobrado
            bono_total = bono_liga + bono_copa

            # Acreditar el bono de liga al balance del usuario
            try:
                mi_equipo.balance = int(getattr(mi_equipo, 'balance', 0)) + bono_liga
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
            try:  # v3.1.0: pedido abierto = fallado; bonus de potencial por moral
                from alpha_football.directiva import cerrar_pedido_temporada
                cerrar_pedido_temporada(estado)
                from alpha_football.vestuario import cierre_temporada as _cierre_vestuario
                _cierre_vestuario(estado)
            except Exception as e_v31:
                logger.error(f"Error en el cierre de temporada v3.1.0: {e_v31}")
            # v2.8.0: la directiva evalúa el objetivo (premio/multa y posible despido).
            try:
                from alpha_football.directiva import evaluar_temporada
                ev_dir = evaluar_temporada(estado, posicion)
                registro['objetivo'] = ev_dir.get('texto', '')
                registro['objetivo_resultado'] = ev_dir.get('resultado', '')
                registro['directiva_monto'] = ev_dir.get('monto', 0)
                registro['despedido'] = bool(ev_dir.get('despido'))
            except Exception as e_dir:
                logger.error(f"Error al evaluar el objetivo de la directiva: {e_dir}")
            try:  # v3.4.0: DTs de la IA que no cumplieron (usa la tabla final: antes del swap)
                from alpha_football.entrenadores import cierre_temporada as _dts_cierre
                _dts_cierre(estado)
            except Exception as e_dts:
                logger.error(f"Error en el cierre de temporada de los DTs: {e_dts}")
            try:  # v2.9.0: premios de la temporada que termina en su libro de finanzas
                from alpha_football.finanzas import registrar
                registrar(estado, 'premios', bono_liga + int(registro.get('directiva_monto', 0) or 0), temp_anterior)
            except Exception as e_lib:
                logger.error(f"Error al registrar los premios: {e_lib}")
            estado.setdefault('historial', []).append(registro)
            logger.info(
                f"Fin T{temp_anterior}: pos {posicion}, pts {mi_equipo.puntos}, "
                f"copa {mejor_fase}, bono €{bono_total:,}"
            )
        except Exception as e_hist:
            logger.error(f"Error al guardar historial de campaña: {e_hist}")

        # 2a. v2.9.1: las ofertas pendientes no pasan a la temporada siguiente.
        estado['ofertas_recibidas'] = []

        # 2b. v3.8.0: la clasificación a la copa de la temporada nueva sale del motor al final
        #     (tabla final de cada 1ª en copa_ranking; ascender no da copa; 2ª no juega copa).
        estado['copa_clasificado_motivo'] = ""

        _pc.mostrar("PASANDO DE TEMPORADA", "Ascensos y descensos", 0.25)
        # 3a. SWAP promoción/relegación entre la 1ª y la 2ª del país del usuario.
        # v2.3.5: ambas ligas son las reales de la partida (persistidas y simuladas de
        # fondo). Antes, con el user en 2ª, la 1ª se recargaba de disco con 0 puntos
        # (descendían equipos al azar) y los ascendidos se perdían al guardar.
        try:
            from alpha_football.ui.league_screen import completar_ligas_de_fondo
            completar_ligas_de_fondo(estado)
        except Exception as e_fondo:
            logger.error(f"Error completando ligas de fondo: {e_fondo}")

        segunda = estado.setdefault('segunda_division', {})
        primeras = estado.setdefault('primera_division', {})
        liga_tipo = getattr(liga, 'tipo', '')
        if getattr(liga, 'division', 1) == 1:
            liga_1a, liga_2a = liga, segunda.get(liga_tipo)
        else:
            liga_1a, liga_2a = primeras.get(liga_tipo), liga
        if liga_tipo:
            # la del user siempre es el objeto de su mapa
            if liga_1a is not None:
                primeras[liga_tipo] = liga_1a
            if liga_2a is not None:
                segunda[liga_tipo] = liga_2a

        # 3a-0. v4.4.0: rendimiento de la temporada (tramos, objetivos, grandes) antes del swap
        try:
            from alpha_football.nivel_temporada import preparar as _nivel_preparar
            _nivel_preparar(estado)
        except Exception as e_niv:
            logger.error(f"Error preparando el nivel de fin de temporada: {e_niv}")

        # 3a-bis. v2.3.6: con TODAS las tablas finales cerradas (antes del reset):
        #   - tabla final de cada 1ª = clasificados reales de la próxima copa
        #   - Balón de Oro al mejor rendimiento de las 10 ligas
        try:
            from alpha_football.ui.copa_screen import guardar_ranking_copas
            guardar_ranking_copas(estado)
        except Exception as e_rank:
            logger.error(f"Error guardando la tabla final para la copa: {e_rank}")
        try:
            from alpha_football.premios import calcular_balon_de_oro
            # v3.8.0: campeones de las dos copas + goles/asistencias de copa de cada jugador
            balon = calcular_balon_de_oro(primeras, segunda, temp_anterior,
                                          [c for c in campeones_copas.values() if c],
                                          datos_copas=(estado.get('datos_carrera') or {}).get('copas'))
            if balon:
                estado.setdefault('datos_carrera', {}).setdefault('balon_oro', []).append(balon)
                estado['balon_oro_ultimo'] = balon
                logger.info(f"Balón de Oro T{temp_anterior}: {balon['ganador']['nombre']} ({balon['ganador']['equipo']})")
        except Exception as e_balon:
            logger.error(f"Error calculando el Balón de Oro: {e_balon}")

        # 3a. SWAP promoción/relegación en los 5 países (v2.3.6: antes solo en el del
        # user y en las demás ligas los últimos seguían en 1ª la temporada siguiente).
        user_asc = user_des = False
        movimientos = []
        premio_ascenso_user = 0
        estado['_recien_ascendidos'] = []
        from alpha_football.mercado_ia import aplicar_ascenso, aplicar_descenso
        for tipo_x in sorted(set(primeras) | set(segunda)):
            l1, l2 = primeras.get(tipo_x), segunda.get(tipo_x)
            try:
                ascenden, descienden = _swap_promocion(l1, l2)
            except Exception as e_promo:
                logger.error(f"Error en swap promoción/relegación de '{tipo_x}': {e_promo}")
                continue
            if not ascenden and not descienden:
                continue
            # v4.4.0: ascenso +3..+6 (techo 83) y descenso −2..−5 según rendimiento (nivel_temporada);
            # el que asciende cobra el premio de ascenso.
            for eq in ascenden:
                try:
                    premio = aplicar_ascenso(eq, tipo_x, estado)
                    estado['_recien_ascendidos'].append(eq.nombre)
                    if eq.id == mi_equipo.id:
                        premio_ascenso_user = premio
                        try:   # el premio de ascenso también va al libro de finanzas de la temporada
                            from alpha_football.finanzas import registrar
                            registrar(estado, 'premios', int(premio or 0), temp_anterior)
                        except Exception as e_lib_asc:
                            logger.error(f"No se pudo registrar el premio de ascenso: {e_lib_asc}")
                except Exception as e_asc:
                    logger.error(f"Error aplicando el ascenso de {eq.nombre}: {e_asc}")
            for eq in descienden:
                try:
                    aplicar_descenso(eq, estado)
                except Exception as e_des:
                    logger.error(f"Error aplicando el descenso de {eq.nombre}: {e_des}")
            movimientos.append({'tipo': tipo_x,
                                'ascendidos': [e.nombre for e in ascenden],
                                'descendidos': [e.nombre for e in descienden]})
            if tipo_x == liga_tipo:
                def _payload(equipos, origen, destino):
                    return [{'nombre': getattr(e, 'nombre', '?'), 'ovr': getattr(e, 'ovr_promedio', 0),
                             'origen': origen, 'destino': destino, 'es_user': e.id == mi_equipo.id}
                            for e in equipos]
                user_asc = any(e.id == mi_equipo.id for e in ascenden)
                user_des = any(e.id == mi_equipo.id for e in descienden)
                estado['promo_releg_data'] = {
                    'ascendidos': _payload(ascenden, 2, 1),
                    'descendidos': _payload(descienden, 1, 2),
                    'user_ascendio': user_asc,
                    'user_descendio': user_des,
                }
            logger.info(
                f"Promo/releg {tipo_x} T{nueva_temp}: ascendieron {[e.nombre for e in ascenden]} "
                f"/ descendieron {[e.nombre for e in descienden]}"
            )
        if movimientos:
            estado.setdefault('promo_releg_data', {'ascendidos': [], 'descendidos': [],
                                                   'user_ascendio': False, 'user_descendio': False})
            estado['promo_releg_data']['todos_paises'] = movimientos
            estado['promo_releg_data']['premio_ascenso_user'] = premio_ascenso_user

        try:  # v4.4.0: temporada sin ningún objetivo cumplido → 0 a −2 según rendimiento
            from alpha_football.nivel_temporada import aplicar_objetivos
            aplicar_objetivos(estado)
        except Exception as e_nobj:
            logger.error(f"Error aplicando el bajón por objetivos: {e_nobj}")

        # 3b. Reubicar al usuario: estado['liga'] = la de su división; en los mapas
        #     primera/segunda_division la del user es el mismo objeto que estado['liga'].
        if user_asc:
            liga = liga_1a
            # v3.0.0: ascender no da copa; solo los puestos de copa de la tabla de 1ª
            estado['copa_clasificado_motivo'] = "Ascendiste a 1ª división (la copa se gana en la tabla de 1ª)."
        elif user_des:
            liga = liga_2a
            estado['copa_clasificado_motivo'] = "Descendiste a 2ª división."
        if liga_tipo:
            if liga_1a is not None:
                primeras[liga_tipo] = liga_1a
            if liga_2a is not None:
                segunda[liga_tipo] = liga_2a
        estado['liga'] = liga
        estado['equipos'] = liga.equipos
        estado['liga_usuario_division'] = getattr(liga, 'division', 1)

        # 4. Reset de temporada en la liga del user y en TODAS las de fondo
        #    (antes las 2ª jugaban una sola temporada y quedaban congeladas).
        todas = [liga] + [l for l in list(primeras.values()) + list(segunda.values())
                          if l is not None and l is not liga]
        for liga_r in todas:
            for eq in liga_r.equipos:
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
                    from alpha_football.sanciones import nueva_temporada as _sanc_nueva
                    _sanc_nueva(j)              # sanciones y amarillas de liga y copa a cero
                    j.energia = 100.0           # v3.1.0: pretemporada
            # 4b. Desarrollo pasivo de fin de temporada (envejecimiento + OVR).
            try:
                from alpha_football.desarrollo import progresar_liga_pasivo
                progresar_liga_pasivo(liga_r, 1)
            except Exception as e_dev_pasivo:
                logger.error(f"Error en desarrollo pasivo de fin de temporada: {e_dev_pasivo}")
            # 5. Calendario nuevo
            liga_r.calendario = []
            liga_r.jornada_actual = 1

        try:  # v4.4.0: tope bajón + curva por edad y correo al user con los cambios de nivel
            from alpha_football.nivel_temporada import aplicar_topes
            aplicar_topes(estado)
        except Exception as e_tope:
            logger.error(f"Error aplicando los topes de nivel: {e_tope}")

        # 4a-bis. v3.7.0: saves viejos → cada liga a 12 clubes (22 jornadas) y los países que
        #          falten (Italia, Uruguay, Ecuador). La temporada vieja ya cerró con su formato.
        try:
            from alpha_football.paises import completar_ligas
            completar_ligas(estado)
            estado['equipos'] = liga.equipos
        except Exception as e_comp:
            logger.error(f"Error completando las ligas a 12: {e_comp}")

        _pc.mostrar("PASANDO DE TEMPORADA", "Retiros y regens", 0.5)
        # 4b-bis. v2.3.8: retiros (35+ años, sorteado) → regens de su país y posición.
        try:
            from alpha_football.retiros import procesar_retiros
            procesar_retiros(estado)
        except Exception as e_ret:
            logger.error(f"Error procesando retiros: {e_ret}")

        _pc.mostrar("PASANDO DE TEMPORADA", "Mercado de pretemporada", 0.65)
        # 4c. v2.3.7: ingresos de la IA y mercado de pretemporada (los recién
        #     ascendidos fichan más para intentar mantenerse).
        try:
            from alpha_football.mercado_ia import ingresos_fin_temporada, ronda_fichajes_ia
            ingresos_fin_temporada(estado)
            estado['mercado_ia_log'] = []
            ronda_fichajes_ia(estado, 'pretemporada')
        except Exception as e_mia:
            logger.error(f"Error en el mercado de pretemporada de la IA: {e_mia}")

        try:  # v4.4.0: la IA vende a los que pidieron salir tras descender
            from alpha_football.mercado_ia import vender_salidas_forzadas
            vender_salidas_forzadas(estado)
        except Exception as e_sf:
            logger.error(f"Error vendiendo las salidas forzadas de la IA: {e_sf}")

        try:  # v4.4.0: objetivo de la IA para la temporada que empieza (tras la pretemporada)
            from alpha_football.nivel_temporada import foto_objetivos_ia
            foto_objetivos_ia(estado)
        except Exception as e_foto:
            logger.error(f"Error guardando los objetivos de la IA: {e_foto}")

        _pc.mostrar("PASANDO DE TEMPORADA", "Contratos y finanzas", 0.8)
        # 4d. v2.9.0: contratos (−1 año; los del user que vencen se van libres) y quiebra.
        try:
            from alpha_football.finanzas import cierre_temporada
            cierre_temporada(estado)
        except Exception as e_fin:
            logger.error(f"Error en el cierre financiero de la temporada: {e_fin}")

        # DESPUÉS del cierre de contratos: el que se va libre no recibe oferta ni se cotiza con su contrato viejo
        try:  # v4.4.0: primera tanda de ofertas para los que piden salir (la J1 ya es ventana)
            from alpha_football.salidas import ofertas_garantizadas
            ofertas_garantizadas(estado)
        except Exception as e_og:
            logger.error(f"Error creando las ofertas de pretemporada: {e_og}")
        try:  # J1 es ventana: vuelven los préstamos de 1 año y arrancan los acordados
            from alpha_football.prestamos import revisar_jornada as _prestamos_j1
            _prestamos_j1(estado)
        except Exception as e_pr:
            logger.error(f"Error con los préstamos al empezar la temporada: {e_pr}")

        _pc.mostrar("PASANDO DE TEMPORADA", "Sorteando las copas", 0.9)
        # 5. v3.8.0: copas de la temporada nueva (clasificados por la tabla final de cada 1ª).
        if not estado.get('copa_clasificado_motivo') and getattr(liga, 'division', 1) == 2:
            estado['copa_clasificado_motivo'] = "En 2ª división no se clasifica a copa."
        try:
            from alpha_football.ui.copa_screen import iniciar_copas_temporada
            iniciar_copas_temporada(estado, forzar=True)
        except Exception as e_copa_nueva:
            logger.error(f"Error al sortear las copas de la temporada nueva: {e_copa_nueva}")

        _pc.mostrar("PASANDO DE TEMPORADA", "Guardando la partida", 0.97)
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
                    "formacion": str(alin.formacion),
                    "convocados": list(getattr(alin, 'convocados', []) or []),
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
                # v2.3.5: división del usuario + 2ª divisiones + 1ª del país (tras el swap)
                **_save.campos_divisiones(estado),
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
    finally:
        if liga and mi_equipo:                  # sin partida no hubo carga que mostrar
            _pc.mostrar("PASANDO DE TEMPORADA", "Listo", 1.0)
        _pc.cerrar()


# v3.9.0: rects expuestos (ayuda H). AVANZAR sube a y=646 (antes 652: la barra de atajos lo pisaba).
R_BANNER = pygame.Rect(100, 82, 1080, 84)
R_BONO = pygame.Rect(100, 600, 1080, 40)
R_CLASIFICACION = pygame.Rect(100, 180, 520, 408)
R_PREMIOS = pygame.Rect(660, 180, 520, 408)
R_AVANZAR = pygame.Rect(SCREEN_W // 2 - 200, 646, 400, 48)


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
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                click_pos = R_AVANZAR.center   # v3.0.0: Enter/Espacio = EMPEZAR TEMPORADA (v3.9.0: centro del botón)

        def _centrado(txt, y, size, color):   # v3.0.0: texto centrado en pantalla
            draw_text(screen, txt, ((SCREEN_W - get_font(size).size(txt)[0]) // 2, y), size=size, color=color)

        # Dibujar fondo base
        draw_gradient_bg(screen)

        # Título
        _centrado("RESUMEN DE LA TEMPORADA", 18, 'xl', 'azul')

        # Banner de Campeón / Felicitaciones
        banner_rect = R_BANNER
        draw_panel(screen, banner_rect)
        # v2.3 (Fase 1): inicializar pos_user ANTES del if para que esté disponible
        # en el bloque del bono (líneas abajo) incluso si el user es campeón
        # (rama del if no asignaba pos_user → UnboundLocalError por frame).
        pos_user = 1
        if usuario_es_campeon:
            # Felicitaciones neón brillante al usuario por ganar la liga
            pygame.draw.rect(screen, COLORS['verde'], banner_rect, width=3, border_radius=8)
            _centrado("¡¡¡FELICITACIONES, ERES EL CAMPEÓN DE LA LIGA!!!", 94, 'lg', 'verde')
            _centrado(f"Has llevado a {mi_equipo.nombre} a la cima del fútbol local. ¡Una campaña histórica!", 136, 'sm', 'blanco')
        else:
            # El campeón es otro club de la IA
            _centrado(f"¡EL CAMPEÓN ES {campeon.nombre.upper()}!", 94, 'lg', 'dorado')
            pos_user = next((idx + 1 for idx, eq in enumerate(equipos_ordenados) if eq.id == mi_equipo.id), 1)
            _centrado(f"Tu equipo ({mi_equipo.corto}) finalizó en la posición #{pos_user}. ¡A por la revancha la próxima temporada!", 136, 'sm', 'blanco')

        # v0.8.2: F6/F7 — banner de bono de fin de temporada (variables por país/continente)
        try:
            # v0.8.7.3: si el user no clasificó, no hay bono de copa.
            # v3.8.0: fase de copa derivada del motor
            mejor_fase = (estado.get('copa_mejor_fase_temp') or 'Fase de liga') if estado.get('copa_user_en_copa') else 'No clasificado'
            # Reutilizamos las mismas tablas (deben coincidir con las de avanzar_nueva_temporada)
            _BONO_LIGA_POR_PAIS = {
                'premier':    [150_000_000, 90_000_000, 50_000_000, 50_000_000, 25_000_000, 25_000_000, 10_000_000, 10_000_000, 10_000_000, 10_000_000, 10_000_000, 10_000_000],
                'laliga':     [100_000_000, 60_000_000, 30_000_000, 30_000_000, 15_000_000, 15_000_000,  5_000_000,  5_000_000,  5_000_000,  5_000_000,  5_000_000,  5_000_000],
                'seriea':     [100_000_000, 60_000_000, 30_000_000, 30_000_000, 15_000_000, 15_000_000,  5_000_000,  5_000_000,  5_000_000,  5_000_000,  5_000_000,  5_000_000],   # v3.7.0
                'brasil':     [ 60_000_000, 35_000_000, 20_000_000, 20_000_000, 10_000_000, 10_000_000,  3_000_000,  3_000_000,  3_000_000,  3_000_000,  3_000_000,  3_000_000],
                'argentina':  [ 30_000_000, 18_000_000, 10_000_000, 10_000_000,  5_000_000,  5_000_000,  2_000_000,  2_000_000,  2_000_000,  2_000_000,  2_000_000,  2_000_000],
                'betplay':    [ 20_000_000, 12_000_000,  7_000_000,  7_000_000,  3_000_000,  3_000_000,  1_000_000,  1_000_000,  1_000_000,  1_000_000,  1_000_000,  1_000_000],
            }
            # v2.3: tabla de 2ª división ×2 (declarada a nivel de módulo arriba)
            # — _BONO_LIGA_2A_X2
            tipo_liga_b = getattr(liga, 'tipo', '') or ''
            # v2.3: si la liga es de 2ª división, usar tabla ×2
            liga_division_b = getattr(liga, 'division', 1)
            if liga_division_b == 2:
                tabla_bonos_b = _BONO_LIGA_2A_X2.get(tipo_liga_b) or _BONO_LIGA_2A_X2['betplay']
            else:
                tabla_bonos_b = _BONO_LIGA_POR_PAIS.get(tipo_liga_b) or _BONO_LIGA_POR_PAIS['betplay']
            idx_b = max(0, min(len(tabla_bonos_b) - 1, pos_user - 1))
            bono_liga = tabla_bonos_b[idx_b]
            bono_copa = _premios_copa_temporada(estado)      # v3.8.0: premios por fase ya cobrados
            bono_total = bono_liga + bono_copa
            if bono_total > 0:
                bono_rect = R_BONO
                draw_panel(screen, bono_rect)
                pygame.draw.rect(screen, COLORS['verde'], bono_rect, width=2, border_radius=8)
                _centrado(f"BONO DE FIN DE TEMPORADA: +€{bono_total:,}  "
                          f"(Liga: €{bono_liga:,}  ·  Copa: €{bono_copa:,})", 609, 'sm', 'verde')
        except Exception as e_bono:
            logger.error(f"Error al mostrar banner de bono: {e_bono}")

        # PANEL IZQUIERDO: Clasificación Final
        panel_izq = R_CLASIFICACION
        draw_panel(screen, panel_izq)
        draw_text(screen, "CLASIFICACIÓN FINAL", (120, 190), size='md', color='azul')
        
        headers = ["#", "Equipo", "PJ", "DG", "PTS"]
        h_x = [120, 160, 430, 480, 540]
        for h, x in zip(headers, h_x):
            draw_text(screen, h, (x, 226), size='sm', color='dorado')
            
        pygame.draw.line(screen, COLORS['azul'], (120, 246), (600, 246), 1)
        
        # Filas de la clasificación (v3.0.0: TODOS los equipos, alto de fila según cuántos haya)
        alto_fila = min(42, 330 // max(1, len(equipos_ordenados)))
        for idx, eq in enumerate(equipos_ordenados, 1):
            y = 252 + (idx - 1) * alto_fila
            color_row = 'verde' if eq.id == mi_equipo.id else ('dorado' if idx == 1 else 'blanco')
            
            draw_text(screen, str(idx), (120, y), size='sm', color=color_row)
            draw_text(screen, eq.nombre[:22], (160, y), size='sm', color=color_row)
            draw_text(screen, str(eq.pj), (430, y), size='sm', color=color_row)
            dg = eq.gf - eq.gc
            dg_str = f"+{dg}" if dg > 0 else str(dg)
            draw_text(screen, dg_str, (480, y), size='sm', color=color_row)
            draw_text(screen, str(eq.puntos), (540, y), size='sm', color=color_row)

        # PANEL DERECHO: Premios de la Temporada
        panel_der = R_PREMIOS
        draw_panel(screen, panel_der)
        draw_text(screen, "PREMIOS Y DISTINCIONES", (680, 190), size='md', color='azul')
        
        awards_y = 240
        
        # 1. Goleador
        if goleador_j:
            draw_text(screen, "BOTA DE ORO (MÁX. GOLEADOR)", (680, awards_y), size='sm', color='dorado')
            g_str = f"{goleador_j.nombre_completo} ({goleador_eq.corto}) — {goleador_j.goles} Goles"
            draw_text(screen, g_str, (680, awards_y + 20), size='sm', color='blanco')
            
        # 2. Asistidor
        if asistidor_j:
            draw_text(screen, "MÁXIMO ASISTENTE", (680, awards_y + 55), size='sm', color='dorado')
            a_str = f"{asistidor_j.nombre_completo} ({asistidor_eq.corto}) — {asistidor_j.asistencias} Asist."
            draw_text(screen, a_str, (680, awards_y + 75), size='sm', color='blanco')

        # 3. Valla Invicta
        if portero_j:
            draw_text(screen, "GUANTE DE ORO (VALLAS INVICTAS)", (680, awards_y + 110), size='sm', color='dorado')
            p_str = f"{portero_j.nombre_completo} ({portero_eq.corto}) — {portero_j.porterias_cero} Vallas"
            draw_text(screen, p_str, (680, awards_y + 130), size='sm', color='blanco')

        # 4. MVP Nota
        if mvp_j:
            draw_text(screen, "JUGADOR MVP (MEJOR RENDIMIENTO)", (680, awards_y + 165), size='sm', color='dorado')
            m_str = f"{mvp_j.nombre_completo} ({mvp_eq.corto}) — Nota: {mvp_j.promedio_nota}"
            draw_text(screen, m_str, (680, awards_y + 185), size='sm', color='blanco')

        # Hito del DT
        dt_text = f"Director Técnico: {estado.get('dt_nombre', 'DT')} ({estado.get('dt_nacionalidad', 'Colombia')})"
        draw_text(screen, dt_text, (680, awards_y + 240), size='sm', color='verde')

        # Botón Avanzar a Temporada 2
        btn_avanzar = R_AVANZAR
        hover_av = btn_avanzar.collidepoint(mouse_pos)
        
        texto_sig_temp = f"EMPEZAR TEMPORADA {estado.get('temporada', 1) + 1}  (Enter)"
        draw_button(screen, btn_avanzar, texto_sig_temp, hover_av)

        if click_pos and btn_avanzar.collidepoint(click_pos):
            # v2.3.4: primero ejecutar el swap, luego ver si hay datos de promo/releg.
            # El swap (avanzar_nueva_temporada) es quien CREA promo_releg_data, así que
            # debemos llamarlo ANTES de verificar el flag.
            avanzar_nueva_temporada(estado)
            return siguiente_pantalla_tras_temporada(estado)

        return None
    except Exception as e_render:
        logger.error(f"Error al renderizar resumen_temporada_screen: {e_render}")
        return "menu"
