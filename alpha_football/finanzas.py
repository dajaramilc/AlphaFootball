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

SALARIO_PCT_VALOR = 0.08        # v4.6.0: salario anual = 8% del valor (antes 5%: nadie quebraba)
FACTOR_MIGRACION_SALARIOS = 0.08 / 0.05
# v4.6.0: ingresos por (liga, división) para que la masa salarial media de cada liga sea ~70% de sus
# ingresos (medido con las plantillas de la base: las bandas de presupuesto de BetPlay, Uruguay,
# Ecuador y las 2ª no cuadraban con el valor de sus jugadores). Sin entrada = 1.0.
FACTOR_INGRESOS = {
    ('betplay', 1): 2.7, ('uruguay', 1): 1.6, ('ecuador', 1): 1.3,
    ('premier', 2): 1.5, ('laliga', 2): 3.4, ('seriea', 2): 2.7, ('brasil', 2): 1.2,
    ('argentina', 2): 2.4, ('betplay', 2): 4.4, ('uruguay', 2): 2.6, ('ecuador', 2): 2.5,
}
SALARIO_MIN = 20_000
CLAUSULA_MULT_INICIAL = 2.0
PATROCINIO_FRAC = 0.55          # v4.9.0 (antes 0.40): valor de referencia de los patrocinios de la temporada
TAQUILLA_FRAC = 0.35            # v4.9.0 (antes 0.50): la suma sigue en 0.90 (ingresos_esperados no cambia)
FACTOR_TAQUILLA = {'victoria': 1.2, 'empate': 1.0, 'derrota': 0.85}
JORNADAS_ROJO_VENTA = 4         # v4.6.0: antes 3
PUNTOS_QUIEBRA = 6              # v4.6.0: cerrar la temporada en rojo resta puntos en la siguiente
VENTA_FORZADA_FRAC = 0.8        # la directiva malvende al 80% del valor
EDAD_LIBRE_IA = 28              # v0.4.21.0: al vencer su contrato, el suplente de la IA de esta edad o más...
PROB_LIBRE_IA = 0.30            # ...queda libre con esta probabilidad (más o menos uno por club y temporada)
PLANTILLA_MIN_LIBRE_IA = 20     # el club no suelta a nadie si se queda con menos (mercado_ia.PLANTILLA_MIN_VENDEDOR)
CLAVES_LIBRO = ['taquilla', 'patrocinio', 'salarios', 'fichajes', 'ventas', 'premios', 'directiva',
                'camisetas']  # v3.2.0: + espaldarazo; v0.4.26.0: + venta de camisetas


def _valor(j, sano: bool = False) -> int:
    """Valor de mercado del jugador. v0.4.27.0: `sano=True` ignora la lesión (base de sueldos y cláusulas)."""
    try:
        from alpha_football.market import calcular_valor
        return int(calcular_valor(j, con_lesion=not sano))
    except Exception:
        return int(getattr(j, 'valor', 0) or 0)


def salario_mercado(j) -> int:
    """v3.1.0: lo que 'merece' cobrar según su valor (base de contratos y de la moral).
    v0.4.27.0: con su valor sano: estar lesionado no abarata el sueldo."""
    return max(SALARIO_MIN, int(_valor(j, sano=True) * SALARIO_PCT_VALOR))


def contrato_inicial(j, rng: Optional[random.Random] = None) -> tuple[int, int, int]:
    """(salario anual, años, cláusula) de un contrato nuevo según valor y edad."""
    azar = rng or random.Random(f"{j.nombre}|{j.apellido}|{j.edad}|{j.posicion}")
    v = _valor(j, sano=True)
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


TECHO_PRESUPUESTO = 350_000_000       # v0.4.25.0: el presupuesto con que arranca una temporada no pasa de 350 M$
# v0.4.27.0: durante la temporada un club SÍ puede juntar más de 350 M$; el techo solo recorta el presupuesto
# nuevo al empezar la temporada (presupuesto_temporada / presupuesto_nuevo_ia). El reloj y la carga ya no recortan.


