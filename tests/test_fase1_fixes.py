"""Test end-to-end del swap promo/releg bidireccional."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(42)

from alpha_football.data import betplay, segunda_betplay
from alpha_football.plantilla import expandir_liga
from alpha_football.ui.resumen_temporada_screen import avanzar_nueva_temporada

def test_user_en_1a_asciende_alguien():
    """User en 1a: bottom-2 de 1a descienden, top-2 de 2a ascienden."""
    liga1 = betplay.get_liga()
    liga2 = segunda_betplay.get_liga()
    expandir_liga(liga1, 25, 40)
    expandir_liga(liga2, 25, 40)

    # User es el primer equipo de 1a
    mi = liga1.equipos[0]
    # Dar stats para que el user sea top y no descienda
    mi.puntos = 30; mi.gf = 20; mi.gc = 5
    # Bottom 2 de 1a: los ultimos con pocos puntos
    liga1.equipos[-1].puntos = 2; liga1.equipos[-1].gf = 1; liga1.equipos[-1].gc = 20
    liga1.equipos[-2].puntos = 5; liga1.equipos[-2].gf = 3; liga1.equipos[-2].gc = 15
    # Top 2 de 2a: los primeros
    liga2.equipos[0].puntos = 25; liga2.equipos[0].gf = 15; liga2.equipos[0].gc = 2
    liga2.equipos[1].puntos = 22; liga2.equipos[1].gf = 12; liga2.equipos[1].gc = 3

    estado = {
        'liga': liga1, 'mi_equipo': mi, 'temporada': 1,
        'segunda_division': {'betplay': liga2},
        'copa_user_en_copa': True, 'copa_clasificado': True,
        'historial': [], 'transfer_log': [],
    }
    n_1a_before = len(liga1.equipos)
    n_2a_before = len(liga2.equipos)

    avanzar_nueva_temporada(estado)

    assert estado['temporada'] == 2
    assert 'promo_releg_resultado' in estado
    pr = estado['promo_releg_resultado']
    assert len(pr['ascendieron']) == 2, f"Ascendieron {len(pr['ascendieron'])} equipos"
    assert len(pr['descendieron']) == 2, f"Descendieron {len(pr['descendieron'])} equipos"
    assert pr['user_ascendio'] == False, "User no debio ascender (ya estaba en 1a)"
    assert pr['user_descendio'] == False, "User no debio descender (es top)"

    print("  test_user_en_1a_asciende_alguien: OK")

def test_user_en_2a_puede_ascender():
    """User en 2a: top-2 de 2a ascienden (incluyendo al user)."""
    liga1 = betplay.get_liga()
    liga2 = segunda_betplay.get_liga()
    expandir_liga(liga1, 25, 40)
    expandir_liga(liga2, 25, 40)

    # User en 2a
    mi = liga2.equipos[0]
    mi.puntos = 30; mi.gf = 20; mi.gc = 2
    liga2.equipos[1].puntos = 25; liga2.equipos[1].gf = 15; liga2.equipos[1].gc = 3
    liga2.equipos[2].puntos = 10
    liga2.equipos[3].puntos = 8
    liga2.equipos[4].puntos = 5
    liga2.equipos[5].puntos = 3

    # Bottom 2 de 1a
    liga1.equipos[-1].puntos = 1; liga1.equipos[-1].gf = 1; liga1.equipos[-1].gc = 25
    liga1.equipos[-2].puntos = 4; liga1.equipos[-2].gf = 3; liga1.equipos[-2].gc = 18

    estado = {
        'liga': liga2, 'mi_equipo': mi, 'temporada': 1,
        'liga_usuario_division': 2,
        'segunda_division': {'betplay': liga2},
        'copa_user_en_copa': False, 'copa_clasificado': False,
        'historial': [], 'transfer_log': [],
    }

    avanzar_nueva_temporada(estado)

    assert estado['temporada'] == 2
    assert 'promo_releg_resultado' in estado
    pr = estado['promo_releg_resultado']
    assert len(pr['ascendieron']) == 2
    assert pr['user_ascendio'] == True, "¡User debio ascender de 2a a 1a!"
    assert pr['user_descendio'] == False
    assert estado['liga_usuario_division'] == 1, f"Division deberia ser 1, es {estado['liga_usuario_division']}"
    # El user ahora debe estar en la liga 1a
    assert estado['liga'] is not None
    assert estado['liga'].division == 1, f"Liga division={estado['liga'].division}"

    print("  test_user_en_2a_puede_ascender: OK")

def test_convocados_survive_roundtrip():
    """Verifica que convocados se persiste en save/load."""
    from alpha_football.models import Alineacion, EstadoJuego
    a = Alineacion(titulares=list(range(11)), formacion="4-3-3", convocados=[11,12,13,14,15,16,17,18,19,20])
    ej = EstadoJuego()
    ej.alineacion_activa = a
    d = ej.to_dict()
    alin_d = d['alineacion_activa']
    assert 'convocados' in alin_d, "convocados no esta en el dict serializado"
    assert alin_d['convocados'] == list(range(11,21)), f"convocados={alin_d['convocados']}"
    ej2 = EstadoJuego.from_dict(d)
    assert ej2.alineacion_activa is not None
    assert ej2.alineacion_activa.convocados == list(range(11,21)), f"cargados={ej2.alineacion_activa.convocados}"
    print("  test_convocados_survive_roundtrip: OK")

if __name__ == '__main__':
    tests = [test_user_en_1a_asciende_alguien, test_user_en_2a_puede_ascender, test_convocados_survive_roundtrip]
    ok = fail = 0
    for t in tests:
        try:
            t()
            ok += 1
        except Exception as e:
            fail += 1
            print(f"  {t.__name__}: FAIL - {e}")
    print(f"\n{ok}/{ok+fail} tests pasaron")
    if fail: sys.exit(1)
