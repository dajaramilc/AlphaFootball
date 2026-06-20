# -*- coding: utf-8 -*-
"""
Alpha Football — POOLS INTERNACIONALES (v0.8.8: plantillas reales).

Expone los equipos de la Copa Libertadores y la Champions League con plantillas
de jugadores REALES parodiados (OVR y edad fieles, mismo estilo que las ligas en
`data/premier.py`), en vez del relleno sintético anterior.

API:
    - DATOS_LIBERTADORES / DATOS_CHAMPIONS : datos crudos por club.
    - get_pool_libertadores() / get_pool_champions() : devuelven COPIAS FRESCAS
      de los Equipo (espejo de data/<liga>.get_liga()), para que el envejecimiento
      pasivo por temporada no se acumule sobre los globals del módulo.
    - POOL_LIBERTADORES / POOL_CHAMPIONS : instancias base (compatibilidad: las usa
      `copa_screen.encontrar_equipo_copa` como fallback por nombre).
    - _generar_jugadores_equipo(...) : se conserva para el relleno ficticio de copa.
"""

from __future__ import annotations

import logging
import random
from alpha_football.models import Equipo, Jugador

logger = logging.getLogger(__name__)

RASGOS = ["regateador", "lider", "rustico", "pulmon_de_hierro"]


def _atributos_exactos(ovr: int, posicion: str) -> tuple[int, int, int, int, int]:
    """
    Genera los 5 atributos (ataque, defensa, fisico, tecnica, mental) por posición
    garantizando que el promedio entero sea EXACTAMENTE `ovr` (misma técnica que
    premier.generar_atributos_por_posicion).
    """
    ovr_obj = min(max(int(ovr), 40), 99)
    if posicion == "POR":
        atributos = [15, ovr_obj + 15, ovr_obj + 5, ovr_obj - 10, ovr_obj + 10]
    elif posicion == "DEF":
        atributos = [ovr_obj - 25, ovr_obj + 15, ovr_obj + 10, ovr_obj - 10, ovr_obj + 10]
    elif posicion == "MED":
        atributos = [ovr_obj - 5, ovr_obj - 5, ovr_obj, ovr_obj + 10, ovr_obj]
    else:  # DEL
        atributos = [ovr_obj + 15, ovr_obj - 25, ovr_obj + 5, ovr_obj + 10, ovr_obj - 5]

    atributos = [max(10, min(99, v)) for v in atributos]
    objetivo = ovr_obj * 5
    for _ in range(60):
        actual = sum(atributos)
        if actual == objetivo:
            break
        paso = 1 if objetivo > actual else -1
        indices = [0, 1, 2, 3, 4]
        random.shuffle(indices)
        for idx in indices:
            nuevo = atributos[idx] + paso
            if 10 <= nuevo <= 99:
                atributos[idx] = nuevo
                break
    return tuple(atributos)  # type: ignore


def _construir_jugadores(lista_tuplas: list, id_start: int) -> list[Jugador]:
    """Construye los Jugador reales desde tuplas (nombre, apellido, pos, ovr, rasgo, edad)."""
    jugadores = []
    for i, datos in enumerate(lista_tuplas):
        try:
            nombre, apellido, pos, ovr, rasgo, edad = datos
        except Exception:
            # Tolerante: tupla mal formada -> jugador de banca neutro.
            nombre, apellido, pos, ovr, rasgo, edad = ("Sub", f"Banca {i}", "MED", 65, None, 24)
        atk, dfs, fis, tec, men = _atributos_exactos(int(ovr), pos)
        jugadores.append(Jugador(
            nombre=nombre, apellido=apellido, posicion=pos,
            ataque=atk, defensa=dfs, fisico=fis, tecnica=tec, mental=men,
            moral=70, rasgo=rasgo, edad=int(edad), id=id_start + i,
        ))
    return jugadores


