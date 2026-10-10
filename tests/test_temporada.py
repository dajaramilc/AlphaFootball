"""v0.4.13.0: la temporada por fechas (ventanas, ritmos de mitad, fin de temporada, hub)."""
import sys, os, random, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
from datetime import date, timedelta
from test_calendario import screen, key, _e, _jugar, _con_copa   # noqa: E402  (deja save.guardar_en_slot sin efecto)
from alpha_football import calendario as CAL, correo as C, dias as D, temporada as T


def test_hitos_y_ventanas_de_cada_continente():
    e = _e()
    h = T.hitos(e)
    assert (h['inicio'], h['cierre1'], h['mitad'], h['cierre2'], h['fin']) == (
        date(2026, 7, 1), date(2026, 8, 31), date(2027, 1, 1), date(2027, 1, 31), date(2027, 6, 30))
    assert T.ventanas(e) == {'inicio': (date(2026, 7, 1), date(2026, 8, 31)),
                             'invierno': (date(2027, 1, 1), date(2027, 1, 31))}
    assert T.hitos(e, 2)['inicio'] == date(2027, 7, 1)                    # la temporada siguiente
    sa = _e('betplay'); hs = T.hitos(sa)
    assert (hs['inicio'], hs['cierre1'], hs['mitad'], hs['cierre2'], hs['fin']) == (
        date(2027, 1, 1), date(2027, 1, 31), date(2027, 7, 1), date(2027, 8, 31), date(2027, 12, 31))
    assert T.inicio(e) == date(2026, 7, 1) and T.mitad(e) == date(2027, 1, 1) and T.fin(e) == date(2027, 6, 30)


def test_fecha_sin_reloj_es_la_del_partido_y_con_reloj_la_del_reloj():
    e = _e()
    assert T.fecha(e) == CAL.fecha_liga(e, 1)
    e['liga'].jornada_actual = 3
    assert T.fecha(e) == CAL.fecha_liga(e, 3)
    D.hoy(e)                                                              # nace el reloj
    assert T.fecha(e) == D.hoy(e)
    CAL.asegurar(e)['dia'] = '2026-10-10'
    assert T.fecha(e) == date(2026, 10, 10)                               # con reloj manda el reloj, no la jornada
    assert T.fecha({}) == date(2026, 7, 1)                                # sin partida: el inicio


def test_el_mercado_esta_cerrado_en_la_j3_y_la_j13_aunque_la_jornada_toque():
    e = _e(); liga = e['liga']
    abiertas = {}
    for j in (1, 2, 3, 4, 10, 11, 12, 13, 14):
        liga.jornada_actual = j
        abiertas[j] = T.ventana_abierta(e)
    assert abiertas == {1: True, 2: True, 3: False, 4: False, 10: False, 11: True, 12: True, 13: False, 14: False}
    sa = _e('betplay'); l = sa['liga']
    for j, esperado in ((1, True), (2, True), (3, False), (9, False), (10, True), (11, True), (12, True), (13, False)):
        l.jornada_actual = j
        assert T.ventana_abierta(sa) == esperado, j


def test_ventana_actual_cierres_y_proxima_apertura():
    e = _e(); D.hoy(e); cal = CAL.asegurar(e)
    cal['dia'] = '2026-08-31'
    assert T.ventana_actual(e) == 'inicio' and T.ultimo_dia(e) and T.dias_para_cierre(e) == 0
    assert T.proxima_apertura(e) == date(2027, 1, 1) and T.siguiente_ventana(e) == (1, 'inicio')
    cal['dia'] = '2026-09-01'
    assert T.ventana_actual(e) is None and not T.ultimo_dia(e) and T.dias_para_cierre(e) is None
    assert T.siguiente_ventana(e) == (1, 'invierno') and T.hito_del_dia(e, date(2026, 9, 1)) is None and T.hito_del_dia(e, date(2026, 8, 31)) == 'ultimo'   # v0.4.14.0
    cal['dia'] = '2027-02-10'
    assert T.proxima_apertura(e) == date(2027, 7, 1) and T.siguiente_ventana(e) == (2, 'inicio')
    assert T.hito_del_dia(e, date(2026, 7, 1)) == 'abre' and T.hito_del_dia(e, date(2026, 7, 2)) is None


