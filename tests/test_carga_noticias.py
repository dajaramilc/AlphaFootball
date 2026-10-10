"""0.4.23.0: pantalla de carga de temporada con titulares de noticias pasando."""
import sys, os, copy, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save
save.guardar_en_slot = lambda *a, **k: None
save.guardar_partida = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402

from alpha_football import noticias as N
from alpha_football.ui import pantalla_carga as PC

_BASE = None


def _estado():
    global _BASE
    if _BASE is None:
        _BASE = estado_carrera()
    return copy.deepcopy(_BASE)


def _noticia(i=1, categoria='resultado'):
    return {'id': i, 'tipo': 'resultado', 'categoria': categoria, 'titular': f"Titular de prueba {i}",
            'cuerpo': "x", 'temporada': 1, 'jornada': 1, 'importancia': 4}


class _Espia:
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


def _sin_imagenes():
    orig = N.imagen
    N.imagen = lambda noticia: None
    return orig


def test_sin_titulares_dibuja_como_antes():
    PC.fijar_titulares(None)
    screen.fill((0, 0, 0))
    PC._dibujar(screen, "PASANDO DE TEMPORADA", "Retiros", 0.5)
    r = PC.R_BARRA
    assert screen.get_at((r.x + r.width // 4, r.centery))[:3] == PC.COLOR_BARRA
    zona = screen.subsurface(PC.R_TITULARES).copy()
    sin = [tuple(zona.get_at((x, y)))[:3] for x in (5, 100, 200) for y in (5, 150, 380)]
    PC.fijar_titulares([_noticia()])
    orig = _sin_imagenes()
    try:
        PC._dibujar(screen, "PASANDO DE TEMPORADA", "Retiros", 0.5, transcurrido=1.75)
    finally:
        N.imagen = orig
        PC.fijar_titulares(None)
    zona2 = screen.subsurface(PC.R_TITULARES).copy()
    con = [tuple(zona2.get_at((x, y)))[:3] for x in (5, 100, 200) for y in (5, 150, 380)]
    assert con != sin                                                    # con titulares la zona derecha cambia
    assert screen.get_at((r.x + r.width // 4, r.centery))[:3] == PC.COLOR_BARRA   # y la barra sigue en su lugar


def test_titulares_no_pisan_titulo_ni_barra():
    assert PC.R_TITULARES.left > PC.R_BARRA.right and PC.R_TITULARES.right <= 1280 and PC.R_TITULARES.bottom <= 720


def test_el_indice_rota_por_tiempo():
    i0, a0 = PC.titular_vigente(2, 0.0)
    assert i0 == 0 and a0 == 0                                          # entra con fundido: empieza transparente
    i1, a1 = PC.titular_vigente(2, 1.75)
    assert i1 == 0 and a1 == 255                                        # a mitad de tramo, opaca
    assert PC.titular_vigente(2, 3.6)[0] == 1
    assert PC.titular_vigente(2, 7.2)[0] == 0
    assert 0 < PC.titular_vigente(2, PC.SEGUNDOS_POR_TITULAR - 0.1)[1] < 255   # sale con fundido
    assert PC.titular_vigente(0, 5.0) == (0, 0)                         # sin titulares no hay nada que mostrar
    assert PC.titular_vigente(1, 99.0)[0] == 0


def test_cerrar_con_minimo_espera_y_redibuja():
    reloj = [1000.0]
    original = (time.monotonic, time.sleep, PC._dibujar)
    dibujos = []
    time.monotonic = lambda: reloj[0]
    time.sleep = lambda s: reloj.__setitem__(0, reloj[0] + s)
    PC._dibujar = lambda *a, **k: dibujos.append(1)
    PC._inicio = None
    try:
        PC.mostrar("PASANDO DE TEMPORADA", "Listo", 1.0)
        n0 = len(dibujos)
        PC.cerrar(minimo=1.0)
        assert reloj[0] - 1000.0 >= 1.0 - 1e-6                           # esperó el mínimo
        assert len(dibujos) - n0 >= 5                                    # y redibujó mientras tanto (animación)
        assert PC._inicio is None
        PC.mostrar("GUARDANDO PARTIDA")
        t0 = reloj[0]
        PC.cerrar()                                                      # sin argumento: el mínimo de siempre
        assert abs((reloj[0] - t0) - PC.MINIMO) < 0.06 or PC.MINIMO == 0.0
    finally:
        time.monotonic, time.sleep, PC._dibujar = original
        PC._inicio = None


def test_minimo_de_temporada_es_cero_en_tests_y_mayor_que_el_normal_en_juego():
    assert PC.MINIMO_TEMPORADA == 0.0                                    # SDL dummy
    assert PC._minimo_temporada(real=True) >= 3.0 and PC._minimo_temporada(real=False) == 0.0


def test_temporada_usa_los_textos_nuevos_y_limpia_los_titulares():
    from alpha_football.ui.resumen_temporada_screen import avanzar_nueva_temporada
    e = _estado()
    with _Espia() as es:
        avanzar_nueva_temporada(e)
    assert e['temporada'] == 2
    pasos = [p for t, p, _a in es.llamadas if t == "PASANDO DE TEMPORADA"]
    esperados = ["Cerrando temporada", "Actualizando clasificaciones y descensos", "Generando agentes libres",
                 "Procesando mercado de pases", "Preparando nueva temporada"]
    pos = -1
    for texto in esperados:
        sig = next((i for i, p in enumerate(pasos) if p.startswith(texto) and i > pos), None)
        assert sig is not None, (texto, pasos)
        pos = sig
    avances = [a for t, _p, a in es.llamadas if t == "PASANDO DE TEMPORADA"]
    assert avances == sorted(avances) and avances[-1] == 1.0
    assert PC._titulares == [] and PC._inicio is None


def test_el_cierre_publica_noticias_con_la_temporada_cerrada():
    from alpha_football.ui.resumen_temporada_screen import avanzar_nueva_temporada
    e = _estado()
    avanzar_nueva_temporada(e)
    assert e['temporada'] == 2
    camp = [n for n in N.lista(e) if n['tipo'] == 'campeon']
    assert camp and all(n['temporada'] == 1 for n in camp)


def test_la_carga_arranca_con_las_ultimas_noticias():
    from alpha_football.ui.resumen_temporada_screen import avanzar_nueva_temporada
    e = _estado()
    for i in range(12):
        N.publicar(e, 'resultado', f"Titular {i}", "x", importancia=3)
    vistos = []
    original = PC.fijar_titulares
    PC.fijar_titulares = lambda lista: (vistos.append(None if lista is None else len(lista)), original(lista))[1]
    try:
        avanzar_nueva_temporada(e)
    finally:
        PC.fijar_titulares = original
    assert vistos[0] == 10                                               # arranca con las 10 más recientes
    assert vistos[-1] is None                                            # y las quita al terminar


def test_carga_sin_noticias_ni_liga():
    from alpha_football.ui.resumen_temporada_screen import avanzar_nueva_temporada
    PC.fijar_titulares([])
    PC.mostrar("PASANDO DE TEMPORADA", "x", 0.5)
    PC.cerrar()
    with _Espia() as es:
        avanzar_nueva_temporada({})
    assert es.llamadas == [] and PC._inicio is None


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
