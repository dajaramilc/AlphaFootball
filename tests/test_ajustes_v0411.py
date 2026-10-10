"""v0.4.11.0: ajustes (volver a la notificación, goles totales, ofertas DT, objetivos, canteranos)."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
screen = pygame.display.set_mode((1280, 720))
from alpha_football import save
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402
from alpha_football import correo as C


def key(k):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=''))


def test_volver_desde_el_destino_regresa_al_correo():
    for salida in ('volver', 'league_screen'):
        e = {'volver_notif': 'finanzas_screen'}
        assert C.retorno(e, 'finanzas_screen', salida) == 'correo_screen'
        assert 'volver_notif' not in e


def test_navegar_mas_adentro_conserva_la_marca():
    e = {'volver_notif': 'plantilla_screen'}
    assert C.retorno(e, 'plantilla_screen', 'negociacion_screen') == 'negociacion_screen'
    assert C.retorno(e, 'negociacion_screen', 'plantilla_screen') == 'plantilla_screen'
    assert e['volver_notif'] == 'plantilla_screen'
    assert C.retorno(e, 'plantilla_screen', 'volver') == 'correo_screen'


def test_marca_vieja_se_borra_al_seguir_desde_el_hub():
    e = {'volver_notif': 'plantilla_screen'}
    assert C.retorno(e, 'league_screen', 'team_screen') == 'team_screen'
    assert 'volver_notif' not in e
    assert C.retorno(e, 'plantilla_screen', 'volver') == 'volver'      # ya no vuelve al correo


def test_sin_marca_o_sin_cambio_no_toca_nada():
    assert C.retorno({}, 'finanzas_screen', 'volver') == 'volver'
    e = {'volver_notif': 'finanzas_screen'}
    assert C.retorno(e, 'finanzas_screen', None) is None and e['volver_notif'] == 'finanzas_screen'


def test_pestana_del_hub_no_se_borra_al_abrir_una_tarjeta():
    e = {'volver_notif': 'league_screen', 'volver_notif_tab': 'negociaciones'}
    assert C.retorno(e, 'league_screen', 'buscador_screen') == 'buscador_screen'
    assert e['volver_notif'] == 'league_screen'


def test_ir_desde_un_mensaje_deja_la_marca():
    from alpha_football.ui import correo_screen as CS
    e = estado_carrera()
    m1 = C.enviar(e, 'club', "a", "b", C.accion('finanzas_screen', "VER FINANZAS"))
    assert CS._ir(e, m1) == 'finanzas_screen' and e['volver_notif'] == 'finanzas_screen'
    m2 = C.enviar(e, 'club', "a", "b", C.accion('negociaciones', "IR A NEGOCIACIONES"))
    assert CS._ir(e, m2) == 'league_screen'
    assert e['volver_notif'] == 'league_screen' and e['volver_notif_tab'] == 'negociaciones'


def test_esc_en_la_pestana_abierta_desde_un_mensaje_vuelve_al_correo():
    from alpha_football.ui import league_screen as L
    e = estado_carrera()
    from alpha_football import dias as _D                  # v0.4.13.0: el cartel es por fecha y solo con reloj
    e['datos_carrera']['aviso_mercado_visto'] = [1, _D.hoy(e).isoformat()]     # sin cartel de mercado
    e.update(hub_tab='negociaciones', volver_notif='league_screen', volver_notif_tab='negociaciones')
    pygame.event.clear(); L.render(screen, e)              # primer cuadro: inicializa el hub
    key(pygame.K_ESCAPE)
    assert L.render(screen, e) == 'correo_screen'
    assert 'volver_notif' not in e and e['hub_tab'] == 'inicio'


def test_cambiar_de_pestana_borra_la_marca_del_hub():
    from alpha_football.ui import league_screen as L
    e = estado_carrera()
    from alpha_football import dias as _D                  # v0.4.13.0: el cartel es por fecha y solo con reloj
    e['datos_carrera']['aviso_mercado_visto'] = [1, _D.hoy(e).isoformat()]
    e.update(hub_tab='oficina', volver_notif='league_screen', volver_notif_tab='negociaciones')
    pygame.event.clear(); L.render(screen, e)
    assert 'volver_notif' not in e


def test_goles_totales_suma_liga_y_copas():
    from alpha_football import competiciones as CP
    e = estado_carrera(); mi = e['mi_equipo']; j = mi.jugadores[0]
    j.goles = 4
    assert CP.goles_totales(e, j) == 4                                 # sin copas: solo liga
    e['datos_carrera']['copas'] = {
        'champions': {'stats': {f"{mi.nombre}|{j.nombre_completo}": {'nombre': j.nombre_completo, 'club': mi.nombre, 'goles': 3},
                                f"Otro|{j.nombre_completo}": {'nombre': j.nombre_completo, 'club': 'Otro', 'goles': 9}}},
        'libertadores': {'stats': {}}}
    assert CP.goles_totales(e, j) == 7                                 # no suma al homónimo de otro club
    assert CP.goles_totales(e, j, mi.nombre, CP.goles_copa(e)) == 7    # con club e índice dados
    assert CP.club_de(e, j) == mi.nombre
    rival = e['liga'].equipos[1]
    assert CP.club_de(e, rival.jugadores[0]) == rival.nombre


def test_goles_totales_con_datos_rotos():
    from alpha_football import competiciones as CP
    e = estado_carrera(); j = e['mi_equipo'].jugadores[0]; j.goles = 2
    e['datos_carrera']['copas'] = {'champions': None, 'libertadores': {'stats': {'x': {'goles': 'n/a'}}}}
    assert CP.goles_totales(e, j) == 2
    assert CP.goles_totales({}, j) == 2


def test_en_banda_tiene_piso():
    from alpha_football import entrenadores as EN
    e = estado_carrera(); mi = e['mi_equipo']

    class Club:
        pass
    q = Club()
    for calif, dentro, fuera in ((75, (-2, 0, 10), (-3, 11, -20)),
                                 (60, (-4, 0, 5), (-5, 6, -20)),
                                 (30, (-6, -3, 0), (-7, 1, -20))):
        e['datos_carrera']['calif_dt'] = calif
        for d in dentro:
            q.ovr_promedio = mi.ovr_promedio + d
            assert EN.en_banda(e, q), (calif, d)
        for d in fuera:
            q.ovr_promedio = mi.ovr_promedio + d
            assert not EN.en_banda(e, q), (calif, d)


def test_objetivo_exigente_solo_con_el_parametro():
    from alpha_football import directiva as D
    assert D.objetivo_por_ranking(8, 20, 1, 4)[:2] == ('mitad', 8)                       # IA: como antes
    assert D.objetivo_por_ranking(8, 20, 1, 4, exigente=True)[:2] == ('mitad', 6)         # dos puestos más
    assert D.objetivo_por_ranking(6, 20, 1, 4, exigente=True)[:2] == ('copa', 4)          # 6º por media: copa
    assert D.objetivo_por_ranking(1, 20, 1, 4, ventaja=3)[:2] == ('copa', 4)
    assert D.objetivo_por_ranking(1, 20, 1, 4, ventaja=3, exigente=True)[:2] == ('campeon', 1)
    assert D.objetivo_por_ranking(1, 20, 1, 4, ventaja=2, exigente=True)[:2] == ('copa', 4)
    assert D.objetivo_por_ranking(3, 12, 2, 0, exigente=True)[:2] == ('ascenso', 2)
    assert D.objetivo_por_ranking(4, 12, 2, 0, exigente=True)[:2] == ('mitad', 3)         # en 2ª, solo un puesto más
    assert D.objetivo_por_ranking(1, 12, 1, 3, exigente=True)[1] >= 1                     # nunca bajo el 1º


def test_objetivo_exigente_en_liga_de_12():
    from alpha_football import directiva as D
    metas = [D.objetivo_por_ranking(r, 12, 1, 5, exigente=True)[1] for r in range(1, 13)]
    assert metas == [5, 5, 5, 5, 5, 5, 5, 6, 7, 10, 10, 10]
    assert D.objetivo_por_ranking(9, 12, 1, 5, exigente=True)[0] == 'mitad'               # "entre los 7 primeros"
    assert [D.objetivo_por_ranking(r, 12, 1, 5)[1] for r in range(1, 13)] == [5, 5, 5, 5, 5, 6, 10, 10, 10, 10, 11, 11]


def test_el_objetivo_del_user_es_el_exigente():
    from alpha_football import directiva as D
    from alpha_football.ui.copa_screen import cupos_copa
    e = estado_carrera('premier', 5); liga, mi = e['liga'], e['mi_equipo']
    obj = D.definir_objetivo(e)
    rk = sorted(liga.equipos, key=lambda x: -x.ovr_promedio)
    r = next(i + 1 for i, x in enumerate(rk) if x is mi)
    esperado = D.objetivo_por_ranking(r, len(rk), 1, cupos_copa('premier'),
                                      rk[0].ovr_promedio - rk[1].ovr_promedio, exigente=True)
    assert (obj['tipo'], obj['pos_max']) == esperado[:2]


def test_canterano_se_guarda():
    from alpha_football.models import Jugador
    j = Jugador(nombre="A", apellido="B", posicion="MED", ataque=60, defensa=60, fisico=60, tecnica=60, mental=60)
    assert j.canterano == ''
    j.canterano = 'Club X'
    assert Jugador.from_dict(j.to_dict()).canterano == 'Club X'
    viejo = j.to_dict(); viejo.pop('canterano', None)                              # save viejo: sin el campo
    assert Jugador.from_dict(viejo).canterano == ''


def test_subir_de_la_cantera_marca_al_canterano():
    from alpha_football import cantera as CA
    e = estado_carrera(); mi = e['mi_equipo']
    jid = CA.cantera(e)[0].id
    ok, _msg = CA.subir(e, jid)
    assert ok
    assert next(x for x in mi.jugadores if x.id == jid).canterano == mi.nombre


def test_factor_canterano():
    from alpha_football import desarrollo as DS
    from alpha_football.models import Jugador
    e = estado_carrera(); mi, otro = e['mi_equipo'], e['liga'].equipos[1]
    j = Jugador(nombre="A", apellido="B", posicion="MED", ataque=60, defensa=60, fisico=60, tecnica=60, mental=60)
    j.edad = 19
    assert DS.factor_canterano(j, mi) == 1.0                    # no es canterano
    j.canterano = mi.nombre
    assert DS.factor_canterano(j, mi) == DS.BOOST_CANTERANO == 1.35     # v0.4.18.0: antes 1.5
    assert DS.factor_canterano(j, otro) == 1.0                  # vendido o cedido: se apaga
    j.edad = DS.EDAD_BOOST_CANTERANO
    assert DS.factor_canterano(j, mi) == 1.35
    j.edad = DS.EDAD_BOOST_CANTERANO + 1
    assert DS.factor_canterano(j, mi) == 1.0


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
