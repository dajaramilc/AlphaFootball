"""v2.6.0: plantilla completa en DIRECCIÓN (lista, ficha y transferibles)."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(5)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import market
from alpha_football.models import Jugador, alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams
from alpha_football.ui import plantilla_screen, league_screen


def click(pos):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def key(k):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=''))


def estado_carrera():
    liga = load_league_teams('premier')
    mi = liga.equipos[0]
    mi.alineacion_activa = alineacion_por_defecto(mi)
    return {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
            'alineacion_activa': mi.alineacion_activa}


def test_ordenar_plantilla():
    jug = estado_carrera()['mi_equipo'].jugadores
    por_ovr = [jug[i].overall for i in plantilla_screen.ordenar_plantilla(jug, 'ovr')]
    assert por_ovr == sorted(por_ovr, reverse=True)
    por_pos = [jug[i].posicion for i in plantilla_screen.ordenar_plantilla(jug, 'pos')]
    orden = {'POR': 0, 'DEF': 1, 'MED': 2, 'DEL': 3}
    assert [orden[p] for p in por_pos] == sorted(orden[p] for p in por_pos)
    edades = [jug[i].edad for i in plantilla_screen.ordenar_plantilla(jug, 'edad')]
    assert edades == sorted(edades)
    assert sorted(plantilla_screen.ordenar_plantilla(jug, 'valor')) == list(range(len(jug)))
    print("  test_ordenar_plantilla: OK")


def test_alternar_transferible_baja_moral():
    j = estado_carrera()['mi_equipo'].jugadores[0]
    j.moral = 70
    assert plantilla_screen.alternar_transferible(j) is True
    assert j.transferible and j.moral == 65
    assert plantilla_screen.alternar_transferible(j) is False
    assert not j.transferible and j.moral == 65
    print("  test_alternar_transferible_baja_moral: OK")


def test_guardado_transferible():
    j = estado_carrera()['mi_equipo'].jugadores[0]
    j.transferible = True
    assert Jugador.from_dict(j.to_dict()).transferible is True
    d = j.to_dict(); d.pop('transferible')
    assert Jugador.from_dict(d).transferible is False
    print("  test_guardado_transferible: OK")


def test_transferibles_atraen_ofertas():
    e = estado_carrera()
    mi, rivales = e['mi_equipo'], e['liga'].equipos[1:]
    market.ACTIVE_ESTADO = None
    rng = random.Random(3)
    base = sum(market.crear_oferta_ui(mi, rivales, 1, 10, rng=rng) is not None for _ in range(400))
    objetivo = mi.jugadores[5]
    objetivo.transferible = True
    ofertas = [market.crear_oferta_ui(mi, rivales, 1, 10, rng=rng) for _ in range(400)]
    ofertas = [o for o in ofertas if o]
    por_transf = sum(o['jugador'] is objetivo for o in ofertas)
    print(f"    ofertas sin transferibles {base}/400 · con uno {len(ofertas)}/400 ({por_transf} por él)")
    assert len(ofertas) > 2 * base
    assert por_transf / len(ofertas) > 0.6
    assert all(market.crear_oferta_ui(mi, rivales, 5, 10, rng=random.Random(i)) is None for i in range(50))
    print("  test_transferibles_atraen_ofertas: OK")


def test_pantalla_plantilla():
    e = estado_carrera()
    mi = e['mi_equipo']
    assert ('PLANTILLA', 'Todos tus jugadores, ficha y transferibles', 'plantilla_screen') in league_screen.TARJETAS['direccion']
    pygame.event.clear()
    assert plantilla_screen.render(screen, e) is None
    orden = plantilla_screen.ordenar_plantilla(mi.jugadores, e['plantilla_orden'])
    click(plantilla_screen._rect_fila(2).center)
    plantilla_screen.render(screen, e)
    assert e['plantilla_sel'] == orden[2]
    j = mi.jugadores[orden[2]]
    click(plantilla_screen._rects()['transferible'].center)
    plantilla_screen.render(screen, e)
    assert j.transferible
    key(pygame.K_DOWN); plantilla_screen.render(screen, e)
    assert e['plantilla_sel'] == orden[3]
    key(pygame.K_t); plantilla_screen.render(screen, e)
    assert mi.jugadores[orden[3]].transferible
    key(pygame.K_s); plantilla_screen.render(screen, e)
    assert e['plantilla_orden'] != 'pos'
    key(pygame.K_ESCAPE)
    assert plantilla_screen.render(screen, e) == 'league_screen'
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'main.py'), encoding='utf-8').read()
    assert "'plantilla_screen': 'alpha_football.ui.plantilla_screen'" in src   # v3.6.0: MODULOS_PANTALLA
    print("  test_pantalla_plantilla: OK")


TESTS = [test_ordenar_plantilla, test_alternar_transferible_baja_moral, test_guardado_transferible,
         test_transferibles_atraen_ofertas, test_pantalla_plantilla]


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
