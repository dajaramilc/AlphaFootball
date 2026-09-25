"""v4.4.0 (sesión bebita): energía por colores, adición, nombres únicos, ventas con 25% para el club,
correo de llegada, "lo analizo" del jugador en el contrato e historial ordenable."""
import sys, os, random, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(44)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import save, engine, energia as E, nombres as NM, negociacion as N, correo as C
from alpha_football import contraofertas as CO
from alpha_football.models import alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams, _ligas_por_division
from alpha_football.ui import historial_pases_screen as H

save.guardar_en_slot = lambda *a, **k: None


def estado_carrera(tipo='premier', idx=0):
    liga = load_league_teams(tipo)
    mi = liga.equipos[idx]
    mi.alineacion_activa = alineacion_por_defecto(mi)
    primeras, segunda = _ligas_por_division(liga, {}, {})
    return {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
            'alineacion_activa': mi.alineacion_activa, 'primera_division': primeras,
            'segunda_division': segunda, 'datos_carrera': {}, 'historial': []}


class RngFijo(random.Random):
    def __init__(self, v): super().__init__(1); self.v = v
    def random(self): return self.v


def test_energia_umbrales():
    assert E.factor_energia(100) == 1.0 and E.factor_energia(70) == 1.0
    assert abs(E.factor_energia(55) - (1 - 15 / 600)) < 1e-9          # amarillo: pendiente simple
    assert abs(E.factor_energia(45) - (1 - 25 / 600 - 10 / 600)) < 1e-9   # rojo: pendiente doble
    assert E.factor_lesion(60) == 1.0                                    # lesiones sin cambios


def test_adicion_en_partidos():
    e = estado_carrera()
    a, b = e['liga'].equipos[0], e['liga'].equipos[1]
    fines, tardios = set(), 0
    for _ in range(60):
        r = engine.simular_partido(a, b, aplicar_fisico=False)
        assert 93 <= r.ctx.fin <= 100
        fines.add(r.ctx.fin)
        tardios += sum(1 for ev in r.eventos if ev.get('minuto', 0) > 90)
    assert len(fines) > 3 and tardios > 0


def test_nombres_unicos():
    e = estado_carrera()
    assert NM.desduplicar(e) >= 0
    c = collections.Counter(f"{j.nombre} {j.apellido}".lower() for j in NM._todos_los_jugadores(e))
    assert max(c.values()) == 1
    nuevos = {NM.nombre_unico() for _ in range(1500)}
    assert len(nuevos) == 1500 and not any(f"{n} {a}".lower() in c for n, a in nuevos)


def test_venta_retiene_25_y_avisa():
    e = estado_carrera(); mi = e['mi_equipo']; comp = e['liga'].equipos[3]
    comp.balance = 10 ** 10
    j = mi.jugadores[5]; antes = mi.balance
    assert CO.vender(e, {'jugador': j, 'comprador': comp, 'monto': 10_000_000})
    assert mi.balance - antes == 7_500_000
    m = C.bandeja(e)[0]
    assert "10,000,000" in m['cuerpo'] and "7,500,000" in m['cuerpo'] and "designamos" in m['cuerpo']


def test_fichaje_avisa_llegada():
    e = estado_carrera(); mi = e['mi_equipo']; mi.balance = 10 ** 10
    club = e['liga'].equipos[2]; j = sorted(club.jugadores, key=lambda x: x.overall)[0]
    ok, _ = N.fichar(e, j, club, precio=1000)
    assert ok and "acomódalo en tu plantilla" in C.bandeja(e)[0]['cuerpo']


def test_contrato_en_analisis_renovacion_y_fichaje():
    e = estado_carrera(); mi = e['mi_equipo']; mi.balance = 10 ** 10
    e['liga'].jornada_actual = 1
    # Renovación: 90% de lo que pide → "lo analizo"; al 70% → rechazo normal.
    j = mi.jugadores[4]
    N.iniciar_negociacion(e, j, None, 'renovar', 'plantilla_screen')
    pedido = N.salario_pedido(j, 'renovar', e['neg']['clausula_mult'])
    e['neg']['salario'] = int(pedido * 0.7)
    assert N.analizar_contrato(e, e['neg']) is None
    e['neg']['salario'] = int(pedido * 0.9)
    assert "analizo" in N.analizar_contrato(e, e['neg']).lower()
    CO.resolver_analisis(e, rng=RngFijo(0.0))                   # misma jornada: nada
    assert e['datos_carrera']['analisis_contratos']
    e['liga'].jornada_actual = 2
    CO.resolver_analisis(e, rng=RngFijo(0.0))                   # acepta
    assert not e['datos_carrera']['analisis_contratos'] and j.salario == int(pedido * 0.9)
    assert "renovar" in C.bandeja(e)[0]['asunto']
    # Fichaje: el jugador lo analiza y, si acepta, llega con el correo de bienvenida.
    club = e['liga'].equipos[2]; f = sorted(club.jugadores, key=lambda x: x.overall)[1]
    N.iniciar_negociacion(e, f, club, 'fichaje', 'buscador_screen')
    e['neg']['etapa'], e['neg']['monto'] = 'jugador', 1000
    pedido = N.salario_pedido(f, 'fichaje', e['neg']['clausula_mult'])
    e['neg']['salario'] = int(pedido * 0.95)
    assert N.analizar_contrato(e, e['neg'])
    e['liga'].jornada_actual = 3
    CO.resolver_analisis(e, rng=RngFijo(0.0))
    assert f in mi.jugadores and "acomódalo" in C.bandeja(e)[0]['cuerpo']
    # Rechazo: correo con lo que pide.
    g = sorted(club.jugadores, key=lambda x: x.overall)[1]
    N.iniciar_negociacion(e, g, club, 'fichaje', 'buscador_screen')
    e['neg']['monto'] = 1000
    e['neg']['salario'] = int(N.salario_pedido(g, 'fichaje', e['neg']['clausula_mult']) * 0.9)
    e['liga'].jornada_actual = 1                                # ventana abierta
    N.analizar_contrato(e, e['neg'])
    e['liga'].jornada_actual = 2
    CO.resolver_analisis(e, rng=RngFijo(0.99))
    assert g not in mi.jugadores and "no acepta" in C.bandeja(e)[0]['asunto']


def test_historial_ordenable():
    pases = [{'temporada': 1, 'jornada': 3, 'jugador': 'Beto', 'media': 70, 'monto': 5, 'de': 'X', 'a': 'Y'},
             {'temporada': 1, 'jornada': 2, 'jugador': 'ana', 'media': 80, 'monto': 9, 'de': 'Z', 'a': 'W'},
             {'temporada': 1, 'jornada': 1, 'jugador': 'Carlos', 'media': 60, 'monto': 1, 'de': 'A', 'a': 'B'}]
    assert [p['jugador'] for p in H.ordenar(pases, 'jugador', False)] == ['ana', 'Beto', 'Carlos']
    assert [p['monto'] for p in H.ordenar(pases, 'monto', True)] == [9, 5, 1]
    assert [p['jornada'] for p in H.ordenar(pases, 'cuando', False)] == [1, 2, 3]
    e = estado_carrera()
    e['datos_carrera']['historial_pases'] = list(reversed(pases))
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=H._rect_columna(3).center))
    assert H.render(screen, e) is None and e['hist_pases_orden'] == ('media', True)
