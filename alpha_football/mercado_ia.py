# -*- coding: utf-8 -*-
"""
Alpha Football v2.3.7 — ECONOMÍA Y MERCADO DE LA IA.

- Presupuestos realistas por liga, división y prestigio del club.
- Ingresos de fin de temporada para los clubes de la IA (TV, patrocinio) y premio
  por ascenso para todos (también el usuario).
- Ascenso: toda la plantilla +4 de media (y +4 de potencial). Descenso: -2.
- Fichajes entre clubes de la IA de las 10 ligas: cada club busca reforzar su puesto
  más flojo del once con lo que su presupuesto le permite. Pretemporada = ronda grande
  (los recién ascendidos fichan más); ventanas del calendario = rondas pequeñas.
El equipo del usuario nunca compra ni vende aquí (sus ventas van por el buzón de ofertas).
"""
from __future__ import annotations

import logging
import random
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Rango de presupuesto de fichajes (USD) por (liga, división): club de 2 estrellas → 5 estrellas.
PRESUPUESTO_RANGO = {
    ('premier', 1): (60_000_000, 220_000_000),
    ('laliga', 1): (35_000_000, 200_000_000),
    ('brasil', 1): (10_000_000, 45_000_000),
    ('argentina', 1): (6_000_000, 30_000_000),
    ('betplay', 1): (2_000_000, 12_000_000),
    ('premier', 2): (12_000_000, 40_000_000),
    ('laliga', 2): (4_000_000, 15_000_000),
    ('brasil', 2): (2_000_000, 8_000_000),
    ('argentina', 2): (1_000_000, 4_000_000),
    ('betplay', 2): (500_000, 2_500_000),
    # v3.7.0: Italia como LaLiga; Uruguay y Ecuador como BetPlay.
    ('seriea', 1): (35_000_000, 200_000_000),
    ('seriea', 2): (4_000_000, 15_000_000),
    ('uruguay', 1): (2_000_000, 12_000_000),
    ('uruguay', 2): (500_000, 2_500_000),
    ('ecuador', 1): (2_000_000, 12_000_000),
    ('ecuador', 2): (500_000, 2_500_000),
}
INGRESO_TEMPORADA = 0.7        # fracción del presupuesto base que ingresa cada temporada (IA)
PRECIO_REMATE = 0.60           # v4.6.0: un club en quiebra remata a sus figuras al 60% del valor
N_REMATE = (2, 3)
COLCHON_QUIEBRA_IA = 0.10      # v4.6.0: quiebra si el rojo supera esta fracción de sus ingresos (calibración)
VARIACION_INGRESOS_IA = (0.75, 1.15)   # v4.6.0: temporadas buenas y malas (taquilla, TV, patrocinios)
BONO_ASCENSO_FRACCION = 1.0    # premio por ascenso = mínimo del rango de 1ª de ese país
SUBE_ASCENSO = 4
BAJA_DESCENSO = 2
_ATRIBUTOS = ("ataque", "defensa", "fisico", "tecnica", "mental")

PLANTILLA_MIN_VENDEDOR = 20    # un club no vende si se queda con menos
PLANTILLA_MAX_IA = 30          # por encima, libera a los peores suplentes
PROB_CLUB_VENTANA = 0.25       # clubes que buscan refuerzo por jornada con el mercado abierto
PROB_CLUB_INICIO = 0.50        # v0.4.11.0: en la ventana de inicio (reemplaza a la ronda de pretemporada)
MEJORA_MINIMA = 2             # el fichaje debe superar al titular más flojo por 2+


def _rango(tipo: str, division: int) -> tuple[int, int]:
    return PRESUPUESTO_RANGO.get((tipo, int(division or 1)), (1_000_000, 5_000_000))


