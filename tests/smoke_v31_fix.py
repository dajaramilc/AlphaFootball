"""Verifica que load_division_teams carga correctamente para los 5 paises."""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
import sys
sys.path.insert(0, '.')

import pygame
pygame.init()

from alpha_football.ui.menu import PAISES_DISPONIBLES, load_division_teams

print('Test: load_division_teams para 5 paises x 2 divisiones')
print('=' * 60)
errores = 0
for pais in PAISES_DISPONIBLES:
    for div in (1, 2):
        liga = load_division_teams(pais['codigo'], div)
        if liga is None:
            print(f"  FAIL  {pais['nombre']:<12} div {div}: None")
            errores += 1
            continue
        # Verificar tipo
        tipo_ok = liga.tipo == pais['liga_id']
        # Verificar jugadores
        n_eq = len(liga.equipos)
        n_jug_total = sum(len(e.jugadores) for e in liga.equipos)
        ovrs = [j.overall for e in liga.equipos for j in e.jugadores]
        ovr_min, ovr_max = min(ovrs), max(ovrs)
        ovr_avg = sum(ovrs) / len(ovrs)
        status = 'OK' if (tipo_ok and n_jug_total >= 25 * n_eq and ovr_max > 55) else 'FAIL'
        if status == 'FAIL':
            errores += 1
        print(f"  {status}  {pais['nombre']:<12} div {div}: tipo={liga.tipo!r:<10}  {n_eq} eq x {n_jug_total//n_eq} jug  OVR [{ovr_min}-{ovr_max}] avg={ovr_avg:.1f}")

print()
print(f'Errores: {errores}')
sys.exit(1 if errores else 0)