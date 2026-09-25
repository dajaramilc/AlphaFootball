# -*- coding: utf-8 -*-
"""
Alpha Football — DATOS DE LA LIGA AUF URUGUAYA (v3.7.0).

Construye y expone la 1ª división de Uruguay con 12 clubes reales parodiados
(temporada 2025-26) y sus jugadores reales humorísticos (techo sudamericano 81,
rango real ~64-78). Peñarol y Nacional llegan desde el pool internacional con sus
jugadores de siempre.
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
    # v3.7.0: Peñarol y Nacional vienen de data/internacional.py con sus jugadores.
    "Penarol Roto": {
        "ciudad": "Montevideo",
        "estrellas": 3.5,
        "estilo_dt": "haramball",
        "balance": 9000000,
        "jugadores": [
            ("Washington", "Aguerre-muro", "POR", 74, "lider", 34),
            ("Martin", "Campana", "POR", 68, None, 35),
            ("Guzman", "Rodriguez", "DEF", 72, "lider", 33),
            ("Javier", "Mendez", "DEF", 70, None, 27),
            ("Pedro", "Milans", "DEF", 69, None, 28),
            ("Leonardo", "Coelho", "DEF", 70, "rustico", 26),
            ("Nahuel", "Herrera", "DEF", 68, None, 23),
            ("Kevin", "Morgan-pirata", "DEF", 67, None, 26),
            ("Maximiliano", "Olivera-lateral", "DEF", 69, "pulmon_de_hierro", 33),
            ("Jaime", "Baez", "MED", 72, None, 31),
            ("Eric", "Remedi", "MED", 71, None, 29),
            ("Ignacio", "Sosa", "MED", 70, None, 27),
            ("Leonardo", "Fernandez-crack", "MED", 78, "regateador", 26),
            ("Rodrigo", "Perez", "MED", 68, None, 24),
            ("Eduardo", "Darias-llanero", "MED", 69, "regateador", 28),
            ("Damian", "Garcia-carbonero", "MED", 67, None, 27),
            ("Maxi", "Silvera", "DEL", 73, None, 29),
            ("David", "Terans", "DEL", 72, "regateador", 31),
            ("Diego", "Garcia", "DEL", 70, None, 27),
            ("Hector", "Villalba-flecha", "DEL", 70, "regateador", 31),
            ("Matias", "Arezo-goleador", "DEL", 71, None, 23),
        ]
    },
    "Nacionall de Montevideo": {
        "ciudad": "Montevideo",
        "estrellas": 3.5,
        "estilo_dt": "cruyffismo",
        "balance": 8500000,
        "jugadores": [
            ("Sergio", "Rochet-tapa", "POR", 76, "lider", 31),
            ("Luis", "Mejia", "POR", 70, None, 33),
            ("Sebastian", "Coates-torre", "DEF", 76, "rustico", 34),
            ("Nicolas", "Marichal", "DEF", 71, None, 25),
            ("Alfonso", "Trezza", "DEF", 68, None, 24),
            ("Lucas", "Rodriguez", "DEF", 67, None, 23),
            ("Christian", "Almeida", "DEF", 66, None, 22),
            ("Diego", "Polenta-dura", "DEF", 70, "rustico", 33),
            ("Julian", "Millan-carril", "DEF", 66, None, 22),
            ("Felipe", "Carballo", "MED", 73, None, 27),
            ("Christian", "Oliveira", "MED", 71, None, 28),
            ("Mauricio", "Pereyra", "MED", 72, "lider", 34),
            ("Juan", "DeLosSantos", "MED", 70, None, 23),
            ("Nicolas", "Lodeiro-zurdito", "MED", 74, "lider", 36),
            ("Romulo", "Otero-bombazo", "MED", 71, "regateador", 32),
            ("Baltasar", "Barcia-fino", "MED", 67, None, 23),
            ("Gonzalo", "Carneiro", "DEL", 70, None, 29),
            ("Luciano", "Rodriguez-joya", "DEL", 72, "regateador", 21),
            ("Emiliano", "Ancheta", "DEL", 67, None, 22),
            ("Maximiliano", "Gomez-cabezon", "DEL", 73, "rustico", 29),
            ("Diego", "Herazo-cumbiambero", "DEL", 69, None, 28),
        ]
    },
    "Defensor Esporting": {
        "ciudad": "Montevideo",
        "estrellas": 3.0,
        "estilo_dt": "cruyffismo",
        "balance": 5000000,
        "jugadores": [
            ("Kevin", "Dawsonazo", "POR", 71, None, 33),
            ("Santiago", "Guarneri-pibe", "POR", 64, None, 21),
            ("Mateo", "Ponte-puente", "DEF", 69, None, 22),
            ("Alan", "Rodriguez-violeta", "DEF", 68, "rustico", 25),
            ("Francisco", "Barrios-barrera", "DEF", 67, None, 26),
            ("Lucas", "Morales-tranca", "DEF", 67, None, 23),
            ("Juan", "Rodriguez-tuerto", "DEF", 66, None, 29),
            ("Bruno", "Rodrigues-lateral", "DEF", 65, "pulmon_de_hierro", 22),
            ("Emiliano", "Rigoni-ancla", "DEF", 66, None, 27),
            ("Alan", "Medina-mago", "MED", 72, "regateador", 27),
            ("Juan Manuel", "Gutierrez-motor", "MED", 70, "pulmon_de_hierro", 24),
            ("Facundo", "Bonifazi-pase", "MED", 69, None, 26),
            ("Agustin", "Cayetano-ancho", "MED", 68, None, 21),
            ("Patricio", "Pacifico-tranquilo", "MED", 67, None, 22),
            ("Mateo", "Tanlongo-largo", "MED", 66, None, 22),
            ("Santiago", "Homenchenko-tanque", "MED", 69, "rustico", 22),
            ("Brian", "Montenegro-pitbull", "DEL", 71, "rustico", 31),
            ("Renzo", "Machado-hacha", "DEL", 68, None, 22),
            ("Juan", "Cruz de Armas-chico", "DEL", 67, "regateador", 20),
            ("Federico", "Martinez-sueco", "DEL", 68, None, 27),
            ("Ignacio", "Lemmo-lento", "DEL", 66, None, 23),
        ]
    },
    "Danubio Seco": {
        "ciudad": "Montevideo",
        "estrellas": 2.8,
        "estilo_dt": "kloppismo",
        "balance": 4000000,
        "jugadores": [
            ("Salvador", "Ichazo-manos", "POR", 68, "lider", 33),
            ("Lucas", "Nunez-guante", "POR", 63, None, 22),
            ("Guillermo", "Cotugno-veterano", "DEF", 69, "lider", 30),
            ("Martin", "Rabunal-rudo", "DEF", 67, "rustico", 30),
            ("Alex", "Silva-flaco", "DEF", 66, None, 28),
            ("Joaquin", "Pereyra-franja", "DEF", 65, None, 23),
            ("Emanuel", "Laguna-charco", "DEF", 66, None, 24),
            ("Matias", "De los Santos-roca", "DEF", 68, "rustico", 26),
            ("Tiago", "Palacios-pared", "DEF", 64, None, 21),
            ("Rodrigo", "Amaral-promesa", "MED", 68, "regateador", 28),
            ("Christian", "Taboada-tabla", "MED", 69, None, 31),
            ("Pablo", "Siles-sillon", "MED", 67, None, 28),
            ("Mathias", "Tellechea-tela", "MED", 67, None, 22),
            ("Agustin", "Dos Santos-hermano", "MED", 66, "pulmon_de_hierro", 24),
            ("Facundo", "Waller-muralla", "MED", 66, None, 25),
            ("Rodrigo", "Chagas-herida", "MED", 65, None, 23),
            ("Diego", "Romero-ron", "DEL", 69, None, 30),
            ("Mauro", "Mendez-francotirador", "DEL", 68, None, 26),
            ("Ignacio", "Ramirez-nacho", "DEL", 70, "lider", 27),
            ("Nicolas", "Siri-sirena", "DEL", 65, "regateador", 20),
            ("Bruno", "Leyes-ley", "DEL", 64, None, 22),
        ]
    },
    "Liverpul Uruguayo": {
        "ciudad": "Montevideo",
        "estrellas": 3.0,
        "estilo_dt": "flickismo",
        "balance": 4500000,
        "jugadores": [
            ("Sebastian", "Lentinelly-lento", "POR", 70, None, 28),
            ("Mauro", "Silveira-reja", "POR", 64, None, 25),
            ("Alan", "Brun-bruno", "DEF", 67, None, 23),
            ("Kevin", "Amaro-amargo", "DEF", 66, None, 25),
            ("Joaquin", "Trasante-trasero", "DEF", 67, "rustico", 26),
            ("Guzman", "Corujo-lechuza", "DEF", 65, None, 24),
            ("Juan Pablo", "Ubeda-ubicado", "DEF", 66, None, 27),
            ("Santiago", "Sosa-caustica", "DEF", 65, "pulmon_de_hierro", 22),
            ("Federico", "Barrandeguy-barranco", "DEF", 64, None, 25),
            ("Martin", "Barrios-negriazul", "MED", 69, None, 28),
            ("Thiago", "Helguera-helado", "MED", 68, None, 19),
            ("Lucas", "Acosta-costilla", "MED", 67, "pulmon_de_hierro", 25),
            ("Hernan", "Figueredo-figura", "MED", 69, "lider", 30),
            ("Ramiro", "Degregorio-gregario", "MED", 66, None, 24),
            ("Ezequiel", "Olivera-olivo", "MED", 66, None, 22),
            ("Mathias", "Abero-abeja", "MED", 67, "regateador", 34),
            ("Maximiliano", "Noble-plebeyo", "DEL", 68, None, 23),
            ("Emiliano", "Mozzone-mozo", "DEL", 67, None, 27),
            ("Nicolas", "Queiroz-queso", "DEL", 69, "regateador", 23),
            ("Ruben", "Bentancourt-lejano", "DEL", 70, None, 32),
            ("Facundo", "Rodriguez-cuervo", "DEL", 65, None, 21),
        ]
    },
    "Wanderers Perdidos": {
        "ciudad": "Montevideo",
        "estrellas": 2.8,
        "estilo_dt": "haramball",
        "balance": 3500000,
        "jugadores": [
            ("Ignacio", "de Arruabarrena-apellidazo", "POR", 69, "lider", 28),
            ("Christian", "Rodriguez-bohemio", "POR", 63, None, 24),
            ("Emanuel", "Beltran-beltrano", "DEF", 66, None, 26),
            ("Maximiliano", "Pereira-lejana", "DEF", 65, None, 24),
            ("Rodrigo", "Izquierdo-diestro", "DEF", 66, "rustico", 30),
            ("Mathias", "Riquero-rico", "DEF", 64, None, 22),
            ("Diego", "Arismendi-ariete", "DEF", 67, "lider", 32),
            ("Nicolas", "Rizzo-risitas", "DEF", 64, None, 23),
            ("Alejo", "Cruz-crucero", "DEF", 63, None, 20),
            ("Gonzalo", "Napoli-pizza", "MED", 67, None, 25),
            ("Santiago", "Martinez-bohemio", "MED", 66, None, 27),
            ("Adrian", "Colombino-palomo", "MED", 68, "regateador", 32),
            ("Paolo", "Calione-callado", "MED", 65, None, 24),
            ("Martin", "Alaniz-alas", "MED", 67, "pulmon_de_hierro", 28),
            ("Kevin", "Alaniz-primo", "MED", 64, None, 21),
            ("Federico", "Gino-ginebra", "MED", 66, None, 26),
            ("Joaquin", "Zeballos-cebolla", "DEL", 68, None, 29),
            ("Tiago", "Galletto-galleta", "DEL", 66, "regateador", 21),
            ("Leandro", "Otormin-dormido", "DEL", 67, None, 22),
            ("Mathias", "Cubero-cubierto", "DEL", 65, None, 24),
            ("Agustin", "Alvarez-casaca", "DEL", 64, None, 20),
        ]
    },
    "Racing Sin Frenos": {
        "ciudad": "Montevideo",
        "estrellas": 2.7,
        "estilo_dt": "dezerbismo",
        "balance": 3000000,
        "jugadores": [
            ("Mauricio", "Nanni-nana", "POR", 67, None, 28),
            ("Leandro", "Gelpi-golpe", "POR", 62, None, 23),
            ("Mathias", "Suarez-racinguista", "DEF", 66, None, 28),
            ("Tomas", "Olase-ola", "DEF", 65, None, 24),
            ("Santiago", "Etchebarne-hacha", "DEF", 66, "rustico", 26),
            ("Juan Pablo", "Plada-plata", "DEF", 64, None, 22),
            ("Enzo", "Castillo-fuerte", "DEF", 65, None, 25),
            ("Gaston", "Colman-colmena", "DEF", 63, None, 21),
            ("Franco", "Lopez-sayaguero", "DEF", 64, "pulmon_de_hierro", 27),
            ("Gonzalo", "Pastorini-pastor", "MED", 67, None, 25),
            ("Nicolas", "Wunsch-deseo", "MED", 68, "regateador", 30),
            ("Bruno", "Barreto-birrete", "MED", 65, None, 23),
            ("Manuel", "Monzeglio-monje", "MED", 66, None, 26),
            ("Ivan", "Rossi-rosita", "MED", 64, None, 22),
            ("Luciano", "Recalde-recalentado", "MED", 66, "pulmon_de_hierro", 28),
            ("Agustin", "Varela-varilla", "MED", 63, None, 20),
            ("Mauro", "Estol-estola", "DEL", 67, None, 22),
            ("Fabricio", "Diaz-noche", "DEL", 66, "regateador", 22),
            ("Gabriel", "Baez-baul", "DEL", 65, None, 25),
            ("Cristian", "Olivera-racing", "DEL", 68, "lider", 31),
            ("Sebastian", "Assis-asistencia", "DEL", 64, None, 21),
        ]
    },
    "Cerro Largo Larguisimo": {
        "ciudad": "Melo",
        "estrellas": 2.6,
        "estilo_dt": "choloismo",
        "balance": 2800000,
        "jugadores": [
            ("Washington", "Ortega-arco", "POR", 66, "lider", 30),
            ("Federico", "Cristobal-colon", "POR", 61, None, 22),
            ("Diego", "Duarte-arameno", "DEF", 65, None, 27),
            ("Lucas", "Viera-vieira", "DEF", 64, None, 25),
            ("Enzo", "Dos Santos-melense", "DEF", 65, "rustico", 28),
            ("Guillermo", "Fratta-fruta", "DEF", 64, None, 29),
            ("Mauricio", "Amaral-arrabal", "DEF", 63, None, 23),
            ("Kevin", "Lewis-luis", "DEF", 64, None, 26),
            ("Hernan", "Rivero-riberas", "DEF", 63, "pulmon_de_hierro", 24),
            ("Alvaro", "Navarro-navaja", "MED", 66, None, 28),
            ("Matias", "Arrua-arruga", "MED", 65, None, 24),
            ("Brian", "Lozano-lozania", "MED", 67, "regateador", 30),
            ("Jonathan", "Urretaviscaya-trabalenguas", "MED", 66, "regateador", 35),
            ("Pablo", "Lopez-melo", "MED", 63, None, 26),
            ("Gaston", "Fernandez-gaucho", "MED", 63, None, 21),
            ("Nahuel", "Roldan-roldana", "MED", 64, None, 25),
            ("Emiliano", "Alfaro-faro", "DEL", 66, "lider", 36),
            ("Diego", "Vera-veredas", "DEL", 65, None, 29),
            ("Maximiliano", "Freitas-frito", "DEL", 64, None, 24),
            ("Rodrigo", "Canosa-canoso", "DEL", 63, None, 21),
            ("Joaquin", "Fleitas-flete", "DEL", 62, None, 19),
        ]
    },
    "Boston Rivera": {
        "ciudad": "Montevideo",
        "estrellas": 2.8,
        "estilo_dt": "artetismo",
        "balance": 3200000,
        "jugadores": [
            ("Gaston", "Olveira-olvido", "POR", 67, None, 36),
            ("Bruno", "Antunez-antes", "POR", 62, None, 22),
            ("Agustin", "Ale-aleta", "DEF", 65, None, 27),
            ("Paulo", "Lima-limon", "DEF", 64, None, 26),
            ("Nahuel", "Da Silva-dasilvita", "DEF", 66, "rustico", 27),
            ("Santiago", "Brunelli-brunido", "DEF", 64, None, 25),
            ("Mateo", "Munoz-muneco", "DEF", 63, None, 21),
            ("Rodrigo", "Pollero-pollo", "DEF", 65, None, 29),
            ("Federico", "Pintos-pintura", "DEF", 64, "pulmon_de_hierro", 24),
            ("Lucas", "Lemos-limonada", "MED", 66, None, 24),
            ("Manuel", "Ugarte-primo-lejano", "MED", 65, None, 22),
            ("Leandro", "Suhr-sur", "MED", 66, None, 27),
            ("Maximiliano", "Rodriguez-bostoniano", "MED", 65, None, 25),
            ("Ian", "Rocca-roca", "MED", 64, None, 20),
            ("Facundo", "Machado-machete", "MED", 64, "pulmon_de_hierro", 26),
            ("Matias", "Pena-penita", "MED", 63, None, 23),
            ("Cecilio", "Waterman-aguado", "DEL", 67, "rustico", 34),
            ("Facundo", "Bravo-bravucon", "DEL", 65, None, 25),
            ("Nicolas", "Vallejo-vallecito", "DEL", 64, "regateador", 22),
            ("Santiago", "Bello-bellaco", "DEL", 66, None, 27),
            ("Lautaro", "Pereira-boston", "DEL", 63, None, 20),
        ]
    },
    "River Platita": {
        "ciudad": "Montevideo",
        "estrellas": 2.8,
        "estilo_dt": "kloppismo",
        "balance": 3300000,
        "jugadores": [
            ("Mathias", "Vazquez-vaso", "POR", 67, None, 30),
            ("Adrian", "Bentancur-lejano", "POR", 62, None, 23),
            ("Pablo", "Pallas-palas", "DEF", 65, None, 26),
            ("Guillermo", "May-mayo", "DEF", 66, "rustico", 26),
            ("Mauro", "Estramil-estrambote", "DEF", 64, None, 24),
            ("Brandon", "Rodriguez-darsena", "DEF", 63, None, 22),
            ("Ivan", "Silvera-silvestre", "DEF", 65, None, 28),
            ("Mathias", "Techera-techo", "DEF", 64, "pulmon_de_hierro", 25),
            ("Lucas", "Correa-cinturon", "DEF", 63, None, 21),
            ("Santiago", "Ramirez-darsenero", "MED", 66, None, 25),
            ("Federico", "Acevedo-aceite", "MED", 65, None, 24),
            ("Matias", "Cabrera-cabra", "MED", 67, "regateador", 29),
            ("Nicolas", "Albarracin-alba", "MED", 65, None, 27),
            ("Kevin", "Mendez-mendigo", "MED", 64, None, 23),
            ("Braian", "Barboza-barba", "MED", 63, None, 21),
            ("Gustavo", "Viera-veterano", "MED", 66, "lider", 33),
            ("Joaquin", "Ardaiz-ardido", "DEL", 67, None, 26),
            ("Thiago", "Borbas-burbuja", "DEL", 66, "regateador", 22),
            ("Matias", "Ocampo-campito", "DEL", 65, None, 26),
            ("Franco", "Suarez-darsena", "DEL", 64, None, 23),
            ("Lucas", "Guillen-guillotina", "DEL", 63, None, 20),
        ]
    },
    "Cerro Bajo": {
        "ciudad": "Montevideo",
        "estrellas": 2.6,
        "estilo_dt": "choloismo",
        "balance": 2600000,
        "jugadores": [
            ("Leandro", "Rodriguez-cerrense", "POR", 65, None, 29),
            ("Nicolas", "Fernandez-villero", "POR", 61, None, 22),
            ("Pablo", "Caballero-caballo", "DEF", 64, "rustico", 27),
            ("Gary", "Kagelmacher-kaos", "DEF", 67, "lider", 37),
            ("Diego", "Rodriguez-cerrito", "DEF", 63, None, 24),
            ("Axel", "Sosa-sosita", "DEF", 63, None, 22),
            ("Juan", "Izquierdo-villero", "DEF", 64, None, 26),
            ("Matias", "Quintana-quinta", "DEF", 62, None, 21),
            ("Rodrigo", "Mieres-miel", "DEF", 63, "pulmon_de_hierro", 25),
            ("Carlos", "Sanchez-pato", "MED", 67, "lider", 40),
            ("Facundo", "Silva-cerrense", "MED", 64, None, 26),
            ("Gonzalo", "Vega-vegano", "MED", 63, None, 23),
            ("Ignacio", "Pereira-villa", "MED", 64, "regateador", 24),
            ("Joaquin", "Suarez-cerrito", "MED", 63, None, 22),
            ("Pablo", "Ceppelini-cepillo", "MED", 66, "regateador", 34),
            ("Santiago", "Bueno-malo", "MED", 62, None, 20),
            ("Sergio", "Nunez-cerrense", "DEL", 65, None, 28),
            ("Kevin", "Ramirez-rompe", "DEL", 64, None, 25),
            ("Alexander", "Machado-cerrito", "DEL", 63, "regateador", 22),
            ("Jonathan", "Ramis-ramita", "DEL", 65, "rustico", 36),
            ("Bryan", "Olivera-cerrito", "DEL", 62, None, 19),
        ]
    },
    "Juventud de las Piedritas": {
        "ciudad": "Las Piedras",
        "estrellas": 2.6,
        "estilo_dt": "anchelottismo",
        "balance": 2700000,
        "jugadores": [
            ("Thiago", "Cardozo-cardo", "POR", 66, None, 27),
            ("Santiago", "Silva-pedrero", "POR", 61, None, 23),
            ("Pablo", "Lacoste-cocodrilo", "DEF", 65, None, 29),
            ("Matias", "Ferreira-ferreteria", "DEF", 64, None, 26),
            ("Bruno", "Mendez-piedrense", "DEF", 64, "rustico", 25),
            ("Agustin", "Pereira-pedregal", "DEF", 63, None, 22),
            ("Leonardo", "Pais-paisano", "DEF", 65, "lider", 30),
            ("Franco", "Romero-canto", "DEF", 63, None, 24),
            ("Ezequiel", "Busquets-primo", "DEF", 62, None, 21),
            ("Gonzalo", "Castillo-piedra", "MED", 65, None, 27),
            ("Mauro", "Da Luz-apagon", "MED", 66, "regateador", 30),
            ("Diego", "Zabala-zabaleta", "MED", 64, None, 26),
            ("Nicolas", "Sosa-guijarro", "MED", 63, None, 23),
            ("Emiliano", "Velazquez-veloz", "MED", 64, "pulmon_de_hierro", 25),
            ("Marcos", "Montiel-monte", "MED", 63, None, 22),
            ("Rodrigo", "Canzani-cancion", "MED", 62, None, 20),
            ("Mathias", "Acuna-cuna", "DEL", 66, None, 28),
            ("Gaston", "Rodriguez-canto-rodado", "DEL", 65, "rustico", 33),
            ("Brahian", "Aleman-germano", "DEL", 64, "regateador", 35),
            ("Santiago", "Paiva-pava", "DEL", 63, None, 22),
            ("Lucas", "Pintos-lapicera", "DEL", 62, None, 20),
        ]
    },
    # v3.7.0: fin de la lista de clubes
}

DATOS_URUGUAY = PLANTILLAS_PARODIA

NOMBRES_CORTOS = {
    "Penarol Roto": "Peñarol", "Nacionall de Montevideo": "Nacional URU",
    "Defensor Esporting": "Defensor", "Danubio Seco": "Danubio",
    "Liverpul Uruguayo": "Liverpul", "Wanderers Perdidos": "Wanderers",
    "Racing Sin Frenos": "Racing URU", "Cerro Largo Larguisimo": "Cerro Largo",
    "Boston Rivera": "Boston Rivera", "River Platita": "River Platita",
    "Cerro Bajo": "Cerro Bajo", "Juventud de las Piedritas": "Juventud",
}

ESTILO_OVERRIDE = {
    "Penarol Roto": "choloismo",
    "Nacionall de Montevideo": "anchelottismo",
}


def get_liga() -> Liga:
    """
    Construye y devuelve el objeto Liga AUF Uruguaya
    con plantillas de parodia completamente pobladas.
    """
    try:
        equipos = []
        id_counter = 8000  # v3.7.0: rango propio (12 clubes)

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
            nombre="Liga AUF Uruguaya Parodia",
            tipo="uruguay",
            equipos=equipos,
            num_jornadas=max(2, 2 * (len(equipos) - 1))  # v3.7.0: 12 clubes -> 22
        )
    except Exception as e:
        logger.critical(f"Error crítico al construir la Liga AUF Uruguaya: {e}. Retornando liga vacía.")
        # Retorno seguro para evitar que el juego se caiga por completo (resiliencia)
        return Liga("Liga AUF Uruguaya Fallback", "uruguay", [], 22)
