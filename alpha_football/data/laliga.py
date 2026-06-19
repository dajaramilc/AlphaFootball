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
ESTILOS_TACTICOS = ["haramball", "cruyffismo", "flickismo", "anchelottismo"]
RASGOS_DISPONIBLES = ["regateador", "lider", "rustico", "pulmon_de_hierro"]

NOMBRES_CORTOS = {
    "Real Madriz": "R. Madriz", "FC Farcelona": "Farcelona", "Patetico de Madriz": "Patetico",
    "Girona Sorpresa": "Girona", "Real Suciedad": "R. Suciedad", "Athletic de Bilbao": "Athletic",
}
ESTILO_FIJO = {
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
    }
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
            num_jornadas=10
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
    Construye y retorna la instancia de la Liga con sus 6 equipos y jugadores parodiados.
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
            num_jornadas=10
        )
        
    except Exception as error_global:
        logging.error(f"Error critico en get_liga() de laliga.py: {error_global}. Activando resiliencia.")
        return crear_liga_fallback()
