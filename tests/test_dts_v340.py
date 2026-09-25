"""v3.4.0: DTs reales en cada club, despidos entre la IA y ofertas de banquillo para el user."""
import sys, os, random, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(13)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import directiva as D, save
from alpha_football import entrenadores as EN, estilos as ES, correo as C
from alpha_football.data.entrenadores import DT_REALES
from alpha_football.models import alineacion_por_defecto
from alpha_football.ui.menu import load_league_teams, _ligas_por_division

_tmp = tempfile.mkdtemp()
save.guardar_en_slot = lambda *a, **k: None          # los tests no tocan los slots reales


def click(pos):
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def estado_carrera(tipo='premier', idx=0):
    liga = load_league_teams(tipo)
    mi = liga.equipos[idx]
    mi.alineacion_activa = alineacion_por_defecto(mi)
    primeras, segunda = _ligas_por_division(liga, {}, {})
    return {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
            'alineacion_activa': mi.alineacion_activa, 'primera_division': primeras,
            'segunda_division': segunda, 'datos_carrera': {}, 'historial': []}


# ── Task 5: DTs en cada club ────────────────────────────────────────────────

def test_todo_club_ia_tiene_dt():
    e = estado_carrera()
    EN.asegurar_dts(e)
    mi = e['mi_equipo']
    for eq, _liga in EN.clubes(e):
        dt = EN.dt_de(e, eq)
        if eq is mi:
            assert dt is None
        else:
            assert dt and dt['estilo'] in ES.ESTILOS_DT and eq.estilo_dt == dt['estilo']
    assert len(EN.dts(e)['libres']) >= 20
    print("  test_todo_club_ia_tiene_dt: OK")


def test_dt_reales_cubren_primeras():
    e = estado_carrera(); EN.asegurar_dts(e)
    for liga in e['primera_division'].values():
        for eq in liga.equipos:
            assert eq.nombre in DT_REALES, f"falta DT real para {eq.nombre}"
            nombre, estilo = DT_REALES[eq.nombre]
            assert estilo in ES.ESTILOS_DT and nombre
    print("  test_dt_reales_cubren_primeras: OK")


def test_asegurar_dts_idempotente():
    e = estado_carrera(); EN.asegurar_dts(e)
    antes = {k: v['id'] for k, v in EN.dts(e)['por_club'].items()}
    EN.asegurar_dts(e)
    assert {k: v['id'] for k, v in EN.dts(e)['por_club'].items()} == antes
    print("  test_asegurar_dts_idempotente: OK")


def test_calif_inicial():
    class Q: estrellas = 4.5
    assert EN.calif_inicial(Q()) == 65
    Q.estrellas = 1.0; assert EN.calif_inicial(Q()) == 30
    print("  test_calif_inicial: OK")


def test_override_editor():
    e = estado_carrera()
    otro = e['liga'].equipos[1]; otro.dt_nombre = "Profe Inventado"
    EN.asegurar_dts(e)
    assert EN.dt_de(e, otro)['nombre'] == "Profe Inventado"
    print("  test_override_editor: OK")


def test_mejor_libre_y_cambio_de_club():
    e = estado_carrera(); EN.asegurar_dts(e)
    mi, nuevo = e['mi_equipo'], e['liga'].equipos[3]
    dt_nuevo = EN.dt_de(e, nuevo)
    n_libres = len(EN.dts(e)['libres'])
    D.cambiar_de_club(e, nuevo)
    assert EN.dt_de(e, nuevo) is None                        # ahora el DT eres tú
    assert EN.dt_de(e, mi) is not None                       # tu club viejo contrató a alguien
    assert any(d['id'] == dt_nuevo['id'] for d in EN.dts(e)['libres'])
    assert len(EN.dts(e)['libres']) == n_libres               # entra uno, sale otro
    print("  test_mejor_libre_y_cambio_de_club: OK")


def test_persistencia_en_save():
    import json
    e = estado_carrera(); EN.asegurar_dts(e)
    copia = json.loads(json.dumps(e['datos_carrera']))       # datos_carrera debe ser JSON puro
    assert copia['dts']['por_club']
    print("  test_persistencia_en_save: OK")


# ── Task 6: despidos entre la IA y ofertas de banquillo ─────────────────────

