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
      `competiciones.equipo_por_nombre`, v3.8.0).
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
    Se conserva para los clubes que genera `competiciones.equipo_por_nombre` (v3.8.0)
    cuando un clasificado no está en ninguna liga ni en el banco.
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
    # v3.7.0 Uruguay/Ecuador: Peñarol y Nacional viven en data/uruguay.py; Barcelona SC y LDU en
    # data/ecuador.py. Fuera del banco (sin duplicados).
    "Colo Colo Roto": {
        "pais": "Chile", "ciudad": "Santiago", "estrellas": 3.5, "estilo_dt": "flickismo", "balance": 9000000,
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
            # v3.7.0 relleno copas: plantel a 20+
            ("Mauricio", "Isla-lateral-eterno", "DEF", 72, "pulmon_de_hierro", 37),
            ("Jonathan", "Villagra-albo", "DEF", 69, None, 24),
            ("Tomas", "Alarcon-alarma", "MED", 70, None, 26),
            ("Marcos", "Bolados-bolado", "MED", 70, "regateador", 29),
            ("Cristian", "Zavala-cacique", "DEL", 69, "regateador", 26),
        ],
    },
    "Olimpia Abuelo": {
        "pais": "Paraguay", "ciudad": "Asuncion", "estrellas": 3.5, "estilo_dt": "haramball", "balance": 7000000,
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
            # v3.7.0 relleno copas: plantel a 20+
            ("Mateo", "Gamarra-franjeado", "DEF", 67, None, 23),
            ("Gustavo", "Vargas-franja", "DEF", 66, None, 23),
            ("Alejandro", "Silva-uruguayo", "MED", 70, "regateador", 35),
            ("Diego", "Torres-decano", "MED", 67, None, 22),
            ("Marcos", "Gomez-franja", "MED", 66, "pulmon_de_hierro", 24),
            ("Facundo", "Bruera-bravo", "DEL", 69, None, 27),
        ],
    },
    "Bolivar Sin Aire": {
        "pais": "Bolivia", "ciudad": "La Paz", "estrellas": 3.5, "estilo_dt": "haramball", "balance": 6500000,
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
            # v3.7.0 relleno copas: plantel a 20+
            ("Jairo", "Quinteros-altitud", "DEF", 69, "rustico", 23),
            ("Carlos", "Melgar-cumbre", "MED", 67, None, 28),
            ("Fernando", "Saucedo-tokio", "MED", 68, None, 35),
            ("Lucas", "Chavez-oxigeno", "MED", 66, None, 23),
            ("Bruno", "Savio-altiplano", "DEL", 71, "regateador", 30),
            ("Martin", "Cauteruccio-paceno", "DEL", 69, None, 37),
        ],
    },
    "Universitario de la U": {
        "pais": "Perú", "ciudad": "Lima", "estrellas": 3.2, "estilo_dt": "cruyffismo", "balance": 6000000,
        "jugadores": [
            ("Sebastian", "Britos", "POR", 71, None, 37),
            ("Miguel", "Vargas-crema", "POR", 66, None, 24),
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
            # v3.7.0 relleno copas: plantel a 20+
            ("Anderson", "Santamaria-crema", "DEF", 68, "rustico", 33),
            ("Gustavo", "Dulanto-dulce", "DEF", 67, None, 29),
            ("Jorge", "Murrugarra-garra", "MED", 67, "pulmon_de_hierro", 28),
            ("Rodrigo", "Vilca-cremoso", "MED", 67, None, 26),
            ("Jairo", "Velez-rapidito", "DEL", 68, "regateador", 30),
        ],
    },
    # v3.7.0: Boca y Palmeiras viven en sus ligas (Boca Grande, Palmerinha); fuera del banco.
}

