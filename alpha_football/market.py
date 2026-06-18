# -*- coding: utf-8 -*-
"""
Alpha Football v0.4 — MERCADO DE FICHAJES ACTIVO.

Este módulo implementa el mercado activo: bolsa de transferibles, compras/ventas
y la simulación del mercado de pases de los rivales.
Soporta de manera resiliente tanto diccionarios como dataclasses del modelo.
"""

from __future__ import annotations

import logging
import random
from typing import Any, Optional
from alpha_football.models import Liga, Equipo, Jugador, OfertaMercado

logger = logging.getLogger(__name__)

# Parámetros del mercado
TAMANO_MERCADO = 12
PLANTILLA_MINIMA = 11
PLANTILLA_MAXIMA = 25
RECARGO_COMPRA = 1.10
RETORNO_VENTA = 0.90

# --- Lectura y escritura resiliente de campos ---------------------------------

def _campo(entidad: Any, clave: str, por_defecto: Any) -> Any:
    """Lee una clave del dict o atributo de un objeto tolerando estructuras incompletas."""
    if entidad is None:
        return por_defecto
    try:
        if isinstance(entidad, dict):
            valor = entidad.get(clave, por_defecto)
        else:
            # En models.Equipo el presupuesto es el atributo balance
            if clave == "presupuesto" and hasattr(entidad, "balance"):
                valor = entidad.balance
            else:
                valor = getattr(entidad, clave, por_defecto)
        return por_defecto if valor is None else valor
    except Exception as e:
        logger.warning(f"Error al leer '{clave}' de la entidad: {e}. Usando defecto.")
        return por_defecto

def _escribir_campo(entidad: Any, clave: str, valor: Any) -> None:
    """Escribe un valor en un diccionario o atributo de un objeto."""
    if entidad is None:
        return
    try:
        if isinstance(entidad, dict):
            entidad[clave] = valor
        else:
            if clave == "presupuesto" and hasattr(entidad, "balance"):
                entidad.balance = valor
            else:
                setattr(entidad, clave, valor)
    except Exception as e:
        logger.error(f"Error al escribir '{clave}' en la entidad: {e}")

# --- Helpers de búsqueda y conversión -----------------------------------------

def iterar_equipos(estado: Any):
    """Genera todos los equipos del estado de manera resiliente."""
    ligas = _campo(estado, "ligas", [])
    for liga in ligas:
        equipos = _campo(liga, "equipos", [])
        for equipo in equipos:
            yield equipo

def buscar_equipo(estado: Any, equipo_id: str) -> Optional[Any]:
    """Devuelve el equipo con el id/nombre dado, o None si no existe."""
    for equipo in iterar_equipos(estado):
        nombre = _campo(equipo, "nombre", "")
        identificador = _campo(equipo, "id", "")
        if identificador == equipo_id or nombre == equipo_id or identificador.lower() == equipo_id.lower():
            return equipo
    return None

def _quitar_jugador_de_equipo(equipo: Any, jugador_id: int | str) -> Optional[Any]:
    """Extrae y remueve un jugador de la plantilla de un equipo."""
    try:
        plantilla = _campo(equipo, "jugadores", [])
        for indice, jugador in enumerate(plantilla):
            j_id = _campo(jugador, "id", None)
            if str(j_id) == str(jugador_id):
                return plantilla.pop(indice)
    except Exception as e:
        logger.error(f"Error al quitar jugador {jugador_id} de equipo: {e}")
    return None

# --- Lógica de precios de mercado ---------------------------------------------

def calcular_valor(jugador: Any) -> int:
    """Recalcula el valor de mercado de un jugador según su overall."""
    try:
        # Se lee el overall de manera resiliente
        overall = _campo(jugador, "overall", 50)
        # Como models.Jugador no tiene edad, usamos 27 (pico de valor) por defecto
        edad = _campo(jugador, "edad", 27)

        # Base exponencial
        valor_base = int((max(1, overall) ** 2) * 1000)

        # Factor de edad
        if edad < 23:
            factor_edad = 1.05
        elif edad <= 29:
            factor_edad = 1.0
        else:
            factor_edad = max(0.30, 1.0 - (edad - 29) * 0.06)

        return max(1000, int(valor_base * factor_edad))
    except Exception as e:
        logger.error(f"Error al calcular valor del jugador: {e}. Retornando 50000.")
        return 50000

