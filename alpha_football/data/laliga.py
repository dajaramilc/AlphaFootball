# -*- coding: utf-8 -*-
"""
Módulo de Datos: LaLiga EA Sports Parodia
Este archivo expone los equipos de la liga española con nombres de parodia de la temporada 2024-25.
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
    "Real Madriz": "R. Madriz", "FC Farcelona": "Farcelona", "Patetico de Madriz": "Patetico",
    "Girona Sorpresa": "Girona", "Real Suciedad": "R. Suciedad", "Athletic de Bilbao": "Athletic",
    # v3.7.0: 6 clubes más (liga de 12)
    "Submarino Oxidado": "Submarino", "Betis Manque Pierda": "Betis", "Sevilla Sin Monchi": "Sevilla",
    "Valencia Sin Estadio": "Valencia", "Celta de Viejo": "Celta", "Rayo Vallecansado": "Rayo",
}
ESTILO_FIJO = {
    # v3.7.0: clubes nuevos (liga de 12)
    "Submarino Oxidado": "anchelottismo",
    "Betis Manque Pierda": "cruyffismo",
    "Sevilla Sin Monchi": "kloppismo",
    "Valencia Sin Estadio": "haramball",
    "Celta de Viejo": "fullbackismo",
    "Rayo Vallecansado": "kloppismo",
    "Real Madriz": "anchelottismo",
    "FC Farcelona": "cruyffismo",
    "Patetico de Madriz": "haramball",
    "Girona Sorpresa": "cruyffismo",
    "Real Suciedad": "anchelottismo",
    "Athletic de Bilbao": "flickismo",
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
DATOS_LALIGA = {
    "Real Madriz": {
        "ciudad": "Madrid",
        "estrellas": 4.8,
        "jugadores": [
            ("Thibaut", "Murois", "POR", 93, "lider", 32),
            ("Andriy", "Lunito", "POR", 88, None, 25),
            ("Dani", "Tarjetas", "DEF", 91, "rustico", 32),
            ("Eder", "Limitado", "DEF", 90, "rustico", 26),
            ("Antonio", "Lokiger", "DEF", 91, "rustico", 31),
            ("Ferland", "Tronky", "DEF", 86, "pulmon_de_hierro", 29),
            ("Lucas", "Vazquito", "DEF", 82, "pulmon_de_hierro", 32),
            ("Fran", "Garcipillo", "DEF", 80, None, 24),
            ("Fede", "Pajarito", "MED", 93, "pulmon_de_hierro", 25),
            ("Aurelien", "Chuminas", "MED", 90, "pulmon_de_hierro", 24),
            ("Jude", "Bellin-gol", "MED", 93, "lider", 20),
            ("Eduardo", "Camavingazo", "MED", 90, "regateador", 21),
            ("Luka", "Viejic", "MED", 88, "lider", 38),
            ("Dani", "Cebollas", "MED", 80, None, 27),
            ("Arda", "Gülercito", "MED", 84, "regateador", 19),
            ("Ficticius", "Jr", "DEL", 93, "regateador", 23),
            ("Kylian", "Mbappenal", "DEL", 93, "regateador", 25),
            ("Rodryguito", "Pase", "DEL", 91, "regateador", 23),
            ("Brahim", "Diazazo", "DEL", 86, "regateador", 24),
            ("Endricki", "Bebe", "DEL", 82, None, 17),
        ]
    },
    "FC Farcelona": {
        "ciudad": "Barcelona",
        "estrellas": 4.7,
        "jugadores": [
            ("Marc", "Estatua", "POR", 90, None, 32),
            ("Inaki", "Penas", "POR", 79, None, 25),
            ("Jules", "Kouture", "DEF", 90, "pulmon_de_hierro", 25),
            ("Ronald", "Cristal", "DEF", 90, "rustico", 25),
            ("Pau", "Cubardí", "DEF", 86, None, 17),
            ("Alejandro", "Balde-vacío", "DEF", 86, "pulmon_de_hierro", 20),
            ("Inigo", "Martillo", "DEF", 84, "rustico", 33),
            ("Andreas", "Cristales", "DEF", 86, None, 28),
            ("Hector", "Fortachon", "DEF", 77, None, 17),
            ("Pedri-tila", "Gonzalez", "MED", 91, "regateador", 21),
            ("Gavilan", "Perez", "MED", 90, "rustico", 19),
            ("Frenkie", "De Vidrio", "MED", 90, "regateador", 27),
            ("Dani", "Olmito", "MED", 91, "regateador", 26),
            ("Fermin", "Lopezazo", "MED", 84, "pulmon_de_hierro", 21),
            ("Marc", "Soltero", "MED", 82, "pulmon_de_hierro", 20),
            ("Lamine", "Yabien", "DEL", 93, "regateador", 16),
            ("Robert", "Abueloski", "DEL", 91, "lider", 35),
            ("Raphinhazo", "Dias", "DEL", 91, "pulmon_de_hierro", 27),
            ("Ferran", "Ayunorres", "DEL", 84, "pulmon_de_hierro", 24),
            ("Pau", "Delgado", "DEL", 77, None, 22),
        ]
    },
    "Patetico de Madriz": {
        "ciudad": "Madrid",
        "estrellas": 4.5,
        "jugadores": [
            ("Jan", "Muroblak", "POR", 91, "lider", 31),
            ("Juan", "Musso-lento", "POR", 80, None, 30),
            ("Cesar", "Viejito", "DEF", 84, "lider", 34),
            ("Josema", "Lesiones", "DEF", 88, "rustico", 29),
            ("Axel", "Peluca", "DEF", 84, None, 35),
            ("Marcos", "Correcaminos", "DEF", 88, "pulmon_de_hierro", 29),
            ("Robin", "Le Normandia", "DEF", 88, "rustico", 27),
            ("Nahuel", "Molinera", "DEF", 82, "pulmon_de_hierro", 26),
            ("Clement", "Lengletazo", "DEF", 80, None, 29),
            ("Rodrigo", "El Guardaespaldas", "MED", 90, "rustico", 30),
            ("Conor", "Correlotodo", "MED", 88, "pulmon_de_hierro", 24),
            ("Koke-cola", "Resurreccion", "MED", 86, "lider", 32),
            ("Pablo", "Barrilete", "MED", 84, "pulmon_de_hierro", 20),
            ("Thomas", "Limonier", "MED", 79, None, 28),
            ("Samuel", "Lino-rapido", "MED", 81, "regateador", 24),
            ("Antoine", "Hombregris", "DEL", 91, "regateador", 33),
            ("Julian", "Spider", "DEL", 91, "regateador", 24),
            ("Alexander", "Gigantoth", "DEL", 88, None, 28),
            ("Angelito", "Correa", "DEL", 84, "regateador", 29),
            ("Giuliano", "Simeolin", "DEL", 77, "pulmon_de_hierro", 21),
        ]
    },
    "Girona Sorpresa": {
        "ciudad": "Girona",
        "estrellas": 4.0,
        "jugadores": [
            ("Paulo", "Parades", "POR", 84, None, 32),
            ("Juan", "Carlos Falso", "POR", 70, None, 36),
            ("Daley", "Cegato", "DEF", 82, "lider", 34),
            ("David", "Tronquez", "DEF", 80, "rustico", 34),
            ("Arnau", "Corredor", "DEF", 80, "pulmon_de_hierro", 21),
            ("Miguel", "Lateral", "DEF", 86, "regateador", 22),
            ("Ladislav", "Paquetazo", "DEF", 82, "rustico", 25),
            ("Alejandro", "Frances", "DEF", 79, None, 21),
            ("Yangel", "Guerrero", "MED", 84, "rustico", 26),
            ("Ivan", "Toquecito", "MED", 82, None, 25),
            ("Viktor", "Chiguanki", "MED", 86, "regateador", 26),
            ("Oriol", "Tronco", "MED", 79, "rustico", 32),
            ("Donny", "Van de Banco", "MED", 80, None, 27),
            ("Gabriel", "Paquetazo", "MED", 73, "regateador", 18),
            ("Christian", "Stuani Viejito", "DEL", 80, "lider", 37),
            ("Abel", "Ruiz Ballon", "DEL", 80, None, 24),
            ("Portu-gol", "Cristian", "DEL", 82, "pulmon_de_hierro", 32),
            ("Bojan", "Miov", "DEL", 79, None, 24),
            ("Arnaut", "Danjumo", "DEL", 82, "regateador", 27),
            ("Bryan", "Gringuito", "DEL", 82, "regateador", 23),
        ]
    },
    "Real Suciedad": {
        "ciudad": "San Sebastian",
        "estrellas": 4.2,
        "jugadores": [
            ("Alex", "Sinmanos", "POR", 88, None, 29),
            ("Unai", "Marrero", "POR", 70, None, 22),
            ("Hamari", "Moto", "DEF", 82, "pulmon_de_hierro", 32),
            ("Igor", "Subes-y-bajas", "DEF", 84, "rustico", 27),
            ("Javi", "Desborde", "DEF", 80, None, 22),
            ("Jon", "Paquetazo", "DEF", 80, "rustico", 23),
            ("Nayef", "Aguardiente", "DEF", 86, "rustico", 28),
            ("Alvaro", "Odriozolento", "DEF", 74, "pulmon_de_hierro", 28),
            ("Martin", "Subete-a-mendi", "MED", 90, "lider", 25),
            ("Brais", "Magia", "MED", 86, "regateador", 27),
            ("Benat", "Turrientes", "MED", 82, None, 22),
            ("Luka", "Sucic", "MED", 84, "regateador", 21),
            ("Arsen", "Zakhariano", "MED", 80, None, 21),
            ("Jon Ander", "Olasagasti", "MED", 73, None, 23),
            ("Take", "Kubo-rubik", "DEL", 90, "regateador", 23),
            ("Mikel", "Oyarcabezazo", "DEL", 88, "lider", 27),
            ("Ander", "Barrena", "DEL", 82, "regateador", 22),
            ("Umar", "Sadiqaco", "DEL", 79, None, 27),
            ("Orri", "Oskarsson", "DEL", 79, None, 19),
            ("Sheraldo", "Correcaminos", "DEL", 82, "pulmon_de_hierro", 29),
        ]
    },
    "Athletic de Bilbao": {
        "ciudad": "Bilbao",
        "estrellas": 4.3,
        "jugadores": [
            ("Unai", "Paredon", "POR", 91, "lider", 27),
            ("Julen", "Agirrezabaleta", "POR", 80, None, 23),
            ("Oscar", "de Marcos Viejito", "DEF", 82, "lider", 35),
            ("Dani", "Murivian", "DEF", 86, "rustico", 24),
            ("Yeray", "Fuerte", "DEF", 82, "rustico", 29),
            ("Yuri", "Berrinche", "DEF", 82, "rustico", 34),
            ("Aitor", "Paredon", "DEF", 84, "rustico", 23),
            ("Andoni", "Gorosabel", "DEF", 79, None, 27),
            ("Inigo", "Ruiz de Galarreta", "MED", 82, "pulmon_de_hierro", 30),
            ("Oihan", "Sanceto", "MED", 88, "regateador", 24),
            ("Mikel", "Vesgazo", "MED", 80, None, 31),
            ("Benat", "Prados", "MED", 80, "pulmon_de_hierro", 23),
            ("Ander", "Herrera Viejo", "MED", 76, "lider", 34),
            ("Unai", "Gomez Humito", "MED", 79, "pulmon_de_hierro", 21),
            ("Nico", "Billiams", "DEL", 91, "regateador", 21),
            ("Inaki", "Billiams", "DEL", 88, "pulmon_de_hierro", 30),
            ("Gorka", "Gurugol", "DEL", 84, None, 27),
            ("Alex", "Berenguer", "DEL", 82, "regateador", 28),
            ("Alvaro", "Djalito", "DEL", 80, "regateador", 24),
            ("Asier", "Villalibre", "DEL", 76, "rustico", 26),
        ]
    },
    # v3.7.0: 6 clubes reales 2025-26 más (liga de 12), jugadores reales parodiados.
    "Submarino Oxidado": {
        "ciudad": "Villarreal",
        "estrellas": 4.1,
        "jugadores": [
            ("Luiz", "Juniorcito", "POR", 80, None, 24),
            ("Diego", "Condesito", "POR", 79, None, 27),
            ("Juan", "Foytazo", "DEF", 82, None, 27),
            ("Renato", "Veigarrote", "DEF", 81, None, 22),
            ("Rafa", "Marinero", "DEF", 80, None, 23),
            ("Logan", "Costanera", "DEF", 79, "rustico", 24),
            ("Sergi", "Cardonazo", "DEF", 79, None, 26),
            ("Alfonso", "Pedrazo", "DEF", 78, "pulmon_de_hierro", 29),
            ("Santiago", "Mouriñito", "DEF", 76, None, 23),
            ("Santi", "Comesanta", "MED", 81, "pulmon_de_hierro", 29),
            ("Dani", "Parejito", "MED", 83, "lider", 36),
            ("Pape", "Gueyeton", "MED", 80, "rustico", 26),
            ("Alberto", "Moleirazo", "MED", 84, "regateador", 22),
            ("Tajon", "Buchananas", "MED", 79, "regateador", 26),
            ("Ilias", "Akhomachito", "MED", 76, "regateador", 21),
            ("Gerard", "Morenito", "DEL", 81, None, 33),
            ("Ayoze", "Perezoso", "DEL", 83, None, 32),
            ("Nicolas", "Pepetazo", "DEL", 81, "regateador", 30),
            ("Georges", "Mikautadzito", "DEL", 81, None, 25),
            ("Tani", "Oluwaseyito", "DEL", 76, None, 25),
        ]
    },
    "Betis Manque Pierda": {
        "ciudad": "Sevilla",
        "estrellas": 4.0,
        "jugadores": [
            ("Alvaro", "Vallesito", "POR", 80, None, 28),
            ("Adrian", "San Miguelito", "POR", 72, "lider", 38),
            ("Hector", "Bellerinazo", "DEF", 79, None, 30),
            ("Aitor", "Ruibalazo", "DEF", 78, "pulmon_de_hierro", 29),
            ("Diego", "Llorentejo", "DEF", 80, "rustico", 32),
            ("Marc", "Bartrampa", "DEF", 77, "lider", 34),
            ("Natan", "Natacion", "DEF", 80, "rustico", 24),
            ("Valentin", "Gomezquino", "DEF", 78, None, 22),
            ("Ricardo", "Rodriguezuela", "DEF", 76, None, 33),
            ("Isco", "Magia Vieja", "MED", 85, "regateador", 33),
            ("Giovani", "Lo Celsito", "MED", 83, "regateador", 29),
            ("Sofyan", "Amrabatido", "MED", 80, "rustico", 29),
            ("Marc", "Rocadura", "MED", 79, None, 28),
            ("Pablo", "Fornalito", "MED", 80, None, 29),
            ("Sergi", "Altimirador", "MED", 76, None, 24),
            ("Nelson", "Deossito", "MED", 76, "pulmon_de_hierro", 25),
            ("Antony", "Girotrompo", "DEL", 83, "regateador", 25),
            ("Abde", "Ezzalzoulito", "DEL", 81, "regateador", 23),
            ("Cucho", "Hernandito", "DEL", 81, None, 26),
            ("Chimy", "Avilanzado", "DEL", 76, "rustico", 31),
        ]
    },
    "Sevilla Sin Monchi": {
        "ciudad": "Sevilla",
        "estrellas": 3.8,
        "jugadores": [
            ("Odysseas", "Vlachodormido", "POR", 78, None, 32),
            ("Orjan", "Nylandia", "POR", 77, None, 35),
            ("Jose Angel", "Carmonazo", "DEF", 78, None, 23),
            ("Kike", "Salero", "DEF", 77, "rustico", 23),
            ("Marcao", "Marcadon", "DEF", 77, "rustico", 29),
            ("Tanguy", "Nianzouzou", "DEF", 76, None, 23),
            ("Cesar", "Azpilicuesta", "DEF", 77, "lider", 36),
            ("Gabriel", "Suazorro", "DEF", 77, None, 28),
            ("Juanlu", "Sanchezinho", "DEF", 78, "pulmon_de_hierro", 22),
            ("Nemanja", "Gudeljazo", "MED", 79, "lider", 34),
            ("Lucien", "Agoumetralla", "MED", 78, None, 23),
            ("Djibril", "Sowtware", "MED", 78, None, 28),
            ("Batista", "Mendigo", "MED", 76, "rustico", 25),
            ("Joan", "Jordanito", "MED", 76, None, 31),
            ("Ruben", "Vargasolina", "MED", 79, "regateador", 27),
            ("Chidera", "Ejukebox", "DEL", 79, "regateador", 27),
            ("Isaac", "Romerito", "DEL", 78, None, 25),
            ("Akor", "Adamsito", "DEL", 79, None, 25),
            ("Alexis", "Sancheztrasnochado", "DEL", 78, "regateador", 36),
            ("Peque", "Fernandito", "DEL", 74, "regateador", 23),
        ]
    },
    "Valencia Sin Estadio": {
        "ciudad": "Valencia",
        "estrellas": 3.7,
        "jugadores": [
            ("Julen", "Agirrezabalazo", "POR", 79, None, 24),
            ("Stole", "Dimitrievsky", "POR", 77, None, 32),
            ("Jose", "Gaya-yai", "DEF", 80, "lider", 30),
            ("Cesar", "Tarregazo", "DEF", 78, "rustico", 23),
            ("Jose", "Copetudo", "DEF", 76, None, 26),
            ("Mouctar", "Diakhabyte", "DEF", 77, "rustico", 29),
            ("Eray", "Comercial", "DEF", 75, None, 27),
            ("Dimitri", "Foulquierda", "DEF", 76, None, 32),
            ("Thierry", "Correita", "DEF", 76, "pulmon_de_hierro", 26),
            ("Pepelu", "Pepelotas", "MED", 79, "lider", 27),
            ("Javi", "Guerrilla", "MED", 80, None, 22),
            ("Baptiste", "Santamarina", "MED", 77, "rustico", 30),
            ("Andre", "Almeidita", "MED", 78, None, 25),
            ("Filip", "Ugrinico", "MED", 76, None, 26),
            ("Luis", "Riojita", "MED", 78, "regateador", 31),
            ("Diego", "Lopezote", "MED", 78, "regateador", 23),
            ("Hugo", "Duracel", "DEL", 79, "pulmon_de_hierro", 26),
            ("Arnaut", "Danjumanji", "DEL", 79, "regateador", 28),
            ("Dani", "Rabanito", "DEL", 76, None, 30),
            ("Lucas", "Beltranquilo", "DEL", 77, None, 24),
        ]
    },
    "Celta de Viejo": {
        "ciudad": "Vigo",
        "estrellas": 3.6,
        "jugadores": [
            ("Ivan", "Villarejo", "POR", 77, None, 28),
            ("Ionut", "Raduloso", "POR", 76, None, 28),
            ("Oscar", "Minguezazo", "DEF", 79, None, 26),
            ("Carl", "Starfeltro", "DEF", 77, "rustico", 30),
            ("Marcos", "Alonsete", "DEF", 76, "lider", 34),
            ("Javi", "Rodriguito", "DEF", 76, None, 22),
            ("Sergio", "Carreirazo", "DEF", 77, "pulmon_de_hierro", 25),
            ("Joseph", "Aidoodoo", "DEF", 75, None, 29),
            ("Carlos", "Dominguezin", "DEF", 76, None, 24),
            ("Fran", "Beltranca", "MED", 78, None, 26),
            ("Ilaix", "Moribundo", "MED", 78, "rustico", 22),
            ("Hugo", "Sotelito", "MED", 76, None, 22),
            ("Damian", "Rodriguezzz", "MED", 74, None, 22),
            ("Williot", "Swedbergamota", "MED", 76, None, 21),
            ("Hugo", "Alvarezito", "MED", 77, "regateador", 22),
            ("Iago", "Aspasiempre", "DEL", 82, "lider", 38),
            ("Borja", "Iglesiapanda", "DEL", 80, None, 32),
            ("Ferran", "Jutglaaa", "DEL", 77, None, 26),
            ("Bryan", "Zaragozano", "DEL", 77, "regateador", 24),
            ("Pablo", "Duranguito", "DEL", 75, None, 24),
        ]
    },
    "Rayo Vallecansado": {
        "ciudad": "Madrid",
        "estrellas": 3.6,
        "jugadores": [
            ("Augusto", "Batallon", "POR", 78, None, 29),
            ("Dani", "Cardenal", "POR", 74, None, 28),
            ("Florian", "Lejeunito", "DEF", 78, "lider", 34),
            ("Pep", "Chavarriazo", "DEF", 77, None, 27),
            ("Andrei", "Ratiuuu", "DEF", 78, "pulmon_de_hierro", 27),
            ("Ivan", "Balliuna", "DEF", 75, None, 33),
            ("Abdul", "Mumincito", "DEF", 76, "rustico", 27),
            ("Luiz", "Felipon", "DEF", 76, None, 28),
            ("Alfonso", "Espinoso", "DEF", 75, None, 33),
            ("Oscar", "Valentinazo", "MED", 78, "pulmon_de_hierro", 31),
            ("Pathe", "Cissterna", "MED", 77, "rustico", 31),
            ("Unai", "Lopezito", "MED", 77, None, 29),
            ("Oscar", "Trejoven", "MED", 76, "lider", 37),
            ("Isi", "Palazonazo", "MED", 80, "regateador", 30),
            ("Pedro", "Diazepam", "MED", 76, None, 27),
            ("Jorge", "De Frutas", "DEL", 80, "regateador", 28),
            ("Alvaro", "Garciatenazo", "DEL", 78, "regateador", 33),
            ("Sergio", "Camellazo", "DEL", 77, None, 24),
            ("Randy", "Ntekazo", "DEL", 75, None, 27),
            ("Alemao", "Aleman", "DEL", 75, None, 27),
        ]
    },
}

def crear_liga_fallback() -> Liga:
    """
    Solución alternativa de emergencia en caso de que la inicialización principal falle.
    """
    try:
        equipos_fallback = []
        for nombre_eq, data in DATOS_LALIGA.items():
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
            nombre="LaLiga EA Sports Parodia (Fallback)",
            tipo="laliga",
            equipos=equipos_fallback,
            num_jornadas=max(2, 2 * (len(equipos_fallback) - 1))  # v3.7.0
        )
    except Exception as error_fallback:
        logging.critical(f"Fallo critico doble en fallback: {error_fallback}. Retornando objeto estatico basico.")
        return Liga(
            nombre="LaLiga EA Sports Parodia (Emergencia)",
            tipo="laliga",
            equipos=[],
            num_jornadas=10
        )

def get_liga() -> Liga:
    """
    Construye y retorna la instancia de la Liga con sus 12 equipos y jugadores parodiados (v3.7.0).
    """
    try:
        equipos_list = []
        id_counter = 400
        TOP_12_PLAYERS = {
            "Erling Gasoland", "Kylian Mbappenal", "Kevin De Bronca", "Ficticius Jr",
            "Jude Bellin-gol", "Mo Ensalada", "Lamine Yabien", "Cole Frio",
            "Virgil El Muro", "Martin Odegol", "Antoine Gringo", "Bukayo Sacachispas"
        }
        for nombre_equipo, info in DATOS_LALIGA.items():
            jugadores_equipo = []
            for j_data in info["jugadores"]:
                id_counter += 1
                pnombre, papellido, pos, ovr, rasgo, edad = j_data
                
                # Intentar convertir ovr a entero en caso de que accidentalmente venga como string
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
            nombre="LaLiga EA Sports Parodia",
            tipo="laliga",
            equipos=equipos_list,
            num_jornadas=max(2, 2 * (len(equipos_list) - 1))  # v3.7.0: ida y vuelta (12 → 22)
        )
        
    except Exception as error_global:
        logging.error(f"Error critico en get_liga() de laliga.py: {error_global}. Activando resiliencia.")
        return crear_liga_fallback()
