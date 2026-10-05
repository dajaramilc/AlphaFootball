"""Patrocinios v4.9.0: contratos, objetivos, ofertas, acciones, ciclo de temporada, pantalla."""
import sys, os, random, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(49)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save, patrocinios as P, finanzas as F, correo as C
from alpha_football.models import Partido
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402


def _base(e):
    liga = e['liga']
    return F.base_ingresos(e['mi_equipo'], liga.tipo, liga.division)


def _obj(tipo, meta):
    return {'tipo': tipo, 'meta': meta, 'texto': f"{tipo} {meta}"}


def test_fracciones_y_ingresos_esperados():
    e = estado_carrera(); liga = e['liga']; base = _base(e)
    assert F.PATROCINIO_FRAC == 0.55 and F.TAQUILLA_FRAC == 0.35
    esperados = F.ingresos_esperados(e['mi_equipo'], liga.tipo, liga.division)
    assert esperados == int(base * 0.55) + int(base * 0.35)
    assert abs(esperados - int(base * 0.90)) <= 1                      # el total no cambió
    print("  test_fracciones_y_ingresos_esperados: OK")


def test_contratos_iniciales():
    e = estado_carrera(); p = P.datos(e)
    cs = p['contratos']
    assert set(cs) == {'camiseta', 'manga', 'estadio'} and all(cs.values())
    assert p['reputacion'] == 50      # v4.9.1: el club 0 de premier tiene patrocinios reales (pueden repetir rubro)
    for espacio, c in cs.items():
        f_fijo, f_bono, _d = P.PERFILES[c['perfil']]
        ref = P.valor_referencia(e, espacio)
        assert 1 <= c['anios'] <= 3 and c['espacio'] == espacio
        assert c['fijo'] == int(ref * f_fijo) and c['bono'] == int(ref * f_bono)
        assert c['objetivo']['texto'] and c['cumplido_ultima'] is None
    total_ref = sum(P.valor_referencia(e, esp) for esp, _w in P.ESPACIOS)
    assert abs(total_ref - int(_base(e) * F.PATROCINIO_FRAC)) <= 3     # referencia = patrocinio de fórmula
    assert P.datos(e) is p                                             # estable entre llamadas
    e['datos_carrera'] = json.loads(json.dumps(e['datos_carrera']))    # ida y vuelta como el guardado
    assert P.datos(e)['contratos'] == cs
    for basura in ("x", {'club': e['mi_equipo'].nombre}, {'club': e['mi_equipo'].nombre, 'contratos': {'camiseta': 3}}):
        e['datos_carrera']['patrocinios'] = basura                     # corrupto → se regenera
        assert all(P.datos(e)['contratos'].values())
    e['mi_equipo'] = e['liga'].equipos[1]                              # cambio de club
    p2 = P.datos(e)
    assert p2['club'] == e['mi_equipo'].nombre and p2['reputacion'] == 50 and all(p2['contratos'].values())
    print("  test_contratos_iniciales: OK")


