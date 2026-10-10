"""0.4.23.0: conferencias de prensa (overlay), efectos de los cuatro tonos y `factor_tarjetas` del motor."""
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


# ------------------------------------------------------------------ cuándo se ofrece
def test_motivos_y_prioridad():
    e = _estado(); liga = e['liga']
    p, local, visit = _situar(e, 10)
    _poner_posicion(e, 10)
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
    assert P.motivo_partido(e, local, visit, 'liga') is None             # en 2ª no se habla de descenso en la prensa


def test_una_vez_por_fase_y_partido():
    e = _estado()
    p, local, visit = _clasico(e, 1)
    pre = P.evaluar_pre(e, local, visit, 'liga')
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
    e['mi_equipo'].rival = ''
    assert P.evaluar_pre(e, local, visit, 'liga') is None and 'prensa_overlay' not in e


def test_banco_completo():
    assert set(P.TONOS) == {'motivador', 'provocador', 'humilde', 'agresivo'}
    assert set(P.BANCO) == {'copa_final', 'copa_semi', 'clasico', 'titulo', 'descenso', 'lider'}
    for motivo, fases in P.BANCO.items():
        grupos = [('pre', fases['pre'])] + [(f'post/{r}', fases['post'][r]) for r in ('gana', 'empata', 'pierde')]
        for nombre, preguntas in grupos:
            assert len(preguntas) >= 2, (motivo, nombre)
            for q in preguntas:
                assert 0 < len(q['texto']) <= 100, (motivo, nombre, q['texto'])
                assert set(q['respuestas']) == set(P.TONOS), (motivo, nombre)
                assert all(0 < len(t) <= 120 for t in q['respuestas'].values()), (motivo, nombre)


# ------------------------------------------------------------------ efectos de los tonos
def test_motivador_y_humilde_suben_la_moral_propia():
    e = _estado(); mi = e['mi_equipo']
    for j in mi.jugadores:
        j.moral = 50
    mi.jugadores[0].moral = 99
    p, local, visit = _clasico(e, 1)
    conf = P.evaluar_post(e, local, visit, 2, 0, 'liga')
    r = P.responder(e, conf, 'motivador')
    assert r['texto'] and r['efectos']
    assert mi.jugadores[0].moral == 100 and all(j.moral == 52 for j in mi.jugadores[1:])
    n = _declaraciones(e)[0]
    assert n['importancia'] == 3 and n['categoria'] == 'prensa' and n['tipo'] == 'declaracion'
    p2, local2, visit2 = _clasico(e, 2)
    conf2 = P.evaluar_post(e, local2, visit2, 0, 0, 'liga')
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
    conf = P.evaluar_post(e, local, visit, 2, 0, 'liga')
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
    conf = P.evaluar_pre(e, local, visit, 'liga')
    P.responder(e, conf, 'provocador')
    assert all(j.moral == 68 for j in rival.jugadores)
    P.consumir_tension(e)                                                # al terminar ese partido se devuelve
    assert all(j.moral == 70 for j in rival.jugadores)


def test_provocador_con_el_rival_sin_jugadores_no_lanza():
    e = _estado()
    p, local, visit = _clasico(e, 1)
    rival = _rival(e, local, visit)
    conf = P.evaluar_pre(e, local, visit, 'liga')
    P.responder(e, conf, 'provocador')
    rival.jugadores = []
    P.consumir_tension(e)


def test_agresivo_pone_tension_y_se_consume():
    e = _estado()
    p, local, visit = _clasico(e, 1)
    assert P.factor_tarjetas(e) == 1.0
    conf = P.evaluar_post(e, local, visit, 1, 1, 'liga')
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
    conf = P.evaluar_pre(e, local, visit, 'liga')
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
    conf = P.evaluar_pre(e, local, visit, 'liga')
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


# ------------------------------------------------------------------ interfaz
def _tecla(k):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, unicode='', mod=0))


def _nueva_pre(e, jornada=1):
    e['datos_carrera'].pop('prensa', None); e.pop('prensa_overlay', None)
    p, local, visit = _clasico(e, jornada)
    return P.evaluar_pre(e, local, visit, 'liga')


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
    _situar(e, 1)
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
    conf = P.evaluar_post(e, local, visit, 1, 1, 'liga')
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
