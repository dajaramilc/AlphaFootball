"""v0.4.14.1: ajustes tras la prueba a mano de G1-G3 (mensajes de jugadores, fecha exacta, pedido de puntos por
nivel, último día sin costos anunciados, CONTINUAR, simulación desde CALENDARIO y presupuesto por resultados)."""
import sys, os, random, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
from datetime import date, timedelta
from test_calendario import screen, key, _e, _jugar, _con_copa   # noqa: E402  (deja save.guardar_en_slot sin efecto)
from alpha_football import calendario as CAL, correo as C, dias as D


def _en_j1(e):
    """Reloj en el día de la J1, ya jugada: el hueco hasta la J2 está por delante."""
    D.hoy(e); D.hasta_el_partido(e); _jugar(e, 1)


def _plantel_sano(e):
    for j in e['mi_equipo'].jugadores:
        j.personalidad, j.moral, j.energia = 'normal', 70, 100.0
        j.pide_salir = j.salida_forzada = j.transferible = False
        j.prestamo = None


def _traspasar(e, j):
    """Saca al jugador de tu club y lo deja en otro de la liga (lo que hace una venta)."""
    mi = e['mi_equipo']
    mi.jugadores.remove(j)
    next(eq for eq in e['liga'].equipos if eq is not mi).jugadores.append(j)


# --- Bug: escribe un jugador que ya se fue ────────────────────────────────────

def test_el_mensaje_agendado_de_un_jugador_que_ya_se_fue_no_llega():
    from alpha_football import salidas as S
    e = _e(); _en_j1(e); _plantel_sano(e)
    j = e['mi_equipo'].jugadores[0]
    j.moral, j.descontento_avisado = 20, False
    S.cierre_jornada(e, random.Random(1))
    assert any('descontento' in it['datos'].get('asunto', '') for it in D.agenda(e))   # espera su día en la agenda
    _traspasar(e, j)                                                       # se vende antes de que llegue
    r = D.hasta_el_partido(e)
    assert not [m for m in C.bandeja(e) if 'descontento' in m['asunto']], [m['asunto'] for m in C.bandeja(e)]
    assert r['correos'] == 0 and D.agenda(e) == []


def test_el_mensaje_agendado_de_un_jugador_que_sigue_en_el_club_si_llega():
    from alpha_football import salidas as S
    e = _e(); _en_j1(e); _plantel_sano(e)
    j, otro = e['mi_equipo'].jugadores[0], e['mi_equipo'].jugadores[1]
    j.moral, j.descontento_avisado = 20, False
    S.cierre_jornada(e, random.Random(1))
    _traspasar(e, otro)                                                    # se va otro: el mensaje no cambia
    D.hasta_el_partido(e)
    msg = next(m for m in C.bandeja(e) if 'descontento' in m['asunto'])
    assert msg['jugador']['id'] == j.id and C.jugador_de(e, msg) is j


def test_el_evento_agendado_de_un_jugador_que_ya_se_fue_no_llega():
    from alpha_football import eventos as EV
    e = _e(); _en_j1(e); _plantel_sano(e)
    for s in range(300):                                                   # 12% por jornada: alguna semilla lo da
        EV.cierre_jornada(e, random.Random(s))
        if D.agenda(e):
            break
    assert D.agenda(e), "ningún sorteo dio evento"
    ids = D.agenda(e)[0]['datos']['evento']['protagonistas']
    for j in [x for x in e['mi_equipo'].jugadores if x.id in ids]:
        _traspasar(e, j)
    r = D.hasta_el_partido(e)
    assert r['eventos'] == 0 and EV.pendiente(e) is None and not [m for m in C.bandeja(e) if m.get('evento')]


# --- Mensajes: plantilla con el jugador, su ficha y la fecha exacta ───────────

def _dibujado(mod, e) -> list:
    """Los textos que dibuja una pantalla en un render."""
    dib, original = [], mod.draw_text
    mod.draw_text = lambda scr, txt, *a, **k: (dib.append(txt), original(scr, txt, *a, **k))[1]
    try:
        pygame.event.clear()
        mod.render(screen, e)
    finally:
        mod.draw_text = original
    return dib


