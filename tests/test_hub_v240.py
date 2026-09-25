"""v2.4.0: hub de carrera por columnas + copa automática desde JUGAR."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(7)
screen = pygame.display.set_mode((1280, 720))

from alpha_football.models import alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams, _ligas_por_division
from alpha_football.ui import copa_screen, league_screen
from alpha_football import competiciones as CP       # v3.8.0


def click(pos):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def key(k):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=''))


def estado_carrera():
    liga = load_league_teams('premier')
    mi = liga.equipos[0]
    alin = alineacion_por_defecto(mi)
    mi.alineacion_activa = alin
    primeras, segunda = _ligas_por_division(liga, {}, {})
    return {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
            'alineacion_activa': alin, 'primera_division': primeras, 'segunda_division': segunda,
            'team_contexto': 'carrera',
            'datos_carrera': {'aviso_mercado_visto': [1, 1]}}   # v4.4.0: sin cartel de mercado en J1


def estado_copa():
    """
    v3.8.0: carrera con el user en la Champions (club de mayor media de la Premier) y la fecha 1
    de la fase de liga ya vencida (se juega tras la J2 → JUGAR la ofrece en la J3).
    """
    e = estado_carrera()
    mi = max(e['liga'].equipos, key=lambda x: x.ovr_promedio)
    mi.alineacion_activa = alineacion_por_defecto(mi)
    e['mi_equipo'], e['alineacion_activa'] = mi, mi.alineacion_activa
    e['datos_carrera'] = {}
    CP.iniciar_temporada(e, random.Random(5))
    e['liga'].jornada_actual = CP.copa(e, 'champions')['fechas_jornada'][0] + 1
    e['datos_carrera']['aviso_mercado_visto'] = [1, e['liga'].jornada_actual]   # v4.4.0: sin cartel
    copa_screen.sincronizar_copa_user(e)
    assert e['copa_user_en_copa'] is True
    return e


def partidos_user(e):
    mi = e['mi_equipo'].nombre
    return [p for p in CP.copa(e, 'champions')['partidos'] if mi in (p['local'], p['visitante'])]


def test_preparar_partido_copa_grupos():
    """v3.8.0: (antes: grupos) el partido pendiente de la fase de liga queda listo para prepartido."""
    e = estado_copa()
    assert copa_screen.preparar_partido_copa(e) is True
    assert e['match_mode'] == 'copa' and e['partido_actual'] is None
    nombres = {e['partido_local_obj'].nombre, e['partido_visitante_obj'].nombre}
    assert e['mi_equipo'].nombre in nombres
    assert e['partido_copa_dict']['fecha'] == 0 and e['partido_copa_dict']['fase'] == 'Fase de liga'
    assert 'partido_copa_bracket_fase' not in e
    print("  test_preparar_partido_copa_grupos: OK")


def test_preparar_partido_copa_sin_pendiente():
    e = estado_copa()
    e['liga'].jornada_actual = 1                     # la fecha 1 de copa aún no se juega
    assert copa_screen.preparar_partido_copa(e) is False
    assert e.get('match_mode') != 'copa'
    assert copa_screen.rival_copa_pendiente(e) == (None, None)
    print("  test_preparar_partido_copa_sin_pendiente: OK")


def _ganar_grupos(e):
    """v3.8.0: (antes: 3 de grupo) el user gana 3-0 sus 8 partidos de la fase de liga."""
    mi = e['mi_equipo'].nombre
    for p in partidos_user(e):
        if p['fase'] == 'Fase de liga' and not p['jugado']:
            CP.registrar_resultado_user(e, p['id'], 3 if p['local'] == mi else 0, 0 if p['local'] == mi else 3)


def test_sincronizar_simula_ajenos_y_pasa_a_cuartos():
    """v3.8.0: (antes: pasa a cuartos) sincronizar juega lo ajeno vencido y, con la fase de liga
    terminada, arma las llaves; el user top 8 pasa directo a octavos."""
    e = estado_copa()
    mi = e['mi_equipo'].nombre
    c = CP.copa(e, 'champions')
    copa_screen.sincronizar_copa_user(e)
    f0 = [p for p in c['partidos'] if p['fecha'] == 0]
    assert all(p['jugado'] for p in f0 if mi not in (p['local'], p['visitante']))
    assert not any(p['jugado'] for p in partidos_user(e))
    f1 = [p for p in c['partidos'] if p['fecha'] == 1]
    assert not any(p['jugado'] for p in f1), "la fecha 2 aún no se juega"
    # El user gana sus 8 partidos y la liga llega a la fecha de octavos.
    _ganar_grupos(e)
    e['liga'].jornada_actual = c['fechas_jornada'][9] + 1
    copa_screen.sincronizar_copa_user(e)
    assert all(p['jugado'] for p in c['partidos'] if p['fase'] == 'Fase de liga')
    assert c['fase_actual'] in ('Octavos', 'Playoff') and e['copa_mejor_fase_temp'] == 'Octavos'
    print("  test_sincronizar_simula_ajenos_y_pasa_a_cuartos: OK")


def test_preparar_partido_copa_eliminatoria():
    e = estado_copa()
    _ganar_grupos(e)
    c = CP.copa(e, 'champions')
    e['liga'].jornada_actual = c['fechas_jornada'][10] + 1
    copa_screen.sincronizar_copa_user(e)
    e['partido_copa_dict'] = {'basura': True}         # resto de un partido anterior
    fase_nombre, rival = copa_screen.rival_copa_pendiente(e)
    assert fase_nombre == "Champions · Octavos (ida)" and rival
    assert copa_screen.preparar_partido_copa(e) is True
    assert e['mi_equipo'] in (e['partido_local_obj'], e['partido_visitante_obj'])
    assert rival in (e['partido_local_obj'].nombre, e['partido_visitante_obj'].nombre)
    assert e['partido_copa_dict']['fase'] == 'Octavos' and 'basura' not in e['partido_copa_dict']
    assert 'partido_copa_bracket_fase' not in e
    print("  test_preparar_partido_copa_eliminatoria: OK")


def test_linea_copa_user():
    e = estado_copa()
    linea = copa_screen.linea_copa_user(e)
    assert linea.startswith("Copa · Champions · Fase de liga (fecha 1/8) vs ") and "(tras J2)" in linea, linea
    c = CP.copa(e, 'champions'); mi = e['mi_equipo'].nombre
    c['llaves'] = [{'fase': 'Playoff', 'a': mi, 'b': 'X', 'ida': None, 'vuelta': None, 'ganador': 'X'}]
    c['mejor_fase'][mi] = 'Playoff'
    assert copa_screen.linea_copa_user(e) == "Copa: eliminado en Playoff (Champions)"
    c['campeon'] = mi
    assert copa_screen.linea_copa_user(e) == "Copa: ¡CAMPEONES de la Champions!"
    e['mi_equipo'] = min(e['liga'].equipos, key=lambda x: x.ovr_promedio)     # club sin copa
    assert copa_screen.linea_copa_user(e) is None
    print("  test_linea_copa_user: OK")


def test_retornos_de_copa():
    from alpha_football.ui import prepartido_screen
    # Resultado de un partido de copa simulado al instante → Inicio.
    e = estado_copa()
    assert copa_screen.preparar_partido_copa(e)
    e['prepartido_resultado'] = {'titulo': '1 - 0', 'goles': []}
    e['hub_tab'] = 'oficina'
    # v3.9.0: CONTINUAR subió para no quedar bajo la barra de atajos → se usa su rect real
    boton = prepartido_screen.rects_resultado(False)['continuar'].center
    res = prepartido_screen._render_resultado(screen, e, (0, 0), boton)
    assert res == 'league_screen' and e['hub_tab'] == 'inicio'
    # Salir de la pantalla de copa con Esc → pestaña OFICINA.
    e = estado_copa()
    e['hub_tab'] = 'inicio'
    key(pygame.K_ESCAPE)
    assert copa_screen.render(screen, e) == 'volver' and e['hub_tab'] == 'oficina'
    # La pantalla de copa no lanza partidos: Enter no hace nada con un partido pendiente.
    e = estado_copa()
    key(pygame.K_RETURN)
    copa_screen.render(screen, e)
    copa_screen.render(screen, e)
    assert e.get('match_mode') != 'copa'
    print("  test_retornos_de_copa: OK")


def test_pestanas_y_tarjetas_llevan_a_cada_pantalla():
    esperado = {'direccion': ['team_screen', 'plantilla_screen'],
                'negociaciones': ['buscador_screen', 'ofertas_screen', 'historial_pases_screen', 'ojeador_screen'],
                'oficina': ['correo_screen', 'stats_screen', 'copa_screen', 'career_screen', 'otras_ligas_screen', 'objetivos_screen',
                            'contrato_dt_screen', 'ofertas_dt_screen'],      # v3.2.0: MI CONTRATO · v3.4.0: OFERTAS DT
                'finanzas': ['finanzas_screen', 'plantilla_screen']}
    rects = league_screen._rects_barra()
    assert len(rects) == 6          # v4.2.0: GUARDAR pasó a OPCIONES
    for i, tab in enumerate(league_screen.PESTANAS):
        if tab == 'inicio':
            continue
        for k, destino in enumerate(esperado[tab]):
            e = estado_carrera()
            click(rects[i].center)
            assert league_screen.render(screen, e) is None and e['hub_tab'] == tab
            click(league_screen._rects_tarjetas(len(esperado[tab]))[k].center)
            assert league_screen.render(screen, e) == destino, (tab, destino)
            pygame.event.clear()
            assert league_screen.render(screen, e) is None and e['hub_tab'] == tab, "vuelve a la misma pestaña"
    e = estado_carrera()
    click(rects[5].center)
    assert league_screen.render(screen, e) == 'options_screen' and e['options_return'] == 'league_screen'
    print("  test_pestanas_y_tarjetas_llevan_a_cada_pantalla: OK")


def test_teclado_pestanas():
    e = estado_carrera()
    key(pygame.K_RIGHT)
    assert league_screen.render(screen, e) is None and e['hub_tab'] == 'direccion'
    key(pygame.K_RETURN)
    assert league_screen.render(screen, e) == 'team_screen' and e['team_contexto'] == 'carrera'
    key(pygame.K_ESCAPE)
    assert league_screen.render(screen, e) is None and e['hub_tab'] == 'inicio'
    key(pygame.K_ESCAPE)                              # v3.6.0: en INICIO, Esc abre el diálogo de salida
    assert league_screen.render(screen, e) is None and e['dialogo_salir']
    key(pygame.K_s)
    assert league_screen.render(screen, e) == 'menu'
    print("  test_teclado_pestanas: OK")


def test_panel_jornada_teclado_y_reinicio():
    e = estado_carrera()
    liga = e['liga']
    key(pygame.K_DOWN)
    league_screen.render(screen, e)
    assert e['hub_foco'] == 1 and e['hub_jornada_vista'] == 1
    key(pygame.K_RIGHT)
    league_screen.render(screen, e)
    assert e['hub_tab'] == 'inicio' and e['hub_jornada_vista'] == 2
    for _ in range(40):
        key(pygame.K_RIGHT); league_screen.render(screen, e)
    assert e['hub_jornada_vista'] == liga.num_jornadas
    for _ in range(40):
        key(pygame.K_LEFT); league_screen.render(screen, e)
    assert e['hub_jornada_vista'] == 1
    click(league_screen._rects_jornada()[1].center)
    league_screen.render(screen, e)
    assert e['hub_jornada_vista'] == 2
    liga.jornada_actual = 3                              # se jugó una jornada: vuelve al default
    pygame.event.clear()
    league_screen.render(screen, e)
    assert e['hub_jornada_vista'] == 3
    print("  test_panel_jornada_teclado_y_reinicio: OK")


def test_jugar_liga_y_copa():
    e = estado_carrera()
    click(league_screen.R_JUGAR.center)
    assert league_screen.render(screen, e) == 'prepartido_screen'
    assert e['match_mode'] == 'liga' and e['partido_actual'].jornada == 1
    e = estado_copa()
    click(league_screen.R_JUGAR.center)
    assert league_screen.render(screen, e) == 'prepartido_screen' and e['match_mode'] == 'copa'
    e = estado_copa()
    e['hub_tab'] = 'oficina'
    key(pygame.K_j)                                      # J juega desde cualquier pestaña
    assert league_screen.render(screen, e) == 'prepartido_screen' and e['match_mode'] == 'copa'
    print("  test_jugar_liga_y_copa: OK")


def test_copa_antes_que_avanzar_temporada():
    e = estado_copa()
    liga = e['liga']
    league_screen.inicializar_calendario_liga(liga)
    liga.jornada_actual = liga.num_jornadas
    for p in liga.calendario:
        p.jugado, p.goles_local, p.goles_visitante = True, 0, 0
    click(league_screen.R_JUGAR.center)
    assert league_screen.render(screen, e) == 'prepartido_screen' and e['match_mode'] == 'copa'
    print("  test_copa_antes_que_avanzar_temporada: OK")


def test_alertas_inicio():
    e = estado_carrera()
    mi = e['mi_equipo']
    t0 = mi.jugadores[e['alineacion_activa'].titulares[0]]
    t0.lesion_partidos = 2
    e['ofertas_recibidas'] = [{}, {}]
    avisos = league_screen._alertas_inicio(e, mi)
    assert any(t0.apellido in texto for texto, _ in avisos)
    assert avisos[-1][0] == "2 ofertas sin responder"
    assert len(avisos) <= 3
    print("  test_alertas_inicio: OK")


def test_guardar_sin_salir():
    from alpha_football import save
    from alpha_football.ui import save_slots_screen
    orig_slot, orig_partida = save.guardar_en_slot, save.guardar_partida
    llamados = []
    save.guardar_en_slot = lambda est, n, nombre: llamados.append((n, nombre))
    save.guardar_partida = lambda est: llamados.append(('fallback', None))
    try:
        e = estado_carrera()
        e['save_slots_return'] = 'league_screen'
        click((140 + 260, 190 + 26))                     # slot 1
        assert save_slots_screen.render(screen, e) == 'league_screen'
        assert llamados and llamados[0][0] == 1, llamados
        assert e['hub_toast'][0] == "Guardado en slot 1"
        assert e['slot_activo'] == 1
        click((360 + 120, 560 + 24))                     # SALIR AL MENÚ
        assert save_slots_screen.render(screen, e) == 'menu'
    finally:
        save.guardar_en_slot, save.guardar_partida = orig_slot, orig_partida
    print("  test_guardar_sin_salir: OK")


def test_panel_muestra_la_ultima_jornada_al_jugarla():
    e = estado_carrera()
    liga = e['liga']
    league_screen.inicializar_calendario_liga(liga)
    n = liga.num_jornadas
    liga.jornada_actual = n
    for p in liga.calendario:
        if p.jornada < n:
            p.jugado, p.goles_local, p.goles_visitante = True, 1, 0
    pygame.event.clear()
    league_screen.render(screen, e)
    assert e['hub_jornada_vista'] == n - 1              # J_N sin resultados: la última jugada
    for p in liga.calendario:
        if p.jornada == n:
            p.jugado, p.goles_local, p.goles_visitante = True, 2, 2
    pygame.event.clear()
    league_screen.render(screen, e)
    assert e['hub_jornada_vista'] == n, "tras jugar la última jornada se muestra esa"
    print("  test_panel_muestra_la_ultima_jornada_al_jugarla: OK")


def test_linea_copa_campeon_sin_copa_campeon():
    """v3.8.0: el título sale del motor aunque falte la clave derivada copa_campeon."""
    e = estado_copa()
    CP.copa(e, 'champions')['campeon'] = e['mi_equipo'].nombre
    e.pop('copa_campeon', None)
    assert copa_screen.linea_copa_user(e) == "Copa: ¡CAMPEONES de la Champions!"
    print("  test_linea_copa_campeon_sin_copa_campeon: OK")


def test_enter_no_reabre_guardar_al_volver():
    e = estado_carrera()
    e['hub_tab'], e['hub_bar_foco'], e['hub_foco'] = 'inicio', 5, 0   # volvió de GUARDAR
    key(pygame.K_RETURN)
    assert league_screen.render(screen, e) == 'prepartido_screen'
    print("  test_enter_no_reabre_guardar_al_volver: OK")


TESTS = [test_preparar_partido_copa_grupos, test_preparar_partido_copa_sin_pendiente,
         test_sincronizar_simula_ajenos_y_pasa_a_cuartos, test_preparar_partido_copa_eliminatoria,
         test_linea_copa_user, test_retornos_de_copa,
         test_pestanas_y_tarjetas_llevan_a_cada_pantalla, test_teclado_pestanas,
         test_panel_jornada_teclado_y_reinicio, test_jugar_liga_y_copa,
         test_copa_antes_que_avanzar_temporada, test_alertas_inicio,
         test_guardar_sin_salir, test_panel_muestra_la_ultima_jornada_al_jugarla,
         test_linea_copa_campeon_sin_copa_campeon, test_enter_no_reabre_guardar_al_volver]


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
