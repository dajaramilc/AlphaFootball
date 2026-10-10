"""0.4.22.0: editor ampliado (DT completos, jugador con todos sus campos, crear jugador de club)."""
import sys, os, json, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
screen = pygame.display.set_mode((1280, 720))
from alpha_football import save
save.guardar_en_slot = lambda *a, **k: None

from alpha_football.models import Jugador, Equipo
from alpha_football.ui import edit_screen as E


def _jugador(i=1, **kw):
    base = dict(nombre="Ana", apellido=f"Prueba{i}", posicion="MED", ataque=70, defensa=70, fisico=70,
                tecnica=70, mental=70, moral=70, id=i, edad=27)
    base.update(kw)
    d = Jugador(**base).to_dict()
    d['potencial'] = 75
    return d


def _db(n_jugadores=2):
    return {'premier': [{'nombre': 'Club A', 'balance': 1_000_000, 'estrellas': 3.0,
                         'jugadores': [_jugador(i) for i in range(1, n_jugadores + 1)]}],
            '_libres': [_jugador(90000)],
            '_dts_libres': [{'nombre': 'Libre Uno', 'estilo': 'cruyffismo', 'calif': 61,
                             'nacionalidad': 'Italia', 'edad': 58},
                            {'nombre': 'Libre Dos', 'estilo': 'anchelottismo', 'calif': 40}]}


# ---------------------------------------------------------------- 2A: lógica pura
def test_fijar_atributo_sincroniza_overall_y_potencial():
    j = _jugador()
    j['potencial'] = 71
    assert E.fijar_campo_int(j, 'ataque', 99, 1, 99) == 99
    assert j['overall'] == E.overall_de(j) == (99 + 70 * 4) // 5
    assert j['potencial'] >= j['overall']
    assert E.fijar_campo_int(j, 'moral', 150, 0, 100) == 100 and j['moral'] == 100
    assert E.fijar_campo_int(j, 'defensa', -5, 1, 99) == 1


def test_fijar_ovr_todos():
    j = _jugador()
    E.fijar_ovr_todos(j, 88)
    assert all(j[a] == 88 for a in E.ATRIBUTOS) and j['overall'] == 88 and j['potencial'] >= 88
    E.fijar_ovr_todos(j, 500)
    assert j['overall'] == 99


def test_teclear_y_borrar_digitos():
    assert E.teclear_entero(0, '7', 1, 99, 2) == 7
    assert E.teclear_entero(7, '5', 1, 99, 2) == 75
    assert E.teclear_entero(75, '1', 1, 99, 2) == 75          # un tercer dígito no entra
    assert E.teclear_entero(50, 'x', 1, 99, 2) == 50          # solo dígitos
    assert E.teclear_entero(9, '9', 0, 50, 3) == 50           # el techo manda
    assert E.borrar_digito(75) == 7 and E.borrar_digito(7) == 0 and E.borrar_digito(0) == 0


def test_sanear_jugador():
    j = _jugador()
    j.update(ataque=0, moral=300, contrato_anios=-1, salario=-5, energia=500)
    E.sanear_jugador(j)
    assert j['ataque'] == 1 and j['moral'] == 100 and j['contrato_anios'] == 0
    assert j['salario'] == 0 and j['energia'] == 100
    assert j['overall'] == E.overall_de(j)


def test_ciclar_opcion():
    ops = ['a', 'b', 'c']
    assert E.ciclar_opcion('a', ops) == 'b' and E.ciclar_opcion('c', ops) == 'a'
    assert E.ciclar_opcion('a', ops, -1) == 'c'
    assert E.ciclar_opcion('zzz', ops) == 'a'
    assert E.ciclar_opcion('x', []) == 'x'


def test_opciones_nacionalidad_incluye_las_de_la_base():
    db = _db()
    db['premier'][0]['jugadores'][0]['nacionalidad'] = 'Francia'
    ops = E.opciones_nacionalidad(db)
    assert 'Francia' in ops and 'Uruguay' in ops and len(ops) == len(set(ops))


def test_nuevo_jugador_club_respeta_el_maximo():
    from alpha_football import market
    from alpha_football.data.nombres_genericos import NOMBRES_POR_PAIS as N
    db = _db(market.PLANTILLA_MAXIMA - 1)
    ids = {j['id'] for j in db['premier'][0]['jugadores']} | {90000}
    idx = E.nuevo_jugador_club(db, 'premier', 0)
    plantilla = db['premier'][0]['jugadores']
    assert idx == market.PLANTILLA_MAXIMA - 1 == len(plantilla) - 1
    nuevo = plantilla[idx]
    assert nuevo['id'] not in ids
    assert nuevo['nombre'] in N['Inglaterra'][0] and nuevo['apellido'] in N['Inglaterra'][1]
    assert nuevo['nacionalidad'] == 'Inglaterra' and nuevo['posicion'] == 'MED' and nuevo['overall'] == 70
    assert E.nuevo_jugador_club(db, 'premier', 0) == -1 and len(plantilla) == market.PLANTILLA_MAXIMA


