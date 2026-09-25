"""v3.8.0: competiciones reales — Champions (fase de liga suiza de 36) y Libertadores (8 grupos de 4)."""
import sys, os, random, tempfile, math, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(13)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import competiciones as CP, save
from alpha_football.models import alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams, _ligas_por_division

_tmp = tempfile.mkdtemp()
save.guardar_en_slot = lambda *a, **k: None          # los tests no tocan los slots reales


def click(pos):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def estado_carrera(tipo='premier', idx=None):
    """v3.8.0: por defecto el user dirige el club de mayor media de la liga (clasifica en la T1)."""
    liga = load_league_teams(tipo)
    if idx is None:
        idx = max(range(len(liga.equipos)), key=lambda i: liga.equipos[i].ovr_promedio)
    mi = liga.equipos[idx]
    mi.alineacion_activa = alineacion_por_defecto(mi)
    primeras, segunda = _ligas_por_division(liga, {}, {})
    return {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
            'alineacion_activa': mi.alineacion_activa, 'primera_division': primeras,
            'segunda_division': segunda, 'datos_carrera': {}, 'historial': []}


def _clubes(n, paises):
    return [{'nombre': f"C{i}", 'ovr': 90 - i // 2, 'pais': paises[i % len(paises)]} for i in range(n)]


# ── Task 1: sorteos, fechas, tablas y llaves ────────────────────────────────────

def test_fechas_monotonicas():
    for n in (17, 13):
        for J in (22, 10):
            js = [CP.jornada_de_fecha(i, n, J) for i in range(n)]
            assert js == sorted(js) and js[0] >= 1 and js[-1] == J - 1, (n, J, js)
    print("  test_fechas_monotonicas: OK")


def test_sorteo_fase_liga():
    peor = 0.0
    for seed in range(10):
        cl = _clubes(36, ['ING', 'ESP', 'ITA', 'ALE', 'FRA', 'POR', 'NED', 'BEL'])
        t0 = time.perf_counter()
        ps = CP.sorteo_fase_liga(cl, random.Random(seed))
        peor = max(peor, time.perf_counter() - t0)
        assert len(ps) == 144 and sorted({p['fecha'] for p in ps}) == list(range(8))
        bombo = {c['nombre']: i // 9 for i, c in enumerate(sorted(cl, key=lambda c: -c['ovr']))}
        pais = {c['nombre']: c['pais'] for c in cl}
        for c in cl:
            n = c['nombre']
            mios = [p for p in ps if n in (p['local'], p['visitante'])]
            assert len(mios) == 8 and sum(p['local'] == n for p in mios) == 4
            rivales = [p['visitante'] if p['local'] == n else p['local'] for p in mios]
            assert len(set(rivales)) == 8
            assert sorted(bombo[r] for r in rivales) == [0, 0, 1, 1, 2, 2, 3, 3]
            assert all(pais[r] != pais[n] for r in rivales)
            assert sorted(p['fecha'] for p in mios) == list(range(8))        # uno por fecha
    assert peor < 2.0, f"sorteo lento: {peor:.2f}s"
    print(f"  test_sorteo_fase_liga: OK (peor sorteo {peor:.3f}s)")


def test_sorteo_grupos():
    cl = _clubes(32, ['BRA'] * 7 + ['ARG'] * 6 + ['COL'] * 5 + ['URU'] * 5 + ['ECU'] * 5 + ['CHI', 'PAR', 'PER', 'BOL'])
    g = CP.sorteo_grupos(cl, random.Random(3))
    assert len(g) == 8 and all(len(x) == 4 for x in g)
    assert sorted(n for x in g for n in x) == sorted(c['nombre'] for c in cl)
    ps = CP.partidos_grupos(g)
    assert len(ps) == 96 and sorted({p['fecha'] for p in ps}) == list(range(6))
    print("  test_sorteo_grupos: OK")


def test_sorteo_grupos_por_bombo_sin_repetir_pais():
    # v3.8.0: cupos reales de la Libertadores (7 BRA, 6 ARG, 5 COL/URU/ECU + 4 de relleno), 10 semillas
    paises = ['BRA'] * 7 + ['ARG'] * 6 + ['COL'] * 5 + ['URU'] * 5 + ['ECU'] * 5 + ['CHI', 'PAR', 'PER', 'BOL']
    for seed in range(10):
        rng = random.Random(seed)
        cl = [{'nombre': f"L{i}", 'ovr': rng.randint(65, 85), 'pais': p} for i, p in enumerate(paises)]
        g = CP.sorteo_grupos(cl, random.Random(seed))
        bombo = {c['nombre']: i // 8 for i, c in enumerate(sorted(cl, key=lambda c: -c['ovr']))}
        pais = {c['nombre']: c['pais'] for c in cl}
        for x in g:
            assert sorted(bombo[n] for n in x) == [0, 1, 2, 3], x
            assert len({pais[n] for n in x}) == 4, x
    print("  test_sorteo_grupos_por_bombo_sin_repetir_pais: OK")


def test_sorteo_nunca_cuelga():
    cl = _clubes(32, ['BRA'])                          # todos del mismo país: debe relajar la regla
    assert len(CP.sorteo_grupos(cl, random.Random(1))) == 8
    assert len(CP.sorteo_fase_liga(_clubes(36, ['ING']), random.Random(1))) == 144
    print("  test_sorteo_nunca_cuelga: OK")


def test_tabla_y_cruces():
    nombres = [f"C{i}" for i in range(36)]
    ps = [{'local': nombres[i], 'visitante': nombres[35 - i], 'gl': 2, 'gv': 0, 'jugado': True} for i in range(18)]
    t = CP.tabla(nombres, ps)
    assert t[0]['pts'] == 3 and t[-1]['pts'] == 0 and len(t) == 36
    orden = [f"T{i}" for i in range(36)]
    tab = [{'nombre': n} for n in orden]
    assert CP.cruces_playoff(tab)[0] == ('T8', 'T23') and CP.cruces_playoff(tab)[-1] == ('T15', 'T16')
    octv = CP.cruces_octavos_champions(tab, {p: p[0] for p in CP.cruces_playoff(tab)})
    assert len(octv) == 8 and octv[0][0] == 'T0' and octv[0][1] == 'T15'
    assert octv[7] == ('T7', 'T8')
    print("  test_tabla_y_cruces: OK")


def test_cruces_octavos_libertadores():
    grupos = [[{'nombre': f"{chr(65 + g)}{p}"} for p in range(1, 5)] for g in range(8)]
    oc = CP.cruces_octavos_libertadores(grupos)
    assert len(oc) == 8 and oc[0] == ('A1', 'B2') and oc[1] == ('B1', 'A2') and oc[-1] == ('H1', 'G2')
    print("  test_cruces_octavos_libertadores: OK")


def test_llave_global_y_penales():
    ida = {'local': 'A', 'visitante': 'B', 'gl': 1, 'gv': 0, 'jugado': True}
    vuelta = {'local': 'B', 'visitante': 'A', 'gl': 1, 'gv': 0, 'jugado': True}
    g = CP.resolver_llave(ida, vuelta, random.Random(1), {'A': 80, 'B': 80})
    assert g in ('A', 'B') and 'penales' in vuelta
    vuelta2 = {'local': 'B', 'visitante': 'A', 'gl': 0, 'gv': 0, 'jugado': True}
    assert CP.resolver_llave(ida, vuelta2, random.Random(1), {}) == 'A'
    final = {'local': 'A', 'visitante': 'B', 'gl': 2, 'gv': 2, 'jugado': True}
    assert CP.resolver_llave(final, None, random.Random(2), {}) in ('A', 'B') and 'penales' in final
    # penales ya cargados (partido del user en vivo): se respetan
    final2 = {'local': 'A', 'visitante': 'B', 'gl': 0, 'gv': 0, 'jugado': True, 'penales': {'a': 3, 'b': 4}}
    assert CP.resolver_llave(final2, None, random.Random(2), {}) == 'B'
    print("  test_llave_global_y_penales: OK")


# ── Task 2: temporada de copa ───────────────────────────────────────────────────

def _estado_con_copas():
    e = estado_carrera()
    CP.iniciar_temporada(e, random.Random(5))
    return e


def test_clasificados_cupos():
    e = estado_carrera()
    ch, li = CP.clasificados(e, 'champions'), CP.clasificados(e, 'libertadores')
    assert len(ch) == 36 and len(li) == 32
    assert len({c['nombre'] for c in ch + li}) == 68
    from collections import Counter
    cnt = Counter(c['liga'] for c in ch)
    assert cnt['premier'] == cnt['laliga'] == cnt['seriea'] == 5
    cnt2 = Counter(c['liga'] for c in li)
    assert (cnt2['brasil'], cnt2['argentina'], cnt2['betplay'], cnt2['uruguay'], cnt2['ecuador']) == (7, 6, 5, 5, 5)
    print("  test_clasificados_cupos: OK")


def test_user_forzado_en_champions():
    e = _estado_con_copas()
    assert CP.tipo_copa_user(e) == 'champions'
    c = CP.copa(e, 'champions')
    assert len(c['clubes']) == 36 and len(c['partidos']) == 144 and len(c['fechas_jornada']) == 17
    assert len(CP.copa(e, 'libertadores')['partidos']) == 96
    json.dumps(e['datos_carrera'])                      # serializable (va al save)
    print("  test_user_forzado_en_champions: OK")


def test_temporada_completa_ambas_copas():
    e = _estado_con_copas(); liga = e['liga']
    t0 = time.perf_counter()
    for j in range(1, liga.num_jornadas + 1):
        liga.jornada_actual = j
        pend = CP.partido_pendiente_user(e)
        while pend:
            CP.registrar_resultado_user(e, pend['id'], 1, 0)
            pend = CP.partido_pendiente_user(e)
        CP.avanzar(e, random.Random(j))
    CP.simular_todo(e, random.Random(99))
    dt = time.perf_counter() - t0
    for t in ('champions', 'libertadores'):
        c = CP.copa(e, t)
        assert c['campeon'] and all(p['jugado'] for p in c['partidos']), t
        assert len([p for p in c['partidos'] if p.get('fase') == 'Final']) == 1
        assert CP.campeon(e, t) == c['campeon']
        assert c['stats'] and sum(s['goles'] for s in c['stats'].values()) > 0
    json.dumps(e['datos_carrera'])
    print(f"  test_temporada_completa_ambas_copas: OK ({dt:.1f}s)")


def test_user_eliminado_sigue_copa():
    e = _estado_con_copas(); t = CP.tipo_copa_user(e)
    if t is None: return
    mi = e['mi_equipo'].nombre
    liga = e['liga']
    for j in range(1, liga.num_jornadas + 1):
        liga.jornada_actual = j
        pend = CP.partido_pendiente_user(e)
        while pend:
            CP.registrar_resultado_user(e, pend['id'], 0, 5 if pend['local'] == mi else 0) if pend['local'] == mi \
                else CP.registrar_resultado_user(e, pend['id'], 5, 0)
            pend = CP.partido_pendiente_user(e)
        CP.avanzar(e, random.Random(j))
    assert CP.partido_pendiente_user(e) is None and CP.copa(e, t)['campeon'] != mi
    assert CP.copa(e, t)['campeon']                     # la copa siguió sin el user
    assert 'eliminado' in CP.linea_estado_user(e)
    print("  test_user_eliminado_sigue_copa: OK")


def test_resultado_user_no_se_pisa():
    e = _estado_con_copas(); t = CP.tipo_copa_user(e)
    if t is None: return
    e['liga'].jornada_actual = e['liga'].num_jornadas
    p = CP.partido_pendiente_user(e)
    CP.registrar_resultado_user(e, p['id'], 3, 3)
    CP.simular_todo(e, random.Random(1))
    q = next(x for x in CP.copa(e, t)['partidos'] if x['id'] == p['id'])
    assert (q['gl'], q['gv']) == (3, 3)
    print("  test_resultado_user_no_se_pisa: OK")


def test_fases_esperan_al_user():
    e = _estado_con_copas(); t = CP.tipo_copa_user(e)
    c = CP.copa(e, t)
    e['liga'].jornada_actual = e['liga'].num_jornadas
    CP.avanzar(e, random.Random(3))
    # el user no jugó la fecha 0: la copa se queda en esa fecha (salvo su partido)
    assert not any(p['jugado'] for p in c['partidos'] if p['fecha'] >= 1)
    assert all(p['jugado'] for p in c['partidos'] if p['fecha'] == 0 and e['mi_equipo'].nombre not in (p['local'], p['visitante']))
    assert c['llaves'] == []
    # la otra copa sí avanzó hasta el final
    assert CP.copa(e, 'libertadores')['campeon']
    print("  test_fases_esperan_al_user: OK")


def test_linea_estado_y_fase():
    e = _estado_con_copas()
    assert isinstance(CP.linea_estado_user(e), str)
    if CP.tipo_copa_user(e): assert CP.fase_user(e) in CP.FASES[CP.tipo_copa_user(e)]
    print("  test_linea_estado_y_fase: OK")


def test_equipo_por_nombre():
    e = _estado_con_copas()
    for t in ('champions', 'libertadores'):
        for c in CP.copa(e, t)['clubes']:
            eq = CP.equipo_por_nombre(e, c['nombre'])
            assert eq is not None and eq.nombre == c['nombre'] and eq.jugadores, c['nombre']
    assert CP.equipo_por_nombre(e, e['mi_equipo'].nombre) is e['mi_equipo']
    print("  test_equipo_por_nombre: OK")


# ── Task 3: integración (fachada copa_screen, directiva, premios, hooks) ─────────

def test_directiva_meta_copa_nueva():
    from alpha_football import directiva as D
    assert D.meta_copa(1, 36, ventaja=9) == 'Campeón'
    assert D.meta_copa(4, 36) == 'Finalista' and D.meta_copa(8, 36) == 'Semifinal'
    assert D.meta_copa(16, 36) == 'Cuartos' and D.meta_copa(30, 36) == 'Octavos'
    assert D.FASES_COPA[-1] == 'Campeón' and 'Octavos' in D.FASES_COPA
    print("  test_directiva_meta_copa_nueva: OK")


def test_objetivo_copa_con_motor():
    from alpha_football import directiva as D
    e = estado_carrera(); CP.iniciar_temporada(e, random.Random(5))
    from alpha_football.ui.copa_screen import sincronizar_copa_user
    sincronizar_copa_user(e)
    oc = D.definir_objetivo_copa(e)
    assert oc and oc['n'] == 36 and oc['fase'] in D.FASES_COPA
    # Libertadores: 'Fase de grupos' equivale a 'Fase de liga'
    e['copa_mejor_fase_temp'] = 'Fase de grupos'
    ev = D.evaluar_objetivo_copa(e, 1)
    assert ev['resultado'] in ('fallado', 'cumplido')
    print("  test_objetivo_copa_con_motor: OK")


def test_balon_de_oro_formula():
    from alpha_football import premios as PR
    class J: pass
    j = J(); j.goles, j.asistencias, j.promedio_nota, j.posicion, j.porterias_cero, j.overall = 10, 5, 7.5, 'DEL', 0, 85
    assert PR.puntaje_jugador(j, 1.0, True, False) == 10 * 4 + 5 * 2 + 15 + 15
    assert PR.puntaje_jugador(j, 1.0, False, True) == 10 * 4 + 5 * 2 + 15 + 20
    assert PR.puntaje_jugador(j, 0.5, False, False, goles_copa=5) == (60 + 10 + 15) * 0.5
    assert PR.PESO_LIGA_1A['seriea'] == 1.0 and PR.PESO_LIGA_1A['brasil'] == 0.85 and PR.PESO_LIGA_1A['ecuador'] == 0.75
    print("  test_balon_de_oro_formula: OK")


def test_balon_de_oro_suma_goles_de_copa():
    from alpha_football import premios as PR
    e = estado_carrera()
    liga = e['liga']
    for eq in liga.equipos:
        for j in eq.jugadores:
            j.partidos_jugados, j.promedio_nota, j.goles = 20, 6.0, 0
    estrella = liga.equipos[3].jugadores[0]
    dc = {'copas': {'champions': {'stats': {f"{liga.equipos[3].nombre}|{estrella.nombre_completo}": {
        'nombre': estrella.nombre_completo, 'club': liga.equipos[3].nombre, 'goles': 9, 'asist': 0, 'pj': 8, 'vallas': 0}}}}}
    balon = PR.calcular_balon_de_oro({'premier': liga}, {}, 1, None, datos_copas=dc['copas'])
    assert balon['ganador']['nombre'] == estrella.nombre_completo and balon['ganador']['goles_copa'] == 9
    print("  test_balon_de_oro_suma_goles_de_copa: OK")


def test_save_viejo_regenera_copa():
    e = estado_carrera()
    e['copa_bracket'] = {'cuartos': [{'a': 'X', 'b': 'Y'}]}; e['copa_fase_actual'] = 'cuartos'
    e['copa_grupo_partidos'] = [{'local': 'X', 'visitante': 'Y', 'jugado': False}]
    e['liga'].jornada_actual = 8
    from alpha_football.ui.copa_screen import sincronizar_copa_user
    sincronizar_copa_user(e)
    assert 'copa_bracket' not in e and 'copa_fase_actual' not in e and 'copa_grupo_partidos' not in e
    assert CP.copa(e, 'champions')
    c = CP.copa(e, 'champions')
    vencidas = [i for i, j in enumerate(c['fechas_jornada']) if e['liga'].jornada_actual > j]
    assert vencidas and all(p['jugado'] for p in c['partidos'] if p['fecha'] in vencidas)   # incluidas las del user
    assert e['copa_user_en_copa'] is True and e['copa_mejor_fase_temp'] in CP.FASES['champions']
    print("  test_save_viejo_regenera_copa: OK")


def test_jugar_lleva_a_copa_cuando_toca():
    e = estado_carrera(); CP.iniciar_temporada(e, random.Random(5))
    assert CP.tipo_copa_user(e)
    e['liga'].jornada_actual = CP.copa(e, CP.tipo_copa_user(e))['fechas_jornada'][0] + 1
    from alpha_football.ui.copa_screen import rival_copa_pendiente
    assert rival_copa_pendiente(e)[0] is not None
    # JUGAR en el hub → prepartido con el partido de copa preparado
    from alpha_football.ui import league_screen as L
    e['hub_tab'], e['hub_foco'] = 'inicio', 0
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_j, mod=0, unicode='j'))
    assert L.render(screen, e) == 'prepartido_screen'
    assert e['match_mode'] == 'copa' and e['partido_copa_dict']['id'].startswith('champions-0-')
    assert e['mi_equipo'] in (e['partido_local_obj'], e['partido_visitante_obj'])
    e['liga'].jornada_actual = 1
    assert rival_copa_pendiente(e) == (None, None)
    print("  test_jugar_lleva_a_copa_cuando_toca: OK")


def _jugar_hasta_llave(e, rng):
    """Juega (1-0 a favor del user) hasta que el próximo partido del user sea de una llave."""
    from alpha_football.ui import copa_screen as S
    liga, mi = e['liga'], e['mi_equipo'].nombre
    for j in range(1, liga.num_jornadas + 1):
        liga.jornada_actual = j
        CP.avanzar(e, rng)
        pend = CP.partido_pendiente_user(e)
        while pend:
            if pend.get('llave') is not None:
                return pend
            gl, gv = (1, 0) if pend['local'] == mi else (0, 1)
            S.preparar_partido_copa(e)
            S.registrar_resultado_copa(e, gl, gv)
            pend = CP.partido_pendiente_user(e)
    return None


def test_prepartido_sim_instantanea_copa_y_penales():
    """Flujo real: prepartido (simular al instante) registra en el motor; empate global → penales."""
    from alpha_football.ui import copa_screen as S, prepartido_screen as PP
    e = estado_carrera(); CP.iniciar_temporada(e, random.Random(5)); e['datos_carrera']['finanzas'] = {}
    rng = random.Random(4)
    pend = _jugar_hasta_llave(e, rng)
    assert pend is not None, "el user debería llegar a una llave ganando todo"
    # ida por la vía normal (sim instantánea de prepartido)
    assert S.preparar_partido_copa(e)
    pid = e['partido_copa_dict']['id']
    PP._simular_instantaneo(e, e['partido_local_obj'], e['partido_visitante_obj'])
    c = CP.copa(e, pend['tipo'])
    ida = next(p for p in c['partidos'] if p['id'] == pid)
    assert ida['jugado'] and 'partido_copa_dict' not in e
    # vuelta: forzamos que el global quede empatado y registramos con penales del partido en vivo
    liga = e['liga']
    while not CP.partido_pendiente_user(e):
        liga.jornada_actual += 1
    vuelta = CP.partido_pendiente_user(e)
    assert vuelta['ida_de'] == pid
    S.preparar_partido_copa(e)
    # la vuelta la abre de local el visitante de la ida: el mismo marcador (gl, gv) empata el global
    assert S.necesita_penales(e, ida['gl'], ida['gv'])
    assert not S.necesita_penales(e, ida['gl'] + 1, ida['gv'])
    mi = e['mi_equipo'].nombre
    S.registrar_resultado_copa(e, ida['gl'], ida['gv'], penales_user=(5, 3))
    llave = next(ll for ll in c['llaves'] if ll['vuelta'] == vuelta['id'])
    assert llave['ganador'] == mi
    v = next(p for p in c['partidos'] if p['id'] == vuelta['id'])
    assert v['penales'] == ({'a': 5, 'b': 3} if v['local'] == mi else {'a': 3, 'b': 5})
    print("  test_prepartido_sim_instantanea_copa_y_penales: OK")


def test_premios_por_fase():
    from alpha_football.ui import copa_screen as S
    e = estado_carrera(); CP.iniciar_temporada(e, random.Random(5)); e['datos_carrera']['finanzas'] = {'temporada': 1}
    mi = e['mi_equipo']; antes = mi.balance
    S.sincronizar_copa_user(e)
    assert mi.balance == antes + 2_000_000
    S.sincronizar_copa_user(e)
    assert mi.balance == antes + 2_000_000, "no se cobra dos veces"
    c = CP.copa(e, 'champions'); c['mejor_fase'][mi.nombre] = 'Cuartos'
    S.cobrar_premios_copa(e)
    assert mi.balance == antes + (2 + 1 + 3 + 5) * 1_000_000
    assert e['datos_carrera']['finanzas'].get('premios', 0) == 11_000_000
    print("  test_premios_por_fase: OK")


def test_finalizar_jornada_avanza_copas():
    from alpha_football.ui.match_screen import finalizar_jornada_liga
    e = estado_carrera(); CP.iniciar_temporada(e, random.Random(5))
    liga, mi = e['liga'], e['mi_equipo']
    from alpha_football.ui.league_screen import inicializar_calendario_liga
    inicializar_calendario_liga(liga)
    for _ in range(3):
        p = next(x for x in liga.calendario if x.jornada == liga.jornada_actual and mi.id in (x.local_id, x.visitante_id))
        finalizar_jornada_liga(e, liga, mi, p, 1, 0)
    lib = CP.copa(e, 'libertadores')
    assert liga.jornada_actual == 4 and all(p['jugado'] for p in lib['partidos'] if p['fecha'] == 0)
    print("  test_finalizar_jornada_avanza_copas: OK")


def test_fin_de_temporada_copas_y_balon():
    from alpha_football.ui.resumen_temporada_screen import avanzar_nueva_temporada
    e = estado_carrera(); CP.iniciar_temporada(e, random.Random(5))
    liga = e['liga']
    from alpha_football.ui.league_screen import inicializar_calendario_liga, completar_ligas_de_fondo
    inicializar_calendario_liga(liga)
    from alpha_football.ui.match_screen import simular_otros_partidos, actualizar_estadisticas_liga
    for j in range(1, liga.num_jornadas + 1):
        liga.jornada_actual = j
        simular_otros_partidos(liga, j)
        CP.avanzar(e)
    actualizar_estadisticas_liga(liga)
    completar_ligas_de_fondo(e)
    for eq in liga.equipos:
        for jj in eq.jugadores:
            jj.partidos_jugados = max(jj.partidos_jugados, 15)
    avanzar_nueva_temporada(e)
    hist = e['historial'][-1]
    assert hist['libertadores'] in CP.FASES['champions'], hist['libertadores']
    assert e['temporada'] == 2
    for t in ('champions', 'libertadores'):
        assert CP.copa(e, t)['temporada'] == 2 and not any(p['jugado'] for p in CP.copa(e, t)['partidos'])
    balon = e['datos_carrera']['balon_oro'][-1]
    assert balon['temporada'] == 1 and 'goles_copa' in balon['ganador']
    assert 'campeones_copas' in e['datos_carrera'] and e['datos_carrera']['campeones_copas'][-1]['temporada'] == 1
    assert 'copa_bracket' not in e and 'copa_fase_actual' not in e
    print("  test_fin_de_temporada_copas_y_balon: OK")


# ── Task 4: UI ───────────────────────────────────────────────────────────────────

def test_copa_screen_pestanas():
    from alpha_football.ui import copa_screen as S
    e = estado_carrera(); CP.iniciar_temporada(e, random.Random(5))
    e['liga'].jornada_actual = 12; CP.avanzar(e, random.Random(2))
    for clave in S.PESTANAS:
        click(S.rect_pestana(clave).center); assert S.render(screen, e) is None
        assert e['copa_pestana'] == clave
    click(S.R_SELECTOR_COPA.center); S.render(screen, e)
    assert e['copa_vista'] == 'libertadores'
    for clave in S.PESTANAS:
        click(S.rect_pestana(clave).center); assert S.render(screen, e) is None
    CP.simular_todo(e, random.Random(3))
    for tipo in ('champions', 'libertadores'):
        e['copa_vista'] = tipo
        for clave in S.PESTANAS:
            e['copa_pestana'] = clave; pygame.event.clear(); assert S.render(screen, e) is None
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode=''))
    assert S.render(screen, e) == 'volver' and e['hub_tab'] == 'oficina'
    print("  test_copa_screen_pestanas: OK")


