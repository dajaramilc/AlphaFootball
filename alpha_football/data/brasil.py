# -*- coding: utf-8 -*-
"""
Alpha Football v0.7 — DATOS DE LIGA BRASILEIRA.

Este módulo construye y expone la Liga Brasileira (Brasil) con 6 equipos
de parodia y sus jugadores reales humorísticos (OVR máximo 80).
Cada equipo cuenta con 20 jugadores reales parodiados.
"""

from __future__ import annotations

import logging
import random
from alpha_football.models import Liga, Equipo, Jugador

logger = logging.getLogger(__name__)

# Pool de rasgos para asignar aleatoriamente
RASGOS = ["regateador", "lider", "rustico", "pulmon_de_hierro"]

def generar_atributos_por_posicion(ovr_sugerido: int, posicion: str) -> tuple[int, int, int, int, int]:
    """
    Genera los 5 atributos individuales de un jugador (ataque, defensa, fisico, tecnica, mental)
    basado en su posición y una valoración general (OVR) sugerida.
    Garantiza de manera resiliente que el promedio entero sea exactamente el OVR.
    """
    try:
        ovr_objetivo = min(max(ovr_sugerido, 40), 83)
        
        if posicion == "POR":
            ataque = 15
            defensa = ovr_objetivo + 15
            fisico = ovr_objetivo + 5
            tecnica = ovr_objetivo - 10
            mental = ovr_objetivo + 10
        elif posicion == "DEF":
            ataque = ovr_objetivo - 25
            defensa = ovr_objetivo + 15
            fisico = ovr_objetivo + 10
            tecnica = ovr_objetivo - 10
            mental = ovr_objetivo + 10
        elif posicion == "MED":
            ataque = ovr_objetivo - 5
            defensa = ovr_objetivo - 5
            fisico = ovr_objetivo
            tecnica = ovr_objetivo + 10
            mental = ovr_objetivo
        else:
            ataque = ovr_objetivo + 15
            defensa = ovr_objetivo - 25
            fisico = ovr_objetivo + 5
            tecnica = ovr_objetivo + 10
            mental = ovr_objetivo - 5

        atributos = [max(10, min(99, val)) for val in (ataque, defensa, fisico, tecnica, mental)]
        
        suma_objetivo = ovr_objetivo * 5
        for _ in range(50):
            suma_actual = sum(atributos)
            if suma_actual == suma_objetivo:
                break
            diferencia = suma_objetivo - suma_actual
            paso = 1 if diferencia > 0 else -1
            
            indices = [0, 1, 2, 3, 4]
            random.shuffle(indices)
            for idx in indices:
                nuevo_valor = atributos[idx] + paso
                if 10 <= nuevo_valor <= 99:
                    atributos[idx] = nuevo_valor
                    break
                    
        return tuple(atributos)

    except Exception as error_generacion:
        logger.error(f"Fallo al generar atributos (OVR={ovr_sugerido}, Pos={posicion}): {error_generacion}. Aplicando fallback.")
        valor_defecto = min(max(ovr_sugerido, 45), 83)
        return (valor_defecto, valor_defecto, valor_defecto, valor_defecto, valor_defecto)