def precio_compra(jugador: Any) -> int:
    """Precio de fichaje (valor + recargo)."""
    valor = _campo(jugador, "valor", 0) or calcular_valor(jugador)
    return int(valor * RECARGO_COMPRA)

def precio_venta(jugador: Any) -> int:
    """Precio que recibe el vendedor."""
    valor = _campo(jugador, "valor", 0) or calcular_valor(jugador)
    return int(valor * RETORNO_VENTA)

def calcular_precio(jugador: Any) -> int:
    """Exposición pública de precio de compra para compatibilidad."""
    return precio_compra(jugador)

# --- Generación y renovación del mercado --------------------------------------

def generar_mercado(estado: Any, cantidad: int = TAMANO_MERCADO,
                    rng: Optional[random.Random] = None) -> list[Any]:
    """Construye y guarda la bolsa de transferibles vigente en el estado."""
    azar = rng or random.Random()
    candidatos = []
    
    mi_equipo_id = _campo(estado, "equipo_usuario_id", _campo(estado, "equipo_usuario", None))

    for equipo in iterar_equipos(estado):
        eq_id = _campo(equipo, "id", _campo(equipo, "nombre", ""))
        # El equipo del usuario no vende de manera automática
        if eq_id == mi_equipo_id:
            continue

        plantilla = _campo(equipo, "jugadores", [])
        excedente = len(plantilla) - PLANTILLA_MINIMA
        if excedente <= 0:
            continue

        # Ordenar de menor a mayor overall para liberar los más flojos
        ordenados = sorted(plantilla, key=lambda j: _campo(j, "overall", 50))
        candidatos.extend(ordenados[:excedente])

    # Agentes libres del estado (si existen)
    libres = _campo(estado, "agentes_libres", [])
    candidatos.extend(libres)

    vistos = set()
    unicos = []
    for jugador in candidatos:
        j_id = _campo(jugador, "id", None)
        if j_id is None or j_id in vistos:
            continue
        vistos.add(j_id)
        # Recalcular e inyectar valor
        val = calcular_valor(jugador)
        _escribir_campo(jugador, "valor", val)
        unicos.append(jugador)

    azar.shuffle(unicos)
    mercado = unicos[:max(0, cantidad)]
    _escribir_campo(estado, "mercado", mercado)
    
    logger.info(f"Mercado generado con {len(mercado)} jugadores.")
    return mercado

# --- Operaciones de Fichajes --------------------------------------------------

class ErrorMercado(Exception):
    """Excepción para violaciones de reglas de negocio en el mercado."""

def fichar_jugador(estado: Any, equipo_id: str, jugador_id: int | str) -> Any:
    """Ficha un jugador de la bolsa de mercado para un equipo."""
    equipo = buscar_equipo(estado, equipo_id)
    if equipo is None:
        raise ErrorMercado(f"Equipo inexistente: {equipo_id}")

    mercado = _campo(estado, "mercado", [])
    jugador = next(
        (j for j in mercado if str(_campo(j, "id", None)) == str(jugador_id)), None
    )
    if jugador is None:
        raise ErrorMercado(f"Jugador no está en el mercado: {jugador_id}")

    costo = precio_compra(jugador)
    presupuesto = _campo(equipo, "presupuesto", 0)
    if costo > presupuesto:
        raise ErrorMercado(f"Presupuesto insuficiente: cuesta {costo}, hay {presupuesto}")

    # Transacción
    _escribir_campo(equipo, "presupuesto", presupuesto - costo)
    _escribir_campo(jugador, "equipo_id", equipo_id)
    
    plantilla = _campo(equipo, "jugadores", [])
    plantilla.append(jugador)
    _escribir_campo(equipo, "jugadores", plantilla)

    # Remover del mercado
    nuevas_ofertas = [j for j in mercado if str(_campo(j, "id", None)) != str(jugador_id)]
    _escribir_campo(estado, "mercado", nuevas_ofertas)

    logger.info(f"Fichaje exitoso: {str(_campo(jugador, 'nombre_completo', jugador_id))} al {equipo_id}")
    return jugador