def test_cobro_jornada():
    e = estado_carrera(); mi = e['mi_equipo']; n = e['liga'].num_jornadas
    cs = P.datos(e)['contratos']
    assert P.cobro_jornada(e) == sum(c['fijo'] // n for c in cs.values())
    assert P.ingreso_anual(e) == sum(c['fijo'] for c in cs.values())
    bal = mi.balance
    mov = F.procesar_jornada(e, es_local=False, gf=0, gc=0)
    assert mov['patrocinio'] == P.cobro_jornada(e) and mi.balance == bal + mov['patrocinio'] - mov['salarios']
    assert F.libro(e)['patrocinio'] == mov['patrocinio']
    cs['manga'] = cs['estadio'] = None
    assert P.cobro_jornada(e) == cs['camiseta']['fijo'] // n
    cs['camiseta'] = None                                              # sin patrocinadores no se cobra
    assert P.cobro_jornada(e) == 0 and F.procesar_jornada(e, False, 0, 0)['patrocinio'] == 0
    print("  test_cobro_jornada: OK")


def test_objetivos_cumple_y_progreso():
    e = estado_carrera(); mi = e['mi_equipo']; liga = e['liga']
    c = lambda tipo, meta: {'objetivo': _obj(tipo, meta)}
    assert P.cumple(e, c('posicion', 4), posicion=4) is True and P.cumple(e, c('posicion', 4), posicion=5) is False
    mi.gf = 30
    assert P.cumple(e, c('goles', 30)) is True and P.cumple(e, c('goles', 31)) is False
    assert abs(P.progreso(e, c('goles', 60)) - 0.5) < 1e-9
    rival = liga.equipos[1] if liga.equipos[0] is mi else liga.equipos[0]
    liga.calendario = [Partido(local_id=mi.id, visitante_id=rival.id, jornada=1, goles_local=2, goles_visitante=0, jugado=True),
                       Partido(local_id=mi.id, visitante_id=rival.id, jornada=3, goles_local=1, goles_visitante=1, jugado=True),
                       Partido(local_id=rival.id, visitante_id=mi.id, jornada=2, goles_local=0, goles_visitante=3, jugado=True)]
    assert P.cumple(e, c('local', 1)) is True and P.cumple(e, c('local', 2)) is False   # solo cuenta ganar de local
    for j in mi.jugadores:
        j.edad, j.partidos_jugados = 25, 9
    mi.jugadores[0].edad, mi.jugadores[1].edad = 19, 20
    assert P.cumple(e, c('u21', 18)) is True and P.cumple(e, c('u21', 19)) is False
    e['copa_mejor_fase_temp'] = None                                   # temporada sin copa: no aplica
    assert P.cumple(e, c('copa', 'Octavos')) is None and P.progreso(e, c('copa', 'Octavos')) == 0.0
    e['copa_mejor_fase_temp'] = 'Cuartos'
    assert P.cumple(e, c('copa', 'Octavos')) is True and P.cumple(e, c('copa', 'Semifinal')) is False
    for tipo, meta in (('posicion', 3), ('goles', 40), ('local', 6), ('u21', 20), ('copa', 'Semifinal')):
        assert 0.0 <= P.progreso(e, c(tipo, meta)) <= 1.0
    print("  test_objetivos_cumple_y_progreso: OK")


def test_crear_objetivo_dificultad():
    e = estado_carrera(); rng = random.Random(2)
    for tipo in ('goles', 'local', 'u21'):
        metas = [P.crear_objetivo(e, d, rng, tipo=tipo)['meta'] for d in (0, 1, 2)]
        assert metas == sorted(metas) and metas[0] < metas[2], (tipo, metas)
    pos = [P.crear_objetivo(e, d, rng, tipo='posicion')['meta'] for d in (0, 1, 2)]
    assert pos[0] >= pos[1] >= pos[2] >= 1                              # más difícil = puesto más alto
    assert all(P.crear_objetivo(e, 1, rng)['tipo'] != 'copa' for _ in range(40))   # sin copa no se ofrece
    assert P.mult_reputacion(0) == 0.80 and P.mult_reputacion(50) == 1.00 and abs(P.mult_reputacion(100) - 1.30) < 1e-9
    print("  test_crear_objetivo_dificultad: OK")


class _Azar(random.Random):
    """random() fijo para forzar el éxito o el fracaso de una negociación."""
    def __init__(self, valor):
        super().__init__(1); self._valor = valor
    def random(self):
        return self._valor


def _vaciar(e, espacio):
    p = P.datos(e); viejo = p['contratos'][espacio]; p['contratos'][espacio] = None
    return p, viejo


def test_generar_ofertas_exclusividad_y_valor():
    e = estado_carrera(); e['liga'].jornada_actual = 5
    p, _v = _vaciar(e, 'manga')
    ofertas = P.generar_ofertas(e, 'manga', random.Random(3))
    ocupados = {c['rubro'] for esp, c in p['contratos'].items() if c}
    assert len(ofertas) == 2 and len({o['rubro'] for o in ofertas}) == 2
    assert not ocupados & {o['rubro'] for o in ofertas}                 # exclusividad de rubro
    assert len({o['id'] for o in ofertas}) == 2 and all(o['espacio'] == 'manga' and not o['renovacion'] for o in ofertas)
    assert P.ofertas_de(e, 'manga') == ofertas and P.ofertas_de(e, 'camiseta') == []
    p['reputacion'] = P.REP_SIN_INTERES
    bajo = P.generar_ofertas(e, 'manga', random.Random(3))              # misma semilla, peor reputación
    p['reputacion'] = 100
    alto = P.generar_ofertas(e, 'manga', random.Random(3))
    assert [o['marca'] for o in bajo] == [o['marca'] for o in alto]
    assert all(a['fijo'] > b['fijo'] * 1.4 for a, b in zip(alto, bajo))   # ×1.30 contra ×0.86
    assert len(P.ofertas_de(e, 'manga')) == 2                           # regenerar reemplaza, no acumula
    print("  test_generar_ofertas_exclusividad_y_valor: OK")


def test_renovacion_solo_si_cumplio():
    # v4.9.1: club 2 (Pool de Higado): el club 0 repite rubro (Etihat en camiseta y estadio) y eso bloquea renovar
    e = estado_carrera('premier', 2); e['liga'].jornada_actual = 5
    p, viejo = _vaciar(e, 'camiseta')
    viejo['cumplido_ultima'] = True
    ofertas = P.generar_ofertas(e, 'camiseta', random.Random(4), anterior=viejo)
    ren = [o for o in ofertas if o['renovacion']]
    assert len(ofertas) == 3 and len(ren) == 1 and ren[0]['marca'] == viejo['marca']
    assert viejo['fijo'] * 1.10 - 1 <= ren[0]['fijo'] <= viejo['fijo'] * 1.20 + 1
    for estado_obj in (False, None):                                    # falló o no aplicó: no renueva
        viejo['cumplido_ultima'] = estado_obj
        ofertas = P.generar_ofertas(e, 'camiseta', random.Random(4), anterior=viejo)
        assert len(ofertas) == 2 and viejo['marca'] not in {o['marca'] for o in ofertas}
    print("  test_renovacion_solo_si_cumplio: OK")


def test_sin_interesados():
    e = estado_carrera(); e['liga'].jornada_actual = 5
    p, _v = _vaciar(e, 'estadio')
    prob = P.PROB_NO_OFERTA
    try:
        P.PROB_NO_OFERTA = 1.0
        p['reputacion'] = P.REP_SIN_INTERES - 1
        assert P.generar_ofertas(e, 'estadio', random.Random(5)) == []   # nadie se presenta
        p['reputacion'] = P.REP_SIN_INTERES
        assert len(P.generar_ofertas(e, 'estadio', random.Random(5))) == 2
    finally:
        P.PROB_NO_OFERTA = prob
    print("  test_sin_interesados: OK")


def test_firmar_y_prima():
    e = estado_carrera(); mi = e['mi_equipo']; e['liga'].jornada_actual = 5
    p, _v = _vaciar(e, 'manga')
    o = dict(P.generar_ofertas(e, 'manga', random.Random(6))[0])
    ok, msg = P.firmar(e, o['id'])
    c = p['contratos']['manga']
    assert ok and o['marca'] in msg and c['marca'] == o['marca'] and c['fijo'] == o['fijo']
    assert not {'id', 'renovacion', 'negociada'} & set(c) and P.ofertas_de(e, 'manga') == []
    assert P.firmar(e, o['id']) == (False, "Esa oferta ya no está disponible.")
    p, _v = _vaciar(e, 'estadio')
    o = dict(P.generar_ofertas(e, 'estadio', random.Random(7))[0])
    bal, lib = mi.balance, F.libro(e)['patrocinio']
    ok, msg = P.firmar(e, o['id'], con_prima=True)
    prima = int(o['fijo'] * P.PRIMA_FRAC)
    assert ok and mi.balance == bal + prima and F.libro(e)['patrocinio'] == lib + prima
    assert p['contratos']['estadio']['fijo'] == int(o['fijo'] * P.PRIMA_FIJO)
    print("  test_firmar_y_prima: OK")


def test_firmar_exclusividad():
    e = estado_carrera(); e['liga'].jornada_actual = 5
    p, _v = _vaciar(e, 'manga')
    o = P.generar_ofertas(e, 'manga', random.Random(8))[0]
    o['rubro'] = p['contratos']['camiseta']['rubro']                     # como si otra firma hubiera ocupado el rubro
    ok, msg = P.firmar(e, o['id'])
    assert not ok and "rubro" in msg and p['contratos']['manga'] is None
    p['contratos']['manga'] = dict(p['contratos']['estadio'], espacio='manga', rubro='otro')
    ok, msg = P.firmar(e, o['id'])                                       # espacio ya ocupado
    assert not ok
    print("  test_firmar_exclusividad: OK")


def test_rechazar_todo_deja_vacio():
    e = estado_carrera(); e['liga'].jornada_actual = 5; n = e['liga'].num_jornadas
    p, _v = _vaciar(e, 'camiseta')
    antes = P.cobro_jornada(e)
    for o in list(P.generar_ofertas(e, 'camiseta', random.Random(9))):
        assert P.rechazar(e, o['id']) is True
    assert P.rechazar(e, 999) is False
    assert P.ofertas_de(e, 'camiseta') == [] and p['contratos']['camiseta'] is None
    assert P.cobro_jornada(e) == antes == sum(c['fijo'] // n for c in p['contratos'].values() if c)
    print("  test_rechazar_todo_deja_vacio: OK")


def test_negociar():
    e = estado_carrera(); e['liga'].jornada_actual = 5
    p, _v = _vaciar(e, 'manga')
    assert abs(P.prob_negociar(e, 1) - 0.60) < 1e-9 and abs(P.prob_negociar(e, 2) - 0.30) < 1e-9
    p['reputacion'] = 100
    assert abs(P.prob_negociar(e, 1) - 0.75) < 1e-9
    p['reputacion'] = 0
    assert abs(P.prob_negociar(e, 1) - 0.45) < 1e-9 and abs(P.prob_negociar(e, 2) - 0.15) < 1e-9
    p['reputacion'] = 50
    a, b = P.generar_ofertas(e, 'manga', random.Random(10))
    fijo = a['fijo']
    ok, msg = P.negociar(e, a['id'], 1, _Azar(0.0))
    assert ok and a['fijo'] == int(fijo * 1.10) and a['negociada']
    assert P.negociar(e, a['id'], 2, _Azar(0.0)) == (False, "Ya negociaste esta oferta.") and a['fijo'] == int(fijo * 1.10)
    ok, msg = P.negociar(e, b['id'], 2, _Azar(0.99))
    assert not ok and b['marca'] in msg and [o['id'] for o in P.ofertas_de(e, 'manga')] == [a['id']]   # se retira
    print("  test_negociar: OK")


def test_rescindir():
    e = estado_carrera(); mi = e['mi_equipo']; liga = e['liga']
    liga.calendario = []; liga.jornada_actual = 5                        # mercado cerrado, 0 partidos jugados
    p = P.datos(e); c = p['contratos']['camiseta']; c['anios'] = 2
    multa = int((c['fijo'] + c['fijo'] * 1) * P.MULTA_FRAC)
    assert P.multa_rescision(e, 'camiseta') == multa
    mi.balance = multa - 1
    ok, msg = P.rescindir(e, 'camiseta')
    assert not ok and "Saldo insuficiente" in msg and p['contratos']['camiseta'] is c
    mi.balance = multa + 100
    ok, msg = P.rescindir(e, 'camiseta')
    assert ok and mi.balance == 100 and p['contratos']['camiseta'] is None and p['reputacion'] == 50 + P.REP_RESCISION
    assert P.ofertas_de(e, 'camiseta') == []                             # mercado cerrado: sin ofertas aún
    assert P.rescindir(e, 'camiseta')[0] is False
    liga.jornada_actual = 1                                              # ventana abierta: ofertas de inmediato
    marca = p['contratos']['manga']['marca']; mi.balance = 10 ** 12
    assert P.rescindir(e, 'manga', random.Random(11))[0]
    ofertas = P.ofertas_de(e, 'manga')
    assert ofertas and marca not in {o['marca'] for o in ofertas}        # la marca despechada no vuelve
    print("  test_rescindir: OK")


def _correos(e):
    return [m for m in C.bandeja(e) if m['remitente'] == 'patrocinador']


def test_evaluar_temporada_bonos_y_reputacion():
    e = estado_carrera(); mi = e['mi_equipo']; p = P.datos(e); cs = p['contratos']
    mi.gf = 10; e['copa_mejor_fase_temp'] = None
    cs['camiseta']['objetivo'] = _obj('goles', 5)                        # cumple
    cs['manga']['objetivo'] = _obj('goles', 999)                         # falla
    cs['estadio']['objetivo'] = _obj('copa', 'Octavos')                  # no aplica: no jugó la copa
    bal = mi.balance; bono = cs['camiseta']['bono']
    res = P.evaluar_temporada(e, 5, 1)
    assert res['bonos'] == bono and mi.balance == bal + bono
    assert p['reputacion'] == 50 + P.REP_CUMPLE + P.REP_FALLA
    assert (cs['camiseta']['cumplido_ultima'], cs['manga']['cumplido_ultima'], cs['estadio']['cumplido_ultima']) == (True, False, None)
    assert P.evaluar_temporada(e, 5, 1) is None and mi.balance == bal + bono     # no paga dos veces
    rep = p['reputacion']
    e['liga'].division = 1
    P.evaluar_temporada(e, 1, 2)                                         # campeón de 1ª: +8 además de los objetivos
    assert p['reputacion'] == min(100, rep + P.REP_CUMPLE + P.REP_FALLA + P.REP_TITULO)
    print("  test_evaluar_temporada_bonos_y_reputacion: OK")


def test_cambio_division():
    e = estado_carrera(); p = P.datos(e)
    antes = {esp: (c['fijo'], c['bono']) for esp, c in p['contratos'].items()}
    P.cambio_division(e, False, False)
    assert {esp: (c['fijo'], c['bono']) for esp, c in p['contratos'].items()} == antes and p['reputacion'] == 50
    P.cambio_division(e, False, True)
    assert all(c['fijo'] == int(antes[esp][0] * 0.60) and c['bono'] == int(antes[esp][1] * 0.60)
               for esp, c in p['contratos'].items())
    assert p['reputacion'] == 50 + P.REP_DESCENSO
    antes = {esp: c['fijo'] for esp, c in p['contratos'].items()}
    P.cambio_division(e, True, False)
    assert all(c['fijo'] == int(antes[esp] * 1.30) for esp, c in p['contratos'].items())
    assert p['reputacion'] == 50 + P.REP_DESCENSO + P.REP_ASCENSO
    print("  test_cambio_division: OK")


def test_cierre_contratos_vencen_y_ofertas():
    e = estado_carrera(); mi = e['mi_equipo']; p = P.datos(e); cs = p['contratos']
    e['liga'].jornada_actual = 1; mi.balance = abs(mi.balance) + 1
    cs['camiseta'].update(anios=1, cumplido_ultima=True)
    cs['manga'].update(anios=2, cumplido_ultima=True)
    cs['estadio'].update(anios=1, cumplido_ultima=False)
    marca_cam, marca_est = cs['camiseta']['marca'], cs['estadio']['marca']
    res = P.cierre_contratos(e, random.Random(12))
    assert set(res['vencidos']) == {'camiseta', 'estadio'}
    assert cs['camiseta'] is None and cs['estadio'] is None and cs['manga']['anios'] == 1
    cam, est = P.ofertas_de(e, 'camiseta'), P.ofertas_de(e, 'estadio')
    assert [o['marca'] for o in cam if o['renovacion']] == [marca_cam] and len(cam) == 3
    assert len(est) == 2 and marca_est not in {o['marca'] for o in est} and not any(o['renovacion'] for o in est)
    assert cs['manga']['rubro'] not in {o['rubro'] for o in cam + est}   # exclusividad con el que sigue
    correos = _correos(e)
    assert len(correos) == 1 and correos[0]['accion']['pantalla'] == 'patrocinios_screen'
    assert "Departamento comercial" in C.formatear(e, correos[0])
    rep = p['reputacion']; mi.balance = -1                               # cierre en quiebra
    P.cierre_contratos(e, random.Random(13))
    assert p['reputacion'] == rep + P.REP_QUIEBRA
    print("  test_cierre_contratos_vencen_y_ofertas: OK")


def test_revisar_jornada_ventanas():
    e = estado_carrera(); liga = e['liga']; p = P.datos(e)
    liga.jornada_actual = 1
    for c in p['contratos'].values():
        c['anios'] = 3                                                   # que solo venza la manga
    p['contratos']['manga'].update(anios=1, cumplido_ultima=False)
    P.cierre_contratos(e, random.Random(14))
    assert P.ofertas_de(e, 'manga')
    P.revisar_jornada(e)                                                 # ventana de inicio abierta: siguen
    assert P.ofertas_de(e, 'manga')
    n_correos = len(_correos(e))
    liga.jornada_actual = 5                                              # cerró la ventana: se retiran y avisa
    P.revisar_jornada(e)
    assert p['ofertas'] == [] and p['contratos']['manga'] is None and len(_correos(e)) == n_correos + 1
    P.revisar_jornada(e)
    assert len(_correos(e)) == n_correos + 1                             # no repite el aviso
    liga.jornada_actual = liga.num_jornadas // 2                         # invierno: ofertas nuevas, 15% peores
    P.revisar_jornada(e, random.Random(15))
    inv = P.ofertas_de(e, 'manga')
    assert inv and P.ofertas_de(e, 'camiseta') == []
    ref = P.valor_referencia(e, 'manga')
    assert all(o['fijo'] <= ref * P.PERFILES[o['perfil']][0] * P.FACTOR_INVIERNO * 1.05 + 1 for o in inv)
    ids = [o['id'] for o in inv]
    liga.jornada_actual += 1
    P.revisar_jornada(e, random.Random(16))
    assert [o['id'] for o in P.ofertas_de(e, 'manga')] == ids            # no regenera en la misma ventana
    print("  test_revisar_jornada_ventanas: OK")


def test_enganches_del_ciclo():
    import inspect
    from alpha_football.ui import resumen_temporada_screen as RT, match_screen as MS
    assert 'cierre_contratos' in inspect.getsource(F.cierre_temporada)
    fuente = inspect.getsource(RT)
    assert 'patrocinios' in fuente and 'evaluar_temporada(estado, posicion, temp_anterior)' in fuente
    assert 'cambio_division(estado, user_asc, user_des)' in fuente
    assert 'patrocinios' in inspect.getsource(MS.finalizar_jornada_liga)
    assert C.REMITENTES['patrocinador'] == "Patrocinador"
    print("  test_enganches_del_ciclo: OK")


def click(pos):
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))


