"""v4.6.0: calibración de la economía (manual). Mide quiebras de la IA por temporada y la plata
de un club del user prudente vs derrochador. Uso: python tests/calibrar_finanzas.py [temporadas]"""
import sys, os, random, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
logging.disable(logging.CRITICAL)
from alpha_football import finanzas as F, mercado_ia as MI
from alpha_football.ui.menu import load_league_teams, _ligas_por_division
from alpha_football.models import alineacion_por_defecto

T = int(sys.argv[1]) if len(sys.argv) > 1 else 5
liga = load_league_teams('premier'); mi = liga.equipos[0]; mi.alineacion_activa = alineacion_por_defecto(mi)
primeras, segunda = _ligas_por_division(liga, {}, {})
e = {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1, 'primera_division': primeras,
     'segunda_division': segunda, 'datos_carrera': {'economia_v2': True}, 'historial': []}
F.asegurar_contratos(e)
MI.asignar_presupuestos_realistas(e, incluir_usuario=False, rng=random.Random(1))
n_clubes = sum(len(l.equipos) for l, _t, _d in MI.ligas_de_la_partida(e))
total = 0
for t in range(1, T + 1):
    e['temporada'] = t
    q = MI.ingresos_fin_temporada(e, random.Random(t))
    MI.ronda_fichajes_ia(e, 'pretemporada', random.Random(100 + t))
    for _ in range(3):
        MI.ronda_fichajes_ia(e, 'ventana', random.Random(200 + t))
    total += len(q)
    print(f"T{t}: {len(q)} quiebras IA {q}")
print(f"Promedio: {total / T:.2f} quiebras de la IA por temporada entre {n_clubes} clubes (objetivo ≈ 1)")
for tipo in ('premier', 'laliga', 'brasil', 'argentina', 'betplay'):
    lg = load_league_teams(tipo)
    for eq in (max(lg.equipos, key=lambda x: x.estrellas), min(lg.equipos, key=lambda x: x.estrellas)):
        ing = F.ingresos_esperados(eq, tipo, 1)
        masa = sum(F.contrato_inicial(j, random.Random(0))[0] for j in eq.jugadores)
        print(f"{tipo:9} {eq.nombre[:18]:18} ingresos {ing / 1e6:6.1f}M  sueldos {masa / 1e6:6.1f}M  "
              f"neto {(ing - masa) / 1e6:+6.1f}M  (derrochador +30% masa: {(ing - masa * 1.3) / 1e6:+6.1f}M)")
