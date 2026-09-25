"""v2.8.0: OFICINA — objetivos de la directiva, confianza, premio/multa y despido."""
import sys, os, random, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(13)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import directiva as D, save
from alpha_football.models import alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams, _ligas_por_division

_tmp = tempfile.mkdtemp()
save.guardar_en_slot = lambda *a, **k: None          # los tests no tocan los slots reales


def click(pos):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def estado_carrera(tipo='premier', idx=0):
    liga = load_league_teams(tipo)
    mi = liga.equipos[idx]
    mi.alineacion_activa = alineacion_por_defecto(mi)
    primeras, segunda = _ligas_por_division(liga, {}, {})
    return {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
            'alineacion_activa': mi.alineacion_activa, 'primera_division': primeras,
            'segunda_division': segunda, 'datos_carrera': {}, 'historial': []}


def test_objetivo_por_ranking():
    assert D.objetivo_por_ranking(1, 20, 1, 4, ventaja=10)[:2] == ('campeon', 1)
    assert D.objetivo_por_ranking(1, 20, 1, 4, ventaja=3)[:2] == ('copa', 4)
    assert D.objetivo_por_ranking(3, 20, 1, 4)[:2] == ('copa', 4)
    assert D.objetivo_por_ranking(4, 20, 1, 4)[:2] == ('mitad', 5)       # ranking + 1 de margen
    assert D.objetivo_por_ranking(8, 20, 1, 4)[:2] == ('mitad', 9)
    assert D.objetivo_por_ranking(15, 20, 1, 4)[:2] == ('salvarse', 18)
    assert D.objetivo_por_ranking(1, 8, 2, 0)[:2] == ('ascenso', 2)
    assert D.objetivo_por_ranking(5, 8, 2, 0)[:2] == ('mitad', 6)
    print("  test_objetivo_por_ranking: OK")


def test_definir_objetivo_una_vez_por_temporada():
    e = estado_carrera()
    obj = D.definir_objetivo(e)
    assert obj['temporada'] == 1 and obj['tipo'] in D.TIPOS and obj['texto']
    assert obj['presupuesto_ref'] == e['mi_equipo'].balance
    e['mi_equipo'].balance += 1
    assert D.definir_objetivo(e) is obj                    # misma temporada: no cambia
    e['temporada'] = 2
    assert D.definir_objetivo(e)['temporada'] == 2
    print("  test_definir_objetivo_una_vez_por_temporada: OK")


def test_confianza():
    e = estado_carrera()
    assert D.confianza(e) == D.CONFIANZA_INICIAL
    D.actualizar_confianza(e, 2, 0)
    assert D.confianza(e) == D.CONFIANZA_INICIAL + 3
    D.actualizar_confianza(e, 0, 1); D.actualizar_confianza(e, 0, 1)
    assert D.confianza(e) == D.CONFIANZA_INICIAL - 3
    D.actualizar_confianza(e, 1, 1)
    assert D.confianza(e) == D.CONFIANZA_INICIAL - 3
    for _ in range(50):
        D.actualizar_confianza(e, 0, 3)
    assert D.confianza(e) == 0
    print("  test_confianza: OK")


def test_evaluar_temporada():
    e = estado_carrera()
    obj = D.definir_objetivo(e)
    obj.update(tipo='copa', pos_max=4)
    ref = obj['presupuesto_ref']
    bal = e['mi_equipo'].balance
    r = D.evaluar_temporada(e, 2)                          # superado
    assert r['resultado'] == 'superado' and e['mi_equipo'].balance == bal + int(ref * 0.30)
    assert not e.get('despido_pendiente')
    obj = D.definir_objetivo(e); obj.update(tipo='copa', pos_max=4)
    bal = e['mi_equipo'].balance
    assert D.evaluar_temporada(e, 4)['resultado'] == 'cumplido'
    assert e['mi_equipo'].balance == bal + int(obj['presupuesto_ref'] * 0.15)
    # v3.1.0: fallado sin advertencia previa: segunda oportunidad (advertencia, multa, confianza 40)
    obj = D.definir_objetivo(e); obj.update(tipo='mitad', pos_max=2)
    bal = e['mi_equipo'].balance
    r = D.evaluar_temporada(e, 4)
    assert r['resultado'] == 'fallado' and not r['despido'] and D.confianza(e) == 40
    assert e['datos_carrera']['advertencia_dt'] is True
    assert e['mi_equipo'].balance == bal - int(obj['presupuesto_ref'] * 0.20)
    # fallar con la advertencia vigente: despido con 3 opciones de menor nivel
    obj = D.definir_objetivo(e); obj.update(tipo='mitad', pos_max=2)
    r = D.evaluar_temporada(e, 4)
    assert r['despido'] and e['despido_pendiente']
    opciones = D.opciones_de_club(e)
    assert len(opciones) == 3 and len({id(o) for o in opciones}) == 3
    assert all(o.ovr_promedio < e['mi_equipo'].ovr_promedio for o in opciones)
    print("  test_evaluar_temporada: OK")


