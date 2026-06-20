# -*- coding: utf-8 -*-
"""
Tests del fix "Valor $0": asignar_valores_iniciales + coherencia de ofertas.
Ejecutar:  python tests/test_valor_ofertas.py   (sale 0 si todo pasa)
"""
import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha_football.market import (
    asignar_valores_iniciales,
    calcular_valor,
    crear_oferta_ui,
    crear_oferta_exterior,
)
from alpha_football.plantilla import expandir_liga
from alpha_football.models import Equipo, Liga, Jugador


def _equipo_prueba():
    """Liga pequeña con 4 equipos y 11 jugadores por equipo (sin expandir)."""
    eqs = []
    for i in range(4):
        jugs = []
        for j in range(11):
            jugs.append(Jugador(
                nombre=f"J{i}", apellido=f"A{j}", posicion="MED",
                ataque=70, defensa=70, fisico=70, tecnica=70, mental=70,
                edad=24, id=1000 + i * 100 + j,
            ))
        eqs.append(Equipo(
            nombre=f"Eq{i}", ciudad="C", estrellas=3, estilo_dt="cruyffismo",
            balance=5_000_000, jugadores=jugs,
        ))
    return Liga(nombre="Test", tipo="premier", equipos=eqs, num_jornadas=10)


def test_asignar_valores_iniciales_puebla_todo():
    """Tras asignar_valores_iniciales NINGÚN jugador tiene valor=0 ni potencial=0."""
    liga = _equipo_prueba()
    asignar_valores_iniciales(liga)
    nulos = 0
    for eq in liga.equipos:
        for j in eq.jugadores:
            if getattr(j, "valor", 0) <= 0:
                nulos += 1
            if getattr(j, "potencial", 0) <= 0:
                nulos += 1
    assert nulos == 0, f"quedan {nulos} jugadores con valor=0 o potencial=0 tras asignar_valores_iniciales"


def test_asignar_valores_iniciales_idempotente():
    """Llamarla dos veces seguidas no rompe ni cambia los valores."""
    liga = _equipo_prueba()
    asignar_valores_iniciales(liga)
    snapshot = [(j.id, j.valor, j.potencial) for eq in liga.equipos for j in eq.jugadores]
    asignar_valores_iniciales(liga)
    snapshot2 = [(j.id, j.valor, j.potencial) for eq in liga.equipos for j in eq.jugadores]
    assert snapshot == snapshot2, "asignar_valores_iniciales no es idempotente"


def test_crear_oferta_ui_puebla_valor_y_coherencia():
    """crear_oferta_ui: el monto es coherente con el valor del jugador y su valor queda > 0."""
    # v0.8.x: crear_oferta_ui requiere plantilla > 11 (PLANTILLA_MINIMA). Ponemos 12+
    # jugadores, uno de ellos OVR alto y con valor=0 para verificar que la oferta
    # genera el valor y muestra coherencia entre monto y valor.
    jugadores_mi = []
    for i in range(11):
        jugadores_mi.append(Jugador(
            nombre=f"Relleno{i}", apellido="X", posicion="MED",
            ataque=70, defensa=70, fisico=70, tecnica=70, mental=70,
            edad=24, id=9100 + i,
        ))
    # El crack que queremos que sea ofertado
    jugadores_mi.append(Jugador(
        nombre="Crack", apellido="X", posicion="DEL",
        ataque=92, defensa=70, fisico=85, tecnica=92, mental=85,
        edad=27, id=9001,
    ))
    mi_equipo = Equipo(nombre="Mio", ciudad="C", estrellas=4, estilo_dt="cruyffismo",
                       balance=100_000_000, jugadores=jugadores_mi)
    rival = Equipo(nombre="Rival", ciudad="C", estrellas=4, estilo_dt="anchelottismo",
                   balance=200_000_000, jugadores=[])
    # Forzar el valor a 0 en el crack
    mi_equipo.jugadores[11].valor = 0
    of = crear_oferta_ui(
        mi_equipo, [rival], jornada=2, num_jornadas=10,
        rng=random.Random(7), prob=1.0,
    )
    # prob=1.0 garantiza que SI se genera oferta
    assert of is not None, "crear_oferta_ui no genero oferta con prob=1.0"
    jug = of["jugador"]
    monto = of["monto"]
    assert getattr(jug, "valor", 0) > 0, f"valor del jugador sigue 0: {jug.valor}"
    assert monto > 0, f"monto <= 0: {monto}"
    # El monto debe ser ~valor * 0.95..1.5
    val = jug.valor
    assert val * 0.9 <= monto <= val * 1.6, f"monto {monto} fuera de rango de valor {val}"


def test_crear_oferta_exterior_valor_y_coherencia():
    """crear_oferta_exterior: misma coherencia que crear_oferta_ui para ofertas del exterior."""
    # Mismo requerimiento: plantilla > 11
    jugadores_mi = []
    for i in range(11):
        jugadores_mi.append(Jugador(
            nombre=f"Relleno{i}", apellido="X", posicion="MED",
            ataque=70, defensa=70, fisico=70, tecnica=70, mental=70,
            edad=24, id=9200 + i, promedio_nota=7.0,
        ))
    jugadores_mi.append(Jugador(
        nombre="Crack", apellido="X", posicion="DEL",
        ataque=92, defensa=70, fisico=85, tecnica=92, mental=85,
        edad=27, id=9002, promedio_nota=7.5, goles=5, asistencias=2,
    ))
    mi_equipo = Equipo(nombre="Mio", ciudad="C", estrellas=4, estilo_dt="cruyffismo",
                       balance=100_000_000, jugadores=jugadores_mi)
    # Estado mínimo para pool_internacional
    estado = {"_pool_internacional": [
        (mi_equipo.jugadores[11], mi_equipo, "champions")
    ]}
    mi_equipo.jugadores[11].valor = 0  # forzar 0
    of = crear_oferta_exterior(mi_equipo, estado, rng=random.Random(11), prob=1.0)
    assert of is not None, "crear_oferta_exterior no genero oferta con prob=1.0"
    jug = of["jugador"]
    monto = of["monto"]
    assert getattr(jug, "valor", 0) > 0, f"valor del jugador sigue 0: {jug.valor}"
    assert monto > 0, f"monto <= 0: {monto}"
    # Monto debe ser ~valor * 1.3..2.2
    val = jug.valor
    assert val * 1.2 <= monto <= val * 2.3, f"monto {monto} fuera de rango de valor {val}"


def test_flujo_cargar_liga_premier():
    """Flujo end-to-end: cargar Premier League, expandir plantilla, asignar valores."""
    from alpha_football.data.premier import get_liga
    liga = get_liga()
    expandir_liga(liga, 20)
    asignar_valores_iniciales(liga)
    min_valor = min(j.valor for eq in liga.equipos for j in eq.jugadores)
    assert min_valor > 0, f"min valor en Premier tras asignar: {min_valor}"


if __name__ == "__main__":
    fns = [
        test_asignar_valores_iniciales_puebla_todo,
        test_asignar_valores_iniciales_idempotente,
        test_crear_oferta_ui_puebla_valor_y_coherencia,
        test_crear_oferta_exterior_valor_y_coherencia,
        test_flujo_cargar_liga_premier,
    ]
    for fn in fns:
        fn()
        print(f"  OK  {fn.__name__}")
    print(f"\n{len(fns)} tests de valor/ofertas PASARON.")