def _generar_jugadores_equipo(ovr_promedio: int, id_start: int) -> list[Jugador]:
    """
    Genera una plantilla simplificada de 11 jugadores de RELLENO (sin nombres reales).
    Se conserva para el relleno ficticio que arma `copa_screen.inicializar_copa_si_falta`
    cuando faltan equipos para completar los 16 de la copa.
    """
    posiciones = ["POR"] + ["DEF"] * 4 + ["MED"] * 3 + ["DEL"] * 3
    nombres_pool = ["Nico", "Lucas", "Mateo", "Alex", "Diego", "Franco", "Felipe", "Lucho", "Santi", "Juan", "Pedro"]
    apellidos_pool = ["Falso", "Tronco", "Viejo", "Parodia", "Lento", "Roto", "Malo", "Gomez", "Lopez", "Perez", "Silva"]

    jugadores = []
    for i, pos in enumerate(posiciones):
        ovr = max(40, min(95, ovr_promedio + random.randint(-4, 4)))
        atk, dfs, fis, tec, men = _atributos_exactos(ovr, pos)
        rasgo = random.choice(RASGOS) if random.random() < 0.25 else None
        jugadores.append(Jugador(
            nombre=nombres_pool[i % len(nombres_pool)],
            apellido=apellidos_pool[i % len(apellidos_pool)] + f" {i}",
            posicion=pos, ataque=atk, defensa=dfs, fisico=fis, tecnica=tec, mental=men,
            moral=70, rasgo=rasgo, edad=random.randint(20, 31), id=id_start + i,
        ))
    return jugadores


# ════════════════════════════════════════════════════════════════════════════
# DATOS REALES (parodiados) — formato por club:
#   "Nombre Largo": {ciudad, estrellas, estilo_dt, balance(crudo),
#                    jugadores: [(nombre, apellido, pos, ovr, rasgo, edad), ...]}
# El balance crudo se escala con market.BUDGET_SCALE en el builder.
# ════════════════════════════════════════════════════════════════════════════

