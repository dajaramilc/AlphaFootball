"""v3.9.0: ayuda con la tecla H — overlay que numera y explica cada zona de la pantalla."""
import sys, os, random, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(13)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save, competiciones as CP
from alpha_football.models import alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams, _ligas_por_division
from alpha_football.ui import ayuda as AY

_tmp = tempfile.mkdtemp()
save.guardar_en_slot = lambda *a, **k: None          # los tests no tocan los slots reales


def _main():
    """Importa main sin dejar parcheado pygame.event.get (main lo reemplaza al importarse)."""
    orig_get = pygame.event.get
    try:
        import main
    finally:
        pygame.event.get = orig_get
    return main


def kd(k, u=''):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=u)


def estado_carrera(tipo='premier', idx=None):
    liga = load_league_teams(tipo)
    if idx is None:
        idx = max(range(len(liga.equipos)), key=lambda i: liga.equipos[i].ovr_promedio)
    mi = liga.equipos[idx]
    mi.alineacion_activa = alineacion_por_defecto(mi)
    primeras, segunda = _ligas_por_division(liga, {}, {})
    e = {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
         'alineacion_activa': mi.alineacion_activa, 'primera_division': primeras,
         'segunda_division': segunda, 'datos_carrera': {}, 'historial': []}
    CP.iniciar_temporada(e, random.Random(5))
    return e


# ---------------------------------------------------------------- Task 1: motor del overlay
def test_h_abre_y_cierra():
    e = {}
    assert AY.manejar_evento(e, kd(pygame.K_h, 'h'), 'league_screen') and e['ayuda_abierta']
    assert AY.manejar_evento(e, kd(pygame.K_ESCAPE), 'league_screen') and not e['ayuda_abierta']
    assert AY.manejar_evento(e, kd(pygame.K_h, 'h'), 'league_screen') and e['ayuda_abierta']
    assert AY.manejar_evento(e, kd(pygame.K_h, 'h'), 'league_screen') and not e['ayuda_abierta']
    # cerrada, otras teclas no se consumen
    assert not AY.manejar_evento(e, kd(pygame.K_ESCAPE), 'league_screen')
    print("  test_h_abre_y_cierra: OK")


def test_h_con_texto_activo():
    e = {'texto_activo': True}
    assert not AY.manejar_evento(e, kd(pygame.K_h, 'h'), 'buscador_screen') and not e.get('ayuda_abierta')
    print("  test_h_con_texto_activo: OK")


def test_eventos_bloqueados():
    e = {'ayuda_abierta': True}
    ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(100, 100))
    assert AY.manejar_evento(e, ev, 'league_screen')
    assert AY.manejar_evento(e, kd(pygame.K_RETURN), 'league_screen') and e['ayuda_abierta']
    # QUIT nunca se consume (la ventana se puede cerrar con la ayuda abierta)
    assert not AY.manejar_evento(e, pygame.event.Event(pygame.QUIT), 'league_screen')
    print("  test_eventos_bloqueados: OK")


def test_paginado():
    AY.AYUDA['_prueba'] = [(pygame.Rect(10 + i * 20, 10, 10, 10), f"T{i}", "texto") for i in range(23)]
    try:
        e = {'ayuda_abierta': True}
        AY.dibujar(screen, '_prueba', e); assert e.get('ayuda_pagina', 0) == 0
        AY.manejar_evento(e, kd(pygame.K_RIGHT), '_prueba'); assert e['ayuda_pagina'] == 1
        AY.manejar_evento(e, kd(pygame.K_RIGHT), '_prueba'); AY.manejar_evento(e, kd(pygame.K_RIGHT), '_prueba')
        assert e['ayuda_pagina'] == 2                      # 23 items / 10 = 3 páginas
        AY.dibujar(screen, '_prueba', e)
        AY.manejar_evento(e, kd(pygame.K_LEFT), '_prueba'); assert e['ayuda_pagina'] == 1
        AY.manejar_evento(e, kd(pygame.K_ESCAPE), '_prueba'); assert e['ayuda_pagina'] == 0
    finally:
        del AY.AYUDA['_prueba']
    print("  test_paginado: OK")


def test_pantalla_sin_ayuda():
    e = {'ayuda_abierta': True}
    assert AY.items('no_existe', e) == [] and AY.dibujar(screen, 'no_existe', e) is None
    print("  test_pantalla_sin_ayuda: OK")


