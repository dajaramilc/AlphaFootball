"""v0.4.12.0: avance por días (reloj, agenda, CONTINUAR / +1 DÍA)."""
import sys, os, random, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
from datetime import date, timedelta
from test_calendario import screen, key, _e, _jugar, _con_copa   # noqa: E402  (deja save.guardar_en_slot sin efecto)
from alpha_football import calendario as CAL, correo as C, energia as E, dias as D


def test_el_reloj_nace_al_inicio_de_la_temporada():
    e = _e()
    assert not D.activo(e)                                                 # sin hub, sin reloj
    assert D.hoy(e) == date(2026, 7, 1) and D.activo(e)                    # Europa: 1 de julio
    assert D.hoy(e) == date(2026, 7, 1)                                    # estable
    sa = _e('betplay')
    assert D.hoy(sa) == date(2027, 1, 1)                                   # Sudamérica: 1 de enero
    assert D.hoy({}) == date(2026, 7, 1) and not D.activo({})              # sin partida: no escribe nada


def test_el_reloj_de_un_save_a_mitad_de_temporada_nace_en_su_proximo_partido():
    e = _e(); _jugar(e, 1); _jugar(e, 2)
    assert D.hoy(e) == CAL.fecha_liga(e, 3)


def test_avanzar_dia_mueve_un_dia_y_no_pasa_del_partido():
    e = _e(); D.hoy(e)
    primero = CAL.fecha_liga(e, 1)
    n = (primero - date(2026, 7, 1)).days
    assert n > 1 and D.es_dia_de_continuar(e)
    r = D.avanzar_dia(e)
    assert r['dias'] == 1 and D.hoy(e) == date(2026, 7, 2)
    for _ in range(n - 1):
        D.avanzar_dia(e)
    assert D.hoy(e) == primero and not D.es_dia_de_continuar(e)            # día de partido: JUGAR
    assert D.avanzar_dia(e)['dias'] == 0 and D.hoy(e) == primero           # no pasa por encima del partido


def test_continuar_llega_al_dia_del_partido():
    e = _e(); D.hoy(e)
    r = D.continuar(e)
    assert D.hoy(e) == CAL.fecha_liga(e, 1)
    assert r['dias'] == (CAL.fecha_liga(e, 1) - date(2026, 7, 1)).days
    assert D.continuar(e)['dias'] == 0                                     # ya es día de partido
    _jugar(e, 1)
    assert D.hasta_el_partido(e)['dias'] > 0 and D.hoy(e) == CAL.fecha_liga(e, 2)


def test_sin_partidos_pendientes_el_reloj_corre_hasta_el_fin_de_temporada():
    e = _e(); D.hoy(e)
    for j in range(1, 23):
        _jugar(e, j)
    assert D.es_dia_de_continuar(e) and D.avanzar_dia(e)['dias'] == 1       # v0.4.13.0: faltan días hasta el 30 de junio
    D.continuar(e, parar=False)
    assert not D.es_dia_de_continuar(e) and D.avanzar_dia(e)['dias'] == 0
    assert D.continuar({})['dias'] == 0 and not D.es_dia_de_continuar({})   # sin partida


def test_si_el_partido_se_mueve_antes_del_reloj_se_juega_ese_dia():
    e = _e(); D.hoy(e); D.hasta_el_partido(e); _jugar(e, 1)
    hoy = D.hoy(e)
    CAL.asegurar(e)['mov']['liga:2'] = (hoy - timedelta(days=1)).isoformat()   # C lo reprogramó "al pasado"
    assert D.hoy(e) == hoy and not D.es_dia_de_continuar(e)                # el reloj no retrocede
    assert D.avanzar_dia(e)['dias'] == 0


def test_la_energia_se_recupera_cada_dia_como_en_el_reparto_de_c():
    e = _e(); D.hoy(e); j = e['mi_equipo'].jugadores[0]
    total = (CAL.fecha_liga(e, 1) - D.hoy(e)).days
    j.energia = 10
    D.continuar(e)
    esperado = min(100.0, 10 + E.recuperacion(j) * total)           # v0.4.26.0: cantidad fija POR DÍA
    assert abs(j.energia - esperado) < 1e-6


