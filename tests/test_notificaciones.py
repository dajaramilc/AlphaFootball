"""v0.4.10.0: NOTIFICACIONES = MENSAJES (jugadores y presidente) + CORREO (club)."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
screen = pygame.display.set_mode((1280, 720))
from alpha_football import save
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402

from alpha_football import correo as C


def test_canal_por_remitente_y_explicito():
    e = estado_carrera()
    a = C.enviar(e, 'jugador', "a", "x")
    b = C.enviar(e, 'presidente', "b", "x")
    c = C.enviar(e, 'directiva', "c", "x")
    d = C.enviar(e, 'medico', "d", "x")
    assert [C.canal(m) for m in (a, b, c, d)] == ['mensaje', 'mensaje', 'correo', 'correo']
    d['canal'] = 'mensaje'
    assert C.canal(d) == 'mensaje'
    assert C.canal({'remitente': 'jugador', 'asunto': 'save viejo'}) == 'mensaje'


def test_de_canal_y_no_leidos():
    e = estado_carrera()
    for i in range(7):
        C.enviar(e, 'jugador', f"m{i}", "x")
    for i in range(3):
        C.enviar(e, 'club', f"c{i}", "x")
    assert [m['asunto'] for m in C.de_canal(e, 'mensaje')[:5]] == ['m6', 'm5', 'm4', 'm3', 'm2']
    assert len(C.de_canal(e, 'correo')) == 3
    assert (C.no_leidos(e), C.no_leidos(e, 'mensaje'), C.no_leidos(e, 'correo')) == (10, 7, 3)
    C.marcar_leido(e, C.de_canal(e, 'correo')[0]['id'])
    assert (C.no_leidos(e), C.no_leidos(e, 'correo')) == (9, 2)


def test_presidente_escribe_sin_plantilla_formal():
    e = estado_carrera(); e['dt_nombre'] = "Diego Jaramillo"
    m = C.enviar(e, 'presidente', "Bien hecho", "Así se gana un clásico.")
    texto = C.formatear(e, m)
    assert "Estimado" not in texto and "Atentamente" not in texto
    assert texto.endswith("El presidente")
    assert "Atentamente" in C.formatear(e, C.enviar(e, 'directiva', "Objetivos", "…"))


def test_portada_y_lista_filtrada():
    from alpha_football.ui import notificaciones_screen as NS, correo_screen as CS
    e = estado_carrera()
    for i in range(7):
        C.enviar(e, 'jugador', f"m{i}", "hola míster")
    C.enviar(e, 'club', "c0", "informe")
    assert [m['asunto'] for m in NS.ultimos(e, 'mensaje')] == ['m6', 'm5', 'm4', 'm3', 'm2']
    assert NS.render(screen, e) is None                       # dibuja sin romperse
    m3 = next(m for m in C.bandeja(e) if m['asunto'] == 'm3')
    assert NS.abrir(e, 'mensaje', m3) == 'correo_screen'
    assert e['correo_canal'] == 'mensaje' and CS._mensajes(e)[e['correo_sel']] is m3
    assert all(C.canal(m) == 'mensaje' for m in CS._mensajes(e))
    assert NS.abrir(e, 'correo') == 'correo_screen' and e['correo_sel'] == 0
    assert [m['asunto'] for m in CS._mensajes(e)] == ['c0']
    assert CS.render(screen, e) is None


def test_m_abre_notificaciones_y_hub():
    import main
    from alpha_football.ui import league_screen
    assert main.MODULOS_PANTALLA['notificaciones_screen'].endswith('notificaciones_screen')
    assert any(t[2] == 'notificaciones_screen' and t[0] == "NOTIFICACIONES"
               for t in league_screen.TARJETAS['oficina'])


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
