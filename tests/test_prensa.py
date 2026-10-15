"""0.4.23.0: conferencias de prensa (overlay), efectos de los tonos y `factor_tarjetas` del motor.
0.4.25.0: ocho tonos (cuatro por pregunta) y motivos contextuales."""
import sys, os, copy, json, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
screen = pygame.display.set_mode((1280, 720))
from alpha_football import save
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402

from alpha_football import noticias as N
from alpha_football import prensa as P
from alpha_football import engine as ENG
from alpha_football import partido_ctx as PC
from alpha_football.ui import league_screen as L

_BASE = None


def _estado():
    """Carrera de la Premier con el calendario armado y sin clásicos (se copia: cargarla cuesta ~3 s)."""
    global _BASE
    if _BASE is None:
        _BASE = estado_carrera()
        L.inicializar_calendario_liga(_BASE['liga'])
        for x in _BASE['liga'].equipos:
            x.rival = ''
    return copy.deepcopy(_BASE)


def _situar(e, jornada=1):
    """Deja el partido del user de esa jornada como el actual; devuelve (partido, local, visitante)."""
    liga, mi = e['liga'], e['mi_equipo']
    p = next(x for x in liga.calendario if x.jornada == jornada and mi.id in (x.local_id, x.visitante_id))
    e['partido_actual'], e['match_mode'], liga.jornada_actual = p, 'liga', jornada
    local = next(x for x in liga.equipos if x.id == p.local_id)
    visit = next(x for x in liga.equipos if x.id == p.visitante_id)
    return p, local, visit


def _rival(e, local, visit):
    return visit if local.id == e['mi_equipo'].id else local


def _poner_posicion(e, pos):
    """Reparte puntos para que el user quede en `pos` con 3 puntos de diferencia entre puestos."""
    liga, mi = e['liga'], e['mi_equipo']
    otros = [x for x in liga.equipos if x is not mi]
    orden = otros[:pos - 1] + [mi] + otros[pos - 1:]
    for i, x in enumerate(orden):
        x.puntos, x.gf, x.gc = (len(orden) - i) * 3, 10, 10


def _clasico(e, jornada=1):
    p, local, visit = _situar(e, jornada)
    e['mi_equipo'].rival = _rival(e, local, visit).nombre
    return p, local, visit


def _declaraciones(e):
    return [n for n in N.lista(e) if n['tipo'] == 'declaracion' and n['categoria'] == 'prensa']


def _morales(equipo):
    return [j.moral for j in equipo.jugadores]


def _base(conf):
    """Deja en la conferencia una pregunta de las de siempre (con los cuatro tonos base): la que el partido sortea
    puede ser de las nuevas, que ofrecen otros tonos. Devuelve la misma conferencia (o None)."""
    if conf:
        grupo = P.BANCO[conf['motivo']]['pre'] if conf['fase'] == 'pre' else P.BANCO[conf['motivo']]['post'][conf['resultado']]
        conf['pregunta'] = copy.deepcopy(grupo[0])
        assert set(conf['pregunta']['respuestas']) == {'motivador', 'provocador', 'humilde', 'agresivo'}
    return conf


def _tabla(e, mi_pos, rival_pos):
    """Reparte puntos (3 por puesto) para que el user quede en `mi_pos` y su rival del partido actual en `rival_pos`."""
    liga, mi = e['liga'], e['mi_equipo']
    p = e['partido_actual']
    rival = next(x for x in liga.equipos if x.id in (p.local_id, p.visitante_id) and x is not mi)
    otros = [x for x in liga.equipos if x is not mi and x is not rival]
    orden = [None] * len(liga.equipos)
    orden[mi_pos - 1], orden[rival_pos - 1] = mi, rival
    for i in range(len(orden)):
        if orden[i] is None:
            orden[i] = otros.pop(0)
    for i, x in enumerate(orden):
        x.puntos, x.gf, x.gc = (len(orden) - i) * 3, 10, 10
    return rival


# ------------------------------------------------------------------ cuándo se ofrece
def test_motivos_y_prioridad():
    e = _estado(); liga = e['liga']
    p, local, visit = _situar(e, 10)
    _poner_posicion(e, 6)
    assert P.motivo_partido(e, local, visit, 'liga') is None             # mitad de tabla, nada especial
    _poner_posicion(e, 1)
    assert P.motivo_partido(e, local, visit, 'liga') == 'lider'          # líder con la temporada a medias
    _poner_posicion(e, len(liga.equipos))
    assert P.motivo_partido(e, local, visit, 'liga') == 'descenso'
    p, local, visit = _situar(e, liga.num_jornadas - 2)                  # quedan 3 jornadas
    _poner_posicion(e, 2)
    assert P.motivo_partido(e, local, visit, 'liga') == 'titulo'         # a 3 puntos del líder
    _poner_posicion(e, 5)
    assert P.motivo_partido(e, local, visit, 'liga') is None             # a 12 puntos: ya no pelea el título
    e['mi_equipo'].rival = _rival(e, local, visit).nombre
    assert P.motivo_partido(e, local, visit, 'liga') == 'clasico'
    e['partido_copa_dict'] = {'id': 'champions-3-1', 'fase': 'Semifinal'}
    assert P.motivo_partido(e, local, visit, 'copa') == 'copa_semi'      # gana al clásico
    e['partido_copa_dict'] = {'id': 'champions-4-1', 'fase': 'Final'}
    assert P.motivo_partido(e, local, visit, 'copa') == 'copa_final'     # y 'semifinal' no cuenta como 'final'
    assert P.motivo_partido(e, local, visit, 'amistoso') is None