def test_con_reloj_cerrar_el_partido_no_recupera_energia_y_los_dias_si():
    from alpha_football.ui.match_screen import finalizar_jornada_liga
    e = _e(); liga, mi = e['liga'], e['mi_equipo']
    D.hoy(e); D.hasta_el_partido(e)
    p = next(p for p in liga.calendario if p.jornada == 1 and mi.id in (p.local_id, p.visitante_id))
    for j in mi.jugadores:
        j.energia = 10.0
    finalizar_jornada_liga(e, liga, mi, p, 1, 0)
    assert all(j.energia == 10.0 for j in mi.jugadores)                    # cerrar no recupera: lo hacen los días
    D.hasta_el_partido(e)
    dias = (CAL.fecha_liga(e, 2) - CAL.fecha_liga(e, 1)).days             # v0.4.26.0: cantidad fija POR DÍA
    bien = [j for j in mi.jugadores if abs(j.energia - min(100.0, 10 + E.recuperacion(j) * dias)) < 1e-6]
    assert len(bien) >= len(mi.jugadores) - 2, (len(bien), len(mi.jugadores))


def test_textos_del_hub_y_resumen():
    e = _e()
    assert D.textos_hub(e) is None                                         # sin reloj: como siempre
    D.hoy(e)
    l1, l2, l3 = D.textos_hub(e)
    assert l1 == "CONTINUAR" and l2.startswith("mié 1 jul 2026") and "Mercado abierto" in l2
    assert l3.startswith("Próximo: J1") and "(en " in l3 and l3.endswith(")") and len(l3) <= 56
    D.hasta_el_partido(e)
    assert D.textos_hub(e) is None                                         # día de partido: JUGAR
    assert D.texto_resumen({'dias': 3, 'ofertas': 1, 'correos': 2, 'eventos': 0}) == "Pasaron 3 días: 1 oferta, 2 correos"
    assert D.texto_resumen({'dias': 1, 'ofertas': 0, 'correos': 0, 'eventos': 1}) == "Pasó 1 día: 1 evento"
    assert D.texto_resumen({'dias': 2, 'ofertas': 0, 'correos': 0, 'eventos': 0}) == "Pasaron 2 días"
    assert D.texto_resumen({'dias': 0}) == "Hoy es día de partido"


def _en_j1(e):
    """Reloj en el día de la J1, ya jugada: el hueco hasta la J2 está por delante."""
    D.hoy(e); D.hasta_el_partido(e); _jugar(e, 1)


def test_la_agenda_asigna_dias_del_hueco_y_es_estable():
    e = _e(); _en_j1(e)
    d1, d2 = CAL.fecha_liga(e, 1), CAL.fecha_liga(e, 2)
    for _ in range(5):
        D.programar(e, 'oferta')
    assert D.asignar_dias(e) == 5 and D.asignar_dias(e) == 0              # la segunda vez no hay nada sin día
    fechas = [date.fromisoformat(it['fecha']) for it in D.agenda(e)]
    assert all(d1 < f < d2 for f in fechas), (fechas, d1, d2)
    f = _e(); _en_j1(f)                                                    # misma partida, mismo sorteo
    for _ in range(5):
        D.programar(f, 'oferta')
    D.asignar_dias(f)
    assert [it['fecha'] for it in D.agenda(f)] == [it['fecha'] for it in D.agenda(e)]


def test_nada_cae_el_dia_de_un_partido_aunque_haya_copa_en_el_hueco():
    e = _e(); _con_copa(e, fecha=0)
    D.hoy(e); D.hasta_el_partido(e); _jugar(e, 1); D.hasta_el_partido(e); _jugar(e, 2)
    d2, copa, d3 = CAL.fecha_liga(e, 2), CAL.fecha_copa(e, 'champions', 0), CAL.fecha_liga(e, 3)
    for _ in range(40):
        D.programar(e, 'oferta')
    D.asignar_dias(e)
    fechas = {date.fromisoformat(it['fecha']) for it in D.agenda(e)}
    assert d2 < copa < d3 and len(fechas) > 3
    assert copa not in fechas and d2 not in fechas and d3 not in fechas
    assert all(d2 < f < d3 for f in fechas)


