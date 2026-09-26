"""v4.4.0: nivel de fin de temporada (ascenso/descenso/objetivos), salidas de jugadores
(descontento, pide salir, salida forzada, ofertas garantizadas, escalada) y aviso de mercado."""
import sys, os, random, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(13)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save
from alpha_football.models import Jugador, Equipo, alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams, _ligas_por_division

_tmp = tempfile.mkdtemp()
save.guardar_en_slot = lambda *a, **k: None          # los tests no tocan los slots reales


def key(k, uni=''):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=uni))


def estado_carrera(tipo='premier', idx=0):
    liga = load_league_teams(tipo)
    mi = liga.equipos[idx]
    mi.alineacion_activa = alineacion_por_defecto(mi)
    primeras, segunda = _ligas_por_division(liga, {}, {})
    return {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
            'alineacion_activa': mi.alineacion_activa, 'primera_division': primeras,
            'segunda_division': segunda, 'datos_carrera': {}, 'historial': []}


def jug(pos='MED', ovr=70, edad=25, nota=6.0, pj=20, jid=None):
    j = Jugador("N", f"J{jid or random.randint(1, 10**6)}", pos, ovr, ovr, ovr, ovr, ovr)
    j.id = jid or random.randint(1, 10**6)
    j.edad, j.promedio_nota, j.partidos_jugados, j.potencial = edad, nota, pj, min(99, ovr + 5)
    return j


# ---------------------------------------------------------------- Task 1: campos del jugador
def test_campos_nuevos_persisten():
    j = jug(jid=7)
    assert (j.salida_forzada, j.escalon_salida, j.causas_moral, j.jornadas_sin_jugar,
            j.descontento_avisado) == (False, 0, [], 0, False)
    j.salida_forzada, j.escalon_salida, j.jornadas_sin_jugar, j.descontento_avisado = True, 3, 2, True
    j.causas_moral = [{'minutos': -2, 'equipo': 0, 'sueldo': 0}]
    r = Jugador.from_dict(j.to_dict())
    assert (r.salida_forzada, r.escalon_salida, r.jornadas_sin_jugar, r.descontento_avisado) == (True, 3, 2, True)
    assert r.causas_moral == [{'minutos': -2, 'equipo': 0, 'sueldo': 0}]
    viejo = j.to_dict()
    for k in ('salida_forzada', 'escalon_salida', 'causas_moral', 'jornadas_sin_jugar', 'descontento_avisado'):
        viejo.pop(k)
    v = Jugador.from_dict(viejo)                          # save viejo: defaults
    assert (v.salida_forzada, v.escalon_salida, v.causas_moral) == (False, 0, [])
    print("  test_campos_nuevos_persisten: OK")


def test_limpiar_salida():
    from alpha_football.salidas import limpiar
    j = jug()
    j.transferible = j.pide_salir = j.salida_forzada = j.descontento_avisado = True
    j.escalon_salida = 4
    limpiar(j)
    assert not (j.transferible or j.pide_salir or j.salida_forzada or j.descontento_avisado)
    assert j.escalon_salida == 0
    print("  test_limpiar_salida: OK")


# ---------------------------------------------------------------- Task 2: tramos y ascenso/descenso
def _liga_de(equipos, num_jornadas=22):
    class L: pass
    l = L(); l.equipos = equipos; l.num_jornadas = num_jornadas; l.division = 1; l.tipo = 'premier'
    return l


