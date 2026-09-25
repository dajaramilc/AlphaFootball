"""v3.7.0: 8 países, ligas de 12 — registro central de países (paises.py) y jornadas derivadas."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame; pygame.init()
random.seed(13)
screen = pygame.display.set_mode((1280, 720))

from alpha_football import paises as P


def test_registro_paises():
    assert P.TIPOS_LIGA == ('premier', 'laliga', 'seriea', 'brasil', 'argentina', 'betplay', 'uruguay', 'ecuador')
    assert P.EUROPA == ('premier', 'laliga', 'seriea') and 'uruguay' in P.SUDAMERICA
    assert P.num_jornadas(12) == 22 and P.num_jornadas(6) == 10
    assert P.es_sudamerica('libertadores') and not P.es_europa('ecuador')
    from alpha_football.ui import menu
    assert tuple(menu.TIPOS_LIGA) == P.TIPOS_LIGA and len(menu.PAISES_DISPONIBLES) == 8
    print("  test_registro_paises: OK")


def test_sin_listas_fijas_de_5_ligas():
    import subprocess
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = subprocess.run([sys.executable, '-c', "import re,pathlib;print(sum(1 for f in pathlib.Path('alpha_football').rglob('*.py') for l in f.read_text(encoding='utf-8').splitlines() if re.search(r\"\\['premier', 'laliga'\\]|\\('premier', 'laliga'\\)|\\['betplay', 'brasil', 'argentina'\\]\", l)))"],
                         capture_output=True, text=True, cwd=raiz)
    assert out.stdout.strip() == '0', out.stdout
    print("  test_sin_listas_fijas_de_5_ligas: OK")


def test_nombres_y_regiones():
    # v3.7.0: los nombres de las ligas existentes se conservan; las tablas por liga cubren los 8 países.
    assert P.nombre_liga_defecto('premier', 1) == 'Premier League Parodia'
    assert P.nombre_liga_defecto('laliga', 2) == 'LaLiga EA Sports Parodia - Segunda División'
    assert P.nombre_liga_defecto('seriea', 1) == 'Serie A Parodia' and P.nombre_liga_defecto('seriea', 2) == 'Serie B Parodia'
    assert P.pais_de('ecuador')['nombre'] == 'Ecuador' and P.pais_de('nada') is None
    from alpha_football.market import fuerza_liga, TIPOS_LATAM
    from alpha_football.mercado_ia import PRESUPUESTO_RANGO
    from alpha_football.premios import PESO_LIGA_1A
    from alpha_football.negociacion import PAIS_CORTO
    from alpha_football.ui.copa_screen import CUPOS_COPA, LIGAS_COPA
    from alpha_football.plantilla import TIPOS_SUDAMERICA
    for t in P.TIPOS_LIGA:
        assert t in PESO_LIGA_1A and t in PAIS_CORTO and t in CUPOS_COPA, t
        assert (t, 1) in PRESUPUESTO_RANGO and (t, 2) in PRESUPUESTO_RANGO, t
    assert fuerza_liga('seriea') == fuerza_liga('laliga') and fuerza_liga('uruguay') == fuerza_liga('betplay')
    assert 'ecuador' in TIPOS_LATAM and 'uruguay' in TIPOS_SUDAMERICA and 'seriea' not in TIPOS_SUDAMERICA
    assert 'seriea' in LIGAS_COPA['Champions'] and 'ecuador' in LIGAS_COPA['Libertadores']
    print("  test_nombres_y_regiones: OK")


def test_ligas_sin_datos_no_rompen():
    # v3.7.0: mientras no existan los datos de un país, la carga devuelve None (no un mock).
    from alpha_football.ui.menu import load_league_teams, load_division_teams
    for tipo in P.TIPOS_LIGA:
        l1 = load_league_teams(tipo)
        assert l1 is None or (l1.tipo == tipo and l1.num_jornadas == P.num_jornadas(len(l1.equipos))), tipo
        l2 = load_division_teams(tipo, 2)
        assert l2 is None or l2.num_jornadas == P.num_jornadas(len(l2.equipos)), tipo
    print("  test_ligas_sin_datos_no_rompen: OK")


# --- v3.7.0 Task 5: carga completa, merge con base editada, migración y rendimiento ---

def estado_carrera(tipo='premier', idx=0):
    from alpha_football.models import alineacion_por_defecto
    from alpha_football.ui.menu import load_league_teams, _ligas_por_division
    liga = load_league_teams(tipo)
    mi = liga.equipos[idx]
    mi.alineacion_activa = alineacion_por_defecto(mi)
    primeras, segunda = _ligas_por_division(liga, {}, {})
    return {'liga': liga, 'mi_equipo': mi, 'equipos': liga.equipos, 'temporada': 1,
            'alineacion_activa': mi.alineacion_activa, 'primera_division': primeras,
            'segunda_division': segunda, 'datos_carrera': {}, 'historial': []}


_ESTADO = {}


def _estado_compartido():
    # v3.7.0: cargar las 16 ligas cuesta; los tests de solo lectura comparten un estado.
    if not _ESTADO:
        _ESTADO['e'] = estado_carrera()
    return _ESTADO['e']


def test_carga_16_ligas():
    e = _estado_compartido()
    for tipo in P.TIPOS_LIGA:
        for div in (e['primera_division'], e['segunda_division']):
            liga = div[tipo]
            assert len(liga.equipos) == 12 and liga.num_jornadas == 22, (tipo, len(liga.equipos))
            assert all(len(x.jugadores) >= 20 for x in liga.equipos), tipo
    print("  test_carga_16_ligas: OK")


def test_sin_duplicados_globales():
    e = _estado_compartido()
    nombres = [x.nombre for d in ('primera_division', 'segunda_division') for l in e[d].values() for x in l.equipos]
    assert len(nombres) == len(set(nombres)), sorted({n for n in nombres if nombres.count(n) > 1})
    from alpha_football.market import pool_internacional
    choque = set(nombres) & {c.nombre for _j, c, _t in pool_internacional(e)}
    assert not choque, choque
    print("  test_sin_duplicados_globales: OK")


def test_merge_base_editada():
    import json, shutil
    ruta = 'alpha_football_edited_db.json'; respaldo = ruta + '.bak_test'
    if os.path.exists(ruta): shutil.copy(ruta, respaldo)
    try:
        from alpha_football.ui.menu import load_league_teams
        if os.path.exists(ruta): os.remove(ruta)
        base = load_league_teams('premier')
        editados = [x.to_dict() for x in base.equipos[:6]]; editados[0]['nombre'] = 'Club Editado FC'
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump({'premier': editados, '_ligas': {'premier': {'nombre': 'X'}}}, f)
        liga = load_league_teams('premier')
        nombres = [x.nombre for x in liga.equipos]
        assert len(liga.equipos) == 12 and 'Club Editado FC' in nombres and len(set(nombres)) == 12, nombres
        assert base.equipos[0].nombre not in nombres, "el club renombrado no vuelve con su nombre de los datos"
        assert liga.num_jornadas == 22
        assert load_league_teams('seriea') is not None and len(load_league_teams('seriea').equipos) == 12
    finally:
        os.remove(ruta)
        if os.path.exists(respaldo): shutil.move(respaldo, ruta)
    print("  test_merge_base_editada: OK")


def test_migracion_save_viejo():
    e = estado_carrera()
    for d in ('primera_division', 'segunda_division'):
        for l in e[d].values():
            l.equipos[:] = l.equipos[:6]; l.num_jornadas = 10
    for t in ('seriea', 'uruguay', 'ecuador'):
        e['primera_division'].pop(t); e['segunda_division'].pop(t)
    P.completar_ligas(e)
    for t in P.TIPOS_LIGA:
        for d in ('primera_division', 'segunda_division'):
            l = e[d][t]
            assert len(l.equipos) == 12 and l.num_jornadas == 22, (t, d, len(l.equipos))
    nombres = [x.nombre for d in ('primera_division', 'segunda_division') for l in e[d].values() for x in l.equipos]
    assert len(nombres) == len(set(nombres))
    assert e['liga'] is e['primera_division']['premier'] and e['equipos'] is e['liga'].equipos
    P.completar_ligas(e)   # idempotente
    assert all(len(l.equipos) == 12 for d in ('primera_division', 'segunda_division') for l in e[d].values())
    print("  test_migracion_save_viejo: OK")


def test_avanzar_temporada_completa_save_viejo():
    # v3.7.0: el save viejo cierra su temporada de 10 jornadas y al avanzar queda en 12/22.
    from alpha_football import save
    from alpha_football.ui import resumen_temporada_screen as R
    save.guardar_en_slot = lambda *a, **k: None
    e = estado_carrera()
    for d in ('primera_division', 'segunda_division'):
        for l in e[d].values():
            l.equipos[:] = l.equipos[:6]; l.num_jornadas = 10
    for t in ('uruguay',):
        e['primera_division'].pop(t); e['segunda_division'].pop(t)
    R.avanzar_nueva_temporada(e)
    assert e['temporada'] == 2
    for t in P.TIPOS_LIGA:
        assert len(e['primera_division'][t].equipos) == 12 and e['segunda_division'][t].num_jornadas == 22, t
    assert len(e['liga'].equipos) == 12 and e['liga'].calendario == []
    print("  test_avanzar_temporada_completa_save_viejo: OK")


def test_ascenso_mantiene_12():
    from alpha_football.ui.resumen_temporada_screen import _swap_promocion
    e = estado_carrera()
    l1, l2 = e['primera_division']['seriea'], e['segunda_division']['seriea']
    _swap_promocion(l1, l2)
    assert len(l1.equipos) == 12 and len(l2.equipos) == 12
    print("  test_ascenso_mantiene_12: OK")


def test_rendimiento_jornada():
    import time
    from alpha_football.ui.league_screen import simular_jornada_segunda_division, inicializar_calendario_liga
    from alpha_football.ui.match_screen import simular_otros_partidos
    e = estado_carrera()
    for d in ('primera_division', 'segunda_division'):
        for l in e[d].values():
            inicializar_calendario_liga(l)
    t0 = time.perf_counter()
    for l in e['primera_division'].values():
        simular_otros_partidos(l, l.jornada_actual)
    simular_jornada_segunda_division(e)
    dt = time.perf_counter() - t0
    assert dt < 1.5, dt
    print(f"  test_rendimiento_jornada: OK ({dt:.2f} s)")


# --- v3.7.0 Task 6: editor de ligas, renombrar liga y menús del alta ---

def test_renombrar_liga():
    import shutil, json
    ruta = 'alpha_football_edited_db.json'; respaldo = ruta + '.bak_test'
    nombre_usuario = P.nombre_liga('seriea', 1)                # el que tenga la base editada del usuario
    if os.path.exists(ruta): shutil.move(ruta, respaldo)      # v3.9.1: sin los renombres del usuario
    try:
        P.renombrar_liga('seriea', 1, 'Calcio de Mentira ' + 'x' * 80)
        assert P.nombre_liga('seriea', 1).startswith('Calcio de Mentira') and len(P.nombre_liga('seriea', 1)) <= 40
        with open(ruta, encoding='utf-8') as f:
            db = json.load(f)
        assert db['_ligas']['seriea']['nombre'].startswith('Calcio')
        assert P.nombre_liga('seriea', 2) == 'Serie B Parodia'
        P.renombrar_liga('seriea', 2, '  ')          # vacío = vuelve al nombre por defecto
        assert P.nombre_liga('seriea', 2) == 'Serie B Parodia'
        from alpha_football.ui.menu import load_league_teams
        liga = load_league_teams('seriea')           # la clave _ligas no es una liga
        assert liga is not None and len(liga.equipos) == 12 and liga.nombre.startswith('Calcio')
    finally:
        if os.path.exists(ruta): os.remove(ruta)
        if os.path.exists(respaldo): shutil.move(respaldo, ruta)
    assert P.nombre_liga('seriea', 1) == nombre_usuario        # se restauró la base del usuario
    print("  test_renombrar_liga: OK")


def test_alta_ocho_paises():
    from alpha_football.ui import menu
    rects = menu.rects_paises()
    assert len(rects) == 8 and all(0 <= r.x and r.right <= 1280 and r.bottom <= 698 for r in rects)
    assert not any(a.colliderect(b) for i, a in enumerate(rects) for b in rects[i + 1:])
    assert menu.texto_division('premier', 1) == "12 equipos · 22 jornadas"
    assert menu.texto_division('ecuador', 2) == "12 equipos · 22 jornadas"
    e = {'menu_step': 'select_country'}
    pygame.event.clear()
    menu.render(screen, e)
    print("  test_alta_ocho_paises: OK")


def test_editor_pestanas_paises():
    from alpha_football.ui import edit_screen as ES
    claves = [c for c, _t in ES.pestanas_editor()]
    assert claves[:8] == list(P.TIPOS_LIGA) and claves[-2:] == ['libertadores', 'champions']
    e = {}
    db = {'premier': [], 'champions': [], 'libertadores': []}   # base vieja: sin 2ª ni países nuevos
    ES._backfill_ligas(db)
    for t in P.TIPOS_LIGA:
        assert len(db[t]) == 12 and len(db[P.clave_db(t, 2)]) == 12, t
    nombres = [x['nombre'] for t in P.TIPOS_LIGA for d in (1, 2) for x in db[P.clave_db(t, d)]]
    assert len(nombres) == len(set(nombres))
    e['edited_db'] = db
    e['edit_liga_sel'] = 'seriea'
    ES.cambiar_division_editor(e)
    assert e['edit_liga_sel'] == 'segunda_seriea'
    ES.cambiar_division_editor(e)
    assert e['edit_liga_sel'] == 'seriea'
    pygame.event.clear()
    assert ES.render(screen, e) is None
    ES.set_nombre_liga_editor(e, 'Calcio Trucho')
    assert db['_ligas']['seriea']['nombre'] == 'Calcio Trucho'
    e['edit_liga_sel'] = 'segunda_seriea'
    ES.set_nombre_liga_editor(e, 'B' * 60)
    assert db['_ligas']['seriea']['nombre_2a'] == 'B' * 40
    assert ES.render(screen, e) is None
    print("  test_editor_pestanas_paises: OK")


TESTS = [test_registro_paises, test_sin_listas_fijas_de_5_ligas, test_nombres_y_regiones,
         test_ligas_sin_datos_no_rompen, test_carga_16_ligas, test_sin_duplicados_globales,
         test_merge_base_editada, test_migracion_save_viejo, test_avanzar_temporada_completa_save_viejo,
         test_ascenso_mantiene_12, test_rendimiento_jornada, test_renombrar_liga, test_alta_ocho_paises,
         test_editor_pestanas_paises]


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
