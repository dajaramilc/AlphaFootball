# -*- coding: utf-8 -*-
"""
Alpha Football v2.3.8 — RETIROS Y REGENS.

Al cerrar la temporada, los jugadores de 35 años o más pueden retirarse (se sortea;
la probabilidad sube con la edad y baja si hicieron una gran temporada). Cada retirado
deja su lugar a un REGEN: un juvenil de 16-18 años con su misma nacionalidad, posición y
potencial máximo, y un nombre genérico de su país. El regen ocupa el MISMO índice en la
plantilla, así la alineación guardada del usuario sigue siendo válida.
"""
from __future__ import annotations

import logging
import random
from typing import Any, Optional

logger = logging.getLogger(__name__)

from alpha_football.paises import PAISES as _PAISES   # noqa: E402
PAIS_POR_LIGA = {p['liga_id']: p['nombre'] for p in _PAISES}   # v3.7.0: 8 países

# Probabilidad de retiro por edad (ya cumplida al cerrar la temporada).
PROB_RETIRO = {35: 0.35, 36: 0.50, 37: 0.65, 38: 0.80, 39: 0.90}
PROB_RETIRO_40_MAS = 0.97
NOTA_SIGUE_JUGANDO = 7.3   # con una gran temporada la probabilidad se reduce a la mitad

# Nombres genéricos por país (no parodias).
NOMBRES_POR_PAIS = {
    'Colombia': (
        ["Juan", "Andrés", "Carlos", "Santiago", "Sebastián", "Camilo", "Felipe", "Jhon", "Luis", "Daniel",
         "Kevin", "Brayan", "Juan David", "Jhonatan", "Mateo", "Samuel", "Cristian", "Óscar", "Duván", "Yeison"],
        ["Rodríguez", "Gómez", "Martínez", "Hernández", "López", "García", "Moreno", "Mosquera", "Ramírez",
         "Valencia", "Palacios", "Castaño", "Rentería", "Cuesta", "Arboleda", "Quiñones", "Murillo", "Zapata",
         "Ospina", "Cardona", "Restrepo", "Giraldo", "Bedoya", "Cuadrado"]),
    'Brasil': (
        ["João", "Pedro", "Lucas", "Gabriel", "Matheus", "Rafael", "Gustavo", "Felipe", "Vinícius", "Thiago",
         "Bruno", "Caio", "Rodrigo", "Diego", "Igor", "Luan", "Wesley", "Kaique", "Davi", "Everton"],
        ["Silva", "Santos", "Oliveira", "Souza", "Lima", "Pereira", "Costa", "Ferreira", "Almeida", "Carvalho",
         "Ribeiro", "Gomes", "Martins", "Rocha", "Barbosa", "Araújo", "Nascimento", "Moura", "Cardoso",
         "Teixeira", "Correia", "Dias"]),
    'Argentina': (
        ["Juan", "Matías", "Lautaro", "Nicolás", "Facundo", "Santiago", "Tomás", "Agustín", "Franco", "Gonzalo",
         "Ezequiel", "Julián", "Thiago", "Valentín", "Leandro", "Maximiliano", "Joaquín", "Bruno", "Lucas", "Enzo"],
        ["González", "Fernández", "Rodríguez", "López", "Martínez", "Pérez", "Gómez", "Díaz", "Romero", "Sosa",
         "Álvarez", "Benítez", "Acosta", "Medina", "Herrera", "Suárez", "Aguirre", "Giménez", "Ledesma",
         "Paredes", "Molina", "Correa"]),
    'España': (
        ["Pablo", "Álvaro", "Sergio", "Javier", "Adrián", "Hugo", "Marcos", "Iker", "Unai", "Raúl",
         "Alejandro", "Daniel", "Mario", "Rubén", "Iván", "Aitor", "Jorge", "Manuel", "Gonzalo", "Nacho"],
        ["García", "Fernández", "González", "Rodríguez", "López", "Martínez", "Sánchez", "Pérez", "Gómez",
         "Martín", "Jiménez", "Ruiz", "Hernández", "Díaz", "Moreno", "Muñoz", "Álvarez", "Romero", "Navarro",
         "Torres", "Domínguez", "Vázquez"]),
    'Inglaterra': (
        ["Jack", "Harry", "Oliver", "George", "James", "Charlie", "Thomas", "Jacob", "Alfie", "Oscar",
         "William", "Joshua", "Ethan", "Callum", "Mason", "Lewis", "Ryan", "Connor", "Jordan", "Tyler"],
        ["Smith", "Jones", "Taylor", "Brown", "Williams", "Wilson", "Johnson", "Davies", "Robinson", "Wright",
         "Thompson", "Evans", "Walker", "White", "Roberts", "Green", "Hall", "Wood", "Jackson", "Clarke",
         "Harris", "Lewis"]),
}

