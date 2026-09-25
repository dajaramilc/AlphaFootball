# -*- coding: utf-8 -*-
"""
Smoke test headless v2.3 — verifica imports + carga de 5 segundas divisiones.
"""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
import sys
sys.path.insert(0, '.')

# Importar los 5 módulos de 2ª división
from alpha_football.data.segunda_betplay import get_liga as gb
from alpha_football.data.segunda_laliga import get_liga as gl
from alpha_football.data.segunda_premier import get_liga as gp
from alpha_football.data.segunda_brasil import get_liga as gbr
from alpha_football.data.segunda_argentina import get_liga as ga

# Verificar que cada uno carga correctamente
total_j = 0
for fn, name in [(gb, 'betplay'), (gl, 'laliga'), (gp, 'premier'), (gbr, 'brasil'), (ga, 'argentina')]:
    liga = fn()
    assert liga.division == 2, f'{name}: division debe ser 2'
    assert len(liga.equipos) == 6, f'{name}: deben ser 6 equipos'
    for eq in liga.equipos:
        assert len(eq.jugadores) == 25, f'{name}/{eq.nombre}: deben ser 25 jugadores'
        assert eq.division == 2, f'{name}/{eq.nombre}: division del eq debe ser 2'
        for j in eq.jugadores:
            assert getattr(j, 'nombre', None), f'{name}/{eq.nombre}: jugador sin nombre'
            assert j.overall > 0, f'{name}/{eq.nombre}: jugador con overall 0'
    n_j = sum(len(e.jugadores) for e in liga.equipos)
    total_j += n_j
    print(f'OK {name}: 6 equipos × 25 = {n_j} jugadores, division={liga.division}, num_jornadas={liga.num_jornadas}')

print(f'\nTOTAL jugadores en 5 segundas divisiones: {total_j}')
assert total_j == 750, f'Esperaba 750, hay {total_j}'

# Verificar que los modelos aceptan los nuevos campos
from alpha_football.models import Liga, Equipo, Jugador, Alineacion, EstadoJuego
alin = Alineacion(titulares=[0,1,2,3,4,5,6,7,8,9,10], formacion='4-3-3', convocados=[11,12,13,14,15,16,17,18,19,20])
assert len(alin.convocados) == 10
print('OK Alineacion.convocados: 10 índices')

eq = Equipo(nombre='Test', ciudad='X', estrellas=3.0, estilo_dt='cruyffismo', balance=1000000)
assert eq.division == 1  # default
print('OK Equipo.division default 1')

liga = Liga(nombre='Test', tipo='betplay', equipos=[eq], num_jornadas=10, division=2)
assert liga.division == 2
print('OK Liga.division=2 seteable')

print('\n[v2.3 SMOKE OK]')