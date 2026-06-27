# -*- coding: utf-8 -*-
"""
v2.3 (Fase 4) — Datos de la 2ª DIVISIÓN Liga Argentina (Primera Nacional).
6 equipos parodiados, 25 jugadores cada uno (150 totales).
OVR ~50-65 (los más bajos del juego, refleja la realidad de la 2ª del fútbol argentino).
"""
from __future__ import annotations

import logging
from alpha_football.models import Liga, Equipo, Jugador
from alpha_football.data.argentina import generar_atributos_por_posicion

logger = logging.getLogger(__name__)

PLANTILLAS_2A = {
    "San Lorenzo de Boedo B": {
        "ciudad": "Buenos Aires",
        "estrellas": 3.0,
        "estilo_dt": "anchelottismo",
        "balance": 4_500_000,
        "jugadores": [
            ("Augusto", "Batalla", "POR", 60, "lider", 30),
            ("Gastón", "Campi", "DEF", 59, "rustico", 29),
            ("Gonzalo", "Luján", "DEF", 58, None, 27),
            ("Carlos", "Sánchez", "DEF", 57, "pulmon_de_hierro", 30),
            ("Malcom", "Braida", "DEF", 56, None, 25),
            ("Gabriel", "Rojas", "DEF", 55, None, 28),
            ("Jhohan", "Romaña", "DEF", 54, None, 25),
            ("Reali", "Lateral", "DEF", 53, None, 22),
            ("Gordillo", "Muro", "DEF", 52, None, 26),
            ("Elián", "Mata", "MED", 60, "regateador", 24),
            ("Iker", "Muniain", "MED", 59, None, 23),
            ("Nahuel", "Bustos", "MED", 58, None, 27),
            ("Malcom", "Braida", "MED", 57, None, 24),
            ("Manuel", "Insaurralde", "MED", 56, "pulmon_de_hierro", 26),
            ("Francisco", "Fydriszewski", "MED", 55, None, 25),
            ("Sebastián", "Moyano", "MED", 54, None, 27),
            ("Ezequiel", "Cerutti", "MED", 53, None, 28),
            ("Néstor", "Ortigoza", "MED", 52, None, 33),
            ("Iván", "Pillud", "MED", 51, None, 24),
            ("Adrián", "Martegani", "DEL", 60, "regateador", 23),
            ("Andrés", "Vombergar", "DEL", 59, None, 28),
            ("Bareiro", "Tanque", "DEL", 58, None, 26),
            ("Ortigoza", "Volante", "DEL", 57, None, 30),
            ("Tapia", "Promesa", "DEL", 56, "pulmon_de_hierro", 22),
            ("Ferreyra", "Globo", "DEL", 55, None, 24),
        ],
    },
    "Velez Sarfield Junior": {
        "ciudad": "Buenos Aires",
        "estrellas": 3.0,
        "estilo_dt": "haramball",
        "balance": 4_800_000,
        "jugadores": [
            ("Randall", "Rodríguez", "POR", 60, None, 28),
            ("Tomás", "Guidara", "DEF", 59, "rustico", 26),
            ("Valentín", "Gómez", "DEF", 58, None, 23),
            ("Miguel", "Brizuela", "DEF", 57, "pulmon_de_hierro", 27),
            ("Elías", "Gómez", "DEF", 56, None, 30),
            ("Joaquín", "García", "DEF", 55, None, 25),
            ("Agustín", "Lagos", "DEF", 54, None, 22),
            ("Diego", "Godoy", "DEF", 53, None, 28),
            ("Franco", "Paredes", "DEF", 52, None, 23),
            ("Claudio", "Aquino", "MED", 60, "regateador", 27),
            ("Cristian", "Núñez", "MED", 59, None, 26),
            ("Sebastián", "Gallego", "MED", 58, "pulmon_de_hierro", 24),
            ("Abiel", "Osorio", "MED", 57, None, 22),
            ("Francisco", "Pizzini", "MED", 56, None, 25),
            ("Luca", "Orellano", "MED", 55, None, 24),
            ("Juan", "Méndez", "MED", 54, None, 23),
            ("Ignacio", "Méndez", "MED", 53, None, 22),
            ("Jonathan", "Ramírez", "MED", 52, None, 26),
            ("Gianluca", "Ferrario", "MED", 51, None, 24),
            ("Braian", "Romero", "DEL", 60, "regateador", 26),
            ("Walterm", "Bordachar", "DEL", 59, None, 25),
            ("Lucas", "Janson", "DEL", 58, "pulmon_de_hierro", 28),
            ("Abel", "Ramos", "DEL", 57, None, 27),
            ("Florián", "Monzón", "DEL", 56, None, 24),
            ("Dilan", "Pino", "DEL", 55, "regateador", 22),
        ],
    },
    "Estudiantes de la Plata B": {
        "ciudad": "La Plata",
        "estrellas": 2.5,
        "estilo_dt": "cruyffismo",
        "balance": 4_200_000,
        "jugadores": [
            ("Mariano", "Andujar", "POR", 58, "lider", 40),
            ("Eros", "Mancuso", "DEF", 57, "rustico", 25),
            ("Santiago", "Núñez", "DEF", 56, None, 24),
            ("Fabían", "Mancuso", "DEF", 55, "pulmon_de_hierro", 26),
            ("Gastón", "Suso", "DEF", 54, None, 25),
            ("Zair", "Romero", "DEF", 53, None, 23),
            ("Tomás", "Beltrán", "DEF", 52, None, 22),
            ("Bautista", "Kociubinski", "DEF", 51, None, 21),
            ("Lautaro", "Giménez", "DEF", 50, None, 24),
            ("Fernando", "Zuqui", "MED", 58, "regateador", 31),
            ("Mauro", "Boselli", "MED", 57, None, 35),
            ("Juan", "Gutiérrez", "MED", 56, None, 24),
            ("Josep", "Riffo", "MED", 55, None, 22),
            ("Gastón", "Gil", "MED", 54, None, 26),
            ("Carlos", "Lattanzio", "MED", 53, None, 23),
            ("Manuel", "Cecchini", "MED", 52, None, 24),
            ("Esequiel", "Muñoz", "MED", 51, None, 22),
            ("Matías", "Pellegrini", "MED", 50, None, 26),
            ("Franco", "Díaz", "MED", 49, None, 23),
            ("Guido", "Carrillo", "DEL", 58, "regateador", 28),
            ("Mauro", "Méndez", "DEL", 57, None, 30),
            ("Edwin", "Mancilla", "DEL", 56, None, 25),
            ("Franco", "Pérez", "DEL", 55, "pulmon_de_hierro", 24),
            ("Diego", "Vallejos", "DEL", 54, None, 23),
            ("Román", "Cuello", "DEL", 53, "regateador", 22),
        ],
    },
    "Newells Old Boys B": {
        "ciudad": "Rosario",
        "estrellas": 3.0,
        "estilo_dt": "flickismo",
        "balance": 4_500_000,
        "jugadores": [
            ("Lucas", "Hoyos", "POR", 59, None, 31),
            ("Armando", "Méndez", "DEF", 58, "rustico", 28),
            ("Gustavo", "Velázquez", "DEF", 57, None, 28),
            ("Leonel", "Vangioni", "DEF", 56, "pulmon_de_hierro", 32),
            ("Víctor", "Méndez", "DEF", 55, None, 26),
            ("Augusto", "Bracho", "DEF", 54, None, 24),
            ("Marco", "Cardozo", "DEF", 53, None, 22),
            ("Jherson", "Mosquera", "DEF", 52, None, 24),
            ("Bruno", "Caballero", "DEF", 51, None, 26),
            ("Jabes", "Cabral", "MED", 59, "regateador", 24),
            ("Ever", "Banega", "MED", 58, None, 35),
            ("Iván", "Gómez", "MED", 57, None, 27),
            ("Maximiliano", "Rodríguez", "MED", 56, None, 38),
            ("Tomás", "Pérez", "MED", 55, None, 23),
            ("Juan", "García", "MED", 54, None, 24),
            ("Franco", "Rinaldi", "MED", 53, None, 22),
            ("Agustín", "Sández", "MED", 52, None, 21),
            ("Diego", "Novaretti", "MED", 51, None, 30),
            ("Cristian", "Sotelo", "MED", 50, None, 22),
            ("Djorkaeff", "Reasco", "DEL", 59, "regateador", 24),
            ("Ramiro", "Sordo", "DEL", 58, None, 26),
            ("Brian", "Aguirre", "DEL", 57, None, 23),
            ("Juan", "Mancilla", "DEL", 56, "pulmon_de_hierro", 25),
            ("Francisco", "González", "DEL", 55, None, 24),
            ("Ignacio", "Schor", "DEL", 54, "regateador", 21),
        ],
    },
    "Tigre de Victoria B": {
        "ciudad": "Victoria",
        "estrellas": 2.5,
        "estilo_dt": "anchelottismo",
        "balance": 3_800_000,
        "jugadores": [
            ("Felipe", "Zenobio", "POR", 56, None, 28),
            ("Martín", "Galmarini", "DEF", 55, "rustico", 32),
            ("Brian", "Leizza", "DEF", 54, None, 24),
            ("Lautaro", "Monzón", "DEF", 53, "pulmon_de_hierro", 23),
            ("Abel", "Luciatti", "DEF", 52, None, 25),
            ("Lorenzo", "Esparza", "DEF", 51, None, 22),
            ("Diego", "Godoy", "DEF", 50, None, 26),
            ("Martín", "Ortega", "DEF", 49, None, 24),
            ("Sebastián", "García", "DEF", 48, None, 22),
            ("Sebastián", "Prediger", "MED", 56, "regateador", 35),
            ("Lorenzo", "Loyola", "MED", 55, None, 24),
            ("Lucas", "Menossi", "MED", 54, None, 30),
            ("Cristian", "Tarragona", "MED", 53, None, 28),
            ("Tomás", "Moya", "MED", 52, "pulmon_de_hierro", 25),
            ("Alexis", "Soto", "MED", 51, None, 24),
            ("Sebastián", "Sánchez", "MED", 50, None, 26),
            ("Facundo", "Pérez", "MED", 49, None, 22),
            ("David", "Rivas", "MED", 48, None, 24),
            ("Kevin", "López", "MED", 47, None, 22),
            ("Blas", "Armoa", "DEL", 56, "regateador", 26),
            ("Pablo", "Magnín", "DEL", 55, None, 30),
            ("Flavio", "Cádiz", "DEL", 54, None, 25),
            ("Gonzalo", "Maripán", "DEL", 53, "pulmon_de_hierro", 23),
            ("Erik", "Lamparello", "DEL", 52, None, 24),
            ("Juan", "Cavallaro", "DEL", 51, "regateador", 26),
        ],
    },
    "Belgrano de Cordillera": {
        "ciudad": "Córdoba",
        "estrellas": 2.5,
        "estilo_dt": "haramball",
        "balance": 3_900_000,
        "jugadores": [
            ("Nahuel", "Losada", "POR", 57, None, 32),
            ("Andrés", "Romero", "DEF", 56, "rustico", 28),
            ("Alejandro", "Rébola", "DEF", 55, None, 33),
            ("Wilmar", "Barrios", "DEF", 54, "pulmon_de_hierro", 27),
            ("Rafael", "Delgado", "DEF", 53, None, 30),
            ("Juan", "Barinaga", "DEF", 52, None, 27),
            ("Agustín", "Chiatti", "DEF", 51, None, 25),
            ("Gonzalo", "Lértora", "DEF", 50, None, 28),
            ("Mauricio", "Centurión", "DEF", 49, None, 22),
            ("Lucas", "Passerini", "MED", 57, "regateador", 28),
            ("Iván", "Ramírez", "MED", 56, None, 26),
            ("Matías", "Gallego", "MED", 55, None, 27),
            ("Juan", "Almirón", "MED", 54, "pulmon_de_hierro", 30),
            ("Ulises", "Sánchez", "MED", 53, None, 26),
            ("Hernán", "Bernardello", "MED", 52, None, 35),
            ("Esteban", "Rolón", "MED", 51, None, 27),
            ("Gerónimo", "Vella", "MED", 50, None, 23),
            ("Mariano", "Troilo", "MED", 49, None, 24),
            ("Facundo", "Barrionuevo", "MED", 48, None, 22),
            ("Pablo", "Vegetti", "DEL", 57, "regateador", 32),
            ("Joaquín", "Arce", "DEL", 56, None, 28),
            ("Franco", "Jara", "DEL", 55, None, 30),
            ("Cristian", "Lema", "DEL", 54, "pulmon_de_hierro", 27),
            ("Agustín", "Almendra", "DEL", 53, None, 22),
            ("Jeremías", "Cáceres", "DEL", 52, "regateador", 25),
        ],
    },
}