def test_mitad_fin_y_texto_de_la_fase():
    e = _e(); D.hoy(e); cal = CAL.asegurar(e)
    cal['dia'] = '2026-12-31'
    assert not T.segunda_mitad(e) and T.texto_fase(e) == "Primera mitad"
    cal['dia'] = '2027-01-01'
    assert T.segunda_mitad(e) and T.texto_fase(e) == "Mercado abierto · cierra en 30 días"
    cal['dia'] = '2027-01-31'
    assert T.texto_fase(e) == "Mercado abierto · último día"
    cal['dia'] = '2027-02-01'
    assert T.texto_fase(e) == "Segunda mitad" and not T.es_fin(e)
    cal['dia'] = '2027-06-30'
    assert T.es_fin(e) and T.texto_fase(e).startswith("Temporada terminada")


def test_jornadas_de_cada_ventana_y_rondas_de_la_ia():
    e = _e()
    assert T.jornada_de(e, date(2026, 7, 1)) == 1 and T.jornada_de(e, date(2026, 9, 1)) == 3
    assert T.jornada_de(e, date(2027, 1, 1)) == 11
    assert T.ventana_jornadas(e, 'inicio') == (1, 2) and T.ventana_jornadas(e, 'invierno') == (11, 12)
    sa = _e('betplay')
    assert T.ventana_jornadas(sa, 'inicio') == (1, 2) and T.ventana_jornadas(sa, 'invierno') == (10, 12)
    r = T.dias_de_ronda(e)
    assert len(r) == 6 and r == T.dias_de_ronda(e)                         # 3 por ventana, estable
    cierres = {b for _a, b in T.ventanas(e).values()}
    assert all(T.ventana_en(e, d) and d not in cierres for d in r)         # dentro de la ventana, nunca el último día
    assert T.es_dia_de_ronda(e, r[0]) and not T.es_dia_de_ronda(e, date(2026, 12, 1))


def test_market_usa_las_fechas_cuando_recibe_el_estado():
    from alpha_football import market
    e = _e(); liga = e['liga']; liga.jornada_actual = 3
    assert market.ventana_mercado_abierta(3, 22) is True                   # sin estado: la regla vieja por jornada
    assert market.ventana_mercado_abierta(3, 22, estado=e) is False        # con estado: la J3 (5 sep) ya cerró
    liga.jornada_actual = 2
    assert market.ventana_mercado_abierta(2, 22, estado=e) is True
    assert market.ventana_actual(2, 22, estado=e) == (1, 2, 'inicio')
    assert market.clave_ventana_traspaso(1, 2, 22, estado=e) == '1-verano'
    liga.jornada_actual = 3
    assert market.clave_ventana_traspaso(1, 3, 22, estado=e) == '' and market.proxima_apertura(3, 22, estado=e) == 11
    liga.jornada_actual = 11
    assert market.clave_ventana_traspaso(1, 11, 22, estado=e) == '1-invierno'
    liga.jornada_actual = 13
    assert market.proxima_apertura(13, 22, estado=e) == 1                  # la de inicio de la temporada siguiente


def test_los_que_deciden_leen_la_fecha():
    from alpha_football import traspasos_pendientes as TP, salidas as S
    e = _e(); liga = e['liga']
    liga.jornada_actual = 3
    assert not TP.mercado_abierto(e) and not S._ventana_abierta(e)
    liga.jornada_actual = 2
    assert TP.mercado_abierto(e) and S._ventana_abierta(e)


