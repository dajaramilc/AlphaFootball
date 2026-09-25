# -*- coding: utf-8 -*-
"""
ALPHA FOOTBALL — Negociaciones (v2.7.0)
Lógica sin UI de la columna NEGOCIACIONES: el buscador de jugadores (pool de las 10 ligas
vivas + agentes libres, filtros y orden), el fichaje del user, el historial de pases
(general y propio) y el ojeador (3 recomendaciones por ventana de mercado).
"""
from __future__ import annotations

import logging
import unicodedata
from typing import Any, Optional

logger = logging.getLogger(__name__)

from alpha_football.paises import PAISES as _PAISES   # noqa: E402
PAIS_CORTO = {p['liga_id']: p['corto'] for p in _PAISES}   # v3.7.0: 8 países
LIBRES = "LIBRES"
MAX_HISTORIAL = 500
N_MEJORES = 40
ORDENES = ['ovr', 'pot', 'edad', 'precio']
_ORDEN_POS = {'POR': 0, 'DEF': 1, 'MED': 2, 'DEL': 3}


def _sin_tildes(txt: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', str(txt or '').lower())
                   if unicodedata.category(c) != 'Mn')


def etiqueta_liga(tipo: str, division: int) -> str:
    return f"{PAIS_CORTO.get(tipo, str(tipo)[:3].upper())} {'2ª' if division == 2 else '1ª'}"


def dinero_exacto(v) -> str:
    """v3.5.0: monto completo, sin redondear ($12,345,000)."""
    return f"${int(v or 0):,}"


def precio_fichaje(jugador) -> int:
    try:
        from alpha_football.market import precio_compra, factor_contrato
        return int(int(precio_compra(jugador)) * factor_contrato(jugador))   # v3.5.0: último año −25%
    except Exception:
        return int(getattr(jugador, 'valor', 0) or 0)


def pool_buscador(estado: dict) -> list:
    """(jugador, club o None, etiqueta de liga) de todos los que el user podría fichar."""
    mi = estado.get('mi_equipo')
    pool = []
    vistos = set()
    for division, clave in ((1, 'primera_division'), (2, 'segunda_division')):
        for tipo, liga in (estado.get(clave) or {}).items():
            if liga is None or id(liga) in vistos:
                continue
            vistos.add(id(liga))
            etiqueta = etiqueta_liga(tipo, getattr(liga, 'division', division) or division)
            for eq in getattr(liga, 'equipos', []) or []:
                if eq is mi or (mi is not None and getattr(eq, 'id', None) == getattr(mi, 'id', None)):
                    continue
                for j in getattr(eq, 'jugadores', []) or []:
                    pool.append((j, eq, etiqueta))
    for j in estado.get('free_agents_list') or []:
        pool.append((j, None, LIBRES))
    return pool


def filtrar(pool: list, filtros: dict) -> list:
    """Aplica los filtros del buscador: nombre, pos, liga, edad_min/max, media_min/max (o el viejo
    ovr_min), pot_min/max, precio_min/max y solo_libres. v3.6.0: un máximo en 0/None = sin tope."""
    f = filtros or {}
    nombre = _sin_tildes(f.get('nombre', '')).strip()
    pos = f.get('pos', 'TODAS')
    liga = f.get('liga', 'TODAS')
    edad_min, edad_max = int(f.get('edad_min', 0) or 0), int(f.get('edad_max', 99) or 99)
    ovr_min = int(f.get('media_min', f.get('ovr_min', 0)) or 0)            # v3.6.0
    ovr_max = int(f.get('media_max', 99) or 99)
    pot_min, pot_max = int(f.get('pot_min', 0) or 0), int(f.get('pot_max', 99) or 99)
    precio_min = int(f.get('precio_min', 0) or 0)
    precio_max = f.get('precio_max')
    precio_max = int(precio_max) if precio_max else None
    solo_libres = bool(f.get('solo_libres', False))
    salida = []
    for j, club, etiqueta in pool:
        if solo_libres and etiqueta != LIBRES:
            continue
        if nombre and nombre not in _sin_tildes(f"{j.nombre} {j.apellido}"):
            continue
        if pos != 'TODAS' and j.posicion != pos:
            continue
        if liga != 'TODAS' and etiqueta != liga:
            continue
        if not (edad_min <= j.edad <= edad_max):
            continue
        if not (ovr_min <= j.overall <= ovr_max):
            continue
        if not (pot_min <= (getattr(j, 'potencial', 0) or j.overall) <= pot_max):
            continue
        if precio_min or precio_max is not None:
            precio = precio_fichaje(j)
            if precio < precio_min or (precio_max is not None and precio > precio_max):
                continue
        salida.append((j, club, etiqueta))
    return salida


