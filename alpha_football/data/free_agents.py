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
from typing import Optional
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


def get_free_agents(jornada: int, rng: Optional[random.Random] = None,
                    cantidad: Optional[int] = None) -> list[Jugador]:
    """
    Retorna una lista de 6 a 9 agentes libres cada jornada (antes solo en pares).
    Los jugadores se generan con datos coherentes:
      - edad 28–35 (los agentes libres suelen ser veteranos)
      - atributos repartidos por posición
      - `valor` y `potencial` poblados desde el inicio (cero "Valor $0")
    v0.4.21.0: con `rng` (y `cantidad`) el lote sale de esa semilla y conserva los nombres de parodia
    (relleno_libres descarta después los que ya están en uso).
    """
    try:
        azar = rng or random
        # v0.8.x: eliminamos el gate `if jornada % 2 != 0: return []` — ahora
        # SIEMPRE hay agentes libres. Esto resuelve el bug de que la pestaña
        # "Libres" se cacheaba vacía en jornadas impares (en la vieja pantalla del mercado).
        num_jugadores = cantidad or azar.randint(6, 9)
        seleccionados = azar.sample(NOMBRES_LIBRES, min(num_jugadores, len(NOMBRES_LIBRES)))
        # v4.4.0: si ese nombre ya lo tiene alguien en la carrera (p. ej. uno que fichaste), otro
        from alpha_football.nombres import en_uso, nombre_unico
        if rng is None:
            seleccionados = [nombre_unico(reservar=False) if en_uso(n, a) else (n, a) for n, a in seleccionados]

        resultado = []
        id_base = 5000 + (max(1, int(jornada)) * 10)

        for idx, (nombre, apellido) in enumerate(seleccionados):
            pos = azar.choice(POSICIONES)
            # v0.8.x: los agentes libres suelen ser veteranos → OVR un poco más bajo
            # pero el rango refleja "free agents decentes", no estrellas.
            ovr = azar.randint(64, 76)

            # Generación de atributos individuales por posición
            if pos == "POR":
                atk, dfs, fis, tec, men = 15, ovr + 5, ovr, ovr - 10, ovr + 5
            elif pos == "DEF":
                atk, dfs, fis, tec, men = ovr - 20, ovr + 10, ovr + 5, ovr - 10, ovr + 5
            elif pos == "MED":
                atk, dfs, fis, tec, men = ovr - 5, ovr - 5, ovr, ovr + 5, ovr
            else:  # DEL
                atk, dfs, fis, tec, men = ovr + 10, ovr - 20, ovr, ovr + 5, ovr

            rasgo = azar.choice(RASGOS) if azar.random() < 0.3 else None
            # v0.8.x: edad entre 28 y 35 (veterano, perfil de agente libre)
            edad = azar.randint(28, 35)

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
            from alpha_football.data.nacionalidades import nacionalidad_real
            j.nacionalidad = nacionalidad_real(f"{nombre} {apellido}")    # v0.4.10.0
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


def relleno_libres(temporada: int, faltan: int, presentes=()) -> list[Jugador]:
    """v0.4.21.0: veteranos de parodia para cuando la bolsa real de agentes libres tiene pocos. Salen de una
    semilla por temporada: son los mismos toda la temporada (ya no cambian de posición ni de media de una
    jornada a otra). Se descartan los que ya juegan en algún club y los que ya están en la lista."""
    if faltan <= 0:
        return []
    from alpha_football.nombres import en_uso
    temporada = max(1, int(temporada or 1))
    lote = get_free_agents(temporada * 3, random.Random(f"libres-{temporada}"), len(NOMBRES_LIBRES))
    return [j for j in lote if not en_uso(j.nombre, j.apellido) and j.nombre_completo not in presentes][:faltan]


# ── v4.6.0: jugadores libres creados en el editor ────────────────────────────
# Están en el mercado desde el inicio de la carrera hasta que alguien los fiche. Se guardan como
# dicts en datos_carrera['libres_editor'] (sobreviven al guardado) y se rearman cada jornada.

def _libres_de_la_base() -> list:
    """Jugadores libres de la base editada (clave '_libres')."""
    try:
        import json
        import os
        from alpha_football.paises import RUTA_DB_EDITADA
        if not os.path.exists(RUTA_DB_EDITADA):
            return []
        with open(RUTA_DB_EDITADA, 'r', encoding='utf-8') as f:
            db = json.load(f)
        return [x for x in (db.get('_libres') or []) if isinstance(x, dict)]
    except Exception as e:
        logger.error(f"No se pudieron leer los libres del editor: {e}")
        return []


def libres_editor(estado: dict) -> list[Jugador]:
    """Los libres del editor que nadie fichó todavía (la primera vez se copian de la base)."""
    dc = estado.setdefault('datos_carrera', {})
    if 'libres_editor' not in dc:
        dc['libres_editor'] = _libres_de_la_base()
    out = []
    for d in dc['libres_editor']:
        try:
            j = Jugador.from_dict(d)
            if not int(getattr(j, 'valor', 0) or 0):
                j.valor = calcular_valor(j)
            if not int(getattr(j, 'potencial', 0) or 0):
                j.potencial = calcular_potencial(j.overall, j.edad, random.Random(int(j.id or 0)))
            out.append(j)
        except Exception as e:
            logger.error(f"Libre del editor inválido {d.get('nombre', '?')}: {e}")
    return out


def quitar_libre_editor(estado: dict, jugador) -> None:
    """Alguien lo fichó: deja de estar en la bolsa de libres del editor."""
    try:
        dc = estado.get('datos_carrera') or {}
        clave = (int(getattr(jugador, 'id', -1) or -1), getattr(jugador, 'nombre', ''), getattr(jugador, 'apellido', ''))
        dc['libres_editor'] = [d for d in dc.get('libres_editor') or []
                               if (int(d.get('id', -2) or -2), d.get('nombre', ''), d.get('apellido', '')) != clave]
    except Exception as e:
        logger.error(f"No se pudo quitar el libre del editor: {e}")
