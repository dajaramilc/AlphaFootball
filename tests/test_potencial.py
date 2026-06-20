# -*- coding: utf-8 -*-
"""
Tests del sistema de Potencial Final.
Ejecutar:  python tests/test_potencial.py   (sale 0 si todo pasa)
"""
import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha_football.models import Jugador, Equipo
from alpha_football.desarrollo import (
    calcular_potencial,
    progresar_pasivo,
    _potencial_perezoso,
    desarrollar_plantilla_post_partido,
)


def _jug(ovr, edad, pos="MED", promedio_nota=0.0):
    return Jugador(
        nombre="N", apellido="A", posicion=pos,
        ataque=ovr, defensa=ovr, fisico=ovr, tecnica=ovr, mental=ovr,
        edad=edad, promedio_nota=promedio_nota
    )


def _equipo(jugadores):
    return Equipo(nombre="Test", ciudad="C", estrellas=3.0,
                  estilo_dt="cruyffismo", balance=1_000_000, jugadores=jugadores)


def test_calcular_potencial_ejemplos_plan():
    """Los 3 ejemplos del plan (20/80, 24/85, 27/80) caen en los rangos prometi­dos."""
    rng = random.Random(0)
    # Recorremos muchos seeds para confirmar que el rango cubre lo prometido
    for seed in range(50):
        rng = random.Random(seed)
        p_20_80 = calcular_potencial(80, 20, rng)
        assert 90 <= p_20_80 <= 92, f"20/80 con seed {seed} -> {p_20_80} (esperado 90-92)"
        p_24_85 = calcular_potencial(85, 24, rng)
        assert 89 <= p_24_85 <= 91, f"24/85 con seed {seed} -> {p_24_85} (esperado 89-91)"
        p_27_80 = calcular_potencial(80, 27, rng)
        assert 83 <= p_27_80 <= 85, f"27/80 con seed {seed} -> {p_27_80} (esperado 83-85)"


def test_calcular_potencial_acotado():
    """calcular_potencial devuelve [overall+1, 99] en todos los casos."""
    for ovr in (50, 60, 70, 80, 90, 95):
        for edad in (16, 18, 20, 22, 25, 28, 32, 35, 40):
            p = calcular_potencial(ovr, edad, random.Random(7))
            assert p >= ovr + 1, f"OVR={ovr} edad={edad} -> pot={p} < ovr+1"
            assert p <= 99, f"OVR={ovr} edad={edad} -> pot={p} > 99"


def test_desarrollo_no_supera_potencial():
    """desarrollar_plantilla_post_partido nunca deja OVR > potencial."""
    j = _jug(85, 24)
    # Sembrar potencial conocido
    j.potencial = 90
    j.progreso_desarrollo = 5.0  # daría 5 subidas si no hubiera techo
    # Notas perfectas + muchos goles para forzar subidas
    for _ in range(10):
        # bump atributos para que progreso se acumule rápido
        j.progreso_desarrollo = 5.0
        desarrollar_plantilla_post_partido(
            _equipo([j]),
            goles_favor=10, goles_contra=0,
            indices_jugaron=[0],
            rng=random.Random(0),
        )
    # El OVR final nunca debe superar el potencial
    assert j.overall <= j.potencial, f"OVR {j.overall} > potencial {j.potencial}"


def test_progresar_pasivo_no_supera_potencial():
    """progresar_pasivo nunca deja OVR > potencial aunque el delta sea positivo."""
    j = _jug(90, 22)  # joven, +8 -> potencial ~98-100
    j.potencial = 95  # techo explícito
    j.promedio_nota = 0  # sin regla destacada, curva por edad normal
    ovr0 = j.overall
    eq = _equipo([j])
    progresar_pasivo(eq, 5, random.Random(0))
    assert j.overall <= j.potencial, f"OVR {j.overall} > potencial {j.potencial}"
    assert j.edad == 27, f"edad esperada 27, fue {j.edad}"


def test_potencial_perezoso_calcula_y_almacena():
    """_potencial_perezoso calcula y guarda el potencial si estaba en 0."""
    j = _jug(80, 20, pos="DEL", promedio_nota=0)
    assert j.potencial == 0
    pot = _potencial_perezoso(j, random.Random(0))
    assert pot > 0, f"potencial perezoso no se calculo: {pot}"
    assert j.potencial == pot, "no se guardo en el jugador"
    # Idempotente: segunda llamada devuelve el mismo valor
    pot2 = _potencial_perezoso(j, random.Random(99))
    assert pot2 == pot, f"perezoso no es estable: {pot2} != {pot}"


def test_to_dict_from_dict_conserva_potencial():
    """Flujo del editor: to_dict incluye potencial y from_dict lo reconstruye."""
    j = _jug(85, 24, pos="MED")
    j.potencial = 91
    d = j.to_dict()
    assert "potencial" in d, "to_dict no incluye potencial"
    assert d["potencial"] == 91, f"to_dict guardo {d['potencial']}, esperado 91"
    # Reconstruir
    j2 = Jugador.from_dict(d)
    assert j2.potencial == 91, f"from_dict reconstruyo {j2.potencial}, esperado 91"
    # Save viejo sin la clave
    d_viejo = {k: v for k, v in d.items() if k != "potencial"}
    j3 = Jugador.from_dict(d_viejo)
    assert j3.potencial == 0, f"save viejo: potencial deberia ser 0, fue {j3.potencial}"


if __name__ == "__main__":
    fns = [
        test_calcular_potencial_ejemplos_plan,
        test_calcular_potencial_acotado,
        test_desarrollo_no_supera_potencial,
        test_progresar_pasivo_no_supera_potencial,
        test_potencial_perezoso_calcula_y_almacena,
        test_to_dict_from_dict_conserva_potencial,
    ]
    for fn in fns:
        fn()
        print(f"  OK  {fn.__name__}")
    print(f"\n{len(fns)} tests de potencial PASARON.")
