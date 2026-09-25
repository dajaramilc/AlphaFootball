"""v2.3.6: dirección en vivo, copa con clasificados reales, nerf de progreso, techo
Sudamérica 81, suerte/goleadas, descensos en todas las ligas, eventos por posición y
Balón de Oro."""
import sys, os, random, tempfile, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(11)

from alpha_football import save as _save_mod
_TMP_SAVES = tempfile.mkdtemp(prefix="af_test_saves_")
_orig = _save_mod.guardar_en_slot
_save_mod.guardar_en_slot = lambda estado, n, nombre, carpeta=None: _orig(estado, n, nombre, _TMP_SAVES)

from alpha_football import engine
from alpha_football.models import EstadoJuego, alineacion_por_defecto
from alpha_football.desarrollo import desarrollar_plantilla_post_partido, progresar_pasivo
from alpha_football.ui.menu import load_league_teams, _ligas_por_division
from alpha_football.ui.league_screen import simular_jornada_segunda_division, _simular_jornada_liga_fondo
from alpha_football.ui.resumen_temporada_screen import avanzar_nueva_temporada
from alpha_football.ui import copa_screen as C
from alpha_football.ui.team_screen import _cambio_en_partido
from alpha_football.ui.match_screen import _snapshot_alineacion, _restaurar_alineacion


def nuevo_estado(tipo='laliga', idx=0):
    liga = load_league_teams(tipo)
    primeras, segunda = _ligas_por_division(liga, {}, {})
    eq = liga.equipos[idx]
    eq.alineacion_activa = alineacion_por_defecto(eq)
    return {
        'liga': liga, 'mi_equipo': eq, 'equipos': liga.equipos,
        'temporada': 1, 'historial': [], 'transfer_log': [], 'liga_usuario_division': 1,
        'primera_division': primeras, 'segunda_division': segunda, 'datos_carrera': {},
        'copa_clasificado': True, 'alineacion_activa': eq.alineacion_activa,
    }


def jugar_temporada(estado):
    liga = estado['liga']
    while _simular_jornada_liga_fondo(liga):
        simular_jornada_segunda_division(estado)


def test_eventos_por_posicion():
    """Las frases de portero solo salen cuando defiende el POR."""
    liga = load_league_teams('premier')
    a, b = liga.equipos[0], liga.equipos[1]
    por_id = {j.id: j.posicion for e in (a, b) for j in e.jugadores}
    marcas_por = ("portero", "Paradon", "ataja", "vuela")
    vistos = 0
    for _ in range(40):
        for ev in engine.simular_partido(a, b).eventos:
            if ev['tipo'] != 'defensa':
                continue
            texto = ev['detalle'].split('. ', 1)[-1]
            if any(m in texto for m in marcas_por):
                vistos += 1
                assert por_id.get(ev['defensor_id']) == 'POR', texto
    assert vistos > 0


def test_suerte_y_goleadas():
    """Favorito claro gana casi siempre pero no siempre; goleadas de 7+ raras."""
    europa = load_league_teams('premier').equipos
    col = load_league_teams('betplay').equipos
    grande = max(europa, key=engine._media_once)
    chico = min(col, key=engine._media_once)
    # v3.7.0: con ligas de 12 el 'chico' cambió y su estilo contrarresta al del grande (±15%);
    # el test mide la brecha de calidad, así que ambos juegan con el mismo estilo.
    grande.estilo_dt = chico.estilo_dt = 'anchelottismo'
    n, gana, dif7 = 600, 0, 0
    for _ in range(n):
        r = engine.simular_partido(chico, grande)
        gana += r.goles_visitante > r.goles_local
        dif7 += abs(r.goles_local - r.goles_visitante) >= 7
    assert 0.70 < gana / n < 0.99, gana / n
    assert dif7 / n < 0.02, dif7 / n
    # Dentro de una liga el pequeño saca resultados con frecuencia
    liga = sorted(load_league_teams('laliga').equipos, key=engine._media_once)
    n = 300
    no_pierde = sum(r.goles_local >= r.goles_visitante
                    for r in (engine.simular_partido(liga[0], liga[-1]) for _ in range(n)))
    assert no_pierde / n > 0.10, no_pierde / n


