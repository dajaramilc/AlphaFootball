# -*- coding: utf-8 -*-
"""
Módulo de Datos: Premier League Parodia
Este archivo expone los equipos de la liga inglesa con nombres de parodia de la temporada 2024-25.
Desarrollado de forma resiliente siguiendo los lineamientos de resiliencia del proyecto.
"""

import random
import logging

# Configuración básica del logging del sistema
logging.basicConfig(level=logging.INFO)

# Intentamos importar las clases del contrato de datos principal desde el módulo models
try:
    from alpha_football.models import Liga, Equipo, Jugador
    logging.info("Clases de datos importadas correctamente desde alpha_football.models")
except ImportError as error_importacion:
    logging.warning(
        f"No se pudo importar alpha_football.models debido al aislamiento: {error_importacion}. "
        "Inicializando clases mock locales como solución alternativa de resiliencia."
    )
    from dataclasses import dataclass, field
    from typing import Optional, List

    @dataclass
    class Jugador:
        nombre: str
        apellido: str
        posicion: str
        ataque: int
        defensa: int
        fisico: int
        tecnica: int
        mental: int
        moral: int = 70
        rasgo: Optional[str] = None
        lesion_partidos: int = 0
        id: int = 0
        edad: int = 25

        @property
        def overall(self) -> int:
            return (self.ataque + self.defensa + self.fisico + self.tecnica + self.mental) // 5

        @property
        def nombre_completo(self) -> str:
            return f"{self.nombre} {self.apellido}"

    @dataclass
    class Equipo:
        nombre: str
        ciudad: str
        estrellas: float
        estilo_dt: str
        balance: int
        jugadores: List[Jugador] = field(default_factory=list)
        nombre_corto: str = ""

    @dataclass
    class Liga:
        nombre: str
        tipo: str
        equipos: List[Equipo]
        num_jornadas: int

# Constantes del juego para estilos tácticos de los directores técnicos y rasgos especiales
# v3.3.0: los 9 estilos del motor (sorteo del estilo de los equipos sin estilo fijo).
from alpha_football.estilos import ESTILOS_DT as ESTILOS_TACTICOS  # noqa: E402
RASGOS_DISPONIBLES = ["regateador", "lider", "rustico", "pulmon_de_hierro"]

NOMBRES_CORTOS = {
    "Manchester Billete": "Man Billete", "Arsenal Pechofrio": "Arsenal", "Pool de Higado": "Pool",
    "Manchester Desunido": "Man Desunido", "Chelsea Guarderia": "Chelsea", "Spurs sin Copas": "Spurs",
    # v3.7.0: 6 clubes más (liga de 12)
    "Newcastle Petrodolar": "Newcastle", "Aston Villano": "Villano", "Nottingham Deforestado": "Forest",
    "Brighton Algoritmo": "Brighton", "Crystal Palacete": "Palacete", "Everton Caramelo": "Everton",
}
ESTILO_FIJO = {
    # v3.7.0: clubes nuevos (liga de 12)
    "Newcastle Petrodolar": "kloppismo",
    "Aston Villano": "artetismo",
    "Nottingham Deforestado": "haramball",
    "Brighton Algoritmo": "dezerbismo",
    "Crystal Palacete": "fullbackismo",
    "Everton Caramelo": "haramball",
    "Manchester Billete": "cruyffismo",
    "Arsenal Pechofrio": "cruyffismo",
    "Pool de Higado": "flickismo",
    "Manchester Desunido": "anchelottismo",
    "Chelsea Guarderia": "anchelottismo",
    "Spurs sin Copas": "haramball",
}

