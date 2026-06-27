# -*- coding: utf-8 -*-
"""
v2.3 (Fase 4) — Datos de la 2ª DIVISIÓN BetPlay (Colombia).
6 equipos parodiados, 25 jugadores cada uno (150 totales).
OVR ~10-15 pts más bajo que la 1ª división (rango 50-65).
"""
from __future__ import annotations

import logging
from alpha_football.models import Liga, Equipo, Jugador
from alpha_football.data.betplay import generar_atributos_por_posicion

logger = logging.getLogger(__name__)

# 25 jugadores por equipo. Formato: (Nombre, Apellido, Posicion, OVR, Rasgo, Edad)
PLANTILLAS_2A = {
    "Equidad Segundita": {
        "ciudad": "Bogotá",
        "estrellas": 3.0,
        "estilo_dt": "cruyffismo",
        "balance": 4_500_000,
        "jugadores": [
            # 1 POR
            ("Andrés", "Calderita", "POR", 60, "lider", 31),
            # 8 DEF
            ("Camilo", "Barrera Baja", "DEF", 58, "rustico", 26),
            ("Yair", "Cepillo", "DEF", 56, None, 24),
            ("Tomás", "Riñón", "DEF", 55, None, 27),
            ("Brayan", "Trancazo", "DEF", 54, "rustico", 22),
            ("Duván", "Matorral", "DEF", 53, None, 25),
            ("Jhon", "Pisotón", "DEF", 52, "pulmon_de_hierro", 23),
            ("Stiven", "Mojado", "DEF", 51, None, 21),
            ("Yerson", "Chispa", "DEF", 50, None, 24),
            # 10 MED
            ("Andrés", "Tilín", "MED", 60, "regateador", 23),
            ("Kevin", "Triste", "MED", 58, None, 22),
            ("Cristian", "Hormiga", "MED", 57, "pulmon_de_hierro", 28),
            ("Sebastián", "Gotera", "MED", 56, None, 25),
            ("Julián", "Rasguño", "MED", 55, None, 21),
            ("Michael", "Bufido", "MED", 54, "regateador", 24),
            ("Jhony", "Cerillo", "MED", 53, None, 26),
            ("Daniel", "Tabique", "MED", 52, None, 22),
            ("Yeison", "Garfio", "MED", 51, None, 23),
            ("Breiner", "Tobillo", "MED", 50, None, 20),
            # 6 DEL
            ("Johan", "Chicharrón", "DEL", 60, "regateador", 21),
            ("Luis", "Tronco", "DEL", 58, None, 23),
            ("Marlon", "Piedra", "DEL", 56, None, 22),
            ("Robert", "Chispa", "DEL", 54, "pulmon_de_hierro", 25),
            ("Bayron", "Cuello", "DEL", 53, None, 24),
            ("Jair", "Trapo", "DEL", 52, None, 22),
        ],
    },
    "Real Cartagenero": {
        "ciudad": "Cartagena",
        "estrellas": 3.0,
        "estilo_dt": "haramball",
        "balance": 4_000_000,
        "jugadores": [
            ("Wilder", "Mojado", "POR", 58, None, 30),
            ("Julián", "Teja", "DEF", 58, "rustico", 25),
            ("Mauricio", "Cáscara", "DEF", 57, None, 27),
            ("Luis", "Punta", "DEF", 56, None, 24),
            ("Ricardo", "Garita", "DEF", 55, "lider", 29),
            ("Óscar", "Tranca", "DEF", 54, None, 26),
            ("Carlos", "Muralla", "DEF", 53, "rustico", 22),
            ("Jader", "Muelle", "DEF", 52, None, 23),
            ("Darío", "Piña", "DEF", 51, None, 24),
            ("Johan", "Chicharrón", "MED", 58, "regateador", 23),
            ("Edwin", "Cartilla", "MED", 57, None, 25),
            ("Yamid", "Tablón", "MED", 56, "pulmon_de_hierro", 22),
            ("Jhon", "Kilo", "MED", 55, None, 26),
            ("Arbey", "Cacharro", "MED", 54, "regateador", 24),
            ("Ronaldo", "Berraquera", "MED", 53, None, 21),
            ("César", "Loza", "MED", 52, None, 23),
            ("Héctor", "Chuzo", "MED", 51, None, 25),
            ("Camilo", "Tarro", "MED", 50, None, 22),
            ("Andrés", "Chicharra", "MED", 50, None, 21),
            ("Iván", "Candela", "DEL", 58, "pulmon_de_hierro", 22),
            ("Mauricio", "Roño", "DEL", 56, None, 25),
            ("Aldair", "Punta", "DEL", 55, None, 23),
            ("Neider", "Batata", "DEL", 54, None, 21),
            ("Junior", "Berrugo", "DEL", 53, "regateador", 24),
            ("Ómar", "Piñata", "DEL", 52, None, 22),
        ],
    },
    "Chicó Filial Sub-23": {
        "ciudad": "Tunja",
        "estrellas": 2.5,
        "estilo_dt": "anchelottismo",
        "balance": 3_500_000,
        "jugadores": [
            ("Sergio", "Tarro", "POR", 56, None, 22),
            ("Camilo", "Gotera", "DEF", 55, None, 21),
            ("Daniel", "Chinche", "DEF", 54, "rustico", 20),
            ("Andrés", "Manilla", "DEF", 53, None, 22),
            ("Felipe", "Muelle", "DEF", 52, None, 21),
            ("Mauricio", "Tubo", "DEF", 51, "pulmon_de_hierro", 20),
            ("Julián", "Raspa", "DEF", 50, None, 19),
            ("Brayan", "Clavo", "DEF", 49, None, 21),
            ("Stiven", "Gotera", "DEF", 48, None, 20),
            ("Yerson", "Chispa", "MED", 56, "regateador", 21),
            ("Kevin", "Tabique", "MED", 55, None, 20),
            ("Jair", "Trapo", "MED", 54, None, 22),
            ("Michael", "Bufido", "MED", 53, None, 21),
            ("Daniel", "Tablón", "MED", 52, None, 20),
            ("Cristian", "Hormiga", "MED", 51, "pulmon_de_hierro", 22),
            ("Sebastián", "Tubo", "MED", 50, None, 21),
            ("Jhony", "Cerillo", "MED", 49, None, 20),
            ("Yeison", "Garfio", "MED", 48, None, 19),
            ("Jhon", "Chuzo", "MED", 47, None, 20),
            ("Bayron", "Cuello", "DEL", 55, "regateador", 21),
            ("Marlon", "Piedra", "DEL", 54, None, 22),
            ("Robert", "Chispa", "DEL", 53, None, 20),
            ("Jair", "Tarro", "DEL", 52, None, 19),
            ("Breiner", "Tobillo", "DEL", 51, "pulmon_de_hierro", 20),
            ("Johan", "Chicharrón", "DEL", 50, None, 19),
        ],
    },
    "Fortaleza Sin Título": {
        "ciudad": "Zipaquirá",
        "estrellas": 2.5,
        "estilo_dt": "flickismo",
        "balance": 3_800_000,
        "jugadores": [
            ("Juan", "Boquerón", "POR", 58, "lider", 33),
            ("Roberto", "Candado", "DEF", 57, "rustico", 28),
            ("Carlos", "Tablón", "DEF", 56, None, 26),
            ("Luis", "Chuzo", "DEF", 55, None, 24),
            ("Pedro", "Pala", "DEF", 54, None, 27),
            ("Andrés", "Maza", "DEF", 53, "pulmon_de_hierro", 25),
            ("Diego", "Tranca", "DEF", 52, None, 23),
            ("Sebastián", "Candado", "DEF", 51, None, 24),
            ("Mauricio", "Tranca", "DEF", 50, None, 22),
            ("Stiven", "Chinche", "MED", 58, "regateador", 25),
            ("Kevin", "Clavo", "MED", 57, None, 24),
            ("Julián", "Tubo", "MED", 56, None, 22),
            ("Yeison", "Gotera", "MED", 55, "pulmon_de_hierro", 26),
            ("Michael", "Raspa", "MED", 54, None, 23),
            ("Cristian", "Tarro", "MED", 53, None, 25),
            ("Bayron", "Chispa", "MED", 52, None, 22),
            ("Jhon", "Tarro", "MED", 51, None, 24),
            ("Daniel", "Tubo", "MED", 50, None, 21),
            ("Brayan", "Gotera", "MED", 49, None, 22),
            ("Roberto", "Taco", "DEL", 58, "regateador", 23),
            ("Camilo", "Punta", "DEL", 56, None, 25),
            ("Jhony", "Tobillo", "DEL", 55, None, 22),
            ("Iván", "Bufido", "DEL", 54, "pulmon_de_hierro", 24),
            ("Neider", "Chinchón", "DEL", 53, None, 21),
            ("Aldair", "Chuzo", "DEL", 52, None, 23),
        ],
    },
    "Leones del Valle B": {
        "ciudad": "Palmira",
        "estrellas": 3.0,
        "estilo_dt": "cruyffismo",
        "balance": 4_200_000,
        "jugadores": [
            ("Mauricio", "Chispa", "POR", 59, None, 28),
            ("Héctor", "Chinchón", "DEF", 58, "rustico", 26),
            ("Cristian", "Candado", "DEF", 57, None, 25),
            ("Sergio", "Tubo", "DEF", 56, None, 27),
            ("Julián", "Tranca", "DEF", 55, "pulmon_de_hierro", 24),
            ("Jair", "Tobillo", "DEF", 54, None, 23),
            ("Daniel", "Manilla", "DEF", 53, None, 25),
            ("Sebastián", "Muelle", "DEF", 52, None, 24),
            ("Brayan", "Pala", "DEF", 51, None, 22),
            ("Roberto", "Gotera", "MED", 59, "regateador", 24),
            ("Luis", "Raspa", "MED", 58, None, 26),
            ("Kevin", "Chuzo", "MED", 57, None, 23),
            ("Michael", "Tarro", "MED", 56, "pulmon_de_hierro", 25),
            ("Andrés", "Clavo", "MED", 55, None, 22),
            ("Stiven", "Tubo", "MED", 54, None, 24),
            ("Camilo", "Chinche", "MED", 53, None, 23),
            ("Iván", "Tarro", "MED", 52, None, 21),
            ("Yeison", "Muela", "MED", 51, None, 22),
            ("Cristian", "Tablón", "MED", 50, None, 20),
            ("Mauricio", "Trapo", "DEL", 59, "regateador", 23),
            ("Neider", "Chinchón", "DEL", 58, None, 25),
            ("Aldair", "Pala", "DEL", 56, None, 22),
            ("Jhon", "Taco", "DEL", 55, "pulmon_de_hierro", 24),
            ("Ómar", "Bufido", "DEL", 54, None, 21),
            ("Camilo", "Muela", "DEL", 53, None, 23),
        ],
    },
    "Valledupar Junior B": {
        "ciudad": "Valledupar",
        "estrellas": 2.0,
        "estilo_dt": "haramball",
        "balance": 3_200_000,
        "jugadores": [
            ("Óscar", "Chinchón", "POR", 54, None, 30),
            ("Roberto", "Boquerón", "DEF", 53, "rustico", 26),
            ("Camilo", "Tranca", "DEF", 52, None, 24),
            ("Julián", "Tobillo", "DEF", 51, None, 22),
            ("Mauricio", "Candado", "DEF", 50, "pulmon_de_hierro", 25),
            ("Pedro", "Trapo", "DEF", 49, None, 23),
            ("Héctor", "Pala", "DEF", 48, None, 24),
            ("Yeison", "Bufido", "DEF", 47, None, 22),
            ("Michael", "Tarro", "DEF", 46, None, 21),
            ("Stiven", "Chinche", "MED", 53, None, 24),
            ("Jair", "Tubo", "MED", 52, "regateador", 22),
            ("Cristian", "Tarro", "MED", 51, None, 23),
            ("Jhon", "Manilla", "MED", 50, None, 21),
            ("Kevin", "Gotera", "MED", 49, None, 22),
            ("Andrés", "Chinchón", "MED", 48, None, 23),
            ("Brayan", "Raspa", "MED", 47, "pulmon_de_hierro", 20),
            ("Daniel", "Muelle", "MED", 46, None, 21),
            ("Sebastián", "Tablón", "MED", 45, None, 22),
            ("Neider", "Clavo", "MED", 44, None, 20),
            ("Iván", "Tranca", "DEL", 53, "regateador", 22),
            ("Aldair", "Muela", "DEL", 52, None, 23),
            ("Jhony", "Tubo", "DEL", 51, None, 21),
            ("Bayron", "Chinche", "DEL", 50, "pulmon_de_hierro", 22),
            ("Jair", "Muelle", "DEL", 49, None, 20),
            ("Camilo", "Clavo", "DEL", 48, None, 21),
        ],
    },
}


def _construir_equipo(nombre: str, datos: dict, id_base: int) -> Equipo:
    """Construye un objeto Equipo con 25 jugadores parodiados."""
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
    """
    Devuelve la 2ª división BetPlay con 6 equipos parodiados y 25 jugadores cada uno.
    """
    try:
        equipos = []
        id_base = 30000  # IDs únicos (1ª división usa hasta ~9999)
        for nombre, datos in PLANTILLAS_2A.items():
            eq = _construir_equipo(nombre, datos, id_base)
            equipos.append(eq)
            id_base += 100
        liga = Liga(
            nombre="Liga BetPlay Dimayor Parodia - Segunda División",
            tipo="betplay",
            equipos=equipos,
            num_jornadas=10,  # 6 equipos → round-robin doble = 10 jornadas
            division=2,
            jornada_actual=1,
        )
        logger.info(f"2ª división BetPlay cargada: {len(equipos)} equipos, "
                     f"{sum(len(e.jugadores) for e in equipos)} jugadores totales")
        return liga
    except Exception as e:
        logger.error(f"Error al construir 2ª división BetPlay: {e}")
        return Liga(nombre="2ª BetPlay (error)", tipo="betplay", equipos=[], num_jornadas=10, division=2)