def test_nuevo_jugador_club_no_ensucia_el_registro_global():
    from alpha_football import nombres as NM
    antes = set(NM._USADOS)
    E.nuevo_jugador_club(_db(), 'premier', 0)
    assert NM._USADOS == antes


def test_quitar_dt_lo_manda_a_libres():
    db = _db()
    club = db['premier'][0]
    club.update(dt_nombre='Pep Nuevo', dt_estilo='cruyffismo', dt_calif=77, dt_nacionalidad='España', dt_edad=52)
    n = len(db['_dts_libres'])
    assert E.quitar_dt(db, club) is True
    assert len(db['_dts_libres']) == n + 1
    ult = db['_dts_libres'][-1]
    assert (ult['nombre'], ult['calif'], ult['nacionalidad'], ult['edad']) == ('Pep Nuevo', 77, 'España', 52)
    assert club['dt_sin'] is True and 'dt_nombre' not in club and 'dt_calif' not in club
    assert E.quitar_dt(db, club) is False and len(db['_dts_libres']) == n + 1


def test_quitar_dt_real_y_sin_definir():
    db = _db()
    club = db['premier'][0]
    club['nombre'] = 'Manchester Billete'                       # club con DT real en data/entrenadores.DT_REALES
    from alpha_football.data.entrenadores import DT_REALES
    real = DT_REALES.get(club['nombre'])
    E.quitar_dt(db, club)
    if real:
        assert db['_dts_libres'][-1]['nombre'] == real[0]
    db2 = _db()
    club2 = db2['premier'][0]                                   # 'Club A': sin DT real ni editado
    E.quitar_dt(db2, club2)
    assert db2['_dts_libres'][-1]['nombre'].strip() != ''


def test_asignar_dt_intercambia():
    db = _db()
    club = db['premier'][0]
    club.update(dt_nombre='Viejo DT', dt_estilo='cruyffismo', dt_calif=55)
    assert E.asignar_dt(db, club, 0) is True
    assert club['dt_nombre'] == 'Libre Uno' and club['dt_calif'] == 61
    assert club['dt_nacionalidad'] == 'Italia' and club['dt_edad'] == 58 and 'dt_sin' not in club
    assert club['estilo_dt'] == club['dt_estilo']
    nombres = [d['nombre'] for d in db['_dts_libres']]
    assert 'Libre Uno' not in nombres and 'Viejo DT' in nombres
    assert E.asignar_dt(db, club, 99) is False


def test_asignar_dt_a_club_sin_dt_no_agrega_saliente():
    db = _db()
    club = db['premier'][0]
    club['dt_sin'] = True
    n = len(db['_dts_libres'])
    assert E.asignar_dt(db, club, 1) is True
    assert len(db['_dts_libres']) == n - 1 and club['dt_nombre'] == 'Libre Dos' and 'dt_sin' not in club


def test_prestigio_de():
    assert [E.prestigio_de(c) for c in (1, 49, 50, 69, 70, 99)] == ['BAJO', 'BAJO', 'MEDIO', 'MEDIO', 'ALTO', 'ALTO']


def test_equipo_from_dict_lee_los_dt_nuevos():
    e = Equipo.from_dict({'nombre': 'X', 'dt_nacionalidad': 'Italia', 'dt_edad': 55, 'dt_sin': True})
    assert (e.dt_nacionalidad, e.dt_edad, e.dt_sin) == ('Italia', 55, True)
    viejo = Equipo.from_dict({'nombre': 'Y'})                    # base editada vieja: sin los campos
    assert (viejo.dt_nacionalidad, viejo.dt_edad, viejo.dt_sin) == ('', 0, False)
    assert Equipo.from_dict(e.to_dict()).dt_edad == 55           # ida y vuelta


def test_campos_nuevos_llegan_a_la_carrera():
    from alpha_football import finanzas
    d = _jugador(5, salario=1_234_000, contrato_anios=3, clausula=9_000_000, personalidad='lider',
                 nacionalidad='Uruguay', moral=88, resistencia=77, penales=91, energia=60.0)
    j = Jugador.from_dict(d)
    assert (j.salario, j.contrato_anios, j.clausula) == (1_234_000, 3, 9_000_000)
    assert (j.personalidad, j.nacionalidad, j.moral, j.resistencia, j.penales) == ('lider', 'Uruguay', 88, 77, 91)
    assert j.energia == 60.0
    finanzas.asegurar_contrato(j)
    assert j.salario == 1_234_000                                # solo rellena si salario <= 0