# Reparto de atributos por posición (desvío respecto de la media); se ajusta a la media exacta.
_PERFIL = {
    'POR': (-45, 15, 5, -5, 10),
    'DEF': (-20, 15, 10, -5, 5),
    'MED': (0, -5, 0, 10, 5),
    'DEL': (15, -25, 5, 10, 0),
}
_ATRIBUTOS = ("ataque", "defensa", "fisico", "tecnica", "mental")


def prob_retiro(edad: int, promedio_nota: float = 0.0) -> float:
    """Probabilidad de retirarse al cerrar la temporada (0 antes de los 35)."""
    edad = int(edad or 0)
    if edad < 35:
        return 0.0
    prob = PROB_RETIRO.get(edad, PROB_RETIRO_40_MAS)
    if float(promedio_nota or 0) >= NOTA_SIGUE_JUGANDO:
        prob *= 0.5
    return prob


def asignar_nacionalidades(estado: dict) -> None:
    """Completa la nacionalidad que falte con el país de la liga donde juega el jugador."""
    from alpha_football.mercado_ia import ligas_de_la_partida
    for liga, tipo, _div in ligas_de_la_partida(estado):
        pais = PAIS_POR_LIGA.get(tipo, '')
        for eq in liga.equipos:
            for j in eq.jugadores:
                if not getattr(j, 'nacionalidad', ''):
                    j.nacionalidad = pais


def _atributos_para(posicion: str, ovr: int, rng: random.Random) -> list[int]:
    """5 atributos cuya media entera es exactamente `ovr`, con el perfil de la posición."""
    perfil = _PERFIL.get(posicion, _PERFIL['MED'])
    attrs = [max(10, min(99, ovr + d + rng.randint(-2, 2))) for d in perfil]
    objetivo = ovr * 5
    for _ in range(200):
        dif = objetivo - sum(attrs)
        if dif == 0:
            break
        paso = 1 if dif > 0 else -1
        i = rng.randrange(5)
        if 10 <= attrs[i] + paso <= 99:
            attrs[i] += paso
    return attrs


def generar_regen(retirado: Any, rng: random.Random, id_nuevo: int, nombres_usados: set) -> Any:
    """Juvenil que reemplaza a `retirado`: misma nacionalidad, posición y potencial máximo."""
    from alpha_football.models import Jugador
    pais = getattr(retirado, 'nacionalidad', '') or 'España'
    nombres, apellidos = NOMBRES_POR_PAIS.get(pais, NOMBRES_POR_PAIS['España'])
    from alpha_football.nombres import en_uso, nombre_unico, reservar
    for _ in range(20):
        nombre, apellido = rng.choice(nombres), rng.choice(apellidos)
        if f"{nombre} {apellido}" not in nombres_usados and not en_uso(nombre, apellido):
            break
    else:   # v4.4.0: único en toda la carrera, no solo en el club
        nombre, apellido = nombre_unico(pais, rng)
    nombres_usados.add(f"{nombre} {apellido}")
    reservar(nombre, apellido)
    potencial = max(int(getattr(retirado, 'potencial', 0) or 0), int(retirado.overall))
    ovr = max(45, potencial - rng.randint(14, 20))
    ataque, defensa, fisico, tecnica, mental = _atributos_para(retirado.posicion, ovr, rng)
    return Jugador(nombre=nombre, apellido=apellido, posicion=retirado.posicion,
                   ataque=ataque, defensa=defensa, fisico=fisico, tecnica=tecnica, mental=mental,
                   id=id_nuevo, edad=rng.randint(16, 18), potencial=min(99, potencial), nacionalidad=pais)