DATOS_LIBERTADORES = {
    "Penarol Roto": {
        "ciudad": "Montevideo", "estrellas": 3.5, "estilo_dt": "haramball", "balance": 8000000,
        "jugadores": [
            ("Washington", "Aguerre-muro", "POR", 74, "lider", 34),
            ("Martin", "Campana", "POR", 68, None, 35),
            ("Guzman", "Rodriguez", "DEF", 72, "lider", 33),
            ("Javier", "Mendez", "DEF", 70, None, 27),
            ("Pedro", "Milans", "DEF", 69, None, 28),
            ("Leonardo", "Coelho", "DEF", 70, "rustico", 26),
            ("Nahuel", "Herrera", "DEF", 68, None, 23),
            ("Jaime", "Baez", "MED", 72, None, 31),
            ("Eric", "Remedi", "MED", 71, None, 29),
            ("Ignacio", "Sosa", "MED", 70, None, 27),
            ("Leonardo", "Fernandez-crack", "MED", 78, "regateador", 26),
            ("Rodrigo", "Perez", "MED", 68, None, 24),
            ("Maxi", "Silvera", "DEL", 73, None, 29),
            ("David", "Terans", "DEL", 72, "regateador", 31),
            ("Diego", "Garcia", "DEL", 70, None, 27),
        ],
    },
    "Nacionall de Montevideo": {
        "ciudad": "Montevideo", "estrellas": 3.5, "estilo_dt": "cruyffismo", "balance": 7500000,
        "jugadores": [
            ("Sergio", "Rochet-tapa", "POR", 76, "lider", 31),
            ("Luis", "Mejia", "POR", 70, None, 33),
            ("Sebastian", "Coates-torre", "DEF", 76, "rustico", 34),
            ("Nicolas", "Marichal", "DEF", 71, None, 25),
            ("Alfonso", "Trezza", "DEF", 68, None, 24),
            ("Lucas", "Rodriguez", "DEF", 67, None, 23),
            ("Christian", "Almeida", "DEF", 66, None, 22),
            ("Felipe", "Carballo", "MED", 73, None, 27),
            ("Christian", "Oliveira", "MED", 71, None, 28),
            ("Mauricio", "Pereyra", "MED", 72, "lider", 34),
            ("Juan", "DeLosSantos", "MED", 70, None, 23),
            ("Gonzalo", "Carneiro", "DEL", 70, None, 29),
            ("Luciano", "Rodriguez-joya", "DEL", 72, "regateador", 21),
            ("Emiliano", "Ancheta", "DEL", 67, None, 22),
        ],
    },
    "Colo Colo Roto": {
        "ciudad": "Santiago", "estrellas": 3.5, "estilo_dt": "flickismo", "balance": 9000000,
        "jugadores": [
            ("Brayan", "Cortes", "POR", 74, None, 29),
            ("Fernando", "De Paul", "POR", 68, None, 35),
            ("Maximiliano", "Falcon", "DEF", 73, "rustico", 27),
            ("Alan", "Saldivia", "DEF", 71, None, 24),
            ("Emiliano", "Amor", "DEF", 70, None, 30),
            ("Oscar", "Opazo", "DEF", 70, None, 34),
            ("Erick", "Wiemberg", "DEF", 68, None, 30),
            ("Esteban", "Pavez", "MED", 72, "lider", 34),
            ("Vicente", "Pizarro", "MED", 73, None, 22),
            ("Arturo", "Vidal-king", "MED", 78, "pulmon_de_hierro", 37),
            ("Claudio", "Aquino", "MED", 71, None, 28),
            ("Victor", "Mendez", "MED", 71, None, 29),
            ("Javier", "Correa", "DEL", 72, None, 30),
            ("Lucas", "Cepeda", "DEL", 72, "regateador", 22),
            ("Salomon", "Rodriguez", "DEL", 69, None, 26),
        ],
    },
    "Olimpia Abuelo": {
        "ciudad": "Asuncion", "estrellas": 3.5, "estilo_dt": "haramball", "balance": 7000000,
        "jugadores": [
            ("Gaspar", "Servio", "POR", 71, None, 37),
            ("Alfredo", "Aguilar", "POR", 70, None, 28),
            ("Junior", "Barreto", "DEF", 69, None, 28),
            ("Ivan", "Torres", "DEF", 68, None, 31),
            ("Saul", "Salcedo", "DEF", 70, "rustico", 27),
            ("Yostin", "Salinas", "DEF", 67, None, 24),
            ("Abel", "Paredes", "DEF", 66, None, 22),
            ("Ivan", "Leguizamon", "MED", 68, None, 26),
            ("Hugo", "Quintana", "MED", 68, None, 27),
            ("Richard", "Ortiz", "MED", 70, "lider", 32),
            ("Derlis", "Gonzalez-crack", "MED", 74, "regateador", 30),
            ("Walter", "Gonzalez", "DEL", 70, None, 30),
            ("Guillermo", "Paiva", "DEL", 70, None, 26),
            ("Tacuara", "Cardozo-gol", "DEL", 71, "lider", 41),
        ],
    },
    "Barcelona Falso de Guayaquil": {
        "ciudad": "Guayaquil", "estrellas": 3.5, "estilo_dt": "cruyffismo", "balance": 8500000,
        "jugadores": [
            ("Javier", "Burrai", "POR", 72, None, 37),
            ("Gilmar", "Napa", "POR", 66, None, 24),
            ("Luca", "Sosa", "DEF", 69, None, 27),
            ("Mario", "Pineida", "DEF", 70, None, 32),
            ("Xavier", "Arreaga", "DEF", 70, "rustico", 30),
            ("Gabriel", "Cortez", "DEF", 67, None, 26),
            ("Anibal", "Chala", "DEF", 68, None, 27),
            ("Damian", "Diaz-bicho", "MED", 74, "regateador", 38),
            ("Nilson", "Angulo", "MED", 70, None, 21),
            ("Joao", "Rojas", "MED", 70, None, 31),
            ("Sergio", "Lopez", "MED", 67, None, 25),
            ("Janner", "Corozo", "DEL", 69, None, 24),
            ("Allen", "Obando", "DEL", 71, "regateador", 20),
            ("Jhon", "Cifuente", "DEL", 70, None, 31),
        ],
    },
    "Liga de Quito Rota": {
        "ciudad": "Quito", "estrellas": 3.8, "estilo_dt": "anchelottismo", "balance": 11000000,
        "jugadores": [
            ("Alexander", "Dominguez-pulpo", "POR", 75, "lider", 37),
            ("Gonzalo", "Valle", "POR", 68, None, 27),
            ("Jose", "Quintero", "DEF", 70, None, 26),
            ("Facundo", "Rodriguez", "DEF", 70, None, 25),
            ("Ricardo", "Ade", "DEF", 71, "rustico", 28),
            ("Leonel", "Quinonez", "DEF", 69, None, 29),
            ("Dario", "Aimar", "DEF", 68, None, 23),
            ("Sebastian", "Gonzalez", "MED", 71, None, 28),
            ("Jhojan", "Julio", "MED", 71, "regateador", 24),
            ("Ezequiel", "Piovi", "MED", 72, None, 29),
            ("Gabriel", "Villamil", "MED", 71, None, 24),
            ("Mauricio", "Martinez", "MED", 70, None, 28),
            ("Alex", "Arce-gol", "DEL", 74, None, 32),
            ("Lisandro", "Alzugaray", "DEL", 71, None, 29),
            ("Jeison", "Medina", "DEL", 69, None, 27),
        ],
    },
    "Bolivar Sin Aire": {
        "ciudad": "La Paz", "estrellas": 3.5, "estilo_dt": "haramball", "balance": 6500000,
        "jugadores": [
            ("Carlos", "Lampe-muro", "POR", 73, "lider", 37),
            ("Ruben", "Cordano", "POR", 66, None, 27),
            ("Jose", "Sagredo", "DEF", 67, None, 28),
            ("Luis", "Haquin", "DEF", 70, "rustico", 27),
            ("Jefferson", "Tavares", "DEF", 68, None, 26),
            ("Diego", "Bejarano", "DEF", 68, None, 31),
            ("Hector", "Cuellar", "DEF", 66, None, 23),
            ("Leonel", "Justiniano", "MED", 70, None, 24),
            ("Patricio", "Rodriguez", "MED", 71, None, 30),
            ("Robson", "Matheus", "MED", 70, None, 27),
            ("Ramiro", "Vaca", "MED", 71, "regateador", 29),
            ("Francisco", "da Costa", "DEL", 70, None, 25),
            ("Carmelo", "Algaranaz", "DEL", 70, None, 26),
            ("Maximiliano", "Ramirez", "DEL", 69, None, 27),
        ],
    },
    "Universitario de la U": {
        "ciudad": "Lima", "estrellas": 3.2, "estilo_dt": "cruyffismo", "balance": 6000000,
        "jugadores": [
            ("Sebastian", "Britos", "POR", 71, None, 37),
            ("Diego", "Romero", "POR", 67, None, 24),
            ("Aldo", "Corzo", "DEF", 70, "lider", 35),
            ("Williams", "Riveros", "DEF", 69, None, 32),
            ("Matias", "Di Benedetto", "DEF", 70, "rustico", 32),
            ("Andy", "Polo", "DEF", 69, None, 30),
            ("Hugo", "Ancajima", "DEF", 66, None, 23),
            ("Jairo", "Concha", "MED", 71, None, 25),
            ("Martin", "Perez-Guedes", "MED", 71, None, 28),
            ("Rodrigo", "Urena", "MED", 70, "rustico", 31),
            ("Horacio", "Calcaterra", "MED", 69, None, 35),
            ("Edison", "Flores-orejas", "MED", 72, "regateador", 30),
            ("Alex", "Valera-gol", "DEL", 73, None, 28),
            ("Jose", "Rivera", "DEL", 68, None, 22),
            ("Diego", "Churin", "DEL", 69, None, 34),
        ],
    },
    "Boca Amargo": {
        "ciudad": "Buenos Aires", "estrellas": 4.3, "estilo_dt": "haramball", "balance": 18000000,
        "jugadores": [
            ("Sergio", "Romero-chiquito", "POR", 77, "lider", 37),
            ("Leandro", "Brey", "POR", 70, None, 22),
            ("Marcos", "Rojo-rustico", "DEF", 75, "rustico", 34),
            ("Nicolas", "Figal", "DEF", 73, None, 30),
            ("Luis", "Advincula", "DEF", 76, "pulmon_de_hierro", 34),
            ("Lautaro", "Blanco", "DEF", 71, None, 25),
            ("Cristian", "Lema", "DEF", 70, None, 33),
            ("Cristian", "Medina", "MED", 77, "regateador", 22),
            ("Pol", "Fernandez", "MED", 74, None, 33),
            ("Kevin", "Zenon", "MED", 75, None, 23),
            ("Jorman", "Campuzano", "MED", 71, None, 28),
            ("Ignacio", "Miramon", "MED", 70, None, 23),
            ("Edinson", "Cavani-matador", "DEL", 79, "lider", 37),
            ("Miguel", "Merentiel", "DEL", 76, None, 28),
            ("Exequiel", "Zeballos", "DEL", 73, "regateador", 22),
            ("Brian", "Aguirre", "DEL", 71, None, 24),
        ],
    },
    "Palmeirras": {
        "ciudad": "Sao Paulo", "estrellas": 4.5, "estilo_dt": "flickismo", "balance": 22000000,
        "jugadores": [
            ("Weverton", "Pereira", "POR", 78, "lider", 36),
            ("Marcelo", "Lomba", "POR", 70, None, 37),
            ("Gustavo", "Gomez-capitan", "DEF", 79, "lider", 31),
            ("Murilo", "Cerqueira", "DEF", 77, "rustico", 27),
            ("Joaquin", "Piquerez", "DEF", 78, "pulmon_de_hierro", 26),
            ("Marcos", "Rocha", "DEF", 72, None, 35),
            ("Vanderlan", "Silva", "DEF", 70, None, 22),
            ("Ze", "Rafael", "MED", 75, None, 31),
            ("Anibal", "Moreno", "MED", 76, None, 25),
            ("Richard", "Rios", "MED", 78, "regateador", 24),
            ("Raphael", "Veiga", "MED", 79, "lider", 29),
            ("Mauricio", "Goncalves", "MED", 74, None, 24),
            ("Estevao", "Mensajito", "DEL", 81, "regateador", 17),
            ("Jose", "Flaco-Lopez", "DEL", 75, None, 24),
            ("Dudu", "Pereira", "DEL", 76, "regateador", 32),
            ("Rony", "Silva", "DEL", 75, None, 29),
        ],
    },
}

