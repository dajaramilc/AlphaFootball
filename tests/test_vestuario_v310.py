"""v3.1.0 (sub-proyecto 2): energía, moral, correo, personalidades, clásicos, cláusulas y DT."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(13)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import energia as E
from alpha_football.models import Jugador, Equipo, alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams, _ligas_por_division


def jug(pos='MED', ovr=70, edad=25, res=50, **kw):
    j = Jugador("Test", f"J{random.randint(0, 10**6)}", pos, ovr, ovr, ovr, ovr, ovr, edad=edad,
                id=random.randint(10**6, 10**7), resistencia=res, **kw)
    return j


def test_gasto_y_recuperacion_por_resistencia():
    alto, medio, bajo = jug(res=90), jug(res=50), jug(res=30)
    assert abs(E.energia_en_minuto(alto, 90) - (100 - 0.40 * 0.6 * 90)) < 0.01      # ~78.4
    assert E.energia_en_minuto(alto, 90) > E.energia_en_minuto(medio, 90) > E.energia_en_minuto(bajo, 90)
    viejo = jug(res=50, edad=33)
    assert E.energia_en_minuto(viejo, 90) < E.energia_en_minuto(medio, 90)
    assert E.recuperacion(alto) == 15 + 0.15 * 90 and E.recuperacion(viejo) == 15 + 0.15 * 50 - 3
    medio.energia = 90; E.recuperar(medio); assert medio.energia == 100
    print("  test_gasto_y_recuperacion_por_resistencia: OK")


def test_factores_en_extremos():
    assert E.factor_energia(100) == 1.0 and E.factor_energia(70) == 1.0 and abs(E.factor_energia(0) - (1 - 125 / 600)) < 1e-9
    assert E.factor_lesion(80) == 1.0 and E.factor_lesion(0) == 3.0
    assert E.factor_moral(70) == 1.0 and abs(E.factor_moral(40) - 0.88) < 1e-9 and abs(E.factor_moral(100) - 1.12) < 1e-9
    print("  test_factores_en_extremos: OK")


def test_resistencia_por_rasgo_y_edad():
    base = E.resistencia_inicial(70, 25, None, "x")
    assert E.resistencia_inicial(70, 25, 'pulmon_de_hierro', "x") == min(99, base + 15)
    assert E.resistencia_inicial(70, 25, 'rustico', "x") == min(99, base + 8)
    assert E.resistencia_inicial(70, 25, 'regateador', "x") == max(1, base - 5)
    assert E.resistencia_inicial(70, 34, None, "x") == max(1, base - 8)
    assert E.resistencia_inicial(70, 25, None, "x") == base                          # determinista
    assert all(1 <= E.resistencia_inicial(f, 38, None, str(f)) <= 99 for f in (1, 50, 99))
    print("  test_resistencia_por_rasgo_y_edad: OK")


def test_cerrar_partido_gasta_solo_minutos_jugados():
    eq = Equipo("Prueba FC", "X", 3.0, "cruyffismo", 1_000_000, [jug(), jug(), jug()])
    a, b, c = eq.jugadores
    c.lesion_partidos, c.partidos_sancion = 2, 1
    E.cerrar_partido(eq, {a.id: 90, b.id: 30}, rng=random.Random(99))
    assert abs(a.energia - E.energia_en_minuto(jug(), 90)) < 0.01 or a.lesion_partidos > 0
    assert b.energia > a.energia                                   # sustituido en el 30' gasta menos
    assert c.energia == 100 and c.lesion_partidos == 1 and c.partidos_sancion == 0   # no jugó: descuenta
    print("  test_cerrar_partido_gasta_solo_minutos_jugados: OK")


def test_lesiones_mas_probables_con_energia_baja():
    def tasa(energia):
        n = 0
        for s in range(4000):
            j = jug(); j.energia = energia
            eq = Equipo("T", "X", 3.0, "cruyffismo", 1, [j])
            n += any(i['tipo'] == 'lesion' for i in E.cerrar_partido(eq, {j.id: 90}, rng=random.Random(s)))
        return n / 4000
    fresca, vacia = tasa(100), tasa(0)
    assert 0.006 < fresca < 0.02 and vacia > 2 * fresca, (fresca, vacia)
    print("  test_lesiones_mas_probables_con_energia_baja: OK")


def test_jugador_nuevo_y_save_viejo():
    j = Jugador("Ana", "Pulmón", "MED", 70, 70, 70, 70, 70, rasgo='pulmon_de_hierro', id=1234)
    assert 1 <= j.resistencia <= 99 and j.energia == 100 and j.personalidad in (
        'normal', 'lider', 'profesional', 'polemico', 'mercenario')
    viejo = {k: v for k, v in j.to_dict().items()
             if k not in ('resistencia', 'energia', 'personalidad', 'pide_salir', 'jornadas_moral_baja', 'notas_recientes')}
    k = Jugador.from_dict(viejo)
    assert k.resistencia == j.resistencia and k.personalidad == j.personalidad and k.energia == 100
    assert 'energia_vivo' not in j.to_dict()
    lider = Jugador("L", "Der", "DEF", 70, 70, 70, 70, 70, rasgo='lider', id=5)
    assert lider.personalidad == 'lider'
    j.energia, j.notas_recientes, j.pide_salir = 42.5, [6.0, 7.1], True
    r = Jugador.from_dict(j.to_dict())
    assert r.energia == 42.5 and r.notas_recientes == [6.0, 7.1] and r.pide_salir
    eq = Equipo("A", "X", 3.0, "cruyffismo", 1, [], rival="B")
    assert Equipo.from_dict(eq.to_dict()).rival == "B" and Equipo.from_dict({'nombre': 'Z'}).rival == ""
    print("  test_jugador_nuevo_y_save_viejo: OK")


def test_rendimiento_por_moral_y_energia():
    j = jug(ovr=70)
    base = j.poder_ataque_efectivo()
    j.moral = 40; assert abs(j.poder_ataque_efectivo() / base - 0.88) < 0.01
    j.moral = 70; j.energia = 0; assert abs(j.poder_ataque_efectivo() / base - (1 - 125 / 600)) < 0.01   # v4.4.0
    j.energia_vivo = 100; assert abs(j.poder_defensa_efectivo() / jug(ovr=70).poder_defensa_efectivo() - 1) < 0.01
    print("  test_rendimiento_por_moral_y_energia: OK")


def _liga(tipo='premier'):
    return load_league_teams(tipo)


def test_equipo_cansado_rinde_menos():
    from alpha_football import engine
    liga = _liga()
    a, b = liga.equipos[0], liga.equipos[1]
    def goles(energia_a, n=1500):                      # diferencia de gol de `a` (ataque y defensa)
        tot = 0
        for _ in range(n):
            for j in a.jugadores: j.energia = energia_a
            for j in b.jugadores: j.energia = 100
            r = engine.simular_partido(a, b, aplicar_fisico=False)
            tot += r.goles_local - r.goles_visitante
        return tot / n
    fresco, vacio = goles(100), goles(0)
    assert vacio < fresco, (fresco, vacio)
    print("  test_equipo_cansado_rinde_menos: OK")


class _SinIncidencias:
    """v4.0.0: sin tarjetas, lesiones ni cambios en el partido (estos tests miden el cierre físico
    con los 11 jugando 90'; los cambios reales se prueban en test_motor_v400)."""
    def __enter__(self):
        from alpha_football import engine
        self.prev = (engine._C_FALTA, engine.PROB_CAMBIO_IA_MIN)
        engine._C_FALTA, engine.PROB_CAMBIO_IA_MIN = -1.0, 0.0

    def __exit__(self, *a):
        from alpha_football import engine
        engine._C_FALTA, engine.PROB_CAMBIO_IA_MIN = self.prev


def test_simular_partido_gasta_energia_de_los_titulares():
    with _SinIncidencias():
        _test_simular_partido_gasta_energia_de_los_titulares()


def _test_simular_partido_gasta_energia_de_los_titulares():
    from alpha_football import engine
    liga = _liga()
    a, b = liga.equipos[0], liga.equipos[1]
    for j in a.jugadores + b.jugadores: j.energia = 100
    once = engine._once_titular(a)
    engine.simular_partido(a, b)
    assert all(j.energia < 100 or j.lesion_partidos for j in once)
    assert all(j.energia == 100 for j in a.jugadores if j not in once)
    assert all(getattr(j, 'energia_vivo', None) is None for j in a.jugadores)
    for j in a.jugadores: j.energia = 100
    engine.simular_partido(a, b, aplicar_fisico=False)
    assert all(j.energia == 100 for j in a.jugadores)
    print("  test_simular_partido_gasta_energia_de_los_titulares: OK")


def test_ia_rota_al_cansado():
    from alpha_football import engine
    eq = _liga().equipos[0]
    eq.alineacion_activa = None
    once = engine._once_titular(eq)
    estrella = max((j for j in once if j.posicion != 'POR'), key=lambda j: j.overall)
    estrella.energia = 5
    assert estrella not in engine._once_titular(eq)
    print("  test_ia_rota_al_cansado: OK")


def test_correo_basico_y_guardado():
    import json
    from alpha_football import correo as C
    e = {'temporada': 2, 'datos_carrera': {}}
    m = C.enviar(e, 'medico', "Lesión de X", "3 partidos", C.accion('team_screen', 'VER DIRECCIÓN'))
    assert m['id'] == 1 and not m['leido'] and C.no_leidos(e) == 1 and C.bandeja(e)[0] is m
    C.marcar_leido(e, 1); assert C.no_leidos(e) == 0
    for i in range(250): C.enviar(e, 'club', f"m{i}", "")
    assert len(C.bandeja(e)) == C.MAX_CORREOS and C.bandeja(e)[0]['asunto'] == 'm249'
    assert json.loads(json.dumps(e['datos_carrera']))['correo'][0]['asunto'] == 'm249'
    print("  test_correo_basico_y_guardado: OK")


def test_clasicos_reales():
    from alpha_football.data.clasicos import es_clasico, asignar_rivales
    liga = load_league_teams('laliga')
    primeras, segunda = _ligas_por_division(liga, {}, {})
    por_nombre = {e.nombre: e for l in list(primeras.values()) + list(segunda.values()) for e in l.equipos}
    assert por_nombre['Real Vadrid'].rival == 'FC Farcelona' and por_nombre['FC Farcelona'].rival == 'Real Vadrid'
    assert es_clasico(por_nombre['Patetico de Madriz'], por_nombre['Real Vadrid'])
    assert es_clasico(por_nombre['Boca Grande'], por_nombre['River Au'])
    assert not es_clasico(por_nombre['Real Vadrid'], por_nombre['Real Suciedad'])
    por_nombre['Real Vadrid'].rival = 'Gordona'                  # editado a mano: no se pisa
    asignar_rivales(list(por_nombre.values()))
    assert por_nombre['Real Vadrid'].rival == 'Gordona'
    print("  test_clasicos_reales: OK")


def _plantel(n=16, **kw):
    js = [jug(ovr=60 + i, **kw) for i in range(n)]
    for j in js: j.salario = 10**9            # sueldo alto: sin efecto de contrato
    return Equipo("Prueba FC", "X", 3.0, "cruyffismo", 1, js)


def _rep(js, nota):
    return [{'id': j.id, 'nota': nota} for j in js]


def test_moral_reglas():
    from alpha_football import vestuario as V
    eq = _plantel(); js = eq.jugadores
    for j in js: j.personalidad, j.moral = 'normal', 70
    once = js[-11:]; ids = {j.id for j in once}
    V.actualizar_moral(eq, _rep(once, 7.5), 2, 0, False, ids)
    assert all(j.moral == 75 for j in once)                   # +3 nota, +2 victoria
    assert all(j.moral == 72 for j in js[:5])                 # +2 victoria (no son top 5)
    for j in js: j.moral, j.jornadas_sin_jugar = 70, 0
    top = sorted(js, key=lambda j: -j.overall)[0]
    V.actualizar_moral(eq, _rep([j for j in once if j is not top], 6.0), 0, 0, False, ids - {top.id})
    assert top.moral == 64                                     # v4.4.0: top 5 sin jugar −3 ×2
    for j in js: j.moral, j.jornadas_sin_jugar = 70, 0
    V.actualizar_moral(eq, _rep(once, 6.0), 0, 1, True, ids)
    assert all(j.moral == 60 for j in once)                   # v4.5.0: (−1 derrota −4 clásico) ×2
    for j in js: j.moral, j.personalidad, j.jornadas_sin_jugar = 70, 'normal', 0
    once[0].personalidad = 'lider'
    V.actualizar_moral(eq, _rep(once, 6.0), 0, 1, True, ids)
    assert all(j.moral == 70 + 2 * V._mitad(V.MORAL_DERROTA + V.MORAL_CLASICO_PERDIDO) for j in once)   # líder: mitad, ×2
    j0 = js[0]; j0.moral, j0.salario, j0.personalidad = 70, 1, 'mercenario'
    V.actualizar_moral(eq, [], 0, 0, False, set())
    assert j0.moral == 62                                      # v4.4.0: sueldo bajo mercenario −4 ×2
    j0.moral, j0.notas_recientes = 80, [5.0] * 5
    j0.salario = 10**9
    V.actualizar_moral(eq, [], 0, 0, False, set())
    assert j0.moral == 76                                      # v4.4.0: mala forma −2 ×2
    j0.notas_recientes, j0.moral = [], 80
    V.actualizar_moral(eq, [], 0, 0, False, set())
    assert j0.moral == 80                                      # v4.4.0: la deriva ya no baja
    print("  test_moral_reglas: OK")


def test_pide_salir_y_polemico():
    from alpha_football import vestuario as V
    from alpha_football.salidas import revisar_curados
    eq = _plantel(); js = eq.jugadores
    for j in js: j.personalidad, j.moral = 'profesional', 70
    a, b = js[0], js[1]
    a.personalidad, b.personalidad = 'normal', 'polemico'
    salen = []
    for _ in range(6):
        a.moral = b.moral = 20
        salen += V.actualizar_moral(eq, [], 0, 0, False, set(), rng=random.Random(1))['pide_salir']
    assert b in salen and a in salen and salen.index(b) < salen.index(a)   # v4.4.0: polémico 3, normal 4
    assert any(j.moral < 70 for j in js[2:])                            # el polémico contagia
    a.moral = 55
    revisar_curados({'mi_equipo': eq, 'datos_carrera': {}})              # v4.4.0: la cura vive en salidas
    assert not a.pide_salir and not a.transferible
    print("  test_pide_salir_y_polemico: OK")


def test_desarrollo_mas_rapido_con_buena_moral():
    from alpha_football.desarrollo import desarrollar_plantilla_post_partido
    attrs = ('ataque', 'defensa', 'fisico', 'tecnica', 'mental')
    def progreso(moral):
        eq = _liga().equipos[0]
        for j in eq.jugadores:
            j.moral, j.notas_recientes, j.progreso_desarrollo, j.potencial = moral, [7.0] * 5, 0.0, 99
        antes = sum(getattr(j, a) for j in eq.jugadores for a in attrs)
        desarrollar_plantilla_post_partido(eq, 3, 0, rng=random.Random(4))
        subidas = sum(getattr(j, a) for j in eq.jugadores for a in attrs) - antes
        return sum(j.progreso_desarrollo for j in eq.jugadores) + subidas / 3   # 1.0 de progreso = +3 atributos
    assert progreso(80) > progreso(70) * 1.10
    eq = _liga().equipos[0]
    desarrollar_plantilla_post_partido(eq, 1, 0, rng=random.Random(4))
    assert all(len(j.notas_recientes) <= 5 for j in eq.jugadores)
    assert any(j.notas_recientes for j in eq.jugadores)
    print("  test_desarrollo_mas_rapido_con_buena_moral: OK")


def test_cierre_temporada_potencial():
    from alpha_football import vestuario as V
    eq = _plantel(); mi = eq
    for j in eq.jugadores: j.edad, j.moral, j.promedio_nota, j.partidos_jugados, j.potencial = 21, 80, 7.0, 10, 80
    V.cierre_temporada({'mi_equipo': mi}, rng=random.Random(2))
    subieron = [j for j in eq.jugadores if j.potencial > 80]
    assert 0 < len(subieron) < len(eq.jugadores) and all(j.potencial <= 82 for j in eq.jugadores)
    print("  test_cierre_temporada_potencial: OK")


def _estado(tipo='premier', idx=0):
    from alpha_football.ui.league_screen import inicializar_calendario_liga
    liga = load_league_teams(tipo)
    mi = liga.equipos[idx]
    mi.alineacion_activa = alineacion_por_defecto(mi)
    primeras, segunda = _ligas_por_division(liga, {}, {})
    inicializar_calendario_liga(liga)
    return {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
            'alineacion_activa': mi.alineacion_activa, 'primera_division': primeras,
            'segunda_division': segunda, 'datos_carrera': {}, 'historial': []}


def test_catastrofico_despide_sin_segunda_oportunidad():
    from alpha_football import directiva as D, correo as C
    e = _estado()
    D.definir_objetivo(e).update(pos_max=2)
    r = D.evaluar_temporada(e, len(e['liga'].equipos))          # último = desciende
    assert r['despido'] and D.calif_dt(e) == 50 - 8 - 12 - 10
    e2 = _estado()
    D.definir_objetivo(e2).update(pos_max=1)
    r2 = D.evaluar_temporada(e2, 3)                             # 2 debajo: advertencia
    # v3.2.0: la advertencia va dentro del correo de rendimiento
    assert not r2['despido'] and r2['veredicto'] == 'regano'
    assert any(m['asunto'].startswith("Evaluación de la temporada") for m in C.bandeja(e2))
    e3 = _estado(); D.definir_objetivo(e3).update(pos_max=3)
    D.evaluar_temporada(e3, 1)
    assert D.calif_dt(e3) == 50 + 8 + 10
    print("  test_catastrofico_despide_sin_segunda_oportunidad: OK")


def test_calif_escala_opciones_de_club():
    from alpha_football import directiva as D
    e = _estado()
    ovr = e['mi_equipo'].ovr_promedio
    e['datos_carrera']['calif_dt'] = 90
    alto = D.opciones_de_club(e)
    e['datos_carrera']['calif_dt'] = 10
    bajo = D.opciones_de_club(e)
    assert sum(o.ovr_promedio for o in alto) > sum(o.ovr_promedio for o in bajo)
    assert all(o.ovr_promedio >= ovr - 12 for o in alto)
    print("  test_calif_escala_opciones_de_club: OK")


def test_pedidos_de_la_directiva():
    from alpha_football import directiva as D
    e = _estado(); liga, mi = e['liga'], e['mi_equipo']
    def jugar_jornada(pts):
        p = next(p for p in liga.calendario if not p.jugado and mi.id in (p.local_id, p.visitante_id))
        p.jugado = True; mi.puntos += pts
        liga.jornada_actual = min(liga.num_jornadas, liga.jornada_actual + 1)
        D.revisar_pedido(e, rng=random.Random(3))
    jugar_jornada(3)
    p = D.pedido_activo(e)
    assert p and p['tipo'] in ('clasico', 'puntos', 'sub21')
    p.update(tipo='puntos', hasta=6, puntos_ini=mi.puntos)       # forzar el de puntos
    for pts in (3, 3, 0, 0, 3):
        jugar_jornada(pts)
    assert p['resuelto'] and p['cumplido'] and D.calif_dt(e) == 53
    # vencido sin resolver al cierre de la temporada = fallado
    e2 = _estado()
    e2['datos_carrera']['pedido'] = {'temporada': 1, 'tipo': 'clasico', 'texto': 'x', 'hasta': 99,
                                     'resuelto': False, 'creado_en': [1, 1]}
    D.cerrar_pedido_temporada(e2)
    assert e2['datos_carrera']['pedido']['resuelto'] and not e2['datos_carrera']['pedido']['cumplido']
    print("  test_pedidos_de_la_directiva: OK")


def test_pago_de_clausulas():
    from alpha_football import mercado_ia as M, correo as C
    e = _estado(); mi = e['mi_equipo']
    for j in mi.jugadores: j.clausula = 0
    barato = max(mi.jugadores, key=lambda j: j.overall)
    barato.clausula, barato.personalidad, barato.moral = 1_000_000, 'mercenario', 90
    ok = []
    for s in range(400):
        h = M.pago_clausulas(e, rng=random.Random(s))
        if h:
            assert h['jugador'] is barato and not h['rechazo']
            assert barato not in mi.jugadores and barato in h['comprador'].jugadores
            ok.append(h)
            h['comprador'].jugadores.remove(barato); mi.jugadores.append(barato)   # volver a probar
    assert 0.06 < len(ok) / 400 < 0.14, len(ok)
    assert any('cláusula' in m['asunto'].lower() for m in C.bandeja(e))
    assert any(h.get('propio') and h['monto'] == 1_000_000 for h in e['datos_carrera']['historial_pases'])
    # plantilla corta: nadie paga
    e2 = _estado(); mi2 = e2['mi_equipo']
    mi2.jugadores[:] = mi2.jugadores[:18]
    for j in mi2.jugadores: j.clausula = 1
    assert all(M.pago_clausulas(e2, rng=random.Random(s), prob=1.0) is None for s in range(20))
    print("  test_pago_de_clausulas: OK")


def test_simulacion_instantanea_aplica_vestuario():
    with _SinIncidencias():
        _test_simulacion_instantanea_aplica_vestuario()


def _test_simulacion_instantanea_aplica_vestuario():
    from alpha_football.ui import prepartido_screen
    e = _estado(); liga, mi = e['liga'], e['mi_equipo']
    liga.jornada_actual = 1
    p = next(p for p in liga.calendario if p.jornada == 1 and mi.id in (p.local_id, p.visitante_id))
    e['partido_actual'], e['match_mode'] = p, 'liga'
    local = next(x for x in liga.equipos if x.id == p.local_id)
    visit = next(x for x in liga.equipos if x.id == p.visitante_id)
    for j in mi.jugadores: j.energia = 100
    once_ids = {mi.jugadores[i].id for i in mi.alineacion_activa.titulares}
    prepartido_screen._simular_instantaneo(e, local, visit)
    gastaron = [j for j in mi.jugadores if j.id in once_ids]
    for j in gastaron:                                  # gastó 90' + adición (3-10, v4.4.0) y recuperó la jornada (tope 100)
        esperado = [min(100.0, max(0.0, 100 - E.gasto_por_minuto(j) * m) + E.recuperacion(j)) for m in (100, 90)]
        assert esperado[0] - 0.01 <= j.energia <= esperado[1] + 0.01, (j.energia, esperado)
    assert all(j.energia == 100 for j in mi.jugadores if j.id not in once_ids)
    assert len(e['datos_carrera'].get('racha', [])) == 1          # el hook de vestuario corrió una vez
    print("  test_simulacion_instantanea_aplica_vestuario: OK")


def test_amistoso_sin_consecuencias():
    from alpha_football.ui import prepartido_screen
    e = _estado(); a, b = e['liga'].equipos[0], e['liga'].equipos[1]
    e['match_mode'], e['amis_local'], e['amis_visitante'] = 'amistoso', a, b
    for j in a.jugadores + b.jugadores: j.energia, j.moral = 100, 70
    prepartido_screen._simular_instantaneo(e, a, b)
    assert all(j.energia == 100 and j.moral == 70 for j in a.jugadores + b.jugadores)
    assert not (e['datos_carrera'].get('correo'))
    print("  test_amistoso_sin_consecuencias: OK")


def test_lesion_del_user_llega_al_correo():
    from alpha_football import vestuario as V, correo as C, energia as Ener
    e = _estado(); mi, rival = e['mi_equipo'], e['liga'].equipos[1]
    orig = Ener.PROB_LESION_90
    Ener.PROB_LESION_90 = 1.0
    try:
        V.post_partido_user(e, mi, rival, 1, 0, [], {mi.jugadores[0].id: 90}, rng=random.Random(1))
    finally:
        Ener.PROB_LESION_90 = orig
    assert mi.jugadores[0].lesion_partidos > 0
    assert any(x['remitente'] == 'medico' and x['accion']['pantalla'] == 'team_screen' for x in C.bandeja(e))
    print("  test_lesion_del_user_llega_al_correo: OK")


def test_pantallas_v310():
    from alpha_football.ui import correo_screen, league_screen, plantilla_screen, objetivos_screen
    from alpha_football import correo as C
    assert league_screen.TARJETAS['oficina'][0][2] == 'correo_screen'
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'main.py'), encoding='utf-8').read()
    assert "'correo_screen': 'alpha_football.ui.correo_screen'" in src   # v3.6.0: MODULOS_PANTALLA
    e = _estado()
    C.enviar(e, 'medico', "Lesión: X", "2 partidos", C.accion('team_screen', "VER DIRECCIÓN DE EQUIPO"))
    pygame.event.clear()
    assert correo_screen.render(screen, e) is None and C.no_leidos(e) == 0     # abrir = leído (el 1º)
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=correo_screen._rect_accion().center))
    assert correo_screen.render(screen, e) == 'team_screen' and e['team_contexto'] == 'carrera'
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode=''))
    assert correo_screen.render(screen, e) == 'league_screen'
    C.enviar(e, 'club', "Oferta", "")
    assert any('correo' in t.lower() for t, _c in league_screen._alertas_inicio(e, e['mi_equipo']))
    for mod in (plantilla_screen, objetivos_screen):
        pygame.event.clear(); assert mod.render(screen, e) is None
    print("  test_pantallas_v310: OK")