def limitar_presupuestos(estado: dict) -> int:
    """Recorta a TECHO_PRESUPUESTO el saldo de todo club de la partida y devuelve cuántos recortó. Es idempotente.
    v0.4.27.0: ya no la llama el reloj ni la carga del guardado (el recorte es solo al empezar temporada nueva y
    ya va dentro de presupuesto_temporada / presupuesto_nuevo_ia); queda como utilidad de migración."""
    recortados = 0
    clubes = _todos_los_equipos(estado) + list(getattr(estado.get('liga'), 'equipos', None) or [])
    for eq in clubes:
        try:
            if int(getattr(eq, 'balance', 0) or 0) > TECHO_PRESUPUESTO:
                eq.balance = TECHO_PRESUPUESTO
                recortados += 1
        except Exception as e:
            logger.error(f"No se pudo limitar el presupuesto de {getattr(eq, 'nombre', '?')}: {e}")
    if recortados:
        logger.info(f"Presupuestos: {recortados} club(es) recortados al techo de {TECHO_PRESUPUESTO:,}.")
    return recortados


def asegurar_contratos(estado: dict) -> None:
    for eq in _todos_los_equipos(estado):
        for j in eq.jugadores:
            asegurar_contrato(j)
    for j in estado.get('free_agents_list') or []:
        asegurar_contrato(j)


def valor_club(equipo, estado: Optional[dict] = None) -> int:
    """v4.7.0: valor del club = valor de mercado de la plantilla + saldo.
    v0.4.26.0: con `estado`, el club del user suma además su venta de camisetas (valor_camisetas)."""
    valor = (sum(int(getattr(j, 'valor', 0) or 0) for j in getattr(equipo, 'jugadores', []) or [])
             + int(getattr(equipo, 'balance', 0) or 0))
    if estado is not None and equipo is estado.get('mi_equipo'):
        valor += valor_camisetas(estado)
    return valor


# --- v0.4.26.0: venta de camisetas, un activo del club ────────────────────────────
# Ingreso por jornada = base de ingresos del club (su tamaño) × CAMISETAS_FRAC × popularidad / 50. La popularidad
# (0-100, datos_carrera['camisetas']) se dispara cuando el club rinde por encima de lo que se esperaba de él
# (la meta de la directiva) y baja despacio. El valor del club suma MULT_VALOR_CAMISETAS años de ese ingreso.
CAMISETAS_FRAC = 0.10                  # del ingreso base, a popularidad 50
POPULARIDAD_INICIAL = 50.0
POPULARIDAD_MIN, POPULARIDAD_MAX = 10.0, 100.0
MULT_VALOR_CAMISETAS = 5               # el club vale 5 años de camisetas más
SUBE_POR_PUESTO, SUBE_MAX = 0.8, 6.0   # por jornada: por cada puesto sobre la meta (tope por jornada)
BAJA_BASE, BAJA_POR_PUESTO, BAJA_MAX = 0.1, 0.1, 1.0   # por jornada bajo la meta: baja despacio
POP_VICTORIA, POP_DERROTA = 0.8, -0.3
JORNADAS_PESO_TABLA = 4                # hasta la 4ª jornada la tabla pesa de a poco (todavía no dice nada)
POP_CAMPEON_LIGA, POP_CAMPEON_COPA = 8.0, 6.0
POP_SUPERADO, POP_FALLADO = 4.0, -4.0  # al cierre de la temporada, según la meta


def popularidad(estado: dict) -> float:
    """Popularidad de las camisetas del club del user (0-100). Sin dato (partida vieja, club nuevo): la inicial."""
    try:
        c = (estado.get('datos_carrera') or {}).get('camisetas')
        return float(c.get('popularidad', POPULARIDAD_INICIAL)) if isinstance(c, dict) else POPULARIDAD_INICIAL
    except Exception as e:
        logger.error(f"No se pudo leer la popularidad de las camisetas: {e}")
        return POPULARIDAD_INICIAL


def ingreso_anual_camisetas(estado: dict) -> int:
    """Lo que dejarían las camisetas en una temporada entera con la popularidad de hoy."""
    mi, liga = estado.get('mi_equipo'), estado.get('liga')
    if mi is None or liga is None:
        return 0
    base = base_ingresos(mi, getattr(liga, 'tipo', ''), getattr(liga, 'division', 1) or 1)
    return int(base * CAMISETAS_FRAC * popularidad(estado) / 50.0)


def valor_camisetas(estado: dict) -> int:
    """Lo que las camisetas suman al valor del club."""
    return MULT_VALOR_CAMISETAS * ingreso_anual_camisetas(estado)