class RngFijo(random.Random):
    """random() siempre devuelve `v` (para forzar despidos/ofertas)."""
    def __init__(self, v): super().__init__(1); self.v = v
    def random(self): return self.v


def _hundir(liga, eq):
    """Deja a `eq` último en la tabla y a mitad de temporada."""
    liga.jornada_actual = liga.num_jornadas // 2 + 1
    for x in liga.equipos:
        x.puntos = 30
    eq.puntos = 0


def _liga_ia(e):
    # una liga que NO es la del user, para aislar
    return next(l for l in e['primera_division'].values() if l is not e['liga'])


def test_posicion_y_esperado():
    e = estado_carrera(); EN.asegurar_dts(e)
    liga = _liga_ia(e); fuerte = max(liga.equipos, key=lambda x: x.ovr_promedio)
    assert EN.esperado(liga, fuerte) == 1
    _hundir(liga, fuerte)
    assert EN.posicion(liga, fuerte) == len(liga.equipos)
    print("  test_posicion_y_esperado: OK")


def test_despido_ia_umbral_y_tope():
    e = estado_carrera(); EN.asegurar_dts(e)
    e['datos_carrera']['calif_dt'] = 0                       # sin ofertas al user
    liga = _liga_ia(e); fuerte = max(liga.equipos, key=lambda x: x.ovr_promedio)
    viejo = EN.dt_de(e, fuerte)
    _hundir(liga, fuerte)
    EN.revisar_jornada(e, rng=RngFijo(0.99))                 # 99% > 8% → no echa
    assert EN.dt_de(e, fuerte)['id'] == viejo['id']
    EN.revisar_jornada(e, rng=RngFijo(0.0))
    assert EN.dt_de(e, fuerte)['id'] != viejo['id']
    assert any(d['id'] == viejo['id'] and d['calif'] == viejo['calif'] - 10 for d in EN.dts(e)['libres'])
    otro = sorted(liga.equipos, key=lambda x: -x.ovr_promedio)[1]
    dt_otro = EN.dt_de(e, otro); _hundir(liga, otro)
    EN.revisar_jornada(e, rng=RngFijo(0.0))                  # tope: 1 por liga por temporada
    assert EN.dt_de(e, otro)['id'] == dt_otro['id']
    print("  test_despido_ia_umbral_y_tope: OK")


def test_no_echa_antes_de_un_tercio():
    e = estado_carrera(); EN.asegurar_dts(e); e['datos_carrera']['calif_dt'] = 0
    liga = _liga_ia(e); fuerte = max(liga.equipos, key=lambda x: x.ovr_promedio)
    _hundir(liga, fuerte); liga.jornada_actual = 1
    viejo = EN.dt_de(e, fuerte)['id']
    EN.revisar_jornada(e, rng=RngFijo(0.0))
    assert EN.dt_de(e, fuerte)['id'] == viejo
    print("  test_no_echa_antes_de_un_tercio: OK")


def test_oferta_al_user_y_vencimiento():
    e = estado_carrera(); EN.asegurar_dts(e)
    e['datos_carrera']['calif_dt'] = 90
    liga = e['liga']
    club = max((x for x in liga.equipos if x is not e['mi_equipo']), key=lambda x: x.ovr_promedio)
    assert EN.en_banda(e, club)
    _hundir(liga, club)
    EN.revisar_jornada(e, rng=RngFijo(0.0))
    of = EN.ofertas_activas(e)
    assert len(of) == 1 and of[0]['club_id'] == str(club.id) and of[0]['jornadas'] == 3
    assert EN.dt_de(e, club)['interino'] and C.bandeja(e)[0]['accion']['pantalla'] == 'ofertas_dt_screen'
    for _ in range(3):
        EN.revisar_jornada(e, rng=RngFijo(0.99))
    assert not EN.ofertas_activas(e) and not EN.dt_de(e, club)['interino']
    print("  test_oferta_al_user_y_vencimiento: OK")


