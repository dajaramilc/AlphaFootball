"""Botón de pantalla completa en OPCIONES (sesión 2026-09-27)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
screen = pygame.display.set_mode((1280, 720))

from alpha_football import audio
from alpha_football.ui import options_screen as O

guardadas = {}
audio.guardar_preferencias = lambda p: guardadas.update(p)
cambios = []
pygame.display.toggle_fullscreen = lambda: cambios.append(1) or 1


def _click(pos):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def test_boton_alterna_y_guarda():
    e = {'pantalla_completa': False}
    _click(O.rects_opciones()['pantalla'].center); O.render(screen, e)
    assert e['pantalla_completa'] is True and guardadas.get('pantalla_completa') is True and len(cambios) == 1
    _click(O.rects_opciones()['pantalla'].center); O.render(screen, e)
    assert e['pantalla_completa'] is False and guardadas.get('pantalla_completa') is False and len(cambios) == 2
    print("  test_boton_alterna_y_guarda: OK")


def test_teclado_y_orden():
    e = {'mi_equipo': object(), 'pantalla_completa': False}
    assert O.items_opciones(e) == ['volumen', 'pantalla', 'importar', 'volver', 'guardar', 'playlist']
    assert O.items_opciones({}) == ['volumen', 'pantalla', 'importar', 'volver', 'playlist']
    e['opt_foco'] = 1
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode='\r'))
    O.render(screen, e)
    assert e['pantalla_completa'] is True
    print("  test_teclado_y_orden: OK")


def test_preferencia_por_defecto():
    assert audio._PREFS_DEFECTO.get('pantalla_completa') is False
    print("  test_preferencia_por_defecto: OK")


TESTS = [test_boton_alterna_y_guarda, test_teclado_y_orden, test_preferencia_por_defecto]


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
