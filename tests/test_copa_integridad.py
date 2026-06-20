# -*- coding: utf-8 -*-
"""
Tests de integridad de la copa internacional (copa_screen).
Verifica el gating secuencial de fases y que el bracket nunca queda con equipos
vacios/'?'/duplicados, incluido el modo espectador (usuario no clasificado).

Ejecutar:  python tests/test_copa_integridad.py   (sale 0 si todo pasa)
"""
import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha_football.data import premier
from alpha_football.plantilla import expandir_liga
from alpha_football.ui import copa_screen as C


def _estado(jornada=10, clasificado=True):
    liga = premier.get_liga()
    expandir_liga(liga, 20)
    liga.jornada_actual = jornada
    mi = liga.equipos[0]
    estado = {
        "liga": liga,
        "mi_equipo": mi,
        "temporada": 1,
        "copa_clasificado": clasificado,
        "copa_user_en_copa": clasificado,
    }
    return estado


def test_no_cuartos_sin_grupos_completos():
    """En J8 (umbral de cuartos superado) NO se debe poder saltar a cuartos sin grupos."""
    random.seed(101)
    estado = _estado(jornada=8)
    C.inicializar_copa_si_falta(estado)
    assert estado["copa_fase_actual"] == "grupos"
    # Forzar el intento de avanzar: con grupos incompletos debe quedarse en 'grupos'.
    C.avanzar_fase_bracket(estado)
    assert estado["copa_fase_actual"] == "grupos", "no debe sembrar cuartos sin grupos completos"
    assert not C._grupos_completos(estado), "los grupos no deberian estar completos aun"


def test_avance_secuencial_valido():
    """Con todos los grupos jugados, cuartos queda bien sembrado (sin '?'/duplicados)."""
    random.seed(202)
    estado = _estado(jornada=10)
    C.inicializar_copa_si_falta(estado)
    rng = random.Random(5)
    for p in estado["copa_grupo_partidos"]:
        p["goles_l"], p["goles_v"], p["jugado"] = rng.randint(0, 4), rng.randint(0, 4), True
    C.recalcular_standings_copa(estado)
    assert C._grupos_completos(estado)
    C.avanzar_fase_bracket(estado)
    assert estado["copa_fase_actual"] in ("cuartos", "eliminado")
    assert C._bracket_fase_valida(estado, "cuartos"), "cuartos mal sembrados (vacio/?/duplicado)"


def test_espectador_simula_copa_completa():
    """Usuario no clasificado: la copa se simula entera y declara un campeon valido."""
    random.seed(303)
    estado = _estado(jornada=10, clasificado=False)
    C.inicializar_copa_si_falta(estado)
    assert estado["copa_user_en_copa"] is False
    C.simular_copa_entera_ia(estado)
    assert estado["copa_fase_actual"] == "campeon", f"fase final inesperada: {estado['copa_fase_actual']}"
    camp = estado.get("copa_campeon")
    assert C._equipo_valido(camp), f"campeon invalido: {camp!r}"
    for fase in ("cuartos", "semis", "final"):
        assert C._bracket_fase_valida(estado, fase), f"bracket invalido en {fase}"
        assert C._fase_completamente_jugada(estado, fase), f"fase no jugada del todo: {fase}"


def test_usuario_eliminado_no_ofrece_fase():
    """Si el usuario cae en grupos, no se le ofrece un partido jugable de cuartos."""
    random.seed(404)
    estado = _estado(jornada=10)
    C.inicializar_copa_si_falta(estado)
    estado["copa_fase_actual"] = "eliminado"
    fase, partido = C.obtener_partido_copa_pendiente(estado)
    assert fase is None and partido is None, "un usuario eliminado no debe tener partido pendiente"


if __name__ == "__main__":
    fns = [
        test_no_cuartos_sin_grupos_completos,
        test_avance_secuencial_valido,
        test_espectador_simula_copa_completa,
        test_usuario_eliminado_no_ofrece_fase,
    ]
    for fn in fns:
        fn()
        print(f"  OK  {fn.__name__}")
    print(f"\n{len(fns)} tests de integridad de copa PASARON.")