def test_tramos_por_cuartos_y_corregidos_por_puesto():
    from alpha_football import nivel_temporada as N
    # 8 elegibles: 1 portero con 6.6 (media de porteros 6.6) y 7 de campo en escalera
    por = jug('POR', 70, nota=6.6, jid=1)
    campo = [jug('MED', 70, nota=6.4 - 0.1 * i, jid=10 + i) for i in range(7)]
    banco = jug('DEL', 70, nota=7.5, pj=2, jid=99)          # no elegible (2 de 22)
    eq = Equipo("A", "A", 3.0, "cruyffismo", 1, [por] + campo + [banco])
    medias = N.medias_por_puesto(_liga_de([eq]))
    assert abs(medias['POR'] - 6.6) < 1e-9 and abs(medias['MED'] - 6.1) < 1e-9
    d = N.deltas_equipo(eq, medias, 22, 'descenso')
    # puntajes: MED 6.4 → +0.3 (mejor), portero 0.0 (medio), MED 5.8 → −0.3 (peor)
    assert d[id(campo[0])] == -2 and d[id(campo[-1])] == -5
    assert d[id(por)] in (-3, -4)                          # el portero NO queda primero
    assert d[id(banco)] == N.NO_ELEGIBLE['descenso'] == -3
    a = N.deltas_equipo(eq, medias, 22, 'ascenso')
    assert a[id(campo[0])] == 6 and a[id(campo[-1])] == 3 and a[id(banco)] == 4
    o = N.deltas_equipo(eq, medias, 22, 'objetivos')
    assert o[id(campo[0])] == 0 and o[id(campo[-1])] == -2 and o[id(banco)] == -1
    print("  test_tramos_por_cuartos_y_corregidos_por_puesto: OK")


def test_pocos_elegibles():
    from alpha_football import nivel_temporada as N
    js = [jug('MED', 70, nota=6.5, jid=1)] + [jug('MED', 70, nota=6.0, pj=0, jid=2 + i) for i in range(5)]
    eq = Equipo("B", "B", 3.0, "cruyffismo", 1, js)
    d = N.deltas_equipo(eq, N.medias_por_puesto(_liga_de([eq])), 22, 'descenso')
    assert d[id(js[0])] == -2 and all(d[id(j)] == -3 for j in js[1:])
    eq0 = Equipo("C", "C", 3.0, "cruyffismo", 1, [jug(pj=0, jid=50)])
    assert N.deltas_equipo(eq0, N.medias_por_puesto(_liga_de([eq0])), 22, 'ascenso')[id(eq0.jugadores[0])] == 4
    print("  test_pocos_elegibles: OK")


def test_ascenso_techo_83_y_potencial():
    from alpha_football import nivel_temporada as N
    a, b, c = jug(ovr=80, jid=1), jug(ovr=83, jid=2), jug(ovr=70, jid=3)
    for x in (a, b, c):
        x.partidos_jugados = 0                              # no elegibles → +4
    pot_c = c.potencial
    eq = Equipo("D", "D", 3.0, "cruyffismo", 1, [a, b, c])
    N.aplicar(eq, 'ascenso', {})
    assert a.overall == 83 and b.overall == 83 and c.overall == 74
    assert c.potencial == min(99, max(pot_c + 4, c.overall + 1))
    print("  test_ascenso_techo_83_y_potencial: OK")


def test_descenso_sin_plan_y_registro():
    from alpha_football.mercado_ia import aplicar_descenso
    js = [jug(ovr=70, pj=0, jid=i + 1) for i in range(4)]
    eq = Equipo("E", "E", 3.0, "cruyffismo", 1, js)
    e = {'mi_equipo': eq}
    aplicar_descenso(eq, e)
    assert all(j.overall == 67 for j in js)
    assert e['_nivel_tmp'][id(js[0])] == (-3, 67, -6)
    assert e['_nivel_user']['caso'] == 'descenso' and id(eq) in e['_nivel_movidos']
    print("  test_descenso_sin_plan_y_registro: OK")


# ---------------------------------------------------------------- Task 3: objetivos, topes, cierre
def test_objetivo_fallado_user():
    from alpha_football import nivel_temporada as N
    e = {'temporada': 3, 'datos_carrera': {'directiva_ultimo': {'temporada': 2, 'resultado': 'fallado', 'copa': None}}}
    assert N.objetivo_fallado_user(e)
    e['datos_carrera']['directiva_ultimo']['copa'] = {'resultado': 'cumplido'}
    assert not N.objetivo_fallado_user(e)                         # cumplió la copa
    e['datos_carrera']['directiva_ultimo']['copa'] = {'resultado': 'fallado'}
    e['datos_carrera']['pedidos_temporada'] = [{'temporada': 2, 'cumplido': True}]
    assert not N.objetivo_fallado_user(e)                         # cumplió un pedido
    e['datos_carrera']['pedidos_temporada'] = [{'temporada': 1, 'cumplido': True}, {'temporada': 2, 'cumplido': False}]
    assert N.objetivo_fallado_user(e)                             # el cumplido es de otra temporada
    e['datos_carrera']['directiva_ultimo']['resultado'] = 'cumplido'
    assert not N.objetivo_fallado_user(e)
    e['datos_carrera']['directiva_ultimo'] = {'temporada': 1, 'resultado': 'fallado'}
    assert not N.objetivo_fallado_user(e)                         # evaluación vieja: no cuenta
    print("  test_objetivo_fallado_user: OK")


