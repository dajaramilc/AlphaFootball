"""v3.0.0 (sub-proyecto 1): bugs de integridad — simulación instantánea fiel y de un solo partido."""
import sys, os, random, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(5)
screen = pygame.display.set_mode((1280, 720))

from alpha_football.models import alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams, _ligas_por_division
from alpha_football.ui import prepartido_screen, league_screen


def key(k):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=''))


def estado_carrera():
    liga = load_league_teams('premier')
    mi = liga.equipos[0]
    alin = alineacion_por_defecto(mi)
    mi.alineacion_activa = alin
    primeras, segunda = _ligas_por_division(liga, {}, {})
    return {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
            'alineacion_activa': alin, 'primera_division': primeras, 'segunda_division': segunda,
            'team_contexto': 'carrera'}


def partido_user(liga, mi, jornada):
    return next(p for p in liga.calendario if p.jornada == jornada and mi.id in (p.local_id, p.visitante_id))


def test_simular_instantaneo_juega_un_solo_partido_y_fiel():
    for _ in range(10):
        e = estado_carrera()
        liga, mi = e['liga'], e['mi_equipo']
        league_screen.inicializar_calendario_liga(liga)
        liga.jornada_actual = 1
        p1, p2 = partido_user(liga, mi, 1), partido_user(liga, mi, 2)
        e['partido_actual'], e['match_mode'] = p1, 'liga'
        key(pygame.K_2)
        prepartido_screen.render(screen, e)
        assert liga.jornada_actual == 2, f"avanzó a J{liga.jornada_actual}"
        assert p1.jugado and not p2.jugado
        gl, gv = map(int, re.search(r"(\d+) - (\d+)", e['prepartido_resultado']['titulo']).groups())
        assert (p1.goles_local, p1.goles_visitante) == (gl, gv)
    print("  test_simular_instantaneo_juega_un_solo_partido_y_fiel: OK")


def test_brecha_entre_divisiones_10_a_14():
    from statistics import mean
    from alpha_football.ui.menu import load_division_teams
    for tipo in ('betplay', 'laliga', 'premier', 'brasil', 'argentina'):
        l1, l2 = load_league_teams(tipo), load_division_teams(tipo, 2)
        brecha = mean(e.ovr_promedio for e in l1.equipos) - mean(e.ovr_promedio for e in l2.equipos)
        assert 10 <= brecha <= 14, f"{tipo}: brecha {brecha:.1f}"
        assert all(j.potencial >= j.overall for e in l2.equipos for j in e.jugadores)
    print("  test_brecha_entre_divisiones_10_a_14: OK")


TESTS = [test_simular_instantaneo_juega_un_solo_partido_y_fiel, test_brecha_entre_divisiones_10_a_14]


if __name__ == '__main__':
    fail = 0
    for t in TESTS:
        try:
            t()
        except Exception as ex:
            fail += 1
            import traceback; traceback.print_exc()
            print(f"  {t.__name__}: FAIL - {ex}")
    print(f"{len(TESTS) - fail}/{len(TESTS)} OK")
    sys.exit(1 if fail else 0)
