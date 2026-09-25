"""v3.6.0: UX — orden por columnas, filtros en overlay, teclado en opciones/guardar, diálogo de salida,
barra de atajos, nota en vivo, prepartido y editor."""
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
from alpha_football.ui import plantilla_screen as PS

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
            'segunda_division': segunda, 'historial': [],
            'datos_carrera': {'aviso_mercado_visto': [1, 1]}}   # v4.4.0: sin cartel de mercado en J1


# ---------------------------------------------------------------- Task 1: orden por columnas
def test_orden_por_columna():
    e = estado_carrera(); js = e['mi_equipo'].jugadores
    for clave in ('pos', 'nombre', 'media', 'pot', 'edad', 'valor', 'contrato', 'moral', 'energia'):
        a = PS.ordenar_plantilla(js, clave, False); b = PS.ordenar_plantilla(js, clave, True)
        assert len(a) == len(js) and a != [] and (a == list(reversed(b)) or clave in ('pos',)), clave
    edades = [js[i].edad for i in PS.ordenar_plantilla(js, 'edad', False)]
    assert edades == sorted(edades)
    print("  test_orden_por_columna: OK")


def test_click_encabezado_invierte():
    e = estado_carrera()
    pygame.event.clear(); PS.render(screen, e)
    click(PS.rect_columna('edad').center); PS.render(screen, e)
    assert e['plantilla_orden'] == ('edad', False)
    click(PS.rect_columna('edad').center); PS.render(screen, e)
    assert e['plantilla_orden'] == ('edad', True)
    print("  test_click_encabezado_invierte: OK")


def test_orden_con_nulos():
    e = estado_carrera(); js = e['mi_equipo'].jugadores
    js[0].valor = None; js[1].contrato_anios = None; js[2].moral = None
    PS.ordenar_plantilla(js, 'valor', True); PS.ordenar_plantilla(js, 'contrato', False)
    PS.ordenar_plantilla(js, 'moral', False)
    e['plantilla_orden'] = 'contrato'                     # clave vieja (atajo CONTRATOS del hub)
    pygame.event.clear(); assert PS.render(screen, e) is None
    assert e['plantilla_orden'] == ('contrato', False)
    print("  test_orden_con_nulos: OK")


# ---------------------------------------------------------------- Task 2: filtros en overlay
def test_filtrar_min_max_y_libres():
    from alpha_football import negociacion as N
    e = estado_carrera(); pool = N.pool_buscador(e)
    r = N.filtrar(pool, {'edad_min': 20, 'edad_max': 25, 'media_min': 70, 'media_max': 80})
    assert r and all(20 <= j.edad <= 25 and 70 <= j.overall <= 80 for j, _c, _et in r)
    r = N.filtrar(pool, {'pot_min': 75, 'pot_max': 85, 'precio_min': 1_000_000, 'precio_max': 30_000_000})
    assert r and all(75 <= (j.potencial or j.overall) <= 85 and 1_000_000 <= N.precio_fichaje(j) <= 30_000_000
                     for j, _c, _et in r)
    libres = N.filtrar(pool, {'solo_libres': True})
    assert all(et == N.LIBRES for _j, _c, et in libres)
    assert N.filtrar(pool, {'media_min': 60}) == N.filtrar(pool, {'media_min': 60, 'solo_libres': False})
    assert N.filtrar(pool, {'ovr_min': 70}) == N.filtrar(pool, {'media_min': 70})     # clave vieja
    print("  test_filtrar_min_max_y_libres: OK")


def test_filtros_overlay_aplicar():
    from alpha_football.ui import buscador_screen as B
    e = estado_carrera(); pygame.event.clear(); B.render(screen, e)
    click(B.R_FILTROS.center); B.render(screen, e); assert e['filtros_abierto'] and e['texto_activo']
    click(B.rect_campo('edad_max').center); B.render(screen, e)
    for d in '23':
        key(getattr(pygame, f'K_{d}'), d); B.render(screen, e)
    click(B.R_APLICAR.center); B.render(screen, e)
    assert not e['filtros_abierto'] and not e.get('texto_activo')
    assert e['busq_resultados'] and all(j.edad <= 23 for j, _c, _et in e['busq_resultados'])
    # LIMPIAR deja los filtros base en el borrador
    click(B.R_FILTROS.center); B.render(screen, e)
    click(B.R_LIMPIAR.center); B.render(screen, e)
    key(pygame.K_RETURN); B.render(screen, e)
    assert not e['filtros_abierto'] and e['busq']['filtros']['edad_max'] == B.FILTROS_BASE['edad_max']
    print("  test_filtros_overlay_aplicar: OK")


def test_filtros_teclas_no_escapan():
    from alpha_football.ui import buscador_screen as B
    e = estado_carrera(); pygame.event.clear(); B.render(screen, e)
    e['filtros_abierto'] = True
    key(pygame.K_ESCAPE)
    assert B.render(screen, e) is None and not e['filtros_abierto']      # ESC cierra el overlay, no sale
    print("  test_filtros_teclas_no_escapan: OK")