def test_base_vieja_abre_y_guarda():
    db = {'premier': [{'nombre': 'Club A', 'jugadores': [{'nombre': 'A', 'apellido': 'B', 'posicion': 'DEF',
                                                           'ataque': 60, 'defensa': 60, 'fisico': 60,
                                                           'tecnica': 60, 'mental': 60, 'id': 3}]}]}
    j = db['premier'][0]['jugadores'][0]
    E.sanear_jugador(j)
    assert E.quitar_dt(db, db['premier'][0]) is True and db['_dts_libres']
    assert E.nuevo_jugador_club(db, 'premier', 0) == 1
    json.dumps(db)


def test_sanear_no_agrega_claves_ni_toca_lo_que_esta_en_rango():
    j = {'nombre': 'A', 'apellido': 'B', 'ataque': 60, 'defensa': 60, 'fisico': 60, 'tecnica': 60,
         'mental': 60, 'energia': 63.5, 'penales': 0}
    E.sanear_jugador(j)
    assert 'resistencia' not in j and 'salario' not in j and 'moral' not in j     # base vieja: no se inventa nada
    assert j['energia'] == 63.5 and j['penales'] == 0                              # en rango: intacto (0 = automático)


# ---------------------------------------------------------------- 2B: interfaz
def _estado(seccion, db=None, liga='premier', **extra):
    e = {'edited_db': db or _db(), 'edit_seccion': seccion, 'edit_liga_sel': liga,
         'edit_equipo_idx': 0, 'edit_jugador_idx': -1}
    e.update(extra)
    return e


def _clic(pos):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def _teclas(*teclas):
    pygame.event.clear()
    for t in teclas:
        car = chr(t) if 32 <= t < 127 else ''
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=t, unicode=car, mod=0))


def test_render_de_cada_seccion_y_pagina():
    e = _estado('entrenadores')
    assert E.render(screen, e) is None                                  # DT de un club
    e['edited_db']['premier'][0]['dt_sin'] = True
    assert E.render(screen, e) is None                                  # club sin DT
    e.update(edit_liga_sel=E.LIBRES, edit_equipo_idx=0)
    assert E.render(screen, e) is None                                  # DT libre
    e = _estado('clubes')
    assert E.render(screen, e) is None
    e = _estado('ligas')
    assert E.render(screen, e) is None
    for pag in (1, 2):
        e = _estado('jugadores', edit_jugador_idx=0, edit_pag_jugador=pag)
        assert E.render(screen, e) is None, pag                         # jugador de club
        e = _estado('jugadores', liga=E.LIBRES, edit_jugador_idx=0, edit_pag_jugador=pag)
        assert E.render(screen, e) is None, pag                         # jugador libre
    e = _estado('jugadores')                                            # club elegido, ningún jugador
    assert E.render(screen, e) is None


def test_pagina_2_y_edicion_de_atributo():
    e = _estado('jugadores', edit_jugador_idx=0)
    E.render(screen, e)
    _clic(E.R_PAG.center)
    E.render(screen, e)
    assert e['edit_pag_jugador'] == 2
    _clic(E.rect_campo_p2(0).center)                                    # ataque
    E.render(screen, e)
    assert e['edit_input_activo'] == 'p2:ataque'
    _teclas(pygame.K_BACKSPACE, pygame.K_BACKSPACE, pygame.K_9, pygame.K_9)
    E.render(screen, e)
    j = e['edited_db']['premier'][0]['jugadores'][0]
    assert j['ataque'] == 99 and j['overall'] == (99 + 70 * 4) // 5
    _teclas(pygame.K_RETURN)
    E.render(screen, e)
    assert not e['edit_input_activo'] and j['ataque'] == 99
    _clic(E.R_PAG.center)
    E.render(screen, e)
    assert e['edit_pag_jugador'] == 1


def test_borrar_todo_se_sanea_al_salir_del_campo():
    e = _estado('jugadores', edit_jugador_idx=0, edit_pag_jugador=2, edit_input_activo='p2:defensa')
    E.render(screen, e)
    _teclas(pygame.K_BACKSPACE, pygame.K_BACKSPACE)
    E.render(screen, e)
    j = e['edited_db']['premier'][0]['jugadores'][0]
    assert j['defensa'] == 0 and e['edit_input_activo'] == 'p2:defensa'   # mientras se edita se admite 0
    _teclas(pygame.K_RETURN)
    E.render(screen, e)
    assert j['defensa'] == 1


