"""v0.4.14.0: el último día de fichajes (20 horas, costos, "lo analizamos", cierre y hub)."""
import sys, os, random, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
from datetime import date, timedelta
from test_calendario import screen, key, _e, _jugar, _con_copa   # noqa: E402  (deja save.guardar_en_slot sin efecto)
from alpha_football import calendario as CAL, correo as C, dias as D, temporada as T, dia_final as DF


def _en_el_ultimo_dia():
    """Partida con J1 y J2 jugadas y el reloj recién llegado al 31 de agosto (20 horas)."""
    e = _e(); D.hoy(e); _jugar(e, 1); _jugar(e, 2)
    CAL.asegurar(e)['dia'] = '2026-08-30'
    r = D.avanzar_dia(e)
    return e, r


def test_el_ultimo_dia_se_abre_al_llegar_el_reloj_al_cierre_con_20_horas():
    e, r = _en_el_ultimo_dia()
    assert D.hoy(e) == date(2026, 8, 31) and r['hito'] == 'ultimo'
    assert DF.activo(e) and DF.horas(e) == 20 and not DF.cerrado(e)
    assert T.ventana_abierta(e) and T.ultimo_dia(e)
    assert T.hito_del_dia(e, date(2026, 8, 31)) == 'ultimo' and T.hito_del_dia(e, date(2026, 9, 1)) is None
    assert T.hito_del_dia(e, date(2026, 7, 1)) == 'abre'


def test_con_horas_el_dia_no_pasa_ni_con_mas_un_dia_ni_con_continuar():
    e, _ = _en_el_ultimo_dia()
    assert not D.es_dia_de_continuar(e) and D.avanzar_dia(e)['dias'] == 0
    assert D.continuar(e)['dias'] == 0 and D.hoy(e) == date(2026, 8, 31)


def test_hasta_el_partido_cierra_el_ultimo_dia_solo():
    e = _e(); D.hoy(e); _jugar(e, 1); _jugar(e, 2)
    CAL.asegurar(e)['dia'] = '2026-08-22'
    D.hasta_el_partido(e)                                                  # pasa por el 31 de agosto sin quedarse
    assert D.hoy(e) == CAL.fecha_liga(e, 3) and not T.ventana_abierta(e)
    assert any(m['asunto'] == "Se cerró el mercado de pases" for m in C.bandeja(e))


def test_avanzar_hora_gasta_una_hora_y_a_las_cero_se_cierra_el_mercado():
    e, _ = _en_el_ultimo_dia()
    for _ in range(19):
        assert DF.avanzar_hora(e, random.Random(1))['horas'] == 1
    assert DF.horas(e) == 1 and DF.activo(e)
    r = DF.avanzar_hora(e, random.Random(1))
    assert r['cerro'] and DF.horas(e) == 0 and not DF.activo(e) and DF.cerrado(e) and not T.ventana_abierta(e)
    assert e['aviso_mercado_activo']['tipo'] == 'cierra'
    assert DF.avanzar_hora(e)['horas'] == 0                                # cerrado: no gasta más
    assert D.es_dia_de_continuar(e) and D.avanzar_dia(e)['dias'] == 1 and D.hoy(e) == date(2026, 9, 1)


def test_los_costos_en_horas_y_fuera_del_ultimo_dia_es_gratis():
    e, _ = _en_el_ultimo_dia()
    assert DF.gastar(e, DF.HORAS_FICHAJE) and DF.horas(e) == 17
    assert DF.gastar(e, DF.HORAS_VENTA) and DF.horas(e) == 15
    assert not DF.gastar(e, 99) and DF.horas(e) == 15                      # no alcanza: no gasta
    f = _e(); D.hoy(f)
    assert DF.gastar(f, 3) is True and not DF.activo(f)                    # un día cualquiera: sin horas


