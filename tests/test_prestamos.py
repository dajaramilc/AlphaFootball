"""Préstamos (spec 2026-09-25-prestamos-design.md)."""
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


def test_regreso_por_ventana():
    e = estado_carrera(); n = e['liga'].num_jornadas            # 22: ventanas 1-3, 11-13, 20-22
    _abierto(e, 2)
    assert P.regreso(e, 6) == [1, 11] and P.regreso(e, 12) == [2, 1]
    _abierto(e, 12)
    assert P.regreso(e, 6) == [1, n - 2] and P.regreso(e, 12) == [2, 11]
    _abierto(e, 21)
    assert P.regreso(e, 6) == [2, 11]
    _abierto(e, 8)                                              # cerrado: empieza en el invierno
    assert P.regreso(e, 6) == [1, n - 2]
    print("  test_regreso_por_ventana: OK")


def test_ida_y_vuelta_con_mercado_abierto():
    e = estado_carrera(); _abierto(e, 1)
    mi, club = e['mi_equipo'], e['liga'].equipos[3]
    j = club.jugadores[10]
    txt = P.iniciar(e, j, club, mi, 6, 40)
    assert j in mi.jugadores and j not in club.jugadores and 'préstamo' in txt
    assert j.prestamo['dueno'] == club.nombre and j.prestamo['pct_dueno'] == 40
    assert P.entrantes(e) == [j]
    e['liga'].jornada_actual = 11                                # llega el invierno
    P.revisar_jornada(e)
    assert j in club.jugadores and j not in mi.jugadores and j.prestamo is None
    assert any('vuelve' in m['asunto'].lower() or 'volvió' in m['asunto'].lower() for m in C.bandeja(e))
    print("  test_ida_y_vuelta_con_mercado_abierto: OK")


def test_acordado_con_mercado_cerrado_espera_la_ventana():
    e = estado_carrera(); _abierto(e, 6)
    mi, club = e['mi_equipo'], e['liga'].equipos[4]
    j = club.jugadores[9]
    txt = P.iniciar(e, j, club, mi, 6, 50)
    assert j in club.jugadores and 'jornada 11' in txt
    e['datos_carrera'] = json.loads(json.dumps(e['datos_carrera']))    # guardar / cargar
    e['liga'].jornada_actual = 11
    P.revisar_jornada(e)
    assert j in mi.jugadores and j.prestamo['vuelve'] == [1, e['liga'].num_jornadas - 2]
    print("  test_acordado_con_mercado_cerrado_espera_la_ventana: OK")


def test_terminar_antes():
    e = estado_carrera(); _abierto(e, 1)
    mi, club = e['mi_equipo'], e['liga'].equipos[5]
    j = club.jugadores[8]
    P.iniciar(e, j, club, mi, 12, 50)
    e['liga'].jornada_actual = 5                                 # cerrado → vuelve en la próxima ventana
    assert 'jornada 11' in P.terminar(e, j) and j in mi.jugadores
    e['liga'].jornada_actual = 11
    P.revisar_jornada(e)
    assert j in club.jugadores and j.prestamo is None
    j2 = club.jugadores[7]
    P.iniciar(e, j2, club, mi, 12, 50)                           # abierto → vuelve ya
    P.terminar(e, j2)
    assert j2 in club.jugadores and j2.prestamo is None
    print("  test_terminar_antes: OK")


def test_prestamo_se_guarda_en_el_jugador():
    e = estado_carrera(); _abierto(e, 1)
    club = e['liga'].equipos[3]; j = club.jugadores[6]
    P.iniciar(e, j, club, e['mi_equipo'], 6, 30)
    copia = Jugador.from_dict(json.loads(json.dumps(j.to_dict())))
    assert copia.prestamo == j.prestamo
    assert Jugador.from_dict({'nombre': 'A', 'apellido': 'B'}).prestamo is None   # saves viejos
    print("  test_prestamo_se_guarda_en_el_jugador: OK")