def test_descenso_pide_primera_y_jornada_4():
    e = _estado(); liga = e['liga']
    p, local, visit = _situar(e, 3)
    _poner_posicion(e, len(liga.equipos))
    assert P.motivo_partido(e, local, visit, 'liga') is None             # jornada 3: muy pronto
    p, local, visit = _situar(e, 10)
    liga.division = 2
    assert P.motivo_partido(e, local, visit, 'liga') != 'descenso'       # en 2ª no se habla de descenso en la prensa


def test_una_vez_por_fase_y_partido():
    e = _estado()
    p, local, visit = _clasico(e, 1)
    pre = _base(P.evaluar_pre(e, local, visit, 'liga'))
    assert pre and pre['fase'] == 'pre' and e['prensa_overlay'] is pre
    P.responder(e, pre, 'humilde')
    assert P.evaluar_pre(e, local, visit, 'liga') is None                # ya hecha
    post = P.evaluar_post(e, local, visit, 2, 1, 'liga')
    assert post and post['fase'] == 'post'                               # pre y post son independientes
    P.saltar(e)
    assert P.evaluar_post(e, local, visit, 2, 1, 'liga') is None
    p2, local2, visit2 = _clasico(e, 2)                                  # otro partido sí
    assert P.evaluar_pre(e, local2, visit2, 'liga')


def test_nunca_en_amistoso_ni_sin_motivo():
    e = _estado()
    p, local, visit = _clasico(e, 1)
    assert P.evaluar_pre(e, local, visit, 'amistoso') is None
    assert P.evaluar_post(e, local, visit, 1, 0, 'amistoso') is None
    p, local, visit = _situar(e, 6)                                      # jornada 6, mitad de tabla: nada especial
    _poner_posicion(e, 6)
    e['mi_equipo'].rival = ''
    assert P.evaluar_pre(e, local, visit, 'liga') is None and 'prensa_overlay' not in e


def test_banco_completo():
    assert set(P.TONOS) == {'motivador', 'provocador', 'humilde', 'agresivo', 'ironico', 'diplomatico', 'elogioso',
                            'evasivo'}
    antiguos = {'copa_final', 'copa_semi', 'clasico', 'titulo', 'descenso', 'lider'}
    nuevos = {'copa_ronda', 'racha_buena', 'racha_mala', 'lesionados', 'favorito', 'david', 'rival_directo', 'debut',
              'cierre', 'figura', 'goleada_favor', 'goleada_contra'}
    assert set(P.BANCO) == antiguos | nuevos
    assert set(P.MOTIVO_TEXTO) >= set(P.BANCO)
    for motivo, fases in P.BANCO.items():
        grupos = [('pre', fases.get('pre') or [])] + [(f'post/{r}', (fases.get('post') or {}).get(r) or [])
                                                       for r in ('gana', 'empata', 'pierde')]
        for nombre, preguntas in grupos:
            if not preguntas:                                            # solo lesionados (sin post) y goleadas (sin pre)
                assert motivo in ('lesionados', 'goleada_favor', 'goleada_contra'), (motivo, nombre)
                continue
            minimo = 3 if motivo in antiguos else 1                       # los de siempre: 2 + las nuevas
            assert len(preguntas) >= minimo, (motivo, nombre)
            for q in preguntas:
                assert 0 < len(q['texto']) <= 100, (motivo, nombre, q['texto'])
                assert len(q['respuestas']) == 4 and set(q['respuestas']) <= set(P.TONOS), (motivo, nombre)
                assert all(0 < len(t) <= 120 for t in q['respuestas'].values()), (motivo, nombre)
    total = sum(len(g.get('pre') or []) + sum(len(v) for v in (g.get('post') or {}).values()) for g in P.BANCO.values())
    assert total >= 140                                                  # antes eran 48 preguntas


def test_todas_las_marcas_se_rellenan():
    """Ninguna pregunta ni respuesta deja una marca {…} sin rellenar, aunque falte el contexto."""
    for motivo, fases in P.BANCO.items():
        grupos = list(fases.get('pre') or []) + [q for v in (fases.get('post') or {}).values() for q in v]
        for q in grupos:
            for ctx in (None, {}, {'jugador': "Pérez", 'fase': "Octavos", 'puesto': 3, 'racha': 4, 'lesionados': 5}):
                marcas = P._marcas(ctx, "Club A", "Club B")
                for texto in [q['texto']] + list(q['respuestas'].values()):
                    for k, v in marcas.items():
                        texto = texto.replace('{' + k + '}', v)
                    assert '{' not in texto and '}' not in texto, (motivo, texto)


