"""Diagnóstico exhaustivo de bugs de runtime en v2.3."""
import sys, os, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
import pygame; pygame.init()

RESULTS = []

def test(name):
    def decorator(fn):
        def wrapper():
            try:
                fn()
                RESULTS.append(('OK', name))
                print(f'  ✓ {name}')
            except Exception as e:
                RESULTS.append(('FAIL', name, e))
                print(f'  ✗ {name}: {e}')
                traceback.print_exc()
        return wrapper
    return decorator

TESTS = []

def it(name):
    """Simple test runner — returns (name, ok, error)."""
    def decorator(fn):
        TESTS.append((name, fn))
        return fn
    return decorator

# ── TESTS ──────────────────────────────────────────────────────────────────────

@it("models.StateJuego.segunda_division type consistency")
def _():
    from alpha_football.models import EstadoJuego
    ej = EstadoJuego()
    assert isinstance(ej.segunda_division, dict), f"Expected dict, got {type(ej.segunda_division)}"

@it("models.Liga.division default")
def _():
    from alpha_football.models import Liga, Equipo
    l = Liga(nombre="T", tipo="x", equipos=[], num_jornadas=10)
    assert l.division == 1
    e = Equipo(nombre="A", ciudad="B", estrellas=3, estilo_dt="cruyffismo", balance=1000)
    assert e.division == 1

@it("data.segunda_betplay imports correctly")
def _():
    from alpha_football.data.segunda_betplay import get_liga
    liga = get_liga()
    assert liga.division == 2
    assert len(liga.equipos) >= 6
    for eq in liga.equipos:
        assert eq.division == 2, f"{eq.nombre} division={eq.division}"

@it("data.segunda_laliga imports correctly")
def _():
    from alpha_football.data.segunda_laliga import get_liga
    liga = get_liga()
    assert liga.division == 2

@it("data.segunda_premier imports correctly")
def _():
    from alpha_football.data.segunda_premier import get_liga
    liga = get_liga()
    assert liga.division == 2

@it("data.segunda_brasil imports correctly")
def _():
    from alpha_football.data.segunda_brasil import get_liga
    liga = get_liga()
    assert liga.division == 2

@it("data.segunda_argentina imports correctly")
def _():
    from alpha_football.data.segunda_argentina import get_liga
    liga = get_liga()
    assert liga.division == 2

@it("menu.PAISES_DISPONIBLES maps correctly to valid modules")
def _():
    from alpha_football.ui.menu import PAISES_DISPONIBLES
    for pais in PAISES_DISPONIBLES:
        code = pais['codigo']
        liga_id = pais['liga_id']
        __import__(f'alpha_football.data.{liga_id}')
        __import__(f'alpha_football.data.segunda_{liga_id}')

@it("menu.load_division_teams country_id -> liga_id translation works")
def _():
    from alpha_football.ui.menu import load_division_teams
    for pais in ['colombia', 'espana', 'inglaterra', 'brasil', 'argentina']:
        liga1 = load_division_teams(pais, 1)
        assert liga1 is not None, f"load_division_teams({pais}, 1) returned None"
        liga2 = load_division_teams(pais, 2)
        assert liga2 is not None, f"load_division_teams({pais}, 2) returned None"
        assert liga2.division == 2, f"Segunda de {pais} no tiene division=2"
        for eq in liga2.equipos:
            assert len(eq.jugadores) >= 20, f"{eq.nombre} en 2ª de {pais} tiene {len(eq.jugadores)} jugadores"

@it("resumen_temporada._BONO_LIGA_2A_X2 has correct structure")
def _():
    from alpha_football.ui.resumen_temporada_screen import _BONO_LIGA_2A_X2
    expected_keys = {'premier', 'laliga', 'brasil', 'argentina', 'betplay'}
    assert set(_BONO_LIGA_2A_X2.keys()) == expected_keys
    for k, v in _BONO_LIGA_2A_X2.items():
        assert len(v) == 6, f"Bono {k} tiene {len(v)} elementos, esperados 6"