def test_dueno_desaparecido_queda_libre():
    e = estado_carrera(); _abierto(e, 1)
    mi, club = e['mi_equipo'], e['liga'].equipos[6]
    j = club.jugadores[5]
    P.iniciar(e, j, club, mi, 6, 50)
    j.prestamo['dueno'] = 'Club Que No Existe'
    P.terminar(e, j)
    assert j not in mi.jugadores and j in e.get('free_agents_list', []) and j.prestamo is None
    print("  test_dueno_desaparecido_queda_libre: OK")


def test_vuelve_al_empezar_la_temporada():
    from alpha_football.ui.resumen_temporada_screen import avanzar_nueva_temporada
    e = estado_carrera(); _abierto(e, 2); mi = e['mi_equipo']
    club = e['liga'].equipos[3]; j = club.jugadores[10]
    P.iniciar(e, j, club, mi, 12, 50)                           # vuelve en J1 de la T2
    for p in getattr(e['liga'], 'calendario', []) or []:
        p.jugado = True
    avanzar_nueva_temporada(e)
    assert e['temporada'] == 2 and j.prestamo is None and any(x is j for x in club.jugadores)
    print("  test_vuelve_al_empezar_la_temporada: OK")


def test_plantilla_lista_y_concluir():
    from alpha_football.ui import plantilla_screen as PS
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    club = e['liga'].equipos[3]; j = club.jugadores[10]
    P.iniciar(e, j, club, mi, 12, 50)
    pygame.event.clear(); PS.render(screen, e)
    idx = mi.jugadores.index(j); e['plantilla_sel'] = idx
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=PS._rects()['prestamos'].center))
    PS.render(screen, e)
    assert e.get('prestamos_abierto')
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=PS.rects_overlay_prestamos(1)[0][1].center))
    PS.render(screen, e)
    assert j.prestamo is None and j in club.jugadores           # mercado abierto: vuelve ya
    otro = sorted(mi.jugadores, key=lambda x: x.overall)[0]
    e['plantilla_sel'] = mi.jugadores.index(otro); e['prestamos_abierto'] = False
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p, mod=0, unicode='p'))
    PS.render(screen, e)
    assert P.en_lista(e, otro)
    print("  test_plantilla_lista_y_concluir: OK")


def test_ia_no_oferta_por_jugadores_a_prestamo():
    from alpha_football import market as M
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    for j in mi.jugadores:                                     # toda la plantilla a préstamo
        j.prestamo = {'dueno': 'Otro', 'club': mi.nombre, 'pct_dueno': 50, 'vuelve': [2, 1], 'meses': 12}
        j.transferible = True
    siempre = random.Random(1); siempre.random = lambda: 0.0
    rivales = [x for x in e['liga'].equipos if x is not mi]
    assert M.crear_oferta_ui(mi, rivales, 1, e['liga'].num_jornadas, rng=siempre) is None
    assert M.crear_oferta_exterior(mi, e, rng=siempre, prob=1.0) is None
    print("  test_ia_no_oferta_por_jugadores_a_prestamo: OK")


def _relleno(mi, hasta):
    while len(mi.jugadores) < hasta:
        mi.jugadores.append(Jugador(nombre='Relleno', apellido=str(len(mi.jugadores)), posicion='MED',
                                    ataque=50, defensa=50, fisico=50, tecnica=50, mental=50))


def test_clubes_internacionales_no_prestan_ni_reciben():
    # revisión final #1: el pool internacional no se guarda → el jugador se perdería/duplicaría
    from alpha_football import negociacion as N
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    intl = N.clubes_internacionales(e)
    assert intl, "hace falta el pool internacional"
    club = intl[0][0]
    j = sorted(club.jugadores, key=lambda x: x.overall)[0]
    assert P.evaluar_pedido(e, j, club, 6, 100)[0] == 'rechaza'
    ced = sorted(mi.jugadores, key=lambda x: x.overall)[0]
    P.alternar_lista(e, ced)
    azar = random.Random(7); azar.random = lambda: 0.0
    for _ in range(80):
        e['ofertas_recibidas'] = []
        for of in P.generar_ofertas(e, azar):
            assert not N.es_club_internacional(of['comprador']), of['comprador'].nombre
    print("  test_clubes_internacionales_no_prestan_ni_reciben: OK")


