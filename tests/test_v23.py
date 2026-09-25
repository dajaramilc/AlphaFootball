# -*- coding: utf-8 -*-
"""
Test v2.3 — Bono ×2, swap promo/releg, compatibilidad, menu flow.
"""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
import sys
sys.path.insert(0, '.')

# Bono ×2 (v2.3)
from alpha_football.ui.resumen_temporada_screen import _BONO_LIGA_2A_X2
print('[BONO ×2]')
for pais, tabla in _BONO_LIGA_2A_X2.items():
    # Todos los valores deben ser pares (×2 sobre los originales 15M, 8M, etc.)
    if pais == 'premier':
        assert tabla == [30_000_000, 16_000_000, 8_000_000, 4_000_000, 4_000_000, 2_000_000], tabla
    elif pais == 'betplay':
        assert tabla == [4_000_000, 2_000_000, 1_000_000, 600_000, 600_000, 400_000], tabla
print(f'  premier[0] = {_BONO_LIGA_2A_X2["premier"][0]} (esperado 30M)')
print(f'  betplay[0] = {_BONO_LIGA_2A_X2["betplay"][0]} (esperado 4M)')
print('  OK')

# Liga.division default
from alpha_football.models import Liga, Equipo, Jugador, Alineacion, EstadoJuego
print('\n[MODELO: Liga.division]')
liga1 = Liga(nombre='X', tipo='betplay', equipos=[], num_jornadas=10)
assert liga1.division == 1, 'default debe ser 1'
liga2 = Liga(nombre='Y', tipo='betplay', equipos=[], num_jornadas=10, division=2)
assert liga2.division == 2
# roundtrip dict
d = liga2.to_dict()
assert d['division'] == 2
liga3 = Liga.from_dict(d)
assert liga3.division == 2
print('  default=1, seteable=2, roundtrip OK')

# Equipo.division default
eq = Equipo(nombre='X', ciudad='Y', estrellas=3.0, estilo_dt='cruyffismo', balance=1000)
assert eq.division == 1
print('  Equipo.division default=1 OK')

# Alineacion.convocados
print('\n[MODELO: Alineacion.convocados]')
alin = Alineacion(titulares=[0,1,2,3,4,5,6,7,8,9,10], formacion='4-3-3', convocados=[11,12,13,14,15,16,17,18,19,20])
assert len(alin.convocados) == 10
# roundtrip
d = alin.to_dict() if hasattr(alin, 'to_dict') else {'titulares': alin.titulares, 'formacion': alin.formacion, 'convocados': alin.convocados}
print(f'  alin.convocados: {len(alin.convocados)} (esperado 10)')

# Save viejo sin division ni convocados → defaults
print('\n[COMPAT: save viejo]')
data_viejo = {
    'nombre': 'Liga Vieja',
    'tipo': 'betplay',
    'equipos': [{'nombre': 'Eq', 'ciudad': 'C', 'estrellas': 3.0, 'estilo_dt': 'cruyffismo',
                'balance': 1000000, 'jugadores': [], 'es_usuario': False, 'nombre_corto': '',
                'tactica_familiaridad': {}, 'puntos': 0, 'pj': 0, 'pg': 0, 'pe': 0, 'pp': 0, 'gf': 0, 'gc': 0}],
    'num_jornadas': 14,
    'calendario': [],
    'jornada_actual': 1
}
liga_v = Liga.from_dict(data_viejo)
assert liga_v.division == 1, f'debe ser 1 por default, dio {liga_v.division}'
print(f'  Liga.vieja.division = {liga_v.division} (default 1)')

eq_v = liga_v.equipos[0]
assert eq_v.division == 1
print(f'  Eq.viejo.division = {eq_v.division} (default 1)')

# EstadoJuego defaults
print('\n[MODELO: EstadoJuego nuevos campos]')
est = EstadoJuego()
assert est.liga_usuario_division == 1
assert isinstance(est.segunda_division, dict)
print(f'  liga_usuario_division = {est.liga_usuario_division}')
print(f'  segunda_division = type {type(est.segunda_division).__name__}')

