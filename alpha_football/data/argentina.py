# -*- coding: utf-8 -*-
"""
Alpha Football v0.7 — DATOS DE LIGA ARGENTINA.

Este módulo construye y expone la Liga Argentina con 6 equipos de parodia
y sus jugadores reales humorísticos (OVR máximo 80).
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

# Plantillas de parodia para los clubes argentinos (20 jugadores base por equipo)
PLANTILLAS_PARODIA = {
    "Boca Grande": {
        "ciudad": "Buenos Aires",
        "estrellas": 4.3,
        "estilo_dt": "cruyffismo",
        "balance": 18000000,
        "jugadores": [
            ("Sergio", "Chiquito Sinmanos", "POR", 74, None, 37),
            ("Leandro", "Brey", "POR", 72, None, 21),
            ("Lucho", "Rayo Advincula", "DEF", 79, "pulmon_de_hierro", 34),
            ("Marcos", "Rojo Expulsado", "DEF", 76, "rustico", 34),
            ("Nico", "Cagadon Figal", "DEF", 74, "rustico", 30),
            ("Lautaro", "Blanco Facil", "DEF", 78, "pulmon_de_hierro", 25),
            ("Cristian", "Lema Rustico", "DEF", 76, "rustico", 34),
            ("Aaron", "Anselminio", "DEF", 77, None, 19),
            ("Juan", "Saraleguito", "DEF", 74, None, 21),
            ("Pecho", "Pol Fernandez", "MED", 74, None, 32),
            ("Cristian", "Medinita Humo", "MED", 80, "regateador", 22),
            ("Kevin", "Zenon Mago", "MED", 80, "regateador", 22),
            ("Tomas", "Belmonte", "MED", 74, "rustico", 26),
            ("Exequiel", "Zeballos Roto", "MED", 77, "regateador", 22),
            ("Ignacio", "Miramon", "MED", 73, None, 21),
            ("Edinson", "Matador Viejito", "DEL", 82, "lider", 37),
            ("Miguel", "Bestia Triste", "DEL", 81, "pulmon_de_hierro", 28),
            ("Brian", "Aguirre", "DEL", 75, "regateador", 21),
            ("Milton", "Gimenez", "DEL", 76, None, 27),
            ("Lucas", "Janson", "DEL", 71, None, 29)
        ]
    },
    "River Au": {
        "ciudad": "Buenos Aires",
        "estrellas": 4.4,
        "estilo_dt": "flickismo",
        "balance": 20000000,
        "jugadores": [
            ("Franco", "Armani Sinreflejos", "POR", 79, "lider", 37),
            ("Jeremias", "Ledesma", "POR", 76, None, 31),
            ("Paulo", "Diaz Pegador", "DEF", 80, "rustico", 29),
            ("Leandro", "Pirez Pifia", "DEF", 74, "rustico", 32),
            ("Milton", "Casquito Viejo", "DEF", 74, "lider", 36),
            ("Fabricio", "Bustos Roto", "DEF", 77, "pulmon_de_hierro", 28),
            ("Marcos", "Huevo Acuna", "DEF", 81, "rustico", 32),
            ("German", "Pezzella", "DEF", 80, "lider", 32),
            ("Enzo", "Diaz", "DEF", 75, None, 28),
            ("Rodrigo", "Aliendro Fantasma", "MED", 76, None, 33),
            ("Manu", "Lesionini", "MED", 76, "regateador", 31),
            ("Diablito", "Echeverri Vendido", "MED", 81, "regateador", 18),
            ("Franco", "Mastantuono", "MED", 80, "regateador", 16),
            ("Maxi", "Meza", "MED", 76, None, 31),
            ("Matias", "Kranevitter", "MED", 74, "rustico", 31),
            ("Santiago", "Simon", "MED", 75, "pulmon_de_hierro", 22),
            ("Miguel", "Borjita Colibri", "DEL", 83, "lider", 31),
            ("Facundo", "Colidio Frio", "DEL", 78, None, 24),
            ("Pablo", "Solari Sinmira", "DEL", 77, "regateador", 23),
            ("Adam", "Bareiro", "DEL", 76, None, 27)
        ]
    },
    "Corriendo": {
        "ciudad": "Avellaneda",
        "estrellas": 4.0,
        "estilo_dt": "haramball",
        "balance": 14000000,
        "jugadores": [
            ("Gabriel", "Arias Volador", "POR", 79, None, 36),
            ("Facundo", "Cambeses", "POR", 74, None, 27),
            ("Marco", "Di Cesare Lento", "DEF", 77, "rustico", 22),
            ("Santiago", "Quiros Pibe", "DEF", 72, None, 22),
            ("Facundo", "Mura Pasito", "DEF", 75, "pulmon_de_hierro", 25),
            ("Gabriel", "Rojas Cortas", "DEF", 75, "pulmon_de_hierro", 27),
            ("Agustin", "Garcia Basso", "DEF", 77, "rustico", 32),
            ("Nazareno", "Colombo", "DEF", 74, None, 25),
            ("Leonardo", "Sigali Viejo", "DEF", 71, "lider", 37),
            ("Bruno", "Zuculini Tronco", "MED", 73, "rustico", 31),
            ("Agustin", "Almendra Rancia", "MED", 77, "regateador", 24),
            ("Juanfer", "Quintero Panza", "MED", 82, "regateador", 31),
            ("Santiago", "Sosa Pulmon", "MED", 78, "pulmon_de_hierro", 25),
            ("Baltasar", "Rodriguez", "MED", 75, None, 21),
            ("Juan", "Nardoni", "MED", 77, "pulmon_de_hierro", 21),
            ("Adrian", "Maravilla Martinez", "DEL", 82, "lider", 31),
            ("Roger", "Martinez Frio", "DEL", 78, None, 30),
            ("Johan", "Carbonero Humo", "DEL", 77, "regateador", 24),
            ("Maximiliano", "Salas", "DEL", 75, None, 26),
            ("Luciano", "Vietto", "DEL", 74, None, 30)
        ]
    },
    "Desindependiente": {
        "ciudad": "Avellaneda",
        "estrellas": 3.8,
        "estilo_dt": "cruyffismo",
        "balance": 10000000,
        "jugadores": [
            ("Rodrigo", "Rey Atajador", "POR", 78, None, 33),
            ("Diego", "Segovia", "POR", 68, None, 24),
            ("Joaquin", "Laso Rustico", "DEF", 73, "rustico", 33),
            ("Federico", "Fedelito Vera", "DEF", 75, "pulmon_de_hierro", 26),
            ("Damian", "Perez Abuelo", "DEF", 71, "lider", 35),
            ("Felipe", "Lomita Aguilar", "DEF", 74, "rustico", 31),
            ("Kevin", "Lomonaco", "DEF", 75, "rustico", 22),
            ("Adrian", "Sporle", "DEF", 73, None, 28),
            ("Ivan", "Marcone Lento", "MED", 75, "lider", 34),
            ("Lucas", "Gonzalez Saltarin", "MED", 74, None, 24),
            ("Federico", "Mancuello Viejo", "MED", 74, "lider", 35),
            ("David", "Martinez", "MED", 72, None, 20),
            ("Felipe", "Loyola", "MED", 77, "pulmon_de_hierro", 23),
            ("Alex", "Promesa Luna", "MED", 74, "regateador", 19),
            ("Jhonny", "Quinonez", "MED", 72, None, 25),
            ("Gabriel", "Avalos Poste", "DEL", 78, None, 33),
            ("Santiago", "Hidalgo Pibe", "DEL", 71, None, 19),
            ("Alexis", "Canelo", "DEL", 74, None, 31),
            ("Matias", "Gimenez Roto", "DEL", 75, None, 25),
            ("Maestro", "Puch", "DEL", 71, None, 20)
        ]
    },
    "San Lorenzont": {
        "ciudad": "Buenos Aires",
        "estrellas": 3.7,
        "estilo_dt": "haramball",
        "balance": 9000000,
        "jugadores": [
            ("Gaston", "Gomez Chila", "POR", 74, None, 28),
            ("Facundo", "Altamirano", "POR", 73, None, 28),
            ("Jhohan", "Romana Muro", "DEF", 77, "rustico", 25),
            ("Gaston", "Campi Tronco", "DEF", 74, "rustico", 33),
            ("Gonzalo", "Lujan Joven", "DEF", 74, None, 23),
            ("Malcom", "Braida Rapido", "DEF", 76, "pulmon_de_hierro", 27),
            ("Nahuel", "Arias", "DEF", 72, None, 19),
            ("Elias", "Baez", "DEF", 71, None, 19),
            ("Eric", "Remedi Tapon", "MED", 75, "rustico", 29),
            ("Elian", "Irala", "MED", 74, None, 20),
            ("Iker", "Muniain Navarro", "MED", 80, "regateador", 31),
            ("Nahuel", "Barrios Perrito", "MED", 75, "regateador", 26),
            ("Sebastian", "Blanco Abuelo", "MED", 73, None, 36),
            ("Ivan", "Tapia", "MED", 71, None, 25),
            ("Ezequiel", "Cerutti Pocho", "DEL", 73, None, 32),
            ("Alexis", "Cuello", "DEL", 75, "regateador", 24),
            ("Andres", "Vombergar", "DEL", 74, None, 29),
            ("Matias", "Reali", "DEL", 75, "regateador", 26),
            ("Francisco", "Fydriszewski", "DEL", 74, None, 31),
            ("Nahuel", "Bustos", "DEL", 75, None, 25)
        ]
    },
    "Talleres de tallarines": {
        "ciudad": "Córdoba",
        "estrellas": 4.1,
        "estilo_dt": "anchelottismo",
        "balance": 12000000,
        "jugadores": [
            ("Guido", "Herrera Salvador", "POR", 80, "lider", 32),
            ("Lautaro", "Morales", "POR", 72, None, 24),
            ("Gaston", "Benavidez", "DEF", 77, "pulmon_de_hierro", 28),
            ("Matias", "Catalan Muro", "DEF", 77, "rustico", 31),
            ("Juan", "Carlos Portillo", "DEF", 75, "rustico", 24),
            ("Miguel", "Navarro", "DEF", 75, "pulmon_de_hierro", 25),
            ("Lucas", "Suarez", "DEF", 73, None, 29),
            ("Blas", "Riveros", "DEF", 74, None, 26),
            ("Ulises", "Ortegoza", "MED", 77, "pulmon_de_hierro", 27),
            ("Marcos", "Portillo", "MED", 74, None, 23),
            ("Ruben", "Botta Mago", "MED", 81, "regateador", 34),
            ("Matias", "Galarza", "MED", 74, None, 22),
            ("Juan", "Camilo Portilla", "MED", 77, "pulmon_de_hierro", 25),
            ("Bruno", "Barticciotto", "MED", 75, None, 23),
            ("Sebastian", "Palacios", "DEL", 75, "regateador", 32),
            ("Ramon", "Sosa Vendido", "DEL", 82, "regateador", 24),
            ("Valentin", "Depietri", "DEL", 73, None, 23),
            ("Alejandro", "Martinez", "DEL", 75, None, 26),
            ("Federico", "Girotti", "DEL", 76, None, 25),
            ("Cristian", "Tarragona", "DEL", 74, None, 33)
        ]
    }
}

NOMBRES_CORTOS = {
    "Boca Grande": "Boca Grande", "River Au": "River Au",
    "Corriendo": "Corriendo", "Desindependiente": "Independiente",
    "San Lorenzont": "Lorenzont", "Talleres de tallarines": "Talleres",
}
ESTILO_OVERRIDE = {
    "Boca Grande": "anchelottismo",
    "River Au": "flickismo",
    "Corriendo": "haramball"
}

def get_liga() -> Liga:
    """
    Construye y devuelve el objeto Liga Argentina
    con plantillas de parodia completamente pobladas de 20 jugadores.
    """
    try:
        equipos = []
        id_counter = 300
        
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
            nombre="Liga Profesional Argentina",
            tipo="argentina",
            equipos=equipos,
            num_jornadas=10
        )
    except Exception as e:
        logger.critical(f"Error crítico al construir Liga Argentina: {e}. Retornando fallback.")
        return Liga("Liga Argentina Fallback", "argentina", [], 10)
