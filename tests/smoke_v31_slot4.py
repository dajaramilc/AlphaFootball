"""Verifica el caso pathologico del slot 4 viejo con tipo='colombia'."""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
import sys
sys.path.insert(0, '.')

import pygame
pygame.init()

from alpha_football.ui.menu import load_league_teams, load_division_teams

print('Caso patologico: el slot 4 viejo se guardo con tipo="colombia"')
print('Cuando se recargue, el save tiene liga.tipo="colombia" y no matchea con ningun modulo.')
print()

# load_league_teams llamado con 'colombia' (lo que habia en el slot viejo) -> FALLA
print('Test 1: load_league_teams("colombia") (caso patologico del slot 4 viejo)')
resultado = load_league_teams('colombia')
print(f'  Resultado: {resultado}')
if resultado is None:
    print('  OK: retorna None, no rompe')
elif 'Ficticia' in resultado.nombre:
    print(f'  ATENCION: cae al fallback Liga Ficticia -> {resultado.nombre}')
print()

# load_division_teams con country_id correcto: 'colombia' deberia mapear a 'betplay'
print('Test 2: load_division_teams("colombia", 1) -> deberia cargar BetPlay 1a')
liga = load_division_teams('colombia', 1)
print(f'  Liga cargada: {liga.nombre if liga else None}')
print(f'  Tipo: {liga.tipo if liga else None}')
print(f'  Equipos: {len(liga.equipos) if liga else 0}')
print(f'  Primer equipo: {liga.equipos[0].nombre if liga and liga.equipos else "N/A"}')
print(f'  Jugadores primer eq: {len(liga.equipos[0].jugadores) if liga and liga.equipos else 0}')
if liga and liga.equipos:
    ovrs = [j.overall for j in liga.equipos[0].jugadores]
    print(f'  OVR primer eq: min={min(ovrs)}, max={max(ovrs)}, avg={sum(ovrs)/len(ovrs):.1f}')