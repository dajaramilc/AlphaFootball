"""v3.2.0: Carrera del DT — contrato, patrimonio, renovación, veredicto, espaldarazo, objetivo de copa."""
import sys, os, random, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(13)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import directiva as D, save
from alpha_football import carrera_dt as CD, correo as C
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


def test_ofertas_contrato_variantes():
    e = estado_carrera()
    mi = e['mi_equipo']; mi.balance = 50_000_000
    of = CD.ofertas_contrato(e, mi)                     # calif inicial 50 → ×1.0
    assert [o['anios'] for o in of] == [1, 2, 3]
    assert of[1]['sueldo'] == 2_000_000                 # 4% de 50M
    assert of[0]['sueldo'] == 2_500_000 and of[2]['sueldo'] == 1_700_000
    ren = CD.ofertas_contrato(e, mi, renovacion=True)
    assert ren[1]['sueldo'] == 2_200_000


def test_ofertas_balance_negativo():
    e = estado_carrera(); mi = e['mi_equipo']; mi.balance = -5_000_000
    assert CD.ofertas_contrato(e, mi)[1]['sueldo'] == 100_000


def test_firmar_y_pagar():
    e = estado_carrera(); mi = e['mi_equipo']; mi.balance = 50_000_000
    c = CD.firmar(e, mi, {'anios': 2, 'sueldo': 1_400_000})
    assert c == {'club': mi.nombre, 'sueldo': 1_400_000, 'desde': 1, 'hasta': 2}
    n = e['liga'].num_jornadas
    assert CD.pagar_jornada(e) == 1_400_000 // n
    assert CD.patrimonio(e) == 1_400_000 // n


def test_indemnizacion():
    e = estado_carrera(); mi = e['mi_equipo']
    CD.firmar(e, mi, {'anios': 3, 'sueldo': 1_000_000})      # hasta T3
    assert CD.indemnizacion(e, 1) == 1_000_000             # faltan 2 → 50% × 2
    assert CD.indemnizacion(e, 3) == 0
    assert CD.cobrar_indemnizacion(e, 2) == 500_000 and CD.patrimonio(e) == 500_000


def test_renovacion_segun_calif():
    e = estado_carrera(); mi = e['mi_equipo']
    CD.firmar(e, mi, {'anios': 1, 'sueldo': 1_000_000})      # vence esta temporada
    e['liga'].jornada_actual = e['liga'].num_jornadas // 2 + 1
    e['datos_carrera']['calif_dt'] = 65
    CD.revisar_renovacion(e)
    assert e['datos_carrera']['renovacion_dt'] == {'temporada': 1, 'estado': 'ofrecida'}
    assert C.bandeja(e)[0]['accion']['pantalla'] == 'contrato_dt_screen'
    CD.revisar_renovacion(e)                                    # no repite
    assert sum(1 for m in C.bandeja(e) if 'renovación' in m['asunto'].lower()) == 1
    e2 = estado_carrera(); CD.firmar(e2, e2['mi_equipo'], {'anios': 1, 'sueldo': 1})
    e2['liga'].jornada_actual = e2['liga'].num_jornadas
    e2['datos_carrera']['calif_dt'] = 40
    CD.revisar_renovacion(e2)
    assert e2['datos_carrera']['renovacion_dt']['estado'] == 'negada'


def test_renovar_extiende_y_vencimiento():
    e = estado_carrera(); mi = e['mi_equipo']
    CD.firmar(e, mi, {'anios': 1, 'sueldo': 1_000_000})
    assert CD.contrato_vencido(e, 1)
    CD.firmar(e, mi, {'anios': 2, 'sueldo': 1_200_000}, renovacion=True)
    c = CD.contrato(e)
    assert (c['desde'], c['hasta'], c['sueldo']) == (1, 3, 1_200_000)
    assert e['datos_carrera']['renovacion_dt']['estado'] == 'aceptada'
    assert not CD.contrato_vencido(e, 1)
    CD.rechazar_renovacion(e)
    assert e['datos_carrera']['renovacion_dt']['estado'] == 'rechazada'