def test_ver_plantilla_desde_un_mensaje_selecciona_a_ese_jugador():
    from alpha_football.ui import correo_screen as CS, plantilla_screen as PS
    e = _e(); mi = e['mi_equipo']
    orden = PS.ordenar_plantilla(list(mi.jugadores), PS.normalizar_orden(None))
    idx = orden[-1]                                                        # el último de la lista: fuera de la vista
    msg = C.enviar(e, 'jugador', "Estoy molesto", "Míster…", C.accion('plantilla_screen', "VER PLANTILLA"),
                   jugador=mi.jugadores[idx])
    e['plantilla_sel'], e['plantilla_scroll'] = orden[0], 0
    assert CS._ir(e, msg) == 'plantilla_screen'
    pygame.event.clear(); assert PS.render(screen, e) is None
    assert e['plantilla_sel'] == idx
    pos = len(orden) - 1
    assert e['plantilla_scroll'] <= pos < e['plantilla_scroll'] + PS.FILAS_VISIBLES   # y se ve
    e['plantilla_sel'] = orden[2]                                          # un correo sin jugador no mueve la selección
    assert CS._ir(e, C.enviar(e, 'club', "Aviso", "x", C.accion('plantilla_screen', "VER PLANTILLA"))) == 'plantilla_screen'
    assert e['plantilla_sel'] == orden[2]


def test_el_mensaje_de_un_jugador_muestra_su_posicion_y_su_media():
    from alpha_football.ui import correo_screen as CS
    e = _e(); j = e['mi_equipo'].jugadores[3]
    C.enviar(e, 'jugador', "Estoy molesto", "Míster…", C.accion('plantilla_screen', "VER PLANTILLA"), jugador=j)
    e['correo_canal'], e['correo_sel'] = 'mensaje', 0
    ficha = f"{j.posicion} · {j.overall}"
    assert ficha in _dibujado(CS, e)
    antes = j.overall
    j.ataque = j.defensa = j.fisico = j.tecnica = j.mental = 99            # la media es la de hoy, no la del envío
    assert j.overall != antes and f"{j.posicion} · {j.overall}" in _dibujado(CS, e)
    _traspasar(e, j)
    assert not [t for t in _dibujado(CS, e) if t.startswith(f"{j.posicion} · ")]     # ya no está: sin ficha


def test_cada_mensaje_guarda_su_fecha_exacta_y_los_viejos_siguen_con_la_jornada():
    e = _e(); D.hoy(e)                                                     # el reloj nace el 1 jul 2026
    m = C.enviar(e, 'club', "Hola", "x")
    assert m['fecha'] == '2026-07-01' and C.texto_fecha(m) == "mié 1 jul 2026"
    assert C.texto_fecha({'temporada': 2, 'jornada': 5}) == "T2 J5"        # mensajes de un save viejo
    assert C.texto_fecha({'temporada': 2, 'jornada': 5, 'fecha': 'basura'}) == "T2 J5"


def test_el_mensaje_agendado_lleva_la_fecha_del_dia_en_que_llega():
    e = _e(); _en_j1(e)
    with D.diferir_correos(e):
        C.enviar(e, 'club', "Luego", "x")
    D.asignar_dias(e)
    dia = D.agenda(e)[0]['fecha']
    assert dia != D.hoy(e).isoformat()
    D.hasta_el_partido(e)
    assert next(m for m in C.bandeja(e) if m['asunto'] == "Luego")['fecha'] == dia


def test_notificaciones_y_correo_muestran_la_fecha():
    from alpha_football.ui import correo_screen as CS, notificaciones_screen as NS
    e = _e(); D.hoy(e)
    C.enviar(e, 'club', "Hola", "x")
    assert [t for t in _dibujado(NS, e) if "mié 1 jul 2026" in t]
    e['correo_canal'], e['correo_sel'] = 'correo', 0
    assert len([t for t in _dibujado(CS, e) if "mié 1 jul 2026" in t]) >= 2   # en la lista y en el mensaje


# --- Pedido de la directiva: los puntos dependen del nivel del club ───────────

