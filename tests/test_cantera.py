"""Cantera v4.8.0: generación, renovación, subir/liberar, IA, pantalla."""
import sys, os, random, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(48)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save, cantera as K, correo as C, market as M
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402


def test_generar_canterano_rangos():
    e = estado_carrera(); mi = e['mi_equipo']; nivel = M.nivel_club(mi)
    rng = random.Random(1)
    for _ in range(40):
        j = K.generar_canterano(e, mi, rng)
        assert 15 <= j.edad <= 18 and not j.joya
        assert max(40, nivel - 28) <= j.overall <= max(40, nivel - 18)
        assert j.overall + 10 <= j.potencial <= min(99, j.overall + 20)           # v0.4.18.0: mínimo 10 (antes 8)
        assert j.posicion in ('POR', 'DEF', 'MED', 'DEL')
    joya = K.generar_canterano(e, mi, rng, joya=True)
    assert joya.joya and 16 <= joya.edad <= 18 and nivel - 4 <= joya.overall <= nivel
    assert joya.overall + 10 <= joya.potencial <= min(99, joya.overall + 14)      # v0.4.18.0: antes +5 a +12
    ids = {K.generar_canterano(e, mi, rng).id for _ in range(5)}
    assert len(ids) == 5                                   # ids únicos (contador regen_id)
    print("  test_generar_canterano_rangos: OK")


def test_cantera_inicial_y_guardado():
    e = estado_carrera()
    lista = K.cantera(e)
    assert len(lista) == K.TAMANO_INICIAL
    assert [j.id for j in K.cantera(e)] == [j.id for j in lista]      # estable entre llamadas
    dc = e['datos_carrera']
    assert dc['cantera_club'] == e['mi_equipo'].nombre and dc['cantera_ultima'] == K._hito(e)
    e['datos_carrera'] = json.loads(json.dumps(dc))                    # ida y vuelta como el guardado
    assert [(j.id, j.overall, j.potencial) for j in K.cantera(e)] == [(j.id, j.overall, j.potencial) for j in lista]
    print("  test_cantera_inicial_y_guardado: OK")


def test_cantera_corrupta_y_cambio_de_club():
    e = estado_carrera()
    for basura in ("texto", [{'foo': 1}], [1, 2], None):
        e['datos_carrera']['cantera'] = basura
        assert len(K.cantera(e)) == K.TAMANO_INICIAL
    ids = {j.id for j in K.cantera(e)}
    e['mi_equipo'] = e['liga'].equipos[1]                              # el DT cambió de club
    nuevos = K.cantera(e)
    assert len(nuevos) == K.TAMANO_INICIAL and not ids & {j.id for j in nuevos}
    assert e['datos_carrera']['cantera_club'] == e['mi_equipo'].nombre
    K._guardar(e, [])                                                  # vacía a propósito: no se regenera
    assert K.cantera(e) == []
    print("  test_cantera_corrupta_y_cambio_de_club: OK")


