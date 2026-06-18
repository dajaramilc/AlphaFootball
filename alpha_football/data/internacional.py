# -*- coding: utf-8 -*-
"""
Alpha Football v0.4 — POOLS INTERNACIONALES.

Este módulo expone los pools de equipos para la Copa Libertadores
y la Champions League con sus nombres de parodia y jugadores.
"""

from __future__ import annotations

import logging
import random
from alpha_football.models import Equipo, Jugador

logger = logging.getLogger(__name__)

RASGOS = ["regateador", "lider", "rustico", "pulmon_de_hierro"]

def _generar_jugadores_equipo(ovr_promedio: int, id_start: int) -> list[Jugador]:
    """Genera una plantilla simplificada de 11 jugadores (1 POR, 4 DEF, 3 MED, 3 DEL) para los pools."""
    posiciones = ["POR"] + ["DEF"] * 4 + ["MED"] * 3 + ["DEL"] * 3
    nombres_pool = ["Nico", "Lucas", "Mateo", "Alex", "Diego", "Franco", "Felipe", "Lucho", "Santi", "Juan", "Pedro"]
    apellidos_pool = ["Falso", "Tronco", "Viejo", "Parodia", "Lento", "Roto", "Malo", "Gomez", "Lopez", "Perez", "Silva"]
    
    jugadores = []
    for i, pos in enumerate(posiciones):
        # Ajustamos el overall individual alrededor del promedio del equipo
        ovr = ovr_promedio + random.randint(-4, 4)
        ovr = max(40, min(95, ovr))
        
        # Generar atributos
        if pos == "POR":
            atk, dfs, fis, tec, men = 15, ovr + 5, ovr, ovr - 10, ovr + 5
        elif pos == "DEF":
            atk, dfs, fis, tec, men = ovr - 20, ovr + 10, ovr + 5, ovr - 10, ovr + 5
        elif pos == "MED":
            atk, dfs, fis, tec, men = ovr - 5, ovr - 5, ovr, ovr + 5, ovr
        else: # DEL
            atk, dfs, fis, tec, men = ovr + 10, ovr - 20, ovr, ovr + 5, ovr
            
        rasgo = random.choice(RASGOS) if random.random() < 0.25 else None
        
        jugadores.append(Jugador(
            nombre=nombres_pool[i % len(nombres_pool)],
            apellido=apellidos_pool[i % len(apellidos_pool)] + f" {i}",
            posicion=pos,
            ataque=max(10, min(99, atk)),
            defensa=max(10, min(99, dfs)),
            fisico=max(10, min(99, fis)),
            tecnica=max(10, min(99, tec)),
            mental=max(10, min(99, men)),
            moral=70,
            rasgo=rasgo,
            id=id_start + i
        ))
    return jugadores

# Definimos POOL_LIBERTADORES (Sudamérica, OVR promedio ~75-78)
POOL_LIBERTADORES = [
    Equipo(
        nombre="Penarol Roto", ciudad="Montevideo", estrellas=3.5, estilo_dt="haramball", balance=8000000,
        jugadores=_generar_jugadores_equipo(76, 600)
    ),
    Equipo(
        nombre="Nacionall de Montevideo", ciudad="Montevideo", estrellas=3.5, estilo_dt="cruyffismo", balance=7500000,
        jugadores=_generar_jugadores_equipo(75, 620)
    ),
    Equipo(
        nombre="Colo Colo Roto", ciudad="Santiago", estrellas=3.5, estilo_dt="flickismo", balance=9000000,
        jugadores=_generar_jugadores_equipo(76, 640)
    ),
    Equipo(
        nombre="Olimpia Abuelo", ciudad="Asunción", estrellas=3.5, estilo_dt="haramball", balance=7000000,
        jugadores=_generar_jugadores_equipo(75, 660)
    ),
    Equipo(
        nombre="Barcelona Falso de Guayaquil", ciudad="Guayaquil", estrellas=3.5, estilo_dt="cruyffismo", balance=8500000,
        jugadores=_generar_jugadores_equipo(75, 680)
    ),
    Equipo(
        nombre="Liga de Quito Rota", ciudad="Quito", estrellas=3.8, estilo_dt="flickismo", balance=11000000,
        jugadores=_generar_jugadores_equipo(77, 700)
    ),
    Equipo(
        nombre="Bolivar Sin Aire", ciudad="La Paz", estrellas=3.5, estilo_dt="haramball", balance=6500000,
        jugadores=_generar_jugadores_equipo(74, 720)
    ),
    Equipo(
        nombre="Universitario de la U", ciudad="Lima", estrellas=3.2, estilo_dt="cruyffismo", balance=6000000,
        jugadores=_generar_jugadores_equipo(73, 740)
    ),
    Equipo(
        nombre="Boca Amargo", ciudad="Buenos Aires", estrellas=4.3, estilo_dt="haramball", balance=18000000,
        jugadores=_generar_jugadores_equipo(78, 760)
    ),
    Equipo(
        nombre="Palmeirras", ciudad="São Paulo", estrellas=4.5, estilo_dt="flickismo", balance=22000000,
        jugadores=_generar_jugadores_equipo(78, 780)
    )
]

# Definimos POOL_CHAMPIONS (Europa, OVR promedio ~82-85)
POOL_CHAMPIONS = [
    Equipo(
        nombre="Bayerna de Munich", ciudad="Múnich", estrellas=4.8, estilo_dt="flickismo", balance=50000000,
        jugadores=_generar_jugadores_equipo(84, 800)
    ),
    Equipo(
        nombre="Borussia Dormund", ciudad="Dortmund", estrellas=4.3, estilo_dt="cruyffismo", balance=35000000,
        jugadores=_generar_jugadores_equipo(82, 820)
    ),
    Equipo(
        nombre="Piamonte Calcio", ciudad="Turín", estrellas=4.5, estilo_dt="haramball", balance=40000000,
        jugadores=_generar_jugadores_equipo(83, 840)
    ),
    Equipo(
        nombre="Inter de Milan Roto", ciudad="Milán", estrellas=4.6, estilo_dt="flickismo", balance=45000000,
        jugadores=_generar_jugadores_equipo(84, 860)
    ),
    Equipo(
        nombre="Milan Abuelo", ciudad="Milán", estrellas=4.2, estilo_dt="haramball", balance=30000000,
        jugadores=_generar_jugadores_equipo(81, 880)
    ),
    Equipo(
        nombre="Paris Saint-Germain Sin Champions", ciudad="París", estrellas=4.7, estilo_dt="cruyffismo", balance=60000000,
        jugadores=_generar_jugadores_equipo(84, 900)
    ),
    Equipo(
        nombre="Benfica Maldito", ciudad="Lisboa", estrellas=4.0, estilo_dt="flickismo", balance=25000000,
        jugadores=_generar_jugadores_equipo(80, 920)
    ),
    Equipo(
        nombre="Puerto FC", ciudad="Oporto", estrellas=4.0, estilo_dt="haramball", balance=22000000,
        jugadores=_generar_jugadores_equipo(80, 940)
    )
]

# Cada club internacional también recibe 5 suplentes (plantillas más profundas, igual
# que las ligas locales). Se hace una sola vez al importar el módulo y es idempotente.
try:
    from alpha_football.plantilla import expandir_plantilla
    for _equipo_internacional in POOL_LIBERTADORES + POOL_CHAMPIONS:
        expandir_plantilla(_equipo_internacional, 5)
except Exception as _error_suplentes_copa:
    logger.warning(f"No se pudieron agregar suplentes a los pools internacionales: {_error_suplentes_copa}")