def key(k):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, unicode='', mod=0))


def test_pantalla_patrocinios():
    from alpha_football.ui import patrocinios_screen as PS, league_screen
    assert ("PATROCINIOS", "Marcas, objetivos y ofertas", 'patrocinios_screen') in league_screen.TARJETAS['finanzas']
    e = estado_carrera(); mi = e['mi_equipo']; liga = e['liga']; liga.calendario = []; liga.jornada_actual = 5
    p = P.datos(e); mi.balance = 10 ** 12
    pygame.event.clear()
    assert PS.render(screen, e) is None
    click(PS._rect_espacio(1).center); PS.render(screen, e)
    assert e['patro_esp'] == 1
    # rescindir pide confirmación: primer clic marca, ESC cancela, dos clics rescinden
    click(PS._rect_rescindir(1).center); PS.render(screen, e)
    assert e['patro_confirma'] == 'manga' and p['contratos']['manga'] is not None
    key(pygame.K_ESCAPE)
    assert PS.render(screen, e) is None and e['patro_confirma'] is None
    click(PS._rect_rescindir(1).center); PS.render(screen, e)
    click(PS._rect_rescindir(1).center); PS.render(screen, e)
    assert p['contratos']['manga'] is None and "rescindido" in e['patro_msg']
    assert PS.render(screen, e) is None                                  # espacio vacío sin ofertas
    a, b = P.generar_ofertas(e, 'manga', random.Random(17))
    PS.render(screen, e)
    click(PS._rects_oferta(1)['rechazar'].center); PS.render(screen, e)
    assert [o['id'] for o in P.ofertas_de(e, 'manga')] == [a['id']]
    prob = P.prob_negociar
    try:
        P.prob_negociar = lambda _e, _n: 2.0                             # negociación que siempre sale bien
        fijo = a['fijo']
        click(PS._rects_oferta(0)['n1'].center); PS.render(screen, e)
        assert a['fijo'] == int(fijo * 1.10) and a['negociada']
    finally:
        P.prob_negociar = prob
    click(PS._rects_oferta(0)['firmar'].center); PS.render(screen, e)
    assert p['contratos']['manga']['marca'] == a['marca'] and P.ofertas_de(e, 'manga') == []
    e['patro_esp'], e['patro_of'] = 7, 9                                 # índices fuera de rango: se acotan
    assert PS.render(screen, e) is None and e['patro_esp'] == 2 and e['patro_of'] == 0
    p['contratos']['estadio'] = None
    o = P.generar_ofertas(e, 'estadio', random.Random(18))[0]
    bal = mi.balance
    PS.render(screen, e); key(pygame.K_p); PS.render(screen, e)          # P: firmar con prima la oferta elegida
    assert p['contratos']['estadio']['marca'] == o['marca'] and mi.balance == bal + int(o['fijo'] * P.PRIMA_FRAC)
    key(pygame.K_ESCAPE)
    assert PS.render(screen, e) == 'league_screen'
    print("  test_pantalla_patrocinios: OK")


