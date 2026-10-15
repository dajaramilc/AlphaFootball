"""v0.4.23.0: núcleo de noticias (publicar, caducidad, tope, orden, leídas, imágenes, saves viejos)."""
import sys, os, json, shutil, tempfile
from types import SimpleNamespace
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import alpha_football
from alpha_football import noticias as N, eventos as EV

CAMPOS = ('id', 'tipo', 'categoria', 'titular', 'cuerpo', 'temporada', 'jornada', 'importancia',
          'equipos_ids', 'jugadores_ids', 'dt_ids', 'leida', 'fecha_creacion')


def _jornada(e, jugadas):
    """Deja al user con `jugadas` partidos de liga jugados (así cuenta la jornada todo el juego)."""
    liga = e['liga']
    liga.calendario = [SimpleNamespace(jugado=i < jugadas, local_id=1, visitante_id=2, jornada=i + 1)
                       for i in range(liga.num_jornadas)]
    liga.jornada_actual = min(liga.num_jornadas, jugadas + 1)


def estado(temporada=1, jornada=5, n=38):
    liga = SimpleNamespace(nombre='Liga', tipo='premier', num_jornadas=n, jornada_actual=1, calendario=[], equipos=[])
    e = {'liga': liga, 'mi_equipo': SimpleNamespace(id=1, nombre='Mi Club', jugadores=[]),
         'temporada': temporada, 'datos_carrera': {}}
    _jornada(e, jornada)
    return e


def test_publicar_campos():
    e = estado(temporada=2, jornada=5)
    e['datos_carrera']['calendario'] = {'dia': '2026-09-12'}
    n = N.publicar(e, 'fichaje', "Llega un crack", "Cuerpo", importancia=4, equipos=[SimpleNamespace(id=7), 9],
                   jugadores=[SimpleNamespace(id=33)], dts=[{'id': 4}], origen='x')
    assert all(c in n for c in CAMPOS), [c for c in CAMPOS if c not in n]
    assert n['tipo'] == 'fichaje' and n['categoria'] == 'fichaje' and n['titular'] == "Llega un crack"
    assert (n['temporada'], n['jornada'], n['importancia']) == (2, 5, 4) and n['leida'] is False
    assert n['equipos_ids'] == [7, 9] and n['jugadores_ids'] == [33] and n['dt_ids'] == [4]
    assert n['fecha_creacion'] == '2026-09-12' and n['origen'] == 'x'
    assert N.lista(e) == [n] and e['datos_carrera']['noticias'] is N.lista(e)
    # categoría por defecto según el tipo; la explícita manda; tipo desconocido -> 'otro'; importancia acotada 1-5
    assert N.publicar(e, 'dt_cambio', "a", "b")['categoria'] == 'entrenador'
    assert N.publicar(e, 'descenso', "a", "b", categoria='ascenso')['categoria'] == 'ascenso'
    raro = N.publicar(e, 'inventado', "a", "b", importancia=9)
    assert raro['tipo'] == 'otro' and raro['categoria'] == 'general' and raro['importancia'] == 5
    assert N.publicar(e, 'otro', "a", "b", importancia=0)['importancia'] == 1
    assert N.publicar(estado(), 'otro', "a", "b")['fecha_creacion'] is None      # sin reloj no hay fecha
    print("  test_publicar_campos: OK")


def test_tablas_del_contrato():
    assert (N.MAX_NOTICIAS, N.JORNADAS_VIDA, N.IMPORTANCIA_FEED) == (50, 3, 3)
    assert len(N.TIPOS) == 16 and set(N.CATEGORIA) == set(N.TIPOS) == set(N.ETIQUETA)
    assert len(N.COLOR) == 16 and set(N.CATEGORIA.values()) <= set(N.COLOR)
    assert all(len(c) == 3 and all(0 <= v <= 255 for v in c) for c in N.COLOR.values())
    print("  test_tablas_del_contrato: OK")


def test_titular_se_recorta_a_60():
    e = estado()
    n = N.publicar(e, 'otro', "x" * 80, "c")
    assert len(n['titular']) == 60 and n['titular'].endswith('…')
    assert N.publicar(e, 'otro', "y" * 60, "c")['titular'] == "y" * 60
    print("  test_titular_se_recorta_a_60: OK")