def test_los_puntos_del_pedido_dependen_del_nivel_del_club():
    from alpha_football import directiva as DIR
    e = _e()
    n = len(e['liga'].equipos)
    orden = sorted(e['liga'].equipos, key=lambda x: -x.ovr_promedio)
    esperado = {1: 12, n // 4: 12, n // 4 + 1: 10, n // 2: 10, n // 2 + 1: 8, n: 8}
    for r, pts in esperado.items():
        e['mi_equipo'] = orden[r - 1]
        assert DIR.puntos_pedido(e) == pts, (r, n, DIR.puntos_pedido(e), pts)


def test_el_pedido_de_puntos_guarda_su_meta_y_se_resuelve_con_ella():
    from alpha_football import directiva as DIR
    e = _e(); liga = e['liga']
    mi = e['mi_equipo'] = max(liga.equipos, key=lambda x: x.ovr_promedio)  # el mejor de la liga: 12 puntos
    mi.rival = ''                                                          # sin clásico: quedan 'puntos' y 'sub21'
    for s in range(50):
        e['datos_carrera'].pop('pedido', None)
        DIR._crear_pedido(e, 0, random.Random(s))
        if e['datos_carrera']['pedido']['tipo'] == 'puntos':
            break
    p = e['datos_carrera']['pedido']
    assert p['tipo'] == 'puntos' and p['puntos'] == 12 and p['texto'].startswith("Sumar 12 puntos en las próximas 5")
    hechos = []
    DIR.resolver_pedido, original = (lambda est, ok: hechos.append(ok)), DIR.resolver_pedido
    try:
        for partido in [x for x in liga.calendario if mi.id in (x.local_id, x.visitante_id)][:5]:
            partido.jugado = True
        mi.puntos = p['puntos_ini'] + 11                                   # 11 de 12: no alcanza
        DIR.revisar_pedido(e, random.Random(1))
        mi.puntos = p['puntos_ini'] + 12
        DIR.revisar_pedido(e, random.Random(1))
    finally:
        DIR.resolver_pedido = original
    assert hechos[:2] == [False, True], hechos


def test_un_pedido_viejo_sin_meta_guardada_sigue_pidiendo_ocho():
    from alpha_football import directiva as DIR
    e = _e(); liga, mi = e['liga'], e['mi_equipo']
    e['datos_carrera']['pedido'] = {'temporada': 1, 'tipo': 'puntos', 'texto': 'Sumar 8 puntos', 'hasta': 5,
                                    'puntos_ini': 0, 'pj_ini': {}, 'resuelto': False, 'cumplido': False}
    for partido in [x for x in liga.calendario if mi.id in (x.local_id, x.visitante_id)][:5]:
        partido.jugado = True
    mi.puntos = 8
    hechos = []
    DIR.resolver_pedido, original = (lambda est, ok: hechos.append(ok)), DIR.resolver_pedido
    try:
        DIR.revisar_pedido(e, random.Random(1))
    finally:
        DIR.resolver_pedido = original
    assert hechos[:1] == [True], hechos


# --- Último día: solo las horas que quedan ────────────────────────────────────

def _en_el_31(e):
    """Reloj en el 31 de agosto con el último día abierto (20 horas)."""
    from alpha_football import dia_final as DF
    D.hoy(e); CAL.asegurar(e)['dia'] = '2026-08-31'
    assert DF.abrir(e)
    return DF


def test_el_ultimo_dia_solo_avisa_las_horas_que_quedan():
    from alpha_football.ui import aviso_mercado as AM, ayuda, league_screen as L
    e = _e(); DF = _en_el_31(e)
    assert AM.linea_cartel(e, 'ultimo') == "Quedan 20 horas."
    DF._bloque(e)['horas'] = 1
    assert AM.linea_cartel(e, 'ultimo') == "Queda 1 hora."
    DF._bloque(e)['horas'] = 20
    AM._abrir(e, 'ultimo', '2026-08-31')
    cuerpo = next(m for m in C.bandeja(e) if m['asunto'] == "Último día de fichajes")['cuerpo']
    assert "quedan 20 horas" in cuerpo
    e['hub_tab'] = 'inicio'
    textos = [cuerpo, AM.linea_cartel(e, 'ultimo')] + [x for r, _t, x in ayuda.items('league_screen', e) if r == L.R_HORA]
    assert len(textos) == 3
    for t in textos:                                                       # los costos se aplican, pero no se anuncian
        assert "3 h" not in t and "2 h" not in t and "cuesta" not in t, t


def test_el_ultimo_dia_los_costos_siguen_aplicandose():
    e = _e(); DF = _en_el_31(e)
    assert DF.gastar(e, DF.HORAS_FICHAJE) and DF.horas(e) == 17
    assert DF.gastar(e, DF.HORAS_VENTA) and DF.horas(e) == 15


# --- CONTINUAR: solo lo frenan una oferta, un evento o un partido ─────────────

def test_continuar_no_se_detiene_por_un_correo_comun():
    e = _e(); _en_j1(e)
    with D.diferir_correos(e):
        C.enviar(e, 'club', "Aviso", "x")
    D.asignar_dias(e)
    assert date.fromisoformat(D.agenda(e)[0]['fecha']) < CAL.fecha_liga(e, 2)
    r = D.continuar(e)
    assert D.hoy(e) == CAL.fecha_liga(e, 2), (D.hoy(e), CAL.fecha_liga(e, 2))   # llegó al partido sin frenar
    assert r['correos'] == 1 and "1 correo" in D.texto_resumen(r)                # pero el resumen lo cuenta


def test_continuar_no_se_detiene_por_la_apertura_del_mercado():
    e = _e(); D.hoy(e); cal = CAL.asegurar(e)
    for jor in range(1, 11):
        _jugar(e, jor)                                                     # el próximo partido es la J11 (enero)
    e['liga'].jornada_actual = 11
    cal['dia'] = '2026-12-30'
    r = D.continuar(e)
    assert D.hoy(e) == CAL.fecha_liga(e, 11) and D.hoy(e) > date(2027, 1, 1)     # pasó el 1 de enero sin parar
    assert r.get('hito') == 'abre' and "abre el mercado" in D.texto_resumen(r)


def test_continuar_se_detiene_por_una_oferta_y_por_un_evento():
    e = _e(); _en_j1(e); e['liga'].jornada_actual = 2
    it = D.programar(e, 'oferta'); D.asignar_dias(e)
    r = D.continuar(e)
    assert r['ofertas'] == 1 and D.hoy(e) == date.fromisoformat(it['fecha']) < CAL.fecha_liga(e, 2)
    f = _e(); _en_j1(f)
    with D.diferir_correos(f):
        C.enviar(f, 'club', "Riña", "x")['evento'] = {'id': 'x', 'resuelto': None}
    D.asignar_dias(f)
    dia = date.fromisoformat(D.agenda(f)[0]['fecha'])
    r = D.continuar(f)
    assert r['eventos'] == 1 and D.hoy(f) == dia < CAL.fecha_liga(f, 2)


def test_continuar_sigue_parando_en_el_ultimo_dia_de_fichajes():
    e = _e(); D.hoy(e); cal = CAL.asegurar(e)
    _jugar(e, 1); _jugar(e, 2)
    cal['dia'] = '2026-08-29'
    r = D.continuar(e)
    assert D.hoy(e) == date(2026, 8, 31) and r['hito'] == 'ultimo'


def test_un_paso_del_dia_puede_pedir_que_el_avance_se_detenga():
    from alpha_football import cantera
    e = _e(); _en_j1(e)
    objetivo = D.hoy(e) + timedelta(days=2)
    original = cantera.revisar_jornada

    def _revisar(estado):
        if D.hoy(estado) == objetivo:
            estado['_parar_avance'] = True                                 # p. ej. una gala que el hub debe mostrar hoy
        return original(estado)
    cantera.revisar_jornada = _revisar
    try:
        r = D.continuar(e)
    finally:
        cantera.revisar_jornada = original
    assert D.hoy(e) == objetivo and r['dias'] == 2 and '_parar_avance' not in e
    D.continuar(e)
    assert D.hoy(e) == CAL.fecha_liga(e, 2)                                # la marca no queda pegada


# --- CONTINUAR avanza a la vista, un día por cuadro ───────────────────────────

def _hub(e):
    D.hoy(e); e['datos_carrera']['aviso_mercado_visto'] = [1, D.hoy(e).isoformat()]   # sin el cartel de apertura
    from alpha_football.ui import league_screen as L
    return L


def _avance_a_la_vista(L, e, tope=400) -> list:
    """Corre el avance de CONTINUAR cuadro a cuadro, sin esperar el reloj real. Devuelve las fechas por las que pasó."""
    fechas = []
    for _ in range(tope):
        if 'hub_avance' not in e:
            return fechas
        e['hub_avance']['sig'] = 0
        pygame.event.clear(); assert L.render(screen, e) is None
        fechas.append(D.hoy(e))
    raise AssertionError("el avance no terminó")


def test_continuar_avanza_a_la_vista_un_dia_por_cuadro():
    e = _e(); L = _hub(e)
    pygame.event.clear(); L.render(screen, e)
    desde = D.hoy(e)
    key(pygame.K_RETURN); assert L.render(screen, e) is None
    assert 'hub_avance' in e and D.hoy(e) <= desde + timedelta(days=1)     # no corre todo de golpe
    fechas = [D.hoy(e)] + _avance_a_la_vista(L, e)
    assert D.hoy(e) == CAL.fecha_liga(e, 1)
    assert all((b - a).days <= 1 for a, b in zip(fechas, fechas[1:]))      # de a un día
    total = (CAL.fecha_liga(e, 1) - desde).days
    assert e['hub_toast'][0].startswith(f"Pasaron {total} días")
    key(pygame.K_RETURN); assert L.render(screen, e) == 'prepartido_screen'   # ya es día de partido


def test_mientras_avanza_se_ve_el_dia_y_una_tecla_lo_detiene_ahi():
    e = _e(); L = _hub(e)
    pygame.event.clear(); L.render(screen, e)
    key(pygame.K_RETURN); L.render(screen, e)
    e['hub_avance']['sig'] = 0
    dib = _dibujado(L, e)                                                  # este cuadro también avanza un día
    assert "AVANZANDO" in dib and CAL.texto_fecha(D.hoy(e)) in dib
    antes = D.hoy(e)
    key(pygame.K_RETURN)
    assert L.render(screen, e) is None and 'hub_avance' not in e           # esa tecla solo detiene
    assert D.hoy(e) == antes < CAL.fecha_liga(e, 1) and e['hub_toast'][0].startswith("Pas")
    assert "AVANZANDO" not in _dibujado(L, e)


def test_el_avance_a_la_vista_se_detiene_por_una_oferta():
    e = _e(); _en_j1(e); e['liga'].jornada_actual = 2; L = _hub(e)
    it = D.programar(e, 'oferta'); D.asignar_dias(e)
    pygame.event.clear(); L.render(screen, e)
    key(pygame.K_RETURN); L.render(screen, e)
    _avance_a_la_vista(L, e)
    assert D.hoy(e) == date.fromisoformat(it['fecha']) < CAL.fecha_liga(e, 2)
    assert "1 oferta" in e['hub_toast'][0] and len(e['ofertas_recibidas']) == 1


def test_un_dia_suelto_no_abre_el_avance():
    e = _e(); L = _hub(e)
    pygame.event.clear(); L.render(screen, e)
    antes = D.hoy(e)
    key(pygame.K_d); L.render(screen, e)
    assert 'hub_avance' not in e and D.hoy(e) == antes + timedelta(days=1)


# --- Presupuesto de la temporada: pesan los resultados ────────────────────────

def test_el_presupuesto_depende_mas_de_los_resultados_que_de_la_base():
    from alpha_football import finanzas as F
    base, sano = 100_000_000, 50_000_000                                   # saldo sano: salud ×1.00
    fallado = F.presupuesto_temporada(base, sano, 'fallado')['total']
    cumplido = F.presupuesto_temporada(base, sano, 'cumplido')['total']
    superado = F.presupuesto_temporada(base, sano, 'superado')['total']
    doblete = F.presupuesto_temporada(base, sano, 'superado', True, True)['total']
    assert (fallado, cumplido, superado, doblete) == (55_000_000, 95_000_000, 120_000_000, 165_000_000)
    assert F.PARTE_FIJA == 0.40 and doblete == 3 * fallado                 # los resultados mueven el triple
    assert F.presupuesto_temporada(base, sano, '')['total'] == base        # sin dato del objetivo: la base tal cual


def test_la_salud_financiera_sube_o_baja_el_presupuesto_hasta_un_20_por_ciento():
    from alpha_football import finanzas as F
    base = 100_000_000
    rojo = F.presupuesto_temporada(base, -1, 'cumplido')
    rico = F.presupuesto_temporada(base, 900_000_000, 'cumplido')
    assert rojo['salud'] == 0.80 and abs(rojo['mult'] - 0.95 * 0.80) < 1e-9
    assert rico['salud'] == 1.20 and abs(rico['mult'] - 0.95 * 1.20) < 1e-9


def test_el_correo_del_presupuesto_no_muestra_la_cuenta():
    from alpha_football import finanzas as F
    from test_revision_v291 import estado_carrera
    e = estado_carrera(); mi = e['mi_equipo']; mi.balance = 50_000_000
    e['temporada'] = 2
    e['historial'] = [{'temporada': 1, 'equipo': mi.nombre, 'objetivo_resultado': 'superado', 'campeon_liga': mi.nombre}]
    info = F.aplicar_presupuesto_temporada(e)
    m = next(x for x in C.bandeja(e) if x['asunto'] == "Presupuesto de la temporada 2")
    assert "debido a sus resultados" in m['cuerpo'] and f"${info['total'] / 1_000_000:.1f}M" in m['cuerpo']
    for sobra in ("×", "base", "Salud", "Objetivo", "Títulos", "Cierre de la temporada"):
        assert sobra not in m['cuerpo'], (sobra, m['cuerpo'])
    assert m['accion']['pantalla'] == 'finanzas_screen'


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
