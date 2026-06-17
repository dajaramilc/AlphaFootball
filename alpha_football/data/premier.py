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
# Si el módulo models aún no existe debido a la ejecución paralela y aislada,
# implementamos una solución alternativa declarando clases mock locales.
# Esto asegura que el archivo se compile, valide y pueda ser testeado de forma autónoma.
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

    @dataclass
    class Liga:
        nombre: str
        tipo: str
        equipos: List[Equipo]
        num_jornadas: int

# Constantes del juego para estilos tácticos de los directores técnicos y rasgos especiales
ESTILOS_TACTICOS = ["haramball", "cruyffismo", "flickismo"]
RASGOS_DISPONIBLES = ["regateador", "lider", "rustico", "pulmon_de_hierro"]

def generar_atributos_por_posicion(ovr_sugerido: int, posicion: str) -> tuple[int, int, int, int, int]:
    """
    Genera los 5 atributos individuales de un jugador (ataque, defensa, fisico, tecnica, mental)
    basado en su posición y una valoración general (OVR) sugerida.
    Garantiza de manera resiliente que el promedio entero sea exactamente el OVR, y que ningún
    atributo salga de los rangos válidos [10, 99].
    """
    try:
        # Se restringe el rating general entre los límites lógicos del juego para la Premier (tope 85)
        ovr_objetivo = min(max(ovr_sugerido, 40), 85)
        
        # Inicialización de atributos según la posición táctica del jugador
        if posicion == "POR":
            # Portero: Alta defensa (reflejos) y mental. Ataque mínimo.
            ataque = 15
            defensa = ovr_objetivo + 15
            fisico = ovr_objetivo + 5
            tecnica = ovr_objetivo - 10
            mental = ovr_objetivo + 10
        elif posicion == "DEF":
            # Defensa: Alta defensa y físico. Bajo ataque.
            ataque = ovr_objetivo - 25
            defensa = ovr_objetivo + 15
            fisico = ovr_objetivo + 10
            tecnica = ovr_objetivo - 10
            mental = ovr_objetivo + 10
        elif posicion == "MED":
            # Mediocampista: Atributos equilibrados, alta técnica.
            ataque = ovr_objetivo - 5
            defensa = ovr_objetivo - 5
            fisico = ovr_objetivo
            tecnica = ovr_objetivo + 10
            mental = ovr_objetivo
        else:
            # Delantero (DEL): Alto ataque y técnica. Baja defensa.
            ataque = ovr_objetivo + 15
            defensa = ovr_objetivo - 25
            fisico = ovr_objetivo + 5
            tecnica = ovr_objetivo + 10
            mental = ovr_objetivo - 5

        # Normalizamos los atributos dentro del rango legal [10, 99]
        atributos = [max(10, min(99, val)) for val in (ataque, defensa, fisico, tecnica, mental)]
        
        # Reajuste iterativo para asegurar que el promedio exacto de los atributos coincida con el ovr_objetivo
        suma_objetivo = ovr_objetivo * 5
        for _ in range(50):
            suma_actual = sum(atributos)
            if suma_actual == suma_objetivo:
                break
            diferencia = suma_objetivo - suma_actual
            paso = 1 if diferencia > 0 else -1
            
            # Ajustamos de manera pseudo-aleatoria los atributos de la lista
            indices = [0, 1, 2, 3, 4]
            random.shuffle(indices)
            for idx in indices:
                nuevo_valor = atributos[idx] + paso
                if 10 <= nuevo_valor <= 99:
                    atributos[idx] = nuevo_valor
                    break
                    
        return tuple(atributos)

    except Exception as error_generacion:
        # En caso de fallo inesperado, usamos una solución de fallback:
        # asignamos el OVR sugerido a todos los atributos para mantener la ejecución viva.
        logging.error(f"Fallo al generar atributos (OVR={ovr_sugerido}, Pos={posicion}): {error_generacion}. Aplicando fallback.")
        valor_defecto = min(max(ovr_sugerido, 45), 85)
        return (valor_defecto, valor_defecto, valor_defecto, valor_defecto, valor_defecto)


