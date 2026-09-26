"""Sanciones por competición (liga/copa separadas) y acumulación de amarillas (5 liga, 3 copa)."""
import sys, os, random, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(13)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save, sanciones as S, energia as E, correo as C
from alpha_football.models import Jugador
from alpha_football.formaciones import mejor_once

save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402


def _amarilla(j):
    return [{'tipo': 'amarilla', 'jugador': j, 'partidos': 0}]


def test_acumulacion_liga_y_aviso():
    j = estado_carrera()['mi_equipo'].jugadores[0]
    tipos = [[i['tipo'] for i in E.aplicar_incidencias(_amarilla(j))] for _ in range(4)]
    assert tipos == [[], [], [], ['aviso_amarillas']] and S.amarillas(j, 'liga') == 4
    out = E.aplicar_incidencias(_amarilla(j))
    assert out[0]['tipo'] == 'sancion' and out[0]['motivo'] == 'acumulacion' and out[0]['competicion'] == 'liga'
    assert S.partidos_sancion(j, 'liga') == 1 and S.amarillas(j, 'liga') == 0
    assert S.amarillas(j, 'copa') == 0 and not S.sancionado(j, 'copa')
    print("  test_acumulacion_liga_y_aviso: OK")


def test_acumulacion_copa_separada():
    j = estado_carrera()['mi_equipo'].jugadores[1]
    with S.en_competicion('copa'):
        for _ in range(2):
            E.aplicar_incidencias(_amarilla(j))
        assert S.amarillas(j) == 2
        E.aplicar_incidencias(_amarilla(j))
    assert S.sancionado(j, 'copa') and not S.sancionado(j, 'liga') and S.amarillas(j, 'liga') == 0
    assert S.competicion_actual() == 'liga'                      # el contexto se restaura
    print("  test_acumulacion_copa_separada: OK")


def test_roja_de_copa_se_cumple_en_copa():
    e = estado_carrera(); mi = e['mi_equipo']
    js = mi.jugadores
    estrella = js[mejor_once(js, "4-3-3")[5]]
    with S.en_competicion('copa'):
        E.aplicar_incidencias([{'tipo': 'sancion', 'jugador': estrella, 'partidos': 1}])
        assert estrella.sancion_copa == 1 and estrella.partidos_sancion == 0
        assert all(js[i] is not estrella for i in mejor_once(js, "4-3-3"))     # no juega la copa
    assert any(js[i] is estrella for i in mejor_once(js, "4-3-3"))              # sí juega la liga
    # partido de liga sin él: la sanción de copa no se descuenta
    E.cerrar_partido(mi, {x.id: 90 for x in js[:11] if x is not estrella}, incidencias=[])
    assert estrella.sancion_copa == 1
    with S.en_competicion('copa'):
        E.cerrar_partido(mi, {x.id: 90 for x in js[:11] if x is not estrella}, incidencias=[])
    assert estrella.sancion_copa == 0
    print("  test_roja_de_copa_se_cumple_en_copa: OK")


def test_doble_amarilla_no_acumula():
    from alpha_football.partido_ctx import nuevo_estado, aplicar_evento, incidencias_de
    from alpha_football.engine import _once_titular
    e = estado_carrera(); mi, rival = e['mi_equipo'], e['liga'].equipos[1]
    ctx = nuevo_estado(mi, rival, _once_titular(mi), _once_titular(rival), auto_l=False, auto_v=True)
    a, b = _once_titular(mi)[3], _once_titular(mi)[4]
    for ev in ({'tipo': 'amarilla', 'jugador': a}, {'tipo': 'amarilla', 'jugador': b},
               {'tipo': 'amarilla', 'jugador': b}, {'tipo': 'roja', 'jugador': b, 'motivo': 'doble amarilla'}):
        aplicar_evento(ctx, dict(ev, minuto=30, lado='l', jugador_id=ev['jugador'].id))
    inc = incidencias_de(ctx, 'l')
    amar = [i['jugador'] for i in inc if i['tipo'] == 'amarilla']
    assert amar == [a] and any(i['tipo'] == 'sancion' and i['jugador'] is b for i in inc)
    print("  test_doble_amarilla_no_acumula: OK")


def test_correos_del_vestuario():
    from alpha_football.vestuario import post_partido_user
    e = estado_carrera(); mi, rival = e['mi_equipo'], e['liga'].equipos[1]
    j = mi.jugadores[mejor_once(mi.jugadores, "4-3-3")[2]]
    j.amarillas_liga = 3
    minutos = {x.id: 90 for x in mi.jugadores[:11]}
    post_partido_user(e, mi, rival, 1, 0, [], minutos, incidencias=_amarilla(j), incidencias_rival=[])
    assert any(m['asunto'].startswith("En riesgo") for m in C.bandeja(e))
    post_partido_user(e, mi, rival, 1, 0, [], minutos, incidencias=_amarilla(j), incidencias_rival=[])
    assert any(m['asunto'].startswith("Suspensión por acumulación") for m in C.bandeja(e))
    assert S.partidos_sancion(j, 'liga') == 1
    print("  test_correos_del_vestuario: OK")


def test_guardar_y_nueva_temporada():
    j = estado_carrera()['mi_equipo'].jugadores[2]
    j.amarillas_liga, j.amarillas_copa, j.sancion_copa, j.partidos_sancion = 4, 2, 1, 1
    copia = Jugador.from_dict(json.loads(json.dumps(j.to_dict())))
    assert (copia.amarillas_liga, copia.amarillas_copa, copia.sancion_copa) == (4, 2, 1)
    viejo = Jugador.from_dict({'nombre': 'A', 'apellido': 'B'})
    assert (viejo.amarillas_liga, viejo.amarillas_copa, viejo.sancion_copa) == (0, 0, 0)
    S.nueva_temporada(j)
    assert (j.amarillas_liga, j.amarillas_copa, j.sancion_copa, j.partidos_sancion) == (0, 0, 0, 0)
    print("  test_guardar_y_nueva_temporada: OK")


def test_pantallas_con_copa():
    from alpha_football.ui import team_screen as T, plantilla_screen as PS
    e = estado_carrera(); mi = e['mi_equipo']
    j = mi.jugadores[0]; j.sancion_copa = 1; j.amarillas_liga = 2
    assert T.baja_de(e, j, False) is None                        # en liga puede jugar
    with S.en_competicion('copa'):
        assert T.baja_de(e, j, False) == 'roja'
    e['match_mode'] = 'copa'; e['team_contexto'] = 'carrera'
    pygame.event.clear(); T.render(screen, e)                    # se dibuja con las sanciones de copa
    e.pop('match_mode')
    pygame.event.clear(); PS.render(screen, e)
    assert S.competicion_actual() == 'liga'
    print("  test_pantallas_con_copa: OK")


TESTS = [test_acumulacion_liga_y_aviso, test_acumulacion_copa_separada, test_roja_de_copa_se_cumple_en_copa,
         test_doble_amarilla_no_acumula, test_correos_del_vestuario, test_guardar_y_nueva_temporada,
         test_pantallas_con_copa]


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
