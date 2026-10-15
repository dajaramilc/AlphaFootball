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
        from alpha_football.market import precio_compra, factor_contrato, calcular_valor, cifra_cerrada
        if getattr(jugador, 'remate', False):   # v4.6.0: club en quiebra: 60% del valor
            from alpha_football.mercado_ia import PRECIO_REMATE
            return cifra_cerrada((int(getattr(jugador, 'valor', 0) or 0) or calcular_valor(jugador)) * PRECIO_REMATE)   # v0.4.18.0
        return int(int(precio_compra(jugador)) * factor_contrato(jugador))   # v3.5.0: último año −25%
    except Exception:
        return int(getattr(jugador, 'valor', 0) or 0)


MIN_LIBRES = 10        # v0.4.21.0: con menos libres que esto, se completa con veteranos de relleno
LIBRES_PASE = "Libre"  # origen en el historial de pases de un agente libre que firma con un club


def liberar(estado: dict, jugador, desde: Optional[int] = None) -> None:
    """v0.4.21.0: el jugador entra a la bolsa real de agentes libres (se guarda con la partida).
    `desde`: temporada desde la que está sin club (por defecto, la actual)."""
    jugador.fin_de_contrato = True       # libre de verdad: no se regenera al cambiar de jornada
    jugador.libre_desde = int(desde if desde is not None else estado.get('temporada', 1) or 1)
    jugador.transferible = jugador.pide_salir = False
    jugador.remate = jugador.salida_forzada = False
    estado.setdefault('free_agents_list', []).append(jugador)


def libres_reales(estado: dict) -> list:
    """Los agentes libres de verdad (los que soltó un club), sin el relleno ni los del editor."""
    return [j for j in estado.get('free_agents_list') or [] if getattr(j, 'fin_de_contrato', False)]


INDEMNIZACION_LIBERACION = 0.5


def indemnizacion_liberacion(jugador) -> int:
    """Costo de rescindir: la mitad de los sueldos que quedan por contrato."""
    from alpha_football.finanzas import asegurar_contrato
    asegurar_contrato(jugador)
    anios = max(1, int(getattr(jugador, 'contrato_anios', 1) or 1))
    return int(int(jugador.salario) * anios * INDEMNIZACION_LIBERACION)


def motivo_no_liberable(estado: dict, jugador) -> Optional[str]:
    """v0.4.27.0: por qué no se puede liberar a `jugador` (None si se puede). La pantalla lo consulta antes de abrir
    la confirmación; `liberar_jugador` lo vuelve a comprobar."""
    mi = estado.get('mi_equipo')
    if mi is None or jugador not in getattr(mi, 'jugadores', []):
        return "El jugador no está en tu plantilla."
    if getattr(jugador, 'prestamo', None):
        return f"{jugador.nombre_completo} está a préstamo: no se puede liberar."
    from alpha_football.traspasos_pendientes import pendiente_de
    if pendiente_de(estado, jugador) is not None:
        return f"{jugador.nombre_completo} ya tiene un acuerdo: no se puede liberar."
    return None


def liberar_jugador(estado: dict, jugador) -> tuple[bool, str]:
    """Rescinde el contrato, paga la indemnización y deja al jugador como agente libre."""
    mi = estado.get('mi_equipo')
    motivo = motivo_no_liberable(estado, jugador)
    if motivo:
        return False, motivo

    indemnizacion = indemnizacion_liberacion(jugador)
    from alpha_football import finanzas, prestamos
    if prestamos.en_lista(estado, jugador):
        prestamos.alternar_lista(estado, jugador)
    estado['ofertas_recibidas'] = [oferta for oferta in estado.get('ofertas_recibidas') or []
                                   if oferta.get('jugador') is not jugador]
    finanzas.quitar_de_plantilla(mi, jugador)
    from alpha_football.salidas import limpiar
    limpiar(jugador)
    liberar(estado, jugador)
    mi.balance = int(mi.balance) - indemnizacion
    finanzas.registrar(estado, 'salarios', indemnizacion,       # v0.4.27.0: concepto del historial de transacciones
                       concepto=f"Indemnización por liberar a {jugador.nombre_completo}")
    registrar_pase(estado, jugador, mi.nombre, 'Libre (rescisión)', 0, True)
    estado.setdefault('transfer_log', []).append(
        f"Rescisión: {jugador.nombre_completo} liberado (indemnización ${indemnizacion:,})")
    return True, f"{jugador.nombre_completo} fue liberado por {dinero_exacto(indemnizacion)}."


def guardar_libres(estado: dict) -> None:
    """v0.4.21.0: copia la bolsa real a datos_carrera['libres'] para que viaje con el guardado. Si la
    partida todavía no armó la lista (recién cargada), no toca lo que ya estaba guardado."""
    if 'free_agents_list' not in estado:
        return
    temporada = int(estado.get('temporada', 1) or 1)
    estado.setdefault('datos_carrera', {})['libres'] = [
        dict(j.to_dict(), libre_desde=int(getattr(j, 'libre_desde', temporada) or temporada))
        for j in libres_reales(estado)]


def cargar_libres(estado: dict) -> None:
    """v0.4.21.0: al cargar la partida, rearma la bolsa real desde datos_carrera['libres']."""
    from alpha_football.models import Jugador
    temporada = int(estado.get('temporada', 1) or 1)
    lista = []
    for d in (estado.get('datos_carrera') or {}).get('libres') or []:
        try:
            j = Jugador.from_dict(d)
            j.fin_de_contrato = True
            j.libre_desde = int(d.get('libre_desde', temporada) or temporada)
            lista.append(j)
        except Exception as e:
            logger.error(f"Agente libre guardado inválido {d.get('nombre', '?') if isinstance(d, dict) else '?'}: {e}")
    estado['free_agents_list'] = lista
    estado['free_agents_clave'] = None        # la lista de la jornada (editor y relleno) se arma al abrirla


