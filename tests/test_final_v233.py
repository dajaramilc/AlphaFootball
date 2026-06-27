"""Tests completos para todas las features reparadas en Fase 1 + Fase 2."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(42)

from alpha_football.data import betplay, segunda_betplay
from alpha_football.plantilla import expandir_liga
from alpha_football.ui.resumen_temporada_screen import avanzar_nueva_temporada

FAILS = []

def check(cond, msg):
    if not cond:
        FAILS.append(msg)

# ── 1. Promo/releg bidireccional ─────────────────────────────────────

def test_user_en_1a_no_desciende_si_top():
    liga1 = betplay.get_liga(); liga2 = segunda_betplay.get_liga()
    expandir_liga(liga1, 25, 40); expandir_liga(liga2, 25, 40)
    mi = liga1.equipos[0]; mi.puntos = 30; mi.gf = 20; mi.gc = 5
    liga1.equipos[-1].puntos = 2; liga1.equipos[-1].gf = 1; liga1.equipos[-1].gc = 20
    liga1.equipos[-2].puntos = 5; liga1.equipos[-2].gf = 3; liga1.equipos[-2].gc = 15
    liga2.equipos[0].puntos = 25; liga2.equipos[0].gf = 15; liga2.equipos[0].gc = 2
    liga2.equipos[1].puntos = 22; liga2.equipos[1].gf = 12; liga2.equipos[1].gc = 3
    estado = {'liga': liga1, 'mi_equipo': mi, 'temporada': 1,
              'segunda_division': {'betplay': liga2},
              'copa_user_en_copa': True, 'copa_clasificado': True,
              'historial': [], 'transfer_log': []}
    avanzar_nueva_temporada(estado)
    pr = estado.get('promo_releg_resultado', {})
    check(pr.get('user_ascendio') == False, "User no debio ascender")
    check(pr.get('user_descendio') == False, "User no debio descender")
    check(len(pr.get('ascendieron', [])) == 2, "Deben ascender 2")
    check(len(pr.get('descendieron', [])) == 2, "Deben descender 2")
    print("  test_user_en_1a_no_desciende_si_top: OK")

def test_user_en_2a_asciende():
    liga1 = betplay.get_liga(); liga2 = segunda_betplay.get_liga()
    expandir_liga(liga1, 25, 40); expandir_liga(liga2, 25, 40)
    mi = liga2.equipos[0]; mi.puntos = 30; mi.gf = 20; mi.gc = 2
    liga2.equipos[1].puntos = 25; liga2.equipos[1].gf = 15; liga2.equipos[1].gc = 3
    liga1.equipos[-1].puntos = 1; liga1.equipos[-1].gf = 1; liga1.equipos[-1].gc = 25
    liga1.equipos[-2].puntos = 4; liga1.equipos[-2].gf = 3; liga1.equipos[-2].gc = 18
    estado = {'liga': liga2, 'mi_equipo': mi, 'temporada': 1,
              'liga_usuario_division': 2,
              'segunda_division': {'betplay': liga2},
              'copa_user_en_copa': False, 'copa_clasificado': False,
              'historial': [], 'transfer_log': []}
    avanzar_nueva_temporada(estado)
    pr = estado.get('promo_releg_resultado', {})
    check(pr.get('user_ascendio') == True, "User en 2a debio ascender")
    check(estado.get('liga_usuario_division') == 1, f"Division={estado.get('liga_usuario_division')}")
    check(estado['liga'].division == 1, "Liga debe ser 1a division")
    print("  test_user_en_2a_asciende: OK")

def test_user_en_1a_desciende_si_bottom():
    liga1 = betplay.get_liga(); liga2 = segunda_betplay.get_liga()
    expandir_liga(liga1, 25, 40); expandir_liga(liga2, 25, 40)
    # Dar puntos a TODOS los equipos de 1a para que el ordenamiento funcione
    for i, eq in enumerate(liga1.equipos):
        eq.puntos = 15 - i; eq.pj = 10; eq.gf = 20 - i; eq.gc = 10
    # Bottom 2: user = ultimo con 2 pts
    mi = liga1.equipos[-1]; mi.puntos = 2; mi.gf = 1; mi.gc = 20
    liga1.equipos[-2].puntos = 3; liga1.equipos[-2].gf = 2; liga1.equipos[-2].gc = 18
    # Top 2 de 2a
    for i, eq in enumerate(liga2.equipos):
        eq.puntos = 10 - i; eq.pj = 10; eq.gf = 10 + i; eq.gc = 3
    liga2.equipos[0].puntos = 25; liga2.equipos[0].gf = 15
    liga2.equipos[1].puntos = 22; liga2.equipos[1].gf = 12
    estado = {'liga': liga1, 'mi_equipo': mi, 'temporada': 1,
              'liga_usuario_division': 1,
              'segunda_division': {'betplay': liga2},
              'copa_user_en_copa': True, 'copa_clasificado': True,
              'historial': [], 'transfer_log': []}
    avanzar_nueva_temporada(estado)
    pr = estado.get('promo_releg_resultado', {})
    check(pr.get('user_descendio') == True, "User debio descender")
    check(estado.get('liga_usuario_division') == 2, f"Division={estado.get('liga_usuario_division')}")
    check(estado.get('copa_user_en_copa') == False, "Sin copa en 2a")
    print("  test_user_en_1a_desciende_si_bottom: OK")

# ── 2. Convocados save/load ────────────────────────────────────────

def test_convocados_persistencia():
    from alpha_football.models import Alineacion, EstadoJuego
    a = Alineacion(titulares=list(range(11)), formacion="4-3-3", convocados=list(range(11,21)))
    ej = EstadoJuego(); ej.alineacion_activa = a
    d = ej.to_dict()
    check('convocados' in d['alineacion_activa'], "to_dict no incluye convocados")
    check(d['alineacion_activa']['convocados'] == list(range(11,21)), "convocados incorrectos en to_dict")
    ej2 = EstadoJuego.from_dict(d)
    check(ej2.alineacion_activa.convocados == list(range(11,21)), "from_dict no cargo convocados")
    print("  test_convocados_persistencia: OK")

def test_convocados_retrocompatibilidad():
    """Saves viejos sin campo convocados deben cargar con lista vacía."""
    from alpha_football.models import EstadoJuego
    d = {'ligas': [], 'copas': [], 'alineacion_activa': {'titulares': [], 'formacion': '4-3-3'}}
    ej = EstadoJuego.from_dict(d)
    check(ej.alineacion_activa.convocados == [], f"Retrocompat: {ej.alineacion_activa.convocados}")
    print("  test_convocados_retrocompatibilidad: OK")

# ── 3. Engine simulacion 2a division ───────────────────────────────

def test_liga_2a_tracking_stats():
    liga2 = segunda_betplay.get_liga(); expandir_liga(liga2, 25, 40)
    e1, e2 = liga2.equipos[0], liga2.equipos[1]
    from alpha_football import engine
    res = engine.simular_partido(e1, e2)
    e1.gf += res.goles_local; e1.gc += res.goles_visitante; e1.pj += 1
    e2.gf += res.goles_visitante; e2.gc += res.goles_local; e2.pj += 1
    if res.goles_local > res.goles_visitante:
        e1.puntos += 3; e1.pg += 1; e2.pp += 1
    elif res.goles_local < res.goles_visitante:
        e2.puntos += 3; e2.pg += 1; e1.pp += 1
    else:
        e1.puntos += 1; e2.puntos += 1; e1.pe += 1; e2.pe += 1
    # Stats deben ser consistentes
    check(e1.pj == 1 and e2.pj == 1, f"pj: {e1.pj}/{e2.pj}")
    total_pts = e1.puntos + e2.puntos
    check(total_pts in (2, 3, 4), f"total_pts={total_pts} (debe ser 2-4)")
    print("  test_liga_2a_tracking_stats: OK")

# ── 4. Bono 2a division (valores correctos segun diseño) ──────────

def test_bono_2a_valores():
    from alpha_football.ui.resumen_temporada_screen import _BONO_LIGA_2A_X2
    check('premier' in _BONO_LIGA_2A_X2, "Falta premier en bono 2a")
    check('betplay' in _BONO_LIGA_2A_X2, "Falta betplay en bono 2a")
    # Cada entrada debe tener 6 posiciones
    for k, v in _BONO_LIGA_2A_X2.items():
        check(len(v) == 6, f"Bono {k} len={len(v)}, esperado 6")
    print("  test_bono_2a_valores: OK")

# ── RUN ───────────────────────────────────────────────────────────

if __name__ == '__main__':
    tests = [test_user_en_1a_no_desciende_si_top, test_user_en_2a_asciende,
             test_user_en_1a_desciende_si_bottom,
             test_convocados_persistencia, test_convocados_retrocompatibilidad,
             test_liga_2a_tracking_stats, test_bono_2a_valores]
    ok = 0
    for t in tests:
        try:
            t()  # prints OK already
            ok += 1
        except Exception as e:
            print(f"  {t.__name__}: CRASH - {e}")
    if FAILS:
        print(f"\n{len(FAILS)} FALLOS:")
        for f in FAILS:
            print(f"  - {f}")
    print(f"\n{ok}/{len(tests)} pasaron ({len(FAILS)} asserts fallidos)")
    if FAILS:
        sys.exit(1)
