"""Préstamos: pedir a préstamo y ceder (spec 2026-09-25-prestamos-design.md)."""
import sys, os, random, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(5)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save, prestamos as P, correo as C
from alpha_football.models import Jugador

save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402


def _abierto(e, j=1):
    e['liga'].jornada_actual = j


def test_pedido_reglas_del_club():
    e = estado_carrera(); _abierto(e, 1)
    club = e['liga'].equipos[2]
    top = sorted(club.jugadores, key=lambda x: -x.overall)[0]
    assert P.evaluar_pedido(e, top, club, 6, 100)[0] == 'rechaza'           # pieza clave
    from alpha_football.formaciones import mejor_once
    tit = {club.jugadores[i].nombre_completo for i in mejor_once(club.jugadores, "4-3-3")}
    top3 = {x.nombre_completo for x in sorted(club.jugadores, key=lambda x: -x.overall)[:3]}
    sup = next(x for x in club.jugadores if x.nombre_completo not in tit | top3)
    assert P.evaluar_pedido(e, sup, club, 6, 30)[0] == 'acepta'
    assert P.evaluar_pedido(e, sup, club, 6, 10)[0] == 'analiza'
    assert e['datos_carrera']['analisis_prestamos'][-1]['jugador'] == sup.nombre_completo
    titular = next(x for x in club.jugadores if x.nombre_completo in tit and x.nombre_completo not in top3)
    assert P.evaluar_pedido(e, titular, club, 6, 30)[0] == 'rechaza'
    assert P.evaluar_pedido(e, titular, club, 6, 60)[0] == 'acepta'
    print("  test_pedido_reglas_del_club: OK")


def test_analisis_se_resuelve_la_jornada_siguiente():
    e = estado_carrera(); _abierto(e, 1)
    club = e['liga'].equipos[2]
    from alpha_football.formaciones import mejor_once
    tit = {club.jugadores[i].nombre_completo for i in mejor_once(club.jugadores, "4-3-3")}
    top3 = {x.nombre_completo for x in sorted(club.jugadores, key=lambda x: -x.overall)[:3]}
    sup = next(x for x in club.jugadores if x.nombre_completo not in tit | top3)   # suplente: mínimo 30%
    assert P.evaluar_pedido(e, sup, club, 6, 10)[0] == 'analiza'
    class Si: random = staticmethod(lambda: 0.0)
    P.resolver_analisis(e, Si())                                # misma jornada: nada
    assert sup in club.jugadores
    e['liga'].jornada_actual = 2
    P.resolver_analisis(e, Si())
    assert sup in e['mi_equipo'].jugadores and sup.prestamo['pct_dueno'] == 90
    print("  test_analisis_se_resuelve_la_jornada_siguiente: OK")


def test_plantilla_llena_no_pide():
    e = estado_carrera(); _abierto(e, 1)
    from alpha_football.market import PLANTILLA_MAXIMA
    mi, club = e['mi_equipo'], e['liga'].equipos[2]
    while len(mi.jugadores) < PLANTILLA_MAXIMA:
        mi.jugadores.append(Jugador(nombre='Relleno', apellido=str(len(mi.jugadores)), posicion='MED',
                                    ataque=50, defensa=50, fisico=50, tecnica=50, mental=50))
    ok, msg = P.cerrar_pedido(e, sorted(club.jugadores, key=lambda x: x.overall)[0], club, 6, 100)
    assert not ok and 'Plantilla llena' in msg and len(mi.jugadores) == PLANTILLA_MAXIMA
    print("  test_plantilla_llena_no_pide: OK")


