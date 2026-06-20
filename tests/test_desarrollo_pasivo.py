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


def _jug(ovr, edad, pos="MED", promedio_nota=0.0):
    return Jugador(nombre="N", apellido="Apellido", posicion=pos,
                   ataque=ovr, defensa=ovr, fisico=ovr, tecnica=ovr, mental=ovr,
                   edad=edad, promedio_nota=promedio_nota)


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


def test_veterano_33_gran_temporada_no_baja_y_sube_potencial():
    """v0.8.x: veterano 33 con promedio_nota>=7.3 NO debe bajar y su potencial sube."""
    j = _jug(85, 33, pos="DEL", promedio_nota=7.8)
    pot0 = j.potencial  # 0 inicialmente
    ovr0 = j.overall
    progresar_pasivo(_equipo([j]), 1, random.Random(0))
    # La curva base para 33 años es declive (-1, -1, -2). Con la regla destacada
    # debe ganar (delta = max(delta_curva, +1) = +1) y subir el techo.
    assert j.overall >= ovr0, f"OVR 33/gran_temporada deberia subir/mantenerse: {ovr0} -> {j.overall}"
    assert j.potencial > pot0, f"potencial deberia subir: {pot0} -> {j.potencial}"
    assert j.edad == 34, f"edad esperada 34, fue {j.edad}"


def test_veterano_35_gran_temporada_no_baja():
    """v0.8.x: veterano 35 con gran promedio NO debe bajar (no se aplica la subida +1)."""
    j = _jug(82, 35, pos="DEF", promedio_nota=8.0)
    ovr0 = j.overall
    pot0 = j.potencial
    progresar_pasivo(_equipo([j]), 1, random.Random(0))
    # Regla: edad>=34 con nota>=7.3 → delta = max(delta, 0). No baja.
    assert j.overall >= ovr0, f"veterano 35/gran_temporada no deberia bajar: {ovr0} -> {j.overall}"
    # El potencial SÍ sube (la regla destacada lo incrementa, independientemente de la edad)
    assert j.potencial > pot0, f"potencial deberia subir: {pot0} -> {j.potencial}"
    assert j.edad == 36, f"edad esperada 36, fue {j.edad}"


def test_fondo_sin_nota_sigue_curva_edad():
    """Jugador de fondo (promedio_nota=0, sin rendimiento) sigue la curva por edad normal."""
    j = _jug(82, 35, pos="DEF", promedio_nota=0)
    ovr0 = j.overall
    pot0 = j.potencial
    progresar_pasivo(_equipo([j]), 1, random.Random(0))
    # Sin nota no se activa la regla destacada: la curva por edad 35 cae (-1, -1, -2).
    assert j.overall < ovr0, f"fondo 35 sin nota deberia bajar: {ovr0} -> {j.overall}"
    # El potencial del fondo SÍ se calcula perezosamente (>= ovr+1) pero NO se incrementa
    # por la regla destacada.
    assert pot0 == 0 and j.potencial > 0, "el potencial perezoso deberia haberse calculado"


if __name__ == "__main__":
    fns = [
        test_joven_sube,
        test_veterano_baja,
        test_determinismo,
        test_liga_completa_y_valor,
        test_veterano_33_gran_temporada_no_baja_y_sube_potencial,
        test_veterano_35_gran_temporada_no_baja,
        test_fondo_sin_nota_sigue_curva_edad,
    ]
    for fn in fns:
        fn()
        print(f"  OK  {fn.__name__}")
    print(f"\n{len(fns)} tests de desarrollo pasivo PASARON.")