def test_un_save_cargado_el_31_arranca_con_20_horas_y_el_dia_cerrado_se_conserva():
    e = _e(); D.hoy(e); _jugar(e, 1); _jugar(e, 2)
    CAL.asegurar(e)['dia'] = '2026-08-31'                                  # cargado en el último día, sin abrir
    assert not DF.activo(e) and DF.abrir(e) and DF.horas(e) == 20
    assert not DF.abrir(e)                                                 # ya estaba abierto
    DF.cerrar(e)
    f = _e(); f['datos_carrera'] = json.loads(json.dumps(e['datos_carrera']))
    assert DF.cerrado(f) and not DF.activo(f) and not DF.abrir(f)          # cerrado, sigue cerrado al cargar


def test_cada_hora_puede_entrar_una_oferta_con_el_10_o_el_25_por_ciento():
    e, _ = _en_el_ultimo_dia()
    for j in e['mi_equipo'].jugadores:
        j.transferible = j.pide_salir = False
    assert DF.prob_oferta_hora(e) == 0.10
    e['mi_equipo'].jugadores[3].transferible = True
    assert DF.prob_oferta_hora(e) == 0.25
    llamadas = []
    original = D._entregar_oferta
    original_noticias = DF.noticias_de_la_hora
    D._entregar_oferta = lambda estado, exterior: llamadas.append(exterior) or 1
    DF.noticias_de_la_hora = lambda *a, **k: 0                          # 4.000 horas: las noticias no son de esta prueba
    try:
        for transf, esperado in ((False, 0.10), (True, 0.25)):
            e['mi_equipo'].jugadores[3].transferible = transf
            llamadas.clear(); rng = random.Random(5); N = 2000
            for _ in range(N):
                DF._bloque(e)['horas'] = 20                                # que no cierre
                DF.avanzar_hora(e, rng)
            assert abs(len(llamadas) / N - esperado) < 0.03, (transf, len(llamadas) / N)
            assert not any(llamadas)                                       # son ofertas locales, no del exterior
    finally:
        D._entregar_oferta = original
        DF.noticias_de_la_hora = original_noticias


def test_cada_hora_trae_noticias_y_reinicia_el_feed():
    """v0.4.25.0: el último día las noticias se actualizan cada hora (pasada ligera de fichajes + rumores)."""
    from alpha_football import mercado_ia as MIA, rumores as RU, noticias as NO
    e, _ = _en_el_ultimo_dia()
    modos, rumores_horas = [], []
    orig_ronda, orig_rum = MIA.ronda_fichajes_ia, RU.revisar_hora

    def _ronda(estado, modo='ventana', rng=None):
        modos.append(modo)
        NO.publicar(estado, 'fichaje', f"Fichaje {len(modos)}", "Cuerpo", importancia=4)
        return []
    MIA.ronda_fichajes_ia = _ronda
    RU.revisar_hora = lambda estado, rng=None: rumores_horas.append(1) or 0
    try:
        e['feed_t0'] = 123
        DF._bloque(e)['horas'] = 10
        r = DF.avanzar_hora(e, random.Random(2))
        assert modos == ['hora'] and rumores_horas == [1]               # una pasada por hora, ligera
        assert r['horas'] == 1 and r['noticias'] == 1
        assert 'feed_t0' not in e                                        # el hub vuelve a las más recientes
        assert "1 noticia" in DF.texto_hora(r)
        assert "noticia" not in DF.texto_hora({'horas': 1, 'noticias': 0})
        assert DF.gastar(e, DF.HORAS_FICHAJE)                            # un fichaje cuesta 3 horas: 3 pasadas
        assert modos == ['hora'] * 4
    finally:
        MIA.ronda_fichajes_ia, RU.revisar_hora = orig_ronda, orig_rum


def test_la_ultima_hora_no_hace_pasada_porque_cierra_la_ronda_de_cierre():
    from alpha_football import mercado_ia as MIA
    e, _ = _en_el_ultimo_dia()
    modos = []
    orig = MIA.ronda_fichajes_ia
    MIA.ronda_fichajes_ia = lambda estado, modo='ventana', rng=None: modos.append(modo) or []
    try:
        DF._bloque(e)['horas'] = 1
        r = DF.avanzar_hora(e, random.Random(2))
        assert r['cerro'] and modos == ['ventana']                       # solo la ronda de cierre
    finally:
        MIA.ronda_fichajes_ia = orig


