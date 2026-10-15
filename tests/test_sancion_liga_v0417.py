"""v0.4.17.0: sanción de la liga por tope salarial, veredicto con motivos y evaluación resumida."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(17)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save, correo as C, directiva as D, finanzas as F, sancion_liga as SL
save.guardar_en_slot = lambda *a, **k: None
from test_revision_v291 import estado_carrera   # noqa: E402


def _base(e):
    mi, liga = e['mi_equipo'], e['liga']
    return F.presupuesto_base(mi, liga.tipo, getattr(liga, 'division', 1) or 1)


def _sancion_mala(e):
    """Sanción con multa ya vigente (temporada 2)."""
    e['mi_equipo'].balance = -1
    s = SL.registrar(e, 12_000_000, 10_000_000, 1)
    e['temporada'] = 2
    return s


# ── Task 1: núcleo ───────────────────────────────────────────────────────────────

def test_registrar_salud_buena_sin_multa():
    e = estado_carrera(); mi = e['mi_equipo']
    mi.balance = _base(e)                                   # 100% de la base: salud buena
    s = SL.registrar(e, 12_000_000, 10_000_000, 1)
    assert s['club'] == mi.nombre and s['temporada'] == 2
    assert s['salud_mala'] is False and s['multa'] == 0 and s['multa_estado'] is None
    assert e['datos_carrera']['sancion_liga'] is s
    assert "no podrá fichar" in SL.texto(s) and "multa" not in SL.texto(s)
    print("  test_registrar_salud_buena_sin_multa: OK")


def test_registrar_salud_mala_multa_40():
    for pct in (-0.5, 0.10):                                # en rojo y con menos del 25% de la base
        e = estado_carrera(); mi = e['mi_equipo']
        mi.balance = int(_base(e) * pct)
        s = SL.registrar(e, 12_000_000, 10_000_000, 1)
        assert s['salud_mala'] is True and s['multa'] == int(_base(e) * SL.MULTA_PCT_BASE), pct
        assert "impone una multa" in SL.texto(s)
    print("  test_registrar_salud_mala_multa_40: OK")


def test_activa_solo_club_y_temporada():
    e = estado_carrera(); mi = e['mi_equipo']
    mi.balance = _base(e)
    SL.registrar(e, 12_000_000, 10_000_000, 1)
    assert SL.activa(e) is None and SL.motivo_bloqueo(e) is None      # la temporada 1 no está sancionada
    e['temporada'] = 2
    assert SL.activa(e) is not None and "Sanción de la liga" in SL.motivo_bloqueo(e)
    e['mi_equipo'] = e['liga'].equipos[3]                              # otro club: no sigue al DT
    assert SL.activa(e) is None and SL.motivo_bloqueo(e) is None
    e['mi_equipo'] = mi; e['temporada'] = 3                            # dura una temporada
    assert SL.activa(e) is None
    print("  test_activa_solo_club_y_temporada: OK")


def test_sin_sancion_o_datos_rotos_no_bloquea():
    e = estado_carrera()
    assert SL.activa(e) is None and SL.motivo_bloqueo(e) is None and SL.cobrar_multa(e) is None
    for basura in ("basura", {'club': e['mi_equipo'].nombre}, {'club': e['mi_equipo'].nombre, 'temporada': 'x'}):
        e['datos_carrera']['sancion_liga'] = basura
        assert SL.activa(e) is None and SL.motivo_bloqueo(e) is None, basura
    print("  test_sin_sancion_o_datos_rotos_no_bloquea: OK")


def test_multa_pagada_una_sola_vez():
    e = estado_carrera(); mi = e['mi_equipo']
    s = _sancion_mala(e)
    mi.balance, mi.puntos = s['multa'] + 500_000, 0
    assert SL.cobrar_multa(e) is s
    assert mi.balance == 500_000 and mi.puntos == 0 and s['multa_estado'] == 'pagada' and s['puntos'] == 0
    assert F.libro(e)['premios'] == -s['multa']
    assert C.bandeja(e)[0]['asunto'].startswith("Sanción de la liga")
    assert SL.cobrar_multa(e) is None and mi.balance == 500_000
    print("  test_multa_pagada_una_sola_vez: OK")


def test_multa_impaga_quita_presupuesto_y_puntos():
    e = estado_carrera(); mi = e['mi_equipo']
    s = _sancion_mala(e)
    mi.balance, mi.puntos, mi.sancion_puntos = s['multa'] - 1, 0, 0
    SL.cobrar_multa(e)
    assert mi.balance == 0 and mi.puntos == -SL.PUNTOS_MULTA and mi.sancion_puntos == SL.PUNTOS_MULTA
    assert s['multa_estado'] == 'impaga' and s['puntos'] == SL.PUNTOS_MULTA
    assert F.libro(e)['premios'] == -(s['multa'] - 1)                  # solo se llevó lo que había
    assert SL.cobrar_multa(e) is None and mi.puntos == -SL.PUNTOS_MULTA
    print("  test_multa_impaga_quita_presupuesto_y_puntos: OK")


def test_multa_no_se_cobra_con_salud_buena_ni_a_otro_club():
    e = estado_carrera(); mi = e['mi_equipo']
    mi.balance = _base(e)
    SL.registrar(e, 12_000_000, 10_000_000, 1); e['temporada'] = 2
    saldo = mi.balance
    assert SL.cobrar_multa(e) is None and mi.balance == saldo
    e2 = estado_carrera(); _sancion_mala(e2)
    otro = e2['liga'].equipos[3]; e2['mi_equipo'] = otro; saldo = otro.balance
    assert SL.cobrar_multa(e2) is None and otro.balance == saldo
    print("  test_multa_no_se_cobra_con_salud_buena_ni_a_otro_club: OK")


# ── Task 2: bloqueo ──────────────────────────────────────────────────────────────

def _sancionar(e):
    """Sanción sin multa vigente en la temporada 2. Devuelve el motivo del bloqueo."""
    e['mi_equipo'].balance = _base(e)
    SL.registrar(e, 12_000_000, 10_000_000, 1); e['temporada'] = 2
    return SL.motivo_bloqueo(e)


def test_bloqueo_compra_y_agente_libre():
    from alpha_football import negociacion as N
    e = estado_carrera(); mi = e['mi_equipo']
    club = e['liga'].equipos[3]; j = min(club.jugadores, key=lambda x: x.overall)
    assert SL.motivo_bloqueo(e, corto=True) is None                           # sin sanción no hay motivo
    motivo = _sancionar(e)
    corto = SL.motivo_bloqueo(e, corto=True)
    assert corto.startswith("Sanción de la liga") and len(corto) <= 60 and len(motivo) > 60
    mi.balance = 10 ** 10
    assert N.evaluar_compra(e, j, club, 10 ** 9) == ('rechaza', motivo, 0)
    assert N.evaluar_compra(e, j, None, 0) == ('rechaza', motivo, 0)          # agente libre
    n = len(mi.jugadores)
    assert N.fichar(e, j, club, 1) == (False, motivo)
    assert j in club.jugadores and len(mi.jugadores) == n and mi.balance == 10 ** 10
    libre = N.asegurar_agentes_libres(e)[0]
    assert N.fichar(e, libre, None, 0) == (False, motivo) and libre not in mi.jugadores
    assert N.reanudar_compra(e, {'club_id': club.id, 'jugador_id': j.id, 'temporada': 2, 'monto': 1}) is None
    aviso = e['correo_aviso']                                                 # el correo lo recorta a 60
    assert aviso == corto and len(aviso) <= 60 and aviso.startswith("Sanción de la liga")
    print("  test_bloqueo_compra_y_agente_libre: OK")


def test_bloqueo_se_ve_al_abrir_la_negociacion():
    from alpha_football import negociacion as N
    e = estado_carrera(); mi = e['mi_equipo']
    club = e['liga'].equipos[3]; j = club.jugadores[0]
    motivo = _sancionar(e)
    for modo in ('fichaje', 'prestamo'):
        assert N.iniciar_negociacion(e, j, club, modo, 'buscador_screen') == 'negociacion_screen'
        assert e['neg']['msg'] == (motivo, 'rojo'), modo
    N.iniciar_negociacion(e, mi.jugadores[0], None, 'renovar', 'plantilla_screen')
    assert e['neg']['msg'] is None                                            # renovar sí se puede
    print("  test_bloqueo_se_ve_al_abrir_la_negociacion: OK")


def test_bloqueo_prestamos():
    from alpha_football import prestamos as P
    e = estado_carrera(); mi = e['mi_equipo']
    club = e['liga'].equipos[2]; j = min(club.jugadores, key=lambda x: x.overall)
    motivo = _sancionar(e)
    n = len(mi.jugadores)
    assert P.evaluar_pedido(e, j, club, 6, 100) == ('rechaza', motivo)
    assert P.cerrar_pedido(e, j, club, 6, 100) == (False, motivo)
    assert len(mi.jugadores) == n and not getattr(j, 'prestamo', None) and P.pendiente_de(e, j) is None
    print("  test_bloqueo_prestamos: OK")


def test_sin_sancion_todo_sigue_igual():
    from alpha_football import negociacion as N, prestamos as P
    e = estado_carrera(); mi = e['mi_equipo']
    club = e['liga'].equipos[3]; j = min(club.jugadores, key=lambda x: x.overall)
    mi.balance = 10 ** 10
    assert N.evaluar_compra(e, j, club, 10 ** 9)[0] == 'acepta'
    assert "Sanción" not in P.evaluar_pedido(e, j, club, 6, 100)[1]
    N.iniciar_negociacion(e, j, club, 'fichaje', 'buscador_screen')
    assert e['neg']['msg'] is None
    print("  test_sin_sancion_todo_sigue_igual: OK")


def test_lo_acordado_antes_se_respeta():
    from alpha_football import traspasos_pendientes as TP
    e = estado_carrera(); mi = e['mi_equipo']
    club = e['liga'].equipos[3]; j = min(club.jugadores, key=lambda x: x.overall)
    TP.diferir_compra(e, j, club, 1)                       # firmado antes del cierre
    _sancionar(e)
    e['liga'].jornada_actual = 1
    assert TP.mercado_abierto(e), "la jornada 1 debe ser ventana"
    assert TP.ejecutar(e) == 1 and j in mi.jugadores and j not in club.jugadores
    print("  test_lo_acordado_antes_se_respeta: OK")


# ── Task 3: evaluación ───────────────────────────────────────────────────────────

def _info(**k):
    base = {'posicion': 3, 'resultado': 'cumplido', 'texto': 'Terminar entre los 5 primeros', 'monto': 0,
            'calif': 50, 'confianza': 70, 'veredicto': 'neutro', 'fallos_financieros': []}
    base.update(k)
    return base


def _con_tope(e, pos_max=5):
    obj = D.definir_objetivo(e); obj.update(tipo='mitad', pos_max=pos_max)
    return obj


def test_motivos_fallo():
    assert D.motivos_fallo({}) == []
    assert D.motivos_fallo(_info()) == []
    m = D.motivos_fallo(_info(resultado='fallado', posicion=9,
                              fallos_financieros=['masa salarial $12.0M sobre el tope de $10.0M']))
    assert m == ["Terminaste 9º; la meta era: Terminar entre los 5 primeros",
                 "Masa salarial $12.0M sobre el tope de $10.0M"]
    print("  test_motivos_fallo: OK")


def test_texto_evaluacion_variantes():
    t = D.texto_evaluacion
    assert t(_info()).startswith("Cumplió con todo lo que le pedimos")
    assert t(_info(resultado='superado', veredicto='felicitacion')).startswith("Temporada sobresaliente")
    uno = t(_info(resultado='fallado', posicion=9, veredicto='regano'))
    assert uno.startswith("Cumplió con todo menos con el objetivo de liga") and "muy importante" in uno
    assert "Es su advertencia" in uno
    dos = t(_info(resultado='fallado', posicion=9, veredicto='regano',
                  fallos_financieros=['masa salarial $12.0M sobre el tope de $10.0M']))
    assert dos.startswith("No cumplió con lo más importante:") and " y las finanzas (" in dos
    sec = t(_info(juveniles={'texto': 'Fichar un juvenil', 'resultado': 'fallado'},
                  marca={'texto': 'm', 'resultado': 'cumplido'}))
    assert sec.startswith("Cumplió con lo importante. Nos quedó pendiente el objetivo de Juveniles")
    assert "solo afecta su calificación" in sec and "Marca: cumplido" in sec and "Juveniles: fallado" in sec
    mixto = t(_info(resultado='fallado', veredicto='regano',
                    copa={'alcanzada': 'Octavos', 'texto': 'Cuartos', 'resultado': 'fallado'}))
    assert mixto.startswith("No cumplió con el objetivo de liga") and "Cumplió con todo menos" not in mixto
    assert "muy importante para nosotros. También quedó pendiente la copa" in mixto and "Copa: fallado" in mixto
    desp = t(_info(resultado='fallado', veredicto='despido', indemnizacion=250_000))
    assert desp.startswith("Lamentamos comunicarle que prescindimos de sus servicios: no cumplió con el objetivo de liga")
    assert "Es su advertencia" not in desp and "indemnización" in desp
    fin = t(_info(veredicto='fin_contrato'))
    assert fin.startswith("Su contrato ha finalizado") and "Cumplió con todo lo que le pedimos" in fin
    san = t(_info(veredicto='regano', fallos_financieros=['masa salarial $12.0M sobre el tope de $10.0M'],
                  sancion={'temporada': 2, 'masa': 12_000_000, 'tope': 10_000_000, 'salud_mala': True,
                           'multa': 4_000_000}))
    assert "La liga sanciona al club" in san and "multa de $4.0M" in san and "Finanzas: fallado" in san
    assert t({'posicion': 1, 'resultado': 'cumplido', 'texto': 't'})          # info mínima (saves viejos)
    print("  test_texto_evaluacion_variantes: OK")


def test_evaluar_registra_sancion_y_motivos():
    e = estado_carrera(); mi = e['mi_equipo']
    obj = _con_tope(e)
    obj['tope_salarial'] = F.masa_salarial(mi, e) - 1                         # un peso sobre el tope
    obj['saldo_minimo'] = 0
    mi.balance = _base(e) * 2                                                 # salud buena
    info = D.evaluar_temporada(e, 3)                                          # la liga se cumple
    s = e['datos_carrera']['sancion_liga']
    assert s['temporada'] == 2 and s['salud_mala'] is False and s['multa'] == 0
    assert info['sancion'] == s and info['sancion'] is not s and info['veredicto'] == 'regano'
    assert len(info['motivos']) == 1 and info['motivos'][0].startswith("Masa salarial")
    assert e['veredicto_pendiente']['info']['motivos'] == info['motivos']
    txt = C.bandeja(e)[0]['cuerpo']
    assert "con las finanzas (masa salarial" in txt and "muy importante" in txt
    assert ("Cumplió con todo menos" in txt) != ("También quedó pendiente" in txt)   # juntas se contradicen
    assert "La liga sanciona al club" in txt and "impone una multa" not in txt
    print("  test_evaluar_registra_sancion_y_motivos: OK")


def test_evaluar_salud_mala_trae_multa():
    e = estado_carrera(); mi = e['mi_equipo']
    obj = _con_tope(e); obj['tope_salarial'] = F.masa_salarial(mi, e) - 1
    obj['presupuesto_ref'] = 0                                                # sin premio: el saldo no cambia
    mi.balance = -1_000_000
    info = D.evaluar_temporada(e, 3)
    s = e['datos_carrera']['sancion_liga']
    assert s['salud_mala'] and s['multa'] == int(_base(e) * SL.MULTA_PCT_BASE)
    assert info['sancion']['multa'] == s['multa'] and len(info['motivos']) == 2    # tope y saldo mínimo
    assert "impone una multa" in C.bandeja(e)[0]['cuerpo']
    print("  test_evaluar_salud_mala_trae_multa: OK")


def test_sin_pasar_el_tope_no_hay_sancion():
    e = estado_carrera(); mi = e['mi_equipo']
    obj = _con_tope(e); obj['tope_salarial'] = F.masa_salarial(mi, e) + 1; obj['saldo_minimo'] = 0
    info = D.evaluar_temporada(e, 3)
    assert 'sancion_liga' not in e['datos_carrera'] and info['sancion'] is None and info['motivos'] == []
    print("  test_sin_pasar_el_tope_no_hay_sancion: OK")


def test_cierre_financiero_cobra_la_multa():
    e = estado_carrera(); mi = e['mi_equipo']
    s = _sancion_mala(e)
    F.cierre_temporada(e)
    assert s['multa_estado'] in ('pagada', 'impaga')
    if s['multa_estado'] == 'impaga':
        assert mi.balance <= 0 and mi.sancion_puntos >= SL.PUNTOS_MULTA
    print("  test_cierre_financiero_cobra_la_multa: OK")


# ── Task 4: veredicto ────────────────────────────────────────────────────────────

def test_veredicto_muestra_motivos_y_sancion():
    from alpha_football.ui import veredicto_screen as V
    info = _info(resultado='fallado', posicion=9, veredicto='regano',
                 fallos_financieros=['masa salarial $12.0M sobre el tope de $10.0M'],
                 sancion={'temporada': 2, 'salud_mala': True, 'multa': 4_000_000, 'masa': 12_000_000,
                          'tope': 10_000_000})
    lineas = V.lineas_veredicto({'tipo': 'regano', 'info': info})             # save viejo: sin 'motivos'
    textos = [t for t, _c in lineas]
    assert textos[0] == "Motivo: Terminaste 9º; la meta era: Terminar entre los 5 primeros"
    assert textos[1].startswith("Motivo: Masa salarial")
    assert all(c == 'rojo' for t, c in lineas if t.startswith("Motivo"))
    assert any(t.startswith("Sanción de la liga") and "multa de $4.0M" in t for t in textos)
    assert sum("9º" in t for t in textos) == 1 and len(lineas) <= 8           # la posición ya va en el motivo
    assert not any(t.startswith("Terminaste") for t in textos)
    info['motivos'] = ["Uno", "Dos", "Tres", "Cuatro"]                        # nunca más de 3 motivos
    assert sum(t.startswith("Motivo") for t, _c in V.lineas_veredicto({'tipo': 'despido', 'info': info})) == 3
    ok = V.lineas_veredicto({'tipo': 'neutro', 'info': _info()})
    assert not any(t.startswith(("Motivo", "Sanción")) for t, _c in ok)
    assert sum(t.startswith("Terminaste 3º") for t, _c in ok) == 1            # sin motivo de liga, la línea sigue
    for tipo, extra in (('regano', {'fallos_financieros': ['saldo $1.0M bajo el mínimo de $2.0M']}),
                        ('fin_contrato', {'resultado': 'fallado'})):         # regaño solo por finanzas; sin motivos
        otras = [t for t, _c in V.lineas_veredicto({'tipo': tipo, 'info': _info(**extra)})]
        assert sum(t.startswith("Terminaste 3º") for t in otras) == 1, tipo
    assert V.lineas_veredicto({'tipo': 'regano', 'info': {}})                 # info vacía no rompe
    e = estado_carrera()
    e['veredicto_pendiente'] = {'correo_id': -1, 'tipo': 'regano', 'info': info}; e['veredicto_paso'] = 1
    pygame.event.clear()
    assert V.render(screen, e) is None and 'veredicto_pendiente' in e         # dibuja sin romperse
    print("  test_veredicto_muestra_motivos_y_sancion: OK")


# ── Revisión final ───────────────────────────────────────────────────────────────

def test_el_juego_avisa_de_la_sancion_antes():
    from alpha_football.ui import objetivos_screen as OS
    e = estado_carrera(); mi = e['mi_equipo']
    obj = _con_tope(e)
    objetivos = next(m for m in C.bandeja(e) if m['asunto'].startswith("Objetivos de la temporada"))
    assert "sanción de la liga" in objetivos['cuerpo'] and "sin fichar" in objetivos['cuerpo']
    obj['tope_salarial'] = F.masa_salarial(mi, e) - 1
    D.avisar_tope_salarial(e)
    aviso = C.bandeja(e)[0]
    assert aviso['asunto'] == "Te pasaste del tope salarial"
    assert "la liga sancionará al club" in aviso['cuerpo'] and "sin fichar" in aviso['cuerpo']
    assert "sin fichar" in OS.TEXTO_REGLA_TOPE
    print("  test_el_juego_avisa_de_la_sancion_antes: OK")


def test_sancionado_no_recibe_la_meta_de_fichar_una_estrella():
    e = estado_carrera()
    _sancionar(e)
    for semilla in range(12):
        D._dc(e).pop('objetivo_marca', None)
        # v0.4.27.0: sancionado sale 'valor' o 'camisetas' (nunca 'estrella')
        assert D.definir_objetivo_marca(e, random.Random(semilla))['tipo'] in ('valor', 'camisetas'), semilla
    e2 = estado_carrera()                                   # sin sanción siguen saliendo las tres metas
    tipos = set()
    for semilla in range(12):
        D._dc(e2).pop('objetivo_marca', None)
        tipos.add(D.definir_objetivo_marca(e2, random.Random(semilla))['tipo'])
    assert tipos == {'valor', 'estrella', 'camisetas'}
    print("  test_sancionado_no_recibe_la_meta_de_fichar_una_estrella: OK")


def test_prestamo_acordado_antes_se_respeta():
    from alpha_football import prestamos as P, traspasos_pendientes as TP
    e = estado_carrera(); mi = e['mi_equipo']
    club = e['liga'].equipos[2]; j = min(club.jugadores, key=lambda x: x.overall)
    e['liga'].jornada_actual = 16                           # tras el mercado de invierno: se acuerda para la J1
    assert not TP.mercado_abierto(e), "la jornada 16 no debe ser ventana"
    P.iniciar(e, j, club, mi, 6, 50)
    assert P.pendiente_de(e, j) is not None and j in club.jugadores
    _sancionar(e)
    e['liga'].jornada_actual = 1
    assert TP.mercado_abierto(e), "la jornada 1 debe ser ventana"
    P.revisar_jornada(e)
    assert j in mi.jugadores and getattr(j, 'prestamo', None) and P.pendiente_de(e, j) is None
    print("  test_prestamo_acordado_antes_se_respeta: OK")


def test_cambiar_de_club_deja_la_sancion_atras():
    from alpha_football import negociacion as N
    e = estado_carrera(); viejo = e['mi_equipo']
    _sancionar(e)
    nuevo = e['liga'].equipos[4]
    D.cambiar_de_club(e, nuevo)
    assert e['mi_equipo'] is nuevo and SL.activa(e) is None and SL.motivo_bloqueo(e) is None
    club = e['liga'].equipos[3]; j = min(club.jugadores, key=lambda x: x.overall)
    nuevo.balance = 10 ** 10
    assert N.evaluar_compra(e, j, club, 10 ** 9)[0] == 'acepta'             # el club nuevo ficha normal
    assert e['datos_carrera']['sancion_liga']['club'] == viejo.nombre       # la sanción sigue siendo del viejo
    print("  test_cambiar_de_club_deja_la_sancion_atras: OK")


def test_cierre_real_de_temporada_sanciona_la_siguiente():
    from alpha_football import competiciones as CP
    from alpha_football.ui.resumen_temporada_screen import avanzar_nueva_temporada
    from alpha_football.ui.league_screen import inicializar_calendario_liga, completar_ligas_de_fondo
    from alpha_football.ui.match_screen import simular_otros_partidos, actualizar_estadisticas_liga
    e = estado_carrera(); mi = e['mi_equipo']; liga = e['liga']
    CP.iniciar_temporada(e, random.Random(5)); inicializar_calendario_liga(liga)
    obj = _con_tope(e, pos_max=len(liga.equipos))
    obj['tope_salarial'] = F.masa_salarial(mi, e) - 1                       # se pasa del tope...
    for j in range(1, liga.num_jornadas + 1):
        liga.jornada_actual = j
        simular_otros_partidos(liga, j)
        CP.avanzar(e)
    actualizar_estadisticas_liga(liga)
    completar_ligas_de_fondo(e)
    mi.puntos = 99                                                          # campeón: ni descenso ni despido
    mi.balance = -10 ** 9                                                   # ...y cierra en rojo: salud mala
    avanzar_nueva_temporada(e)
    s = SL.activa(e)
    assert e['temporada'] == 2 and e['mi_equipo'] is mi and not e.get('despido_pendiente')
    assert s is not None and s['temporada'] == 2 and s['salud_mala'] and SL.motivo_bloqueo(e)
    pres = e['datos_carrera']['presupuesto_temporada']['total']
    assert s['multa_estado'] == ('pagada' if pres >= s['multa'] else 'impaga')    # sobre el presupuesto NUEVO
    assert F.libro(e)['premios'] == -min(pres, s['multa'])
    if s['multa_estado'] == 'impaga':
        assert s['puntos'] == SL.PUNTOS_MULTA and mi.sancion_puntos == F.PUNTOS_QUIEBRA + SL.PUNTOS_MULTA
        assert mi.puntos == -mi.sancion_puntos                               # −6 por el rojo y −6 por la multa
    info = e['veredicto_pendiente']['info']
    assert info['sancion']['temporada'] == 2 and any(m.startswith("Masa salarial") for m in info['motivos'])
    print("  test_cierre_real_de_temporada_sanciona_la_siguiente: OK")


# ── La sanción a la vista durante la temporada ───────────────────────────────────

def test_texto_corto_de_la_sancion():
    base = "Sanción de la liga: sin fichajes, libres ni préstamos esta temporada"
    assert SL.texto_corto({'salud_mala': False, 'multa': 0, 'multa_estado': None}) == base
    con_multa = {'salud_mala': True, 'multa': 4_000_000, 'puntos': 0}
    assert SL.texto_corto(dict(con_multa, multa_estado='pagada')) == base + " · multa de $4.0M pagada"
    assert SL.texto_corto(dict(con_multa, multa_estado='impaga', puntos=SL.PUNTOS_MULTA)) == \
        base + f" · multa impaga: −{SL.PUNTOS_MULTA} puntos"
    assert SL.texto_corto(dict(con_multa, multa_estado=None)) == base         # todavía sin cobrar
    assert SL.texto_corto({}) == base                                         # datos mínimos no rompen
    print("  test_texto_corto_de_la_sancion: OK")


def _dibujado(pantalla, e):
    """[(texto, rect, color)] de lo que una pantalla dibuja con draw_text (lo espía); exige que no falle."""
    from alpha_football.ui.theme import get_font
    vistos, orig = [], pantalla.draw_text

    def espia(scr, txt, pos, **k):
        vistos.append((txt, pygame.Rect(pos, get_font(k.get('size', 'md')).size(txt)), k.get('color', 'blanco')))
        return orig(scr, txt, pos, **k)
    pantalla.draw_text = espia
    try:
        pygame.event.clear(); assert pantalla.render(screen, e) is None       # None: ni salió ni cayó en el except
    finally:
        pantalla.draw_text = orig
    return vistos


def test_finanzas_muestra_la_sancion_vigente():
    from alpha_football.ui import finanzas_screen as FS
    sancion = lambda vistos: [v for v in vistos if v[0].startswith("Sanción de la liga")]
    e = estado_carrera()
    assert not sancion(_dibujado(FS, e))                                      # sin sanción no sale nada
    s = _sancion_mala(e)                                                      # vigente y en rojo: el panel lleno
    s['multa'], e['datos_carrera']['jornadas_en_rojo'] = 1_234_500_000, 2
    D.definir_objetivo(e)['espaldarazo'] = {'pct': 0.2, 'puestos': 2, 'deuda': 7_500_000}
    for multa_estado in (None, 'pagada', 'impaga'):
        s['multa_estado'] = multa_estado
        vistos = _dibujado(FS, e)
        assert any(t.startswith("¡EN ROJO!") for t, _r, _c in vistos) and any("Deuda" in t for t, _r, _c in vistos)
        (txt, r, color), = sancion(vistos)                                    # una sola línea
        assert txt == SL.texto_corto(s) and color == 'rojo', multa_estado
        assert FS.R_LIBRO.contains(r.inflate(40, 0)), (multa_estado, r)       # cabe en su panel, con el margen
        assert not [t for t, r2, _c in vistos if t != txt and r2.colliderect(r)], multa_estado   # no pisa nada
    e['temporada'] = 3                                                        # dura una temporada
    assert not sancion(_dibujado(FS, e))
    print("  test_finanzas_muestra_la_sancion_vigente: OK")


TESTS = [test_registrar_salud_buena_sin_multa, test_registrar_salud_mala_multa_40,
         test_activa_solo_club_y_temporada, test_sin_sancion_o_datos_rotos_no_bloquea,
         test_multa_pagada_una_sola_vez, test_multa_impaga_quita_presupuesto_y_puntos,
         test_multa_no_se_cobra_con_salud_buena_ni_a_otro_club,
         test_bloqueo_compra_y_agente_libre, test_bloqueo_se_ve_al_abrir_la_negociacion,
         test_bloqueo_prestamos, test_sin_sancion_todo_sigue_igual, test_lo_acordado_antes_se_respeta,
         test_motivos_fallo, test_texto_evaluacion_variantes, test_evaluar_registra_sancion_y_motivos,
         test_evaluar_salud_mala_trae_multa, test_sin_pasar_el_tope_no_hay_sancion,
         test_cierre_financiero_cobra_la_multa, test_veredicto_muestra_motivos_y_sancion,
         test_el_juego_avisa_de_la_sancion_antes, test_sancionado_no_recibe_la_meta_de_fichar_una_estrella,
         test_prestamo_acordado_antes_se_respeta, test_cambiar_de_club_deja_la_sancion_atras,
         test_cierre_real_de_temporada_sanciona_la_siguiente,
         test_texto_corto_de_la_sancion, test_finanzas_muestra_la_sancion_vigente]

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
