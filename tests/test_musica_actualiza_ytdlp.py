"""Descarga de música: si YouTube rechaza la descarga (yt-dlp viejo), se actualiza yt-dlp y se reintenta."""
import sys, os, types
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

from alpha_football import audio


class _Sync:
    """Reemplaza threading.Thread: corre el worker en el acto."""
    def __init__(self, target, args=(), daemon=None):
        self.target, self.args = target, args

    def start(self):
        self.target(*self.args)


def _falso_ytdlp(falla: bool, llamadas: list):
    mod = types.ModuleType('yt_dlp')

    class YoutubeDL:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def download(self, urls):
            llamadas.append('falla' if falla else 'ok')
            if falla:
                raise Exception("ERROR: unable to download video data: HTTP Error 403: Forbidden")
    mod.YoutubeDL = YoutubeDL
    return mod


def _preparar(falla_tras_actualizar: bool):
    llamadas, instalaciones = [], []
    sys.modules['yt_dlp'] = _falso_ytdlp(True, llamadas)

    def instalar(actualizar=False):
        instalaciones.append(actualizar)
        sys.modules['yt_dlp'] = _falso_ytdlp(falla_tras_actualizar, llamadas)
        return True
    audio._intentar_instalar_ytdlp = instalar
    audio._ytdlp_recargado = lambda: sys.modules['yt_dlp']      # la recarga real traería el yt-dlp instalado
    audio._actualizar_playlist = lambda: None
    audio.threading.Thread = _Sync
    audio._DOWNLOAD_STATUS = {"activo": False, "mensaje": ""}
    audio._YTDLP_ACTUALIZADO = False
    return llamadas, instalaciones


def test_403_actualiza_y_reintenta():
    llamadas, instalaciones = _preparar(falla_tras_actualizar=False)
    audio.descargar_url_async("https://www.youtube.com/watch?v=x")
    assert instalaciones == [True], instalaciones          # se pidió pip install -U una vez
    assert llamadas[-1] == 'ok'
    assert 'Listo' in audio.estado_descarga()['mensaje']
    print("  test_403_actualiza_y_reintenta: OK")


def test_si_sigue_fallando_avisa_y_no_repite_actualizacion():
    llamadas, instalaciones = _preparar(falla_tras_actualizar=True)
    audio.descargar_url_async("https://www.youtube.com/watch?v=x")
    assert instalaciones == [True]
    assert 'Falló' in audio.estado_descarga()['mensaje']
    audio.descargar_url_async("https://www.youtube.com/watch?v=y")   # en la misma sesión no reinstala
    assert instalaciones == [True]
    print("  test_si_sigue_fallando_avisa_y_no_repite_actualizacion: OK")


TESTS = [test_403_actualiza_y_reintenta, test_si_sigue_fallando_avisa_y_no_repite_actualizacion]


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