def generar_atributos_por_posicion(ovr_sugerido: int, posicion: str) -> tuple[int, int, int, int, int]:
    """
    Genera los 5 atributos individuales de un jugador (ataque, defensa, fisico, tecnica, mental)
    basado en su posición y una valoración general (OVR) sugerida.
    Garantiza de manera resiliente que el promedio entero sea exactamente el OVR.
    """
    try:
        # La valoración asignada máxima para Europa en creación es de 93
        ovr_objetivo = min(max(ovr_sugerido, 40), 93)
        
        if posicion == "POR":
            ataque = 15
            defensa = ovr_objetivo + 15
            fisico = ovr_objetivo + 5
            tecnica = ovr_objetivo - 10
            mental = ovr_objetivo + 10
        elif posicion == "DEF":
            ataque = ovr_objetivo - 25
            defensa = ovr_objetivo + 15
            fisico = ovr_objetivo + 10
            tecnica = ovr_objetivo - 10
            mental = ovr_objetivo + 10
        elif posicion == "MED":
            ataque = ovr_objetivo - 5
            defensa = ovr_objetivo - 5
            fisico = ovr_objetivo
            tecnica = ovr_objetivo + 10
            mental = ovr_objetivo
        else:
            ataque = ovr_objetivo + 15
            defensa = ovr_objetivo - 25
            fisico = ovr_objetivo + 5
            tecnica = ovr_objetivo + 10
            mental = ovr_objetivo - 5

        atributos = [max(10, min(99, val)) for val in (ataque, defensa, fisico, tecnica, mental)]
        
        suma_objetivo = ovr_objetivo * 5
        for _ in range(50):
            suma_actual = sum(atributos)
            if suma_actual == suma_objetivo:
                break
            diferencia = suma_objetivo - suma_actual
            paso = 1 if diferencia > 0 else -1
            
            indices = [0, 1, 2, 3, 4]
            random.shuffle(indices)
            for idx in indices:
                nuevo_valor = atributos[idx] + paso
                if 10 <= nuevo_valor <= 99:
                    atributos[idx] = nuevo_valor
                    break
                    
        return tuple(atributos)

    except Exception as error_generacion:
        logging.error(f"Fallo al generar atributos (OVR={ovr_sugerido}, Pos={posicion}): {error_generacion}. Aplicando fallback.")
        valor_defecto = min(max(ovr_sugerido, 45), 93)
        return (valor_defecto, valor_defecto, valor_defecto, valor_defecto, valor_defecto)

