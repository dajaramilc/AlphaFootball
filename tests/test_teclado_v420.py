"""v4.2.0: teclado en todo el juego (menú inicial, partido en vivo, pantallas y overlays), atajos
globales M (correo) / O (opciones), GUARDAR dentro de Opciones y sobre de correo en INICIO."""
import sys, os, random, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(13)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save
from alpha_football.models import alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams, _ligas_por_division

_tmp = tempfile.mkdtemp()
save.guardar_en_slot = lambda *a, **k: None          # los tests no tocan los slots reales


def click(pos):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def key(k, uni=''):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=uni))


def estado_carrera(tipo='premier', idx=0):
    liga = load_league_teams(tipo)
    mi = liga.equipos[idx]
    mi.alineacion_activa = alineacion_por_defecto(mi)
    primeras, segunda = _ligas_por_division(liga, {}, {})
    return {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
            'alineacion_activa': mi.alineacion_activa, 'primera_division': primeras,
            'segunda_division': segunda, 'datos_carrera': {}, 'historial': []}


# ---------------------------------------------------------------- Task 1: orden por columnas


# ---------------------------------------------------------------- Task 7: menú inicial
from alpha_football.ui import menu as M


def test_menu_main_teclado():
    e = {'menu_step': 'main'}
    pygame.event.clear(); M.render(screen, e)
    assert e.get('menu_foco', 0) == 0
    key(pygame.K_DOWN); M.render(screen, e); assert e['menu_foco'] == 1
    key(pygame.K_UP); M.render(screen, e); key(pygame.K_UP); M.render(screen, e)
    assert e['menu_foco'] == len(M.botones_main()) - 1          # da la vuelta
    e['menu_foco'] = [b[2] for b in M.botones_main()].index('opciones')
    key(pygame.K_RETURN); assert M.render(screen, e) == 'options_screen'
    e2 = {'menu_step': 'main', 'menu_foco': 0}
    key(pygame.K_RETURN); M.render(screen, e2); assert e2['menu_step'] == 'select_country'
    print("  test_menu_main_teclado: OK")


def test_menu_elegir_club_teclado():
    liga = load_league_teams('premier')
    e = {'menu_step': 'select_team', 'selected_liga_obj': liga}
    pygame.event.clear(); M.render(screen, e)
    key(pygame.K_RIGHT); M.render(screen, e)
    key(pygame.K_RETURN); M.render(screen, e)
    assert e['menu_step'] == 'dt_setup' and e['pending_equipo'] is liga.equipos[1]
    key(pygame.K_ESCAPE); M.render(screen, e)
    assert e['menu_step'] == 'select_team'
    key(pygame.K_ESCAPE); M.render(screen, e)
    assert e['menu_step'] == 'select_division'
    print("  test_menu_elegir_club_teclado: OK")


def test_menu_dt_tab_y_lista():
    liga = load_league_teams('premier')
    e = {'menu_step': 'dt_setup', 'selected_liga_obj': liga, 'pending_equipo': liga.equipos[0], 'dt_nombre': 'Diego'}
    pygame.event.clear(); M.render(screen, e)
    assert e['dt_focus'] == 'name'
    key(pygame.K_TAB); M.render(screen, e); assert e['dt_focus'] == 'lista'
    key(pygame.K_DOWN); M.render(screen, e); assert e.get('dt_nac_sel') in M.NACIONALIDADES
    key(pygame.K_TAB); M.render(screen, e); assert e['dt_focus'] == 'nac'
    print("  test_menu_dt_tab_y_lista: OK")


def test_menu_cargar_esc():
    e = {'menu_step': 'load_slots'}
    pygame.event.clear(); M.render(screen, e)
    key(pygame.K_ESCAPE); M.render(screen, e)
    assert e['menu_step'] == 'main'
    print("  test_menu_cargar_esc: OK")


def test_menu_amistoso_equipo_teclado():
    liga = load_league_teams('premier')
    e = {'menu_step': 'amistoso_teams', 'amistoso_liga': liga, 'amis_phase': 'local'}
    pygame.event.clear(); M.render(screen, e)
    key(pygame.K_DOWN); M.render(screen, e)
    key(pygame.K_RETURN); M.render(screen, e)
    assert e['amis_local'] is liga.equipos[2] and e['menu_step'] == 'amistoso_country'
    print("  test_menu_amistoso_equipo_teclado: OK")


