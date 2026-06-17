"""Copas internacionales de Alpha Football v0.4 (Libertadores / Champions).

Gestiona un torneo de copa con fase de grupos + eliminatorias a partido único
(con definición por penales en caso de empate). El torneo avanza una fase por
llamada a `avanzar_ronda`, lo que encaja con el flujo por pantallas de la UI.

================================================================================
CONTRATO DE DATOS (fijo, compartido entre todos los módulos del juego)
================================================================================
Reutiliza las mismas estructuras Jugador/Equipo/Estado descritas en market.py.
De cada Equipo este módulo solo necesita: "id", "nombre" y "jugadores"
(para calcular su fuerza a partir del overall de la plantilla).

Estructura Copa (dict, serializable a JSON):
    {
        "nombre": str,            # "Copa Libertadores" | "UEFA Champions"
        "fase": str,              # "grupos" | "octavos" | "cuartos"
                                  #  | "semifinal" | "final" | "terminada"
        "participantes": [str],   # ids de los equipos inscritos
        "grupos": [
            {
                "nombre": str,            # "A", "B", ...
                "equipos": [str],         # ids
                "tabla": { id: {"pj","pg","pe","pp","gf","gc","pts"} },
                "partidos": [Partido],
            }, ...
        ],
        "llave": [Partido],       # cruces de la eliminatoria actual
        "historial": [str],       # crónica de resultados para la UI
        "campeon": str|None,      # id del ganador cuando fase == "terminada"
    }

Partido (dict):
    {
        "local": str, "visitante": str,        # ids de equipo
        "goles_local": int|None, "goles_visitante": int|None,
        "penales": str|None,                   # "4-3" si hubo tanda, o None
        "ganador": str|None,
    }
================================================================================
"""

from __future__ import annotations

import logging
import math
import random
from typing import Optional

logger = logging.getLogger(__name__)

# Orden de las fases eliminatorias según cuántos clasificados queden.
_FASE_POR_EQUIPOS = {
    16: "octavos",
    8: "cuartos",
    4: "semifinal",
    2: "final",
}


# --- Acceso resiliente al contrato de datos ----------------------------------

def _campo(entidad: dict, clave: str, por_defecto):
    """Lee una clave del dict tolerando estructuras incompletas o None."""
    try:
        valor = entidad.get(clave, por_defecto)
        return por_defecto if valor is None else valor
    except AttributeError:
        logger.warning("Entidad no es dict al leer '%s'; uso defecto", clave)
        return por_defecto


def fuerza_equipo(equipo: dict) -> float:
    """Calcula la fuerza de un equipo como el promedio de overall de su plantilla.

    Si el equipo no tiene jugadores (dato incompleto de otro módulo), devuelve
    una fuerza neutra de 50 para no romper la simulación del partido.
    """
    plantilla = _campo(equipo, "jugadores", [])
    if not plantilla:
        return 50.0
    overalls = [_campo(j, "overall", 50) for j in plantilla]
    # Pesa más a los 11 mejores: un banquillo enorme no infla la fuerza real.
    titulares = sorted(overalls, reverse=True)[:11]
    return sum(titulares) / len(titulares)


# --- Simulación de un partido de copa ----------------------------------------

