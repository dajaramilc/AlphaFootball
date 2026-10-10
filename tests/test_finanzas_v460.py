"""v4.6.0: economía más dura, quiebra del user y de la IA, objetivos financieros, espaldarazo como
deuda y ofertas de clubes durante la temporada."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(46)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import finanzas as F, save
from alpha_football.models import alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams, _ligas_por_division

save.guardar_en_slot = lambda *a, **k: None          # los tests no tocan los slots reales


def estado_carrera(tipo='premier', idx=0):
    liga = load_league_teams(tipo)
    mi = liga.equipos[idx]
    mi.alineacion_activa = alineacion_por_defecto(mi)
    primeras, segunda = _ligas_por_division(liga, {}, {})
    return {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
            'alineacion_activa': mi.alineacion_activa, 'primera_division': primeras,
            'segunda_division': segunda, 'datos_carrera': {}, 'historial': []}


# ---------------------------------------------------------------- Task 1: economía
def test_ingresos_por_club():
    e = estado_carrera(); liga = e['liga']
    grande = max(liga.equipos, key=lambda x: x.estrellas); chico = min(liga.equipos, key=lambda x: x.estrellas)
    assert F.presupuesto_base(grande, 'premier', 1) > F.presupuesto_base(chico, 'premier', 1)
    base = F.presupuesto_base(grande, 'premier', 1)
    assert F.ingresos_esperados(grande, 'premier', 1) == int(base * F.PATROCINIO_FRAC) + int(base * F.TAQUILLA_FRAC)
    e['mi_equipo'] = grande
    mov = F.procesar_jornada(e, es_local=False, gf=0, gc=0)
    from alpha_football import patrocinios as P                      # v4.9.0: cobran los contratos
    assert mov['patrocinio'] == P.cobro_jornada(e) > 0
    print("  test_ingresos_por_club: OK")


def test_migracion_una_sola_vez():
    e = estado_carrera(); F.asegurar_contratos(e)
    j = e['mi_equipo'].jugadores[0]; j.salario = 1_000_000
    e['datos_carrera']['contratos_v290'] = True           # save viejo: ya tenía contratos
    assert F.migrar_economia(e) and j.salario == 1_600_000
    assert not F.migrar_economia(e) and j.salario == 1_600_000
    print("  test_migracion_una_sola_vez: OK")


# ---------------------------------------------------------------- Task 2: quiebra del user
def _asuntos(e):
    return [m['asunto'] for m in e['datos_carrera'].get('correo', [])]


def test_rojo_avisa_y_vende_en_la_4a():
    from alpha_football.market import calcular_valor
    e = estado_carrera(); mi = e['mi_equipo']; mi.balance = -200_000_000
    estrella = max(mi.jugadores, key=calcular_valor)
    for n in range(1, 4):
        F.procesar_jornada(e, es_local=False, gf=0, gc=0)
        assert estrella in mi.jugadores and e['datos_carrera']['jornadas_en_rojo'] == n
    assert sum(1 for a in _asuntos(e) if 'rojo' in a.lower() or 'negativo' in a.lower()) == 3
    F.procesar_jornada(e, es_local=False, gf=0, gc=0)
    assert estrella not in mi.jugadores and any('venta forzada' in a.lower() for a in _asuntos(e))
    print("  test_rojo_avisa_y_vende_en_la_4a: OK")


def test_saldo_recuperado_resetea():
    e = estado_carrera(); mi = e['mi_equipo']; mi.balance = -1
    F.procesar_jornada(e, es_local=True, gf=1, gc=0)
    if mi.balance < 0:
        mi.balance = 10_000_000
        F.procesar_jornada(e, es_local=True, gf=1, gc=0)
    assert e['datos_carrera']['jornadas_en_rojo'] == 0
    print("  test_saldo_recuperado_resetea: OK")


def test_temporada_en_rojo_resta_puntos_y_la_2a_despide():
    e = estado_carrera(); mi = e['mi_equipo']
    for j in mi.jugadores:
        j.contrato_anios = 3
    mi.balance = -1; mi.puntos = 0
    F.cierre_temporada(e)
    assert mi.puntos == -F.PUNTOS_QUIEBRA and not e.get('despido_pendiente')
    assert e['datos_carrera']['temporadas_en_rojo'] == 1
    mi.balance = -1
    F.cierre_temporada(e)
    assert e['despido_pendiente'] and 'quiebra' in e['despido_pendiente']['motivo'].lower()
    e2 = estado_carrera(); e2['datos_carrera']['temporadas_en_rojo'] = 1; e2['mi_equipo'].balance = 5
    F.cierre_temporada(e2)
    assert e2['datos_carrera']['temporadas_en_rojo'] == 0
    print("  test_temporada_en_rojo_resta_puntos_y_la_2a_despide: OK")


# ---------------------------------------------------------------- Task 3: quiebra de la IA
def test_quiebra_ia_remata_sanciona_y_avisa():
    from alpha_football import mercado_ia as MI
    e = estado_carrera(); liga = e['liga']
    eq = liga.equipos[5]; eq.puntos = 0
    tops = sorted(eq.jugadores, key=lambda j: -j.overall)[:3]
    for c in liga.equipos:
        c.balance = 10**10
    eq.balance = -10**10
    quebrados = MI.ingresos_fin_temporada(e, random.Random(1))
    assert eq.nombre in quebrados
    assert eq.puntos == -F.PUNTOS_QUIEBRA and eq.sin_fichajes_hasta == e['temporada']
    en_remate = [j for j in tops if j.remate]          # v0.4.21.0: esperan 7 días en el club (primero el user)
    assert 2 <= len(en_remate) <= 3 and all(j in eq.jugadores for j in en_remate)
    from alpha_football import noticias as NO                  # v0.4.23.0: noticia, ya no correo de Prensa
    noticia = next(n for n in NO.lista(e) if n['titular'] == f"Quiebra en {eq.nombre}")
    assert (noticia['tipo'], noticia['importancia']) == ('economia', 4) and noticia['equipos_ids'] == [eq.id]
    assert noticia['accion']['pantalla'] == 'buscador_screen' and all(j.apellido in noticia['cuerpo'] for j in en_remate)
    assert not [m for m in e['datos_carrera'].get('correo', []) if m['remitente'] == 'prensa']
    for r in e['datos_carrera']['remates']:
        r['vence'] = '2000-01-01'
    MI.resolver_remates(e, random.Random(1))
    assert all(j not in eq.jugadores for j in en_remate)   # vencido el plazo, se los lleva la IA
    print("  test_quiebra_ia_remata_sanciona_y_avisa: OK")


def test_ia_sin_fichajes_no_compra():
    from alpha_football import mercado_ia as MI
    e = estado_carrera()
    for eq in e['liga'].equipos:
        eq.balance = 10**10
        eq.sin_fichajes_hasta = e['temporada']
    log = MI.ronda_fichajes_ia(e, 'pretemporada', random.Random(2))
    assert not any(l.startswith(eq.nombre + ' ficha a ') for eq in e['liga'].equipos for l in log)
    print("  test_ia_sin_fichajes_no_compra: OK")


def test_remate_sin_comprador_queda_barato_para_el_user():
    from alpha_football import mercado_ia as MI, negociacion as N
    from alpha_football.market import calcular_valor
    e = estado_carrera(); eq = e['liga'].equipos[6]
    for liga in list(e['primera_division'].values()) + list(e['segunda_division'].values()):
        for c in getattr(liga, 'equipos', []) or []:
            c.balance = 0                              # nadie puede pagar
    eq.balance = -1
    rem = MI.quiebra_ia(e, eq, random.Random(3))
    libres = [j for j, comp, _p in rem if comp is None]
    assert libres and all(j.remate and j in eq.jugadores for j in libres)
    j = libres[0]
    from alpha_football.market import cifra_cerrada      # v0.4.18.0: el remate sale en cifra cerrada
    esperado = cifra_cerrada((int(getattr(j, 'valor', 0) or 0) or calcular_valor(j)) * MI.PRECIO_REMATE)
    assert N.precio_fichaje(j) == esperado and N.minimo_club(j, eq) == esperado
    N.registrar_pase(e, j, eq.nombre, 'Otro', 1, False)
    assert not j.remate
    print("  test_remate_sin_comprador_queda_barato_para_el_user: OK")


def test_campos_nuevos_persisten():
    from alpha_football.models import Equipo
    e = estado_carrera(); eq = e['liga'].equipos[0]; eq.sin_fichajes_hasta = 3
    j = eq.jugadores[0]; j.remate = True
    eq2 = Equipo.from_dict(eq.to_dict())
    assert eq2.sin_fichajes_hasta == 3 and eq2.jugadores[0].remate
    d = eq.to_dict(); d.pop('sin_fichajes_hasta')
    assert Equipo.from_dict(d).sin_fichajes_hasta == 0
    print("  test_campos_nuevos_persisten: OK")


# ---------------------------------------------------------------- Task 4: objetivos
def _objetivo(e, balance=50_000_000):
    from alpha_football import directiva as D
    e['mi_equipo'].balance = balance
    return D.definir_objetivo(e)


def test_objetivo_sin_margen_y_titulo_con_5():
    from alpha_football import directiva as D
    assert D.objetivo_por_ranking(4, 20, 1, 4)[:2] == ('copa', 4)
    assert D.objetivo_por_ranking(8, 20, 1, 4)[:2] == ('mitad', 8)
    assert D.objetivo_por_ranking(1, 20, 1, 4, ventaja=5)[:2] == ('campeon', 1)
    print("  test_objetivo_sin_margen_y_titulo_con_5: OK")


def test_objetivos_financieros_definidos_y_completados():
    from alpha_football import directiva as D
    e = estado_carrera(); obj = _objetivo(e)
    liga = e['liga']
    assert obj['tope_salarial'] == int(max(D.TOPE_SALARIAL_PCT * F.ingresos_esperados(e['mi_equipo'], liga.tipo, liga.division),
                                           D.MARGEN_MASA_INICIAL * F.masa_salarial(e['mi_equipo'], e)))
    assert obj['saldo_minimo'] == int(D.SALDO_MIN_PCT * 50_000_000)
    viejo = {k: v for k, v in obj.items() if k not in ('tope_salarial', 'saldo_minimo')}
    e['datos_carrera']['objetivo'] = viejo                  # save viejo
    assert 'tope_salarial' in D.definir_objetivo(e) and 'saldo_minimo' in D.definir_objetivo(e)
    print("  test_objetivos_financieros_definidos_y_completados: OK")


def test_fallo_financiero_cuenta_como_fallo():
    from alpha_football import directiva as D
    e = estado_carrera(); obj = _objetivo(e)
    obj['tope_salarial'] = 1                                # masa salarial muy por encima
    info = D.evaluar_temporada(e, 1)                        # deportivo superado
    assert info['resultado'] == 'superado' and info['fallos_financieros']
    assert info['veredicto'] == 'regano' and e['datos_carrera']['advertencia_dt']
    e2 = estado_carrera(); obj2 = _objetivo(e2); obj2['tope_salarial'] = 10**12
    e2['mi_equipo'].balance = -20_000_000                   # + premio 30% (15M) = −5M < mínimo (5M)
    assert D.evaluar_temporada(e2, 1)['fallos_financieros']
    print("  test_fallo_financiero_cuenta_como_fallo: OK")


def test_aviso_tope_salarial_una_vez_por_mitad():
    from alpha_football import directiva as D
    e = estado_carrera(); obj = _objetivo(e); obj['tope_salarial'] = 1
    e['liga'].jornada_actual = 3
    D.avisar_tope_salarial(e); D.avisar_tope_salarial(e)
    avisos = [m for m in e['datos_carrera']['correo'] if 'tope salarial' in m['asunto'].lower()]
    assert len(avisos) == 1
    e['liga'].jornada_actual = e['liga'].num_jornadas // 2 + 1
    D.avisar_tope_salarial(e)
    assert len([m for m in e['datos_carrera']['correo'] if 'tope salarial' in m['asunto'].lower()]) == 2
    print("  test_aviso_tope_salarial_una_vez_por_mitad: OK")


# ---------------------------------------------------------------- Task 5: espaldarazo = deuda
def test_espaldarazo_se_descuenta_al_cierre():
    from alpha_football import directiva as D
    e = estado_carrera(); obj = _objetivo(e, balance=40_000_000)
    obj['tope_salarial'] = 10**12; obj['saldo_minimo'] = 0
    e['liga'].jornada_actual = 1
    ok, _ = D.pedir_espaldarazo(e, 0)
    assert ok and D.deuda_espaldarazo(e) == 3_000_000 and e['mi_equipo'].balance == 46_000_000
    info = D.evaluar_temporada(e, 1)
    assert info['deuda'] == 3_000_000   # v4.7.0: solo la mitad
    assert e['mi_equipo'].balance == 46_000_000 + info['monto'] - 3_000_000
    print("  test_espaldarazo_se_descuenta_al_cierre: OK")


# ---------------------------------------------------------------- Task 6: ofertas de clubes
class _Siempre(random.Random):
    def random(self):
        return 0.0


def _con_jugadas(n):
    from alpha_football import directiva as D
    D._jugadas = lambda l, m: n


def test_oferta_segun_calif_y_maximo_2():
    from alpha_football import ofertas_dt as O, directiva as D
    orig = D._jugadas
    try:
        e = estado_carrera(); liga = e['liga']; mi = e['mi_equipo']
        from alpha_football.ui.league_screen import inicializar_calendario_liga
        inicializar_calendario_liga(liga)
        e['datos_carrera']['calif_dt'] = 80
        _con_jugadas(3)
        O.revisar_jornada(e, _Siempre(1))
        of = O.oferta_vigente(e)
        assert of and of['media'] >= round(mi.ovr_promedio, 1)
        assert any('quiere' in m['asunto'].lower() for m in e['datos_carrera']['correo'])
        O.rechazar(e); assert O.oferta_vigente(e) is None
        O.revisar_jornada(e, _Siempre(2)); O.rechazar(e)
        O.revisar_jornada(e, _Siempre(3))
        assert O.oferta_vigente(e) is None                         # ya hubo 2 esta temporada
    finally:
        D._jugadas = orig
    print("  test_oferta_segun_calif_y_maximo_2: OK")


def test_oferta_vence_y_aceptar_cambia_de_club():
    from alpha_football import ofertas_dt as O, directiva as D
    orig = D._jugadas
    try:
        e = estado_carrera(); liga = e['liga']
        from alpha_football.ui.league_screen import inicializar_calendario_liga
        inicializar_calendario_liga(liga)
        e['datos_carrera']['calif_dt'] = 55
        _con_jugadas(3)
        O.revisar_jornada(e, _Siempre(4))
        assert O.oferta_vigente(e)
        _con_jugadas(3 + O.PLAZO)
        O.revisar_jornada(e, random.Random(5))                    # solo vence
        assert O.oferta_vigente(e) is None
        _con_jugadas(4)
        e['datos_carrera']['ofertas_dt_temporada'] = [1, 0]
        O.revisar_jornada(e, _Siempre(6))
        of = O.oferta_vigente(e); viejo = e['mi_equipo']
        msg = O.aceptar(e)
        assert e['mi_equipo'] is not viejo and e['mi_equipo'].nombre == of['club'] and of['club'] in msg
        assert O.oferta_vigente(e) is None and e['historial'][-1].get('se_fue')
        assert 'objetivo' not in e['datos_carrera'] and 'pedido' not in e['datos_carrera']
    finally:
        D._jugadas = orig
    from alpha_football.ui import league_screen as LS
    if not getattr(e['liga'], 'calendario', None):
        LS.inicializar_calendario_liga(e['liga'])
    pygame.event.clear()
    assert LS.render(screen, e) != 'menu'                         # el hub de la liga nueva abre
    assert any(eq is e['mi_equipo'] for eq in e['liga'].equipos)
    print("  test_oferta_vence_y_aceptar_cambia_de_club: OK")


# ---------------------------------------------------------------- Task 7: pantalla OBJETIVOS
def _click(pos):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def test_pantalla_objetivos_reglas():
    from alpha_football.ui import objetivos_screen as OS
    e = estado_carrera(); _objetivo(e)
    assert OS.color_barra_tope(0.5) == 'verde' and OS.color_barra_tope(0.9) == 'dorado' and OS.color_barra_tope(1.2) == 'rojo'
    pygame.event.clear(); assert OS.render(screen, e) is None
    _click(OS.R_AYUDA_META.center); OS.render(screen, e)
    assert e.get('objetivos_reglas_abierto')
    _click((5, 5)); OS.render(screen, e)
    assert not e.get('objetivos_reglas_abierto')
    print("  test_pantalla_objetivos_reglas: OK")    # v4.7.0: la oferta de club se prueba en OFERTAS DT


# ---------------------------------------------------------------- revisión final
def test_sancion_sobrevive_al_recuento_de_la_tabla():
    from alpha_football.ui.match_screen import actualizar_estadisticas_liga
    from alpha_football import mercado_ia as MI
    e = estado_carrera(); mi = e['mi_equipo']
    for j in mi.jugadores:
        j.contrato_anios = 3
    mi.balance = -1
    F.cierre_temporada(e)
    eq = e['liga'].equipos[5]; eq.balance = -10**10
    MI.quiebra_ia(e, eq, random.Random(1))
    actualizar_estadisticas_liga(e['liga'])                   # recuento tras una jornada
    assert mi.puntos == -F.PUNTOS_QUIEBRA and eq.puntos == -F.PUNTOS_QUIEBRA
    from alpha_football.models import Equipo
    assert Equipo.from_dict(mi.to_dict()).sancion_puntos == F.PUNTOS_QUIEBRA
    print("  test_sancion_sobrevive_al_recuento_de_la_tabla: OK")


def test_save_viejo_migra_antes_del_tope():
    from alpha_football.ui import league_screen as LS
    e = estado_carrera(); F.asegurar_contratos(e)
    for eq in [x for l in e['primera_division'].values() for x in l.equipos]:
        for j in eq.jugadores:
            j.salario = int(j.salario / F.FACTOR_MIGRACION_SALARIOS)   # sueldos al 5% (save viejo)
    e['datos_carrera']['contratos_v290'] = True
    LS.inicializar_calendario_liga(e['liga'])
    pygame.event.clear(); LS.render(screen, e)
    obj = e['datos_carrera']['objetivo']
    assert e['datos_carrera'].get('economia_v2')
    assert obj['tope_salarial'] >= int(1.10 * F.masa_salarial(e['mi_equipo'], e)) - 1
    print("  test_save_viejo_migra_antes_del_tope: OK")


def test_despido_doble_indemniza_una_vez_y_no_es_renovable():
    from alpha_football import directiva as D, carrera_dt as CD
    e = estado_carrera()
    llamadas = []
    orig = CD.cobrar_indemnizacion
    CD.cobrar_indemnizacion = lambda est, t: llamadas.append(t) or 1000
    try:
        D.marcar_despido(e, "No cumpliste.")
        D.marcar_despido(e, "Quiebra.")
    finally:
        CD.cobrar_indemnizacion = orig
    assert len(llamadas) == 1 and 'Quiebra' in e['despido_pendiente']['motivo']
    e2 = estado_carrera()
    D.marcar_despido(e2, "Terminó tu contrato.", indemnizar=False, titulo="FIN DE CONTRATO", renovable=True)
    D.marcar_despido(e2, "Quiebra: dos temporadas.", indemnizar=False)
    assert not e2['despido_pendiente'].get('renovable') and e2['despido_pendiente']['titulo'] == "¡DESPEDIDO!"
    print("  test_despido_doble_indemniza_una_vez_y_no_es_renovable: OK")


def test_oferta_completa_plazo_y_aceptar_va_al_contrato():
    from alpha_football.ui import objetivos_screen as OS
    from alpha_football import ofertas_dt as O, directiva as D
    orig = D._jugadas
    try:
        e = estado_carrera(); _objetivo(e)
        e['liga'].calendario = e['liga'].calendario or []
        e['datos_carrera']['calif_dt'] = 55
        _con_jugadas(3)
        O.revisar_jornada(e, _Siempre(7))
        of = O.oferta_vigente(e)
        assert of and of.get('objetivo') and 'presupuesto' in of
        from alpha_football.ui import ofertas_dt_screen as S     # v4.7.0: la oferta se responde en OFERTAS DT
        pygame.event.clear(); _click(S.rect_aceptar(0).center)
        assert S.render(screen, e) == 'contrato_dt_screen' and e.get('contrato_modo') == 'alta'
    finally:
        D._jugadas = orig
    print("  test_oferta_completa_plazo_y_aceptar_va_al_contrato: OK")


def test_cambiar_de_club_borra_la_oferta_vieja():
    from alpha_football import directiva as D, ofertas_dt as O
    e = estado_carrera(); otro = e['liga'].equipos[4]
    e['datos_carrera']['oferta_dt'] = {'club_id': otro.id, 'club': otro.nombre, 'liga': '', 'media': 70, 'temporada': 1, 'vence': 9}
    D.cambiar_de_club(e, e['liga'].equipos[2])
    assert O.oferta_vigente(e) is None
    print("  test_cambiar_de_club_borra_la_oferta_vieja: OK")


TESTS = [f for n, f in list(globals().items()) if n.startswith('test_') and callable(f)]


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