def test_copa_screen_simular_resto():
    from alpha_football.ui import copa_screen as S
    e = estado_carrera(idx=0)
    e['mi_equipo'] = e['liga'].equipos[min(range(len(e['liga'].equipos)), key=lambda i: e['liga'].equipos[i].ovr_promedio)]
    CP.iniciar_temporada(e, random.Random(5))
    assert CP.tipo_copa_user(e) is None
    pygame.event.clear(); S.render(screen, e)
    click(S.R_SIMULAR.center); S.render(screen, e)
    assert CP.campeon(e, 'champions') and CP.campeon(e, 'libertadores')
    print("  test_copa_screen_simular_resto: OK")


def test_hub_tabla_copa():
    from alpha_football.ui import league_screen as L
    e = estado_carrera(); CP.iniciar_temporada(e, random.Random(5)); e['hub_tab'] = 'inicio'
    e.setdefault('datos_carrera', {})['aviso_mercado_visto'] = [1, e['liga'].jornada_actual]   # v4.4.0: sin cartel
    click(L.rect_tab_tabla('copa').center); L.render(screen, e)
    assert e['hub_tabla_tab'] == 'copa'
    pygame.event.clear(); assert L.render(screen, e) is None
    click(L.rect_tab_tabla('liga').center); L.render(screen, e)
    assert e['hub_tabla_tab'] == 'liga'
    print("  test_hub_tabla_copa: OK")