def retirar_libres(estado: dict, temporada_cerrada: int) -> list:
    """v0.4.21.0: al cierre de la temporada, el que lleva una temporada entera sin club se retira."""
    idos = [j for j in libres_reales(estado)
            if int(getattr(j, 'libre_desde', temporada_cerrada) or temporada_cerrada) < int(temporada_cerrada)]
    if idos:
        estado['free_agents_list'] = [j for j in estado['free_agents_list'] if j not in idos]
    return idos


def asegurar_agentes_libres(estado: dict) -> list:
    """
    Agentes libres de la jornada (antes los generaba la pantalla vieja del mercado). La lista dura
    toda la jornada; al cambiar de jornada se conservan los libres de verdad (los que soltó un club, v0.4.21.0)
    y los que están analizando tu propuesta de contrato. El relleno de parodias solo aparece si hay menos de
    MIN_LIBRES y es el mismo toda la temporada.
    """
    liga = estado.get('liga')
    clave = [int(estado.get('temporada', 1) or 1), int(getattr(liga, 'jornada_actual', 1) or 1)]
    if estado.get('free_agents_list') and estado.get('free_agents_clave') == clave:
        return estado['free_agents_list']
    en_analisis = {(str(a.get('jugador_id')), a.get('jugador'))
                   for a in (estado.get('datos_carrera') or {}).get('analisis_contratos', [])
                   if a.get('club_id') is None}
    conservar = [j for j in estado.get('free_agents_list') or []
                 if getattr(j, 'fin_de_contrato', False) or (str(j.id), j.nombre_completo) in en_analisis]
    try:
        from alpha_football.data.free_agents import relleno_libres, libres_editor
        ya = {(str(j.id), j.nombre_completo) for j in conservar}      # v4.6.0: + los libres del editor
        del_editor = [j for j in libres_editor(estado) if (str(j.id), j.nombre_completo) not in ya]
        base = conservar + del_editor
        estado['free_agents_list'] = base + relleno_libres(clave[0], MIN_LIBRES - len(base),
                                                           {j.nombre_completo for j in base})
    except Exception as e:
        logger.error(f"No se pudieron generar los agentes libres: {e}")
        estado['free_agents_list'] = conservar
    estado['free_agents_clave'] = clave
    return estado['free_agents_list']


ETIQUETA_INTL = {'champions': "INT EUR", 'libertadores': "INT SUD"}


def clubes_internacionales(estado: dict) -> list:
    """
    (club, etiqueta) de los clubes de relleno de Champions/Libertadores: los que no juegan en
    ninguna de las 16 ligas. Son los mismos objetos que usa el motor de copas (se fichan de ahí).
    """
    out = []
    try:
        from alpha_football import competiciones as CP
        from alpha_football.data.internacional import RELLENO_CHAMPIONS, RELLENO_LIBERTADORES
        for tipo, nombres in (('champions', RELLENO_CHAMPIONS), ('libertadores', RELLENO_LIBERTADORES)):
            pool = CP._pool(estado, tipo)
            out += [(pool[n], ETIQUETA_INTL[tipo]) for n in nombres if n in pool]
    except Exception as e:
        logger.error(f"No se pudieron cargar los clubes internacionales del buscador: {e}")
    return out


def es_club_internacional(club) -> bool:
    try:
        from alpha_football.data.internacional import RELLENO_CHAMPIONS, RELLENO_LIBERTADORES
        return getattr(club, 'nombre', None) in set(RELLENO_CHAMPIONS) | set(RELLENO_LIBERTADORES)
    except Exception:
        return False


def pool_buscador(estado: dict) -> list:
    """(jugador, club o None, etiqueta de liga) de todos los que el user podría fichar."""
    mi = estado.get('mi_equipo')
    if mi is not None:
        asegurar_agentes_libres(estado)
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
    for eq, etiqueta in clubes_internacionales(estado):
        for j in getattr(eq, 'jugadores', []) or []:
            pool.append((j, eq, etiqueta))
    for j in estado.get('free_agents_list') or []:
        pool.append((j, None, LIBRES))
    return pool


# --- Favoritos: jugadores que el user sigue para ficharlos después ───────────────
# Se guardan por nombre completo (los nombres son únicos en la carrera desde v4.4.0) en
# datos_carrera['favoritos'], así sobreviven a guardar/cargar y a que el jugador cambie de club.

def _favs(estado: dict) -> list:
    return estado.setdefault('datos_carrera', {}).setdefault('favoritos', [])


def es_favorito(estado: dict, jugador) -> bool:
    return getattr(jugador, 'nombre_completo', None) in _favs(estado)


def alternar_favorito(estado: dict, jugador) -> bool:
    """Agrega o quita al jugador de favoritos. Devuelve si quedó como favorito."""
    favs, nombre = _favs(estado), jugador.nombre_completo
    if nombre in favs:
        favs.remove(nombre)
        return False
    favs.append(nombre)
    return True


def quitar_favorito(estado: dict, jugador) -> None:
    nombre = getattr(jugador, 'nombre_completo', None)
    if nombre in _favs(estado):
        _favs(estado).remove(nombre)


def favoritos(estado: dict) -> list:
    """(jugador, club, etiqueta) de los favoritos en el orden en que se agregaron. Los que ya son
    del user o no aparecen en ningún lado (retirados) salen de la lista."""
    favs = _favs(estado)
    if not favs:
        return []
    mi = estado.get('mi_equipo')
    propios = {j.nombre_completo for j in getattr(mi, 'jugadores', []) or []}
    por_nombre = {}
    for j, club, et in pool_buscador(estado):
        por_nombre.setdefault(j.nombre_completo, (j, club, et))
    vigentes = [n for n in favs if n in por_nombre and n not in propios]
    favs[:] = vigentes
    return [por_nombre[n] for n in vigentes]


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