# v0.4.27.0: la meta de Marca de la directiva puede ser de camisetas: cobrar esta temporada un 10% más de lo que
# dejaría la popularidad de hoy (con tope: la popularidad media exigida nunca pasa del 95% del máximo).
FACTOR_META_CAMISETAS = 1.10
POP_META_TOPE = POPULARIDAD_MAX * 0.95


def meta_camisetas(estado: dict) -> int:
    """Lo que debe cobrar el club por camisetas en la temporada para cumplir la meta de Marca (0 = sin base)."""
    pop = popularidad(estado)
    if pop <= 0:
        return 0
    exigida = min(pop * FACTOR_META_CAMISETAS, POP_META_TOPE)
    return int(ingreso_anual_camisetas(estado) * exigida / pop)


def cobrado_camisetas(estado: dict, temporada: Optional[int] = None) -> int:
    """Camisetas cobradas en `temporada` (la actual por defecto), leídas del libro sin reiniciarlo."""
    try:
        t = int(temporada if temporada is not None else estado.get('temporada', 1) or 1)
        return int(libro_de(estado, t).get('camisetas', 0) or 0)
    except Exception as e:
        logger.error(f"No se pudo leer lo cobrado en camisetas: {e}")
        return 0


def _cambiar_popularidad(estado: dict, delta: float) -> float:
    c = estado.setdefault('datos_carrera', {}).setdefault('camisetas', {})
    previa = float(c.get('popularidad', POPULARIDAD_INICIAL))
    c['popularidad'] = round(max(POPULARIDAD_MIN, min(POPULARIDAD_MAX, previa + float(delta))), 2)
    c['ultimo_delta'] = round(c['popularidad'] - previa, 2)
    return c['popularidad']


def _puesto_esperado(estado: dict, liga, mi) -> int:
    """El puesto que se espera del club: la meta de la directiva de esta temporada; sin ella, el que le toca por la
    media de su plantilla (lo mismo que nivel_temporada espera de un club de la IA)."""
    obj = (estado.get('datos_carrera') or {}).get('objetivo') or {}
    if obj.get('temporada') == int(estado.get('temporada', 1) or 1) and obj.get('pos_max'):
        return int(obj['pos_max'])
    ranking = sorted(liga.equipos, key=lambda e: -float(getattr(e, 'ovr_promedio', 0) or 0))
    return next((i + 1 for i, e in enumerate(ranking) if e is mi), len(ranking))


def actualizar_popularidad(estado: dict, gf: int, gc: int) -> float:
    """Tras cada partido de liga del user: sube fuerte si va por encima de su meta (por puesto de ventaja y por
    victoria) y baja despacio si va por debajo. Devuelve el cambio aplicado."""
    mi, liga = estado.get('mi_equipo'), estado.get('liga')
    if mi is None or liga is None:
        return 0.0
    jugados = max(0, int(getattr(liga, 'jornada_actual', 1) or 1) - 1)     # la tabla aún no cuenta este partido
    peso = min(1.0, jugados / JORNADAS_PESO_TABLA)
    orden = sorted(liga.equipos, key=lambda e: (getattr(e, 'puntos', 0), getattr(e, 'gf', 0) - getattr(e, 'gc', 0),
                                                getattr(e, 'gf', 0)), reverse=True)
    puesto = next((i + 1 for i, e in enumerate(orden) if e is mi or e.id == mi.id), len(orden))
    margen = _puesto_esperado(estado, liga, mi) - puesto            # > 0: por encima de lo esperado
    if margen > 0:
        delta = min(SUBE_MAX, SUBE_POR_PUESTO * margen) * peso
    elif margen < 0:
        delta = -min(BAJA_MAX, BAJA_BASE + BAJA_POR_PUESTO * -margen) * peso
    else:
        delta = 0.0
    delta += POP_VICTORIA if gf > gc else POP_DERROTA if gf < gc else 0.0
    antes = popularidad(estado)
    return round(_cambiar_popularidad(estado, delta) - antes, 2)


def info_camisetas(estado: dict) -> dict:
    """Para la pantalla de finanzas: popularidad, tendencia, ingreso anual con la de hoy, lo que sumó al valor del
    club y lo cobrado esta temporada."""
    c = (estado.get('datos_carrera') or {}).get('camisetas')
    return {'popularidad': popularidad(estado),
            'tendencia': float(c.get('ultimo_delta', 0.0)) if isinstance(c, dict) else 0.0,
            'ingreso_anual': ingreso_anual_camisetas(estado), 'valor': valor_camisetas(estado),
            'cobrado': int(libro(estado).get('camisetas', 0))}


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


