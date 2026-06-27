# -*- coding: utf-8 -*-
"""
v2.3 (Fase 4) — Datos de la 2ª DIVISIÓN LaLiga (España).
6 equipos parodiados, 25 jugadores cada uno (150 totales).
OVR ~60-75 (más alto que BetPlay 2ª pero más bajo que LaLiga 1ª).
"""
from __future__ import annotations

import logging
from alpha_football.models import Liga, Equipo, Jugador
from alpha_football.data.laliga import generar_atributos_por_posicion

logger = logging.getLogger(__name__)

# 25 jugadores por equipo
PLANTILLAS_2A = {
    "Real Racing Acelerado": {
        "ciudad": "Santander",
        "estrellas": 3.5,
        "estilo_dt": "anchelottismo",
        "balance": 11_000_000,
        "jugadores": [
            ("Iván", "Roble", "POR", 70, "lider", 30),
            ("Lucas", "Ábrego", "DEF", 68, "rustico", 26),
            ("Saúl", "Tijereta", "DEF", 67, None, 24),
            ("Yago", "Muro", "DEF", 66, None, 25),
            ("Pol", "Vigueta", "DEF", 65, "pulmon_de_hierro", 23),
            ("Carlos", "Cerrojo", "DEF", 64, None, 27),
            ("Sergio", "Chinchón", "DEF", 63, None, 22),
            ("Marcos", "Clavo", "DEF", 62, None, 24),
            ("Iker", "Tubo", "DEF", 61, None, 23),
            ("David", "Puntería", "MED", 70, "regateador", 25),
            ("Álvaro", "Tranca", "MED", 68, None, 23),
            ("Héctor", "Piedra", "MED", 67, "pulmon_de_hierro", 24),
            ("Borja", "Raspa", "MED", 66, None, 22),
            ("Adrián", "Tarro", "MED", 65, "regateador", 25),
            ("Roberto", "Tijera", "MED", 64, None, 23),
            ("Mario", "Tubo", "MED", 63, None, 22),
            ("Óscar", "Tabique", "MED", 62, None, 24),
            ("Mateu", "Muela", "MED", 61, None, 23),
            ("Ismael", "Chinche", "MED", 60, None, 22),
            ("Yeremay", "Punta", "DEL", 70, "regateador", 24),
            ("Andrés", "Tronco", "DEL", 68, None, 25),
            ("Íñigo", "Chinchón", "DEL", 67, "pulmon_de_hierro", 23),
            ("Asier", "Tobillo", "DEL", 66, None, 26),
            ("Manu", "Tranca", "DEL", 65, "regateador", 22),
            ("Koldo", "Clavo", "DEL", 64, None, 24),
        ],
    },
    "Depor Tivo": {
        "ciudad": "La Coruña",
        "estrellas": 3.5,
        "estilo_dt": "cruyffismo",
        "balance": 10_500_000,
        "jugadores": [
            ("Germán", "Paraguas", "POR", 69, None, 29),
            ("Ximo", "Muralla", "DEF", 68, "rustico", 28),
            ("Álex", "Boquerón", "DEF", 67, None, 25),
            ("Pablo", "Tranca", "DEF", 66, "pulmon_de_hierro", 24),
            ("Diego", "Chinchón", "DEF", 65, None, 26),
            ("Jaime", "Muro", "DEF", 64, None, 23),
            ("Mikel", "Tubo", "DEF", 63, None, 25),
            ("Ander", "Manilla", "DEF", 62, None, 24),
            ("Iago", "Tarro", "DEF", 61, None, 22),
            ("Nico", "Tijera", "MED", 69, "regateador", 26),
            ("Josep", "Raspa", "MED", 68, None, 24),
            ("Álex", "Chispa", "MED", 67, None, 25),
            ("Carles", "Tranco", "MED", 66, "pulmon_de_hierro", 23),
            ("Pau", "Muela", "MED", 65, None, 24),
            ("Roger", "Tabique", "MED", 64, None, 23),
            ("Xavi", "Clavo", "MED", 63, None, 22),
            ("Marc", "Piedra", "MED", 62, "regateador", 24),
            ("Eric", "Gotera", "MED", 61, None, 23),
            ("Sergi", "Tubo", "MED", 60, None, 22),
            ("Lucas", "Puntería", "DEL", 69, "regateador", 25),
            ("Hugo", "Tranca", "DEL", 68, None, 26),
            ("Dani", "Chinchón", "DEL", 67, None, 24),
            ("Gabi", "Tobillo", "DEL", 66, "pulmon_de_hierro", 23),
            ("Iván", "Raspa", "DEL", 65, None, 25),
            ("Pablo", "Muela", "DEL", 64, "regateador", 24),
        ],
    },
    "UD Almeríaso": {
        "ciudad": "Almería",
        "estrellas": 3.0,
        "estilo_dt": "flickismo",
        "balance": 9_500_000,
        "jugadores": [
            ("Luciano", "Candado", "POR", 68, "lider", 31),
            ("Marcos", "Muro", "DEF", 67, None, 27),
            ("César", "Tubo", "DEF", 66, "rustico", 25),
            ("Álex", "Tranca", "DEF", 65, None, 24),
            ("Nacho", "Clavo", "DEF", 64, "pulmon_de_hierro", 23),
            ("Sergio", "Chinchón", "DEF", 63, None, 25),
            ("Antonio", "Muro", "DEF", 62, None, 24),
            ("Rober", "Tarro", "DEF", 61, None, 23),
            ("Iván", "Manilla", "DEF", 60, None, 22),
            ("Lazo", "Tijera", "MED", 68, "regateador", 26),
            ("Robert", "Raspa", "MED", 67, None, 24),
            ("Samú", "Tabique", "MED", 66, "pulmon_de_hierro", 23),
            ("Melero", "Tranco", "MED", 65, None, 25),
            ("Petrov", "Muela", "MED", 64, None, 24),
            ("Appindáyé", "Gotera", "MED", 63, None, 22),
            ("Eguaras", "Tubo", "MED", 62, None, 24),
            ("Centelles", "Piedra", "MED", 61, None, 23),
            ("Arnau", "Clavo", "MED", 60, None, 22),
            ("Lazaro", "Tarro", "MED", 59, None, 21),
            ("Bilal", "Punta", "DEL", 68, "regateador", 25),
            ("Embarba", "Tobillo", "DEL", 67, None, 24),
            ("Pubill", "Chinchón", "DEL", 66, None, 23),
            ("Chumi", "Tranca", "DEL", 65, "pulmon_de_hierro", 24),
            ("Brandariz", "Raspa", "DEL", 64, None, 22),
            ("Arribas", "Muela", "DEL", 63, "regateador", 23),
        ],
    },
    "Las Palma-Hand": {
        "ciudad": "Las Palmas",
        "estrellas": 3.0,
        "estilo_dt": "anchelottismo",
        "balance": 9_800_000,
        "jugadores": [
            ("Aarón", "Muralla", "POR", 67, None, 28),
            ("Alex", "Tubo", "DEF", 66, "rustico", 26),
            ("Mika", "Mármol", "DEF", 65, None, 24),
            ("Marcos", "Tranco", "DEF", 64, "pulmon_de_hierro", 25),
            ("Saúl", "Clavo", "DEF", 63, None, 23),
            ("Julián", "Muro", "DEF", 62, None, 24),
            ("Lemos", "Chinchón", "DEF", 61, None, 23),
            ("Coco", "Tarro", "DEF", 60, None, 22),
            ("Eric", "Manilla", "DEF", 59, None, 21),
            ("Loiodice", "Tijera", "MED", 67, None, 26),
            ("Moleiro", "Raspa", "MED", 66, "regateador", 22),
            ("Fuster", "Tabique", "MED", 65, None, 25),
            ("Pejiño", "Muela", "MED", 64, "pulmon_de_hierro", 23),
            ("Cardona", "Tranco", "MED", 63, None, 24),
            ("Pinchi", "Gotera", "MED", 62, None, 22),
            ("Jonathan", "Tubo", "MED", 61, None, 24),
            ("Álex", "Piedra", "MED", 60, None, 23),
            ("Sergi", "Clavo", "MED", 59, None, 22),
            ("Beto", "Tarro", "MED", 58, None, 21),
            ("Jesé", "Punta", "DEL", 67, "regateador", 26),
            ("Benito", "Chinchón", "DEL", 66, None, 24),
            ("Silva", "Tobillo", "DEL", 65, "pulmon_de_hierro", 23),
            ("Marc", "Raspa", "DEL", 64, None, 25),
            ("Sandro", "Tranca", "DEL", 63, "regateador", 22),
            ("Cabrera", "Muela", "DEL", 62, None, 24),
        ],
    },
    "Graná CF": {
        "ciudad": "Granada",
        "estrellas": 3.0,
        "estilo_dt": "haramball",
        "balance": 9_200_000,
        "jugadores": [
            ("Luca", "Tranca", "POR", 66, None, 30),
            ("Carlos", "Muralla", "DEF", 65, "rustico", 27),
            ("Miquel", "Tubo", "DEF", 64, None, 25),
            ("Lejeune", "Clavo", "DEF", 63, None, 26),
            ("Quini", "Tarro", "DEF", 62, "pulmon_de_hierro", 24),
            ("Ricard", "Muro", "DEF", 61, None, 23),
            ("Carlos", "Chinchón", "DEF", 60, None, 25),
            ("Álex", "Manilla", "DEF", 59, None, 24),
            ("Pablo", "Tubo", "DEF", 58, None, 22),
            ("Melendo", "Tijera", "MED", 66, "regateador", 25),
            ("Bodiger", "Raspa", "MED", 65, None, 24),
            ("Gonalons", "Tabique", "MED", 64, None, 26),
            ("Petrov", "Muela", "MED", 63, None, 25),
            ("Gallar", "Tranco", "MED", 62, "regateador", 23),
            ("Puertas", "Gotera", "MED", 61, "pulmon_de_hierro", 24),
            ("Aranda", "Tubo", "MED", 60, None, 23),
            ("Milla", "Piedra", "MED", 59, None, 22),
            ("Neva", "Clavo", "MED", 58, None, 21),
            ("Ricard", "Tarro", "MED", 57, None, 23),
            ("Weissman", "Punta", "DEL", 66, None, 27),
            ("Uzuni", "Chinchón", "DEL", 65, "regateador", 25),
            ("Boyé", "Tobillo", "DEL", 64, None, 24),
            ("Bryan", "Raspa", "DEL", 63, "pulmon_de_hierro", 23),
            ("Jorge", "Tranca", "DEL", 62, None, 22),
            ("Myrto", "Muela", "DEL", 61, "regateador", 24),
        ],
    },
    "Eibar Plus": {
        "ciudad": "Eibar",
        "estrellas": 2.5,
        "estilo_dt": "haramball",
        "balance": 8_500_000,
        "jugadores": [
            ("Jon", "Tranca", "POR", 64, None, 32),
            ("Ander", "Tubo", "DEF", 63, "rustico", 26),
            ("Arbilla", "Clavo", "DEF", 62, None, 28),
            ("Chori", "Tarro", "DEF", 61, None, 24),
            ("Bautista", "Muro", "DEF", 60, "pulmon_de_hierro", 23),
            ("Tejero", "Chinchón", "DEF", 59, None, 25),
            ("Sergio", "Manilla", "DEF", 58, None, 24),
            ("Ripa", "Tubo", "DEF", 57, None, 22),
            ("Lombardi", "Tarro", "DEF", 56, None, 21),
            ("Edu", "Tijera", "MED", 64, "regateador", 27),
            ("Matheus", "Raspa", "MED", 63, None, 25),
            ("Aketxe", "Tabique", "MED", 62, None, 24),
            ("Vadillo", "Muela", "MED", 61, None, 23),
            ("Blasco", "Tranco", "MED", 60, "pulmon_de_hierro", 25),
            ("Corpas", "Gotera", "MED", 59, None, 24),
            ("Stoichkov", "Tubo", "MED", 58, None, 22),
            ("Yangel", "Piedra", "MED", 57, None, 23),
            ("Álvaro", "Clavo", "MED", 56, None, 21),
            ("Peru", "Tarro", "MED", 55, None, 20),
            ("Stoichkov", "Punta", "DEL", 64, "regateador", 24),
            ("Quique", "Chinchón", "DEL", 63, None, 26),
            ("Iván", "Tobillo", "DEL", 62, "pulmon_de_hierro", 23),
            ("Jon", "Raspa", "DEL", 61, None, 25),
            ("Garrido", "Tranca", "DEL", 60, "regateador", 22),
            ("Bebé", "Muela", "DEL", 59, None, 24),
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
        id_base = 31000
        for nombre, datos in PLANTILLAS_2A.items():
            eq = _construir_equipo(nombre, datos, id_base)
            equipos.append(eq)
            id_base += 100
        liga = Liga(
            nombre="LaLiga EA Sports Parodia - Segunda División",
            tipo="laliga",
            equipos=equipos,
            num_jornadas=10,
            division=2,
            jornada_actual=1,
        )
        logger.info(f"2ª división LaLiga cargada: {len(equipos)} equipos, "
                     f"{sum(len(e.jugadores) for e in equipos)} jugadores totales")
        return liga
    except Exception as e:
        logger.error(f"Error al construir 2ª división LaLiga: {e}")
        return Liga(nombre="2ª LaLiga (error)", tipo="laliga", equipos=[], num_jornadas=10, division=2)