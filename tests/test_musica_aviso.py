"""0.4.24.0: aviso al iniciar si no hay música instalada (detección + overlay modal con cómo conseguirla)."""
import sys, os, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
screen = pygame.display.set_mode((1280, 720))

from alpha_football import audio
from alpha_football.ui import musica_overlay as MO


class _Carpeta:
    """MUSIC_DIR temporal con los archivos indicados; lo deja como estaba al salir."""
    def __init__(self, *archivos):
        self.archivos = archivos

    def __enter__(self):
        self.dir = tempfile.mkdtemp()
        for a in self.archivos:
            open(os.path.join(self.dir, a), 'wb').close()
        self.antes = audio.MUSIC_DIR
        audio.MUSIC_DIR = self.dir
        return self.dir

    def __exit__(self, *a):
        audio.MUSIC_DIR = self.antes
        shutil.rmtree(self.dir, ignore_errors=True)


def _tecla(tecla):
    return pygame.event.Event(pygame.KEYDOWN, key=tecla, unicode='', mod=0)


def _clic(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)


def test_hay_musica_detecta_audio_reproducible():
    with _Carpeta():
        assert audio.hay_musica() is False                         # carpeta vacía
    with _Carpeta('.descargas.json', 'ffmpeg.exe', 'nota.txt', 'pista.webm'):
        assert audio.hay_musica() is False                         # ni el manifiesto, ni ffmpeg, ni crudos sin convertir
    for nombre in ('a.mp3', 'B.WAV', 'c.ogg', 'd.m4a'):
        with _Carpeta('nota.txt', nombre):
            assert audio.hay_musica() is True, nombre
    audio.MUSIC_DIR, antes = os.path.join(tempfile.gettempdir(), 'no-existe-af-musica'), audio.MUSIC_DIR
    try:
        assert audio.hay_musica() is False                         # carpeta inexistente: sin música, sin reventar
    finally:
        audio.MUSIC_DIR = antes


def test_preparar_solo_avisa_sin_musica():
    with _Carpeta():
        e = {}
        MO.preparar(e)
        assert MO.activo(e)
    with _Carpeta('a.mp3'):
        e = {}
        MO.preparar(e)
        assert not MO.activo(e)


def test_es_modal_pero_deja_pasar_quit_y_audio():
    e = {'aviso_musica': True}
    assert MO.manejar_evento(e, _tecla(pygame.K_a)) is True
    assert MO.manejar_evento(e, _clic((5, 5))) is True              # clic fuera de los botones: lo consume y sigue abierto
    assert MO.manejar_evento(e, pygame.event.Event(pygame.MOUSEMOTION, pos=(5, 5), rel=(0, 0), buttons=(0, 0, 0))) is True
    assert MO.manejar_evento(e, pygame.event.Event(pygame.QUIT)) is False
    assert MO.manejar_evento(e, pygame.event.Event(pygame.USEREVENT + 100)) is False   # fin de pista: sigue la cadena
    assert MO.activo(e)
    cerrado = {}
    assert MO.manejar_evento(cerrado, _tecla(pygame.K_RETURN)) is False   # sin aviso no consume nada


def test_cerrar_con_teclado_y_con_boton():
    for tecla in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_ESCAPE):
        e = {'aviso_musica': True}
        assert MO.manejar_evento(e, _tecla(tecla)) is True and not MO.activo(e)
    e = {'aviso_musica': True}
    assert MO.manejar_evento(e, _clic(MO.R_CERRAR.center)) is True and not MO.activo(e)


def test_abrir_opciones_vuelve_al_menu():
    e = {'aviso_musica': True, 'current_screen': 'menu'}
    assert MO.manejar_evento(e, _clic(MO.R_OPCIONES.center)) is True
    assert not MO.activo(e)
    assert e['current_screen'] == 'options_screen' and e['options_return'] == 'menu'


def test_abrir_carpeta_la_crea_y_deja_el_aviso():
    abiertas = []
    original = MO._abrir_carpeta
    MO._abrir_carpeta = lambda ruta: abiertas.append(ruta)
    try:
        with _Carpeta() as d:
            e = {'aviso_musica': True}
            assert MO.manejar_evento(e, _clic(MO.R_CARPETA.center)) is True
            assert abiertas == [d] and MO.activo(e)                # sigue abierto: el user copia sus archivos y se cierra solo
    finally:
        MO._abrir_carpeta = original


def test_se_cierra_solo_cuando_aparece_musica():
    with _Carpeta() as d:
        e = {'aviso_musica': True}
        MO.revisar(e)
        assert MO.activo(e)
        open(os.path.join(d, 'nueva.mp3'), 'wb').close()
        MO.revisar(e)
        assert not MO.activo(e)


def test_dibuja_titulo_y_ruta_de_la_carpeta():
    dibujado = []
    original = MO.draw_text
    MO.draw_text = lambda scr, texto, *a, **k: dibujado.append(str(texto))
    try:
        with _Carpeta() as d:
            e = {'aviso_musica': True}
            screen.fill((0, 0, 0))
            MO.dibujar(screen, e)
            assert any("NO HAY MÚSICA" in t for t in dibujado), dibujado
            assert any(os.path.basename(d) in t for t in dibujado), dibujado
            assert MO.activo(e)
    finally:
        MO.draw_text = original
    e = {}
    MO.dibujar(screen, e)                                          # sin aviso no dibuja ni revienta


def test_main_lo_registra():
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'main.py'),
               encoding='utf-8').read()
    assert 'musica_overlay' in src and 'filtrar_eventos_musica' in src
    assert src.index('musica_overlay.preparar') > src.index('audio.init_audio()')


TESTS = [f for n, f in list(globals().items()) if n.startswith('test_') and callable(f)]


if __name__ == '__main__':
    fail = 0
    for t in TESTS:
        try:
            t()
            print(f"  {t.__name__}: OK")
        except Exception as ex:
            fail += 1
            import traceback; traceback.print_exc()
            print(f"  {t.__name__}: FAIL - {ex}")
    print(f"\n{len(TESTS) - fail}/{len(TESTS)} tests pasaron")
    if fail:
        sys.exit(1)
