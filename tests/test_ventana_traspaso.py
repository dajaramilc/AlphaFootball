"""Un jugador traspasado no puede volver a cambiar de club en la misma ventana (sí a préstamo)."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(21)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save
from alpha_football.models import Jugador, alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams, _ligas_por_division
from alpha_football.market import clave_ventana_traspaso, traspasado_en_ventana
from alpha_football import negociacion as N

save.guardar_en_slot = lambda *a, **k: None          # los tests no tocan los slots reales


def estado_carrera(tipo='premier', idx=0):
    liga = load_league_teams(tipo)
    mi = liga.equipos[idx]
    mi.alineacion_activa = alineacion_por_defecto(mi)
    primeras, segunda = _ligas_por_division(liga, {}, {})
    return {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
            'alineacion_activa': mi.alineacion_activa, 'primera_division': primeras,
            'segunda_division': segunda, 'datos_carrera': {}, 'historial': []}


def test_clave_ventana():
    n = 22
    assert clave_ventana_traspaso(1, 2, n) == '1-verano'
    assert clave_ventana_traspaso(1, 11, n) == '1-invierno'
    assert clave_ventana_traspaso(1, 21, n) == ''               # v0.4.11.0: ya no hay ventana de cierre
    assert clave_ventana_traspaso(1, 7, n) == ''               # mercado cerrado
    print("  test_clave_ventana: OK")


def test_marca_persiste():
    j = Jugador("N", "X", "MED", 70, 70, 70, 70, 70)
    j.ventana_traspaso = '3-invierno'
    assert Jugador.from_dict(j.to_dict()).ventana_traspaso == '3-invierno'
    d = j.to_dict(); d.pop('ventana_traspaso')
    assert Jugador.from_dict(d).ventana_traspaso == ''        # save viejo
    print("  test_marca_persiste: OK")


def test_ia_no_revende_en_la_misma_ventana():
    e = estado_carrera()
    e['liga'].jornada_actual = 1
    from alpha_football.mercado_ia import ronda_fichajes_ia
    for eq in e['liga'].equipos:
        eq.balance = 10**10
    for _ in range(5):
        ronda_fichajes_ia(e, 'pretemporada', random.Random(_))
    pases = [h for h in e['datos_carrera']['historial_pases'] if not h['propio']]
    assert pases, "la IA debería fichar algo"
    # nadie cambió de club dos veces en la ventana
    nombres = [h['jugador'] for h in pases]
    assert len(nombres) == len(set(nombres)), [n for n in nombres if nombres.count(n) > 1]
    print("  test_ia_no_revende_en_la_misma_ventana: OK")


def test_user_no_compra_recien_traspasado_pero_si_en_otra_ventana():
    e = estado_carrera()
    e['liga'].jornada_actual = 2
    club = e['liga'].equipos[3]
    j = club.jugadores[5]
    N.registrar_pase(e, j, 'Otro', club.nombre, 1000, False)
    assert traspasado_en_ventana(e, j)
    resp, msg, _ = N.evaluar_compra(e, j, club, 10**9)
    assert resp == 'rechaza' and 'préstamo' in msg
    e['mi_equipo'].balance = 10**10
    ok, msg = N.fichar(e, j, club, 1000)
    assert not ok and j in club.jugadores
    e['liga'].jornada_actual = 11                              # invierno: ya puede
    assert not traspasado_en_ventana(e, j)
    assert N.evaluar_compra(e, j, club, 10**9)[0] == 'acepta'
    print("  test_user_no_compra_recien_traspasado_pero_si_en_otra_ventana: OK")


def test_recien_llegado_no_recibe_ofertas():
    e = estado_carrera()
    e['liga'].jornada_actual = 2
    mi = e['mi_equipo']
    j = mi.jugadores[0]
    N.registrar_pase(e, j, 'Otro', mi.nombre, 1000, True)
    comprador = e['liga'].equipos[4]
    from alpha_football.contraofertas import vender
    assert not vender(e, {'jugador': j, 'comprador': comprador, 'monto': 5000})
    assert j in mi.jugadores
    from alpha_football.salidas import ofertas_garantizadas
    j.pide_salir = True
    ofertas_garantizadas(e, random.Random(1))
    assert not any(o.get('jugador') is j for o in e.get('ofertas_recibidas') or [])
    print("  test_recien_llegado_no_recibe_ofertas: OK")


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