def test_cerrar_retira_ofertas_cae_los_analisis_hace_la_ronda_y_no_se_repite():
    from alpha_football import mercado_ia as MIA
    e, _ = _en_el_ultimo_dia(); mi, liga = e['mi_equipo'], e['liga']
    e['ofertas_recibidas'] = [{'jugador': mi.jugadores[3], 'comprador': liga.equipos[1], 'monto': 1}]
    dc = e['datos_carrera']
    dc['analisis_compras'] = [{'jugador_id': 1, 'club_id': 2, 'club': 'X', 'jugador': 'Y', 'monto': 5,
                               'jornada': 3, 'temporada': 1, 'hora_resp': 10},
                              {'jugador_id': 7, 'club_id': 2, 'club': 'X', 'jugador': 'Z', 'monto': 5,
                               'jornada': 3, 'temporada': 1}]                  # el de la jornada siguiente se queda
    llamadas = []
    original = MIA.ronda_fichajes_ia
    MIA.ronda_fichajes_ia = lambda estado, modo='ventana', rng=None: llamadas.append(modo) or []
    try:
        r = DF.cerrar(e)
        assert DF.cerrar(e) == {'ofertas': 0, 'analisis': 0, 'ronda': False}   # idempotente
    finally:
        MIA.ronda_fichajes_ia = original
    assert r == {'ofertas': 1, 'analisis': 1, 'ronda': True} and llamadas == ['ventana']
    assert e['ofertas_recibidas'] == [] and [a['jugador'] for a in dc['analisis_compras']] == ['Z']
    caidos = [m for m in C.bandeja(e) if "Se cayó el trato por Y" in m['asunto']]
    assert len(caidos) == 1 and "se acabó el mercado" in caidos[0]['cuerpo'].lower()
    assert len([m for m in C.bandeja(e) if m['asunto'] == "Se cerró el mercado de pases"]) == 1


def test_un_fichaje_cuesta_3_horas_y_con_menos_queda_acordado_para_la_proxima_ventana():
    from alpha_football import negociacion as N, traspasos_pendientes as TP
    e, _ = _en_el_ultimo_dia(); mi, liga = e['mi_equipo'], e['liga']; mi.balance = 10 ** 12
    DF._bloque(e)['horas'] = 2
    club, j = liga.equipos[1], liga.equipos[1].jugadores[0]
    ok, msg = N.fichar(e, j, club, 1_000)
    assert ok and TP.pendiente_de(e, j) is not None and j not in mi.jugadores and DF.horas(e) == 2
    DF._bloque(e)['horas'] = 5
    club2, j2 = liga.equipos[2], liga.equipos[2].jugadores[0]
    ok, msg = N.fichar(e, j2, club2, 1_000)
    assert ok and j2 in mi.jugadores and TP.pendiente_de(e, j2) is None and DF.horas(e) == 2


def test_una_venta_cuesta_2_horas_y_sin_horas_queda_acordada():
    from alpha_football import contraofertas as CO, traspasos_pendientes as TP
    e, _ = _en_el_ultimo_dia(); mi, comp = e['mi_equipo'], e['liga'].equipos[1]; comp.balance = 10 ** 12
    j = mi.jugadores[8]
    assert CO.vender(e, {'jugador': j, 'comprador': comp, 'monto': 5_000_000}) and j not in mi.jugadores
    assert DF.horas(e) == 18
    j2 = mi.jugadores[8]; DF._bloque(e)['horas'] = 1
    assert CO.vender(e, {'jugador': j2, 'comprador': comp, 'monto': 5_000_000})
    assert TP.pendiente_de(e, j2) is not None and j2 in mi.jugadores and DF.horas(e) == 1


def test_fuera_del_ultimo_dia_las_puertas_no_cobran_horas():
    from alpha_football import contraofertas as CO
    e = _e(); D.hoy(e); mi, comp = e['mi_equipo'], e['liga'].equipos[1]; comp.balance = 10 ** 12
    j = mi.jugadores[8]
    assert CO.vender(e, {'jugador': j, 'comprador': comp, 'monto': 5_000_000}) and j not in mi.jugadores
    assert DF.horas(e) == 0 and not DF.activo(e)


