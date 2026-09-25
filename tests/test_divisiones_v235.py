"""v2.3.5: flujo real de 1ª/2ª división a lo largo de varias temporadas.

Cubre lo que rompió v2.3.4: 2ª divisiones que no se guardaban, 1ª recargada de disco
cuando el user está en 2ª, ligas de fondo congeladas tras la T1 y equipos duplicados.
"""
import sys, os, random, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(7)

from alpha_football import save as _save_mod
_TMP_SAVES = tempfile.mkdtemp(prefix="af_test_saves_")
_orig = _save_mod.guardar_en_slot
_save_mod.guardar_en_slot = lambda estado, n, nombre, carpeta=None: _orig(estado, n, nombre, _TMP_SAVES)

from alpha_football.models import EstadoJuego
from alpha_football.ui.menu import load_league_teams, _ligas_por_division
from alpha_football.ui.league_screen import (
    simular_jornada_segunda_division, _simular_jornada_liga_fondo)
from alpha_football.ui.resumen_temporada_screen import avanzar_nueva_temporada

TIPOS = ('betplay', 'laliga', 'premier', 'brasil', 'argentina')


def nuevo_estado():
    liga = load_league_teams('betplay')
    primeras, segunda = _ligas_por_division(liga, {}, {})
    return {
        'liga': liga, 'mi_equipo': liga.equipos[0], 'equipos': liga.equipos,
        'temporada': 1, 'historial': [], 'transfer_log': [], 'liga_usuario_division': 1,
        'primera_division': primeras, 'segunda_division': segunda,
    }


def jugar_temporada(estado, user_pts=None):
    """Juega toda la liga del user (como si él jugara) + las de fondo, jornada a jornada."""
    liga = estado['liga']
    while _simular_jornada_liga_fondo(liga):
        simular_jornada_segunda_division(estado)
    if user_pts is not None:
        estado['mi_equipo'].puntos = user_pts


def ids(liga):
    return {e.id for e in liga.equipos}


def check_consistencia(estado):
    liga = estado['liga']
    seg = estado['segunda_division']['betplay']
    pri = estado['primera_division']['betplay']
    assert (pri if liga.division == 1 else seg) is liga, "la liga del user debe ser la de su mapa, no una copia"
    otra = seg if liga.division == 1 else pri
    assert otra is not None and otra is not liga
    assert not (ids(liga) & ids(otra)), "equipo duplicado entre 1ª y 2ª"
    assert estado['mi_equipo'] in liga.equipos
    todas = list(estado['primera_division'].values()) + list(estado['segunda_division'].values())
    from alpha_football.paises import TIPOS_LIGA as _T   # v3.7.0: 8 países × 2 divisiones
    assert len(todas) == 2 * len(_T)
    for l in todas:
        assert l.jornada_actual == 1 and not l.calendario, f"{l.nombre} no se reinició"
        assert all(e.pj == 0 and e.puntos == 0 for e in l.equipos), f"{l.nombre} con stats viejas"


def roundtrip(estado):
    """Guardar y cargar como lo hace el juego (datos_estado -> JSON -> EstadoJuego)."""
    datos = {"ligas": [estado['liga'].to_dict()], "equipo_usuario_id": estado['mi_equipo'].id,
             "liga_usuario_id": estado['liga'].tipo, "temporada": estado['temporada'],
             **_save_mod.campos_divisiones(estado)}
    return EstadoJuego.from_dict(EstadoJuego.from_dict(datos).to_dict())


def test_descenso_y_ascenso():
    estado = nuevo_estado()
    n1 = len(estado['liga'].equipos)

    # T1: el user queda último -> desciende
    jugar_temporada(estado, user_pts=-1)
    avanzar_nueva_temporada(estado)
    assert estado['promo_releg_data']['user_descendio']
    assert estado['liga'].division == 2 and estado['liga_usuario_division'] == 2
    assert estado['copa_user_en_copa'] is False
    assert len(estado['primera_division']['betplay'].equipos) == n1
    check_consistencia(estado)

    # Guardar/cargar en 2ª: la 1ª del país y las 2ª vuelven intactas
    cargado = roundtrip(estado)
    assert all(ids(cargado.primera_division[t]) == ids(estado['primera_division'][t]) for t in TIPOS)
    assert ids(cargado.segunda_division['betplay']) == ids(estado['liga'])
    assert cargado.ligas[0].division == 2

    # T2 en 2ª: la 1ª del país se juega de fondo completa
    jugar_temporada(estado, user_pts=999)
    liga_1a = estado['primera_division']['betplay']
    assert any(p.jugado for p in liga_1a.calendario), "la 1ª no avanza de fondo"
    # La 1ª (14 jornadas) es más larga que la 2ª (10): al cerrar se completa
    from alpha_football.ui.league_screen import completar_ligas_de_fondo
    completar_ligas_de_fondo(estado)
    assert all(p.jugado for p in liga_1a.calendario), "1ª de fondo incompleta"
    avanzar_nueva_temporada(estado)
    assert estado['promo_releg_data']['user_ascendio']
    assert estado['liga'].division == 1 and estado['primera_division']['betplay'] is estado['liga']
    # v3.0.0: ascender NO da copa; la copa solo se gana en los puestos de la tabla de 1ª
    assert estado['copa_user_en_copa'] is False and estado['copa_clasificado'] is False
    check_consistencia(estado)

    # Guardar/cargar en 1ª: la 2ª guardada no duplica equipos
    cargado = roundtrip(estado)
    assert not (ids(cargado.ligas[0]) & ids(cargado.segunda_division['betplay']))
    print("  test_descenso_y_ascenso: OK")


def test_segundas_siguen_jugando_cada_temporada():
    estado = nuevo_estado()
    for _ in range(3):
        jugar_temporada(estado, user_pts=999)
        for l in list(estado['primera_division'].values()) + list(estado['segunda_division'].values()):
            if l is estado['liga']:
                continue
            assert l.calendario and any(p.jugado for p in l.calendario), f"{l.nombre} no jugó"
        avanzar_nueva_temporada(estado)
    assert estado['temporada'] == 4
    print("  test_segundas_siguen_jugando_cada_temporada: OK")


def test_promo_screen_vuelve_a_liga():
    from alpha_football.ui import promo_releg_screen
    screen = pygame.display.set_mode((1280, 720))
    estado = {'promo_releg_data': {'ascendidos': [], 'descendidos': []}}
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    assert promo_releg_screen.render(screen, estado) == "league_screen"
    assert 'promo_releg_data' not in estado
    print("  test_promo_screen_vuelve_a_liga: OK")


if __name__ == '__main__':
    tests = [test_descenso_y_ascenso, test_segundas_siguen_jugando_cada_temporada,
             test_promo_screen_vuelve_a_liga]
    fail = 0
    for t in tests:
        try:
            t()
        except Exception as e:
            fail += 1
            import traceback; traceback.print_exc()
            print(f"  {t.__name__}: FAIL - {e}")
    print(f"\n{len(tests) - fail}/{len(tests)} tests pasaron")
    if fail:
        sys.exit(1)