# Plantillas de parodia para los clubes brasileños (20 jugadores base por equipo)
PLANTILLAS_PARODIA = {
    "Flamenguito": {
        "ciudad": "Río de Janeiro",
        "estrellas": 4.5,
        "estilo_dt": "cruyffismo",
        "balance": 22000000,
        "jugadores": [
            ("Rossi", "Rossini", "POR", 79, "None", 28),
            ("Matheus", "Cunhazo", "POR", 72, "None", 23),
            ("David", "Lloron", "DEF", 74, "lider", 37),
            ("Leo", "Pereira Roto", "DEF", 76, "rustico", 28),
            ("Guillermo", "Varela Lenta", "DEF", 74, None, 31),
            ("Ayrton", "Lucas Veloz", "DEF", 77, "pulmon_de_hierro", 26),
            ("Fabricio", "Bruno", "DEF", 78, "rustico", 28),
            ("Matias", "Vinazo", "DEF", 75, None, 26),
            ("Wesley", "Regateador", "DEF", 73, "pulmon_de_hierro", 20),
            ("Erick", "Pulgar Fuerte", "MED", 76, "rustico", 30),
            ("Nicolas", "De Arrastra", "MED", 82, "regateador", 30),
            ("Gerson", "Coringa", "MED", 82, "lider", 27),
            ("Nicolas", "De la Cruzazo", "MED", 82, "pulmon_de_hierro", 27),
            ("Allan", "Lento", "MED", 74, None, 27),
            ("Evertton", "Araujazo", "MED", 72, None, 21),
            ("Alcaraz", "Millonario", "MED", 76, None, 21),
            ("Everton", "Cebollon", "DEL", 77, "regateador", 28),
            ("Luiz", "Araujo Falso", "DEL", 76, "regateador", 28),
            ("Pedro", "Pedrogol", "DEL", 83, "lider", 26),
            ("Gabigol", "Gabilento", "DEL", 78, "lider", 27)
        ]
    },
    "Palmeras de Sao Paulo": {
        "ciudad": "São Paulo",
        "estrellas": 4.5,
        "estilo_dt": "flickismo",
        "balance": 24000000,
        "jugadores": [
            ("Weverton", "Wevertonin", "POR", 78, "lider", 36),
            ("Marcelo", "Lomba", "POR", 71, None, 37),
            ("Gustavo", "Gominola", "DEF", 81, "lider", 31),
            ("Murilo", "Murilito", "DEF", 79, "rustico", 27),
            ("Marcos", "Rocha Vieja", "DEF", 73, None, 35),
            ("Piquerez", "Uruguayita", "DEF", 79, "pulmon_de_hierro", 25),
            ("Vitor", "Reis", "DEF", 75, None, 18),
            ("Mayke", "Centros", "DEF", 74, None, 31),
            ("Caio", "Paulista", "DEF", 73, "pulmon_de_hierro", 26),
            ("Anibal", "Moreno Rapido", "MED", 78, "rustico", 24),
            ("Raphael", "Vejiga", "MED", 82, "regateador", 29),
            ("Ze", "Rafaelin", "MED", 76, "rustico", 31),
            ("Richard", "Rios Cafe", "MED", 78, "regateador", 24),
            ("Mauricio", "Joven", "MED", 77, None, 23),
            ("Gabriel", "Menino", "MED", 75, None, 23),
            ("Rony", "Ronito Volador", "DEL", 76, "pulmon_de_hierro", 29),
            ("Estevao", "Estevito", "DEL", 83, "regateador", 17),
            ("Felipe", "Anderson Roto", "DEL", 78, "regateador", 31),
            ("Flaco", "Lopez", "DEL", 81, None, 23),
            ("Lazaro", "Promesa", "DEL", 74, None, 22)
        ]
    },
    "Botafogo Estrella": {
        "ciudad": "Río de Janeiro",
        "estrellas": 4.0,
        "estilo_dt": "haramball",
        "balance": 19000000,
        "jugadores": [
            ("John", "Victorin", "POR", 78, None, 28),
            ("Gatito", "Fernandez", "POR", 72, None, 36),
            ("Bastos", "Bastonero", "DEF", 77, "rustico", 32),
            ("Alexander", "Barboza Rustico", "DEF", 76, "rustico", 29),
            ("Mateo", "Ponte Duro", "DEF", 75, "pulmon_de_hierro", 21),
            ("Marcal", "Marcelito", "DEF", 73, None, 35),
            ("Adryelson", "Muro", "DEF", 78, "rustico", 26),
            ("Vitinho", "Rapido", "DEF", 74, None, 24),
            ("Cuiabano", "Lateral", "DEF", 75, "pulmon_de_hierro", 21),
            ("Marlon", "Freitas Frito", "MED", 76, "rustico", 29),
            ("Thiago", "Almada", "MED", 82, "regateador", 23),
            ("Gregore", "Volante", "MED", 76, "rustico", 30),
            ("Allan", "Volantazo", "MED", 74, None, 27),
            ("Jefferson", "Savarino", "MED", 78, "regateador", 27),
            ("Tche Tche", "Corredor", "MED", 74, "pulmon_de_hierro", 31),
            ("Luiz", "Enrique Lento", "DEL", 82, "regateador", 23),
            ("Tiquinho", "Suarez", "DEL", 78, "lider", 33),
            ("Junior", "Santitos", "DEL", 76, "pulmon_de_hierro", 29),
            ("Igor", "Jesus", "DEL", 80, None, 23),
            ("Matheus", "Martins", "DEL", 75, "regateador", 20)
        ]
    },
    "Don Pablo": {
        "ciudad": "São Paulo",
        "estrellas": 4.0,
        "estilo_dt": "cruyffismo",
        "balance": 16000000,
        "jugadores": [
            ("Rafael", "Rafaelazo", "POR", 77, None, 34),
            ("Jandrei", "Manos", "POR", 71, None, 31),
            ("Arboleda", "Arbolito", "DEF", 78, "rustico", 32),
            ("Alan", "Franco Malo", "DEF", 75, "rustico", 27),
            ("Rafinha", "Rafita Abuelo", "DEF", 73, "lider", 38),
            ("Welington", "Welingtonin", "DEF", 75, "pulmon_de_hierro", 23),
            ("Igor", "Vinicius", "DEF", 74, "pulmon_de_hierro", 27),
            ("Sabino", "Zurdo", "DEF", 72, None, 27),
            ("Ferraresi", "Vinotinto", "DEF", 73, None, 25),
            ("Pablo", "Maia Incesto", "MED", 77, "rustico", 22),
            ("Alisson", "Corredor", "MED", 76, "pulmon_de_hierro", 31),
            ("Giuliano", "Galoppo", "MED", 74, None, 25),
            ("Damian", "Bobadilla", "MED", 74, None, 22),
            ("Luiz", "Gustavo Abuelo", "MED", 73, "lider", 36),
            ("Wellington", "Rato", "MED", 74, None, 32),
            ("Lucas", "Muera", "DEL", 82, "regateador", 31),
            ("Jonathan", "Callao", "DEL", 79, "lider", 30),
            ("Luciano", "Lucianito", "DEL", 77, "lider", 31),
            ("Ferreirinha", "Ferro", "DEL", 76, "regateador", 26),
            ("Andre", "Silva", "DEL", 74, None, 27)
        ]
    },
    "Flu": {
        "ciudad": "Río de Janeiro",
        "estrellas": 4.0,
        "estilo_dt": "anchelottismo",
        "balance": 15000000,
        "jugadores": [
            ("Fabio", "Abuelo", "POR", 76, "lider", 43),
            ("Felipe", "Alves", "POR", 69, None, 36),
            ("Thiago", "Silva Monumento", "DEF", 81, "lider", 39),
            ("Felipe", "Melo Loco", "DEF", 72, "rustico", 40),
            ("Guga", "Lateral", "DEF", 73, None, 25),
            ("Samuel", "Xavier", "DEF", 73, "rustico", 34),
            ("Diogo", "Barbosa", "DEF", 72, None, 31),
            ("Ignacio", "Muro", "DEF", 75, "rustico", 27),
            ("Manoel", "Tronco", "DEF", 72, None, 34),
            ("Martinelli", "Fluminense", "MED", 76, "pulmon_de_hierro", 22),
            ("Ganso", "Tortuga", "MED", 78, "regateador", 34),
            ("Jhon", "Arias Mago", "MED", 82, "regateador", 26),
            ("Facundo", "Bernal", "MED", 75, None, 20),
            ("Renato", "Augusto Vidrio", "MED", 75, None, 36),
            ("Nonato", "Corredor", "MED", 73, None, 26),
            ("German", "Cano Goleador", "DEL", 78, None, 36),
            ("Keno", "Regates", "DEL", 75, "regateador", 34),
            ("Kaua", "Elias Joven", "DEL", 75, None, 18),
            ("Marquinhos", "Rapido", "DEL", 75, "regateador", 21),
            ("John", "Kennedy Fiestero", "DEL", 75, None, 22)
        ]
    },
    "Gremio Copero": {
        "ciudad": "Porto Alegre",
        "estrellas": 4.1,
        "estilo_dt": "haramball",
        "balance": 14000000,
        "jugadores": [
            ("Agustin", "Marchesin", "POR", 75, None, 36),
            ("Caique", "Muro", "POR", 71, None, 26),
            ("Jemerson", "Lento", "DEF", 74, "rustico", 31),
            ("Walter", "Kannemann Carnicero", "DEF", 77, "rustico", 33),
            ("Reinaldo", "Penales", "DEF", 75, "pulmon_de_hierro", 34),
            ("Joao", "Pedro", "DEF", 75, None, 27),
            ("Rodrigo", "Ely", "DEF", 73, "rustico", 30),
            ("Fabio", "Lateral", "DEF", 72, None, 33),
            ("Gustavo", "Martins", "DEF", 72, None, 21),
            ("Villasanti", "Pulmon", "MED", 78, "pulmon_de_hierro", 27),
            ("Pepe", "Pase", "MED", 75, None, 26),
            ("Edenilson", "Viejo", "MED", 73, None, 34),
            ("Franco", "Cristaldo", "MED", 78, "regateador", 27),
            ("Yeferson", "Soteldo Enano", "MED", 81, "regateador", 26),
            ("Dodi", "Volante", "MED", 74, "rustico", 28),
            ("Martin", "Braithwaite Vikingo", "DEL", 78, "lider", 32),
            ("Diego", "Costa Abuelo", "DEL", 76, "rustico", 35),
            ("Pavon", "Turbo", "DEL", 76, "regateador", 28),
            ("Gustavo", "Nunes", "DEL", 74, "regateador", 18),
            ("Nathan", "Fernandes", "DEL", 73, None, 19)
        ]
    }
}