DATOS_CHAMPIONS = {
    "Bayerna de Munich": {
        "pais": "Alemania", "ciudad": "Munich", "estrellas": 4.8, "estilo_dt": "flickismo", "balance": 50000000,
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
            ("Serge", "Gnabry", "DEL", 83, None, 29),
            ("Michael", "Olise-mago", "DEL", 84, "regateador", 23),
            # v3.7.0 relleno copas: plantel a 20+
            ("Jonathan", "Tah-muralla", "DEF", 84, "rustico", 29),
            ("Sacha", "Boey-buey", "DEF", 78, None, 24),
            ("Tom", "Bischof-obispo", "MED", 79, None, 20),
            ("Lennart", "Karl-wunderkind", "MED", 76, "regateador", 17),
            ("Luis", "Diaz-guajiro", "DEL", 85, "regateador", 28),
        ],
    },
    "Borussia Dormund": {
        "pais": "Alemania", "ciudad": "Dortmund", "estrellas": 4.3, "estilo_dt": "cruyffismo", "balance": 35000000,
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
            # v3.7.0 relleno copas: plantel a 20+
            ("Salih", "Ozcan-ozono", "MED", 75, None, 27),
            ("Carney", "Chukwuemeka-trabalenguas", "MED", 77, None, 21),
            ("Fabio", "Silva-portugues", "DEL", 77, None, 23),
        ],
    },
    # v3.7.0: Juventus (Piamonte Calcio), Inter y Milan pasaron a data/seriea.py (Serie A).
    "Paris Saint-Germain Sin Champions": {
        "pais": "Francia", "ciudad": "Paris", "estrellas": 4.7, "estilo_dt": "cruyffismo", "balance": 60000000,
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
            # v3.7.0 relleno copas: plantel a 20+
            ("Lucas", "Chevalier-caballero", "POR", 82, None, 24),
            ("Ilya", "Zabarnyi-ucraniano", "DEF", 81, "rustico", 23),
            ("Lucas", "Beraldo-beraldito", "DEF", 78, None, 21),
            ("Senny", "Mayulu-joya", "MED", 75, None, 19),
        ],
    },
    "Benfica Maldito": {
        "pais": "Portugal", "ciudad": "Lisboa", "estrellas": 4.0, "estilo_dt": "flickismo", "balance": 25000000,
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
            # v3.7.0 relleno copas: plantel a 20+
            ("Samuel", "Dahl-sueco", "DEF", 76, None, 22),
            ("Leandro", "Barreiro-barrio", "MED", 77, "pulmon_de_hierro", 25),
            ("Enzo", "Barrenechea-barreno", "MED", 77, None, 24),
            ("Franjo", "Ivanovic-croata", "DEL", 76, None, 21),
        ],
    },
    "Puerto FC": {
        "pais": "Portugal", "ciudad": "Oporto", "estrellas": 4.0, "estilo_dt": "haramball", "balance": 22000000,
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
            # v3.7.0 relleno copas: plantel a 20+
            ("Victor", "Froholdt-danes", "MED", 77, None, 19),
            ("Gabri", "Veiga-gallego", "MED", 79, "regateador", 23),
            ("Luuk", "de Jong-veterano", "DEL", 76, "lider", 35),
        ],
    },
    # ── v3.7.0 relleno copas: clubes europeos para completar la Champions (RELLENO_CHAMPIONS) ──
    "Bayer Neverkusen": {
        "pais": "Alemania", "ciudad": "Leverkusen", "estrellas": 4.2, "estilo_dt": "fullbackismo", "balance": 30000000,
        "jugadores": [
            ("Mark", "Flekken-flan", "POR", 81, None, 32),
            ("Janis", "Blaswich", "POR", 74, None, 34),
            ("Edmond", "Tapsoba-tapon", "DEF", 82, "rustico", 26),
            ("Jeanuel", "Belocian-veloz", "DEF", 73, None, 20),
            ("Loic", "Bade-bache", "DEF", 80, None, 25),
            ("Alejandro", "Grimaldo-zurdazo", "DEF", 84, "regateador", 30),
            ("Lucas", "Vazquez-exmadridista", "DEF", 78, "pulmon_de_hierro", 34),
            ("Arthur", "Augusto-carrilero", "DEF", 75, None, 22),
            ("Exequiel", "Palacios-palacete", "MED", 82, None, 27),
            ("Robert", "Andrich-cresta", "MED", 80, "rustico", 31),
            ("Aleix", "Garcia-metronomo", "MED", 80, None, 28),
            ("Malik", "Tillman-till", "MED", 79, "regateador", 23),
            ("Ibrahim", "Maza-mazo", "MED", 76, None, 19),
            ("Equi", "Fernandez-equis", "MED", 77, None, 23),
            ("Patrik", "Schick-chic", "DEL", 82, None, 29),
            ("Christian", "Kofane-cafe", "DEL", 74, None, 19),
            ("Martin", "Terrier-perrito", "DEL", 78, None, 28),
            ("Nathan", "Tella-tela", "DEL", 77, "regateador", 26),
            ("Eliesse", "Ben Seghir-segundero", "DEL", 78, "regateador", 20),
            ("Ernest", "Poku-poquito", "DEL", 75, None, 21),
        ],
    },
    "Lata Bull Leipzig": {
        "pais": "Alemania", "ciudad": "Leipzig", "estrellas": 4.0, "estilo_dt": "kloppismo", "balance": 28000000,
        "jugadores": [
            ("Peter", "Gulacsi-guante", "POR", 79, "lider", 35),
            ("Maarten", "Vandevoordt-vocal", "POR", 76, None, 23),
            ("Willi", "Orban-urbano", "DEF", 81, "lider", 32),
            ("Castello", "Lukeba-castillo", "DEF", 81, None, 22),
            ("El Chadaille", "Bitshiabu-bicho", "DEF", 74, None, 20),
            ("David", "Raum-espacio", "DEF", 80, "pulmon_de_hierro", 27),
            ("Lukas", "Klostermann-claustro", "DEF", 77, None, 29),
            ("Ridle", "Baku-bakalao", "DEF", 78, None, 27),
            ("Xaver", "Schlager-cancion", "MED", 80, "rustico", 27),
            ("Amadou", "Haidara-jaiba", "MED", 77, None, 27),
            ("Christoph", "Baumgartner-jardinero", "MED", 79, None, 26),
            ("Kevin", "Kampl-campo", "MED", 76, None, 34),
            ("Nicolas", "Seiwald-selva", "MED", 78, "pulmon_de_hierro", 24),
            ("Assan", "Ouedraogo-ouija", "MED", 75, None, 19),
            ("Antonio", "Nusa-nube", "DEL", 79, "regateador", 20),
            ("Romulo", "Cardoso-remo", "DEL", 76, None, 23),
            ("Johan", "Bakayoko-bacalao", "DEL", 79, "regateador", 22),
            ("Conrad", "Harder-duro", "DEL", 76, None, 20),
            ("Tidiam", "Gomis-gomita", "DEL", 73, None, 19),
            ("Yan", "Diomande-diamantito", "DEL", 76, "regateador", 18),
        ],
    },
    "Salchicha de Frankfurt": {
        "pais": "Alemania", "ciudad": "Frankfurt", "estrellas": 3.8, "estilo_dt": "flickismo", "balance": 22000000,
        "jugadores": [
            ("Michael", "Zetterer-zeta", "POR", 77, None, 30),
            ("Kaua", "Santos-santito", "POR", 74, None, 22),
            ("Robin", "Koch-cocinero", "DEF", 80, "lider", 29),
            ("Arthur", "Theate-teatro", "DEF", 79, "rustico", 25),
            ("Nathaniel", "Brown-marron", "DEF", 77, "pulmon_de_hierro", 22),
            ("Rasmus", "Kristensen-cristal", "DEF", 77, None, 28),
            ("Aurele", "Amenda-enmienda", "DEF", 74, None, 22),
            ("Nnamdi", "Collins-coctel", "DEF", 74, None, 21),
            ("Mario", "Gotze-gotita", "MED", 78, "regateador", 33),
            ("Ellyes", "Skhiri-esqui", "MED", 79, "pulmon_de_hierro", 30),
            ("Hugo", "Larsson-largo", "MED", 79, None, 21),
            ("Oscar", "Hojlund-hermanito", "MED", 74, None, 20),
            ("Fares", "Chaibi-chai", "MED", 77, "regateador", 22),
            ("Can", "Uzun-usted", "MED", 78, None, 19),
            ("Jonathan", "Burkardt-burka", "DEL", 80, None, 25),
            ("Michy", "Batshuayi-batido", "DEL", 76, None, 32),
            ("Jean-Matteo", "Bahoya-bahia", "DEL", 76, "regateador", 20),
            ("Ritsu", "Doan-don", "DEL", 79, "regateador", 27),
            ("Elye", "Wahi-wifi", "DEL", 75, None, 22),
            ("Ansgar", "Knauff-knock", "DEL", 76, "pulmon_de_hierro", 23),
        ],
    },
    "Olympique Bullabesa": {
        "pais": "Francia", "ciudad": "Marsella", "estrellas": 4.0, "estilo_dt": "dezerbismo", "balance": 26000000,
        "jugadores": [
            ("Geronimo", "Rulli-rulo", "POR", 81, "lider", 33),
            ("Jeffrey", "de Lange-langosta", "POR", 72, None, 27),
            ("Leonardo", "Balerdi-balero", "DEF", 80, "rustico", 26),
            ("Facundo", "Medina-zurdito", "DEF", 79, None, 26),
            ("Nayef", "Aguerd-aguardiente", "DEF", 80, None, 29),
            ("CJ", "Egan-Riley-egano", "DEF", 74, None, 22),
            ("Emerson", "Palmieri-palmera", "DEF", 76, None, 31),
            ("Amir", "Murillo-murcielago", "DEF", 77, "pulmon_de_hierro", 29),
            ("Pierre-Emile", "Hojbjerg-hielo", "MED", 81, "lider", 30),
            ("Geoffrey", "Kondogbia-condor", "MED", 78, "rustico", 32),
            ("Arthur", "Vermeeren-verbena", "MED", 77, None, 20),
            ("Angel", "Gomes-goma", "MED", 78, "regateador", 25),
            ("Matt", "ORiley-irlandes", "MED", 79, None, 24),
            ("Bilal", "Nadir-nadie", "MED", 73, None, 21),
            ("Mason", "Greenwood-bosque", "DEL", 83, "regateador", 24),
            ("Pierre-Emerick", "Aubameyang-antifaz", "DEL", 80, None, 36),
            ("Igor", "Paixao-pasion", "DEL", 79, "regateador", 25),
            ("Amine", "Gouiri-guiri", "DEL", 79, None, 25),
            ("Neal", "Maupay-maullido", "DEL", 73, None, 29),
            ("Hamed", "Traore-tractor", "DEL", 75, None, 25),
        ],
    },
    "AS Paraiso Fiscal": {
        "pais": "Francia", "ciudad": "Mónaco", "estrellas": 3.9, "estilo_dt": "cruyffismo", "balance": 25000000,
        "jugadores": [
            ("Lukas", "Hradecky-lento", "POR", 80, "lider", 35),
            ("Philipp", "Kohn-cono", "POR", 76, None, 27),
            ("Thilo", "Kehrer-quehacer", "DEF", 78, None, 28),
            ("Mohammed", "Salisu-salsa", "DEF", 78, "rustico", 26),
            ("Vanderson", "Lateral-lujo", "DEF", 80, "pulmon_de_hierro", 24),
            ("Caio", "Henrique-banquero", "DEF", 78, None, 28),
            ("Kassoum", "Ouattara-guatemala", "DEF", 72, None, 21),
            ("Eric", "Dier-diario", "DEF", 77, None, 31),
            ("Christian", "Mawissa-mayonesa", "DEF", 74, None, 20),
            ("Denis", "Zakaria-zanahoria", "MED", 80, "lider", 28),
            ("Lamine", "Camara-camarita", "MED", 79, None, 21),
            ("Aleksandr", "Golovin-golondrina", "MED", 80, "regateador", 29),
            ("Paul", "Pogba-regreso", "MED", 77, None, 32),
            ("Maghnes", "Akliouche-joyero", "MED", 80, "regateador", 23),
            ("Takumi", "Minamino-minimo", "MED", 78, None, 30),
            ("Mamadou", "Coulibaly-coliflor", "MED", 74, None, 21),
            ("Folarin", "Balogun-globo", "DEL", 80, None, 24),
            ("Ansu", "Fati-fatiga", "DEL", 76, "regateador", 22),
            ("George", "Ilenikhena-ilegible", "DEL", 74, None, 19),
            ("Mika", "Biereth-cerveza", "DEL", 77, None, 22),
        ],
    },
    "Lille Frio": {
        "pais": "Francia", "ciudad": "Lille", "estrellas": 3.7, "estilo_dt": "anchelottismo", "balance": 20000000,
        "jugadores": [
            ("Berke", "Ozer-ozono", "POR", 78, None, 25),
            ("Arnaud", "Bodart-bodega", "POR", 72, None, 27),
            ("Aissa", "Mandi-mandarina", "DEF", 77, "lider", 34),
            ("Nathan", "Ngoy-ngoyo", "DEF", 77, None, 22),
            ("Thomas", "Meunier-molinero", "DEF", 77, None, 33),
            ("Romain", "Perraud-perro", "DEF", 76, None, 28),
            ("Tiago", "Santos-santon", "DEF", 77, "pulmon_de_hierro", 23),
            ("Calvin", "Verdonk-verdura", "DEF", 75, None, 28),
            ("Benjamin", "Andre-capitan", "MED", 79, "lider", 35),
            ("Nabil", "Bentaleb-talento", "MED", 77, None, 30),
            ("Ayyoub", "Bouaddi-bodoque", "MED", 78, None, 18),
            ("Hakon", "Haraldsson-vikingo", "MED", 79, "regateador", 22),
            ("Ngalayel", "Mukau-maullido", "MED", 75, None, 21),
            ("Osame", "Sahraoui-sahara", "MED", 76, "regateador", 24),
            ("Andre", "Gomes-abrigado", "MED", 75, None, 32),
            ("Olivier", "Giroud-girasol", "DEL", 78, "lider", 38),
            ("Hamza", "Igamane-iman", "DEL", 77, None, 22),
            ("Matias", "Fernandez-Pardo-pardo", "DEL", 77, "regateador", 20),
            ("Felix", "Correia-correa", "DEL", 75, None, 24),
            ("Marius", "Broholm-brocoli", "DEL", 72, None, 20),
        ],
    },
    "Sporting Sin Gyokeres": {
        "pais": "Portugal", "ciudad": "Lisboa", "estrellas": 4.0, "estilo_dt": "flickismo", "balance": 24000000,
        "jugadores": [
            ("Rui", "Silva-leon", "POR", 80, None, 31),
            ("Joao", "Virginia-virgen", "POR", 72, None, 26),
            ("Ousmane", "Diomande-diamante", "DEF", 82, "rustico", 21),
            ("Goncalo", "Inacio-zurdo", "DEF", 82, None, 24),
            ("Zeno", "Debast-debate", "DEF", 79, None, 22),
            ("Eduardo", "Quaresma-cuaresma", "DEF", 78, None, 23),
            ("Maxi", "Araujo-charrua", "DEF", 79, "pulmon_de_hierro", 25),
            ("Ivan", "Fresneda-fresa", "DEF", 76, None, 21),
            ("Morten", "Hjulmand-capitan", "MED", 82, "lider", 26),
            ("Hidemasa", "Morita-mora", "MED", 79, None, 30),
            ("Daniel", "Braganca-braga", "MED", 78, None, 26),
            ("Joao", "Simoes-simio", "MED", 76, None, 18),
            ("Pedro", "Goncalves-pote", "MED", 82, "regateador", 27),
            ("Francisco", "Trincao-trinchera", "MED", 82, "regateador", 25),
            ("Giorgi", "Kochorashvili-coche", "MED", 76, None, 26),
            ("Luis", "Suarez-el-otro", "DEL", 81, None, 28),
            ("Fotis", "Ioannidis-griego", "DEL", 79, None, 25),
            ("Geny", "Catamo-catamaran", "DEL", 78, "pulmon_de_hierro", 24),
            ("Geovany", "Quenda-quinceanera", "DEL", 79, "regateador", 18),
            ("Alisson", "Santos-sporting", "DEL", 75, None, 23),
        ],
    },
    "Ajax de Amsterdamnada": {
        "pais": "Países Bajos", "ciudad": "Amsterdam", "estrellas": 3.8, "estilo_dt": "cruyffismo", "balance": 18000000,
        "jugadores": [
            ("Vitezslav", "Jaros-jarra", "POR", 76, None, 24),
            ("Remko", "Pasveer-abuelo", "POR", 73, "lider", 41),
            ("Josip", "Sutalo-sutil", "DEF", 78, None, 25),
            ("Youri", "Baas-jefe", "DEF", 77, None, 22),
            ("Ko", "Itakura-tabla", "DEF", 77, None, 28),
            ("Lucas", "Rosa-rosado", "DEF", 74, "pulmon_de_hierro", 25),
            ("Anton", "Gaaei-gaita", "DEF", 74, None, 23),
            ("Aaron", "Bouwman-obrero", "DEF", 71, None, 18),
            ("Jordan", "Henderson-hendo", "MED", 77, "lider", 35),
            ("Kenneth", "Taylor-sastre", "MED", 78, None, 23),
            ("Youri", "Regeer-regidor", "MED", 75, None, 22),
            ("Davy", "Klaassen-clasico", "MED", 75, None, 32),
            ("Branco", "van den Boomen-bombo", "MED", 75, None, 30),
            ("Sean", "Steur-timon", "MED", 70, None, 18),
            ("Oscar", "Gloukh-glu", "MED", 78, "regateador", 21),
            ("Mika", "Godts-dios", "DEL", 76, "regateador", 20),
            ("Wout", "Weghorst-torre", "DEL", 76, "rustico", 33),
            ("Kasper", "Dolberg-dolar", "DEL", 75, None, 27),
            ("Oliver", "Edvardsen-eduardo", "DEL", 74, None, 25),
            ("Raheem", "Sterling-libra", "DEL", 76, "regateador", 31),
        ],
    },
    "PSV Eindhofen": {
        "pais": "Países Bajos", "ciudad": "Eindhoven", "estrellas": 3.9, "estilo_dt": "flickismo", "balance": 20000000,
        "jugadores": [
            ("Walter", "Benitez-paraguas", "POR", 77, None, 32),
            ("Matej", "Kovar-kovacho", "POR", 75, None, 25),
            ("Ryan", "Flamingo-flamenco", "DEF", 77, None, 22),
            ("Jerdy", "Schouten-escudo", "DEF", 77, "lider", 28),
            ("Armando", "Obispo-cura", "DEF", 74, "rustico", 26),
            ("Sergino", "Dest-destello", "DEF", 76, None, 24),
            ("Mauro", "Junior-junior", "DEF", 75, None, 26),
            ("Anass", "Salah-Eddine-sal", "DEF", 74, None, 23),
            ("Yarek", "Gasiorowski-gas", "DEF", 73, None, 20),
            ("Joey", "Veerman-verano", "MED", 78, None, 26),
            ("Paul", "Wanner-wanabi", "MED", 76, "regateador", 19),
            ("Guus", "Til-tilde", "MED", 76, None, 27),
            ("Ismael", "Saibari-sabio", "MED", 78, "regateador", 24),
            ("Dennis", "Man-hombre", "MED", 76, None, 26),
            ("Couhaib", "Driouech-driblin", "MED", 75, "regateador", 23),
            ("Ricardo", "Pepi-pepino", "DEL", 76, None, 22),
            ("Myron", "Boadu-boda", "DEL", 74, None, 24),
            ("Ivan", "Perisic-veterano", "DEL", 77, "pulmon_de_hierro", 36),
            ("Alassane", "Plea-pleito", "DEL", 75, None, 32),
            ("Esmir", "Bajraktarevic-bajon", "DEL", 72, "regateador", 20),
        ],
    },
    "Feyenoord de Rottendam": {
        "pais": "Países Bajos", "ciudad": "Rotterdam", "estrellas": 3.8, "estilo_dt": "kloppismo", "balance": 17000000,
        "jugadores": [
            ("Timon", "Wellenreuther-ola", "POR", 77, None, 29),
            ("Justin", "Bijlow-bijou", "POR", 75, None, 27),
            ("Gernot", "Trauner-trueno", "DEF", 77, "lider", 33),
            ("Tsuyoshi", "Watanabe-wasabi", "DEF", 75, "rustico", 28),
            ("Anel", "Ahmedhodzic-ahumado", "DEF", 76, None, 26),
            ("Givairo", "Read-lector", "DEF", 75, "pulmon_de_hierro", 19),
            ("Jordan", "Bos-jefe", "DEF", 75, None, 22),
            ("Gijs", "Smal-flaco", "DEF", 72, None, 28),
            ("Hugo", "Bueno-malo", "DEF", 72, None, 22),
            ("Quinten", "Timber-madera", "MED", 78, "lider", 24),
            ("In-beom", "Hwang-tigre", "MED", 78, None, 28),
            ("Oussama", "Targhalline-tarjeta", "MED", 74, None, 23),
            ("Luciano", "Valente-valiente", "MED", 74, "regateador", 22),
            ("Jakub", "Moder-moda", "MED", 74, None, 26),
            ("Sem", "Steijn-estaño", "MED", 76, None, 23),
            ("Ayase", "Ueda-lluvia", "DEL", 77, None, 26),
            ("Anis", "Hadj Moussa-musaka", "DEL", 77, "regateador", 23),
            ("Leo", "Sauer-chucrut", "DEL", 72, "regateador", 19),
            ("Gonzalo", "Borges-jorge", "DEL", 73, None, 21),
            ("Casper", "Tengstedt-tenedor", "DEL", 73, None, 25),
        ],
    },
    "Club Brujas": {
        "pais": "Bélgica", "ciudad": "Brujas", "estrellas": 3.6, "estilo_dt": "anchelottismo", "balance": 15000000,
        "jugadores": [
            ("Simon", "Mignolet-mingo", "POR", 76, "lider", 37),
            ("Nordin", "Jackers-jaque", "POR", 72, None, 28),
            ("Brandon", "Mechele-mechon", "DEF", 76, "rustico", 32),
            ("Joel", "Ordonez-ordenado", "DEF", 75, None, 21),
            ("Kyriani", "Sabbe-sabio", "DEF", 73, None, 20),
            ("Joaquin", "Seys-seis", "DEF", 74, "pulmon_de_hierro", 20),
            ("Bjorn", "Meijer-mejor", "DEF", 73, None, 22),
            ("Zaid", "Romero-romerito", "DEF", 72, None, 22),
            ("Hans", "Vanaken-capitan", "MED", 78, "lider", 32),
            ("Raphael", "Onyedika-onda", "MED", 77, "rustico", 24),
            ("Aleksandar", "Stankovic-tanque", "MED", 75, None, 20),
            ("Hugo", "Vetlesen-veleta", "MED", 74, None, 25),
            ("Ludovit", "Reis-rey", "MED", 72, None, 25),
            ("Cisse", "Sandra-sandia", "MED", 71, None, 21),
            ("Christos", "Tzolis-trolis", "DEL", 78, "regateador", 23),
            ("Nicolo", "Tresoldi-tres", "DEL", 73, None, 21),
            ("Carlos", "Forbs-forbes", "DEL", 75, "regateador", 21),
            ("Romeo", "Vermant-vermut", "DEL", 71, None, 21),
            ("Gustaf", "Nilsson-nilo", "DEL", 71, None, 28),
            ("Mamadou", "Diakhon-diacono", "DEL", 70, None, 20),
        ],
    },
    "Celtic de Glasgow Lluvioso": {
        "pais": "Escocia", "ciudad": "Glasgow", "estrellas": 3.6, "estilo_dt": "artetismo", "balance": 16000000,
        "jugadores": [
            ("Kasper", "Schmeichel-hijo", "POR", 76, "lider", 38),
            ("Viljami", "Sinisalo-sinsal", "POR", 70, None, 23),
            ("Cameron", "Carter-Vickers-cartero", "DEF", 77, "rustico", 27),
            ("Liam", "Scales-escalera", "DEF", 74, None, 27),
            ("Auston", "Trusty-confiable", "DEF", 73, None, 26),
            ("Alistair", "Johnston-juanito", "DEF", 75, "pulmon_de_hierro", 26),
            ("Kieran", "Tierney-tierno", "DEF", 75, None, 28),
            ("Jeffrey", "Schlupp-sorbo", "DEF", 72, None, 32),
            ("Callum", "McGregor-capitan", "MED", 77, "lider", 32),
            ("Reo", "Hatate-hatatito", "MED", 77, None, 27),
            ("Arne", "Engels-angel", "MED", 75, None, 22),
            ("Paulo", "Bernardo-sanbernardo", "MED", 74, None, 23),
            ("Luke", "McCowan-vaca", "MED", 72, None, 27),
            ("Benjamin", "Nygren-negro", "MED", 73, "regateador", 24),
            ("Daizen", "Maeda-rayo", "DEL", 78, "pulmon_de_hierro", 27),
            ("Kyogo", "Furuhashi-puente", "DEL", 74, None, 30),
            ("Adam", "Idah-ida", "DEL", 73, None, 24),
            ("Johnny", "Kenny-quenny", "DEL", 71, None, 22),
            ("Sebastian", "Tounekti-tunecino", "DEL", 73, "regateador", 23),
            ("Callum", "Osmand-osmosis", "DEL", 70, None, 25),
        ],
    },
    "Galatasaray Kebab": {
        "pais": "Turquía", "ciudad": "Estambul", "estrellas": 4.0, "estilo_dt": "anchelottismo", "balance": 24000000,
        "jugadores": [
            ("Ugurcan", "Cakir-cakiri", "POR", 80, None, 29),
            ("Gunay", "Guvenc-guante", "POR", 72, None, 34),
            ("Davinson", "Sanchez-tumaco", "DEF", 79, "rustico", 29),
            ("Abdulkerim", "Bardakci-bardo", "DEF", 77, None, 30),
            ("Wilfried", "Singo-cingo", "DEF", 77, None, 24),
            ("Roland", "Sallai-salami", "DEF", 76, "pulmon_de_hierro", 28),
            ("Eren", "Elmali-manzana", "DEF", 74, None, 25),
            ("Ismail", "Jakobs-jacobo", "DEF", 74, None, 26),
            ("Lucas", "Torreira-torrija", "MED", 79, "rustico", 29),
            ("Gabriel", "Sara-sarita", "MED", 78, None, 26),
            ("Ilkay", "Gundogan-gundo", "MED", 80, "lider", 34),
            ("Mario", "Lemina-lamina", "MED", 76, None, 31),
            ("Yunus", "Akgun-yunque", "MED", 75, "regateador", 24),
            ("Kaan", "Ayhan-ayayay", "MED", 74, None, 30),
            ("Leroy", "Sane-luz", "DEL", 82, "regateador", 29),
            ("Victor", "Osimhen-mascara", "DEL", 85, "pulmon_de_hierro", 26),
            ("Baris", "Alper Yilmaz-baron", "DEL", 78, "regateador", 25),
            ("Mauro", "Icardi-wanda", "DEL", 78, None, 32),
            ("Ahmed", "Kutucu-cuchillo", "DEL", 70, None, 25),
            ("Przemyslaw", "Frankowski-franco", "DEF", 74, None, 30),
        ],
    },
    "Lata Bull Salzburgo": {
        "pais": "Austria", "ciudad": "Salzburgo", "estrellas": 3.4, "estilo_dt": "kloppismo", "balance": 13000000,
        "jugadores": [
            ("Alexander", "Schlager-martillo", "POR", 74, None, 29),
            ("Christian", "Zawieschitzky-zeta", "POR", 66, None, 24),
            ("Jacob", "Rasmussen-rasmus", "DEF", 73, "rustico", 28),
            ("Joane", "Gadou-gadito", "DEF", 72, None, 18),
            ("Aleksa", "Terzic-terco", "DEF", 72, None, 26),
            ("Frans", "Kratzig-rasguno", "DEF", 72, None, 22),
            ("Stefan", "Lainer-lana", "DEF", 72, "pulmon_de_hierro", 33),
            ("Tim", "Trummer-tambor", "DEF", 70, None, 19),
            ("Mads", "Bidstrup-bistec", "MED", 74, "lider", 24),
            ("Maurits", "Kjaergaard-carguero", "MED", 74, None, 22),
            ("Soumaila", "Diabate-diablo", "MED", 72, "rustico", 22),
            ("Bobby", "Clark-claro", "MED", 70, None, 20),
            ("Sota", "Kitano-quitano", "MED", 71, "regateador", 20),
            ("John", "Mellberg-mel", "MED", 69, None, 19),
            ("Karim", "Onisiwo-onix", "DEL", 71, None, 33),
            ("Petar", "Ratkov-raton", "DEL", 72, None, 22),
            ("Yorbe", "Vertessen-vertice", "DEL", 71, "regateador", 24),
            ("Edmund", "Baidoo-baile", "DEL", 70, "regateador", 21),
            ("Kerim", "Alajbegovic-alabanza", "DEL", 71, "regateador", 18),
            ("Clement", "Bischoff-obispito", "DEL", 68, None, 20),
        ],
    },
    "Dinamo de Zagreb Ajedrez": {
        "pais": "Croacia", "ciudad": "Zagreb", "estrellas": 3.3, "estilo_dt": "anchelottismo", "balance": 11000000,
        "jugadores": [
            ("Ivan", "Nevistic-nevera", "POR", 73, None, 26),
            ("Danijel", "Zagorac-zagal", "POR", 68, None, 38),
            ("Kevin", "Theophile-Catherine-teofilo", "DEF", 72, "rustico", 35),
            ("Scott", "McKenna-mecha", "DEF", 72, None, 28),
            ("Stefan", "Ristovski-risto", "DEF", 70, "pulmon_de_hierro", 33),
            ("Sergi", "Dominguez-domingo", "DEF", 71, None, 20),
            ("Moris", "Valincic-valija", "DEF", 69, None, 22),
            ("Bruno", "Goda-goda", "DEF", 68, None, 20),
            ("Josip", "Misic-misa", "MED", 73, "lider", 31),
            ("Martin", "Baturina-batidora", "MED", 77, "regateador", 22),
            ("Luka", "Stojkovic-estoico", "MED", 71, None, 21),
            ("Lukas", "Kacavenda-cacao", "MED", 70, None, 22),
            ("Petar", "Sucic-sucio", "MED", 74, None, 22),
            ("Gabriel", "Vidovic-vida", "MED", 72, "regateador", 22),
            ("Mateo", "Lisica-lisa", "MED", 68, None, 21),
            ("Sandro", "Kulenovic-kulebra", "DEL", 71, None, 25),
            ("Arber", "Hoxha-hoja", "DEL", 71, "regateador", 27),
            ("Dion", "Beljo-bello", "DEL", 72, None, 23),
            ("Marko", "Pjaca-pijama", "DEL", 70, None, 30),
            ("Monsef", "Bakrar-bacalao", "DEL", 71, None, 24),
        ],
    },
    "Shakhtar Donetsko": {
        "pais": "Ucrania", "ciudad": "Donetsk", "estrellas": 3.4, "estilo_dt": "dezerbismo", "balance": 12000000,
        "jugadores": [
            ("Dmytro", "Riznyk-riesgo", "POR", 74, None, 26),
            ("Kiril", "Fesyun-fiesta", "POR", 67, None, 23),
            ("Mykola", "Matviyenko-matador", "DEF", 74, "lider", 29),
            ("Valeriy", "Bondar-bondad", "DEF", 73, "rustico", 26),
            ("Yukhym", "Konoplia-canapé", "DEF", 72, "pulmon_de_hierro", 26),
            ("Pedro", "Henrique-enrique", "DEF", 71, None, 24),
            ("Irakli", "Azarovi-azar", "DEF", 70, None, 23),
            ("Vinicius", "Tobias-tobi", "DEF", 70, None, 21),
            ("Artem", "Bondarenko-bonda", "MED", 73, None, 25),
            ("Oleh", "Ocheretko-ochenta", "MED", 72, None, 22),
            ("Georgiy", "Sudakov-sudor", "MED", 76, "regateador", 23),
            ("Marlon", "Gomes-goma", "MED", 72, None, 21),
            ("Pedrinho", "Pedrito-shakhtar", "MED", 73, "regateador", 27),
            ("Dmytro", "Kryskiv-crisis", "MED", 70, None, 24),
            ("Eguinaldo", "Eguinaldo-ego", "DEL", 74, "regateador", 21),
            ("Kevin", "Kelsy-kelsi", "DEL", 73, "regateador", 22),
            ("Newerton", "Newerton-nuevo", "DEL", 71, None, 20),
            ("Lassina", "Traore-tractor", "DEL", 72, None, 25),
            ("Kauan", "Elias-elias", "DEL", 71, None, 22),
            ("Alisson", "Santana-santo", "DEL", 71, "regateador", 19),
        ],
    },
    # v3.7.0 relleno copas: fin de clubes europeos
}