def vender_jugador(estado: Any, equipo_id: str, jugador_id: int | str) -> int:
    """Vende un jugador enviándolo al mercado y sumando balance."""
    equipo = buscar_equipo(estado, equipo_id)
    if equipo is None:
        raise ErrorMercado(f"Equipo inexistente: {equipo_id}")

    plantilla = _campo(equipo, "jugadores", [])
    if len(plantilla) <= PLANTILLA_MINIMA:
        raise ErrorMercado(f"No se puede vender: plantilla mínima es {PLANTILLA_MINIMA}")

    jugador = _quitar_jugador_de_equipo(equipo, jugador_id)
    if jugador is None:
        raise ErrorMercado(f"El equipo no tiene al jugador: {jugador_id}")

    ingreso = precio_venta(jugador)
    presupuesto = _campo(equipo, "presupuesto", 0)
    
    _escribir_campo(equipo, "presupuesto", presupuesto + ingreso)
    _escribir_campo(jugador, "equipo_id", None)
    
    val = calcular_valor(jugador)
    _escribir_campo(jugador, "valor", val)

    # Añadir a mercado
    mercado = _campo(estado, "mercado", [])
    mercado.append(jugador)
    _escribir_campo(estado, "mercado", mercado)

    logger.info(f"Venta exitosa: {str(_campo(jugador, 'nombre_completo', jugador_id))} por {ingreso}")
    return ingreso

# --- Simulación de IA y Fichajes entre Rivales --------------------------------

def simular_movimientos_ia(estado: Any, rng: Optional[random.Random] = None) -> list[str]:
    """Simula los movimientos automáticos de los equipos controlados por la IA."""
    azar = rng or random.Random()
    movimientos = []
    mi_equipo_id = _campo(estado, "equipo_usuario_id", _campo(estado, "equipo_usuario", None))

    for equipo in list(iterar_equipos(estado)):
        eq_id = _campo(equipo, "id", _campo(equipo, "nombre", ""))
        if eq_id == mi_equipo_id:
            continue

        prestigio = int(_campo(equipo, "estrellas", 3.0) * 20.0) # Escala prestigio
        probabilidad = 0.15 + (prestigio / 300.0)
        
        if azar.random() > probabilidad:
            continue

        plantilla = _campo(equipo, "jugadores", [])
        try:
            if len(plantilla) > PLANTILLA_MAXIMA and plantilla:
                peor = min(plantilla, key=lambda j: _campo(j, "overall", 50))
                ingreso = vender_jugador(estado, eq_id, _campo(peor, "id", ""))
                movimientos.append(f"{_campo(equipo, 'nombre', eq_id)} vendió a {_campo(peor, 'nombre_completo', '?')} (+${ingreso:,})")
                continue

            # Buscar mejor objetivo asequible
            objetivo = _mejor_objetivo_asequible(estado, equipo, azar)
            if objetivo is not None:
                costo = precio_compra(objetivo)
                fichar_jugador(estado, eq_id, _campo(objetivo, "id", ""))
                movimientos.append(f"{_campo(equipo, 'nombre', eq_id)} fichó a {_campo(objetivo, 'nombre_completo', '?')} (-${costo:,})")
        except Exception as e:
            logger.debug(f"Movimiento IA omitido para {eq_id}: {e}")

    return movimientos

def _mejor_objetivo_asequible(estado: Any, equipo: Any, azar: random.Random) -> Optional[Any]:
    presupuesto = _campo(equipo, "presupuesto", 0)
    asequibles = [
        j for j in _campo(estado, "mercado", [])
        if precio_compra(j) <= presupuesto
    ]
    if not asequibles:
        return None

    if azar.random() < 0.25:
        return azar.choice(asequibles)
    return max(asequibles, key=lambda j: _campo(j, "overall", 50))

# --- Nuevas funciones del contrato de datos ----------------------------------