def test_pedido_queda_registrado():
    from alpha_football import directiva as D
    e = estado_carrera()
    e['datos_carrera']['pedido'] = {'temporada': 1, 'tipo': 'puntos', 'texto': 'x', 'hasta': 5,
                                    'resuelto': False, 'cumplido': False}
    D.resolver_pedido(e, True)
    assert e['datos_carrera']['pedidos_temporada'][-1] == {'temporada': 1, 'cumplido': True}
    print("  test_pedido_queda_registrado: OK")


def test_objetivo_ia_con_y_sin_foto():
    from alpha_football import nivel_temporada as N
    e = estado_carrera()
    liga = e['liga']
    ranking = sorted(liga.equipos, key=lambda x: -x.ovr_promedio)
    peor = ranking[-1]
    pm = N.pos_max_ia(liga, 'premier', 1, peor)
    assert 1 <= pm <= len(liga.equipos)
    e['temporada'] = 2
    N.foto_objetivos_ia(e)
    foto = e['datos_carrera']['objetivos_ia']
    assert foto['temporada'] == 2 and foto['pos_max'][peor.nombre] == pm
    print("  test_objetivo_ia_con_y_sin_foto: OK")


def test_topes_con_la_curva():
    from alpha_football import nivel_temporada as N
    from alpha_football.mercado_ia import _mover_media
    a, b = jug(ovr=70, pj=0, jid=1), jug(ovr=70, pj=0, jid=2)
    eq = Equipo("F", "F", 3.0, "cruyffismo", 1, [a, b])
    e = {'mi_equipo': eq, 'datos_carrera': {}, 'temporada': 2,
         'primera_division': {'premier': _liga_de([eq])}, 'segunda_division': {}}
    N.aplicar(eq, 'descenso', e)                                   # −3 a los dos
    _mover_media(a, -4)                                            # curva de un veterano: −4 → total −7
    _mover_media(b, 1)                                             # joven: +1 → total −2 (no se toca)
    N.aplicar_topes(e)
    assert a.overall == 64 and b.overall == 68                     # tope −6 / subida suma
    assert '_nivel_tmp' not in e and '_nivel_user' not in e
    correo = e['datos_carrera']['correo'][0]
    assert correo['asunto'].startswith("Descenso") and "mala forma" in correo['asunto']
    print("  test_topes_con_la_curva: OK")


def test_no_se_suman_bajones():
    from alpha_football import nivel_temporada as N
    eq = Equipo("G", "G", 3.0, "cruyffismo", 1, [jug(ovr=70, pj=0, jid=1)])
    e = {'mi_equipo': None, 'datos_carrera': {}, 'temporada': 2,
         'primera_division': {'premier': _liga_de([eq])}, 'segunda_division': {},
         '_nivel_plan': {id(eq): {'medias': {'*': 6.0}, 'num_jornadas': 22, 'grande': False,
                                  'objetivo_fallado': True}}}
    N.aplicar(eq, 'descenso', e)
    N.aplicar_objetivos(e)                                          # ya se movió: no suma
    assert eq.jugadores[0].overall == 67
    print("  test_no_se_suman_bajones: OK")