def presupuesto_realista(tipo: str, division: int, estrellas: float,
                         rng: Optional[random.Random] = None) -> int:
    """Presupuesto de fichajes según liga, división y prestigio (estrellas 2..5), ±10%."""
    azar = rng or random
    minimo, maximo = _rango(tipo, division)
    t = max(0.0, min(1.0, (float(estrellas or 3.0) - 2.0) / 3.0))
    base = minimo + t * (maximo - minimo)
    return int(base * azar.uniform(0.9, 1.1))


def ligas_de_la_partida(estado: dict) -> list:
    """[(liga, tipo, division)] de las 10 ligas vivas (1ª y 2ª de los 5 países)."""
    res = []
    for division, clave in ((1, 'primera_division'), (2, 'segunda_division')):
        for tipo, liga in (estado.get(clave) or {}).items():
            if liga is not None and getattr(liga, 'equipos', None):
                res.append((liga, tipo, division))
    return res


def asignar_presupuestos_realistas(estado: dict, incluir_usuario: bool,
                                   rng: Optional[random.Random] = None) -> None:
    """Fija el presupuesto de cada club de las 10 ligas (el del user solo si se pide)."""
    mi_equipo = estado.get('mi_equipo')
    for liga, tipo, division in ligas_de_la_partida(estado):
        for eq in liga.equipos:
            if eq is mi_equipo and not incluir_usuario:
                continue
            try:
                eq.balance = presupuesto_realista(tipo, division, getattr(eq, 'estrellas', 3.0), rng)
            except Exception as e_bal:
                logger.error(f"No se pudo fijar el presupuesto de {getattr(eq, 'nombre', '?')}: {e_bal}")


def ingresos_fin_temporada(estado: dict, rng: Optional[random.Random] = None) -> list:
    """
    v4.6.0: al empezar la temporada cada club de la IA cobra sus ingresos (patrocinio + taquilla,
    como el user) y paga su masa salarial. El que queda en rojo quiebra (quiebra_ia).
    Devuelve los nombres de los clubes que quebraron.
    """
    from alpha_football.finanzas import ingresos_esperados, masa_salarial
    from alpha_football.entrenadores import dt_de, sueldo as sueldo_dt
    azar = rng or random.Random()
    mi_equipo = estado.get('mi_equipo')
    quebrados = []
    for liga, tipo, division in ligas_de_la_partida(estado):
        for eq in liga.equipos:
            for j in eq.jugadores:
                j.remate = False          # el remate dura hasta la temporada siguiente
            if eq is mi_equipo:
                continue  # el user cobra por jornada (finanzas.procesar_jornada)
            ingreso = int(ingresos_esperados(eq, tipo, division) * azar.uniform(*VARIACION_INGRESOS_IA))
            eq.balance = (int(getattr(eq, 'balance', 0) or 0) + ingreso - masa_salarial(eq)
                          - sueldo_dt(dt_de(estado, eq)))          # v4.6.0: + el sueldo de su DT
            if eq.balance < -COLCHON_QUIEBRA_IA * ingreso:
                quebrados.append(eq)
    for eq in quebrados:
        try:
            quiebra_ia(estado, eq, azar)
        except Exception as e_q:
            logger.error(f"Quiebra de {getattr(eq, 'nombre', '?')} fallida: {e_q}")
    return [eq.nombre for eq in quebrados]


