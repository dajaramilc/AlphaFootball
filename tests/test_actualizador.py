"""v0.4.15.0: auto-actualización. Sin red: la consulta, la descarga y git son falsos, y la «instalación»
es una carpeta temporal."""
import sys, os, io, zipfile, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


# --- Versión y título ─────────────────────────────────────────────────────────

def test_la_version_sale_del_archivo_version_y_el_titulo_la_usa():
    import alpha_football
    from alpha_football import actualizador as A
    escrita = (RAIZ / 'VERSION').read_text(encoding='utf-8').strip()
    assert A.version_valida(escrita)
    assert alpha_football.__version__ == escrita == A.version_local()
    assert alpha_football.TITULO == f"Alpha Football v{escrita}"
    fuente = (RAIZ / 'main.py').read_text(encoding='utf-8')
    assert "set_caption(TITULO)" in fuente and "Alpha Football v0." not in fuente   # sin versión escrita a mano


def test_las_versiones_se_comparan_numero_a_numero():
    from alpha_football import actualizador as A
    assert A.es_mayor('0.4.11.0', '0.4.10.0') and A.es_mayor('0.4.10.0', '0.4.9.2') and A.es_mayor('0.5', '0.4.99.9')
    assert not A.es_mayor('0.4.10.0', '0.4.10.0') and not A.es_mayor('0.4.9.2', '0.4.10.0')
    assert not A.es_mayor('0.4.10', '0.4.10.0')                           # los ceros de la cola no cuentan
    for basura in ('', 'v0.4.11', '<html>', '0.4.x', None, '1', '0..4'):
        assert not A.version_valida(basura) and not A.es_mayor(basura, '0.4.10.0'), basura
    assert A.es_mayor('0.4.10.0', '')                                     # sin VERSION local: cualquier remota es nueva


# --- Consulta ─────────────────────────────────────────────────────────────────

def test_la_consulta_devuelve_la_version_remota_o_nada():
    from alpha_football import actualizador as A
    pedidos = []

    def buena(url, espera):
        pedidos.append((url, espera))
        return b"0.4.11.0\n"
    assert A.consultar(buena) == '0.4.11.0'
    assert pedidos == [("https://raw.githubusercontent.com/dajaramilc/AlphaFootball/main/VERSION", 4)]

    def sin_red(url, espera):
        raise OSError("sin red")
    assert A.consultar(sin_red) is None
    for basura in (b"<html>Inicia sesion en el wifi</html>", b"", b"404: Not Found", b"\xff\xfe"):
        assert A.consultar(lambda u, e, b=basura: b) is None, basura


# --- Tipo de copia ────────────────────────────────────────────────────────────

def _git_falso(respuestas: dict, llamadas: list):
    """git de mentira: {('status', '--porcelain'): (0, '')…}; lo no previsto falla (rc 1)."""
    def git(carpeta, *args):
        llamadas.append(args)
        return respuestas.get(args, (1, 'comando no previsto'))
    return git


LIMPIA = {('status', '--porcelain'): (0, ''), ('rev-list', '--count', '@{u}..HEAD'): (0, '0\n')}


def test_el_tipo_de_copia_ante_la_duda_no_se_toca():
    from alpha_football import actualizador as A
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = Path(tmp)
        llamadas = []
        assert A.tipo_copia(carpeta, _git_falso({}, llamadas)) == 'zip' and llamadas == []   # sin .git no se llama a git
        (carpeta / '.git').mkdir()
        assert A.tipo_copia(carpeta, _git_falso(LIMPIA, [])) == 'git_limpia'
        casos = {
            'cambios sin commitear': {**LIMPIA, ('status', '--porcelain'): (0, ' M main.py\n')},
            'commits sin subir': {**LIMPIA, ('rev-list', '--count', '@{u}..HEAD'): (0, '2\n')},
            'sin rama remota': {**LIMPIA, ('rev-list', '--count', '@{u}..HEAD'): (128, 'fatal: no upstream')},
            'git no responde': {},
        }
        for nombre, respuestas in casos.items():
            assert A.tipo_copia(carpeta, _git_falso(respuestas, [])) == 'git_sucia', nombre