def test_linea_copa_eliminado_con_fase():
    from alpha_football.ui import copa_screen as S
    e = estado_carrera(); CP.iniciar_temporada(e, random.Random(5))
    c = CP.copa(e, 'champions'); mi = e['mi_equipo'].nombre
    c['llaves'] = [{'fase': 'Octavos', 'a': mi, 'b': 'X', 'ida': None, 'vuelta': None, 'ganador': 'X'}]
    c['mejor_fase'][mi] = 'Octavos'
    assert S.linea_copa_user(e) == "Copa: eliminado en Octavos (Champions)"
    c['campeon'] = mi
    assert S.linea_copa_user(e).startswith("Copa: ¡CAMPEONES")
    print("  test_linea_copa_eliminado_con_fase: OK")


def test_otras_ligas_copas():
    from alpha_football.ui import otras_ligas_screen as O
    e = estado_carrera(); CP.iniciar_temporada(e, random.Random(5))
    click(O.rect_tab_copas().center); assert O.render(screen, e) is None
    assert e.get('otras_ligas_copas')
    pygame.event.clear(); assert O.render(screen, e) is None
    CP.simular_todo(e, random.Random(3))
    for k in (0, 1):
        click(O.rect_pais(k).center); assert O.render(screen, e) is None
    print("  test_otras_ligas_copas: OK")