def test_pantalla_registrada_con_ayuda_y_atajos():
    import main
    from alpha_football.ui import ayuda, atajos
    assert 'patrocinios_screen' in main.nombres_pantallas()
    e = estado_carrera()
    its = ayuda.AYUDA['patrocinios_screen'](e)
    assert len(its) >= 3 and all(len(x) <= 110 for _r, _t, x in its)
    assert 'patrocinios_screen' in ayuda._TEXTO_TARJETA
    assert "Firmar" in atajos.texto('patrocinios_screen', e)
    print("  test_pantalla_registrada_con_ayuda_y_atajos: OK")



# --- v4.9.1: catálogo de 150 marcas por región y patrocinios reales ---------------------------
from alpha_football.data import patrocinadores as PAT   # noqa: E402
from alpha_football.mercado_ia import ligas_de_la_partida   # noqa: E402
SUDAMERICA = ('brasil', 'argentina', 'betplay', 'uruguay', 'ecuador')


def _club(tipo, nombre):
    from alpha_football.ui.menu import load_league_teams
    liga = load_league_teams(tipo)
    return estado_carrera(tipo, [q.nombre for q in liga.equipos].index(nombre))


def _regiones_ok(estado, nombres):
    reg = P.region_de(estado)
    permitidas = {'global', reg}
    por_nombre = {m[0]: m for m in P.MARCAS}
    return all(por_nombre[n][3] in permitidas for n in nombres)