def _mitad(e):
    return max(2, int(e['liga'].num_jornadas) // 2)


def test_renovar_crecen_llegan_y_topes():
    e = estado_carrera(); e['liga'].jornada_actual = _mitad(e)         # mitad: no cumplen años
    antes = {j.id: (j.overall, j.potencial, j.edad) for j in K.cantera(e)}
    res = K.renovar(e, random.Random(3))
    ahora = K.cantera(e)
    assert K.TAMANO_MIN <= len(ahora) <= K.TAMANO_MAX
    assert len(res['llegan']) >= 2
    for j in ahora:
        if j.id in antes:
            ovr0, pot0, edad0 = antes[j.id]
            # v0.4.18.0: sube de +2 a +5 y el potencial sube con la media (siempre a 10 o más)
            assert 2 <= j.overall - ovr0 <= 5 and j.potencial - pot0 == j.overall - ovr0 and j.edad == edad0
            assert j.potencial - j.overall >= 10
    idos = {j.id for j, _m in res['se_van']}
    assert idos <= set(antes) and not idos & {j.id for j in ahora}
    for _ in range(12):                                                # nunca se sale de los topes
        K.renovar(e, random.Random())
        assert K.TAMANO_MIN <= len(K.cantera(e)) <= K.TAMANO_MAX
    print("  test_renovar_crecen_llegan_y_topes: OK")


def test_renovar_inicio_cumplen_anios_y_se_van_por_edad():
    e = estado_carrera()
    lista = K.cantera(e)
    for j in lista:
        j.edad = 19
    K._guardar(e, lista)
    viejos = {j.id for j in lista}
    e['temporada'], e['liga'].jornada_actual = 2, 1                    # inicio: +1 año → 20 → se van
    res = K.renovar(e, random.Random(4))
    assert {j.id for j, m in res['se_van'] if m == 'edad'} == viejos
    ahora = K.cantera(e)
    assert len(ahora) >= K.TAMANO_MIN and not viejos & {j.id for j in ahora}
    print("  test_renovar_inicio_cumplen_anios_y_se_van_por_edad: OK")


def test_joya_forzada_y_no_se_va_por_azar():
    e = estado_carrera(); mi = e['mi_equipo']; e['liga'].jornada_actual = _mitad(e)
    K.cantera(e)
    prob = K.PROB_JOYA_USER
    try:
        K.PROB_JOYA_USER = 1.0
        res = K.renovar(e, random.Random(5))
        joya = res['joya']
        nivel = M.nivel_club(mi)
        assert joya is not None and joya.joya and nivel - 4 <= joya.overall <= nivel
        assert sum(1 for j in res['llegan'] if j.joya) == 1            # máximo una por renovación
        K.PROB_JOYA_USER = 0.0
        for _ in range(10):
            assert K.renovar(e, random.Random())['joya'] is None
            assert joya.id in {j.id for j in K.cantera(e)}             # solo se va por edad
    finally:
        K.PROB_JOYA_USER = prob
    print("  test_joya_forzada_y_no_se_va_por_azar: OK")


def test_revisar_jornada_hitos():
    e = estado_carrera(); e['liga'].jornada_actual = 1
    assert K.revisar_jornada(e) is None                                # partida nueva/vieja: crea, no renueva
    assert not [m for m in C.bandeja(e) if m['remitente'] == 'cantera']
    e['liga'].jornada_actual = _mitad(e)
    res = K.revisar_jornada(e, random.Random(6))
    assert res is not None and e['datos_carrera']['cantera_ultima'] == "1-mitad"
    correos = [m for m in C.bandeja(e) if m['remitente'] == 'cantera']
    assert len(correos) == 1 and correos[0]['accion']['pantalla'] == 'cantera_screen'
    assert "Coordinación de cantera" in C.formatear(e, correos[0])
    e['liga'].jornada_actual += 1
    assert K.revisar_jornada(e) is None                                # no repite en la misma mitad
    e['temporada'], e['liga'].jornada_actual = 2, 1
    assert K.revisar_jornada(e, random.Random(7)) is not None          # inicio de la temporada siguiente
    assert len([m for m in C.bandeja(e) if m['remitente'] == 'cantera']) == 2
    print("  test_revisar_jornada_hitos: OK")


def test_correo_de_joya():
    e = estado_carrera(); e['liga'].jornada_actual = 1
    K.cantera(e); e['liga'].jornada_actual = _mitad(e)
    prob = K.PROB_JOYA_USER
    try:
        K.PROB_JOYA_USER = 1.0
        res = K.revisar_jornada(e, random.Random(8))
    finally:
        K.PROB_JOYA_USER = prob
    msg = next(m for m in C.bandeja(e) if m['remitente'] == 'cantera')
    assert msg['asunto'].startswith("Una joya en la cantera") and res['joya'].apellido in msg['cuerpo']
    assert K.proximo_informe(e) == "inicio de la próxima temporada"
    e['liga'].jornada_actual = 1
    from datetime import date                                              # v0.4.13.0: la mitad es una fecha
    from alpha_football import calendario as CAL
    assert K.proximo_informe(e) == CAL.texto_fecha(date(2027, 1, 1), False)
    print("  test_correo_de_joya: OK")


def test_subir_al_primer_equipo():
    e = estado_carrera(); mi = e['mi_equipo']
    j = K.cantera(e)[0]; n = len(mi.jugadores)
    ok, msg = K.subir(e, j.id)
    assert ok and j.apellido in msg
    nuevo = mi.jugadores[-1]
    assert len(mi.jugadores) == n + 1 and nuevo.id == j.id and not nuevo.joya
    assert nuevo.salario > 0 and nuevo.contrato_anios >= 2 and nuevo.valor > 0
    assert j.id not in {x.id for x in K.cantera(e)} and len(K.cantera(e)) == K.TAMANO_INICIAL - 1
    ok, _msg = K.subir(e, j.id)                                        # ya no está en la cantera
    assert not ok and len(mi.jugadores) == n + 1
    print("  test_subir_al_primer_equipo: OK")


def test_subir_plantilla_llena():
    e = estado_carrera(); mi = e['mi_equipo']
    j = K.cantera(e)[0]; tope = M.PLANTILLA_MAXIMA
    try:
        M.PLANTILLA_MAXIMA = len(mi.jugadores)
        ok, msg = K.subir(e, j.id)
    finally:
        M.PLANTILLA_MAXIMA = tope
    assert not ok and "llena" in msg
    assert j.id in {x.id for x in K.cantera(e)}                        # no se pierde
    print("  test_subir_plantilla_llena: OK")


def test_liberar():
    e = estado_carrera()
    j = K.cantera(e)[0]
    assert K.liberar(e, j.id) is True
    assert j.id not in {x.id for x in K.cantera(e)}
    assert K.liberar(e, j.id) is False
    print("  test_liberar: OK")


def test_subir_cumple_objetivo_fichar_joven():
    from alpha_football import directiva as D
    e = estado_carrera(); mi = e['mi_equipo']
    oj = D._dc(e)['objetivo_juveniles'] = {'temporada': 1, 'club': mi.nombre, 'tipo': 'fichar_joven', 'meta': 21,
                                           'texto': "Fichar un jugador de 21 años o menos",
                                           'ids_inicio': [j.id for j in mi.jugadores], 'cumplido': False}
    for j in mi.jugadores:
        j.edad = max(j.edad, 22)
    assert not D.cumplido_secundario(e, oj)
    K.subir(e, K.cantera(e)[0].id)
    assert D.cumplido_secundario(e, oj)
    print("  test_subir_cumple_objetivo_fichar_joven: OK")


def _clubes_ia(e):
    from alpha_football.mercado_ia import ligas_de_la_partida
    return [eq for liga, _t, _d in ligas_de_la_partida(e) for eq in liga.equipos if eq is not e['mi_equipo']]


def test_ia_sube_canteranos():
    from alpha_football import mercado_ia as MI
    e = estado_carrera(); mi = e['mi_equipo']
    clubes = _clubes_ia(e)
    antes = {id(eq): len(eq.jugadores) for eq in clubes}
    por_pos = {id(eq): {p for p in ('POR', 'DEF', 'MED', 'DEL') if any(j.posicion == p for j in eq.jugadores)}
               for eq in clubes}
    n_mi = len(mi.jugadores)
    p_c, p_j = K.PROB_CANTERANO_IA, K.PROB_JOYA_IA
    try:
        K.PROB_CANTERANO_IA, K.PROB_JOYA_IA = 1.0, 0.0
        altas = K.renovar_ia(e, random.Random(9))
    finally:
        K.PROB_CANTERANO_IA, K.PROB_JOYA_IA = p_c, p_j
    assert len(mi.jugadores) == n_mi                                   # al user no lo toca
    assert altas and not any(a['joya'] for a in altas)
    for eq in clubes:
        esperado = antes[id(eq)] + 1 if antes[id(eq)] < MI.PLANTILLA_MAX_IA else antes[id(eq)]
        assert antes[id(eq)] <= len(eq.jugadores) <= esperado and len(eq.jugadores) <= max(antes[id(eq)], MI.PLANTILLA_MAX_IA)
        assert por_pos[id(eq)] <= {j.posicion for j in eq.jugadores}   # no pierde ninguna posición
    assert all(not j.joya for eq in clubes for j in eq.jugadores)
    print("  test_ia_sube_canteranos: OK")


def test_ia_probabilidad_cero_y_joya_en_prensa():
    e = estado_carrera()
    clubes = _clubes_ia(e)
    antes = sum(len(eq.jugadores) for eq in clubes)
    p_c, p_j = K.PROB_CANTERANO_IA, K.PROB_JOYA_IA
    try:
        K.PROB_CANTERANO_IA, K.PROB_JOYA_IA = 0.0, 0.0
        assert K.renovar_ia(e, random.Random(10)) == []
        assert sum(len(eq.jugadores) for eq in clubes) == antes
        K.PROB_JOYA_IA = 1.0
        altas = K.renovar_ia(e, random.Random(11))
    finally:
        K.PROB_CANTERANO_IA, K.PROB_JOYA_IA = p_c, p_j
    assert altas and all(a['joya'] for a in altas)
    rivales = {eq.nombre for eq in e['liga'].equipos if eq is not e['mi_equipo']}
    from alpha_football import noticias as NO
    joyas = [n for n in NO.lista(e) if n['tipo'] == 'cantera']       # v0.4.23.0: noticia, ya no correo de Prensa
    assert joyas and len(joyas) == sum(1 for a in altas if a['club'] in rivales)   # solo los de tu liga
    assert all(n['importancia'] == 3 and n['categoria'] == 'promesa' and len(n['equipos_ids']) == 1 for n in joyas)
    assert not [m for m in C.bandeja(e) if m['remitente'] == 'prensa']
    print("  test_ia_probabilidad_cero_y_joya_en_prensa: OK")


def test_revisar_jornada_incluye_ia():
    e = estado_carrera(); e['liga'].jornada_actual = 1
    K.cantera(e); e['liga'].jornada_actual = _mitad(e)
    res = K.revisar_jornada(e, random.Random(12))
    assert isinstance(res.get('ia'), list)
    print("  test_revisar_jornada_incluye_ia: OK")


def click(pos):
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))