def test_hueco_corto_de_tres_dias_deja_dos_dias_libres():
    e = _e(); _en_j1(e)
    d1 = CAL.fecha_liga(e, 1)
    CAL.asegurar(e)['mov']['liga:2'] = (d1 + timedelta(days=3)).isoformat()
    assert D.dias_libres(e) == [d1 + timedelta(days=1), d1 + timedelta(days=2)]
    D.programar(e, 'oferta'); D.asignar_dias(e)
    assert date.fromisoformat(D.agenda(e)[0]['fecha']) in D.dias_libres(e)


def test_los_correos_diferidos_van_a_la_agenda_y_llegan_el_dia_sorteado():
    e = _e(); _en_j1(e)
    with D.diferir_correos(e):
        msg = C.enviar(e, 'club', "Hola", "Cuerpo")
        msg['evento'] = {'id': 'x', 'resuelto': None}                      # lo que hace eventos.sortear
    assert C.bandeja(e) == [] and msg['id'] == 0 and D.agenda(e)[0]['tipo'] == 'correo'
    json.dumps(e['datos_carrera'])                                         # se puede guardar la partida
    D.asignar_dias(e)
    fecha = date.fromisoformat(D.agenda(e)[0]['fecha'])
    r = D.continuar(e)
    assert D.hoy(e) == fecha and r['eventos'] == 1 and r['correos'] == 0   # lleva 'evento': cuenta como evento
    assert [m['asunto'] for m in C.bandeja(e)] == ["Hola"] and C.bandeja(e)[0]['id'] == 1
    assert C.bandeja(e)[0]['evento'] == {'id': 'x', 'resuelto': None} and D.agenda(e) == []
    f = _e()                                                               # sin reloj: se envía en el acto
    with D.diferir_correos(f):
        C.enviar(f, 'club', "Ya", "x")
    assert [m['asunto'] for m in C.bandeja(f)] == ["Ya"]


def test_agenda_danada_o_con_tipos_desconocidos_no_rompe_el_avance():
    e = _e(); _en_j1(e)
    e['datos_carrera']['calendario']['agenda'] = "rota"
    assert D.agenda(e) == []
    D.agenda(e).extend([{'fecha': 'no-es-fecha', 'tipo': 'correo', 'datos': {}}, 'basura',
                        {'fecha': None, 'tipo': 'marciano', 'datos': {}}])
    r = D.hasta_el_partido(e)
    assert r['dias'] > 0 and D.hoy(e) == CAL.fecha_liga(e, 2)
    assert D.agenda(e) == [] and C.bandeja(e) == []                        # lo dañado se descarta sin ensuciar el correo


def test_al_final_de_la_liga_lo_agendado_llega_en_el_acto():
    e = _e(); D.hoy(e)
    for j in range(1, 23):
        _jugar(e, j)
    with D.diferir_correos(e):
        C.enviar(e, 'club', "Fin", "x")
    D.asignar_dias(e)                                                      # no hay más partidos: sin días libres
    assert [m['asunto'] for m in C.bandeja(e)] == ["Fin"] and D.agenda(e) == []


def test_reloj_y_agenda_sobreviven_a_guardar_y_cargar():
    e = _e(); _en_j1(e)
    with D.diferir_correos(e):
        C.enviar(e, 'club', "Guardado", "x")
    D.asignar_dias(e)
    f = _e(); f['datos_carrera'] = json.loads(json.dumps(e['datos_carrera']))
    assert D.activo(f) and D.hoy(f) == D.hoy(e)
    assert D.agenda(f) == D.agenda(e) and len(D.agenda(f)) == 1


