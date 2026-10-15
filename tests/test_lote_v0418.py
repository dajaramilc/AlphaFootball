"""v0.4.18.0: ritmo de la simulación, ofertas en cifras cerradas, canteranos, historial de pases,
animación de horas del último día, correo de reprogramación y racha de victorias."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
screen = pygame.display.set_mode((1280, 720))
from alpha_football import save
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402
from test_calendario import _e as _e_cal, _con_copa, _jugar, _reprogramados   # noqa: E402
from test_vestuario_v310 import _estado as _estado_vestuario   # noqa: E402
from alpha_football import calendario as CAL, correo as C, vestuario as V


# ---------- 6. correo de partido reprogramado ----------

def test_correo_reprogramado_no_menciona_los_dias_de_descanso():
    e = _e_cal(); _con_copa(e, fecha=0); _jugar(e, 1); _jugar(e, 2)
    cal = CAL.asegurar(e)
    cal['mov']['copa:champions:0'] = '2026-09-03'                         # jueves
    cal['mov']['liga:3'] = '2026-09-05'                                   # sábado: a 2 días
    CAL.revisar_choques(e)
    m = _reprogramados(e)[0]
    assert 'descanso' not in m['cuerpo'] and 'Para respetar' not in m['cuerpo'], m['cuerpo']
    assert 'dom 6 sep' in m['cuerpo'] and 'Quedaba demasiado cerca' in m['cuerpo'], m['cuerpo']
    assert m['cuerpo'].startswith('La jornada 3 de liga contra'), m['cuerpo']   # sigue diciendo qué partido se movió


# ---------- 7. racha de victorias ----------

HITOS_RACHA = (3, 5, 10, 15, 20, 25, 30)


def _jugar_resultado(e, gf, gc, veces=1):
    mi = e['mi_equipo']; rival = e['liga'].equipos[1]
    for _ in range(veces):
        V.post_partido_user(e, mi, rival, gf, gc, [], {mi.jugadores[0].id: 90}, rng=random.Random(1))


def _avisos_racha(e):
    return [m for m in C.bandeja(e) if 'victorias seguidas' in m['asunto']]


def test_felicita_solo_al_llegar_a_3_5_10_15_20_25_y_30():
    e = _estado_vestuario()
    vistos = []
    for n in range(1, 36):
        antes = len(_avisos_racha(e))
        _jugar_resultado(e, 1, 0)
        if len(_avisos_racha(e)) > antes:
            vistos.append(n)
    assert vistos == list(HITOS_RACHA), vistos       # antes: salía en 3, 6, 9, 12...


def test_cada_felicitacion_es_distinta_y_mas_asombrada():
    e = _estado_vestuario()
    _jugar_resultado(e, 1, 0, veces=30)
    avisos = list(reversed(_avisos_racha(e)))        # la bandeja guarda el más nuevo primero
    assert len(avisos) == 7
    assert len({m['cuerpo'] for m in avisos}) == 7 and len({m['asunto'] for m in avisos}) == 7
    exclamaciones = [m['cuerpo'].count('!') for m in avisos]
    assert exclamaciones == sorted(exclamaciones) and exclamaciones[-1] > exclamaciones[0], exclamaciones
    assert all(m['remitente'] == 'presidente' for m in avisos)


def test_un_empate_o_derrota_reinicia_la_cuenta_de_victorias():
    e = _estado_vestuario()
    _jugar_resultado(e, 1, 0, veces=3)
    assert len(_avisos_racha(e)) == 1
    _jugar_resultado(e, 0, 0)                        # el empate corta la racha
    _jugar_resultado(e, 1, 0, veces=2)
    assert len(_avisos_racha(e)) == 1                # solo 2 desde el empate
    _jugar_resultado(e, 1, 0)
    assert len(_avisos_racha(e)) == 2                # 3 otra vez: vuelve a felicitar el hito de 3
    assert _avisos_racha(e)[0]['asunto'] == _avisos_racha(e)[1]['asunto']


def test_tres_derrotas_y_ult_res_siguen_igual():
    e = _estado_vestuario()
    _jugar_resultado(e, 1, 0, veces=3)
    _jugar_resultado(e, 0, 1, veces=3)
    derrotas = [m for m in C.bandeja(e) if m['asunto'].startswith("Tres derrotas seguidas")]
    assert len(derrotas) == 1
    assert e['datos_carrera']['ult_res'] == ['P', 'P', 'P']
    from alpha_football import eventos
    assert eventos.va_mal(e)


def test_cambiar_de_club_borra_la_cuenta_de_victorias():
    from alpha_football import directiva as D
    e = _estado_vestuario()
    _jugar_resultado(e, 1, 0, veces=4)
    assert e['datos_carrera'].get('racha_g') == 4
    D.cambiar_de_club(e, D.opciones_de_club(e)[0])
    assert not e['datos_carrera'].get('racha_g')


# ---------- 3. canteranos: 10 de diferencia, potencial que sube con la media, boost menor ----------

def _juvenil(ovr, pot, edad=17):
    from alpha_football.models import Jugador
    j = Jugador(nombre="Ca", apellido="Ntera", posicion="MED",
                ataque=ovr, defensa=ovr, fisico=ovr, tecnica=ovr, mental=ovr, edad=edad, potencial=pot)
    return j


def test_canterano_nace_con_al_menos_10_de_diferencia():
    import alpha_football.market as M
    from alpha_football import cantera as K
    e = estado_carrera(); mi = e['mi_equipo']
    real = M.nivel_club
    try:
        for nivel in (50, 70, 85, 95):                     # a nivel 95 la joya toparía el potencial en 99
            M.nivel_club = lambda _eq, n=nivel: n
            rng = random.Random(nivel)
            for i in range(120):
                j = K.generar_canterano(e, mi, rng, joya=(i % 4 == 0))
                assert j.potencial - j.overall >= 10, (nivel, j.joya, j.overall, j.potencial)
                assert j.potencial <= 99 and j.overall <= 89, (nivel, j.overall, j.potencial)
    finally:
        M.nivel_club = real


def test_crecer_sube_el_potencial_lo_mismo_que_la_media():
    from alpha_football import cantera as K
    vistos = set()
    for semilla in range(200):
        j = _juvenil(60, 72)
        sube = K._crecer(j, random.Random(semilla))
        vistos.add(sube)
        assert j.overall == 60 + sube and j.potencial == 72 + sube, (sube, j.overall, j.potencial)
    assert vistos == {2, 3, 4, 5}, vistos                   # antes: +1 a +4 y sin pasar el potencial


def test_crecer_no_pasa_de_89_ni_deja_el_potencial_a_menos_de_10():
    from alpha_football import cantera as K
    for semilla in range(60):
        j = _juvenil(87, 97)
        K._crecer(j, random.Random(semilla))
        assert j.overall <= 89 and j.potencial <= 99 and j.potencial - j.overall >= 10, (j.overall, j.potencial)
    j = _juvenil(60, 63)                                    # cantera vieja: solo 3 de diferencia
    K._crecer(j, random.Random(1))
    assert j.potencial - j.overall >= 10, (j.overall, j.potencial)


def test_cantera_guardada_con_menos_de_10_se_corrige_al_cargar():
    from alpha_football import cantera as K
    e = estado_carrera()
    lista = K.cantera(e)
    for j in lista:
        j.potencial = j.overall + 3                         # como las de una partida anterior
    K._guardar(e, lista)
    nueva = K.cantera(e)
    assert all(j.potencial - j.overall >= 10 for j in nueva)
    assert all(c['potencial'] - (c['ataque'] + c['defensa'] + c['fisico'] + c['tecnica'] + c['mental']) // 5 >= 10
               for c in e['datos_carrera']['cantera'])      # y quedó guardado así


def test_boost_de_canterano_baja_a_1_35():
    from alpha_football import desarrollo as DS
    e = estado_carrera(); mi = e['mi_equipo']
    j = _juvenil(60, 75, edad=19)
    j.canterano = mi.nombre
    assert DS.BOOST_CANTERANO == 1.35 and DS.factor_canterano(j, mi) == 1.35
    assert 1.0 < DS.BOOST_CANTERANO < 1.5                   # sigue creciendo más que un normal, sin pasarse


# ---------- 5. animación de las horas del último día ----------

def test_gastar_horas_el_ultimo_dia_deja_anotada_la_animacion():
    from alpha_football import dia_final as DF
    from test_dia_final import _en_el_ultimo_dia
    e, _r = _en_el_ultimo_dia()
    assert 'anim_horas' not in e
    assert DF.gastar(e, DF.HORAS_FICHAJE) and DF.horas(e) == 17
    assert e['anim_horas'] == {'desde': 20, 'hasta': 17, 'motivo': "Fichaje concretado", 'inicio': None}, e['anim_horas']
    assert DF.gastar(e, DF.HORAS_VENTA) and DF.horas(e) == 15      # otra operación antes de verla: sigue la misma cuenta
    assert e['anim_horas'] == {'desde': 20, 'hasta': 15, 'motivo': "Venta concretada", 'inicio': None}, e['anim_horas']
    e['anim_horas']['hasta'] = 99                                  # una anotación que ya no encaja no se encadena
    assert DF.gastar(e, 2) and e['anim_horas']['desde'] == 15 and e['anim_horas']['hasta'] == 13


def test_gastar_horas_fuera_del_ultimo_dia_no_anima_ni_cobra():
    from alpha_football import dia_final as DF
    e = _e_cal()
    assert DF.gastar(e, DF.HORAS_FICHAJE) is True and 'anim_horas' not in e
    from test_dia_final import _en_el_ultimo_dia
    e2, _r = _en_el_ultimo_dia()
    DF.gastar(e2, 18)
    assert DF.gastar(e2, 99) is False                              # sin horas suficientes: no gasta ni anima
    assert DF.horas(e2) == 2 and e2['anim_horas']['hasta'] == 2
    assert DF.gastar(e2, DF.HORAS_FICHAJE) is True                 # v0.4.26.0: con 2 horas un fichaje entra y cierra
    assert DF.horas(e2) == 0 and e2['anim_horas']['desde'] == 20 and e2['anim_horas']['hasta'] == 0   # la cuenta sigue


def test_la_animacion_cuenta_una_hora_cada_500_ms_y_termina():
    from alpha_football.ui import horas_anim as HA
    anim = {'desde': 20, 'hasta': 17, 'motivo': "Fichaje concretado", 'inicio': 1000}
    horas = [HA.estado_anim(anim, t)['horas'] for t in (1000, 1499, 1500, 2000, 2499, 2500, 3000)]
    assert horas == [20, 20, 19, 18, 18, 17, 17], horas
    assert not HA.estado_anim(anim, 2500)['terminada']
    assert HA.estado_anim(anim, 2500 + HA.MS_PAUSA_FINAL)['terminada']
    assert HA.estado_anim({'desde': 20, 'hasta': 17, 'inicio': None}, 9999)['horas'] == 20   # aún sin empezar


def test_dibujar_horas_muestra_las_horas_corriendo_y_se_apaga():
    from alpha_football.ui import horas_anim as HA
    e = _e_cal()
    dibujado, restaurar = _capturar_texto(HA)
    try:
        HA.dibujar(screen, e, ahora=500)
        assert dibujado == []                                      # sin animación pendiente: no dibuja nada
        e['anim_horas'] = {'desde': 20, 'hasta': 17, 'motivo': "Fichaje concretado", 'inicio': None}
        HA.dibujar(screen, e, ahora=10_000)                        # primer cuadro: empieza a contar
        assert e['anim_horas']['inicio'] == 10_000 and "20 h" in dibujado, dibujado
        assert any("Fichaje concretado" in t for t in dibujado) and any("3 h" in t for t in dibujado)
        del dibujado[:]
        HA.dibujar(screen, e, ahora=11_500)
        assert "17 h" in dibujado and "20 h" not in dibujado, dibujado
        HA.dibujar(screen, e, ahora=11_500 + HA.MS_PAUSA_FINAL)
        assert 'anim_horas' not in e                               # terminó: se retira sola
    finally:
        restaurar()


# ---------- 4. historial de pases con fecha real, 8 por página; plantilla con 8 por página ----------

def _capturar_texto(modulo):
    """Cambia modulo.draw_text por uno que anota lo dibujado. Devuelve (lista, restaurar)."""
    dibujado, original = [], modulo.draw_text
    modulo.draw_text = lambda scr, txt, *a, **k: (dibujado.append(str(txt)), original(scr, txt, *a, **k))[1]
    return dibujado, lambda: setattr(modulo, 'draw_text', original)


def test_registrar_pase_guarda_la_fecha_real():
    from alpha_football import negociacion as N, dias as D
    e = _e_cal(); j = e['mi_equipo'].jugadores[3]
    D.hoy(e)                                            # el reloj de la partida ya existe cuando se ficha
    D.avanzar_dia(e)
    N.registrar_pase(e, j, 'Club A', 'Club B', 1_500_000, True)
    h = e['datos_carrera']['historial_pases'][-1]
    assert h['fecha'] == D.hoy(e).isoformat() and h['fecha'] > '2026-07-01', h


def test_texto_cuando_usa_la_fecha_y_respalda_los_registros_viejos():
    from alpha_football.ui import historial_pases_screen as H
    nuevo = {'temporada': 2, 'jornada': 7, 'fecha': '2026-10-04'}
    linea1, linea2 = H.texto_cuando(nuevo)
    assert 'dom 4 oct 2026' == linea1 and 'T2' in linea2 and 'J7' in linea2, (linea1, linea2)
    viejo = {'temporada': 1, 'jornada': 5}                         # guardado antes de v0.4.18.0: sin fecha
    assert H.texto_cuando(viejo) == ("T1 J5", "")
    assert H.texto_cuando({'temporada': 1, 'jornada': 5, 'fecha': 'basura'}) == ("T1 J5", "")
    assert H.texto_cuando({}) == ("T? J?", "")


def test_historial_de_pases_muestra_8_por_pagina_con_la_fecha():
    from alpha_football.ui import historial_pases_screen as H
    e = _e_cal()
    e['datos_carrera']['historial_pases'] = [
        {'temporada': 1, 'jornada': 1 + i, 'fecha': f"2026-09-{1 + i:02d}", 'jugador': f"Nombre{i} Apellido{i}",
         'posicion': 'MED', 'media': 70, 'de': 'Club A', 'a': 'Club B', 'monto': 2_000_000 + i, 'propio': False}
        for i in range(20)]
    assert H.FILAS_VISIBLES == 8 and H.FILA_Y0 + 8 * H.FILA_H <= H.R_LISTA.bottom
    dibujado, restaurar = _capturar_texto(H)
    try:
        pygame.event.clear(); assert H.render(screen, e) is None
    finally:
        restaurar()
    for i in range(19, 11, -1):                                    # los 8 más recientes
        assert f"Nombre{i} Apellido{i}" in dibujado, i
    assert "Nombre11 Apellido11" not in dibujado and "Nombre0 Apellido0" not in dibujado
    assert "sáb 19 sep 2026" in dibujado                           # la fecha real del más reciente


def test_plantilla_muestra_8_por_pagina():
    from alpha_football.ui import plantilla_screen as PS
    e = estado_carrera(); mi = e['mi_equipo']
    assert PS.FILAS_VISIBLES == 8 and PS.FILA_Y0 + 8 * PS.FILA_H <= PS.R_LISTA.bottom
    dibujado, restaurar = _capturar_texto(PS)
    try:
        pygame.event.clear(); assert PS.render(screen, e) is None
    finally:
        restaurar()
    orden = PS.ordenar_plantilla(mi.jugadores, *e['plantilla_orden'])
    nombres = [f"{mi.jugadores[i].nombre[:1]}. {mi.jugadores[i].apellido}"[:18] for i in orden]
    assert all(n in dibujado for n in nombres[:8]), [n for n in nombres[:8] if n not in dibujado]
    assert not any(n in dibujado for n in nombres[8:] if n not in nombres[:8])


# ---------- 1. simulación más lenta, día por día ----------

def test_continuar_espera_un_segundo_entre_dia_y_dia():
    from datetime import timedelta
    from alpha_football import dias as D
    from alpha_football.ui import league_screen as L
    e = _e_cal(); inicio = D.hoy(e)
    L._iniciar_avance(e)
    assert L._paso_avance(e, ahora=10_000) is True                    # el primer día pasa sin esperar
    assert D.hoy(e) == inicio + timedelta(days=1)
    assert e['hub_avance']['sig'] == 11_000, e['hub_avance']['sig']   # y el siguiente, 1 segundo después
    L._paso_avance(e, ahora=10_999)
    assert D.hoy(e) == inicio + timedelta(days=1)                     # 999 ms: todavía no
    L._paso_avance(e, ahora=11_000)
    assert D.hoy(e) == inicio + timedelta(days=2)


def test_simulacion_del_calendario_pasa_medio_segundo_por_dia():
    from datetime import timedelta
    from alpha_football import dias as D
    from alpha_football.ui import calendario_screen as KS
    e = _e_cal(); hoy = D.hoy(e)
    sim = {'fase': 'corriendo', 'hasta': (hoy + timedelta(days=3)).isoformat(), 'sig': 0,
           'dias': 0, 'pj': 0, 'g': 0, 'e': 0, 'p': 0}
    e['cal_sim'] = sim
    real = pygame.time.get_ticks
    pygame.time.get_ticks = lambda: 20_000
    try:
        KS._paso_sim(e, sim)
        assert sim['dias'] == 1 and sim['sig'] == 20_500, (sim['dias'], sim['sig'])
        pygame.time.get_ticks = lambda: 20_499
        KS._paso_sim(e, sim)
        assert sim['dias'] == 1                                       # 499 ms: todavía no
        pygame.time.get_ticks = lambda: 20_500
        KS._paso_sim(e, sim)
        assert sim['dias'] == 2
    finally:
        pygame.time.get_ticks = real
    assert KS.MS_TRAS_PARTIDO > KS.MS_PASO_SIM                        # la pausa del partido se nota más que un día cualquiera


# ---------- 2. ofertas en cifras cerradas (múltiplos de 10.000) ----------

def _cerrado(monto):
    return monto > 0 and monto % 10_000 == 0


def test_cifra_cerrada_redondea_a_multiplos_de_10000():
    from alpha_football.market import cifra_cerrada
    assert cifra_cerrada(12_345_678) == 12_350_000 and cifra_cerrada(12_344_999) == 12_340_000
    assert cifra_cerrada(12_345_678, abajo=True) == 12_340_000
    assert cifra_cerrada(7_500_000) == 7_500_000
    assert cifra_cerrada(4_000) == 10_000 and cifra_cerrada(4_000, abajo=True) == 0   # una oferta no queda en 0 al redondear
    assert cifra_cerrada(0) == 0 and cifra_cerrada(-5) == 0


def test_oferta_de_la_ia_sale_en_cifra_cerrada():
    import alpha_football.market as M
    e = estado_carrera(); mi = e['mi_equipo']; rivales = [eq for eq in e['liga'].equipos if eq is not mi]
    for r in rivales:
        r.balance = 10**10
    montos = []
    for semilla in range(40):
        of = M.crear_oferta_ui(mi, rivales, 1, 10, rng=random.Random(semilla), prob=1.0)
        if of:
            montos.append(of['monto'])
    assert len(montos) >= 20 and all(_cerrado(m) for m in montos), [m for m in montos if not _cerrado(m)][:5]


def test_oferta_del_exterior_sale_en_cifra_cerrada():
    import alpha_football.market as M
    e = estado_carrera(); mi = e['mi_equipo']
    montos = [M.crear_oferta_exterior(mi, e, rng=random.Random(s), prob=1.0) for s in range(30)]
    montos = [o['monto'] for o in montos if o]
    assert len(montos) >= 15 and all(_cerrado(m) for m in montos), [m for m in montos if not _cerrado(m)][:5]


def test_oferta_recibida_clasica_sale_en_cifra_cerrada():
    import alpha_football.market as M
    e = estado_carrera(); mi = e['mi_equipo']
    est = {'ligas': [e['liga']], 'equipo_usuario_id': mi.id, 'mercado_ofertas': []}
    montos = []
    for semilla in range(30):
        montos += [o.monto for o in M.generar_ofertas_recibidas(est, 1, 38, rng=random.Random(semilla), prob=1.0)]
    assert len(montos) >= 15 and all(_cerrado(m) for m in montos), [m for m in montos if not _cerrado(m)][:5]


def test_oferta_garantizada_y_remate_salen_en_cifra_cerrada():
    from alpha_football import salidas as S
    from test_mercado_v440 import _estado_salidas
    normales, remates = [], []
    for semilla in range(40):
        e = _estado_salidas(); mi = e['mi_equipo']; j = mi.jugadores[0]
        j.pide_salir = j.transferible = True
        remate = bool(semilla % 2)
        if remate:                                       # nadie puede pagar: sale el remate (95% del balance)
            j.valor = 9_000_000
            for eq in e['liga'].equipos:
                if eq is not mi:
                    eq.balance = 7_654_321 + semilla * 1_111
        for of in S.ofertas_garantizadas(e, rng=random.Random(semilla)):
            (remates if remate else normales).append((of['monto'], int(of['comprador'].balance)))
    assert len(normales) >= 15 and len(remates) >= 15, (len(normales), len(remates))
    assert all(_cerrado(m) for m, _b in normales + remates), [m for m, _b in normales + remates if not _cerrado(m)][:5]
    assert all(m <= b for m, b in remates), "el remate no puede superar el balance del comprador"


def test_tope_de_la_contraoferta_sale_en_cifra_cerrada():
    from alpha_football import contraofertas as CO
    from test_mercado_v350 import _oferta
    e = estado_carrera()
    for semilla in range(30):
        of = _oferta(e, monto=10_123_456, balance=10**9)
        assert CO.asignar_tope(of, random.Random(semilla)) % 10_000 == 0
    of = _oferta(e, monto=10_123_456, balance=10_555_555)         # topado por el balance: nunca por encima
    assert CO.asignar_tope(of, random.Random(1)) <= 10_555_555


def test_remate_de_club_quebrado_sale_en_cifra_cerrada():
    from alpha_football import negociacion as N
    e = estado_carrera(); j = e['mi_equipo'].jugadores[3]
    for valor in (12_345_678, 8_111_111, 3_333_333):
        j.valor = valor; j.remate = True
        assert _cerrado(N.precio_fichaje(j)), N.precio_fichaje(j)


TESTS = [test_gastar_horas_el_ultimo_dia_deja_anotada_la_animacion,
         test_gastar_horas_fuera_del_ultimo_dia_no_anima_ni_cobra,
         test_la_animacion_cuenta_una_hora_cada_500_ms_y_termina,
         test_dibujar_horas_muestra_las_horas_corriendo_y_se_apaga,
         test_registrar_pase_guarda_la_fecha_real,
         test_texto_cuando_usa_la_fecha_y_respalda_los_registros_viejos,
         test_historial_de_pases_muestra_8_por_pagina_con_la_fecha,
         test_plantilla_muestra_8_por_pagina,
         test_continuar_espera_un_segundo_entre_dia_y_dia,
         test_simulacion_del_calendario_pasa_medio_segundo_por_dia,
         test_cifra_cerrada_redondea_a_multiplos_de_10000,
         test_oferta_de_la_ia_sale_en_cifra_cerrada,
         test_oferta_del_exterior_sale_en_cifra_cerrada,
         test_oferta_recibida_clasica_sale_en_cifra_cerrada,
         test_oferta_garantizada_y_remate_salen_en_cifra_cerrada,
         test_tope_de_la_contraoferta_sale_en_cifra_cerrada,
         test_remate_de_club_quebrado_sale_en_cifra_cerrada,
         test_canterano_nace_con_al_menos_10_de_diferencia,
         test_crecer_sube_el_potencial_lo_mismo_que_la_media,
         test_crecer_no_pasa_de_89_ni_deja_el_potencial_a_menos_de_10,
         test_cantera_guardada_con_menos_de_10_se_corrige_al_cargar,
         test_boost_de_canterano_baja_a_1_35,
         test_correo_reprogramado_no_menciona_los_dias_de_descanso,
         test_felicita_solo_al_llegar_a_3_5_10_15_20_25_y_30,
         test_cada_felicitacion_es_distinta_y_mas_asombrada,
         test_un_empate_o_derrota_reinicia_la_cuenta_de_victorias,
         test_tres_derrotas_y_ult_res_siguen_igual,
         test_cambiar_de_club_borra_la_cuenta_de_victorias]


if __name__ == '__main__':
    fail = 0
    for t in TESTS:
        try:
            t()
            print(f"  {t.__name__}: OK")
        except Exception as ex:
            fail += 1
            import traceback; traceback.print_exc()
            print(f"  {t.__name__}: FAIL - {ex}")
    print(f"\n{len(TESTS) - fail}/{len(TESTS)} tests pasaron")
    if fail:
        sys.exit(1)