def test_nerf_veteranos():
    """Un 32 años con partidos normales no sube; con temporada normal tiende a bajar."""
    liga = load_league_teams('laliga')
    eq = liga.equipos[0]
    for j in eq.jugadores:
        j.edad = 32
    antes = [j.overall for j in eq.jugadores[:11]]
    rng = random.Random(3)
    for _ in range(14):
        desarrollar_plantilla_post_partido(eq, 1, 1, list(range(11)), rng)
    despues = [j.overall for j in eq.jugadores[:11]]
    assert sum(despues) - sum(antes) <= 2, (antes, despues)
    for j in eq.jugadores[:11]:
        j.promedio_nota = 6.6
    antes = sum(j.overall for j in eq.jugadores[:11])
    progresar_pasivo(eq, 1, random.Random(5))
    assert sum(j.overall for j in eq.jugadores[:11]) < antes


def test_techo_sudamerica():
    for tipo in ('betplay', 'brasil', 'argentina'):
        liga = load_league_teams(tipo)
        mx = max(j.overall for e in liga.equipos for j in e.jugadores)
        assert mx <= 81, (tipo, mx)
    euro = load_league_teams('premier')
    assert max(j.overall for e in euro.equipos for j in e.jugadores) > 81


def test_copa_clasificados_reales_sin_parodias():
    # v3.8.0: Champions de 36 del motor (cupos 5 por liga europea + relleno del banco).
    from alpha_football import competiciones as CP
    estado = nuevo_estado('laliga', 0)
    C.sincronizar_copa_user(estado)
    equipos = [c['nombre'] for c in CP.copa(estado, 'champions')['clubes']]
    assert len(equipos) == 36 and len(set(equipos)) == 36
    idents = [C.identidad_club(n) for n in equipos if C.identidad_club(n)]
    assert len(idents) == len(set(idents)), f"parodias duplicadas: {idents}"
    assert 'Real Madriz' not in equipos or 'Real Vadrid' not in equipos
    nombres_liga = {e.nombre for e in estado['primera_division']['laliga'].equipos}
    nombres_prem = {e.nombre for e in estado['primera_division']['premier'].equipos}
    assert len([n for n in equipos if n in nombres_liga]) == 5
    assert len([n for n in equipos if n in nombres_prem]) == 5

    # Libertadores: el Boca/Palmeiras de la liga reemplaza al del banco
    estado = nuevo_estado('argentina', 0)
    C.sincronizar_copa_user(estado)
    equipos = [c['nombre'] for c in CP.copa(estado, 'libertadores')['clubes']]
    idents = [C.identidad_club(n) for n in equipos if C.identidad_club(n)]
    assert len(idents) == len(set(idents)), f"parodias duplicadas: {idents}"
    assert 'Boca Amargo' not in equipos and 'Palmeirras' not in equipos


def test_temporada_completa_descensos_y_balon():
    estado = nuevo_estado('laliga', 0)
    jugar_temporada(estado)
    fondo = [e for t, l in estado['primera_division'].items() if t != 'laliga' for e in l.equipos]
    assert any(j.partidos_jugados > 0 for e in fondo for j in e.jugadores), "ligas de fondo sin desarrollo"
    # La BetPlay tiene 14 jornadas y La Liga 10: avanzar_nueva_temporada completa las que faltan
    # antes de los descensos, así que la foto de "los últimos" se toma con las ligas terminadas.
    from alpha_football.ui.league_screen import completar_ligas_de_fondo
    completar_ligas_de_fondo(estado)
    ultimos = {}
    for t, l in estado['primera_division'].items():
        ordenados = sorted(l.equipos, key=lambda e: (e.puntos, e.gf - e.gc, e.gf))
        ultimos[t] = {e.nombre for e in ordenados[:2]}
    avanzar_nueva_temporada(estado)
    for t, nombres in ultimos.items():
        en_2a = {e.nombre for e in estado['segunda_division'][t].equipos}
        assert nombres <= en_2a, f"{t}: los últimos no descendieron"
    movs = estado['promo_releg_data']['todos_paises']
    from alpha_football.paises import TIPOS_LIGA as _T   # v3.7.0: 8 países
    assert len(movs) == len(_T)
    balon = (estado['datos_carrera'].get('balon_oro') or [None])[-1]
    assert balon and balon['ganador']['nombre'], balon
    ranking = estado['datos_carrera']['copa_ranking']
    from alpha_football.paises import TIPOS_LIGA   # v3.7.0: los 8 países
    assert set(ranking) == set(TIPOS_LIGA)
    # Persistencia de datos_carrera
    datos = {"ligas": [estado['liga'].to_dict()], "equipo_usuario_id": estado['mi_equipo'].id,
             "liga_usuario_id": estado['liga'].tipo, "temporada": estado['temporada'],
             **_save_mod.campos_divisiones(estado)}
    cargado = EstadoJuego.from_dict(EstadoJuego.from_dict(datos).to_dict())
    assert cargado.datos_carrera['balon_oro'][-1]['ganador']['nombre'] == balon['ganador']['nombre']
    assert cargado.datos_carrera['copa_ranking'] == ranking