# 20 Jugadores base parodiados por club (con OVR sugerido hasta 93 máximo, rasgo y edad reales de Transfermarkt)
DATOS_PREMIER = {
    "Manchester Billete": {
        "ciudad": "Manchester",
        "estrellas": 4.9,
        "jugadores": [
            ("Ederson", "Penales", "POR", 91, None, 30),
            ("Stefan", "Ortegon", "POR", 84, None, 31),
            ("Kyle", "Correcaminos", "DEF", 90, "pulmon_de_hierro", 34),
            ("Ruben", "Murallas", "DEF", 93, "rustico", 27),
            ("John", "Piedras", "DEF", 90, "lider", 30),
            ("Josko", "Pasaporte", "DEF", 91, "rustico", 22),
            ("Manuel", "Alkansio", "DEF", 90, None, 28),
            ("Nathan", "Akejado", "DEF", 86, "rustico", 29),
            ("Rico", "Bravito", "DEF", 80, "pulmon_de_hierro", 19),
            ("Rodriguez", "5 Estrellas", "MED", 93, "lider", 27),
            ("Kevin", "De Bronca", "MED", 93, "lider", 32),
            ("Mateo", "Pasecito", "MED", 88, None, 30),
            ("Bernardo", "Bosquecito", "MED", 91, "regateador", 29),
            ("Matheus", "Nuñito", "MED", 82, None, 25),
            ("Jack", "Gringo", "MED", 86, "regateador", 28),
            ("James", "Maceta", "MED", 77, None, 21),
            ("Phil", "Fodencito", "DEL", 93, "regateador", 24),
            ("Erling", "Gasoland", "DEL", 93, "pulmon_de_hierro", 23),
            ("Jeremy", "Doku-palo", "DEL", 88, "regateador", 22),
            ("Savinho", "Regates", "DEL", 86, "regateador", 20),
        ]
    },
    "Arsenal Pechofrio": {
        "ciudad": "Londres",
        "estrellas": 4.7,
        "jugadores": [
            ("David", "Rayamuro", "POR", 90, None, 28),
            ("Neto", "Atajadon", "POR", 77, None, 34),
            ("Ben", "Blanco", "DEF", 88, "rustico", 26),
            ("William", "Salivazo", "DEF", 91, "rustico", 23),
            ("Gabriel", "Muralla", "DEF", 90, "rustico", 26),
            ("Jurrien", "Madera", "DEF", 84, None, 23),
            ("Takehiro", "Tomiyaso", "DEF", 82, "rustico", 25),
            ("Oleksandr", "Zinchenco", "DEF", 82, None, 27),
            ("Riccardo", "Calafiori-roto", "DEF", 86, "rustico", 22),
            ("Declan", "Arroz", "MED", 91, "pulmon_de_hierro", 25),
            ("Martin", "Odegol", "MED", 93, "lider", 25),
            ("Thomas", "Fiesta", "MED", 86, None, 31),
            ("Jorginho", "Abuelo", "MED", 82, "lider", 32),
            ("Mikel", "Merino-oro", "MED", 88, "pulmon_de_hierro", 28),
            ("Ethan", "Nwanerito", "MED", 75, "regateador", 17),
            ("Bukayo", "Sacachispas", "DEL", 93, "regateador", 22),
            ("Kai", "Gol-fantasma", "DEL", 90, "regateador", 25),
            ("Gabriel", "Correlotodo", "DEL", 88, "regateador", 27),
            ("Leandro", "Trossardito", "DEL", 88, "regateador", 29),
            ("Gabriel", "Martinellito", "DEL", 86, "regateador", 22),
        ]
    },
    "Pool de Higado": {
        "ciudad": "Liverpool",
        "estrellas": 4.8,
        "jugadores": [
            ("Alisson", "Manos", "POR", 91, "lider", 31),
            ("Caoimhin", "Kelleherazo", "POR", 84, None, 25),
            ("Trent", "Centros", "DEF", 90, "regateador", 25),
            ("Virgil", "El Muro", "DEF", 93, "lider", 32),
            ("Ibrahima", "Konazo", "DEF", 88, "rustico", 25),
            ("Andy", "Correcaminos", "DEF", 88, "pulmon_de_hierro", 30),
            ("Jarell", "Quansah-pibe", "DEF", 80, None, 21),
            ("Conor", "Bradley-rapido", "DEF", 80, "pulmon_de_hierro", 20),
            ("Joe", "Gomez-comodin", "DEF", 82, "rustico", 27),
            ("Alexis", "El Colorado", "MED", 90, "lider", 25),
            ("Dominik", "Impronunciable", "MED", 88, None, 23),
            ("Ryan", "Graven-banco", "MED", 86, "pulmon_de_hierro", 22),
            ("Wataru", "Endo-viejo", "MED", 80, "rustico", 31),
            ("Curtis", "Jonesito", "MED", 82, None, 23),
            ("Harvey", "Elliotito", "MED", 82, "regateador", 21),
            ("Mo", "Ensalada", "DEL", 93, "regateador", 32),
            ("Darwin", "Caos", "DEL", 88, "rustico", 24),
            ("Lucho", "Guajiro", "DEL", 90, "regateador", 27),
            ("Cody", "Gakpazo", "DEL", 86, "regateador", 25),
            ("Diogo", "Jotas", "DEL", 88, "pulmon_de_hierro", 27),
        ]
    },
    "Manchester Desunido": {
        "ciudad": "Manchester",
        "estrellas": 4.2,
        "jugadores": [
            ("Andre", "Manosflojas", "POR", 86, None, 28),
            ("Altay", "Bayindirazo", "POR", 73, None, 26),
            ("Diogo", "Corredor", "DEF", 84, "pulmon_de_hierro", 25),
            ("Matthijs", "De Tronco", "DEF", 86, "rustico", 24),
            ("Lisandro", "El Carnicero", "DEF", 88, "rustico", 26),
            ("Luke", "Lesiones", "DEF", 82, None, 28),
            ("Harry", "Cabezon", "DEF", 80, "rustico", 31),
            ("Noussair", "Mazraouito", "DEF", 84, "pulmon_de_hierro", 26),
            ("Leny", "Yoro-joven", "DEF", 82, None, 18),
            ("Casemito", "Silva", "MED", 86, "lider", 32),
            ("Kobbie", "Minino", "MED", 84, None, 19),
            ("Bruno", "Penaldes", "MED", 91, "lider", 29),
            ("Christian", "Eriksenazo", "MED", 82, None, 32),
            ("Mason", "Monte", "MED", 80, None, 25),
            ("Manuel", "Ugartazo", "MED", 86, "rustico", 23),
            ("Alejandro", "Bichito", "DEL", 86, "regateador", 19),
            ("Marcus", "Corretodo", "DEL", 86, "regateador", 26),
            ("Rasmus", "Joyita", "DEL", 84, None, 21),
            ("Joshua", "Zirkzeazo", "DEL", 82, "regateador", 23),
            ("Antony", "Giros", "DEL", 77, "regateador", 24),
        ]
    },
    "Chelsea Guarderia": {
        "ciudad": "Londres",
        "estrellas": 4.4,
        "jugadores": [
            ("Robert", "Manitos", "POR", 84, None, 26),
            ("Filip", "Jorgensenazo", "POR", 79, None, 22),
            ("Malo", "Gusto", "DEF", 86, "pulmon_de_hierro", 21),
            ("Levi", "Col-pared", "DEF", 84, "rustico", 21),
            ("Wesley", "Fofanas", "DEF", 82, None, 23),
            ("Marc", "Peluca", "DEF", 86, "pulmon_de_hierro", 25),
            ("Axel", "Disasito", "DEF", 80, "rustico", 26),
            ("Reece", "Cristal", "DEF", 88, "lider", 24),
            ("Tosin", "Adarabioyo", "DEF", 80, "rustico", 26),
            ("Enzo", "Dolares", "MED", 88, "lider", 23),
            ("Moises", "Millonario", "MED", 88, "pulmon_de_hierro", 22),
            ("Christopher", "Lesiones", "MED", 88, None, 26),
            ("Romeo", "Lavanda", "MED", 80, "pulmon_de_hierro", 20),
            ("Kiernan", "Dewsbury", "MED", 82, None, 25),
            ("Joao", "Felixazo", "MED", 86, "regateador", 24),
            ("Cole", "Frio", "DEL", 93, "regateador", 22),
            ("Nico", "Fallon", "DEL", 86, None, 22),
            ("Misha", "Tronco", "DEL", 80, "regateador", 23),
            ("Noni", "Madueke", "DEL", 84, "regateador", 22),
            ("Pedro", "Neto-rapido", "DEL", 86, "regateador", 24),
        ]
    },
    "Spurs sin Copas": {
        "ciudad": "Londres",
        "estrellas": 4.3,
        "jugadores": [
            ("Guglielmo", "Paratodo", "POR", 86, None, 27),
            ("Fraser", "Forster-abuelo", "POR", 70, None, 36),
            ("Cristian", "Romero-pego", "DEF", 91, "rustico", 26),
            ("Micky", "Veloz", "DEF", 88, "pulmon_de_hierro", 23),
            ("Destiny", "Udogazo", "DEF", 88, "pulmon_de_hierro", 21),
            ("Pedro", "Porrito", "DEF", 88, "regateador", 24),
            ("Radu", "Dragusin", "DEF", 80, "rustico", 22),
            ("Ben", "Davies-comodin", "DEF", 76, None, 31),
            ("Rodrigo", "Pinturita", "MED", 86, "pulmon_de_hierro", 26),
            ("Yves", "Bissumazo", "MED", 86, "rustico", 27),
            ("James", "Regalon", "MED", 90, "regateador", 27),
            ("Archie", "Gray-joven", "MED", 76, None, 18),
            ("Pape", "Sarr-rapido", "MED", 82, "pulmon_de_hierro", 21),
            ("Dejan", "Pelusa", "MED", 86, "regateador", 24),
            ("Lucas", "Bergvall", "MED", 75, None, 18),
            ("Heung-min", "Hijo", "DEL", 91, "lider", 31),
            ("Richarlison", "Pajarito", "DEL", 84, "rustico", 27),
            ("Timo", "Werner-fallon", "DEL", 80, "pulmon_de_hierro", 28),
            ("Brennan", "Johnsonazo", "DEL", 80, "pulmon_de_hierro", 23),
            ("Dominic", "Solankazo", "DEL", 86, None, 26),
        ]
    },
    # v3.7.0: 6 clubes reales 2025-26 más (liga de 12), jugadores reales parodiados.
    "Newcastle Petrodolar": {
        "ciudad": "Newcastle",
        "estrellas": 4.3,
        "jugadores": [
            ("Nick", "Papa", "POR", 84, "lider", 33),
            ("Aaron", "Ramsdalito", "POR", 80, None, 27),
            ("Kieran", "Tripiero", "DEF", 83, "lider", 35),
            ("Sven", "Botmanazo", "DEF", 84, "rustico", 25),
            ("Fabian", "Schartazo", "DEF", 81, "rustico", 33),
            ("Dan", "Burnout", "DEF", 82, "rustico", 33),
            ("Malick", "Thiawaii", "DEF", 82, None, 24),
            ("Tino", "Livramiento", "DEF", 83, "pulmon_de_hierro", 22),
            ("Lewis", "Hallazgo", "DEF", 80, None, 20),
            ("Bruno", "Guimaraesquisito", "MED", 88, "lider", 27),
            ("Sandro", "Tonalidad", "MED", 87, "pulmon_de_hierro", 25),
            ("Joelinton", "Toro", "MED", 85, "rustico", 29),
            ("Jacob", "Ramsiempre", "MED", 80, None, 24),
            ("Joe", "Willockazo", "MED", 79, None, 26),
            ("Lewis", "Mileyito", "MED", 76, None, 19),
            ("Anthony", "Gordoon", "DEL", 87, "regateador", 24),
            ("Nick", "Woltemadera", "DEL", 84, None, 23),
            ("Yoane", "Wissaguas", "DEL", 83, None, 29),
            ("Harvey", "Barniz", "DEL", 81, "regateador", 28),
            ("Anthony", "Elangosta", "DEL", 82, "regateador", 23),
        ]
    },
    "Aston Villano": {
        "ciudad": "Birmingham",
        "estrellas": 4.2,
        "jugadores": [
            ("Emiliano", "Dibu-Bailarin", "POR", 87, "lider", 33),
            ("Marco", "Bizcocho", "POR", 76, None, 34),
            ("Ezri", "Konsagrado", "DEF", 83, None, 27),
            ("Pau", "Torreta", "DEF", 83, None, 28),
            ("Tyrone", "Mingote", "DEF", 80, "rustico", 32),
            ("Matty", "Cashback", "DEF", 81, "pulmon_de_hierro", 28),
            ("Lucas", "Dignidad", "DEF", 80, None, 32),
            ("Ian", "Maatsenado", "DEF", 79, None, 23),
            ("Victor", "Lindelento", "DEF", 78, "lider", 31),
            ("Youri", "Tielemaniaco", "MED", 85, None, 28),
            ("Boubacar", "Kamarada", "MED", 84, "rustico", 25),
            ("John", "McGinebra", "MED", 83, "lider", 30),
            ("Amadou", "Onanana", "MED", 83, "pulmon_de_hierro", 24),
            ("Morgan", "Rogelio", "MED", 85, "regateador", 23),
            ("Ross", "Barquito", "MED", 76, None, 31),
            ("Emiliano", "Buendiario", "MED", 78, "regateador", 28),
            ("Ollie", "Guatkins", "DEL", 85, None, 29),
            ("Donyell", "Malentendido", "DEL", 80, None, 26),
            ("Evann", "Guessandia", "DEL", 79, None, 24),
            ("Jadon", "Sanchocho", "DEL", 79, "regateador", 25),
        ]
    },
    "Nottingham Deforestado": {
        "ciudad": "Nottingham",
        "estrellas": 3.9,
        "jugadores": [
            ("Matz", "Selfie", "POR", 83, None, 33),
            ("John", "Victorioso", "POR", 74, None, 29),
            ("Murillo", "Murallito", "DEF", 84, "rustico", 23),
            ("Nikola", "Milenkobrick", "DEF", 83, "rustico", 27),
            ("Ola", "Aina-hola", "DEF", 81, "pulmon_de_hierro", 29),
            ("Neco", "Williamsito", "DEF", 80, None, 24),
            ("Morato", "Moraton", "DEF", 77, None, 24),
            ("Nicolo", "Savonata", "DEF", 77, None, 22),
            ("Elliot", "Andersoon", "MED", 85, "pulmon_de_hierro", 22),
            ("Morgan", "Gibbs-Blanco", "MED", 85, "regateador", 25),
            ("Ibrahim", "Sangarage", "MED", 79, "rustico", 28),
            ("Nicolas", "Dominguito", "MED", 79, None, 27),
            ("James", "McAtiempo", "MED", 78, None, 22),
            ("Omari", "Hutchinsonrisa", "MED", 78, "regateador", 22),
            ("Chris", "Troncoso", "DEL", 83, None, 33),
            ("Callum", "Hudson-Otroi", "DEL", 80, "regateador", 24),
            ("Dan", "Ndoyito", "DEL", 80, "regateador", 25),
            ("Igor", "Jesusito", "DEL", 79, None, 24),
            ("Arnaud", "Kalimuendito", "DEL", 78, None, 23),
            ("Dilane", "Bakwando", "DEL", 76, "regateador", 23),
        ]
    },
    "Brighton Algoritmo": {
        "ciudad": "Brighton",
        "estrellas": 3.9,
        "jugadores": [
            ("Bart", "Verbruguesa", "POR", 81, None, 23),
            ("Jason", "Stealth", "POR", 72, None, 35),
            ("Jan Paul", "Van Heckerito", "DEF", 81, "rustico", 25),
            ("Lewis", "Dunkeado", "DEF", 80, "lider", 34),
            ("Joel", "Veltmano", "DEF", 77, None, 33),
            ("Ferdi", "Kadiogluten", "DEF", 81, "pulmon_de_hierro", 26),
            ("Maxim", "De Cuypercito", "DEF", 78, None, 24),
            ("Olivier", "Boscaglio", "DEF", 77, None, 27),
            ("Carlos", "Balebalazo", "MED", 84, "pulmon_de_hierro", 21),
            ("Mats", "Wiefferino", "MED", 79, None, 25),
            ("Yasin", "Ayarigato", "MED", 79, None, 22),
            ("Jack", "Hinshelguau", "MED", 77, None, 20),
            ("James", "Milnerario", "MED", 75, "lider", 39),
            ("Diego", "Gomezclado", "MED", 78, None, 22),
            ("Tommy", "Watsonrisa", "MED", 76, "regateador", 19),
            ("Kaoru", "Mitomate", "DEL", 83, "regateador", 28),
            ("Danny", "Welbecario", "DEL", 79, None, 34),
            ("Yankuba", "Mintehado", "DEL", 81, "regateador", 21),
            ("Stefanos", "Tzimasas", "DEL", 76, None, 19),
            ("Brajan", "Grudazo", "DEL", 77, "regateador", 21),
        ]
    },
    "Crystal Palacete": {
        "ciudad": "Londres",
        "estrellas": 3.9,
        "jugadores": [
            ("Dean", "Hendersonrisa", "POR", 83, "lider", 28),
            ("Walter", "Benitezcito", "POR", 75, None, 32),
            ("Marc", "Guehielo", "DEF", 84, "lider", 25),
            ("Maxence", "Lacruz", "DEF", 82, "rustico", 25),
            ("Chris", "Riquezas", "DEF", 79, None, 25),
            ("Daniel", "Muñoztang", "DEF", 82, "pulmon_de_hierro", 29),
            ("Tyrick", "Mitchellin", "DEF", 79, None, 25),
            ("Borna", "Sosaso", "DEF", 76, None, 27),
            ("Nathaniel", "Clynazo", "DEF", 72, None, 34),
            ("Jaydee", "Canvoto", "DEF", 74, None, 19),
            ("Adam", "Whartonazo", "MED", 84, None, 21),
            ("Jefferson", "Lermita", "MED", 80, "rustico", 30),
            ("Will", "Hughesito", "MED", 77, None, 30),
            ("Daichi", "Kamadita", "MED", 80, None, 29),
            ("Justin", "Devenido", "MED", 74, None, 22),
            ("Christantus", "Uchepa", "MED", 76, None, 22),
            ("Ismaila", "Sarrampion", "DEL", 83, "regateador", 27),
            ("Jean-Philippe", "Mateteta", "DEL", 83, None, 28),
            ("Yeremy", "Pinito", "DEL", 80, "regateador", 23),
            ("Eddie", "Nketiahora", "DEL", 76, None, 26),
        ]
    },
    "Everton Caramelo": {
        "ciudad": "Liverpool",
        "estrellas": 3.8,
        "jugadores": [
            ("Jordan", "Pickfuria", "POR", 84, "lider", 31),
            ("Mark", "Traversura", "POR", 74, None, 26),
            ("James", "Tarkowskazo", "DEF", 81, "rustico", 32),
            ("Jarrad", "Branthwaitazo", "DEF", 82, "rustico", 23),
            ("Michael", "Keanejo", "DEF", 77, None, 32),
            ("Vitalii", "Mykolenkito", "DEF", 78, None, 26),
            ("Jake", "O'Brienazo", "DEF", 77, None, 24),
            ("Nathan", "Pattersonrisa", "DEF", 75, None, 23),
            ("Seamus", "Colemanazo", "DEF", 71, "lider", 37),
            ("James", "Garnacha", "MED", 80, "pulmon_de_hierro", 24),
            ("Idrissa", "Gueyeperro", "MED", 79, "rustico", 36),
            ("Tim", "Iroegbunombre", "MED", 74, None, 22),
            ("Kiernan", "Dewsbury-Mall", "MED", 79, None, 27),
            ("Carlos", "Alcaraqueta", "MED", 75, None, 22),
            ("Jack", "Grealishampu", "MED", 83, "regateador", 30),
            ("Merlin", "Rolito", "MED", 74, None, 23),
            ("Iliman", "Ndiayeah", "DEL", 81, "regateador", 25),
            ("Beto", "Betoven", "DEL", 77, None, 27),
            ("Thierno", "Barrial", "DEL", 77, None, 23),
            ("Dwight", "McNeilson", "DEL", 78, "regateador", 25),
            ("Tyler", "Diblingo", "DEL", 75, "regateador", 19),
        ]
    },
}