def test_titular_elige_la_primera_forma_que_cabe():
    largo, corto = "a" * 61, "b" * 60
    assert N.titular(largo, corto, "c") == corto and N.titular("x", corto) == "x"
    assert N.titular(largo, "d" * 70) == "d" * 70               # ninguna cabe: la última (publicar la recorta)
    print("  test_titular_elige_la_primera_forma_que_cabe: OK")


def test_tope_50_conserva_las_importantes():
    e = estado()
    top = [N.publicar(e, 'campeon', f"Top {i}", "c", importancia=5)['id'] for i in range(5)]
    resto = [N.publicar(e, 'otro', f"N {i}", "c", importancia=3)['id'] for i in range(55)]
    ids = [n['id'] for n in N.lista(e)]
    assert len(ids) == 50 and all(t in ids for t in top)
    assert all(r not in ids for r in resto[:10]) and all(r in ids for r in resto[10:])   # salen las más viejas
    print("  test_tope_50_conserva_las_importantes: OK")


def test_caducan_a_las_3_jornadas():
    e = estado(jornada=5)
    n = N.publicar(e, 'otro', "t", "c")
    _jornada(e, 7)
    assert N.antiguedad(e, n) == 2 and N.purgar(e) == 0 and n in N.activas(e)
    _jornada(e, 8)
    assert N.antiguedad(e, n) == 3 and n not in N.activas(e)
    assert N.purgar(e) == 1 and N.lista(e) == []
    print("  test_caducan_a_las_3_jornadas: OK")


def test_ultima_jornada_vive_al_cambiar_de_temporada():
    e = estado(temporada=1, jornada=38, n=38)
    n = N.publicar(e, 'campeon', "Campeón", "c", importancia=5)
    e['temporada'] = 2
    _jornada(e, 0)
    assert N.antiguedad(e, n) == 0 and n in N.activas(e) and N.purgar(e) == 0
    _jornada(e, 3)
    assert N.antiguedad(e, n) == 3 and N.purgar(e) == 1
    print("  test_ultima_jornada_vive_al_cambiar_de_temporada: OK")


def test_override_temporada_jornada():
    e = estado(temporada=2, jornada=0, n=38)                 # el contador ya subió
    n = N.publicar(e, 'campeon', "Campeón", "c", importancia=5, temporada=1, jornada=38)
    assert (n['temporada'], n['jornada']) == (1, 38) and N.antiguedad(e, n) == 0
    print("  test_override_temporada_jornada: OK")


def test_orden_activas():
    e = estado(jornada=5)
    vieja = N.publicar(e, 'otro', "vieja 3", "c", importancia=3)
    baja = N.publicar(e, 'otro', "baja", "c", importancia=2)
    _jornada(e, 6)
    nueva = N.publicar(e, 'otro', "nueva 3", "c", importancia=3)
    otra = N.publicar(e, 'otro', "otra 3", "c", importancia=3)
    alta = N.publicar(e, 'otro', "alta", "c", importancia=5)
    assert [n['id'] for n in N.activas(e)] == [alta['id'], otra['id'], nueva['id'], vieja['id'], baja['id']]
    assert [n['id'] for n in N.para_feed(e)] == [alta['id'], otra['id'], nueva['id'], vieja['id']]
    assert [n['id'] for n in N.ultimas(e, 2)] == [alta['id'], otra['id']] and len(N.ultimas(e)) == 5
    print("  test_orden_activas: OK")


def test_orden_activas_lo_mas_reciente_primero():
    """v0.4.24.0: manda la fecha real (la más reciente arriba); dentro del mismo día, la más importante."""
    e = estado(jornada=5)
    e['datos_carrera']['calendario'] = {'dia': '2026-09-10'}
    vieja_alta = N.publicar(e, 'campeon', "vieja alta", "c", importancia=5)
    e['datos_carrera']['calendario'] = {'dia': '2026-09-12'}
    nueva_baja = N.publicar(e, 'otro', "nueva baja", "c", importancia=2)
    nueva_alta = N.publicar(e, 'otro', "nueva alta", "c", importancia=4)
    nueva_media = N.publicar(e, 'otro', "nueva media", "c", importancia=3)
    assert [n['id'] for n in N.activas(e)] == [nueva_alta['id'], nueva_media['id'], nueva_baja['id'],
                                                vieja_alta['id']]
    assert [n['id'] for n in N.para_feed(e)] == [nueva_alta['id'], nueva_media['id'], vieja_alta['id']]
    # una noticia sin fecha (guardado anterior al reloj) no se cuela por encima de las que sí la tienen
    sin_fecha = N.publicar(e, 'otro', "sin fecha", "c", importancia=5)
    sin_fecha['fecha_creacion'] = None
    assert N.activas(e)[-1]['id'] == sin_fecha['id']
    print("  test_orden_activas_lo_mas_reciente_primero: OK")


