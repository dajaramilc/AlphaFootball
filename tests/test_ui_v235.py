"""v2.3.5: dirección de equipo estilo FIFA, barra de menú superior, OTRAS LIGAS y copa en 2ª."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(3)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import formaciones as F
from alpha_football.models import alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams, load_division_teams, _ligas_por_division
from alpha_football.ui import team_screen, league_screen, otras_ligas_screen, copa_screen


def click(pos):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def estado_carrera(division=1):
    liga = load_league_teams('premier') if division == 1 else load_division_teams('premier', 2)
    mi = liga.equipos[0]
    alin = alineacion_por_defecto(mi)
    mi.alineacion_activa = alin
    primeras, segunda = _ligas_por_division(liga, {}, {})
    return {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
            'alineacion_activa': alin, 'primera_division': primeras, 'segunda_division': segunda,
            'team_contexto': 'carrera'}


def check_once(alin, n_jug):
    assert len(alin.titulares) == 11 and len(set(alin.titulares)) == 11, alin.titulares
    assert len(alin.convocados) == 10 and len(set(alin.convocados)) == 10
    assert not set(alin.titulares) & set(alin.convocados)
    assert all(0 <= i < n_jug for i in alin.titulares + alin.convocados)


def test_intercambiar_nunca_pierde_titulares():
    e = estado_carrera()
    alin, jug = e['alineacion_activa'], e['mi_equipo'].jugadores
    F.normalizar_convocados(alin, jug)
    for _ in range(500):
        zonas = [('campo', random.randrange(11)), ('banco', random.randrange(10))]
        reservas = [i for i in range(len(jug)) if i not in alin.titulares and i not in alin.convocados]
        if reservas:
            zonas.append(('reserva', random.choice(reservas)))
        a, b = random.choice(zonas), random.choice(zonas)
        F.intercambiar(alin, a, b)
        check_once(alin, len(jug))
    print("  test_intercambiar_nunca_pierde_titulares: OK")


def test_acomodar_pone_cada_uno_en_su_puesto():
    e = estado_carrera()
    alin, jug = e['alineacion_activa'], e['mi_equipo'].jugadores
    for f in F.lista_formaciones():
        once = F.mejor_once(jug, f)
        orden = F.acomodar_en_puestos(list(reversed(once)), jug, f)
        assert sorted(orden) == sorted(once)
        assert [jug[i].posicion for i in orden] == F.puestos(f), f
    print("  test_acomodar_pone_cada_uno_en_su_puesto: OK")


def _centro_slot(alin, k):
    px, py = F.posiciones(alin.formacion)[k]
    return (team_screen._CAMPO.x + int(team_screen._CAMPO.width * px),
            team_screen._CAMPO.y + int(team_screen._CAMPO.height * py))


def test_direccion_clic_selecciona_y_cambia():
    e = estado_carrera()
    alin = e['alineacion_activa']
    team_screen.render(screen, e)                       # primer frame: respaldo + acomodo
    check_once(alin, len(e['mi_equipo'].jugadores))
    antes = list(alin.titulares)

    click(_centro_slot(alin, 1))                          # selecciona un DEF
    assert team_screen.render(screen, e) is None
    assert e['team_sel'] == ('campo', 1)
    assert alin.titulares == antes, "un clic no debe quitar a nadie"

    banco0 = alin.convocados[0]
    click((16 + 10, team_screen._BANCO_Y + 40))           # clic en el 1er suplente
    team_screen.render(screen, e)
    assert alin.titulares[1] == banco0 and alin.convocados[0] == antes[1], "cambio titular<->suplente"
    assert e.get('team_sel') is None
    check_once(alin, len(e['mi_equipo'].jugadores))

    click(_centro_slot(alin, 2)); team_screen.render(screen, e)
    click(_centro_slot(alin, 3)); team_screen.render(screen, e)
    assert alin.titulares[2] == antes[3] and alin.titulares[3] == antes[2], "cambio de puesto campo<->campo"

    click(_centro_slot(alin, 5)); team_screen.render(screen, e)
    click(_centro_slot(alin, 5)); team_screen.render(screen, e)
    assert e.get('team_sel') is None, "clic en el mismo jugador lo suelta"
    check_once(alin, len(e['mi_equipo'].jugadores))

    click((1100 + 50, 18 + 20))                           # CANCELAR restaura
    assert team_screen.render(screen, e) == "league_screen"
    assert sorted(alin.titulares) == sorted(antes)
    print("  test_direccion_clic_selecciona_y_cambia: OK")


def test_otras_ligas_muestra_las_10():
    e = estado_carrera(division=2)
    ligas = otras_ligas_screen.ligas_disponibles(e)
    from alpha_football.paises import TIPOS_LIGA as _T   # v3.7.0: 8 países × 2 divisiones
    assert len(ligas) == 2 * len(_T)
    assert ligas[0][0].startswith("Inglaterra") and ligas[1][0].startswith("Inglaterra")
    pygame.event.clear()
    assert otras_ligas_screen.render(screen, e) is None
    assert ligas[e['otras_ligas_sel']][1] is not e['liga'], "abre en la otra división de tu país"
    print("  test_otras_ligas_muestra_las_10: OK")


def test_segunda_no_juega_copa():
    # v3.8.0: las copas salen del motor (clasificados solo de 1ª); se sincroniza como el hub.
    e = estado_carrera(division=2)
    e['copa_clasificado'] = True                          # aunque venga marcado
    copa_screen.sincronizar_copa_user(e)
    assert e['copa_user_en_copa'] is False
    from alpha_football import competiciones as CP
    nombres = {c['nombre'] for t in ('champions', 'libertadores') for c in CP.copa(e, t)['clubes']}
    assert e['mi_equipo'].nombre not in nombres
    print("  test_segunda_no_juega_copa: OK")


if __name__ == '__main__':
    tests = [test_intercambiar_nunca_pierde_titulares, test_acomodar_pone_cada_uno_en_su_puesto,
             test_direccion_clic_selecciona_y_cambia,
             test_otras_ligas_muestra_las_10, test_segunda_no_juega_copa]
    fail = 0
    for t in tests:
        try:
            t()
        except Exception as ex:
            fail += 1
            import traceback; traceback.print_exc()
            print(f"  {t.__name__}: FAIL - {ex}")
    print(f"\n{len(tests) - fail}/{len(tests)} tests pasaron")
    if fail:
        sys.exit(1)