NOMBRES_CORTOS = {
    "Flamenguito": "Flamenguito", "Palmeras de Sao Paulo": "Palmeiras",
    "Botafogo Estrella": "Botafogo", "Don Pablo": "Don Pablo",
    "Flu": "Flu", "Gremio Copero": "Gremio",
}
ESTILO_OVERRIDE = {
    "Flu": "anchelottismo",
    "Gremio Copero": "haramball"
}

def get_liga() -> Liga:
    """
    Construye y devuelve el objeto Liga Brasileira
    con plantillas de parodia completamente pobladas de 20 jugadores.
    """
    try:
        equipos = []
        id_counter = 200
        
        for nombre_parodia, datos in PLANTILLAS_PARODIA.items():
            jugadores = []
            for j_data in datos["jugadores"]:
                id_counter += 1
                
                # Obtener los datos base del jugador
                pnombre, papellido, pos, ovr, rasgo, edad = j_data
                
                # Generamos los 5 atributos individuales de forma coherente y robusta
                atk, dfs, fis, tec, men = generar_atributos_por_posicion(ovr, pos)
                
                jugadores.append(Jugador(
                    nombre=pnombre,
                    apellido=papellido,
                    posicion=pos,
                    ataque=atk,
                    defensa=dfs,
                    fisico=fis,
                    tecnica=tec,
                    mental=men,
                    rasgo=rasgo,
                    moral=70,
                    id=id_counter,
                    edad=edad
                ))
            
            equipos.append(Equipo(
                nombre=nombre_parodia,
                ciudad=datos["ciudad"],
                estrellas=datos["estrellas"],
                estilo_dt=ESTILO_OVERRIDE.get(nombre_parodia, datos["estilo_dt"]),
                balance=datos["balance"],
                jugadores=jugadores,
                nombre_corto=NOMBRES_CORTOS.get(nombre_parodia, "")
            ))
            
        return Liga(
            nombre="Brasileirão Brasil",
            tipo="brasil",
            equipos=equipos,
            num_jornadas=10
        )
    except Exception as e:
        logger.critical(f"Error crítico al construir Liga Brasileira: {e}. Retornando fallback.")
        return Liga("Liga Brasileira Fallback", "brasil", [], 10)
