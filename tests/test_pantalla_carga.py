"""Pantallas de carga: guardar, cargar, pasar de temporada e iniciar carrera (sesión 2026-09-25)."""
import sys, os, random, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(5)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save
from alpha_football.ui import pantalla_carga as PC

save.guardar_en_slot = lambda *a, **k: None
save.guardar_partida = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402


class _Espia:
    """Registra las llamadas a pantalla_carga.mostrar (sigue dibujando de verdad)."""
    def __init__(self):
        self.llamadas, self._orig = [], PC.mostrar

    def __enter__(self):
        def espia(titulo, paso="", avance=None):
            self.llamadas.append((titulo, paso, avance))
            self._orig(titulo, paso, avance)
        PC.mostrar = espia
        return self

    def __exit__(self, *a):
        PC.mostrar = self._orig


def test_dibuja_titulo_y_barra():
    screen.fill((0, 0, 0))
    PC.mostrar("PASANDO DE TEMPORADA", "Retiros", 0.5)
    r = PC.R_BARRA
    lleno = screen.get_at((r.x + r.width // 4, r.centery))[:3]
    vacio = screen.get_at((r.x + r.width * 3 // 4, r.centery))[:3]
    assert lleno != vacio and lleno == PC.COLOR_BARRA, (lleno, vacio)
    PC.cerrar()
    print("  test_dibuja_titulo_y_barra: OK")


def test_minimo_visible():
    viejo = PC.MINIMO
    PC.MINIMO = 0.4
    try:
        t0 = time.monotonic()
        PC.mostrar("GUARDANDO PARTIDA")
        PC.cerrar()
        assert time.monotonic() - t0 >= 0.39
        t0 = time.monotonic()
        PC.cerrar()                                  # sin pantalla abierta: no espera
        assert time.monotonic() - t0 < 0.1
    finally:
        PC.MINIMO = viejo
    print("  test_minimo_visible: OK")


def test_lo_pulsado_durante_la_carga_se_descarta():
    # revisión final #2: un Enter durante la carga jugaba la jornada / firmaba el contrato
    pygame.event.clear()
    PC.mostrar("PASANDO DE TEMPORADA", "Retiros", 0.5)
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode='\r'))
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(10, 10)))
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    PC.cerrar()
    tipos = [ev.type for ev in pygame.event.get()]
    assert pygame.KEYDOWN not in tipos and pygame.MOUSEBUTTONDOWN not in tipos and pygame.QUIT in tipos, tipos
    print("  test_lo_pulsado_durante_la_carga_se_descarta: OK")


def test_error_al_dibujar_no_corta_el_proceso():
    orig = PC._dibujar
    PC._dibujar = lambda *a, **k: 1 / 0
    try:
        PC.mostrar("GUARDANDO PARTIDA")              # solo loggea
        PC.cerrar()
    finally:
        PC._dibujar = orig
    print("  test_error_al_dibujar_no_corta_el_proceso: OK")


def test_guardar_muestra_carga():
    from alpha_football.ui import save_slots_screen as SS
    e = estado_carrera()
    with _Espia() as es:
        SS.guardar_slot(e, 2)
    assert es.llamadas and es.llamadas[0][0] == "GUARDANDO PARTIDA", es.llamadas
    e['save_slots_return'] = 'league_screen'
    save.listar_slots = lambda: [None] * 5
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=SS.rect_slot(0).center))
    with _Espia() as es:
        SS.render(screen, e)
    assert es.llamadas and es.llamadas[0][0] == "GUARDANDO PARTIDA", es.llamadas
    assert PC._inicio is None, "la pantalla de carga se cerró"
    print("  test_guardar_muestra_carga: OK")


def test_temporada_sin_liga_no_muestra_carga():
    from alpha_football.ui.resumen_temporada_screen import avanzar_nueva_temporada
    with _Espia() as es:
        avanzar_nueva_temporada({})
    assert es.llamadas == [] and PC._inicio is None, es.llamadas
    print("  test_temporada_sin_liga_no_muestra_carga: OK")


def test_cargar_muestra_carga():
    from alpha_football.ui import menu as M
    e = {'menu_step': 'load_slots'}
    save.listar_slots = lambda: [{'nombre_partida': 'X', 'temporada': 1, 'jornada': 1}] + [None] * 4
    save.cargar_slot = lambda n: {'falso': n}
    orig = M._aplicar_estado_cargado
    M._aplicar_estado_cargado = lambda estado, loaded: True
    try:
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=M.rects_slots_carga()[0][0].center))
        with _Espia() as es:
            res = M.render(screen, e)
    finally:
        M._aplicar_estado_cargado = orig
    assert res == 'league_screen' and es.llamadas and es.llamadas[0][0] == "CARGANDO PARTIDA", (res, es.llamadas)
    assert PC._inicio is None
    print("  test_cargar_muestra_carga: OK")


def test_pasar_de_temporada_con_pasos():
    from alpha_football.ui.resumen_temporada_screen import avanzar_nueva_temporada
    e = estado_carrera()
    for p in getattr(e['liga'], 'calendario', []) or []:
        p.jugado = True
    with _Espia() as es:
        avanzar_nueva_temporada(e)
    assert e['temporada'] == 2
    avances = [a for t, _p, a in es.llamadas if t == "PASANDO DE TEMPORADA"]
    assert len(avances) >= 4 and avances == sorted(avances) and avances[-1] == 1.0, es.llamadas
    assert all(p for _t, p, _a in es.llamadas), "cada paso dice qué está haciendo"
    assert PC._inicio is None
    print("  test_pasar_de_temporada_con_pasos: OK")


def test_iniciar_carrera_con_pasos():
    from alpha_football.ui import menu as M
    liga = M.load_league_teams('premier')
    e = {'menu_step': 'dt_setup', 'pending_equipo': liga.equipos[0], 'selected_liga_obj': liga,
         'selected_country_id': 'inglaterra', 'selected_division': 1,
         'dt_nombre': 'DT Prueba', 'dt_nac_sel': 'Colombia', 'dt_focus': None}
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode='\r'))
    with _Espia() as es:
        res = M.render(screen, e)
    assert res == 'contrato_dt_screen', res
    avances = [a for t, _p, a in es.llamadas if t == "INICIANDO CARRERA"]
    assert len(avances) >= 3 and avances == sorted(avances) and avances[-1] == 1.0, es.llamadas
    assert PC._inicio is None
    print("  test_iniciar_carrera_con_pasos: OK")


TESTS = [test_dibuja_titulo_y_barra, test_minimo_visible, test_lo_pulsado_durante_la_carga_se_descarta,
         test_error_al_dibujar_no_corta_el_proceso,
         test_guardar_muestra_carga, test_temporada_sin_liga_no_muestra_carga, test_cargar_muestra_carga, test_pasar_de_temporada_con_pasos,
         test_iniciar_carrera_con_pasos]


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