# ------------------------------------------------------------------ efectos de los tonos
def test_motivador_y_humilde_suben_la_moral_propia():
    e = _estado(); mi = e['mi_equipo']
    for j in mi.jugadores:
        j.moral = 50
    mi.jugadores[0].moral = 99
    p, local, visit = _clasico(e, 1)
    conf = _base(P.evaluar_post(e, local, visit, 2, 0, 'liga'))
    r = P.responder(e, conf, 'motivador')
    assert r['texto'] and r['efectos']
    assert mi.jugadores[0].moral == 100 and all(j.moral == 52 for j in mi.jugadores[1:])
    n = _declaraciones(e)[0]
    assert n['importancia'] == 3 and n['categoria'] == 'prensa' and n['tipo'] == 'declaracion'
    p2, local2, visit2 = _clasico(e, 2)
    conf2 = _base(P.evaluar_post(e, local2, visit2, 0, 0, 'liga'))
    P.responder(e, conf2, 'humilde')
    assert all(j.moral == 53 for j in mi.jugadores[1:]) and _declaraciones(e)[0]['importancia'] == 2


def test_provocador_baja_moral_del_siguiente_rival_y_se_devuelve():
    e = _estado(); liga = e['liga']
    p, local, visit = _clasico(e, 1)
    sig = next(x for x in liga.calendario if x.jornada == 2 and e['mi_equipo'].id in (x.local_id, x.visitante_id))
    rival2 = next(x for x in liga.equipos if x.id in (sig.local_id, sig.visitante_id) and x is not e['mi_equipo'])
    for j in rival2.jugadores:
        j.moral = 60
    rival2.jugadores[0].moral = 1                                        # el tope de 0 no debe regalar moral al devolver
    conf = _base(P.evaluar_post(e, local, visit, 2, 0, 'liga'))
    P.responder(e, conf, 'provocador')
    assert rival2.jugadores[0].moral == 0 and all(j.moral == 58 for j in rival2.jugadores[1:])
    assert _declaraciones(e)[0]['importancia'] == 4
    P.consumir_tension(e)
    assert rival2.jugadores[0].moral == 1 and all(j.moral == 60 for j in rival2.jugadores[1:])
    P.consumir_tension(e)                                                # idempotente: no devuelve dos veces
    assert all(j.moral == 60 for j in rival2.jugadores[1:])


def test_provocador_en_pre_castiga_al_rival_del_partido():
    e = _estado()
    p, local, visit = _clasico(e, 1)
    rival = _rival(e, local, visit)
    for j in rival.jugadores:
        j.moral = 70
    conf = _base(P.evaluar_pre(e, local, visit, 'liga'))
    P.responder(e, conf, 'provocador')
    assert all(j.moral == 68 for j in rival.jugadores)
    P.consumir_tension(e)                                                # al terminar ese partido se devuelve
    assert all(j.moral == 70 for j in rival.jugadores)


def test_provocador_con_el_rival_sin_jugadores_no_lanza():
    e = _estado()
    p, local, visit = _clasico(e, 1)
    rival = _rival(e, local, visit)
    conf = _base(P.evaluar_pre(e, local, visit, 'liga'))
    P.responder(e, conf, 'provocador')
    rival.jugadores = []
    P.consumir_tension(e)


def test_agresivo_pone_tension_y_se_consume():
    e = _estado()
    p, local, visit = _clasico(e, 1)
    assert P.factor_tarjetas(e) == 1.0
    conf = _base(P.evaluar_post(e, local, visit, 1, 1, 'liga'))
    P.responder(e, conf, 'agresivo')
    assert P.factor_tarjetas(e) == P.FACTOR_TENSION == 1.6
    assert _declaraciones(e)[0]['importancia'] == 3
    e['match_mode'] = 'amistoso'
    assert P.factor_tarjetas(e) == 1.0                                   # el amistoso no la usa ni la gasta
    e['match_mode'] = 'liga'
    assert P.factor_tarjetas(e) == 1.6
    P.consumir_tension(e)
    assert P.factor_tarjetas(e) == 1.0


def test_saltar_no_cambia_nada():
    e = _estado(); mi = e['mi_equipo']
    p, local, visit = _clasico(e, 1)
    rival = _rival(e, local, visit)
    antes = (_morales(mi), _morales(rival), len(N.lista(e)))
    P.evaluar_pre(e, local, visit, 'liga')
    P.saltar(e)
    assert 'prensa_overlay' not in e
    assert (_morales(mi), _morales(rival), len(N.lista(e))) == antes
    assert P.factor_tarjetas(e) == 1.0
    assert P.evaluar_pre(e, local, visit, 'liga') is None                # saltar también cuenta como hecha


def test_rival_dt_declara_en_pre():
    e = _estado(); mi = e['mi_equipo']
    for j in mi.jugadores:
        j.moral = 50
    p, local, visit = _clasico(e, 1)
    conf = _base(P.evaluar_pre(e, local, visit, 'liga'))
    assert conf['declaracion']                                           # su frase se muestra en el overlay
    P.responder(e, conf, 'agresivo')                                     # el agresivo no toca la moral propia
    assert all(j.moral == 49 for j in mi.jugadores)
    dec = _declaraciones(e)
    assert sorted(n['importancia'] for n in dec) == [2, 3]


