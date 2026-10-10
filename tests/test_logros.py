"""0.4.23.0: logros del DT (nueve hitos, cada uno publica una noticia) y su overlay en HISTORIAL DE CARRERA."""
import sys, os, copy, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
screen = pygame.display.set_mode((1280, 720))
from alpha_football import save
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402

from alpha_football import noticias as N
from alpha_football import logros as G
from alpha_football.ui import league_screen as L
from alpha_football.ui import career_screen as C

_BASE = None
IDS = ('titulo_liga', 'final_continental', 'pj_50', 'pj_100', 'pj_200', 'racha_8', 'salvado', 'clasicos_3',
       'fichaje_84')


def _estado():
    """Carrera de la Premier con el calendario armado y sin clásicos (se copia: cargarla cuesta ~3 s)."""
    global _BASE
    if _BASE is None:
        _BASE = estado_carrera()
        L.inicializar_calendario_liga(_BASE['liga'])
        for x in _BASE['liga'].equipos:
            x.rival = ''
    return copy.deepcopy(_BASE)


def _rivales(e, n=2):
    return [x for x in e['liga'].equipos if x is not e['mi_equipo']][:n]


def _obtenidos(e):
    return set(G.logros(e)['obtenidos'])


def _poner_posicion(e, pos):
    liga, mi = e['liga'], e['mi_equipo']
    otros = [x for x in liga.equipos if x is not mi]
    orden = otros[:pos - 1] + [mi] + otros[pos - 1:]
    for i, x in enumerate(orden):
        x.puntos, x.gf, x.gc = (len(orden) - i) * 3, 10, 10


def _tecla(k):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, unicode='', mod=0))


def _clic(pos):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def _rueda(y):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=y, flipped=False))


# ------------------------------------------------------------------ lógica
def test_estructura_y_json():
    d = {}
    est = G.logros({'datos_carrera': d})
    assert set(est['contadores']) >= {'pj', 'racha', 'clasicos_seguidos'} and est['obtenidos'] == {}
    json.dumps(d)
    assert G.logros({})['obtenidos'] == {}                               # sin datos_carrera (guardado viejo)
    assert len(G.LOGROS) == 9 and {x[0] for x in G.LOGROS} == set(IDS)
    assert all(titulo and desc for _id, titulo, desc in G.LOGROS)


def test_pj_50_100_200_y_amistoso_no_cuenta():
    e = _estado(); mi = e['mi_equipo']; rival = _rivales(e)[0]
    for _ in range(49):
        assert 'pj_50' not in G.registrar_partido(e, mi, rival, 0, 1, 'liga')
    G.registrar_partido(e, mi, rival, 0, 0, 'amistoso')                  # no cuenta
    assert G.logros(e)['contadores']['pj'] == 49
    assert 'pj_50' in G.registrar_partido(e, mi, rival, 0, 1, 'copa')    # la copa sí, y justo en la 50ª
    assert 'pj_50' not in G.registrar_partido(e, mi, rival, 0, 1, 'liga')
    for _ in range(48):
        G.registrar_partido(e, mi, rival, 0, 1, 'liga')
    assert 'pj_100' in G.registrar_partido(e, mi, rival, 0, 1, 'liga')
    for _ in range(99):
        G.registrar_partido(e, mi, rival, 0, 1, 'liga')
    assert 'pj_200' in G.registrar_partido(e, mi, rival, 0, 1, 'liga')


def test_racha_8():
    e = _estado(); mi = e['mi_equipo']; rival = _rivales(e)[0]
    for _ in range(7):
        G.registrar_partido(e, mi, rival, 2, 0, 'liga')
    G.registrar_partido(e, mi, rival, 1, 1, 'liga')                      # el empate corta la racha
    for _ in range(7):
        G.registrar_partido(e, mi, rival, 2, 0, 'liga')
    assert 'racha_8' not in _obtenidos(e)
    assert 'racha_8' in G.registrar_partido(e, mi, rival, 2, 0, 'liga')
    assert 'racha_8' in _obtenidos(e)


def test_racha_cuenta_de_visitante():
    e = _estado(); mi = e['mi_equipo']; rival = _rivales(e)[0]
    for _ in range(8):
        G.registrar_partido(e, rival, mi, 0, 3, 'liga')                  # el user es visitante y gana 3-0
    assert 'racha_8' in _obtenidos(e)


