# -*- coding: utf-8 -*-
"""
Alpha Football v0.8.x — AGENTES LIBRES.

Este módulo expone una función para obtener jugadores libres (agentes libres)
que se inyectan en el mercado.

v0.8.x: antes solo aparecían en jornadas pares, de un pool de 11 nombres, en lotes
de 3–5. Diego pidió que aparezcan CASI SIEMPRE (cada jornada), en lotes más grandes
(6–9) y con un pool más rico (~22 nombres) para que la pestaña "Libres" del mercado
nunca se sienta vacía. Adicionalmente se poplan `valor` y `potencial` desde el
momento de creación para que ninguno salga con "Valor $0".
"""
from __future__ import annotations

import random
import logging
from alpha_football.models import Jugador
from alpha_football.market import calcular_valor
from alpha_football.desarrollo import calcular_potencial

logger = logging.getLogger(__name__)

# Pool de parodias de jugadores reconocibles. v0.8.x: ampliado de 11 a 22 nombres
# para que dos jornadas seguidas no repitan el mismo lote.
NOMBRES_LIBRES = [
    # (los 11 originales)
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
    # (los +11 nuevos de v0.8.x)
    ("Sergio", "Ramos-pega"),
    ("Mauro", "Icardi-flojo"),
    ("Pierre-Emerick", "Auba-viejo"),
    ("Karim", "Benzemóvil"),
    ("Carlos", "Tequila-Vela"),
    ("Mesut", "Ozil-retirado"),
    ("Gareth", "Bale-pensionado"),
    ("Antoine", "Griezman-mediocre"),
    ("Luis", "Suarez-muerde-menos"),
    ("Alexis", "Sanchez-quebrado"),
    ("Alex", "Sandropastoso"),
]

POSICIONES = ["POR", "DEF", "MED", "DEL"]
RASGOS = ["regateador", "lider", "rustico", "pulmon_de_hierro"]


def get_free_agents(jornada: int) -> list[Jugador]:
    """
    Retorna una lista de 6 a 9 agentes libres cada jornada (antes solo en pares).
    Los jugadores se generan con datos coherentes:
      - edad 28–35 (los agentes libres suelen ser veteranos)
      - atributos repartidos por posición
      - `valor` y `potencial` poblados desde el inicio (cero "Valor $0")
    """
    try:
        # v0.8.x: eliminamos el gate `if jornada % 2 != 0: return []` — ahora
        # SIEMPRE hay agentes libres. Esto resuelve el bug de que la pestaña
        # "Libres" se cacheaba vacía en jornadas impares (market_screen.py:384).
        num_jugadores = random.randint(6, 9)
        seleccionados = random.sample(NOMBRES_LIBRES, min(num_jugadores, len(NOMBRES_LIBRES)))

        resultado = []
        id_base = 5000 + (max(1, int(jornada)) * 10)

        for idx, (nombre, apellido) in enumerate(seleccionados):
            pos = random.choice(POSICIONES)
            # v0.8.x: los agentes libres suelen ser veteranos → OVR un poco más bajo
            # pero el rango refleja "free agents decentes", no estrellas.
            ovr = random.randint(64, 76)

            # Generación de atributos individuales por posición
            if pos == "POR":
                atk, dfs, fis, tec, men = 15, ovr + 5, ovr, ovr - 10, ovr + 5
            elif pos == "DEF":
                atk, dfs, fis, tec, men = ovr - 20, ovr + 10, ovr + 5, ovr - 10, ovr + 5
            elif pos == "MED":
                atk, dfs, fis, tec, men = ovr - 5, ovr - 5, ovr, ovr + 5, ovr
            else:  # DEL
                atk, dfs, fis, tec, men = ovr + 10, ovr - 20, ovr, ovr + 5, ovr

            rasgo = random.choice(RASGOS) if random.random() < 0.3 else None
            # v0.8.x: edad entre 28 y 35 (veterano, perfil de agente libre)
            edad = random.randint(28, 35)

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
                id=id_base + idx,
                edad=edad,
            )
            # v0.8.x: poblar valor y potencial al construir para que NUNCA salga
            # con "Valor $0" en la UI del mercado ni en la sección de ofertas.
            try:
                j.valor = calcular_valor(j)
            except Exception as e_v:
                logger.debug(f"No se pudo calcular valor de {nombre} {apellido}: {e_v}")
            try:
                # RNG sembrado con id para que el potencial sea estable
                rng_id = random.Random(int(getattr(j, "id", 0)) or 0)
                j.potencial = calcular_potencial(j.overall, edad, rng_id)
            except Exception as e_pot:
                logger.debug(f"No se pudo calcular potencial de {nombre} {apellido}: {e_pot}")

            resultado.append(j)

        logger.info(f"Se han generado {len(resultado)} agentes libres para la jornada {jornada}.")
        return resultado

    except Exception as e:
        logger.error(f"Error al generar agentes libres: {e}. Retornando lista vacía.")
        return []
