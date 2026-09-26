"""Mercado de invierno (J n/2 a n/2+2), ofertas en análisis sin ACEPTAR/RECHAZAR y renovación del
DT con disculpas si la directiva te la negó pero lograste un hito (título, ascenso o copa)."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(11)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save, market as M, traspasos_pendientes as TP, carrera_dt as CD, correo as C
from alpha_football.ui import aviso_mercado as AM, ofertas_screen as OS

save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402


def test_ventanas_con_invierno():
    assert M.ventanas_mercado(22) == [(1, 3, 'inicio'), (11, 13, 'invierno'), (20, 22, 'cierre')]
    abiertas = [j for j in range(1, 23) if M.ventana_mercado_abierta(j, 22)]
    assert abiertas == [1, 2, 3, 11, 12, 13, 20, 21, 22]
    assert AM.eventos_ventana(22) == {1: 'abre', 4: 'cierra', 11: 'abre', 14: 'cierra', 20: 'abre'}
    e = estado_carrera(); e['liga'].jornada_actual = 8
    assert TP.jornada_apertura(e) == 11                  # acordado en J8 → llega en el invierno
    e['liga'].jornada_actual = 15
    assert TP.jornada_apertura(e) == 20
    print("  test_ventanas_con_invierno: OK")


def test_cartel_de_invierno():
    e = estado_carrera(); n = e['liga'].num_jornadas
    e['liga'].jornada_actual = n // 2
    AM.manejar(e, [], None)
    assert e['aviso_mercado_activo']['tipo'] == 'abre'
    assert any(f"Hasta la jornada {n // 2 + 2}" in m['cuerpo'] for m in C.bandeja(e))
    e['aviso_mercado_activo'] = None; e['liga'].jornada_actual = n // 2 + 3
    AM.manejar(e, [], None)
    assert e['aviso_mercado_activo']['tipo'] == 'cierra'
    assert any(f"Reabre en la jornada {n - 2}" in m['cuerpo'] for m in C.bandeja(e))
    print("  test_cartel_de_invierno: OK")


def test_oferta_en_analisis_no_se_acepta_ni_rechaza():
    e = estado_carrera(); mi = e['mi_equipo']
    j, comp = mi.jugadores[4], e['liga'].equipos[2]
    of = {'jugador': j, 'comprador': comp, 'monto': 5_000_000,
          'contra': {'pedido': 7_000_000, 'estado': 'analizando', 'jornada': 1}}
    e['ofertas_recibidas'] = [of]
    for k in (pygame.K_a, pygame.K_r):
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=''))
        OS.render(screen, e)
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=OS.R_ACEPTAR.center))
    OS.render(screen, e)
    assert e['ofertas_recibidas'] == [of] and j in mi.jugadores
    print("  test_oferta_en_analisis_no_se_acepta_ni_rechaza: OK")


def _negada(e):
    t = int(e.get('temporada', 1))
    e['datos_carrera']['contrato_dt'] = {'club': e['mi_equipo'].nombre, 'desde': t, 'hasta': t,
                                         'sueldo': 1_000_000, 'indemnizacion': 0}
    e['datos_carrera']['renovacion_dt'] = {'temporada': t, 'estado': 'negada'}


def test_hito_trae_renovacion_con_disculpa():
    e = estado_carrera(); _negada(e)
    assert not CD.revisar_renovacion_por_hito(e)                        # sin hito: nada
    liga, mi = e['liga'], e['mi_equipo']
    from alpha_football.ui.league_screen import inicializar_calendario_liga
    inicializar_calendario_liga(liga)
    assert not CD.revisar_renovacion_por_hito(e)                        # calendario sin jugar: tampoco
    for p in liga.calendario:
        p.jugado = True
    for eq in liga.equipos:
        eq.puntos = 10
    mi.puntos = 60                                                      # campeón
    assert CD.hito_temporada(e) == "campeón de liga"
    assert CD.revisar_renovacion_por_hito(e)
    r = e['datos_carrera']['renovacion_dt']
    assert r['estado'] == 'ofrecida' and r.get('disculpa')
    assert C.bandeja(e)[0]['asunto'].startswith("Te pedimos disculpas")
    assert not CD.revisar_renovacion_por_hito(e)                        # una sola vez
    from alpha_football.ui.contrato_dt_screen import modo
    assert modo(e) == 'renovacion'
    print("  test_hito_trae_renovacion_con_disculpa: OK")


def test_copa_campeon_tambien_cuenta():
    e = estado_carrera(); _negada(e)
    e['copa_mejor_fase_temp'] = 'Campeón'
    assert CD.hito_temporada(e) and CD.revisar_renovacion_por_hito(e)
    print("  test_copa_campeon_tambien_cuenta: OK")


def _fin_de_contrato(estado_ren):
    from alpha_football import directiva as D
    e = estado_carrera(); t = int(e.get('temporada', 1))
    e['datos_carrera']['contrato_dt'] = {'club': e['mi_equipo'].nombre, 'desde': t, 'hasta': t, 'sueldo': 1_000_000}
    if estado_ren:
        e['datos_carrera']['renovacion_dt'] = {'temporada': t, 'estado': estado_ren}
    D.evaluar_temporada(e, 1)                                          # campeón: nada de despido
    return e


def test_fin_de_contrato_con_oferta_permite_renovar():
    from alpha_football.ui import despido_screen as DS, contrato_dt_screen as CS
    e = _fin_de_contrato('ofrecida'); t = int(e.get('temporada', 1))
    pend = e['despido_pendiente']
    assert pend['titulo'] == "FIN DE CONTRATO" and pend['renovable'] and DS.items(pend)[0] == DS.RENOVAR
    assert e['datos_carrera']['despido_pendiente']['renovable']        # se guarda con la partida
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=DS._rects_opciones(len(DS.items(pend)))[0].center))
    assert DS.render(screen, e) == 'contrato_dt_screen' and e['contrato_modo'] == 'renovacion'
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=CS.R_RECHAZAR.center))
    assert CS.render(screen, e) == 'despido_screen' and not e['despido_pendiente']['renovable']   # rechazó: otras ofertas
    e['despido_pendiente']['renovable'] = True
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=DS._rects_opciones(len(DS.items(pend)))[0].center))
    DS.render(screen, e)
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=CS._rects(3)[0].center))
    assert CS.render(screen, e) in ('league_screen', 'promo_releg_screen')
    assert 'despido_pendiente' not in e and 'despido_pendiente' not in e['datos_carrera']
    assert CD.contrato(e)['hasta'] > t and CD.contrato(e)['club'] == e['mi_equipo'].nombre
    print("  test_fin_de_contrato_con_oferta_permite_renovar: OK")


def test_fin_de_contrato_sin_oferta_solo_otros_clubes():
    from alpha_football.ui import despido_screen as DS
    for ren in (None, 'negada', 'rechazada'):
        e = _fin_de_contrato(ren)
        pend = e['despido_pendiente']
        assert not pend.get('renovable') and DS.RENOVAR not in DS.items(pend)
    print("  test_fin_de_contrato_sin_oferta_solo_otros_clubes: OK")


TESTS = [test_ventanas_con_invierno, test_cartel_de_invierno, test_oferta_en_analisis_no_se_acepta_ni_rechaza,
         test_hito_trae_renovacion_con_disculpa, test_copa_campeon_tambien_cuenta,
         test_fin_de_contrato_con_oferta_permite_renovar, test_fin_de_contrato_sin_oferta_solo_otros_clubes]


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
