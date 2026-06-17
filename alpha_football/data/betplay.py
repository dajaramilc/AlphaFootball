# -*- coding: utf-8 -*-
"""
Alpha Football v0.4 — DATOS DE LIGA BETPLAY.

Este módulo construye y expone la Liga BetPlay (Colombia) con 8 equipos
de parodia y sus jugadores reales humorísticos (OVR máximo 76).
"""

from __future__ import annotations

import logging
import random
from alpha_football.models import Liga, Equipo, Jugador

logger = logging.getLogger(__name__)

# Pool de rasgos para asignar aleatoriamente
RASGOS = ["regateador", "lider", "rustico", "pulmon_de_hierro"]

# Plantillas de parodia para los clubes
PLANTILLAS_PARODIA = {
    "Nacional de Medellin": {
        "ciudad": "Medellín",
        "estrellas": 4.0,
        "estilo_dt": "cruyffismo",
        "balance": 15000000,
        "jugadores": [
            ("Kevin", "Miedo", "POR", 40, 75, 72, 60, 68),
            ("Cristian", "Castrado", "DEF", 45, 74, 76, 55, 62),
            ("Emmanuel", "Olivera (Rustico)", "DEF", 35, 76, 73, 50, 75),
            ("Alvaro", "Angulo Muerto", "DEF", 42, 72, 75, 58, 60),
            ("Pablo", "Rojizo", "DEF", 38, 71, 70, 56, 59),
            ("Sebastian", "Gomez Triste", "MED", 62, 70, 74, 73, 72),
            ("Marino", "Hinestrozado", "MED", 68, 48, 75, 71, 65),
            ("Jarlan", "Barrigona", "MED", 72, 40, 60, 76, 68),
            ("Jefferson", "Duquesa", "DEL", 76, 35, 68, 64, 74),
            ("Adrian", "Ramitos", "DEL", 75, 38, 69, 68, 76),
            ("Daniel", "Mantequilla", "DEL", 70, 42, 72, 71, 64)
        ]
    },
    "Millonarios de Bogota": {
        "ciudad": "Bogotá",
        "estrellas": 4.0,
        "estilo_dt": "flickismo",
        "balance": 12000000,
        "jugadores": [
            ("Alvaro", "Montonero", "POR", 40, 76, 75, 50, 70),
            ("Andres", "Llantas", "DEF", 38, 75, 76, 55, 68),
            ("Juan Pablo", "Vargas Lentas", "DEF", 35, 74, 75, 58, 72),
            ("Larry", "Vasca", "DEF", 44, 71, 72, 60, 65),
            ("Stiven", "Vegano", "DEF", 40, 72, 70, 62, 64),
            ("David", "Silvido", "MED", 68, 55, 65, 75, 76),
            ("Daniel", "Ruido", "MED", 74, 38, 66, 76, 70),
            ("Omar", "Verde", "MED", 65, 60, 71, 69, 63),
            ("Radamel", "Falso", "DEL", 76, 32, 62, 72, 76),
            ("Fernando", "Aburrido", "DEL", 75, 30, 60, 67, 72),
            ("Leonardo", "Castrado", "DEL", 74, 35, 72, 66, 68)
        ]
    },
    "America de Cali Amargo": {
        "ciudad": "Cali",
        "estrellas": 3.5,
        "estilo_dt": "haramball",
        "balance": 10000000,
        "jugadores": [
            ("Joel", "Gratisrol", "POR", 40, 74, 73, 50, 65),
            ("Marcelino", "Carretera", "DEF", 42, 72, 74, 55, 60),
            ("Jeisson", "Pinones", "DEF", 38, 71, 72, 52, 62),
            ("Kevin", "Andrajoso", "DEF", 35, 73, 73, 50, 59),
            ("Yesus", "Cabrita", "DEF", 48, 68, 70, 66, 64),
            ("Rodrigo", "Arena", "MED", 62, 70, 75, 70, 71),
            ("Carlos", "Sierra Nevada", "MED", 66, 62, 72, 68, 67),
            ("Michael", "Rango", "MED", 72, 35, 74, 63, 68),
            ("Deinner", "Quinotos", "DEL", 71, 40, 68, 73, 62),
            ("Pablo", "Malito", "DEL", 69, 30, 72, 62, 60),
            ("Jorge", "Mantequilla", "DEL", 68, 38, 70, 64, 61)
        ]
    },
    "Junior de Barranquilla": {
        "ciudad": "Barranquilla",
        "estrellas": 3.5,
        "estilo_dt": "cruyffismo",
        "balance": 18000000,
        "jugadores": [
            ("Sebastian", "Viejo", "POR", 40, 75, 68, 55, 76),
            ("Fabio", "Delgadito", "DEF", 35, 70, 72, 58, 60),
            ("German", "Quimera", "DEF", 30, 73, 75, 48, 65),
            ("Darwin", "Atrancado", "DEF", 38, 72, 71, 52, 61),
            ("Jose", "Enamorado (Rapido)", "DEF", 69, 50, 75, 72, 63),
            ("Didier", "Morgue", "MED", 58, 72, 76, 65, 70),
            ("Fredy", "Incesto", "MED", 68, 52, 73, 70, 66),
            ("Edwuin", "Cetre (Glow)", "MED", 72, 45, 72, 73, 68),
            ("Carlos", "Vaca", "DEL", 76, 30, 62, 70, 75),
            ("Teofilo", "Guti", "DEL", 73, 35, 60, 75, 76),
            ("Miguel", "Borja Cola", "DEL", 75, 28, 74, 62, 72)
        ]
    },
    "Deportivo Cali Roto": {
        "ciudad": "Cali",
        "estrellas": 3.0,
        "estilo_dt": "flickismo",
        "balance": 8000000,
        "jugadores": [
            ("Nicolas", "Viboras", "POR", 40, 72, 71, 50, 68),
            ("Harold", "Mosquitos", "DEF", 38, 70, 72, 55, 58),
            ("Juan Pablo", "Segovias", "DEF", 35, 71, 74, 48, 62),
            ("Hernando", "Copa", "DEF", 36, 68, 70, 50, 56),
            ("Oscar", "Lozanito", "DEF", 40, 69, 68, 54, 59),
            ("Jhon", "Vazquitas", "MED", 68, 48, 71, 70, 64),
            ("Andres", "Colorado", "MED", 60, 69, 74, 67, 68),
            ("Kevin", "Velitas", "MED", 70, 52, 70, 72, 63),
            ("Marco", "Perezoso", "DEL", 73, 28, 66, 60, 67),
            ("Jhon", "Cordon", "DEL", 71, 32, 73, 64, 60),
            ("Carlos", "Robles", "DEL", 65, 45, 68, 62, 61)
        ]
    },
    "Independiente Santa Fe": {
        "ciudad": "Bogotá",
        "estrellas": 3.0,
        "estilo_dt": "haramball",
        "balance": 7500000,
        "jugadores": [
            ("Leandro", "Castellon", "POR", 40, 73, 69, 52, 72),
            ("Yulian", "Gomez (Tenue)", "DEF", 38, 68, 72, 54, 58),
            ("Jersson", "Gonzalito", "DEF", 42, 69, 70, 58, 60),
            ("Nelson", "Deos", "DEF", 35, 70, 73, 50, 62),
            ("Andres", "Cadaver", "DEF", 32, 72, 74, 45, 75),
            ("Baldomero", "Pelado", "MED", 64, 66, 76, 65, 68),
            ("Jhojan", "Valenzuela", "MED", 58, 69, 72, 63, 64),
            ("Juan", "Penas", "MED", 65, 50, 70, 68, 60),
            ("Hugo", "Rodagol", "DEL", 74, 30, 65, 68, 74),
            ("Elvis", "Perlas", "DEL", 66, 52, 68, 62, 63),
            ("Diego", "Valdovino", "DEL", 68, 32, 70, 64, 59)
        ]
    },
    "Deportes Tolima Oro": {
        "ciudad": "Ibagué",
        "estrellas": 3.0,
        "estilo_dt": "flickismo",
        "balance": 9000000,
        "jugadores": [
            ("Alvaro", "Villa", "POR", 40, 72, 70, 50, 64),
            ("Juan David", "Riascos", "DEF", 38, 69, 73, 52, 61),
            ("Sergio", "Mosquitos", "DEF", 32, 73, 75, 48, 66),
            ("Cristian", "Borracho", "DEF", 35, 70, 71, 50, 60),
            ("Juan", "Pildorita", "DEF", 40, 68, 69, 54, 58),
            ("Anderson", "Platita", "MED", 71, 45, 75, 72, 63),
            ("Steven", "Locura", "MED", 69, 48, 71, 71, 62),
            ("Omar", "Albornos", "MED", 66, 55, 70, 67, 60),
            ("Michael", "Morita", "DEL", 70, 30, 70, 63, 61),
            ("Jaminton", "Campazo", "DEL", 72, 38, 68, 73, 64),
            ("Luciano", "Espina", "DEL", 67, 35, 72, 61, 59)
        ]
    },
    "Once Caldas Viejo": {
        "ciudad": "Manizales",
        "estrellas": 2.5,
        "estilo_dt": "haramball",
        "balance": 6000000,
        "jugadores": [
            ("Diego", "Novato", "POR", 40, 71, 70, 48, 65),
            ("Cesar", "Quinterito", "DEF", 38, 67, 69, 50, 56),
            ("Jhon", "Garrote", "DEF", 32, 69, 72, 45, 60),
            ("Dairon", "Mosquito", "DEF", 35, 68, 70, 48, 55),
            ("Julian", "Quinon", "DEF", 32, 70, 71, 42, 62),
            ("Gustavo", "Torres Roto", "MED", 65, 48, 72, 66, 60),
            ("Rolan", "Piedras", "MED", 62, 50, 68, 64, 59),
            ("Jorge", "Obregoncito", "MED", 64, 42, 70, 63, 58),
            ("Carlos", "Perol", "DEL", 71, 28, 69, 58, 64),
            ("Brayan", "Rovin", "DEL", 68, 45, 71, 62, 60),
            ("Jose", "Cuadrito", "DEL", 65, 30, 64, 60, 62)
        ]
    }
}