def test_solo_libres_toggle():
    from alpha_football.ui import buscador_screen as B
    from alpha_football import negociacion as N
    e = estado_carrera(); pygame.event.clear(); B.render(screen, e)
    click(B.R_SOLO_LIBRES.center); B.render(screen, e)
    assert e['busq']['filtros']['solo_libres'] and all(et == N.LIBRES for _j, _c, et in e['busq_resultados'])
    print("  test_solo_libres_toggle: OK")


# ---------------------------------------------------------------- Task 3: teclado, salida y foco
def test_opciones_teclado():
    from alpha_football.ui import options_screen as O
    e = estado_carrera(); e['opt_foco'] = 0
    key(pygame.K_DOWN); O.render(screen, e); assert e['opt_foco'] == 1
    key(pygame.K_UP); O.render(screen, e); assert e['opt_foco'] == 0
    items = O.items_opciones(e)          # v4.2.0: en carrera incluye GUARDAR
    key(pygame.K_UP); O.render(screen, e); assert e['opt_foco'] == len(items) - 1
    e['opt_foco'] = items.index('importar')
    key(pygame.K_RETURN); O.render(screen, e); assert e['opt_input_activo']
    key(pygame.K_ESCAPE); O.render(screen, e); assert not e['opt_input_activo']      # Esc suelta el campo
    e['opt_foco'] = items.index('playlist')
    key(pygame.K_RETURN); O.render(screen, e); assert e['opt_view'] == 'playlist'
    key(pygame.K_ESCAPE); O.render(screen, e); assert e['opt_view'] == 'main'
    key(pygame.K_ESCAPE); assert O.render(screen, e) is not None
    print("  test_opciones_teclado: OK")


def test_guardar_teclado():
    from alpha_football.ui import save_slots_screen as S
    e = estado_carrera(); e['slot_foco'] = 0
    key(pygame.K_DOWN); S.render(screen, e); assert e['slot_foco'] == 1
    key(pygame.K_UP); S.render(screen, e); assert e['slot_foco'] == 0
    guardados = []
    orig = save.guardar_en_slot
    save.guardar_en_slot = lambda ej, n, nombre: guardados.append(n)
    try:
        e['slot_foco'] = 2
        key(pygame.K_RETURN); assert S.render(screen, e) == 'league_screen'
    finally:
        save.guardar_en_slot = orig
    assert guardados == [3] and e['slot_activo'] == 3
    # Supr pide confirmación; Esc la cancela sin borrar
    borrados = []
    orig_b = save.eliminar_slot
    save.eliminar_slot = lambda n, *a, **k: borrados.append(n)
    try:
        key(pygame.K_DELETE); S.render(screen, e); assert e.get('slot_borrar') == 3
        key(pygame.K_ESCAPE); assert S.render(screen, e) is None and not e.get('slot_borrar') and not borrados
        key(pygame.K_DELETE); S.render(screen, e)
        key(pygame.K_RETURN); assert S.render(screen, e) is None and borrados == [3]
    finally:
        save.eliminar_slot = orig_b
    print("  test_guardar_teclado: OK")


def test_dialogo_salir():
    from alpha_football.ui import league_screen as L
    e = estado_carrera(); e['hub_tab'] = 'inicio'
    key(pygame.K_ESCAPE); L.render(screen, e); assert e['dialogo_salir']
    key(pygame.K_ESCAPE); L.render(screen, e); assert not e['dialogo_salir']          # cancelar
    key(pygame.K_ESCAPE); L.render(screen, e)
    key(pygame.K_s, 's'); assert L.render(screen, e) == 'menu'                          # sin guardar
    assert not e.get('dialogo_salir')
    guardados = []
    orig = save.guardar_en_slot
    save.guardar_en_slot = lambda ej, n, nombre: guardados.append(n)
    try:
        e['slot_activo'] = 4; e['dialogo_salir'] = True
        key(pygame.K_RETURN); assert L.render(screen, e) == 'menu' and guardados == [4]
    finally:
        save.guardar_en_slot = orig
    e['dialogo_salir'] = True
    click(L.R_SALIR_CANCELAR.center); L.render(screen, e); assert not e['dialogo_salir']
    print("  test_dialogo_salir: OK")


def test_salir_sin_slot():
    from alpha_football.ui import league_screen as L
    from alpha_football.ui import save_slots_screen as S
    e = estado_carrera(); e['hub_tab'] = 'inicio'; e.pop('slot_activo', None); e['dialogo_salir'] = True
    key(pygame.K_RETURN); assert L.render(screen, e) == 'save_slots_screen'
    assert e['salir_tras_guardar'] and not e.get('dialogo_salir')
    e['slot_foco'] = 0
    key(pygame.K_RETURN); assert S.render(screen, e) == 'menu' and not e.get('salir_tras_guardar')
    print("  test_salir_sin_slot: OK")


def test_esc_en_otra_pestana_vuelve_a_inicio():
    from alpha_football.ui import league_screen as L
    e = estado_carrera(); e['hub_tab'] = 'oficina'
    key(pygame.K_ESCAPE); L.render(screen, e); assert e['hub_tab'] == 'inicio' and not e.get('dialogo_salir')
    print("  test_esc_en_otra_pestana_vuelve_a_inicio: OK")