def test_cierre_temporada_completo():
    from alpha_football.ui.resumen_temporada_screen import avanzar_nueva_temporada
    from alpha_football.ui.league_screen import completar_ligas_de_fondo
    e = estado_carrera('premier', 0)
    e['liga'].jornada_actual = e['liga'].num_jornadas + 1
    completar_ligas_de_fondo(e)
    for liga in list(e['primera_division'].values()) + list(e['segunda_division'].values()):
        for eq in liga.equipos:
            for i, j in enumerate(eq.jugadores):
                j.partidos_jugados = liga.num_jornadas if i < 14 else 0
                j.promedio_nota = 6.0 + (i % 5) * 0.1
    antes = {id(j): j.overall for l in e['primera_division'].values() for eq in l.equipos for j in eq.jugadores}
    avanzar_nueva_temporada(e)
    assert e['temporada'] == 2
    assert e['datos_carrera']['objetivos_ia']['temporada'] == 2
    assert not any(k.startswith('_nivel_') for k in e)
    movidos = [id(j) for l in e['primera_division'].values() for eq in l.equipos for j in eq.jugadores
               if id(j) in antes and j.overall != antes[id(j)]]
    assert movidos                                                  # alguien cambió de nivel
    print("  test_cierre_temporada_completo: OK")


# ---------------------------------------------------------------- Task 4: moral
def _plantel_moral(n=16):
    js = [jug(ovr=60 + i, jid=100 + i) for i in range(n)]
    for j in js:
        j.salario, j.personalidad, j.moral = 10**9, 'normal', 70
    return Equipo("Moral FC", "M", 3.0, "cruyffismo", 1, js)


def test_moral_sin_jugar_y_causas():
    from alpha_football import vestuario as V
    eq = _plantel_moral(); js = eq.jugadores
    crack = js[-1]                                                # 75 ≥ media (67.5)
    once = {j.id for j in js[:11]}                                # el crack no juega
    for i in range(3):
        V.actualizar_moral(eq, [], 0, 0, False, once)
    assert crack.jornadas_sin_jugar == 3
    # jornadas 1-3: top5 sin jugar −6 c/u; jornada 3 además −2 (3 sin jugar)
    assert crack.moral == 70 - 6 - 6 - 8
    assert crack.causas_moral[-1] == {'minutos': -8, 'equipo': 0, 'sueldo': 0}
    V.actualizar_moral(eq, [], 0, 0, False, once | {crack.id})
    assert crack.jornadas_sin_jugar == 0
    print("  test_moral_sin_jugar_y_causas: OK")


def test_sueldo_80_por_ciento():
    from alpha_football import vestuario as V
    from alpha_football.finanzas import salario_mercado
    eq = _plantel_moral(); j = eq.jugadores[0]
    j.salario = int(salario_mercado(j) * 0.79)
    V.actualizar_moral(eq, [], 0, 0, False, {x.id for x in eq.jugadores})
    assert j.moral == 66 and j.causas_moral[-1]['sueldo'] == -4
    j.moral, j.salario = 70, int(salario_mercado(j) * 0.81) + 1
    V.actualizar_moral(eq, [], 0, 0, False, {x.id for x in eq.jugadores})
    assert j.moral == 70
    print("  test_sueldo_80_por_ciento: OK")


def test_pide_salir_umbral_50():
    from alpha_football import vestuario as V
    eq = _plantel_moral(); js = eq.jugadores
    norm, pol, lid = js[0], js[1], js[2]
    pol.personalidad, lid.personalidad = 'polemico', 'lider'
    todos = {j.id for j in js}
    salen = []
    for _ in range(5):
        for x in (norm, pol, lid):
            x.moral = 45
        salen += V.actualizar_moral(eq, [], 0, 0, False, todos)['pide_salir']
    assert salen.index(pol) < salen.index(norm) < salen.index(lid)     # 3 / 4 / 5 jornadas
    assert norm.transferible and norm.pide_salir
    norm.moral = 60
    V.actualizar_moral(eq, [], 0, 0, False, todos)
    assert norm.pide_salir                                            # la cura es de salidas.py
    print("  test_pide_salir_umbral_50: OK")


# ---------------------------------------------------------------- Task 5: salidas
def _estado_salidas():
    e = estado_carrera('premier', 0)
    e['liga'].jornada_actual = 2                                   # ventana abierta
    for eq in e['liga'].equipos:
        eq.balance = 10**10
    return e


