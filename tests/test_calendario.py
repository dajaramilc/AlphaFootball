"""v0.4.11.0: calendario real (fechas, copa, reprogramación, descanso) y pantalla CALENDARIO."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
screen = pygame.display.set_mode((1280, 720))
from datetime import date, timedelta
from alpha_football import save
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402
from alpha_football import calendario as CAL, correo as C, energia as E, competiciones as CP
from alpha_football.ui.league_screen import inicializar_calendario_liga


def key(k):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=''))


def _e(tipo='premier', idx=0):
    e = estado_carrera(tipo, idx)
    inicializar_calendario_liga(e['liga'])
    return e


def _jugar(e, jornada, gl=1, gv=0):
    """Marca como jugado el partido de liga del user de esa jornada (sin simular nada)."""
    mi = e['mi_equipo']
    p = next(p for p in e['liga'].calendario if p.jornada == jornada and mi.id in (p.local_id, p.visitante_id))
    p.jugado, p.goles_local, p.goles_visitante = True, gl, gv
    return p


def _con_copa(e, tipo='champions', fecha=0, local=True):
    """Copa mínima con un partido del user en la fecha dada. Devuelve fechas_jornada."""
    mi = e['mi_equipo'].nombre
    fj = [CP.jornada_de_fecha(i, CP.N_FECHAS[tipo], 22) for i in range(CP.N_FECHAS[tipo])]
    e['datos_carrera']['copas'] = {tipo: {
        'tipo': tipo, 'temporada': 1, 'clubes': [{'nombre': mi}, {'nombre': 'Rival Copa'}], 'num_jornadas': 22,
        'fechas_jornada': fj, 'campeon': None,
        'partidos': [{'id': f"{tipo}-{fecha}-0", 'fecha': fecha, 'fase': 'Fase de liga',
                      'local': mi if local else 'Rival Copa', 'visitante': 'Rival Copa' if local else mi,
                      'gl': 0, 'gv': 0, 'jugado': False}]}}
    return fj


def test_sabados_europa_22():
    s = CAL.sabados(22, 'europa', 2026)
    assert len(s) == 22 and all(d.weekday() == 5 for d in s)
    assert all(b > a for a, b in zip(s, s[1:]))
    assert s[0] == date(2026, 8, 15) and s[1] == date(2026, 8, 22)        # J1-J2 en agosto, antes del 31
    assert s[2] == date(2026, 9, 5) and s[9] == date(2026, 12, 19)        # J3-J10: septiembre a diciembre
    assert s[10] == date(2027, 1, 2) and s[11] == date(2027, 1, 23)       # J11-J12 en enero, antes del 31
    assert s[12] == date(2027, 2, 6) and s[21] == date(2027, 5, 29)       # J13-J22: febrero a mayo
    c1, c2 = CAL.cierres('europa', 2026)
    assert (c1, c2) == (date(2026, 8, 31), date(2027, 1, 31))
    assert s[1] + timedelta(days=2) < c1 < s[2] and s[11] + timedelta(days=2) < c2 < s[12]


def test_sabados_sudamerica_22():
    s = CAL.sabados(22, 'sudamerica', 2027)
    assert len(s) == 22 and all(d.weekday() == 5 for d in s)
    assert s[0] == date(2027, 1, 16) and s[1] == date(2027, 1, 23)        # J1-J2 en enero
    assert s[2] == date(2027, 2, 6) and s[9] == date(2027, 7, 17)         # J3-J10: febrero a julio
    assert s[10] == date(2027, 8, 7) and s[11] == date(2027, 8, 28)       # J11-J12 en agosto
    assert s[12] == date(2027, 9, 4) and s[21] == date(2027, 12, 11)      # J13-J22: septiembre a diciembre
    assert CAL.cierres('sudamerica', 2027) == (date(2027, 1, 31), date(2027, 8, 31))


def test_otros_largos_de_liga():
    for n in (38, 14, 6, 2, 1):
        for cont, anio in (('europa', 2026), ('sudamerica', 2027)):
            s = CAL.sabados(n, cont, anio)
            assert len(s) == n and all(d.weekday() == 5 for d in s), (n, cont)
            assert all(b > a for a, b in zip(s, s[1:])), (n, cont)
    s38 = CAL.sabados(38, 'europa', 2026)
    assert s38[0] >= date(2026, 8, 1) and s38[-1] <= date(2027, 6, 15)


def test_fecha_de_liga_es_fin_de_semana_y_estable():
    e = _e()
    fechas = [CAL.fecha_liga(e, j) for j in range(1, 23)]
    assert all(f.weekday() in (5, 6, 0) for f in fechas)                  # sábado, domingo o lunes
    assert fechas == [CAL.fecha_liga(e, j) for j in range(1, 23)]         # la semilla no cambia
    assert all(0 <= (f - b).days <= 2 for f, b in zip(fechas, CAL.sabados(22, 'europa', 2026)))
    assert CAL.fecha_liga(e, 0) == fechas[0] and CAL.fecha_liga(e, 99) == fechas[-1]   # fuera de rango: se acota
    assert CAL.texto_fecha(date(2026, 8, 15)) == "sáb 15 ago 2026"
    assert CAL.texto_fecha(date(2026, 8, 15), False) == "sáb 15 ago"


def test_anio_y_continente():
    e = _e()
    assert CAL.continente(e) == 'europa' and CAL.anio(e) == 2026
    e['temporada'] = 3
    assert CAL.anio(e) == 2028 and CAL.fecha_liga(e, 1).year == 2028
    sa = _e('betplay')
    assert CAL.continente(sa) == 'sudamerica' and CAL.anio(sa) == 2027 and CAL.fecha_liga(sa, 1).month == 1
    sa['datos_carrera']['mundo'] = {'anio': {'sudamerica': 2031}}         # lo que escribirá el sub-proyecto F
    assert CAL.anio(sa) == 2031
    assert CAL.continente({}) == 'europa'


def test_el_calendario_se_rearma_al_cambiar_de_temporada_o_club():
    e = _e()
    cal = CAL.asegurar(e)
    assert cal['mov'] == {} and cal['clave'][0] == 2026
    cal['mov']['liga:5'] = '2026-10-04'
    assert CAL.fecha_liga(e, 5) == date(2026, 10, 4)                      # lo reprogramado manda
    assert CAL.asegurar(e) is cal                                         # misma temporada: se conserva
    e['temporada'] = 2
    assert CAL.asegurar(e)['mov'] == {} and CAL.fecha_liga(e, 5).year == 2027
    e['mi_equipo'] = e['liga'].equipos[1]
    assert CAL.asegurar(e)['clave'][3] == str(e['liga'].equipos[1].id)
    viejo = _e(); viejo['datos_carrera']['calendario'] = "roto"           # save con el dato dañado
    assert CAL.asegurar(viejo)['mov'] == {}
    viejo['datos_carrera']['calendario']['mov']['liga:1'] = 'no-es-fecha'
    assert CAL.fecha_liga(viejo, 1).weekday() in (5, 6, 0)                # fecha inválida: se ignora


def test_fechas_de_copa_entre_jornadas_y_despues_del_cierre():
    e = _e(); fj = _con_copa(e)
    s = CAL.sabados(22, 'europa', 2026)
    c1, c2 = CAL.cierres('europa', 2026)
    for i, j in enumerate(fj[:-1]):
        f = CAL.fecha_copa(e, 'champions', i)
        assert f.weekday() in (1, 2, 3), (i, f)                           # martes, miércoles o jueves
        assert s[j - 1] < f < s[j], (i, j, f)                             # entre esa jornada y la siguiente
        for c in (c1, c2):
            if s[j - 1] < c < s[j]:
                assert f > c, (i, f, c)                                   # nunca antes del cierre de mercado
    assert CAL.fecha_copa(e, 'champions', len(fj) - 1) == s[-1] + timedelta(days=7)    # la final
    assert CAL.fecha_copa(e, 'champions', 0) == CAL.fecha_copa(e, 'champions', 0)      # estable


def test_copa_que_no_existe_o_fecha_fuera_de_rango():
    e = _e()
    assert CAL.fecha_copa(e, 'champions', 0) is None                      # sin copas
    _con_copa(e)
    assert CAL.fecha_copa(e, 'champions', 99) is None and CAL.fecha_copa(e, 'champions', -1) is None
    assert CAL.fecha_copa(e, 'libertadores', 0) is None
    e['datos_carrera']['copas']['champions']['fechas_jornada'] = None
    assert CAL.fecha_copa(e, 'champions', 0) is None


def test_partidos_del_user_en_orden():
    e = _e(); _con_copa(e, fecha=0)                                       # la fecha 0 se juega tras la J2
    evs = CAL.eventos_user(e)
    assert [x['clave'] for x in evs[:4]] == ['liga:1', 'liga:2', 'copa:champions:0', 'liga:3']
    assert all(b['fecha'] >= a['fecha'] for a, b in zip(evs, evs[1:]))
    assert len([x for x in evs if x['tipo'] == 'liga']) == 22
    copa = evs[2]
    assert copa['etiqueta'] == 'UCL' and copa['rival'] == 'Rival Copa' and copa['local'] and not copa['jugado']
    assert CAL.proximo_evento(e)['clave'] == 'liga:1' and CAL.hoy(e) == CAL.fecha_liga(e, 1)
    assert CAL.texto_proximo(e) == CAL.texto_fecha(CAL.fecha_liga(e, 1))
    _jugar(e, 1, 2, 1)
    assert CAL.proximo_evento(e)['clave'] == 'liga:2'
    ev1 = CAL.eventos_user(e)[0]
    assert ev1['jugado'] and {ev1['gf'], ev1['gc']} == {2, 1} and ev1['rival'] != '?'


def test_sin_liga_o_temporada_terminada():
    assert CAL.eventos_user({}) == [] and CAL.proximo_evento({}) is None and CAL.texto_proximo({}) == ''
    e = _e()
    for j in range(1, 23):
        _jugar(e, j)
    assert CAL.proximo_evento(e) is None and CAL.hoy(e) == CAL.fecha_liga(e, 22)
    vacio = estado_carrera()                                              # liga sin calendario armado
    vacio['liga'].calendario = []
    assert CAL.eventos_user(vacio) == [] and CAL.hoy(vacio) == CAL.sabados(22, 'europa', 2026)[0]


def _reprogramados(e):
    return [m for m in C.bandeja(e) if m['asunto'].startswith("Partido reprogramado")]


def test_choque_mueve_la_liga_dentro_del_fin_de_semana():
    e = _e(); _con_copa(e, fecha=0); _jugar(e, 1); _jugar(e, 2)
    cal = CAL.asegurar(e)
    cal['mov']['copa:champions:0'] = '2026-09-03'                         # jueves
    cal['mov']['liga:3'] = '2026-09-05'                                   # sábado: a 2 días
    cambios = CAL.revisar_choques(e)
    assert [c['clave'] for c in cambios] == ['liga:3']
    assert cambios[0]['de'] == date(2026, 9, 5) and cambios[0]['a'] == date(2026, 9, 6)
    assert CAL.fecha_liga(e, 3) == date(2026, 9, 6)                       # pasa al domingo
    m = _reprogramados(e)[0]
    assert m['accion']['pantalla'] == 'calendario_screen' and "dom 6 sep" in m['cuerpo']
    assert CAL.revisar_choques(e) == [] and len(_reprogramados(e)) == 1   # ya no hay choque


def test_choque_lunes_martes_adelanta_la_liga():
    e = _e(); _con_copa(e, fecha=0); _jugar(e, 1)
    cal = CAL.asegurar(e)
    cal['mov']['liga:1'] = '2026-08-15'
    cal['mov']['liga:2'] = '2026-08-24'                                   # lunes
    cal['mov']['copa:champions:0'] = '2026-08-25'                         # martes
    cambios = CAL.revisar_choques(e)
    assert [c['clave'] for c in cambios] == ['liga:2'] and CAL.fecha_liga(e, 2) == date(2026, 8, 22)


def test_si_la_liga_no_puede_moverse_se_mueve_la_copa():
    e = _e(); _con_copa(e, fecha=0); _jugar(e, 1); _jugar(e, 2)
    cal = CAL.asegurar(e)
    cal['mov']['copa:champions:0'] = '2026-09-03'                         # jueves
    cal['mov']['liga:3'] = '2026-09-05'                                   # sábado
    cal['mov']['liga:4'] = '2026-09-08'                                   # martes: el domingo y el lunes no sirven
    cambios = CAL.revisar_choques(e)
    assert [c['clave'] for c in cambios] == ['copa:champions:0']
    assert CAL.fecha_copa(e, 'champions', 0) == date(2026, 9, 2)          # miércoles


def test_choque_sin_solucion_no_mueve_nada():
    e = _e(); _con_copa(e, fecha=0); _jugar(e, 1); _jugar(e, 2)
    cal = CAL.asegurar(e)
    cal['mov']['liga:2'] = '2026-08-31'                                   # ya jugado, pegado al de copa
    cal['mov']['copa:champions:0'] = '2026-09-03'
    cal['mov']['liga:3'] = '2026-09-04'                                   # viernes: a 1 día
    cal['mov']['liga:4'] = '2026-09-07'
    antes = dict(cal['mov'])
    assert CAL.revisar_choques(e) == [] and cal['mov'] == antes and _reprogramados(e) == []


def test_solo_mira_los_proximos_partidos():
    e = _e(); _con_copa(e, fecha=0)
    cal = CAL.asegurar(e)
    cal['mov']['liga:9'] = '2026-11-21'
    cal['mov']['liga:10'] = '2026-11-22'                                  # choque lejano: todavía no se mira
    assert CAL.revisar_choques(e) == []
    assert CAL.revisar_choques({}) == []                                  # sin partida: nada


def test_el_hub_revisa_los_choques_una_sola_vez():
    from alpha_football.ui import league_screen as L
    e = _e(); _con_copa(e, fecha=0)
    from alpha_football import dias as _D0                                 # v0.4.13.0: el cartel de apertura es por fecha
    e['datos_carrera']['aviso_mercado_visto'] = [1, _D0.hoy(e).isoformat()]
    pygame.event.clear(); L.render(screen, e)
    assert CAL.asegurar(e).get('revisado') is True


def test_descanso_reparte_los_dias_del_hueco():
    e = _e()
    total = (CAL.fecha_liga(e, 2) - CAL.fecha_liga(e, 1)).days
    assert CAL.descanso_tras_liga(e, 1) == (float(total), 0.0)            # sin copa en el hueco
    _con_copa(e, fecha=0)                                                  # fecha 0: tras la J2
    d1, d2 = CAL.descanso_tras_liga(e, 2)
    assert d1 == (CAL.fecha_copa(e, 'champions', 0) - CAL.fecha_liga(e, 2)).days > 0
    assert d1 + d2 == (CAL.fecha_liga(e, 3) - CAL.fecha_liga(e, 2)).days and d2 > 0
    assert CAL.descanso_tras_liga(e, 1) == (float(total), 0.0)            # esa copa no cae en el hueco de la J1
    assert CAL.descanso_tras_liga(e, 22) == (7.0, 0.0)                    # tras la última jornada
    e['datos_carrera']['copas']['champions']['campeon'] = 'Alguien'       # copa terminada: no cuenta
    assert CAL.descanso_tras_liga(e, 2)[1] == 0.0
    assert abs(CAL.dias_por_jornada(e) - 287 / 21) < 1e-9


def test_recuperacion_proporcional_a_los_dias():
    e = _e(); j = e['mi_equipo'].jugadores[0]
    ref = CAL.dias_por_jornada(e)
    j.energia = 10; E.recuperar_todos(e)
    assert abs(j.energia - 10 - E.recuperacion(j)) < 1e-9                 # sin días: la de siempre
    j.energia = 10; E.recuperar_todos(e, ref)
    assert abs(j.energia - 10 - E.recuperacion(j)) < 1e-6
    j.energia = 10; E.recuperar_todos(e, ref / 2)
    assert abs(j.energia - 10 - E.recuperacion(j) / 2) < 1e-6
    j.energia = 10; E.recuperar_todos(e, 0); assert j.energia == 10
    j.energia = 10; E.recuperar_todos(e, -5); assert j.energia == 10      # días negativos: nada
    j.energia = 95; E.recuperar_todos(e, 60); assert j.energia == 100     # tope
    j.energia = 50; E.recuperar(j, 0.5)
    assert abs(j.energia - 50 - E.recuperacion(j) / 2) < 1e-9


def test_descanso_pendiente_se_aplica_tras_la_copa():
    e = _e(); j = e['mi_equipo'].jugadores[0]
    CAL.asegurar(e)
    e['datos_carrera']['descanso_pendiente'] = CAL.dias_por_jornada(e)
    j.energia = 10
    CAL.tras_partido_copa_user(e)
    assert abs(j.energia - 10 - E.recuperacion(j)) < 1e-6
    assert 'descanso_pendiente' not in e['datos_carrera']
    assert CAL.aplicar_descanso_pendiente(e) == 0                         # no se aplica dos veces
    assert CAL.aplicar_descanso_pendiente({}) == 0


def test_la_jornada_recupera_segun_los_dias_de_descanso():
    from alpha_football.ui.match_screen import finalizar_jornada_liga
    e = _e(); liga, mi = e['liga'], e['mi_equipo']
    p = next(p for p in liga.calendario if p.jornada == 1 and mi.id in (p.local_id, p.visitante_id))
    for j in mi.jugadores:
        j.energia = 10.0
    finalizar_jornada_liga(e, liga, mi, p, 1, 0)
    factor = (CAL.fecha_liga(e, 2) - CAL.fecha_liga(e, 1)).days / CAL.dias_por_jornada(e)
    bien = [j for j in mi.jugadores if abs(j.energia - min(100.0, 10 + E.recuperacion(j) * factor)) < 1e-6]
    assert len(bien) >= len(mi.jugadores) - 2, (len(bien), len(mi.jugadores))
    assert 'descanso_pendiente' not in e['datos_carrera']                 # sin copa pendiente: todo aplicado


def test_hub_y_prepartido_dibujan_la_fecha_sin_errores():
    import logging
    from alpha_football.ui import league_screen as L

    class _Errores(logging.Handler):
        def __init__(self):
            super().__init__(level=logging.ERROR); self.vistos = []
        def emit(self, record):
            self.vistos.append(record.getMessage())
    h = _Errores(); logging.getLogger().addHandler(h)
    dibujados, original = [], L.draw_text
    L.draw_text = lambda scr, txt, *a, **k: (dibujados.append(txt), original(scr, txt, *a, **k))[1]
    try:
        e = _e(); _con_copa(e, fecha=0)
        from alpha_football import dias as _D0                             # v0.4.13.0: el cartel de apertura es por fecha
        e['datos_carrera']['aviso_mercado_visto'] = [1, _D0.hoy(e).isoformat()]
        pygame.event.clear(); L.render(screen, e)
        pygame.event.clear(); L.render(screen, e)
    finally:
        L.draw_text = original
        logging.getLogger().removeHandler(h)
    assert not [m for m in h.vistos if 'fecha' in m.lower() or 'calendario' in m.lower()], h.vistos
    assert CAL.texto_proximo(e).startswith(('sáb', 'dom', 'lun'))
    from alpha_football import dias as _D                                  # v0.4.13.0: sin partido hoy, la fecha de hoy va en la línea 2 de CONTINUAR
    assert any(str(t).startswith(CAL.texto_fecha(_D.hoy(e))) for t in dibujados)


def test_cuadricula_del_mes():
    from alpha_football.ui import calendario_screen as KS
    c = KS.celdas_mes(2026, 8)
    assert len(c) == 42 and c[0].weekday() == 0 and c[0] <= date(2026, 8, 1) and c[-1] >= date(2026, 8, 31)
    assert [(b - a).days for a, b in zip(c, c[1:])] == [1] * 41
    assert KS.rect_celda(41).bottom <= KS.R_GRILLA.bottom and KS.rect_celda(6).right <= KS.R_GRILLA.right
    assert KS.R_GRILLA.bottom <= 696                                       # no pisa la barra de atajos


def test_pantalla_calendario_navega_y_vuelve():
    from alpha_football.ui import calendario_screen as KS
    e = _e(); _con_copa(e)
    por_dia = KS.eventos_por_dia(e)
    assert por_dia[CAL.fecha_liga(e, 1)][0]['clave'] == 'liga:1'
    assert KS.limites(e) == ((2026, 7), (2027, 6))                         # v0.4.13.0: del 1 de julio al 30 de junio
    pygame.event.clear(); assert KS.render(screen, e) is None
    assert e['cal_mes'] == [2026, 7]                                       # abre en el mes de hoy (el reloj nace el 1 jul)
    key(pygame.K_RIGHT); KS.render(screen, e); assert e['cal_mes'] == [2026, 8]
    key(pygame.K_LEFT); KS.render(screen, e); key(pygame.K_LEFT); KS.render(screen, e)
    assert e['cal_mes'] == [2026, 7]                                       # no retrocede antes del inicio
    for _ in range(14):
        key(pygame.K_RIGHT); KS.render(screen, e)
    assert e['cal_mes'] == [2027, 6]                                       # ni pasa del fin
    key(pygame.K_ESCAPE); assert KS.render(screen, e) == 'league_screen' and 'cal_mes' not in e
    assert KS.render(screen, {}) == 'league_screen'                        # sin partida: vuelve


def test_la_pantalla_esta_registrada():
    orig_get = pygame.event.get
    try:
        import main                                                        # main parchea pygame.event.get al importarse
    finally:
        pygame.event.get = orig_get
    from alpha_football.ui import league_screen as L, ayuda
    assert any(t[2] == 'calendario_screen' for t in L.TARJETAS['direccion'])
    assert len(L.TARJETAS['oficina']) == 9                                 # v0.4.23.0: + NOTICIAS (3 columnas)
    assert main.MODULOS_PANTALLA['calendario_screen'] == 'alpha_football.ui.calendario_screen'
    assert 'calendario_screen' in ayuda.AYUDA and ayuda.AYUDA['calendario_screen']({})


if __name__ == '__main__':
    TESTS = [v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
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
