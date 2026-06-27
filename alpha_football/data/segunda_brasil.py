# -*- coding: utf-8 -*-
"""
v2.3 (Fase 4) — Datos de la 2ª DIVISIÓN Brasileirão (Brasil).
6 equipos parodiados, 25 jugadores cada uno (150 totales).
OVR ~55-70 (entre BetPlay 2ª y LaLiga 2ª).
"""
from __future__ import annotations

import logging
from alpha_football.models import Liga, Equipo, Jugador
from alpha_football.data.brasil import generar_atributos_por_posicion

logger = logging.getLogger(__name__)

PLANTILLAS_2A = {
    "Palmeiras de Sao Paulo B": {
        "ciudad": "São Paulo",
        "estrellas": 3.0,
        "estilo_dt": "anchelottismo",
        "balance": 7_500_000,
        "jugadores": [
            ("Marcelo", "Lomba", "POR", 65, "lider", 30),
            ("Gustavo", "Gómez", "DEF", 64, "rustico", 30),
            ("Murilo", "Cerqueira", "DEF", 63, None, 26),
            ("Naves", "Defensor", "DEF", 62, "pulmon_de_hierro", 24),
            ("Vanderlan", "Esquerdo", "DEF", 61, None, 22),
            ("Piquerez", "Zagueiro", "DEF", 60, None, 25),
            ("Marcos", "Rocha", "DEF", 59, None, 28),
            ("Luan", "Garcia", "DEF", 58, None, 23),
            ("Naldo", "Paredes", "DEF", 57, None, 24),
            ("Raphael", "Vega", "MED", 65, "regateador", 25),
            ("Zé", "Rafaelo", "MED", 64, None, 26),
            ("Richard", "Rios", "MED", 63, None, 23),
            ("Mauricio", "Sampa", "MED", 62, "pulmon_de_hierro", 24),
            ("Jailson", "Marcelo", "MED", 61, None, 27),
            ("Naves", "Volante", "MED", 60, None, 23),
            ("Fabinho", "Mineiro", "MED", 59, None, 25),
            ("Gabriel", "Menino", "MED", 58, None, 24),
            ("Caio", "Paulista", "MED", 57, None, 22),
            ("Gustavo", "Garrincha", "MED", 56, None, 23),
            ("Rony", "Rústico", "DEL", 65, "regateador", 27),
            ("Dudu", "Decano", "DEL", 64, None, 30),
            ("Flaco", "López", "DEL", 63, None, 23),
            ("Endrick", "Promesa", "DEL", 62, "pulmon_de_hierro", 17),
            ("Estevão", "Will", "DEL", 61, None, 18),
            ("Caio", "Hulk", "DEL", 60, "regateador", 24),
        ],
    },
    "Santos Dumont B": {
        "ciudad": "Santos",
        "estrellas": 3.0,
        "estilo_dt": "cruyffismo",
        "balance": 7_000_000,
        "jugadores": [
            ("João", "Paulo", "POR", 64, None, 30),
            ("Gil", "Bauer", "DEF", 63, "rustico", 33),
            ("João", "Basso", "DEF", 62, None, 26),
            ("Hayner", "Direita", "DEF", 61, None, 24),
            ("Escobar", "Zagueiro", "DEF", 60, "pulmon_de_hierro", 26),
            ("JP", "Chern", "DEF", 59, None, 23),
            ("Sandry", "Volante", "DEF", 58, None, 22),
            ("Maicon", "Rocha", "DEF", 57, None, 25),
            ("Messias", "Pedra", "DEF", 56, None, 24),
            ("Diego", "Pituca", "MED", 64, None, 31),
            ("Giuliano", "Bola", "MED", 63, "regateador", 32),
            ("Carlos", "Andrade", "MED", 62, "pulmon_de_hierro", 24),
            ("Tomas", "Rincon", "MED", 61, None, 28),
            ("Cazares", "Equator", "MED", 60, None, 27),
            ("Gabriel", "Verón", "MED", 59, None, 22),
            ("Vinicius", "Balieiro", "MED", 58, None, 21),
            ("Patrick", "Bola", "MED", 57, None, 24),
            ("Bryan", "Bola", "MED", 56, None, 22),
            ("Ivson", "Promesa", "MED", 55, None, 20),
            ("Soteldo", "Chico", "DEL", 64, "regateador", 27),
            ("Furch", "Tanque", "DEL", 63, None, 32),
            ("Otero", "Vinotinto", "DEL", 62, None, 28),
            ("Willian", "Bigode", "DEL", 61, "pulmon_de_hierro", 30),
            ("Pedrinho", "Mineiro", "DEL", 60, None, 22),
            ("Guilherme", "Pato", "DEL", 59, "regateador", 24),
        ],
    },
    "Cruzeiro do Sul B": {
        "ciudad": "Belo Horizonte",
        "estrellas": 2.5,
        "estilo_dt": "haramball",
        "balance": 6_500_000,
        "jugadores": [
            ("Cássio", "Ramos", "POR", 63, "lider", 35),
            ("Lucas", "Ribeiro", "DEF", 62, "rustico", 26),
            ("Zé", "Ivaldo", "DEF", 61, None, 28),
            ("Marlon", "Freitas", "DEF", 60, "pulmon_de_hierro", 27),
            ("William", "Bigode", "DEF", 59, None, 29),
            ("Rafaela", "Silva", "DEF", 58, None, 25),
            ("Wesley", "Gasolina", "DEF", 57, None, 22),
            ("João", "Marcelo", "DEF", 56, None, 23),
            ("Lucas", "Salva", "DEF", 55, None, 24),
            ("Matheus", "Pereira", "MED", 63, "regateador", 27),
            ("Lucas", "Silva", "MED", 62, None, 26),
            ("Fernando", "Canhoto", "MED", 61, None, 28),
            ("Ronaldo", "Fenômeno", "MED", 60, None, 30),
            ("Barreal", "Mágico", "MED", 59, "pulmon_de_hierro", 24),
            ("Robert", "Senna", "MED", 58, None, 25),
            ("Lucas", "Romero", "MED", 57, None, 23),
            ("Wesley", "Gaspar", "MED", 56, None, 21),
            ("Lucas", "Oliveira", "MED", 55, None, 22),
            ("Japa", "Cruzeirense", "MED", 54, None, 24),
            ("Kaio", "Jorge", "DEL", 63, None, 22),
            ("Gilberto", "Tanque", "DEL", 62, "regateador", 32),
            ("Wesley", "Gass", "DEL", 61, None, 23),
            ("Rafa", "Muro", "DEL", 60, "pulmon_de_hierro", 25),
            ("Juan", "Dybala", "DEL", 59, None, 24),
            ("Stênio", "Júnior", "DEL", 58, "regateador", 21),
        ],
    },
    "Corithians-SP B": {
        "ciudad": "São Paulo",
        "estrellas": 3.0,
        "estilo_dt": "flickismo",
        "balance": 7_200_000,
        "jugadores": [
            ("Cássio", "Goleiro", "POR", 64, "lider", 36),
            ("Fagner", "Lateral", "DEF", 63, "rustico", 33),
            ("Félix", "Torres", "DEF", 62, None, 27),
            ("Gustavo", "Mancha", "DEF", 61, None, 25),
            ("Caetano", "Zagueiro", "DEF", 60, "pulmon_de_hierro", 24),
            ("Hugo", "Souza", "DEF", 59, None, 23),
            ("Matheuzinho", "Lateral", "DEF", 58, None, 22),
            ("Bruno", "Méndez", "DEF", 57, None, 24),
            ("Fagner", "Russo", "DEF", 56, None, 23),
            ("Maycon", "Volante", "MED", 64, None, 26),
            ("Raniele", "Volante", "MED", 63, None, 27),
            ("Rodrigo", "Garro", "MED", 62, "regateador", 26),
            ("Igor", "Cordeiro", "MED", 61, None, 24),
            ("Charles", "Pimentel", "MED", 60, "pulmon_de_hierro", 28),
            ("Breno", "Bidoglio", "MED", 59, None, 22),
            ("Pedro", "Naressi", "MED", 58, None, 23),
            ("Igor", "Formiga", "MED", 57, None, 21),
            ("Roni", "Volante", "MED", 56, None, 24),
            ("Giuliano", "Vampeta", "MED", 55, None, 25),
            ("Yuri", "Alberto", "DEL", 64, "regateador", 23),
            ("Romero", "Paraguaio", "DEL", 63, None, 30),
            ("Pedro", "Mineiro", "DEL", 62, None, 27),
            ("Wesley", "Golaço", "DEL", 61, "pulmon_de_hierro", 22),
            ("Talles", "Magno", "DEL", 60, None, 21),
            ("Breno", "Bidog", "DEL", 59, "regateador", 22),
        ],
    },
    "Atletico Minera B": {
        "ciudad": "Belo Horizonte",
        "estrellas": 3.0,
        "estilo_dt": "anchelottismo",
        "balance": 7_800_000,
        "jugadores": [
            ("Everson", "Pillar", "POR", 64, "lider", 33),
            ("Maurício", "Lateral", "DEF", 63, "rustico", 28),
            ("Bruno", "Fuchs", "DEF", 62, None, 26),
            ("Junior", "Alonso", "DEF", 61, None, 32),
            ("Igor", "Rabello", "DEF", 60, "pulmon_de_hierro", 27),
            ("Guilherme", "Arana", "DEF", 59, None, 27),
            ("Mariano", "Lateral", "DEF", 58, None, 35),
            ("Renzo", "Saravia", "DEF", 57, None, 26),
            ("Iago", "Maidana", "DEF", 56, None, 25),
            ("Otávio", "Volante", "MED", 64, None, 30),
            ("Igor", "Gomes", "MED", 63, "regateador", 22),
            ("Gustavo", "Scarpa", "MED", 62, "pulmon_de_hierro", 30),
            ("Alan", "Franco", "MED", 61, None, 26),
            ("Matheus", "Belém", "MED", 60, None, 23),
            ("Rodrigo", "Battaglia", "MED", 59, None, 32),
            ("Igor", "Fernandes", "MED", 58, None, 24),
            ("Vargas", "Chileno", "MED", 57, None, 32),
            ("Cadu", "Volante", "MED", 56, None, 26),
            ("Igor", "Carioca", "MED", 55, None, 24),
            ("Hulk", "Paraiba", "DEL", 64, "regateador", 37),
            ("Paulinho", "Touro", "DEL", 63, None, 23),
            ("Vargas", "Lobo", "DEL", 62, "pulmon_de_hierro", 26),
            ("Cadu", "Atacante", "DEL", 61, None, 28),
            ("Alisson", "Mineiro", "DEL", 60, None, 31),
            ("Deyverson", "Brasa", "DEL", 59, "regateador", 32),
        ],
    },
    "Vasco da Gama B": {
        "ciudad": "Rio de Janeiro",
        "estrellas": 2.5,
        "estilo_dt": "cruyffismo",
        "balance": 6_800_000,
        "jugadores": [
            ("Léo", "Jardim", "POR", 63, None, 28),
            ("Paulo", "Henrique", "DEF", 62, "rustico", 28),
            ("Léandro", "Graxaim", "DEF", 61, None, 27),
            ("Maicon", "Pirulito", "DEF", 60, "pulmon_de_hierro", 30),
            ("Raul", "Cáceres", "DEF", 59, None, 30),
            ("Lucas", "Pitbull", "DEF", 58, None, 27),
            ("José", "Welison", "DEF", 57, None, 26),
            ("Lyncon", "Lateral", "DEF", 56, None, 22),
            ("Mateus", "Diniz", "DEF", 55, None, 24),
            ("Hugo", "Moura", "MED", 63, None, 25),
            ("Sforza", "Volante", "MED", 62, None, 28),
            ("Praxedes", "Volante", "MED", 61, None, 21),
            ("Lucas", "Eduardo", "MED", 60, "pulmon_de_hierro", 27),
            ("Barros", "Volante", "MED", 59, None, 24),
            ("De", "Arrascaeta", "MED", 58, "regateador", 30),
            ("Otero", "Vinotinto", "MED", 57, None, 28),
            ("Bruno", "Tubarão", "MED", 56, None, 23),
            ("Praxedes", "Bola", "MED", 55, None, 22),
            ("Adson", "Bexiga", "MED", 54, None, 24),
            ("Vegetti", "Pirata", "DEL", 63, "regateador", 35),
            ("Payet", "Francês", "DEL", 62, None, 36),
            ("Adson", "Cria", "DEL", 61, "pulmon_de_hierro", 24),
            ("Rayan", "Promessa", "DEL", 60, None, 18),
            ("Pablo", "Vegetti", "DEL", 59, None, 32),
            ("Lucas", "Ribamar", "DEL", 58, "regateador", 26),
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
        id_base = 33000
        for nombre, datos in PLANTILLAS_2A.items():
            eq = _construir_equipo(nombre, datos, id_base)
            equipos.append(eq)
            id_base += 100
        liga = Liga(
            nombre="Brasileirao Parodia - Série B",
            tipo="brasil",
            equipos=equipos,
            num_jornadas=10,
            division=2,
            jornada_actual=1,
        )
        logger.info(f"2ª división Brasil cargada: {len(equipos)} equipos, "
                     f"{sum(len(e.jugadores) for e in equipos)} jugadores totales")
        return liga
    except Exception as e:
        logger.error(f"Error al construir 2ª división Brasil: {e}")
        return Liga(nombre="2ª Brasil (error)", tipo="brasil", equipos=[], num_jornadas=10, division=2)