def key(k):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, unicode='', mod=0))


def test_pantalla_cantera():
    from alpha_football.ui import cantera_screen as CS, league_screen
    assert ("CANTERA", "Juveniles del club: súbelos o libéralos", 'cantera_screen') in league_screen.TARJETAS['direccion']
    e = estado_carrera(); mi = e['mi_equipo']
    pygame.event.clear()
    assert CS.render(screen, e) is None
    orden = CS.ordenar(K.cantera(e))
    assert [j.overall for j in orden] == sorted((j.overall for j in orden), reverse=True)
    click(CS._rect_fila(2).center); CS.render(screen, e)
    assert e['cantera_sel'] == 2
    n = len(mi.jugadores); elegido = orden[2]
    click(CS._rects()['subir'].center); CS.render(screen, e)
    assert len(mi.jugadores) == n + 1 and mi.jugadores[-1].id == elegido.id and elegido.apellido in e['cantera_msg']
    # liberar pide confirmación: primer clic marca, ESC cancela, dos clics liberan
    antes = len(K.cantera(e))
    click(CS._rects()['liberar'].center); CS.render(screen, e)
    assert e['cantera_confirma'] is not None and len(K.cantera(e)) == antes
    key(pygame.K_ESCAPE)
    assert CS.render(screen, e) is None and e['cantera_confirma'] is None      # ESC cancela, no sale
    click(CS._rects()['liberar'].center); CS.render(screen, e)
    click(CS._rects()['liberar'].center); CS.render(screen, e)
    assert len(K.cantera(e)) == antes - 1
    # selección fuera de rango: se acota, no revienta
    e['cantera_sel'] = 99
    assert CS.render(screen, e) is None and e['cantera_sel'] == len(K.cantera(e)) - 1
    K._guardar(e, [])                                                          # cantera vacía
    click(CS._rects()['subir'].center)
    assert CS.render(screen, e) is None
    key(pygame.K_ESCAPE)
    assert CS.render(screen, e) == 'league_screen'
    print("  test_pantalla_cantera: OK")