def crear_liga_fallback() -> Liga:
    """
    Solución alternativa de emergencia en caso de que la inicialización principal falle.
    """
    try:
        equipos_fallback = []
        for nombre_eq, data in DATOS_PREMIER.items():
            jugadores_fallback = []
            for j_data in data["jugadores"]:
                jugadores_fallback.append(Jugador(
                    nombre=j_data[0],
                    apellido=j_data[1],
                    posicion=j_data[2],
                    ataque=70,
                    defensa=70,
                    fisico=70,
                    tecnica=70,
                    mental=70,
                    moral=70,
                    rasgo=None,
                    lesion_partidos=0,
                    edad=j_data[5] if len(j_data) > 5 else 25
                ))
            
            equipos_fallback.append(Equipo(
                nombre=nombre_eq,
                ciudad=data["ciudad"],
                estrellas=data["estrellas"],
                estilo_dt=random.choice(ESTILOS_TACTICOS),
                balance=int(data["estrellas"] * 5000000),
                jugadores=jugadores_fallback,
                nombre_corto=NOMBRES_CORTOS.get(nombre_eq, "")
            ))
            
        return Liga(
            nombre="Premier League Parodia (Fallback)",
            tipo="premier",
            equipos=equipos_fallback,
            num_jornadas=max(2, 2 * (len(equipos_fallback) - 1))  # v3.7.0
        )
    except Exception as error_fallback:
        logging.critical(f"Fallo critico doble en fallback: {error_fallback}. Retornando objeto estatico basico.")
        return Liga(
            nombre="Premier League Parodia (Emergencia)",
            tipo="premier",
            equipos=[],
            num_jornadas=10
        )