def test_final_titular_no_disponible_no_juega_en_vivo():
    from alpha_football.ui import match_screen
    from alpha_football import formaciones as F
    e = _estado(); mi = e['mi_equipo']; alin = mi.alineacion_activa
    js = mi.jugadores
    lesionado, sancionado = js[alin.titulares[3]], js[alin.titulares[5]]
    lesionado.lesion_partidos, sancionado.partidos_sancion = 2, 1
    match_screen._depurar_titulares(mi, alin)
    en_cancha = [js[i] for i in alin.titulares]
    assert len(en_cancha) == 11 and lesionado not in en_cancha and sancionado not in en_cancha
    assert all(j.disponible for j in en_cancha)
    assert all(js[i].partidos_sancion <= 0 for i in F.mejor_once(js, '4-3-3'))      # AUTO ONCE sin sancionados
    print("  test_final_titular_no_disponible_no_juega_en_vivo: OK")


def test_final_ids_duplicados_no_cruzan_energia():
    with _SinIncidencias():
        _test_final_ids_duplicados_no_cruzan_energia()


def _test_final_ids_duplicados_no_cruzan_energia():
    from alpha_football import engine
    from alpha_football.models import asegurar_ids_unicos
    liga = _liga(); a, b = liga.equipos[0], liga.equipos[1]
    for j in a.jugadores: j.id, j.energia = 0, 100          # como los reemplazos generados (id 0)
    once = engine._once_titular(a)
    engine.simular_partido(a, b)
    assert all(j.energia == 100 for j in a.jugadores if j not in once), "un suplente con id repetido gastó energía"
    assert len({j.id for j in a.jugadores}) == len(a.jugadores)
    eq = Equipo("X", "X", 3.0, "cruyffismo", 1, [jug(), jug(), jug()])
    eq.jugadores[1].id = eq.jugadores[2].id = eq.jugadores[0].id
    asegurar_ids_unicos(eq)
    assert len({j.id for j in eq.jugadores}) == 3
    print("  test_final_ids_duplicados_no_cruzan_energia: OK")