def test_la_oferta_de_la_ia_respeta_la_fecha_de_la_ventana():
    from alpha_football import market
    e = _e(); liga, mi = e['liga'], e['mi_equipo']; rivales = [x for x in liga.equipos if x.id != mi.id]
    liga.jornada_actual = 3                                                 # 5 de septiembre: cerrado
    assert market.crear_oferta_ui(mi, rivales, 3, 22, prob=1.0, estado=e) is None
    liga.jornada_actual = 2
    assert market.crear_oferta_ui(mi, rivales, 2, 22, prob=1.0, estado=e) is not None


def test_lo_acordado_con_el_mercado_cerrado_dice_la_fecha_y_se_concreta_al_abrir():
    from alpha_football import traspasos_pendientes as TP
    e = _e(); liga, mi = e['liga'], e['mi_equipo']; liga.jornada_actual = 3          # 5 de septiembre: cerrado
    assert TP.fecha_apertura(e) == date(2027, 1, 1) and TP.jornada_apertura(e) == 11
    assert TP.texto_apertura(e) == "el " + CAL.texto_fecha(date(2027, 1, 1)) and TP.texto_apertura(e, True) == "vie 1 ene"
    j = mi.jugadores[5]; comprador = liga.equipos[1]
    aviso = TP.diferir_venta(e, j, comprador, 1_000_000)
    assert "1 ene 2027" in aviso and TP.pendiente_de(e, j)['fecha'] == '2027-01-01'
    liga.jornada_actual = 11                                                          # 2 de enero: abierto
    assert TP.mercado_abierto(e) and TP.ejecutar(e) == 1 and TP.pendiente_de(e, j) is None


def _sano(e):
    for j in e['mi_equipo'].jugadores:
        j.personalidad, j.moral, j.energia = 'normal', 70, 100.0
        j.pide_salir = j.salida_forzada = j.transferible = False
        j.prestamo = None


def test_los_ritmos_de_mitad_cambian_en_la_fecha_no_en_la_jornada():
    from alpha_football import cantera as CA
    e = _e(); D.hoy(e); cal = CAL.asegurar(e)
    cal['dia'] = '2026-12-31'
    assert CA._hito(e) == '1-inicio' and CA.proximo_informe(e) == CAL.texto_fecha(date(2027, 1, 1), False)
    cal['dia'] = '2027-01-01'
    assert CA._hito(e) == '1-mitad' and CA.proximo_informe(e) == "inicio de la próxima temporada"


def test_quiere_renovar_solo_desde_la_mitad_por_fecha():
    from alpha_football import salidas as S
    e = _e(); D.hoy(e); cal = CAL.asegurar(e); _sano(e)
    j = e['mi_equipo'].jugadores[0]; j.contrato_anios, j.moral, j.renovacion_avisada = 1, 90, False
    cal['dia'] = '2026-12-31'
    assert S.revisar_renovaciones(e, random.Random(1)) == []
    cal['dia'] = '2027-01-01'
    assert S.revisar_renovaciones(e, random.Random(1))


def test_el_espaldarazo_y_el_tope_usan_la_mitad_por_fecha():
    from alpha_football import directiva as DI
    e = _e(); D.hoy(e); cal = CAL.asegurar(e)
    DI.definir_objetivo(e)
    cal['dia'] = '2027-01-01'
    ok, msg = DI.pedir_espaldarazo(e, 0)
    assert not ok and "mitad" in msg
    cal['dia'] = '2026-12-31'
    ok, msg = DI.pedir_espaldarazo(e, 0)
    assert "hasta la mitad" not in msg                                     # puede fallar por otra razón, no por la fecha


def test_el_ojeador_trabaja_por_ventana_de_fecha():
    from alpha_football import negociacion as N
    e = _e(); D.hoy(e); cal = CAL.asegurar(e)
    cal['dia'] = '2026-08-10'; assert N._clave_ventana(e) == (1, 'inicio')
    cal['dia'] = '2026-09-10'; assert N._clave_ventana(e) == (1, 'invierno')
    cal['dia'] = '2027-02-10'; assert N._clave_ventana(e) == (2, 'inicio')