def _reacomodar_once_usuario(equipo: Any, indices_retirados: list) -> None:
    """Si se retiró un titular del user, entra el mejor disponible de su posición (no el regen)."""
    alin = getattr(equipo, 'alineacion_activa', None)
    if alin is None or not getattr(alin, 'titulares', None):
        return
    js = equipo.jugadores
    for k, idx in enumerate(list(alin.titulares)):
        if idx not in indices_retirados:
            continue
        candidatos = [i for i, j in enumerate(js)
                      if i not in alin.titulares and i not in indices_retirados
                      and j.posicion == js[idx].posicion and getattr(j, 'lesion_partidos', 0) == 0]
        if candidatos:
            alin.titulares[k] = max(candidatos, key=lambda i: js[i].overall)
    try:
        from alpha_football.formaciones import normalizar_convocados
        normalizar_convocados(alin, js)
    except Exception as e_conv:
        logger.error(f"No se pudo normalizar el banco tras los retiros: {e_conv}")


def procesar_retiros(estado: dict, rng: Optional[random.Random] = None) -> list[dict]:
    """
    Sortea los retiros de las 10 ligas y pone un regen en el lugar de cada retirado.
    Retorna (y guarda en estado['retiros_ultimos']) la lista de retiros.
    """
    from alpha_football.mercado_ia import ligas_de_la_partida
    from alpha_football.market import calcular_valor, registrar_region_jugador
    azar = rng or random.Random()
    asignar_nacionalidades(estado)
    datos = estado.setdefault('datos_carrera', {})
    siguiente_id = int(datos.get('regen_id', 700000) or 700000)
    mi_equipo = estado.get('mi_equipo')
    retiros = []
    for liga, tipo, _div in ligas_de_la_partida(estado):
        for eq in liga.equipos:
            usados = {f"{j.nombre} {j.apellido}" for j in eq.jugadores}
            reemplazados = []
            for idx, j in enumerate(list(eq.jugadores)):
                try:
                    if azar.random() >= prob_retiro(getattr(j, 'edad', 25), getattr(j, 'promedio_nota', 0)):
                        continue
                    regen = generar_regen(j, azar, siguiente_id, usados)
                    siguiente_id += 1
                    eq.jugadores[idx] = regen
                    registrar_region_jugador(regen, tipo)
                    regen.valor = calcular_valor(regen)
                    reemplazados.append(idx)
                    retiros.append({
                        'nombre': j.nombre_completo, 'edad': j.edad, 'ovr': j.overall, 'equipo': eq.nombre,
                        'regen': regen.nombre_completo, 'regen_edad': regen.edad, 'regen_pot': regen.potencial,
                        'posicion': j.posicion, 'es_user': eq is mi_equipo,
                    })
                except Exception as e_ret:
                    logger.error(f"Error procesando el retiro de {getattr(j, 'nombre', '?')}: {e_ret}")
            if reemplazados and eq is mi_equipo:
                _reacomodar_once_usuario(eq, reemplazados)
    datos['regen_id'] = siguiente_id
    estado['retiros_ultimos'] = retiros
    if retiros:
        logger.info(f"Retiros de fin de temporada: {len(retiros)} (regens creados).")
    return retiros