def test_textos_descontento_5_por_causa():
    from alpha_football import salidas as S
    for causa in ('minutos', 'equipo', 'sueldo'):
        assert len(set(S.TEXTOS_DESCONTENTO[causa])) == 5, causa
    print("  test_textos_descontento_5_por_causa: OK")


def test_descontento_por_causa_y_una_vez():
    from alpha_football import salidas as S
    e = _estado_salidas(); mi = e['mi_equipo']
    j = mi.jugadores[0]
    j.moral = 45
    j.causas_moral = [{'minutos': 0, 'equipo': -4, 'sueldo': -8}]
    assert S.causa_principal(j) == 'sueldo'
    S.revisar_descontento(e, rng=random.Random(1))
    msgs = [m for m in e['datos_carrera']['correo'] if j.apellido in m['asunto']]
    assert len(msgs) == 1 and msgs[0]['accion'].get('renovar') == j.id
    S.revisar_descontento(e)                                      # mismo episodio: no repite
    assert len([m for m in e['datos_carrera']['correo'] if j.apellido in m['asunto']]) == 1
    j.moral = 60; S.revisar_descontento(e)
    assert not j.descontento_avisado                              # episodio cerrado
    j.causas_moral = [{'minutos': -6, 'equipo': 0, 'sueldo': 0}]
    assert S.causa_principal(j) == 'minutos'
    print("  test_descontento_por_causa_y_una_vez: OK")


def test_curados_y_forzada_no_se_cura():
    from alpha_football import salidas as S
    e = _estado_salidas(); a, b = e['mi_equipo'].jugadores[:2]
    for x in (a, b):
        x.pide_salir = x.transferible = True; x.moral = 60; x.escalon_salida = 2
    b.salida_forzada = True
    assert S.revisar_curados(e) == [a]
    assert not a.pide_salir and not a.transferible and a.escalon_salida == 0
    assert b.pide_salir and b.transferible
    print("  test_curados_y_forzada_no_se_cura: OK")


def test_oferta_garantizada_solo_con_ventana():
    from alpha_football import salidas as S
    e = _estado_salidas(); j = e['mi_equipo'].jugadores[0]
    j.pide_salir = j.transferible = True
    nuevas = S.ofertas_garantizadas(e, rng=random.Random(2))
    assert len(nuevas) == 1 and nuevas[0]['jugador'] is j and nuevas[0]['comprador'] is not e['mi_equipo']
    assert S.ofertas_garantizadas(e) == []                          # ya tiene una pendiente
    e['ofertas_recibidas'] = []
    e['liga'].jornada_actual = 8                                    # ventana cerrada
    assert S.ofertas_garantizadas(e) == []
    print("  test_oferta_garantizada_solo_con_ventana: OK")


def test_escalada_por_rechazo_y_por_jornada():
    from alpha_football import salidas as S, directiva as D
    e = _estado_salidas(); j = e['mi_equipo'].jugadores[0]
    j.pide_salir = j.transferible = True; j.moral = 40
    e['datos_carrera']['confianza'] = 70
    calif0 = D.calif_dt(e)
    S.oferta_rechazada(e, j)
    assert j.escalon_salida == 1 and j.moral == 32
    S.oferta_rechazada(e, j)                                        # misma jornada: 2º escalón
    assert j.escalon_salida == 2 and D.confianza(e) == 65
    correos = [m for m in e['datos_carrera']['correo'] if j.apellido in m['asunto']]
    assert len(correos) == 1                                        # un correo por jornada
    e['liga'].jornada_actual = 3
    S.cierre_jornada(e, rng=random.Random(3))                       # jornada sin vender: escalón 3
    assert j.escalon_salida == 3 and D.confianza(e) == 60 and D.calif_dt(e) == calif0 - 2
    e['liga'].jornada_actual = 20
    S.cierre_jornada(e, rng=random.Random(3))
    assert j.escalon_salida == 4 and D.confianza(e) == 50 and D.calif_dt(e) == calif0 - 6
    e['liga'].jornada_actual = 10                                   # ventana cerrada: no sube
    S.cierre_jornada(e)
    assert j.escalon_salida == 4
    print("  test_escalada_por_rechazo_y_por_jornada: OK")