# v3.7.0: clubes que completan las copas (sub-proyecto 6). Todos existen en DATOS_CHAMPIONS /
# DATOS_LIBERTADORES con plantel real parodiado (20-25) y campo 'pais'.
RELLENO_CHAMPIONS: list[str] = [
    # Alemania (5)
    "Bayerna de Munich", "Borussia Dormund", "Bayer Neverkusen", "Lata Bull Leipzig", "Salchicha de Frankfurt",
    # Francia (4)
    "Paris Saint-Germain Sin Champions", "Olympique Bullabesa", "AS Paraiso Fiscal", "Lille Frio",
    # Portugal (3)
    "Benfica Maldito", "Puerto FC", "Sporting Sin Gyokeres",
    # Países Bajos (3)
    "Ajax de Amsterdamnada", "PSV Eindhofen", "Feyenoord de Rottendam",
    # Bélgica, Escocia, Turquía, Austria, Croacia, Ucrania (1 c/u)
    "Club Brujas", "Celtic de Glasgow Lluvioso", "Galatasaray Kebab", "Lata Bull Salzburgo",
    "Dinamo de Zagreb Ajedrez", "Shakhtar Donetsko",
]
RELLENO_LIBERTADORES: list[str] = [
    "Colo Colo Roto", "Olimpia Abuelo", "Universitario de la U", "Bolivar Sin Aire",
]