# ---------------------------------------------------------------- Task 8: partido en vivo y dirección
def _ev(k, uni=''):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=uni)


def _vivo():
    from alpha_football.ui import match_screen as MS
    from alpha_football.ui.league_screen import inicializar_calendario_liga
    e = estado_carrera(); liga = e['liga']; mi = e['mi_equipo']
    if not getattr(liga, 'calendario', None):
        inicializar_calendario_liga(liga)
    e['partido_actual'] = next(p for p in liga.calendario if p.jornada == liga.jornada_actual
                               and mi.id in (p.local_id, p.visitante_id))
    e['match_mode'] = 'liga'; pygame.event.clear(); MS.render(screen, e)
    return MS, e


def test_vivo_teclas_velocidad_tactica_mentalidad():
    MS, e = _vivo()
    v0 = e['sim_velocidad_factor']; key(pygame.K_v); MS.render(screen, e)
    assert e['sim_velocidad_factor'] != v0
    key(pygame.K_5); MS.render(screen, e)
    assert e['mi_equipo'].mentalidad == 'todo_o_nada'
    key(pygame.K_t); MS.render(screen, e); assert e.get('sim_tactico_abierto')
    key(pygame.K_RETURN); MS.render(screen, e); assert not e.get('sim_tactico_abierto')
    print("  test_vivo_teclas_velocidad_tactica_mentalidad: OK")


def test_direccion_cursor_y_espacio():
    from alpha_football.ui import team_screen as TS
    e = estado_carrera(); mi = e['mi_equipo']; alin = mi.alineacion_activa
    from alpha_football import formaciones as F
    F.normalizar_convocados(alin, mi.jugadores)
    antes = list(alin.titulares); banco0 = alin.convocados[0]
    llamar = lambda evs: TS._render_direccion(screen, e, mi, alin, False, False, 'league_screen', (0, 0), None,
                                              key_events=evs)
    llamar([])
    llamar([_ev(pygame.K_SPACE)])                 # selecciona el 1º del campo
    assert e.get('team_sel') == ('campo', 0)
    llamar([_ev(pygame.K_DOWN)])                  # baja al banco
    llamar([_ev(pygame.K_SPACE)])                 # intercambia con el 1º del banco
    assert alin.titulares != antes and banco0 in alin.titulares
    print("  test_direccion_cursor_y_espacio: OK")


def test_penales_teclado():
    MS, e = _vivo()
    mi = e['mi_equipo']
    assert MS._menu_penales(screen, e, mi, (0, 0), None, [pygame.K_DOWN, pygame.K_SPACE]) is None
    assert len(e['sim_penales_sel']) == 4                 # quitó al 2º de la lista
    assert MS._menu_penales(screen, e, mi, (0, 0), None, [pygame.K_a]) is None
    assert len(e['sim_penales_sel']) == 5
    elegidos = MS._menu_penales(screen, e, mi, (0, 0), None, [pygame.K_RETURN])
    assert elegidos and len(elegidos) == 5
    print("  test_penales_teclado: OK")


# ---------------------------------------------------------------- Task 9: auditoría de pantallas
def test_despido_teclado():
    from alpha_football.ui import despido_screen as DS
    e = estado_carrera(); liga = e['liga']
    elegidos = []
    orig = DS.D.cambiar_de_club
    DS.D.cambiar_de_club = lambda est, eq: elegidos.append(eq)
    try:
        e['despido_pendiente'] = {'titulo': '¡DESPEDIDO!', 'motivo': 'x', 'opciones': [liga.equipos[3], liga.equipos[4]]}
        pygame.event.clear(); DS.render(screen, e)
        key(pygame.K_RIGHT); DS.render(screen, e)
        key(pygame.K_RETURN); assert DS.render(screen, e) == 'contrato_dt_screen'
        assert elegidos == [liga.equipos[4]]
    finally:
        DS.D.cambiar_de_club = orig
    print("  test_despido_teclado: OK")