def test_el_regreso_de_un_prestamo_es_el_primer_dia_de_su_ventana():
    from alpha_football import prestamos as PR
    e = _e(); D.hoy(e); cal = CAL.asegurar(e)
    cal['dia'] = '2026-08-10'                                              # ventana de inicio abierta
    assert PR._regreso(e, 6) == (1, 'invierno', 11)                         # 6 meses: la de invierno (1 ene)
    assert PR._regreso(e, 12) == (2, 'inicio', 1)                           # 1 año: la misma, la temporada siguiente
    cal['dia'] = '2026-10-10'                                              # cerrado: la próxima es la de invierno
    assert PR._regreso(e, 6) == (2, 'inicio', 1)
    assert PR._regreso(e, 12) == (2, 'invierno', 11)
    sa = _e('betplay'); D.hoy(sa); CAL.asegurar(sa)['dia'] = '2027-01-10'
    assert PR._regreso(sa, 6) == (2027 - 2026, 'invierno', 10)             # Sudamérica: invierno = 1 jul, J10


def test_un_vuelve_viejo_con_jornada_se_traduce_por_su_ventana():
    from alpha_football import prestamos as PR
    e = _e(); D.hoy(e)
    p = {'vuelve': [1, 3], 'ventana': 'invierno'}                           # save viejo: la jornada ya no vale
    assert PR._vuelve(p, 22, e) == [1, 11]
    assert PR._vuelve({'vuelve': [1, 9], 'ventana': 'cierre'}, 22, e) == [2, 1]
    assert PR._vuelve({'vuelve': [1, 9], 'ventana': 0}, 22, e) == [1, 1]


def test_el_reloj_nace_el_1_de_julio_en_europa_y_el_1_de_enero_en_sudamerica():
    e = _e(); sa = _e('betplay')
    assert D.hoy(e) == date(2026, 7, 1) and D.hoy(sa) == date(2027, 1, 1)


def test_continuar_se_detiene_al_abrir_y_al_cerrar_el_mercado():
    e = _e(); D.hoy(e); cal = CAL.asegurar(e)
    _jugar(e, 1); _jugar(e, 2)                                             # el próximo partido es la J3 (5 de septiembre)
    cal['dia'] = '2026-08-29'
    r = D.continuar(e)                                                     # v0.4.14.0: no se detiene el 30; para el 31 (último día de fichajes)
    assert r['dias'] == 2 and D.hoy(e) == date(2026, 8, 31) and r['hito'] == 'ultimo'
    cal['dia'] = '2026-08-30'
    r = D.continuar(e)
    assert r['dias'] == 1 and D.hoy(e) == date(2026, 8, 31) and r['hito'] == 'ultimo'
    assert D.texto_resumen(r) == "Pasó 1 día: último día de fichajes"
    assert D.continuar(e)['dias'] == 0                                     # con horas, el día no pasa
    cal['dia'] = '2026-06-30'                                              # (antes del inicio: abre el 1 de julio)
    assert D.avanzar_dia(e)['hito'] == 'abre'


def test_cada_dia_se_revisan_los_ritmos_y_se_concretan_los_traspasos_al_abrir():
    from alpha_football import traspasos_pendientes as TP
    e = _e(); liga, mi = e['liga'], e['mi_equipo']; D.hoy(e); cal = CAL.asegurar(e)
    for jor in range(1, 11):
        _jugar(e, jor)                                                     # el próximo partido es la J11 (2 de enero)
    cal['dia'] = '2026-12-31'
    liga.jornada_actual = 11
    j = mi.jugadores[5]; TP.diferir_venta(e, j, liga.equipos[1], 1_000_000)  # cerrado hasta el 1 de enero
    assert TP.pendiente_de(e, j) is not None
    D.avanzar_dia(e)                                                       # 1 de enero: abre
    assert D.hoy(e) == date(2027, 1, 1) and TP.pendiente_de(e, j) is None and j not in mi.jugadores


