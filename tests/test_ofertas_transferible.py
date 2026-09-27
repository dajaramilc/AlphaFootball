"""Ofertas por jugadores transferibles: la tarjeta y el correo lo marcan (sesión 2026-09-26)."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(5)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save, correo as C
from alpha_football.ui import ofertas_screen as O, match_screen as M

save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402


def _oferta(e, transferible):
    j = e['mi_equipo'].jugadores[0]
    j.transferible = transferible
    return {'jugador': j, 'comprador': e['liga'].equipos[3], 'monto': 5_000_000}


def _textos_tarjeta(of):
    textos, original = [], O.draw_text
    O.draw_text = lambda s, t, *a, **k: textos.append(t)
    try:
        O._dibujar_tarjeta(screen, O.rect_oferta(0), of, False, (0, 0))
    finally:
        O.draw_text = original
    return textos


def test_tarjeta_marca_transferible():
    e = estado_carrera()
    assert "TRANSFERIBLE" in _textos_tarjeta(_oferta(e, True))
    assert "TRANSFERIBLE" not in _textos_tarjeta(_oferta(e, False))
    print("  test_tarjeta_marca_transferible: OK")


def test_correo_marca_transferible():
    e = estado_carrera()
    M._correo_oferta(e, _oferta(e, True), "Oferta por")
    assert "transferibles" in C.bandeja(e)[0]['cuerpo']
    e = estado_carrera()
    M._correo_oferta(e, _oferta(e, False), "Oferta por")
    assert "transferibles" not in C.bandeja(e)[0]['cuerpo']
    print("  test_correo_marca_transferible: OK")


TESTS = [test_tarjeta_marca_transferible, test_correo_marca_transferible]


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
