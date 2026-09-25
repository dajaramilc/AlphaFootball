"""v4.3.0: correos de premio de copa y de objetivo cumplido, historial con copa, Balón de Oro liga + copa."""
import sys, os, random, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(13)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save
from alpha_football.models import alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams, _ligas_por_division

_tmp = tempfile.mkdtemp()
save.guardar_en_slot = lambda *a, **k: None          # los tests no tocan los slots reales


def click(pos):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def key(k, uni=''):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=uni))


def estado_carrera(tipo='premier', idx=0):
    liga = load_league_teams(tipo)
    mi = liga.equipos[idx]
    mi.alineacion_activa = alineacion_por_defecto(mi)
    primeras, segunda = _ligas_por_division(liga, {}, {})
    return {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
            'alineacion_activa': mi.alineacion_activa, 'primera_division': primeras,
            'segunda_division': segunda, 'datos_carrera': {}, 'historial': []}


# ---------------------------------------------------------------- Task 1: orden por columnas


# ---------------------------------------------------------------- Task 11: correos de premio y de objetivo
from alpha_football.ui import copa_screen as CS
from alpha_football import directiva as D, correo as C


def test_texto_premio_porcentajes():
    total = CS.premio_total('champions')
    assert total == sum(CS.PREMIO_FASE_CHAMPIONS.values())
    t = CS.texto_premio('champions', 'Cuartos', 11_000_000)
    assert 'Cuartos' in t and f"{round(5_000_000 * 100 / total)}%" in t and f"{round(11_000_000 * 100 / total)}%" in t
    print("  test_texto_premio_porcentajes: OK")


def test_correo_por_cada_fase_cobrada():
    e = estado_carrera(); orig = (CS.CP.tipo_copa_user, CS.CP.fase_user)
    CS.CP.tipo_copa_user = lambda est: 'champions'
    try:
        CS.CP.fase_user = lambda est: 'Octavos'
        n0 = len(C.bandeja(e))
        cobrado = CS.cobrar_premios_copa(e)
        fases = ['Fase de liga', 'Playoff', 'Octavos']
        assert cobrado == sum(CS.premio_fase('champions', f) for f in fases)
        asuntos = [m['asunto'] for m in C.bandeja(e)[:len(C.bandeja(e)) - n0]]   # los nuevos van primero
        assert sum(1 for a in asuntos if a.startswith('Premio')) == 3, asuntos
        n1 = len(C.bandeja(e))
        CS.cobrar_premios_copa(e)                       # nada nuevo que cobrar: sin correos
        assert len(C.bandeja(e)) == n1
    finally:
        CS.CP.tipo_copa_user, CS.CP.fase_user = orig
    print("  test_correo_por_cada_fase_cobrada: OK")


def test_objetivo_copa_cumplido_avisa_una_vez():
    e = estado_carrera(); orig = CS.CP.fase_user
    e['datos_carrera']['objetivo_copa'] = {'temporada': 1, 'fase': 'Cuartos', 'texto': 'Llegar a cuartos',
                                           'tipo': 'champions'}
    try:
        CS.CP.fase_user = lambda est: 'Octavos'
        assert D.revisar_objetivo_copa_cumplido(e) is False
        CS.CP.fase_user = lambda est: 'Semifinal'
        n0 = len(C.bandeja(e))
        assert D.revisar_objetivo_copa_cumplido(e) is True and len(C.bandeja(e)) == n0 + 1
        assert D.revisar_objetivo_copa_cumplido(e) is False and len(C.bandeja(e)) == n0 + 1
    finally:
        CS.CP.fase_user = orig
    print("  test_objetivo_copa_cumplido_avisa_una_vez: OK")


def _calendario(e):
    liga = e['liga']
    if not getattr(liga, 'calendario', None):
        from alpha_football.ui.league_screen import inicializar_calendario_liga
        inicializar_calendario_liga(liga)
    return liga