def quiebra_ia(estado: dict, eq: Any, rng: Optional[random.Random] = None) -> list:
    """v4.6.0: remate de 2-3 figuras al 60%, sin fichajes esta temporada, −6 puntos y noticia."""
    from alpha_football.finanzas import PUNTOS_QUIEBRA
    from alpha_football.market import traspasado_en_ventana, calcular_valor
    azar = rng or random.Random()
    temporada = int(estado.get('temporada', 1) or 1)
    mi_equipo = estado.get('mi_equipo')
    eq.sin_fichajes_hasta = temporada
    eq.puntos = int(getattr(eq, 'puntos', 0) or 0) - PUNTOS_QUIEBRA
    eq.sancion_puntos = int(getattr(eq, 'sancion_puntos', 0) or 0) + PUNTOS_QUIEBRA
    compradores = [(c, t) for liga, t, d in ligas_de_la_partida(estado) if d == 1 for c in liga.equipos
                   if c is not eq and c is not mi_equipo]
    figuras = sorted([j for j in eq.jugadores if not getattr(j, 'prestamo', None)
                      and not traspasado_en_ventana(estado, j)], key=lambda j: -j.overall)
    rematados = []
    for j in figuras[:azar.randint(*N_REMATE)]:
        if len(eq.jugadores) <= PLANTILLA_MIN_VENDEDOR:
            break
        precio = int((int(getattr(j, 'valor', 0) or 0) or calcular_valor(j)) * PRECIO_REMATE)
        pueden = [(c, t) for c, t in compradores
                  if int(getattr(c, 'balance', 0) or 0) >= precio and len(c.jugadores) < PLANTILLA_MAX_IA]
        if not pueden:
            j.remate = True           # nadie pudo pagar: el user lo puede comprar al precio de remate
            rematados.append((j, None, precio))
            continue
        comprador, tipo_c = azar.choice(pueden)
        _traspasar(j, eq, comprador, precio, tipo_c)
        try:
            from alpha_football.negociacion import registrar_pase
            registrar_pase(estado, j, eq.nombre, comprador.nombre, precio, False)
        except Exception as e_h:
            logger.error(f"No se pudo registrar el remate: {e_h}")
        rematados.append((j, comprador, precio))
    try:
        from alpha_football import correo as C
        lineas = [f"{j.nombre_completo} ({j.posicion} {j.overall}) → "
                  + (f"{comp.nombre} por ${p / 1_000_000:.1f}M" if comp is not None
                     else f"sin comprador: disponible por ${p / 1_000_000:.1f}M")
                  for j, comp, p in rematados]
        C.enviar(estado, 'prensa', f"Quiebra en {eq.nombre}",
                 f"{eq.nombre} se ha declarado en quiebra. La liga le resta {PUNTOS_QUIEBRA} puntos y no podrá "
                 "fichar esta temporada. "
                 + ("Jugadores rematados: " + "; ".join(lineas) + "." if lineas else "No tenía jugadores para rematar."),
                 C.accion('buscador_screen', "VER BUSCADOR"))
    except Exception as e_c:
        logger.error(f"No se pudo enviar la noticia de la quiebra: {e_c}")
    logger.info(f"Quiebra de la IA: {eq.nombre} ({len(rematados)} rematados)")
    return rematados


def _mover_media(jugador: Any, delta: int) -> None:
    """Mueve la media exactamente `delta` repartiendo 5*delta puntos entre los atributos
    que tienen margen (un crack con varios 99 igual sube lo que le toca)."""
    paso = 1 if delta > 0 else -1
    pendientes = abs(int(delta)) * 5
    while pendientes > 0:
        movibles = [a for a in _ATRIBUTOS if 10 <= int(getattr(jugador, a)) + paso <= 99]
        if not movibles:
            break
        for attr in movibles:
            if pendientes == 0:
                break
            setattr(jugador, attr, int(getattr(jugador, attr)) + paso)
            pendientes -= 1


def aplicar_ascenso(equipo: Any, tipo: str, estado: Optional[dict] = None) -> int:
    """v4.4.0: +3 a +6 según rendimiento (techo 83, nivel_temporada) y premio por ascenso."""
    try:
        from alpha_football.nivel_temporada import aplicar
        aplicar(equipo, 'ascenso', estado)
    except Exception as e_niv:
        logger.error(f"Error aplicando el ascenso de {getattr(equipo, 'nombre', '?')}: {e_niv}")
    premio = int(_rango(tipo, 1)[0] * BONO_ASCENSO_FRACCION)
    equipo.balance = int(getattr(equipo, 'balance', 0) or 0) + premio
    return premio


def aplicar_descenso(equipo: Any, estado: Optional[dict] = None) -> None:
    """v4.4.0: −2 a −5 según rendimiento (nivel_temporada)."""
    try:
        from alpha_football.nivel_temporada import aplicar
        aplicar(equipo, 'descenso', estado)
    except Exception as e_niv:
        logger.error(f"Error aplicando el descenso de {getattr(equipo, 'nombre', '?')}: {e_niv}")