def test_mover_moral_anota_causa():
    e = _estado(); mi = e['mi_equipo']
    j = mi.jugadores[0]
    j.moral, j.causas_moral = 1, [{'minutos': 0, 'equipo': 0, 'sueldo': 0}]
    P.mover_moral([j], -5)
    assert j.moral == 0 and j.causas_moral[-1]['equipo'] == -5
    P.mover_moral([j], +200)
    assert j.moral == 100


def test_datos_carrera_json_y_save_viejo():
    e = _estado()
    e['datos_carrera'] = {}
    p, local, visit = _clasico(e, 1)
    conf = _base(P.evaluar_pre(e, local, visit, 'liga'))
    P.responder(e, conf, 'provocador')
    P.consumir_tension(e)
    P.factor_tarjetas(e)
    json.dumps(e['datos_carrera'])
    e.pop('datos_carrera')                                               # sin datos_carrera tampoco lanza
    P.factor_tarjetas(e); P.consumir_tension(e); P.saltar(e)


# ------------------------------------------------------------------ motor
def test_remapeo_del_sorteo():
    rejilla = [(i + 0.5) / 10000 for i in range(10000)]
    assert all(ENG._remapear_sorteo_tarjetas(r, 1.0) == r for r in rejilla)
    k = 1.6
    mapa = [ENG._remapear_sorteo_tarjetas(r, k) for r in rejilla]
    assert all(b >= a for a, b in zip(mapa, mapa[1:]))                   # monótono
    masa_tarjetas = sum(1 for m in mapa if m < ENG._C_ROJA) / len(mapa)
    assert abs(masa_tarjetas - k * ENG._C_ROJA) < 1e-3
    resto = sum(1 for m in mapa if ENG._C_ROJA <= m < ENG._C_FALTA) / len(mapa)
    sin_cambio = sum(1 for r in rejilla if ENG._C_ROJA <= r < ENG._C_FALTA) / len(rejilla)
    assert abs(resto - sin_cambio) < 1e-3                                # lesiones, penales y faltas no cambian


def test_ctx_copia_el_factor():
    e = _estado(); liga = e['liga']
    a, b = liga.equipos[0], liga.equipos[1]
    ctx = PC.nuevo_estado(a, b, ENG._once_titular(a), ENG._once_titular(b))
    assert ctx.factor_tarjetas == 1.0
    ctx.factor_tarjetas = 1.6
    assert ctx.copia().factor_tarjetas == 1.6
    random.seed(3)
    res = ENG.simular_partido(a, b, aplicar_fisico=False, factor_tarjetas=1.6)
    assert res.ctx.factor_tarjetas == 1.6
    assert ENG.simular_partido(a, b, aplicar_fisico=False).ctx.factor_tarjetas == 1.0


def test_el_factor_da_mas_tarjetas_en_el_motor():
    e = _estado(); liga = e['liga']
    a, b = liga.equipos[0], liga.equipos[1]

    def tarjetas(k, semilla):
        random.seed(semilla)
        total = 0
        for _ in range(120):
            ctx = PC.nuevo_estado(a, b, ENG._once_titular(a), ENG._once_titular(b))
            ctx.factor_tarjetas = k
            eventos = []
            for m in range(1, 91):
                ENG._incidencias_minuto(m, a, b, ctx, eventos)
            total += sum(1 for ev in eventos if ev['tipo'] in ('amarilla', 'roja'))
        return total
    base, tenso = tarjetas(1.0, 11), tarjetas(2.0, 11)
    assert tenso > base * 1.5, (base, tenso)


def test_el_partido_en_vivo_hereda_la_tension():
    from alpha_football.ui import match_screen as MS
    e = _estado()
    _situar(e, 1)
    e['datos_carrera']['prensa'] = {'tension': P.FACTOR_TENSION}
    pygame.event.clear(); MS.render(screen, e)
    assert e['sim_ctx'].factor_tarjetas == P.FACTOR_TENSION
    e2 = _estado()
    _situar(e2, 1)
    pygame.event.clear(); MS.render(screen, e2)
    assert e2['sim_ctx'].factor_tarjetas == 1.0


def test_simulacion_instantanea_pasa_la_tension_y_la_consume():
    from alpha_football.ui import prepartido_screen as PS
    e = _estado()
    p, local, visit = _situar(e, 1)
    e['datos_carrera']['prensa'] = {'tension': P.FACTOR_TENSION}
    vistos, original = [], ENG.simular_partido

    def espia(*a, **k):
        vistos.append(k.get('factor_tarjetas'))
        return original(*a, **k)
    ENG.simular_partido = espia
    try:
        random.seed(5)
        PS._simular_instantaneo(e, local, visit)
    finally:
        ENG.simular_partido = original
    assert vistos[0] == P.FACTOR_TENSION                                 # el partido del user lleva la tensión
    assert all(v is None for v in vistos[1:])                            # los partidos IA-IA siguen en 1.0
    assert p.jugado and P.factor_tarjetas(e) == 1.0                      # el partido oficial gasta la tensión


# ------------------------------------------------------------------ motivos contextuales (0.4.25.0)
def _contadores(e, **kw):
    c = e['datos_carrera'].setdefault('logros', {}).setdefault('contadores', {})
    c.update(kw)