def test_peor_posicion_posible():
    e = estado_carrera(); liga = _calendario(e); mi = e['mi_equipo']
    for eq in liga.equipos:
        eq.puntos = 0
    mi.puntos = 100
    for p in liga.calendario:
        p.jugado = True
    assert D.peor_posicion_posible(liga, mi) == 1
    for p in liga.calendario:
        p.jugado = False
    mi.puntos = 0
    assert D.peor_posicion_posible(liga, mi) == len(liga.equipos)
    print("  test_peor_posicion_posible: OK")


def test_objetivo_liga_avisa_una_vez():
    e = estado_carrera(); liga = _calendario(e); mi = e['mi_equipo']
    D.definir_objetivo(e)
    for p in liga.calendario:
        p.jugado = True
    for eq in liga.equipos:
        eq.puntos = 0
    mi.puntos = 99
    n0 = len(C.bandeja(e))
    assert D.revisar_objetivo_liga_asegurado(e) is True and len(C.bandeja(e)) == n0 + 1
    assert D.revisar_objetivo_liga_asegurado(e) is False and len(C.bandeja(e)) == n0 + 1
    print("  test_objetivo_liga_avisa_una_vez: OK")


# ---------------------------------------------------------------- Task 12: historial con copa y Balón de Oro
def test_historial_incluye_copa():
    from alpha_football.ui import league_screen as L
    import alpha_football.competiciones as K
    e = estado_carrera(); liga = _calendario(e); mi = e['mi_equipo']
    K.iniciar_temporada(e, forzar=True)
    tipo = K.tipo_copa_user(e)
    assert tipo, "el club de prueba debería jugar copa"
    c = K.copa(e, tipo); user = K._nombre_user(e)
    p = next(x for x in sorted(c['partidos'], key=lambda x: x['fecha']) if user in (x['local'], x['visitante']))
    K.registrar_resultado_user(e, p['id'], 2, 1)
    pl = next(x for x in liga.calendario if x.jornada == 1 and mi.id in (x.local_id, x.visitante_id))
    pl.jugado, pl.goles_local, pl.goles_visitante = True, 1, 1
    h = L.partidos_historial(e)
    assert [x['etiqueta'] for x in h].count('UCL' if tipo == 'champions' else 'LIB') == 1
    assert any(x['etiqueta'] == 'J1' for x in h)
    assert h == sorted(h, key=lambda x: x['orden'], reverse=True)          # lo más reciente primero
    pygame.event.clear(); e['hub_tab'] = 'inicio'; L.render(screen, e)      # se dibuja sin errores
    print("  test_historial_incluye_copa: OK")


def test_balon_de_oro_cuenta_copa():
    from alpha_football import premios as P
    e = estado_carrera(); liga = e['liga']
    for eq in liga.equipos:
        for j in eq.jugadores:
            j.partidos_jugados = 0; j.goles = 0; j.asistencias = 0
    eq0 = liga.equipos[0]; estrella = eq0.jugadores[0]
    estrella.partidos_jugados = int(liga.num_jornadas * 0.3)            # con la liga sola no llega al 50%
    estrella.goles = 30
    otro = liga.equipos[1].jugadores[0]; otro.partidos_jugados = liga.num_jornadas; otro.goles = 1
    primeras = {liga.tipo: liga}
    copas = {'champions': {'stats': {f"{eq0.nombre}|{estrella.nombre_completo}": {
        'nombre': estrella.nombre_completo, 'club': eq0.nombre, 'pos': estrella.posicion,
        'goles': 8, 'asist': 0, 'pj': 10, 'vallas': 0}}}}
    nombres = lambda r: [f['nombre'] for f in (r or {}).get('podio', [])]
    sin = P.calcular_balon_de_oro(primeras, {}, 1, datos_copas=None)
    con = P.calcular_balon_de_oro(primeras, {}, 1, datos_copas=copas)
    assert estrella.nombre_completo not in nombres(sin)
    assert estrella.nombre_completo in nombres(con)
    ficha = next(f for f in con['podio'] if f['nombre'] == estrella.nombre_completo)
    assert ficha['pj'] == estrella.partidos_jugados + 10
    print("  test_balon_de_oro_cuenta_copa: OK")


if __name__ == '__main__':
    for _n, _f in list(globals().items()):
        if _n.startswith('test_') and callable(_f):
            _f()
    print("OK test_copa_v430")