def ordenar(resultados: list, orden: str = 'ovr', desc: bool = True) -> list:
    claves = {
        'ovr': lambda r: r[0].overall,
        'pot': lambda r: getattr(r[0], 'potencial', 0) or r[0].overall,
        'edad': lambda r: r[0].edad,
        'precio': lambda r: precio_fichaje(r[0]),
    }
    return sorted(resultados, key=claves.get(orden, claves['ovr']), reverse=desc)


def mejores(pool: list, n: int = N_MEJORES) -> list:
    """Lo que muestra el buscador antes de buscar: los n de mayor media."""
    return ordenar(pool, 'ovr', True)[:n]


def registrar_pase(estado: dict, jugador, de: str, a: str, monto: int, propio: bool) -> None:
    """Agrega un pase al historial persistente (datos_carrera['historial_pases'])."""
    try:
        liga = estado.get('liga')
        hist = estado.setdefault('datos_carrera', {}).setdefault('historial_pases', [])
        hist.append({
            'temporada': int(estado.get('temporada', 1) or 1),
            'jornada': int(getattr(liga, 'jornada_actual', 1) or 1),
            'jugador': f"{jugador.nombre} {jugador.apellido}",
            'posicion': getattr(jugador, 'posicion', ''),
            'media': int(getattr(jugador, 'overall', 0) or 0),
            'de': str(de), 'a': str(a), 'monto': int(monto or 0), 'propio': bool(propio),
        })
        # v2.9.1: el tope solo recorta pases ajenos (la IA hace cientos por temporada y
        # borraba los tuyos de la pestaña PROPIO).
        exceso = sum(1 for h in hist if not h.get('propio')) - MAX_HISTORIAL
        if exceso > 0:
            quitar = set()
            for i, h in enumerate(hist):
                if len(quitar) == exceso:
                    break
                if not h.get('propio'):
                    quitar.add(i)
            hist[:] = [h for i, h in enumerate(hist) if i not in quitar]
    except Exception as e:
        logger.error(f"No se pudo registrar el pase: {e}")


def historial(estado: dict, propio: Optional[bool] = None) -> list:
    """Pases del más reciente al más viejo; propio=True/False filtra, None = todos."""
    hist = list((estado.get('datos_carrera') or {}).get('historial_pases') or [])
    if propio is not None:
        hist = [h for h in hist if bool(h.get('propio')) == propio]
    return list(reversed(hist))


def avisar_llegada(estado: dict, jugador) -> None:
    """v4.4.0: correo de bienvenida al fichar (y reserva su nombre para que no se repita)."""
    try:
        from alpha_football import correo as C
        from alpha_football.nombres import registrar
        registrar(jugador)
        nombre = getattr(jugador, 'nombre_completo', None) or f"{jugador.nombre} {jugador.apellido}"
        C.enviar(estado, 'club', f"{nombre} ha llegado",
                 f"{nombre} ha llegado, acomódalo en tu plantilla.",
                 C.accion('plantilla_screen', "VER PLANTILLA"))
    except Exception as e:
        logger.error(f"No se pudo avisar la llegada del fichaje: {e}")