def test_ofertas_dt_teclado():
    from alpha_football.ui import ofertas_dt_screen as OD
    e = estado_carrera(); rech = []
    orig = (OD.EN.ofertas_activas, OD.EN.rechazar_oferta, OD.EN._club_por_id)
    OD.EN.ofertas_activas = lambda est: [{'club_id': 'x', 'club': 'Club X', 'liga': 'Liga', 'jornadas': 2}]
    OD.EN.rechazar_oferta = lambda est, cid: rech.append(cid)
    OD.EN._club_por_id = lambda est, cid: (None, None)
    try:
        pygame.event.clear(); OD.render(screen, e)
        key(pygame.K_RIGHT); OD.render(screen, e)          # ACEPTAR -> RECHAZAR
        key(pygame.K_RETURN); OD.render(screen, e)
        assert rech == ['x']
    finally:
        OD.EN.ofertas_activas, OD.EN.rechazar_oferta, OD.EN._club_por_id = orig
    print("  test_ofertas_dt_teclado: OK")


def test_ojeador_teclado():
    from alpha_football.ui import ojeador_screen as OJ
    e = estado_carrera(); otro = e['liga'].equipos[5]; j = otro.jugadores[0]
    orig = (OJ.N.recomendaciones_ojeador, OJ.N.iniciar_negociacion)
    OJ.N.recomendaciones_ojeador = lambda est: [(j, otro, 'titular', 1_000_000, 'porque sí')]
    OJ.N.iniciar_negociacion = lambda est, jj, club, tipo, volver: 'negociacion_screen'
    try:
        pygame.event.clear(); OJ.render(screen, e)
        key(pygame.K_RETURN); assert OJ.render(screen, e) == 'negociacion_screen'
    finally:
        OJ.N.recomendaciones_ojeador, OJ.N.iniciar_negociacion = orig
    print("  test_ojeador_teclado: OK")


def test_negociacion_teclado():
    from alpha_football import negociacion as N
    from alpha_football.ui import negociacion_screen as NS
    e = estado_carrera(); otro = e['liga'].equipos[5]; j = otro.jugadores[3]
    assert N.iniciar_negociacion(e, j, otro, 'fichaje', 'league_screen') == 'negociacion_screen'
    pygame.event.clear(); NS.render(screen, e)
    key(pygame.K_RETURN); NS.render(screen, e)           # foco inicial: OFERTAR
    assert e['neg'].get('msg')
    key(pygame.K_ESCAPE); assert NS.render(screen, e) == 'league_screen'
    print("  test_negociacion_teclado: OK")


def test_contrato_renovacion_r():
    from alpha_football.ui import contrato_dt_screen as CT
    e = estado_carrera(); rech = []
    orig = CT.CD.rechazar_renovacion
    CT.CD.rechazar_renovacion = lambda est: rech.append(True)
    try:
        e['contrato_modo'] = 'renovacion'
        pygame.event.clear(); CT.render(screen, e)
        key(pygame.K_r, 'r'); CT.render(screen, e)
        assert rech == [True]
    finally:
        CT.CD.rechazar_renovacion = orig
    print("  test_contrato_renovacion_r: OK")


def test_editor_teclado():
    from alpha_football.ui import edit_screen as ED
    e = {}
    pygame.event.clear(); ED.render(screen, e)
    i0 = e['edit_equipo_idx']
    key(pygame.K_DOWN); ED.render(screen, e); assert e['edit_equipo_idx'] == i0 + 1
    key(pygame.K_RIGHT); ED.render(screen, e); assert e['edit_jugador_idx'] == 0
    key(pygame.K_DOWN); ED.render(screen, e); assert e['edit_jugador_idx'] == 1
    key(pygame.K_LEFT); ED.render(screen, e); assert e['edit_jugador_idx'] == -1
    key(pygame.K_ESCAPE); assert ED.render(screen, e) == 'menu'
    print("  test_editor_teclado: OK")


def test_editor_dropdown_teclado():
    from alpha_football.ui import edit_screen as ED
    e = {}
    pygame.event.clear(); ED.render(screen, e)
    e['edit_jugador_idx'] = 0; e['edit_dropdown_activo'] = 'posicion'
    pygame.event.clear(); ED.render(screen, e)
    key(pygame.K_DOWN); ED.render(screen, e)
    key(pygame.K_RETURN); ED.render(screen, e)
    assert e.get('edit_dropdown_activo') is None
    e['edit_dropdown_activo'] = 'rasgo'
    key(pygame.K_ESCAPE); ED.render(screen, e)
    assert e.get('edit_dropdown_activo') is None and e.get('menu_step') != 'main'   # Esc cierra, no sale
    print("  test_editor_dropdown_teclado: OK")