def simular_partido(equipo_local: dict, equipo_visitante: dict,
                    rng: Optional[random.Random] = None,
                    desempate: bool = False) -> dict:
    """Simula un partido y devuelve un Partido con el resultado.

    Los goles se modelan con una Poisson aproximada cuya media depende de la
    fuerza relativa de cada equipo más una pizca de azar (factor caótico). Si
    `desempate` es True y hay empate, se resuelve por penales y se fija ganador.
    """
    azar = rng or random.Random()

    fuerza_local = fuerza_equipo(equipo_local) + 3.0  # ventaja de localía
    fuerza_visitante = fuerza_equipo(equipo_visitante)

    goles_local = _muestrear_goles(fuerza_local, fuerza_visitante, azar)
    goles_visitante = _muestrear_goles(fuerza_visitante, fuerza_local, azar)

    partido = {
        "local": _campo(equipo_local, "id", "?"),
        "visitante": _campo(equipo_visitante, "id", "?"),
        "goles_local": goles_local,
        "goles_visitante": goles_visitante,
        "penales": None,
        "ganador": None,
    }

    if goles_local > goles_visitante:
        partido["ganador"] = partido["local"]
    elif goles_visitante > goles_local:
        partido["ganador"] = partido["visitante"]
    elif desempate:
        # Eliminatoria empatada: se define por penales (50/50 con leve sesgo
        # hacia el equipo más fuerte para que no sea pura lotería).
        partido["ganador"], marcador = _tanda_penales(
            equipo_local, equipo_visitante, azar
        )
        partido["penales"] = marcador

    return partido


def _muestrear_goles(fuerza_atacante: float, fuerza_rival: float,
                     azar: random.Random) -> int:
    """Devuelve un número de goles según la diferencia de fuerzas.

    Modela los goles con una Poisson (algoritmo de Knuth) cuya media crece con
    la ventaja del atacante. Se acota a [0, 7] para evitar marcadores absurdos.
    """
    ventaja = (fuerza_atacante - fuerza_rival) / 20.0
    media = max(0.15, 1.25 + ventaja)

    # Algoritmo de Knuth: cuenta cuántos eventos caben antes de superar e^-media.
    limite = math.exp(-media)
    goles = 0
    producto = 1.0
    while goles < 7:
        producto *= azar.random()
        if producto <= limite:
            break
        goles += 1
    return goles


def _tanda_penales(equipo_a: dict, equipo_b: dict,
                   azar: random.Random) -> tuple:
    """Resuelve una tanda de penales y devuelve (id_ganador, "X-Y")."""
    fuerza_a = fuerza_equipo(equipo_a)
    fuerza_b = fuerza_equipo(equipo_b)
    # Probabilidad de que A gane sesgada por fuerza, pero acotada (40%..60%).
    prob_a = min(0.60, max(0.40, 0.50 + (fuerza_a - fuerza_b) / 200.0))

    if azar.random() < prob_a:
        ganador = _campo(equipo_a, "id", "?")
        marcador = azar.choice(["4-3", "5-4", "3-2", "4-2"])
    else:
        ganador = _campo(equipo_b, "id", "?")
        marcador = azar.choice(["3-4", "4-5", "2-3", "2-4"])
    return ganador, marcador


# --- Construcción del torneo -------------------------------------------------