TESTS = [test_fechas_monotonicas, test_sorteo_fase_liga, test_sorteo_grupos,
         test_sorteo_grupos_por_bombo_sin_repetir_pais, test_sorteo_nunca_cuelga, test_tabla_y_cruces,
         test_cruces_octavos_libertadores, test_llave_global_y_penales,
         test_clasificados_cupos, test_user_forzado_en_champions, test_temporada_completa_ambas_copas,
         test_user_eliminado_sigue_copa, test_resultado_user_no_se_pisa, test_fases_esperan_al_user,
         test_linea_estado_y_fase, test_equipo_por_nombre,
         # v3.8.0 Task 3
         test_directiva_meta_copa_nueva, test_objetivo_copa_con_motor, test_balon_de_oro_formula,
         test_balon_de_oro_suma_goles_de_copa, test_save_viejo_regenera_copa,
         test_jugar_lleva_a_copa_cuando_toca, test_prepartido_sim_instantanea_copa_y_penales,
         test_premios_por_fase, test_finalizar_jornada_avanza_copas, test_fin_de_temporada_copas_y_balon,
         # v3.8.0 Task 4
         test_copa_screen_pestanas, test_copa_screen_simular_resto, test_hub_tabla_copa,
         test_linea_copa_eliminado_con_fase, test_otras_ligas_copas]


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
