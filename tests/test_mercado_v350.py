"""v3.5.0: mercado y negociación — contraofertas, "lo analizamos", montos exactos, rivalidad, contrato por vencer."""
import sys, os, random, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(13)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save
from alpha_football import market as M, negociacion as N, correo as C
from alpha_football.models import alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams, _ligas_por_division

_tmp = tempfile.mkdtemp()
save.guardar_en_slot = lambda *a, **k: None          # los tests no tocan los slots reales


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


class RngFijo(random.Random):
    def __init__(self, v): super().__init__(1); self.v = v
    def random(self): return self.v


# --- Task 1: precios ──────────────────────────────────────────────────────────

def test_dinero_exacto():
    assert N.dinero_exacto(12_345_000) == "$12,345,000" and N.dinero_exacto(0) == "$0"
    print("  test_dinero_exacto: OK")


def test_factor_contrato():
    e = estado_carrera(); j = e['mi_equipo'].jugadores[3]
    j.contrato_anios = 1; assert M.factor_contrato(j) == 0.75
    base = int(M.precio_compra(j))
    assert N.precio_fichaje(j) == int(base * 0.75)
    j.contrato_anios = 2; assert M.factor_contrato(j) == 1.0 and N.precio_fichaje(j) == base
    j.contrato_anios = 0; assert M.factor_contrato(j) == 1.0
    print("  test_factor_contrato: OK")


def test_oferta_ia_con_descuento_contrato():
    e = estado_carrera(); mi = e['mi_equipo']
    for j in mi.jugadores: j.contrato_anios = 1
    rivales = [x for x in e['liga'].equipos if x is not mi]
    for r in rivales: r.balance = 10**10
    of = M.crear_oferta_ui(mi, rivales, 1, 10, rng=RngFijo(0.0))
    assert of and of['monto'] == int(of['jugador'].valor * 0.95 * 0.75)
    print("  test_oferta_ia_con_descuento_contrato: OK")


def test_clasico_no_oferta_salvo_moral_baja():
    e = estado_carrera(); mi = e['mi_equipo']; rival = e['liga'].equipos[1]
    mi.rival, rival.rival = rival.nombre, mi.nombre
    rival.balance = 10**10
    for j in mi.jugadores: j.moral = 70; j.transferible = False
    assert M.crear_oferta_ui(mi, [rival], 1, 10, rng=RngFijo(0.0)) is None
    for j in mi.jugadores: j.moral = 30
    assert M.crear_oferta_ui(mi, [rival], 1, 10, rng=RngFijo(0.0)) is not None
    print("  test_clasico_no_oferta_salvo_moral_baja: OK")


def test_exterior_mas_ofertas_y_top3():
    import inspect
    assert inspect.signature(M.crear_oferta_exterior).parameters['prob'].default == 0.25
    e = estado_carrera(); mi = e['mi_equipo']
    for j in mi.jugadores: j.promedio_nota = 0.0; j.goles = j.asistencias = 0
    of = M.crear_oferta_exterior(mi, e, rng=RngFijo(0.0))
    top3 = sorted(mi.jugadores, key=lambda j: -j.overall)[:3]
    assert of and of['jugador'] in top3 and of['exterior']
    print("  test_exterior_mas_ofertas_y_top3: OK")


# --- Task 2: contraofertas (ventas) y análisis de compras ─────────────────────

from alpha_football import contraofertas as CO


def _oferta(e, monto=10_000_000, exterior=False, balance=10**9):
    mi = e['mi_equipo']; j = mi.jugadores[5]; comp = e['liga'].equipos[1]; comp.balance = balance
    of = {'jugador': j, 'comprador': comp, 'monto': monto}
    if exterior: of['exterior'] = True
    e['ofertas_recibidas'] = [of]
    return of


def test_tope():
    e = estado_carrera(); of = _oferta(e)
    t = CO.asignar_tope(of, random.Random(1))
    assert 11_000_000 <= t <= 13_500_000 and CO.asignar_tope(of) == t       # no cambia
    of2 = _oferta(e, balance=10_500_000); assert CO.asignar_tope(of2, RngFijo(0.99)) <= 10_500_000
    of3 = _oferta(e, exterior=True, balance=0); assert CO.asignar_tope(of3, RngFijo(0.99)) > 13_000_000
    print("  test_tope: OK")


def test_contraoferta_aceptada():
    e = estado_carrera(); of = _oferta(e); of['tope'] = 12_000_000
    mi = e['mi_equipo']; antes = mi.balance; j = of['jugador']
    r, _ = CO.contraofertar(e, of, 11_500_000)
    assert r == 'aceptada' and j not in mi.jugadores and mi.balance == antes + 11_500_000 - int(11_500_000 * CO.RETENCION_CLUB)   # v4.4.0: 25% para el club
    assert not e['ofertas_recibidas']
    print("  test_contraoferta_aceptada: OK")