MAX_FICHAJES_IA_JORNADA = 4     # noticias de fichajes entre clubes de la IA por jornada: quedan las de más puntaje
BONO_TU_LIGA = 3                # puntaje = media + esto si participa un club de tu liga (tus rivales pesan más)
MAX_LIBERACIONES_IA_JORNADA = 2     # v0.4.27.0: noticias de liberaciones de la IA por jornada (las de más puntaje)
PASES_LIBERACION = ('Libre', 'Libre (rescisión)')   # destino de un jugador que su club suelta (no: fin de contrato)


def _hora_del_ultimo_dia(estado: dict) -> Optional[int]:
    """Las horas que quedan del último día de fichajes (None fuera de él). Solo lee: no crea el reloj ni el bloque
    del calendario (`dia_final.activo` los asegura, y una partida sin reloj cambiaría de comportamiento)."""
    try:
        cal = (estado.get('datos_carrera') or {}).get('calendario')
        bloque = cal.get('dia_final') if isinstance(cal, dict) else None
        if not isinstance(bloque, dict) or bloque.get('fecha') != cal.get('dia'):
            return None
        horas = int(bloque.get('horas', 0) or 0)
        return horas if horas > 0 else None
    except Exception as e:
        logger.debug(f"negociacion: sin hora del último día: {e}")
        return None


# v0.4.27.0: fichajes atípicos. Son variantes del titular y del cuerpo de la MISMA noticia del fichaje (etiqueta propia,
# +1 de importancia y +2 de puntaje para el tope de la jornada; no la hacen salir si no pasaba ya el filtro de media).
GANGA_PCT_MAX = 60               # "Ganga de mercado": se pagó el 60 % o menos del valor del jugador (el remate es el 60 %)
GENEROSO_PCT_MIN = 150           # "Pago generoso": se pagó el 150 % o más de su valor
MONTO_MINIMO_ATIPICO = 5_000_000   # ganga: su valor llega a esto; pago generoso: lo pagado llega a esto (sin calderilla)
BONO_IMPORTANCIA_ATIPICO = 1
BONO_PUNTAJE_ATIPICO = 2         # (la etiqueta de cada variante vive en noticias.ETIQUETA_VARIANTE)


def _millones(monto) -> str:
    """'$222M' (un decimal solo si hace falta: '$7.5M'); por debajo del millón, en miles ('$850K')."""
    v = int(monto or 0)
    if v >= 1_000_000:
        m = f"{v / 1_000_000:.1f}".rstrip('0').rstrip('.')
        return f"${m}M"
    return f"${v // 1000}K"


def _valor_de_referencia(jugador) -> int:
    """El valor del jugador en este momento, el mismo que muestra su ficha: el guardado si está sano y, si está
    lesionado, el calculado hoy (con el descuento por lesión de market.calcular_valor). Así el precio normal de un
    lesionado (que el mercado ya rebaja por su lesión) no pasa por "ganga": solo cuenta pagar mucho menos que lo que
    vale hoy, lesionado o no."""
    v = int(getattr(jugador, 'valor', 0) or 0)
    if v <= 0 or int(getattr(jugador, 'lesion_dias', 0) or 0) > 0:
        try:
            from alpha_football.market import calcular_valor
            v = int(calcular_valor(jugador))
        except Exception as e:
            logger.error(f"No se pudo calcular el valor para la noticia del fichaje: {e}")
            v = 0
    return v


def _variante_fichaje(jugador, de: str, a: str, monto: int, clubes: dict) -> tuple:
    """('traicion' | 'ganga' | 'generoso' | '', % del valor pagado). Prioridad: traición > ganga / pago generoso.
    Traición: el jugador pasa entre clubes rivales (data/clasicos.es_clasico). Los préstamos y los pases libres no
    llegan aquí (monto 0 → ni ganga ni pago generoso)."""
    try:
        monto = int(monto or 0)
        valor = _valor_de_referencia(jugador)
        pct = int(round(monto / valor * 100)) if valor > 0 and monto > 0 else 0
        from alpha_football.data.clasicos import es_clasico
        if str(de) in clubes and str(a) in clubes and es_clasico(clubes[str(de)], clubes[str(a)]):
            return 'traicion', pct
        if monto > 0 and valor >= MONTO_MINIMO_ATIPICO and pct <= GANGA_PCT_MAX:
            return 'ganga', pct
        if monto >= MONTO_MINIMO_ATIPICO and pct >= GENEROSO_PCT_MIN:
            return 'generoso', pct
    except Exception as e:
        logger.error(f"No se pudo ver si el fichaje es atípico: {e}")
    return '', 0


def _textos_variante(variante: str, pct: int, pre: str, nombre: str, de: str, a: str, monto: int, jugador,
                     media: int, formas: list, cuerpo: str) -> tuple:
    """(formas del titular, cuerpo) de la noticia del fichaje en su variante; ante un error, los de siempre."""
    try:
        m = _millones(monto)
        pos = getattr(jugador, 'posicion', '')
        base = f"{a} cerró el fichaje de {nombre} ({pos}, media {media}) desde {de} por {dinero_exacto(monto)}"
        if variante == 'traicion':
            return ([f"{pre}Traición: {nombre} deja a {de} por su rival {a}", f"{pre}{nombre} traiciona a {de} y ficha por {a}",
                     f"{pre}Traición: {nombre} ficha por {a}", f"{pre}Traición de {nombre}"],
                    f"{base}. {a} es el gran rival de {de}: la hinchada lo vive como una traición.")
        if variante == 'ganga':
            return ([f"{pre}Ganga de mercado: {a} ficha a {nombre} por {m}", f"{pre}Ganga: {nombre} ficha por {a} ({m})",
                     f"{pre}Ganga de mercado: {nombre} a {a}", f"{pre}Ganga de {nombre}"],
                    f"{base}, apenas el {pct} % de lo que vale hoy en el mercado. Una ganga.")
        if variante == 'generoso':
            return ([f"{pre}Pago generoso: {a} paga {m} por {nombre}", f"{pre}Pago generoso: {nombre} por {m} a {a}",
                     f"{pre}Pago generoso: {a} paga {m}", f"{pre}Pago generoso por {nombre}"],
                    f"{base}, el {pct} % de lo que vale hoy: mucho más de lo que marca el mercado.")
    except Exception as e:
        logger.error(f"No se pudo armar la noticia del fichaje atípico: {e}")
    return formas, cuerpo