def test_ui_pedir_prestamo_desde_el_buscador():
    from alpha_football.ui import buscador_screen as B, negociacion_screen as NS
    e = estado_carrera(); _abierto(e, 1)
    pygame.event.clear(); B.render(screen, e)
    k, (j, club, _et) = next((i, x) for i, x in enumerate(e['busq_resultados']) if x[1] is not None)
    e['busq']['sel'] = k
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=B._rects()['prestamo'].center))
    assert B.render(screen, e) == 'negociacion_screen'
    neg = e['neg']
    assert neg['modo'] == 'prestamo' and neg['etapa'] == 'club' and neg['meses'] == 6 and neg['pct'] == 50
    pygame.event.clear(); assert NS.render(screen, e) is None
    print("  test_ui_pedir_prestamo_desde_el_buscador: OK")


def test_lista_y_ofertas_de_prestamo():
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    j = sorted(mi.jugadores, key=lambda x: x.overall)[0]
    assert P.alternar_lista(e, j) and P.en_lista(e, j)
    siempre = random.Random(3); siempre.random = lambda: 0.0      # siempre hay oferta
    nuevas = P.generar_ofertas(e, siempre)
    assert len(nuevas) == 1 and nuevas[0]['prestamo']['meses'] in (6, 12) and nuevas[0] in e['ofertas_recibidas']
    assert P.generar_ofertas(e, siempre) == []                   # no repite mientras haya una pendiente
    of = nuevas[0]
    P.aceptar_oferta(e, of)
    assert j not in mi.jugadores and j in of['comprador'].jugadores
    assert j.prestamo['dueno'] == mi.nombre and j.prestamo['pct_dueno'] == 100 - of['prestamo']['pct_ellos']
    assert not P.en_lista(e, j) and of not in e['ofertas_recibidas']
    e['liga'].jornada_actual = 5
    assert P.generar_ofertas(e, siempre) == []                   # mercado cerrado: sin ofertas
    print("  test_lista_y_ofertas_de_prestamo: OK")


def test_contraoferta_de_prestamo():
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    j = sorted(mi.jugadores, key=lambda x: x.overall)[1]
    comp = e['liga'].equipos[7]
    of = {'jugador': j, 'comprador': comp, 'monto': 0, 'prestamo': {'meses': 6, 'pct_ellos': 40}, 'tope_pct': 60}
    e['ofertas_recibidas'] = [of]
    assert P.contraofertar(e, of, 30)[0] == 'invalida'
    assert P.contraofertar(e, of, 70)[0] == 'analizando' and of['contra']['estado'] == 'analizando'
    class Si: random = staticmethod(lambda: 0.0)
    e['liga'].jornada_actual = 2
    P.resolver_analisis(e, Si())
    assert j in comp.jugadores and j.prestamo['pct_dueno'] == 30
    of2 = {'jugador': mi.jugadores[3], 'comprador': comp, 'monto': 0, 'prestamo': {'meses': 12, 'pct_ellos': 50}, 'tope_pct': 50}
    e['ofertas_recibidas'] = [of2]
    assert P.contraofertar(e, of2, 90)[0] == 'rechazada' and of2 not in e['ofertas_recibidas']
    print("  test_contraoferta_de_prestamo: OK")


def test_ofertas_screen_prestamo():
    from alpha_football.ui import ofertas_screen as OS
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    j = sorted(mi.jugadores, key=lambda x: x.overall)[2]
    comp = e['liga'].equipos[8]
    e['ofertas_recibidas'] = [{'jugador': j, 'comprador': comp, 'monto': 0, 'prestamo': {'meses': 6, 'pct_ellos': 60}}]
    pygame.event.clear(); OS.render(screen, e)
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, mod=0, unicode='a'))
    OS.render(screen, e)
    assert j in comp.jugadores and j.prestamo['pct_dueno'] == 40
    print("  test_ofertas_screen_prestamo: OK")


TESTS = [test_pedido_reglas_del_club, test_analisis_se_resuelve_la_jornada_siguiente,
         test_plantilla_llena_no_pide, test_ui_pedir_prestamo_desde_el_buscador,
         test_lista_y_ofertas_de_prestamo, test_contraoferta_de_prestamo, test_ofertas_screen_prestamo]


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
