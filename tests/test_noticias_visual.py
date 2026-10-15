"""0.4.23.0: tarjetas visuales de noticias (feed del hub, pantalla Noticias, carga de temporada)."""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
screen = pygame.display.set_mode((1280, 720))

from alpha_football import noticias as N
from alpha_football.ui import noticias_visual as V
from alpha_football.ui.theme import get_font

_imagen_original = N.imagen


def _noticia(i=1, titular="Goleada histórica en el clásico", categoria='resultado', tipo='resultado'):
    return {'id': i, 'tipo': tipo, 'categoria': categoria, 'titular': titular, 'cuerpo': "Cuerpo de prueba.",
            'temporada': 1, 'jornada': 1, 'importancia': 4}


def _png(carpeta, w, h, color, nombre="img.png"):
    s = pygame.Surface((w, h))
    s.fill(color)
    ruta = os.path.join(carpeta, nombre)
    pygame.image.save(s, ruta)
    return ruta


def _con_imagen(ruta):
    N.imagen = lambda noticia: ruta
    V.vaciar_cache()


def _restaurar():
    N.imagen = _imagen_original
    V.vaciar_cache()


def test_sin_imagen_usa_el_color_de_la_categoria():
    _con_imagen(None)
    try:
        for k, cat in enumerate(('resultado', 'ascenso', 'prensa')):    # un id por noticia: la caché es por id
            s = V.tarjeta(_noticia(i=10 + k, categoria=cat), 198, 352)
            assert s.get_size() == (198, 352)
            assert tuple(s.get_at((196, 2)))[:3] == N.COLOR[cat], cat
    finally:
        _restaurar()


def test_categoria_desconocida_cae_a_un_color_por_defecto():
    _con_imagen(None)
    try:
        s = V.tarjeta(_noticia(categoria='inexistente', tipo='otro'), 198, 352)
        assert s.get_size() == (198, 352)
    finally:
        _restaurar()


def test_con_imagen_recorta_a_cubrir():
    with tempfile.TemporaryDirectory() as tmp:
        _con_imagen(_png(tmp, 300, 100, (200, 10, 10)))          # horizontal: debe llenar una tarjeta vertical
        try:
            s = V.tarjeta(_noticia(), 198, 352)
            assert s.get_size() == (198, 352)
            assert tuple(s.get_at((190, 5)))[:3] == (200, 10, 10)
            assert tuple(s.get_at((190, 120)))[:3] == (200, 10, 10)
        finally:
            _restaurar()


def test_cache_por_id_y_tamano():
    _con_imagen(None)
    try:
        n = _noticia()
        a = V.tarjeta(n, 198, 352)
        assert V.tarjeta(n, 198, 352) is a
        assert V.tarjeta(n, 330, 586) is not a
        assert V.tarjeta(n, 198, 352, dim=True) is not a
        assert V.tarjeta(n, 198, 352, titular=False) is not a
        assert V.tarjeta(_noticia(i=2), 198, 352) is not a
        V.vaciar_cache()
        assert V.tarjeta(n, 198, 352) is not a
    finally:
        _restaurar()


def test_dim_oscurece():
    with tempfile.TemporaryDirectory() as tmp:
        _con_imagen(_png(tmp, 200, 400, (240, 240, 240)))
        try:
            n = _noticia()
            claro = sum(tuple(V.tarjeta(n, 198, 352).get_at((100, 100)))[:3])
            oscuro = sum(tuple(V.tarjeta(n, 198, 352, dim=True).get_at((100, 100)))[:3])
            assert oscuro < claro
        finally:
            _restaurar()


def test_titular_largo_se_recorta():
    f = get_font('md')
    lineas = V.envolver("Las crónicas dicen que el delantero estrella del equipo rompió todos los récords del club "
                        "durante la presente temporada", f, 170, 3)
    assert len(lineas) <= 3 and lineas[-1].endswith("…")
    assert all(f.size(ln)[0] <= 170 for ln in lineas)
    corto = V.envolver("Gol y victoria", f, 170, 5)
    assert corto and not corto[-1].endswith("…") and " ".join(corto) == "Gol y victoria"
    gigante = V.envolver("Anticonstitucionalisimamente " * 3, f, 120, 4)
    assert 1 <= len(gigante) <= 4                                     # una palabra más ancha que la tarjeta no rompe
    assert V.envolver("", f, 170, 3) == [] and V.envolver(None, f, 170, 3) == []