def _noticia_record_traspaso(estado: dict, jugador, de: str, a: str, monto: int, propio: bool) -> bool:
    """v0.4.27.0: el récord de traspaso arranca en el de Neymar ($222M, datos_carrera['records']['traspaso']). Un pase
    que lo supera (estrictamente) se lleva el récord, queda guardado (el siguiente tiene que superar a este) y sale
    como noticia aparte de tipo 'record', importancia 5: siempre, y no cuenta para el tope de fichajes de la jornada.
    Devuelve True si fue récord (entonces `_noticia_fichaje` no publica el fichaje además)."""
    try:
        monto = int(monto or 0)
        if monto <= 0:
            return False
        from alpha_football import noticias, noticias_gen
        from alpha_football.mercado_ia import ligas_de_la_partida
        rec = noticias_gen.record_traspaso(estado)
        anterior, anterior_nombre = int(rec.get('valor', 0) or 0), str(rec.get('nombre') or '')
        if monto <= anterior:
            return False
        nombre = f"{jugador.nombre} {jugador.apellido}"
        media, pos = int(getattr(jugador, 'overall', 0) or 0), getattr(jugador, 'posicion', '')
        rec.update({'valor': monto, 'nombre': nombre, 'temporada': int(estado.get('temporada', 1) or 1),
                    'de': str(de), 'a': str(a)})
        previo = f"el récord de {anterior_nombre}, {_millones(anterior)}" if anterior_nombre else f"el récord anterior, {_millones(anterior)}"
        clubes = {c.nombre: c for liga, _t, _d in ligas_de_la_partida(estado) for c in liga.equipos}
        noticias.publicar(
            estado, 'record',
            noticias.titular(f"Récord de traspaso: {nombre} ficha por {a} ({_millones(monto)})",
                             f"Récord de traspaso: {a} paga {_millones(monto)} por {nombre}",
                             f"Récord de traspaso: {_millones(monto)}"),
            f"{a} paga {dinero_exacto(monto)} a {de} por {nombre} ({pos}, media {media}) y establece un nuevo récord de "
            f"traspaso: supera {previo}.",
            importancia=5, equipos=[clubes[n] for n in (str(a), str(de)) if n in clubes], jugadores=[jugador],
            media=media, propio=bool(propio), traspaso_record=True)
        return True
    except Exception as e:
        logger.error(f"No se pudo registrar el récord de traspaso: {e}")
        return False


def _noticia_fichaje(estado: dict, jugador, de: str, a: str, monto: int, propio: bool, confirmado: bool) -> None:
    """v0.4.23.0: un traspaso relevante es noticia.
    Tuyo (compra o venta): siempre; media >= 85 → importancia 5, >= 80 → 4, resto → 3.
    Entre clubes de la IA: desde media 80 (76 si participa un club de tu liga); >= 90 → 5, >= 85 → 4, resto → 3;
    y como la IA mueve cientos de jugadores, solo quedan los MAX_FICHAJES_IA_JORNADA de más puntaje de cada jornada.
    `confirmado` (lo había adelantado un rumor): se publica siempre y no cuenta para ese tope.
    v0.4.27.0: un pase que supera el récord de traspaso es la noticia aparte de `_noticia_record_traspaso` (y este
    fichaje no se repite); si no, puede salir como TRAICIÓN (entre clubes rivales), GANGA (≤ 60 % del valor) o PAGO
    GENEROSO (≥ 150 %): el mismo fichaje con otro titular, +1 de importancia y sujeto al mismo tope."""
    from alpha_football import noticias
    from alpha_football.mercado_ia import ligas_de_la_partida
    from alpha_football.salidas import _clave_jornada
    media = int(getattr(jugador, 'overall', 0) or 0)
    if _noticia_record_traspaso(estado, jugador, de, a, monto, propio):
        return                               # v0.4.27.0: el récord de traspaso es su propia noticia; el fichaje no se repite
    tuyas = {c.nombre for c in getattr(estado.get('liga'), 'equipos', None) or []}
    de_tu_liga = str(a) in tuyas or str(de) in tuyas
    puntaje = media + (BONO_TU_LIGA if de_tu_liga else 0)
    if propio:
        importancia = 5 if media >= 85 else 4 if media >= 80 else 3
    else:
        if not confirmado and media < (76 if de_tu_liga else 80):
            return
        importancia = 5 if media >= 90 else 4 if media >= 85 else 3
    clubes = {c.nombre: c for liga, _t, _d in ligas_de_la_partida(estado) for c in liga.equipos}
    variante, pct = _variante_fichaje(jugador, de, a, monto, clubes)     # v0.4.27.0: traición / ganga / pago generoso
    if variante:
        importancia = min(5, importancia + BONO_IMPORTANCIA_ATIPICO)
        puntaje += BONO_PUNTAJE_ATIPICO      # gana puestos en el tope de la jornada, pero el tope se respeta
    hora = _hora_del_ultimo_dia(estado)      # v0.4.25.0: el último día cada hora tiene su propio cupo de noticias
    if not propio and not confirmado:
        ahora = tuple(_clave_jornada(estado))
        hoy = [n for n in noticias.lista(estado) if n['tipo'] == 'fichaje' and not n.get('propio')
               and not n.get('confirmado') and (n['temporada'], n['jornada']) == ahora and n.get('hora') == hora]
        if len(hoy) >= MAX_FICHAJES_IA_JORNADA:
            flojo = min(hoy, key=lambda n: (n.get('puntaje', 0), n['id']))
            if puntaje <= flojo.get('puntaje', 0):
                return
            noticias.retirar(estado, flojo['id'])
    nombre = f"{jugador.nombre} {jugador.apellido}"
    libre = str(de).startswith('Libre')
    pre = "Confirmado: " if confirmado else ""
    formas = [f"{pre}{nombre} ficha por {a}", f"{pre}{a} ficha a {nombre}", f"{pre}{nombre} cambia de club"]
    if not libre:
        formas.insert(0, f"{pre}{nombre} deja {de} y ficha por {a}")
    cuerpo = (f"{a} cerró el fichaje de {nombre} ({getattr(jugador, 'posicion', '')}, media {media}), "
              + ("que llega libre." if libre else f"que llega desde {de} por {dinero_exacto(monto)}."))
    if variante:                              # el mismo fichaje, con otro titular y una frase más
        formas, cuerpo = _textos_variante(variante, pct, pre, nombre, de, a, monto, jugador, media, formas, cuerpo)
    noticias.publicar(estado, 'fichaje', noticias.titular(*formas), cuerpo,
                      importancia=importancia, equipos=[clubes[n] for n in (str(a), str(de)) if n in clubes],
                      jugadores=[jugador], media=media, propio=bool(propio), confirmado=bool(confirmado),
                      puntaje=puntaje, **({'variante': variante} if variante else {}),
                      **({'hora': hora} if hora is not None else {}))


