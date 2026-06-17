# -*- coding: utf-8 -*-
"""
Alpha Football v0.4 — AGENTES LIBRES.

Este módulo expone una función para obtener jugadores libres (agentes libres)
que se inyectan en el mercado cada 2 jornadas.
"""

from __future__ import annotations

import random
import logging
from alpha_football.models import Jugador

logger = logging.getLogger(__name__)

# Pool de nombres de parodia de jugadores conocidos o graciosos que están libres
NOMBRES_LIBRES = [
    ("Mario", "Balotellin"),
    ("Eden", "Hazarrica"),
    ("Zlatan", "Ibrahimo-viejito"),
    ("Paul", "Pogbanned"),
    ("Dele", "Alli-triste"),
    ("David", "De Gea-silla"),
    ("James", "Rodriguez-vidrio"),
    ("Neymar", "Duro-en-fiesta"),
    ("Keylor", "Navas-banca"),
    ("Marcelo", "Gordito"),
    ("Arturo", "Vidal-copas"),
]

POSICIONES = ["POR", "DEF", "MED", "DEL"]
RASGOS = ["regateador", "lider", "rustico", "pulmon_de_hierro"]

def get_free_agents(jornada: int) -> list[Jugador]:
    """
    Retorna una lista de 3 a 5 jugadores libres que aparecen cada 2 jornadas.
    En jornadas impares o si no corresponde, retorna una lista vacía.
    """
    try:
        # Solo aparecen en jornadas pares
        if jornada % 2 != 0:
            return []
            
        num_jugadores = random.randint(3, 5)
        seleccionados = random.sample(NOMBRES_LIBRES, min(num_jugadores, len(NOMBRES_LIBRES)))
        
        resultado = []
        id_base = 5000 + (jornada * 10)
        
        for idx, (nombre, apellido) in enumerate(seleccionados):
            pos = random.choice(POSICIONES)
            # overall sugerido entre 65 y 78 (agentes libres decentes)
            ovr = random.randint(65, 78)
            
            # Generación de atributos individuales
            if pos == "POR":
                atk, dfs, fis, tec, men = 15, ovr + 5, ovr, ovr - 10, ovr + 5
            elif pos == "DEF":
                atk, dfs, fis, tec, men = ovr - 20, ovr + 10, ovr + 5, ovr - 10, ovr + 5
            elif pos == "MED":
                atk, dfs, fis, tec, men = ovr - 5, ovr - 5, ovr, ovr + 5, ovr
            else: # DEL
                atk, dfs, fis, tec, men = ovr + 10, ovr - 20, ovr, ovr + 5, ovr
                
            rasgo = random.choice(RASGOS) if random.random() < 0.3 else None
            
            j = Jugador(
                nombre=nombre,
                apellido=apellido,
                posicion=pos,
                ataque=max(10, min(99, atk)),
                defensa=max(10, min(99, dfs)),
                fisico=max(10, min(99, fis)),
                tecnica=max(10, min(99, tec)),
                mental=max(10, min(99, men)),
                moral=70,
                rasgo=rasgo,
                id=id_base + idx
            )
            resultado.append(j)
            
        logger.info(f"Se han generado {len(resultado)} agentes libres para la jornada {jornada}.")
        return resultado
        
    except Exception as e:
        logger.error(f"Error al generar agentes libres: {e}. Retornando lista vacía.")
        return []