def test_asegurar_contrato_save_viejo():
    e = estado_carrera()
    CD.asegurar_contrato(e)
    c = CD.contrato(e)
    assert c['club'] == e['mi_equipo'].nombre and c['hasta'] - c['desde'] == 1
    e['datos_carrera']['contrato_dt']['club'] = 'Otro'          # club distinto → se rehace
    CD.asegurar_contrato(e)
    assert CD.contrato(e)['club'] == e['mi_equipo'].nombre


def _con_objetivo(pos_max=5, balance=40_000_000):
    # BetPlay: 8 equipos, 14 jornadas (la Premier de prueba tiene solo 6 y el 5º-6º desciende)
    e = estado_carrera('betplay'); e['mi_equipo'].balance = balance
    D.definir_objetivo(e)
    e['datos_carrera']['objetivo']['pos_max'] = pos_max
    CD.firmar(e, e['mi_equipo'], {'anios': 3, 'sueldo': 1_000_000})
    return e


def test_veredictos():
    e = _con_objetivo(5); assert D.evaluar_temporada(e, 2)['veredicto'] == 'felicitacion'
    e = _con_objetivo(5); assert D.evaluar_temporada(e, 5)['veredicto'] == 'neutro'
    e = _con_objetivo(5); assert D.evaluar_temporada(e, 6)['veredicto'] == 'regano'
    e = _con_objetivo(5); e['datos_carrera']['advertencia_dt'] = True
    ev = D.evaluar_temporada(e, 6)
    assert ev['veredicto'] == 'despido' and e['despido_pendiente']['titulo'] == "¡DESPEDIDO!"
    assert ev['indemnizacion'] == 1_000_000 and CD.patrimonio(e) == 1_000_000   # faltaban 2 temp.
    e = _con_objetivo(5); e['copa_mejor_fase_temp'] = 'Campeón'
    assert D.evaluar_temporada(e, 6)['veredicto'] == 'regano'      # fallar la liga pesa más


def test_correo_rendimiento_y_pendiente():
    e = _con_objetivo(5)
    ev = D.evaluar_temporada(e, 3)
    vp = e['veredicto_pendiente']
    assert vp['tipo'] == ev['veredicto'] and C.bandeja(e)[0]['id'] == vp['correo_id']
    assert C.bandeja(e)[0]['asunto'].startswith("Evaluación de la temporada")
    from alpha_football.ui.resumen_temporada_screen import siguiente_pantalla_tras_temporada
    assert siguiente_pantalla_tras_temporada(e) == 'veredicto_screen'


def test_fin_de_contrato():
    e = _con_objetivo(5)
    CD.firmar(e, e['mi_equipo'], {'anios': 1, 'sueldo': 1_000_000})
    ev = D.evaluar_temporada(e, 3)
    assert ev['veredicto'] == 'fin_contrato'
    assert e['despido_pendiente']['titulo'] == "FIN DE CONTRATO" and CD.patrimonio(e) == 0
    e['despido_pendiente'] = None
    assert D.restaurar_despido(e) and e['despido_pendiente']['titulo'] == "FIN DE CONTRATO"


def test_marcar_despido_indemniza():
    e = estado_carrera()                       # sin objetivo (quiebra a mitad de temporada)
    CD.firmar(e, e['mi_equipo'], {'anios': 2, 'sueldo': 800_000})
    D.marcar_despido(e, "Quiebra")
    assert CD.patrimonio(e) == 400_000


