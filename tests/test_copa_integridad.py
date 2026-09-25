# -*- coding: utf-8 -*-
"""
Tests de integridad de la copa internacional.
v3.8.0: adaptados al motor de competiciones (Champions de 36 / Libertadores de 32). Misma
intención que los de v0.8.8: gating secuencial de fases, llaves nunca con equipos
vacíos/'?'/duplicados, modo espectador (usuario no clasificado) y usuario eliminado sin partido.

Ejecutar:  python tests/test_copa_integridad.py   (sale 0 si todo pasa)
"""
import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha_football import competiciones as CP
from alpha_football.data import premier
from alpha_football.plantilla import expandir_liga
from alpha_football.ui import copa_screen as C


def _estado(jornada=10, clasificado=True):
    liga = premier.get_liga()
    expandir_liga(liga, 20)
    liga.jornada_actual = jornada
    orden = sorted(liga.equipos, key=lambda e: -e.ovr_promedio)
    mi = orden[0] if clasificado else orden[-1]          # v3.8.0: clasifica el top por media
    estado = {"liga": liga, "mi_equipo": mi, "temporada": 1, "datos_carrera": {},
              "primera_division": {"premier": liga}, "segunda_division": {}}
    CP.iniciar_temporada(estado, random.Random(7))
    return estado


def _equipo_valido(nombre) -> bool:
    return isinstance(nombre, str) and nombre.strip() not in ('', '?', '—', '-')


def _llaves_validas(c: dict, fase: str) -> bool:
    """Todas las llaves de `fase` con dos equipos válidos y sin repetir ningún equipo."""
    llaves = [ll for ll in c['llaves'] if ll['fase'] == fase]
    nombres = [n for ll in llaves for n in (ll['a'], ll['b'])]
    return bool(llaves) and all(_equipo_valido(n) for n in nombres) and len(nombres) == len(set(nombres))


def test_no_llaves_sin_fase_de_liga_completa():
    """Aunque la liga vaya muy adelante, sin terminar la fase de liga NO se arman llaves."""
    estado = _estado(jornada=20)
    t = CP.tipo_copa_user(estado)
    assert t == 'champions'
    CP.avanzar(estado, random.Random(1))         # el user no jugó su fecha 1: la copa lo espera
    c = CP.copa(estado, t)
    assert c['llaves'] == [], "no debe sortear el playoff sin la fase de liga completa"
    assert c['fase_actual'] == 'Fase de liga'


def test_avance_secuencial_valido():
    """Con la fase de liga jugada, el playoff queda bien sembrado (sin '?'/duplicados) y las fases siguen en orden."""
    estado = _estado(jornada=22)
    mi = estado['mi_equipo'].nombre
    pend = CP.partido_pendiente_user(estado)
    while pend and pend['fase'] == 'Fase de liga':
        CP.registrar_resultado_user(estado, pend['id'], 2, 1)
        pend = CP.partido_pendiente_user(estado)
    c = CP.copa(estado, 'champions')
    assert all(p['jugado'] for p in c['partidos'] if p['fase'] == 'Fase de liga')
    assert _llaves_validas(c, 'Playoff'), "playoff mal sembrado (vacío/?/duplicado)"
    assert not any(ll['fase'] == 'Cuartos' for ll in c['llaves']) or all(
        ll.get('ganador') for ll in c['llaves'] if ll['fase'] == 'Octavos'), "cuartos antes de terminar octavos"
    assert mi in {n for ll in c['llaves'] for n in (ll['a'], ll['b'])} or CP.fase_user(estado) == 'Fase de liga'


def test_espectador_simula_copa_completa():
    """Usuario no clasificado: las copas se simulan enteras y declaran un campeón válido."""
    estado = _estado(jornada=10, clasificado=False)
    assert CP.tipo_copa_user(estado) is None
    C.simular_copa_entera(estado)
    assert estado["copa_user_en_copa"] is False
    for t in ('champions', 'libertadores'):
        c = CP.copa(estado, t)
        assert _equipo_valido(c['campeon']), f"campeón inválido: {c['campeon']!r}"
        for fase, _f in CP.ETAPAS[t][1:]:
            assert _llaves_validas(c, fase), f"llaves inválidas en {t}/{fase}"
            assert all(p['jugado'] for p in c['partidos'] if p['fase'] == fase), f"fase no jugada: {fase}"


def test_usuario_eliminado_no_ofrece_fase():
    """Si el usuario queda eliminado, no se le ofrece un partido jugable de la fase siguiente."""
    estado = _estado(jornada=22)
    mi = estado['mi_equipo'].nombre
    pend = CP.partido_pendiente_user(estado)
    while pend:                                   # pierde todo 0-4
        gl, gv = (0, 4) if pend['local'] == mi else (4, 0)
        CP.registrar_resultado_user(estado, pend['id'], gl, gv)
        pend = CP.partido_pendiente_user(estado)
    assert C.rival_copa_pendiente(estado) == (None, None), "un usuario eliminado no debe tener partido pendiente"
    assert (C.linea_copa_user(estado) or '').startswith("Copa: eliminado en")


if __name__ == "__main__":
    fns = [
        test_no_llaves_sin_fase_de_liga_completa,
        test_avance_secuencial_valido,
        test_espectador_simula_copa_completa,
        test_usuario_eliminado_no_ofrece_fase,
    ]
    for fn in fns:
        fn()
        print(f"  OK  {fn.__name__}")
    print(f"\n{len(fns)} tests de integridad de copa PASARON.")