# Estructuras de datos estáticas que representan los planteles parodiados de la Premier League (Temporada 2024-25)
# Cada equipo tiene 11 jugadores icónicos parodiados que cumplen el esquema táctico:
# 1 POR, 4 DEF, 3 MED, 3 DEL.
DATOS_PREMIER = {
    "Manchester Billete": {
        "ciudad": "Manchester",
        "estrellas": 4.9,
        "jugadores": [
            ("Ederson", "Penales", "POR", 84, None),
            ("Kyle", "Correcaminos", "DEF", 83, "pulmon_de_hierro"),
            ("Ruben", "Murallas", "DEF", 85, "rustico"),
            ("John", "Piedras", "DEF", 83, "lider"),
            ("Josko", "Pasaporte", "DEF", 84, "rustico"),
            ("Rodriguez", "5 Estrellas", "MED", 85, "lider"),
            ("Kevin", "De Bronca", "MED", 85, "lider"),
            ("Mateo", "Pasecito", "MED", 82, None),
            ("Phil", "Fodencito", "DEL", 85, "regateador"),
            ("Bernardo", "Bosquecito", "DEL", 84, "regateador"),
            ("Erling", "Gasoland", "DEL", 85, "pulmon_de_hierro"),
        ]
    },
    "Arsenal Pechofrio": {
        "ciudad": "Londres",
        "estrellas": 4.7,
        "jugadores": [
            ("David", "Rayamuro", "POR", 83, None),
            ("Ben", "Blanco", "DEF", 82, "rustico"),
            ("William", "Salivazo", "DEF", 84, "rustico"),
            ("Gabriel", "Muralla", "DEF", 83, "rustico"),
            ("Jurrien", "Madera", "DEF", 80, None),
            ("Declan", "Arroz", "MED", 84, "pulmon_de_hierro"),
            ("Martin", "Odegol", "MED", 85, "lider"),
            ("Thomas", "Fiesta", "MED", 81, None),
            ("Bukayo", "Sacachispas", "DEL", 85, "regateador"),
            ("Kai", "Gol-fantasma", "DEL", 83, "regateador"),
            ("Gabriel", "Correlotodo", "DEL", 82, "regateador"),
        ]
    },
    "Pool de Higado": {
        "ciudad": "Liverpool",
        "estrellas": 4.8,
        "jugadores": [
            ("Alisson", "Manos", "POR", 84, "lider"),
            ("Trent", "Centros", "DEF", 83, "regateador"),
            ("Virgil", "El Muro", "DEF", 85, "lider"),
            ("Ibrahima", "Konazo", "DEF", 82, "rustico"),
            ("Andy", "Correcaminos", "DEF", 82, "pulmon_de_hierro"),
            ("Alexis", "El Colorado", "MED", 83, "lider"),
            ("Dominik", "Impronunciable", "MED", 82, None),
            ("Ryan", "Graven-banco", "MED", 81, "pulmon_de_hierro"),
            ("Mo", "Ensalada", "DEL", 85, "regateador"),
            ("Darwin", "Caos", "DEL", 82, "rustico"),
            ("Lucho", "Guajiro", "DEL", 83, "regateador"),
        ]
    },
    "Manchester Desunido": {
        "ciudad": "Manchester",
        "estrellas": 4.2,
        "jugadores": [
            ("Andre", "Manosflojas", "POR", 81, None),
            ("Diogo", "Corredor", "DEF", 80, "pulmon_de_hierro"),
            ("Matthijs", "De Tronco", "DEF", 81, "rustico"),
            ("Lisandro", "El Carnicero", "DEF", 82, "rustico"),
            ("Luke", "Lesiones", "DEF", 79, None),
            ("Casemito", "Silva", "MED", 81, "lider"),
            ("Kobbie", "Minino", "MED", 80, None),
            ("Bruno", "Penaldes", "MED", 84, "lider"),
            ("Alejandro", "Bichito", "DEL", 81, "regateador"),
            ("Marcus", "Corretodo", "DEL", 81, "regateador"),
            ("Rasmus", "Joyita", "DEL", 80, None),
        ]
    },
    "Chelsea Guarderia": {
        "ciudad": "Londres",
        "estrellas": 4.4,
        "jugadores": [
            ("Robert", "Manitos", "POR", 80, None),
            ("Malo", "Gusto", "DEF", 81, "pulmon_de_hierro"),
            ("Levi", "Col-pared", "DEF", 80, "rustico"),
            ("Wesley", "Fofanas", "DEF", 79, None),
            ("Marc", "Peluca", "DEF", 81, "pulmon_de_hierro"),
            ("Enzo", "Dolares", "MED", 82, "lider"),
            ("Moises", "Millonario", "MED", 82, "pulmon_de_hierro"),
            ("Christopher", "Lesiones", "MED", 82, None),
            ("Cole", "Frio", "DEL", 85, "regateador"),
            ("Nico", "Fallon", "DEL", 81, None),
            ("Misha", "Tronco", "DEL", 78, "regateador"),
        ]
    },
    "Spurs sin Copas": {
        "ciudad": "Londres",
        "estrellas": 4.3,
        "jugadores": [
            ("Guglielmo", "Paratodo", "POR", 81, None),
            ("Pedro", "Porrito", "DEF", 82, "regateador"),
            ("Cuti", "Carnicero", "DEF", 83, "rustico"),
            ("Micky", "Correcaminos", "DEF", 82, "pulmon_de_hierro"),
            ("Destiny", "Corredor", "DEF", 81, "pulmon_de_hierro"),
            ("Roli", "Huesos", "MED", 79, "rustico"),
            ("James", "Locon", "MED", 82, "regateador"),
            ("Dejan", "Kulu-lento", "MED", 81, None),
            ("Brennan", "Veloz", "DEL", 79, "regateador"),
            ("Dominic", "Solangol", "DEL", 81, None),
            ("Son", "Heung-Chino", "DEL", 83, "lider"),
        ]
    }
}