def test_espaldarazo():
    e = _con_objetivo(6, balance=40_000_000)
    ops = D.opciones_espaldarazo(e)
    assert [(o['pct'], o['puestos'], o['monto']) for o in ops] == [
        (0.15, 1, 6_000_000), (0.30, 2, 12_000_000), (0.50, 3, 20_000_000)]
    ok, _ = D.pedir_espaldarazo(e, 1)
    obj = e['datos_carrera']['objetivo']
    assert ok and obj['pos_max'] == 4 and obj['espaldarazo'] == {'pct': 0.30, 'puestos': 2}
    assert e['mi_equipo'].balance == 52_000_000
    assert "4" in obj['texto']
    ok2, msg = D.pedir_espaldarazo(e, 0)
    assert not ok2 and "temporada" in msg.lower()
    assert D.evaluar_temporada(e, 5)['resultado'] == 'fallado'           # meta más alta
    assert e['datos_carrera']['advertencia_dt']                           # conserva 2ª oportunidad


def test_espaldarazo_negado_y_limites():
    e = _con_objetivo(6); e['datos_carrera']['calif_dt'] = 39
    ok, msg = D.pedir_espaldarazo(e, 0)
    assert not ok and "calificación" in msg.lower()
    e = _con_objetivo(6); e['liga'].jornada_actual = e['liga'].num_jornadas // 2 + 1
    assert not D.pedir_espaldarazo(e, 0)[0]


def test_espaldarazo_no_baja_de_1():
    e = _con_objetivo(2)
    disp = [o['disponible'] for o in D.opciones_espaldarazo(e)]
    assert disp == [True, False, False]
    assert not D.pedir_espaldarazo(e, 2)[0]


def test_objetivo_copa():
    # v3.8.0: la copa sale del motor de competiciones (Libertadores de 32 clubes).
    from alpha_football import competiciones as CP
    e = _con_objetivo(5)
    e['mi_equipo'] = min(e['liga'].equipos, key=lambda x: x.ovr_promedio)     # no clasifica
    CP.iniciar_temporada(e, random.Random(5))
    assert D.definir_objetivo_copa(e) is None
    e = _con_objetivo(5)
    e['mi_equipo'] = max(e['liga'].equipos, key=lambda x: x.ovr_promedio)     # clasifica
    CP.iniciar_temporada(e, random.Random(5))
    oc = D.definir_objetivo_copa(e)
    assert oc['fase'] in D.FASES_COPA[2:] and oc['n'] == 32
    e['copa_mejor_fase_temp'] = 'Campeón'
    calif_antes = D.calif_dt(e)
    ev = D.evaluar_objetivo_copa(e, 1)
    assert ev['resultado'] in ('superado', 'cumplido')
    assert D.calif_dt(e) - calif_antes in (6, 3)


def test_meta_copa_por_ranking():
    # v3.8.0: r ≤ n/8 Finalista, r ≤ n/4 Semifinal, r ≤ n/2 Cuartos, si no Octavos
    assert D.meta_copa(1, 8, ventaja=9) == 'Campeón'
    assert D.meta_copa(1, 8, ventaja=2) == 'Finalista'
    assert D.meta_copa(2, 8) == 'Semifinal'
    assert D.meta_copa(4, 8) == 'Cuartos'
    assert D.meta_copa(6, 8) == 'Octavos'
    assert D.meta_copa(1, 1) == 'Octavos'


def key(k):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=''))


def test_contrato_screen_alta():
    from alpha_football.ui import contrato_dt_screen as S
    e = estado_carrera(); e['mi_equipo'].balance = 50_000_000
    e['contrato_modo'] = 'alta'
    pygame.event.clear(); assert S.render(screen, e) is None
    key(pygame.K_RIGHT); S.render(screen, e)
    key(pygame.K_RETURN); assert S.render(screen, e) == 'league_screen'
    assert CD.contrato(e)['hasta'] == 3 and 'contrato_modo' not in e
    e['contrato_modo'] = 'alta'; e['promo_releg_data'] = {'x': 1}
    key(pygame.K_RETURN); assert S.render(screen, e) == 'promo_releg_screen'