def test_la_probabilidad_de_oferta_es_la_de_hoy():
    from alpha_football import market
    e = _e(); mi = e['mi_equipo']
    for j in mi.jugadores:
        j.transferible = j.pide_salir = False
    assert market.prob_oferta_ia(mi) == market.PROB_OFERTA_POR_JORNADA
    mi.jugadores[3].transferible = True
    assert market.prob_oferta_ia(mi) == market.PROB_OFERTA_CON_TRANSFERIBLES


def test_el_sorteo_de_ofertas_conserva_las_frecuencias_y_respeta_la_ventana():
    e = _e(); _en_j1(e)                                                # reloj el día de la J1: hueco corto = 1 tirada
    for j in e['mi_equipo'].jugadores:
        j.transferible = j.pide_salir = False
    rng = random.Random(7); N = 3000
    n_loc = n_ext = 0
    for _ in range(N):
        D.agenda(e).clear()
        for it in D.programar_ofertas(e, rng):
            n_loc += it['tipo'] == 'oferta'; n_ext += it['tipo'] == 'oferta_ext'
    assert abs(n_loc / N - 0.15) < 0.03 and abs(n_ext / N - 0.25) < 0.03, (n_loc / N, n_ext / N)
    for j in range(2, 10):
        _jugar(e, j)
    CAL.asegurar(e)['dia'] = CAL.fecha_liga(e, 9).isoformat()          # el hueco hasta la J10 cae en noviembre/diciembre: cerrado
    assert all(it['tipo'] == 'oferta_ext' for _ in range(300) for it in D.programar_ofertas(e, rng))


def test_la_oferta_local_se_crea_el_dia_sorteado_y_no_antes():
    e = _e(); _en_j1(e); e['liga'].jornada_actual = 2
    it = D.programar(e, 'oferta'); D.asignar_dias(e)
    fecha = date.fromisoformat(it['fecha'])
    assert not e.get('ofertas_recibidas')
    r = D.continuar(e)
    assert D.hoy(e) == fecha and r['ofertas'] == 1 and len(e['ofertas_recibidas']) == 1
    assert any(m['asunto'].startswith("Oferta por") for m in C.bandeja(e))


def test_oferta_agendada_con_el_mercado_cerrado_no_se_crea_ni_rompe_el_avance():
    e = _e(); _en_j1(e)
    for j in range(2, 10):
        _jugar(e, j)
    CAL.asegurar(e)['dia'] = CAL.fecha_liga(e, 9).isoformat()              # ventana cerrada ese día
    D.programar(e, 'oferta')
    r = D.hasta_el_partido(e)
    assert r['ofertas'] == 0 and not e.get('ofertas_recibidas') and D.agenda(e) == []
    assert D.hoy(e) == CAL.fecha_liga(e, 10)                               # y el avance siguió sin romperse


def test_la_oferta_del_exterior_se_consume_sin_romper():
    e = _e(); _en_j1(e)
    D.programar(e, 'oferta_ext')
    r = D.hasta_el_partido(e)
    assert r['ofertas'] in (0, 1) and D.agenda(e) == [] and D.hoy(e) == CAL.fecha_liga(e, 2)


def test_cerrar_el_partido_con_reloj_agenda_las_ofertas_con_dia_y_no_las_crea_en_el_acto():
    from alpha_football import market
    from alpha_football.ui.match_screen import finalizar_jornada_liga
    e = _e(); liga, mi = e['liga'], e['mi_equipo']
    D.hoy(e); D.hasta_el_partido(e)
    p = next(p for p in liga.calendario if p.jornada == 1 and mi.id in (p.local_id, p.visitante_id))
    viejo_loc, viejo_ext = market.PROB_OFERTA_POR_JORNADA, D.PROB_OFERTA_EXTERIOR
    market.PROB_OFERTA_POR_JORNADA = D.PROB_OFERTA_EXTERIOR = 1.0
    try:
        finalizar_jornada_liga(e, liga, mi, p, 1, 0)
    finally:
        market.PROB_OFERTA_POR_JORNADA, D.PROB_OFERTA_EXTERIOR = viejo_loc, viejo_ext
    assert not e.get('ofertas_recibidas')                                  # nada en el acto
    tipos = {it['tipo'] for it in D.agenda(e)}
    assert {'oferta', 'oferta_ext'} <= tipos
    assert all(date.fromisoformat(it['fecha']) < CAL.fecha_liga(e, 2) for it in D.agenda(e))
    D.hasta_el_partido(e)
    assert e.get('ofertas_recibidas') and D.agenda(e) == []                # llegaron en los días del hueco


