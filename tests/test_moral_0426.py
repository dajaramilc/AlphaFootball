"""v0.4.26.0: impulso de moral (ítem 15) y bonus de potencial al cerrar la temporada (ítem 9)."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(27)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import vestuario as V
from alpha_football.models import Jugador, Equipo, alineacion_por_defecto, asegurar_ids_unicos
from alpha_football.ui.menu import load_league_teams, _ligas_por_division


def jug(pos='MED', ovr=70, edad=25, **kw):
    return Jugador("Test", f"J{random.randint(0, 10**6)}", pos, ovr, ovr, ovr, ovr, ovr, edad=edad,
                   id=random.randint(10**6, 10**7), resistencia=60, **kw)


def _equipo(jugadores):
    return Equipo(nombre="Test FC", ciudad="C", estrellas=3.0, estilo_dt="cruyffismo",
                  balance=1_000_000, jugadores=jugadores)


def _estado(tipo='premier', idx=0):
    from alpha_football.ui.league_screen import inicializar_calendario_liga
    liga = load_league_teams(tipo)
    mi = liga.equipos[idx]
    mi.alineacion_activa = alineacion_por_defecto(mi)
    primeras, segunda = _ligas_por_division(liga, {}, {})
    inicializar_calendario_liga(liga)
    return {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
            'alineacion_activa': mi.alineacion_activa, 'primera_division': primeras,
            'segunda_division': segunda, 'datos_carrera': {}, 'historial': []}


# --- impulso_moral ------------------------------------------------------------------------------------

def test_impulso_moral_sube_a_toda_la_plantilla_con_tope_100_y_deja_la_causa():
    a, b, c = jug(moral=70), jug(moral=95), jug(moral=100)
    eq = _equipo([a, b, c])
    assert V.impulso_moral({}, eq, 10, 'titulo') == 2                     # c ya estaba en 100
    assert (a.moral, b.moral, c.moral) == (80, 100, 100)
    assert a.causas_moral[-1]['impulso'] == 10 and a.causas_moral[-1]['motivo_impulso'] == 'titulo'
    assert b.causas_moral[-1]['impulso'] == 5 and c.causas_moral[-1]['impulso'] == 0
    assert V.impulso_moral({}, eq, 25, 'titulo') == 1                     # solo a sube; 80 + 25 → 100
    assert a.moral == 100 and a.causas_moral[-1]['impulso'] == 30         # se acumula en la misma entrada


def test_impulso_moral_conserva_las_bajas_y_no_pasa_de_4_entradas():
    j = jug(moral=60)
    j.causas_moral = [{'minutos': -3, 'equipo': 0, 'sueldo': 0} for _ in range(4)]
    V.impulso_moral({}, _equipo([j]), 8, 'fase_copa')
    assert len(j.causas_moral) == 4 and j.causas_moral[-1]['minutos'] == -3 and j.causas_moral[-1]['impulso'] == 8
    from alpha_football.salidas import causa_principal
    assert causa_principal(j) == 'minutos'                                # el impulso no tapa la causa de la baja


def test_impulso_moral_sin_equipo_usa_el_del_user_y_tolera_valores_raros():
    j = jug(moral=70)
    e = {'mi_equipo': _equipo([j])}
    assert V.impulso_moral(e, None, 8, 'fase_copa') == 1 and j.moral == 78
    assert V.impulso_moral(e, None, 0, 'x') == 0 and V.impulso_moral(e, None, -5, 'x') == 0
    assert V.impulso_moral({}, None, 10, 'x') == 0                        # sin equipo: nada, sin romper
    assert j.moral == 78


# --- ganar tras 3+ partidos sin ganar ---------------------------------------------------------------

def _cerrar(e, gf, gc, previos):
    mi, rival = e['mi_equipo'], e['liga'].equipos[1]
    asegurar_ids_unicos(mi)
    for j in mi.jugadores:
        j.moral, j.salario, j.notas_recientes, j.causas_moral = 60, 0, [], []
    e['datos_carrera']['ult_res'] = list(previos)
    minutos = {j.id: 90 for j in mi.jugadores}
    V.post_partido_user(e, mi, rival, gf, gc, [], minutos, rng=random.Random(1), incidencias=[],
                        incidencias_rival=[])
    return mi


def _impulsos(mi):
    return [j.causas_moral[-1].get('impulso') for j in mi.jugadores if j.causas_moral]


def test_ganar_tras_tres_sin_ganar_levanta_a_todo_el_vestuario_10():
    mi = _cerrar(_estado(), 2, 0, ['P', 'E', 'P'])
    assert _impulsos(mi) and all(i == 10 for i in _impulsos(mi))
    assert all(j.causas_moral[-1].get('motivo_impulso') == 'racha_sin_ganar' for j in mi.jugadores)


def test_sin_impulso_si_hubo_una_victoria_reciente_o_si_no_gana():
    assert not any(_impulsos(_cerrar(_estado(), 2, 0, ['P', 'G', 'P'])))        # ganó hace 2 partidos
    assert not any(_impulsos(_cerrar(_estado(), 1, 1, ['P', 'E', 'P'])))        # empata: no gana
    assert not any(_impulsos(_cerrar(_estado(), 0, 1, ['P', 'P', 'P'])))        # pierde
    assert not any(_impulsos(_cerrar(_estado(), 2, 0, ['P', 'P'])))             # solo 2 partidos de historia


# --- cierre de temporada: bonus de potencial -------------------------------------------------------

def _plantel_joven(n, moral, promedio, notas=None):
    js = [jug(edad=21, moral=moral, promedio_nota=promedio, partidos_jugados=10, potencial=80,
              notas_recientes=list(notas or [])) for _ in range(n)]
    return _equipo(js)


def test_bonus_de_potencial_alcanza_a_mas_jugadores_y_sube_hasta_3():
    eq = _plantel_joven(200, moral=72, promedio=6.4)          # con la regla vieja (moral >= 75 y promedio >= 6.5): nadie
    V.cierre_temporada({'mi_equipo': eq}, rng=random.Random(7))
    subidas = [j.potencial - 80 for j in eq.jugadores]
    assert 0.75 <= sum(1 for s in subidas if s > 0) / 200 <= 0.95         # ~85 %
    assert max(subidas) == 3 and min(subidas) == 0
    assert 1.0 <= sum(subidas) / 200 <= 1.5                               # media ≈ +1.24 (antes +0.70)


def test_la_buena_forma_abre_el_bonus_aunque_la_moral_sea_baja():
    con_forma = _plantel_joven(100, moral=60, promedio=6.5, notas=[7.0] * 5)
    sin_forma = _plantel_joven(100, moral=60, promedio=6.5)
    V.cierre_temporada({'mi_equipo': con_forma}, rng=random.Random(3))
    V.cierre_temporada({'mi_equipo': sin_forma}, rng=random.Random(3))
    assert any(j.potencial > 80 for j in con_forma.jugadores)
    assert all(j.potencial == 80 for j in sin_forma.jugadores)
    assert all(j.potencial <= 83 for j in con_forma.jugadores + sin_forma.jugadores)