def _noticia_liberacion(estado: dict, jugador, de: str, propio: bool) -> None:
    """v0.4.27.0: que un club suelte a un jugador es noticia. Tuyo (rescisión): siempre; media >= 85 → importancia 5,
    >= 80 → 4, resto → 3. De la IA (suelta sobrantes): desde media 80 (76 si es un club de tu liga); >= 90 → 5,
    >= 85 → 4, resto → 3; y como suelta a muchos, solo quedan los MAX_LIBERACIONES_IA_JORNADA de más puntaje de cada
    jornada (o de cada hora del último día). Es una noticia de tipo 'otro' con la imagen de fichajes y la marca
    `liberacion` (su etiqueta es LIBERADO); no cuenta para el tope de fichajes."""
    from alpha_football import noticias
    from alpha_football.mercado_ia import ligas_de_la_partida
    from alpha_football.salidas import _clave_jornada
    media = int(getattr(jugador, 'overall', 0) or 0)
    tuyas = {c.nombre for c in getattr(estado.get('liga'), 'equipos', None) or []}
    de_tu_liga = str(de) in tuyas
    puntaje = media + (BONO_TU_LIGA if de_tu_liga else 0)
    if propio:
        importancia = 5 if media >= 85 else 4 if media >= 80 else 3
    else:
        if media < (76 if de_tu_liga else 80):
            return
        importancia = 5 if media >= 90 else 4 if media >= 85 else 3
    hora = _hora_del_ultimo_dia(estado)
    if not propio:
        ahora = tuple(_clave_jornada(estado))
        hoy = [n for n in noticias.lista(estado) if n.get('liberacion') and not n.get('propio')
               and (n['temporada'], n['jornada']) == ahora and n.get('hora') == hora]
        if len(hoy) >= MAX_LIBERACIONES_IA_JORNADA:
            flojo = min(hoy, key=lambda n: (n.get('puntaje', 0), n['id']))
            if puntaje <= flojo.get('puntaje', 0):
                return
            noticias.retirar(estado, flojo['id'])
    nombre = f"{jugador.nombre} {jugador.apellido}"
    posicion = getattr(jugador, 'posicion', '')
    formas = [f"{de} libera a {nombre}", f"{de} deja libre a {nombre}", f"{nombre} sale de {de}"]
    cuerpo = (f"{de} rescindió el contrato de {nombre} ({posicion}, media {media}). El jugador queda como agente "
              "libre y cualquier club puede ficharlo sin pagar traspaso.")
    clubes = {c.nombre: c for liga, _t, _d in ligas_de_la_partida(estado) for c in liga.equipos}
    noticias.publicar(estado, 'otro', noticias.titular(*formas), cuerpo, importancia=importancia, categoria='fichaje',
                      equipos=[clubes[str(de)]] if str(de) in clubes else [], jugadores=[jugador],
                      liberacion=True, media=media, propio=bool(propio), puntaje=puntaje,
                      **({'hora': hora} if hora is not None else {}))


MAX_ULTIMO_PASE = 1500          # v0.4.26.0: notas de "cuándo cambió de club" que se guardan antes de podar las viejas


def _anotar_ultimo_pase(estado: dict, jugador) -> None:
    """v0.4.26.0: anota la fecha en que el jugador cambió de club por última vez (datos_carrera['ultimo_pase'],
    por nombre completo, que es único en la carrera). El historial de pases no sirve: la IA hace cientos y se
    recorta. market.cambio_reciente la lee para bajar la probabilidad de que vuelva a moverse en 12 meses."""
    try:
        from datetime import date
        from alpha_football.correo import _hoy_iso
        from alpha_football.market import DIAS_CAMBIO_RECIENTE
        hoy, nombre = _hoy_iso(estado), getattr(jugador, 'nombre_completo', None)
        if not hoy or not nombre:
            return
        notas = estado.setdefault('datos_carrera', {}).setdefault('ultimo_pase', {})
        notas[nombre] = hoy
        if len(notas) > MAX_ULTIMO_PASE:      # fuera lo que ya pasó del año: no cuenta para nada
            limite = date.fromisoformat(hoy).toordinal() - DIAS_CAMBIO_RECIENTE
            for viejo in [n for n, f in notas.items() if date.fromisoformat(str(f)).toordinal() < limite]:
                del notas[viejo]
    except Exception as e:
        logger.error(f"No se pudo anotar la fecha del último pase: {e}")