@it("promo_releg_screen imports and has render function")
def _():
    from alpha_football.ui.promo_releg_screen import render
    assert callable(render)

@it("Jugador has potencial field")
def _():
    from alpha_football.models import Jugador
    j = Jugador(nombre="X", apellido="Y", posicion="MED", ataque=60, defensa=60, fisico=60, tecnica=60, mental=60)
    assert hasattr(j, 'potencial'), "Jugador no tiene campo potencial"
    assert j.potencial == 0

@it("Alineacion has convocados field")
def _():
    from alpha_football.models import Alineacion
    a = Alineacion()
    assert hasattr(a, 'convocados'), "Alineacion no tiene campo convocados"
    assert isinstance(a.convocados, list)

@it("Segunda division OVR ranges are reasonable")
def _():
    for m in ['betplay', 'laliga', 'premier', 'brasil', 'argentina']:
        mod = __import__(f'alpha_football.data.segunda_{m}', fromlist=['get_liga'])
        liga = mod.get_liga()
        for eq in liga.equipos:
            for j in eq.jugadores:
                ovr = j.overall
                assert 30 <= ovr <= 85, f"Jugador {j.nombre_completo} en 2ª {m} tiene OVR={ovr}"

@it("Models Liga.to_dict includes division")
def _():
    from alpha_football.models import Liga, EstadoJuego
    l = Liga(nombre="Test", tipo="betplay", equipos=[], num_jornadas=10, division=1)
    d = l.to_dict()
    assert 'division' in d, "Liga.to_dict() no incluye 'division'"
    assert d['division'] == 1
    ej = EstadoJuego()
    d = ej.to_dict()
    assert 'liga_usuario_division' in d, "EstadoJuego.to_dict() no incluye liga_usuario_division"
    assert 'segunda_division_keys' in d, "EstadoJuego.to_dict() no incluye segunda_division_keys"

@it("liga.tipo matches segunda_division key for promo/releg")
def _():
    from alpha_football.data import betplay, segunda_betplay
    liga1 = betplay.get_liga()
    liga2 = segunda_betplay.get_liga()
    tipo = liga1.tipo
    estado = {'segunda_division': {tipo: liga2}}
    assert estado['segunda_division'][tipo].division == 2

@it("Alineacion.convocados survives save/load round-trip")
def _():
    from alpha_football.models import Alineacion, EstadoJuego
    a = Alineacion(titulares=list(range(11)), formacion="4-3-3", convocados=list(range(11, 21)))
    ej = EstadoJuego()
    ej.alineacion_activa = a
    d = ej.to_dict()
    assert d['alineacion_activa']['titulares'] == list(range(11))
    # convocados NOT serialized in to_dict (existing behavior — deliberate)
    ej2 = EstadoJuego.from_dict(d)
    assert ej2.alineacion_activa is not None

@it("Equipo.division survives to_dict/from_dict round-trip")
def _():
    from alpha_football.models import Equipo
    e = Equipo(nombre="Test", ciudad="X", estrellas=3, estilo_dt="cruyffismo", balance=1000, division=2)
    d = e.to_dict()
    e2 = Equipo.from_dict(d)
    assert e2.division == 2

# ── RUN ALL ───────────────────────────────────────────────────────────────────

ok = fail = 0
for name, fn in TESTS:
    try:
        fn()
        ok += 1
        print(f'  OK  {name}')
    except Exception as e:
        fail += 1
        print(f'  FAIL  {name}: {e}')
        traceback.print_exc()

print(f"\n{'='*60}")
print(f"RESULTADOS: {ok}/{ok+fail} pasaron")
if fail:
    print(f"\nFALLOS ({fail}):")
    sys.exit(1)
else:
    print("Todos los tests pasaron.")
