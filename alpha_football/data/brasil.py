# -*- coding: utf-8 -*-
"""
Alpha Football v0.4 — DATOS DE LIGA BRASILEIRA.

Este módulo construye y expone la Liga Brasileira (Brasil) con 6 equipos
de parodia y sus jugadores reales humorísticos (OVR máximo 80).
"""

from __future__ import annotations

import logging
import random
from alpha_football.models import Liga, Equipo, Jugador

logger = logging.getLogger(__name__)

# Pool de rasgos para asignar aleatoriamente
RASGOS = ["regateador", "lider", "rustico", "pulmon_de_hierro"]

# Plantillas de parodia para los clubes brasileños
PLANTILLAS_PARODIA = {
    "Flamenguito de Rio": {
        "ciudad": "Río de Janeiro",
        "estrellas": 4.5,
        "estilo_dt": "cruyffismo",
        "balance": 22000000,
        "jugadores": [
            ("Rossi", "Rossini", "POR", 40, 80, 78, 55, 75),
            ("David", "Lloron (Lider)", "DEF", 35, 78, 80, 50, 80),
            ("Leo", "Pereira Roto", "DEF", 32, 77, 78, 48, 70),
            ("Guillermo", "Varela Lenta", "DEF", 38, 75, 76, 52, 65),
            ("Ayrton", "Lucas Veloz", "DEF", 65, 74, 80, 70, 68),
            ("Erick", "Pulgar Fuerte", "MED", 58, 78, 79, 66, 74),
            ("Nicolas", "De Arrastra", "MED", 78, 45, 70, 80, 77),
            ("Everton", "Cebollon", "MED", 76, 38, 77, 79, 70),
            ("Luiz", "Araujo Falso", "DEL", 75, 40, 78, 74, 68),
            ("Pedro", "Pedrogol", "DEL", 80, 30, 74, 70, 78),
            ("Gabigol", "Gabilento", "DEL", 78, 35, 70, 75, 80)
        ]
    },
    "Palmeras de Sao Paulo": {
        "ciudad": "São Paulo",
        "estrellas": 4.5,
        "estilo_dt": "flickismo",
        "balance": 24000000,
        "jugadores": [
            ("Weverton", "Wevertonin", "POR", 40, 80, 79, 50, 76),
            ("Gustavo", "Gominola (Lider)", "DEF", 30, 80, 80, 48, 80),
            ("Murilo", "Murilito", "DEF", 32, 78, 79, 45, 71),
            ("Marcos", "Rocha Vieja", "DEF", 35, 74, 73, 56, 73),
            ("Piquerez", "Uruguayita", "DEF", 62, 76, 78, 72, 70),
            ("Anibal", "Moreno Rápido", "MED", 60, 77, 78, 68, 72),
            ("Raphael", "Vejiga", "MED", 78, 48, 72, 80, 76),
            ("Ze", "Rafaelin", "MED", 70, 72, 76, 71, 73),
            ("Rony", "Ronito Volador", "DEL", 77, 38, 80, 68, 75),
            ("Estevao", "Estevito 5★", "DEL", 80, 35, 74, 80, 70),
            ("Felipe", "Anderson Roto", "DEL", 78, 42, 75, 78, 72)
        ]
    },
    "Botafogo Estrella": {
        "ciudad": "Río de Janeiro",
        "estrellas": 4.0,
        "estilo_dt": "haramball",
        "balance": 19000000,
        "jugadores": [
            ("John", "Victorin", "POR", 40, 77, 76, 50, 70),
            ("Bastos", "Bastonero", "DEF", 30, 78, 78, 42, 72),
            ("Alexander", "Barboza Rustico", "DEF", 28, 79, 80, 40, 76),
            ("Mateo", "Ponte Duro", "DEF", 45, 74, 76, 60, 64),
            ("Marcal", "Marcelito", "DEF", 38, 73, 73, 58, 67),
            ("Marlon", "Freitas Frito", "MED", 64, 75, 77, 72, 73),
            ("Thiago", "Almohada", "MED", 76, 50, 74, 80, 74),
            ("Luiz", "Enrique Lento", "MED", 78, 42, 78, 79, 68),
            ("Tiquinho", "Suarez", "DEL", 79, 32, 76, 70, 77),
            ("Junior", "Santitos", "DEL", 77, 36, 79, 73, 70),
            ("Igor", "Jesus Cristo", "DEL", 78, 30, 77, 71, 73)
        ]
    },
    "San Pablo FC": {
        "ciudad": "São Paulo",
        "estrellas": 4.0,
        "estilo_dt": "cruyffismo",
        "balance": 16000000,
        "jugadores": [
            ("Rafael", "Rafaelazo", "POR", 40, 78, 75, 48, 73),
            ("Arboleda", "Arbolito", "DEF", 25, 79, 80, 40, 74),
            ("Alan", "Franco Malo", "DEF", 32, 76, 76, 45, 68),
            ("Rafinha", "Rafita Abuelo", "DEF", 35, 73, 68, 60, 78),
            ("Welington", "Welingtonin", "DEF", 55, 72, 78, 65, 63),
            ("Pablo", "Maya Incesto", "MED", 62, 76, 77, 70, 71),
            ("James", "Ruedas (Vidrio)", "MED", 77, 30, 60, 80, 76),
            ("Lucas", "Muera", "MED", 79, 40, 77, 79, 78),
            ("Jonathan", "Callao", "DEL", 80, 32, 76, 65, 78),
            ("Luciano", "Lucianito", "DEL", 76, 35, 71, 72, 72),
            ("Ferreirinha", "Ferro", "DEL", 75, 30, 74, 75, 64)
        ]
    },
    "Fluminense Tricolor": {
        "ciudad": "Río de Janeiro",
        "estrellas": 4.0,
        "estilo_dt": "cruyffismo",
        "balance": 14000000,
        "jugadores": [
            ("Fabio", "Fabian", "POR", 40, 78, 70, 52, 80),
            ("Thiago", "Abuelosilva", "DEF", 30, 80, 74, 55, 80),
            ("Manoel", "Manolo", "DEF", 28, 75, 77, 42, 69),
            ("Samuel", "Xavierin", "DEF", 38, 73, 73, 58, 68),
            ("Marcelo", "Pelo Rulo", "DEF", 70, 72, 68, 80, 79),
            ("Andre", "Andresito", "MED", 65, 78, 79, 73, 76),
            ("Ganso", "Gansito", "MED", 75, 45, 62, 80, 79),
            ("Jhon", "Ario (Arias)", "MED", 78, 55, 78, 78, 75),
            ("German", "Canon", "DEL", 80, 25, 70, 68, 80),
            ("Keno", "Keniata", "DEL", 75, 30, 73, 74, 68),
            ("John", "Kennedy Balas", "DEL", 76, 32, 76, 71, 65)
        ]
    },
    "Gremio Inmortal Roto": {
        "ciudad": "Porto Alegre",
        "estrellas": 3.5,
        "estilo_dt": "haramball",
        "balance": 11000000,
        "jugadores": [
            ("Marchesin", "Marche", "POR", 40, 77, 72, 50, 74),
            ("Pedro", "Geromel Viejo", "DEF", 28, 76, 71, 45, 78),
            ("Walter", "Rustico Kannemann", "DEF", 25, 78, 79, 38, 80),
            ("Joao", "Pedro Lento", "DEF", 40, 72, 74, 55, 62),
            ("Reinaldo", "Rei del penal", "DEF", 58, 72, 75, 64, 69),
            ("Villasanti", "Villa Triste", "MED", 62, 76, 78, 68, 73),
            ("Pepê", "Pepito", "MED", 68, 60, 72, 70, 67),
            ("Franco", "Cristaldo", "MED", 75, 48, 71, 77, 72),
            ("Enano", "Soteldo", "DEL", 78, 30, 70, 79, 70),
            ("Diego", "Costilla", "DEL", 77, 35, 76, 68, 78),
            ("Cristian", "Pavito", "DEL", 74, 38, 74, 71, 65)
        ]
    }
}

def get_liga() -> Liga:
    """
    Construye y devuelve el objeto Liga Brasileira
    con plantillas de parodia completamente pobladas.
    """
    try:
        equipos = []
        id_counter = 200
        
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
            nombre="Brasileirão Brasil",
            tipo="brasil", # de acuerdo a models.py tipo = brasil
            equipos=equipos,
            num_jornadas=10 # 6 equipos -> 10 jornadas ida y vuelta
        )
    except Exception as e:
        logger.critical(f"Error crítico al construir Liga Brasileira: {e}. Retornando fallback.")
        return Liga("Liga Brasileira Fallback", "brasil", [], 10)