def test_rechazo_desde_ofertas_screen_y_venta_limpia():
    from alpha_football import salidas as S
    from alpha_football.ui import ofertas_screen as OS
    from alpha_football.contraofertas import vender
    e = _estado_salidas(); j = e['mi_equipo'].jugadores[0]
    j.pide_salir = j.transferible = True
    of = S.ofertas_garantizadas(e, rng=random.Random(4))[0]
    OS._rechazar_sel(e, of)
    assert j.escalon_salida == 1
    of2 = S.ofertas_garantizadas(e, rng=random.Random(5))[0]
    assert vender(e, of2) and j.escalon_salida == 0 and not j.pide_salir
    print("  test_rechazo_desde_ofertas_screen_y_venta_limpia: OK")


def test_transferible_bloqueado():
    from alpha_football.ui import plantilla_screen as PS
    j = jug(); j.pide_salir = j.transferible = True
    assert PS.alternar_transferible(j) is True and j.transferible
    k = jug(); assert PS.alternar_transferible(k) is True and PS.alternar_transferible(k) is False
    print("  test_transferible_bloqueado: OK")


def test_renovar_bien_pagado_sube_moral():
    from alpha_football.finanzas import salario_mercado
    from alpha_football.negociacion import renovar
    e = _estado_salidas(); j = e['mi_equipo'].jugadores[0]
    j.moral = 45; j.causas_moral = [{'minutos': 0, 'equipo': 0, 'sueldo': -4}]
    renovar(e, j, salario_mercado(j), 3, 2.0)
    assert j.moral == 55 and all(c['sueldo'] == 0 for c in j.causas_moral)
    j.moral = 45
    renovar(e, j, int(salario_mercado(j) * 0.9), 3, 2.0)
    assert j.moral == 45
    print("  test_renovar_bien_pagado_sube_moral: OK")


def test_correo_renovar_abre_negociacion():
    from alpha_football.ui import correo_screen as CS
    e = _estado_salidas(); j = e['mi_equipo'].jugadores[0]
    destino = CS._ir(e, {'id': 1, 'accion': {'pantalla': 'negociacion_screen', 'texto': 'RENOVAR', 'renovar': j.id}})
    assert destino == 'negociacion_screen' and e['neg']['jugador'] is j and e['neg']['modo'] == 'renovar'
    print("  test_correo_renovar_abre_negociacion: OK")


# ---------------------------------------------------------------- Task 6: salida forzada
def test_marcar_salida_forzada_user_e_ia():
    from alpha_football import salidas as S
    e = _estado_salidas(); mi = e['mi_equipo']
    top3 = sorted(mi.jugadores, key=lambda x: -x.overall)[:3]
    assert S.marcar_salida_forzada(e, mi) == top3
    assert all(j.pide_salir and j.transferible and j.salida_forzada for j in top3)
    assert any("piden salir" in m['asunto'] for m in e['datos_carrera']['correo'])
    ia = e['liga'].equipos[1]
    S.marcar_salida_forzada(e, ia)
    marcados = [j for j in ia.jugadores if j.salida_forzada]
    assert len(marcados) == 3 and not any(j.pide_salir for j in marcados)
    print("  test_marcar_salida_forzada_user_e_ia: OK")


def test_descenso_de_grande_marca_y_de_chico_no():
    from alpha_football import nivel_temporada as N
    e = _estado_salidas(); liga = e['liga']
    rk = sorted(liga.equipos, key=lambda x: -x.ovr_promedio)
    grande, chico = rk[0], rk[-1]
    e['temporada'] = 2
    N.preparar(e)
    N.aplicar(chico, 'descenso', e)
    assert not any(j.salida_forzada for j in chico.jugadores)
    N.aplicar(grande, 'descenso', e)
    assert sum(1 for j in grande.jugadores if j.salida_forzada) == 3
    print("  test_descenso_de_grande_marca_y_de_chico_no: OK")


