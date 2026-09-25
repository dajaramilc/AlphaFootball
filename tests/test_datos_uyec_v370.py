"""v3.7.0: datos Sudamérica B — uruguay, ecuador (1ª y 2ª) + relleno internacional de las copas."""
import sys, os, importlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

MODULOS = ['uruguay', 'ecuador', 'segunda_uruguay', 'segunda_ecuador']
POS_MIN = {'POR': 2, 'DEF': 6, 'MED': 6, 'DEL': 3}
RASGOS = {None, 'regateador', 'lider', 'rustico', 'pulmon_de_hierro'}


def _datos(mod):
    m = importlib.import_module(f'alpha_football.data.{mod}')
    return getattr(m, 'PLANTILLAS_2A', None) or next(v for k, v in vars(m).items() if k.startswith('DATOS_'))


def _validar_plantel(etiqueta, club, js, ovr_max, vistos):
    assert 20 <= len(js) <= 25, (etiqueta, club, len(js))
    for pos, n in POS_MIN.items():
        assert sum(1 for j in js if j[2] == pos) >= n, (etiqueta, club, pos)
    for nom, ape, pos, ovr, rasgo, edad in js:
        assert pos in POS_MIN and rasgo in RASGOS and 16 <= edad <= 41 and 40 <= ovr <= ovr_max, (etiqueta, club, nom)
        assert (nom, ape) not in vistos, (etiqueta, club, nom, ape)
        vistos.add((nom, ape))


def test_doce_clubes_validos():
    vistos = set()
    for mod in MODULOS:
        datos = _datos(mod)
        assert len(datos) == 12, (mod, len(datos))
        for club, info in datos.items():
            _validar_plantel(mod, club, info['jugadores'], 81, vistos)
    print("  test_doce_clubes_validos: OK")


def test_get_liga_construye():
    for mod in MODULOS:
        liga = importlib.import_module(f'alpha_football.data.{mod}').get_liga()
        assert liga and len(liga.equipos) == 12 and all(len(e.jugadores) >= 20 for e in liga.equipos), mod
        ids = [j.id for e in liga.equipos for j in e.jugadores]
        assert len(ids) == len(set(ids)), mod
    print("  test_get_liga_construye: OK")


def test_dt_y_clasicos_1a():
    from alpha_football.data.entrenadores import DT_REALES
    from alpha_football.estilos import ESTILOS_DT
    from alpha_football.data.clasicos import asignar_rivales
    for mod in ('uruguay', 'ecuador'):
        for club in _datos(mod):
            assert club in DT_REALES, club
            assert DT_REALES[club][1] in ESTILOS_DT, club
        eqs = importlib.import_module(f'alpha_football.data.{mod}').get_liga().equipos
        asignar_rivales(eqs)
        con_rival = [e for e in eqs if e.rival]
        assert len(con_rival) >= 6, (mod, [e.nombre for e in con_rival])
    print("  test_dt_y_clasicos_1a: OK")


def test_relleno_internacional():
    from alpha_football.data import internacional as I
    assert len(I.RELLENO_CHAMPIONS) == 21 and len(I.RELLENO_LIBERTADORES) == 4
    assert len(set(I.RELLENO_CHAMPIONS)) == 21 and len(set(I.RELLENO_LIBERTADORES)) == 4
    datos = {**I.DATOS_CHAMPIONS, **I.DATOS_LIBERTADORES}
    for club in I.RELLENO_CHAMPIONS:
        assert club in I.DATOS_CHAMPIONS, club
    for club in I.RELLENO_LIBERTADORES:
        assert club in I.DATOS_LIBERTADORES, club
    vistos = set()
    for club in I.RELLENO_CHAMPIONS + I.RELLENO_LIBERTADORES:
        assert datos[club].get('pais'), club
        _validar_plantel('internacional', club, datos[club]['jugadores'], 93, vistos)
    paises = [datos[c]['pais'] for c in I.RELLENO_CHAMPIONS]
    esperado = {'Alemania': 5, 'Francia': 4, 'Portugal': 3, 'Países Bajos': 3, 'Bélgica': 1,
                'Escocia': 1, 'Turquía': 1, 'Austria': 1, 'Croacia': 1, 'Ucrania': 1}
    assert {p: paises.count(p) for p in set(paises)} == esperado, paises
    assert sorted(datos[c]['pais'] for c in I.RELLENO_LIBERTADORES) == sorted(['Chile', 'Paraguay', 'Perú', 'Bolivia'])
    nombres_ligas = set()
    for mod in ('premier', 'laliga', 'seriea', 'brasil', 'argentina', 'betplay', 'uruguay', 'ecuador',
                'segunda_uruguay', 'segunda_ecuador'):
        nombres_ligas |= set(_datos(mod))
    assert not nombres_ligas & set(datos), nombres_ligas & set(datos)
    assert len(I.get_pool_champions()) == len(I.DATOS_CHAMPIONS)
    assert len(I.get_pool_libertadores()) == len(I.DATOS_LIBERTADORES)
    print("  test_relleno_internacional: OK")


TESTS = [test_doce_clubes_validos, test_get_liga_construye, test_dt_y_clasicos_1a, test_relleno_internacional]


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