def test_catalogo_150_marcas():
    ms = P.MARCAS
    assert len(ms) == 150 and ms is PAT.MARCAS
    assert len({m[0] for m in ms}) == 150
    assert all(len(m) == 4 and m[2] in P.PERFILES and m[3] in ('global', 'europa', 'sudamerica') for m in ms)
    assert {m[3] for m in ms} == {'global', 'europa', 'sudamerica'}
    print("  test_catalogo_150_marcas: OK")


def test_reales_existen_y_son_compatibles():
    e = estado_carrera()
    por_nombre = {m[0]: m for m in P.MARCAS}
    primeras = {}
    for liga, tipo, division in ligas_de_la_partida(e):
        if division == 1:
            for q in liga.equipos:
                primeras[q.nombre] = tipo
    assert len(primeras) == 96
    assert len(PAT.PATROCINIOS_REALES) >= 60
    for club, d in PAT.PATROCINIOS_REALES.items():
        # v4.9.1: según la base (por defecto o editada) 3 clubes de LaLiga tienen otro nombre
        alias = club in PAT.ALIAS_BD_EDITADA or club in PAT.ALIAS_BD_EDITADA.values()
        assert club in primeras or alias, f"{club} no es un club de 1ª"
        assert set(d) == {'camiseta', 'manga', 'estadio'}
        permitidas = {'global', 'sudamerica' if primeras.get(club, 'laliga') in SUDAMERICA else 'europa'}
        for esp, marca in d.items():
            assert marca is None or marca in por_nombre, f"{club}/{esp}: {marca} no está en MARCAS"
            assert marca is None or por_nombre[marca][3] in permitidas, f"{club}/{esp}: {marca} de otra región"
    print("  test_reales_existen_y_son_compatibles: OK")