DATOS_CHAMPIONS = {
    "Bayerna de Munich": {
        "ciudad": "Munich", "estrellas": 4.8, "estilo_dt": "flickismo", "balance": 50000000,
        "jugadores": [
            ("Manuel", "Neuer-muro", "POR", 86, "lider", 38),
            ("Sven", "Ulreich", "POR", 75, None, 36),
            ("Dayot", "Upamecano", "DEF", 84, "rustico", 26),
            ("Kim", "Minjae-roto", "DEF", 84, "rustico", 28),
            ("Alphonso", "Davies-cohete", "DEF", 85, "pulmon_de_hierro", 24),
            ("Joshua", "Kimmichismo", "DEF", 87, "lider", 29),
            ("Raphael", "Guerreirito", "DEF", 80, None, 31),
            ("Konrad", "Laimer-corre", "DEF", 80, "pulmon_de_hierro", 27),
            ("Jamal", "Musialazo", "MED", 87, "regateador", 22),
            ("Leon", "Goretzka-gym", "MED", 83, None, 29),
            ("Aleksandar", "Pavlovic", "MED", 80, None, 21),
            ("Joao", "Palhinha-tractor", "MED", 83, "rustico", 29),
            ("Harry", "Kane-gol", "DEL", 89, "lider", 31),
            ("Leroy", "Sane-luz", "DEL", 85, "regateador", 29),
            ("Serge", "Gnabry", "DEL", 83, None, 29),
            ("Kingsley", "Coman-fino", "DEL", 84, "regateador", 28),
            ("Michael", "Olise-mago", "DEL", 84, "regateador", 23),
        ],
    },
    "Borussia Dormund": {
        "ciudad": "Dortmund", "estrellas": 4.3, "estilo_dt": "cruyffismo", "balance": 35000000,
        "jugadores": [
            ("Gregor", "Kobel-muro", "POR", 85, None, 27),
            ("Alexander", "Meyer", "POR", 72, None, 34),
            ("Nico", "Schlotterbeck", "DEF", 83, "rustico", 25),
            ("Niklas", "Sule-tanque", "DEF", 82, "rustico", 29),
            ("Julian", "Ryerson", "DEF", 79, "pulmon_de_hierro", 27),
            ("Waldemar", "Anton", "DEF", 80, None, 28),
            ("Ramy", "Bensebaini", "DEF", 79, None, 29),
            ("Yan", "Couto", "DEF", 79, None, 22),
            ("Emre", "Can-capitan", "MED", 81, "lider", 30),
            ("Marcel", "Sabitzer", "MED", 81, None, 30),
            ("Felix", "Nmecha", "MED", 79, None, 24),
            ("Pascal", "Gross", "MED", 80, None, 33),
            ("Julian", "Brandt-mago", "MED", 83, "regateador", 28),
            ("Serhou", "Guirassy-gol", "DEL", 84, "pulmon_de_hierro", 28),
            ("Karim", "Adeyemi-rayo", "DEL", 81, "regateador", 23),
            ("Donyell", "Malen", "DEL", 80, None, 26),
            ("Maximilian", "Beier", "DEL", 78, None, 22),
        ],
    },
    "Piamonte Calcio": {
        "ciudad": "Turin", "estrellas": 4.5, "estilo_dt": "haramball", "balance": 40000000,
        "jugadores": [
            ("Michele", "Di Gregorio", "POR", 83, None, 27),
            ("Mattia", "Perin", "POR", 78, None, 32),
            ("Gleison", "Bremer-muro", "DEF", 85, "rustico", 27),
            ("Federico", "Gatti", "DEF", 80, "rustico", 26),
            ("Pierre", "Kalulu", "DEF", 81, None, 24),
            ("Andrea", "Cambiaso", "DEF", 81, "pulmon_de_hierro", 24),
            ("Danilo", "Capitano", "DEF", 80, "lider", 33),
            ("Lloyd", "Kelly", "DEF", 78, None, 26),
            ("Manuel", "Locatelli", "MED", 82, "lider", 27),
            ("Khephren", "Thuram", "MED", 82, None, 23),
            ("Teun", "Koopmeiners", "MED", 83, None, 27),
            ("Weston", "McKennie", "MED", 80, "pulmon_de_hierro", 26),
            ("Douglas", "Luiz", "MED", 81, None, 26),
            ("Dusan", "Vlahovic-gol", "DEL", 84, None, 25),
            ("Kenan", "Yildiz-joya", "DEL", 81, "regateador", 19),
            ("Nico", "Gonzalez", "DEL", 81, "regateador", 26),
            ("Timothy", "Weah", "DEL", 78, None, 24),
        ],
    },
    "Inter de Milan Roto": {
        "ciudad": "Milan", "estrellas": 4.6, "estilo_dt": "anchelottismo", "balance": 45000000,
        "jugadores": [
            ("Yann", "Sommer-gato", "POR", 84, None, 35),
            ("Josep", "Martinez", "POR", 76, None, 26),
            ("Alessandro", "Bastoni-clase", "DEF", 86, "rustico", 25),
            ("Francesco", "Acerbi", "DEF", 82, "lider", 36),
            ("Benjamin", "Pavard", "DEF", 83, None, 28),
            ("Stefan", "de Vrij", "DEF", 80, None, 32),
            ("Yann", "Bisseck", "DEF", 79, "rustico", 24),
            ("Carlos", "Augusto", "DEF", 79, None, 25),
            ("Nicolo", "Barella-motor", "MED", 87, "pulmon_de_hierro", 27),
            ("Hakan", "Calhanoglu", "MED", 86, "lider", 30),
            ("Henrikh", "Mkhitaryan", "MED", 81, None, 35),
            ("Davide", "Frattesi", "MED", 81, None, 25),
            ("Federico", "Dimarco-zurda", "DEF", 84, "regateador", 27),
            ("Denzel", "Dumfries", "DEF", 82, "pulmon_de_hierro", 28),
            ("Lautaro", "Martinez-toro", "DEL", 88, "lider", 27),
            ("Marcus", "Thuram", "DEL", 85, None, 27),
            ("Mehdi", "Taremi", "DEL", 80, None, 32),
        ],
    },
    "Milan Abuelo": {
        "ciudad": "Milan", "estrellas": 4.2, "estilo_dt": "anchelottismo", "balance": 30000000,
        "jugadores": [
            ("Mike", "Maignan-muro", "POR", 86, "lider", 29),
            ("Marco", "Sportiello", "POR", 74, None, 32),
            ("Theo", "Hernandez-cohete", "DEF", 85, "pulmon_de_hierro", 27),
            ("Fikayo", "Tomori", "DEF", 82, "rustico", 26),
            ("Malick", "Thiaw", "DEF", 80, None, 23),
            ("Matteo", "Gabbia", "DEF", 78, None, 25),
            ("Strahinja", "Pavlovic", "DEF", 79, "rustico", 23),
            ("Emerson", "Royal", "DEF", 78, None, 25),
            ("Tijjani", "Reijnders", "MED", 84, None, 26),
            ("Youssouf", "Fofana", "MED", 81, None, 25),
            ("Ruben", "Loftus-Cheek", "MED", 80, None, 28),
            ("Yunus", "Musah", "MED", 78, "pulmon_de_hierro", 22),
            ("Christian", "Pulisic-USA", "MED", 84, "regateador", 26),
            ("Rafael", "Leao-turbo", "DEL", 86, "regateador", 25),
            ("Alvaro", "Morata", "DEL", 81, "lider", 32),
            ("Tammy", "Abraham", "DEL", 78, None, 27),
            ("Samuel", "Chukwueze", "DEL", 78, "regateador", 25),
        ],
    },
    "Paris Saint-Germain Sin Champions": {
        "ciudad": "Paris", "estrellas": 4.7, "estilo_dt": "cruyffismo", "balance": 60000000,
        "jugadores": [
            ("Gianluigi", "Donnarumma-muro", "POR", 87, None, 25),
            ("Matvey", "Safonov", "POR", 78, None, 25),
            ("Marquinhos", "Capitano", "DEF", 86, "lider", 30),
            ("Willian", "Pacho", "DEF", 82, "rustico", 23),
            ("Lucas", "Hernandez", "DEF", 82, None, 28),
            ("Nuno", "Mendes-cohete", "DEF", 84, "pulmon_de_hierro", 22),
            ("Achraf", "Hakimi-flecha", "DEF", 85, "pulmon_de_hierro", 26),
            ("Vitinha", "Motor", "MED", 85, None, 24),
            ("Warren", "Zaire-Emery", "MED", 82, None, 18),
            ("Joao", "Neves", "MED", 84, None, 20),
            ("Fabian", "Ruiz", "MED", 83, None, 28),
            ("Lee", "Kang-in", "MED", 80, "regateador", 23),
            ("Ousmane", "Dembele-mago", "DEL", 85, "regateador", 27),
            ("Bradley", "Barcola", "DEL", 83, "regateador", 22),
            ("Khvicha", "Kvaratskhelia-magia", "DEL", 86, "regateador", 23),
            ("Goncalo", "Ramos", "DEL", 81, None, 23),
            ("Desire", "Doue", "DEL", 80, "regateador", 19),
        ],
    },
    "Benfica Maldito": {
        "ciudad": "Lisboa", "estrellas": 4.0, "estilo_dt": "flickismo", "balance": 25000000,
        "jugadores": [
            ("Anatoliy", "Trubin", "POR", 82, None, 23),
            ("Samuel", "Soares", "POR", 70, None, 22),
            ("Nicolas", "Otamendi-general", "DEF", 81, "lider", 36),
            ("Antonio", "Silva", "DEF", 81, "rustico", 21),
            ("Alexander", "Bah", "DEF", 78, "pulmon_de_hierro", 27),
            ("Alvaro", "Carreras", "DEF", 79, None, 22),
            ("Tomas", "Araujo", "DEF", 78, None, 22),
            ("Orkun", "Kokcu", "MED", 81, None, 24),
            ("Florentino", "Luis", "MED", 80, "rustico", 25),
            ("Fredrik", "Aursnes", "MED", 80, None, 29),
            ("Renato", "Sanches", "MED", 78, None, 27),
            ("Kerem", "Akturkoglu", "MED", 80, "regateador", 26),
            ("Vangelis", "Pavlidis", "DEL", 80, None, 26),
            ("Angel", "DiMaria-fideo", "DEL", 83, "regateador", 37),
            ("Andreas", "Schjelderup", "DEL", 77, None, 20),
            ("Zeki", "Amdouni", "DEL", 76, None, 24),
        ],
    },
    "Puerto FC": {
        "ciudad": "Oporto", "estrellas": 4.0, "estilo_dt": "haramball", "balance": 22000000,
        "jugadores": [
            ("Diogo", "Costa-muro", "POR", 84, "lider", 25),
            ("Claudio", "Ramos", "POR", 72, None, 33),
            ("Nehuen", "Perez", "DEF", 80, "rustico", 24),
            ("Ivan", "Marcano", "DEF", 76, None, 37),
            ("Zaidu", "Sanusi", "DEF", 78, "pulmon_de_hierro", 27),
            ("Joao", "Mario", "DEF", 79, None, 31),
            ("Wendell", "Silva", "DEF", 77, None, 31),
            ("Tiago", "Djalo", "DEF", 77, None, 24),
            ("Alan", "Varela", "MED", 81, None, 23),
            ("Stephen", "Eustaquio", "MED", 80, "pulmon_de_hierro", 28),
            ("Marko", "Grujic", "MED", 78, "rustico", 28),
            ("Pepe", "Brasil", "MED", 81, "regateador", 27),
            ("Fabio", "Vieira", "MED", 79, None, 24),
            ("Samu", "Aghehowa", "DEL", 80, "pulmon_de_hierro", 20),
            ("Galeno", "Turbo", "DEL", 81, "regateador", 27),
            ("Danny", "Namaso", "DEL", 75, None, 24),
            ("William", "Gomes", "DEL", 75, "regateador", 19),
        ],
    },
}

