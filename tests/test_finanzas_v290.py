"""v2.9.0: FINANZAS (salarios, taquilla, patrocinios, quiebra) y CONTRATOS (fichaje negociado, renovaciones)."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(21)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import finanzas as F, negociacion as N, save
from alpha_football.market import calcular_valor
from alpha_football.models import Jugador, alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams, _ligas_por_division

save.guardar_en_slot = lambda *a, **k: None


def click(pos):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def key(k):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=''))


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


def jugador_ia(e, max_ovr=None):
    mi = e['mi_equipo']
    tope = max_ovr if max_ovr is not None else 200
    return next((j, c) for j, c, _et in N.pool_buscador(e) if c is not None and j.overall <= tope)


def test_contrato_inicial():
    e = estado_carrera()
    for j in e['mi_equipo'].jugadores:
        v = calcular_valor(j)
        assert j.salario == max(F.SALARIO_MIN, int(v * F.SALARIO_PCT_VALOR))
        assert 1 <= j.contrato_anios <= 5 and j.clausula == int(v * F.CLAUSULA_MULT_INICIAL)
        if j.edad >= 32:
            assert j.contrato_anios <= 2
    d = e['mi_equipo'].jugadores[0].to_dict()
    j2 = Jugador.from_dict(d)
    assert (j2.salario, j2.contrato_anios, j2.clausula) == (e['mi_equipo'].jugadores[0].salario,
                                                            e['mi_equipo'].jugadores[0].contrato_anios,
                                                            e['mi_equipo'].jugadores[0].clausula)
    print("  test_contrato_inicial: OK")


def test_jornada_cobra_y_paga():
    e = estado_carrera()
    mi, liga = e['mi_equipo'], e['liga']
    bal = mi.balance
    mov = F.procesar_jornada(e, es_local=True, gf=2, gc=0)
    esperado = mov['patrocinio'] + mov['taquilla'] - mov['salarios']
    assert mi.balance == bal + esperado and mov['taquilla'] > 0
    assert mov['salarios'] == F.masa_salarial(mi) // liga.num_jornadas
    bal = mi.balance
    mov2 = F.procesar_jornada(e, es_local=False, gf=0, gc=1)
    assert mov2['taquilla'] == 0 and mi.balance == bal + mov2['patrocinio'] - mov2['salarios']
    libro = F.libro(e)
    assert libro['salarios'] == mov['salarios'] + mov2['salarios'] and libro['taquilla'] == mov['taquilla']
    print("  test_jornada_cobra_y_paga: OK")


def test_quiebra_vende_al_mejor_tras_3_jornadas():
    e = estado_carrera()
    mi = e['mi_equipo']
    mi.balance = -50_000_000
    estrella = max(mi.jugadores, key=calcular_valor)
    for _ in range(2):
        F.procesar_jornada(e, es_local=False, gf=0, gc=0)
    assert estrella in mi.jugadores
    F.procesar_jornada(e, es_local=False, gf=0, gc=0)
    assert estrella not in mi.jugadores
    assert e['datos_carrera']['jornadas_en_rojo'] == 0 and e.get('aviso_finanzas')
    assert N.historial(e, propio=True)[0]['jugador'] == f"{estrella.nombre} {estrella.apellido}"
    print("  test_quiebra_vende_al_mejor_tras_3_jornadas: OK")


def test_fin_de_temporada_contratos_y_quiebra():
    e = estado_carrera()
    mi = e['mi_equipo']
    for j in mi.jugadores:
        j.contrato_anios = 3
    se_va, sigue = mi.jugadores[3], mi.jugadores[4]
    se_va.contrato_anios = 1
    ia = e['liga'].equipos[1].jugadores[0]
    ia.contrato_anios = 1
    mi.balance = 10_000_000
    salidas = F.cierre_temporada(e)
    assert se_va not in mi.jugadores and se_va in e.get('free_agents_list', [])
    assert sigue.contrato_anios == 2 and ia.contrato_anios >= 1
    assert [s['jugador'] for s in salidas] == [f"{se_va.nombre} {se_va.apellido}"]
    assert not e.get('despido_pendiente')
    mi.balance = -1
    F.cierre_temporada(e)
    assert e['despido_pendiente'] and 'quiebra' in e['despido_pendiente']['motivo'].lower()
    print("  test_fin_de_temporada_contratos_y_quiebra: OK")


def test_negociacion_con_el_club():
    e = estado_carrera()
    j, club = jugador_ia(e)
    minimo = N.minimo_club(j, club)
    ok, msg, contra = N.evaluar_oferta_club(j, club, int(minimo * 0.9))
    assert not ok and contra == minimo
    ok, _m, _c = N.evaluar_oferta_club(j, club, minimo)
    assert ok
    figura = max(club.jugadores, key=lambda x: x.overall)
    assert N.minimo_club(figura, club) > N.precio_fichaje(figura)
    assert N.evaluar_oferta_club(figura, club, figura.clausula)[0]
    print("  test_negociacion_con_el_club: OK")


def test_negociacion_con_el_jugador():
    e = estado_carrera()
    j, _club = jugador_ia(e)
    j.edad = 26
    pedido = N.salario_pedido(j, 'fichaje', 2.0)
    ok, msg, contra = N.evaluar_contrato(j, int(pedido * 0.8), 3, 2.0, 'fichaje')
    assert not ok and contra == pedido
    assert N.evaluar_contrato(j, pedido, 3, 2.0, 'fichaje')[0]
    assert N.salario_pedido(j, 'fichaje', 3.0) > pedido > N.salario_pedido(j, 'fichaje', 1.5)
    j.edad = 33
    assert not N.evaluar_contrato(j, pedido * 3, 4, 2.0, 'fichaje')[0]    # veterano: máx. 2 años
    print("  test_negociacion_con_el_jugador: OK")


def test_completar_fichaje_y_renovar():
    e = estado_carrera()
    mi = e['mi_equipo']
    mi.balance = 10 ** 10
    j, club = jugador_ia(e, max_ovr=80)
    antes_club = club.balance
    ok, msg = N.completar_fichaje(e, j, club, monto=50_000_000, salario=3_000_000, anios=4, clausula_mult=3.0)
    assert ok, msg
    assert j in mi.jugadores and j not in club.jugadores and club.balance == antes_club + 50_000_000
    assert (j.salario, j.contrato_anios) == (3_000_000, 4) and j.clausula == int(calcular_valor(j) * 3.0)
    assert F.libro(e)['fichajes'] == 50_000_000
    N.renovar(e, j, salario=3_500_000, anios=2, clausula_mult=2.0)
    assert (j.salario, j.contrato_anios) == (3_500_000, 2)
    print("  test_completar_fichaje_y_renovar: OK")


def test_temporada_sin_movimientos_no_quiebra():
    from alpha_football.mercado_ia import asignar_presupuestos_realistas
    for tipo in ('premier', 'betplay', 'brasil'):
        e = estado_carrera(tipo)
        asignar_presupuestos_realistas(e, True)
        mi, liga = e['mi_equipo'], e['liga']
        inicio = mi.balance
        for jn in range(liga.num_jornadas):
            F.procesar_jornada(e, es_local=jn % 2 == 0, gf=1, gc=1)
        print(f"    {tipo}: saldo {inicio / 1e6:.1f}M → {mi.balance / 1e6:.1f}M · masa salarial {F.masa_salarial(mi) / 1e6:.1f}M")
        assert mi.balance > 0
    print("  test_temporada_sin_movimientos_no_quiebra: OK")


def test_pantallas_finanzas_y_negociacion():
    from alpha_football.ui import league_screen, finanzas_screen, negociacion_screen, buscador_screen, plantilla_screen
    claves = [b[0] for b in league_screen.BARRA_MENU]
    assert claves == ['inicio', 'direccion', 'negociaciones', 'oficina', 'finanzas', 'opciones']   # v4.2.0: GUARDAR en OPCIONES
    assert [t[2] for t in league_screen.TARJETAS['finanzas']] == ['finanzas_screen', 'contratos']
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'main.py'), encoding='utf-8').read()
    assert "'finanzas_screen': 'alpha_football.ui.finanzas_screen'" in src and "'negociacion_screen': 'alpha_football.ui.negociacion_screen'" in src   # v3.6.0: MODULOS_PANTALLA
    e = estado_carrera()
    e['mi_equipo'].balance = 10 ** 10
    pygame.event.clear()
    assert finanzas_screen.render(screen, e) is None
    # buscador: FICHAR abre la negociación (ya no ficha directo)
    pygame.event.clear(); buscador_screen.render(screen, e)
    j, club, _et = e['busq_resultados'][0]
    click(buscador_screen._rects()['fichar'].center)
    assert buscador_screen.render(screen, e) == 'negociacion_screen'
    assert e['neg']['jugador'] is j and e['neg']['volver'] == 'buscador_screen' and j not in e['mi_equipo'].jugadores
    # negociación: pagar la cláusula y aceptar lo que pide el jugador
    pygame.event.clear(); negociacion_screen.render(screen, e)
    r = negociacion_screen._rects()
    click(r['clausula'].center); negociacion_screen.render(screen, e)
    assert e['neg']['etapa'] == 'jugador'
    e['neg']['salario'] = N.salario_pedido(j, 'fichaje', e['neg']['clausula_mult'])
    click(r['proponer'].center); negociacion_screen.render(screen, e)
    assert e['neg']['etapa'] == 'hecho' and j in e['mi_equipo'].jugadores
    click(r['volver'].center)
    assert negociacion_screen.render(screen, e) == 'buscador_screen' and 'neg' not in e
    # plantilla: RENOVAR abre la negociación en modo renovación
    e['plantilla_sel'] = 0
    pygame.event.clear(); plantilla_screen.render(screen, e)
    click(plantilla_screen._rects()['renovar'].center)
    assert plantilla_screen.render(screen, e) == 'negociacion_screen' and e['neg']['modo'] == 'renovar'
    print("  test_pantallas_finanzas_y_negociacion: OK")


TESTS = [test_contrato_inicial, test_jornada_cobra_y_paga, test_quiebra_vende_al_mejor_tras_3_jornadas,
         test_fin_de_temporada_contratos_y_quiebra, test_negociacion_con_el_club, test_negociacion_con_el_jugador,
         test_completar_fichaje_y_renovar, test_temporada_sin_movimientos_no_quiebra,
         test_pantallas_finanzas_y_negociacion]


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