def fichar(estado: dict, jugador, club, precio: Optional[int] = None) -> tuple[bool, str]:
    """
    Ficha a `jugador` (de `club`, o agente libre si club es None) para el user: valida con
    market.puede_fichar, cobra, mueve al jugador y registra el pase.
    """
    mi = estado.get('mi_equipo')
    if mi is None:
        return False, "No hay equipo."
    precio = precio_fichaje(jugador) if precio is None else int(precio)
    try:
        from alpha_football.market import puede_fichar
        ok, motivo = puede_fichar(mi, jugador, precio)
    except Exception as e:
        logger.error(f"puede_fichar falló: {e}")
        ok, motivo = mi.balance >= precio, "Presupuesto insuficiente."
    if not ok:
        return False, motivo
    try:
        if club is not None:
            if jugador not in club.jugadores:
                return False, "El jugador ya no está en ese club."
            club.jugadores.remove(jugador)
            club.alineacion_activa = None   # v2.9.1: sus índices quedaron corridos
            club.balance = int(getattr(club, 'balance', 0) or 0) + precio
        elif jugador in (estado.get('free_agents_list') or []):
            estado['free_agents_list'].remove(jugador)
        mi.balance -= precio
        jugador.transferible = jugador.pide_salir = False     # v3.1.0
        try:  # v4.4.0: se borra la escalada de salida
            from alpha_football.salidas import limpiar as _limpiar_salida
            _limpiar_salida(jugador)
        except Exception as e_lim:
            logger.error(f"No se pudo limpiar la salida: {e_lim}")
        mi.jugadores.append(jugador)
        estado['fichajes_realizados'] = int(estado.get('fichajes_realizados', 0) or 0) + 1
        de = getattr(club, 'nombre', 'Libre') if club is not None else 'Libre'
        estado.setdefault('transfer_log', []).append(f"Compra: {jugador.nombre_completo} de {de} por ${precio:,}")
        registrar_pase(estado, jugador, de, mi.nombre, precio, True)
        try:
            from alpha_football.finanzas import registrar
            registrar(estado, 'fichajes', precio)
        except Exception as e_fin:
            logger.error(f"No se pudo registrar el gasto del fichaje: {e_fin}")
        avisar_llegada(estado, jugador)     # v4.4.0
        return True, f"¡Fichaje de {jugador.nombre_completo}!"
    except Exception as e:
        logger.error(f"Error al fichar: {e}")
        return False, "No se pudo completar el fichaje."


# --- Ojeador ──────────────────────────────────────────────────────────────────

def _clave_ventana(estado: dict) -> tuple:
    """Ventana de mercado actual o la próxima: (temporada, 'inicio'|'cierre')."""
    liga = estado.get('liga')
    j = int(getattr(liga, 'jornada_actual', 1) or 1)
    temporada = int(estado.get('temporada', 1) or 1)
    return (temporada, 'inicio' if j <= 3 else 'cierre')


def necesidades(mi_equipo) -> dict:
    """Media más baja del mejor 4-3-3 por posición (lo que más urge reforzar)."""
    try:
        from alpha_football.formaciones import mejor_once
        once = [mi_equipo.jugadores[i] for i in mejor_once(mi_equipo.jugadores, "4-3-3")]
    except Exception:
        once = sorted(mi_equipo.jugadores, key=lambda j: -j.overall)[:11]
    peor = {}
    for j in once:
        peor[j.posicion] = min(peor.get(j.posicion, 99), j.overall)
    return peor


def recomendar_fichajes(estado: dict, n: int = 3) -> list:
    """
    n fichajes (jugador, club, etiqueta, precio, motivo) que mejoran el puesto más flojo del
    once y que el user puede pagar (y fichar según market.puede_fichar). Prioriza posiciones
    distintas y la mejora por dólar; los jóvenes con potencial suman.
    """
    mi = estado.get('mi_equipo')
    if mi is None:
        return []
    peor = necesidades(mi)
    try:
        from alpha_football.market import puede_fichar
    except Exception:
        puede_fichar = None
    candidatos = []
    for j, club, etiqueta in pool_buscador(estado):
        base = peor.get(j.posicion)
        if base is None or j.overall < base + 2:
            continue
        precio = precio_fichaje(j)
        if precio > mi.balance:
            continue
        if puede_fichar is not None and not puede_fichar(mi, j, precio)[0]:
            continue
        mejora = j.overall - base
        extra_pot = max(0, (getattr(j, 'potencial', 0) or j.overall) - j.overall) * 0.3 if j.edad <= 23 else 0
        puntaje = (mejora + extra_pot) / (1 + precio / max(1, mi.balance))
        motivo = f"+{mejora} sobre tu {j.posicion} más flojo ({base})"
        if extra_pot:
            motivo += f" · joven con potencial {j.potencial}"
        candidatos.append((puntaje, j, club, etiqueta, precio, motivo))
    candidatos.sort(key=lambda c: -c[0])
    elegidos, posiciones = [], set()
    for c in candidatos:                      # primero, una por posición
        if c[1].posicion not in posiciones:
            elegidos.append(c); posiciones.add(c[1].posicion)
        if len(elegidos) == n:
            break
    for c in candidatos:                      # si faltan, las mejores que queden
        if len(elegidos) == n:
            break
        if c not in elegidos:
            elegidos.append(c)
    return [(j, club, etiqueta, precio, motivo) for _p, j, club, etiqueta, precio, motivo in elegidos]