def _recalcular_valores(equipo: Any) -> None:
    try:
        from alpha_football.market import calcular_valor
        for j in equipo.jugadores:
            j.valor = calcular_valor(j)
    except Exception as e_val:
        logger.debug(f"No se pudieron recalcular valores de {getattr(equipo, 'nombre', '?')}: {e_val}")


# --- Fichajes entre clubes de la IA ─────────────────────────────────────────────

def _riqueza_liga(tipo: str, division: int) -> int:
    return _rango(tipo, division)[1]


def _nivel(equipo: Any) -> int:
    from alpha_football.market import nivel_club
    return nivel_club(equipo)


def _puesto_mas_flojo(equipo: Any, rng: random.Random) -> Optional[tuple[str, int]]:
    """(posición, OVR) del titular más flojo del mejor 4-3-3 del club."""
    from alpha_football.formaciones import mejor_once
    js = equipo.jugadores
    once = [js[i] for i in mejor_once(js, "4-3-3") if 0 <= i < len(js)]
    if not once:
        return None
    peor = min(once, key=lambda j: (j.overall, rng.random()))
    return peor.posicion, peor.overall


def _buscar_refuerzo(comprador: Any, tipo_c: str, div_c: int, equipos: list, mi_equipo: Any,
                     limite: float, ascendido: bool, rng: random.Random,
                     estado: Optional[dict] = None) -> Optional[tuple]:
    from alpha_football.market import precio_compra, traspasado_en_ventana
    flojo = _puesto_mas_flojo(comprador, rng)
    if flojo is None:
        return None
    posicion, ovr_flojo = flojo
    nivel_c = _nivel(comprador)
    riqueza_c = _riqueza_liga(tipo_c, div_c)
    tolerancia = 10 if ascendido else 6
    mejores = []
    for vendedor, tipo_v, div_v in equipos:
        if vendedor is comprador or vendedor is mi_equipo:
            continue
        if len(vendedor.jugadores) <= PLANTILLA_MIN_VENDEDOR:
            continue
        top3 = None   # v3.7.0: perezoso (16 ligas: ordenar cada plantilla para cada comprador era lo más caro)
        nivel_v = None
        for j in vendedor.jugadores:
            if getattr(j, 'prestamo', None):   # a préstamo: no se toca
                continue
            if traspasado_en_ventana(estado, j):   # ya cambió de club en esta ventana
                continue
            if j.posicion != posicion or j.overall < ovr_flojo + MEJORA_MINIMA:
                continue
            if getattr(j, 'lesion_partidos', 0) > 0:
                continue
            # El jugador acepta si el club está a su altura o si la liga paga más.
            if j.overall > nivel_c + tolerancia and riqueza_c <= _riqueza_liga(tipo_v, div_v):
                continue
            precio = precio_compra(j)
            if top3 is None:
                top3 = sorted(vendedor.jugadores, key=lambda x: x.overall, reverse=True)[:3]
            if j in top3:
                # las figuras solo se van a un club más grande, y con sobreprecio
                nivel_v = nivel_v if nivel_v is not None else _nivel(vendedor)
                if nivel_c < nivel_v and riqueza_c <= _riqueza_liga(tipo_v, div_v):
                    continue
                precio = int(precio * 1.25)
            if precio > limite:
                continue
            mejora = j.overall - ovr_flojo
            edad = int(getattr(j, 'edad', 27) or 27)
            puntaje = mejora * 10 - (precio / max(1.0, limite)) * 6 - max(0, edad - 30) * 2 + rng.random() * 4
            mejores.append((puntaje, j, vendedor, precio))
    if not mejores:
        return None
    mejores.sort(key=lambda m: m[0], reverse=True)
    return mejores[0][1:]