def test_contrato_screen_renovacion_y_ver():
    from alpha_football.ui import contrato_dt_screen as S
    e = estado_carrera(); CD.firmar(e, e['mi_equipo'], {'anios': 1, 'sueldo': 1_000_000})
    e['datos_carrera']['renovacion_dt'] = {'temporada': 1, 'estado': 'ofrecida'}
    assert S.modo(e) == 'renovacion'
    click(S.R_RECHAZAR.center); assert S.render(screen, e) == 'league_screen'
    assert e['datos_carrera']['renovacion_dt']['estado'] == 'rechazada'
    assert S.modo(e) == 'ver'
    pygame.event.clear(); assert S.render(screen, e) is None
    key(pygame.K_ESCAPE); assert S.render(screen, e) == 'league_screen'


def test_veredicto_screen_flujo():
    from alpha_football.ui import veredicto_screen as V
    e = _con_objetivo(5); e['datos_carrera']['advertencia_dt'] = True
    D.evaluar_temporada(e, 7)
    pygame.event.clear(); assert V.render(screen, e) is None        # paso 1: el correo
    key(pygame.K_RETURN); assert V.render(screen, e) is None        # paso 2: veredicto
    assert C.bandeja(e)[0]['leido']
    key(pygame.K_RETURN); assert V.render(screen, e) == 'despido_screen'
    assert 'veredicto_pendiente' not in e


def test_despido_lleva_a_contrato():
    from alpha_football.ui import despido_screen as DS
    e = _con_objetivo(5); D.marcar_despido(e, "x")
    r = DS._rects_opciones(len(e['despido_pendiente']['opciones']))[0]
    click(r.center)
    assert DS.render(screen, e) == 'contrato_dt_screen' and e['contrato_modo'] == 'alta'


def test_objetivos_screen_espaldarazo_y_copa():
    from alpha_football.ui import objetivos_screen as O
    e = _con_objetivo(6); e['copa_user_en_copa'] = False
    pygame.event.clear(); assert O.render(screen, e) is None
    click(O.R_ESPALDARAZO.center); O.render(screen, e)
    assert e.get('espaldarazo_abierto')
    key(pygame.K_1); O.render(screen, e)
    assert e['datos_carrera']['objetivo']['pos_max'] == 5 and not e.get('espaldarazo_abierto')


def test_fin_contrato_siempre_hay_oferta():
    """Aunque dirijas al club más flojo de las 10 ligas, al vencer el contrato alguien te llama."""
    e = _con_objetivo(5)
    todos = [eq for c in ('primera_division', 'segunda_division')
             for lg in (e.get(c) or {}).values() for eq in lg.equipos]
    peor = min(todos, key=lambda x: x.ovr_promedio)
    D.cambiar_de_club(e, peor)
    D.definir_objetivo(e)
    CD.firmar(e, peor, {'anios': 1, 'sueldo': 100_000})
    for cal in (0, 50, 90):
        e['datos_carrera']['calif_dt'] = cal
        assert D.opciones_de_club(e), f"sin ofertas con calif {cal}"
    D.evaluar_temporada(e, 1)
    assert e['despido_pendiente']['titulo'] == "FIN DE CONTRATO" and e['despido_pendiente']['opciones']


TESTS = [test_fin_contrato_siempre_hay_oferta, test_ofertas_contrato_variantes, test_ofertas_balance_negativo, test_firmar_y_pagar,
         test_indemnizacion, test_renovacion_segun_calif, test_renovar_extiende_y_vencimiento,
         test_asegurar_contrato_save_viejo,
         test_veredictos, test_correo_rendimiento_y_pendiente, test_fin_de_contrato,
         test_marcar_despido_indemniza, test_espaldarazo, test_espaldarazo_negado_y_limites,
         test_espaldarazo_no_baja_de_1, test_objetivo_copa, test_meta_copa_por_ranking,
         test_contrato_screen_alta, test_contrato_screen_renovacion_y_ver, test_veredicto_screen_flujo,
         test_despido_lleva_a_contrato, test_objetivos_screen_espaldarazo_y_copa]


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