def registrar_pase(estado: dict, jugador, de: str, a: str, monto: int, propio: bool,
                   confirmado: bool = False) -> None:
    """Agrega un pase al historial persistente (datos_carrera['historial_pases']) y, si es relevante y no
    es una liberación, publica la noticia del fichaje (`confirmado`: el titular empieza por "Confirmado:").
    v0.4.27.0: cuando un club suelta a un jugador (rescisión o sobrante de la IA) publica la noticia de la liberación;
    el fin de contrato no (son cientos al cerrar la temporada)."""
    if not str(a).startswith('Libre'):
        try:
            _noticia_fichaje(estado, jugador, de, a, monto, propio, confirmado)
        except Exception as e:
            logger.error(f"No se pudo publicar la noticia del fichaje: {e}")
    elif str(a) in PASES_LIBERACION:
        try:
            _noticia_liberacion(estado, jugador, de, propio)
        except Exception as e:
            logger.error(f"No se pudo publicar la noticia de la liberación: {e}")
    try:
        liga = estado.get('liga')
        hist = estado.setdefault('datos_carrera', {}).setdefault('historial_pases', [])
        jugador.remate = False               # v4.6.0: cambió de club: se terminó el remate
        from alpha_football.correo import _hoy_iso
        hist.append({
            'temporada': int(estado.get('temporada', 1) or 1),
            'jornada': int(getattr(liga, 'jornada_actual', 1) or 1),
            'fecha': _hoy_iso(estado),       # v0.4.18.0: fecha real ('AAAA-MM-DD'); los registros viejos no la tienen
            'jugador': f"{jugador.nombre} {jugador.apellido}",
            'posicion': getattr(jugador, 'posicion', ''),
            'media': int(getattr(jugador, 'overall', 0) or 0),
            'de': str(de), 'a': str(a), 'monto': int(monto or 0), 'propio': bool(propio),
        })
        if not str(a).startswith('Libre'):   # cambió de club: no se mueve otra vez en esta ventana
            from alpha_football.market import clave_ventana_traspaso
            jugador.ventana_traspaso = clave_ventana_traspaso(
                int(estado.get('temporada', 1) or 1), int(getattr(liga, 'jornada_actual', 1) or 1),
                int(getattr(liga, 'num_jornadas', 22) or 22), estado=estado)
            _anotar_ultimo_pase(estado, jugador)
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
                 f"{nombre} ya se ha incorporado al club. Puede acomodarlo en su formación.",
                 C.accion('team_screen', "VER FORMACIÓN"))
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
    from alpha_football import sancion_liga as SL       # v0.4.17.0: sancionado por la liga no ficha (ni libres)
    bloqueo = SL.motivo_bloqueo(estado)
    if bloqueo:
        return False, bloqueo
    if getattr(jugador, 'prestamo', None):   # préstamos: no se compra a uno que está a préstamo
        return False, f"{jugador.nombre_completo} está a préstamo: no se puede fichar."
    from alpha_football.market import traspasado_en_ventana
    if club is not None and traspasado_en_ventana(estado, jugador):
        return False, f"{jugador.nombre_completo} ya fue traspasado en esta ventana: solo a préstamo."
    precio = precio_fichaje(jugador) if precio is None else int(precio)
    try:
        from alpha_football.market import puede_fichar
        ok, motivo = puede_fichar(mi, jugador, precio)
    except Exception as e:
        logger.error(f"puede_fichar falló: {e}")
        ok, motivo = mi.balance >= precio, "Presupuesto insuficiente."
    if not ok:
        return False, motivo
    from alpha_football import traspasos_pendientes as TP
    if TP.pendiente_de(estado, jugador) is not None:
        return False, f"Ya está acordado: llega {TP.texto_apertura(estado)}."
    from alpha_football import dia_final as DF      # v0.4.14.0: el último día, un fichaje cuesta 3 horas
    if not TP.puede_concretar(estado, DF.HORAS_FICHAJE, jugador):
        return _fichar_diferido(estado, jugador, club, precio)
    try:
        if club is not None:
            if jugador not in club.jugadores:
                return False, "El jugador ya no está en ese club."
            club.jugadores.remove(jugador)
            club.alineacion_activa = None   # v2.9.1: sus índices quedaron corridos
            if es_club_internacional(club):
                # el pool internacional se rehace desde los datos al cargar o cambiar de temporada:
                # se anota para que el fichado no vuelva a aparecer en su club viejo
                estado.setdefault('datos_carrera', {}).setdefault('fichados_intl', []).append(
                    [club.nombre, jugador.nombre_completo])
            club.balance = int(getattr(club, 'balance', 0) or 0) + precio
            try:    # v0.4.20.0: si le pagaste la cláusula estando en el mínimo, sube juveniles
                from alpha_football.mercado_ia import asegurar_minimo_ia
                asegurar_minimo_ia(estado)
            except Exception as e_min:
                logger.error(f"No se pudo completar la plantilla de {club.nombre}: {e_min}")
        elif jugador in (estado.get('free_agents_list') or []):
            estado['free_agents_list'].remove(jugador)
            from alpha_football.data.free_agents import quitar_libre_editor   # v4.6.0
            quitar_libre_editor(estado, jugador)
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
            registrar(estado, 'fichajes', precio,       # v0.4.27.0: concepto del historial de transacciones
                      concepto=f"Fichaje de {jugador.nombre_completo} (de {de})")
        except Exception as e_fin:
            logger.error(f"No se pudo registrar el gasto del fichaje: {e_fin}")
        avisar_llegada(estado, jugador)     # v4.4.0
        quitar_favorito(estado, jugador)
        return True, f"¡Fichaje de {jugador.nombre_completo}!"
    except Exception as e:
        logger.error(f"Error al fichar: {e}")
        return False, "No se pudo completar el fichaje."