def test_motivos_contextuales_de_tabla():
    e = _estado(); n = len(e['liga'].equipos)
    p, local, visit = _situar(e, 8)
    _tabla(e, 2, n)                                                      # tú arriba, rival último
    assert P.motivo_partido(e, local, visit, 'liga') == 'favorito'
    _tabla(e, n - 3, 2)                                                  # tú abajo, rival entre los tres primeros
    assert P.motivo_partido(e, local, visit, 'liga') == 'david'
    _tabla(e, 3, 4)                                                      # vecinos en la zona alta
    assert P.motivo_partido(e, local, visit, 'liga') == 'rival_directo'
    _tabla(e, n - 3, n - 2)                                              # vecinos en la zona baja
    assert P.motivo_partido(e, local, visit, 'liga') == 'rival_directo'
    _tabla(e, 6, 7)                                                      # vecinos a mitad de tabla: sin motivo
    assert P.motivo_partido(e, local, visit, 'liga') is None
    p, local, visit = _situar(e, 3)
    _tabla(e, 2, n)
    assert P.motivo_partido(e, local, visit, 'liga') is None             # antes de la jornada 4 no hay favoritos


def test_motivos_debut_y_cierre_y_prioridades():
    e = _estado(); liga = e['liga']; n = len(liga.equipos)
    p, local, visit = _situar(e, 1)
    _tabla(e, 6, 7)
    assert P.motivo_partido(e, local, visit, 'liga') == 'debut'
    e['mi_equipo'].rival = _rival(e, local, visit).nombre
    assert P.motivo_partido(e, local, visit, 'liga') == 'clasico'        # el clásico manda sobre el debut
    e['mi_equipo'].rival = ''
    p, local, visit = _situar(e, liga.num_jornadas)                      # última jornada
    _tabla(e, 6, 7)
    assert P.motivo_partido(e, local, visit, 'liga') == 'cierre'
    p, local, visit = _situar(e, liga.num_jornadas - 1)                  # penúltima
    assert P.motivo_partido(e, local, visit, 'liga') == 'cierre'
    _tabla(e, 1, n)
    assert P.motivo_partido(e, local, visit, 'liga') == 'titulo'         # pelear el título pesa más que el cierre


def test_motivos_de_racha_y_enfermeria():
    e = _estado()
    p, local, visit = _situar(e, 8)
    _tabla(e, 6, 7)
    assert P.motivo_partido(e, local, visit, 'liga') is None
    _contadores(e, racha=3)
    assert P.motivo_partido(e, local, visit, 'liga') == 'racha_buena'
    _contadores(e, racha=2)
    assert P.motivo_partido(e, local, visit, 'liga') is None
    _contadores(e, racha=0, derrotas_seguidas=2)
    assert P.motivo_partido(e, local, visit, 'liga') == 'racha_mala'
    _contadores(e, derrotas_seguidas=0, sin_ganar=4)
    assert P.motivo_partido(e, local, visit, 'liga') == 'racha_mala'
    _contadores(e, sin_ganar=0)
    for j in e['mi_equipo'].jugadores[:3]:
        j.lesion_dias = 12
    assert P.motivo_partido(e, local, visit, 'liga') == 'lesionados'
    assert P.motivo_partido(e, local, visit, 'liga', fase='post') is None   # la enfermería es solo de la previa
    for j in e['mi_equipo'].jugadores[:3]:
        j.lesion_dias = 0
    e['mi_equipo'].jugadores[5].goles = 7
    assert P.motivo_partido(e, local, visit, 'liga') == 'figura'
    assert P.contexto(e, local, visit, 'liga')['jugador'] == e['mi_equipo'].jugadores[5].apellido


def test_copa_que_no_es_semi_ni_final_es_copa_ronda():
    e = _estado()
    p, local, visit = _situar(e, 8)
    for fase in ("Octavos", "Cuartos", "Playoff", "Fase de liga"):
        e['partido_copa_dict'] = {'id': 'champions-1-1', 'fase': fase}
        assert P.motivo_partido(e, local, visit, 'copa') == 'copa_ronda', fase
    e['partido_copa_dict'] = {'id': 'champions-3-1', 'fase': 'Semifinal'}
    assert P.motivo_partido(e, local, visit, 'copa') == 'copa_semi'
    e['partido_copa_dict'] = {'id': 'champions-1-1', 'fase': 'Cuartos'}
    conf = P.evaluar_pre(e, local, visit, 'copa')
    assert conf and conf['motivo'] == 'copa_ronda' and '{' not in conf['pregunta']['texto']
    assert P.contexto(e, local, visit, 'copa')['fase'] == 'Cuartos'
    q = P._pregunta('copa_ronda', 'pre', None, 'k', "Mi Club", "Rival FC", P.contexto(e, local, visit, 'copa'))
    assert '{' not in q['texto']
    assert P._marcas({'fase': 'Cuartos'}, "A", "B")['fase'] == 'Cuartos'


