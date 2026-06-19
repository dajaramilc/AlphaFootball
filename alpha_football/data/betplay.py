# -*- coding: utf-8 -*-
"""
Alpha Football — DATOS DE LIGA BETPLAY.

Este módulo construye y expone la Liga BetPlay (Colombia) con 8 equipos
de parodia y sus jugadores reales humorísticos (OVR máximo 76).
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
    Garantiza de manera resiliente que el promedio entero sea exactamente el OVR, y que ningún
    atributo salga de los rangos válidos [10, 99].
    """
    try:
        # Se restringe el rating general entre los límites lógicos del juego para BetPlay (tope 83)
        ovr_objetivo = min(max(ovr_sugerido, 40), 83)
        
        # Inicialización de atributos según la posición táctica del jugador
        if posicion == "POR":
            # Portero: Alta defensa (reflejos) y mental. Ataque mínimo.
            ataque = 15
            defensa = ovr_objetivo + 15
            fisico = ovr_objetivo + 5
            tecnica = ovr_objetivo - 10
            mental = ovr_objetivo + 10
        elif posicion == "DEF":
            # Defensa: Alta defensa y físico. Bajo ataque.
            ataque = ovr_objetivo - 25
            defensa = ovr_objetivo + 15
            fisico = ovr_objetivo + 10
            tecnica = ovr_objetivo - 10
            mental = ovr_objetivo + 10
        elif posicion == "MED":
            # Mediocampista: Atributos equilibrados, alta técnica.
            ataque = ovr_objetivo - 5
            defensa = ovr_objetivo - 5
            fisico = ovr_objetivo
            tecnica = ovr_objetivo + 10
            mental = ovr_objetivo
        else:
            # Delantero (DEL): Alto ataque y técnica. Baja defensa.
            ataque = ovr_objetivo + 15
            defensa = ovr_objetivo - 25
            fisico = ovr_objetivo + 5
            tecnica = ovr_objetivo + 10
            mental = ovr_objetivo - 5

        # Normalizamos los atributos dentro del rango legal [10, 99]
        atributos = [max(10, min(99, val)) for val in (ataque, defensa, fisico, tecnica, mental)]
        
        # Reajuste iterativo para asegurar que el promedio exacto de los atributos coincida con el ovr_objetivo
        suma_objetivo = ovr_objetivo * 5
        for _ in range(50):
            suma_actual = sum(atributos)
            if suma_actual == suma_objetivo:
                break
            diferencia = suma_objetivo - suma_actual
            paso = 1 if diferencia > 0 else -1
            
            # Ajustamos de manera pseudo-aleatoria los atributos de la lista
            indices = [0, 1, 2, 3, 4]
            random.shuffle(indices)
            for idx in indices:
                nuevo_valor = atributos[idx] + paso
                if 10 <= nuevo_valor <= 99:
                    atributos[idx] = nuevo_valor
                    break
                    
        return tuple(atributos)

    except Exception as error_generacion:
        # En caso de fallo inesperado, usamos una solución de fallback
        logger.error(f"Fallo al generar atributos (OVR={ovr_sugerido}, Pos={posicion}): {error_generacion}. Aplicando fallback.")
        valor_defecto = min(max(ovr_sugerido, 45), 83)
        return (valor_defecto, valor_defecto, valor_defecto, valor_defecto, valor_defecto)