def recomendaciones_ojeador(estado: dict) -> list:
    """Las del ojeador para la ventana actual/próxima: se calculan una vez por ventana."""
    clave = list(_clave_ventana(estado))
    dc = estado.setdefault('datos_carrera', {})
    guardado = dc.get('ojeador') or {}
    pool = {id(j): (j, club, et) for j, club, et in pool_buscador(estado)}
    if guardado.get('clave') == clave:
        recs = []
        for r in guardado.get('recs', []):
            hallado = next(((j, club, et) for j, club, et in pool.values()
                            if f"{j.nombre} {j.apellido}" == r['jugador'] and j.posicion == r['posicion']), None)
            if hallado:
                j, club, et = hallado
                recs.append((j, club, et, precio_fichaje(j), r['motivo']))
        return recs
    recs = recomendar_fichajes(estado)
    dc['ojeador'] = {'clave': clave, 'recs': [
        {'jugador': f"{j.nombre} {j.apellido}", 'posicion': j.posicion, 'motivo': m}
        for j, _c, _e, _p, m in recs]}
    return recs


# --- v2.9.0: negociación (club + contrato) y renovaciones ─────────────────────

MULT_CLAUSULA = {1.5: 0.95, 2.0: 1.0, 3.0: 1.08}   # cláusula más alta → pide más salario
RECARGO_FIGURA = 1.25                              # por las 3 figuras de un club se pide +25%
EDAD_CONTRATO_CORTO, ANIOS_MAX_VETERANO = 32, 2


def _dinero(v: int) -> str:
    return f"${v / 1_000_000:.1f}M" if v >= 1_000_000 else f"${v / 1000:.0f}K"


def minimo_club(jugador, club) -> int:
    """Lo mínimo que acepta el club: el precio de mercado (+25% si es una de sus 3 figuras)."""
    precio = precio_fichaje(jugador)
    figuras = sorted(getattr(club, 'jugadores', []) or [], key=lambda j: -j.overall)[:3]
    return int(precio * RECARGO_FIGURA) if any(f is jugador for f in figuras) else precio


def evaluar_oferta_club(jugador, club, monto: int) -> tuple[bool, str, int]:
    """(acepta, mensaje, contraoferta). Pagar la cláusula siempre se acepta."""
    from alpha_football.finanzas import asegurar_contrato
    asegurar_contrato(jugador)
    if club is None:
        return True, "Agente libre: no hay club con quien negociar.", 0
    if monto >= int(jugador.clausula or 0) > 0:
        return True, f"Pagas la cláusula: {club.nombre} no puede negarse.", 0
    minimo = minimo_club(jugador, club)
    if monto >= minimo:
        return True, f"{club.nombre} acepta {dinero_exacto(monto)}.", 0          # v3.5.0: monto exacto
    return False, f"{club.nombre} rechaza. Pide {dinero_exacto(minimo)}.", minimo


# --- v3.5.0: "lo analizamos" en compras, rivalidad y acuerdos por correo ─────────

UMBRAL_ANALISIS = 0.85
MORAL_BAJA = 40


def buscar_en_club(estado: dict, club_id, jugador_id) -> tuple:
    """(club, jugador) por id en las ligas vivas; (None, None) o (club, None) si no está."""
    for clave in ('primera_division', 'segunda_division'):
        for liga in (estado.get(clave) or {}).values():
            for eq in getattr(liga, 'equipos', []) or []:
                if str(eq.id) == str(club_id):
                    return eq, next((j for j in eq.jugadores if str(j.id) == str(jugador_id)), None)
    return None, None