def test_un_prestamo_que_llega_cuesta_3_horas_y_una_cesion_2():
    from alpha_football import prestamos as PR
    e, _ = _en_el_ultimo_dia(); mi, otro = e['mi_equipo'], e['liga'].equipos[1]
    j = otro.jugadores[0]
    PR.iniciar(e, j, otro, mi, 6, 50)                                      # llega a tu club
    assert j in mi.jugadores and DF.horas(e) == 17
    j2 = mi.jugadores[10]
    PR.iniciar(e, j2, mi, otro, 6, 50)                                     # tu jugador se va cedido
    assert j2 in otro.jugadores and DF.horas(e) == 15


def test_vencido_por_jornada_como_siempre_o_por_hora():
    e, _ = _en_el_ultimo_dia()
    liga = e['liga']; liga.jornada_actual = 3
    assert not DF.vencido(e, {'jornada': 3}) and DF.vencido(e, {'jornada': 2})        # la regla de siempre
    assert DF.vencido(e, {'jornada': 3, 'temporada': 7})                              # otra temporada: ya toca
    assert not DF.vencido(e, {'jornada': 3, 'hora_resp': 17}) and DF.horas(e) == 20
    DF._bloque(e)['horas'] = 17
    assert DF.vencido(e, {'jornada': 3, 'hora_resp': 17})                             # llegó su hora
    CAL.asegurar(e)['dia'] = '2026-09-02'
    assert DF.vencido(e, {'jornada': 3, 'hora_resp': 5})                              # el día final ya pasó


def test_analisis_con_horas_responde_a_las_3_horas_y_con_menos_no_hay_tiempo():
    from alpha_football import contraofertas as CO
    e, _ = _en_el_ultimo_dia(); mi, comp = e['mi_equipo'], e['liga'].equipos[1]
    assert DF.analisis(e) == (True, 17) and DF.texto_respuesta(17) == "Te responden en 3 horas."
    assert DF.texto_respuesta(None) == "Te responden por correo en la próxima jornada."
    of = {'jugador': mi.jugadores[4], 'comprador': comp, 'monto': 900, 'tope': 1000}
    e['ofertas_recibidas'] = [of]
    res, msg = CO.contraofertar(e, of, 1001)
    assert res == 'analizando' and of['contra']['hora_resp'] == 17 and "3 horas" in msg
    DF.avanzar_hora(e, random.Random(2)); DF.avanzar_hora(e, random.Random(2))
    assert of['contra']['estado'] == 'analizando' and DF.horas(e) == 18               # todavía no es su hora
    n0 = len(C.bandeja(e))
    DF.avanzar_hora(e, random.Random(2))                                              # la tercera hora: responde
    assert len(C.bandeja(e)) > n0 and of not in e['ofertas_recibidas']                # acepta (vende) o se retira
    DF._bloque(e)['horas'] = 2                                                        # menos de 3 horas
    of2 = {'jugador': mi.jugadores[5], 'comprador': comp, 'monto': 900, 'tope': 1000}
    e['ofertas_recibidas'] = [of2]
    res, msg = CO.contraofertar(e, of2, 1001)
    assert res == 'rechazada' and "no hay tiempo" in msg and e['ofertas_recibidas'] == []


def test_un_analisis_que_vence_justo_a_las_0_horas_se_responde_antes_de_cerrar():
    from alpha_football import negociacion as N
    from alpha_football.data.clasicos import es_clasico
    e, _ = _en_el_ultimo_dia(); mi, liga = e['mi_equipo'], e['liga']
    club = next(x for x in liga.equipos[1:] if not es_clasico(x, mi))               # el clásico solo vende por la cláusula
    j = club.jugadores[0]
    DF._bloque(e)['horas'] = 3
    minimo = N.minimo_club(j, club)
    res, msg, _c = N.evaluar_compra(e, j, club, int(minimo * N.UMBRAL_ANALISIS) + 1)
    assert res == 'analiza' and "3 horas" in msg
    assert e['datos_carrera']['analisis_compras'][0]['hora_resp'] == 0
    DF.avanzar_hora(e, random.Random(1)); DF.avanzar_hora(e, random.Random(1)); DF.avanzar_hora(e, random.Random(1))
    assert DF.cerrado(e) and e['datos_carrera']['analisis_compras'] == []
    asuntos = [m['asunto'] for m in C.bandeja(e)]
    assert any("acepta tu oferta" in a or "rechaza tu oferta" in a for a in asuntos)  # respondió antes de cerrar
    assert not any("Se cayó el trato" in a for a in asuntos)