def presupuesto_base(equipo, tipo: str, division: int) -> int:
    """v4.6.0: presupuesto de referencia del club (punto medio de su banda según estrellas, sin azar)."""
    try:
        from alpha_football.mercado_ia import _rango
        lo, hi = _rango(tipo or 'betplay', int(division or 1))
    except Exception:
        lo, hi = 1_000_000, 5_000_000
    t = max(0.0, min(1.0, (float(getattr(equipo, 'estrellas', 3.0) or 3.0) - 2.0) / 3.0))
    return int(lo + t * (hi - lo))


def base_ingresos(equipo, tipo: str, division: int) -> int:
    """v4.6.0: base de patrocinio y taquilla del club (su presupuesto de referencia × factor de su liga)."""
    return int(presupuesto_base(equipo, tipo, division) * FACTOR_INGRESOS.get((tipo, int(division or 1)), 1.0))


def ingresos_esperados(equipo, tipo: str, division: int) -> int:
    """v4.6.0: patrocinio + taquilla de una temporada (todos empates): base del tope salarial y de la IA."""
    base = base_ingresos(equipo, tipo, division)
    return int(base * PATROCINIO_FRAC) + int(base * TAQUILLA_FRAC)


def migrar_economia(estado: dict) -> bool:
    """v4.6.0: saves viejos: los sueldos pasan del 5% al 8% del valor (una sola vez)."""
    dc = estado.setdefault('datos_carrera', {})
    if dc.get('economia_v2'):
        return False
    for eq in _todos_los_equipos(estado):
        for j in getattr(eq, 'jugadores', []) or []:
            if int(getattr(j, 'salario', 0) or 0) > 0:
                j.salario = int(round(j.salario * FACTOR_MIGRACION_SALARIOS / 1000)) * 1000
    for p in dc.get('traspasos_pendientes') or []:     # v4.7.0: fichajes acordados (agentes libres guardados)
        d = p.get('datos') if isinstance(p, dict) else None
        if isinstance(d, dict) and int(d.get('salario', 0) or 0) > 0:
            d['salario'] = int(round(d['salario'] * FACTOR_MIGRACION_SALARIOS / 1000)) * 1000
    dc['economia_v2'] = True
    return True


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


def libro_de(estado: dict, temporada: int) -> dict:
    """v0.4.27.0: el libro de `temporada` (la actual o la anterior) SIN reiniciar nada; {} si no lo hay."""
    dc = estado.get('datos_carrera') or {}
    for lib in (dc.get('finanzas'), dc.get('finanzas_anterior')):
        if isinstance(lib, dict) and lib.get('temporada') == int(temporada):
            return lib
    return {}


# --- v0.4.27.0: historial de transacciones del club del user (FINANZAS › HISTORIAL DE TRANSACCIONES) ----------
HISTORIAL_MAX = 600                       # movimientos guardados en datos_carrera['transacciones'] (salen los más viejos)
GASTOS_LIBRO = ('salarios', 'fichajes')   # en estas claves del libro un monto positivo es un gasto (resta)
CONCEPTO_LIBRO = {'taquilla': "Taquilla", 'patrocinio': "Patrocinio", 'salarios': "Salarios", 'fichajes': "Fichaje",
                  'ventas': "Venta de jugador", 'premios': "Premio", 'directiva': "Directiva",
                  'camisetas': "Venta de camisetas"}


def anotar_movimiento(estado: dict, concepto: str, importe: int, clave: str = '') -> None:
    """Una línea del historial de transacciones (fecha real del reloj del juego). `importe` va con signo: + entra,
    − sale. Importe 0 no se anota. Un fallo aquí nunca debe impedir el movimiento de dinero."""
    try:
        importe = int(importe or 0)
        if importe == 0:
            return
        dc = estado.setdefault('datos_carrera', {})
        lista = dc.get('transacciones')
        if not isinstance(lista, list):
            lista = dc['transacciones'] = []
        try:    # el reloj del juego (la misma fecha con que se sellan los correos); sin reloj, sin fecha
            from alpha_football.correo import _hoy_iso
            fecha = _hoy_iso(estado)
        except Exception as e_fecha:
            logger.error(f"No se pudo leer la fecha del movimiento: {e_fecha}")
            fecha = None
        lista.append({'fecha': fecha, 'temporada': int(estado.get('temporada', 1) or 1),
                      'jornada': int(getattr(estado.get('liga'), 'jornada_actual', 1) or 1),
                      'concepto': str(concepto or CONCEPTO_LIBRO.get(clave, "Movimiento"))[:90],
                      'importe': importe, 'clave': clave})
        if len(lista) > HISTORIAL_MAX:
            del lista[:len(lista) - HISTORIAL_MAX]
    except Exception as e:
        logger.error(f"No se pudo anotar el movimiento '{concepto}' en el historial: {e}")