def evaluar_compra(estado: dict, jugador, club, monto: int) -> tuple:
    """v3.5.0: ('acepta'|'analiza'|'rechaza', mensaje, contraoferta) para una oferta del user."""
    from alpha_football.finanzas import asegurar_contrato
    asegurar_contrato(jugador)
    monto = int(monto or 0)
    if club is None:
        return 'acepta', "Agente libre: no hay club con quien negociar.", 0
    clausula = int(jugador.clausula or 0)
    if monto >= clausula > 0:
        return 'acepta', f"Pagas la cláusula: {club.nombre} no puede negarse.", 0
    from alpha_football.data.clasicos import es_clasico
    if es_clasico(club, estado.get('mi_equipo')) and int(getattr(jugador, 'moral', 70)) >= MORAL_BAJA:
        return 'rechaza', f"Es tu clásico: solo por la cláusula de {dinero_exacto(clausula)}.", clausula
    minimo = minimo_club(jugador, club)
    if monto >= minimo:
        return 'acepta', f"{club.nombre} acepta {dinero_exacto(monto)}.", 0
    if monto >= int(minimo * UMBRAL_ANALISIS):
        dc = estado.setdefault('datos_carrera', {})
        pend = [a for a in dc.get('analisis_compras', []) if a.get('jugador_id') != jugador.id]
        pend.append({'jugador_id': jugador.id, 'club_id': club.id, 'club': club.nombre,
                     'jugador': jugador.nombre_completo, 'monto': monto,
                     'jornada': int(getattr(estado.get('liga'), 'jornada_actual', 1) or 1),
                     'temporada': int(estado.get('temporada', 1) or 1)})
        dc['analisis_compras'] = pend
        return 'analiza', f"{club.nombre}: \"Lo analizamos\". Te responden por correo en la próxima jornada.", 0
    return 'rechaza', f"{club.nombre} rechaza. Pide {dinero_exacto(minimo)}.", minimo


def reanudar_compra(estado: dict, compra: dict) -> Optional[str]:
    """v3.5.0: desde el correo 'acepta tu oferta', negociación del contrato con el monto pactado."""
    from alpha_football.market import ventana_mercado_abierta
    liga = estado.get('liga')
    club, j = buscar_en_club(estado, compra.get('club_id'), compra.get('jugador_id'))
    motivo = None
    if int(compra.get('temporada', -1)) != int(estado.get('temporada', 1) or 1):
        motivo = "El acuerdo era de otra temporada."
    elif liga is None or not ventana_mercado_abierta(liga.jornada_actual, liga.num_jornadas):
        motivo = "La ventana de fichajes está cerrada."
    elif j is None:
        motivo = "El jugador ya no está en ese club."
    if motivo:
        estado['correo_aviso'] = motivo
        return None
    iniciar_negociacion(estado, j, club, 'fichaje', 'correo_screen')
    estado['neg']['etapa'] = 'jugador'
    estado['neg']['monto'] = int(compra['monto'])
    return 'negociacion_screen'


def salario_pedido(jugador, modo: str, clausula_mult: float) -> int:
    """Salario anual que exige: sube un 20% para cambiar de club y un 10% para renovar."""
    from alpha_football.finanzas import asegurar_contrato, SALARIO_MIN, SALARIO_PCT_VALOR, _valor
    asegurar_contrato(jugador)
    base = max(SALARIO_MIN, int(_valor(jugador) * SALARIO_PCT_VALOR))
    actual = int(jugador.salario or base)
    pedido = max(base, int(actual * (1.2 if modo == 'fichaje' else 1.1)))
    return int(pedido * MULT_CLAUSULA.get(clausula_mult, 1.0))


def evaluar_contrato(jugador, salario: int, anios: int, clausula_mult: float, modo: str) -> tuple[bool, str, int]:
    """(acepta, mensaje, contraoferta de salario)."""
    pedido = salario_pedido(jugador, modo, clausula_mult)
    if not 1 <= int(anios) <= 5:
        return False, "El contrato debe ser de 1 a 5 años.", pedido
    if jugador.edad >= EDAD_CONTRATO_CORTO and anios > ANIOS_MAX_VETERANO:
        return False, f"Con {jugador.edad} años solo firma hasta {ANIOS_MAX_VETERANO} años.", pedido
    if salario >= pedido:
        return True, f"{jugador.nombre_completo} acepta.", 0
    return False, f"No acepta. Pide {dinero_exacto(pedido)} al año.", pedido   # v3.5.0