# Plantillas de parodia para los clubes (20 jugadores base por equipo)
# Formato: (Nombre, Apellido, Posicion, OVR, Rasgo (u omitido/None), Edad)
PLANTILLAS_PARODIA = {
    "Narconal": {
        "ciudad": "Medellín",
        "estrellas": 4.0,
        "estilo_dt": "cruyffismo",
        "balance": 15000000,
        "jugadores": [
            ("David", "Espina", "POR", 82, "lider", 37),
            ("Harlen", "Castillo (Chipi)", "POR", 72, None, 30),
            ("Felipe", "Romano", "DEF", 76, "pulmon_de_hierro", 28),
            ("Alvaro", "Angulo Muerto", "DEF", 74, None, 27),
            ("William", "Tejido", "DEF", 81, "lider", 33),
            ("Juan Felipe", "Hoguera", "DEF", 75, "rustico", 28),
            ("Samuel", "Velita", "DEF", 72, None, 20),
            ("Simón", "García", "DEF", 69, None, 21),
            ("Robert", "Miedito", "MED", 74, "pulmon_de_hierro", 24),
            ("Jhojan", "Amargo", "MED", 70, None, 22),
            ("Edwin", "Cartona", "MED", 83, "lider", 32),
            ("Juan Manuel", "Zapato", "MED", 74, None, 23),
            ("Pablo", "Pincelini", "MED", 75, "regateador", 33),
            ("Kevin", "Parado", "MED", 71, None, 21),
            ("Kilian", "Tosco", "MED", 69, "rustico", 22),
            ("Alfredo", "Morral", "DEL", 81, "rustico", 28),
            ("Kevin", "Vivero", "DEL", 75, "regateador", 25),
            ("Dairon", "Aspirina", "DEL", 73, "pulmon_de_hierro", 31),
            ("Marino", "Te-destroza", "DEL", 74, "regateador", 23),
            ("Hanyer", "Quinotos", "DEL", 69, None, 19)
        ]
    },
    "Pobres Vagos": {
        "ciudad": "Bogotá",
        "estrellas": 4.0,
        "estilo_dt": "flickismo",
        "balance": 12000000,
        "jugadores": [
            ("Alvaro", "Montonero", "POR", 83, "lider", 29),
            ("Diego", "Novato", "POR", 70, None, 34),
            ("Juan Pablo", "Vargas Lentas", "DEF", 81, "lider", 29),
            ("Andres", "Llantas", "DEF", 76, "rustico", 28),
            ("Danovis", "Manguero", "DEF", 73, None, 36),
            ("Delvin", "Alfalfa", "DEF", 74, "pulmon_de_hierro", 26),
            ("Jorge", "Arepas", "DEF", 71, "rustico", 32),
            ("Sander", "Naranjo", "DEF", 70, None, 22),
            ("Daniel", "Girasol", "MED", 74, "pulmon_de_hierro", 31),
            ("David", "Silvido", "MED", 81, "lider", 36),
            ("Daniel", "Ruido", "MED", 78, "regateador", 22),
            ("Stiven", "Vegano", "MED", 74, "pulmon_de_hierro", 27),
            ("Felix", "Chatarra", "MED", 69, None, 22),
            ("Juan Carlos", "Pereza", "MED", 73, None, 33),
            ("Radamel", "Falso", "DEL", 83, "lider", 39),
            ("Leonardo", "Castrado", "DEL", 78, "pulmon_de_hierro", 31),
            ("Santiago", "Jordán", "DEL", 74, "rustico", 29),
            ("Daniel", "Castaño", "MED", 76, "regateador", 32),
            ("Jader", "Amargo", "DEL", 71, None, 27),
            ("Beckham", "Castro", "DEL", 70, None, 22)
        ]
    },
    "ABerica de Cali": {
        "ciudad": "Cali",
        "estrellas": 3.5,
        "estilo_dt": "haramball",
        "balance": 10000000,
        "jugadores": [
            ("Joel", "Gratisrol", "POR", 78, None, 27),
            ("Jorge", "Sótano", "POR", 70, None, 31),
            ("Daniel", "Bocasucia", "DEF", 76, "lider", 37),
            ("Andres", "Mosquita", "DEF", 74, "rustico", 33),
            ("Edwin", "Velas", "DEF", 74, None, 32),
            ("Nilson", "Castrado", "DEF", 73, None, 28),
            ("Jeisson", "Pinones", "DEF", 71, "rustico", 29),
            ("Marcos", "Minero", "DEF", 69, None, 25),
            ("Harold", "Riachuelo", "MED", 73, None, 30),
            ("Franco", "Leyes", "MED", 74, "rustico", 26),
            ("Jader", "Quinotos", "MED", 73, None, 25),
            ("Alexis", "Zapato", "MED", 74, "regateador", 26),
            ("Luis", "Guerra", "MED", 71, "lider", 35),
            ("Eder", "Balanza", "MED", 77, "lider", 31),
            ("Adrian", "Ramitos", "DEL", 81, "lider", 39),
            ("Cristian", "Vecindario", "DEL", 77, "regateador", 26),
            ("Rodrigo", "Arena", "DEL", 75, "rustico", 29),
            ("Duvan", "Verdulero", "DEL", 83, "regateador", 29),
            ("Pipe", "Gomecito", "DEL", 70, None, 24),
            ("Yohan", "Garcita", "DEL", 69, None, 19)
        ]
    },
    "Junior daddy": {
        "ciudad": "Barranquilla",
        "estrellas": 3.5,
        "estilo_dt": "cruyffismo",
        "balance": 18000000,
        "jugadores": [
            ("Santiago", "Miel", "POR", 83, "lider", 28),
            ("Jefferson", "Martin", "POR", 70, None, 31),
            ("Emmanuel", "Olivera (Rustico)", "DEF", 77, "rustico", 33),
            ("Jermein", "Penas", "DEF", 75, "rustico", 24),
            ("Gabriel", "Fuenterroto", "DEF", 76, "pulmon_de_hierro", 27),
            ("Edwin", "Herradura", "DEF", 74, None, 26),
            ("Rafa", "Perezoso", "DEF", 74, "lider", 35),
            ("Yeferson", "Morado", "DEF", 69, None, 22),
            ("Victor", "Canto", "MED", 77, "lider", 31),
            ("Didier", "Morgue", "MED", 74, "pulmon_de_hierro", 33),
            ("Homero", "Martin", "MED", 73, None, 26),
            ("Leider", "Birra", "MED", 71, None, 26),
            ("Yimmi", "Chatarra", "MED", 81, "regateador", 34),
            ("Roberto", "Hinojo", "MED", 73, "regateador", 25),
            ("Carlos", "Vaca", "DEL", 83, "lider", 38),
            ("Jose", "Enamorado (Rapido)", "DEL", 78, "regateador", 25),
            ("Deiber", "Caido", "DEL", 75, "regateador", 25),
            ("Marco", "Perezoso", "DEL", 74, "rustico", 34),
            ("Titi", "Rodriguez", "DEL", 72, None, 28),
            ("Cariaco", "Gonzalez", "MED", 73, "regateador", 33)
        ]
    },
    "Deportivo Casi": {
        "ciudad": "Cali",
        "estrellas": 3.0,
        "estilo_dt": "flickismo",
        "balance": 8000000,
        "jugadores": [
            ("Alejo", "Rodriguez", "POR", 73, None, 22),
            ("Joaquin", "Papa", "POR", 68, None, 29),
            ("Pacho", "Mesa", "DEF", 73, "rustico", 35),
            ("Brayan", "Montañita", "DEF", 70, None, 22),
            ("Jonathan", "Mula", "DEF", 71, None, 30),
            ("Yulian", "Gomez (Tenue)", "DEF", 70, None, 26),
            ("Jose", "Caldito", "DEF", 69, None, 24),
            ("Onel", "Costas", "DEF", 67, None, 21),
            ("Alex", "Miedito", "MED", 74, "lider", 36),
            ("Kelvin", "Osito", "MED", 72, None, 31),
            ("Juanma", "Valiente", "MED", 70, None, 25),
            ("Javier", "Rey", "MED", 73, "regateador", 34),
            ("Fabian", "Castillo", "DEL", 73, "regateador", 32),
            ("Jarlan", "Barrigona", "MED", 73, "regateador", 28),
            ("Fredy", "Montañero", "DEL", 78, "lider", 37),
            ("Andrey", "Estupido", "DEL", 71, None, 26),
            ("Anderson", "Platita", "DEL", 73, "pulmon_de_hierro", 34),
            ("Gian", "Cabezón", "MED", 69, None, 20),
            ("Rafa", "Busto", "MED", 69, None, 23),
            ("Jaider", "Morado", "DEL", 67, None, 20)
        ]
    },
    "Independiente Casi Fue": {
        "ciudad": "Bogotá",
        "estrellas": 3.0,
        "estilo_dt": "haramball",
        "balance": 7500000,
        "jugadores": [
            ("Andres", "Marmolejo", "POR", 80, "lider", 34),
            ("Juan", "Espinilla", "POR", 69, None, 24),
            ("Facu", "Agua", "DEF", 74, "rustico", 30),
            ("Marcelo", "Sapo", "DEF", 74, "rustico", 29),
            ("David", "Piscina", "DEF", 71, None, 21),
            ("Dairon", "Mosquito", "DEF", 73, None, 33),
            ("Elvis", "Perlas", "DEF", 71, "pulmon_de_hierro", 36),
            ("Diego", "Hernia", "DEF", 70, None, 25),
            ("Daniel", "Torrez", "MED", 75, "lider", 36),
            ("Yilmar", "Vela", "MED", 73, "pulmon_de_hierro", 26),
            ("Jhojan", "Torito", "MED", 71, None, 21),
            ("Juan", "Zulu", "MED", 73, "pulmon_de_hierro", 31),
            ("Pacho", "Chavera", "MED", 74, "regateador", 26),
            ("Omar", "Albornos", "MED", 71, None, 29),
            ("Hugo", "Rodagol", "DEL", 81, "lider", 40),
            ("Agustin", "Rodri", "DEL", 73, "rustico", 27),
            ("Harold", "Mosquitos", "DEL", 74, "regateador", 29),
            ("Jown", "Cartona", "MED", 71, None, 29),
            ("William", "Huevo", "DEL", 68, None, 21),
            ("John", "Mela", "DEF", 69, None, 24)
        ]
    },
    "Deportes Llorima": {
        "ciudad": "Ibagué",
        "estrellas": 3.0,
        "estilo_dt": "flickismo",
        "balance": 9000000,
        "jugadores": [
            ("Neto", "Volador", "POR", 75, None, 33),
            ("Juan", "Chavera", "POR", 70, None, 31),
            ("Marlon", "Torre", "DEF", 74, "rustico", 30),
            ("Cesar", "Rayo", "DEF", 73, None, 24),
            ("Yhormar", "Tortuga", "DEF", 71, None, 29),
            ("Junior", "Herradura", "DEF", 74, "pulmon_de_hierro", 25),
            ("Jeison", "Angulito", "DEF", 70, None, 29),
            ("Anderson", "Angulo Muerto", "DEF", 70, None, 29),
            ("Cristian", "Truco", "MED", 73, "pulmon_de_hierro", 26),
            ("Juan", "Nieto", "MED", 74, "lider", 33),
            ("Yeison", "Guzman", "MED", 81, "regateador", 27),
            ("Brayan", "Rovin", "MED", 74, "pulmon_de_hierro", 27),
            ("Edu", "Manguito", "MED", 71, None, 28),
            ("Carlos", "Esparrago", "MED", 69, None, 25),
            ("Alex", "Castrado", "DEL", 73, None, 31),
            ("Jeison", "Loco", "DEL", 74, "regateador", 30),
            ("Tavo", "Ramirez", "DEL", 73, "rustico", 33),
            ("Brayan", "Pereza", "DEL", 73, "rustico", 24),
            ("Facu", "Hueso", "DEL", 71, None, 30),
            ("Yilson", "Rosas", "DEF", 69, None, 25)
        ]
    },
    "Once Faldas": {
        "ciudad": "Manizales",
        "estrellas": 2.5,
        "estilo_dt": "haramball",
        "balance": 6000000,
        "jugadores": [
            ("James", "Hoguera", "POR", 75, "lider", 32),
            ("Ezequiel", "Mastro", "POR", 69, None, 34),
            ("Sergio", "Palacio", "DEF", 73, "rustico", 20),
            ("Jeider", "Riquera", "DEF", 70, None, 33),
            ("Juan", "Cuesta", "DEF", 71, "pulmon_de_hierro", 27),
            ("Leyder", "Morado", "DEF", 69, None, 23),
            ("Yonatan", "Muro", "DEF", 70, None, 33),
            ("Stalin", "Valiente", "DEF", 68, None, 21),
            ("Ivan", "Rojizo", "MED", 73, "pulmon_de_hierro", 28),
            ("Mateo", "Garcita", "MED", 73, "pulmon_de_hierro", 27),
            ("Alejo", "Garcia", "MED", 71, "lider", 24),
            ("Esteban", "Beltrán", "MED", 70, None, 25),
            ("Alvaro", "Montañita", "MED", 69, None, 23),
            ("Roger", "Torre", "MED", 70, None, 34),
            ("Dayro", "Moreno", "DEL", 81, "lider", 40),
            ("Billy", "Arco", "DEL", 75, "regateador", 27),
            ("John", "Araujo", "DEL", 69, None, 23),
            ("Santi", "Mera", "DEL", 70, None, 24),
            ("David", "Lemos", "DEL", 70, None, 30),
            ("Lucho", "Palacio", "DEL", 69, None, 26)
        ]
    }
}

# v0.7: nombre corto (anti-solapamiento) y override de estilo (algunos equipos equilibrados).
NOMBRES_CORTOS = {
    "Narconal": "Narconal", "Pobres Vagos": "Pobres Vagos",
    "ABerica de Cali": "ABerica", "Junior daddy": "Junior",
    "Deportivo Casi": "Depor Casi", "Independiente Casi Fue": "Casi Fue",
    "Deportes Llorima": "Llorima", "Once Faldas": "Once Faldas",
}
ESTILO_OVERRIDE = {
    "Junior daddy": "anchelottismo",
    "Independiente Casi Fue": "anchelottismo",
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
            nombre="Liga BetPlay Colombia",
            tipo="betplay",
            equipos=equipos,
            num_jornadas=14
        )
    except Exception as e:
        logger.critical(f"Error crítico al construir Liga BetPlay: {e}. Retornando liga vacía.")
        # Retorno seguro para evitar que el juego se caiga por completo (resiliencia)
        return Liga("Liga BetPlay Fallback", "betplay", [], 14)