def transacciones(estado: dict) -> list:
    """El historial del club del user, el más reciente primero (lista vacía en partidas viejas)."""
    lista = (estado.get('datos_carrera') or {}).get('transacciones')
    return [t for t in reversed(lista) if isinstance(t, dict)] if isinstance(lista, list) else []


def registrar(estado: dict, clave: str, monto: int, temporada: Optional[int] = None,
              concepto: Optional[str] = None) -> None:
    """Suma al libro de la temporada actual (o al de `temporada` si es la anterior).
    v0.4.27.0: además anota el movimiento en el historial de transacciones (`concepto` lo describe; sin él, el
    nombre de la clave). `monto` positivo en una clave de gasto (salarios, fichajes) sale del saldo."""
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
    es_gasto = clave in GASTOS_LIBRO
    importe = -int(monto) if es_gasto else int(monto)
    if not concepto:
        base = CONCEPTO_LIBRO.get(clave, str(clave).capitalize())
        concepto = base if (importe < 0) == es_gasto else f"{base} (ajuste)"
    anotar_movimiento(estado, concepto, importe, clave)


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
                      if i not in alin.titulares and getattr(o, 'lesion_dias', 0) == 0
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
                 f"por ${monto / 1_000_000:.1f}M (se va {TP.texto_apertura(estado)})")
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
    medio = base_ingresos(mi, getattr(liga, 'tipo', ''), getattr(liga, 'division', 1) or 1)   # v4.6.0: según el club y su liga
    resultado = 'victoria' if gf > gc else 'derrota' if gf < gc else 'empate'
    try:   # v4.9.0: cobran los contratos de patrocinio (sin contratos, no hay patrocinio)
        from alpha_football import patrocinios as _P
        patrocinio = _P.cobro_jornada(estado)
    except Exception as e_pat:   # un fallo no deja al club sin cobrar: patrocinio de fórmula
        logger.error(f"Error cobrando los patrocinios: {e_pat}")
        patrocinio = int(medio * PATROCINIO_FRAC / n)
    taquilla = int(medio * TAQUILLA_FRAC / max(1, n / 2) * FACTOR_TAQUILLA[resultado]) if es_local else 0
    salarios = masa_salarial(mi, estado) // n
    camisetas = 0
    try:   # v0.4.26.0: se cobra con la popularidad de antes del partido; después el resultado la mueve
        camisetas = ingreso_anual_camisetas(estado) // n
        actualizar_popularidad(estado, gf, gc)
    except Exception as e_cam:
        logger.error(f"Error en la venta de camisetas: {e_cam}")
    mi.balance = int(mi.balance) + patrocinio + taquilla + camisetas - salarios
    jornada = int(getattr(liga, 'jornada_actual', 1) or 1)       # v0.4.27.0: conceptos del historial
    registrar(estado, 'patrocinio', patrocinio, concepto=f"Patrocinio · jornada {jornada}")
    registrar(estado, 'taquilla', taquilla, concepto=f"Taquilla · jornada {jornada} (local, {resultado})")
    registrar(estado, 'camisetas', camisetas, concepto=f"Venta de camisetas · jornada {jornada}")
    registrar(estado, 'salarios', salarios, concepto=f"Salarios · jornada {jornada}")
    dc = estado.setdefault('datos_carrera', {})
    estado.pop('aviso_finanzas', None)
    from alpha_football import correo as C
    ir = C.accion('finanzas_screen', "VER FINANZAS")
    if mi.balance < 0:
        dc['jornadas_en_rojo'] = n_rojo = int(dc.get('jornadas_en_rojo', 0)) + 1
        if n_rojo >= JORNADAS_ROJO_VENTA:
            dc['jornadas_en_rojo'] = 0
            texto = vender_mejor(estado) or "Quiebra: no se pudo vender a nadie."
            estado['aviso_finanzas'] = texto
            C.enviar(estado, 'directiva', "Venta forzada por deudas",
                     f"Tras {JORNADAS_ROJO_VENTA} jornadas consecutivas con saldo negativo, la directiva se ha "
                     f"visto obligada a vender. {texto}", ir)
        else:
            faltan = JORNADAS_ROJO_VENTA - n_rojo
            estado['aviso_finanzas'] = aviso = (f"Saldo negativo: en {faltan} jornada{'s' if faltan != 1 else ''} "
                                                f"la directiva venderá a tu mejor jugador")
            C.enviar(estado, 'directiva',
                     "Saldo negativo" if n_rojo == 1 else f"Siguen los números rojos ({n_rojo}/{JORNADAS_ROJO_VENTA})",
                     f"El saldo del club es de −${abs(mi.balance) / 1_000_000:.1f}M. {aviso}. Le rogamos que "
                     "venda jugadores o reduzca la masa salarial para volver a números positivos.", ir)
    else:
        if int(dc.get('jornadas_en_rojo', 0) or 0) > 0:
            C.enviar(estado, 'directiva', "Saldo recuperado",
                     "El club ha vuelto a números positivos, por lo que se cancela la venta forzada.", ir)
        dc['jornadas_en_rojo'] = 0
    return {'patrocinio': patrocinio, 'taquilla': taquilla, 'salarios': salarios, 'camisetas': camisetas}