# --- ZIP ──────────────────────────────────────────────────────────────────────

def _zip(archivos: dict, prefijo='AlphaFootball-main/') -> bytes:
    """ZIP en memoria como el de GitHub: todo dentro de una carpeta raíz."""
    datos = io.BytesIO()
    with zipfile.ZipFile(datos, 'w') as z:
        for nombre, contenido in archivos.items():
            z.writestr(prefijo + nombre, contenido)
    return datos.getvalue()


NUEVO = {'main.py': "print('nuevo')", 'VERSION': "0.4.11.0\n", 'requirements.txt': "pygame>=2.6\n",
         'alpha_football/__init__.py': "# nuevo", 'alpha_football/nuevo_modulo.py': "x = 1",
         # datos del jugador que NO deben pisarse aunque vengan en el ZIP
         'saves/slot1.json': "ZIP", 'music/cancion.mp3': "ZIP", 'preferencias.json': "ZIP", 'musica.txt': "ZIP",
         'alpha_football_save.json': "ZIP", 'alpha_football_save.json.bak': "ZIP",
         'alpha_football_edited_db.json': "ZIP", 'alpha_football_db_custom.json': "ZIP", 'context.md': "ZIP"}
VIEJO = dict(NUEVO, **{'main.py': "print('viejo')", 'VERSION': "0.4.10.0\n", 'alpha_football/__init__.py': "# viejo"})
VIEJO = {k: (v if v != "ZIP" else "MIO") for k, v in VIEJO.items() if k != 'alpha_football/nuevo_modulo.py'}


def _instalacion(tmp, archivos=VIEJO) -> Path:
    carpeta = Path(tmp) / 'juego'
    for nombre, contenido in archivos.items():
        (carpeta / nombre).parent.mkdir(parents=True, exist_ok=True)
        (carpeta / nombre).write_text(contenido, encoding='utf-8', newline='')
    return carpeta


def _foto(carpeta: Path) -> dict:
    return {p.relative_to(carpeta).as_posix(): p.read_bytes().decode('utf-8')
            for p in sorted(carpeta.rglob('*')) if p.is_file()}


def test_el_zip_se_valida_antes_de_tocar_nada():
    from alpha_football import actualizador as A
    assert A.validar_zip(_zip(NUEVO), '0.4.11.0') == (True, '', 'AlphaFootball-main/')
    assert A.validar_zip(_zip(NUEVO, prefijo=''), '0.4.11.0') == (True, '', '')            # ZIP plano
    malos = {
        'no es un zip': b"<html>error</html>",
        'sin main.py': _zip({k: v for k, v in NUEVO.items() if k != 'main.py'}),
        'sin VERSION': _zip({k: v for k, v in NUEVO.items() if k != 'VERSION'}),
        'otra versión': _zip(dict(NUEVO, VERSION="0.4.12.0")),
        'sube de carpeta': _zip(dict(NUEVO, **{'../fuera.py': "x"})),
        'sube por dentro': _zip(dict(NUEVO, **{'alpha_football/../../fuera.py': "x"})),
        'ruta absoluta': _zip(dict(NUEVO, **{'/etc/fuera': "x"}), prefijo=''),
        'con unidad': _zip(dict(NUEVO, **{'C:/fuera.py': "x"}), prefijo=''),
        'con barra invertida': _zip(dict(NUEVO, **{'..\\fuera.py': "x"})),
        'vacío': _zip({}),
    }
    for nombre, datos in malos.items():
        ok, motivo, _prefijo = A.validar_zip(datos, '0.4.11.0')
        assert not ok and motivo, nombre