def test_fecha_texto():
    e = estado(temporada=2, jornada=7)
    e['datos_carrera']['calendario'] = {'dia': '2026-09-12'}
    con = N.publicar(e, 'otro', "a", "b")
    assert N.fecha_texto(con) == "sáb 12 sep 2026" and N.fecha_texto(con, largo=False) == "sáb 12 sep"
    sin = N.publicar(estado(temporada=2, jornada=7), 'otro', "a", "b")          # sin reloj: respaldo
    assert N.fecha_texto(sin) == "Temporada 2 – Jornada 7" and N.fecha_texto(sin, largo=False) == "T2 · J7"
    rota = {'fecha_creacion': 'no-es-fecha', 'temporada': 1, 'jornada': 3}
    assert N.fecha_texto(rota) == "Temporada 1 – Jornada 3"
    print("  test_fecha_texto: OK")


def test_la_jornada_se_lee_una_vez_por_consulta():
    # el hub dibuja el feed a 60 FPS: leer la jornada recorre el calendario, no puede hacerse por noticia
    e = estado(jornada=5)
    for i in range(50):
        N.publicar(e, 'otro', f"n{i}", "c")
    real, cuenta = N._ahora, []

    def contado(est):
        cuenta.append(1)
        return real(est)

    N._ahora = contado
    try:
        for consulta in (N.activas, N.para_feed, N.no_leidas, N.purgar):
            del cuenta[:]
            consulta(e)
            assert len(cuenta) == 1, (consulta.__name__, len(cuenta))
    finally:
        N._ahora = real
    assert len(N.activas(e)) == 50
    print("  test_la_jornada_se_lee_una_vez_por_consulta: OK")


def test_leidas():
    e = estado()
    a = N.publicar(e, 'otro', "a", "c"); N.publicar(e, 'otro', "b", "c")
    assert N.no_leidas(e) == 2
    N.marcar_leida(e, a['id'])
    assert a['leida'] is True and N.no_leidas(e) == 1
    N.marcar_leida(e, 9999)                                   # id inexistente: no falla
    assert N.no_leidas(e) == 1
    print("  test_leidas: OK")


def test_retirar():
    e = estado()
    a = N.publicar(e, 'otro', "a", "c"); b = N.publicar(e, 'otro', "b", "c")
    assert N.retirar(e, a['id']) is True and N.lista(e) == [b]
    assert N.retirar(e, a['id']) is False and N.retirar(e, 9999) is False and N.lista(e) == [b]
    assert N.publicar(e, 'otro', "c", "c")['id'] > b['id']      # el id retirado tampoco se reutiliza
    print("  test_retirar: OK")


def test_ids_no_se_reutilizan():
    e = estado(jornada=5)
    ids = [N.publicar(e, 'otro', f"n{i}", "c")['id'] for i in range(3)]
    assert ids == sorted(set(ids))
    _jornada(e, 9)
    assert N.purgar(e) == 3 and N.lista(e) == []
    assert N.publicar(e, 'otro', "nueva", "c")['id'] > max(ids)
    print("  test_ids_no_se_reutilizan: OK")


def test_formato_viejo_se_normaliza():
    e = estado(jornada=5)
    e['datos_carrera']['noticias'] = [
        {'id': 2, 'temporada': 1, 'jornada': 5, 'tipo': 'vestuario', 'titular': "Riña en el vestuario",
         'cuerpo': "c", 'jugadores': [11, 12], 'evento': 'rina', 'opcion': 1},
        {'id': 1, 'temporada': 1, 'jornada': 1, 'tipo': 'vestuario', 'titular': "Vieja", 'cuerpo': "c",
         'jugadores': [], 'evento': 'tarde', 'opcion': 0},
        "basura"]
    act = N.activas(e)
    assert [n['id'] for n in act] == [2]                        # la de la jornada 1 ya caducó
    n = act[0]
    assert all(c in n for c in CAMPOS) and n['categoria'] == 'vestuario' and n['importancia'] == 3
    assert n['jugadores_ids'] == [11, 12] and n['jugadores'] == [11, 12] and n['evento'] == 'rina' and n['leida'] is False
    assert N.no_leidas(e) == 1 and len(N.lista(e)) == 2         # lo que no es una noticia se descarta
    assert N.publicar(e, 'otro', "nueva", "c")['id'] == 3       # el contador arranca después de las viejas
    for roto in (None, "x", {'a': 1}):                          # clave ausente o con basura: lista vacía, sin excepción
        e2 = estado()
        if roto is not None:
            e2['datos_carrera']['noticias'] = roto
        assert N.lista(e2) == [] and N.activas(e2) == [] and N.no_leidas(e2) == 0 and N.purgar(e2) == 0
    assert N.lista({}) == [] and N.para_feed({}) == []          # sin datos_carrera tampoco revienta
    print("  test_formato_viejo_se_normaliza: OK")


