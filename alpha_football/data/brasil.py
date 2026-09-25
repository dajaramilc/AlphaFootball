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
            ("Rossi", "Rossini", "POR", 79, None, 28),
            ("Matheus", "Cunhazo", "POR", 72, None, 23),
            ("David", "Lloron", "DEF", 74, "lider", 37),
            ("Leo", "Pereira Roto", "DEF", 76, "rustico", 28),
            ("Guillermo", "Varela Lenta", "DEF", 74, None, 31),
            ("Ayrton", "Lucas Veloz", "DEF", 77, "pulmon_de_hierro", 26),
            ("Fabricio", "Bruno", "DEF", 78, "rustico", 28),
            ("Matias", "Vinazo", "DEF", 75, None, 26),
            ("Wesley", "Regateador", "DEF", 73, "pulmon_de_hierro", 20),
            ("Erick", "Pulgar Fuerte", "MED", 76, "rustico", 30),
            ("Nicolas", "De Arrastra", "MED", 81, "regateador", 30),
            ("Gerson", "Coringa", "MED", 81, "lider", 27),
            ("Nicolas", "De la Cruzazo", "MED", 81, "pulmon_de_hierro", 27),
            ("Allan", "Lento", "MED", 74, None, 27),
            ("Evertton", "Araujazo", "MED", 72, None, 21),
            ("Alcaraz", "Millonario", "MED", 76, None, 21),
            ("Everton", "Cebollon", "DEL", 77, "regateador", 28),
            ("Luiz", "Araujo Falso", "DEL", 76, "regateador", 28),
            ("Pedro", "Pedrogol", "DEL", 81, "lider", 26),
            ("Gabigol", "Gabilento", "DEL", 78, "lider", 27)
        ]
    },
    "Palmerinha": {
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
            ("Raphael", "Vejiga", "MED", 81, "regateador", 29),
            ("Ze", "Rafaelin", "MED", 76, "rustico", 31),
            ("Richard", "Rios Cafe", "MED", 78, "regateador", 24),
            ("Mauricio", "Joven", "MED", 77, None, 23),
            ("Gabriel", "Menino", "MED", 75, None, 23),
            ("Rony", "Ronito Volador", "DEL", 76, "pulmon_de_hierro", 29),
            ("Estevao", "Estevito", "DEL", 81, "regateador", 17),
            ("Felipe", "Anderson Roto", "DEL", 78, "regateador", 31),
            ("Flaco", "Lopez", "DEL", 81, None, 23),
            ("Lazaro", "Promesa", "DEL", 74, None, 22)
        ]
    },
    "Botaagua": {
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
            ("Thiago", "Almada", "MED", 81, "regateador", 23),
            ("Gregore", "Volante", "MED", 76, "rustico", 30),
            ("Allan", "Volantazo", "MED", 74, None, 27),
            ("Jefferson", "Savarino", "MED", 78, "regateador", 27),
            ("Tche Tche", "Corredor", "MED", 74, "pulmon_de_hierro", 31),
            ("Luiz", "Enrique Lento", "DEL", 81, "regateador", 23),
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
            ("Lucas", "Muera", "DEL", 81, "regateador", 31),
            ("Jonathan", "Callao", "DEL", 79, "lider", 30),
            ("Luciano", "Lucianito", "DEL", 77, "lider", 31),
            ("Ferreirinha", "Ferro", "DEL", 76, "regateador", 26),
            ("Andre", "Silva", "DEL", 74, None, 27)
        ]
    },
    "Flumando": {
        "ciudad": "Río de Janeiro",
        "estrellas": 4.0,
        "estilo_dt": "anchelottismo",
        "balance": 15000000,
        "jugadores": [
            ("Fabio", "Abuelo", "POR", 76, "lider", 41),
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
            ("Jhon", "Arias Mago", "MED", 81, "regateador", 26),
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
    "Gremiont": {
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
    },
    # ── v3.7.0: clubes nuevos (Brasileirão 2025, liga de 12) ──
    "Corinchados": {
        "ciudad": "São Paulo",
        "estrellas": 4.0,
        "estilo_dt": "haramball",
        "balance": 15000000,
        "jugadores": [
            ("Hugo", "Sousa Manos", "POR", 78, "lider", 26),
            ("Felipe", "Largo", "POR", 68, None, 21),
            ("Felix", "Torres Gemelas", "DEF", 76, "rustico", 28),
            ("Andre", "Ramalhazo", "DEF", 75, None, 33),
            ("Gustavo", "Henrique Lento", "DEF", 73, None, 32),
            ("Caca", "Zaguero", "DEF", 72, "rustico", 26),
            ("Fabrizio", "Angileri Loco", "DEF", 73, "pulmon_de_hierro", 31),
            ("Matheus", "Bidu Bidu", "DEF", 72, None, 26),
            ("Matheuzinho", "Carrilero", "DEF", 75, "pulmon_de_hierro", 25),
            ("Raniele", "Barredor", "MED", 75, "rustico", 29),
            ("Jose", "Martinez Tanque", "MED", 75, "rustico", 31),
            ("Breno", "Bidonzito", "MED", 74, None, 20),
            ("Andre", "Carrillo Picante", "MED", 76, "regateador", 34),
            ("Rodrigo", "Garrote", "MED", 78, "regateador", 27),
            ("Maycon", "Mayconazo", "MED", 74, None, 28),
            ("Charles", "Charlatan", "MED", 71, None, 29),
            ("Memphis", "Depaycito", "DEL", 81, "regateador", 31),
            ("Yuri", "Alberto Gol", "DEL", 78, "lider", 24),
            ("Angel", "Romero Viejo", "DEL", 75, None, 33),
            ("Talles", "Magno Chico", "DEL", 73, "regateador", 23),
            ("Hector", "Hernandez Poste", "DEL", 71, None, 30),
            ("Gui", "Negao Joven", "DEL", 68, None, 19),
        ]
    },
    "Colorado Desteñido": {
        "ciudad": "Porto Alegre",
        "estrellas": 3.8,
        "estilo_dt": "kloppismo",
        "balance": 12000000,
        "jugadores": [
            ("Sergio", "Rochet Cohete", "POR", 77, "lider", 32),
            ("Anthoni", "Suplentinho", "POR", 67, None, 23),
            ("Vitao", "Muralla Roja", "DEF", 75, "rustico", 25),
            ("Clayton", "Sampaio Lento", "DEF", 71, None, 25),
            ("Agustin", "Rogel Rudo", "DEF", 74, "rustico", 27),
            ("Alexandro", "Bernabeicito", "DEF", 75, "pulmon_de_hierro", 25),
            ("Braian", "Aguirre Carrilero", "DEF", 73, None, 25),
            ("Victor", "Gabriel Pibe", "DEF", 70, None, 19),
            ("Kaique", "Rochita", "DEF", 70, None, 24),
            ("Alan", "Patrick Estrella", "MED", 78, "lider", 34),
            ("Thiago", "Maia Maya", "MED", 74, "rustico", 28),
            ("Fernando", "Veterano", "MED", 71, None, 37),
            ("Bruno", "Henrique Colorado", "MED", 73, None, 35),
            ("Bruno", "Tabata Tabla", "MED", 73, "regateador", 28),
            ("Oscar", "Romero Paraguayo", "MED", 73, None, 33),
            ("Gustavo", "Prado Verde", "MED", 70, None, 20),
            ("Enner", "Valencia Naranja", "DEL", 77, "lider", 35),
            ("Rafael", "Borre Borroso", "DEL", 77, "pulmon_de_hierro", 29),
            ("Vitinho", "Colorado Fugaz", "DEL", 74, "regateador", 31),
            ("Johan", "Carbonero Carbon", "DEL", 73, "regateador", 25),
            ("Ricardo", "Mathias Pibe", "DEL", 68, None, 20),
            ("Lucca", "Drummondzinho", "DEL", 68, None, 19),
        ]
    },
    "Galo Cansado": {
        "ciudad": "Belo Horizonte",
        "estrellas": 4.0,
        "estilo_dt": "choloismo",
        "balance": 16000000,
        "jugadores": [
            ("Everson", "Manos de Galo", "POR", 76, "lider", 35),
            ("Gabriel", "Delfin Volador", "POR", 70, None, 24),
            ("Lyanco", "Lyancazo", "DEF", 76, "rustico", 28),
            ("Junior", "Alonso Muro", "DEF", 76, "lider", 32),
            ("Natanael", "Lateralzinho", "DEF", 72, None, 23),
            ("Guilherme", "Arana Araña", "DEF", 78, "pulmon_de_hierro", 28),
            ("Renzo", "Saravia Sarasa", "DEF", 72, None, 32),
            ("Ivan", "Roman Imperio", "DEF", 71, None, 22),
            ("Vitor", "Hugo Bravo", "DEF", 71, "rustico", 34),
            ("Alan", "Franco Tirador", "MED", 75, "rustico", 26),
            ("Gustavo", "Scarpa Zapato", "MED", 77, "regateador", 31),
            ("Fausto", "Vera Verita", "MED", 74, None, 25),
            ("Igor", "Gomes Goma", "MED", 72, None, 26),
            ("Bernard", "Bernardito", "MED", 74, "regateador", 32),
            ("Patrick", "de Paula Pausa", "MED", 71, None, 25),
            ("Hulk", "Increible Viejo", "DEL", 80, "lider", 39),
            ("Dudu", "Pataleta", "DEL", 76, "regateador", 33),
            ("Tomas", "Cuello Largo", "DEL", 74, "regateador", 25),
            ("Biel", "Bielzinho", "DEL", 71, None, 24),
            ("Cadu", "Cadubra", "DEL", 68, None, 19),
            ("Junior", "Santos Goleador", "DEL", 71, None, 30),
        ]
    },
    "Cruzeiro Endeudado": {
        "ciudad": "Belo Horizonte",
        "estrellas": 3.9,
        "estilo_dt": "artetismo",
        "balance": 14000000,
        "jugadores": [
            ("Cassio", "Gigante Abuelo", "POR", 77, "lider", 38),
            ("Leo", "Aragon Reserva", "POR", 69, None, 30),
            ("Jonathan", "Jesus Salvador", "DEF", 74, "rustico", 26),
            ("Lucas", "Villalba Muro", "DEF", 74, None, 31),
            ("William", "Lateral Eterno", "DEF", 74, "pulmon_de_hierro", 30),
            ("Kaiki", "Kaikazo", "DEF", 72, None, 22),
            ("Fagner", "Fagnerzao", "DEF", 72, "lider", 36),
            ("Marlon", "Marlonzinho", "DEF", 70, None, 28),
            ("Joao", "Marcelo Muro", "DEF", 71, None, 24),
            ("Lucas", "Romero Pampa", "MED", 76, "lider", 31),
            ("Lucas", "Silva Lenta", "MED", 72, None, 32),
            ("Christian", "Cristiano Falso", "MED", 74, "pulmon_de_hierro", 24),
            ("Matheus", "Henrique Raposa", "MED", 75, None, 27),
            ("Matheus", "Pereira Magia", "MED", 80, "regateador", 29),
            ("Eduardo", "Eduzinho", "MED", 72, None, 35),
            ("Walace", "Tractor", "MED", 73, "rustico", 30),
            ("Murilo", "Rhikman Pibe", "MED", 66, None, 18),
            ("Kaio", "Jorge Goleador", "DEL", 79, "lider", 23),
            ("Wanderson", "Zurdito", "DEL", 73, "regateador", 30),
            ("Lautaro", "Diaz Soleado", "DEL", 73, None, 27),
            ("Marquinhos", "Marquitos", "DEL", 71, "regateador", 26),
            ("Luis", "Sinisterra Diestro", "DEL", 74, "regateador", 26),
        ]
    },
    "Bahía Citizen": {
        "ciudad": "Salvador",
        "estrellas": 3.7,
        "estilo_dt": "cruyffismo",
        "balance": 13000000,
        "jugadores": [
            ("Marcos", "Felipe Parador", "POR", 75, "lider", 29),
            ("Danilo", "Fernandes Viejo", "POR", 68, None, 37),
            ("Gilberto", "Lateral Citizen", "DEF", 73, None, 32),
            ("Santiago", "Arias Lesionado", "DEF", 74, "pulmon_de_hierro", 33),
            ("David", "Duarte Duro", "DEF", 72, "rustico", 30),
            ("Kanu", "Kanuto", "DEF", 72, None, 28),
            ("Gabriel", "Xavier Profesor", "DEF", 72, None, 27),
            ("Luciano", "Juba Zurda", "DEF", 76, "regateador", 25),
            ("Santiago", "Ramos Mingo", "DEF", 71, None, 23),
            ("Jean", "Lucas Motor", "MED", 76, "pulmon_de_hierro", 27),
            ("Caio", "Alexandre Magno", "MED", 75, None, 26),
            ("Everton", "Ribeiro Eterno", "MED", 77, "lider", 36),
            ("Rodrigo", "Nestor Nesquik", "MED", 74, "regateador", 25),
            ("Cauly", "Caulyflor", "MED", 76, "regateador", 30),
            ("Nicolas", "Acevedo Aceite", "MED", 72, "rustico", 26),
            ("Michel", "Araujo Charrua", "MED", 71, None, 28),
            ("Everaldo", "Cabezazo", "DEL", 72, None, 34),
            ("Willian", "Jose Torre", "DEL", 74, None, 34),
            ("Luciano", "Rodriguez Lucho", "DEL", 74, None, 22),
            ("Ademir", "Rayo", "DEL", 73, "regateador", 30),
            ("Erick", "Pulga Saltarina", "DEL", 73, "regateador", 24),
        ]
    },
    "Vasco da Goma": {
        "ciudad": "Río de Janeiro",
        "estrellas": 3.6,
        "estilo_dt": "choloismo",
        "balance": 11000000,
        "jugadores": [
            ("Leo", "Jardin Botanico", "POR", 76, "lider", 30),
            ("Daniel", "Fusible", "POR", 67, None, 28),
            ("Paulo", "Henrique Puerto", "DEF", 72, None, 28),
            ("Lucas", "Piton Piton", "DEF", 74, "pulmon_de_hierro", 24),
            ("Mauricio", "Lemos Lento", "DEF", 72, "rustico", 29),
            ("Joao", "Victor Victoria", "DEF", 72, None, 27),
            ("Lucas", "Freitas Frito", "DEF", 70, None, 19),
            ("Robert", "Renteria Renta", "DEF", 71, None, 22),
            ("Puma", "Rodriguez Felino", "DEF", 70, None, 26),
            ("Philippe", "Coutinho Regreso", "MED", 79, "regateador", 33),
            ("Hugo", "Moura Mora", "MED", 72, None, 27),
            ("Tche", "Tche Tche", "MED", 73, "pulmon_de_hierro", 32),
            ("Jair", "Jairzinho Vasco", "MED", 71, None, 30),
            ("Mateus", "Carvalho Carbon", "MED", 71, None, 23),
            ("Nuno", "Moreira Portugues", "MED", 73, "regateador", 26),
            ("Dimitri", "Payet Jubilado", "MED", 76, "regateador", 38),
            ("Pablo", "Vegetariano", "DEL", 78, "lider", 36),
            ("Rayan", "Rayito", "DEL", 74, "regateador", 19),
            ("David", "Correa Veloz", "DEL", 73, "regateador", 30),
            ("Andres", "Gomez Lanzado", "DEL", 71, None, 22),
            ("Adson", "Atropellador", "DEL", 72, None, 25),
            ("Loide", "Augusto Cometa", "DEL", 70, None, 25),
        ]
    },
}

# v3.7.0: alias con el nombre común de los datos de liga (tests y merge).
DATOS_BRASIL = PLANTILLAS_PARODIA

NOMBRES_CORTOS = {
    "Flamenguito": "Flamenguito", "Palmerinha": "Palmeiras",
    "Botaagua": "Botafogo", "Don Pablo": "Don Pablo",
    "Flumando": "Flumando", "Gremiont": "Gremio",
    # v3.7.0: clubes nuevos
    "Corinchados": "Corinchados", "Colorado Desteñido": "Colorado", "Galo Cansado": "Galo",
    "Cruzeiro Endeudado": "Cruzeiro", "Bahía Citizen": "Bahía", "Vasco da Goma": "Vasco",
}
ESTILO_OVERRIDE = {
    "Flumando": "anchelottismo",
    "Gremiont": "haramball"
}

def get_liga() -> Liga:
    """
    Construye y devuelve el objeto Liga Brasileira
    con plantillas de parodia completamente pobladas de 20 jugadores.
    """
    try:
        equipos = []
        id_counter = 2000  # v3.7.0: rango propio (12 clubes)
        
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
            num_jornadas=max(2, 2 * (len(equipos) - 1))  # v3.7.0: 12 clubes -> 22
        )
    except Exception as e:
        logger.critical(f"Error crítico al construir Liga Brasileira: {e}. Retornando fallback.")
        return Liga("Liga Brasileira Fallback", "brasil", [], 10)