# v0.7: nombre corto (anti-solapamiento en tabla/bracket de copa).
_NOMBRES_CORTOS_INTL = {
    "Colo Colo Roto": "Colo Colo", "Olimpia Abuelo": "Olimpia",
    "Bolivar Sin Aire": "Bolívar", "Universitario de la U": "Universitario",
    "Bayerna de Munich": "Bayerna", "Borussia Dormund": "Dormund",
    "Paris Saint-Germain Sin Champions": "PSG",   # v3.7.0: sin italianos (Serie A)
    "Benfica Maldito": "Benfica", "Puerto FC": "Puerto",
    # v3.7.0 relleno copas
    "Bayer Neverkusen": "Neverkusen", "Lata Bull Leipzig": "Leipzig", "Salchicha de Frankfurt": "Frankfurt",
    "Olympique Bullabesa": "Marsella", "AS Paraiso Fiscal": "Monaco", "Lille Frio": "Lille",
    "Sporting Sin Gyokeres": "Sporting", "Ajax de Amsterdamnada": "Ajax", "PSV Eindhofen": "PSV",
    "Feyenoord de Rottendam": "Feyenoord", "Club Brujas": "Brujas", "Celtic de Glasgow Lluvioso": "Celtic",
    "Galatasaray Kebab": "Galatasaray", "Lata Bull Salzburgo": "Salzburgo",
    "Dinamo de Zagreb Ajedrez": "Dinamo Zagreb", "Shakhtar Donetsko": "Shakhtar",
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


# Instancias base (compatibilidad; v3.8.0: el motor usa get_pool_* frescos).
POOL_LIBERTADORES = get_pool_libertadores()
POOL_CHAMPIONS = get_pool_champions()