def test_clasicos_3_seguidos():
    e = _estado(); mi = e['mi_equipo']
    rc, rn = _rivales(e)
    mi.rival = rc.nombre
    G.registrar_partido(e, mi, rc, 2, 0, 'liga')
    G.registrar_partido(e, mi, rc, 1, 0, 'liga')
    G.registrar_partido(e, mi, rn, 0, 1, 'liga')                         # un partido que no es clásico no rompe la cuenta
    assert 'clasicos_3' not in _obtenidos(e)
    assert 'clasicos_3' in G.registrar_partido(e, mi, rc, 3, 1, 'copa')
    e2 = _estado(); mi2 = e2['mi_equipo']
    rc2, _rn2 = _rivales(e2)
    mi2.rival = rc2.nombre
    for gl, gv in ((1, 0), (2, 0), (1, 1), (1, 0), (2, 1)):              # el empate reinicia
        G.registrar_partido(e2, mi2, rc2, gl, gv, 'liga')
    assert 'clasicos_3' not in _obtenidos(e2)
    assert 'clasicos_3' in G.registrar_partido(e2, mi2, rc2, 4, 0, 'liga')


def _ultima_jornada(e, jugada=None):
    liga, mi = e['liga'], e['mi_equipo']
    jornada = liga.num_jornadas if jugada is None else jugada
    p = next(x for x in liga.calendario if x.jornada == jornada and mi.id in (x.local_id, x.visitante_id))
    p.jugado, p.goles_local, p.goles_visitante = True, 1, 0
    return p


def test_salvado_en_la_ultima_jornada():
    e = _estado(); mi = e['mi_equipo']; rival = _rivales(e)[0]; n = len(e['liga'].equipos)
    _ultima_jornada(e)
    _poner_posicion(e, n - 2)                                            # termina fuera del descenso
    assert 'salvado' in G.registrar_partido(e, mi, rival, 1, 0, 'liga', pos_antes=n - 1)
    e = _estado(); mi = e['mi_equipo']; rival = _rivales(e)[0]
    _ultima_jornada(e, jugada=10)                                        # no es la última jornada
    _poner_posicion(e, n - 2)
    assert 'salvado' not in G.registrar_partido(e, mi, rival, 1, 0, 'liga', pos_antes=n - 1)
    e = _estado(); mi = e['mi_equipo']; rival = _rivales(e)[0]
    _ultima_jornada(e)
    e['liga'].division = 2                                               # en 2ª no cuenta
    _poner_posicion(e, n - 2)
    assert 'salvado' not in G.registrar_partido(e, mi, rival, 1, 0, 'liga', pos_antes=n - 1)
    e = _estado(); mi = e['mi_equipo']; rival = _rivales(e)[0]
    _ultima_jornada(e)
    _poner_posicion(e, n - 1)                                            # sigue en la zona: no se salvó
    assert 'salvado' not in G.registrar_partido(e, mi, rival, 1, 0, 'liga', pos_antes=n - 1)
    e = _estado(); mi = e['mi_equipo']; rival = _rivales(e)[0]
    _ultima_jornada(e)
    _poner_posicion(e, n - 2)
    assert 'salvado' not in G.registrar_partido(e, mi, rival, 1, 0, 'liga', pos_antes=n - 5)   # no estaba en peligro
    assert 'salvado' not in G.registrar_partido(e, mi, rival, 1, 0, 'liga')                    # sin pos_antes tampoco


def test_titulo_y_final_continental():
    e = _estado(); e['historial'] = [{'temporada': 1, 'pos': 3, 'libertadores': 'Semifinal'}]
    assert G.revisar(e) == []
    e['historial'].append({'temporada': 2, 'pos': 1, 'libertadores': 'No clasificado'})
    assert G.revisar(e) == ['titulo_liga']
    assert G.revisar(e) == []                                            # una sola vez
    for fase, esperado in (("Subcampeón", True), ("Final", True), ("Finalista", True), ("Campeón", True),
                           ("Semifinal", False), ("Cuartos", False), ("Fase de liga", False)):
        e = _estado(); e['historial'] = [{'temporada': 1, 'pos': 5, 'libertadores': fase}]
        assert ('final_continental' in G.revisar(e)) == esperado, fase
    e = _estado(); e['historial'] = []
    e['copa_mejor_fase_temp'] = 'Finalista'
    assert 'final_continental' in G.revisar(e)                           # la temporada en curso también cuenta
    e = _estado(); e['copa_mejor_fase_temp'] = 'Semifinal'
    assert G.revisar(e) == []