def test_cambiar_de_club():
    e = estado_carrera()
    D.definir_objetivo(e)
    viejo = e['mi_equipo']
    nuevo = D.opciones_de_club(e)[0]
    D.cambiar_de_club(e, nuevo)
    assert e['mi_equipo'] is nuevo and nuevo in e['liga'].equipos and e['equipos'] is e['liga'].equipos
    assert e['alineacion_activa'] is nuevo.alineacion_activa and len(nuevo.alineacion_activa.titulares) == 11
    assert e['copa_user_en_copa'] is False and not e.get('despido_pendiente')
    assert D.confianza(e) == D.CONFIANZA_INICIAL and 'objetivo' not in e['datos_carrera']
    assert not e['datos_carrera'].get('advertencia_dt')
    print("  test_cambiar_de_club: OK")


def test_cierre_de_temporada_lleva_al_despido():
    from alpha_football.ui import resumen_temporada_screen as R
    from alpha_football.ui.league_screen import inicializar_calendario_liga
    e = estado_carrera()
    liga, mi = e['liga'], e['mi_equipo']
    inicializar_calendario_liga(liga)
    D.definir_objetivo(e)['pos_max'] = 1
    e['datos_carrera']['confianza'] = 10
    for eq in liga.equipos:
        eq.puntos = 0 if eq is mi else 30                  # el user termina último
    R.avanzar_nueva_temporada(e)
    assert e.get('despido_pendiente') and len(e['despido_pendiente']['opciones']) == 3
    assert R.siguiente_pantalla_tras_temporada(e) == 'veredicto_screen'    # v3.2.0: veredicto primero
    e.pop('veredicto_pendiente')
    assert R.siguiente_pantalla_tras_temporada(e) == 'despido_screen'
    assert e['historial'][-1]['objetivo_resultado'] == 'fallado'
    print("  test_cierre_de_temporada_lleva_al_despido: OK")


def test_pantallas_oficina():
    from alpha_football.ui import league_screen, objetivos_screen, despido_screen
    assert ('OBJETIVOS', 'Lo que exige la directiva y su confianza', 'objetivos_screen') in league_screen.TARJETAS['oficina']
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'main.py'), encoding='utf-8').read()
    assert "'objetivos_screen': 'alpha_football.ui.objetivos_screen'" in src and "'despido_screen': 'alpha_football.ui.despido_screen'" in src   # v3.6.0: MODULOS_PANTALLA
    e = estado_carrera()
    pygame.event.clear()
    assert objetivos_screen.render(screen, e) is None
    assert e['datos_carrera']['objetivo']['temporada'] == 1
    # despido: elegir la 2ª opción cambia de club
    e['datos_carrera']['confianza'] = 5
    D.definir_objetivo(e)['pos_max'] = 1
    D.evaluar_temporada(e, 6)
    opciones = e['despido_pendiente']['opciones']
    pygame.event.clear()
    assert despido_screen.render(screen, e) is None
    click(despido_screen._rects_opciones(len(opciones))[1].center)
    assert despido_screen.render(screen, e) == 'contrato_dt_screen'      # v3.2.0: firma antes de seguir
    assert e['mi_equipo'] is opciones[1]
    print("  test_pantallas_oficina: OK")


TESTS = [test_objetivo_por_ranking, test_definir_objetivo_una_vez_por_temporada, test_confianza,
         test_evaluar_temporada, test_cambiar_de_club, test_cierre_de_temporada_lleva_al_despido,
         test_pantallas_oficina]


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