def _con_carpeta(archivos):
    tmp = tempfile.mkdtemp()
    for nombre in archivos:
        open(os.path.join(tmp, nombre), 'wb').close()
    return tmp


def test_imagen_sin_carpeta_es_none():
    real = N.RUTA_IMAGENES
    n = {'id': 3, 'tipo': 'fichaje', 'categoria': 'fichaje'}
    try:
        N.RUTA_IMAGENES = os.path.join(tempfile.gettempdir(), 'no_existe_alpha_football_noticias')
        assert N.imagen(n) is None                              # carpeta inexistente
        N.RUTA_IMAGENES = vacia = _con_carpeta([])
        assert N.imagen(n) is None                              # vacía
        N.RUTA_IMAGENES = otra = _con_carpeta(['fichaje1.txt', 'fichaje2.webp', 'fichajes1.jpg', 'rumor1.jpg', 'fichaje.jpg'])
        assert N.imagen(n) is None                              # otra extensión u otra categoría
        assert N.imagen({'id': 1}) is None and N.imagen({}) is None
    finally:
        N.RUTA_IMAGENES = real
        shutil.rmtree(vacia, ignore_errors=True); shutil.rmtree(otra, ignore_errors=True)
    print("  test_imagen_sin_carpeta_es_none: OK")


def test_imagen_estable_por_id():
    real = N.RUTA_IMAGENES
    try:
        N.RUTA_IMAGENES = tmp = _con_carpeta(['fichaje1.jpg', 'fichaje2.jpg', 'fichaje10.JPG', 'rumor1.jpg'])
        vistas = set()
        for i in range(1, 13):
            n = {'id': i, 'categoria': 'fichaje'}
            ruta = N.imagen(n)
            assert ruta == N.imagen(n) and os.path.isfile(ruta)             # siempre la misma para ese id
            assert os.path.basename(ruta).lower().startswith('fichaje')
            vistas.add(os.path.basename(ruta))
        assert vistas == {'fichaje1.jpg', 'fichaje2.jpg', 'fichaje10.JPG'}  # reparte entre las de su categoría
        assert os.path.basename(N.imagen({'id': 5, 'categoria': 'rumor'})) == 'rumor1.jpg'
        assert N.imagen({'id': 5, 'tipo': 'rumor'}) == N.imagen({'id': 5, 'categoria': 'rumor'})   # sin categoría: la del tipo
    finally:
        N.RUTA_IMAGENES = real
        shutil.rmtree(tmp, ignore_errors=True)
    print("  test_imagen_estable_por_id: OK")


def test_carpeta_real_cubre_las_16_categorias():
    assert os.path.normpath(N.RUTA_IMAGENES).endswith(os.path.join('alpha_football', 'assets', 'noticias'))
    for cat in N.COLOR:
        ruta = N.imagen({'id': 1, 'categoria': cat})
        assert ruta and os.path.isfile(ruta), f"sin imagen para {cat}"
    print("  test_carpeta_real_cubre_las_16_categorias: OK")


def test_registrar_noticia_de_eventos_pasa_por_el_nucleo():
    e = estado(temporada=1, jornada=5)
    n = EV.registrar_noticia(e, "Riña en el vestuario", "Cuerpo", jugadores=[7, 8], evento='rina', opcion=1)
    assert n['tipo'] == 'vestuario' and n['categoria'] == 'vestuario' and n['importancia'] >= N.IMPORTANCIA_FEED
    assert n['evento'] == 'rina' and n['opcion'] == 1 and n['jugadores'] == [7, 8] and n['jugadores_ids'] == [7, 8]
    assert all(c in n for c in CAMPOS) and (n['temporada'], n['jornada']) == (1, 5)
    assert N.lista(e) == [n] and EV.noticias(e) == [n] and n in N.para_feed(e)
    print("  test_registrar_noticia_de_eventos_pasa_por_el_nucleo: OK")