def _pase(e, media, de, a, propio=True):
    e['datos_carrera'].setdefault('historial_pases', []).append(
        {'temporada': 1, 'jornada': 1, 'jugador': "Jugador Prueba", 'posicion': 'DEL', 'media': media,
         'de': de, 'a': a, 'monto': 1_000_000, 'propio': propio})


def test_fichaje_84_lee_el_historial_de_pases():
    e = _estado(); mi = e['mi_equipo']
    assert 'fichaje_84' not in G.revisar(e)                              # guardado viejo, sin historial de pases
    j = mi.jugadores[0]                                                  # un 84 que ya estaba en la plantilla
    j.ataque = j.defensa = j.fisico = j.tecnica = j.mental = 84
    j.ventana_traspaso, j.canterano = '1:1', ''
    assert 'fichaje_84' not in G.revisar(e)                              # estar en la plantilla no es un fichaje
    _pase(e, 80, "Otro FC", mi.nombre)                                   # llegó con 80 y creció hasta 84
    assert 'fichaje_84' not in G.revisar(e)
    _pase(e, 90, mi.nombre, "Otro FC")                                   # venta de un 90: no es un fichaje
    assert 'fichaje_84' not in G.revisar(e)
    _pase(e, 90, "Otro FC", "Tercero FC", propio=False)                  # pase entre clubes de la IA
    assert 'fichaje_84' not in G.revisar(e)
    _pase(e, 84, "Otro FC", mi.nombre)                                   # compra de un 84
    assert 'fichaje_84' in G.revisar(e)
    ob = G.logros(e)['obtenidos']['fichaje_84']
    assert ob['temporada'] == e['temporada']
    e2 = _estado()
    _pase(e2, 86, "Libre", e2['mi_equipo'].nombre)                       # un agente libre también es fichar
    assert 'fichaje_84' in G.revisar(e2)


def test_desbloquear_publica_noticia_y_una_sola_vez():
    e = _estado()
    n = G.desbloquear(e, 'pj_50')
    assert n and n['tipo'] == 'logro' and n['importancia'] == 5
    assert n['accion'] == {'pantalla': 'career_screen', 'texto': "VER LOGROS"}
    assert n['titular'].startswith("Logro") and len(n['titular']) <= 60
    ob = G.logros(e)['obtenidos']['pj_50']
    assert ob['temporada'] == e['temporada'] and ob['jornada'] == e['liga'].jornada_actual
    antes = len(N.lista(e))
    assert G.desbloquear(e, 'pj_50') is None and len(N.lista(e)) == antes
    assert G.desbloquear(e, 'no_existe') is None
    assert G.desbloquear(e, 'racha_8', temporada=7, jornada=12)
    assert G.logros(e)['obtenidos']['racha_8'] == {'temporada': 7, 'jornada': 12}


def test_para_overlay_orden():
    e = _estado()
    assert [f['obtenido'] for f in G.para_overlay(e)] == [False] * 9
    G.desbloquear(e, 'pj_50', temporada=1, jornada=10)
    G.desbloquear(e, 'racha_8', temporada=2, jornada=3)
    filas = G.para_overlay(e)
    assert len(filas) == 9 and [f['id'] for f in filas[:2]] == ['racha_8', 'pj_50']     # el más reciente arriba
    assert all(f['obtenido'] for f in filas[:2]) and not any(f['obtenido'] for f in filas[2:])
    assert all(f['titulo'] and f['descripcion'] for f in filas)
    assert (filas[0]['temporada'], filas[0]['jornada']) == (2, 3)