def _plantel_sano(e):
    for j in e['mi_equipo'].jugadores:
        j.personalidad, j.moral, j.energia = 'normal', 70, 100.0
        j.pide_salir = j.salida_forzada = j.transferible = False
        j.prestamo = None


def test_el_aviso_de_renovar_llega_en_un_dia_sorteado():
    from alpha_football import salidas as S
    e = _e(); _en_j1(e); _plantel_sano(e)
    j = e['mi_equipo'].jugadores[0]
    j.contrato_anios, j.moral, j.renovacion_avisada = 1, 90, False
    CAL.asegurar(e)['dia'] = '2027-02-01'                                  # v0.4.13.0: pasada la mitad de la temporada (por fecha)
    S.cierre_jornada(e, random.Random(1))
    assert not [m for m in C.bandeja(e) if 'quiere renovar' in m['asunto']]
    assert any('quiere renovar' in it['datos'].get('asunto', '') for it in D.agenda(e))
    json.dumps(e['datos_carrera'])
    D.asignar_dias(e); D.entregar(e, date(2100, 1, 1))                     # el reloj ya pasó de los partidos pendientes
    assert [m for m in C.bandeja(e) if 'quiere renovar' in m['asunto']]


def test_sin_reloj_el_aviso_de_renovar_sigue_cayendo_en_el_acto():
    from alpha_football import salidas as S
    e = _e(); _plantel_sano(e)
    j = e['mi_equipo'].jugadores[0]
    j.contrato_anios, j.moral, j.renovacion_avisada = 1, 90, False
    e['liga'].jornada_actual = 12
    S.cierre_jornada(e, random.Random(1))
    assert [m for m in C.bandeja(e) if 'quiere renovar' in m['asunto']] and D.agenda(e) == []


def test_el_descontento_llega_en_un_dia_sorteado():
    from alpha_football import salidas as S
    e = _e(); _en_j1(e); _plantel_sano(e)
    j = e['mi_equipo'].jugadores[0]
    j.moral, j.descontento_avisado = 20, False
    S.cierre_jornada(e, random.Random(1))
    assert not [m for m in C.bandeja(e) if 'descontento' in m['asunto']]
    assert any('descontento' in it['datos'].get('asunto', '') for it in D.agenda(e))
    D.hasta_el_partido(e)
    assert [m for m in C.bandeja(e) if 'descontento' in m['asunto']]


def test_las_ofertas_garantizadas_llegan_un_dia_despues_de_cerrar():
    from alpha_football import salidas as S
    e = _e(); _en_j1(e); _plantel_sano(e); e['liga'].jornada_actual = 2   # ventana abierta
    j = e['mi_equipo'].jugadores[0]
    j.pide_salir, j.moral = True, 30
    S.cierre_jornada(e, random.Random(1))
    assert not e.get('ofertas_recibidas') and any(it['tipo'] == 'garantizadas' for it in D.agenda(e))
    r = D.hasta_el_partido(e)
    assert r['ofertas'] >= 1 and e['ofertas_recibidas']


def test_el_evento_de_vestuario_llega_en_un_dia_sorteado():
    from alpha_football import eventos as EV
    e = _e(); _en_j1(e); _plantel_sano(e)
    for s in range(300):                                                   # 12% por jornada: alguna semilla lo da
        EV.cierre_jornada(e, random.Random(s))
        if D.agenda(e):
            break
    assert D.agenda(e), "ningún sorteo dio evento"
    assert not [m for m in C.bandeja(e) if m.get('evento')] and EV.pendiente(e) is None
    json.dumps(e['datos_carrera'])
    r = D.hasta_el_partido(e)
    assert r['eventos'] == 1 and EV.pendiente(e) is not None               # ya se puede decidir


