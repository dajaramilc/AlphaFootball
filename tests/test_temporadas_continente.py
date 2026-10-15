"""v0.4.16.0: temporadas por continente (desfase por fecha, cierre del otro continente, tu cierre, copas por
continente, cambio de continente y saves viejos)."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
from datetime import date, timedelta
from test_calendario import screen, key, _e, _jugar   # noqa: E402  (deja save.guardar_en_slot sin efecto)
from alpha_football import calendario as CAL, correo as C, dias as D, temporada as T, temporadas as TS
from alpha_football import competiciones as CP
from alpha_football.paises import EUROPA, SUDAMERICA


def _ligas_de(e, paises):
    """Las ligas (1ª y 2ª) de esos países."""
    return [l for mapa in (e['primera_division'], e['segunda_division']) for t, l in mapa.items()
            if l is not None and t in paises]


def _jugados(liga) -> int:
    """Jornadas completas ya jugadas en esa liga."""
    cal = getattr(liga, 'calendario', None) or []
    return max((p.jornada for p in cal if p.jugado), default=0)


# --- Task 1: el mundo ─────────────────────────────────────────────────────────

def test_continentes_y_anios():
    assert set(TS.paises_de('europa')) == set(EUROPA) and set(TS.paises_de('sudamerica')) == set(SUDAMERICA)
    assert len(EUROPA) == 3 and len(SUDAMERICA) == 5
    assert TS.continente_de('premier') == 'europa' and TS.continente_de('betplay') == 'sudamerica'
    assert TS.otro('europa') == 'sudamerica' and TS.otro('sudamerica') == 'europa'
    assert TS.anio_en('europa', date(2027, 6, 30)) == 2026 and TS.anio_en('europa', date(2027, 7, 1)) == 2027
    assert TS.anio_en('sudamerica', date(2026, 12, 31)) == 2026 and TS.anio_en('sudamerica', date(2027, 1, 1)) == 2027


def test_sin_marca_no_hay_desfase():
    e = _e()
    assert not TS.activo(e) and 'mundo' not in e['datos_carrera']          # leer no deja la marca
    assert TS.anio(e, 'europa') == CAL.anio(e) == 2026
    assert TS.anio(e, 'sudamerica') == 2026                                # el 1 de julio de 2026 corre la 2026
    assert TS.fin(e, 'europa') == date(2027, 6, 30) and TS.fin(e, 'sudamerica') == date(2026, 12, 31)
    assert len(TS.ligas(e)) == 16 and len(TS.ligas(e, SUDAMERICA)) == 10 and len(TS.ligas(e, EUROPA)) == 6


def test_la_jornada_del_otro_continente_sale_de_la_fecha():
    e = _e()
    liga = e['primera_division']['betplay']
    n = liga.num_jornadas
    sabs = CAL.sabados(n, 'sudamerica', 2026)
    esperado = sum(1 for s in sabs if s <= date(2026, 7, 1))
    assert TS.jornadas_por_fecha(e, liga, date(2026, 7, 1)) == esperado and 6 <= esperado <= n // 2 + 1
    assert TS.fecha_jornada(e, liga, 1) == sabs[0] and TS.fecha_jornada(e, liga, n) == sabs[-1]
    assert TS.jornadas_por_fecha(e, liga, date(2026, 12, 31)) == n
    assert TS.jornadas_por_fecha(e, liga, date(2026, 1, 1)) == 0


# --- Task 2: filtros de países ────────────────────────────────────────────────

def _saldos(e, paises):
    return {eq.nombre: eq.balance for l in _ligas_de(e, paises) for eq in l.equipos if eq is not e['mi_equipo']}


def test_los_filtros_de_paises_solo_tocan_esas_ligas():
    from alpha_football.ui import league_screen as L
    from alpha_football.ui.copa_screen import guardar_ranking_copas
    from alpha_football import nivel_temporada as NT, mercado_ia as MIA
    e = _e()
    L.completar_ligas_de_fondo(e, paises=SUDAMERICA)
    assert all(_jugados(l) == l.num_jornadas for l in _ligas_de(e, SUDAMERICA))
    assert all(_jugados(l) == 0 for l in _ligas_de(e, EUROPA))
    e['datos_carrera']['copa_ranking'] = {'premier': ['A', 'B'], 'betplay': ['viejo']}
    guardar_ranking_copas(e, paises=SUDAMERICA)
    rk = e['datos_carrera']['copa_ranking']
    assert rk['premier'] == ['A', 'B'] and set(rk) == {'premier'} | set(SUDAMERICA)        # funde, no reemplaza
    campeon = max(e['primera_division']['betplay'].equipos, key=lambda x: (x.puntos, x.gf - x.gc, x.gf))
    assert rk['betplay'][0] == campeon.nombre and len(rk['betplay']) == 12
    europeos = _saldos(e, EUROPA); sudamericanos = _saldos(e, SUDAMERICA)
    MIA.ingresos_fin_temporada(e, random.Random(1), paises=SUDAMERICA)
    assert _saldos(e, EUROPA) == europeos and _saldos(e, SUDAMERICA) != sudamericanos
    e['datos_carrera']['objetivos_ia'] = {'temporada': 1, 'pos_max': {'Club europeo': 3, 'Club viejo': 9}}
    NT.foto_objetivos_ia(e, paises=SUDAMERICA)
    pm = e['datos_carrera']['objetivos_ia']['pos_max']
    assert pm['Club europeo'] == 3 and campeon.nombre in pm                                 # funde
    NT.preparar(e, paises=SUDAMERICA)
    ids_sud = {id(eq) for l in _ligas_de(e, SUDAMERICA) for eq in l.equipos}
    assert set(e['_nivel_plan']) == ids_sud


def test_el_cierre_de_dts_con_filtro_no_borra_tus_ofertas():
    from alpha_football import entrenadores as EN
    e = _e()
    EN.asegurar_dts(e)
    d = EN.dts(e)
    d['ofertas'], d['despidos_temp'] = [{'club_id': 'x'}], {'algo': 1}
    EN.cierre_temporada(e, random.Random(1), paises=SUDAMERICA)            # tu liga (premier) no está en el filtro
    assert d['ofertas'] == [{'club_id': 'x'}] and d['despidos_temp'] == {'algo': 1}
    EN.cierre_temporada(e, random.Random(1), paises=EUROPA)
    assert d['ofertas'] == [] and d['despidos_temp'] == {}


def test_sin_filtro_todo_como_hoy():
    from alpha_football.ui import league_screen as L
    from alpha_football.ui.copa_screen import guardar_ranking_copas
    from alpha_football import nivel_temporada as NT
    e = _e()
    assert len(L._ligas_de_fondo(e)) == 15 and len(L._ligas_de_fondo(e, SUDAMERICA)) == 10   # todas menos la tuya
    L.simular_jornada_segunda_division(e)
    assert all(_jugados(l) == 1 for l in _ligas_de(e, EUROPA + SUDAMERICA) if l is not e['liga'])
    e['datos_carrera']['copa_ranking'] = {'fantasma': ['x']}
    guardar_ranking_copas(e)
    assert set(e['datos_carrera']['copa_ranking']) == set(EUROPA + SUDAMERICA)               # sin filtro reemplaza
    NT.foto_objetivos_ia(e)
    assert len(e['datos_carrera']['objetivos_ia']['pos_max']) >= 16 * 12 - 4
    NT.preparar(e)
    assert len(e['_nivel_plan']) == 16 * 12


# --- Task 3: copas por continente ─────────────────────────────────────────────

def _marcar(e):
    """Pone la marca del desfase a mano (sin jugar nada) y sortea las copas con el año de su continente."""
    m = TS.mundo(e)
    m['desfase'] = True
    m['anio'] = {'europa': 2026, 'sudamerica': 2026}
    CP.iniciar_temporada(e, random.Random(1), forzar=True)
    return m


def _fechas_jugadas(e, tipo) -> int:
    return len({p['fecha'] for p in CP.copa(e, tipo)['partidos'] if p['jugado']})


def test_cada_copa_sigue_la_jornada_de_su_continente():
    from alpha_football.ui import league_screen as L
    e = _e(); _marcar(e)
    assert CP.copa(e, 'champions')['anio'] == 2026 and CP.copa(e, 'libertadores')['anio'] == 2026
    for _ in range(11):
        L.simular_jornada_segunda_division(e, paises=SUDAMERICA)           # Sudamérica va por la J12; tú, por la J1
    assert CP._jornada_copa(e, 'champions') == 1 and CP._jornada_copa(e, 'libertadores') == 12
    CP.avanzar(e, random.Random(1))
    assert _fechas_jugadas(e, 'libertadores') >= 4 and _fechas_jugadas(e, 'champions') == 0


def test_rehacer_una_copa_no_toca_la_otra():
    e = _e(); m = _marcar(e)
    champions = CP.copa(e, 'champions')
    m['anio']['sudamerica'] = 2027                                          # Sudamérica cambió de temporada
    assert CP._vigente(e, champions, 'champions') and not CP._vigente(e, CP.copa(e, 'libertadores'), 'libertadores')
    CP._asegurar(e, random.Random(2))
    assert CP.copa(e, 'champions') is champions and CP.copa(e, 'libertadores')['anio'] == 2027
    CP.simular_todo(e, random.Random(3), tipos=('libertadores',))
    assert CP.campeon(e, 'libertadores') and not CP.campeon(e, 'champions')
    CP.iniciar_temporada(e, random.Random(4), forzar=True, tipos=('libertadores',))
    assert CP.copa(e, 'champions') is champions and not CP.campeon(e, 'libertadores')


def test_sin_marca_las_copas_como_hoy():
    e = _e()
    CP.iniciar_temporada(e, random.Random(1), forzar=True)
    a, b = CP.copa(e, 'champions'), CP.copa(e, 'libertadores')
    assert 'anio' not in a and CP._jornada_copa(e, 'libertadores') == CP._jornada_actual(e) == 1
    CP._asegurar(e)
    assert CP.copa(e, 'champions') is a and CP.copa(e, 'libertadores') is b
    e['temporada'] = 2
    CP._asegurar(e, random.Random(2))
    assert CP.copa(e, 'champions') is not a and CP.copa(e, 'libertadores') is not b
    assert CP.copa(e, 'champions')['temporada'] == 2


# --- Task 4: los pasos por liga del cierre ────────────────────────────────────

def _terminar_ligas(e, paises=None):
    """Juega de fondo todo lo que falta (tu liga incluida si su país está en `paises` o no hay filtro)."""
    from alpha_football.ui import league_screen as L
    L.completar_ligas_de_fondo(e, paises=paises)
    liga = e['liga']
    if paises is None or liga.tipo in paises:
        while L._simular_jornada_liga_fondo(liga):
            pass
        liga.jornada_actual = liga.num_jornadas


def _en_cero(liga) -> bool:
    return (liga.jornada_actual == 1 and not any(p.jugado for p in (liga.calendario or []))
            and all(eq.puntos == 0 and eq.pj == 0 and eq.gf == 0 for eq in liga.equipos))


def _edades(e) -> dict:
    return {id(j): j.edad for l in _ligas_de(e, EUROPA + SUDAMERICA) for eq in l.equipos for j in eq.jugadores}


def _envejecieron(e, antes: dict) -> float:
    """Parte de los jugadores que siguen en la partida y tienen exactamente un año más."""
    siguen = [j for l in _ligas_de(e, EUROPA + SUDAMERICA) for eq in l.equipos for j in eq.jugadores if id(j) in antes]
    return sum(1 for j in siguen if j.edad == antes[id(j)] + 1) / max(1, len(siguen))


def test_el_cierre_de_un_save_sin_marca_cierra_las_16_ligas():
    from alpha_football.ui import resumen_temporada_screen as R
    e = _e(); _terminar_ligas(e)
    antes = _edades(e)
    R.avanzar_nueva_temporada(e)
    assert e['temporada'] == 2 and e['liga'].tipo == 'premier'
    movs = e['promo_releg_data']['todos_paises']
    assert len(movs) == 8 and all(len(m['ascendidos']) == 2 and len(m['descendidos']) == 2 for m in movs)
    assert all(len(l.equipos) == 12 for l in _ligas_de(e, EUROPA + SUDAMERICA))
    assert all(_en_cero(l) for l in _ligas_de(e, EUROPA))                  # tu continente arranca de cero
    assert _envejecieron(e, antes) > 0.95                                  # un año más para todos
    # F6: recién ahí el save viejo se desfasa: el otro continente queda a mitad de su temporada
    assert TS.activo(e) and e['datos_carrera']['mundo']['anio'] == {'europa': 2027, 'sudamerica': 2027}
    for l in _ligas_de(e, SUDAMERICA):
        assert _jugados(l) == TS.jornadas_por_fecha(e, l, date(2027, 7, 1)) >= 6 and len(l.equipos) == 12
    assert CP.copa(e, 'champions')['anio'] == 2027 and _fechas_jugadas(e, 'champions') == 0
    assert CP.copa(e, 'libertadores')['anio'] == 2027 and _fechas_jugadas(e, 'libertadores') >= 3


# --- Task 5: el otro continente por fecha y el arranque desfasado ─────────────

def _desfasada(tipo='premier', idx=0):
    """Carrera recién creada, con las copas sorteadas y los continentes ya desfasados (lo que hace el alta)."""
    e = _e(tipo, idx)
    CP.iniciar_temporada(e, random.Random(1), forzar=True)
    assert TS.arrancar_desfase(e)
    return e


def _por_fecha(e, liga, d) -> int:
    return TS.jornadas_por_fecha(e, liga, d)


def test_arranque_desfasado_europa():
    e = _desfasada()
    assert TS.activo(e) and e['datos_carrera']['mundo']['anio'] == {'europa': 2026, 'sudamerica': 2026}
    assert CAL.anio(e) == 2026 and T.inicio(e) == date(2026, 7, 1)
    for l in _ligas_de(e, SUDAMERICA):                                     # a mitad de su temporada 2026
        tocan = _por_fecha(e, l, date(2026, 7, 1))
        assert _jugados(l) == tocan and 6 <= tocan <= 11, (l.nombre, _jugados(l), tocan)
        assert all(eq.pj == tocan for eq in l.equipos) and sum(j.goles for eq in l.equipos for j in eq.jugadores) > 0
    assert all(_jugados(l) == 0 for l in _ligas_de(e, EUROPA))             # tu continente, sin empezar
    assert CP.copa(e, 'champions')['anio'] == 2026 and CP.copa(e, 'libertadores')['anio'] == 2026
    assert _fechas_jugadas(e, 'libertadores') >= 3 and _fechas_jugadas(e, 'champions') == 0
    foto = [_jugados(l) for l in _ligas_de(e, SUDAMERICA)]
    assert not TS.arrancar_desfase(e) and [_jugados(l) for l in _ligas_de(e, SUDAMERICA)] == foto   # una sola vez


def test_arranque_desfasado_sudamerica():
    e = _desfasada('betplay', 0)
    assert e['datos_carrera']['mundo']['anio'] == {'sudamerica': 2027, 'europa': 2026}
    assert CAL.anio(e) == 2027 and T.inicio(e) == date(2027, 1, 1)
    for l in _ligas_de(e, EUROPA):                                         # Europa va por la mitad de la 2026/27
        tocan = _por_fecha(e, l, date(2027, 1, 1))
        assert _jugados(l) == tocan and 8 <= tocan <= 11, (l.nombre, _jugados(l), tocan)
    assert all(_jugados(l) == 0 for l in _ligas_de(e, SUDAMERICA))
    assert _fechas_jugadas(e, 'champions') >= 3 and _fechas_jugadas(e, 'libertadores') == 0


def test_el_otro_continente_avanza_con_los_dias_y_el_tuyo_con_tu_jornada():
    from alpha_football.ui.match_screen import finalizar_jornada_liga
    e = _desfasada(); liga, mi = e['liga'], e['mi_equipo']
    antes = {id(l): _jugados(l) for l in _ligas_de(e, SUDAMERICA)}
    D.hoy(e); D.hasta_el_partido(e)                                        # del 1 de julio a tu J1 (agosto)
    hoy = D.hoy(e)
    for l in _ligas_de(e, SUDAMERICA):
        assert _jugados(l) == _por_fecha(e, l, hoy) > antes[id(l)], (l.nombre, _jugados(l), antes[id(l)])
    assert all(_jugados(l) == 0 for l in _ligas_de(e, EUROPA))             # tu continente espera tu jornada
    p = next(x for x in liga.calendario if x.jornada == 1 and mi.id in (x.local_id, x.visitante_id))
    finalizar_jornada_liga(e, liga, mi, p, 1, 0)
    assert all(_jugados(l) == 1 for l in _ligas_de(e, EUROPA))             # exactamente una, como tú
    for l in _ligas_de(e, SUDAMERICA):
        assert _jugados(l) == _por_fecha(e, l, D.hoy(e))                   # y el otro, ni una de más


def test_sin_marca_revisar_no_hace_nada():
    e = _e()
    TS.revisar_jornada(e)
    assert TS.poner_al_dia(e, date(2027, 6, 30)) == 0 and all(_jugados(l) == 0 for l in _ligas_de(e, EUROPA + SUDAMERICA))
    assert 'mundo' not in e['datos_carrera']


# --- Task 6: el cierre del otro continente ────────────────────────────────────

def _foto_liga(l) -> tuple:
    return (l.jornada_actual, _jugados(l), tuple(sorted((eq.nombre, eq.puntos, eq.pj) for eq in l.equipos)))


def test_cierre_del_otro_continente_a_mitad_de_tu_temporada():
    e = _desfasada('premier', 11); D.hoy(e)                                # un club sin copa: el reloj no espera partidos de copa
    cal = CAL.asegurar(e)
    for jor in range(1, 11):
        _jugar(e, jor)                                                     # tu próximo partido es la J11 (enero)
    e['liga'].jornada_actual = 11
    cal['dia'] = '2026-12-30'
    D.avanzar_dia(e)                                                       # 31 de diciembre: todavía no cierra
    assert D.hoy(e) == date(2026, 12, 31) and e['datos_carrera']['mundo']['anio']['sudamerica'] == 2026
    assert all(_jugados(l) == l.num_jornadas for l in _ligas_de(e, SUDAMERICA))
    campeon_betplay = max(e['primera_division']['betplay'].equipos, key=lambda x: (x.puntos, x.gf - x.gc, x.gf)).nombre
    clubes_1a = {t: {eq.nombre for eq in e['primera_division'][t].equipos} for t in SUDAMERICA}
    europa = [_foto_liga(l) for l in _ligas_de(e, EUROPA)]
    champions = CP.copa(e, 'champions')
    edades = _edades(e)
    n_correos = len(C.bandeja(e))
    D.avanzar_dia(e)                                                       # 1 de enero: Sudamérica cerró su 2026
    m = e['datos_carrera']['mundo']
    assert m['anio'] == {'europa': 2026, 'sudamerica': 2027} and m['campeones']['libertadores']
    for t in SUDAMERICA:
        l1, l2 = e['primera_division'][t], e['segunda_division'][t]
        assert _en_cero(l1) and _en_cero(l2) and len(l1.equipos) == 12 == len(l2.equipos)
        ahora = {eq.nombre for eq in l1.equipos}
        assert len(ahora - clubes_1a[t]) == 2 and len(clubes_1a[t] - ahora) == 2      # 2 suben y 2 bajan
    assert [_foto_liga(l) for l in _ligas_de(e, EUROPA)] == europa         # tu continente, intacto
    assert CP.copa(e, 'champions') is champions
    lib = CP.copa(e, 'libertadores')
    assert lib['anio'] == 2027 and not lib.get('campeon') and _fechas_jugadas(e, 'libertadores') == 0
    assert _edades(e) == edades or _envejecieron(e, edades) == 0           # nadie cumple años en el cierre ajeno
    assert e['temporada'] == 1 and e['liga'].jornada_actual == 11
    nuevos = C.bandeja(e)[:len(C.bandeja(e)) - n_correos]
    from alpha_football import noticias as NO                              # v0.4.23.0: noticias, ya no correo de Prensa
    assert not [x for x in nuevos if x['remitente'] == 'prensa']
    aviso = next(x for x in NO.lista(e) if x['titular'] == "Terminó la temporada en Sudamérica")
    assert (aviso['tipo'], aviso['importancia']) == ('campeon', 4)
    # v0.4.25.0: solo los campeones de liga (sin copa, ascensos ni descensos) y con el año real de la temporada
    assert campeon_betplay in aviso['cuerpo'] and "2026" in aviso['cuerpo']
    assert not any(x in aviso['cuerpo'] for x in ("Suben", "bajan", "Libertadores:"))
    copa = next(x for x in NO.lista(e) if x['tipo'] == 'campeon' and x['importancia'] == 5)
    assert m['campeones']['libertadores'] in copa['titular'] and "Libertadores" in copa['titular'] + copa['cuerpo']
    assert e['datos_carrera']['copa_ranking']['betplay'][0] == campeon_betplay
    pend = [x for x in e['datos_carrera'].get('premios_pendientes', []) if x['premio'] == 'sudamericano']
    assert len(pend) == 1 and pend[0]['fecha_entrega'] == '2027-01-15'     # el Sudamericano del Año de la 2026
    assert len(m['balon']['sudamerica']) == 3                              # podio congelado para tu Balón de Oro
    foto = [_foto_liga(l) for l in _ligas_de(e, SUDAMERICA)]
    D.avanzar_dia(e)                                                       # 2 de enero: no se cierra otra vez
    assert m['anio']['sudamerica'] == 2027 and [_foto_liga(l) for l in _ligas_de(e, SUDAMERICA)] == foto


def test_un_paso_roto_no_bloquea_el_cierre_del_otro_continente():
    from alpha_football import entrenadores as EN
    e = _desfasada()
    TS.poner_al_dia(e, date(2026, 12, 31))
    original = EN.cierre_temporada

    def _rota(*a, **k):
        raise RuntimeError("liga dañada")
    EN.cierre_temporada = _rota
    try:
        res = TS.cerrar_continente(e, 'sudamerica')
    finally:
        EN.cierre_temporada = original
    assert e['datos_carrera']['mundo']['anio']['sudamerica'] == 2027       # el año sube igual: no se repite cada día
    assert all(_en_cero(l) for l in _ligas_de(e, SUDAMERICA)) and len(res['movimientos']) == 5
    assert TS.cerrar_continente(e, 'europa') == {'campeones': {}, 'copa': None, 'movimientos': []}   # nunca el tuyo


# --- Task 7: tu cierre de temporada ───────────────────────────────────────────

def _un_anio_europeo(e):
    """Lleva una carrera europea desfasada hasta su cierre: Sudamérica cierra el 31 de diciembre y sigue
    por fecha hasta el 30 de junio; tu continente termina sus ligas y cierras tu temporada."""
    from alpha_football.ui import resumen_temporada_screen as R
    a = TS.anio(e, 'europa')
    TS.poner_al_dia(e, date(a, 12, 31))
    TS.cerrar_continente(e, 'sudamerica')
    TS.poner_al_dia(e, date(a + 1, 6, 30))
    _terminar_ligas(e, EUROPA)
    R.avanzar_nueva_temporada(e)


def test_tu_cierre_solo_cierra_tu_continente():
    from alpha_football.ui import resumen_temporada_screen as R
    e = _desfasada('premier', 11)
    TS.poner_al_dia(e, date(2026, 12, 31)); TS.cerrar_continente(e, 'sudamerica'); TS.poner_al_dia(e, date(2027, 6, 30))
    _terminar_ligas(e, EUROPA)
    campeon_lib = e['datos_carrera']['mundo']['campeones']['libertadores']
    sudamerica = [_foto_liga(l) for l in _ligas_de(e, SUDAMERICA)]
    clubes_sud = {t: {eq.nombre for eq in e['primera_division'][t].equipos} for t in SUDAMERICA}
    libertadores, champions = CP.copa(e, 'libertadores'), CP.copa(e, 'champions')
    edades = _edades(e)
    R.avanzar_nueva_temporada(e)
    m = e['datos_carrera']['mundo']
    assert e['temporada'] == 2 and m['anio'] == {'europa': 2027, 'sudamerica': 2027}
    assert CAL.anio(e) == 2027 and T.inicio(e) == date(2027, 7, 1)
    assert all(_en_cero(l) for l in _ligas_de(e, EUROPA))                  # tu continente arranca de cero
    assert [_foto_liga(l) for l in _ligas_de(e, SUDAMERICA)] == sudamerica  # el otro sigue su temporada
    assert {t: {eq.nombre for eq in e['primera_division'][t].equipos} for t in SUDAMERICA} == clubes_sud
    movs = e['promo_releg_data']['todos_paises']
    assert sorted(x['tipo'] for x in movs) == sorted(EUROPA)               # ascensos y descensos solo en tu continente
    assert _envejecieron(e, edades) > 0.95                                 # un año más para TODOS (también Sudamérica)
    assert CP.copa(e, 'libertadores') is libertadores                      # su copa sigue en juego
    nueva = CP.copa(e, 'champions')
    assert nueva is not champions and nueva['anio'] == 2027 and _fechas_jugadas(e, 'champions') == 0
    reg = e['datos_carrera']['campeones_copas'][-1]
    assert reg['temporada'] == 1 and reg['champions'] and reg['libertadores'] == campeon_lib
    balon = next(x for x in e['datos_carrera']['premios_pendientes'] if x['premio'] == 'balon_oro')
    assert balon['fecha_entrega'].startswith('2027-10') and len(balon['datos']['podio']) == 3
    puntajes = [f['puntaje'] for f in balon['datos']['podio']]
    assert puntajes == sorted(puntajes, reverse=True) and balon['datos']['ganador'] == balon['datos']['podio'][0]
    assert m['balon']['sudamerica'] == []                                  # el podio congelado ya se usó


def test_el_balon_de_oro_funde_tu_continente_con_el_podio_congelado_del_otro():
    from alpha_football import premios as PR
    e = _desfasada('premier', 11)
    crack = {'nombre': 'Crack Sudamericano', 'equipo': 'Club', 'puntaje': 9999.0}
    flojo = {'nombre': 'Suplente', 'equipo': 'Club', 'puntaje': 0.01}
    e['datos_carrera']['mundo']['balon'] = {'sudamerica': [crack, flojo]}
    europeos = [{'nombre': f"Europeo {k}", 'equipo': 'X', 'puntaje': 100.0 - k} for k in range(3)]
    PR._pendientes(e).append({'premio': 'balon_oro', 'fecha_entrega': '2027-10-25',
                              'datos': {'temporada': 1, 'ganador': europeos[0], 'podio': list(europeos)}})
    TS.fundir_balon(e)
    datos = PR._pendientes(e)[0]['datos']
    assert [f['nombre'] for f in datos['podio']] == ['Crack Sudamericano', 'Europeo 0', 'Europeo 1']
    assert datos['ganador'] == crack and e['datos_carrera']['mundo']['balon']['sudamerica'] == []
    TS.fundir_balon(e)                                                     # sin nada congelado no cambia
    assert [f['nombre'] for f in PR._pendientes(e)[0]['datos']['podio']] == ['Crack Sudamericano', 'Europeo 0', 'Europeo 1']


def test_dos_temporadas_seguidas_sin_perder_el_desfase():
    e = _desfasada('premier', 11)
    _un_anio_europeo(e)
    _un_anio_europeo(e)
    assert e['temporada'] == 3 and e['datos_carrera']['mundo']['anio'] == {'europa': 2028, 'sudamerica': 2028}
    assert all(_en_cero(l) for l in _ligas_de(e, EUROPA))
    for l in _ligas_de(e, SUDAMERICA):                                     # otra vez a mitad de su temporada
        tocan = TS.jornadas_por_fecha(e, l, date(2028, 6, 30))
        assert _jugados(l) == tocan and 6 <= tocan <= 11 and len(l.equipos) == 12
    assert [x['temporada'] for x in e['datos_carrera']['campeones_copas']] == [1, 2]
    assert all(x['champions'] and x['libertadores'] for x in e['datos_carrera']['campeones_copas'])
    assert CP.copa(e, 'champions')['anio'] == 2028 and CP.copa(e, 'libertadores')['anio'] == 2028


# --- Task 8: cambiar de continente ────────────────────────────────────────────

def test_cambiar_de_continente_sigue_en_la_jornada_de_esa_liga():
    from alpha_football.directiva import cambiar_de_club
    e = _desfasada('premier', 11); D.hoy(e)
    for jor in range(1, 15):
        _jugar(e, jor)
    e['liga'].jornada_actual = 15
    CAL.asegurar(e)['dia'] = '2027-03-10'                                  # marzo de 2027, a mitad de tu 2026/27
    TS.revisar_jornada(e)                                                  # Sudamérica cerró su 2026 y va por la 2027
    betplay = e['primera_division']['betplay']
    jugadas = _jugados(betplay)
    assert e['datos_carrera']['mundo']['anio']['sudamerica'] == 2027 and jugadas == TS.jornadas_por_fecha(e, betplay, date(2027, 3, 10)) >= 3
    libres = [eq for eq in betplay.equipos
              if not any(c.get('nombre') == eq.nombre for c in CP.copa(e, 'libertadores')['clubes'])]
    nuevo = libres[0]                                                      # un club sin copa: su próximo partido es de liga
    tabla = sorted((eq.nombre, eq.puntos) for eq in betplay.equipos)
    cambiar_de_club(e, nuevo)
    assert e['mi_equipo'] is nuevo and e['liga'] is betplay and e['temporada'] == 1
    assert CAL.continente(e) == 'sudamerica' and CAL.anio(e) == 2027 and T.fin(e) == date(2027, 12, 31)
    assert _jugados(betplay) == jugadas and sorted((eq.nombre, eq.puntos) for eq in betplay.equipos) == tabla
    assert D.hoy(e) == date(2027, 3, 10)                                   # el reloj conserva el día
    prox = CAL.proximo_evento(e)
    assert prox['tipo'] == 'liga' and prox['num'] == jugadas + 1 and prox['fecha'] >= date(2027, 3, 10)
    for l in _ligas_de(e, EUROPA):                                         # el continente que dejas queda al día por fecha
        assert _jugados(l) == TS.jornadas_por_fecha(e, l, date(2027, 3, 10)) >= 12
    CAL.asegurar(e)['dia'] = '2027-07-01'
    TS.revisar_jornada(e)                                                  # Europa cierra el 30 de junio como "otro continente"
    m = e['datos_carrera']['mundo']
    assert m['anio'] == {'europa': 2027, 'sudamerica': 2027} and m['campeones']['champions']
    assert all(_en_cero(l) for l in _ligas_de(e, EUROPA)) and _jugados(betplay) == jugadas   # tu liga nueva, intacta


def test_cambiar_de_club_en_tu_mismo_continente_o_sin_desfase_no_cambia_nada_mas():
    from alpha_football.directiva import cambiar_de_club
    e = _e('premier', 11)                                                  # sin desfase
    cambiar_de_club(e, e['primera_division']['betplay'].equipos[0])
    assert not TS.activo(e) and all(_jugados(l) == 0 for l in _ligas_de(e, EUROPA + SUDAMERICA))
    f = _desfasada('premier', 11)
    sud = [_foto_liga(l) for l in _ligas_de(f, SUDAMERICA)]
    cambiar_de_club(f, f['primera_division']['laliga'].equipos[0])         # mismo continente
    assert CAL.continente(f) == 'europa' and [_foto_liga(l) for l in _ligas_de(f, SUDAMERICA)] == sud
    assert all(_jugados(l) == 0 for l in _ligas_de(f, EUROPA))


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
