"""v3.3.0: 9 estilos de juego — matriz de ventajas, Kloppismo gasta más y estilos viejos."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(13)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import estilos as ES, engine, energia as E
from alpha_football.models import Equipo


def test_nueve_estilos():
    assert len(ES.ESTILOS_DT) == 9 and set(ES.ESTILOS_DT) == set(ES.NOMBRE_ESTILO) == set(ES.DESC_ESTILO)
    assert engine.ESTILOS_DT is ES.ESTILOS_DT
    assert ES.ESTILOS_UI[0] == 'anchelottismo' and sorted(ES.ESTILOS_UI) == sorted(ES.ESTILOS_DT)


def test_matriz_sin_contradicciones():
    total = 0
    for a, gana in ES.ESTILO_VENTAJA.items():
        for b in gana:
            assert a not in ES.ESTILO_VENTAJA.get(b, ()), f"{a} y {b} se ganan mutuamente"
            total += 1
    assert total == 20
    assert 'anchelottismo' not in ES.ESTILO_VENTAJA
    assert all('anchelottismo' not in g for g in ES.ESTILO_VENTAJA.values())


def test_matriz_de_diego():
    V = ES.ESTILO_VENTAJA
    # v3.9.0: Cruyffismo y Fullbackismo equilibrados (+1 victoria y −1 derrota cada uno)
    assert V['cruyffismo'] == {'flickismo', 'artetismo'}
    assert V['flickismo'] == {'haramball', 'artetismo'}
    assert V['haramball'] == {'cruyffismo', 'dezerbismo', 'kloppismo'}
    assert V['kloppismo'] == {'choloismo', 'fullbackismo'}
    assert V['artetismo'] == {'haramball', 'choloismo', 'dezerbismo'}
    assert V['choloismo'] == {'cruyffismo', 'dezerbismo', 'fullbackismo'}
    assert V['dezerbismo'] == {'flickismo', 'kloppismo', 'fullbackismo'}
    assert V['fullbackismo'] == {'cruyffismo', 'haramball'}
    # nadie queda con más de 1 de diferencia entre victorias y derrotas
    for a in V:
        g = len(V[a]); p = sum(1 for b in V if a in V[b])
        assert abs(g - p) <= 1, (a, g, p)


def test_bono_estilo():
    assert engine.bono_estilo('artetismo', 'haramball') == 1.10      # v3.9.0: ventaja bajada a 10%
    assert engine.bono_estilo('haramball', 'artetismo') == 0.91
    assert engine.bono_estilo('artetismo', 'kloppismo') == 1.0           # par neutro
    assert engine.bono_estilo('artetismo', 'cruyffismo') == 0.91         # v3.9.0: Cruyff le gana a Arteta
    assert engine.bono_estilo('anchelottismo', 'kloppismo') == 1.0
    assert engine.bono_estilo('desconocido', 'haramball') == 1.0


def test_kloppismo_gasta_mas():
    assert ES.factor_gasto_estilo('kloppismo') == 1.3 and ES.factor_gasto_estilo('haramball') == 1.0
    from alpha_football.ui.menu import load_league_teams
    liga = load_league_teams('premier')
    j = liga.equipos[0].jugadores[0]; j.energia = 100.0
    normal = E.energia_en_minuto(j, 90)
    klopp = E.energia_en_minuto(j, 90, mult=1.3)
    assert round(100 - klopp, 6) == round((100 - normal) * 1.3, 6) or klopp == 0.0


def test_normalizar_estilo():
    assert ES.normalizar_estilo('guardiolismo') == 'cruyffismo'
    assert ES.normalizar_estilo('simeonismo') == 'choloismo'
    assert ES.normalizar_estilo('mourinhismo') == 'haramball'
    assert ES.normalizar_estilo('bielsismo') == 'kloppismo'
    assert ES.normalizar_estilo('chapecoense') == 'anchelottismo'
    assert ES.normalizar_estilo('KLOPPISMO') == 'kloppismo'
    eq = Equipo.from_dict({'nombre': 'X', 'estilo_dt': 'simeonismo', 'jugadores': []})
    assert eq.estilo_dt == 'choloismo'


def test_listas_ui_unificadas():
    from alpha_football.ui import team_screen, edit_screen
    assert team_screen.TACTICAS == ES.ESTILOS_UI
    assert edit_screen.ESTILOS_TACTICOS == ES.ESTILOS_UI


TESTS = [test_nueve_estilos, test_matriz_sin_contradicciones, test_matriz_de_diego, test_bono_estilo,
         test_kloppismo_gasta_mas, test_normalizar_estilo, test_listas_ui_unificadas]


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