def test_final_clausula_de_portero_repone_plantilla():
    from alpha_football import mercado_ia as M
    e = _estado(); mi = e['mi_equipo']
    porteros = [j for j in mi.jugadores if j.posicion == 'POR']
    for j in mi.jugadores: j.clausula = 0
    for j in porteros[2:]: mi.jugadores.remove(j)              # quedan exactamente 2 porteros
    assert len(mi.jugadores) > 18
    p0 = next(j for j in mi.jugadores if j.posicion == 'POR')
    p0.clausula, p0.personalidad = 1_000_000, 'mercenario'
    h = M.pago_clausulas(e, rng=random.Random(0), prob=1.0)
    assert h and h['jugador'] is p0, h
    assert sum(1 for j in mi.jugadores if j.posicion == 'POR') >= 2
    print("  test_final_clausula_de_portero_repone_plantilla: OK")


def test_final_energia_llena_en_nueva_temporada():
    from alpha_football.ui.resumen_temporada_screen import avanzar_nueva_temporada
    e = _estado()
    for eq in e['liga'].equipos:
        for j in eq.jugadores: j.energia = 20
    avanzar_nueva_temporada(e)
    assert all(j.energia == 100 for eq in e['liga'].equipos for j in eq.jugadores)
    print("  test_final_energia_llena_en_nueva_temporada: OK")