# ---------------------------------------------------------------- Task 10: M / O, GUARDAR en opciones, sobre
def _main():
    """main.py reemplaza pygame.event.get al importarse: se restaura para que key()/click() lleguen."""
    import main as MAIN
    pygame.event.get = MAIN._original_event_get
    return MAIN


def test_atajos_globales_m_o():
    MAIN = _main()
    e = estado_carrera(); e['current_screen'] = 'league_screen'
    quedan = MAIN.procesar_atajos_globales(e, [_ev(pygame.K_m, 'm')])
    assert quedan == [] and e['current_screen'] == 'correo_screen'
    e['current_screen'] = 'stats_screen'
    MAIN.procesar_atajos_globales(e, [_ev(pygame.K_o, 'o')])
    assert e['current_screen'] == 'options_screen' and e['options_return'] == 'stats_screen'
    print("  test_atajos_globales_m_o: OK")


def test_atajos_globales_con_texto():
    MAIN = _main()
    e = estado_carrera(); e['current_screen'] = 'league_screen'; e['texto_activo'] = True
    quedan = MAIN.procesar_atajos_globales(e, [_ev(pygame.K_m, 'm')])
    assert len(quedan) == 1 and e['current_screen'] == 'league_screen'
    e['texto_activo'] = False; e['current_screen'] = 'options_screen'
    assert len(MAIN.procesar_atajos_globales(e, [_ev(pygame.K_m, 'm')])) == 1   # M = silenciar en opciones
    e2 = {'current_screen': 'menu'}                                             # fuera de carrera no hay correo
    assert len(MAIN.procesar_atajos_globales(e2, [_ev(pygame.K_m, 'm')])) == 1
    print("  test_atajos_globales_con_texto: OK")


def test_guardar_en_opciones_solo_carrera():
    from alpha_football.ui import options_screen as O
    from alpha_football.ui import league_screen as L
    e = estado_carrera()
    assert 'guardar' in O.items_opciones(e)
    assert 'guardar' not in O.items_opciones({})
    assert 'guardar' not in O.items_opciones(dict(e, match_mode='amistoso'))
    assert 'guardar' not in [b[0] for b in L.BARRA_MENU]
    e['opt_foco'] = O.items_opciones(e).index('guardar')
    e['options_return'] = 'league_screen'
    key(pygame.K_RETURN); assert O.render(screen, e) == 'save_slots_screen'
    assert e['save_slots_return'] == 'options_screen'
    print("  test_guardar_en_opciones_solo_carrera: OK")


def test_sobre_badge():
    from alpha_football.ui import league_screen as L
    from alpha_football import correo as C
    assert L.texto_badge(0) is None and L.texto_badge(3) == '3' and L.texto_badge(12) == '9+'
    e = estado_carrera()
    for i in range(3):
        C.enviar(e, 'club', f'm{i}', 'x')
    e['hub_tab'] = 'inicio'
    e['datos_carrera']['aviso_mercado_visto'] = [1, e['liga'].jornada_actual]   # sin el cartel del mercado (v4.4.0)
    pygame.event.clear(); L.render(screen, e)
    click(L.R_SOBRE.center)
    assert L.render(screen, e) == 'correo_screen'
    assert not any(r.colliderect(L.R_SOBRE) for r in L._rects_barra())
    print("  test_sobre_badge: OK")


def test_negociacion_nueva_arranca_en_ofertar():
    from alpha_football import negociacion as N
    from alpha_football.ui import negociacion_screen as NS
    e = estado_carrera(); otro = e['liga'].equipos[5]
    e['foco_neg_club'] = 1                                   # quedó en PAGAR CLÁUSULA de otra negociación
    N.iniciar_negociacion(e, otro.jugadores[3], otro, 'fichaje', 'league_screen')
    pygame.event.clear(); NS.render(screen, e)
    assert e['foco_neg_club'] == 0
    print("  test_negociacion_nueva_arranca_en_ofertar: OK")


if __name__ == '__main__':
    for _n, _f in list(globals().items()):
        if _n.startswith('test_') and callable(_f):
            _f()
    print("OK test_teclado_v420")