def test_actualizar_por_zip_copia_el_codigo_y_no_pisa_los_datos_del_jugador():
    from alpha_football import actualizador as A
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = _instalacion(tmp)
        pedidos = []
        ok, motivo = A.actualizar_zip(carpeta, '0.4.11.0', lambda u, e: (pedidos.append((u, e)), _zip(NUEVO))[1])
        assert ok and motivo == '', motivo
        assert pedidos == [("https://github.com/dajaramilc/AlphaFootball/archive/refs/heads/main.zip", 60)]
        foto = _foto(carpeta)
        assert foto['main.py'] == "print('nuevo')" and foto['VERSION'] == "0.4.11.0\n"
        assert foto['alpha_football/__init__.py'] == "# nuevo" and foto['alpha_football/nuevo_modulo.py'] == "x = 1"
        for protegido in ('saves/slot1.json', 'music/cancion.mp3', 'preferencias.json', 'musica.txt',
                          'alpha_football_save.json', 'alpha_football_save.json.bak',
                          'alpha_football_edited_db.json', 'alpha_football_db_custom.json', 'context.md'):
            assert foto[protegido] == "MIO", protegido
        assert A.protegido('saves/x/y.json') and A.protegido('alpha_football_save.json.tmp')
        assert not A.protegido('alpha_football/save.py') and not A.protegido('main.py')


def test_un_zip_malo_o_una_descarga_caida_no_tocan_nada():
    from alpha_football import actualizador as A
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = _instalacion(tmp)
        antes = _foto(carpeta)

        def caida(url, espera):
            raise OSError("se cortó")
        for descarga in (caida, lambda u, e: b"basura", lambda u, e: _zip(dict(NUEVO, VERSION="9.9.9")),
                         lambda u, e: _zip(dict(NUEVO, **{'../fuera.py': "x"}))):
            ok, motivo = A.actualizar_zip(carpeta, '0.4.11.0', descarga)
            assert not ok and motivo and _foto(carpeta) == antes
        assert not (Path(tmp) / 'fuera.py').exists()


def test_si_la_copia_falla_a_la_mitad_todo_vuelve_a_como_estaba():
    from alpha_football import actualizador as A
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = _instalacion(tmp)
        antes = _foto(carpeta)
        original, hechas = A._copiar_archivo, []

        def falla_en_la_tercera(origen, destino):
            hechas.append(destino)
            if len(hechas) == 3:
                Path(destino).write_text("a medio escribir", encoding='utf-8')     # deja basura, como un disco lleno
                raise PermissionError("archivo en uso")
            return original(origen, destino)
        A._copiar_archivo = falla_en_la_tercera
        try:
            ok, motivo = A.actualizar_zip(carpeta, '0.4.11.0', lambda u, e: _zip(NUEVO))
        finally:
            A._copiar_archivo = original
        assert not ok and "archivo en uso" in motivo and len(hechas) == 3
        assert _foto(carpeta) == antes                                    # ni lo pisado ni lo nuevo quedan


# --- revisar: consulta, decide e instala ──────────────────────────────────────

def _red(version, zip_bytes=None, pedidos=None):
    """Red de mentira: VERSION responde `version` (None = sin red); el ZIP, `zip_bytes` (None = no debe pedirse)."""
    def descargar(url, espera):
        if pedidos is not None:
            pedidos.append(url)
        if url.endswith('/VERSION'):
            if version is None:
                raise OSError("sin red")
            return version
        assert zip_bytes is not None, "no debía descargarse el ZIP"
        return zip_bytes
    return descargar


def test_sin_red_o_al_dia_no_se_toca_nada_ni_se_avisa():
    from alpha_football import actualizador as A
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = _instalacion(tmp)
        antes = _foto(carpeta)
        for remota, estado in ((None, 'sin_red'), (b"<html>", 'sin_red'), (b"0.4.10.0", 'al_dia'), (b"0.4.9.2", 'al_dia')):
            r = A.revisar(carpeta, _red(remota))
            assert r['estado'] == estado and not r['reiniciar'] and r['aviso'] == '', (remota, r)
        assert _foto(carpeta) == antes