def test_ajuste_no_castiga_al_que_no_podia_jugar():
    from alpha_football import vestuario as V
    e = _estado(); mi, rival = e['mi_equipo'], e['liga'].equipos[1]
    top = max(mi.jugadores, key=lambda j: j.overall)
    for j in mi.jugadores: j.moral, j.salario, j.notas_recientes = 70, 10**9, []
    top.lesion_partidos = 1                                   # cumple su último partido de lesión
    otros = {j.id: 90 for j in mi.jugadores if j is not top}
    V.post_partido_user(e, mi, rival, 0, 0, [], otros, rng=random.Random(1))
    assert top.lesion_partidos == 0 and top.moral == 70, top.moral
    print("  test_ajuste_no_castiga_al_que_no_podia_jugar: OK")


def test_ajuste_bonus_potencial_llega_al_correo():
    from alpha_football import vestuario as V, correo as C
    e = _estado(); mi = e['mi_equipo']
    for j in mi.jugadores: j.edad, j.moral, j.promedio_nota, j.partidos_jugados, j.potencial = 21, 80, 7.0, 10, 80
    textos = V.cierre_temporada(e, rng=random.Random(2))
    assert textos and any('potencial' in m['asunto'].lower() for m in C.bandeja(e))
    assert all(t.split(' +')[0] in C.bandeja(e)[0]['cuerpo'] for t in textos)
    print("  test_ajuste_bonus_potencial_llega_al_correo: OK")