def test_cierre_jornada_sigue_si_un_generador_falla():
    e = estado(jornada=5)
    N.publicar(e, 'otro', "vieja", "c")
    _jornada(e, 8)
    llamadas = []

    def falla(estado):
        llamadas.append('gen')
        raise RuntimeError("generador roto")

    falsos = {'noticias_gen': SimpleNamespace(generar_jornada=falla),
              'rumores': SimpleNamespace(revisar_jornada=lambda estado: llamadas.append('rumores'))}
    antes = {k: (sys.modules.get(f'alpha_football.{k}'), getattr(alpha_football, k, None)) for k in falsos}
    try:
        for k, mod in falsos.items():
            sys.modules[f'alpha_football.{k}'] = mod
            setattr(alpha_football, k, mod)
        N.cierre_jornada(e)                                     # no propaga la excepción
    finally:
        for k, (mod, attr) in antes.items():
            sys.modules.pop(f'alpha_football.{k}', None)
            if mod is not None:
                sys.modules[f'alpha_football.{k}'] = mod
            if attr is not None:
                setattr(alpha_football, k, attr)
            elif hasattr(alpha_football, k):
                delattr(alpha_football, k)
    assert llamadas == ['rumores', 'gen'] and N.lista(e) == []   # los demás corrieron y la purga también
    N.cierre_jornada({})                                         # sin carrera: no hace nada ni revienta
    print("  test_cierre_jornada_sigue_si_un_generador_falla: OK")


def test_el_cierre_de_jornada_de_liga_llama_al_nucleo_una_vez():
    os.environ['SDL_VIDEODRIVER'] = 'dummy'; os.environ['SDL_AUDIODRIVER'] = 'dummy'
    import pygame; pygame.init(); pygame.display.set_mode((1280, 720))
    from alpha_football import save
    save.guardar_en_slot = lambda *a, **k: None              # los tests no tocan los slots reales
    from alpha_football.models import alineacion_por_defecto
    from alpha_football.ui.menu import load_league_teams
    from alpha_football.ui.league_screen import inicializar_calendario_liga
    from alpha_football.ui.match_screen import finalizar_jornada_liga
    liga = load_league_teams('premier'); mi = liga.equipos[0]
    mi.alineacion_activa = alineacion_por_defecto(mi)
    e = {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
         'alineacion_activa': mi.alineacion_activa, 'primera_division': {'premier': liga},
         'segunda_division': {}, 'datos_carrera': {}, 'historial': []}
    inicializar_calendario_liga(liga)
    p = next(x for x in liga.calendario if x.jornada == 1 and mi.id in (x.local_id, x.visitante_id))
    llamadas, real = [], N.cierre_jornada
    N.cierre_jornada = lambda est: llamadas.append(N._ahora(est))
    try:
        finalizar_jornada_liga(e, liga, mi, p, 1, 0)
        finalizar_jornada_liga(e, liga, mi, p, 1, 0)            # un partido ya cerrado no vuelve a cerrar la jornada
    finally:
        N.cierre_jornada = real
    assert llamadas == [(1, 1)], llamadas                       # una vez, con tu partido ya contado
    print("  test_el_cierre_de_jornada_de_liga_llama_al_nucleo_una_vez: OK")


def test_json():
    e = estado()
    N.publicar(e, 'fichaje', "t", "c", equipos=[1], jugadores=[2], dts=[3],
               accion={'pantalla': 'buscador', 'texto': 'VER BUSCADOR'})
    EV.registrar_noticia(e, "t", "c", jugadores=[4], evento='rina', opcion=0)
    vuelta = json.loads(json.dumps(e['datos_carrera']))
    assert vuelta['noticias'] == e['datos_carrera']['noticias']
    assert N.activas({'datos_carrera': vuelta, 'liga': e['liga'], 'mi_equipo': e['mi_equipo'], 'temporada': 1})
    print("  test_json: OK")


TESTS = [f for n, f in list(globals().items()) if n.startswith('test_') and callable(f)]


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