def test_contraoferta_analizando_y_resolucion():
    for v, vendido in ((0.0, True), (0.99, False)):
        e = estado_carrera(); of = _oferta(e); of['tope'] = 12_000_000
        j = of['jugador']; mi = e['mi_equipo']
        r, msg = CO.contraofertar(e, of, 15_000_000)
        assert r == 'analizando' and "analizamos" in msg.lower()
        assert of['contra']['estado'] == 'analizando' and j in mi.jugadores
        CO.resolver_analisis(e, rng=RngFijo(v))                  # misma jornada: no resuelve
        assert of in e['ofertas_recibidas']
        e['liga'].jornada_actual += 1
        CO.resolver_analisis(e, rng=RngFijo(v))
        assert (j not in mi.jugadores) == vendido and not e['ofertas_recibidas']
        assert C.bandeja(e)[0]['remitente'] == 'club'
    print("  test_contraoferta_analizando_y_resolucion: OK")


def test_contraoferta_rechazada():
    e = estado_carrera(); of = _oferta(e); of['tope'] = 12_000_000
    r, _ = CO.contraofertar(e, of, 20_000_000)
    assert r == 'rechazada' and not e['ofertas_recibidas'] and of['jugador'] in e['mi_equipo'].jugadores
    print("  test_contraoferta_rechazada: OK")


def test_una_sola_contraoferta():
    e = estado_carrera(); of = _oferta(e); of['tope'] = 12_000_000
    assert CO.contraofertar(e, of, 9_000_000)[0] == 'invalida' and 'contra' not in of
    CO.contraofertar(e, of, 15_000_000)
    assert CO.contraofertar(e, of, 11_000_000)[0] == 'invalida'
    print("  test_una_sola_contraoferta: OK")


def test_analisis_jugador_ya_no_esta():
    e = estado_carrera(); of = _oferta(e); of['tope'] = 12_000_000
    CO.contraofertar(e, of, 15_000_000)
    from alpha_football.finanzas import quitar_de_plantilla
    quitar_de_plantilla(e['mi_equipo'], of['jugador'])
    antes = e['mi_equipo'].balance
    e['liga'].jornada_actual += 1
    CO.resolver_analisis(e, rng=RngFijo(0.0))
    assert e['mi_equipo'].balance == antes and not e['ofertas_recibidas']
    print("  test_analisis_jugador_ya_no_esta: OK")


def _objetivo_compra(e, moral=70):
    club = e['liga'].equipos[2]; j = sorted(club.jugadores, key=lambda x: -x.overall)[5]
    j.moral = moral; j.contrato_anios = 3
    return club, j


def test_compra_rangos():
    e = estado_carrera(); club, j = _objetivo_compra(e)
    minimo = N.minimo_club(j, club)
    assert N.evaluar_compra(e, j, club, minimo)[0] == 'acepta'
    r, msg, _ = N.evaluar_compra(e, j, club, int(minimo * 0.9))
    assert r == 'analiza' and "analizamos" in msg.lower()
    assert e['datos_carrera']['analisis_compras'][0]['jugador_id'] == j.id
    r, _, contra = N.evaluar_compra(e, j, club, int(minimo * 0.5))
    assert r == 'rechaza' and contra == minimo
    print("  test_compra_rangos: OK")


def test_compra_clasico_solo_clausula():
    e = estado_carrera(); club, j = _objetivo_compra(e)
    e['mi_equipo'].rival, club.rival = club.nombre, e['mi_equipo'].nombre
    r, msg, contra = N.evaluar_compra(e, j, club, N.minimo_club(j, club) * 3)
    if j.clausula > N.minimo_club(j, club) * 3:
        assert r == 'rechaza' and "clásico" in msg.lower() and contra == int(j.clausula)
    assert N.evaluar_compra(e, j, club, int(j.clausula))[0] == 'acepta'
    j.moral = 30
    assert N.evaluar_compra(e, j, club, N.minimo_club(j, club))[0] == 'acepta'
    print("  test_compra_clasico_solo_clausula: OK")


def test_compra_analizada_correo_y_reanudar():
    e = estado_carrera(); club, j = _objetivo_compra(e); e['liga'].jornada_actual = 1
    monto = int(N.minimo_club(j, club) * 0.9)
    N.evaluar_compra(e, j, club, monto)
    e['liga'].jornada_actual = 2
    CO.resolver_analisis(e, rng=RngFijo(0.0))
    msg = C.bandeja(e)[0]
    assert msg['accion']['compra']['jugador_id'] == j.id and not e['datos_carrera']['analisis_compras']
    assert N.reanudar_compra(e, msg['accion']['compra']) == 'negociacion_screen'
    assert e['neg']['etapa'] == 'jugador' and e['neg']['monto'] == monto and e['neg']['jugador'] is j
    print("  test_compra_analizada_correo_y_reanudar: OK")