def test_la_ia_hace_sus_rondas_en_los_dias_sorteados_de_la_ventana():
    from alpha_football import mercado_ia as MIA
    e = _e(); D.hoy(e); cal = CAL.asegurar(e)
    _jugar(e, 1); _jugar(e, 2)                                             # el próximo partido es la J3: los días de julio y agosto están libres
    dia = T.dias_de_ronda(e)[0]
    llamadas = []
    original = MIA.ronda_fichajes_ia
    MIA.ronda_fichajes_ia = lambda estado, modo='ventana', rng=None: llamadas.append(modo) or []
    try:
        cal['dia'] = (dia - timedelta(days=1)).isoformat()
        D.avanzar_dia(e)                                                   # llega al día de ronda
        siguiente = (dia + timedelta(days=1))
        assert llamadas == ['ventana'] and D.hoy(e) == dia
        if siguiente not in T.dias_de_ronda(e):
            D.avanzar_dia(e); assert llamadas == ['ventana']              # el día siguiente no hay ronda
    finally:
        MIA.ronda_fichajes_ia = original


def test_las_ofertas_se_agendan_dentro_de_la_ventana_y_el_hueco_largo_tira_mas_veces():
    from alpha_football import market
    e = _e(); D.hoy(e)                                                     # 1 de julio: hueco de 45 días hasta la J1
    for j in e['mi_equipo'].jugadores:
        j.transferible = j.pide_salir = False
    viejo = market.PROB_OFERTA_POR_JORNADA
    market.PROB_OFERTA_POR_JORNADA = 1.0                                    # siempre sale
    try:
        nuevos = [it for it in D.programar_ofertas(e, random.Random(3)) if it['tipo'] == 'oferta']
    finally:
        market.PROB_OFERTA_POR_JORNADA = viejo
    assert len(nuevos) == len(D.dias_libres(e)) // 14 >= 3
    D.asignar_dias(e)
    assert all(T.ventana_en(e, date.fromisoformat(it['fecha'])) for it in D.agenda(e))


def test_el_cartel_sale_el_dia_que_abre_y_el_ultimo_dia():
    from alpha_football.ui import aviso_mercado as AM
    e = _e(); D.hoy(e); cal = CAL.asegurar(e)
    assert AM.evento_pendiente(e) == ('abre', '2026-07-01')                 # el reloj nace el día que abre el mercado
    AM._abrir(e, 'abre', '2026-07-01')
    assert AM.evento_pendiente(e) is None and e['datos_carrera']['aviso_mercado_visto'] == [1, '2026-07-01']
    assert e['aviso_mercado_activo']['fecha'] == '2026-07-01'
    cal['dia'] = '2026-08-15'; e['aviso_mercado_activo'] = None
    assert AM.evento_pendiente(e) is None
    cal['dia'] = '2026-08-31'; assert AM.evento_pendiente(e) == ('ultimo', '2026-08-31')   # v0.4.14.0: el cartel del último día
    cal['dia'] = '2026-09-01'; assert AM.evento_pendiente(e) is None
    assert any("Se abrió" in m['asunto'] for m in C.bandeja(e))


def test_la_franja_y_la_cabecera_cuentan_dias():
    from alpha_football.ui import aviso_mercado as AM
    e = _e(); D.hoy(e); cal = CAL.asegurar(e)
    cal['dia'] = '2026-08-12'
    assert AM._texto_franja(e) == ("MERCADO ABIERTO · cierra en 19 días", 'verde')
    assert AM._texto_franja(e, True) == ("MERCADO ABIERTO · 19 d.", 'verde')
    cal['dia'] = '2026-08-31'
    assert AM._texto_franja(e) == ("MERCADO ABIERTO · ÚLTIMO DÍA", 'dorado')
    cal['dia'] = '2026-09-02'
    assert AM._texto_franja(e) is None