def _fichar_diferido(estado: dict, jugador, club, precio: int) -> tuple[bool, str]:
    """Mercado cerrado: se paga ya y el jugador llega cuando se abra la ventana."""
    from alpha_football import traspasos_pendientes as TP
    from alpha_football import correo as C
    mi = estado['mi_equipo']
    try:
        if club is not None:
            if jugador not in club.jugadores:
                return False, "El jugador ya no está en ese club."
            club.balance = int(getattr(club, 'balance', 0) or 0) + precio
        elif jugador in (estado.get('free_agents_list') or []):
            estado['free_agents_list'].remove(jugador)   # ya no se lo puede llevar otro
            from alpha_football.data.free_agents import quitar_libre_editor   # v4.6.0
            quitar_libre_editor(estado, jugador)
        mi.balance -= precio
        aviso = TP.diferir_compra(estado, jugador, club, precio)
        estado['fichajes_realizados'] = int(estado.get('fichajes_realizados', 0) or 0) + 1
        de = getattr(club, 'nombre', 'Libre') if club is not None else 'Libre'
        estado.setdefault('transfer_log', []).append(
            f"Compra acordada: {jugador.nombre_completo} de {de} por ${precio:,} (llega en la ventana)")
        try:
            from alpha_football.finanzas import registrar
            registrar(estado, 'fichajes', precio,       # v0.4.27.0: concepto del historial de transacciones
                      concepto=f"Fichaje acordado de {jugador.nombre_completo} (de {de})")
        except Exception as e_fin:
            logger.error(f"No se pudo registrar el gasto del fichaje: {e_fin}")
        C.enviar(estado, 'club', f"Fichaje acordado: {jugador.nombre_completo}",
                 f"Se han pagado {dinero_exacto(precio)} a {de}. {aviso}")
        quitar_favorito(estado, jugador)
        return True, f"¡Acuerdo cerrado! {jugador.nombre_completo} llega {TP.texto_apertura(estado)}."
    except Exception as e:
        logger.error(f"Error al fichar con el mercado cerrado: {e}")
        return False, "No se pudo completar el fichaje."


# --- Ojeador ──────────────────────────────────────────────────────────────────

def _clave_ventana(estado: dict) -> tuple:
    """Ventana de mercado actual o la próxima: (temporada, 'inicio'|'invierno'). v0.4.13.0: por fecha."""
    from alpha_football import temporada as T
    return T.siguiente_ventana(estado)


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


def es_comprable(estado: dict, jugador, club) -> bool:
    """v0.4.26.0: ¿se lo puede comprar hoy? Las mismas puertas que cierran fichar() y evaluar_compra(): a préstamo,
    traspaso ya acordado, llegó a su club en esta ventana, club con la plantilla corta o tu clásico (esos solo por
    cláusula) y tu club sancionado por la liga. No tiene efectos: lo usa el ojeador."""
    try:
        from alpha_football import sancion_liga as SL
        from alpha_football import traspasos_pendientes as TP
        from alpha_football.market import traspasado_en_ventana
        if SL.motivo_bloqueo(estado):
            return False
        if getattr(jugador, 'prestamo', None) or TP.pendiente_de(estado, jugador) is not None:
            return False
        if club is None:                       # agente libre
            return True
        if traspasado_en_ventana(estado, jugador):
            return False
        if plantilla_corta(estado, club) and not getattr(jugador, 'remate', False):
            return False
        from alpha_football.data.clasicos import es_clasico
        if es_clasico(club, estado.get('mi_equipo')) and int(getattr(jugador, 'moral', 70)) >= MORAL_BAJA:
            return False
        return True
    except Exception as e:
        logger.error(f"No se pudo saber si {getattr(jugador, 'nombre_completo', '?')} se puede comprar: {e}")
        return False