def test_goleada_manda_sobre_los_motivos_menores_en_el_postpartido():
    e = _estado()
    p, local, visit = _situar(e, 8)
    _tabla(e, 6, 7)
    es_local = local.id == e['mi_equipo'].id
    g = (4, 0) if es_local else (0, 4)                                   # ganas por 4
    conf = P.evaluar_post(e, local, visit, *g, 'liga')
    assert conf and conf['motivo'] == 'goleada_favor' and conf['resultado'] == 'gana' and conf['marcador'] == '4-0'
    P.saltar(e)
    p, local, visit = _situar(e, 9)
    _tabla(e, 6, 7)
    es_local = local.id == e['mi_equipo'].id
    g = (0, 3) if es_local else (3, 0)                                   # pierdes por 3
    conf = P.evaluar_post(e, local, visit, *g, 'liga')
    assert conf and conf['motivo'] == 'goleada_contra' and conf['resultado'] == 'pierde'
    P.saltar(e)
    p, local, visit = _situar(e, 10)
    _tabla(e, 6, 7)
    assert P.evaluar_post(e, local, visit, 1, 0, 'liga') is None         # por la mínima y sin motivo: nada
    e['mi_equipo'].rival = _rival(e, local, visit).nombre                # clásico: manda el clásico aunque sea goleada
    es_local = local.id == e['mi_equipo'].id
    conf = P.evaluar_post(e, local, visit, *((5, 0) if es_local else (0, 5)), 'liga')
    assert conf and conf['motivo'] == 'clasico'


def test_goleada_no_aplica_si_no_hay_pregunta_para_ese_resultado():
    e = _estado()
    p, local, visit = _situar(e, 8)
    _tabla(e, 6, 7)
    # 'goleada_favor' solo tiene preguntas para ganar; con una diferencia de goles del lado contrario cae en 'contra'
    assert set(P.BANCO['goleada_favor']['post']) == {'gana'}
    assert set(P.BANCO['goleada_contra']['post']) == {'pierde'}


def test_marcas_del_contexto_aparecen_en_la_pregunta():
    e = _estado()
    p, local, visit = _situar(e, 8)
    _tabla(e, 6, 7)
    e['mi_equipo'].jugadores[2].goles = 9
    rival = _rival(e, local, visit)
    q = P._pregunta('figura', 'pre', None, 'k1', "Mi Club", rival.nombre, P.contexto(e, local, visit, 'liga'))
    texto = q['texto'] + " ".join(q['respuestas'].values())
    assert e['mi_equipo'].jugadores[2].apellido in texto and '{' not in texto
    q2 = P._pregunta('racha_buena', 'pre', None, 'k2', "Mi Club", "Rival FC", {'racha': 5})
    assert "5 victorias" in q2['texto'] or '{' not in q2['texto']


# ------------------------------------------------------------------ los cuatro tonos nuevos
def _conf_con(e, tono):
    """Una conferencia previa a un clásico cuya pregunta ofrece `tono` (la construye con ese tono a mano)."""
    p, local, visit = _clasico(e, 1)
    conf = P.evaluar_pre(e, local, visit, 'liga')
    resp = {t: f"Respuesta {t}" for t in ('motivador', 'humilde', 'agresivo')}
    resp[tono] = f"Respuesta {tono}"
    conf['pregunta'] = {'texto': "Pregunta de prueba", 'respuestas': resp}
    return conf, local, visit


def test_ironico_sube_tu_moral_y_baja_la_del_rival():
    e = _estado(); mi = e['mi_equipo']
    conf, local, visit = _conf_con(e, 'ironico')
    rival = _rival(e, local, visit)
    for j in mi.jugadores:
        j.moral = 50
    for j in rival.jugadores:
        j.moral = 70
    r = P.responder(e, conf, 'ironico')
    assert r['tono'] == 'ironico' and r['texto'] == "Respuesta ironico"
    assert all(j.moral == 50 + 1 - 1 for j in mi.jugadores)              # +1 propio, -1 por las palabras del DT rival
    assert all(j.moral == 69 for j in rival.jugadores)                   # -1 al rival (mitad del provocador)
    P.consumir_tension(e)
    assert all(j.moral == 70 for j in rival.jugadores)                   # se devuelve igual que el del provocador
    assert [n for n in _declaraciones(e) if n['importancia'] == 3]


def test_diplomatico_evita_el_golpe_del_dt_rival():
    e = _estado(); mi = e['mi_equipo']
    conf, local, visit = _conf_con(e, 'diplomatico')
    assert conf['declaracion']
    for j in mi.jugadores:
        j.moral = 50
    r = P.responder(e, conf, 'diplomatico')
    assert all(j.moral == 51 for j in mi.jugadores)                      # +1, y sin el -1 del mensaje del DT rival
    assert any("calma" in x for x in r['efectos'])
    assert P.factor_tarjetas(e) == 1.0


