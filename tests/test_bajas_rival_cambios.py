"""Lesionados/sancionados a reservas al empezar el partido, visor del rival en vivo y más cambios de la IA."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(31)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save
from alpha_football.models import alineacion_por_defecto, asegurar_ids_unicos
from alpha_football.ui.menu import load_league_teams, _ligas_por_division
from alpha_football.ui import match_screen as MS
from alpha_football import formaciones as F

save.guardar_en_slot = lambda *a, **k: None          # los tests no tocan los slots reales


def key(k, uni=''):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=uni))


def click(pos):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def estado_carrera(tipo='premier', idx=0):
    liga = load_league_teams(tipo)
    mi = liga.equipos[idx]
    mi.alineacion_activa = alineacion_por_defecto(mi)
    primeras, segunda = _ligas_por_division(liga, {}, {})
    return {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
            'alineacion_activa': mi.alineacion_activa, 'primera_division': primeras,
            'segunda_division': segunda, 'datos_carrera': {}, 'historial': []}


def test_bajas_a_reservas():
    e = estado_carrera(); mi = e['mi_equipo']; js = mi.jugadores; alin = mi.alineacion_activa
    F.normalizar_convocados(alin, js)
    tit, ban = alin.titulares[3], alin.convocados[0]
    js[tit].lesion_partidos = 2
    js[ban].partidos_sancion = 1
    pos = js[tit].posicion
    retirados = F.retirar_no_disponibles(alin, js)
    assert js[tit] in retirados and js[ban] in retirados
    assert tit not in alin.titulares and tit not in alin.convocados
    assert ban not in alin.titulares and ban not in alin.convocados
    assert len(alin.titulares) == 11 and len(set(alin.titulares)) == 11
    assert js[alin.titulares[3]].posicion == pos                    # lo cubre uno de su puesto
    assert not set(alin.titulares) & set(alin.convocados)
    assert all(js[i].lesion_partidos == 0 and not js[i].partidos_sancion for i in alin.titulares + alin.convocados)
    assert F.retirar_no_disponibles(alin, js) == []                 # idempotente
    print("  test_bajas_a_reservas: OK")


def _vivo(e):
    liga = e['liga']
    from alpha_football.ui.league_screen import inicializar_calendario_liga
    if not getattr(liga, 'calendario', None):
        inicializar_calendario_liga(liga)
    mi = e['mi_equipo']
    p = next(p for p in liga.calendario if p.jornada == liga.jornada_actual and mi.id in (p.local_id, p.visitante_id))
    e['partido_actual'] = p; e['match_mode'] = 'liga'
    pygame.event.clear(); MS.render(screen, e)
    return 'l' if p.local_id == mi.id else 'v'


def test_visor_rival_pausa_y_cierra():
    e = estado_carrera(); _vivo(e)
    for _ in range(20):                                          # unos minutos de partido
        e['sim_last_tick'] = -10**9; e['sim_pausa_hasta'] = 0
        pygame.event.clear(); MS.render(screen, e)
    key(pygame.K_r); MS.render(screen, e)
    assert e.get('sim_rival_abierto')
    minuto = e['sim_minuto']
    e['sim_last_tick'] = -10**9; e['sim_pausa_hasta'] = 0
    pygame.event.clear(); MS.render(screen, e)
    assert e['sim_minuto'] == minuto and e.get('sim_rival_abierto')   # reloj en pausa, sigue abierto
    click(MS.R_RIVAL_VOLVER.center); MS.render(screen, e)
    assert not e.get('sim_rival_abierto')
    print("  test_visor_rival_pausa_y_cierra: OK")


def test_ia_hace_mas_cambios():
    from alpha_football.engine import simular_partido
    liga = load_league_teams('premier'); a, b = liga.equipos[0], liga.equipos[1]
    for eq in (a, b):
        asegurar_ids_unicos(eq)
    random.seed(5)
    cambios = []
    for _ in range(40):
        r = simular_partido(a, b, aplicar_fisico=False)
        cambios += [r.ctx.cambios.get('l', 0), r.ctx.cambios.get('v', 0)]
    prom = sum(cambios) / len(cambios)
    assert prom >= 4.0 and max(cambios) <= 5, prom
    print(f"  test_ia_hace_mas_cambios: OK (promedio {prom:.2f})")


TESTS = [f for n, f in list(globals().items()) if n.startswith('test_') and callable(f)]


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