def get_liga() -> Liga:
    """
    Construye y retorna la instancia de la Liga con sus 12 equipos y jugadores parodiados (v3.7.0).
    """
    try:
        equipos_list = []
        id_counter = 500
        TOP_12_PLAYERS = {
            "Erling Gasoland", "Kylian Mbappenal", "Kevin De Bronca", "Ficticius Jr",
            "Jude Bellin-gol", "Mo Ensalada", "Lamine Yabien", "Cole Frio",
            "Virgil El Muro", "Martin Odegol", "Antoine Gringo", "Bukayo Sacachispas"
        }
        for nombre_equipo, info in DATOS_PREMIER.items():
            jugadores_equipo = []
            for j_data in info["jugadores"]:
                id_counter += 1
                pnombre, papellido, pos, ovr, rasgo, edad = j_data
                
                # Intentar convertir ovr a entero en caso de que venga como string
                try:
                    ovr_int = int(ovr)
                except Exception:
                    ovr_int = 75
                
                # Regulación de Ratings Europa (Máximo 12 jugadores OVR >= 90)
                full_name = f"{pnombre} {papellido}".strip()
                if ovr_int >= 90 and full_name not in TOP_12_PLAYERS:
                    ovr_int = 89
                
                # Generamos los 5 atributos individuales de forma coherente y robusta
                atk, dfs, fis, tec, men = generar_atributos_por_posicion(ovr_int, pos)
                
                jugador = Jugador(
                    nombre=pnombre,
                    apellido=papellido,
                    posicion=pos,
                    ataque=atk,
                    defensa=dfs,
                    fisico=fis,
                    tecnica=tec,
                    mental=men,
                    moral=70,
                    rasgo=rasgo,
                    lesion_partidos=0,
                    id=id_counter,
                    edad=edad
                )
                jugadores_equipo.append(jugador)
            
            presupuesto = int(info["estrellas"] * 5000000)
            estilo = ESTILO_FIJO.get(nombre_equipo) or random.choice(ESTILOS_TACTICOS)

            equipo = Equipo(
                nombre=nombre_equipo,
                ciudad=info["ciudad"],
                estrellas=info["estrellas"],
                estilo_dt=estilo,
                balance=presupuesto,
                jugadores=jugadores_equipo,
                nombre_corto=NOMBRES_CORTOS.get(nombre_equipo, "")
            )
            equipos_list.append(equipo)
            
        return Liga(
            nombre="Premier League Parodia",
            tipo="premier",
            equipos=equipos_list,
            num_jornadas=max(2, 2 * (len(equipos_list) - 1))  # v3.7.0: ida y vuelta (12 → 22)
        )
        
    except Exception as error_global:
        logging.error(f"Error critico en get_liga() de premier.py: {error_global}. Activando resiliencia.")
        return crear_liga_fallback()