def test_ajuste_venta_borra_pide_salir():
    from alpha_football.ui.ofertas_screen import _aceptar
    e = _estado(); mi, comp = e['mi_equipo'], e['liga'].equipos[1]
    j = mi.jugadores[-1]; j.pide_salir = True
    _aceptar(e, {'jugador': j, 'comprador': comp, 'monto': 1_000_000})
    assert j in comp.jugadores and not j.pide_salir
    print("  test_ajuste_venta_borra_pide_salir: OK")


def test_ajuste_racha_no_pasa_al_club_nuevo_y_pedido_en_partidos():
    from alpha_football import directiva as D
    from alpha_football.ui import objetivos_screen
    e = _estado()
    e['datos_carrera']['racha'] = ['P', 'P']
    D.cambiar_de_club(e, D.opciones_de_club(e)[0])
    assert not e['datos_carrera'].get('racha')
    assert objetivos_screen.texto_pedido({'texto': 'Sumar 8 puntos', 'hasta': 6}, 2) ==         "Pedido: Sumar 8 puntos (quedan 4 partidos)"
    print("  test_ajuste_racha_no_pasa_al_club_nuevo_y_pedido_en_partidos: OK")


TESTS = [test_gasto_y_recuperacion_por_resistencia, test_factores_en_extremos, test_resistencia_por_rasgo_y_edad,
         test_cerrar_partido_gasta_solo_minutos_jugados, test_lesiones_mas_probables_con_energia_baja,
         test_jugador_nuevo_y_save_viejo, test_rendimiento_por_moral_y_energia,
         test_equipo_cansado_rinde_menos, test_simular_partido_gasta_energia_de_los_titulares, test_ia_rota_al_cansado,
         test_correo_basico_y_guardado, test_clasicos_reales,
         test_moral_reglas, test_pide_salir_y_polemico, test_desarrollo_mas_rapido_con_buena_moral,
         test_cierre_temporada_potencial, test_catastrofico_despide_sin_segunda_oportunidad,
         test_calif_escala_opciones_de_club, test_pedidos_de_la_directiva,
         test_pago_de_clausulas, test_simulacion_instantanea_aplica_vestuario, test_amistoso_sin_consecuencias,
         test_lesion_del_user_llega_al_correo, test_pantallas_v310,
         test_final_titular_no_disponible_no_juega_en_vivo, test_final_ids_duplicados_no_cruzan_energia,
         test_final_clausula_de_portero_repone_plantilla, test_final_energia_llena_en_nueva_temporada,
         test_ajuste_no_castiga_al_que_no_podia_jugar, test_ajuste_bonus_potencial_llega_al_correo,
         test_ajuste_venta_borra_pide_salir, test_ajuste_racha_no_pasa_al_club_nuevo_y_pedido_en_partidos]


if __name__ == '__main__':
    fail = 0
    for t in TESTS:
        try:
            t()
        except Exception as ex:
            fail += 1
            import traceback; traceback.print_exc()
            print(f"  {t.__name__}: FAIL - {ex}")
    print(f"{len(TESTS) - fail}/{len(TESTS)} tests pasaron")
    sys.exit(1 if fail else 0)