def test_main_filtra_eventos():
    """main: con la ayuda abierta la pantalla no ve el clic; texto activo se limpia al cambiar de pantalla."""
    main = _main()
    e = {'ayuda_abierta': True, 'current_screen': 'league_screen'}
    evs = [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(100, 100)), pygame.event.Event(pygame.QUIT)]
    quedan = main.filtrar_eventos_ayuda(e, evs)
    assert [ev.type for ev in quedan] == [pygame.QUIT]
    e = {'current_screen': 'league_screen'}
    quedan = main.filtrar_eventos_ayuda(e, [kd(pygame.K_j, 'j'), kd(pygame.K_h, 'h')])   # J pasa, H abre
    assert e['ayuda_abierta'] and [ev.key for ev in quedan] == [pygame.K_j]
    print("  test_main_filtra_eventos: OK")


# ---------------------------------------------------------------- Task 2: contenido
def test_cobertura_total():
    main = _main()
    faltan = [n for n in main.nombres_pantallas() if n not in AY.AYUDA]
    assert not faltan, faltan
    print("  test_cobertura_total: OK")


def test_items_validos():
    main = _main()
    e = estado_carrera()
    for n in main.nombres_pantallas():
        its = AY.items(n, e)
        minimo = 2 if n in ('menu', 'veredicto_screen', 'despido_screen') else 3
        assert len(its) >= minimo, (n, len(its))
        for r, t, x in its:
            assert 0 <= r.x and r.right <= 1280 and 0 <= r.y and r.bottom <= 720, (n, t, r)
            assert t and x and len(x) <= 110, (n, t, len(x))
        e2 = dict(e); e2['ayuda_abierta'] = True
        AY.dibujar(screen, n, e2)
    print("  test_items_validos: OK")


def test_hub_por_pestana():
    e = estado_carrera()
    e['hub_tab'] = 'inicio'; a = [t for _r, t, _x in AY.items('league_screen', e)]
    e['hub_tab'] = 'oficina'; b = [t for _r, t, _x in AY.items('league_screen', e)]
    assert a != b
    print("  test_hub_por_pestana: OK")


def click(pos):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def test_texto_activo_en_pantallas():
    """Buscador (nombre), editor y alta del DT marcan texto_activo mientras un campo recibe teclas."""
    from alpha_football.ui import buscador_screen as B, edit_screen as ED, menu as MN
    e = estado_carrera()
    pygame.event.clear(); B.render(screen, e)
    click(B._rects()['nombre'].center); B.render(screen, e)
    pygame.event.clear(); B.render(screen, e)
    assert e['texto_activo']
    AY.manejar_evento(e, kd(pygame.K_h, 'h'), 'buscador_screen'); assert not e.get('ayuda_abierta')
    click((640, 700)); B.render(screen, e)                       # clic fuera del campo: lo suelta
    pygame.event.clear(); B.render(screen, e)
    assert not e['texto_activo']
    e['edit_input_activo'] = 'team_name'; pygame.event.clear(); ED.render(screen, e)
    assert e['texto_activo']
    e['edit_input_activo'] = None; pygame.event.clear(); ED.render(screen, e)
    assert not e['texto_activo']
    m = {'menu_step': 'dt_setup', 'dt_focus': 'name'}
    pygame.event.clear(); MN.render(screen, m); assert m['texto_activo']
    m['menu_step'] = 'main'; pygame.event.clear(); MN.render(screen, m); assert not m['texto_activo']
    print("  test_texto_activo_en_pantallas: OK")


def test_reloj_del_partido_pausado():
    """Con la ayuda abierta el partido en vivo no avanza."""
    from alpha_football.ui import match_screen as MS, league_screen as LS
    e = estado_carrera()
    liga, mi = e['liga'], e['mi_equipo']
    if not getattr(liga, 'calendario', None):
        LS.inicializar_calendario_liga(liga)
    liga.jornada_actual = 1
    e['partido_actual'] = next(p for p in liga.calendario if p.jornada == 1 and mi.id in (p.local_id, p.visitante_id))
    e['match_mode'] = 'liga'
    pygame.event.clear(); MS.render(screen, e)
    e['sim_estado'], e['sim_flash_goles'], e['sim_last_tick'] = 'jugando', 0, -10_000
    m0 = e['sim_minuto']
    e['ayuda_abierta'] = True
    pygame.event.clear(); MS.render(screen, e)
    assert e['sim_minuto'] == m0
    e['ayuda_abierta'] = False
    pygame.event.clear(); MS.render(screen, e)
    assert e['sim_minuto'] == m0 + 1
    print("  test_reloj_del_partido_pausado: OK")


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