def test_foco_jugar_tras_copa():
    from alpha_football.ui import league_screen as L
    e = estado_carrera(); e['hub_tab'] = 'inicio'; e['hub_foco'] = 2; e['pantalla_anterior'] = 'copa_screen'
    pygame.event.clear(); L.render(screen, e)
    assert e['hub_foco'] == 0 and e['hub_tab'] == 'inicio'                              # 0 = JUGAR
    e['hub_foco'] = 1; e['pantalla_anterior'] = 'match_screen'
    pygame.event.clear(); L.render(screen, e); assert e['hub_foco'] == 0
    print("  test_foco_jugar_tras_copa: OK")


# ---------------------------------------------------------------- Task 4: barra de atajos y nota en vivo
def test_atajos_todas_las_pantallas():
    orig_get = pygame.event.get
    try:
        import main                                       # main parchea pygame.event.get al importarse
    finally:
        pygame.event.get = orig_get
    from alpha_football.ui import atajos as A
    nombres = main.nombres_pantallas()
    assert 'league_screen' in nombres and 'menu' in nombres
    for nombre in nombres:
        if nombre in A.SIN_BARRA:
            continue
        assert nombre in A.ATAJOS, nombre
        t = A.texto(nombre, {})
        assert "H Ayuda" in t and len(t) <= 150, nombre
    assert "ESC Inicio" in A.texto('league_screen', {'hub_tab': 'oficina'})
    print("  test_atajos_todas_las_pantallas: OK")


def test_atajos_por_defecto():
    from alpha_football.ui import atajos as A
    assert A.texto('pantalla_que_no_existe', {}) == "H Ayuda · ESC Volver"
    A.dibujar(screen, 'league_screen', {})
    A.dibujar(screen, 'pantalla_que_no_existe', None)
    print("  test_atajos_por_defecto: OK")


def test_nota_en_vivo():
    from alpha_football.ui import team_screen as T
    e = estado_carrera(); j = e['mi_equipo'].jugadores[e['mi_equipo'].alineacion_activa.titulares[0]]
    assert T.texto_nota_vivo(j, {'sim_nota_por_jugador': {j.id: 7.8}}) == ("7.8", 'verde')
    assert T.texto_nota_vivo(j, {'sim_nota_por_jugador': {j.id: 5.4}}) == ("5.4", 'rojo')
    assert T.texto_nota_vivo(j, {'sim_nota_por_jugador': {}}) == ("6.0", 'blanco')
    assert T.texto_nota_vivo(j, {}) is None
    print("  test_nota_en_vivo: OK")


# ---------------------------------------------------------------- Task 5: prepartido y editor
def test_prepartido_botones_caben():
    from alpha_football.ui import prepartido_screen as P
    from alpha_football.ui.theme import get_font
    for dir_hab in (True, False):
        for rival in (True, False):
            botones = P.botones_menu(dir_hab, rival)
            assert len(botones) == 5
            for texto, rect in botones:
                assert get_font('md').size(texto)[0] <= rect.width - 16, texto
                assert rect.bottom < 698, texto
            rects = [r for _t, r in botones]
            assert not any(a.colliderect(b) for i, a in enumerate(rects) for b in rects[i + 1:])
    print("  test_prepartido_botones_caben: OK")


def test_dropdown_rasgo_no_restaura():
    from alpha_football.ui import edit_screen as ED
    llamado = []
    orig = ED.restaurar_base
    ED.restaurar_base = lambda *a, **k: llamado.append(1)
    try:
        e = {}; pygame.event.clear(); ED.render(screen, e)             # inicializa el editor
        e['edit_dropdown_activo'] = 'rasgo'                            # (modo equipo: el rasgo no aplica)
        click(ED.R_RESTAURAR.center); ED.render(screen, e)
        assert not llamado and not e['edit_dropdown_activo']
        # con un jugador elegido, el clic sobre RESTAURAR BASE cae en un ítem del rasgo: lo cambia
        e['edit_jugador_idx'] = 0; pygame.event.clear(); ED.render(screen, e)
        e['edit_dropdown_activo'] = 'rasgo'
        valor = next(v for v, _t, r in ED._opciones_dropdown('rasgo') if r.collidepoint(ED.R_RESTAURAR.center))
        click(ED.R_RESTAURAR.center); ED.render(screen, e)
        db = ED.cargar_base_datos_inicial(e)
        jug = db[e['edit_liga_sel']][e['edit_equipo_idx']]['jugadores'][0]
        assert not llamado and jug.get('rasgo') == (None if valor == 'ninguno' else valor)
        # clic fuera con el dropdown abierto: solo lo cierra
        e['edit_dropdown_activo'] = 'estilo_dt'; e['edit_jugador_idx'] = -1
        click((5, 5)); assert ED.render(screen, e) is None and not e['edit_dropdown_activo']
    finally:
        ED.restaurar_base = orig
    print("  test_dropdown_rasgo_no_restaura: OK")


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