def _hub_ultimo(e):
    from alpha_football.ui import league_screen as L
    e['datos_carrera']['aviso_mercado_visto'] = [1, '2026-08-31']          # sin el cartel de inicio del día
    return L


def test_el_hub_muestra_el_panel_del_dia_y_avanza_horas_con_enter_y_clic():
    e, _ = _en_el_ultimo_dia(); L = _hub_ultimo(e)
    info = L._info_partido(e, e['liga'], e['mi_equipo'])
    l1, l2, l3, hab = L._textos_jugar(e['liga'], e['mi_equipo'], info, e)
    assert l1 == "ÚLTIMO DÍA" and "quedan 20 h" in l2 and l3 == "" and hab
    pygame.event.clear(); assert L.render(screen, e) is None
    key(pygame.K_RETURN); assert L.render(screen, e) is None
    assert DF.horas(e) == 19 and e['hub_toast'][0].startswith("Pasó 1 hora")
    assert L.R_JUGAR.contains(L.R_HORA) and L.R_JUGAR.contains(L.R_CERRAR) and not L.R_HORA.colliderect(L.R_CERRAR)
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=L.R_HORA.center, button=1))
    assert L.render(screen, e) is None and DF.horas(e) == 18
    key(pygame.K_d); L.render(screen, e); assert D.hoy(e) == date(2026, 8, 31) and DF.horas(e) == 18   # D no pasa el día


def test_cerrar_el_mercado_pide_confirmacion_y_despues_el_dia_sigue():
    e, _ = _en_el_ultimo_dia(); L = _hub_ultimo(e)
    pygame.event.clear(); L.render(screen, e)
    key(pygame.K_c); L.render(screen, e)
    assert e.get('confirmar_cierre_mercado') and DF.horas(e) == 20          # primera vez: solo pregunta
    key(pygame.K_RETURN); L.render(screen, e)                               # Enter confirma
    assert DF.cerrado(e) and not e.get('confirmar_cierre_mercado') and not T.ventana_abierta(e)
    info = L._info_partido(e, e['liga'], e['mi_equipo'])
    assert L._textos_jugar(e['liga'], e['mi_equipo'], info, e)[0] == "CONTINUAR"


def test_la_franja_el_cartel_y_los_textos_del_ultimo_dia():
    from alpha_football.ui import aviso_mercado as AM
    e, _ = _en_el_ultimo_dia()
    assert AM._texto_franja(e) == ("ÚLTIMO DÍA · quedan 20 h", 'dorado')
    assert AM._texto_franja(e, True) == ("ÚLTIMO DÍA · 20 h", 'dorado')
    assert AM.evento_pendiente(e) == ('ultimo', '2026-08-31')
    AM._abrir(e, 'ultimo', '2026-08-31')
    assert e['aviso_mercado_activo']['tipo'] == 'ultimo' and AM.evento_pendiente(e) is None
    asunto = [m for m in C.bandeja(e) if m['asunto'] == "Último día de fichajes"]
    assert asunto and "20 horas" in asunto[0]['cuerpo']
    DF.cerrar(e)
    assert AM._texto_franja(e) is None and DF.texto_hora({'horas': 1, 'correos': 1, 'ofertas': 1}) == "Pasó 1 hora: 1 oferta, 1 correo"
    assert DF.texto_hora({'horas': 1, 'cerro': True}) == "Pasó 1 hora: se cerró el mercado"