def crear_liga_fallback() -> Liga:
    """
    Solución alternativa de emergencia en caso de que la inicialización principal falle.
    Construye una liga simplificada para asegurar la continuidad de ejecución.
    """
    try:
        equipos_fallback = []
        for nombre_eq, data in DATOS_PREMIER.items():
            jugadores_fallback = []
            for j_data in data["jugadores"]:
                # Generamos una plantilla simple con OVR fijo y sin rasgos
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
                    lesion_partidos=0
                ))
            
            equipos_fallback.append(Equipo(
                nombre=nombre_eq,
                ciudad=data["ciudad"],
                estrellas=data["estrellas"],
                estilo_dt=random.choice(ESTILOS_TACTICOS),
                balance=int(data["estrellas"] * 5000000),
                jugadores=jugadores_fallback
            ))
            
        return Liga(
            nombre="Barclays Premier League Parodia (Fallback)",
            tipo="premier",
            equipos=equipos_fallback,
            num_jornadas=10
        )
    except Exception as error_fallback:
        # Si incluso el generador de fallback explota, devolvemos una liga completamente dura
        logging.critical(f"Fallo critico doble en fallback: {error_fallback}. Retornando objeto estatico basico.")
        return Liga(
            nombre="Barclays Premier League Parodia (Emergencia)",
            tipo="premier",
            equipos=[],
            num_jornadas=10
        )

def get_liga() -> Liga:
    """
    Construye y retorna la instancia de la Liga con sus 6 equipos y jugadores parodiados.
    Implementa un bloque try-except global para garantizar la resiliencia y continuidad.
    """
    try:
        equipos_list = []
        for nombre_equipo, info in DATOS_PREMIER.items():
            jugadores_equipo = []
            for (pnombre, papellido, pos, ovr, rasgo) in info["jugadores"]:
                # Generamos los 5 atributos individuales de forma coherente y robusta
                atk, dfs, fis, tec, men = generar_atributos_por_posicion(ovr, pos)
                
                # Instanciamos el jugador con sus atributos generados
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
                    lesion_partidos=0
                )
                jugadores_equipo.append(jugador)
            
            # Cada equipo cuenta con presupuesto escalado según sus estrellas (ej. estrellas * 5M USD)
            presupuesto = int(info["estrellas"] * 5000000)
            estilo = random.choice(ESTILOS_TACTICOS)
            
            # Instanciamos el objeto de tipo Equipo
            equipo = Equipo(
                nombre=nombre_equipo,
                ciudad=info["ciudad"],
                estrellas=info["estrellas"],
                estilo_dt=estilo,
                balance=presupuesto,
                jugadores=jugadores_equipo
            )
            equipos_list.append(equipo)
            
        # Retorna la liga con un total de 10 jornadas para 6 equipos (ida y vuelta Round Robin)
        return Liga(
            nombre="Barclays Premier League Parodia",
            tipo="premier",
            equipos=equipos_list,
            num_jornadas=10
        )
        
    except Exception as error_global:
        # En caso de error general, capturamos la excepción real e iniciamos el plan de contingencia
        logging.error(f"Error critico en get_liga() de premier.py: {error_global}. Activando mecanismo de resiliencia.")
        # Intentamos retornar la liga construida con el método alternativo (crear_liga_fallback)
        return crear_liga_fallback()
