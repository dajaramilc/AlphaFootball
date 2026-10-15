"""0.4.26.0 (xd3, mercado y economía): fichajes de quien cambió hace poco y de las figuras de la IA, respuestas de
"lo analizamos" por días, venta de camisetas, el doble de ofertas por transferibles y cedibles, espaldarazo con tope
salarial, ojeador que solo recomienda comprables, precios regulados y el cierre del mercado con 1-2 horas.
NO CORRIDO: la orden de Diego del 2026-10-14 es no correr pytest hasta que él lo diga."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
from datetime import date, timedelta
from test_calendario import _e                    # noqa: E402  (deja save.guardar_en_slot sin efecto)
from test_dia_final import _en_el_ultimo_dia      # noqa: E402
from test_revision_v291 import estado_carrera     # noqa: E402

from alpha_football import calendario as CAL, correo as C, dias as D, temporada as T, dia_final as DF
from alpha_football import market as M, negociacion as N, finanzas as F, directiva as DI, mercado_ia as MIA
from alpha_football import prestamos as PR, traspasos_pendientes as TP


class _Azar:
    """Azar fijo: random() siempre devuelve `v` (0.0 deja pasar todo lo que se sortea; 0.99 lo descarta)."""
    def __init__(self, v):
        self.v = v

    def random(self):
        return self.v

    def uniform(self, a, b):
        return a

    def choice(self, seq):
        return seq[0]


def _poner_media(j, valor):
    for a in ('ataque', 'defensa', 'fisico', 'tecnica', 'mental'):
        setattr(j, a, int(valor))


# ---------------------------------------------------------------- ítem 23: precios
def test_defensas_y_porteros_valen_menos_con_el_mismo_perfil():
    e = estado_carrera()
    j = max(e['mi_equipo'].jugadores, key=lambda x: x.overall)
    j.edad = 27
    j.posicion = 'MED'
    base = M.calcular_valor(j)
    j.posicion = 'DEL'
    assert M.calcular_valor(j) == base
    j.posicion = 'DEF'
    assert abs(M.calcular_valor(j) - base * 0.85) <= 1
    j.posicion = 'POR'
    assert abs(M.calcular_valor(j) - base * 0.75) <= 1


def test_los_veteranos_valen_menos_que_con_la_curva_vieja():
    e = estado_carrera()
    j = max(e['mi_equipo'].jugadores, key=lambda x: x.overall)
    j.posicion = 'MED'
    j.edad = 29
    base = M.calcular_valor(j)
    previo = base
    for edad in range(30, 37):
        j.edad = edad
        v = M.calcular_valor(j)
        vieja = base * max(0.30, 1.0 - (edad - 29) * 0.06)
        assert v < previo and v <= vieja + 1, (edad, v, vieja)         # cae cada año y más que la curva de 0.4.25.0
        previo = v
    j.edad = 22
    assert M.calcular_valor(j) > base                                  # los jóvenes siguen valiendo 10% más


# ---------------------------------------------------------------- ítem 2: quien cambió hace poco, las figuras
def test_registrar_pase_anota_la_fecha_y_cambio_reciente_la_lee():
    e = estado_carrera()
    j = e['mi_equipo'].jugadores[6]
    assert not M.cambio_reciente(e, j)
    N.registrar_pase(e, j, 'Club A', 'Club B', 1_000_000, False)
    notas = e['datos_carrera']['ultimo_pase']
    assert j.nombre_completo in notas and M.cambio_reciente(e, j)
    hoy = date.fromisoformat(C._hoy_iso(e))
    notas[j.nombre_completo] = (hoy - timedelta(days=M.DIAS_CAMBIO_RECIENTE - 1)).isoformat()
    assert M.cambio_reciente(e, j)                                     # hace 364 días: todavía cuenta
    notas[j.nombre_completo] = (hoy - timedelta(days=M.DIAS_CAMBIO_RECIENTE + 1)).isoformat()
    assert not M.cambio_reciente(e, j)                                 # hace más de un año: ya no


def test_partida_vieja_sin_nota_usa_la_marca_de_la_ventana():
    e = estado_carrera()
    j = e['mi_equipo'].jugadores[6]
    e['temporada'] = 3
    j.ventana_traspaso = '3-verano'
    assert M.cambio_reciente(e, j)                                     # esta misma temporada
    j.ventana_traspaso = '1-verano'
    assert not M.cambio_reciente(e, j)                                 # hace dos temporadas
    j.ventana_traspaso = ''
    assert not M.cambio_reciente(e, j)


def test_las_notas_viejas_se_podan():
    e = estado_carrera()
    hoy = date.fromisoformat(C._hoy_iso(e))
    viejo = (hoy - timedelta(days=500)).isoformat()
    notas = e['datos_carrera'].setdefault('ultimo_pase', {})
    for k in range(N.MAX_ULTIMO_PASE + 10):
        notas[f"Viejo {k}"] = viejo
    j = e['mi_equipo'].jugadores[2]
    N._anotar_ultimo_pase(e, j)
    assert list(notas) == [j.nombre_completo]                          # solo queda lo que cuenta


def _montar_compra(e, otros_media=50):
    """(comprador, vendedor, candidato, equipos): el vendedor solo tiene un jugador que mejora al titular más flojo
    del comprador; todos los demás son de la misma posición opuesta y de nivel bajo."""
    liga = e['liga']
    mi = e['mi_equipo']
    comprador = max((c for c in liga.equipos if c is not mi), key=lambda c: c.ovr_promedio)
    vendedor = next(c for c in liga.equipos if c is not comprador and c is not mi)
    comprador.balance = 10 ** 12
    pos, ovr_flojo = MIA._puesto_mas_flojo(comprador, random.Random(1))
    otra = 'POR' if pos != 'POR' else 'DEL'
    for p in vendedor.jugadores:
        p.posicion = otra
        _poner_media(p, otros_media)
        p.prestamo = None
        p.remate = False
        p.lesion_dias = 0
    candidato = vendedor.jugadores[0]
    candidato.posicion = pos
    _poner_media(candidato, ovr_flojo + 4)
    return comprador, vendedor, candidato, [(vendedor, liga.tipo, 1)], pos, ovr_flojo


def test_la_ia_vende_a_sus_3_mejores_con_menos_probabilidad():
    e = estado_carrera()
    comprador, vendedor, candidato, equipos, _pos, _ovr = _montar_compra(e)      # es el mejor del vendedor: top 3
    tipo = e['liga'].tipo
    hallado = MIA._buscar_refuerzo(comprador, tipo, 1, equipos, e['mi_equipo'], 10 ** 12, False, _Azar(0.0), e)
    assert hallado is not None and hallado[0] is candidato                      # el azar lo deja pasar
    hallado = MIA._buscar_refuerzo(comprador, tipo, 1, equipos, e['mi_equipo'], 10 ** 12, False, _Azar(0.99), e)
    assert hallado is None                                                       # el azar lo frena: no se anula, se baja
    assert 0 < M.FACTOR_FIGURA_IA < 1


def test_quien_cambio_hace_poco_se_mueve_con_menos_probabilidad():
    e = estado_carrera()
    comprador, vendedor, candidato, equipos, pos, ovr = _montar_compra(e)
    otras = [p for p in vendedor.jugadores if p is not candidato][:3]
    for p in otras:                    # tres estrellas más: el candidato ya no es de los 3 mejores del club
        _poner_media(p, 85)
    tipo = e['liga'].tipo
    args = (comprador, tipo, 1, equipos, e['mi_equipo'], 10 ** 12, False)
    assert MIA._buscar_refuerzo(*args, _Azar(0.99), e) is not None               # sin marca: no lo frena nadie
    N.registrar_pase(e, candidato, 'Otro', vendedor.nombre, 1_000_000, False)
    candidato.ventana_traspaso = ''                                              # (que no lo tape la regla de la ventana)
    assert M.cambio_reciente(e, candidato)
    assert MIA._buscar_refuerzo(*args, _Azar(0.99), e) is None
    assert MIA._buscar_refuerzo(*args, _Azar(0.0), e) is not None
    assert 0 < M.FACTOR_CAMBIO_RECIENTE < 1


def test_una_oferta_por_tus_jugadores_evita_al_recien_llegado():
    e = estado_carrera()
    mi, rivales = e['mi_equipo'], e['liga'].equipos[1:]
    M.ACTIVE_ESTADO = None
    reciente = mi.jugadores[5]
    N.registrar_pase(e, reciente, 'Otro', mi.nombre, 1_000_000, True)
    reciente.ventana_traspaso = ''
    rng = random.Random(7)
    ofertas = [M.crear_oferta_ui(mi, rivales, 1, 10, rng=rng, prob=1.0, estado=e) for _ in range(300)]
    por_el = sum(1 for o in ofertas if o and o['jugador'] is reciente)
    otros = sum(1 for o in ofertas if o and o['jugador'] is not reciente)
    assert otros > 0 and por_el < otros / (len(mi.jugadores) - 1) * 0.6          # con 1/20 del azar, muy por debajo de uno más


# ---------------------------------------------------------------- ítem 11: el doble de ofertas
def test_el_doble_de_ofertas_por_transferibles_y_cedibles():
    e = estado_carrera()
    mi = e['mi_equipo']
    assert M.prob_oferta_ia(mi) == M.PROB_OFERTA_POR_JORNADA
    mi.jugadores[4].transferible = True
    assert M.prob_oferta_ia(mi) == M.PROB_OFERTA_CON_TRANSFERIBLES >= 0.90        # antes 0.45
    assert DF.PROB_OFERTA_HORA_TRANSFERIBLES == 0.50 and DF.PROB_OFERTA_HORA == 0.10   # antes 0.25
    assert PR.PROB_OFERTA_PRESTAMO == 0.60                                        # antes 0.30


# ---------------------------------------------------------------- ítem 5: respuestas por días
def _compra_en_analisis(e, dia='2026-07-10'):
    from alpha_football.data.clasicos import es_clasico
    D.hoy(e)
    CAL.asegurar(e)['dia'] = dia
    mi, liga = e['mi_equipo'], e['liga']
    club = next(x for x in liga.equipos[1:] if not es_clasico(x, mi))
    j = club.jugadores[0]
    minimo = N.minimo_club(j, club)
    res, msg, _c = N.evaluar_compra(e, j, club, int(minimo * N.UMBRAL_ANALISIS) + 1)
    return res, msg, e['datos_carrera']['analisis_compras'][0], club, j


def test_lo_analizamos_responde_a_los_1_a_3_dias_y_no_por_jornada():
    e = _e()
    res, msg, item, _club, _j = _compra_en_analisis(e)
    assert res == 'analiza' and 'fecha_resp' in item and 'hora_resp' not in item
    dias = (date.fromisoformat(item['fecha_resp']) - date(2026, 7, 10)).days
    assert 1 <= dias <= 3 and f"{dias} día" in msg and "jornada" not in msg
    assert not DF.vencido(e, item)                                               # hoy todavía no
    CAL.asegurar(e)['dia'] = (date.fromisoformat(item['fecha_resp']) - timedelta(days=1)).isoformat()
    assert not DF.vencido(e, item)
    CAL.asegurar(e)['dia'] = item['fecha_resp']
    assert DF.vencido(e, item)                                                   # llegó su día


def test_la_respuesta_llega_por_correo_el_dia_que_toca():
    e = _e()
    res, _msg, item, _club, _j = _compra_en_analisis(e)
    n0 = len(C.bandeja(e))
    DF.responder(e, random.Random(1))
    assert len(C.bandeja(e)) == n0 and e['datos_carrera']['analisis_compras']    # antes de su día no responde
    CAL.asegurar(e)['dia'] = item['fecha_resp']
    DF.responder(e, random.Random(1))
    asuntos = [m['asunto'] for m in C.bandeja(e)]
    assert e['datos_carrera']['analisis_compras'] == []
    assert any("acepta tu oferta" in a or "rechaza tu oferta" in a for a in asuntos)


def test_con_el_mercado_por_cerrar_la_respuesta_llega_antes_del_cierre():
    e = _e()
    _res, _msg, item, _club, _j = _compra_en_analisis(e, dia='2026-08-30')       # queda 1 día de mercado
    assert item['fecha_resp'] == '2026-08-31'


def test_sin_reloj_la_respuesta_sigue_siendo_por_jornada():
    e = estado_carrera()
    mi, liga = e['mi_equipo'], e['liga']
    from alpha_football.data.clasicos import es_clasico
    club = next(x for x in liga.equipos[1:] if not es_clasico(x, mi))
    j = club.jugadores[0]
    res, msg, _c = N.evaluar_compra(e, j, club, int(N.minimo_club(j, club) * N.UMBRAL_ANALISIS) + 1)
    item = e['datos_carrera']['analisis_compras'][0]
    assert res == 'analiza' and 'fecha_resp' not in item and "próxima jornada" in msg
    liga.jornada_actual += 1
    assert DF.vencido(e, item)


def test_texto_respuesta_con_dias():
    assert DF.texto_respuesta(None, dias=1) == "Te responden por correo en 1 día."
    assert DF.texto_respuesta(None, uno=True, dias=3) == "Te responde por correo en 3 días."
    assert DF.texto_respuesta(7, dias=2) == "Te responden en 3 horas."          # por hora manda
    assert DF.texto_respuesta(None) == "Te responden por correo en la próxima jornada."


# ---------------------------------------------------------------- ítem 24: 1-2 horas de mercado
def test_con_1_o_2_horas_el_trato_entra_y_el_mercado_se_cierra():
    e, _ = _en_el_ultimo_dia()
    DF._bloque(e)['horas'] = 2
    assert DF.gastar(e, DF.HORAS_FICHAJE) and DF.horas(e) == 0 and DF.cerrado(e)
    f, _ = _en_el_ultimo_dia()
    DF._bloque(f)['horas'] = 1
    assert DF.gastar(f, DF.HORAS_VENTA) and DF.horas(f) == 0 and DF.cerrado(f)
    g, _ = _en_el_ultimo_dia()
    DF._bloque(g)['horas'] = 2
    assert DF.analisis(g) == (False, None)                                       # analizar sigue pidiendo 3 horas
    assert not DF.gastar(g, 99) and DF.horas(g) == 2


def test_la_ronda_de_cierre_no_se_lleva_al_jugador_del_trato_en_curso():
    from alpha_football import negociacion as NG
    e, _ = _en_el_ultimo_dia(); mi, liga = e['mi_equipo'], e['liga']; mi.balance = 10 ** 12
    DF._bloque(e)['horas'] = 2
    club, j = liga.equipos[1], liga.equipos[1].jugadores[0]
    vistos, original = [], MIA.ronda_fichajes_ia
    MIA.ronda_fichajes_ia = lambda estado, modo='ventana', rng=None: vistos.append(M.traspasado_en_ventana(estado, j)) or []
    try:
        ok, _msg = NG.fichar(e, j, club, 1_000)
    finally:
        MIA.ronda_fichajes_ia = original
    assert ok and j in mi.jugadores and vistos == [True]                         # la IA lo veía ya traspasado


# ---------------------------------------------------------------- ítem 16: ojeador
def test_es_comprable_cierra_las_mismas_puertas_que_el_mercado():
    e = estado_carrera()
    mi, liga = e['mi_equipo'], e['liga']
    from alpha_football.data.clasicos import es_clasico
    club = next(x for x in liga.equipos[1:] if not es_clasico(x, mi))
    j = club.jugadores[3]
    assert N.es_comprable(e, j, club)
    j.prestamo = {'dueno': club.nombre, 'pct_dueno': 50}
    assert not N.es_comprable(e, j, club)                                        # a préstamo: no se compra
    j.prestamo = None
    j.ventana_traspaso = M.clave_ventana_traspaso(1, liga.jornada_actual, liga.num_jornadas, e)
    assert M.traspasado_en_ventana(e, j) and not N.es_comprable(e, j, club)      # llegó en este mercado
    j.ventana_traspaso = ''
    TP.diferir_compra(e, j, club, 1_000)
    assert not N.es_comprable(e, j, club)                                        # ya está acordado
    e['datos_carrera']['traspasos_pendientes'] = []
    j2 = club.jugadores[4]
    j2.remate = False
    assert N.es_comprable(e, j2, None)                                           # un libre, sin club con quien negociar


def test_el_ojeador_no_recomienda_al_que_llego_a_su_club_en_este_mercado():
    e = estado_carrera()
    mi, liga = e['mi_equipo'], e['liga']
    mi.balance = 10 ** 10
    recs = N.recomendar_fichajes(e)
    assert recs
    j, club = recs[0][0], recs[0][1]
    j.ventana_traspaso = M.clave_ventana_traspaso(1, liga.jornada_actual, liga.num_jornadas, e)
    assert M.traspasado_en_ventana(e, j)
    assert all(r[0] is not j for r in N.recomendar_fichajes(e))
    # y la lista que el ojeador guardó para la ventana se rehace si alguno ya no se puede comprar
    j.ventana_traspaso = ''
    guardadas = N.recomendaciones_ojeador(e)
    primero = guardadas[0][0]
    primero.ventana_traspaso = M.clave_ventana_traspaso(1, liga.jornada_actual, liga.num_jornadas, e)
    nuevas = N.recomendaciones_ojeador(e)
    assert all(r[0] is not primero for r in nuevas)


# ---------------------------------------------------------------- ítem 13: espaldarazo
def test_el_espaldarazo_sube_tambien_el_tope_de_masa_salarial():
    e = estado_carrera()
    obj = DI.definir_objetivo(e)
    obj['pos_max'] = max(6, int(obj.get('pos_max', 6)))
    tope = int(obj['tope_salarial'])
    ok, msg = DI.pedir_espaldarazo(e, 1)                                         # el de +30%
    assert ok, msg
    assert obj['tope_salarial'] == tope + int(tope * 0.30)
    assert obj['tope_espaldarazo'] == int(tope * 0.30) and "tope salarial" in msg
    assert obj['espaldarazo']['pct'] == 0.30 and set(obj['espaldarazo']) == {'pct', 'puestos', 'deuda'}
    ok2, _msg2 = DI.pedir_espaldarazo(e, 0)
    assert not ok2 and obj['tope_salarial'] == tope + int(tope * 0.30)           # una sola vez por temporada


# ---------------------------------------------------------------- ítem 10: camisetas
def test_la_popularidad_parte_de_50_y_el_ingreso_sigue_al_tamano_del_club():
    e = estado_carrera()
    mi, liga = e['mi_equipo'], e['liga']
    assert F.popularidad(e) == 50.0
    base = F.base_ingresos(mi, liga.tipo, liga.division)
    assert abs(F.ingreso_anual_camisetas(e) - int(base * F.CAMISETAS_FRAC)) <= 1
    e['datos_carrera']['camisetas'] = {'popularidad': 100.0}
    assert abs(F.ingreso_anual_camisetas(e) - int(base * F.CAMISETAS_FRAC * 2)) <= 1
    assert F.valor_camisetas(e) == F.MULT_VALOR_CAMISETAS * F.ingreso_anual_camisetas(e)


def test_el_valor_del_club_suma_las_camisetas_solo_con_estado():
    e = estado_carrera()
    mi = e['mi_equipo']
    plano = F.valor_club(mi)
    assert F.valor_club(mi, e) == plano + F.valor_camisetas(e) > plano
    otro = e['liga'].equipos[1]
    assert F.valor_club(otro, e) == F.valor_club(otro)                           # solo el club del user
    e['datos_carrera']['camisetas'] = {'popularidad': 100.0}
    assert F.valor_club(mi, e) > plano + F.MULT_VALOR_CAMISETAS * F.ingreso_anual_camisetas({**e, 'datos_carrera': {}})


def test_la_jornada_cobra_camisetas_y_las_anota_en_el_libro():
    e = estado_carrera()
    mi, liga = e['mi_equipo'], e['liga']
    esperado = F.ingreso_anual_camisetas(e) // liga.num_jornadas
    bal = mi.balance
    mov = F.procesar_jornada(e, es_local=True, gf=1, gc=1)
    assert mov['camisetas'] == esperado > 0
    assert mi.balance == bal + mov['patrocinio'] + mov['taquilla'] + mov['camisetas'] - mov['salarios']
    assert F.libro(e)['camisetas'] == esperado


def _tabla(e, mi, puntos_mi, puntos_otros=0):
    for eq in e['liga'].equipos:
        eq.puntos = puntos_otros
        eq.gf = eq.gc = 0
    mi.puntos = puntos_mi


def test_la_popularidad_se_dispara_sobre_lo_esperado_y_baja_despacio():
    e = estado_carrera()
    mi, liga = e['mi_equipo'], e['liga']
    obj = DI.definir_objetivo(e)
    obj['pos_max'] = 10
    liga.jornada_actual = 8                                                      # 7 jugadas: la tabla pesa entera
    _tabla(e, mi, 30)                                                            # líder, 9 puestos sobre la meta
    delta = F.actualizar_popularidad(e, 2, 0)
    assert delta >= F.SUBE_MAX                                                   # se dispara (tope por jornada + victoria)
    assert abs(F.popularidad(e) - (50.0 + delta)) < 1e-6
    # por debajo de la meta baja, pero despacio
    e2 = estado_carrera()
    mi2, liga2 = e2['mi_equipo'], e2['liga']
    DI.definir_objetivo(e2)['pos_max'] = 1
    liga2.jornada_actual = 8
    for eq in liga2.equipos:
        eq.puntos, eq.gf, eq.gc = 20, 0, 0
    mi2.puntos = 0                                                               # último
    d2 = F.actualizar_popularidad(e2, 1, 1)                                      # empate
    assert -F.BAJA_MAX <= d2 < 0 and abs(d2) < delta / 4
    assert F.POPULARIDAD_MIN <= F.popularidad(e2) <= F.POPULARIDAD_MAX


def test_la_popularidad_no_pasa_de_100_ni_baja_de_10():
    e = estado_carrera()
    F._cambiar_popularidad(e, 500)
    assert F.popularidad(e) == F.POPULARIDAD_MAX
    F._cambiar_popularidad(e, -500)
    assert F.popularidad(e) == F.POPULARIDAD_MIN


def test_el_cierre_de_temporada_mueve_la_popularidad_por_titulo_y_meta():
    e = estado_carrera()
    mi = e['mi_equipo']
    e['temporada'] = 2
    e['historial'] = [{'equipo': mi.nombre, 'temporada': 1, 'campeon_liga': mi.nombre, 'objetivo_resultado': 'superado'}]
    F.aplicar_presupuesto_temporada(e)
    assert F.popularidad(e) == 50.0 + F.POP_SUPERADO + F.POP_CAMPEON_LIGA