def crear_copa(nombre: str, equipos: list,
               rng: Optional[random.Random] = None) -> dict:
    """Crea una copa con fase de grupos a partir de la lista de equipos.

    Forma grupos de 4 equipos. Para que la eliminatoria posterior cuadre, el
    número de grupos se ajusta a una potencia de 2 (8, 4, 2 o 1 grupos), de la
    que clasifican los 2 primeros de cada grupo.
    """
    azar = rng or random.Random()
    participantes = [_campo(e, "id", None) for e in equipos
                     if _campo(e, "id", None) is not None]

    num_grupos = _grupos_validos(len(participantes))
    if num_grupos == 0:
        # Muy pocos equipos para grupos: arrancamos directo en eliminatorias.
        logger.info("Copa '%s' sin fase de grupos (%d equipos)",
                    nombre, len(participantes))
        copa = {
            "nombre": nombre,
            "fase": "_pendiente_eliminatoria",
            "participantes": participantes,
            "grupos": [],
            "llave": [],
            "historial": [f"Inscritos {len(participantes)} equipos en {nombre}."],
            "campeon": None,
        }
        clasificados = _recorte_potencia_de_dos(participantes)
        _iniciar_eliminatoria(copa, clasificados, azar)
        return copa

    grupos = sortear_grupos(participantes, num_grupos, azar)
    logger.info("Copa '%s' creada: %d grupos de %d equipos",
                nombre, num_grupos, len(participantes) // num_grupos)
    return {
        "nombre": nombre,
        "fase": "grupos",
        "participantes": participantes,
        "grupos": grupos,
        "llave": [],
        "historial": [f"Sorteo de {nombre}: {num_grupos} grupos."],
        "campeon": None,
    }


def _grupos_validos(total_equipos: int) -> int:
    """Devuelve cuántos grupos de 4 formar (potencia de 2), o 0 si no aplica."""
    posibles = total_equipos // 4
    for candidato in (8, 4, 2, 1):
        if candidato <= posibles:
            return candidato
    return 0


def _recorte_potencia_de_dos(ids: list) -> list:
    """Recorta una lista de ids a la mayor potencia de 2 posible (>=2)."""
    tamano = 1
    while tamano * 2 <= len(ids):
        tamano *= 2
    return ids[:max(2, tamano)] if len(ids) >= 2 else ids


def sortear_grupos(participantes: list, num_grupos: int,
                   rng: Optional[random.Random] = None) -> list:
    """Reparte equipos en `num_grupos` grupos de forma aleatoria (serpiente)."""
    azar = rng or random.Random()
    mezclados = list(participantes)
    azar.shuffle(mezclados)

    grupos = [
        {
            "nombre": chr(ord("A") + i),
            "equipos": [],
            "tabla": {},
            "partidos": [],
        }
        for i in range(num_grupos)
    ]

    # Reparto round-robin: equipo i va al grupo i % num_grupos.
    for indice, equipo_id in enumerate(mezclados):
        grupo = grupos[indice % num_grupos]
        grupo["equipos"].append(equipo_id)
        grupo["tabla"][equipo_id] = _fila_tabla_vacia()

    return grupos


def _fila_tabla_vacia() -> dict:
    """Fila inicial de la tabla de un grupo (todo en cero)."""
    return {"pj": 0, "pg": 0, "pe": 0, "pp": 0, "gf": 0, "gc": 0, "pts": 0}


# --- Fase de grupos ----------------------------------------------------------

def simular_fase_grupos(copa: dict, mapa_equipos: dict,
                        rng: Optional[random.Random] = None) -> None:
    """Juega todos los partidos de todos los grupos y actualiza las tablas.

    `mapa_equipos` es un dict {equipo_id: Equipo} para poder calcular fuerzas.
    Tras esto, prepara la eliminatoria con los 2 primeros de cada grupo.
    """
    azar = rng or random.Random()

    for grupo in _campo(copa, "grupos", []):
        equipos_grupo = _campo(grupo, "equipos", [])
        # Todos contra todos (ida sencilla).
        for i in range(len(equipos_grupo)):
            for j in range(i + 1, len(equipos_grupo)):
                id_local, id_visit = equipos_grupo[i], equipos_grupo[j]
                local = _resolver_equipo(mapa_equipos, id_local)
                visitante = _resolver_equipo(mapa_equipos, id_visit)
                partido = simular_partido(local, visitante, azar, desempate=False)
                grupo["partidos"].append(partido)
                _aplicar_resultado_tabla(grupo["tabla"], partido)

    clasificados = clasificados_de_grupos(copa)
    copa["historial"].append(
        f"Fin de fase de grupos: {len(clasificados)} clasificados."
    )
    _iniciar_eliminatoria(copa, clasificados, azar)


def _aplicar_resultado_tabla(tabla: dict, partido: dict) -> None:
    """Actualiza la tabla de un grupo con el resultado de un partido."""
    local, visitante = partido["local"], partido["visitante"]
    gl, gv = partido["goles_local"], partido["goles_visitante"]

    # Aseguramos que ambas filas existan (resiliencia ante datos parciales).
    fila_local = tabla.setdefault(local, _fila_tabla_vacia())
    fila_visit = tabla.setdefault(visitante, _fila_tabla_vacia())

    fila_local["pj"] += 1
    fila_visit["pj"] += 1
    fila_local["gf"] += gl
    fila_local["gc"] += gv
    fila_visit["gf"] += gv
    fila_visit["gc"] += gl

    if gl > gv:
        fila_local["pg"] += 1
        fila_local["pts"] += 3
        fila_visit["pp"] += 1
    elif gv > gl:
        fila_visit["pg"] += 1
        fila_visit["pts"] += 3
        fila_local["pp"] += 1
    else:
        fila_local["pe"] += 1
        fila_visit["pe"] += 1
        fila_local["pts"] += 1
        fila_visit["pts"] += 1


def clasificados_de_grupos(copa: dict) -> list:
    """Devuelve los ids de los 2 primeros de cada grupo, intercalados.

    Se intercala 1º de A con 2º de B, etc., para emparejar cabezas de serie
    contra segundos en la eliminatoria (como en las copas reales).
    """
    primeros, segundos = [], []
    for grupo in _campo(copa, "grupos", []):
        tabla = _campo(grupo, "tabla", {})
        ordenados = sorted(
            _campo(grupo, "equipos", []),
            key=lambda eid: _clave_orden_tabla(tabla.get(eid, _fila_tabla_vacia())),
            reverse=True,
        )
        if ordenados:
            primeros.append(ordenados[0])
        if len(ordenados) > 1:
            segundos.append(ordenados[1])

    # Rotamos los segundos para no cruzar 1º y 2º del mismo grupo de entrada.
    segundos = segundos[1:] + segundos[:1]
    clasificados = []
    for primero, segundo in zip(primeros, segundos):
        clasificados.append(primero)
        clasificados.append(segundo)
    return clasificados


def _clave_orden_tabla(fila: dict) -> tuple:
    """Criterio de orden de la tabla: puntos, luego diferencia de gol, luego GF."""
    diferencia = _campo(fila, "gf", 0) - _campo(fila, "gc", 0)
    return (_campo(fila, "pts", 0), diferencia, _campo(fila, "gf", 0))


# --- Eliminatorias -----------------------------------------------------------

def _iniciar_eliminatoria(copa: dict, clasificados: list,
                          azar: random.Random) -> None:
    """Crea los cruces de la primera ronda eliminatoria a partir de clasificados."""
    clasificados = _recorte_potencia_de_dos(clasificados)
    fase = _FASE_POR_EQUIPOS.get(len(clasificados), "final")
    copa["fase"] = fase
    copa["llave"] = _emparejar(clasificados)
    copa["historial"].append(f"Comienza {fase} con {len(clasificados)} equipos.")


def _emparejar(ids: list) -> list:
    """Crea Partidos enfrentando 1º vs último, 2º vs penúltimo, etc."""
    cruces = []
    izquierda, derecha = 0, len(ids) - 1
    while izquierda < derecha:
        cruces.append({
            "local": ids[izquierda],
            "visitante": ids[derecha],
            "goles_local": None,
            "goles_visitante": None,
            "penales": None,
            "ganador": None,
        })
        izquierda += 1
        derecha -= 1
    return cruces


def simular_ronda_eliminatoria(copa: dict, mapa_equipos: dict,
                               rng: Optional[random.Random] = None) -> list:
    """Juega la llave actual, fija ganadores y prepara la siguiente ronda.

    Devuelve la lista de ganadores (ids). Si solo quedaba un cruce (la final),
    marca al campeón y cierra la copa.
    """
    azar = rng or random.Random()
    ganadores = []

    for cruce in _campo(copa, "llave", []):
        local = _resolver_equipo(mapa_equipos, cruce["local"])
        visitante = _resolver_equipo(mapa_equipos, cruce["visitante"])
        # `desempate=True`: en eliminatoria no puede quedar empate.
        resultado = simular_partido(local, visitante, azar, desempate=True)
        cruce.update(resultado)
        ganadores.append(resultado["ganador"])
        copa["historial"].append(_cronica(cruce, mapa_equipos))

    if len(ganadores) <= 1:
        # Era la final: tenemos campeón.
        copa["campeon"] = ganadores[0] if ganadores else None
        copa["fase"] = "terminada"
        copa["llave"] = []
        nombre = _campo(_resolver_equipo(mapa_equipos, copa["campeon"]),
                        "nombre", copa["campeon"])
        copa["historial"].append(f"🏆 Campeón de {copa['nombre']}: {nombre}")
        logger.info("Copa '%s' finalizada. Campeón: %s", copa["nombre"], nombre)
    else:
        copa["fase"] = _FASE_POR_EQUIPOS.get(len(ganadores), "final")
        copa["llave"] = _emparejar(ganadores)

    return ganadores


def _cronica(cruce: dict, mapa_equipos: dict) -> str:
    """Genera la línea de crónica de un cruce para el historial de la UI."""
    nombre_local = _campo(_resolver_equipo(mapa_equipos, cruce["local"]),
                          "nombre", cruce["local"])
    nombre_visit = _campo(_resolver_equipo(mapa_equipos, cruce["visitante"]),
                          "nombre", cruce["visitante"])
    base = (f"{nombre_local} {cruce['goles_local']}-"
            f"{cruce['goles_visitante']} {nombre_visit}")
    if cruce.get("penales"):
        base += f" (pen {cruce['penales']})"
    return base


# --- Driver de avance por turno/pantalla -------------------------------------

def avanzar_ronda(copa: dict, mapa_equipos: dict,
                  rng: Optional[random.Random] = None) -> dict:
    """Avanza la copa una fase y devuelve un resumen para la UI.

    Llamar repetidamente: grupos -> octavos -> cuartos -> semifinal -> final
    -> terminada. Es idempotente al final: si la copa ya terminó, no hace nada.
    """
    azar = rng or random.Random()
    fase_previa = _campo(copa, "fase", "terminada")

    if fase_previa == "terminada":
        return {"fase": "terminada", "campeon": copa.get("campeon"),
                "novedades": []}

    marca_historial = len(_campo(copa, "historial", []))

    try:
        if fase_previa == "grupos":
            simular_fase_grupos(copa, mapa_equipos, azar)
        else:
            simular_ronda_eliminatoria(copa, mapa_equipos, azar)
    except Exception as error:  # noqa: BLE001 - una copa rota no debe colgar el juego
        logger.error("Fallo al avanzar la copa '%s': %s",
                     _campo(copa, "nombre", "?"), error, exc_info=True)
        return {"fase": fase_previa, "campeon": None, "novedades": [],
                "error": str(error)}

    novedades = _campo(copa, "historial", [])[marca_historial:]
    return {
        "fase": _campo(copa, "fase", "terminada"),
        "campeon": copa.get("campeon"),
        "novedades": novedades,
    }


def obtener_campeon(copa: dict) -> Optional[str]:
    """Devuelve el id del campeón, o None si la copa no ha terminado."""
    return copa.get("campeon") if _campo(copa, "fase", "") == "terminada" else None


def construir_mapa_equipos(estado: dict) -> dict:
    """Helper de integración: arma {equipo_id: Equipo} desde el estado del juego.

    Recorre todas las ligas. Útil para pasar a las funciones de simulación de
    copa sin que el llamador tenga que conocer la estructura interna del estado.
    """
    mapa = {}
    for liga in _campo(estado, "ligas", []):
        for equipo in _campo(liga, "equipos", []):
            identificador = _campo(equipo, "id", None)
            if identificador is not None:
                mapa[identificador] = equipo
    return mapa


def _resolver_equipo(mapa_equipos: dict, equipo_id: str) -> dict:
    """Obtiene un Equipo del mapa; devuelve un stub neutro si falta (resiliencia)."""
    equipo = mapa_equipos.get(equipo_id) if hasattr(mapa_equipos, "get") else None
    if equipo is None:
        # Equipo ausente (dato incompleto): stub con fuerza neutra para no romper.
        logger.warning("Equipo '%s' no está en el mapa; uso stub neutro", equipo_id)
        return {"id": equipo_id, "nombre": str(equipo_id), "jugadores": []}
    return equipo
