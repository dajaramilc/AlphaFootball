"""v0.4.11.0: calibración de los objetivos del user (manual). Simula temporadas completas de una liga
y mide cuántas veces un club cumple su meta con el criterio de la IA y con el exigente del user.
Uso: python tests/calibrar_objetivos.py [temporadas] [liga] [división]"""
import sys, os, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init(); pygame.display.set_mode((1280, 720))
logging.disable(logging.CRITICAL)
from alpha_football import directiva as D
from alpha_football.ui.menu import load_division_teams
from alpha_football.ui.league_screen import _simular_jornada_liga_fondo
from alpha_football.ui.copa_screen import cupos_copa

T = int(sys.argv[1]) if len(sys.argv) > 1 else 60
tipo = sys.argv[2] if len(sys.argv) > 2 else 'premier'
div = int(sys.argv[3]) if len(sys.argv) > 3 else 1
cupo = cupos_copa(tipo) if div == 1 else 0
cumple = {False: 0, True: 0}
total = 0
for _ in range(T):
    liga = load_division_teams(tipo, div)
    assert all(eq.pj == 0 for eq in liga.equipos), "load_division_teams devolvió una liga ya jugada"
    rk = sorted(liga.equipos, key=lambda e: -e.ovr_promedio)
    ventaja = rk[0].ovr_promedio - rk[1].ovr_promedio
    metas = {eq.id: {ex: D.objetivo_por_ranking(r, len(rk), div, cupo, ventaja, exigente=ex)[1]
                     for ex in (False, True)} for r, eq in enumerate(rk, 1)}
    while _simular_jornada_liga_fondo(liga):
        pass
    tabla = sorted(liga.equipos, key=lambda e: (e.puntos, e.gf - e.gc, e.gf), reverse=True)
    for pos, eq in enumerate(tabla, 1):
        total += 1
        for ex in (False, True):
            cumple[ex] += pos <= metas[eq.id][ex]
antes, ahora = 100 * cumple[False] / total, 100 * cumple[True] / total
print(f"{tipo} {div}ª: {T} temporadas, {total} clubes-temporada")
print(f"Cumplimiento con el criterio de la IA: {antes:.1f}%  ·  exigente (user): {ahora:.1f}%  ·  caída: {antes - ahora:.1f} puntos")
print("Objetivo en 1ª: caída entre 10 y 15 puntos. En 2ª se pide un solo puesto extra (ya es la más dura).")