# v0.4.11.0: presupuesto por temporada. El saldo no se arrastra: al cerrar, el club se queda con
# el sobrante y fija un presupuesto nuevo según su tamaño (base), su salud y el objetivo deportivo.
SALUD_ROJO = 0.80
SALUD_TRAMOS = ((0.25, 0.90), (0.75, 1.00), (1.50, 1.10))    # (saldo/base menor que, factor)
SALUD_MAX = 1.20
# v0.4.14.1: pesan más los resultados que el tamaño del club: base × (parte fija + resultados) × salud
PARTE_FIJA = 0.40                 # lo que el club da por ser quien es
PARTE_OBJETIVO = {'superado': 0.80, 'cumplido': 0.55, 'fallado': 0.15}
PARTE_NEUTRA = 0.60               # sin dato del objetivo (club nuevo, save viejo): la base tal cual
BONO_LIGA, BONO_COPA = 0.20, 0.25
PISO_PRESUPUESTO = 0.10


def factor_salud(saldo: int, base: int) -> float:
    """Cómo cerró el club respecto de su presupuesto base: en rojo 0.80 … más de 150% 1.20."""
    if int(saldo) < 0:
        return SALUD_ROJO
    r = int(saldo) / max(1, int(base))
    return next((f for tope, f in SALUD_TRAMOS if r < tope), SALUD_MAX)


def presupuesto_temporada(base: int, saldo: int, resultado: str, campeon_liga: bool = False,
                          campeon_copa: bool = False) -> dict:
    """Desglose del presupuesto nuevo. v0.4.14.1: base × (0.40 + objetivo + títulos) × salud, de ×0.44
    (objetivo fallado y en rojo) a ×1.98 (superado, liga, copa y las arcas llenas); la deuda se descuenta
    entera (piso: 10% de la base). Nunca pasa de TECHO_PRESUPUESTO."""
    base, saldo = int(base), int(saldo)
    salud = factor_salud(saldo, base)
    objetivo = PARTE_OBJETIVO.get(resultado, PARTE_NEUTRA)
    bonos = (BONO_LIGA if campeon_liga else 0.0) + (BONO_COPA if campeon_copa else 0.0)
    mult = (PARTE_FIJA + objetivo + bonos) * salud
    deuda = max(0, -saldo)
    total = min(TECHO_PRESUPUESTO, max(int(base * PISO_PRESUPUESTO), int(round(base * mult)) - deuda))
    return {'base': base, 'saldo': saldo, 'salud': salud, 'objetivo': objetivo, 'bonos': bonos,
            'mult': mult, 'deuda': deuda, 'total': total}