def test_cambios_en_vivo():
    liga = load_league_teams('premier')
    eq = liga.equipos[0]
    alin = alineacion_por_defecto(eq)
    from alpha_football import formaciones as F
    F.normalizar_convocados(alin, eq.jugadores)
    foto = _snapshot_alineacion(eq, alin)
    estado = {'sim_subs_realizadas': 0, 'sim_salieron': []}
    for k in range(5):
        salieron = set(estado['sim_salieron'])
        _cambio_en_partido(estado, alin, eq.jugadores, ('campo', k + 1), ('banco', k),
                           estado['sim_subs_realizadas'], salieron)
    assert estado['sim_subs_realizadas'] == 5
    # 6º cambio: bloqueado
    titulares = list(alin.titulares)
    _cambio_en_partido(estado, alin, eq.jugadores, ('campo', 7), ('banco', 6), 5, set(estado['sim_salieron']))
    assert alin.titulares == titulares and estado['sim_subs_realizadas'] == 5
    # El que salió no puede volver
    estado['sim_subs_realizadas'] = 0
    _cambio_en_partido(estado, alin, eq.jugadores, ('campo', 1), ('banco', 0), 0, set(estado['sim_salieron']))
    assert alin.titulares == titulares
    # Cambio de puesto (campo↔campo) es gratis
    _cambio_en_partido(estado, alin, eq.jugadores, ('campo', 2), ('campo', 3), 0, set())
    assert estado['sim_subs_realizadas'] == 0
    # Al terminar el partido se restaura la alineación previa
    eq.estilo_dt = 'haramball'
    _restaurar_alineacion(eq, alin, foto)
    assert alin.titulares == foto['titulares'] and eq.estilo_dt == foto['estilo']


def test_reserva_por_jugador_del_banco():
    """En Dirección de equipo: seleccionar un suplente del banco, pasar a RESERVAS y
    elegir una reserva los intercambia (antes al cambiar de vista se soltaba la selección)."""
    from alpha_football.ui import team_screen
    screen = pygame.display.set_mode((1280, 720))

    def click(pos):
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))

    estado = nuevo_estado('premier', 0)
    estado['team_contexto'] = 'carrera'
    alin = estado['alineacion_activa']
    team_screen.render(screen, estado)
    banco0 = alin.convocados[0]
    click((16 + 10, team_screen._BANCO_Y + 40))           # selecciona el 1er suplente
    team_screen.render(screen, estado)
    click((1050 + 100, team_screen._BANCO_Y - 5))         # VER RESERVAS
    team_screen.render(screen, estado)
    assert estado.get('team_sel') == ('banco', 0), "la selección debe sobrevivir al cambio de vista"
    click((16 + 10, team_screen._BANCO_Y + 40))           # 1ª reserva
    team_screen.render(screen, estado)
    assert alin.convocados[0] != banco0, "la reserva debe entrar al banco"
    assert banco0 not in alin.convocados and banco0 not in alin.titulares


def test_v237_presupuestos_y_regiones():
    from alpha_football.mercado_ia import asignar_presupuestos_realistas
    from alpha_football.market import registrar_regiones, es_jugador_latam, calcular_valor
    estado = nuevo_estado('laliga', 0)
    registrar_regiones(estado)
    asignar_presupuestos_realistas(estado, incluir_usuario=True, rng=random.Random(1))
    p, s = estado['primera_division'], estado['segunda_division']
    top = lambda l: max(e.balance for e in l.equipos)
    assert top(p['premier']) > top(p['brasil']) > top(p['betplay']) > top(s['betplay'])
    assert top(s['premier']) < min(e.balance for e in p['premier'].equipos)
    # Un jugador de una liga sudamericana de FONDO se valora como sudamericano
    j = p['brasil'].equipos[0].jugadores[0]
    assert es_jugador_latam(j)
    assert not es_jugador_latam(p['premier'].equipos[0].jugadores[0])


