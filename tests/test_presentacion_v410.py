"""v4.1.0: presentación del partido — post-partido (calificaciones/tabla), pausas y cambios en vivo,
línea de tiempo de la simulación instantánea."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(17)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save
from alpha_football.models import alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams, _ligas_por_division
from alpha_football.ui import postpartido as PP
from alpha_football.engine import simular_partido
from alpha_football import partido_ctx as PC

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


def _partido(e):
    liga = e['liga']; a, b = liga.equipos[0], liga.equipos[1]
    random.seed(9); r = simular_partido(a, b, aplicar_fisico=False)
    return a, b, r


# ---------------------------------------------------------------- Task 4: postpartido
def test_linea_de_tiempo_filtra_y_ordena():
    e = estado_carrera(); a, b, r = _partido(e)
    lt = PP.linea_de_tiempo(r.eventos, a, b)
    assert [x['minuto'] for x in lt] == sorted(x['minuto'] for x in lt)
    assert {x['tipo'] for x in lt} <= {'gol', 'amarilla', 'roja', 'lesion', 'cambio', 'penal_fallado'}
    assert sum(1 for x in lt if x['tipo'] == 'gol') == r.goles_local + r.goles_visitante
    assert all(x['lado'] in ('l', 'v') and x['texto'] for x in lt)
    print("  test_linea_de_tiempo_filtra_y_ordena: OK")


def test_filas_calificaciones():
    e = estado_carrera(); a, b, r = _partido(e)
    filas = PP.filas_calificaciones(r.ctx, r.notas, 'l')
    assert len(filas) >= 11 and all(3.0 <= f['nota'] <= 10.0 for f in filas)
    assert filas[0]['pos'] == 'POR'
    entraron = [f for f in filas if f['entro']]
    assert all(filas.index(f) >= 11 for f in entraron)      # los que entraron van al final
    print("  test_filas_calificaciones: OK")


def test_postpartido_teclado():
    e = estado_carrera(); a, b, r = _partido(e)
    PP.armar_datos(e, 'liga', a, b, r.goles_local, r.goles_visitante, r.ctx, r.notas, r.eventos)
    assert PP.render(screen, e, (0, 0), None, [pygame.K_RIGHT]) is None and e['postpartido_tab'] == 'tabla'
    assert PP.render(screen, e, (0, 0), None, [pygame.K_LEFT]) is None and e['postpartido_tab'] == 'calificaciones'
    assert PP.render(screen, e, (0, 0), None, [pygame.K_RETURN]) == 'continuar'
    assert PP.render(screen, e, (0, 0), PP.R_CONTINUAR.center, []) == 'continuar'
    click(PP.R_TAB_TABLA.center)
    assert PP.render(screen, e, (0, 0), PP.R_TAB_TABLA.center, []) is None and e['postpartido_tab'] == 'tabla'
    print("  test_postpartido_teclado: OK")


def test_amistoso_sin_tabla():
    e = estado_carrera(); a, b, r = _partido(e)
    PP.armar_datos(e, 'amistoso', a, b, 1, 0, r.ctx, r.notas, r.eventos)
    PP.render(screen, e, (0, 0), None, [pygame.K_RIGHT])
    assert e.get('postpartido_tab', 'calificaciones') == 'calificaciones'
    print("  test_amistoso_sin_tabla: OK")


def test_posicion_liga():
    e = estado_carrera(); liga = e['liga']
    for i, eq in enumerate(liga.equipos):
        eq.puntos = 100 - i
    assert PP.posicion_liga(liga, liga.equipos[0].id) == 1
    assert PP.posicion_liga(liga, liga.equipos[-1].id) == len(liga.equipos)
    print("  test_posicion_liga: OK")


# ---------------------------------------------------------------- Task 5: en vivo
from alpha_football.ui import match_screen as MS


def _preparar_vivo(e):
    liga = e['liga']; mi = e['mi_equipo']
    p = next(p for p in liga.calendario if p.jornada == liga.jornada_actual and mi.id in (p.local_id, p.visitante_id))
    e['partido_actual'] = p; e['match_mode'] = 'liga'
    return p


def _vivo(e):
    if not getattr(e['liga'], 'calendario', None):
        from alpha_football.ui.league_screen import inicializar_calendario_liga
        inicializar_calendario_liga(e['liga'])
    p = _preparar_vivo(e); pygame.event.clear(); MS.render(screen, e)
    lado = 'l' if p.local_id == e['mi_equipo'].id else 'v'
    return p, lado


def _avanzar(e, hasta):
    """Avanza el reloj hasta `hasta` saltando pausas; si se abre el selector por lesión, elige el 1º."""
    vueltas = 0
    while e.get('sim_minuto', 0) < hasta and e.get('sim_estado') in ('jugando', 'segundo_tiempo'):
        vueltas += 1; assert vueltas < 5000, "el reloj no avanza"
        if e.get('sim_cambio_forzado') is not None:
            key(pygame.K_RETURN); MS.render(screen, e); continue
        e['sim_last_tick'] = -10**9; e['sim_pausa_hasta'] = 0
        pygame.event.clear(); MS.render(screen, e)


def _inyectar(e, ev):
    e['sim_eventos'] = [x for x in e['sim_eventos'] if x['minuto'] != ev['minuto']] + [ev]


def test_resim_respeta_expulsado():
    e = estado_carrera(); p, lado = _vivo(e)
    rival = 'v' if lado == 'l' else 'l'
    ctx = e['sim_ctx']; j = ctx.en_cancha[rival][4]
    _inyectar(e, {'minuto': 10, 'tipo': 'roja', 'lado': rival, 'equipo_id': ctx.ids_equipo[rival], 'jugador': j,
                  'jugador_id': j.id, 'motivo': 'directa', 'partidos': 1, 'detalle': 'roja'})
    _avanzar(e, 12)
    assert PC.clave(j) in e['sim_ctx'].fuera
    liga = e['liga']
    loc = next(x for x in liga.equipos if x.id == p.local_id); vis = next(x for x in liga.equipos if x.id == p.visitante_id)
    MS._cambiar_mentalidad_en_vivo(e, e['mi_equipo'], loc, vis, 'todo_o_nada', e['sim_minuto'])
    futuros = [x for x in e['sim_eventos'] if x['minuto'] > e['sim_minuto']]
    assert futuros and all(x.get('jugador') is not j for x in futuros)
    print("  test_resim_respeta_expulsado: OK")


def test_lesion_sin_cambios():
    e = estado_carrera(); p, lado = _vivo(e)
    ctx = e['sim_ctx']; e['sim_subs_realizadas'] = 5
    j = ctx.en_cancha[lado][6]
    _inyectar(e, {'minuto': 20, 'tipo': 'lesion', 'lado': lado, 'equipo_id': ctx.ids_equipo[lado], 'jugador': j,
                  'jugador_id': j.id, 'partidos': 2, 'detalle': 'lesion'})
    _avanzar(e, 22)
    assert e.get('sim_cambio_forzado') is None
    assert len(e['sim_ctx'].en_cancha[lado]) <= 10 and j not in e['sim_ctx'].en_cancha[lado]
    print("  test_lesion_sin_cambios: OK")


def test_lesion_abre_selector_y_cambia():
    e = estado_carrera(); p, lado = _vivo(e)
    ctx = e['sim_ctx']; j = ctx.en_cancha[lado][6]
    _inyectar(e, {'minuto': 20, 'tipo': 'lesion', 'lado': lado, 'equipo_id': ctx.ids_equipo[lado], 'jugador': j,
                  'jugador_id': j.id, 'partidos': 2, 'detalle': 'lesion'})
    subs0 = e['sim_subs_realizadas']
    while e['sim_minuto'] < 20:
        if e.get('sim_cambio_forzado') is not None:
            key(pygame.K_RETURN); MS.render(screen, e); subs0 = e['sim_subs_realizadas']; continue
        e['sim_last_tick'] = -10**9; e['sim_pausa_hasta'] = 0; pygame.event.clear(); MS.render(screen, e)
    assert e.get('sim_cambio_forzado') == PC.clave(j)
    key(pygame.K_RETURN); MS.render(screen, e)
    assert e.get('sim_cambio_forzado') is None and j not in e['sim_ctx'].en_cancha[lado]
    assert len(e['sim_ctx'].en_cancha[lado]) == 11 and e['sim_subs_realizadas'] == subs0 + 1
    print("  test_lesion_abre_selector_y_cambia: OK")


def test_pausa_en_gol():
    e = estado_carrera(); p, lado = _vivo(e)
    ctx = e['sim_ctx']; j = ctx.en_cancha[lado][9]
    _inyectar(e, {'minuto': 5, 'tipo': 'gol', 'lado': lado, 'equipo_id': ctx.ids_equipo[lado], 'jugador': j,
                  'jugador_id': j.id, 'asistente': None, 'defensor': None, 'penal': False, 'detalle': 'gol'})
    while e['sim_minuto'] < 5:
        e['sim_last_tick'] = -10**9; e['sim_pausa_hasta'] = 0; e['sim_flash_goles'] = 0
        e.pop('sim_cambio_forzado', None); pygame.event.clear(); MS.render(screen, e)
    assert e['sim_pausa_hasta'] > pygame.time.get_ticks() and e['sim_aviso']['tipo'] == 'gol'
    m = e['sim_minuto']; e['sim_last_tick'] = -10**9; pygame.event.clear(); MS.render(screen, e)
    assert e['sim_minuto'] == m                       # pausado: no avanza
    key(pygame.K_SPACE); MS.render(screen, e)
    assert e['sim_pausa_hasta'] == 0 and e['sim_flash_goles'] == 0
    print("  test_pausa_en_gol: OK")


def test_tactico_no_cambia_expulsado():
    from alpha_football.ui import team_screen as TS
    e = estado_carrera(); p, lado = _vivo(e)
    mi = e['mi_equipo']; alin = mi.alineacion_activa; js = mi.jugadores
    j = js[alin.titulares[3]]
    PC.aplicar_evento(e['sim_ctx'], {'minuto': 5, 'tipo': 'roja', 'lado': lado, 'jugador': j, 'jugador_id': j.id,
                                     'motivo': 'directa', 'partidos': 1})
    antes = list(alin.titulares)
    TS._cambio_en_partido(e, alin, js, ('campo', 3), ('banco', 0), 0, set())
    assert alin.titulares == antes and e.get('sim_subs_realizadas', 0) == 0
    print("  test_tactico_no_cambia_expulsado: OK")


# ---------------------------------------------------------------- Task 6: simulación instantánea
def test_instantaneo_resumen_luego_post():
    from alpha_football.ui import prepartido_screen as PR
    e = estado_carrera()
    if not getattr(e['liga'], 'calendario', None):
        from alpha_football.ui.league_screen import inicializar_calendario_liga
        inicializar_calendario_liga(e['liga'])
    p = _preparar_vivo(e); liga = e['liga']
    loc = next(x for x in liga.equipos if x.id == p.local_id); vis = next(x for x in liga.equipos if x.id == p.visitante_id)
    random.seed(4); PR._simular_instantaneo(e, loc, vis)
    r = e['prepartido_resultado']
    assert 'linea' in r and all('minuto' in x and 'texto' in x for x in r['linea'])
    assert sum(1 for x in r['linea'] if x['tipo'] == 'gol') == p.goles_local + p.goles_visitante
    assert e.get('postpartido') and p.jugado and e['postpartido'].get('pos_antes')
    key(pygame.K_RETURN); PR.render(screen, e)          # resumen -> post
    assert e.get('prepartido_paso') == 'post'
    key(pygame.K_RETURN); dest = PR.render(screen, e)   # post -> continuar
    assert dest == 'league_screen' and 'prepartido_resultado' not in e and 'postpartido' not in e
    print("  test_instantaneo_resumen_luego_post: OK")


# ---------------------------------------------------------------- revisión final: medio tiempo y alineación
def _hasta(e, minuto):
    while e['sim_minuto'] < minuto and e.get('sim_estado') in ('jugando', 'segundo_tiempo'):
        if e.get('sim_cambio_forzado') is not None and e['sim_minuto'] < minuto - 1:
            key(pygame.K_RETURN); MS.render(screen, e); continue
        e['sim_last_tick'] = -10**9; e['sim_pausa_hasta'] = 0; e['sim_flash_goles'] = 0
        pygame.event.clear(); MS.render(screen, e)


def test_enter_en_aviso_del_45_no_salta_medio_tiempo():
    e = estado_carrera(); p, lado = _vivo(e)
    ctx = e['sim_ctx']; j = ctx.en_cancha[lado][9]
    _inyectar(e, {'minuto': 45, 'tipo': 'gol', 'lado': lado, 'equipo_id': ctx.ids_equipo[lado], 'jugador': j,
                  'jugador_id': j.id, 'asistente': None, 'defensor': None, 'penal': False, 'detalle': 'gol'})
    _hasta(e, 45)
    assert e['sim_estado'] == 'medio_tiempo' and e['sim_pausa_hasta'] > pygame.time.get_ticks()
    key(pygame.K_RETURN); MS.render(screen, e)
    assert e['sim_estado'] == 'medio_tiempo', "el Enter del aviso no debe reanudar el descanso"
    print("  test_enter_en_aviso_del_45_no_salta_medio_tiempo: OK")


def test_selector_en_descanso_no_reanuda():
    e = estado_carrera(); p, lado = _vivo(e)
    ctx = e['sim_ctx']; j = ctx.en_cancha[lado][6]
    _inyectar(e, {'minuto': 45, 'tipo': 'lesion', 'lado': lado, 'equipo_id': ctx.ids_equipo[lado], 'jugador': j,
                  'jugador_id': j.id, 'partidos': 2, 'detalle': 'lesion'})
    _hasta(e, 45)
    assert e['sim_estado'] == 'medio_tiempo' and e.get('sim_cambio_forzado') == PC.clave(j)
    key(pygame.K_RETURN); MS.render(screen, e)
    assert e.get('sim_cambio_forzado') is None and e['sim_estado'] == 'medio_tiempo'
    print("  test_selector_en_descanso_no_reanuda: OK")


def test_alineacion_se_restaura_antes_de_cerrar_la_jornada():
    e = estado_carrera(); p, lado = _vivo(e)
    orden = []
    orig_fin, orig_rest = MS.finalizar_jornada_liga, MS._restaurar_alineacion
    MS.finalizar_jornada_liga = lambda *a, **k: orden.append('jornada')
    MS._restaurar_alineacion = lambda *a, **k: orden.append('alineacion')
    try:
        liga = e['liga']
        loc = next(x for x in liga.equipos if x.id == p.local_id); vis = next(x for x in liga.equipos if x.id == p.visitante_id)
        mi = e['mi_equipo']
        MS._cerrar_partido_vivo(e, 'liga', liga, mi, p, loc, vis, mi, mi.alineacion_activa, 1, 0)
    finally:
        MS.finalizar_jornada_liga, MS._restaurar_alineacion = orig_fin, orig_rest
    assert orden == ['alineacion', 'jornada'], orden
    print("  test_alineacion_se_restaura_antes_de_cerrar_la_jornada: OK")


if __name__ == '__main__':
    for _n, _f in list(globals().items()):
        if _n.startswith('test_') and callable(_f):
            _f()
    print("OK test_presentacion_v410")