def test_region_nunca_cruza():
    e_eu = estado_carrera()
    liga2 = e_eu['segunda_division']['premier']
    e_eu['liga'], e_eu['mi_equipo'] = liga2, liga2.equipos[0]
    e_sa = _club('betplay', 'Matecaña Averiada')
    assert P.region_de(e_eu) == 'europa' and P.region_de(e_sa) == 'sudamerica'
    for e, prohibida in ((e_eu, 'sudamerica'), (e_sa, 'europa')):
        assert all(m[3] != prohibida for m in P.marcas_para(e))
        for i in range(60):
            cs = P._nuevo(e, random.Random(i))['contratos']
            assert all(c['marca'] and next(m for m in P.MARCAS if m[0] == c['marca'])[3] != prohibida for c in cs.values())
        p = P.datos(e)
        for i in range(60):
            for espacio in ('camiseta', 'manga', 'estadio'):
                p['contratos'][espacio] = None
                for o in P.generar_ofertas(e, espacio, random.Random(i)):
                    assert next(m for m in P.MARCAS if m[0] == o['marca'])[3] != prohibida
    print("  test_region_nunca_cruza: OK")


def test_club_real_arranca_con_sus_marcas():
    e = estado_carrera()                                   # Manchester Billete
    cs = P.datos(e)['contratos']
    assert [cs[x]['marca'] for x in ('camiseta', 'manga', 'estadio')] == ["Etihat", "Pumba", "Etihat"]
    assert cs['camiseta']['rubro'] == cs['estadio']['rubro'] == "aerolínea"      # la exclusividad no aplica
    e = _club('premier', 'Pool de Higado')                 # v4.9.2: estadio sin naming → arranca sin patrocinador
    real = PAT.PATROCINIOS_REALES['Pool de Higado']
    assert real['estadio'] is None
    cs = P.datos(e)['contratos']
    assert cs['camiseta']['marca'] == real['camiseta'] and cs['manga']['marca'] == real['manga']
    assert cs['estadio'] is None
    for c in (cs['camiseta'], cs['manga']):
        assert 1 <= c['anios'] <= 3 and c['fijo'] > 0 and c['objetivo']['texto']
    print("  test_club_real_arranca_con_sus_marcas: OK")


