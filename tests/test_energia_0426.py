"""v0.4.26.0: recuperación de energía fija por día (ítem 12) y energía de los clubes de la IA (ítem 18)."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(26)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import energia as E
from alpha_football.models import Jugador, Equipo, Liga
from alpha_football.ui.menu import load_league_teams


def jug(pos='MED', ovr=70, edad=25, res=60, **kw):
    return Jugador("Test", f"J{random.randint(0, 10**6)}", pos, ovr, ovr, ovr, ovr, ovr, edad=edad,
                   id=random.randint(10**6, 10**7), resistencia=res, **kw)


def _estado(jugadores, num_jornadas=22):
    eq = Equipo(nombre="Test FC", ciudad="C", estrellas=3.0, estilo_dt="cruyffismo", balance=1_000_000,
                jugadores=jugadores)
    liga = Liga(nombre="L", tipo="premier", equipos=[eq], num_jornadas=num_jornadas)
    return {'liga': liga, 'mi_equipo': eq, 'primera_division': {'premier': liga}, 'temporada': 1,
            'datos_carrera': {}}


# --- ítem 12: recuperación fija por día ------------------------------------------------------------

def test_la_recuperacion_diaria_es_fija_y_da_30_35_por_semana():
    assert abs(E.recuperacion(jug(res=40)) - 4.0) < 1e-9
    assert abs(E.recuperacion(jug(res=60)) - 4.5) < 1e-9
    assert abs(E.recuperacion(jug(res=80)) - 5.0) < 1e-9
    assert abs(E.recuperacion(jug(res=60, edad=33)) - 4.1) < 1e-9          # más de 30 años: −0.4 por día
    for res in (40, 60, 80, 99):
        semana = E.recuperacion(jug(res=res)) * 7
        assert 28 - 1e-9 <= semana <= 39, (res, semana)


def test_17_dias_de_descanso_recuperan_mucho_mas_que_los_30_35_de_antes():
    j = jug(res=60)
    j.energia = 10
    E.recuperar(j, 17)
    assert j.energia >= 10 + 17 * 4.0 - 1e-9                              # antes: 26-34 en 17 días
    j.energia = 95
    E.recuperar(j, 17)
    assert j.energia == 100                                               # tope


def test_recuperar_todos_no_depende_de_la_duracion_de_la_temporada():
    ganancias = []
    for n in (20, 22, 38):
        j = jug(res=60)
        j.energia = 10
        e = _estado([j], num_jornadas=n)
        E.recuperar_todos(e, 17)
        ganancias.append(round(j.energia - 10, 6))
    assert ganancias[0] == ganancias[1] == ganancias[2] and abs(ganancias[0] - 17 * 4.5) < 1e-6


def test_recuperar_todos_sin_dias_es_una_semana_y_con_cero_o_negativos_no_recupera():
    j = jug(res=60)
    e = _estado([j])
    j.energia = 10
    E.recuperar_todos(e)
    assert abs(j.energia - 10 - 4.5 * E.DIAS_SIN_CALENDARIO) < 1e-9
    j.energia = 10
    E.recuperar_todos(e, 0)
    E.recuperar_todos(e, -3)
    assert j.energia == 10


# --- ítem 18: la IA también gasta energía, rinde menos cansada y rota ------------------------------

def test_los_clubes_de_la_ia_gastan_energia_en_sus_partidos():
    from alpha_football.engine import simular_partido
    liga = load_league_teams('premier')
    a, b = liga.equipos[0], liga.equipos[1]
    for j in a.jugadores + b.jugadores:
        j.energia = 100.0
    simular_partido(a, b, con_eventos_caoticos=False)
    for eq in (a, b):
        cansados = [j for j in eq.jugadores if j.energia < 100.0]
        assert len(cansados) >= 9, (eq.nombre, len(cansados))              # los titulares terminan cansados


def test_el_cansancio_baja_el_rendimiento_de_cualquier_jugador():
    j = jug(pos='DEL', ovr=75)
    j.energia = 100.0
    descansado = j.poder_ataque_efectivo()
    j.energia = 30.0
    assert j.poder_ataque_efectivo() < descansado * 0.95


def test_la_ia_rota_al_cansado_con_puntaje_once():
    from alpha_football.engine import _once_titular
    plantel = ([jug('POR', 80), jug('POR', 60)] + [jug('DEF', 70) for _ in range(5)]
               + [jug('MED', 70) for _ in range(4)]
               + [jug('DEL', 75), jug('DEL', 70), jug('DEL', 70), jug('DEL', 69)])
    estrella = plantel[-4]                                                 # el mejor delantero
    eq = Equipo(nombre="IA FC", ciudad="C", estrellas=3.0, estilo_dt="cruyffismo", balance=1_000_000,
                jugadores=plantel)                                         # sin alineación: la arma el motor
    assert eq.alineacion_activa is None
    assert estrella in _once_titular(eq)                                   # descansado: juega
    estrella.energia = 10.0
    assert estrella not in _once_titular(eq)                               # cansado: entra el 4º delantero
    assert plantel[-1] in _once_titular(eq)
