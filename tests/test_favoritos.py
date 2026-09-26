"""NEGOCIACIONES > FAVORITOS: marcar en el buscador, lista aparte con búsqueda y negociar, se
guarda con la partida y sale de la lista al ficharlo. También los traspasos con el mercado cerrado."""
import sys, os, random, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(7)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save, negociacion as N, traspasos_pendientes as TP, contraofertas as CO
from alpha_football.ui import buscador_screen as B, favoritos_screen as FV

save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402


def _tecla(k):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=''))


def _clic(pos):
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def test_marcar_en_el_buscador_y_lista():
    e = estado_carrera()
    pygame.event.clear(); B.render(screen, e)
    res = e['busq_resultados']
    _clic(B._rects()['favorito'].center); B.render(screen, e)
    assert N.es_favorito(e, res[0][0])
    N.alternar_favorito(e, res[3][0])
    assert [j for j, _c, _e in N.favoritos(e)] == [res[0][0], res[3][0]]
    _clic(B._rects()['favorito'].center); B.render(screen, e)          # otro clic lo quita
    assert not N.es_favorito(e, res[0][0])
    print("  test_marcar_en_el_buscador_y_lista: OK")


def test_se_guarda_con_la_partida():
    e = estado_carrera()
    j = N.pool_buscador(e)[5][0]
    N.alternar_favorito(e, j)
    e['datos_carrera'] = json.loads(json.dumps(e['datos_carrera']))
    assert [x.nombre_completo for x, _c, _e in N.favoritos(e)] == [j.nombre_completo]
    print("  test_se_guarda_con_la_partida: OK")


def test_pantalla_busca_quita_y_negocia():
    e = estado_carrera()
    pool = N.pool_buscador(e)
    a, b = pool[0][0], pool[10][0]
    N.alternar_favorito(e, a); N.alternar_favorito(e, b)
    pygame.event.clear(); assert FV.render(screen, e) is None
    FV._estado(e)['nombre'] = b.apellido[:4].lower()
    assert [j for j, _c, _e in FV.lista(e)] == [b]
    FV._estado(e)['nombre'] = ''
    _tecla(pygame.K_DELETE); FV.render(screen, e)                      # Supr quita al elegido
    assert not N.es_favorito(e, a) and N.es_favorito(e, b)
    e['mi_equipo'].balance = 10 ** 10
    _tecla(pygame.K_RETURN)
    assert FV.render(screen, e) == 'negociacion_screen' and e['neg']['jugador'] is b
    assert e['neg']['volver'] == 'favoritos_screen'
    print("  test_pantalla_busca_quita_y_negocia: OK")


def test_al_ficharlo_sale_de_favoritos():
    e = estado_carrera(); e['liga'].jornada_actual = 1           # mercado abierto: fichaje inmediato
    e['mi_equipo'].balance = 10 ** 10
    j, club, _et = next(x for x in N.pool_buscador(e) if x[1] is not None)
    N.alternar_favorito(e, j)
    ok, _msg = N.fichar(e, j, club, 1000)
    assert ok and j in e['mi_equipo'].jugadores and not N.es_favorito(e, j) and N.favoritos(e) == []
    print("  test_al_ficharlo_sale_de_favoritos: OK")


def test_mercado_cerrado_difiere_venta_y_compra():
    e = estado_carrera(); mi, liga = e['mi_equipo'], e['liga']
    liga.jornada_actual = 8; mi.balance = 10 ** 9
    vendido, comprador = mi.jugadores[5], liga.equipos[3]
    b0 = mi.balance
    assert CO.vender(e, {'jugador': vendido, 'comprador': comprador, 'monto': 10_000_000})
    assert vendido in mi.jugadores and mi.balance > b0                     # plata ya, jugador después
    club = liga.equipos[4]; fichado = club.jugadores[0]
    ok, msg = N.fichar(e, fichado, club, 5_000_000)
    assert ok and fichado in club.jugadores and fichado not in mi.jugadores and 'jornada' in msg
    assert N.fichar(e, fichado, club, 1)[0] is False                       # ya está acordado
    e['datos_carrera'] = json.loads(json.dumps(e['datos_carrera']))       # guardar / cargar
    e.pop('_compradores_pendientes', None)
    liga.jornada_actual = liga.num_jornadas - 2                            # se abre el mercado
    assert TP.ejecutar(e) == 2
    assert vendido not in mi.jugadores and any(x is vendido for x in comprador.jugadores)
    assert fichado in mi.jugadores and fichado not in club.jugadores
    asuntos = [m['asunto'] for m in e['datos_carrera']['correo']]
    assert any('ya se fue' in a for a in asuntos) and any('ha llegado' in a for a in asuntos)
    print("  test_mercado_cerrado_difiere_venta_y_compra: OK")


TESTS = [test_marcar_en_el_buscador_y_lista, test_se_guarda_con_la_partida, test_pantalla_busca_quita_y_negocia,
         test_al_ficharlo_sale_de_favoritos, test_mercado_cerrado_difiere_venta_y_compra]


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