def get_liga() -> Liga:
    """
    Construye y devuelve el objeto Liga BetPlay
    con plantillas de parodia completamente pobladas.
    """
    try:
        equipos = []
        id_counter = 100
        
        for nombre_parodia, datos in PLANTILLAS_PARODIA.items():
            jugadores = []
            for j_data in datos["jugadores"]:
                id_counter += 1
                # Rasgo con 28% de probabilidad de no ser nulo
                rasgo = random.choice(RASGOS) if random.random() < 0.28 else None
                jugadores.append(Jugador(
                    nombre=j_data[0],
                    apellido=j_data[1],
                    posicion=j_data[2],
                    ataque=j_data[3],
                    defensa=j_data[4],
                    fisico=j_data[5],
                    tecnica=j_data[6],
                    mental=j_data[7],
                    rasgo=rasgo,
                    moral=70,
                    id=id_counter
                ))
            
            equipos.append(Equipo(
                nombre=nombre_parodia,
                ciudad=datos["ciudad"],
                estrellas=datos["estrellas"],
                estilo_dt=datos["estilo_dt"],
                balance=datos["balance"],
                jugadores=jugadores
            ))
            
        return Liga(
            nombre="Liga BetPlay Colombia",
            tipo="betplay",
            equipos=equipos,
            num_jornadas=14
        )
    except Exception as e:
        logger.critical(f"Error crítico al construir Liga BetPlay: {e}. Retornando liga vacía.")
        # Retorno seguro para evitar que el juego se caiga por completo (resiliencia)
        return Liga("Liga BetPlay Fallback", "betplay", [], 14)
