"""v2.5.0: mentalidad en partido (autobús → todo o nada), del user y de la IA."""
import sys, os, random, copy
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(11)

from alpha_football import engine
from alpha_football.engine import _decidir_mentalidad as decidir
from alpha_football.models import Equipo
from alpha_football.ui.menu import load_league_teams

N = int(os.environ.get("N_MENT", 1500))


def equipos():
    return load_league_teams('premier').equipos


def promedio_goles(local, visitante, ment_l, ment_v, n=N):
    tot, recibidos_l = 0, 0
    for _ in range(n):
        r = engine.simular_partido(local, visitante, ment_l=ment_l, ment_v=ment_v)
        tot += r.goles_local + r.goles_visitante
        recibidos_l += r.goles_visitante
    return tot / n, recibidos_l / n


def test_decidir_mentalidad_umbrales():
    assert decidir(0, 1, 0, 0, True) == 'normal'
    assert decidir(-9, 1, 0, 0, False) == 'defensiva'
    assert decidir(-9, 1, 0, 0, True) == 'normal'            # +2 por local
    assert decidir(-14, 1, 0, 0, False) == 'autobus'
    assert decidir(-14, 1, 0, 0, True) == 'defensiva'        # local nunca autobús de base
    assert decidir(8, 1, 0, 0, False) == 'ofensiva'
    assert decidir(0, 69, 0, 1, True) == 'normal'
    assert decidir(0, 70, 0, 1, True) == 'ofensiva'
    assert decidir(0, 82, 1, 3, True) == 'todo_o_nada'
    assert decidir(0, 88, 0, 3, True) == 'normal'            # perdiendo por 3+: se rinde
    assert decidir(0, 75, 1, 0, True) == 'defensiva'
    assert decidir(-3, 85, 1, 0, False) == 'autobus'         # ganando, más débil, 85'
    assert decidir(3, 85, 1, 0, False) == 'defensiva'        # ganando, más fuerte
    assert decidir(0, 80, 2, 0, True) == 'normal'            # ganando por 2: base
    print("  test_decidir_mentalidad_umbrales: OK")


def _pct_goles_def(local, vis, ment):
    pos = {j.id: j.posicion for j in local.jugadores}
    defs = tot = 0
    for _ in range(N):
        r = engine.simular_partido(local, vis, ment_l=ment, ment_v='normal')
        for e in r.eventos:
            if e.get('tipo') == 'gol' and e.get('equipo_id') == local.id:
                tot += 1
                defs += pos.get(e.get('jugador_id')) == 'DEF'
    return defs, tot


def test_goleadores_por_mentalidad():
    # Los defensas atacan el 40% de las veces en TODO O NADA pero rematan peor, así que
    # su % de goles queda lejos de 40: se exige que sea claramente mayor que en NORMAL.
    eq = equipos()
    d_n, t_n = _pct_goles_def(eq[0], eq[1], 'normal')
    d_t, t_t = _pct_goles_def(eq[0], eq[1], 'todo_o_nada')
    d_a, t_a = _pct_goles_def(eq[0], eq[1], 'autobus')
    print(f"    goles de DEF: normal {d_n}/{t_n} · todo o nada {d_t}/{t_t} · autobús {d_a}/{t_a}")
    assert d_t / t_t > 0.12 and d_t / t_t > 3 * (d_n / t_n)
    assert t_a > 0 and d_a == 0
    print("  test_goleadores_por_mentalidad: OK")


def test_calibracion_parejos():
    a = equipos()[0]
    b = copy.deepcopy(a)
    nn, rec_normal = promedio_goles(a, b, 'normal', 'normal')
    ab, _ = promedio_goles(a, b, 'autobus', 'normal')
    tn, rec_todo = promedio_goles(a, b, 'todo_o_nada', 'normal')
    print(f"    normal-normal {nn:.2f} · autobus-normal {ab:.2f} · todo-normal {tn:.2f} "
          f"(recibe {rec_todo:.2f} vs {rec_normal:.2f})")
    assert 2.2 <= nn <= 2.9, nn                 # normal = motor previo sin cambios
    assert ab < 1.8, ab
    assert tn > 3.5, tn
    assert rec_todo > rec_normal
    print("  test_calibracion_parejos: OK")


def test_ia_vs_ia_ligas_reales():
    tot = n = 0
    for tipo in ('premier', 'laliga', 'betplay', 'brasil', 'argentina'):
        eqs = load_league_teams(tipo).equipos
        for _ in range(300):
            l, v = random.sample(eqs, 2)
            r = engine.simular_partido(l, v, aplicar_fisico=False)   # v3.1.0: calibración sin cansancio acumulado
            tot += r.goles_local + r.goles_visitante
            n += 1
    prom = tot / n
    print(f"    IA vs IA: {prom:.2f} goles/partido")
    assert 2.5 <= prom <= 3.0, prom
    print("  test_ia_vs_ia_ligas_reales: OK")