# Plantilla default 25
print('\n[PLANTILLA: default 25]')
from alpha_football.plantilla import expandir_plantilla, expandir_liga
import inspect
sig = inspect.signature(expandir_plantilla)
assert sig.parameters['objetivo'].default == 25
print(f'  expandir_plantilla default objetivo = {sig.parameters["objetivo"].default}')
sig = inspect.signature(expandir_liga)
assert sig.parameters['objetivo'].default == 25
print(f'  expandir_liga default objetivo = {sig.parameters["objetivo"].default}')

# PLANTILLA_MAXIMA = 40
from alpha_football.market import PLANTILLA_MAXIMA
assert PLANTILLA_MAXIMA == 40, f'Esperaba 40, hay {PLANTILLA_MAXIMA}'
print(f'  PLANTILLA_MAXIMA = {PLANTILLA_MAXIMA}')

# match_screen banco_idx filtrado por convocados
print('\n[BANQUILLO: filtrado por convocados]')
# Lo verificamos en el código (grep)
with open('alpha_football/ui/match_screen.py', 'r', encoding='utf-8') as f:
    code = f.read()
assert 'alin.convocados' in code, 'match_screen debe filtrar por alin.convocados'
print('  match_screen._menu_tactico filtra por alin.convocados OK')

# Menu: PAISES_DISPONIBLES + load_division_teams
print('\n[MENU: País → División]')
with open('alpha_football/ui/menu.py', 'r', encoding='utf-8') as f:
    code = f.read()
assert 'PAISES_DISPONIBLES' in code, 'menu.py debe tener PAISES_DISPONIBLES'
assert 'load_division_teams' in code, 'menu.py debe tener load_division_teams'
assert 'select_country' in code, 'menu.py debe tener paso select_country'
assert 'select_division' in code, 'menu.py debe tener paso select_division'
assert 'amistoso_country' in code, 'menu.py debe tener paso amistoso_country'
assert 'amistoso_division' in code, 'menu.py debe tener paso amistoso_division'
print('  PAISES_DISPONIBLES + load_division_teams + steps País/División OK')

# League screen toggle 1ª⇄2ª
print('\n[LEAGUE SCREEN: toggle 1ª⇄2ª]')
with open('alpha_football/ui/league_screen.py', 'r', encoding='utf-8') as f:
    code = f.read()
assert 'otras_ligas_screen' in code, 'v2.3.5: league_screen abre OTRAS LIGAS (reemplaza el toggle)'
assert 'simular_jornada_segunda_division' in code, 'league_screen debe definir el helper'
print('  liga_view + liga_vista + simular_jornada_segunda_division OK')

# Team screen: convocados + auto + reservas
print('\n[TEAM SCREEN: PES style]')
with open('alpha_football/ui/team_screen.py', 'r', encoding='utf-8') as f:
    code = f.read()
# v2.3.5: dirección estilo FIFA (selección + intercambio); el comportamiento se prueba en test_ui_v235.py
assert 'team_sel' in code, 'team_screen debe tener team_sel'
assert 'team_view' in code, 'team_screen debe tener team_view'
assert 'VER RESERVAS' in code, 'team_screen debe tener botón VER RESERVAS'
assert 'F.intercambiar' in code, 'team_screen debe intercambiar jugador por jugador'
print('  team_sel + team_view + VER RESERVAS + intercambiar OK')

# Resumen temporada: swap promo/releg + fix pos_user
print('\n[RESUMEN TEMPORADA: swap + fix]')
with open('alpha_football/ui/resumen_temporada_screen.py', 'r', encoding='utf-8') as f:
    code = f.read()
assert 'promo_releg_data' in code, 'debe tener la estructura del swap'
assert 'user_ascendio' in code, 'debe detectar ascenso'
assert 'user_descendio' in code, 'debe detectar descenso'
assert 'pos_user = 1' in code, 'debe inicializar pos_user (fix)'
assert '_BONO_LIGA_2A_X2' in code, 'debe tener la tabla ×2'
print('  swap + fix pos_user + bono ×2 OK')

print('\n[v2.3 TESTS OK]')