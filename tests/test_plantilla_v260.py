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


def test_liberar_jugador_paga_indemnizacion_y_corta_sueldo():
    from alpha_football.finanzas import masa_salarial
    from alpha_football.negociacion import indemnizacion_liberacion, liberar_jugador

    e = estado_carrera()
    mi = e['mi_equipo']
    j = mi.jugadores[0]
    j.salario, j.contrato_anios = 1_000_000, 2
    saldo, masa = mi.balance, masa_salarial(mi)

    assert indemnizacion_liberacion(j) == 1_000_000
    ok, _mensaje = liberar_jugador(e, j)

    assert ok
    assert j not in mi.jugadores
    assert j in e['free_agents_list'] and j.fin_de_contrato
    assert mi.balance == saldo - 1_000_000
    assert masa_salarial(mi) == masa - j.salario
    print("  test_liberar_jugador_paga_indemnizacion_y_corta_sueldo: OK")


def test_plantilla_pide_confirmacion_para_liberar():
    """v0.4.27.0: LIBERAR abre una ventana con la indemnización (antes: repetir L); CANCELAR / Esc la cierran sin
    liberar y CONFIRMAR / Enter liberan."""
    e = estado_carrera()
    mi = e['mi_equipo']
    j = mi.jugadores[0]
    j.salario, j.contrato_anios = 1_000_000, 2
    e['plantilla_sel'] = 0

    pygame.event.clear()
    plantilla_screen.render(screen, e)
    click(plantilla_screen._rects()['liberar'].center)
    plantilla_screen.render(screen, e)
    assert j in mi.jugadores                                   # la ventana está abierta, nadie se liberó
    assert e['plantilla_liberar_sel'] == j.id
    pygame.event.clear()
    assert plantilla_screen.render(screen, e) is None          # y se dibuja sin fallar

    rs = plantilla_screen.rects_overlay_liberar()
    click(rs['cancelar'].center)                               # CANCELAR
    plantilla_screen.render(screen, e)
    assert j in mi.jugadores and e.get('plantilla_liberar_sel') is None

    key(pygame.K_l)
    plantilla_screen.render(screen, e)
    assert e['plantilla_liberar_sel'] == j.id
    key(pygame.K_ESCAPE)                                       # Esc cierra la ventana, no la pantalla
    assert plantilla_screen.render(screen, e) is None
    assert j in mi.jugadores and e.get('plantilla_liberar_sel') is None

    click(plantilla_screen._rects()['liberar'].center)
    plantilla_screen.render(screen, e)
    click(rs['confirmar'].center)                              # CONFIRMAR
    plantilla_screen.render(screen, e)
    assert j not in mi.jugadores and j in e['free_agents_list'] and e.get('plantilla_liberar_sel') is None
    print("  test_plantilla_pide_confirmacion_para_liberar: OK")


def test_liberar_con_enter_y_sin_ventana_si_no_se_puede():
    """v0.4.27.0: Enter confirma la ventana; a un jugador a préstamo ni se le abre (el motivo sale directo)."""
    e = estado_carrera()
    mi = e['mi_equipo']
    j, prestado = mi.jugadores[0], mi.jugadores[1]
    e['plantilla_sel'] = 0
    pygame.event.clear()
    plantilla_screen.render(screen, e)
    key(pygame.K_l)
    plantilla_screen.render(screen, e)
    assert e['plantilla_liberar_sel'] == j.id
    key(pygame.K_RETURN)
    plantilla_screen.render(screen, e)
    assert j not in mi.jugadores and e.get('plantilla_liberar_sel') is None

    prestado.prestamo = {'dueno': "Otro Club", 'pct_dueno': 50, 'vuelve': [1, 10]}
    e['plantilla_sel'] = mi.jugadores.index(prestado)
    pygame.event.clear()
    plantilla_screen.render(screen, e)
    key(pygame.K_l)
    plantilla_screen.render(screen, e)
    assert e.get('plantilla_liberar_sel') is None and prestado in mi.jugadores
    assert "préstamo" in e['plantilla_liberar_msg'][0] and e['plantilla_liberar_msg'][1] == 'rojo'
    print("  test_liberar_con_enter_y_sin_ventana_si_no_se_puede: OK")


def test_liberar_publica_noticia_con_la_ficha_del_jugador():
    """v0.4.27.0 (O + C): liberar a tu jugador es noticia; guarda su id y su nombre para abrir la ficha desde NOTICIAS."""
    from alpha_football import noticias as N
    e = estado_carrera()
    mi = e['mi_equipo']
    j = mi.jugadores[0]
    j.salario, j.contrato_anios = 1_000_000, 1
    from alpha_football.negociacion import liberar_jugador
    ok, _m = liberar_jugador(e, j)
    assert ok
    libs = [n for n in N.lista(e) if n.get('liberacion')]
    assert len(libs) == 1 and libs[0]['propio'] and libs[0]['jugadores_ids'] == [j.id]
    assert libs[0]['jugadores_nombres'] == [j.nombre_completo] and N.etiqueta(libs[0]) == "LIBERADO"
    refs = N.jugadores_de(e, libs[0])                          # ya es agente libre: se encuentra por su nombre
    assert len(refs) == 1 and refs[0][0] is j and refs[0][1] == "Agente libre"
    print("  test_liberar_publica_noticia_con_la_ficha_del_jugador: OK")


TESTS = [test_ordenar_plantilla, test_alternar_transferible_baja_moral, test_guardado_transferible,
         test_transferibles_atraen_ofertas, test_pantalla_plantilla,
         test_liberar_jugador_paga_indemnizacion_y_corta_sueldo,
         test_plantilla_pide_confirmacion_para_liberar,
         test_liberar_con_enter_y_sin_ventana_si_no_se_puede,
         test_liberar_publica_noticia_con_la_ficha_del_jugador]


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