def _construir_equipo(nombre: str, datos: dict, id_base: int) -> Equipo:
    jugadores = []
    for idx, (nom, ape, pos, ovr, rasgo, edad) in enumerate(datos["jugadores"]):
        ataque, defensa, fisico, tecnica, mental = generar_atributos_por_posicion(ovr, pos)
        jugadores.append(Jugador(
            nombre=nom,
            apellido=ape,
            posicion=pos,
            ataque=ataque,
            defensa=defensa,
            fisico=fisico,
            tecnica=tecnica,
            mental=mental,
            moral=70,
            rasgo=rasgo,
            id=id_base + idx,
            edad=edad,
        ))
    return Equipo(
        nombre=nombre,
        ciudad=datos["ciudad"],
        estrellas=datos["estrellas"],
        estilo_dt=datos["estilo_dt"],
        balance=datos["balance"],
        jugadores=jugadores,
        es_usuario=False,
        nombre_corto=nombre[:14],
        division=2,
    )


def get_liga() -> Liga:
    try:
        equipos = []
        id_base = 34000
        for nombre, datos in PLANTILLAS_2A.items():
            eq = _construir_equipo(nombre, datos, id_base)
            equipos.append(eq)
            id_base += 100
        liga = Liga(
            nombre="Liga Profesional Argentina Parodia - Primera Nacional",
            tipo="argentina",
            equipos=equipos,
            num_jornadas=10,
            division=2,
            jornada_actual=1,
        )
        logger.info(f"2ª división Argentina cargada: {len(equipos)} equipos, "
                     f"{sum(len(e.jugadores) for e in equipos)} jugadores totales")
        return liga
    except Exception as e:
        logger.error(f"Error al construir 2ª división Argentina: {e}")
        return Liga(nombre="2ª Argentina (error)", tipo="argentina", equipos=[], num_jornadas=10, division=2)