def test_ia_vende_salidas_forzadas():
    from alpha_football.mercado_ia import vender_salidas_forzadas
    e = _estado_salidas()
    ia = e['liga'].equipos[3]
    estrellas = sorted(ia.jugadores, key=lambda x: -x.overall)[:3]
    for j in estrellas:
        j.salida_forzada = True
    log = vender_salidas_forzadas(e, rng=random.Random(1))
    assert len(log) == 3
    assert not any(j in ia.jugadores for j in estrellas) and not any(j.salida_forzada for j in estrellas)
    print("  test_ia_vende_salidas_forzadas: OK")


# ---------------------------------------------------------------- Task 7: aviso de mercado
def test_eventos_ventana():
    from alpha_football.ui import aviso_mercado as AM
    # v4.5.0: mercado de invierno a mitad de temporada
    assert AM.eventos_ventana(22) == {1: 'abre', 4: 'cierra', 11: 'abre', 14: 'cierra', 20: 'abre'}
    assert AM.eventos_ventana(14) == {1: 'abre', 4: 'cierra', 7: 'abre', 10: 'cierra', 12: 'abre'}
    print("  test_eventos_ventana: OK")


def test_cartel_una_vez_y_teclas():
    from alpha_football.ui import aviso_mercado as AM
    e = estado_carrera(); e['liga'].jornada_actual = 1
    assert AM.evento_pendiente(e) == ('abre', 1)
    dest, keys, click = AM.manejar(e, [], None)
    assert e.get('aviso_mercado_activo') and dest is None and AM.evento_pendiente(e) is None
    assert any("abrió el mercado" in m['asunto'] for m in e['datos_carrera']['correo'])
    ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode='')
    dest, keys, click = AM.manejar(e, [ev], (5, 5))
    assert dest is None and keys == [] and click is None and not e.get('aviso_mercado_activo')
    AM.manejar(e, [], None)
    assert not e.get('aviso_mercado_activo')                       # no se repite
    e['liga'].jornada_actual = 4
    AM.manejar(e, [], None)
    assert e['aviso_mercado_activo']['tipo'] == 'cierra'
    enter = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode='')
    dest, _k, _c = AM.manejar(e, [enter], None)                     # cerrado: foco inicial = CONTINUAR
    assert dest is None and not e.get('aviso_mercado_activo')
    print("  test_cartel_una_vez_y_teclas: OK")


def test_cartel_espera_a_la_ayuda():
    from alpha_football.ui import aviso_mercado as AM
    e = estado_carrera(); e['liga'].jornada_actual = 1
    e['ayuda_abierta'] = True
    AM.manejar(e, [], None)
    assert not e.get('aviso_mercado_activo') and AM.evento_pendiente(e) == ('abre', 1)
    e['ayuda_abierta'] = False
    AM.manejar(e, [], None, bloqueado=True)                         # diálogo de salida abierto
    assert not e.get('aviso_mercado_activo')
    print("  test_cartel_espera_a_la_ayuda: OK")


def test_franja_no_choca_y_render():
    from alpha_football.ui import aviso_mercado as AM
    from alpha_football.ui.league_screen import R_SOBRE
    from alpha_football.ui.theme import get_font
    e = estado_carrera(); e['liga'].jornada_actual = 21
    r = AM.rect_franja(e)
    assert r is not None and r.top >= 76 and not r.colliderect(R_SOBRE) and r.bottom <= 106
    assert 16 + AM._ancho_cabecera(e) + 8 <= r.left                 # la cabecera real de este club
    # v4.4.0: peor caso (liga y club con el nombre más largo): pasa al texto corto y sigue sin chocar
    cab = ("PREMIER LEAGUE PARODIA LARGA XX  ·  Manchester City Parodia  ·  1ª División  ·  T12  ·  "
           "Jornada 21/22  ·  $999.9M")
    w = get_font('sm').size(cab)[0]
    r2 = AM.rect_franja(e, ancho_cabecera=w)
    assert 16 + w + 8 <= r2.left and r2.width < r.width
    e['liga'].jornada_actual = 8
    assert AM.rect_franja(e) is None                                # ventana cerrada
    e['liga'].jornada_actual = 1
    AM.manejar(e, [], None)
    AM.dibujar(screen, e, (0, 0))                                   # cartel sin excepciones
    e['aviso_mercado_activo'] = None; e['liga'].jornada_actual = 22
    AM.dibujar(screen, e, (0, 0))                                   # franja "ÚLTIMA JORNADA"
    print("  test_franja_no_choca_y_render: OK")