def test_pantalla_registrada_con_ayuda_y_atajos():
    import main
    from alpha_football.ui import ayuda, atajos
    assert 'cantera_screen' in main.nombres_pantallas()
    e = estado_carrera()
    assert ayuda.AYUDA['cantera_screen'](e)
    assert 'cantera_screen' in ayuda._TEXTO_TARJETA
    assert "Subir" in atajos.texto('cantera_screen', e)
    print("  test_pantalla_registrada_con_ayuda_y_atajos: OK")


def test_ia_reemplazado_queda_libre():
    from alpha_football import mercado_ia as MI
    e = estado_carrera()
    clubes = _clubes_ia(e)
    antes = {id(eq): len(eq.jugadores) for eq in clubes}
    p_c, p_j, tope = K.PROB_CANTERANO_IA, K.PROB_JOYA_IA, MI.PLANTILLA_MAX_IA
    try:
        K.PROB_CANTERANO_IA, K.PROB_JOYA_IA, MI.PLANTILLA_MAX_IA = 0.0, 1.0, 1    # todos "llenos" y con joya
        altas = K.renovar_ia(e, random.Random(13))
    finally:
        K.PROB_CANTERANO_IA, K.PROB_JOYA_IA, MI.PLANTILLA_MAX_IA = p_c, p_j, tope
    assert altas and all(len(eq.jugadores) == antes[id(eq)] for eq in clubes)   # reemplazo, no alta neta
    libres = e.get('free_agents_list') or []
    assert len(libres) == len(altas) and all(getattr(j, 'fin_de_contrato', False) for j in libres)
    en_clubes = {id(j) for eq in clubes for j in eq.jugadores}
    assert not any(id(j) in en_clubes for j in libres)
    print("  test_ia_reemplazado_queda_libre: OK")


