"""Préstamos: sueldo repartido y protecciones (spec 2026-09-25-prestamos-design.md, Task 4)."""
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


def test_sueldo_repartido():
    from alpha_football import finanzas as F
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    antes = F.masa_salarial(mi, e)
    club = e['liga'].equipos[3]; entra = club.jugadores[10]
    P.iniciar(e, entra, club, mi, 6, 70)                       # tú pagas el 30%
    assert F.masa_salarial(mi, e) == antes + entra.salario * 30 // 100
    sale = sorted(mi.jugadores, key=lambda x: x.overall)[0]
    antes = F.masa_salarial(mi, e)
    P.iniciar(e, sale, mi, e['liga'].equipos[4], 6, 40)         # sigues pagando el 40%
    assert F.masa_salarial(mi, e) == antes - sale.salario + sale.salario * 40 // 100
    print("  test_sueldo_repartido: OK")


def test_protecciones():
    from alpha_football import contraofertas as CO, mercado_ia as MIA
    from alpha_football.ui.plantilla_screen import alternar_transferible
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    club = e['liga'].equipos[3]; j = club.jugadores[9]
    P.iniciar(e, j, club, mi, 12, 50)
    assert alternar_transferible(j) is False and not j.transferible
    e['ofertas_recibidas'] = [{'jugador': j, 'comprador': e['liga'].equipos[5], 'monto': 1_000_000}]
    assert CO.vender(e, e['ofertas_recibidas'][0]) is False
    P.limpiar_ofertas(e)
    assert e['ofertas_recibidas'] == []
    cedido = sorted(mi.jugadores, key=lambda x: x.overall)[0]
    destino = e['liga'].equipos[6]
    P.iniciar(e, cedido, mi, destino, 12, 50)
    while len(destino.jugadores) <= MIA.PLANTILLA_MAX_IA:
        destino.jugadores.append(Jugador(nombre='X', apellido=str(len(destino.jugadores)), posicion='DEF',
                                         ataque=30, defensa=30, fisico=30, tecnica=30, mental=30))
    cedido.ataque = cedido.defensa = cedido.fisico = cedido.tecnica = cedido.mental = 20
    MIA._liberar_sobrantes(destino)
    assert cedido in destino.jugadores                           # la IA no libera al cedido
    print("  test_protecciones: OK")


def test_contrato_vence_durante_la_cesion():
    from alpha_football import finanzas as F
    e = estado_carrera(); _abierto(e, 1); mi = e['mi_equipo']
    j = sorted(mi.jugadores, key=lambda x: x.overall)[0]
    destino = e['liga'].equipos[6]
    P.iniciar(e, j, mi, destino, 12, 50)
    j.contrato_anios = 1
    F.cierre_temporada(e)
    assert j.prestamo is None and j not in destino.jugadores and j not in mi.jugadores
    assert j in e.get('free_agents_list', [])                    # vuelve y se va libre
    print("  test_contrato_vence_durante_la_cesion: OK")


TESTS = [test_sueldo_repartido, test_protecciones, test_contrato_vence_durante_la_cesion]


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