def test_club_sin_entrada_marcas_de_su_region():
    e = _club('betplay', 'Matecaña Averiada')
    assert 'Matecaña Averiada' not in PAT.PATROCINIOS_REALES
    for i in range(20):
        cs = P._nuevo(e, random.Random(i))['contratos']
        assert len({c['rubro'] for c in cs.values()}) == 3
        assert _regiones_ok(e, [c['marca'] for c in cs.values()])
    print("  test_club_sin_entrada_marcas_de_su_region: OK")


TESTS = [test_fracciones_y_ingresos_esperados, test_contratos_iniciales, test_cobro_jornada,
         test_objetivos_cumple_y_progreso, test_crear_objetivo_dificultad]
TESTS += [test_generar_ofertas_exclusividad_y_valor, test_renovacion_solo_si_cumplio, test_sin_interesados,
          test_firmar_y_prima, test_firmar_exclusividad, test_rechazar_todo_deja_vacio, test_negociar, test_rescindir]
TESTS += [test_evaluar_temporada_bonos_y_reputacion, test_cambio_division, test_cierre_contratos_vencen_y_ofertas,
          test_revisar_jornada_ventanas, test_enganches_del_ciclo]
TESTS += [test_pantalla_patrocinios, test_pantalla_registrada_con_ayuda_y_atajos]
# v4.9.1: van primero porque los tests de cierre de temporada mutan las ligas cacheadas (ascensos/descensos)
TESTS = [test_catalogo_150_marcas, test_reales_existen_y_son_compatibles, test_region_nunca_cruza,
         test_club_real_arranca_con_sus_marcas, test_club_sin_entrada_marcas_de_su_region] + TESTS
# --- TESTS-FIN ---

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
