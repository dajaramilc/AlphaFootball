# -*- coding: utf-8 -*-
"""
v2.3 (Fase 4) — Datos de la 2ª DIVISIÓN Premier League (Inglaterra).
6 equipos parodiados, 25 jugadores cada uno (150 totales).
OVR ~60-75 (más alto que BetPlay 2ª pero más bajo que Premier 1ª).
"""
from __future__ import annotations

import logging
from alpha_football.models import Liga, Equipo, Jugador
from alpha_football.data.premier import generar_atributos_por_posicion

logger = logging.getLogger(__name__)

PLANTILLAS_2A = {
    "Burnley Express": {
        "ciudad": "Burnley",
        "estrellas": 3.0,
        "estilo_dt": "haramball",
        "balance": 11_000_000,
        "jugadores": [
            ("James", "Truckstop", "POR", 68, "lider", 30),
            ("Connor", "Stonewall", "DEF", 67, "rustico", 27),
            ("Joe", "Brickside", "DEF", 66, None, 25),
            ("Charlie", "Taylord", "DEF", 65, None, 24),
            ("Hannes", "Foggy", "DEF", 64, "pulmon_de_hierro", 26),
            ("Ameer", "Steelrod", "DEF", 63, None, 23),
            ("Lucas", "Pillar", "DEF", 62, None, 25),
            ("Vit", "Hammer", "DEF", 61, None, 24),
            ("Jordan", "Bench", "DEF", 60, None, 22),
            ("Josh", "Puntlong", "MED", 68, "regateador", 26),
            ("Sander", "Bergisch", "MED", 67, None, 24),
            ("Marcus", "Trappola", "MED", 66, "pulmon_de_hierro", 25),
            ("Jóhann", "Bergur", "MED", 65, None, 23),
            ("Hannibal", "Mejbriri", "MED", 64, None, 22),
            ("Aaron", "Ramseyram", "MED", 63, None, 24),
            ("Luca", "Koleosho", "MED", 62, None, 23),
            ("Wilson", "Odobert", "MED", 61, None, 22),
            ("Zian", "Flemming", "MED", 60, None, 21),
            ("Mike", "Trev", "MED", 59, None, 23),
            ("Lyle", "Fosterling", "DEL", 68, "regateador", 24),
            ("Zeki", "Amdouni", "DEL", 67, None, 26),
            ("Manuel", "Benson", "DEL", 66, "pulmon_de_hierro", 25),
            ("Nathan", "Redmond", "DEL", 65, None, 23),
            ("Jaidon", "Anthony", "DEL", 64, None, 24),
            ("Benson", "Manuel", "DEL", 63, "regateador", 22),
        ],
    },
    "Sheffield United-Aires": {
        "ciudad": "Sheffield",
        "estrellas": 3.0,
        "estilo_dt": "anchelottismo",
        "balance": 10_800_000,
        "jugadores": [
            ("Adam", "Stoneside", "POR", 67, None, 29),
            ("George", "Baldock", "DEF", 66, "rustico", 28),
            ("John", "Eganfield", "DEF", 65, None, 26),
            ("Jack", "Roboblade", "DEF", 64, "pulmon_de_hierro", 24),
            ("Chris", "Bashamer", "DEF", 63, None, 25),
            ("Max", "Loweprint", "DEF", 62, None, 23),
            ("Yasser", "Larouch", "DEF", 61, None, 24),
            ("Anel", "Ahmedhodžić", "DEF", 60, None, 22),
            ("Jayden", "Boglez", "DEF", 59, None, 23),
            ("Vinícius", "Souza", "MED", 67, "regateador", 25),
            ("Sander", "Berge-gill", "MED", 66, None, 24),
            ("Oliver", "Norwood", "MED", 65, "pulmon_de_hierro", 26),
            ("Tom", "Dawason", "MED", 64, None, 23),
            ("James", "Mcatee", "MED", 63, None, 24),
            ("Will", "Osulad", "MED", 62, None, 22),
            ("Riyad", "Brewster", "MED", 61, "regateador", 23),
            ("Billy", "Sharpel", "MED", 60, None, 25),
            ("Sydie", "Peckford", "MED", 59, None, 22),
            ("Andre", "Brooks", "MED", 58, None, 21),
            ("Oli", "McBurnie", "DEL", 67, None, 27),
            ("Rhian", "Brewers", "DEL", 66, "regateador", 24),
            ("Daniel", "Jebbison", "DEL", 65, None, 22),
            ("William", "Osula", "DEL", 64, "pulmon_de_hierro", 23),
            ("Tyrese", "Forrest", "DEL", 63, None, 24),
            ("Louie", "Marsh", "DEL", 62, "regateador", 21),
        ],
    },
    "Luton Towner": {
        "ciudad": "Luton",
        "estrellas": 2.5,
        "estilo_dt": "haramball",
        "balance": 9_200_000,
        "jugadores": [
            ("Thomas", "Kaminski", "POR", 65, None, 30),
            ("Dan", "Pottscreen", "DEF", 64, "rustico", 26),
            ("Tom", "Locklock", "DEF", 63, None, 25),
            ("Issa", "Kaboré", "DEF", 62, "pulmon_de_hierro", 24),
            ("Teden", "Mengi", "DEF", 61, None, 22),
            ("Amari", "Bellz", "DEF", 60, None, 25),
            ("Gabriel", "Osho", "DEF", 59, None, 23),
            ("Reece", "Burkel", "DEF", 58, None, 24),
            ("Mads", "Andersen", "DEF", 57, None, 22),
            ("Ross", "Barkleley", "MED", 65, "regateador", 26),
            ("Marvelous", "Nakamba", "MED", 64, None, 25),
            ("Albert", "Sambi", "MED", 63, None, 23),
            ("Pelly", "Ruddock", "MED", 62, "pulmon_de_hierro", 24),
            ("Jordan", "Clarkey", "MED", 61, None, 25),
            ("Tahith", "Chong", "MED", 60, None, 22),
            ("Luke", "Freeman", "MED", 59, None, 26),
            ("Henri", "Landsbury", "MED", 58, None, 23),
            ("Jake", "Bately", "MED", 57, None, 22),
            ("Allan", "Campbellish", "MED", 56, None, 21),
            ("Carlton", "Morris", "DEL", 65, "regateador", 26),
            ("Elijah", "Adebayor", "DEL", 64, None, 25),
            ("Joe", "Taylorish", "DEL", 63, None, 23),
            ("Cauley", "Woodrow", "DEL", 62, "pulmon_de_hierro", 24),
            ("Harry", "Cornick", "DEL", 61, None, 25),
            ("Adebayo", "Efoski", "DEL", 60, "regateador", 23),
        ],
    },
    "Leeds Champion": {
        "ciudad": "Leeds",
        "estrellas": 3.0,
        "estilo_dt": "cruyffismo",
        "balance": 10_500_000,
        "jugadores": [
            ("Karl", "Darloy", "POR", 67, None, 28),
            ("Pascal", "Struijk", "DEF", 66, "rustico", 26),
            ("Liam", "Coopland", "DEF", 65, None, 25),
            ("Ethan", "Ampadu", "DEF", 64, "pulmon_de_hierro", 24),
            ("Luke", "Aylink", "DEF", 63, None, 23),
            ("Junior", "Firpo", "DEF", 62, None, 26),
            ("Pascal", "Bockland", "DEF", 61, None, 25),
            ("Sam", "Byramd", "DEF", 60, None, 24),
            ("Charlie", "Cressley", "DEF", 59, None, 22),
            ("Tyler", "Adamus", "MED", 67, "regateador", 25),
            ("Ilia", "Gruevski", "MED", 66, None, 24),
            ("Ethan", "Graylee", "MED", 65, "pulmon_de_hierro", 23),
            ("Daniel", "Jamesy", "MED", 64, None, 24),
            ("Georginio", "Rutterd", "MED", 63, None, 22),
            ("Wilfried", "Gnontoy", "MED", 62, None, 26),
            ("Archie", "Gray", "MED", 61, None, 20),
            ("Mateo", "Josephs", "MED", 60, None, 21),
            ("Jamie", "Shackleton", "MED", 59, None, 23),
            ("Sam", "Greenwood", "MED", 58, None, 22),
            ("Joël", "Piroe", "DEL", 67, "regateador", 25),
            ("Patrick", "Bamford", "DEL", 66, None, 28),
            ("Crysencio", "Summervill", "DEL", 65, "pulmon_de_hierro", 23),
            ("Largie", "Ramazan", "DEL", 64, None, 24),
            ("Mateo", "Josephy", "DEL", 63, None, 22),
            ("Joe", "Gelhardt", "DEL", 62, "regateador", 21),
        ],
    },
    "Sunderland Til-I-Get-Back": {
        "ciudad": "Sunderland",
        "estrellas": 3.0,
        "estilo_dt": "flickismo",
        "balance": 10_200_000,
        "jugadores": [
            ("Anthony", "Patterson", "POR", 67, None, 27),
            ("Trai", "Humez", "DEF", 66, "rustico", 24),
            ("Dan", "Ballardz", "DEF", 65, None, 25),
            ("Luke", "O'Nien", "DEF", 64, "pulmon_de_hierro", 26),
            ("Jenson", "Seeltz", "DEF", 63, None, 22),
            ("Jack", "Diamond", "DEF", 62, None, 23),
            ("Niall", "Huggins", "DEF", 61, None, 22),
            ("Joe", "Andersons", "DEF", 60, None, 25),
            ("Dennis", "Cirkin", "DEF", 59, None, 21),
            ("Jobe", "Bellingham", "MED", 67, "regateador", 19),
            ("Dan", "Neilz", "MED", 66, None, 22),
            ("Pierre", "Ekwat", "MED", 65, None, 25),
            ("Corry", "Evansz", "MED", 64, "pulmon_de_hierro", 27),
            ("Jay", "Matete", "MED", 63, None, 21),
            ("Abdoullah", "Bailey", "MED", 62, None, 22),
            ("Patrick", "Roberts", "MED", 61, None, 25),
            ("Jack", "Clarkson", "MED", 60, None, 22),
            ("Elliot", "Emblet", "MED", 59, None, 21),
            ("Callum", "Styles", "MED", 58, None, 24),
            ("Jobe", "Bellinghamdel", "DEL", 67, "regateador", 22),
            ("Ross", "Stewart", "DEL", 66, None, 27),
            ("Ellis", "Simmsz", "DEL", 65, "pulmon_de_hierro", 23),
            ("Nazariy", "Rusnak", "DEL", 64, None, 25),
            ("Isaac", "Lihadji", "DEL", 63, None, 21),
            ("Mason", "Burton", "DEL", 62, "regateador", 22),
        ],
    },
    "Middlesbrough-ugh": {
        "ciudad": "Middlesbrough",
        "estrellas": 2.5,
        "estilo_dt": "anchelottismo",
        "balance": 9_800_000,
        "jugadores": [
            ("Gavin", "Bazunu", "POR", 66, None, 26),
            ("Tommy", "Smithy", "DEF", 65, "rustico", 27),
            ("Dael", "Fryz", "DEF", 64, None, 26),
            ("Anfernee", "Dijks", "DEF", 63, "pulmon_de_hierro", 24),
            ("Rav", "Bergj", "DEF", 62, None, 25),
            ("Luke", "Aylinger", "DEF", 61, None, 23),
            ("Paddy", "McNairz", "DEF", 60, None, 25),
            ("Ben", "Gibsony", "DEF", 59, None, 27),
            ("Jonathan", "Howsonz", "DEF", 58, None, 28),
            ("Hayden", "Hackney", "MED", 66, "regateador", 22),
            ("Jonny", "Howsonnet", "MED", 65, None, 30),
            ("Matt", "Cloughts", "MED", 64, None, 27),
            ("Daniel", "Barlaser", "MED", 63, "pulmon_de_hierro", 26),
            ("Marcus", "Forssy", "MED", 62, None, 29),
            ("Sam", "Greenwoody", "MED", 61, None, 22),
            ("Alex", "Morrison", "MED", 60, None, 23),
            ("Josh", "Coburny", "MED", 59, None, 22),
            ("Riley", "McGreego", "MED", 58, None, 21),
            ("Isaiah", "Jonesy", "MED", 57, None, 22),
            ("Chuba", "Akpomz", "DEL", 66, "regateador", 27),
            ("Tammy", "Abrahamz", "DEL", 65, None, 25),
            ("Sonny", "Bradbery", "DEL", 64, "pulmon_de_hierro", 24),
            ("Marcus", "Brewery", "DEL", 63, None, 22),
            ("Josh", "Coburnz", "DEL", 62, None, 23),
            ("Riley", "McGreey", "DEL", 61, "regateador", 22),
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
        id_base = 32000
        for nombre, datos in PLANTILLAS_2A.items():
            eq = _construir_equipo(nombre, datos, id_base)
            equipos.append(eq)
            id_base += 100
        liga = Liga(
            nombre="Premier League Parodia - Championship",
            tipo="premier",
            equipos=equipos,
            num_jornadas=10,
            division=2,
            jornada_actual=1,
        )
        logger.info(f"2ª división Premier cargada: {len(equipos)} equipos, "
                     f"{sum(len(e.jugadores) for e in equipos)} jugadores totales")
        return liga
    except Exception as e:
        logger.error(f"Error al construir 2ª división Premier: {e}")
        return Liga(nombre="2ª Premier (error)", tipo="premier", equipos=[], num_jornadas=10, division=2)