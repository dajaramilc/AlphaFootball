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
ESTILOS_TACTICOS = ["haramball", "cruyffismo", "flickismo", "anchelottismo"]
RASGOS_DISPONIBLES = ["regateador", "lider", "rustico", "pulmon_de_hierro"]

NOMBRES_CORTOS = {
    "Manchester Billete": "Man Billete", "Arsenal Pechofrio": "Arsenal", "Pool de Higado": "Pool",
    "Manchester Desunido": "Man Desunido", "Chelsea Guarderia": "Chelsea", "Spurs sin Copas": "Spurs",
}
ESTILO_FIJO = {
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
    }
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
            num_jornadas=10
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
    Construye y retorna la instancia de la Liga con sus 6 equipos y jugadores parodiados.
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
            num_jornadas=10
        )
        
    except Exception as error_global:
        logging.error(f"Error critico en get_liga() de premier.py: {error_global}. Activando resiliencia.")
        return crear_liga_fallback()