def test_reanudar_compra_invalida():
    e = estado_carrera(); club, j = _objetivo_compra(e)
    compra = {'jugador_id': j.id, 'club_id': club.id, 'monto': 1, 'temporada': 1}
    e['liga'].jornada_actual = 5                                  # ventana cerrada (10 jornadas)
    assert N.reanudar_compra(e, compra) is None and e.get('correo_aviso')
    e['liga'].jornada_actual = 2; compra['temporada'] = 0
    assert N.reanudar_compra(e, compra) is None
    print("  test_reanudar_compra_invalida: OK")


# --- Task 3: UI ────────────────────────────────────────────────────────────────

def key(k, uni=''):
    pygame.event.clear(); pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=uni))


def test_entrada_monto():
    from alpha_football.ui.entrada_monto import editar_valor
    ev = lambda k, u='': pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=u)
    assert editar_valor(12, ev(pygame.K_3, '3')) == 123
    assert editar_valor(123, ev(pygame.K_BACKSPACE)) == 12
    assert editar_valor(12, ev(pygame.K_a, 'a')) == 12
    assert editar_valor(10**11, ev(pygame.K_9, '9')) == 10**11       # tope 12 dígitos
    print("  test_entrada_monto: OK")


def test_ficha_compartida():
    from alpha_football.ui.ficha_jugador import dibujar_ficha
    e = estado_carrera(); j = e['mi_equipo'].jugadores[0]
    y = dibujar_ficha(screen, pygame.Rect(700, 100, 560, 520), j, "Oferta")
    assert 100 < y <= 620
    print("  test_ficha_compartida: OK")


def test_ofertas_screen_contraoferta():
    from alpha_football.ui import ofertas_screen as S
    e = estado_carrera(); of = _oferta(e); of['tope'] = 12_000_000
    pygame.event.clear(); assert S.render(screen, e) is None
    click(S.R_CONTRA.center); S.render(screen, e)
    assert e.get('contra_abierta') and e['contra_monto'] == 11_000_000        # arranca en +10%
    click(S.R_ENVIAR.center); S.render(screen, e)
    assert 'acepta' in e['oferta_msg'][0].lower() and not e['ofertas_recibidas']
    print("  test_ofertas_screen_contraoferta: OK")


def test_negociacion_teclear_y_analiza():
    from alpha_football.ui import negociacion_screen as NS
    e = estado_carrera(); club, j = _objetivo_compra(e)
    N.iniciar_negociacion(e, j, club, 'fichaje', 'buscador_screen')
    e['neg']['monto'] = 0
    for d in str(int(N.minimo_club(j, club) * 0.9)):
        key(getattr(pygame, f'K_{d}'), d); NS.render(screen, e)
    assert e['neg']['monto'] == int(N.minimo_club(j, club) * 0.9)
    e['mi_equipo'].balance = 10**10
    click(NS._rects()['ofertar'].center)
    assert NS.render(screen, e) is None
    assert "analizamos" in e['neg']['msg'][0].lower() and e['datos_carrera']['analisis_compras']
    print("  test_negociacion_teclear_y_analiza: OK")


def test_correo_accion_compra():
    from alpha_football.ui import correo_screen as CS
    e = estado_carrera(); club, j = _objetivo_compra(e); e['liga'].jornada_actual = 2
    msg = {'accion': {'pantalla': 'negociacion_screen', 'texto': 'X',
                      'compra': {'jugador_id': j.id, 'club_id': club.id, 'monto': 5, 'temporada': 1}}}
    assert CS._ir(e, msg) == 'negociacion_screen' and e['neg']['monto'] == 5
    print("  test_correo_accion_compra: OK")


TESTS =[test_dinero_exacto, test_factor_contrato, test_oferta_ia_con_descuento_contrato,
         test_clasico_no_oferta_salvo_moral_baja, test_exterior_mas_ofertas_y_top3,
         test_tope, test_contraoferta_aceptada, test_contraoferta_analizando_y_resolucion,
         test_contraoferta_rechazada, test_una_sola_contraoferta, test_analisis_jugador_ya_no_esta,
         test_compra_rangos, test_compra_clasico_solo_clausula, test_compra_analizada_correo_y_reanudar,
         test_reanudar_compra_invalida,
         test_entrada_monto, test_ficha_compartida, test_ofertas_screen_contraoferta,
         test_negociacion_teclear_y_analiza, test_correo_accion_compra]


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