def test_v237_ascenso_y_descenso():
    from alpha_football.mercado_ia import aplicar_ascenso, aplicar_descenso
    eq = load_league_teams('premier').equipos[0]
    antes = [j.overall for j in eq.jugadores]
    bal = eq.balance
    premio = aplicar_ascenso(eq, 'premier')
    assert premio > 0 and eq.balance == bal + premio
    difs = [j.overall - a for j, a in zip(eq.jugadores, antes)]
    # v4.4.0: sin plan de temporada todos son "no elegibles": +4 con techo 83 (≥83 no sube)
    assert all(d == (0 if a >= 83 else min(4, 83 - a)) for d, a in zip(difs, antes)), difs
    antes = [j.overall for j in eq.jugadores]
    aplicar_descenso(eq)
    difs = [a - j.overall for j, a in zip(eq.jugadores, antes)]
    assert all(d == 3 for d in difs), difs                      # v4.4.0: no elegibles −3


def test_v237_mercado_ia():
    from alpha_football.mercado_ia import asignar_presupuestos_realistas, ronda_fichajes_ia, ligas_de_la_partida
    estado = nuevo_estado('laliga', 0)
    asignar_presupuestos_realistas(estado, incluir_usuario=True, rng=random.Random(2))
    equipos = [e for l, _t, _d in ligas_de_la_partida(estado) for e in l.equipos]
    dinero = sum(e.balance for e in equipos)
    user = estado['mi_equipo']
    plantilla_user = list(user.jugadores)
    log = ronda_fichajes_ia(estado, 'pretemporada', random.Random(3))
    assert len(log) >= 10, log
    assert user.jugadores == plantilla_user, "la IA no toca al equipo del usuario"
    assert sum(e.balance for e in equipos) == dinero, "el dinero solo cambia de manos"
    todos = [id(j) for e in equipos for j in e.jugadores]
    assert len(todos) == len(set(todos)), "jugador en dos clubes"
    for e in equipos:
        if e is not user:
            assert len(e.jugadores) <= 30 and all(e.balance >= 0 for e in equipos)


def test_v238_retiros_y_regens():
    from alpha_football.retiros import prob_retiro, procesar_retiros, NOMBRES_POR_PAIS
    assert prob_retiro(34) == 0 and prob_retiro(35) > 0 and prob_retiro(41) > prob_retiro(36)
    assert prob_retiro(37, 7.8) < prob_retiro(37, 6.5)
    estado = nuevo_estado('betplay', 0)
    user = estado['mi_equipo']
    alin = user.alineacion_activa
    viejos = {}
    for eq in (user, estado['primera_division']['premier'].equipos[0]):
        for i, j in enumerate(eq.jugadores):
            j.edad = 40
            viejos[(id(eq), i)] = (j.posicion, max(j.potencial, j.overall))
    n_antes = len(user.jugadores)
    retiros = procesar_retiros(estado, random.Random(9))
    assert len(retiros) >= 30, len(retiros)
    assert len(user.jugadores) == n_antes, "el regen ocupa el lugar del retirado"
    for eq, pais in ((user, 'Colombia'), (estado['primera_division']['premier'].equipos[0], 'Inglaterra')):
        for i, j in enumerate(eq.jugadores):
            if j.edad <= 18:
                pos, pot = viejos[(id(eq), i)]
                assert j.posicion == pos and j.potencial == min(99, pot) and j.nacionalidad == pais
                assert j.nombre in NOMBRES_POR_PAIS[pais][0] and j.overall < j.potencial
    assert all(0 <= i < len(user.jugadores) for i in alin.titulares + alin.convocados)
    assert any(r['es_user'] for r in retiros)


def test_v238_potencial_jovenes():
    from alpha_football.desarrollo import calcular_potencial
    assert calcular_potencial(70, 17, random.Random(1)) >= 89
    assert calcular_potencial(75, 20, random.Random(1)) >= 90
    assert calcular_potencial(80, 30, random.Random(1)) <= 84


if __name__ == '__main__':
    fallos = 0
    for nombre, fn in list(globals().items()):
        if nombre.startswith('test_') and callable(fn):
            try:
                fn()
                print(f"OK   {nombre}")
            except Exception as e:
                fallos += 1
                import traceback; traceback.print_exc()
                print(f"FAIL {nombre}: {e}")
    sys.exit(1 if fallos else 0)
