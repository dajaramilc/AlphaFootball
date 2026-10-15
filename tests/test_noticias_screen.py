"""0.4.23.0: pantalla OFICINA > NOTICIAS (lista + detalle), su tarjeta en OFICINA y su registro."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
screen = pygame.display.set_mode((1280, 720))
from alpha_football import save
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402

from alpha_football import noticias as N
from alpha_football.ui import noticias_screen as NS
from alpha_football.ui import league_screen as L


def _estado(n=12, **extra):
    e = estado_carrera()
    e['datos_carrera']['aviso_mercado_visto'] = [1, '2026-07-01']   # sin el cartel de apertura del mercado (come los clics)
    for i in range(n):
        N.publicar(e, 'resultado', f"Titular número {i}", f"Cuerpo de la noticia {i}. " * 6,
                   importancia=1 + (i % 5), **extra)
    return e


def _clic(pos):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def _tecla(tecla):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=tecla, unicode='', mod=0))


def _frame(e):
    pygame.event.clear()
    return NS.render(screen, e)


def test_dibuja_con_lista_y_vacia():
    e = estado_carrera()
    assert _frame(e) is None                                    # sin noticias: mensaje
    e = _estado(12)
    assert _frame(e) is None


def test_flechas_marcan_leida():
    e = _estado(4)
    assert N.no_leidas(e) == 4
    _frame(e)                                                   # la primera queda a la vista y se marca leída
    assert e['noticias_sel'] == 0 and N.no_leidas(e) == 3
    _tecla(pygame.K_DOWN); NS.render(screen, e)
    assert e['noticias_sel'] == 1 and N.no_leidas(e) == 2
    _tecla(pygame.K_DOWN); NS.render(screen, e)
    _tecla(pygame.K_DOWN); NS.render(screen, e)
    assert e['noticias_sel'] == 3 and N.no_leidas(e) == 0
    _tecla(pygame.K_DOWN); NS.render(screen, e)
    assert e['noticias_sel'] == 3                               # no pasa del final
    _tecla(pygame.K_UP); NS.render(screen, e)
    assert e['noticias_sel'] == 2
    for _ in range(5):
        _tecla(pygame.K_UP); NS.render(screen, e)
    assert e['noticias_sel'] == 0                               # ni del principio


def test_repag_avpag_saltan_10():
    e = _estado(14)
    _frame(e)
    _tecla(pygame.K_PAGEDOWN); NS.render(screen, e)
    assert e['noticias_sel'] == 10
    _tecla(pygame.K_PAGEDOWN); NS.render(screen, e)
    assert e['noticias_sel'] == len(N.activas(e)) - 1
    _tecla(pygame.K_PAGEUP); NS.render(screen, e)
    assert e['noticias_sel'] == len(N.activas(e)) - 1 - 10


def test_esc_vuelve_al_hub():
    e = _estado(3)
    _tecla(pygame.K_ESCAPE)
    assert NS.render(screen, e) == 'league_screen'
    _tecla(pygame.K_BACKSPACE)
    assert NS.render(screen, e) == 'league_screen'
    pygame.event.clear(); pygame.event.post(pygame.event.Event(pygame.QUIT))
    assert NS.render(screen, e) == 'menu'
    _clic(NS._volver().center)
    assert NS.render(screen, e) == 'league_screen'


def test_clic_en_fila_selecciona():
    e = _estado(8)
    _frame(e)
    _clic(NS.rect_fila(3).center)
    assert NS.render(screen, e) is None
    assert e['noticias_sel'] == 3


def test_rueda_desplaza_la_lista_sin_pasarse():
    e = _estado(30)                                             # el tope de la lista llega a 30 noticias vivas
    _frame(e)
    for _ in range(40):
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=-1))
        NS.render(screen, e)
    total = len(N.activas(e))
    assert 0 <= e['noticias_scroll'] <= max(0, total - NS.FILAS_VISIBLES)
    for _ in range(60):
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=1))
        NS.render(screen, e)
    assert e['noticias_scroll'] == 0


def test_abrir_desde_el_feed_selecciona_por_id():
    e = _estado(8)
    objetivo = N.activas(e)[5]
    assert NS.abrir(e, objetivo['id']) == 'noticias_screen'
    _frame(e)
    assert N.activas(e)[e['noticias_sel']]['id'] == objetivo['id']
    assert objetivo['leida'] is True and 'noticias_sel_id' not in e
    assert NS.abrir(e, 999999) == 'noticias_screen'             # id que ya caducó: no rompe
    assert _frame(e) is None


def test_boton_accion():
    e = _estado(2)
    n = N.publicar(e, 'economia', "Remate de un club", "Cuerpo", importancia=5,
                   accion={'pantalla': 'buscador_screen', 'texto': "VER REMATADOS"})
    NS.abrir(e, n['id'])
    _frame(e)
    _tecla(pygame.K_RETURN)
    assert NS.render(screen, e) == 'buscador_screen'
    _clic(NS.R_ACCION.center)
    assert NS.render(screen, e) == 'buscador_screen'
    sin = _estado(2)                                            # sin `accion`: Enter y el clic no hacen nada
    _frame(sin)
    _tecla(pygame.K_RETURN)
    assert NS.render(screen, sin) is None
    _clic(NS.R_ACCION.center)
    assert NS.render(screen, sin) is None


def test_registro_en_main_ayuda_y_atajos():
    orig_get = pygame.event.get
    try:
        import main
    finally:
        pygame.event.get = orig_get
    from alpha_football.ui import ayuda, atajos
    assert main.MODULOS_PANTALLA['noticias_screen'].endswith('noticias_screen')
    its = ayuda.items('noticias_screen', estado_carrera())
    assert len(its) >= 3
    for r, t, x in its:
        assert 0 <= r.x and r.right <= 1280 and 0 <= r.y and r.bottom <= 720, (t, r)
        assert t and x and len(x) <= 110, (t, len(x))
    t = atajos.ATAJOS['noticias_screen']
    assert "H Ayuda" in t and len(t) <= 150


def test_tarjeta_noticias_en_oficina():
    assert L.TARJETAS['oficina'][0][2] == 'notificaciones_screen'
    assert L.TARJETAS['oficina'][1][2] == 'noticias_screen' and len(L.TARJETAS['oficina']) == 9


def test_oficina_de_9_cabe_en_pantalla():
    for n in (9, 10, 12):
        rs = L._rects_tarjetas(n)
        assert len(rs) == n
        for i, r in enumerate(rs):
            assert r.x >= 0 and r.right <= 1280 and r.bottom <= 696, (n, i, r)
            assert all(not r.colliderect(o) for o in rs[i + 1:]), (n, i)
    assert [r.width for r in L._rects_tarjetas(8)] == [440] * 8      # con 8 o menos sigue igual
    assert len({r.x for r in L._rects_tarjetas(8)}) == 2


def test_hub_oficina_dibuja_y_cuenta_no_leidas():
    e = _estado(5)
    e['hub_tab'] = 'oficina'
    pygame.event.clear()
    assert L.render(screen, e) is None
    assert N.no_leidas(e) == 5                                  # el hub no marca nada como leído


def test_hub_abre_noticias_con_enter_y_clic():
    e = _estado(3)
    e['hub_tab'] = 'oficina'
    L.render(screen, e)
    rect = L._rects_tarjetas(len(L.TARJETAS['oficina']))[1]
    _clic(rect.center)
    assert L.render(screen, e) == 'noticias_screen'


def test_muestra_la_fecha_real_y_no_temporada_jornada():
    """v0.4.24.0: el detalle y las filas muestran la fecha real; 'Temporada X – Jornada Y' solo si no hay fecha."""
    e = _estado(2)
    for n in N.lista(e):
        n['fecha_creacion'] = '2026-09-12'
    dibujado = []
    original = NS.draw_text
    NS.draw_text = lambda scr, texto, *a, **k: dibujado.append(str(texto))
    try:
        assert _frame(e) is None
    finally:
        NS.draw_text = original
    assert "sáb 12 sep 2026" in dibujado                        # detalle de la noticia elegida
    assert "sáb 12 sep" in dibujado                             # filas de la lista
    assert not any(t.startswith("Temporada ") for t in dibujado)
    for n in N.lista(e):
        n['fecha_creacion'] = None
    dibujado.clear()
    NS.draw_text = lambda scr, texto, *a, **k: dibujado.append(str(texto))
    try:
        _frame(e)
    finally:
        NS.draw_text = original
    assert any(t.startswith("Temporada ") for t in dibujado)    # sin fecha real: respaldo


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
