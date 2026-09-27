"""Objetivos por secciones: Marca, Juveniles, ofertas de DT (sesión 2026-09-26)."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(5)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save, correo as C, directiva as D, finanzas as F
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402


def test_valor_club():
    e = estado_carrera(); mi = e['mi_equipo']
    mi.balance = 1_000_000
    for j in mi.jugadores:
        j.valor = 2_000_000
    assert F.valor_club(mi) == 2_000_000 * len(mi.jugadores) + 1_000_000
    print("  test_valor_club: OK")


def _edades(e, edad):
    for j in e['mi_equipo'].jugadores:
        j.edad = edad


def test_marca_valor_y_estrella():
    e = estado_carrera(); mi = e['mi_equipo']
    D._dc(e).pop('objetivo_marca', None)
    om = D.definir_objetivo_marca(e, random.Random(1))
    assert om['tipo'] in ('valor', 'estrella')
    if om['tipo'] == 'valor':
        assert om['meta'] == int(F.valor_club(mi) * 1.10)
    else:
        assert om['meta'] == round(mi.ovr_promedio) + 5
    assert D.definir_objetivo_marca(e) is om          # se fija una vez por temporada
    print("  test_marca_valor_y_estrella: OK")


def test_juveniles_edad_alta_y_normal():
    e = estado_carrera(); _edades(e, 30)
    oj = D.definir_objetivo_juveniles(e, random.Random(1))
    assert oj['tipo'] == 'edad' and oj['meta'] == 29.0
    e = estado_carrera(); _edades(e, 24)
    oj = D.definir_objetivo_juveniles(e, random.Random(1))
    assert oj['tipo'] in ('partidos_u21', 'fichar_joven')
    if oj['tipo'] == 'partidos_u21':
        assert oj['meta'] >= 10
    print("  test_juveniles_edad_alta_y_normal: OK")


def test_estrella_se_cumple_con_fichaje_y_queda_cumplido():
    e = estado_carrera(); mi = e['mi_equipo']
    nuevo = max(e['liga'].equipos[3].jugadores, key=lambda j: j.overall)   # overall es propiedad calculada
    om = D._dc(e)['objetivo_marca'] = {'temporada': 1, 'club': mi.nombre, 'tipo': 'estrella',
                                      'meta': nuevo.overall, 'texto': 'Fichar un jugador de media alta',
                                      'ids_inicio': [j.id for j in mi.jugadores], 'cumplido': False}
    assert not D.cumplido_secundario(e, om)
    mi.jugadores.append(nuevo)
    D.revisar_objetivos_secundarios(e)
    assert om['cumplido'] and any('Objetivo cumplido' in m['asunto'] for m in C.bandeja(e))
    mi.jugadores.remove(nuevo)                          # venderlo no borra el cumplido
    D.revisar_objetivos_secundarios(e)
    assert om['cumplido']
    n = sum('Objetivo cumplido' in m['asunto'] for m in C.bandeja(e))
    D.revisar_objetivos_secundarios(e)
    assert sum('Objetivo cumplido' in m['asunto'] for m in C.bandeja(e)) == n   # un solo aviso
    print("  test_estrella_se_cumple_con_fichaje_y_queda_cumplido: OK")


def test_fichar_joven_y_edad_y_partidos():
    e = estado_carrera(); mi = e['mi_equipo']
    ids = [j.id for j in mi.jugadores]
    base = {'temporada': 1, 'club': mi.nombre, 'ids_inicio': ids, 'cumplido': False, 'texto': 'x'}
    joven = e['liga'].equipos[3].jugadores[0]; joven.edad = 19
    oj = dict(base, tipo='fichar_joven', meta=21)
    assert not D.cumplido_secundario(e, oj)
    mi.jugadores.append(joven)
    assert D.cumplido_secundario(e, oj)
    _edades(e, 30)
    oj = dict(base, tipo='edad', meta=29.0, edad_inicio=30.0)
    assert not D.cumplido_secundario(e, oj) and D.progreso_secundario(e, oj) == 0.0
    _edades(e, 28)
    assert D.cumplido_secundario(e, oj) and D.progreso_secundario(e, oj) == 1.0
    for j in mi.jugadores:
        j.edad, j.partidos_jugados = 20, 0
    oj = dict(base, tipo='partidos_u21', meta=10)
    assert D.progreso_secundario(e, oj) == 0.0
    mi.jugadores[0].partidos_jugados = 10
    assert D.cumplido_secundario(e, oj)
    print("  test_fichar_joven_y_edad_y_partidos: OK")


def test_cierre_calificacion_y_correo():
    e = estado_carrera(); mi = e['mi_equipo']
    D.definir_objetivo(e)
    D._dc(e)['objetivo_marca'] = {'temporada': 1, 'club': mi.nombre, 'tipo': 'estrella', 'meta': 999,
                                  'texto': 'Fichar un jugador de media 999 o más', 'ids_inicio': [], 'cumplido': True}
    D._dc(e)['objetivo_juveniles'] = {'temporada': 1, 'club': mi.nombre, 'tipo': 'fichar_joven', 'meta': 21,
                                      'texto': 'Fichar un jugador de 21 años o menos',
                                      'ids_inicio': [j.id for j in mi.jugadores], 'cumplido': False}
    antes = D.calif_dt(e)
    ev_m = D.evaluar_objetivo_secundario(e, 'objetivo_marca', 1)
    ev_j = D.evaluar_objetivo_secundario(e, 'objetivo_juveniles', 1)
    assert ev_m['resultado'] == 'cumplido' and ev_j['resultado'] == 'fallado'
    assert D.calif_dt(e) == antes + 4 - 3
    txt = D.texto_evaluacion({'posicion': 1, 'resultado': 'cumplido', 'texto': 't', 'marca': ev_m, 'juveniles': ev_j})
    assert 'Marca:' in txt and 'Juveniles:' in txt
    print("  test_cierre_calificacion_y_correo: OK")


def test_cambiar_de_club_refija_marca_y_juveniles():
    e = estado_carrera()
    D.definir_objetivo_marca(e); D.definir_objetivo_juveniles(e)
    nuevo = e['liga'].equipos[2]
    D.cambiar_de_club(e, nuevo)
    om = D.definir_objetivo_marca(e)
    assert om['club'] == nuevo.nombre and set(om['ids_inicio']) == {j.id for j in nuevo.jugadores}
    print("  test_cambiar_de_club_refija_marca_y_juveniles: OK")


def test_correos_de_oferta_dicen_por_que():
    from alpha_football import entrenadores as EN, ofertas_dt as O
    e = estado_carrera(); liga = e['liga']; eq = liga.equipos[3]
    D._dc(e)['calif_dt'] = 62
    EN._ofrecer_al_user(e, eq, liga, "iba 7º y se esperaba 3º")
    m = C.bandeja(e)[0]
    assert 'iba 7º' in m['cuerpo'] and '62/100' in m['cuerpo'] and m['accion']['pantalla'] == 'ofertas_dt_screen'
    assert EN.ofertas_activas(e)[0]['motivo'] == "iba 7º y se esperaba 3º"
    e = estado_carrera(); D.definir_objetivo(e); D._dc(e)['calif_dt'] = 55   # banda de medias parecidas
    orig = D._jugadas
    try:
        D._jugadas = lambda l, m: 3
        azar = random.Random(7); azar.random = lambda: 0.0
        O.revisar_jornada(e, azar)
    finally:
        D._jugadas = orig
    m = C.bandeja(e)[0]
    assert '55/100' in m['cuerpo'] and m['accion']['pantalla'] == 'ofertas_dt_screen'
    print("  test_correos_de_oferta_dicen_por_que: OK")


def test_oferta_por_calif_en_ofertas_dt_screen():
    from alpha_football.ui import ofertas_dt_screen as S
    from alpha_football import ofertas_dt as O
    e = estado_carrera(); D.definir_objetivo(e); otro = e['liga'].equipos[3]
    D._dc(e)['oferta_dt'] = {'club_id': otro.id, 'club': otro.nombre, 'liga': e['liga'].nombre,
                             'media': 70.0, 'temporada': 1, 'vence': 99}
    fs = S.filas(e)
    assert fs[0]['origen'] == 'calif' and 'calificación' in fs[0]['motivo'].lower()
    pygame.event.clear(); assert S.render(screen, e) is None
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=S.rect_rechazar(0).center))
    S.render(screen, e)
    assert O.oferta_vigente(e) is None
    D._dc(e)['oferta_dt'] = {'club_id': otro.id, 'club': otro.nombre, 'liga': e['liga'].nombre,
                             'media': 70.0, 'temporada': 1, 'vence': 99}
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=S.rect_aceptar(0).center))
    assert S.render(screen, e) == 'contrato_dt_screen' and e.get('contrato_modo') == 'alta'
    print("  test_oferta_por_calif_en_ofertas_dt_screen: OK")


def test_pantalla_objetivos_por_secciones():
    from alpha_football.ui import objetivos_screen as O
    from alpha_football.ui import ayuda
    e = estado_carrera(); D.definir_objetivo(e)
    textos, orig = [], O.draw_text
    O.draw_text = lambda s, t, *a, **k: textos.append(str(t))
    try:
        pygame.event.clear(); assert O.render(screen, e) is None
    finally:
        O.draw_text = orig
    for s in ("LOCAL", "INTERNACIONAL", "FINANZAS", "MARCA", "JUVENILES", "CALIFICACIÓN DE DT"):
        assert any(s in t for t in textos), s
    assert not any("HISTORIAL" in t for t in textos) and not any("OFERTA" in t for t in textos)
    assert not hasattr(O, 'R_HIST') and not hasattr(O, 'R_VER_OFERTA')
    assert len(ayuda.AYUDA['objetivos_screen'](e)) == 8
    print("  test_pantalla_objetivos_por_secciones: OK")


def test_valor_no_lo_cumplen_premios_de_cierre_ni_espaldarazo():
    e = estado_carrera(); mi = e['mi_equipo']; D.definir_objetivo(e)
    om = D._dc(e)['objetivo_marca'] = {'temporada': 1, 'club': mi.nombre, 'tipo': 'valor',
                                       'meta': F.valor_club(mi) + 1_000_000, 'texto': 'x',
                                       'ids_inicio': [j.id for j in mi.jugadores], 'cumplido': False}
    D._dc(e)['objetivo']['espaldarazo'] = {'pct': 0.3, 'puestos': 2, 'deuda': 5_000_000}
    mi.balance += 2_000_000                      # entra el aporte: no cuenta mientras sea deuda
    assert not D.cumplido_secundario(e, om)
    mi.balance += 50_000_000                     # premio de liga al cierre, después de la última jornada
    assert D.evaluar_objetivo_secundario(e, 'objetivo_marca', 1)['resultado'] == 'fallado'
    om['cumplido'] = True                        # se cumplió durante la temporada
    assert D.evaluar_objetivo_secundario(e, 'objetivo_marca', 1)['resultado'] == 'cumplido'
    print("  test_valor_no_lo_cumplen_premios_de_cierre_ni_espaldarazo: OK")


def test_valor_negativo_elige_estrella():
    e = estado_carrera(); mi = e['mi_equipo']
    mi.balance = -10 ** 11
    azar = random.Random(1); azar.random = lambda: 0.0      # forzaría 'valor'
    assert D.definir_objetivo_marca(e, azar)['tipo'] == 'estrella'
    print("  test_valor_negativo_elige_estrella: OK")


def test_vuelta_de_prestamo_no_es_fichaje():
    from alpha_football import prestamos as P
    e = estado_carrera(); mi = e['mi_equipo']; club = e['liga'].equipos[4]
    e['liga'].jornada_actual = 1
    j = sorted(mi.jugadores, key=lambda x: x.overall)[0]
    P.iniciar(e, j, mi, club, 6, 50)
    assert j not in mi.jugadores                       # cedido antes de fijar las metas
    D._dc(e).pop('objetivo_juveniles', None)
    oj = D.definir_objetivo_juveniles(e, random.Random(1))
    oj.update(tipo='fichar_joven', meta=99, cumplido=False)     # cualquier "nuevo" lo cumpliría
    club.jugadores.remove(j); mi.jugadores.append(j); j.prestamo = None   # vuelve del préstamo
    assert not D.cumplido_secundario(e, oj)
    print("  test_vuelta_de_prestamo_no_es_fichaje: OK")


def test_ofertas_dt_muestra_objetivo_y_presupuesto():
    from alpha_football.ui import ofertas_dt_screen as S
    e = estado_carrera(); D.definir_objetivo(e); liga = e['liga']; otro = liga.equipos[3]
    D._dc(e)['oferta_dt'] = {'club_id': otro.id, 'club': otro.nombre, 'liga': liga.nombre, 'media': 70.0,
                             'temporada': 1, 'vence': 99, 'objetivo': 'No descender', 'presupuesto': 12_000_000}
    from alpha_football import entrenadores as EN
    EN._ofrecer_al_user(e, liga.equipos[5], liga, "iba 7º y se esperaba 3º")
    fs = S.filas(e)
    assert 'No descender' in fs[0]['detalle'] and '$12.0M' in fs[0]['detalle']
    assert 'Objetivo:' in fs[1]['detalle'] and 'Presupuesto:' in fs[1]['detalle']
    textos, orig = [], S.draw_text
    S.draw_text = lambda s, t, *a, **k: textos.append(str(t))
    try:
        pygame.event.clear(); S.render(screen, e)
    finally:
        S.draw_text = orig
    assert sum('Objetivo:' in t for t in textos) == 2
    print("  test_ofertas_dt_muestra_objetivo_y_presupuesto: OK")


TESTS = [test_vuelta_de_prestamo_no_es_fichaje, test_ofertas_dt_muestra_objetivo_y_presupuesto,
         test_valor_no_lo_cumplen_premios_de_cierre_ni_espaldarazo,test_valor_negativo_elige_estrella,
         test_pantalla_objetivos_por_secciones,test_valor_club, test_marca_valor_y_estrella, test_juveniles_edad_alta_y_normal,
         test_estrella_se_cumple_con_fichaje_y_queda_cumplido, test_fichar_joven_y_edad_y_partidos,
         test_cierre_calificacion_y_correo, test_cambiar_de_club_refija_marca_y_juveniles,
         test_correos_de_oferta_dicen_por_que, test_oferta_por_calif_en_ofertas_dt_screen]


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
