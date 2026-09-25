"""v2.7.0: NEGOCIACIONES — buscador, fichaje, historial de pases y ojeador."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(9)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import negociacion as N
from alpha_football.models import alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams, _ligas_por_division


def click(pos):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def teclear(texto):
    pygame.event.clear()
    for c in texto:
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=ord(c.lower()), mod=0, unicode=c))


def key(k):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=''))


def estado_carrera(tipo='betplay'):
    liga = load_league_teams(tipo)
    mi = liga.equipos[0]
    mi.alineacion_activa = alineacion_por_defecto(mi)
    primeras, segunda = _ligas_por_division(liga, {}, {})
    return {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
            'alineacion_activa': mi.alineacion_activa, 'primera_division': primeras,
            'segunda_division': segunda, 'datos_carrera': {}}


def test_pool_excluye_al_user_y_mejores_ordenados():
    e = estado_carrera()
    pool = N.pool_buscador(e)
    assert pool and all(club is not e['mi_equipo'] for _j, club, _et in pool)
    etiquetas = {et for _j, _c, et in pool}
    assert 'COL 1ª' in etiquetas and 'ING 1ª' in etiquetas and len(etiquetas) == 16   # v3.7.0: 8 países × 2
    top = N.mejores(pool)
    assert len(top) == N.N_MEJORES
    medias = [j.overall for j, _c, _e in top]
    assert medias == sorted(medias, reverse=True) and medias[0] == max(j.overall for j, _c, _e in pool)
    print("  test_pool_excluye_al_user_y_mejores_ordenados: OK")


def test_filtros_y_orden():
    pool = N.pool_buscador(estado_carrera())
    j0 = pool[7][0]
    por_nombre = N.filtrar(pool, {'nombre': j0.apellido.upper()})
    assert any(j is j0 for j, _c, _e in por_nombre)
    assert all(j0.apellido.lower() in f"{j.nombre} {j.apellido}".lower() for j, _c, _e in por_nombre)
    f = {'pos': 'DEF', 'edad_min': 20, 'edad_max': 25, 'ovr_min': 70, 'liga': 'ESP 1ª', 'precio_max': 50_000_000}
    res = N.filtrar(pool, f)
    assert res
    for j, _c, et in res:
        assert j.posicion == 'DEF' and 20 <= j.edad <= 25 and j.overall >= 70 and et == 'ESP 1ª'
        assert N.precio_fichaje(j) <= 50_000_000
    edades = [j.edad for j, _c, _e in N.ordenar(res, 'edad', False)]
    assert edades == sorted(edades)
    precios = [N.precio_fichaje(j) for j, _c, _e in N.ordenar(res, 'precio', True)]
    assert precios == sorted(precios, reverse=True)
    print("  test_filtros_y_orden: OK")


def test_fichar_mueve_cobra_y_registra():
    e = estado_carrera()
    mi = e['mi_equipo']
    j, club, _et = next((j, c, et) for j, c, et in N.pool_buscador(e) if c is not None and j.overall <= 70)
    mi.balance = 10 ** 9
    antes_club, precio = club.balance, N.precio_fichaje(j)
    ok, msg = N.fichar(e, j, club)
    assert ok, msg
    assert j in mi.jugadores and j not in club.jugadores
    assert mi.balance == 10 ** 9 - precio and club.balance == antes_club + precio
    h = N.historial(e, propio=True)
    assert h and h[0]['jugador'] == f"{j.nombre} {j.apellido}" and h[0]['a'] == mi.nombre and h[0]['monto'] == precio
    # sin fondos: no cambia nada
    j2, club2, _ = next((j, c, et) for j, c, et in N.pool_buscador(e) if c is not None and j.overall <= 70)
    mi.balance = 0
    ok, msg = N.fichar(e, j2, club2)
    assert not ok and j2 in club2.jugadores and j2 not in mi.jugadores and mi.balance == 0
    print("  test_fichar_mueve_cobra_y_registra: OK")


def test_historial_general_incluye_la_ia():
    from alpha_football import mercado_ia
    e = estado_carrera()
    log = mercado_ia.ronda_fichajes_ia(e, 'pretemporada', rng=random.Random(4))
    ajenos = N.historial(e, propio=False)
    assert log and len(ajenos) == len(log)
    assert all(not h['propio'] and h['monto'] > 0 for h in ajenos)
    print("  test_historial_general_incluye_la_ia: OK")


def test_ojeador_recomienda_3_pagables_que_mejoran():
    e = estado_carrera()
    mi = e['mi_equipo']
    mi.balance = 30_000_000
    recs = N.recomendaciones_ojeador(e)
    assert 1 <= len(recs) <= 3
    peor = N.necesidades(mi)
    for j, club, _et, precio, motivo in recs:
        assert precio <= mi.balance and j.overall >= peor[j.posicion] + 2 and motivo
    assert len({id(r[0]) for r in recs}) == len(recs)
    otra = N.recomendaciones_ojeador(e)                  # misma ventana: las mismas
    assert [id(r[0]) for r in otra] == [id(r[0]) for r in recs]
    e['liga'].jornada_actual = e['liga'].num_jornadas    # ventana de cierre: se recalculan
    N.recomendaciones_ojeador(e)
    assert e['datos_carrera']['ojeador']['clave'][1] == 'cierre'
    print("  test_ojeador_recomienda_3_pagables_que_mejoran: OK")


def test_pantallas_negociaciones():
    from alpha_football.ui import league_screen, buscador_screen, historial_pases_screen, ojeador_screen
    tarj = [t[2] for t in league_screen.TARJETAS['negociaciones']]
    assert tarj == ['buscador_screen', 'ofertas_screen', 'historial_pases_screen', 'ojeador_screen']
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'main.py'), encoding='utf-8').read()
    for nombre in ('buscador', 'historial_pases', 'ojeador'):
        assert f"'{nombre}_screen': 'alpha_football.ui.{nombre}_screen'" in src, nombre   # v3.6.0: MODULOS_PANTALLA
    # Buscador: primero los mejores; escribir un nombre + Enter filtra; FICHAR ficha.
    e = estado_carrera()
    e['mi_equipo'].balance = 10 ** 9
    pygame.event.clear()
    assert buscador_screen.render(screen, e) is None
    assert len(e['busq_resultados']) == N.N_MEJORES and not e['busq']['buscado']
    click(buscador_screen._rects()['nombre'].center); buscador_screen.render(screen, e)
    objetivo = next(j for j, c, _et in N.pool_buscador(e) if c is not None and j.overall <= 70)
    teclear(objetivo.apellido); buscador_screen.render(screen, e)
    key(pygame.K_RETURN); buscador_screen.render(screen, e)
    assert e['busq']['buscado'] and any(j is objetivo for j, _c, _et in e['busq_resultados'])
    k = next(i for i, (j, _c, _et) in enumerate(e['busq_resultados']) if j is objetivo)
    e['busq']['sel'] = k
    click(buscador_screen._rects()['fichar'].center)
    assert buscador_screen.render(screen, e) == 'negociacion_screen'      # v2.9.0: se negocia
    assert e.pop('neg')['jugador'] is objetivo and objetivo not in e['mi_equipo'].jugadores
    click(buscador_screen._rects()['orden_edad'].center); buscador_screen.render(screen, e)
    assert e['busq']['orden'] == 'edad'
    key(pygame.K_ESCAPE)
    assert buscador_screen.render(screen, e) == 'league_screen'
    # Historial: pestañas general/propio.
    pygame.event.clear()
    assert historial_pases_screen.render(screen, e) is None
    click(historial_pases_screen._rects()['propio'].center); historial_pases_screen.render(screen, e)
    assert e['hist_pases_tab'] == 'propio'
    key(pygame.K_ESCAPE)
    assert historial_pases_screen.render(screen, e) == 'league_screen'
    # Ojeador: muestra recomendaciones y permite fichar la primera.
    e = estado_carrera(); e['mi_equipo'].balance = 30_000_000
    pygame.event.clear()
    assert ojeador_screen.render(screen, e) is None
    recs = N.recomendaciones_ojeador(e)
    click(ojeador_screen._rects_fichar(len(recs))[0].center)
    assert ojeador_screen.render(screen, e) == 'negociacion_screen'
    assert e['neg']['jugador'] is recs[0][0] and e['neg']['volver'] == 'ojeador_screen'
    print("  test_pantallas_negociaciones: OK")


TESTS = [test_pool_excluye_al_user_y_mejores_ordenados, test_filtros_y_orden, test_fichar_mueve_cobra_y_registra,
         test_historial_general_incluye_la_ia, test_ojeador_recomienda_3_pagables_que_mejoran,
         test_pantallas_negociaciones]


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
