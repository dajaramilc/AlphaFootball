"""v4.6.0: sueldo de los DTs de la IA (nadie contrata un DT que no puede pagar), DTs y jugadores
libres creados en el editor, y editor ordenado por ENTRENADORES / CLUBES / LIGAS / JUGADORES."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(21)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save
from alpha_football import entrenadores as EN
from alpha_football import mercado_ia as MI
from alpha_football import negociacion as NG
from alpha_football.data import free_agents as FA
from alpha_football.models import Equipo, Jugador, alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams, _ligas_por_division

save.guardar_en_slot = lambda *a, **k: None
EN._dts_libres_editor = lambda: []            # los tests no dependen de la base editada del disco
FA._libres_de_la_base = lambda: []


def estado_carrera(tipo='premier', idx=0):
    liga = load_league_teams(tipo)
    mi = liga.equipos[idx]
    mi.alineacion_activa = alineacion_por_defecto(mi)
    primeras, segunda = _ligas_por_division(liga, {}, {})
    return {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
            'alineacion_activa': mi.alineacion_activa, 'primera_division': primeras,
            'segunda_division': segunda, 'datos_carrera': {}, 'historial': []}


def _club(e, tipo, pobre=True):
    liga = e['primera_division'][tipo]
    ia = [x for x in liga.equipos if x is not e['mi_equipo']]
    return (min if pobre else max)(ia, key=lambda x: x.balance), liga


# ---------------------------------------------------------------- sueldos de DT
def test_sueldo_sube_con_la_calif():
    s = [EN.sueldo_pedido(c) for c in (30, 50, 70, 90)]
    assert s == sorted(s) and s[0] >= EN.SUELDO_DT_MIN and s[-1] > 10 * s[0]
    print("  test_sueldo_sube_con_la_calif: OK")


def test_dt_de_club_grande_cobra_segun_su_club():
    e = estado_carrera(); EN.asegurar_dts(e)
    grande, _ = _club(e, 'premier', pobre=False)
    dt = EN.dt_de(e, grande)
    assert EN.sueldo(dt) >= int(grande.balance * 0.03), (EN.sueldo(dt), grande.balance)
    print("  test_dt_de_club_grande_cobra_segun_su_club: OK")


def test_club_chico_no_contrata_dt_caro():
    """El Emelec no ficha a Arteta: el DT caro sigue libre y el club paga a uno que le alcanza."""
    e = estado_carrera(); EN.asegurar_dts(e)
    chico, liga = _club(e, 'ecuador')
    d = EN.dts(e)
    arteta = {**EN._nuevo(e, "Mikel Artetazo", 'artetismo', 95), 'sueldo': 9_000_000}
    d['libres'].append(arteta)
    saldo = chico.balance
    EN.despedir(e, chico, liga, "prueba")
    EN._reemplazar(e, chico)
    nuevo = EN.dt_de(e, chico)
    assert nuevo['nombre'] != "Mikel Artetazo" and arteta in d['libres']
    assert EN.sueldo(nuevo) <= EN.FRAC_SUELDO_DT * saldo
    assert chico.balance == saldo - EN.sueldo(nuevo)
    print("  test_club_chico_no_contrata_dt_caro: OK")


def test_club_grande_si_lo_contrata():
    e = estado_carrera(); EN.asegurar_dts(e)
    grande, liga = _club(e, 'premier', pobre=False)
    arteta = {**EN._nuevo(e, "Mikel Artetazo", 'artetismo', 95), 'sueldo': 9_000_000}
    EN.dts(e)['libres'].append(arteta)
    saldo = grande.balance
    EN.despedir(e, grande, liga, "prueba")
    EN._reemplazar(e, grande)
    assert EN.dt_de(e, grande)['nombre'] == "Mikel Artetazo"
    assert grande.balance == saldo - 9_000_000
    print("  test_club_grande_si_lo_contrata: OK")


def test_sin_dt_pagable_contrata_uno_barato_nuevo():
    e = estado_carrera(); EN.asegurar_dts(e)
    chico, liga = _club(e, 'ecuador')
    d = EN.dts(e)
    for x in d['libres']:
        x['sueldo'] = 10 ** 9
    n = len(d['libres'])
    chico.balance = 1_000_000
    EN.despedir(e, chico, liga, "prueba")                 # el despedido entra a libres (n + 1)
    EN._reemplazar(e, chico)
    nuevo = EN.dt_de(e, chico)
    assert len(d['libres']) == n + 1 and nuevo not in d['libres']
    assert EN.sueldo(nuevo) <= max(EN.SUELDO_DT_MIN, EN.FRAC_SUELDO_DT * 1_000_000)
    print("  test_sin_dt_pagable_contrata_uno_barato_nuevo: OK")


def test_interino_no_cobra():
    e = estado_carrera()
    assert EN.sueldo(EN._nuevo(e, "X (interino)", 'anchelottismo', 40, interino=True)) == 0
    print("  test_interino_no_cobra: OK")


def test_temporada_descuenta_sueldo_del_dt():
    e = estado_carrera(); EN.asegurar_dts(e)
    club, _ = _club(e, 'premier', pobre=False)

    class Fijo(random.Random):
        def uniform(self, a, b):
            return 1.0
    saldo = club.balance
    MI.ingresos_fin_temporada(e, rng=Fijo())
    con_dt = club.balance
    club.balance = saldo
    EN.dts(e)['por_club'].pop(str(club.id))
    MI.ingresos_fin_temporada(e, rng=Fijo())
    sin_dt = club.balance
    assert sin_dt - con_dt > 0
    print("  test_temporada_descuenta_sueldo_del_dt: OK")


# ---------------------------------------------------------------- DT editado en el editor
def test_dt_editado_estilo_y_calif():
    e = estado_carrera()
    otro = e['liga'].equipos[2]
    otro.dt_nombre, otro.dt_estilo, otro.dt_calif = "Profe Editado", 'kloppismo', 88
    EN.asegurar_dts(e)
    dt = EN.dt_de(e, otro)
    assert (dt['nombre'], dt['estilo'], dt['calif']) == ("Profe Editado", 'kloppismo', 88)
    assert otro.estilo_dt == 'kloppismo'
    print("  test_dt_editado_estilo_y_calif: OK")


def test_equipo_guarda_dt_editado():
    eq = Equipo("A", "B", 3.0, 'cruyffismo', 1_000_000, dt_estilo='choloismo', dt_calif=77)
    otro = Equipo.from_dict(eq.to_dict())
    assert otro.dt_estilo == 'choloismo' and otro.dt_calif == 77
    print("  test_equipo_guarda_dt_editado: OK")


def test_dts_libres_del_editor_entran_a_la_bolsa_una_vez():
    orig = EN._dts_libres_editor
    EN._dts_libres_editor = lambda: [{'nombre': 'Bielsa Loco', 'estilo': 'kloppismo', 'calif': 81}]
    try:
        e = estado_carrera(); EN.asegurar_dts(e); EN.asegurar_dts(e)
        libres = [x for x in EN.dts(e)['libres'] if x['nombre'] == 'Bielsa Loco']
        assert len(libres) == 1 and libres[0]['estilo'] == 'kloppismo' and libres[0]['calif'] == 81
        assert EN.sueldo(libres[0]) == EN.sueldo_pedido(81)
    finally:
        EN._dts_libres_editor = orig
    print("  test_dts_libres_del_editor_entran_a_la_bolsa_una_vez: OK")


# ---------------------------------------------------------------- jugadores libres del editor
# v4.9.2: nombre que no existe en la base: 'Neymar Duro-en-fiesta' es un libre real y a veces salía dos veces
def _libre_dict(nombre='Libreditor', apellido='De-prueba', ovr=85, jid=90001):
    return Jugador(nombre=nombre, apellido=apellido, posicion='DEL', ataque=ovr, defensa=ovr, fisico=ovr,
                   tecnica=ovr, mental=ovr, moral=70, id=jid, edad=30).to_dict()


def _con_libres_editor(lista):
    orig = FA._libres_de_la_base
    FA._libres_de_la_base = lambda: [dict(x) for x in lista]
    return orig


def test_libres_del_editor_estan_toda_la_carrera():
    orig = _con_libres_editor([_libre_dict()])
    try:
        e = estado_carrera()
        for jornada in (1, 2, 3):
            e['liga'].jornada_actual = jornada
            nombres = [j.nombre_completo for j in NG.asegurar_agentes_libres(e)]
            assert nombres.count('Libreditor De-prueba') == 1, (jornada, nombres)
        j = next(x for x in e['free_agents_list'] if x.nombre == 'Libreditor')
        assert j.overall == 85 and j.valor > 0
    finally:
        FA._libres_de_la_base = orig
    print("  test_libres_del_editor_estan_toda_la_carrera: OK")


def test_libre_del_editor_fichado_ya_no_vuelve():
    orig = _con_libres_editor([_libre_dict()])
    try:
        e = estado_carrera()
        e['mi_equipo'].balance = 10 ** 9
        j = next(x for x in NG.asegurar_agentes_libres(e) if x.nombre == 'Libreditor')
        FA.quitar_libre_editor(e, j)
        e['liga'].jornada_actual = 5
        assert all(x.nombre != 'Libreditor' for x in NG.asegurar_agentes_libres(e))
    finally:
        FA._libres_de_la_base = orig
    print("  test_libre_del_editor_fichado_ya_no_vuelve: OK")


def test_fichar_libre_del_editor_lo_saca_de_la_bolsa():
    orig = _con_libres_editor([_libre_dict()])
    try:
        e = estado_carrera()
        e['mi_equipo'].balance = 10 ** 9
        j = next(x for x in NG.asegurar_agentes_libres(e) if x.nombre == 'Libreditor')
        NG.fichar(e, j, None, 0)
        assert not e['datos_carrera']['libres_editor']
    finally:
        FA._libres_de_la_base = orig
    print("  test_fichar_libre_del_editor_lo_saca_de_la_bolsa: OK")


# ---------------------------------------------------------------- editor por secciones
from alpha_football.ui import edit_screen as ED


def click(pos):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def teclas(*ks):
    pygame.event.clear()
    for k in ks:
        u = k if isinstance(k, str) else ''
        code = pygame.key.key_code(k) if isinstance(k, str) else k
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=code, unicode=u, mod=0))


def _estado_editor():
    liga = load_league_teams('premier')
    db = {'premier': [eq.to_dict() for eq in liga.equipos], 'segunda_premier': [], '_ligas': {}}
    e = {'edited_db': db}
    pygame.event.clear()
    assert ED.render(screen, e) is None
    return e, db


def test_editor_arranca_en_entrenadores_y_cambia_de_seccion():
    e, _db = _estado_editor()
    assert e['edit_seccion'] == 'entrenadores'
    for i, (clave, _t) in enumerate(ED.SECCIONES):
        click(ED.rect_seccion(i).center)
        assert ED.render(screen, e) is None and e['edit_seccion'] == clave
        pygame.event.clear(); assert ED.render(screen, e) is None
    print("  test_editor_arranca_en_entrenadores_y_cambia_de_seccion: OK")


def test_dt_efectivo_de_un_club_real():
    club = {'nombre': 'Manchester Billete', 'estrellas': 5.0, 'estilo_dt': 'haramball'}
    assert ED.dt_efectivo(club) == ('Pep Guardiolo', 'cruyffismo', 70)
    club.update(dt_nombre='Otro', dt_estilo='kloppismo', dt_calif=91)
    assert ED.dt_efectivo(club) == ('Otro', 'kloppismo', 91)
    print("  test_dt_efectivo_de_un_club_real: OK")


def test_editar_dt_de_club_estilo_y_calif():
    e, db = _estado_editor()
    club = db['premier'][0]
    click(ED.R_DT_CALIF.center); ED.render(screen, e)
    teclas(pygame.K_BACKSPACE, pygame.K_BACKSPACE, '7', '7', pygame.K_RETURN); ED.render(screen, e)
    assert club['dt_calif'] == 77
    click(ED.R_DT_ESTILO.center); ED.render(screen, e)
    r = next(r for v, _t, r in ED._opciones_dropdown('estilo_dt') if v == 'kloppismo')
    click(r.center); ED.render(screen, e)
    assert club['dt_estilo'] == 'kloppismo' and club['estilo_dt'] == 'kloppismo'
    print("  test_editar_dt_de_club_estilo_y_calif: OK")


def test_crear_editar_y_borrar_dt_libre():
    e, db = _estado_editor()
    click(ED.R_LIBRES.center); ED.render(screen, e)
    assert e['edit_liga_sel'] == ED.LIBRES
    click(ED.R_NUEVO.center); ED.render(screen, e)
    assert len(db['_dts_libres']) == 1
    click(ED.R_DT_NOMBRE.center); ED.render(screen, e)
    teclas(*([pygame.K_BACKSPACE] * 20), 'B', 'i', 'e', 'l', 's', 'a', pygame.K_RETURN); ED.render(screen, e)
    assert db['_dts_libres'][0]['nombre'] == 'Bielsa'
    click(ED.R_BORRAR.center); ED.render(screen, e)
    assert db['_dts_libres'] == []
    print("  test_crear_editar_y_borrar_dt_libre: OK")


def test_crear_y_editar_jugador_libre():
    e, db = _estado_editor()
    click(ED.rect_seccion(3).center); ED.render(screen, e)
    click(ED.R_LIBRES.center); ED.render(screen, e)
    click(ED.R_NUEVO.center); ED.render(screen, e)
    click(ED.R_NUEVO.center); ED.render(screen, e)
    libres = db['_libres']
    assert len(libres) == 2 and len({j['id'] for j in libres}) == 2 and all(j['id'] >= 90000 for j in libres)
    assert e['edit_jugador_idx'] == 1
    click(ED.R_J_OVR.center); ED.render(screen, e)
    teclas(pygame.K_BACKSPACE, pygame.K_BACKSPACE, '8', '5', pygame.K_RETURN); ED.render(screen, e)
    j = Jugador.from_dict(libres[1])
    assert j.overall == 85
    click(ED.R_BORRAR.center); ED.render(screen, e)
    assert len(db['_libres']) == 1
    print("  test_crear_y_editar_jugador_libre: OK")


def test_ligas_y_clubes():
    e, db = _estado_editor()
    click(ED.rect_seccion(2).center); ED.render(screen, e)
    click(ED.rect_fila_lista(1).center); ED.render(screen, e)
    assert e['edit_liga_sel'] == 'segunda_premier'
    click(ED.R_NOMBRE_LIGA.center); ED.render(screen, e)
    teclas(*([pygame.K_BACKSPACE] * 45), 'Z', pygame.K_RETURN); ED.render(screen, e)
    assert db['_ligas']['premier']['nombre_2a'] == 'Z'
    click(ED.rect_seccion(1).center); ED.render(screen, e)
    assert e['edit_liga_sel'] == 'segunda_premier'
    click(ED.rect_seccion(1).center); e['edit_liga_sel'] = 'premier'; ED.render(screen, e)
    click(ED.R_EQ_PRESUPUESTO.center); ED.render(screen, e)
    teclas(*([pygame.K_BACKSPACE] * 15), '5', pygame.K_RETURN); ED.render(screen, e)
    assert db['premier'][0]['balance'] == 5
    print("  test_ligas_y_clubes: OK")


if __name__ == '__main__':
    for _n, _f in list(globals().items()):
        if _n.startswith('test_') and callable(_f):
            _f()
    print("OK test_editor_libres_dts")
