# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Finanzas y contratos (v2.9.0)
Cada jornada de liga el club del user cobra patrocinio (y taquilla si es local) y paga
salarios. Con saldo negativo no se puede fichar; tras JORNADAS_ROJO_VENTA jornadas en rojo
la directiva vende al jugador más valioso, y cerrar la temporada en negativo = despido.
Contratos: salario anual, años restantes y cláusula; al cerrar la temporada se descuenta
un año y el que llega a 0 se va libre (la IA renueva sola).
Los ingresos se escalan con el rango de presupuestos de cada liga (mercado_ia).
"""
from __future__ import annotations

import logging
import random
from typing import Optional

logger = logging.getLogger(__name__)
from alpha_football.sanciones import sancionado as _sancionado  # noqa: E402  sanción de la competición que se juega

SALARIO_PCT_VALOR = 0.05        # salario anual = 5% del valor de mercado
SALARIO_MIN = 20_000
CLAUSULA_MULT_INICIAL = 2.0
PATROCINIO_FRAC = 0.40          # patrocinio de la temporada = 40% del presupuesto medio de la liga
TAQUILLA_FRAC = 0.50            # taquilla de la temporada (de local) = 50% del presupuesto medio
FACTOR_TAQUILLA = {'victoria': 1.2, 'empate': 1.0, 'derrota': 0.85}
JORNADAS_ROJO_VENTA = 3
VENTA_FORZADA_FRAC = 0.8        # la directiva malvende al 80% del valor
CLAVES_LIBRO = ['taquilla', 'patrocinio', 'salarios', 'fichajes', 'ventas', 'premios', 'directiva']  # v3.2.0: + espaldarazo


def _valor(j) -> int:
    try:
        from alpha_football.market import calcular_valor
        return int(calcular_valor(j))
    except Exception:
        return int(getattr(j, 'valor', 0) or 0)


def salario_mercado(j) -> int:
    """v3.1.0: lo que 'merece' cobrar según su valor (base de contratos y de la moral)."""
    return max(SALARIO_MIN, int(_valor(j) * SALARIO_PCT_VALOR))


def contrato_inicial(j, rng: Optional[random.Random] = None) -> tuple[int, int, int]:
    """(salario anual, años, cláusula) de un contrato nuevo según valor y edad."""
    azar = rng or random.Random(f"{j.nombre}|{j.apellido}|{j.edad}|{j.posicion}")
    v = _valor(j)
    edad = int(getattr(j, 'edad', 25) or 25)
    if edad <= 23:
        anios = azar.randint(3, 5)
    elif edad <= 29:
        anios = azar.randint(2, 4)
    elif edad <= 31:
        anios = azar.randint(1, 3)
    else:
        anios = azar.randint(1, 2)
    return salario_mercado(j), anios, int(v * CLAUSULA_MULT_INICIAL)


def asegurar_contrato(j) -> None:
    """Le da contrato a un jugador que todavía no tiene (saves viejos, regens, libres)."""
    if int(getattr(j, 'salario', 0) or 0) <= 0:
        j.salario, j.contrato_anios, j.clausula = contrato_inicial(j)


def _todos_los_equipos(estado: dict) -> list:
    vistos, equipos = set(), []
    for clave in ('primera_division', 'segunda_division'):
        for liga in (estado.get(clave) or {}).values():
            for eq in getattr(liga, 'equipos', []) or []:
                if id(eq) not in vistos:
                    vistos.add(id(eq)); equipos.append(eq)
    mi = estado.get('mi_equipo')
    if mi is not None and id(mi) not in vistos:
        equipos.append(mi)
    return equipos


def asegurar_contratos(estado: dict) -> None:
    for eq in _todos_los_equipos(estado):
        for j in eq.jugadores:
            asegurar_contrato(j)
    for j in estado.get('free_agents_list') or []:
        asegurar_contrato(j)


def masa_salarial(equipo, estado: Optional[dict] = None) -> int:
    """Sueldos anuales que paga el club: los propios, solo su % de los que tiene a préstamo y, con
    `estado`, el % que sigue pagando de sus cedidos (prestamos.py)."""
    total = 0
    for j in getattr(equipo, 'jugadores', []) or []:
        asegurar_contrato(j)
        p = getattr(j, 'prestamo', None)
        total += int(j.salario) * (100 - int(p['pct_dueno'])) // 100 if p else int(j.salario)
    if estado is not None:
        try:
            from alpha_football.prestamos import cedidos
            for j, _club in cedidos(estado, getattr(equipo, 'nombre', None)):
                total += int(j.salario) * int(j.prestamo['pct_dueno']) // 100
        except Exception as e:
            logger.error(f"No se pudo sumar el sueldo de los cedidos: {e}")
    return total


def presupuesto_medio(liga) -> int:
    try:
        from alpha_football.mercado_ia import _rango
        lo, hi = _rango(getattr(liga, 'tipo', 'betplay'), getattr(liga, 'division', 1) or 1)
    except Exception:
        lo, hi = 1_000_000, 5_000_000
    return (lo + hi) // 2


def libro(estado: dict) -> dict:
    """Movimientos de la temporada actual (se reinicia al empezar otra)."""
    dc = estado.setdefault('datos_carrera', {})
    temporada = int(estado.get('temporada', 1) or 1)
    lib = dc.get('finanzas')
    if not isinstance(lib, dict) or lib.get('temporada') != temporada:
        if isinstance(lib, dict):
            dc['finanzas_anterior'] = lib
        lib = dc['finanzas'] = {'temporada': temporada, **{k: 0 for k in CLAVES_LIBRO}}
    for k in CLAVES_LIBRO:          # v3.2.0: saves viejos sin las claves nuevas
        lib.setdefault(k, 0)
    return lib


def registrar(estado: dict, clave: str, monto: int, temporada: Optional[int] = None) -> None:
    """Suma al libro de la temporada actual (o al de `temporada` si es la anterior)."""
    dc = estado.setdefault('datos_carrera', {})
    anterior = dc.get('finanzas_anterior') or {}
    actual = dc.get('finanzas') or {}
    if temporada is not None and actual.get('temporada') != temporada and anterior.get('temporada') == temporada:
        lib = anterior
    elif temporada is not None and actual.get('temporada') == temporada:
        lib = actual
    else:
        lib = libro(estado)
    lib[clave] = int(lib.get(clave, 0)) + int(monto)


def quitar_de_plantilla(equipo, jugador) -> None:
    """Saca al jugador y reindexa la alineación (los titulares son índices de la lista)."""
    jugadores = equipo.jugadores
    if jugador not in jugadores:
        return
    alin = getattr(equipo, 'alineacion_activa', None)
    tit = [jugadores[i] for i in (getattr(alin, 'titulares', []) or []) if 0 <= i < len(jugadores)] if alin else []
    conv = [jugadores[i] for i in (getattr(alin, 'convocados', []) or []) if 0 <= i < len(jugadores)] if alin else []
    jugadores.remove(jugador)
    if alin is None:
        return
    try:
        from alpha_football import formaciones as Fm
        hueco = next((k for k, o in enumerate(tit) if o is jugador), None)
        alin.titulares = [jugadores.index(o) for o in tit if o is not jugador]
        alin.convocados = [jugadores.index(o) for o in conv if o is not jugador]
        if hueco is not None and len(alin.titulares) == 10:
            # sale un titular: se cubre solo su puesto (mismo slot) con el mejor disponible,
            # prefiriendo su misma posición; el resto del once que armó el user queda igual
            libres = [i for i, o in enumerate(jugadores)
                      if i not in alin.titulares and getattr(o, 'lesion_partidos', 0) == 0
                      and not _sancionado(o)]
            misma = [i for i in libres if getattr(jugadores[i], 'posicion', '') == getattr(jugador, 'posicion', '')]
            if not misma and getattr(jugador, 'posicion', '') != 'POR':
                misma = [i for i in libres if getattr(jugadores[i], 'posicion', '') != 'POR']
            cands = misma or libres
            if cands:
                reemplazo = max(cands, key=lambda i: getattr(jugadores[i], 'overall', 0))
                alin.titulares.insert(min(hueco, len(alin.titulares)), reemplazo)
                alin.convocados = [i for i in alin.convocados if i != reemplazo]
        if len(alin.titulares) < 11:
            alin.titulares = Fm.mejor_once(jugadores, alin.formacion)
        Fm.normalizar_convocados(alin, jugadores)
    except Exception as e:
        logger.error(f"No se pudo reindexar la alineación: {e}")


def vender_mejor(estado: dict) -> Optional[str]:
    """Venta forzada por la directiva: el más valioso al club más rico, al 80% del valor."""
    mi = estado.get('mi_equipo')
    if mi is None or not mi.jugadores:
        return None
    from alpha_football import traspasos_pendientes as TP
    vendibles = [j for j in mi.jugadores if TP.pendiente_de(estado, j) is None   # no vender dos veces al mismo
                 and not getattr(j, 'prestamo', None)]                           # a préstamo: no se toca
    if not vendibles:
        return None
    estrella = max(vendibles, key=_valor)
    rivales = [e for e in _todos_los_equipos(estado) if e is not mi and e.id != mi.id]
    if not rivales:
        return None
    comprador = max(rivales, key=lambda e: int(getattr(e, 'balance', 0) or 0))
    monto = int(_valor(estrella) * VENTA_FORZADA_FRAC)
    if not TP.mercado_abierto(estado):
        # la venta es inmediata (la plata entra ya), pero el jugador se va cuando abra el mercado
        aviso = TP.diferir_venta(estado, estrella, comprador, monto)
        comprador.balance = max(0, int(comprador.balance) - monto)
        from alpha_football.contraofertas import acreditar_venta
        acreditar_venta(estado, estrella, comprador, monto, extra=aviso)
        texto = (f"Quiebra: la directiva vendió a {estrella.nombre_completo} a {comprador.nombre} "
                 f"por ${monto / 1_000_000:.1f}M (se va en la jornada {TP.jornada_apertura(estado)})")
        estado.setdefault('transfer_log', []).append(texto)
        logger.info(texto)
        return texto
    quitar_de_plantilla(mi, estrella)
    comprador.jugadores.append(estrella)
    estrella.transferible = estrella.pide_salir = False     # v3.1.0
    try:  # v4.4.0: se borra la escalada de salida
        from alpha_football.salidas import limpiar as _limpiar_salida
        _limpiar_salida(estrella)
    except Exception as e_lim:
        logger.error(f"No se pudo limpiar la salida: {e_lim}")
    comprador.balance = max(0, int(comprador.balance) - monto)
    from alpha_football.contraofertas import acreditar_venta
    acreditar_venta(estado, estrella, comprador, monto)     # v4.4.0: 25% para el club + correo
    try:
        from alpha_football.negociacion import registrar_pase
        registrar_pase(estado, estrella, mi.nombre, comprador.nombre, monto, True)
    except Exception as e:
        logger.error(f"No se pudo registrar la venta forzada: {e}")
    completar_plantilla(mi)                    # v2.9.1: nunca sin portero; reemplazos con contrato
    texto = (f"Quiebra: la directiva vendió a {estrella.nombre_completo} a {comprador.nombre} "
             f"por ${monto / 1_000_000:.1f}M")
    estado.setdefault('transfer_log', []).append(texto)
    logger.info(texto)
    return texto


def procesar_jornada(estado: dict, es_local: bool, gf: int, gc: int) -> dict:
    """Cobros y pagos de una jornada de liga del user + control de quiebra."""
    mi, liga = estado.get('mi_equipo'), estado.get('liga')
    if mi is None or liga is None:
        return {}
    n = max(1, int(getattr(liga, 'num_jornadas', 10) or 10))
    medio = presupuesto_medio(liga)
    resultado = 'victoria' if gf > gc else 'derrota' if gf < gc else 'empate'
    patrocinio = int(medio * PATROCINIO_FRAC / n)
    taquilla = int(medio * TAQUILLA_FRAC / max(1, n / 2) * FACTOR_TAQUILLA[resultado]) if es_local else 0
    salarios = masa_salarial(mi, estado) // n
    mi.balance = int(mi.balance) + patrocinio + taquilla - salarios
    registrar(estado, 'patrocinio', patrocinio)
    registrar(estado, 'taquilla', taquilla)
    registrar(estado, 'salarios', salarios)
    dc = estado.setdefault('datos_carrera', {})
    estado.pop('aviso_finanzas', None)
    if mi.balance < 0:
        dc['jornadas_en_rojo'] = int(dc.get('jornadas_en_rojo', 0)) + 1
        if dc['jornadas_en_rojo'] >= JORNADAS_ROJO_VENTA:
            dc['jornadas_en_rojo'] = 0
            estado['aviso_finanzas'] = vender_mejor(estado) or "Quiebra: no se pudo vender a nadie."
        else:
            faltan = JORNADAS_ROJO_VENTA - dc['jornadas_en_rojo']
            estado['aviso_finanzas'] = (f"Saldo negativo: en {faltan} jornada{'s' if faltan != 1 else ''} "
                                        f"la directiva venderá a tu mejor jugador")
    else:
        dc['jornadas_en_rojo'] = 0
    return {'patrocinio': patrocinio, 'taquilla': taquilla, 'salarios': salarios}


def cierre_temporada(estado: dict) -> list:
    """
    Fin de temporada: contratos −1 año (los del user que llegan a 0 se van libres; la IA
    renueva sola) y despido si el saldo quedó negativo. Devuelve las salidas del user.
    """
    try:   # cedidos con el contrato por vencer vuelven a su dueño antes de descontar
        from alpha_football.prestamos import cierre_contratos
        cierre_contratos(estado)
    except Exception as e_pr:
        logger.error(f"No se pudieron cerrar los préstamos por contrato: {e_pr}")
    asegurar_contratos(estado)
    mi = estado.get('mi_equipo')
    salidas = []
    azar = random.Random(f"cierre-{estado.get('temporada', 1)}")
    for eq in _todos_los_equipos(estado):
        for j in list(eq.jugadores):
            j.contrato_anios = int(getattr(j, 'contrato_anios', 1) or 1) - 1
            if j.contrato_anios > 0:
                continue
            if eq is mi:
                quitar_de_plantilla(mi, j)
                j.transferible = j.pide_salir = False     # v3.1.0
                try:  # v4.4.0: se borra la escalada de salida
                    from alpha_football.salidas import limpiar as _limpiar_salida
                    _limpiar_salida(j)
                except Exception as e_lim:
                    logger.error(f"No se pudo limpiar la salida: {e_lim}")
                j.fin_de_contrato = True     # sigue en la lista de libres aunque cambie la jornada
                estado.setdefault('free_agents_list', []).append(j)
                salidas.append({'jugador': f"{j.nombre} {j.apellido}", 'posicion': j.posicion, 'media': j.overall})
                try:
                    from alpha_football.negociacion import registrar_pase
                    registrar_pase(estado, j, mi.nombre, 'Libre (fin de contrato)', 0, True)
                except Exception as e:
                    logger.error(f"No se pudo registrar la salida libre: {e}")
            else:
                j.contrato_anios = azar.randint(1, 3)
    if mi is not None:
        completar_plantilla(mi)
    estado.setdefault('datos_carrera', {})['salidas_libres'] = salidas
    if mi is not None and mi.balance < 0:
        from alpha_football.directiva import marcar_despido
        marcar_despido(estado, f"Quiebra: cerraste la temporada con saldo negativo (${mi.balance / 1_000_000:.1f}M).")
    return salidas


MINIMO_POR_POSICION = {'POR': 2, 'DEF': 5, 'MED': 5, 'DEL': 3}
PLANTILLA_MINIMA = 18


def generar_reemplazo(posicion: str, estrellas_equipo: float):
    """Juvenil de relleno para completar la plantilla (nivel según las estrellas del club)."""
    from alpha_football.models import Jugador
    from alpha_football.nombres import nombre_unico   # v4.4.0: sin nombres repetidos
    lo = int(40 + float(estrellas_equipo or 3.0) * 5)
    hi = min(lo + 20, 76)
    nombre, apellido = nombre_unico()
    return Jugador(nombre=nombre, apellido=apellido, posicion=posicion,
                   ataque=random.randint(lo, hi), defensa=random.randint(lo, hi), fisico=random.randint(lo, hi),
                   tecnica=random.randint(lo, hi), mental=random.randint(lo, hi))


def completar_plantilla(equipo) -> None:
    """
    v2.9.1: tras ventas o fines de contrato la plantilla del user nunca queda sin portero
    ni corta: completa los mínimos por posición y luego hasta PLANTILLA_MINIMA, siempre con
    contrato nuevo (antes los reemplazos llegaban sin contrato y se iban en el cierre).
    """
    try:
        estrellas = getattr(equipo, 'estrellas', 3.0)
        faltan = []
        for pos, minimo in MINIMO_POR_POSICION.items():
            tiene = sum(1 for j in equipo.jugadores if j.posicion == pos)
            faltan += [pos] * max(0, minimo - tiene)
        while len(equipo.jugadores) + len(faltan) < PLANTILLA_MINIMA:
            faltan.append('MED')
        for pos in faltan:
            nuevo = generar_reemplazo(pos, estrellas)
            nuevo.salario, nuevo.contrato_anios, nuevo.clausula = contrato_inicial(nuevo)
            nuevo.contrato_anios = max(2, nuevo.contrato_anios)
            equipo.jugadores.append(nuevo)
    except Exception as e:
        logger.error(f"No se pudo completar la plantilla: {e}")