def simular_mercado_rivales(liga: Liga, jornada: int) -> list[str]:
    """
    Cada jornada, 30% prob de que 2-3 clubes rivales hagan fichajes
    ENTRE SÍ (el de más balance compra al mejor de un rival con déficit).
    Retorna las descripciones del log.
    """
    try:
        if random.random() > 0.30:
            return []
            
        transacciones = []
        equipos_ia = [e for e in liga.equipos if not getattr(e, "es_usuario", False)]
        if len(equipos_ia) < 2:
            return []
            
        num_fichajes = random.randint(2, 3)
        for _ in range(num_fichajes):
            comprador = max(equipos_ia, key=lambda e: e.balance)
            vendedores = [e for e in equipos_ia if e != comprador and e.balance < comprador.balance and len(e.jugadores) > 11]
            if not vendedores:
                break
                
            vendedor = random.choice(vendedores)
            if not vendedor.jugadores:
                continue
                
            mejor_jugador = max(vendedor.jugadores, key=lambda j: j.overall)
            precio = precio_compra(mejor_jugador)
            
            if comprador.balance >= precio:
                comprador.balance -= precio
                vendedor.balance += precio
                
                vendedor.jugadores.remove(mejor_jugador)
                comprador.jugadores.append(mejor_jugador)
                
                transacciones.append(
                    f"{comprador.nombre} fichó a {mejor_jugador.nombre_completo} de {vendedor.nombre} por ${precio:,}"
                )
        return transacciones
    except Exception as e:
        logger.error(f"Error al simular mercado de rivales: {e}")
        return []

def mercado_de_pases(mi_equipo: Equipo, liga: Liga) -> None:
    """Ventana de transferencias. En Pygame la UI se maneja por separado."""
    pass


# --- Fase 4: Ofertas recibidas por jugadores del usuario (IA compradora) -------

PROB_OFERTA_POR_JORNADA = 0.15  # 15% por jornada con mercado abierto


def ventana_mercado_abierta(jornada: int, num_jornadas: int) -> bool:
    """El mercado está abierto en las jornadas 1-3 y en las últimas 3 de la liga."""
    try:
        return jornada <= 3 or jornada > (num_jornadas - 3)
    except Exception:
        return False


def generar_ofertas_recibidas(
    estado: Any,
    jornada: int,
    num_jornadas: int,
    rng: Optional[random.Random] = None,
    prob: float = PROB_OFERTA_POR_JORNADA,
) -> list:
    """
    Con mercado abierto, 'prob' (15% por defecto) de que la IA oferte por un jugador
    nuestro. monto = valor_jugador * Random(0.95, 1.5). La oferta se anexa a
    estado.mercado_ofertas (lista de OfertaMercado) y también se devuelve.
    """
    azar = rng or random.Random()
    nuevas: list = []
    try:
        if not ventana_mercado_abierta(jornada, num_jornadas):
            return []
        if azar.random() > prob:
            return []

        mi_equipo_id = _campo(estado, "equipo_usuario_id", _campo(estado, "equipo_usuario", None))
        mi_equipo = buscar_equipo(estado, mi_equipo_id) if mi_equipo_id else None
        if mi_equipo is None:
            return []

        plantilla = _campo(mi_equipo, "jugadores", [])
        if len(plantilla) <= PLANTILLA_MINIMA:
            return []  # no ofertan si nos dejarían bajo la plantilla mínima

        objetivo = azar.choice(plantilla)
        valor = _campo(objetivo, "valor", 0) or calcular_valor(objetivo)
        monto = int(valor * azar.uniform(0.95, 1.5))

        # Oferente: un rival (IA) al azar con balance suficiente; si ninguno, el de más balance.
        rivales = [
            e for e in iterar_equipos(estado)
            if _campo(e, "id", "") != mi_equipo_id
        ]
        if not rivales:
            return []
        candidatos = [e for e in rivales if _campo(e, "presupuesto", 0) >= monto]
        oferente = azar.choice(candidatos) if candidatos else max(rivales, key=lambda e: _campo(e, "presupuesto", 0))

        oferta = OfertaMercado(
            jugador_id=int(_campo(objetivo, "id", 0)),
            equipo_origen_id=str(_campo(mi_equipo, "id", mi_equipo_id)),
            equipo_destino_id=str(_campo(oferente, "id", "")),
            monto=monto,
        )
        ofertas = _campo(estado, "mercado_ofertas", [])
        ofertas.append(oferta)
        _escribir_campo(estado, "mercado_ofertas", ofertas)
        nuevas.append(oferta)
        logger.info(f"Oferta recibida: {_campo(oferente,'nombre','IA')} ofrece ${monto:,} por {_campo(objetivo,'nombre_completo','?')}")
    except Exception as e:
        logger.error(f"Error al generar ofertas recibidas: {e}")
    return nuevas


