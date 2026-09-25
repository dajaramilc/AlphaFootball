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
            ("Edinson", "Matador Viejito", "DEL", 81, "lider", 37),
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
            ("Miguel", "Borjita Colibri", "DEL", 81, "lider", 31),
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
            ("Juanfer", "Quintero Panza", "MED", 81, "regateador", 31),
            ("Santiago", "Sosa Pulmon", "MED", 78, "pulmon_de_hierro", 25),
            ("Baltasar", "Rodriguez", "MED", 75, None, 21),
            ("Juan", "Nardoni", "MED", 77, "pulmon_de_hierro", 21),
            ("Adrian", "Maravilla Martinez", "DEL", 81, "lider", 31),
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
            ("Ramon", "Sosa Vendido", "DEL", 81, "regateador", 24),
            ("Valentin", "Depietri", "DEL", 73, None, 23),
            ("Alejandro", "Martinez", "DEL", 75, None, 26),
            ("Federico", "Girotti", "DEL", 76, None, 25),
            ("Cristian", "Tarragona", "DEL", 74, None, 33)
        ]
    },
    # ── v3.7.0: clubes nuevos (Liga Profesional 2025, liga de 12) ──
    "Pincharratas de La Plata": {
        "ciudad": "La Plata",
        "estrellas": 3.9,
        "estilo_dt": "choloismo",
        "balance": 11000000,
        "jugadores": [
            ("Fernando", "Muslerazo", "POR", 77, "lider", 39),
            ("Matias", "Mansillita", "POR", 71, None, 28),
            ("Santiago", "Nuñez Nube", "DEF", 74, None, 23),
            ("Leandro", "Gonzalez Pirex", "DEF", 74, "rustico", 33),
            ("Eric", "Meza Mesita", "DEF", 73, "pulmon_de_hierro", 26),
            ("Gaston", "Benedetti Bendito", "DEF", 72, None, 24),
            ("Roman", "Gomez Goma", "DEF", 71, None, 21),
            ("Facundo", "Rodriguez Rudo", "DEF", 72, "rustico", 25),
            ("Tomas", "Palacios Palacete", "DEF", 72, None, 22),
            ("Santiago", "Ascacibar Pitbull", "MED", 77, "rustico", 28),
            ("Alexis", "Manyoma Mañoso", "MED", 74, "regateador", 29),
            ("Mikel", "Amondarain Vasco", "MED", 72, None, 23),
            ("Gabriel", "Neves Nieve", "MED", 72, None, 28),
            ("Ezequiel", "Piovi Pioja", "MED", 72, None, 33),
            ("Tiago", "Palacios Principe", "MED", 73, "regateador", 24),
            ("Jose", "Sosa Principito", "MED", 74, "lider", 40),
            ("Edwuin", "Cetre Cetro", "DEL", 77, "regateador", 27),
            ("Guido", "Carrillazo", "DEL", 75, "lider", 34),
            ("Lucas", "Alario Alarma", "DEL", 74, None, 32),
            ("Fabricio", "Perez Pereza", "DEL", 70, None, 20),
        ]
    },
    "Vélez Sarsfall": {
        "ciudad": "Buenos Aires",
        "estrellas": 3.8,
        "estilo_dt": "cruyffismo",
        "balance": 10000000,
        "jugadores": [
            ("Tomas", "Marchiori Martillo", "POR", 76, None, 29),
            ("Alvaro", "Montero Montaña", "POR", 74, "lider", 30),
            ("Emanuel", "Mammana Mañana", "DEF", 75, "rustico", 29),
            ("Jano", "Gordon Gordo", "DEF", 72, None, 21),
            ("Joaquin", "Garcia Gancho", "DEF", 73, "pulmon_de_hierro", 24),
            ("Elias", "Gomez Goleta", "DEF", 72, None, 30),
            ("Damian", "Fernandez Fideo", "DEF", 72, None, 24),
            ("Aaron", "Quiros Quirofano", "DEF", 70, None, 20),
            ("Lautaro", "Garzon Garza", "DEF", 70, None, 20),
            ("Agustin", "Bouzat Buzo", "MED", 74, "pulmon_de_hierro", 31),
            ("Christian", "Ordoñez Ordeño", "MED", 72, None, 21),
            ("Rodrigo", "Aliendro Aliento", "MED", 74, None, 34),
            ("Claudio", "Baeza Bajo", "MED", 72, "rustico", 31),
            ("Tomas", "Galvan Galope", "MED", 72, None, 24),
            ("Manuel", "Lanzini Lanza", "MED", 76, "regateador", 32),
            ("Diego", "Valdes Valde", "MED", 74, "regateador", 31),
            ("Braian", "Romero Romerito", "DEL", 76, "lider", 34),
            ("Michael", "Santos Sanito", "DEL", 73, None, 32),
            ("Imanol", "Machuca Machaca", "DEL", 73, "regateador", 25),
            ("Maher", "Carrizo Carrusel", "DEL", 72, "regateador", 19),
            ("Matias", "Pellegrini Peregrino", "DEL", 71, None, 25),
        ]
    },
    "Rosario Canalla": {
        "ciudad": "Rosario",
        "estrellas": 3.8,
        "estilo_dt": "kloppismo",
        "balance": 10000000,
        "jugadores": [
            ("Jorge", "Fatura Broun", "POR", 76, "lider", 39),
            ("Axel", "Werner Suplente", "POR", 69, None, 29),
            ("Carlos", "Quintana Quinta", "DEF", 74, "rustico", 37),
            ("Facundo", "Mallo Malla", "DEF", 73, None, 30),
            ("Juan", "Cruz Komarca", "DEF", 72, None, 29),
            ("Agustin", "Sandez Sandia", "DEF", 73, "pulmon_de_hierro", 24),
            ("Emanuel", "Coronel Coronado", "DEF", 72, None, 28),
            ("Ignacio", "Ovando Ovalo", "DEF", 70, None, 23),
            ("Gaston", "Avila Avioneta", "DEF", 70, None, 23),
            ("Angel", "Di Maria Fideo", "MED", 81, "regateador", 37),
            ("Ignacio", "Malcorra Malcorre", "MED", 76, "lider", 37),
            ("Franco", "Ibarra Barra", "MED", 73, "rustico", 24),
            ("Jaminton", "Campaz Campeon", "MED", 75, "regateador", 25),
            ("Julian", "Fernandez Fernet", "MED", 72, None, 30),
            ("Tomas", "OConnor Irlandes", "MED", 71, None, 29),
            ("Kevin", "Ortiz Ortiga", "MED", 72, None, 28),
            ("Enzo", "Copetti Copete", "DEL", 74, None, 29),
            ("Alejo", "Veliz Velero", "DEL", 72, None, 22),
            ("Maximiliano", "Lovera Lluvia", "DEL", 72, "regateador", 26),
            ("Enzo", "Gimenez Gemelo", "DEL", 68, None, 20),
            ("Lautaro", "Giaccone Giacomo", "DEL", 70, None, 25),
        ]
    },
    "Lanús Granate Oxidado": {
        "ciudad": "Lanús",
        "estrellas": 3.7,
        "estilo_dt": "artetismo",
        "balance": 9000000,
        "jugadores": [
            ("Nahuel", "Losa Rota", "POR", 76, "lider", 27),
            ("Franco", "Petroleo", "POR", 68, None, 27),
            ("Carlos", "Izquierdazo", "DEF", 75, "lider", 36),
            ("Jose", "Canale Canal", "DEF", 72, None, 29),
            ("Armando", "Mendez Mendigo", "DEF", 72, None, 25),
            ("Sasha", "Marcich Marcha", "DEF", 71, "pulmon_de_hierro", 22),
            ("Gonzalo", "Perez Perezoso", "DEF", 70, None, 26),
            ("Nicolas", "Morgantini Morgan", "DEF", 70, None, 31),
            ("Ronaldo", "De Jesus Milagro", "DEF", 70, None, 26),
            ("Agustin", "Cardozo Cardo", "MED", 73, "rustico", 28),
            ("Felipe", "Peña Biafore Peñasco", "MED", 73, None, 24),
            ("Marcelino", "Moreno Morocho", "MED", 76, "regateador", 30),
            ("Ramiro", "Carrera Corrida", "MED", 72, None, 32),
            ("Raul", "Loaiza Loza", "MED", 71, "rustico", 30),
            ("Agustin", "Medina Medialuna", "MED", 70, None, 26),
            ("Eduardo", "Toto Salvio", "DEL", 75, "regateador", 34),
            ("Walter", "Bou Bu", "DEL", 76, "lider", 31),
            ("Rodrigo", "Castillo Castle", "DEL", 73, None, 26),
            ("Lautaro", "Laucha Acosta", "DEL", 73, "regateador", 37),
            ("Dylan", "Aquino Acuario", "DEL", 71, "regateador", 21),
            ("Franco", "Watson Sherlock", "DEL", 70, None, 20),
        ]
    },
    "Argentinos Juniorsitos": {
        "ciudad": "Buenos Aires",
        "estrellas": 3.4,
        "estilo_dt": "flickismo",
        "balance": 7000000,
        "jugadores": [
            ("Diego", "Rodriguez Ruso", "POR", 73, None, 36),
            ("Gonzalo", "Siri Siri", "POR", 68, None, 36),
            ("Francisco", "Alvarez Alvaro", "DEF", 72, None, 25),
            ("Erik", "Godoy Goya", "DEF", 72, "rustico", 31),
            ("Sebastian", "Prieto Prisa", "DEF", 71, None, 32),
            ("Roman", "Vega Vegano", "DEF", 70, None, 21),
            ("Leandro", "Lozano Lozana", "DEF", 70, None, 30),
            ("Kevin", "Coronel Corona", "DEF", 71, None, 25),
            ("Mateo", "Antoni Antonio", "DEF", 69, None, 20),
            ("Alan", "Lescano Lesionado", "MED", 76, "regateador", 23),
            ("Hernan", "Lopez Muñeco", "MED", 74, None, 25),
            ("Nicolas", "Oroz Oro", "MED", 73, None, 31),
            ("Gonzalo", "Maroni Marron", "MED", 73, "regateador", 26),
            ("Franco", "Moyano Moyo", "MED", 71, "rustico", 27),
            ("Jose", "Herrera Herrero", "MED", 71, None, 23),
            ("Federico", "Fattori Fatiga", "MED", 71, "pulmon_de_hierro", 32),
            ("Lucas", "Gonzalez Pibito", "MED", 67, None, 18),
            ("Tomas", "Molina Molino", "DEL", 75, "lider", 30),
            ("Diego", "Porcel Porcelana", "DEL", 72, "regateador", 21),
            ("Emiliano", "Viveros Vivero", "DEL", 71, "regateador", 23),
            ("Alan", "Rodriguez Rodilla", "DEL", 70, None, 25),
        ]
    },
    "Huracán Brisa": {
        "ciudad": "Buenos Aires",
        "estrellas": 3.3,
        "estilo_dt": "haramball",
        "balance": 6500000,
        "jugadores": [
            ("Hernan", "Galindez Galan", "POR", 76, "lider", 38),
            ("Sebastian", "Meza Mesero", "POR", 68, None, 25),
            ("Hernan", "De la Fuente Fontana", "DEF", 72, None, 28),
            ("Cesar", "Ibañez Iban", "DEF", 72, "pulmon_de_hierro", 26),
            ("Fernando", "Tobio Tobogan", "DEF", 73, "rustico", 35),
            ("Marco", "Pellegrino Pelegrin", "DEF", 72, None, 23),
            ("Lucas", "Carrizo Carrizal", "DEF", 72, "rustico", 27),
            ("Nehuen", "Paz Tranquila", "DEF", 71, None, 32),
            ("Guillermo", "Soto Sotana", "DEF", 70, None, 31),
            ("Emmanuel", "Ojeda Ojera", "MED", 73, "rustico", 28),
            ("Leonardo", "Gil Gilito", "MED", 73, None, 34),
            ("Rodrigo", "Echeverria Echenique", "MED", 74, "pulmon_de_hierro", 29),
            ("Matko", "Miljevic Milagro", "MED", 72, "regateador", 24),
            ("Agustin", "Urzi Urgente", "MED", 71, "regateador", 25),
            ("Emanuel", "Beltran Beltranito", "MED", 70, None, 26),
            ("Facundo", "Waller Walla", "MED", 69, None, 27),
            ("Eric", "Ramirez Ramillete", "DEL", 73, None, 26),
            ("Walter", "Mazzantti Mazapan", "DEL", 75, "regateador", 29),
            ("Jordy", "Caicedo Cacao", "DEL", 72, None, 27),
            ("Leandro", "Garate Garita", "DEL", 70, None, 32),
            ("Ignacio", "Pussetto Pusheta", "DEL", 70, None, 29),
        ]
    },
}

# v3.7.0: alias con el nombre común de los datos de liga (tests y merge).
DATOS_ARGENTINA = PLANTILLAS_PARODIA

NOMBRES_CORTOS = {
    "Boca Grande": "Boca Grande", "River Au": "River Au",
    "Corriendo": "Corriendo", "Desindependiente": "Independiente",
    "San Lorenzont": "Lorenzont", "Talleres de tallarines": "Talleres",
    # v3.7.0: clubes nuevos
    "Pincharratas de La Plata": "Pincha", "Vélez Sarsfall": "Vélez", "Rosario Canalla": "Central",
    "Lanús Granate Oxidado": "Lanús", "Argentinos Juniorsitos": "Argentinos", "Huracán Brisa": "Huracán",
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
        id_counter = 3000  # v3.7.0: rango propio (12 clubes)
        
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
            num_jornadas=max(2, 2 * (len(equipos) - 1))  # v3.7.0: 12 clubes -> 22
        )
    except Exception as e:
        logger.critical(f"Error crítico al construir Liga Argentina: {e}. Retornando fallback.")
        return Liga("Liga Argentina Fallback", "argentina", [], 10)