def test_eventos_de_cambio_de_mentalidad():
    eq = equipos()
    hubo = False
    for _ in range(300):
        r = engine.simular_partido(eq[0], eq[1])
        for e in r.eventos:
            if e.get('tipo') == 'mentalidad':
                hubo = True
                assert e['mentalidad'] in engine.MENTALIDADES and e['minuto'] > 1
                assert "pasa a" in e['detalle']
    assert hubo, "la IA nunca cambió de mentalidad en 300 partidos"
    print("  test_eventos_de_cambio_de_mentalidad: OK")


def test_guardado_mentalidad():
    e = equipos()[0]
    e.mentalidad = 'ofensiva'
    assert Equipo.from_dict(e.to_dict()).mentalidad == 'ofensiva'
    d = e.to_dict(); d['mentalidad'] = 'cualquiera'
    assert Equipo.from_dict(d).mentalidad == 'normal'
    d.pop('mentalidad')
    assert Equipo.from_dict(d).mentalidad == 'normal'
    print("  test_guardado_mentalidad: OK")


screen = pygame.display.set_mode((1280, 720))


def click(pos):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def estado_carrera():
    from alpha_football.models import alineacion_por_defecto
    liga = load_league_teams('premier')
    mi = liga.equipos[0]
    mi.alineacion_activa = alineacion_por_defecto(mi)
    return {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
            'alineacion_activa': mi.alineacion_activa, 'team_contexto': 'carrera'}


def test_direccion_cambia_y_cancela_mentalidad():
    from alpha_football.ui import team_screen
    e = estado_carrera()
    mi = e['mi_equipo']
    assert mi.mentalidad == 'normal'
    pygame.event.clear()
    team_screen.render(screen, e)
    r = team_screen._rects_cabecera()
    click(r['ment_next'].center)
    team_screen.render(screen, e)
    assert mi.mentalidad == 'ofensiva'
    click(r['cancel'].center)
    team_screen.render(screen, e)
    assert mi.mentalidad == 'normal', "CANCELAR restaura la mentalidad"
    print("  test_direccion_cambia_y_cancela_mentalidad: OK")


def test_cambio_en_vivo_resimula_el_resto_de_la_mitad():
    from alpha_football.ui import match_screen
    e = estado_carrera()
    mi, rival = e['mi_equipo'], e['liga'].equipos[1]
    e.update(sim_suerte={'suerte_l': 0.0, 'suerte_v': 0.0}, sim_goles_l=0, sim_goles_v=0,
             sim_comentarios=[],
             sim_eventos=[{'minuto': 10, 'tipo': 'caotico', 'equipo_id': mi.id, 'detalle': 'ANTES'},
                          {'minuto': 30, 'tipo': 'caotico', 'equipo_id': mi.id, 'detalle': 'DESPUES'}])
    match_screen._cambiar_mentalidad_en_vivo(e, mi, mi, rival, 'todo_o_nada', 20)
    assert mi.mentalidad == 'todo_o_nada'
    detalles = [ev['detalle'] for ev in e['sim_eventos']]
    assert 'ANTES' in detalles and 'DESPUES' not in detalles
    assert all(ev['minuto'] <= 20 or 21 <= ev['minuto'] <= 45 for ev in e['sim_eventos'])
    assert e['sim_comentarios'] and 'TODO O NADA' in e['sim_comentarios'][-1]
    assert len(match_screen._rects_tira_mentalidad()) == 5
    print("  test_cambio_en_vivo_resimula_el_resto_de_la_mitad: OK")


def test_mentalidad_vuelve_al_terminar_el_partido():
    from alpha_football.ui import match_screen
    e = estado_carrera()
    mi = e['mi_equipo']
    foto = match_screen._snapshot_alineacion(mi, mi.alineacion_activa)
    mi.mentalidad = 'autobus'
    match_screen._restaurar_alineacion(mi, mi.alineacion_activa, foto)
    assert mi.mentalidad == 'normal'
    print("  test_mentalidad_vuelve_al_terminar_el_partido: OK")


def test_simulacion_instantanea_usa_la_mentalidad_del_user():
    from alpha_football.ui import prepartido_screen
    e = estado_carrera()
    mi, rival = e['mi_equipo'], e['liga'].equipos[1]
    mi.mentalidad = 'ofensiva'
    capturado = {}
    orig = engine.simular_partido
    def falso(local, visitante, *a, **kw):
        capturado.update(kw)
        raise RuntimeError("fin del test")
    engine.simular_partido = falso
    try:
        e['match_mode'] = 'liga'                                   # en amistoso el user es el local
        prepartido_screen._simular_instantaneo(e, rival, mi)       # el user de visitante
    finally:
        engine.simular_partido = orig
    assert capturado.get('ment_l') == 'ia' and capturado.get('ment_v') == 'ofensiva', capturado
    print("  test_simulacion_instantanea_usa_la_mentalidad_del_user: OK")


TESTS = [test_decidir_mentalidad_umbrales, test_goleadores_por_mentalidad, test_calibracion_parejos,
         test_ia_vs_ia_ligas_reales, test_eventos_de_cambio_de_mentalidad, test_guardado_mentalidad,
         test_direccion_cambia_y_cancela_mentalidad, test_cambio_en_vivo_resimula_el_resto_de_la_mitad,
         test_mentalidad_vuelve_al_terminar_el_partido, test_simulacion_instantanea_usa_la_mentalidad_del_user]


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
