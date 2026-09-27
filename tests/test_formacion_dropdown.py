"""Formaciones con hasta 4 tácticas afines, dropdown de formación y "?" de afines (sesión 2026-09-27)."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(5)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save, formaciones as F
from alpha_football.estilos import ESTILOS_DT
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402


def test_afines_hasta_4_y_validas():
    for f in F.lista_formaciones():
        af = F.afines(f)
        assert 1 <= len(af) <= 4 and len(set(af)) == len(af), f
        assert set(af) <= set(ESTILOS_DT), f
        assert F.pref(f) == af[0]
    assert any(len(F.afines(f)) > 1 for f in F.lista_formaciones())
    assert F.afines("no-existe") == ["anchelottismo"]
    print("  test_afines_hasta_4_y_validas: OK")


def test_motor_bonus_con_cualquier_afin():
    from alpha_football.engine import synergy_equipo
    e = estado_carrera(); mi = e['mi_equipo']
    f = next(f for f in F.lista_formaciones() if len(F.afines(f)) > 1)
    mi.alineacion_activa.formacion = f
    mi.tactica_familiaridad = {}
    mi.estilo_dt = F.afines(f)[1]
    con = synergy_equipo(mi)
    mi.estilo_dt = next(t for t in ESTILOS_DT if t not in F.afines(f))
    assert con > synergy_equipo(mi)
    print("  test_motor_bonus_con_cualquier_afin: OK")


def _ev(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode='')


def _direccion(e, click=None, evs=()):
    from alpha_football.ui import team_screen as TS
    mi = e['mi_equipo']
    return TS._render_direccion(screen, e, mi, mi.alineacion_activa, False, False, 'league_screen', (0, 0),
                                click, key_events=list(evs))


def test_dropdown_de_formacion():
    from alpha_football.ui import team_screen as TS
    e = estado_carrera(); alin = e['mi_equipo'].alineacion_activa
    rc = TS._rects_cabecera()
    assert 'form_prev' not in rc and 'form_ayuda' in rc
    _direccion(e, rc['form_box'].center)
    assert e.get('team_form_abierto')
    lista = F.lista_formaciones()
    destino = lista[5] if alin.formacion != lista[5] else lista[6]
    _direccion(e, TS._rects_lista_form(len(lista))[lista.index(destino)].center)
    assert alin.formacion == destino and not e.get('team_form_abierto')
    antes = list(alin.titulares)
    _direccion(e, rc['form_box'].center)                       # teclado: ↓ y Enter
    i = lista.index(alin.formacion)
    _direccion(e, evs=[_ev(pygame.K_DOWN), _ev(pygame.K_RETURN)])
    assert alin.formacion == lista[(i + 1) % len(lista)] and not e.get('team_form_abierto')
    _direccion(e, rc['form_box'].center)
    _direccion(e, evs=[_ev(pygame.K_ESCAPE)])                  # ESC cierra sin cancelar la dirección
    assert not e.get('team_form_abierto') and len(alin.titulares) == len(antes)
    print("  test_dropdown_de_formacion: OK")


def test_ayuda_de_afines():
    from alpha_football.ui import team_screen as TS
    e = estado_carrera()
    rc = TS._rects_cabecera()
    _direccion(e, rc['form_ayuda'].center)
    assert e.get('team_afines_abierto')
    textos, orig = [], TS.draw_text
    TS.draw_text = lambda s, t, *a, **k: textos.append(str(t))
    try:
        _direccion(e)
    finally:
        TS.draw_text = orig
    from alpha_football.estilos import NOMBRE_ESTILO
    f = e['mi_equipo'].alineacion_activa.formacion
    for t in F.afines(f):
        assert any(NOMBRE_ESTILO[t] in x for x in textos), t
    assert not any("Clic en un jugador para seleccionarlo" in x for x in textos)
    _direccion(e, (5, 700))
    assert not e.get('team_afines_abierto')
    print("  test_ayuda_de_afines: OK")


TESTS = [test_afines_hasta_4_y_validas, test_motor_bonus_con_cualquier_afin, test_dropdown_de_formacion,
         test_ayuda_de_afines]


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
