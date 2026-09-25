# -*- coding: utf-8 -*-
"""
v3.7.0 — Módulo de Datos: Serie A Parodia (Italia).
12 clubes reales de la temporada 2025-26 con jugadores reales parodiados. Mismo formato que
data/premier.py. Juventus, Inter y Milan salen de data/internacional.py y conservan sus jugadores.
"""
from __future__ import annotations

import random
import logging

from alpha_football.models import Liga, Equipo, Jugador
from alpha_football.data.premier import generar_atributos_por_posicion
from alpha_football.estilos import ESTILOS_DT as ESTILOS_TACTICOS

logger = logging.getLogger(__name__)

RASGOS_DISPONIBLES = ["regateador", "lider", "rustico", "pulmon_de_hierro"]

NOMBRES_CORTOS = {
    "Piamonte Calcio": "Piamonte", "Inter de Milan Roto": "Inter", "Milan Abuelo": "Milan",
    "Napoli Pizzeria": "Napoli", "Roma Imperio Caido": "Roma", "Lazio Aguila Calva": "Lazio",
    "Atalanta Diosa Cansada": "Atalanta", "Fiorentina Violeta Marchita": "Fiorentina",
    "Bologna Mortadela": "Bologna", "Como Lago Rico": "Como", "Torino Granate Triste": "Torino",
    "Genoa Pesto": "Genoa",
}
# v3.7.0: estilo coherente con el DT real de cada club (data/entrenadores.py).
ESTILO_FIJO = {
    "Piamonte Calcio": "kloppismo",
    "Inter de Milan Roto": "fullbackismo",
    "Milan Abuelo": "haramball",
    "Napoli Pizzeria": "choloismo",
    "Roma Imperio Caido": "kloppismo",
    "Lazio Aguila Calva": "cruyffismo",
    "Atalanta Diosa Cansada": "kloppismo",
    "Fiorentina Violeta Marchita": "anchelottismo",
    "Bologna Mortadela": "flickismo",
    "Como Lago Rico": "cruyffismo",
    "Torino Granate Triste": "anchelottismo",
    "Genoa Pesto": "dezerbismo",
}

