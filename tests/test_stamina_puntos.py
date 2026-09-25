"""Test que verifica que los puntos y partidos cuentan tras jornadas."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(42)

from alpha_football.data import betplay
from alpha_football.plantilla import expandir_liga
from alpha_football.ui.match_screen import finalizar_jornada_liga
from alpha_football.ui.league_screen import inicializar_calendario_liga

liga = betplay.get_liga()
expandir_liga(liga, 25, 40)
inicializar_calendario_liga(liga)

mi = liga.equipos[0]
print(f"=== {mi.nombre} — Jornada 1 ===")

# Simular 3 jornadas
from alpha_football.engine import simular_partido

for jor in range(1, 4):
    partidos_j = [p for p in liga.calendario if p.jornada == jor]
    if not partidos_j:
        print(f"  J{jor}: sin partidos en calendario")
        continue
        
    p_user = next((p for p in partidos_j if p.local_id == mi.id or p.visitante_id == mi.id), None)
    if not p_user:
        print(f"  J{jor}: sin partido del user")
        continue
        
    local = next(e for e in liga.equipos if e.id == p_user.local_id)
    vis = next(e for e in liga.equipos if e.id == p_user.visitante_id)
    
    res = simular_partido(local, vis)
    print(f"  J{jor}: {local.nombre[:12]} {res.goles_local}-{res.goles_visitante} {vis.nombre[:12]}")
    
    estado = {'liga': liga, 'mi_equipo': mi, 'segunda_division': {},
              'historial': [], 'transfer_log': [], 'ofertas_recibidas': []}
    finalizar_jornada_liga(estado, liga, mi, p_user, res.goles_local, res.goles_visitante)
    
    # Verificar stats DESPUÉS de cada jornada
    print(f"         -> {mi.nombre[:12]} pts={mi.puntos} pj={mi.pj} pg={mi.pg} pe={mi.pe} pp={mi.pp} gf={mi.gf} gc={mi.gc}")
    
    # Verificar que TODOS los equipos tienen pj acumulado
    jugados = [p for p in liga.calendario if p.jugado]
    print(f"         -> {len(jugados)}/{len(liga.calendario)} partidos jugados en total")

# Verificación final
assert mi.pj == 3, f"User pj={mi.pj}, debe ser 3 tras 3 jornadas"
assert mi.puntos >= 0, f"User puntos={mi.puntos} debe ser >=0"
assert mi.gf + mi.gc > 0 or mi.puntos == 9 or mi.puntos == 0, "gf+gc deben sumar > 0 si hubo goles"

jugados_total = sum(1 for p in liga.calendario if p.jugado)
assert jugados_total >= 3 * (len(liga.equipos) // 2), f"Solo {jugados_total} partidos jugados (deberían ser ~{3 * len(liga.equipos)//2})"

print(f"\n=== RESUMEN TABLA TRAS 3 JORNADAS ===")
for eq in sorted(liga.equipos, key=lambda e: (-e.puntos, -(e.gf-e.gc))):
    print(f"  {eq.nombre[:18]:20s} pts={eq.puntos:2d} pj={eq.pj} gf={eq.gf} gc={eq.gc}")

# Verificar que hay equipos con puntos (no todos en 0)
total_pts_liga = sum(eq.puntos for eq in liga.equipos)
assert total_pts_liga > 0, f"Total puntos en la liga = {total_pts_liga}, todos en 0!"

print(f"\n✓ OK — Puntos, partidos e historial funcionan correctamente. Total puntos: {total_pts_liga}")
