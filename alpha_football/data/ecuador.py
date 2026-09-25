# -*- coding: utf-8 -*-
"""
Alpha Football — DATOS DE LA LIGAPRO ECUADOR (v3.7.0).

Construye y expone la 1ª división de Ecuador con 12 clubes reales parodiados
(temporada 2025-26) y sus jugadores reales humorísticos (techo sudamericano 81,
rango real ~64-78). Barcelona SC y Liga de Quito llegan desde el pool internacional
con sus jugadores de siempre.
"""

from __future__ import annotations

import logging
from alpha_football.models import Liga, Equipo, Jugador
# v3.7.0: mismo generador de atributos que la Liga BetPlay (promedio exacto = OVR).
from alpha_football.data.betplay import generar_atributos_por_posicion

logger = logging.getLogger(__name__)

# Plantillas de parodia para los clubes (20-25 jugadores por equipo)
# Formato: (Nombre, Apellido, Posicion, OVR, Rasgo (u omitido/None), Edad)
PLANTILLAS_PARODIA = {
    # v3.7.0: Barcelona SC y LDU vienen de data/internacional.py con sus jugadores.
    "Barcelona Falso de Guayaquil": {
        "ciudad": "Guayaquil",
        "estrellas": 3.5,
        "estilo_dt": "cruyffismo",
        "balance": 8500000,
        "jugadores": [
            ("Javier", "Burrai", "POR", 72, None, 37),
            ("Gilmar", "Napa", "POR", 66, None, 24),
            ("Luca", "Sosa", "DEF", 69, None, 27),
            ("Mario", "Pineida", "DEF", 70, None, 32),
            ("Xavier", "Arreaga", "DEF", 70, "rustico", 30),
            ("Gabriel", "Cortez", "DEF", 67, None, 26),
            ("Anibal", "Chala", "DEF", 68, None, 27),
            ("Byron", "Castillo-cedula", "DEF", 70, "pulmon_de_hierro", 26),
            ("Anibal", "Leguizamon-guarani", "DEF", 68, "rustico", 33),
            ("Damian", "Diaz-bicho", "MED", 74, "regateador", 38),
            ("Nilson", "Angulo", "MED", 70, None, 21),
            ("Joao", "Rojas", "MED", 70, None, 31),
            ("Sergio", "Lopez", "MED", 67, None, 25),
            ("Fernando", "Gaibor-gaita", "MED", 69, None, 34),
            ("Leonai", "Souza-samba", "MED", 68, None, 27),
            ("Milton", "Celiz-celoso", "MED", 70, "regateador", 32),
            ("Janner", "Corozo", "DEL", 69, None, 24),
            ("Allen", "Obando", "DEL", 71, "regateador", 20),
            ("Jhon", "Cifuente", "DEL", 70, None, 31),
            ("Octavio", "Rivero-rio", "DEL", 71, None, 33),
            ("Gonzalo", "Mastriani-maestro", "DEL", 70, "rustico", 32),
        ]
    },
    "Liga de Quito Rota": {
        "ciudad": "Quito",
        "estrellas": 3.8,
        "estilo_dt": "anchelottismo",
        "balance": 11000000,
        "jugadores": [
            ("Alexander", "Dominguez-pulpo", "POR", 75, "lider", 37),
            ("Gonzalo", "Valle", "POR", 68, None, 27),
            ("Jose", "Quintero", "DEF", 70, None, 26),
            ("Facundo", "Rodriguez", "DEF", 70, None, 25),
            ("Ricardo", "Ade", "DEF", 71, "rustico", 28),
            ("Leonel", "Quinonez", "DEF", 69, None, 29),
            ("Dario", "Aimar", "DEF", 68, None, 23),
            ("Gian", "Allala-alas", "DEF", 67, None, 28),
            ("Richard", "Mina-dinamita", "DEF", 68, "rustico", 28),
            ("Sebastian", "Gonzalez", "MED", 71, None, 28),
            ("Jhojan", "Julio", "MED", 71, "regateador", 24),
            ("Ezequiel", "Piovi", "MED", 72, None, 29),
            ("Gabriel", "Villamil", "MED", 71, None, 24),
            ("Mauricio", "Martinez", "MED", 70, None, 28),
            ("Fernando", "Cornejo-conejo", "MED", 68, None, 30),
            ("Alexander", "Alvarado-alborotado", "MED", 69, "regateador", 26),
            ("Alex", "Arce-gol", "DEL", 74, None, 32),
            ("Lisandro", "Alzugaray", "DEL", 71, None, 29),
            ("Jeison", "Medina", "DEL", 69, None, 27),
            ("Michael", "Estrada-autopista", "DEL", 70, None, 29),
            ("Bryan", "Ramirez-albo", "DEL", 68, "regateador", 24),
        ]
    },
    "Emelec Sin Luz": {
        "ciudad": "Guayaquil",
        "estrellas": 3.2,
        "estilo_dt": "haramball",
        "balance": 6000000,
        "jugadores": [
            ("Pedro", "Ortiz-apagado", "POR", 71, "lider", 35),
            ("Cristhian", "Mora-demora", "POR", 64, None, 25),
            ("Luis", "Ayovi-velita", "DEF", 67, None, 28),
            ("Jackson", "Rodriguez-bombillo", "DEF", 68, "rustico", 27),
            ("Aharon", "Ortiz-cortocircuito", "DEF", 66, None, 22),
            ("Luis", "Caicedo-voltaje", "DEF", 67, None, 33),
            ("Brian", "Carabali-cable", "DEF", 66, "pulmon_de_hierro", 26),
            ("Jose", "Angulo-enchufe", "DEF", 65, None, 24),
            ("Wellington", "Quinonez-transformador", "DEF", 64, None, 21),
            ("Dixon", "Arroyo-caudaloso", "MED", 70, "lider", 32),
            ("Jose Francisco", "Cevallos-hijo", "MED", 69, "regateador", 30),
            ("Diego", "Garcia-azulito", "MED", 67, None, 28),
            ("Joao", "Paredes-oscuras", "MED", 66, None, 29),
            ("Kevin", "Minda-medidor", "MED", 65, "pulmon_de_hierro", 23),
            ("Sebastian", "Rodriguez-foco", "MED", 67, None, 30),
            ("Maicon", "Solis-bombilla", "MED", 64, None, 22),
            ("Alfonso", "Barco-hundido", "DEL", 68, None, 30),
            ("Jaime", "Ayovi-veterano", "DEL", 66, "rustico", 37),
            ("Ronie", "Carrillo-carrete", "DEL", 67, None, 26),
            ("Luis Fernando", "Leon-sin-rugido", "DEL", 66, "regateador", 32),
            ("Christian", "Ortiz-linterna", "DEL", 63, None, 20),
        ]
    },
    "Independiente del Valle de Lagrimas": {
        "ciudad": "Sangolquí",
        "estrellas": 3.8,
        "estilo_dt": "flickismo",
        "balance": 10000000,
        "jugadores": [
            ("Guillermo", "de Amores-amoroso", "POR", 72, None, 30),
            ("Jhonny", "Farinango-farol", "POR", 64, None, 22),
            ("Richard", "Schunke-chunche", "DEF", 72, "rustico", 34),
            ("Mateo", "Carabajal-carbon", "DEF", 70, None, 26),
            ("Luis", "Segovia-segoviano", "DEF", 69, None, 27),
            ("Beder", "Caicedo-buzo", "DEF", 67, None, 32),
            ("Willian", "Vargas-lagrima", "DEF", 67, "pulmon_de_hierro", 23),
            ("Jose", "Hurtado-robado", "DEF", 68, "pulmon_de_hierro", 24),
            ("Anthony", "Landazuri-lloron", "DEF", 65, None, 21),
            ("Junior", "Sornoza-sorbete", "MED", 73, "regateador", 31),
            ("Patrik", "Mercado-mercadito", "MED", 71, None, 22),
            ("Jordy", "Alcivar-alcancia", "MED", 71, "pulmon_de_hierro", 26),
            ("Joao", "Ortiz-cantera", "MED", 70, None, 29),
            ("Justin", "Cuero-cuerito", "MED", 68, "regateador", 21),
            ("Matias", "Perello-perrito", "MED", 67, None, 22),
            ("Yeltzin", "Erique-erizo", "MED", 66, None, 21),
            ("Claudio", "Spinelli-espina", "DEL", 73, None, 28),
            ("Lautaro", "Diaz-rayo", "DEL", 71, "regateador", 27),
            ("Michael", "Hoyos-huecos", "DEL", 69, None, 25),
            ("Kevin", "Rodriguez-mundialista", "DEL", 70, "rustico", 25),
        ]
    },
    "Aucas Ausentes": {
        "ciudad": "Quito",
        "estrellas": 2.9,
        "estilo_dt": "choloismo",
        "balance": 4000000,
        "jugadores": [
            ("Hamilton", "Piedra-roca", "POR", 69, "lider", 32),
            ("Jean", "Carrasco-ausente", "POR", 63, None, 24),
            ("Alejandro", "Manchot-mancha", "DEF", 67, None, 28),
            ("Jhon", "Espinoza-falta", "DEF", 66, "rustico", 26),
            ("Carlos", "Cuero-ausentismo", "DEF", 65, None, 25),
            ("Juan Carlos", "Paredes-vacias", "DEF", 67, "pulmon_de_hierro", 37),
            ("Robert", "Burbano-burbuja", "DEF", 65, None, 29),
            ("Bryan", "Heras-eras", "DEF", 64, None, 22),
            ("Edison", "Carcelen-carcel", "DEF", 64, None, 32),
            ("Roberto", "Ordonez-ordenado", "MED", 68, None, 39),
            ("Jhon", "Pereira-peregrino", "MED", 66, None, 27),
            ("Luis", "Estupinan-estupendo", "MED", 67, "regateador", 24),
            ("Facundo", "Martinez-oriental", "MED", 66, None, 27),
            ("Kevin", "Pena-no-vino", "MED", 64, None, 22),
            ("Danny", "Luna-nueva", "MED", 65, "pulmon_de_hierro", 29),
            ("Oswaldo", "Minda-falto", "MED", 63, None, 21),
            ("Juan Manuel", "Tevez-primo", "DEL", 68, None, 28),
            ("Jefferson", "Montero-ausente", "DEL", 67, "regateador", 36),
            ("Rodney", "Redes-rotas", "DEL", 66, None, 25),
            ("Roberto", "Rosales-rosa", "DEL", 64, None, 23),
            ("Ismael", "Diaz-panameno", "DEL", 66, None, 28),
        ]
    },
    "El Nacional Importado": {
        "ciudad": "Quito",
        "estrellas": 2.8,
        "estilo_dt": "fullbackismo",
        "balance": 3500000,
        "jugadores": [
            ("Wellington", "Ramirez-cabo", "POR", 66, None, 30),
            ("Jorge", "Pinos-soldado", "POR", 62, None, 23),
            ("Anderson", "Ordonez-teniente", "DEF", 66, "rustico", 25),
            ("Cristian", "Penafiel-cadete", "DEF", 64, None, 23),
            ("Pedro", "Velasco-raso", "DEF", 65, None, 32),
            ("Kevin", "Mercado-cuartel", "DEF", 64, None, 25),
            ("Luis", "Luna-trinchera", "DEF", 65, "pulmon_de_hierro", 27),
            ("Christian", "Nazareno-recluta", "DEF", 63, None, 21),
            ("Jordan", "Jaime-marcial", "DEF", 63, None, 22),
            ("Fidel", "Martinez-mayor", "MED", 68, "regateador", 35),
            ("Marcos", "Caicedo-capitan", "MED", 66, "lider", 33),
            ("Carlos", "Armas-armado", "MED", 65, None, 26),
            ("Edson", "Montano-montana", "MED", 64, None, 25),
            ("Jhon", "Sanchez-desfile", "MED", 64, "pulmon_de_hierro", 24),
            ("Diego", "Arcos-triunfo", "MED", 63, None, 22),
            ("Bryan", "Cabezas-rapadas", "MED", 65, None, 28),
            ("Carlos", "Garces-bayoneta", "DEL", 67, None, 35),
            ("Fernando", "Hidalgo-granada", "DEL", 65, "rustico", 26),
            ("Jonathan", "Borja-tanque", "DEL", 66, None, 31),
            ("Andres", "Chicaiza-canon", "DEL", 63, "regateador", 21),
            ("Cristhian", "Tamayo-trompeta", "DEL", 62, None, 20),
        ]
    },
    "Deportivo Cuenca Seca": {
        "ciudad": "Cuenca",
        "estrellas": 2.8,
        "estilo_dt": "kloppismo",
        "balance": 3500000,
        "jugadores": [
            ("Hernan", "Galindez-toquilla", "POR", 68, "lider", 38),
            ("Adrian", "Pacheco-austral", "POR", 62, None, 24),
            ("Stiven", "Plaza-mayor", "DEF", 66, None, 25),
            ("Jhonny", "Uzhca-cuencano", "DEF", 65, None, 27),
            ("Pablo", "Alvarado-tomebamba", "DEF", 66, "rustico", 30),
            ("Hector", "Mera-quimera", "DEF", 64, None, 23),
            ("Luis", "Sanchez-expreso", "DEF", 65, "pulmon_de_hierro", 28),
            ("Leonardo", "Realpe-realito", "DEF", 64, None, 22),
            ("Mauricio", "Guaman-austral", "DEF", 63, None, 21),
            ("Juan", "Cazares-cazador", "MED", 69, "regateador", 33),
            ("Sebastian", "Quintana-cuencana", "MED", 65, None, 26),
            ("Jonathan", "Gonzalez-sombrerito", "MED", 66, None, 30),
            ("Byron", "Palacios-barranco", "MED", 64, None, 24),
            ("Damian", "Borja-paja", "MED", 65, "pulmon_de_hierro", 27),
            ("Alexis", "Zapata-zapatero", "MED", 63, None, 22),
            ("Pedro", "Perlaza-perla", "MED", 64, None, 29),
            ("Enrique", "Vera-austral", "DEL", 67, None, 30),
            ("Maximiliano", "Barreiro-barro", "DEL", 66, "rustico", 28),
            ("Walter", "Chala-chalito", "DEL", 64, "regateador", 23),
            ("Brian", "Oyola-ola", "DEL", 65, None, 26),
            ("Joel", "Quizhpe-cuencanito", "DEL", 62, None, 19),
        ]
    },
    "Universidad Catolica Atea": {
        "ciudad": "Quito",
        "estrellas": 3.0,
        "estilo_dt": "cruyffismo",
        "balance": 4500000,
        "jugadores": [
            ("Rodrigo", "Espinoza-rezador", "POR", 68, None, 28),
            ("Darwin", "Evolucion", "POR", 64, None, 25),
            ("Gustavo", "Vallecilla-capilla", "DEF", 67, "rustico", 26),
            ("Carlos", "Orejuela-orejita", "DEF", 65, None, 24),
            ("Cristian", "Gimenez-trencito", "DEF", 66, None, 28),
            ("Diego", "Hurtado-hereje", "DEF", 64, None, 23),
            ("Jose", "Cortez-concilio", "DEF", 65, "pulmon_de_hierro", 27),
            ("Brian", "Balseca-balsa", "DEF", 63, None, 21),
            ("Mauro", "Poveda-ateismo", "DEF", 63, None, 22),
            ("Juan Sebastian", "Martinez-chulla", "MED", 67, None, 27),
            ("Alexander", "Bolanos-bolas", "MED", 66, "regateador", 25),
            ("Ricardo", "Phillips-destornillador", "MED", 66, None, 30),
            ("Jeison", "Quinonez-sacristan", "MED", 65, None, 23),
            ("Eduardo", "Gonzalez-trencito", "MED", 64, "pulmon_de_hierro", 26),
            ("Luis", "Congo-conga", "MED", 64, None, 22),
            ("Braian", "Oyola-oyente", "MED", 63, None, 21),
            ("Tomas", "Molina-molino", "DEL", 68, None, 32),
            ("Ivan", "Jarrin-jarra", "DEL", 66, "rustico", 27),
            ("Jhonatan", "Mancilla-mancha", "DEL", 65, None, 24),
            ("Kevin", "Becerra-becerro", "DEL", 64, "regateador", 22),
            ("Mateo", "Troya-trenecito", "DEL", 62, None, 19),
        ]
    },
    "Orense Sin Oro": {
        "ciudad": "Machala",
        "estrellas": 2.8,
        "estilo_dt": "anchelottismo",
        "balance": 3200000,
        "jugadores": [
            ("Luis", "Fernandez-bananero", "POR", 67, None, 29),
            ("Jose", "Contreras-cascara", "POR", 64, None, 30),
            ("Jhon", "Angulo-platano", "DEF", 66, None, 27),
            ("Kevin", "Chamba-maduro", "DEF", 65, "rustico", 25),
            ("Luis", "Mosquera-banano", "DEF", 65, None, 26),
            ("Edder", "Fuertes-racimo", "DEF", 66, "pulmon_de_hierro", 32),
            ("Fernando", "Leon-bonito", "DEF", 64, None, 23),
            ("Ronald", "Pineda-verde", "DEF", 63, None, 21),
            ("Joel", "Lopez-machaleno", "DEF", 64, None, 28),
            ("Leonardo", "Villagra-chifle", "MED", 67, "regateador", 29),
            ("Jose", "Carabali-patacon", "MED", 66, None, 26),
            ("Bryan", "Carabali-bolon", "MED", 64, None, 22),
            ("Carlos", "Rodriguez-guineo", "MED", 65, "pulmon_de_hierro", 28),
            ("Edwin", "Bone-bonito", "MED", 64, None, 24),
            ("Jairo", "Padilla-orito", "MED", 63, None, 21),
            ("Marcos", "Olmedo-sin-oro", "MED", 65, "lider", 31),
            ("Juan Pablo", "Rodriguez-barraganete", "DEL", 67, None, 27),
            ("Leonardo", "Campana-banana", "DEL", 66, "rustico", 33),
            ("Jonny", "Uchuari-mono", "DEL", 65, "regateador", 32),
            ("Anderson", "Julio-agosto", "DEL", 64, None, 23),
            ("Erick", "Plaza-bananal", "DEL", 62, None, 19),
        ]
    },
    "Delfin Varado": {
        "ciudad": "Manta",
        "estrellas": 2.8,
        "estilo_dt": "dezerbismo",
        "balance": 3300000,
        "jugadores": [
            ("Johan", "Padilla-salvavidas", "POR", 67, None, 32),
            ("Raul", "Martinez-ballena", "POR", 62, None, 24),
            ("Jhon", "Garcia-varado", "DEF", 66, "rustico", 28),
            ("Jose", "Mero-merluza", "DEF", 65, None, 26),
            ("Andres", "Lopez-camaron", "DEF", 64, None, 23),
            ("Segundo", "Portocarrero-puerto", "DEF", 65, None, 29),
            ("Luis", "Chila-chilena", "DEF", 64, None, 25),
            ("Oscar", "Zambrano-ancla", "DEF", 63, "pulmon_de_hierro", 22),
            ("Nixon", "Molina-marea", "DEF", 64, None, 27),
            ("Carlos", "Villalba-cetaceo", "MED", 66, None, 28),
            ("Roberto", "Garces-gaviota", "MED", 65, "regateador", 25),
            ("Jonathan", "Betancourt-bote", "MED", 66, "lider", 30),
            ("Pedro", "Quinonez-pulpo", "MED", 64, None, 23),
            ("Ernesto", "Espinoza-erizo", "MED", 63, None, 22),
            ("Jefferson", "Intriago-anzuelo", "MED", 64, None, 26),
            ("Dagner", "Mina-manta", "MED", 63, None, 21),
            ("Angel", "Mena-orca", "DEL", 68, "regateador", 37),
            ("Carlos", "Feraud-tiburon", "DEL", 66, None, 28),
            ("Jose", "Angulo-sardina", "DEL", 65, "rustico", 29),
            ("Cristian", "Zambrano-mantarraya", "DEL", 64, None, 24),
            ("Mike", "Cevallos-pez-espada", "DEL", 62, None, 20),
        ]
    },
    "Tecnico Universitario Repitente": {
        "ciudad": "Ambato",
        "estrellas": 2.7,
        "estilo_dt": "haramball",
        "balance": 3000000,
        "jugadores": [
            ("Luis", "Gonzalez-repitente", "POR", 66, None, 31),
            ("Damian", "Tello-tarea", "POR", 61, None, 22),
            ("Carlos", "Mosquera-examen", "DEF", 65, "rustico", 29),
            ("Victor", "Mina-cuaderno", "DEF", 64, None, 25),
            ("Paul", "Bravo-borrador", "DEF", 65, None, 27),
            ("Andres", "Vasquez-recreo", "DEF", 64, "pulmon_de_hierro", 24),
            ("Josue", "Caicedo-mochila", "DEF", 63, None, 22),
            ("Edwin", "Pacheco-pupitre", "DEF", 64, None, 30),
            ("Rolando", "Silva-supletorio", "DEF", 63, None, 21),
            ("Joffre", "Escobar-rodillo", "MED", 67, "regateador", 30),
            ("Marlon", "de Jesus-tesis", "MED", 66, None, 34),
            ("Kevin", "Villacres-matricula", "MED", 65, None, 25),
            ("Wilson", "Torres-apuntes", "MED", 64, "pulmon_de_hierro", 27),
            ("Byron", "Mina-semestre", "MED", 63, None, 22),
            ("Jorge", "Ordonez-libreta", "MED", 64, None, 28),
            ("Alan", "Franco-profe", "MED", 65, "lider", 26),
            ("Juan Luis", "Anangono-diploma", "DEL", 66, None, 36),
            ("Michael", "Carcelen-rector", "DEL", 65, "regateador", 24),
            ("Gustavo", "Nazareno-nota-baja", "DEL", 64, None, 26),
            ("Ivan", "Bulos-bullicio", "DEL", 63, "rustico", 28),
            ("Cristopher", "Zambrano-cero", "DEL", 61, None, 19),
        ]
    },
    "Mushuc Ruina": {
        "ciudad": "Ambato",
        "estrellas": 2.6,
        "estilo_dt": "artetismo",
        "balance": 2800000,
        "jugadores": [
            ("Jhonny", "Morocho-andino", "POR", 66, "lider", 30),
            ("Segundo", "Pilatasig-paramo", "POR", 61, None, 23),
            ("Luis", "Chicaiza-quiebra", "DEF", 65, "rustico", 28),
            ("Byron", "Caiza-crisis", "DEF", 64, None, 25),
            ("Manuel", "Tixe-deficit", "DEF", 64, None, 27),
            ("Wilmer", "Ayala-apuro", "DEF", 63, None, 23),
            ("Ronny", "Carrasco-remate", "DEF", 64, "pulmon_de_hierro", 26),
            ("Marco", "Pilamunga-paramo", "DEF", 63, None, 21),
            ("Henry", "Toaquiza-frio", "DEF", 62, None, 22),
            ("Cristian", "Chamorro-cumbre", "MED", 66, "regateador", 29),
            ("Luis", "Leon-deuda", "MED", 65, None, 30),
            ("Jairo", "Tenelema-poncho", "MED", 64, "pulmon_de_hierro", 24),
            ("Edison", "Vega-chimborazo", "MED", 64, None, 27),
            ("Nelson", "Guaman-remate", "MED", 63, None, 22),
            ("Diego", "Masaquiza-bancarrota", "MED", 63, None, 25),
            ("Jose", "Quishpe-rebaja", "MED", 62, None, 20),
            ("Jeison", "Ortiz-derrumbe", "DEL", 66, None, 28),
            ("Eduardo", "Morante-escombro", "DEL", 65, "rustico", 31),
            ("Kevin", "Cuero-temblor", "DEL", 64, "regateador", 23),
            ("Franklin", "Guerra-pleito", "DEL", 63, None, 26),
            ("Alex", "Sisa-escombrito", "DEL", 61, None, 19),
        ]
    },
    # v3.7.0: fin de la lista de clubes
}