def recomendar_fichajes(estado: dict, n: int = 3) -> list:
    """
    n fichajes (jugador, club, etiqueta, precio, motivo) que mejoran el puesto más flojo del
    once y que el user puede pagar (y fichar según market.puede_fichar). Prioriza posiciones
    distintas y la mejora por dólar; los jóvenes con potencial suman.
    v0.4.26.0: solo los que se pueden comprar de verdad (es_comprable).
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
        if not es_comprable(estado, j, club):
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
        recs, caidos = [], False
        for r in guardado.get('recs', []):
            hallado = next(((j, club, et) for j, club, et in pool.values()
                            if f"{j.nombre} {j.apellido}" == r['jugador'] and j.posicion == r['posicion']), None)
            if not hallado:
                continue             # ya no está en el pool (lo ficharon): la lista solo se acorta, como siempre
            if es_comprable(estado, hallado[0], hallado[1]):
                j, club, et = hallado
                recs.append((j, club, et, precio_fichaje(j), r['motivo']))
            else:
                caidos = True        # v0.4.26.0: ya no se puede comprar (llegó a su club, se acordó...): se rehace
        if not caidos:
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
    if getattr(jugador, 'remate', False):
        return precio_fichaje(jugador)        # v4.6.0: remate: sin recargo de figura
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
    for eq, _et in clubes_internacionales(estado):
        if str(eq.id) == str(club_id):
            return eq, next((j for j in eq.jugadores if str(j.id) == str(jugador_id)), None)
    return None, None


def plantilla_corta(estado: dict, club) -> bool:
    """v0.4.20.0: el club (de liga o del banco internacional) que ya no vende sin quedar bajo
    PLANTILLA_MIN_IA; cuenta las compras que ya le acordaste y esperan la ventana."""
    from alpha_football.mercado_ia import PLANTILLA_MIN_IA
    salen = sum(1 for p in (estado.get('datos_carrera') or {}).get('traspasos_pendientes') or []
                if p.get('tipo') == 'compra' and p.get('origen') == club.nombre)
    return len(club.jugadores) - salen <= PLANTILLA_MIN_IA


def evaluar_compra(estado: dict, jugador, club, monto: int) -> tuple:
    """v3.5.0: ('acepta'|'analiza'|'rechaza', mensaje, contraoferta) para una oferta del user."""
    from alpha_football.finanzas import asegurar_contrato
    asegurar_contrato(jugador)
    monto = int(monto or 0)
    from alpha_football import sancion_liga as SL       # v0.4.17.0: se sabe en la primera oferta
    bloqueo = SL.motivo_bloqueo(estado)
    if bloqueo:
        return 'rechaza', bloqueo, 0
    p_pr = getattr(jugador, 'prestamo', None)
    if p_pr:   # préstamos: no se vende a uno que está a préstamo (ni tu propio cedido)
        mi = estado.get('mi_equipo')
        if p_pr.get('dueno') == getattr(mi, 'nombre', None):
            return 'rechaza', f"{jugador.nombre_completo} es tuyo (cedido): usa CONCLUIR PRÉSTAMO en PLANTILLA.", 0
        return 'rechaza', f"{jugador.nombre_completo} está a préstamo en {getattr(club, 'nombre', 'otro club')}: no se vende.", 0
    if club is None:
        return 'acepta', "Agente libre: no hay club con quien negociar.", 0
    from alpha_football.market import traspasado_en_ventana
    if traspasado_en_ventana(estado, jugador):
        return 'rechaza', f"{jugador.nombre_completo} llegó a {club.nombre} en esta ventana: solo a préstamo.", 0
    clausula = int(jugador.clausula or 0)
    if monto >= clausula > 0:
        return 'acepta', f"Pagas la cláusula: {club.nombre} no puede negarse.", 0
    if plantilla_corta(estado, club) and not getattr(jugador, 'remate', False):     # v0.4.20.0 (v0.4.21.0: un remate no se frena)
        return 'rechaza', f"{club.nombre} tiene la plantilla corta: solo por la cláusula de {dinero_exacto(clausula)}.", clausula
    from alpha_football.data.clasicos import es_clasico
    if es_clasico(club, estado.get('mi_equipo')) and int(getattr(jugador, 'moral', 70)) >= MORAL_BAJA:
        return 'rechaza', f"Es tu clásico: solo por la cláusula de {dinero_exacto(clausula)}.", clausula
    minimo = minimo_club(jugador, club)
    if monto >= minimo:
        return 'acepta', f"{club.nombre} acepta {dinero_exacto(monto)}.", 0
    if monto >= int(minimo * UMBRAL_ANALISIS):
        from alpha_football import dia_final as DF      # v0.4.14.0
        ok, hora = DF.analisis(estado)
        if not ok:
            return 'rechaza', f"{club.nombre}: no hay tiempo para analizarlo hoy.", minimo
        dc = estado.setdefault('datos_carrera', {})
        pend = [a for a in dc.get('analisis_compras', []) if a.get('jugador_id') != jugador.id]
        pend.append({'jugador_id': jugador.id, 'club_id': club.id, 'club': club.nombre,
                     'jugador': jugador.nombre_completo, 'monto': monto,
                     'jornada': int(getattr(estado.get('liga'), 'jornada_actual', 1) or 1),
                     'temporada': int(estado.get('temporada', 1) or 1)})
        dias = DF.fijar_respuesta(estado, pend[-1], hora)      # v0.4.26.0: responde a los 1-3 días
        dc['analisis_compras'] = pend
        return 'analiza', f"{club.nombre}: \"Lo analizamos\". {DF.texto_respuesta(hora, dias=dias)}", 0
    return 'rechaza', f"{club.nombre} rechaza. Pide {dinero_exacto(minimo)}.", minimo


def reanudar_compra(estado: dict, compra: dict) -> Optional[str]:
    """v3.5.0: desde el correo 'acepta tu oferta', negociación del contrato con el monto pactado."""
    from alpha_football.market import ventana_mercado_abierta
    liga = estado.get('liga')
    club, j = buscar_en_club(estado, compra.get('club_id'), compra.get('jugador_id'))
    motivo = None
    if int(compra.get('temporada', -1)) != int(estado.get('temporada', 1) or 1):
        motivo = "El acuerdo era de otra temporada."
    elif liga is None or not ventana_mercado_abierta(liga.jornada_actual, liga.num_jornadas, estado=estado):
        motivo = "La ventana de fichajes está cerrada."
    elif j is None:
        motivo = "El jugador ya no está en ese club."
    from alpha_football import sancion_liga as SL       # v0.4.17.0: el corto (el correo recorta el aviso a 60)
    motivo = SL.motivo_bloqueo(estado, corto=True) or motivo
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
    correo a los 1-3 días (v0.4.26.0; antes, la próxima jornada: contraofertas.resolver_analisis). None = rechazo normal.
    """
    j, modo, anios = neg['jugador'], neg['modo'], int(neg['anios'])
    pedido = salario_pedido(j, modo, neg['clausula_mult'])
    if not int(pedido * UMBRAL_ANALISIS) <= int(neg['salario']) < pedido:
        return None
    if not 1 <= anios <= 5 or (j.edad >= EDAD_CONTRATO_CORTO and anios > ANIOS_MAX_VETERANO):
        return None
    from alpha_football import dia_final as DF          # v0.4.14.0: sin 3 horas no hay análisis (rechazo normal)
    ok, hora = DF.analisis(estado)
    if not ok:
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
    dias = DF.fijar_respuesta(estado, pend[-1], hora)      # v0.4.26.0: responde a los 1-3 días
    dc['analisis_contratos'] = pend
    return f"{j.nombre_completo}: \"Lo analizo\". {DF.texto_respuesta(hora, uno=True, dias=dias)}"


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
        try:   # agente libre que llega en la ventana: se guarda con su contrato nuevo
            from alpha_football.traspasos_pendientes import actualizar_datos
            actualizar_datos(estado, jugador)
        except Exception as e_tp:
            logger.error(f"No se pudo actualizar el fichaje pendiente: {e_tp}")
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
        'etapa': 'club' if modo in ('fichaje', 'prestamo') and club is not None else 'jugador',
        'monto': precio_fichaje(jugador) if club is not None else 0,
        'salario': int(salario_pedido(jugador, modo, 2.0) * 0.9), 'anios': anios,
        'clausula_mult': 2.0, 'msg': None,
    }
    if modo == 'prestamo':
        estado['neg'].update({'meses': 6, 'pct': 50})    # duración y % del sueldo que pagas tú
    if modo in ('fichaje', 'prestamo'):                 # v0.4.17.0: sancionado por la liga: se ve al abrir
        from alpha_football import sancion_liga as SL
        bloqueo = SL.motivo_bloqueo(estado)
        if bloqueo:
            estado['neg']['msg'] = (bloqueo, 'rojo')
    return 'negociacion_screen'