def _hub(e):
    D.hoy(e); e['datos_carrera']['aviso_mercado_visto'] = [1, D.hoy(e).isoformat()]   # v0.4.13.0: sin el cartel de apertura (por fecha)
    from alpha_football.ui import league_screen as L
    return L


def test_el_hub_crea_el_reloj_muestra_continuar_y_avanza_con_d_y_enter():
    e = _e(); L = _hub(e)
    pygame.event.clear(); assert L.render(screen, e) is None               # el hub crea el reloj
    assert D.activo(e) and D.es_dia_de_continuar(e)
    info = L._info_partido(e, e['liga'], e['mi_equipo'])
    assert L._textos_jugar(e['liga'], e['mi_equipo'], info, e)[0] == "CONTINUAR"
    antes = D.hoy(e)
    key(pygame.K_d); assert L.render(screen, e) is None
    assert D.hoy(e) == antes + timedelta(days=1) and e['hub_toast'][0].startswith("Pasó 1 día")
    key(pygame.K_RETURN); assert L.render(screen, e) is None               # el foco está en el botón grande
    for _ in range(400):                                                   # v0.4.14.1: los días pasan a la vista, uno por cuadro
        if not e.get('hub_avance'):
            break
        e['hub_avance']['sig'] = 0
        pygame.event.clear(); assert L.render(screen, e) is None
    assert D.hoy(e) == CAL.fecha_liga(e, 1) and e['hub_toast'][0].startswith("Pasaron")
    assert L._textos_jugar(e['liga'], e['mi_equipo'], info, e)[0] == "JUGAR"
    key(pygame.K_d); assert L.render(screen, e) is None                    # día de partido: D no hace nada
    assert D.hoy(e) == CAL.fecha_liga(e, 1)
    key(pygame.K_RETURN); assert L.render(screen, e) == 'prepartido_screen'


def test_el_boton_mas_un_dia_con_clic_y_solo_si_no_hay_partido():
    e = _e(); L = _hub(e)
    pygame.event.clear(); L.render(screen, e)
    assert L.R_JUGAR.contains(L.R_DIA) and L.R_DIA.bottom <= L.R_JUGAR.bottom
    antes = D.hoy(e)
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=L.R_DIA.center, button=1))
    assert L.render(screen, e) is None and D.hoy(e) == antes + timedelta(days=1)
    D.hasta_el_partido(e)
    dia = D.hoy(e)
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=L.R_DIA.center, button=1))
    res = L.render(screen, e)
    assert D.hoy(e) == dia and res == 'prepartido_screen'                  # ese clic cae en JUGAR, no avanza


def test_la_pantalla_calendario_resalta_el_dia_del_reloj():
    from alpha_football.ui import calendario_screen as KS
    e = _e(); _con_copa(e)
    pygame.event.clear(); assert KS.render(screen, e) is None
    assert D.activo(e) and e['cal_mes'] == [2026, 7]                       # abre en el mes de hoy (1 de julio)
    D.hasta_el_partido(e); _jugar(e, 1); D.hasta_el_partido(e); _jugar(e, 2); D.hasta_el_partido(e)
    e.pop('cal_mes', None)
    pygame.event.clear(); assert KS.render(screen, e) is None
    assert e['cal_mes'] == [D.hoy(e).year, D.hoy(e).month]                 # hoy = la fecha de la copa


def test_atajo_y_ayuda_del_hub_conocen_los_dias():
    from alpha_football.ui import atajos, ayuda, league_screen as L
    e = _e(); e['hub_tab'] = 'inicio'
    assert "D +1 Día" in atajos.ATAJOS['league_screen']
    its = ayuda.items('league_screen', e)
    assert any(r == L.R_DIA and t == "+1 DÍA" and len(x) <= 110 for r, t, x in its)
    assert all(len(x) <= 110 for _r, _t, x in its)


if __name__ == '__main__':
    TESTS =[v for k, v in sorted(globals().items()) if k.startswith('test_') and callable(v)]
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
