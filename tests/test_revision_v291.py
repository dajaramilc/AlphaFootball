"""v2.9.1: arreglos de la revisión final (ofertas viejas, despido persistente, historial propio,
cambio de club limpio, plantilla siempre con portero y reemplazos con contrato)."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(41)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save, directiva as D, finanzas as F, negociacion as N
from alpha_football.models import alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams, _ligas_por_division

save.guardar_en_slot = lambda *a, **k: None


def estado_carrera(tipo='premier', idx=0):
    liga = load_league_teams(tipo)
    mi = liga.equipos[idx]
    mi.alineacion_activa = alineacion_por_defecto(mi)
    primeras, segunda = _ligas_por_division(liga, {}, {})
    e = {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
         'alineacion_activa': mi.alineacion_activa, 'primera_division': primeras,
         'segunda_division': segunda, 'datos_carrera': {}, 'historial': []}
    F.asegurar_contratos(e)
    return e


def test_oferta_vieja_no_duplica_ni_cobra_dos_veces():
    from alpha_football.ui import ofertas_screen
    e = estado_carrera()
    mi = e['mi_equipo']
    jug = mi.jugadores[5]
    a, b = e['liga'].equipos[1], e['liga'].equipos[2]
    e['ofertas_recibidas'] = [{'jugador': jug, 'comprador': a, 'monto': 10_000_000},
                              {'jugador': jug, 'comprador': b, 'monto': 12_000_000}]
    bal = mi.balance
    ofertas_screen._aceptar(e, e['ofertas_recibidas'].pop(0))
    assert jug in a.jugadores and mi.balance == bal + 7_500_000   # v4.4.0: 25% para el club
    assert not e['ofertas_recibidas'], "las demás ofertas por ese jugador se descartan"
    ofertas_screen._aceptar(e, {'jugador': jug, 'comprador': b, 'monto': 12_000_000})
    assert jug not in b.jugadores and mi.balance == bal + 7_500_000
    print("  test_oferta_vieja_no_duplica_ni_cobra_dos_veces: OK")


def test_despido_sobrevive_a_guardar_y_bloquea_el_hub():
    from alpha_football.ui import league_screen
    e = estado_carrera()
    D.definir_objetivo(e)['pos_max'] = 1
    e['datos_carrera']['confianza'] = 5
    D.evaluar_temporada(e, 6)
    ids = [o.id for o in e['despido_pendiente']['opciones']]
    e.pop('despido_pendiente')                          # simula cerrar el juego y cargar
    assert e['datos_carrera']['despido_pendiente']['opciones_ids'] == ids
    pygame.event.clear()
    assert league_screen.render(screen, e) == 'despido_screen'
    assert [o.id for o in e['despido_pendiente']['opciones']] == ids
    D.cambiar_de_club(e, e['despido_pendiente']['opciones'][0])
    assert 'despido_pendiente' not in e['datos_carrera']
    print("  test_despido_sobrevive_a_guardar_y_bloquea_el_hub: OK")


def test_historial_propio_no_se_pierde():
    e = estado_carrera()
    j = e['mi_equipo'].jugadores[0]
    N.registrar_pase(e, j, 'Yo', 'Otro', 5, True)
    for _ in range(N.MAX_HISTORIAL + 50):
        N.registrar_pase(e, j, 'IA1', 'IA2', 1, False)
    assert len(N.historial(e, propio=True)) == 1
    assert len(N.historial(e, propio=False)) == N.MAX_HISTORIAL
    print("  test_historial_propio_no_se_pierde: OK")


def test_cambiar_de_club_limpia_lo_del_anterior():
    e = estado_carrera()
    viejo = e['mi_equipo']
    e['aviso_finanzas'] = "Saldo negativo..."
    e['datos_carrera']['jornadas_en_rojo'] = 2
    D.cambiar_de_club(e, D.opciones_de_club(e)[0])
    assert viejo.alineacion_activa is None and 'aviso_finanzas' not in e
    assert e['datos_carrera']['jornadas_en_rojo'] == 0
    # fichar de un club IA le resetea la alineación (índices corridos)
    mi = e['mi_equipo']; mi.balance = 10 ** 10
    j, club, _ = next((j, c, et) for j, c, et in N.pool_buscador(e) if c is not None and j.overall <= 70)
    club.alineacion_activa = alineacion_por_defecto(club)
    assert N.fichar(e, j, club)[0] and club.alineacion_activa is None
    print("  test_cambiar_de_club_limpia_lo_del_anterior: OK")


def test_plantilla_siempre_con_portero_y_reemplazos_con_contrato():
    e = estado_carrera()
    mi = e['mi_equipo']
    for j in mi.jugadores:
        j.contrato_anios = 1 if j.posicion == 'POR' else 3
    F.cierre_temporada(e)
    porteros = [j for j in mi.jugadores if j.posicion == 'POR']
    assert len(porteros) >= F.MINIMO_POR_POSICION['POR']
    assert all(j.salario > 0 and j.contrato_anios >= 1 for j in mi.jugadores)
    F.cierre_temporada(e)                              # los reemplazos no se van en el cierre siguiente
    assert len([j for j in mi.jugadores if j.posicion == 'POR']) >= F.MINIMO_POR_POSICION['POR']
    print("  test_plantilla_siempre_con_portero_y_reemplazos_con_contrato: OK")


TESTS = [test_oferta_vieja_no_duplica_ni_cobra_dos_veces, test_despido_sobrevive_a_guardar_y_bloquea_el_hub,
         test_historial_propio_no_se_pierde, test_cambiar_de_club_limpia_lo_del_anterior,
         test_plantilla_siempre_con_portero_y_reemplazos_con_contrato]


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
