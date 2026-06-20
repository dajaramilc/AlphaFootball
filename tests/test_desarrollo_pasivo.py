# -*- coding: utf-8 -*-
"""
Tests del desarrollo PASIVO por temporada (envejecimiento + drift de OVR por edad).
Ejecutar:  python tests/test_desarrollo_pasivo.py   (sale 0 si todo pasa)
"""
import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha_football.models import Jugador, Equipo
from alpha_football.desarrollo import progresar_pasivo, progresar_liga_pasivo


def _jug(ovr, edad, pos="MED"):
    return Jugador(nombre="N", apellido="Apellido", posicion=pos,
                   ataque=ovr, defensa=ovr, fisico=ovr, tecnica=ovr, mental=ovr, edad=edad)


def _equipo(jugadores):
    return Equipo(nombre="Test FC", ciudad="C", estrellas=3.0, estilo_dt="cruyffismo",
                  balance=1_000_000, jugadores=jugadores)


def test_joven_sube():
    j = _jug(70, 18)
    ovr0 = j.overall
    progresar_pasivo(_equipo([j]), 3, random.Random(1))
    assert j.edad == 21, f"edad esperada 21, fue {j.edad}"
    assert j.overall >= ovr0, f"joven deberia subir/mantener: {ovr0} -> {j.overall}"


def test_veterano_baja():
    j = _jug(82, 35)
    ovr0 = j.overall
    progresar_pasivo(_equipo([j]), 3, random.Random(1))
    assert j.edad == 38, f"edad esperada 38, fue {j.edad}"
    assert j.overall < ovr0, f"veterano deberia bajar: {ovr0} -> {j.overall}"


def test_determinismo():
    a, b = _jug(75, 25), _jug(75, 25)
    progresar_pasivo(_equipo([a]), 5, random.Random(42))
    progresar_pasivo(_equipo([b]), 5, random.Random(42))
    assert a.overall == b.overall and a.edad == b.edad, "mismo seed debe dar mismo resultado"


def test_liga_completa_y_valor():
    from alpha_football.models import Liga
    j = _jug(78, 24, "DEL")
    liga = Liga(nombre="L", tipo="premier", equipos=[_equipo([j])], num_jornadas=10)
    progresar_liga_pasivo(liga, 1, random.Random(3))
    assert j.edad == 25, f"la liga debe envejecer +1: {j.edad}"
    assert j.valor > 0, "el valor de mercado debe recalcularse"
    assert 10 <= min(j.ataque, j.defensa, j.fisico, j.tecnica, j.mental), "atributos acotados >= 10"
    assert max(j.ataque, j.defensa, j.fisico, j.tecnica, j.mental) <= 99, "atributos acotados <= 99"


if __name__ == "__main__":
    fns = [test_joven_sube, test_veterano_baja, test_determinismo, test_liga_completa_y_valor]
    for fn in fns:
        fn()
        print(f"  OK  {fn.__name__}")
    print(f"\n{len(fns)} tests de desarrollo pasivo PASARON.")