def test_no_se_compra_a_uno_a_prestamo():
    # revisión final #3: comprar a tu propio cedido (o a uno a préstamo) no debe ser posible
    from alpha_football import negociacion as N
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    ced = sorted(mi.jugadores, key=lambda x: x.overall)[0]
    destino = e['liga'].equipos[6]
    P.iniciar(e, ced, mi, destino, 12, 50)
    assert N.evaluar_compra(e, ced, destino, 10 ** 10)[0] == 'rechaza'
    ok, _msg = N.fichar(e, ced, destino, precio=1)
    assert not ok and ced in destino.jugadores
    assert P.evaluar_pedido(e, ced, destino, 6, 100)[0] == 'rechaza'
    print("  test_no_se_compra_a_uno_a_prestamo: OK")


def test_tope_de_plantilla_cuenta_los_pendientes():
    # revisión final #4: con el mercado cerrado los acordados cuentan para el tope de 40
    from alpha_football.market import PLANTILLA_MAXIMA
    e = estado_carrera(); _abierto(e, 6); mi = e['mi_equipo']
    _relleno(mi, PLANTILLA_MAXIMA - 1)
    club = e['liga'].equipos[2]
    a, b = sorted(club.jugadores, key=lambda x: x.overall)[:2]
    assert P.cerrar_pedido(e, a, club, 6, 100)[0]
    ok, msg = P.cerrar_pedido(e, b, club, 6, 100)
    assert not ok and 'Plantilla llena' in msg
    _relleno(mi, PLANTILLA_MAXIMA)                               # se llenó mientras esperaba
    e['liga'].jornada_actual = 11
    P.revisar_jornada(e)
    assert len(mi.jugadores) == PLANTILLA_MAXIMA and a in club.jugadores
    print("  test_tope_de_plantilla_cuenta_los_pendientes: OK")


def test_prestamo_pendiente_llega_antes_que_la_ia():
    # revisión final #2: al abrir la ventana el préstamo acordado se concreta antes del mercado de la IA
    from alpha_football import mercado_ia as MIA
    from alpha_football.ui import match_screen as MS
    from alpha_football.ui.league_screen import inicializar_calendario_liga
    e = estado_carrera(); liga, mi = e['liga'], e['mi_equipo']
    inicializar_calendario_liga(liga)
    _abierto(e, 10)
    club = liga.equipos[4]; j = club.jugadores[9]
    P.iniciar(e, j, club, mi, 6, 50)                              # cerrado: llega en J11
    visto = {}
    orig = MIA.ronda_fichajes_ia
    MIA.ronda_fichajes_ia = lambda *a, **k: visto.setdefault('ya_llego', j in mi.jugadores)
    try:
        p = next(x for x in liga.calendario if x.jornada == 10 and mi.id in (x.local_id, x.visitante_id))
        MS.finalizar_jornada_liga(e, liga, mi, p, 1, 0)
    finally:
        MIA.ronda_fichajes_ia = orig
    assert liga.jornada_actual == 11 and visto.get('ya_llego') is True, visto
    print("  test_prestamo_pendiente_llega_antes_que_la_ia: OK")


TESTS = [test_regreso_por_ventana, test_ida_y_vuelta_con_mercado_abierto,
         test_acordado_con_mercado_cerrado_espera_la_ventana, test_terminar_antes,
         test_prestamo_se_guarda_en_el_jugador, test_dueno_desaparecido_queda_libre,
         test_vuelve_al_empezar_la_temporada, test_plantilla_lista_y_concluir,
         test_ia_no_oferta_por_jugadores_a_prestamo, test_clubes_internacionales_no_prestan_ni_reciben,
         test_no_se_compra_a_uno_a_prestamo, test_tope_de_plantilla_cuenta_los_pendientes,
         test_prestamo_pendiente_llega_antes_que_la_ia]


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