def test_nombres_de_cantera_reservados():
    from alpha_football import nombres as NB
    e = estado_carrera()
    lista = K.cantera(e)
    NB.desduplicar(e)                                                  # lo que pasa al cargar una partida
    assert all(NB.en_uso(j.nombre, j.apellido) for j in lista)
    print("  test_nombres_de_cantera_reservados: OK")


def test_ficha_sin_contrato():
    from alpha_football.ui import ficha_jugador as FJ
    e = estado_carrera()
    assert FJ.textos_contrato(K.cantera(e)[0]) == ("Sin contrato", "Cláusula —", 'blanco')
    contrato, clausula, _color = FJ.textos_contrato(e['mi_equipo'].jugadores[0])
    assert contrato.startswith("Contrato ") and "$" in clausula
    print("  test_ficha_sin_contrato: OK")


TESTS = [test_generar_canterano_rangos, test_cantera_inicial_y_guardado, test_cantera_corrupta_y_cambio_de_club,
         test_renovar_crecen_llegan_y_topes, test_renovar_inicio_cumplen_anios_y_se_van_por_edad,
         test_joya_forzada_y_no_se_va_por_azar, test_revisar_jornada_hitos, test_correo_de_joya,
         test_subir_al_primer_equipo, test_subir_plantilla_llena, test_liberar,
         test_subir_cumple_objetivo_fichar_joven,
         test_ia_sube_canteranos, test_ia_probabilidad_cero_y_joya_en_prensa, test_revisar_jornada_incluye_ia,
         test_pantalla_cantera, test_pantalla_registrada_con_ayuda_y_atajos,
         test_ia_reemplazado_queda_libre, test_nombres_de_cantera_reservados, test_ficha_sin_contrato]

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
