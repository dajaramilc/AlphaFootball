"""v0.4.20.0: el saldo negativo ya no se multiplica al cargar, ningún club de la IA baja de 16 jugadores
y la IA ficha y vende con prudencia (aparta los sueldos, tope por ingresos y saneamiento)."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(420)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import finanzas as F, mercado_ia as MI, negociacion as N, save
from alpha_football.entrenadores import dt_de, sueldo as sueldo_dt
from alpha_football.models import Equipo, alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams

save.guardar_en_slot = lambda *a, **k: None          # los tests no tocan los slots reales
RICO = 10**10


def estado_chico():
    """Una sola liga (Premier): las rondas de la IA corren en segundos."""
    liga = load_league_teams('premier')
    mi = liga.equipos[0]
    mi.alineacion_activa = alineacion_por_defecto(mi)
    e = {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
         'alineacion_activa': mi.alineacion_activa, 'primera_division': {'premier': liga},
         'segunda_division': {}, 'datos_carrera': {}, 'historial': []}
    F.asegurar_contratos(e)
    return e


def _rival(e):
    """Un club de la IA de tu liga que no es tu clásico."""
    from alpha_football.data.clasicos import es_clasico
    return next(c for c in e['liga'].equipos[1:] if not es_clasico(c, e['mi_equipo']))


def _grande(e):
    return max(e['liga'].equipos[1:], key=lambda c: c.estrellas)


def _gasto(e, eq):
    return F.masa_salarial(eq) + sueldo_dt(dt_de(e, eq))


def _fijar_masa(eq, total):
    """Reparte `total` de sueldos anuales entre toda la plantilla."""
    n = len(eq.jugadores)
    for j in eq.jugadores:
        j.salario = total // n


def _compro(log, eq):
    return any(l.startswith(eq.nombre + ' ficha a ') for l in log)


# ---------------------------------------------------------------- 1: el saldo al cargar
def test_saldo_negativo_no_se_multiplica_al_cargar():
    assert Equipo.from_dict({'nombre': 'X', 'balance': -113485, 'jugadores': []}).balance == -113485
    assert Equipo.from_dict({'nombre': 'X', 'balance': 50, 'jugadores': []}).balance == 50_000_000   # base vieja, en millones
    print("  test_saldo_negativo_no_se_multiplica_al_cargar: OK")


def test_reparar_saldos_corrige_el_rojo_imposible():
    e = estado_chico(); liga = e['liga']; mi = e['mi_equipo']
    roto, sano = liga.equipos[3], liga.equipos[4]
    rojo_normal = -F.ingresos_esperados(sano, 'premier', 1) // 20
    roto.balance, sano.balance, mi.balance = -10**40, rojo_normal, -10**40
    assert MI.reparar_saldos(e) == [roto.nombre]
    assert roto.balance == 0 and sano.balance == rojo_normal
    assert mi.balance == -10**40                       # el club del user no se toca
    print("  test_reparar_saldos_corrige_el_rojo_imposible: OK")


# ---------------------------------------------------------------- 2: mínimo de 16
def test_club_en_el_minimo_no_le_vende_al_user():
    e = estado_chico(); eq = _rival(e)
    del eq.jugadores[MI.PLANTILLA_MIN_IA + 1:]
    j = min(eq.jugadores, key=lambda x: x.overall)
    monto = N.minimo_club(j, eq)
    assert monto < int(j.clausula)
    assert N.evaluar_compra(e, j, eq, monto)[0] == 'acepta'          # con 17 todavía vende
    eq.jugadores.remove(next(x for x in eq.jugadores if x is not j))
    resp, msg, _contra = N.evaluar_compra(e, j, eq, monto)
    assert resp == 'rechaza' and 'plantilla corta' in msg
    print("  test_club_en_el_minimo_no_le_vende_al_user: OK")


def test_la_clausula_se_paga_aunque_el_club_este_en_el_minimo():
    e = estado_chico(); eq = _rival(e)
    del eq.jugadores[MI.PLANTILLA_MIN_IA:]
    j = min(eq.jugadores, key=lambda x: x.overall)
    assert N.evaluar_compra(e, j, eq, int(j.clausula))[0] == 'acepta'
    print("  test_la_clausula_se_paga_aunque_el_club_este_en_el_minimo: OK")


def test_las_compras_acordadas_cuentan_para_el_minimo():
    e = estado_chico(); eq = _rival(e)
    del eq.jugadores[MI.PLANTILLA_MIN_IA + 1:]
    j = min(eq.jugadores, key=lambda x: x.overall)
    e['datos_carrera']['traspasos_pendientes'] = [{'tipo': 'compra', 'origen': eq.nombre, 'jugador': 'Otro'}]
    assert N.evaluar_compra(e, j, eq, N.minimo_club(j, eq))[0] == 'rechaza'
    print("  test_las_compras_acordadas_cuentan_para_el_minimo: OK")


def test_club_bajo_el_minimo_sube_juveniles():
    e = estado_chico(); eq = _rival(e); mi = e['mi_equipo']
    eq.jugadores[:] = [j for j in eq.jugadores if j.posicion != 'POR'][:12]
    viejos = list(eq.jugadores)
    del mi.jugadores[14:]
    assert MI.asegurar_minimo_ia(e) == [eq.nombre]
    assert len(eq.jugadores) >= MI.PLANTILLA_MIN_IA and len(mi.jugadores) == 14     # el del user no se toca
    for pos, minimo in F.MINIMO_POR_POSICION.items():
        assert sum(1 for j in eq.jugadores if j.posicion == pos) >= minimo, pos
    nuevos = [j for j in eq.jugadores if j not in viejos]
    assert all(j.salario > 0 and j.contrato_anios >= 2 and j.valor > 0 for j in nuevos)
    assert MI.asegurar_minimo_ia(e) == []              # ya está completo
    print("  test_club_bajo_el_minimo_sube_juveniles: OK")


def test_tras_pagarle_la_clausula_el_club_vuelve_a_16():
    e = estado_chico(); eq = _rival(e); mi = e['mi_equipo']
    del eq.jugadores[MI.PLANTILLA_MIN_IA:]
    j = min(eq.jugadores, key=lambda x: x.overall)
    mi.balance = RICO
    ok, msg = N.fichar(e, j, eq, int(j.clausula))
    assert ok, msg
    assert j in mi.jugadores and j not in eq.jugadores and len(eq.jugadores) >= MI.PLANTILLA_MIN_IA
    print("  test_tras_pagarle_la_clausula_el_club_vuelve_a_16: OK")


# ---------------------------------------------------------------- 3: la IA prudente
def test_club_sin_margen_para_los_sueldos_no_ficha():
    e = estado_chico(); eq = _grande(e)
    for c in e['liga'].equipos:
        c.balance = RICO
    _fijar_masa(eq, 3 * RICO)                          # ni con todo su saldo paga los sueldos del año
    log = MI.ronda_fichajes_ia(e, 'pretemporada', random.Random(2))
    assert not _compro(log, eq)
    assert any(' ficha a ' in l for l in log)          # los demás sí fichan
    print("  test_club_sin_margen_para_los_sueldos_no_ficha: OK")


def test_no_ficha_si_el_sueldo_nuevo_supera_sus_ingresos():
    e = estado_chico(); eq = _grande(e)
    for c in e['liga'].equipos:
        c.balance = 0                                  # nadie le compra: su masa salarial no baja
    eq.balance = RICO
    ingresos = F.ingresos_esperados(eq, 'premier', 1)
    _fijar_masa(eq, ingresos - sueldo_dt(dt_de(e, eq)) - 1000)     # sueldos al ras de sus ingresos
    assert _gasto(e, eq) <= ingresos
    log = MI.ronda_fichajes_ia(e, 'pretemporada', random.Random(2))
    assert not _compro(log, eq) and _gasto(e, eq) <= ingresos
    print("  test_no_ficha_si_el_sueldo_nuevo_supera_sus_ingresos: OK")


def test_club_con_sueldos_sobre_sus_ingresos_vende_suplentes():
    from alpha_football.formaciones import mejor_once
    e = estado_chico(); eq = _grande(e)
    for c in e['liga'].equipos:
        c.balance = RICO
    eq.balance = 0
    ingresos = F.ingresos_esperados(eq, 'premier', 1)
    _fijar_masa(eq, int(ingresos * 1.5))
    once = [eq.jugadores[i] for i in mejor_once(eq.jugadores, "4-3-3")]
    antes, masa_antes = len(eq.jugadores), F.masa_salarial(eq)
    log = MI.sanear_ia(e, random.Random(1))
    assert log and MI.PLANTILLA_MIN_VENDEDOR <= len(eq.jugadores) < antes
    assert all(j in eq.jugadores for j in once)        # el once no se toca
    assert eq.balance > 0 and F.masa_salarial(eq) < masa_antes
    assert e['datos_carrera'].get('historial_pases') or e.get('mercado_ia_log')
    print("  test_club_con_sueldos_sobre_sus_ingresos_vende_suplentes: OK")


def test_club_sano_no_vende_por_saneamiento():
    e = estado_chico()
    for c in e['liga'].equipos:
        c.balance = RICO
        _fijar_masa(c, F.ingresos_esperados(c, 'premier', 1) // 2)
    tam = [len(c.jugadores) for c in e['liga'].equipos]
    assert MI.sanear_ia(e, random.Random(1)) == []
    assert [len(c.jugadores) for c in e['liga'].equipos] == tam
    print("  test_club_sano_no_vende_por_saneamiento: OK")


def test_el_saneamiento_evita_la_quiebra_al_cierre():
    e = estado_chico(); eq = _grande(e)
    for c in e['liga'].equipos:
        c.balance = RICO
    ingresos = F.ingresos_esperados(eq, 'premier', 1)
    eq.balance = 0
    _fijar_masa(eq, int(ingresos * 1.3))               # sin vender: en rojo hasta en su mejor temporada
    quebrados = MI.ingresos_fin_temporada(e, random.Random(1))
    assert eq.nombre not in quebrados
    assert len(eq.jugadores) >= MI.PLANTILLA_MIN_VENDEDOR
    print("  test_el_saneamiento_evita_la_quiebra_al_cierre: OK")


# ---------------------------------------------------------------- 4: el banco internacional
def _internacionales(e):
    return [c for c, _et in N.clubes_internacionales(e)]


def _fotos(e):
    return {c.nombre: sorted((j.nombre_completo, j.posicion, j.overall) for j in c.jugadores) for c in _internacionales(e)}


def test_el_banco_internacional_nace_con_16():
    e = estado_chico()
    clubes = _internacionales(e)
    assert clubes and all(len(c.jugadores) >= MI.PLANTILLA_MIN_IA for c in clubes)
    print("  test_el_banco_internacional_nace_con_16: OK")


def test_los_juveniles_del_banco_no_cambian_al_rearmarlo():
    e = estado_chico()
    antes = _fotos(e)
    e.pop('_copas_pool')                               # como al cargar la partida
    assert _fotos(e) == antes
    print("  test_los_juveniles_del_banco_no_cambian_al_rearmarlo: OK")


def test_club_internacional_en_el_minimo_solo_vende_por_la_clausula():
    e = estado_chico()
    club = next(c for c in _internacionales(e) if len(c.jugadores) == MI.PLANTILLA_MIN_IA)
    j = min(club.jugadores, key=lambda x: x.overall)
    F.asegurar_contrato(j)
    assert N.evaluar_compra(e, j, club, N.minimo_club(j, club))[0] == 'rechaza'
    assert N.evaluar_compra(e, j, club, int(j.clausula))[0] == 'acepta'
    print("  test_club_internacional_en_el_minimo_solo_vende_por_la_clausula: OK")


def test_tras_la_clausula_el_internacional_vuelve_a_16_y_el_fichado_no_regresa():
    e = estado_chico(); mi = e['mi_equipo']; mi.balance = RICO
    club = next(c for c in _internacionales(e) if len(c.jugadores) == MI.PLANTILLA_MIN_IA)
    j = min(club.jugadores, key=lambda x: x.overall)
    F.asegurar_contrato(j)
    ok, msg = N.fichar(e, j, club, int(j.clausula))
    assert ok, msg
    assert j not in club.jugadores and len(club.jugadores) >= MI.PLANTILLA_MIN_IA
    e.pop('_copas_pool')
    rearmado = next(c for c in _internacionales(e) if c.nombre == club.nombre)
    assert len(rearmado.jugadores) >= MI.PLANTILLA_MIN_IA
    assert j.nombre_completo not in [x.nombre_completo for x in rearmado.jugadores]
    print("  test_tras_la_clausula_el_internacional_vuelve_a_16_y_el_fichado_no_regresa: OK")


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