DATOS_ECUADOR = PLANTILLAS_PARODIA

NOMBRES_CORTOS = {
    "Barcelona Falso de Guayaquil": "Barcelona SC", "Liga de Quito Rota": "LDU Quito",
    "Emelec Sin Luz": "Emelec", "Independiente del Valle de Lagrimas": "Indep. Valle",
    "Aucas Ausentes": "Aucas", "El Nacional Importado": "El Nacional",
    "Deportivo Cuenca Seca": "Dep. Cuenca", "Universidad Catolica Atea": "U. Catolica",
    "Orense Sin Oro": "Orense", "Delfin Varado": "Delfin",
    "Tecnico Universitario Repitente": "Tecnico U.", "Mushuc Ruina": "Mushuc Ruina",
}

ESTILO_OVERRIDE = {
    "Barcelona Falso de Guayaquil": "kloppismo",
    "Liga de Quito Rota": "flickismo",
}


def get_liga() -> Liga:
    """
    Construye y devuelve el objeto LigaPro Ecuador
    con plantillas de parodia completamente pobladas.
    """
    try:
        equipos = []
        id_counter = 9000  # v3.7.0: rango propio (12 clubes)

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
            nombre="LigaPro Ecuador Parodia",
            tipo="ecuador",
            equipos=equipos,
            num_jornadas=max(2, 2 * (len(equipos) - 1))  # v3.7.0: 12 clubes -> 22
        )
    except Exception as e:
        logger.critical(f"Error crítico al construir la LigaPro Ecuador: {e}. Retornando liga vacía.")
        # Retorno seguro para evitar que el juego se caiga por completo (resiliencia)
        return Liga("LigaPro Ecuador Fallback", "ecuador", [], 22)