# v0.7: nombre corto (anti-solapamiento en tabla/bracket de copa).
_NOMBRES_CORTOS_INTL = {
    "Penarol Roto": "Peñarol", "Nacionall de Montevideo": "Nacional URU", "Colo Colo Roto": "Colo Colo",
    "Olimpia Abuelo": "Olimpia", "Barcelona Falso de Guayaquil": "Barcelona SC", "Liga de Quito Rota": "LDU Quito",
    "Bolivar Sin Aire": "Bolívar", "Universitario de la U": "Universitario", "Boca Amargo": "Boca",
    "Palmeirras": "Palmeiras",
    "Bayerna de Munich": "Bayerna", "Borussia Dormund": "Dormund", "Piamonte Calcio": "Piamonte",
    "Inter de Milan Roto": "Inter", "Milan Abuelo": "Milan", "Paris Saint-Germain Sin Champions": "PSG",
    "Benfica Maldito": "Benfica", "Puerto FC": "Puerto",
}


def _budget_scale() -> float:
    """Factor de escalado de presupuesto, igual que las ligas (market.BUDGET_SCALE)."""
    try:
        from alpha_football.market import BUDGET_SCALE
        return float(BUDGET_SCALE)
    except Exception:
        return 8.0


def _construir_pool(datos_dict: dict, id_base: int) -> list[Equipo]:
    """Construye una lista FRESCA de Equipo desde un dict de datos crudos."""
    bs = _budget_scale()
    equipos = []
    for idx, (nombre, meta) in enumerate(datos_dict.items()):
        try:
            team_id = id_base + idx * 60
            jugadores = _construir_jugadores(meta.get("jugadores", []), team_id)
            eq = Equipo(
                nombre=nombre,
                ciudad=meta.get("ciudad", "Internacional"),
                estrellas=meta.get("estrellas", 3.5),
                estilo_dt=meta.get("estilo_dt", "cruyffismo"),
                balance=int(meta.get("balance", 10000000) * bs),
                jugadores=jugadores,
            )
            eq.nombre_corto = _NOMBRES_CORTOS_INTL.get(nombre, "")
            equipos.append(eq)
        except Exception as e_eq:
            logger.warning(f"No se pudo construir el club internacional '{nombre}': {e_eq}")
    return equipos


def get_pool_libertadores() -> list[Equipo]:
    """Copia fresca de los clubes de la Copa Libertadores (para envejecer sin compoundear)."""
    return _construir_pool(DATOS_LIBERTADORES, 600)


def get_pool_champions() -> list[Equipo]:
    """Copia fresca de los clubes de la Champions League."""
    return _construir_pool(DATOS_CHAMPIONS, 1200)


# Instancias base (compatibilidad: encontrar_equipo_copa las usa como fallback por nombre).
POOL_LIBERTADORES = get_pool_libertadores()
POOL_CHAMPIONS = get_pool_champions()