def test_una_copia_zip_se_actualiza_sola_y_pide_reiniciar():
    from alpha_football import actualizador as A
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = _instalacion(tmp)
        pasos, instalaciones = [], []
        r = A.revisar(carpeta, _red(b"0.4.11.0\n", _zip(NUEVO)), paso=lambda t, x="", a=None: pasos.append((t, x)),
                      instalar=lambda c: instalaciones.append(c) or True)
        assert r == {'estado': 'actualizado', 'version': '0.4.11.0', 'aviso': '', 'reiniciar': True}
        assert A.version_local(carpeta) == '0.4.11.0' and _foto(carpeta)['saves/slot1.json'] == "MIO"
        assert pasos and all(t == "ACTUALIZANDO A 0.4.11.0" for t, _x in pasos)
        assert instalaciones == []                                         # requirements.txt no cambió
        assert A.revisar(carpeta, _red(b"0.4.11.0"))['estado'] == 'al_dia'  # tras reiniciar no vuelve a instalar


def test_si_cambian_los_requisitos_se_instalan():
    from alpha_football import actualizador as A
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = _instalacion(tmp)
        instalaciones = []
        con_otra_lib = dict(NUEVO, **{'requirements.txt': "pygame>=2.6\notra-lib\n"})
        r = A.revisar(carpeta, _red(b"0.4.11.0", _zip(con_otra_lib)), instalar=lambda c: instalaciones.append(c) or True)
        assert r['estado'] == 'actualizado' and instalaciones == [carpeta]
        ordenes = []
        assert A.instalar_requisitos(carpeta, lambda cmd, **k: ordenes.append(cmd))
        assert ordenes[0][1:5] == ['-m', 'pip', 'install', '-r'] and ordenes[0][5].endswith('requirements.txt')


def test_una_copia_git_limpia_hace_pull_ff_only():
    from alpha_football import actualizador as A
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = _instalacion(tmp); (carpeta / '.git').mkdir()
        llamadas = []

        def pull(c, *args):
            llamadas.append(args)
            if args == ('pull', '--ff-only'):
                (c / 'VERSION').write_text("0.4.11.0\n", encoding='utf-8')   # lo que haría el pull de verdad
                return 0, 'Updating'
            return LIMPIA.get(args, (1, ''))
        r = A.revisar(carpeta, _red(b"0.4.11.0"), git=pull)
        assert r['estado'] == 'actualizado' and r['reiniciar'] and ('pull', '--ff-only') in llamadas


def test_una_copia_git_con_cambios_solo_avisa():
    from alpha_football import actualizador as A
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = _instalacion(tmp); (carpeta / '.git').mkdir()
        antes, llamadas = _foto(carpeta), []
        sucia = {**LIMPIA, ('status', '--porcelain'): (0, ' M main.py\n')}
        r = A.revisar(carpeta, _red(b"0.4.11.0"), git=_git_falso(sucia, llamadas))
        assert r == {'estado': 'aviso', 'version': '0.4.11.0', 'aviso': "Hay una versión nueva (0.4.11.0)", 'reiniciar': False}
        assert ('pull', '--ff-only') not in llamadas and _foto(carpeta) == antes