def test_campos_de_seleccion_ciclan_con_el_clic():
    e = _estado('jugadores', edit_jugador_idx=0, edit_pag_jugador=2)
    E.render(screen, e)
    j = e['edited_db']['premier'][0]['jugadores'][0]
    antes = j.get('personalidad')
    k_pers = [c[0] for c in E.CAMPOS_JUGADOR_P2].index('personalidad')
    _clic(E.rect_campo_p2(k_pers).center)
    E.render(screen, e)
    assert j['personalidad'] != antes and j['personalidad'] in E.PERSONALIDADES
    k_nac = [c[0] for c in E.CAMPOS_JUGADOR_P2].index('nacionalidad')
    _clic(E.rect_campo_p2(k_nac).center)
    E.render(screen, e)
    assert j['nacionalidad'] in E.opciones_nacionalidad(e['edited_db'])


def test_boton_crear_jugador_club():
    from alpha_football import market
    e = _estado('jugadores', db=_db(market.PLANTILLA_MAXIMA - 1))
    E.render(screen, e)
    _clic(E.R_NUEVO.center)
    E.render(screen, e)
    plantilla = e['edited_db']['premier'][0]['jugadores']
    assert len(plantilla) == market.PLANTILLA_MAXIMA and e['edit_jugador_idx'] == len(plantilla) - 1
    assert e['edit_pag_jugador'] == 1
    _clic(E.R_NUEVO.center)
    E.render(screen, e)
    assert len(plantilla) == market.PLANTILLA_MAXIMA and 'llena' in e['edit_mensaje']


def test_quitar_y_asignar_dt_desde_la_ui():
    e = _estado('entrenadores')
    club = e['edited_db']['premier'][0]
    club.update(dt_nombre='Viejo DT', dt_calif=55)
    E.render(screen, e)
    _clic(E.R_DT_QUITAR.center)
    E.render(screen, e)
    assert club.get('dt_sin') is True and any(d['nombre'] == 'Viejo DT' for d in e['edited_db']['_dts_libres'])
    _clic(E.R_DT_ASIGNAR.center)
    E.render(screen, e)
    assert 'dt_sin' not in club and club['dt_nombre'] == 'Libre Uno'
    e['edited_db']['_dts_libres'].clear()
    _clic(E.R_DT_ASIGNAR.center)
    E.render(screen, e)
    assert club['dt_nombre'] == 'Libre Uno' and 'No hay' in e['edit_mensaje']      # sin libres: no hace nada


def test_nacionalidad_y_edad_del_dt():
    e = _estado('entrenadores')
    club = e['edited_db']['premier'][0]
    E.render(screen, e)
    _clic(E.R_DT_NAC.center)
    E.render(screen, e)
    assert club['dt_nacionalidad'] in E.opciones_nacionalidad(e['edited_db'])
    e['edit_input_activo'] = 'dtx:edad'
    _teclas(pygame.K_1, pygame.K_2)
    E.render(screen, e)
    assert club['dt_edad'] == 12
    _teclas(pygame.K_RETURN)
    E.render(screen, e)
    assert club['dt_edad'] == 30                                        # fuera de 30-80 → se lleva al mínimo
    e['edit_input_activo'] = 'dtx:edad'
    _teclas(pygame.K_BACKSPACE, pygame.K_BACKSPACE)
    E.render(screen, e)
    _teclas(pygame.K_RETURN)
    E.render(screen, e)
    assert club['dt_edad'] == 0                                         # 0 = al azar


def test_escribir_nombre_a_un_club_sin_dt_le_devuelve_el_dt():
    e = _estado('entrenadores')
    club = e['edited_db']['premier'][0]
    club['dt_sin'] = True
    E.render(screen, e)
    _clic(E.R_DT_NOMBRE.center)
    E.render(screen, e)
    assert 'dt_sin' not in club and e['edit_input_activo'] == 'dt_nombre'


def test_guardar_y_recargar_conserva_los_campos_nuevos():
    import tempfile
    viejo = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            db = _db()
            j = db['premier'][0]['jugadores'][0]
            E.fijar_campo_int(j, 'salario', 7_654_000, 0, 500_000_000)
            j['personalidad'] = 'lider'
            db['premier'][0].update(dt_sin=True, dt_nacionalidad='Italia', dt_edad=61)
            e = {'edited_db': db}
            assert E.guardar_base_datos(e) is True
            otro = {}
            db2 = E.cargar_base_datos_inicial(otro)
            club = db2['premier'][0]
            assert club['jugadores'][0]['salario'] == 7_654_000 and club['jugadores'][0]['personalidad'] == 'lider'
            assert (club['dt_sin'], club['dt_nacionalidad'], club['dt_edad']) == (True, 'Italia', 61)
            assert any(d['nombre'] == 'Libre Uno' for d in db2['_dts_libres'])
        finally:
            os.chdir(viejo)


# ---------------------------------------------------------------- pie
if __name__ == '__main__':
    TESTS = [v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
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