def _traspasar(jugador: Any, vendedor: Any, comprador: Any, precio: int, tipo_c: str) -> None:
    from alpha_football.market import calcular_valor, registrar_region_jugador
    comprador.balance -= precio
    vendedor.balance += precio
    vendedor.jugadores.remove(jugador)
    comprador.jugadores.append(jugador)
    registrar_region_jugador(jugador, tipo_c)
    jugador.valor = calcular_valor(jugador)
    jugador.salida_forzada = False      # v4.4.0: ya salió del club que descendió (no se revende)
    # Los índices de una alineación guardada ya no valen: la IA vuelve a su mejor once.
    for eq in (vendedor, comprador):
        if getattr(eq, 'alineacion_activa', None) is not None:
            eq.alineacion_activa = None


def _liberar_sobrantes(equipo: Any) -> None:
    """Deja la plantilla en PLANTILLA_MAX_IA liberando a los peores que no son titulares."""
    from alpha_football.formaciones import mejor_once
    while len(equipo.jugadores) > PLANTILLA_MAX_IA:
        titulares = {id(equipo.jugadores[i]) for i in mejor_once(equipo.jugadores, "4-3-3")}
        suplentes = [j for j in equipo.jugadores if id(j) not in titulares
                     and not getattr(j, 'prestamo', None)]   # a préstamo: no se toca
        if not suplentes:
            break
        equipo.jugadores.remove(min(suplentes, key=lambda j: (j.overall, -int(getattr(j, 'edad', 25) or 25))))


def ronda_fichajes_ia(estado: dict, modo: str = 'ventana',
                      rng: Optional[random.Random] = None) -> list[str]:
    """
    Una ronda de fichajes entre los clubes de la IA de las 16 ligas (v3.7.0).
    modo='pretemporada': todos buscan (hasta 2 fichajes; 3 los recién ascendidos) con el 90%
    del presupuesto. modo='ventana': 25% de los clubes (50% en la ventana de inicio; los recién
    ascendidos, 2 intentos), con el 60%.
    Retorna el log de movimientos (también se acumula en estado['mercado_ia_log']).
    """
    azar = rng or random.Random()
    mi_equipo = estado.get('mi_equipo')
    try:
        from alpha_football.market import registrar_regiones
        registrar_regiones(estado)
    except Exception as e_reg:
        logger.error(f"No se pudieron registrar las regiones de los jugadores: {e_reg}")
    equipos = [(eq, tipo, div) for liga, tipo, div in ligas_de_la_partida(estado) for eq in liga.equipos]
    ascendidos = set(estado.get('_recien_ascendidos') or [])
    compradores = [c for c in equipos if c[0] is not mi_equipo]
    azar.shuffle(compradores)
    en_inicio = False              # v0.4.11.0
    try:
        from alpha_football.market import ventana_actual
        liga_u = estado.get('liga')
        v = ventana_actual(int(getattr(liga_u, 'jornada_actual', 1) or 1),
                           int(getattr(liga_u, 'num_jornadas', 22) or 22))
        en_inicio = bool(v) and v[2] == 'inicio'
    except Exception as e_v:
        logger.error(f"No se pudo leer la ventana de mercado: {e_v}")
    log = []
    for comprador, tipo_c, div_c in compradores:
        if int(getattr(comprador, 'sin_fichajes_hasta', 0) or 0) >= int(estado.get('temporada', 1) or 1):
            continue   # v4.6.0: quebró esta temporada
        es_asc = getattr(comprador, 'nombre', '') in ascendidos
        if modo == 'pretemporada':
            intentos, fraccion = (3 if es_asc else 2), 0.9
        else:
            if azar.random() > (PROB_CLUB_INICIO if en_inicio else PROB_CLUB_VENTANA):
                continue
            intentos, fraccion = (2 if es_asc and en_inicio else 1), 0.6
        for _ in range(intentos):
            try:
                limite = max(0, int(getattr(comprador, 'balance', 0) or 0)) * fraccion
                if limite <= 0:
                    break
                hallado = _buscar_refuerzo(comprador, tipo_c, div_c, equipos, mi_equipo, limite, es_asc, azar, estado)
                if hallado is None:
                    break
                jugador, vendedor, precio = hallado
                _traspasar(jugador, vendedor, comprador, precio, tipo_c)
                try:  # v2.7.0: historial general de pases
                    from alpha_football.negociacion import registrar_pase
                    registrar_pase(estado, jugador, vendedor.nombre, comprador.nombre, precio, False)
                except Exception as e_hist:
                    logger.error(f"No se pudo registrar el pase de la IA: {e_hist}")
                log.append(f"{comprador.nombre} ficha a {jugador.nombre_completo} ({jugador.posicion} "
                           f"{jugador.overall}) de {vendedor.nombre} por ${precio:,}")
            except Exception as e_fichaje:
                logger.error(f"Fichaje de la IA fallido para {getattr(comprador, 'nombre', '?')}: {e_fichaje}")
                break
        if len(comprador.jugadores) > PLANTILLA_MAX_IA:
            _liberar_sobrantes(comprador)
    if log:
        historial = estado.setdefault('mercado_ia_log', [])
        historial.extend(log)
        del historial[:-60]
        logger.info(f"Mercado IA ({modo}): {len(log)} fichajes.")
    return log


