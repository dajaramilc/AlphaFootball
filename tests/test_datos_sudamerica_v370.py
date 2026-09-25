"""v3.7.0: datos Sudamérica A — brasil, argentina, betplay (1ª y 2ª) con 12 clubes reales parodiados."""
import sys, os, importlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

MODULOS = ['brasil', 'argentina', 'betplay', 'segunda_brasil', 'segunda_argentina', 'segunda_betplay']
POS_MIN = {'POR': 2, 'DEF': 6, 'MED': 6, 'DEL': 3}
RASGOS = {None, 'regateador', 'lider', 'rustico', 'pulmon_de_hierro'}


def _datos(mod):
    m = importlib.import_module(f'alpha_football.data.{mod}')
    return getattr(m, 'PLANTILLAS_2A', None) or next(v for k, v in vars(m).items() if k.startswith('DATOS_'))


def test_doce_clubes_validos():
    vistos = set()
    for mod in MODULOS:
        datos = _datos(mod)
        assert len(datos) == 12, (mod, len(datos))
        for club, info in datos.items():
            js = info['jugadores']
            assert 20 <= len(js) <= 25, (mod, club, len(js))
            for pos, n in POS_MIN.items():
                assert sum(1 for j in js if j[2] == pos) >= n, (mod, club, pos)
            for nom, ape, pos, ovr, rasgo, edad in js:
                assert pos in POS_MIN and rasgo in RASGOS and 16 <= edad <= 41 and 40 <= ovr <= 81, (mod, club, nom)
                assert (nom, ape) not in vistos, (mod, club, nom, ape)
                vistos.add((nom, ape))
    print("  test_doce_clubes_validos: OK")


def test_get_liga_construye():
    for mod in MODULOS:
        liga = importlib.import_module(f'alpha_football.data.{mod}').get_liga()
        assert liga and len(liga.equipos) == 12 and all(len(e.jugadores) >= 20 for e in liga.equipos), mod
        assert liga.num_jornadas == 22, (mod, liga.num_jornadas)
        ids = [j.id for e in liga.equipos for j in e.jugadores]
        assert len(ids) == len(set(ids)), mod
    print("  test_get_liga_construye: OK")


def test_dt_y_clasicos_1a():
    from alpha_football.data.entrenadores import DT_REALES
    from alpha_football.estilos import ESTILOS_DT
    from alpha_football.data.clasicos import asignar_rivales
    for mod in ('brasil', 'argentina', 'betplay'):
        for club in _datos(mod):
            assert club in DT_REALES, club
            assert DT_REALES[club][1] in ESTILOS_DT, club
        # v3.7.0: los clásicos se reconocen entre los clubes de la propia 1ª.
        eqs = importlib.import_module(f'alpha_football.data.{mod}').get_liga().equipos
        asignar_rivales(eqs)
        con_rival = [e for e in eqs if e.rival]
        assert len(con_rival) >= 6, (mod, [e.nombre for e in con_rival])
    print("  test_dt_y_clasicos_1a: OK")


def test_sin_duplicados_con_internacional():
    # v3.7.0: ningún club de estas ligas repite nombre (ni identidad) con el pool internacional.
    from alpha_football.data import internacional as I
    otros = set(I.DATOS_CHAMPIONS) | set(I.DATOS_LIBERTADORES)
    sud = [c for mod in MODULOS for c in _datos(mod)]
    assert len(sud) == len(set(sud))
    assert not set(sud) & otros, set(sud) & otros
    assert 'Boca Amargo' not in otros and 'Palmeirras' not in otros
    print("  test_sin_duplicados_con_internacional: OK")


TESTS = [test_doce_clubes_validos, test_get_liga_construye, test_dt_y_clasicos_1a,
         test_sin_duplicados_con_internacional]


if __name__ == '__main__':
    fail = 0
    for t in TESTS:
        try:
            t()
        except Exception as ex:
            fail += 1
            import traceback; traceback.print_exc()
            print(f"  {t.__name__}: FAIL - {ex}")
    print(f"\n{len(TESTS) - fail}/{len(TESTS)} tests pasaron")
    if fail:
        sys.exit(1)