def test_envolver_respeta_los_saltos_de_linea():
    """v0.4.25.0: el equipo del año y la lista de campeones llevan un nombre por renglón."""
    f = get_font('sm')
    cuerpo = "PORTERO\nMarcos Sánchez · Pool de Higado · 7.0\n\nDEFENSAS\nPau Cubardí · Spurs sin Copas · 7.0\n"
    assert V.envolver(cuerpo, f, 400, 10) == ["PORTERO", "Marcos Sánchez · Pool de Higado · 7.0", "",
                                              "DEFENSAS", "Pau Cubardí · Spurs sin Copas · 7.0"]
    assert V.envolver("\n\nSolo una\n\n", f, 400, 5) == ["Solo una"]          # sin blancos al principio ni al final
    assert V.envolver("A\nB\nC\nD", f, 400, 2) == ["A", "B…"]                # el tope de líneas también corta renglones


def test_ajustar_baja_la_letra_cuando_el_titular_no_cabe():
    corto = "Gol y victoria"
    nombre, f, lineas = V.ajustar(corto, 170, 2, 'md')
    assert nombre == 'md' and lineas == [corto]
    largo = "Confirmado: Marcos Alonso deja Atlético Almirante y ficha por Real Sporting"
    nombre, f, lineas = V.ajustar(largo, 200, 3, 'md')
    assert nombre in ('sm', 'xs') and get_font(nombre) is f
    assert not lineas[-1].endswith("…") and " ".join(lineas) == largo        # cabe entero en una letra más chica
    nombre, f, lineas = V.ajustar(largo * 3, 100, 2, 'sm')
    assert nombre == 'xs' and len(lineas) == 2 and lineas[-1].endswith("…")   # ni en la más chica: se recorta
    assert get_font('xs').get_height() < get_font('sm').get_height()


def test_titular_de_60_caracteres_cabe_en_la_tarjeta():
    _con_imagen(None)
    try:
        titular = ("Palabra " * 8)[:59] + "…"
        s = V.tarjeta(_noticia(titular=titular), 198, 352)
        assert s.get_size() == (198, 352)
    finally:
        _restaurar()


def test_imagen_rota_o_inexistente_no_lanza():
    _con_imagen("/no/existe/para/nada.png")
    try:
        s = V.tarjeta(_noticia(), 198, 352)
        assert tuple(s.get_at((196, 2)))[:3] == N.COLOR['resultado']
    finally:
        _restaurar()
    with tempfile.TemporaryDirectory() as tmp:
        roto = os.path.join(tmp, "roto.jpg")
        with open(roto, "wb") as f:
            f.write(b"esto no es una imagen")
        _con_imagen(roto)
        try:
            assert V.tarjeta(_noticia(), 198, 352).get_size() == (198, 352)
        finally:
            _restaurar()


def test_degradado_oscurece_el_tercio_inferior():
    with tempfile.TemporaryDirectory() as tmp:
        _con_imagen(_png(tmp, 200, 400, (240, 240, 240)))
        try:
            s = V.tarjeta(_noticia(titular=""), 198, 352)
            arriba = sum(tuple(s.get_at((190, 352 // 3)))[:3])
            abajo = sum(tuple(s.get_at((190, 352 - 3)))[:3])
            assert abajo < arriba
        finally:
            _restaurar()


def test_imagenes_reales_de_diego_cargan():
    """Con las imágenes del juego (alpha_football/assets/noticias): cada categoría con archivos carga bien."""
    if not os.path.isdir(N.RUTA_IMAGENES):
        return
    V.vaciar_cache()
    for cat in N.COLOR:
        n = _noticia(i=3, categoria=cat, tipo='otro')
        ruta = N.imagen(n)
        if ruta:
            assert os.path.exists(ruta)
            assert V.tarjeta(n, 198, 352).get_size() == (198, 352)


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