def vender_salidas_forzadas(estado: dict, rng: Optional[random.Random] = None) -> list[str]:
    """v4.4.0: los clubes de la IA venden a los que pidieron salir tras descender (a clubes de 1ª)."""
    from alpha_football.market import traspasado_en_ventana
    azar = rng or random.Random()
    mi_equipo = estado.get('mi_equipo')
    primeras = [(eq, tipo) for liga, tipo, div in ligas_de_la_partida(estado) if div == 1 for eq in liga.equipos
                if eq is not mi_equipo]
    log = []
    for liga, _tipo, _div in ligas_de_la_partida(estado):
        for vendedor in list(liga.equipos):
            if vendedor is mi_equipo:
                continue
            for j in [x for x in vendedor.jugadores if getattr(x, 'salida_forzada', False)
                      and not getattr(x, 'prestamo', None)     # a préstamo: no se toca
                      and not traspasado_en_ventana(estado, x)]:
                if len(vendedor.jugadores) <= PLANTILLA_MIN_VENDEDOR:
                    break   # no se desarma la plantilla: los que quedan salen en la próxima ventana
                try:
                    from alpha_football.market import calcular_valor
                    valor = int(getattr(j, 'valor', 0) or 0) or calcular_valor(j)
                    cands = [(eq, t) for eq, t in primeras if eq is not vendedor]
                    # primero los que tienen lugar en la plantilla
                    cands = [(eq, t) for eq, t in cands if len(eq.jugadores) < PLANTILLA_MAX_IA] or cands
                    if not cands:
                        continue
                    pueden = [(eq, t) for eq, t in cands if int(getattr(eq, 'balance', 0) or 0) >= valor]
                    if pueden:
                        comprador, tipo_c = azar.choice(pueden)
                        precio = valor
                    else:
                        comprador, tipo_c = max(cands, key=lambda c: int(getattr(c[0], 'balance', 0) or 0))
                        precio = min(int(valor * 0.8), max(0, int(getattr(comprador, 'balance', 0) or 0)))
                    _traspasar(j, vendedor, comprador, precio, tipo_c)
                    j.salida_forzada = False
                    if len(comprador.jugadores) > PLANTILLA_MAX_IA:
                        _liberar_sobrantes(comprador)
                    try:
                        from alpha_football.negociacion import registrar_pase
                        registrar_pase(estado, j, vendedor.nombre, comprador.nombre, precio, False)
                    except Exception as e_hist:
                        logger.error(f"No se pudo registrar la salida forzada: {e_hist}")
                    log.append(f"{comprador.nombre} ficha a {j.nombre_completo} de {vendedor.nombre} (descenso) por ${precio:,}")
                except Exception as e_sf:
                    logger.error(f"Salida forzada fallida de {getattr(j, 'nombre', '?')}: {e_sf}")
    if log:
        estado.setdefault('mercado_ia_log', []).extend(log)
    return log


