"""0.4.23.0: feed de noticias en el panel de la tabla del hub (pestaña NOTICIAS, tecla N)."""
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
from alpha_football.ui import league_screen as L


def _estado(importancias=(4, 4, 4), tab='noticias'):
    e = estado_carrera()
    e['datos_carrera']['aviso_mercado_visto'] = [1, '2026-07-01']   # sin el cartel del mercado (come clics y teclas)
    for i, imp in enumerate(importancias):
        N.publicar(e, 'resultado', f"Titular {i}", f"Cuerpo {i}", importancia=imp)
    e['hub_tab'] = 'inicio'
    e['hub_tabla_tab'] = tab
    return e


def _clic(pos):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def _tecla(t):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=t, unicode='', mod=0))


def test_feed_rota_cada_5_s():
    e = _estado()
    feed, i = L.feed_actual(e, 0)
    assert len(feed) == 3 and i == 0
    orden = [n['id'] for n in feed]
    assert [orden.index(L.feed_actual(e, ms)[0][L.feed_actual(e, ms)[1]]['id']) for ms in (0, 4999, 5000, 10000, 15000)] \
        == [0, 0, 1, 2, 0]
    assert orden == [n['id'] for n in N.para_feed(e)]                  # el orden es el de para_feed


def test_feed_solo_importancia_3_o_mas():
    e = _estado((2, 5, 1, 3))
    feed, _ = L.feed_actual(e, 0)
    assert sorted(n['importancia'] for n in feed) == [3, 5]
    vacio = _estado(())
    assert L.feed_actual(vacio, 0) == ([], 0)


def test_feed_no_recalcula_por_cuadro():
    e = _estado()
    n_llamadas = []
    original = N.para_feed
    N.para_feed = lambda estado: (n_llamadas.append(1), original(estado))[1]
    try:
        for ms in (0, 100, 200, 300, 400, 4000):                        # mismo paso de rotación y misma lista
            L.feed_actual(e, ms)
        assert len(n_llamadas) == 1
        L.feed_actual(e, 5000)                                          # cambia el paso: se refresca una vez
        assert len(n_llamadas) == 2
        N.publicar(e, 'fichaje', "Nueva", "Cuerpo", importancia=4)      # cambia la lista: se refresca
        L.feed_actual(e, 5100)
        assert len(n_llamadas) == 3
    finally:
        N.para_feed = original


def test_n_alterna_y_recuerda_la_pestana():
    e = {'hub_tabla_tab': 'liga'}
    L.alternar_noticias(e, 1000)
    assert e['hub_tabla_tab'] == 'noticias' and e['hub_tabla_prev'] == 'liga' and e['feed_fade_ms'] == 1000
    L.alternar_noticias(e, 2000)
    assert e['hub_tabla_tab'] == 'liga'
    e['hub_tabla_tab'] = 'copa'
    L.alternar_noticias(e, 3000)
    assert e['hub_tabla_tab'] == 'noticias'
    L.alternar_noticias(e, 4000)
    assert e['hub_tabla_tab'] == 'copa'
    L.alternar_noticias({}, 0)                                          # sin pestaña previa: no rompe


def test_pestanas_liga_y_copa_no_se_mueven():
    R = L.R_TABLA
    assert L.rect_tab_tabla('liga') == pygame.Rect(R.right - 212, R.y + 8, 96, 28)
    assert L.rect_tab_tabla('copa') == pygame.Rect(R.right - 108, R.y + 8, 96, 28)
    n = L.rect_tab_tabla('noticias')
    assert n.right < L.rect_tab_tabla('liga').left and n.top == L.rect_tab_tabla('liga').top
    assert R.contains(n)


def test_tarjeta_cabe_bajo_las_pestanas():
    assert L.R_TABLA.contains(L.R_TARJETA_FEED)
    assert L.R_TARJETA_FEED.size == (198, 352)
    assert L.R_TARJETA_FEED.top >= L.rect_tab_tabla('liga').bottom + 4
    assert L.R_TARJETA_FEED.centerx == L.R_TABLA.centerx


def test_hub_dibuja_con_y_sin_noticias():
    sin = _estado(())
    pygame.event.clear()
    assert L.render(screen, sin) is None                               # mensaje "sin noticias"
    con = _estado((5, 4, 3, 3, 4))
    for ms in (0, 3000):
        pygame.event.clear()
        assert L.render(screen, con) is None


def test_clic_en_la_tarjeta_abre_noticias():
    e = _estado()
    pygame.event.clear()
    L.render(screen, e)
    feed, i = L.feed_actual(e, pygame.time.get_ticks())
    _clic(L.R_TARJETA_FEED.center)
    assert L.render(screen, e) == 'noticias_screen'
    assert e['noticias_sel_id'] in {n['id'] for n in feed}


def test_clic_en_las_pestanas_de_la_tabla():
    e = _estado(tab='liga')
    pygame.event.clear()
    L.render(screen, e)
    _clic(L.rect_tab_tabla('noticias').center)
    L.render(screen, e)
    assert e['hub_tabla_tab'] == 'noticias' and e['hub_tabla_prev'] == 'liga'
    _clic(L.rect_tab_tabla('copa').center)
    L.render(screen, e)
    assert e['hub_tabla_tab'] == 'copa'
    _clic(L.rect_tab_tabla('noticias').center)
    L.render(screen, e)
    assert e['hub_tabla_tab'] == 'noticias' and e['hub_tabla_prev'] == 'copa'
    _clic(L.rect_tab_tabla('liga').center)
    L.render(screen, e)
    assert e['hub_tabla_tab'] == 'liga'


def test_tecla_n_en_el_hub():
    e = _estado(tab='liga')
    pygame.event.clear()
    L.render(screen, e)
    _tecla(pygame.K_n)
    L.render(screen, e)
    assert e['hub_tabla_tab'] == 'noticias'
    _tecla(pygame.K_n)
    L.render(screen, e)
    assert e['hub_tabla_tab'] == 'liga'
    e['hub_tab'] = 'oficina'                                           # en otra pestaña del hub, N no hace nada
    _tecla(pygame.K_n)
    L.render(screen, e)
    assert e['hub_tabla_tab'] == 'liga'


def test_atajos_del_hub_caben():
    from alpha_football.ui import atajos
    t = atajos.ATAJOS['league_screen']
    assert "N Noticias" in t and len(t) <= 150
    assert len(atajos.texto('league_screen', {'hub_tab': 'oficina'})) <= 150


def test_ayuda_del_hub_menciona_la_pestana():
    from alpha_football.ui import ayuda
    its = ayuda.items('league_screen', _estado())
    assert any("NOTICIAS" in t for _r, t, _x in its)
    for r, t, x in its:
        assert 0 <= r.x and r.right <= 1280 and 0 <= r.y and r.bottom <= 720 and len(x) <= 110, (t, len(x))


def test_oficina_cuenta_no_leidas_sin_recalcular_por_cuadro():
    e = _estado((4, 4, 4))
    e['hub_tab'] = 'oficina'
    original = N.no_leidas
    llamadas = []
    N.no_leidas = lambda estado: (llamadas.append(1), original(estado))[1]
    try:
        for _ in range(5):
            pygame.event.clear()
            L.render(screen, e)
        assert len(llamadas) == 1
        N.marcar_leida(e, N.lista(e)[0]['id'])                          # leer una noticia refresca el contador
        pygame.event.clear()
        L.render(screen, e)
        assert len(llamadas) == 2 and e['_hub_no_leidas_noticias'][1] == 2
    finally:
        N.no_leidas = original


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
