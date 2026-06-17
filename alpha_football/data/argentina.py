# -*- coding: utf-8 -*-
"""
Alpha Football v0.4 — DATOS DE LIGA ARGENTINA.

Este módulo construye y expone la Liga Argentina con 6 equipos de parodia
y sus jugadores reales humorísticos (OVR máximo 80).
"""

from __future__ import annotations

import logging
import random
from alpha_football.models import Liga, Equipo, Jugador

logger = logging.getLogger(__name__)

# Pool de rasgos para asignar aleatoriamente
RASGOS = ["regateador", "lider", "rustico", "pulmon_de_hieron"]

# Plantillas de parodia para los clubes argentinos
PLANTILLAS_PARODIA = {
    "Boca Junias": {
        "ciudad": "Buenos Aires",
        "estrellas": 4.3,
        "estilo_dt": "cruyffismo",
        "balance": 18000000,
        "jugadores": [
            ("Sergio", "Chiquito Sinmanos", "POR", 40, 80, 75, 50, 78),
            ("Lucho", "Rayo Advincula", "DEF", 65, 75, 80, 70, 68),
            ("Marcos", "Rojo Expulsado", "DEF", 35, 78, 80, 50, 80),
            ("Nico", "Cagadon Figal", "DEF", 32, 74, 76, 45, 68),
            ("Lautaro", "Blanco Facil", "DEF", 60, 75, 78, 70, 66),
            ("Pecho", "Pol Fernandez", "MED", 58, 74, 75, 71, 72),
            ("Cristian", "Medinita Humo", "MED", 74, 55, 76, 78, 70),
            ("Kevin", "Zenon Mago", "MED", 77, 45, 75, 80, 74),
            ("Edinson", "Matador Viejito", "DEL", 80, 30, 72, 75, 80),
            ("Miguel", "Bestia Triste", "DEL", 78, 35, 78, 68, 75),
            ("Changito", "Zeballos Roto", "DEL", 76, 32, 70, 78, 62)
        ]
    },
    "River Placas": {
        "ciudad": "Buenos Aires",
        "estrellas": 4.4,
        "estilo_dt": "flickismo",
        "balance": 20000000,
        "jugadores": [
            ("Franco", "Armani Sinreflejos", "POR", 40, 80, 76, 45, 79),
            ("Paulo", "Diaz Pegador", "DEF", 35, 79, 80, 52, 78),
            ("Leandro", "Pirez Pifia", "DEF", 30, 74, 78, 40, 70),
            ("Milton", "Casquito Viejo", "DEF", 58, 73, 70, 68, 76),
            ("Fabricio", "Bustos Roto", "DEF", 60, 74, 75, 66, 68),
            ("Rodrigo", "Aliendro Fantasma", "MED", 62, 75, 76, 70, 72),
            ("Manu", "Lesionini", "MED", 75, 40, 65, 80, 73),
            ("Diablito", "Echeverri Vendido", "MED", 78, 38, 70, 80, 71),
            ("Miguel", "Borjita Colibri", "DEL", 80, 32, 74, 65, 78),
            ("Facundo", "Colidio Frio", "DEL", 76, 35, 72, 75, 68),
            ("Pablo", "Solari Sinmira", "DEL", 75, 30, 78, 72, 64)
        ]
    },
    "Racing de Clavo": {
        "ciudad": "Avellaneda",
        "estrellas": 4.0,
        "estilo_dt": "haramball",
        "balance": 14000000,
        "jugadores": [
            ("Gabriel", "Arias Volador", "POR", 40, 78, 75, 48, 74),
            ("Marco", "Di Cesare Lento", "DEF", 32, 76, 78, 42, 68),
            ("Santiago", "Quiros Pibe", "DEF", 30, 74, 75, 45, 65),
            ("Facundo", "Mura Pasito", "DEF", 55, 73, 74, 62, 66),
            ("Gabriel", "Rojas Cortas", "DEF", 58, 72, 73, 65, 67),
            ("Bruno", "Zuculini Tronco", "MED", 50, 75, 78, 60, 70),
            ("Agustin", "Almendra Rancia", "MED", 74, 45, 74, 77, 72),
            ("Juanfer", "Quintero Panza", "MED", 80, 25, 60, 80, 78),
            ("Adrian", "Maravilla Martinez", "DEL", 79, 30, 77, 68, 76),
            ("Roger", "Martinez Frio", "DEL", 77, 32, 75, 74, 70),
            ("Johan", "Carbonero Humo", "DEL", 76, 28, 76, 75, 62)
        ]
    },
    "Desindependiente": {
        "ciudad": "Avellaneda",
        "estrellas": 3.8,
        "estilo_dt": "cruyffismo",
        "balance": 10000000,
        "jugadores": [
            ("Rodrigo", "Rey Atajador", "POR", 40, 77, 74, 50, 73),
            ("Joaquin", "Laso Rustico", "DEF", 28, 75, 78, 38, 74),
            ("Federico", "Fedelito Vera", "DEF", 55, 72, 74, 60, 65),
            ("Damian", "Perez Abuelo", "DEF", 50, 71, 68, 62, 70),
            ("Felipe", "Lomita Aguilar", "DEF", 30, 73, 76, 42, 67),
            ("Ivan", "Marcone Lento", "MED", 52, 74, 76, 64, 75),
            ("Lucas", "Gonzalez Saltarin", "MED", 68, 55, 72, 70, 66),
            ("Federico", "Mancuello Viejo", "MED", 70, 48, 66, 74, 73),
            ("Gabriel", "Avalos Poste", "DEL", 76, 32, 78, 60, 74),
            ("Alex", "Luna Promesa", "DEL", 73, 35, 71, 74, 63),
            ("Santiago", "Hidalgo Pibe", "DEL", 70, 30, 72, 68, 60)
        ]
    },
    "San Lorenzo Roto": {
        "ciudad": "Buenos Aires",
        "estrellas": 3.7,
        "estilo_dt": "haramball",
        "balance": 8000000,
        "jugadores": [
            ("Facundo", "Altamirano Nervios", "POR", 40, 75, 72, 45, 68),
            ("Jhohan", "Romana Roca", "DEF", 25, 76, 80, 35, 73),
            ("Gaston", "Campi Tronco", "DEF", 28, 74, 78, 38, 71),
            ("Nahuel", "Arias Pibe", "DEF", 50, 70, 72, 58, 60),
            ("Malcom", "Braida Corredor", "DEF", 62, 72, 77, 68, 68),
            ("Eric", "Remedi Traba", "MED", 48, 73, 75, 62, 70),
            ("Elian", "Irala Joven", "MED", 64, 60, 73, 67, 65),
            ("Nahuel", "Barrios Perrito", "MED", 74, 35, 68, 77, 66),
            ("Iker", "Muniain Vidrio", "DEL", 78, 38, 68, 79, 76),
            ("Andres", "Vombergar Tanque", "DEL", 74, 30, 78, 58, 70),
            ("Matias", "Reali Rapido", "DEL", 73, 32, 74, 71, 64)
        ]
    },
    "Talleres de Tallarines": {
        "ciudad": "Cordoba",
        "estrellas": 4.1,
        "estilo_dt": "cruyffismo",
        "balance": 13000000,
        "jugadores": [
            ("Guido", "Herrera Atajadon", "POR", 40, 79, 76, 50, 75),
            ("Catalan", "Matias Rustico", "DEF", 32, 76, 78, 40, 72),
            ("Juan", "Portilla Suave", "DEF", 45, 73, 75, 64, 68),
            ("Gaston", "Benavidez Lanza", "DEF", 58, 74, 76, 65, 68),
            ("Blas", "Riveros Lateral", "DEF", 60, 72, 75, 66, 65),
            ("Ulises", "Ortegoza Correcaminos", "MED", 62, 71, 76, 68, 70),
            ("Ruben", "Botta Mago", "MED", 79, 35, 68, 80, 76),
            ("Marcos", "Portillo Centra", "MED", 68, 58, 74, 70, 68),
            ("Bruno", "Barticciotto Goleador", "DEL", 77, 32, 75, 72, 70),
            ("Federico", "Girotti Poste", "DEL", 76, 30, 78, 60, 72),
            ("Sebastian", "Palacios Corredor", "DEL", 75, 34, 74, 72, 65)
        ]
    }
}

def get_liga() -> Liga:
    """
    Construye y devuelve el objeto Liga Argentina
    con plantillas de parodia completamente pobladas.
    """
    try:
        equipos = []
        id_counter = 300
        
        for nombre_parodia, datos in PLANTILLAS_PARODIA.items():
            jugadores = []
            for j_data in datos["jugadores"]:
                id_counter += 1
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
            nombre="Liga Profesional Argentina",
            tipo="argentina",
            equipos=equipos,
            num_jornadas=10 # 6 equipos -> 10 jornadas
        )
    except Exception as e:
        logger.critical(f"Error critico al construir Liga Argentina: {e}. Retornando fallback.")
        return Liga("Liga Argentina Fallback", "argentina", [], 10)