# --- v3.1.0: clubes de la IA que pagan la cláusula de un jugador del user ---
PROB_CLAUSULA = 0.10          # por jornada con la ventana abierta
PROB_NEGATIVA = 0.40


def pago_clausulas(estado: dict, rng: Optional[random.Random] = None, prob: float = PROB_CLAUSULA) -> Optional[dict]:
    """Un club de 1ª de la IA paga la cláusula de un jugador del user (el user no puede negarse)."""
    try:
        from alpha_football import correo as C
        from alpha_football.finanzas import quitar_de_plantilla, PLANTILLA_MINIMA, completar_plantilla
        azar = rng or random.Random()
        mi = estado.get('mi_equipo')
        if mi is None or azar.random() > prob or len(mi.jugadores) <= PLANTILLA_MINIMA:
            return None
        compradores = [(eq, tipo) for tipo, liga in (estado.get('primera_division') or {}).items()
                       if liga is not None for eq in liga.equipos if eq is not mi and eq.id != mi.id]
        cands = []
        from alpha_football.market import traspasado_en_ventana
        for j in mi.jugadores:
            if getattr(j, 'prestamo', None) or traspasado_en_ventana(estado, j):   # a préstamo / recién llegado
                continue
            c = int(getattr(j, 'clausula', 0) or 0)
            ricos = [(eq, t) for eq, t in compradores if c > 0 and eq.balance >= c]
            if ricos:
                cands.append((j, c, ricos))
        if not cands:
            return None
        j, c, ricos = azar.choices(cands, weights=[jj.overall / max(0.1, cc / 1_000_000) for jj, cc, _ in cands])[0]
        comprador, tipo_c = azar.choices(ricos, weights=[1.5 if eq.ovr_promedio > mi.ovr_promedio else 1.0
                                                         for eq, _ in ricos])[0]
        if (j.personalidad != 'mercenario' and j.moral >= 70 and comprador.ovr_promedio < mi.ovr_promedio
                and azar.random() < PROB_NEGATIVA):
            j.moral = min(100, j.moral + 5)
            C.enviar(estado, 'jugador', f"{j.nombre} {j.apellido} rechazó irse a {comprador.nombre}",
                     f"Míster, {comprador.nombre} pagó mi cláusula (${c:,}), pero yo quiero seguir aquí. "
                     "Estoy a gusto en este club y quiero seguir peleando con este grupo.",
                     C.accion('plantilla_screen', "VER PLANTILLA"))
            return {'jugador': j, 'comprador': comprador, 'monto': c, 'rechazo': True}
        from alpha_football.market import registrar_region_jugador
        from alpha_football.negociacion import registrar_pase
        comprador.balance -= c
        quitar_de_plantilla(mi, j)
        completar_plantilla(mi)                 # v3.1.0: nunca sin porteros ni por debajo del mínimo
        comprador.jugadores.append(j)
        comprador.alineacion_activa = None
        j.transferible = j.pide_salir = False
        try:  # v4.4.0: se borra la escalada de salida
            from alpha_football.salidas import limpiar as _limpiar_salida
            _limpiar_salida(j)
        except Exception as e_lim:
            logger.error(f"No se pudo limpiar la salida: {e_lim}")
        registrar_region_jugador(j, tipo_c)
        registrar_pase(estado, j, mi.nombre, comprador.nombre, c, True)
        from alpha_football.contraofertas import acreditar_venta   # v4.4.0: 25% para el club + correo
        acreditar_venta(estado, j, comprador, c, f"{comprador.nombre} pagó la cláusula de {j.nombre} {j.apellido}")
        return {'jugador': j, 'comprador': comprador, 'monto': c, 'rechazo': False}
    except Exception as e:
        logger.error(f"Error en el pago de cláusulas de la IA: {e}")
        return None
