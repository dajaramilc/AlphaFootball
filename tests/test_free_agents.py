# -*- coding: utf-8 -*-
"""
Tests de agentes libres (v0.8.x: aparecen en TODAS las jornadas, pool amplio,
lote grande, valor+potencial poblados).
Ejecutar:  python tests/test_free_agents.py   (sale 0 si todo pasa)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha_football.data.free_agents import get_free_agents, NOMBRES_LIBRES


def test_aparecen_en_jornada_impar():
    """v0.8.x: ya NO hay gate `jornada % 2 != 0` — impares también devuelven lote."""
    libres = get_free_agents(1)
    assert len(libres) > 0, f"jornada 1 (impar) devolvio lista vacia"


def test_aparecen_en_jornada_par():
    libres = get_free_agents(2)
    assert len(libres) > 0, "jornada 2 (par) devolvio lista vacia"


def test_lote_entre_6_y_9():
    """v0.8.x: lote más grande (6-9 jugadores, antes 3-5)."""
    for jor in range(1, 21):
        libres = get_free_agents(jor)
        assert 6 <= len(libres) <= 9, f"jor {jor}: lote {len(libres)} fuera de [6,9]"


def test_todos_con_valor_y_potencial():
    """Todos los agentes libres deben traer valor y potencial > 0 (no "Valor $0")."""
    libres = get_free_agents(5)
    for j in libres:
        assert j.valor > 0, f"{j.nombre_completo} valor=0"
        assert j.potencial > 0, f"{j.nombre_completo} potencial=0"


def test_edad_veterano():
    """v0.8.x: agentes libres son veteranos (28-35)."""
    for jor in (1, 3, 5, 7):
        libres = get_free_agents(jor)
        for j in libres:
            assert 28 <= j.edad <= 35, f"{j.nombre_completo} edad {j.edad} fuera de [28,35]"


def test_pool_ampliado():
    """v0.8.x: el pool de nombres debe ser >= 20 (antes 11)."""
    assert len(NOMBRES_LIBRES) >= 20, f"pool {len(NOMBRES_LIBRES)} < 20"


if __name__ == "__main__":
    fns = [
        test_aparecen_en_jornada_impar,
        test_aparecen_en_jornada_par,
        test_lote_entre_6_y_9,
        test_todos_con_valor_y_potencial,
        test_edad_veterano,
        test_pool_ampliado,
    ]
    for fn in fns:
        fn()
        print(f"  OK  {fn.__name__}")
    print(f"\n{len(fns)} tests de agentes libres PASARON.")