# (nombre, apellido, posición, OVR sugerido, rasgo, edad). Escala ≈ LaLiga (top ~88).
DATOS_SERIEA = {
    "Piamonte Calcio": {
        "ciudad": "Turin",
        "estrellas": 4.5,
        "jugadores": [
            ("Michele", "Di Gregorio", "POR", 83, None, 27),
            ("Mattia", "Perin", "POR", 78, None, 32),
            ("Gleison", "Bremer-muro", "DEF", 85, "rustico", 27),
            ("Federico", "Gatti", "DEF", 80, "rustico", 26),
            ("Pierre", "Kalulu", "DEF", 81, None, 24),
            ("Andrea", "Cambiaso", "DEF", 81, "pulmon_de_hierro", 24),
            ("Danilo", "Capitano", "DEF", 80, "lider", 33),
            ("Lloyd", "Kelly", "DEF", 78, None, 26),
            ("Juan", "Cabalito", "DEF", 77, None, 24),
            ("Manuel", "Locatelli", "MED", 82, "lider", 27),
            ("Khephren", "Thuram", "MED", 82, None, 23),
            ("Teun", "Koopmeiners", "MED", 83, None, 27),
            ("Weston", "McKennie", "MED", 80, "pulmon_de_hierro", 26),
            ("Douglas", "Luiz", "MED", 81, None, 26),
            ("Edon", "Zhegrovazo", "MED", 81, "regateador", 26),
            ("Dusan", "Vlahovic-gol", "DEL", 84, None, 25),
            ("Kenan", "Yildiz-joya", "DEL", 81, "regateador", 19),
            ("Nico", "Gonzalez", "DEL", 81, "regateador", 26),
            ("Timothy", "Weah", "DEL", 78, None, 24),
            ("Jonathan", "Davidazo", "DEL", 82, None, 25),
            ("Francisco", "Conceicaozinho", "DEL", 81, "regateador", 22),
        ]
    },
    "Inter de Milan Roto": {
        "ciudad": "Milan",
        "estrellas": 4.6,
        "jugadores": [
            ("Yann", "Sommer-gato", "POR", 84, None, 35),
            ("Josep", "Martinez", "POR", 76, None, 26),
            ("Alessandro", "Bastoni-clase", "DEF", 86, "rustico", 25),
            ("Francesco", "Acerbi", "DEF", 82, "lider", 36),
            ("Benjamin", "Pavard", "DEF", 83, None, 28),
            ("Stefan", "de Vrij", "DEF", 80, None, 32),
            ("Yann", "Bisseck", "DEF", 79, "rustico", 24),
            ("Carlos", "Augusto", "DEF", 79, None, 25),
            ("Federico", "Dimarco-zurda", "DEF", 84, "regateador", 27),
            ("Denzel", "Dumfries", "DEF", 82, "pulmon_de_hierro", 28),
            ("Nicolo", "Barella-motor", "MED", 87, "pulmon_de_hierro", 27),
            ("Hakan", "Calhanoglu", "MED", 86, "lider", 30),
            ("Henrikh", "Mkhitaryan", "MED", 81, None, 35),
            ("Davide", "Frattesi", "MED", 81, None, 25),
            ("Petar", "Susicazo", "MED", 78, None, 22),
            ("Piotr", "Zielinskazo", "MED", 81, None, 31),
            ("Lautaro", "Martinez-toro", "DEL", 88, "lider", 27),
            ("Marcus", "Thuram", "DEL", 85, None, 27),
            ("Mehdi", "Taremi", "DEL", 80, None, 32),
            ("Ange-Yoan", "Bonnyto", "DEL", 80, None, 21),
            ("Francesco", "Pio Espositino", "DEL", 77, None, 20),
        ]
    },
    "Milan Abuelo": {
        "ciudad": "Milan",
        "estrellas": 4.2,
        "jugadores": [
            ("Mike", "Maignan-muro", "POR", 86, "lider", 29),
            ("Marco", "Sportiello", "POR", 74, None, 32),
            ("Theo", "Hernandez-cohete", "DEF", 85, "pulmon_de_hierro", 27),
            ("Fikayo", "Tomori", "DEF", 82, "rustico", 26),
            ("Malick", "Thiaw", "DEF", 80, None, 23),
            ("Matteo", "Gabbia", "DEF", 78, None, 25),
            ("Strahinja", "Pavlovic", "DEF", 79, "rustico", 23),
            ("Emerson", "Royal", "DEF", 78, None, 25),
            ("Koni", "De Winterfell", "DEF", 77, None, 23),
            ("Tijjani", "Reijnders", "MED", 84, None, 26),
            ("Youssouf", "Fofana", "MED", 81, None, 25),
            ("Ruben", "Loftus-Cheek", "MED", 80, None, 28),
            ("Yunus", "Musah", "MED", 78, "pulmon_de_hierro", 22),
            ("Christian", "Pulisic-USA", "MED", 84, "regateador", 26),
            ("Adrien", "Rabiotazo", "MED", 83, "pulmon_de_hierro", 30),
            ("Samuele", "Riccitel", "MED", 78, None, 24),
            ("Rafael", "Leao-turbo", "DEL", 86, "regateador", 25),
            ("Alvaro", "Morata", "DEL", 81, "lider", 32),
            ("Tammy", "Abraham", "DEL", 78, None, 27),
            ("Samuel", "Chukwueze", "DEL", 78, "regateador", 25),
            ("Christopher", "Nkunkuazo", "DEL", 81, "regateador", 28),
        ]
    },
    "Napoli Pizzeria": {
        "ciudad": "Napoles",
        "estrellas": 4.5,
        "jugadores": [
            ("Alex", "Meretazo", "POR", 83, None, 28),
            ("Vanja", "Milinkovic-Salvado", "POR", 82, None, 28),
            ("Giovanni", "Di Lorenzzo", "DEF", 84, "lider", 32),
            ("Amir", "Rrrahmani", "DEF", 84, "rustico", 31),
            ("Alessandro", "Buongiornale", "DEF", 83, "rustico", 26),
            ("Sam", "Beukemazo", "DEF", 81, None, 27),
            ("Mathias", "Oliverita", "DEF", 81, "pulmon_de_hierro", 28),
            ("Leonardo", "Spinazzolla", "DEF", 78, None, 32),
            ("Miguel", "Gutierrito", "DEF", 80, None, 24),
            ("Stanislav", "Lobotomka", "MED", 86, None, 30),
            ("Scott", "McTomahawk", "MED", 88, "pulmon_de_hierro", 28),
            ("Frank", "Anguisazo", "MED", 84, "rustico", 29),
            ("Billy", "Gilmoura", "MED", 80, None, 24),
            ("Eljif", "Elmasao", "MED", 78, None, 26),
            ("Antonio", "Vergaranja", "MED", 74, None, 22),
            ("Romelu", "Lukakazo", "DEL", 85, "rustico", 32),
            ("Rasmus", "Hojlundito", "DEL", 83, None, 22),
            ("Matteo", "Politanito", "DEL", 81, "pulmon_de_hierro", 32),
            ("David", "Nereseta", "DEL", 82, "regateador", 28),
            ("Noa", "Langosta", "DEL", 81, "regateador", 26),
            ("Lorenzo", "Luccazo", "DEL", 78, None, 25),
        ]
    },
    "Roma Imperio Caido": {
        "ciudad": "Roma",
        "estrellas": 4.1,
        "jugadores": [
            ("Mile", "Svilarazo", "POR", 85, None, 26),
            ("Pierluigi", "Gollinetti", "POR", 74, None, 30),
            ("Gianluca", "Mancinito", "DEF", 82, "rustico", 29),
            ("Evan", "Ndickazo", "DEF", 82, "rustico", 26),
            ("Mario", "Hermosillo", "DEF", 79, "rustico", 30),
            ("Zeki", "Celiko", "DEF", 78, None, 28),
            ("Angelino", "Angelote", "DEF", 81, "pulmon_de_hierro", 28),
            ("Wesley", "Wesleyano", "DEF", 80, "pulmon_de_hierro", 22),
            ("Kostas", "Tsimikaos", "DEF", 77, None, 29),
            ("Bryan", "Cristantemo", "MED", 80, "lider", 30),
            ("Manu", "Konecta", "MED", 83, "pulmon_de_hierro", 24),
            ("Lorenzo", "Pellegrino", "MED", 79, "lider", 29),
            ("Neil", "El Aynaoui-ay", "MED", 79, None, 24),
            ("Niccolo", "Pisillo", "MED", 76, None, 21),
            ("Matias", "Soulecito", "MED", 81, "regateador", 22),
            ("Paulo", "Dybalazo", "DEL", 84, "regateador", 31),
            ("Artem", "Dovbykazo", "DEL", 82, None, 28),
            ("Evan", "Fergusonrisa", "DEL", 78, None, 20),
            ("Stephan", "El Faraonito", "DEL", 77, "regateador", 32),
            ("Leon", "Bailongo", "DEL", 80, "regateador", 28),
        ]
    },
    "Lazio Aguila Calva": {
        "ciudad": "Roma",
        "estrellas": 3.9,
        "jugadores": [
            ("Ivan", "Provedello", "POR", 82, None, 31),
            ("Christos", "Mandarina", "POR", 78, None, 23),
            ("Alessio", "Romagnolito", "DEF", 82, "lider", 30),
            ("Mario", "Gilazo", "DEF", 81, "rustico", 24),
            ("Nuno", "Tavaresco", "DEF", 80, "pulmon_de_hierro", 25),
            ("Adam", "Marusicazo", "DEF", 78, None, 32),
            ("Manuel", "Lazzarito", "DEF", 76, None, 31),
            ("Samuel", "Gigotazo", "DEF", 76, "rustico", 31),
            ("Oliver", "Provstgaardia", "DEF", 74, None, 22),
            ("Luca", "Pellegrinaje", "DEF", 75, None, 26),
            ("Nicolo", "Rovellita", "MED", 82, None, 23),
            ("Matteo", "Guendouzazo", "MED", 81, "pulmon_de_hierro", 26),
            ("Toma", "Basicote", "MED", 76, None, 28),
            ("Fisayo", "Dele-Bashirulo", "MED", 77, None, 24),
            ("Matias", "Vecinito", "MED", 76, "lider", 33),
            ("Gustav", "Isaksenado", "MED", 79, "regateador", 24),
            ("Mattia", "Zaccagnino", "DEL", 83, "regateador", 30),
            ("Taty", "Castellanito", "DEL", 81, None, 26),
            ("Pedro", "Pedrito Viejo", "DEL", 78, "regateador", 38),
            ("Boulaye", "Diamante", "DEL", 78, None, 28),
            ("Tijjani", "Noslinea", "DEL", 77, None, 26),
        ]
    },
    "Atalanta Diosa Cansada": {
        "ciudad": "Bergamo",
        "estrellas": 4.1,
        "jugadores": [
            ("Marco", "Carnesecchino", "POR", 83, None, 25),
            ("Francesco", "Rossino", "POR", 72, None, 34),
            ("Isak", "Hienazo", "DEF", 82, "rustico", 26),
            ("Berat", "Djimsitio", "DEF", 80, "rustico", 32),
            ("Sead", "Kolasinacho", "DEF", 79, "rustico", 32),
            ("Odilon", "Kossounote", "DEF", 80, None, 24),
            ("Giorgio", "Scalvinito", "DEF", 81, None, 21),
            ("Raoul", "Bellanovela", "DEF", 79, "pulmon_de_hierro", 25),
            ("Davide", "Zappatosta", "DEF", 77, None, 33),
            ("Ederson", "Motorcito", "MED", 84, "pulmon_de_hierro", 26),
            ("Marten", "De Roonco", "MED", 81, "lider", 34),
            ("Mario", "Pasalicuas", "MED", 79, None, 30),
            ("Lazar", "Samardzico", "MED", 80, "regateador", 23),
            ("Nicola", "Zalewskito", "MED", 77, None, 23),
            ("Marco", "Palestrina", "MED", 74, None, 23),
            ("Charles", "De Ketchupere", "DEL", 84, "regateador", 24),
            ("Ademola", "Lookmanazo", "DEL", 85, "regateador", 27),
            ("Gianluca", "Scamaccarrones", "DEL", 81, None, 26),
            ("Nikola", "Krstovicho", "DEL", 80, None, 25),
            ("Kamaldeen", "Sulemanita", "DEL", 76, "regateador", 23),
            ("Daniel", "Maldinito", "DEL", 76, None, 23),
        ]
    },
    "Fiorentina Violeta Marchita": {
        "ciudad": "Florencia",
        "estrellas": 3.8,
        "jugadores": [
            ("David", "De Gea-mas", "POR", 84, "lider", 34),
            ("Luca", "Lezzerinito", "POR", 70, None, 32),
            ("Pietro", "Comuzzolo", "DEF", 79, None, 20),
            ("Luca", "Ranierito", "DEF", 79, "rustico", 26),
            ("Marin", "Pongracito", "DEF", 78, "rustico", 28),
            ("Robin", "Gosenazo", "DEF", 80, "pulmon_de_hierro", 31),
            ("Dodo", "Dodotis", "DEF", 81, "pulmon_de_hierro", 27),
            ("Fabiano", "Parisino", "DEF", 77, None, 25),
            ("Niccolo", "Fortinito", "DEF", 74, None, 19),
            ("Rolando", "Mandragoria", "MED", 80, None, 28),
            ("Nicolo", "Fagiolito", "MED", 80, None, 24),
            ("Cher", "Ndourmido", "MED", 77, None, 21),
            ("Hans", "Nicolussi Cavigliosa", "MED", 76, None, 25),
            ("Simon", "Sohmnoliento", "MED", 76, None, 24),
            ("Albert", "Gudmundssonrisa", "MED", 82, "regateador", 28),
            ("Marco", "Brescianinito", "MED", 76, None, 25),
            ("Moise", "Keanazo", "DEL", 84, None, 25),
            ("Edin", "Dzekolosal", "DEL", 80, "lider", 39),
            ("Roberto", "Piccolino", "DEL", 78, None, 24),
            ("Riccardo", "Sottilete", "DEL", 75, "regateador", 26),
        ]
    },
    "Bologna Mortadela": {
        "ciudad": "Bolonia",
        "estrellas": 3.9,
        "jugadores": [
            ("Lukasz", "Skorupskito", "POR", 80, "lider", 34),
            ("Federico", "Ravagliado", "POR", 74, None, 26),
            ("Jhon", "Lucumiedo", "DEF", 81, "rustico", 27),
            ("Torbjorn", "Heggemonia", "DEF", 78, None, 26),
            ("Nicolo", "Casalero", "DEF", 76, None, 27),
            ("Juan", "Mirandita", "DEF", 78, None, 25),
            ("Emil", "Holmsito", "DEF", 78, "pulmon_de_hierro", 25),
            ("Lorenzo", "De Silvestrito", "DEF", 74, "lider", 37),
            ("Charalampos", "Lykogiannidis", "DEF", 76, None, 31),
            ("Remo", "Freulerazo", "MED", 81, "lider", 33),
            ("Lewis", "Fergusonazo", "MED", 81, "pulmon_de_hierro", 26),
            ("Tommaso", "Pobeguita", "MED", 77, None, 26),
            ("Nikola", "Morosito", "MED", 77, None, 27),
            ("Giovanni", "Fabbianito", "MED", 77, None, 22),
            ("Jens", "Odgaardito", "MED", 78, None, 26),
            ("Riccardo", "Orsolinazo", "DEL", 83, "regateador", 28),
            ("Santiago", "Castrito", "DEL", 80, None, 21),
            ("Thijs", "Dallingazo", "DEL", 78, None, 25),
            ("Federico", "Bernardeschiste", "DEL", 77, "regateador", 31),
            ("Jonathan", "Rowecito", "DEL", 77, "regateador", 22),
            ("Ciro", "Inmovilizado", "DEL", 78, "lider", 35),
        ]
    },
    "Como Lago Rico": {
        "ciudad": "Como",
        "estrellas": 3.7,
        "jugadores": [
            ("Jean", "Butezazo", "POR", 79, None, 30),
            ("Noel", "Tornquistito", "POR", 73, None, 23),
            ("Marc-Oliver", "Kempfito", "DEF", 77, "rustico", 30),
            ("Diego", "Carlos-tanque", "DEF", 78, "rustico", 32),
            ("Jacobo", "Ramonazo", "DEF", 76, None, 20),
            ("Alex", "Vallecito", "DEF", 78, "pulmon_de_hierro", 21),
            ("Ignace", "Van der Brempito", "DEF", 76, None, 23),
            ("Alberto", "Morenazo", "DEF", 74, None, 33),
            ("Stefan", "Poschito", "DEF", 76, None, 28),
            ("Nico", "Paz-y-Amor", "MED", 84, "regateador", 21),
            ("Maximo", "Perronito", "MED", 80, None, 22),
            ("Lucas", "Da Cunhado", "MED", 78, "lider", 24),
            ("Sergi", "Robertazo", "MED", 75, None, 33),
            ("Maxence", "Caqueretazo", "MED", 78, None, 25),
            ("Martin", "Baturinero", "MED", 79, "regateador", 22),
            ("Jesus", "Rodriguito", "DEL", 78, "regateador", 20),
            ("Assane", "Diaorama", "DEL", 79, "regateador", 20),
            ("Tasos", "Douvikaso", "DEL", 77, None, 26),
            ("Nicolas", "Kuhnetico", "DEL", 78, "regateador", 25),
            ("Jayden", "Addaito", "DEL", 74, None, 20),
        ]
    },
    "Torino Granate Triste": {
        "ciudad": "Turin",
        "estrellas": 3.5,
        "jugadores": [
            ("Alberto", "Palearito", "POR", 76, None, 33),
            ("Franco", "Israelito", "POR", 76, None, 25),
            ("Saul", "Cocotero", "DEF", 77, "rustico", 27),
            ("Guillermo", "Maripanazo", "DEF", 77, "rustico", 31),
            ("Ardian", "Ismajlito", "DEF", 76, None, 29),
            ("Adam", "Masinota", "DEF", 74, None, 31),
            ("Marcus", "Pedersenito", "DEF", 76, "pulmon_de_hierro", 25),
            ("Valentino", "Lazarillo", "DEF", 75, None, 29),
            ("Cristiano", "Biraghetti", "DEF", 74, "lider", 33),
            ("Kristjan", "Asllanito", "MED", 77, None, 23),
            ("Gvidas", "Gineitizo", "MED", 76, None, 21),
            ("Nikola", "Vlasicazo", "MED", 79, None, 27),
            ("Adrien", "Tamezazo", "MED", 76, "rustico", 31),
            ("Ivan", "Ilicito", "MED", 77, None, 24),
            ("Emirhan", "Ilkhanazo", "MED", 73, None, 21),
            ("Giovanni", "Simeonito", "DEL", 78, "pulmon_de_hierro", 30),
            ("Duvan", "Zapatazo", "DEL", 78, "rustico", 34),
            ("Che", "Adamsguevara", "DEL", 77, None, 29),
            ("Cyril", "Ngongeado", "DEL", 76, "regateador", 25),
            ("Zakaria", "Aboukhlalito", "DEL", 75, "regateador", 25),
        ]
    },
    "Genoa Pesto": {
        "ciudad": "Genova",
        "estrellas": 3.4,
        "jugadores": [
            ("Nicola", "Lealtad", "POR", 76, None, 32),
            ("Benjamin", "Siegristo", "POR", 74, None, 33),
            ("Johan", "Vasquezito", "DEF", 78, "rustico", 26),
            ("Leo", "Ostigardazo", "DEF", 76, "rustico", 25),
            ("Alessandro", "Marcandallo", "DEF", 74, None, 23),
            ("Aaron", "Martincito", "DEF", 76, None, 28),
            ("Brooke", "Norton-Cuffito", "DEF", 75, "pulmon_de_hierro", 21),
            ("Stefano", "Sabellito", "DEF", 74, None, 32),
            ("Morten", "Frendrupazo", "MED", 79, "pulmon_de_hierro", 24),
            ("Ruslan", "Malinovskazo", "MED", 77, None, 32),
            ("Milan", "Badeljazo", "MED", 74, "lider", 36),
            ("Patrizio", "Masinito", "MED", 75, None, 25),
            ("Morten", "Thorsbyte", "MED", 75, None, 29),
            ("Valentin", "Carbonita", "MED", 76, "regateador", 20),
            ("Junior", "Messiasnico", "MED", 76, "regateador", 34),
            ("Lorenzo", "Colombiano", "DEL", 76, None, 23),
            ("Vitinha", "Vitinhazo", "DEL", 76, None, 25),
            ("Caleb", "Ekubanana", "DEL", 73, None, 31),
            ("Jeff", "Ekhatorado", "DEL", 73, None, 19),
            ("Albert", "Gronbaekito", "DEL", 74, None, 24),
        ]
    },
}