def test_hub_consume_eventos_con_cartel():
    from alpha_football.ui import league_screen as LS
    e = estado_carrera(); e['liga'].jornada_actual = 1
    pygame.event.clear(); LS.render(screen, e)                      # abre el cartel
    assert e.get('aviso_mercado_activo')
    key(pygame.K_j)                                                 # J = jugar: el cartel se la come
    assert LS.render(screen, e) is None and e.get('aviso_mercado_activo')
    key(pygame.K_ESCAPE)
    assert LS.render(screen, e) is None and not e.get('aviso_mercado_activo') and not e.get('dialogo_salir')
    print("  test_hub_consume_eventos_con_cartel: OK")


# ---------------------------------------------------------------- Revisión final (fix pass)
def test_traspaso_ia_limpia_salida_forzada():
    from alpha_football.mercado_ia import _traspasar
    e = _estado_salidas(); a, b = e['liga'].equipos[2], e['liga'].equipos[3]
    j = a.jugadores[0]; j.salida_forzada = True
    _traspasar(j, a, b, 1000, 'premier')
    assert j in b.jugadores and not j.salida_forzada               # I1: no se revende desde el club nuevo
    print("  test_traspaso_ia_limpia_salida_forzada: OK")


def test_cambiar_de_club_suelta_a_los_que_piden_salir():
    from alpha_football import directiva as D, salidas as S
    e = _estado_salidas(); viejo = e['mi_equipo']
    forzados = S.marcar_salida_forzada(e, viejo)
    moral = [j for j in viejo.jugadores if j not in forzados][0]
    moral.pide_salir = moral.transferible = True; moral.escalon_salida = 2
    nuevo = e['liga'].equipos[5]
    D.cambiar_de_club(e, nuevo)
    assert not any(j in viejo.jugadores for j in forzados)           # I2: la IA los vende al tomar el club
    assert not moral.pide_salir and not moral.transferible and moral.escalon_salida == 0
    print("  test_cambiar_de_club_suelta_a_los_que_piden_salir: OK")


def test_rechazo_con_mercado_cerrado_no_escala():
    from alpha_football import salidas as S
    e = _estado_salidas(); j = e['mi_equipo'].jugadores[0]
    j.pide_salir = j.transferible = True; j.moral = 40
    e['liga'].jornada_actual = 8                                     # M3: ventana cerrada
    S.oferta_rechazada(e, j)
    assert j.escalon_salida == 0 and j.moral == 40
    print("  test_rechazo_con_mercado_cerrado_no_escala: OK")


def test_escalada_ultima_jornada_manda_correo():
    from alpha_football import salidas as S
    e = _estado_salidas(); liga = e['liga']; mi = e['mi_equipo']; j = mi.jugadores[0]
    j.pide_salir = j.transferible = True; j.escalon_salida = 1; j.moral = 30
    from alpha_football.ui.league_screen import inicializar_calendario_liga
    inicializar_calendario_liga(liga)
    liga.jornada_actual = liga.num_jornadas
    nuestros = [p for p in liga.calendario if mi.id in (p.local_id, p.visitante_id)]
    assert len(nuestros) >= 2
    for p in nuestros[:-1]:
        p.jugado = True
    S.cierre_jornada(e, rng=random.Random(1))                        # cierre de la penúltima fecha jugada
    antes = len(e['datos_carrera']['correo'])
    if nuestros:
        nuestros[-1].jugado = True                                   # última fecha: jornada_actual no avanza
    S.cierre_jornada(e, rng=random.Random(1))
    nuevos = e['datos_carrera']['correo'][:len(e['datos_carrera']['correo']) - antes]
    assert j.escalon_salida == 3 and any(j.apellido in m['asunto'] for m in nuevos)   # M2: hubo correo
    print("  test_escalada_ultima_jornada_manda_correo: OK")


TESTS = [f for n, f in list(globals().items()) if n.startswith('test_') and callable(f)]


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