def test_en_banda_por_calif():
    e = estado_carrera(); mi = e['mi_equipo']
    class Q: pass
    q = Q(); q.ovr_promedio = mi.ovr_promedio + 7
    e['datos_carrera']['calif_dt'] = 75; assert EN.en_banda(e, q)
    e['datos_carrera']['calif_dt'] = 60; assert not EN.en_banda(e, q)
    q.ovr_promedio = mi.ovr_promedio + 4; assert EN.en_banda(e, q)
    e['datos_carrera']['calif_dt'] = 30; assert not EN.en_banda(e, q)
    print("  test_en_banda_por_calif: OK")


def test_aceptar_oferta_consistencia():
    e = estado_carrera(); EN.asegurar_dts(e); e['datos_carrera']['calif_dt'] = 90
    viejo = e['mi_equipo']; liga = e['liga']
    club = max((x for x in liga.equipos if x is not viejo), key=lambda x: x.ovr_promedio)
    _hundir(liga, club); EN.revisar_jornada(e, rng=RngFijo(0.0))
    nuevo = EN.aceptar_oferta(e, str(club.id))
    assert nuevo is club and e['mi_equipo'] is club
    assert EN.dt_de(e, club) is None and EN.dt_de(e, viejo) is not None
    assert not EN.ofertas_activas(e)
    ids = [d['id'] for d in EN.dts(e)['por_club'].values()]
    assert len(ids) == len(set(ids))                         # ningún DT en dos clubes
    print("  test_aceptar_oferta_consistencia: OK")


def test_rechazar_oferta():
    e = estado_carrera(); EN.asegurar_dts(e); e['datos_carrera']['calif_dt'] = 90
    liga = e['liga']
    club = max((x for x in liga.equipos if x is not e['mi_equipo']), key=lambda x: x.ovr_promedio)
    _hundir(liga, club); EN.revisar_jornada(e, rng=RngFijo(0.0))
    EN.rechazar_oferta(e, str(club.id))
    assert not EN.ofertas_activas(e) and not EN.dt_de(e, club)['interino']
    print("  test_rechazar_oferta: OK")


def test_cierre_temporada():
    e = estado_carrera(); EN.asegurar_dts(e)
    liga = _liga_ia(e); fuerte = max(liga.equipos, key=lambda x: x.ovr_promedio)
    _hundir(liga, fuerte); viejo = EN.dt_de(e, fuerte)['id']
    EN.dts(e)['despidos_temp'] = {'x': 1}
    EN.cierre_temporada(e, rng=RngFijo(0.0))
    assert EN.dt_de(e, fuerte)['id'] != viejo and EN.dts(e)['despidos_temp'] == {}
    print("  test_cierre_temporada: OK")


def test_ofertas_dt_screen():
    from alpha_football.ui import ofertas_dt_screen as S
    e = estado_carrera(); EN.asegurar_dts(e); e['datos_carrera']['calif_dt'] = 90
    liga = e['liga']
    club = max((x for x in liga.equipos if x is not e['mi_equipo']), key=lambda x: x.ovr_promedio)
    _hundir(liga, club); EN.revisar_jornada(e, rng=RngFijo(0.0))
    pygame.event.clear(); assert S.render(screen, e) is None
    click(S.rect_aceptar(0).center)
    assert S.render(screen, e) == 'contrato_dt_screen' and e['contrato_modo'] == 'alta'
    assert e['mi_equipo'] is club
    print("  test_ofertas_dt_screen: OK")


TESTS = [test_todo_club_ia_tiene_dt, test_dt_reales_cubren_primeras, test_asegurar_dts_idempotente,
         test_calif_inicial, test_override_editor, test_mejor_libre_y_cambio_de_club, test_persistencia_en_save,
         test_posicion_y_esperado, test_despido_ia_umbral_y_tope, test_no_echa_antes_de_un_tercio,
         test_oferta_al_user_y_vencimiento, test_en_banda_por_calif, test_aceptar_oferta_consistencia,
         test_rechazar_oferta, test_cierre_temporada, test_ofertas_dt_screen]


if __name__ == '__main__':
    fail = 0
    for t in TESTS:
        try:
            t()
        except Exception as ex:
            fail += 1
            import traceback; traceback.print_exc()
            print(f"  {t.__name__}: FAIL - {ex}")
    print(f"\n{len(TESTS) - fail}/{len(TESTS)} tests pasaron")
    if fail:
        sys.exit(1)