def crear_oferta_ui(mi_equipo: Any, rivales: list, jornada: int, num_jornadas: int,
                    rng: Optional[random.Random] = None, prob: float = PROB_OFERTA_POR_JORNADA) -> Optional[dict]:
    """
    Variante para la UI en runtime (trabaja con OBJETOS directos, no con el modelo persistido).
    Con mercado abierto, 'prob' de que un rival oferte por un jugador nuestro.
    Devuelve un dict {jugador, comprador, monto} o None. La UI lo guarda en
    estado['ofertas_recibidas'] y lo procesa con los mismos objetos.
    """
    azar = rng or random.Random()
    try:
        if not ventana_mercado_abierta(jornada, num_jornadas):
            return None
        if azar.random() > prob:
            return None
        if not mi_equipo or len(getattr(mi_equipo, "jugadores", [])) <= PLANTILLA_MINIMA:
            return None
        objetivo = azar.choice(mi_equipo.jugadores)
        valor = getattr(objetivo, "valor", 0) or calcular_valor(objetivo)
        monto = int(valor * azar.uniform(0.95, 1.5))
        rivales_ok = [r for r in rivales if getattr(r, "balance", 0) >= monto] or list(rivales)
        if not rivales_ok:
            return None
        comprador = azar.choice(rivales_ok)
        return {"jugador": objetivo, "comprador": comprador, "monto": monto}
    except Exception as e:
        logger.error(f"Error al crear oferta de la IA (UI): {e}")
        return None


def aceptar_oferta(estado: Any, oferta: OfertaMercado) -> int:
    """Acepta una oferta recibida: traspasa el jugador al oferente y suma el monto a nuestro balance."""
    mi_equipo = buscar_equipo(estado, oferta.equipo_origen_id)
    comprador = buscar_equipo(estado, oferta.equipo_destino_id)
    if mi_equipo is None or comprador is None:
        raise ErrorMercado("Equipos de la oferta inexistentes")

    jugador = _quitar_jugador_de_equipo(mi_equipo, oferta.jugador_id)
    if jugador is None:
        raise ErrorMercado(f"El jugador {oferta.jugador_id} ya no está en la plantilla")

    _escribir_campo(mi_equipo, "presupuesto", _campo(mi_equipo, "presupuesto", 0) + oferta.monto)
    saldo_comprador = _campo(comprador, "presupuesto", 0)
    _escribir_campo(comprador, "presupuesto", max(0, saldo_comprador - oferta.monto))
    plantilla_comprador = _campo(comprador, "jugadores", [])
    plantilla_comprador.append(jugador)
    _escribir_campo(comprador, "jugadores", plantilla_comprador)

    oferta.aceptada = True
    _retirar_oferta(estado, oferta)
    logger.info(f"Oferta aceptada: {_campo(jugador,'nombre_completo','?')} -> {_campo(comprador,'nombre','?')} por ${oferta.monto:,}")
    return oferta.monto


def rechazar_oferta(estado: Any, oferta: OfertaMercado) -> None:
    """Rechaza (descarta) una oferta recibida."""
    oferta.aceptada = False
    _retirar_oferta(estado, oferta)


def _retirar_oferta(estado: Any, oferta: OfertaMercado) -> None:
    """Quita una oferta de la bandeja estado.mercado_ofertas."""
    ofertas = _campo(estado, "mercado_ofertas", [])
    restantes = [
        o for o in ofertas
        if not (getattr(o, "jugador_id", None) == oferta.jugador_id
                and getattr(o, "equipo_destino_id", None) == oferta.equipo_destino_id)
    ]
    _escribir_campo(estado, "mercado_ofertas", restantes)