def analizar_contrato(estado: dict, neg: dict) -> Optional[str]:
    """
    v4.4.0: si el salario ofrecido es al menos el 85% de lo que pide (y los años valen), el
    jugador "lo analiza": queda pendiente en datos_carrera['analisis_contratos'] y responde por
    correo en la próxima jornada (contraofertas.resolver_analisis). None = rechazo normal.
    """
    j, modo, anios = neg['jugador'], neg['modo'], int(neg['anios'])
    pedido = salario_pedido(j, modo, neg['clausula_mult'])
    if not int(pedido * UMBRAL_ANALISIS) <= int(neg['salario']) < pedido:
        return None
    if not 1 <= anios <= 5 or (j.edad >= EDAD_CONTRATO_CORTO and anios > ANIOS_MAX_VETERANO):
        return None
    club = neg.get('club')
    dc = estado.setdefault('datos_carrera', {})
    pend = [a for a in dc.get('analisis_contratos', []) if a.get('jugador_id') != j.id]
    pend.append({'jugador_id': j.id, 'jugador': j.nombre_completo, 'modo': modo,
                 'club_id': getattr(club, 'id', None) if modo == 'fichaje' else None,
                 'monto': int(neg.get('monto', 0) or 0), 'salario': int(neg['salario']), 'anios': anios,
                 'clausula_mult': float(neg['clausula_mult']),
                 'jornada': int(getattr(estado.get('liga'), 'jornada_actual', 1) or 1),
                 'temporada': int(estado.get('temporada', 1) or 1)})
    dc['analisis_contratos'] = pend
    return f"{j.nombre_completo}: \"Lo analizo\". Te responde por correo en la próxima jornada."


def _fijar_contrato(jugador, salario: int, anios: int, clausula_mult: float) -> None:
    from alpha_football.finanzas import _valor
    jugador.salario, jugador.contrato_anios = int(salario), int(anios)
    jugador.clausula = int(_valor(jugador) * clausula_mult)


def completar_fichaje(estado: dict, jugador, club, monto: int, salario: int, anios: int,
                      clausula_mult: float) -> tuple[bool, str]:
    """Traspaso ya acordado con el club y con el jugador."""
    ok, msg = fichar(estado, jugador, club, precio=monto)
    if ok:
        _fijar_contrato(jugador, salario, anios, clausula_mult)
    return ok, msg


def renovar(estado: dict, jugador, salario: int, anios: int, clausula_mult: float) -> None:
    _fijar_contrato(jugador, salario, anios, clausula_mult)
    try:  # v4.4.0: renovar bien pagado sube la moral y corta la queja por sueldo
        from alpha_football.salidas import al_renovar
        al_renovar(estado, jugador, salario)
    except Exception as e_sal:
        logger.error(f"No se pudo aplicar la renovación a la moral: {e_sal}")
    estado.setdefault('transfer_log', []).append(
        f"Renovación: {jugador.nombre_completo} hasta {anios} años por {_dinero(salario)}/año")


def iniciar_negociacion(estado: dict, jugador, club, modo: str, volver: str) -> str:
    """Prepara estado['neg'] para negociacion_screen y devuelve el nombre de la pantalla."""
    from alpha_football.finanzas import asegurar_contrato
    asegurar_contrato(jugador)
    anios = 2 if jugador.edad >= EDAD_CONTRATO_CORTO else 3
    estado['neg'] = {
        'jugador': jugador, 'club': club, 'modo': modo, 'volver': volver,
        'etapa': 'club' if modo == 'fichaje' and club is not None else 'jugador',
        'monto': precio_fichaje(jugador) if club is not None else 0,
        'salario': int(salario_pedido(jugador, modo, 2.0) * 0.9), 'anios': anios,
        'clausula_mult': 2.0, 'msg': None,
    }
    return 'negociacion_screen'