def get_liga() -> Liga:
    """v3.7.0: construye la Serie A Parodia (12 clubes, ida y vuelta → 22 jornadas)."""
    try:
        equipos = []
        id_counter = 2000   # v3.7.0: rango propio (no pisa a premier/laliga/internacional)
        for nombre_equipo, info in DATOS_SERIEA.items():
            jugadores = []
            for pnombre, papellido, pos, ovr, rasgo, edad in info["jugadores"]:
                id_counter += 1
                try:
                    ovr_int = int(ovr)
                except Exception:
                    ovr_int = 75
                atk, dfs, fis, tec, men = generar_atributos_por_posicion(ovr_int, pos)
                jugadores.append(Jugador(
                    nombre=pnombre, apellido=papellido, posicion=pos,
                    ataque=atk, defensa=dfs, fisico=fis, tecnica=tec, mental=men,
                    moral=70, rasgo=rasgo, lesion_partidos=0, id=id_counter, edad=edad,
                ))
            equipos.append(Equipo(
                nombre=nombre_equipo,
                ciudad=info["ciudad"],
                estrellas=info["estrellas"],
                estilo_dt=ESTILO_FIJO.get(nombre_equipo) or random.choice(ESTILOS_TACTICOS),
                balance=int(info["estrellas"] * 5000000),
                jugadores=jugadores,
                nombre_corto=NOMBRES_CORTOS.get(nombre_equipo, ""),
            ))
        return Liga(
            nombre="Serie A Parodia",
            tipo="seriea",
            equipos=equipos,
            num_jornadas=max(2, 2 * (len(equipos) - 1)),
        )
    except Exception as error_global:
        logger.error(f"Error critico en get_liga() de seriea.py: {error_global}")
        return Liga(nombre="Serie A Parodia (Emergencia)", tipo="seriea", equipos=[], num_jornadas=2)