def test_elogioso_sube_la_moral_de_la_figura_nombrada():
    e = _estado(); mi = e['mi_equipo']
    conf, local, visit = _conf_con(e, 'elogioso')
    figura = mi.jugadores[4]
    conf['jugador'], conf['jugador_id'] = figura.apellido, str(figura.id)
    for j in mi.jugadores:
        j.moral = 40
    r = P.responder(e, conf, 'elogioso')
    assert figura.moral == 40 + 3 - 1                                    # +3 al elogiado y -1 del mensaje del DT rival
    assert all(j.moral == 39 for j in mi.jugadores if j is not figura)
    assert any(figura.apellido in x for x in r['efectos'])
    assert any(figura.apellido in n['titular'] for n in _declaraciones(e))
    e2 = _estado(); mi2 = e2['mi_equipo']                                # sin jugador en la pregunta: +1 al plantel
    conf2, _l, _v = _conf_con(e2, 'elogioso')
    conf2['jugador'], conf2['jugador_id'] = '', ''
    for j in mi2.jugadores:
        j.moral = 40
    P.responder(e2, conf2, 'elogioso')
    assert all(j.moral == 40 + 1 - 1 for j in mi2.jugadores)


def test_evasivo_no_cambia_nada_y_es_noticia_menor():
    e = _estado(); mi = e['mi_equipo']
    conf, local, visit = _conf_con(e, 'evasivo')
    rival = _rival(e, local, visit)
    antes_rival = _morales(rival)
    for j in mi.jugadores:
        j.moral = 50
    P.responder(e, conf, 'evasivo')
    assert all(j.moral == 49 for j in mi.jugadores)                      # solo el golpe del mensaje del DT rival
    assert _morales(rival) == antes_rival and P.factor_tarjetas(e) == 1.0
    assert sorted(n['importancia'] for n in _declaraciones(e)) == [1, 2]
    assert not any(n['importancia'] >= N.IMPORTANCIA_FEED for n in _declaraciones(e))   # no entra al feed del hub


def test_la_figura_solo_cuenta_si_la_pregunta_la_menciona():
    e = _estado()
    p, local, visit = _situar(e, 8)
    _tabla(e, 6, 7)
    e['mi_equipo'].jugadores[2].goles = 9
    ctx = P.contexto(e, local, visit, 'liga')
    con = P._pregunta('figura', 'pre', None, 'a', "Mi Club", "Rival FC", ctx)
    sin = P._pregunta('copa_ronda', 'pre', None, 'a', "Mi Club", "Rival FC", ctx)
    assert con['usa_jugador'] is True and sin['usa_jugador'] is False
    assert all('{jugador}' not in t for t in [con['texto'], *con['respuestas'].values()])
    # una pregunta que no habla de nadie deja el overlay sin figura: el elogio va al plantel
    for jornada, motivo in ((8, 'rival_directo'),):
        P.BANCO[motivo]['pre'], original = [P.BANCO[motivo]['pre'][1]], P.BANCO[motivo]['pre']
        try:
            _tabla(e, 3, 4)
            conf = P.evaluar_pre(e, local, visit, 'liga')
            assert conf and conf['motivo'] == motivo and conf['jugador_id'] == '' and conf['jugador'] == ''
        finally:
            P.BANCO[motivo]['pre'] = original


def test_responder_con_un_tono_que_la_pregunta_no_ofrece_no_hace_nada():
    e = _estado()
    conf, local, visit = _conf_con(e, 'ironico')
    r = P.responder(e, conf, 'diplomatico')
    assert r == {'texto': '', 'efectos': []} and conf.get('respuesta') is None
    assert P.responder(e, conf, 'no_existe') == {'texto': '', 'efectos': []}


def test_overlay_asigna_las_teclas_a_los_tonos_de_cada_pregunta():
    from alpha_football.ui import prensa_overlay as PO
    e = _estado()
    conf, local, visit = _conf_con(e, 'elogioso')
    e['prensa_overlay'] = conf
    conf['pregunta']['respuestas'] = {'ironico': "I", 'diplomatico': "D", 'elogioso': "E", 'evasivo': "S"}
    assert PO.tonos_de(conf) == ['ironico', 'diplomatico', 'elogioso', 'evasivo']
    PO.dibujar(screen, e, (0, 0))                                        # etiquetas de los tonos nuevos
    PO.manejar(e, [pygame.K_4], None)
    assert conf['respuesta']['tono'] == 'evasivo'                        # la tecla 4 es el cuarto tono de ESTA pregunta
    e2 = _estado()
    conf2, _l, _v = _conf_con(e2, 'elogioso')
    e2['prensa_overlay'] = conf2
    conf2['pregunta']['respuestas'] = {'ironico': "I", 'diplomatico': "D", 'elogioso': "E", 'evasivo': "S"}
    PO.manejar(e2, [], PO.rect_respuesta(1).center)                      # clic en la segunda caja
    assert conf2['respuesta']['tono'] == 'diplomatico'
    assert all(PO._ETIQUETA_TONO.get(t) for t in P.TONOS)


# ------------------------------------------------------------------ interfaz
def _tecla(k):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, unicode='', mod=0))


def _nueva_pre(e, jornada=1):
    e['datos_carrera'].pop('prensa', None); e.pop('prensa_overlay', None)
    p, local, visit = _clasico(e, jornada)
    return _base(P.evaluar_pre(e, local, visit, 'liga'))