def test_despues_del_ultimo_partido_continuar_corre_hasta_el_fin_de_temporada():
    e = _e(); D.hoy(e)
    for j in range(1, 23):
        _jugar(e, j)
    CAL.asegurar(e)['dia'] = CAL.fecha_liga(e, 22).isoformat()
    assert D.es_dia_de_continuar(e)                                         # faltan días hasta el 30 de junio
    l1, l2, l3 = D.textos_hub(e)
    assert l1 == "CONTINUAR" and "Fin de temporada" in l3 and l3.endswith(")")
    r = D.continuar(e)
    assert D.hoy(e) == date(2027, 6, 30) and r['dias'] == (date(2027, 6, 30) - CAL.fecha_liga(e, 22)).days
    assert not D.es_dia_de_continuar(e) and D.textos_hub(e) is None
    assert D.avanzar_dia(e)['dias'] == 0                                    # el día del fin no pasa


def test_el_hub_dice_avanzar_temporada_solo_desde_la_fecha_de_fin():
    from alpha_football.ui import league_screen as L
    e = _e('premier', 11); D.hoy(e)                                        # un club sin copa: el hub no arma una fase de copa "vencida"
    for p in e['liga'].calendario:                                         # toda la liga jugada (no solo tus partidos)
        p.jugado = True
    e['liga'].jornada_actual = 22
    cal = CAL.asegurar(e); cal['dia'] = '2027-06-01'
    info = L._info_partido(e, e['liga'], e['mi_equipo'])
    assert info[1] is False                                                 # la liga terminó, pero no la temporada
    assert L._textos_jugar(e['liga'], e['mi_equipo'], info, e)[0] == "CONTINUAR"
    cal['dia'] = '2027-06-30'
    info = L._info_partido(e, e['liga'], e['mi_equipo'])
    assert info[1] is True and L._textos_jugar(e['liga'], e['mi_equipo'], info, e)[0] == "AVANZAR TEMPORADA"


def test_la_temporada_nueva_nace_el_dia_despues_del_fin():
    e = _e(); D.hoy(e)
    CAL.asegurar(e)['dia'] = '2027-06-30'
    e['temporada'] = 2                                                      # lo que hace avanzar_nueva_temporada
    assert D.hoy(e) == date(2027, 7, 1) and T.inicio(e) == date(2027, 7, 1)


def test_el_hub_pone_la_fecha_y_la_fase_primero():
    from alpha_football.ui import league_screen as L
    e = _e(); D.hoy(e); e['datos_carrera']['aviso_mercado_visto'] = [1, '2026-07-01']
    info = L._info_partido(e, e['liga'], e['mi_equipo'])
    l1, l2, l3, hab = L._textos_jugar(e['liga'], e['mi_equipo'], info, e)
    assert l1 == "CONTINUAR" and l2.startswith("mié 1 jul 2026 · Mercado abierto · cierra en 61 días") and l3.startswith("Próximo: J1")
    dibujados, original = [], L.draw_text
    L.draw_text = lambda scr, txt, *a, **k: (dibujados.append(txt), original(scr, txt, *a, **k))[1]
    try:
        pygame.event.clear(); L.render(screen, e)
    finally:
        L.draw_text = original
    cab = next(t for t in dibujados if "Div." in t and " · " in t)         # (el nombre de la liga cambia entre cargas: no se usa)
    assert "1 jul · J1/22" in cab and "Jornada " not in cab                 # la fecha primero; la jornada, chica


def test_la_pantalla_calendario_abarca_toda_la_temporada_y_marca_las_ventanas():
    from alpha_football.ui import calendario_screen as KS
    e = _e(); _con_copa(e)
    assert KS.limites(e) == ((2026, 7), (2027, 6))                          # del 1 de julio al 30 de junio
    pygame.event.clear(); assert KS.render(screen, e) is None
    assert e['cal_mes'] == [2026, 7]                                        # abre en el mes de hoy (el reloj nace el 1 jul)


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