def test_si_la_instalacion_falla_o_no_alcanza_la_version_no_hay_bucle_de_reinicios():
    from alpha_football import actualizador as A
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = _instalacion(tmp)
        antes = _foto(carpeta)
        r = A.revisar(carpeta, _red(b"0.4.11.0", b"basura"))               # ZIP inválido
        assert r['estado'] == 'aviso' and not r['reiniciar'] and "0.4.11.0" in r['aviso'] and _foto(carpeta) == antes
        (carpeta / '.git').mkdir()
        ya_estaba = lambda c, *args: (0, 'Already up to date.') if args == ('pull', '--ff-only') else LIMPIA.get(args, (1, ''))
        r = A.revisar(carpeta, _red(b"0.4.11.0"), git=ya_estaba)           # el pull "funciona" pero VERSION sigue atrás
        assert r['estado'] == 'aviso' and not r['reiniciar']
        fallo = lambda c, *args: (1, 'fatal: Not possible to fast-forward') if args == ('pull', '--ff-only') else LIMPIA.get(args, (1, ''))
        assert A.revisar(carpeta, _red(b"0.4.11.0"), git=fallo)['estado'] == 'aviso'

        def explota(url, espera):
            raise RuntimeError("algo raro")
        assert A.revisar(carpeta, explota)['estado'] == 'sin_red'           # nunca lanza


# --- Arranque: al_iniciar, reiniciar y el aviso del menú ──────────────────────

def test_en_los_tests_al_iniciar_jamas_toca_la_red():
    from alpha_football import actualizador as A
    original = A._descargar

    def prohibido(url, espera):
        raise AssertionError("un test tocó la red")
    A._descargar = prohibido
    try:
        assert A.al_iniciar() == {'estado': 'omitido', 'version': None, 'aviso': '', 'reiniciar': False}
        os.environ['ALPHA_SIN_ACTUALIZAR'] = '1'
        assert A.al_iniciar()['estado'] == 'omitido'
    finally:
        A._descargar = original
        os.environ.pop('ALPHA_SIN_ACTUALIZAR', None)


def test_al_iniciar_muestra_los_pasos_y_devuelve_lo_que_dijo_revisar():
    from alpha_football import actualizador as A
    vistos = []

    def revisar_falso(paso=None, **_k):
        paso("ACTUALIZANDO A 0.4.11.0", "Descargando la versión nueva…", 0.15)
        return {'estado': 'actualizado', 'version': '0.4.11.0', 'aviso': '', 'reiniciar': True}
    r = A.al_iniciar(revisar_falso, mostrar=lambda *a: vistos.append(a), cerrar=lambda: vistos.append('cerrar'))
    assert r['reiniciar'] and vistos == [("ACTUALIZANDO A 0.4.11.0", "Descargando la versión nueva…", 0.15), 'cerrar']
    vistos.clear()
    r = A.al_iniciar(lambda paso=None, **_k: {'estado': 'al_dia', 'version': 'x', 'aviso': '', 'reiniciar': False},
                     mostrar=lambda *a: vistos.append(a), cerrar=lambda: vistos.append('cerrar'))
    assert r['estado'] == 'al_dia' and vistos == []                        # sin nada que instalar no hay pantalla de carga


def test_reiniciar_relanza_el_juego_y_cierra_este_proceso():
    from alpha_football import actualizador as A
    hechos = []
    A.reiniciar(lanzar=lambda cmd, cwd: hechos.append((cmd, cwd)), salir=lambda codigo: hechos.append(codigo))
    assert hechos == [([sys.executable] + sys.argv, str(A.raiz())), 0]


def test_el_menu_muestra_el_aviso_de_version_nueva():
    import pygame; pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    from alpha_football.ui import menu
    dib, original = [], menu.draw_text
    menu.draw_text = lambda scr, txt, *a, **k: (dib.append(txt), original(scr, txt, *a, **k))[1]
    try:
        menu._dibujar_aviso_version(screen, {})
        assert dib == []
        menu._dibujar_aviso_version(screen, {'aviso_version': "Hay una versión nueva (0.4.11.0)"})
        assert dib == ["Hay una versión nueva (0.4.11.0)"]
    finally:
        menu.draw_text = original
    fuente = (RAIZ / 'main.py').read_text(encoding='utf-8')
    assert "actualizador.al_iniciar()" in fuente and "estado['aviso_version']" in fuente


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