def test_la_ronda_de_cierre_de_la_ia_ve_el_mercado_abierto_cierres_por_horas_o_a_mano():
    from alpha_football import mercado_ia as MIA
    vistos = []
    original = MIA.ronda_fichajes_ia
    MIA.ronda_fichajes_ia = lambda estado, modo='ventana', rng=None: vistos.append(T.ventana_abierta(estado)) or []
    try:
        e, _ = _en_el_ultimo_dia(); DF.cerrar(e)                                          # CERRAR MERCADO
        f, _ = _en_el_ultimo_dia(); DF._bloque(f)['horas'] = 1
        assert DF.avanzar_hora(f, random.Random(1))['cerro']                              # llega a 0 horas
    finally:
        MIA.ronda_fichajes_ia = original
    assert vistos == [True, True]                                                         # la ronda de cierre ve el mercado abierto
    assert DF.cerrado(e) and DF.cerrado(f) and not T.ventana_abierta(e) and not T.ventana_abierta(f)


def test_el_panel_del_ultimo_dia_no_pisa_sus_botones_ni_se_sale_del_boton():
    e, _ = _en_el_ultimo_dia(); L = _hub_ultimo(e)
    llamadas, original = [], L.draw_text

    def _espia(scr, txt, pos, *a, **k):
        llamadas.append((txt, pos, k.get('size', a[0] if a else 'md')))
        return original(scr, txt, pos, *a, **k)
    L.draw_text = _espia
    try:
        pygame.event.clear(); L.render(screen, e)
    finally:
        L.draw_text = original
    cajas = {txt: pygame.Rect(pos, L.get_font(size).size(txt)) for txt, pos, size in llamadas
             if L.R_JUGAR.collidepoint(pos)}
    titulo = cajas["ÚLTIMO DÍA"]
    linea = next(r for t, r in cajas.items() if "quedan 20 h" in t)        # la fecha y las horas
    assert L.R_JUGAR.contains(linea) and L.R_JUGAR.contains(titulo)
    for boton in (L.R_HORA, L.R_CERRAR):
        assert L.R_JUGAR.contains(boton)
        assert not linea.colliderect(boton) and not titulo.colliderect(boton), (linea, titulo, boton)
    assert not linea.colliderect(titulo)


def test_la_confirmacion_de_cierre_se_cancela_al_cambiar_de_pestana_al_salir_y_al_pasar_las_horas():
    e, _ = _en_el_ultimo_dia(); L = _hub_ultimo(e)
    pygame.event.clear(); L.render(screen, e)
    key(pygame.K_c); L.render(screen, e); assert e.get('confirmar_cierre_mercado')
    key(pygame.K_RIGHT); L.render(screen, e)                                # otra pestaña
    assert e['hub_tab'] != 'inicio' and not e.get('confirmar_cierre_mercado')
    key(pygame.K_ESCAPE); L.render(screen, e); assert e['hub_tab'] == 'inicio'
    key(pygame.K_RETURN); L.render(screen, e)                               # Enter ya no confirma: pasa una hora
    assert not DF.cerrado(e) and DF.horas(e) == 19
    key(pygame.K_c); L.render(screen, e); assert e.get('confirmar_cierre_mercado')
    e['pantalla_anterior'] = 'plantilla_screen'                             # lo que deja main.py al volver de otra pantalla
    pygame.event.clear(); L.render(screen, e)
    assert not e.get('confirmar_cierre_mercado')
    key(pygame.K_c); L.render(screen, e); assert e.get('confirmar_cierre_mercado')
    assert DF.gastar(e, DF.HORAS_FICHAJE)                                   # pasan horas por otro camino (un fichaje)
    key(pygame.K_RETURN); L.render(screen, e)
    assert not DF.cerrado(e) and DF.horas(e) == 15 and not e.get('confirmar_cierre_mercado')   # 19 − 3 − 1: avanzó, no cerró
    key(pygame.K_c); L.render(screen, e); assert e.get('confirmar_cierre_mercado')
    key(pygame.K_c); L.render(screen, e)                                    # la confirmación vigente sí cierra
    assert DF.cerrado(e)


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