def presupuesto_nuevo_ia(equipo, tipo: str, division: int, resultado: str = '', campeon_liga: bool = False,
                         cobertura: int = 0) -> int:
    """Presupuesto de la temporada que empieza para un club de la IA: la misma fórmula que el user (su base según
    liga y estrellas, el saldo con que cerró, el objetivo cumplido y el título de liga). Sin dato del objetivo
    ('' = club sin foto, save viejo) usa la parte neutra.
    `cobertura` es lo que le falta para pagar sus sueldos en una temporada mala (mercado_ia.cuentas): la directiva
    no lo deja por debajo. Sin ese piso, el reajuste le quita a la IA el colchón que le daba acumular saldo y los
    recién descendidos (planilla de 1ª con ingresos de 2ª) quiebran año tras año. Siempre bajo TECHO_PRESUPUESTO."""
    base = presupuesto_base(equipo, tipo, division)
    total = presupuesto_temporada(base, int(getattr(equipo, 'balance', 0) or 0), resultado, campeon_liga)['total']
    return min(TECHO_PRESUPUESTO, max(total, int(cobertura or 0)))


def aplicar_presupuesto_temporada(estado: dict) -> Optional[dict]:
    """Cierre de temporada (ya con la liga y la división nuevas): reemplaza el saldo por el
    presupuesto de la temporada que empieza y lo comunica por correo."""
    mi, liga = estado.get('mi_equipo'), estado.get('liga')
    if mi is None or liga is None:
        return None
    temporada = int(estado.get('temporada', 1) or 1)
    dc = estado.setdefault('datos_carrera', {})
    reg = (estado.get('historial') or [{}])[-1] or {}
    propio = reg.get('equipo') == mi.nombre and int(reg.get('temporada', 0) or 0) == temporada - 1
    copas = (dc.get('campeones_copas') or [{}])[-1] or {}
    campeon_copa = int(copas.get('temporada', 0) or 0) == temporada - 1 and \
        mi.nombre in [v for k, v in copas.items() if k != 'temporada']
    base = presupuesto_base(mi, getattr(liga, 'tipo', 'betplay'), getattr(liga, 'division', 1) or 1)
    info = presupuesto_temporada(base, int(getattr(mi, 'balance', 0) or 0),
                                 reg.get('objetivo_resultado', '') if propio else '',
                                 propio and reg.get('campeon_liga') == mi.nombre, campeon_copa)
    saldo_previo = int(getattr(mi, 'balance', 0) or 0)
    mi.balance = info['total']
    anotar_movimiento(estado, f"Presupuesto de la temporada {temporada} (el saldo no se arrastra)",
                      info['total'] - saldo_previo, 'presupuesto')      # v0.4.27.0: el reinicio también es un movimiento
    try:   # v0.4.26.0: la temporada que cierra deja huella en la popularidad de las camisetas
        resultado = reg.get('objetivo_resultado', '') if propio else ''
        sube = POP_SUPERADO if resultado == 'superado' else POP_FALLADO if resultado == 'fallado' else 0.0
        sube += POP_CAMPEON_LIGA if propio and reg.get('campeon_liga') == mi.nombre else 0.0
        sube += POP_CAMPEON_COPA if campeon_copa else 0.0
        if sube:
            _cambiar_popularidad(estado, sube)
    except Exception as e_pop:
        logger.error(f"No se pudo mover la popularidad al cierre de la temporada: {e_pop}")
    dc['presupuesto_temporada'] = dict(info, temporada=temporada)
    try:
        from alpha_football import correo as C
        # v0.4.14.1: sin la cuenta a la vista: solo el monto y por qué
        C.enviar(estado, 'directiva', f"Presupuesto de la temporada {temporada}",
                 f"Este es su presupuesto para la nueva temporada, debido a sus resultados: "
                 f"${info['total'] / 1_000_000:.1f}M.",
                 C.accion('finanzas_screen', "VER FINANZAS"))
    except Exception as e:
        logger.error(f"No se pudo avisar el presupuesto de la temporada: {e}")
    return info


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
    acordados = set()       # v0.4.11.0: ya traspasados, esperan la J1: su contrato no corre ni vencen
    try:
        from alpha_football import traspasos_pendientes as _TP
        acordados = {(p.get('jugador'), str(p.get('jugador_id'))) for p in _TP._pendientes(estado)}
    except Exception as e_tp:
        logger.error(f"No se pudieron leer los traspasos acordados: {e_tp}")
    from alpha_football.negociacion import liberar, retirar_libres, registrar_pase
    cerrada = int(estado.get('temporada', 1) or 1) - 1      # la temporada ya subió: se cierra la anterior
    try:    # v0.4.21.0: el agente libre que pasó la temporada entera sin club se retira
        retirar_libres(estado, cerrada)
    except Exception as e_ret:
        logger.error(f"No se pudieron retirar los agentes libres viejos: {e_ret}")
    for eq in _todos_los_equipos(estado):
        once = None     # v0.4.21.0: perezoso (solo hace falta si a alguien se le acaba el contrato)
        for j in list(eq.jugadores):
            if acordados and (getattr(j, 'nombre_completo', ''), str(getattr(j, 'id', ''))) in acordados:
                continue
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
                liberar(estado, j, cerrada)  # sigue en la lista de libres aunque cambie la jornada
                salidas.append({'jugador': f"{j.nombre} {j.apellido}", 'posicion': j.posicion, 'media': j.overall})
                try:
                    registrar_pase(estado, j, mi.nombre, 'Libre (fin de contrato)', 0, True)
                except Exception as e:
                    logger.error(f"No se pudo registrar la salida libre: {e}")
                continue
            if once is None:
                from alpha_football.formaciones import mejor_once
                once = {id(eq.jugadores[i]) for i in mejor_once(eq.jugadores, "4-3-3") if 0 <= i < len(eq.jugadores)}
            if (id(j) not in once and int(getattr(j, 'edad', 25) or 25) >= EDAD_LIBRE_IA
                    and not getattr(j, 'prestamo', None) and len(eq.jugadores) > PLANTILLA_MIN_LIBRE_IA
                    and azar.random() < PROB_LIBRE_IA):
                # v0.4.21.0: la IA no renueva a todos: el suplente veterano queda libre (bolsa de agentes libres)
                eq.jugadores.remove(j)
                eq.alineacion_activa = None
                liberar(estado, j, cerrada)
                registrar_pase(estado, j, eq.nombre, 'Libre (fin de contrato)', 0, False)
            else:
                j.contrato_anios = azar.randint(1, 3)
    if mi is not None:
        completar_plantilla(mi)
    estado.setdefault('datos_carrera', {})['salidas_libres'] = salidas
    if mi is not None:     # v4.6.0: 1ª temporada en rojo = −6 puntos; 2ª seguida = despido
        dc = estado.setdefault('datos_carrera', {})
        if mi.balance < 0:
            dc['temporadas_en_rojo'] = int(dc.get('temporadas_en_rojo', 0) or 0) + 1
            if dc['temporadas_en_rojo'] >= 2:
                from alpha_football.directiva import marcar_despido
                marcar_despido(estado, f"Quiebra: dos temporadas seguidas en números rojos "
                                       f"(${mi.balance / 1_000_000:.1f}M).")
            else:
                # el cierre corre después del reset de la tabla: los puntos ya son de la temporada nueva
                mi.puntos = int(getattr(mi, 'puntos', 0) or 0) - PUNTOS_QUIEBRA
                mi.sancion_puntos = int(getattr(mi, 'sancion_puntos', 0) or 0) + PUNTOS_QUIEBRA
                from alpha_football import correo as C
                if not estado.get('despido_pendiente'):     # v4.7.0: al despedido no se le advierte
                    C.enviar(estado, 'directiva', "Temporada cerrada en rojo",
                             f"El club ha cerrado la temporada con −${abs(mi.balance) / 1_000_000:.1f}M. La liga le "
                             f"resta {PUNTOS_QUIEBRA} puntos para esta temporada. Si vuelve a cerrar en números "
                             "rojos, prescindiremos de sus servicios.",
                             C.accion('finanzas_screen', "VER FINANZAS"))
        else:
            dc['temporadas_en_rojo'] = 0
    try:    # v0.4.11.0: el saldo no se arrastra; va después del control de números rojos
        aplicar_presupuesto_temporada(estado)
    except Exception as e_pres:
        logger.error(f"Error fijando el presupuesto de la temporada: {e_pres}")
    try:    # v0.4.17.0: multa de la liga (tope salarial + mala salud) sobre el presupuesto nuevo
        from alpha_football import sancion_liga as _SL
        _SL.cobrar_multa(estado)
    except Exception as e_san:
        logger.error(f"Error cobrando la multa de la liga: {e_san}")
    if mi is not None:     # v4.9.0: vencen patrocinios y llegan las ofertas de la ventana de inicio
        try:
            from alpha_football import patrocinios as _P
            _P.cierre_contratos(estado)
        except Exception as e_pat:
            logger.error(f"Error en el cierre de los patrocinios: {e_pat}")
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