def test_overlay_dibuja_y_consume():
    from alpha_football.ui import prensa_overlay as PO
    e = _estado()
    _nueva_pre(e)
    assert PO.activo(e) and PO.activo(e, 'pre') and not PO.activo(e, 'post')
    PO.dibujar(screen, e, (0, 0))                                        # con la pregunta
    PO.manejar(e, [pygame.K_RETURN], None)
    assert e['prensa_overlay']['respuesta'] is None                      # Enter sin responder no hace nada
    PO.manejar(e, [pygame.K_2], None)
    assert e['prensa_overlay']['respuesta']['tono'] == 'provocador'
    PO.dibujar(screen, e, (0, 0))                                        # con la consecuencia y CONTINUAR
    PO.manejar(e, [pygame.K_RETURN], None)
    assert not PO.activo(e)
    _nueva_pre(e)
    publicadas = len(N.lista(e))
    PO.manejar(e, [pygame.K_ESCAPE], None)
    assert not PO.activo(e) and len(N.lista(e)) == publicadas            # saltar no publica nada
    _nueva_pre(e)
    PO.manejar(e, [pygame.K_s], None)
    assert not PO.activo(e)
    _nueva_pre(e)
    PO.manejar(e, [], PO.R_SALTAR.center)
    assert not PO.activo(e)
    _nueva_pre(e)
    PO.manejar(e, [], PO.rect_respuesta(2).center)
    assert e['prensa_overlay']['respuesta']['tono'] == 'humilde'
    assert all(PO.R_PANEL.contains(PO.rect_respuesta(i)) for i in range(4)) and PO.R_PANEL.contains(PO.R_SALTAR)


def test_prepartido_ofrece_el_overlay_en_un_clasico():
    from alpha_football.ui import prepartido_screen as PS, prensa_overlay as PO
    e = _estado()
    _clasico(e, 1)
    e['datos_carrera']['aviso_mercado_visto'] = [1, '2026-07-01']
    pygame.event.clear()
    assert PS.render(screen, e) is None
    assert e['prensa_overlay']['fase'] == 'pre'
    _base(e['prensa_overlay'])                                           # cuatro tonos de siempre: 1 = motivador
    _tecla(pygame.K_RETURN)
    assert PS.render(screen, e) is None                                  # el partido no arranca
    _tecla(pygame.K_1)
    assert PS.render(screen, e) is None                                  # 1 responde (no es JUGAR)
    assert e['prensa_overlay']['respuesta']['tono'] == 'motivador'
    _tecla(pygame.K_RETURN)
    assert PS.render(screen, e) is None and not PO.activo(e)             # CONTINUAR cierra el overlay
    _tecla(pygame.K_RETURN)
    assert PS.render(screen, e) == 'match_screen'                        # ahora sí: JUGAR


def test_prepartido_sin_motivo_no_ofrece_nada():
    from alpha_football.ui import prepartido_screen as PS
    e = _estado()
    _situar(e, 6)                                                        # jornada 6, mitad de tabla, sin clásico
    _poner_posicion(e, 6)
    e['datos_carrera']['aviso_mercado_visto'] = [1, '2026-07-01']
    pygame.event.clear()
    assert PS.render(screen, e) is None and 'prensa_overlay' not in e
    _tecla(pygame.K_1)
    assert PS.render(screen, e) == 'match_screen'


def test_postpartido_ofrece_el_overlay():
    from alpha_football.ui import postpartido as PP, prensa_overlay as PO
    e = _estado()
    p, local, visit = _clasico(e, 1)
    ctx = PC.nuevo_estado(local, visit, [], [])
    PP.armar_datos(e, 'liga', local, visit, 2, 1, ctx, {}, [], pos_antes=3)
    assert e['prensa_overlay']['fase'] == 'post'
    _base(e['prensa_overlay'])                                           # cuatro tonos de siempre: 3 = humilde
    assert PP.render(screen, e, (0, 0), None, [pygame.K_RETURN]) is None   # el overlay consume la tecla
    PP.render(screen, e, (0, 0), None, [pygame.K_3])
    assert e['prensa_overlay']['respuesta']['tono'] == 'humilde'
    assert PP.render(screen, e, (0, 0), None, [pygame.K_RETURN]) is None and not PO.activo(e)
    assert PP.render(screen, e, (0, 0), None, [pygame.K_RETURN]) == 'continuar'


def test_postpartido_amistoso_no_ofrece_y_consume_la_tension():
    from alpha_football.ui import postpartido as PP
    e = _estado()
    p, local, visit = _clasico(e, 1)
    ctx = PC.nuevo_estado(local, visit, [], [])
    conf = _base(P.evaluar_post(e, local, visit, 1, 1, 'liga'))
    P.responder(e, conf, 'agresivo'); P.saltar(e)
    PP.armar_datos(e, 'amistoso', local, visit, 1, 0, ctx, {}, [])
    assert 'prensa_overlay' not in e and P.factor_tarjetas(e) == 1.6     # el amistoso no gasta la tensión
    PP.armar_datos(e, 'liga', local, visit, 1, 0, ctx, {}, [])
    assert P.factor_tarjetas(e) == 1.0                                   # el partido oficial sí


if __name__ == '__main__':
    fallos = 0
    for nombre, f in sorted(globals().items()):
        if nombre.startswith('test_') and callable(f):
            try:
                f(); print(f"  {nombre}: OK")
            except Exception as ex:
                fallos += 1; print(f"  {nombre}: FALLA {type(ex).__name__}: {ex}")
    sys.exit(1 if fallos else 0)