# ------------------------------------------------------------------ enganches
def test_armar_datos_registra_el_partido():
    from alpha_football.ui import postpartido as PP
    from alpha_football import partido_ctx as PC
    e = _estado(); mi = e['mi_equipo']; rival = _rivales(e)[0]
    e['liga'].jornada_actual = 1
    ctx = PC.nuevo_estado(mi, rival, [], [])
    PP.armar_datos(e, 'liga', mi, rival, 1, 0, ctx, {}, [])
    assert G.logros(e)['contadores']['pj'] == 1
    PP.armar_datos(e, 'amistoso', mi, rival, 1, 0, ctx, {}, [])
    assert G.logros(e)['contadores']['pj'] == 1


def test_generar_jornada_revisa_los_logros():
    from alpha_football import noticias_gen as NG
    e = _estado(); e['historial'] = [{'temporada': 1, 'pos': 1}]
    import random
    NG.generar_jornada(e, rng=random.Random(1))
    assert 'titulo_liga' in _obtenidos(e)


def test_el_cierre_de_temporada_revisa_los_logros():
    from alpha_football.ui.resumen_temporada_screen import avanzar_nueva_temporada
    e = _estado(); _poner_posicion(e, 1)
    avanzar_nueva_temporada(e)
    ob = G.logros(e)['obtenidos']
    assert e['temporada'] == 2 and ob.get('titulo_liga', {}).get('temporada') == 1


# ------------------------------------------------------------------ interfaz
def test_career_overlay():
    e = _estado()
    pygame.event.clear()
    assert C.render(screen, e) is None                                   # sin overlay, sin logros obtenidos
    assert not e.get('career_logros')
    _clic(C.R_LOGROS.center)
    assert C.render(screen, e) is None and e['career_logros'] is True    # el botón lo abre
    pygame.event.clear()
    assert C.render(screen, e) is None                                   # con 0 obtenidos dibuja
    _tecla(pygame.K_ESCAPE)
    assert C.render(screen, e) is None and not e['career_logros']        # ESC lo cierra sin volver
    _tecla(pygame.K_ESCAPE)
    assert C.render(screen, e) == 'volver'                               # cerrado, ESC sí vuelve
    _tecla(pygame.K_l)
    assert C.render(screen, e) is None and e['career_logros'] is True    # la tecla L lo abre
    _clic((5, 5))                                                        # clic fuera del panel lo cierra
    assert C.render(screen, e) is None and not e['career_logros']
    _tecla(pygame.K_l); C.render(screen, e)
    _clic(C.R_PANEL_LOGROS.center)                                       # clic dentro no lo cierra
    assert C.render(screen, e) is None and e['career_logros'] is True
    for _ in range(3):                                                   # la rueda desplaza sin pasarse
        _rueda(-1); C.render(screen, e)
    assert e['career_logros_scroll'] == len(C.filas_logros(e)) - C.FILAS_LOGROS
    for _ in range(3):
        _rueda(1); C.render(screen, e)
    assert e['career_logros_scroll'] == 0
    _tecla(pygame.K_DOWN); C.render(screen, e)
    assert e['career_logros_scroll'] == 1
    assert all(C.R_PANEL_LOGROS.contains(C.rect_fila_logro(i)) for i in range(C.FILAS_LOGROS))
    for i in IDS[:4]:
        G.desbloquear(e, i)
    pygame.event.clear()
    assert C.render(screen, e) is None                                   # con obtenidos y pendientes dibuja


def test_registro_ayuda_y_atajos():
    from alpha_football.ui import ayuda, atajos
    items = ayuda.AYUDA['career_screen']({})
    assert len(items) >= 3
    for rect, titulo, texto in items:
        assert pygame.Rect(0, 0, 1280, 720).contains(rect) and titulo and 0 < len(texto) <= 110, (titulo, texto)
    assert any(tuple(r) == tuple(C.R_LOGROS) for r, _t, _x in items)
    a = atajos.ATAJOS['career_screen']
    assert "L Logros" in a and "H Ayuda" in a and len(a) <= 150


if __name__ == '__main__':
    fallos = 0
    for nombre, f in sorted(globals().items()):
        if nombre.startswith('test_') and callable(f):
            try:
                f(); print(f"  {nombre}: OK")
            except Exception as ex:
                fallos += 1; print(f"  {nombre}: FALLA {type(ex).__name__}: {ex}")
    sys.exit(1 if fallos else 0)
